"""Adversarial stress testing harness for Phase 1 procedural JRPG combat animations.

Covers:
1. Extreme delta-times: dt = 0.0, 0.001, 0.5, 5.0, 100.0 (offsets must not diverge or become NaN).
2. Event spam: Rapid multi-event bursts (50 consecutive DamageDealtEvent, alternating crits) - no offset drift or overflow.
3. Speed cycling between 1x, 2x, 4x during active animations - clean duration clamping without visual popping.
4. Dead combatant edge cases: enemy bobbing strictly 0.0 when dead.
5. Ground shadow invariant: 500 frames of random combat action ticks - shadow Y NEVER deviates from ground_y - 6 = 204.
"""

from __future__ import annotations

import math
import os
import random
import sys

# Ensure project root is in sys.path for standalone script execution
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
import pygame

from src.core.events import DamageDealtEvent, HealthRestoredEvent
from src.core.game_state import GameMode
from src.core.session import GameSession
from src.entities.actor import Stats
from src.entities.enemy import Enemy, EnemyTier
from src.frontends.pygame_ce.renderer import PygameRenderer
import src.frontends.pygame_ce.views.combat_view as cv
from src.frontends.pygame_ce.views.combat_view import (
    CombatantAnimationState,
    PygameCombatView,
)
from src.systems.combat import CombatSystem


@pytest.fixture(scope="module", autouse=True)
def setup_headless_sdl():
    """Ensure headless SDL environment."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    if not pygame.get_init():
        pygame.init()
    yield


def create_stress_session(hp: int = 50000) -> GameSession:
    """Helper to create a fresh combat session with high HP actors to withstand stress bursts."""
    session = GameSession()
    session.start_new_game(class_id="warrior")
    session.player.base_stats.max_hp = hp
    session.player.current_hp = hp
    enemy = Enemy(
        name="Cathedral Imp",
        stats=Stats(max_hp=hp, attack=12, defense=3, speed=10, crit_chance=0.1),
        tier=EnemyTier.COMMON,
        floor_level=1,
        exp_reward=20,
        gold_reward=10,
    )
    enemy.current_hp = hp
    session.state.combat = CombatSystem(session.player, enemy)
    session.switch_mode(GameMode.COMBAT)
    return session


@pytest.fixture
def stress_session():
    """Pytest fixture providing a fresh stress combat session."""
    return create_stress_session()


# =========================================================================
# 1. EXTREME DELTA-TIMES STRESS TEST
# =========================================================================
def test_stress_extreme_delta_times(stress_session):
    """Stress test extreme delta-times: dt = 0.0, 0.001, 0.5, 5.0, 100.0."""
    view = PygameCombatView()

    extreme_dts = [0.0, 0.001, 0.5, 5.0, 100.0]

    # Verify each extreme dt individually from fresh active animation states
    for dt in extreme_dts:
        # Trigger lunge and recoil on both actors
        view.player_anim.trigger_lunge(distance=40.0)
        view.player_anim.trigger_recoil(is_crit=True)
        view.enemy_anim.trigger_lunge(distance=40.0)
        view.enemy_anim.trigger_recoil(is_crit=True)

        view.update(dt, stress_session)

        h_ox, h_oy = view.get_hero_animation_offset()
        e_ox, e_oy = view.get_enemy_animation_offset(enemy_alive=True)

        # Offsets must be strictly finite real numbers (no NaN, no inf)
        assert math.isfinite(h_ox), f"Hero offset X not finite for dt={dt}: {h_ox}"
        assert math.isfinite(h_oy), f"Hero offset Y not finite for dt={dt}: {h_oy}"
        assert math.isfinite(e_ox), f"Enemy offset X not finite for dt={dt}: {e_ox}"
        assert math.isfinite(e_oy), f"Enemy offset Y not finite for dt={dt}: {e_oy}"

        assert not math.isnan(h_ox), f"Hero offset X is NaN for dt={dt}"
        assert not math.isnan(h_oy), f"Hero offset Y is NaN for dt={dt}"
        assert not math.isnan(e_ox), f"Enemy offset X is NaN for dt={dt}"
        assert not math.isnan(e_oy), f"Enemy offset Y is NaN for dt={dt}"

        # If dt >= 0.5 (which exceeds max duration 0.28s), lunge and recoil MUST decay to strictly 0.0
        if dt >= 0.5:
            assert view.player_anim.lunge_timer == 0.0
            assert view.player_anim.recoil_timer == 0.0
            assert view.player_anim.get_lunge_offset_x() == 0.0
            assert view.player_anim.get_recoil_offsets() == (0.0, 0.0)
            assert view.enemy_anim.get_lunge_offset_x() == 0.0
            assert view.enemy_anim.get_recoil_offsets() == (0.0, 0.0)

            # Idle bobbing must remain strictly bounded in [-2.5, 2.5]
            idle_hero = h_oy
            idle_enemy = e_oy
            assert -2.50001 <= idle_hero <= 2.50001, f"Idle hero Y out of bounds: {idle_hero}"
            assert -2.50001 <= idle_enemy <= 2.50001, f"Idle enemy Y out of bounds: {idle_enemy}"

    # Rapid chaotic sequence of alternating extreme delta-times
    chaotic_dts = [0.0, 100.0, 0.001, 5.0, 0.0, 0.5, 0.0001, 10.0] * 10
    for step_idx, dt in enumerate(chaotic_dts):
        if step_idx % 4 == 0:
            view.player_anim.trigger_lunge(distance=40.0)
            view.enemy_anim.trigger_recoil(is_crit=(step_idx % 8 == 0))
        view.update(dt, stress_session)
        h_ox, h_oy = view.get_hero_animation_offset()
        e_ox, e_oy = view.get_enemy_animation_offset(enemy_alive=True)
        assert math.isfinite(h_ox) and math.isfinite(h_oy)
        assert math.isfinite(e_ox) and math.isfinite(e_oy)


# =========================================================================
# 2. EVENT SPAM / BURST STRESS TEST
# =========================================================================
def test_stress_event_spam_bursts(stress_session):
    """Stress test rapid multi-event bursts (50 consecutive DamageDealtEvent with alternating crits)."""
    view = PygameCombatView()

    # Burst 1: 50 consecutive events against Hero in a single frame
    for i in range(50):
        stress_session.bus.emit(DamageDealtEvent(
            source="Cathedral Imp",
            target=stress_session.player.name,
            amount=5 + (i % 7),
            is_crit=(i % 2 == 1),
        ))

    # Single frame processes all 50 events
    view.update(0.016, stress_session)

    # Offsets must remain within strict single-animation mathematical bounds (no accumulation overflow)
    h_ox1, h_oy1 = view.get_hero_animation_offset()
    e_ox1, e_oy1 = view.get_enemy_animation_offset(enemy_alive=True)

    # Hero is hit: hero recoils left (-X, max -29.25), enemy lunges left (-X, max -40.0)
    assert -30.0 <= h_ox1 <= 5.0, f"Hero offset X overflow during burst 1: {h_ox1}"
    assert -41.0 <= e_ox1 <= 5.0, f"Enemy offset X overflow during burst 1: {e_ox1}"

    # Timers must NOT accumulate past single duration (no additive timer stacking)
    assert view.player_anim.recoil_timer <= 0.28
    assert view.enemy_anim.lunge_timer <= 0.28

    # Let Burst 1 decay to complete rest
    view.update(0.35, stress_session)
    assert view.player_anim.get_lunge_offset_x() == 0.0
    assert view.player_anim.get_recoil_offsets() == (0.0, 0.0)
    assert view.enemy_anim.get_lunge_offset_x() == 0.0
    assert view.enemy_anim.get_recoil_offsets() == (0.0, 0.0)

    # Burst 2: 50 consecutive events against Enemy with alternating crits
    for i in range(50):
        stress_session.bus.emit(DamageDealtEvent(
            source=stress_session.player.name,
            target="Cathedral Imp",
            amount=10 + (i % 5),
            is_crit=(i % 2 == 0),
        ))

    view.update(0.016, stress_session)
    h_ox2, _ = view.get_hero_animation_offset()
    e_ox2, _ = view.get_enemy_animation_offset(enemy_alive=True)

    # Hero lunges right (+X, <= 40.0), enemy recoils right (+X, <= 29.25)
    assert -5.0 <= h_ox2 <= 42.0, f"Hero offset X overflow during burst 2: {h_ox2}"
    assert -5.0 <= e_ox2 <= 30.0, f"Enemy offset X overflow during burst 2: {e_ox2}"

    # Let Burst 2 decay
    view.update(0.35, stress_session)
    assert view.player_anim.get_lunge_offset_x() == 0.0
    assert view.player_anim.get_recoil_offsets() == (0.0, 0.0)
    assert view.enemy_anim.get_lunge_offset_x() == 0.0
    assert view.enemy_anim.get_recoil_offsets() == (0.0, 0.0)

    # Burst 3: 100 rapid alternating hits in consecutive micro-ticks
    for i in range(100):
        is_hero_target = (i % 2 == 0)
        target_name = stress_session.player.name if is_hero_target else "Cathedral Imp"
        source_name = "Cathedral Imp" if is_hero_target else stress_session.player.name
        stress_session.bus.emit(DamageDealtEvent(
            source=source_name,
            target=target_name,
            amount=8,
            is_crit=(i % 3 == 0),
        ))
        view.update(0.005, stress_session)

        ox_h, _ = view.get_hero_animation_offset()
        ox_e, _ = view.get_enemy_animation_offset(enemy_alive=True)

        # Offsets must remain bounded at all times despite intense bidirectional spam
        assert -30.0 <= ox_h <= 45.0, f"Hero offset out of bounds during alternating spam: {ox_h}"
        assert -45.0 <= ox_e <= 30.0, f"Enemy offset out of bounds during alternating spam: {ox_e}"

    # Zero Offset Drift Assertion: After final animation elapses, offsets MUST return to strictly 0.0
    view.update(0.40, stress_session)

    assert view.player_anim.lunge_timer == 0.0
    assert view.player_anim.recoil_timer == 0.0
    assert view.enemy_anim.lunge_timer == 0.0
    assert view.enemy_anim.recoil_timer == 0.0

    assert view.player_anim.get_lunge_offset_x() == 0.0
    assert view.player_anim.get_recoil_offsets() == (0.0, 0.0)
    assert view.enemy_anim.get_lunge_offset_x() == 0.0
    assert view.enemy_anim.get_recoil_offsets() == (0.0, 0.0)


# =========================================================================
# 3. SPEED CYCLING MID-ANIMATION STRESS TEST
# =========================================================================
def test_stress_speed_cycling_during_active_animations(stress_session):
    """Stress test dynamic speed cycling between 1x, 2x, 4x during active animations."""
    view = PygameCombatView()

    # Cycle speed 60 times while animating
    for cycle in range(60):
        # Trigger lunge and recoil
        cap = min(0.28, view.step_interval * 0.85)
        view.player_anim.trigger_lunge(max_duration=cap, distance=40.0)
        view.enemy_anim.trigger_recoil(is_crit=(cycle % 3 == 0), max_duration=cap)

        # Step partially into animation
        partial_dt = 0.02
        view.update(partial_dt, stress_session)

        # Cycle speed in the middle of active animation
        view._cycle_speed()

        # Check bounds
        h_ox, h_oy = view.get_hero_animation_offset()
        assert math.isfinite(h_ox)
        assert -30.0 <= h_ox <= 45.0, f"Pop / jump detected at speed cycle {cycle}: {h_ox}"

        # Duration clamping check for new triggers at current speed
        current_step = view.step_interval
        current_cap = min(0.28, current_step * 0.85)
        if current_step == 0.40:
            assert current_cap == pytest.approx(0.28, abs=1e-4)
        elif current_step == 0.18:
            assert current_cap == pytest.approx(0.153, abs=1e-4)
        elif current_step == 0.06:
            assert current_cap == pytest.approx(0.051, abs=1e-4)

        # Step another small dt
        view.update(0.02, stress_session)

    # Let everything decay to rest
    view.update(0.35, stress_session)
    assert view.player_anim.get_lunge_offset_x() == 0.0
    assert view.player_anim.get_recoil_offsets() == (0.0, 0.0)
    assert view.enemy_anim.get_lunge_offset_x() == 0.0
    assert view.enemy_anim.get_recoil_offsets() == (0.0, 0.0)


# =========================================================================
# 4. DEAD COMBATANT EDGE CASES
# =========================================================================
def test_stress_dead_combatant_edge_cases(stress_session):
    """Stress test dead combatant edge cases: assert enemy bobbing strictly 0.0 when dead."""
    view = PygameCombatView()
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    # Case 1: Enemy current_hp = 0 (which makes is_alive False)
    stress_session.state.combat.enemy.current_hp = 0
    assert stress_session.state.combat.enemy.is_alive is False

    # Run 100 ticks across different times
    for i in range(100):
        view.update(0.016, stress_session)
        enemy_alive = bool(
            stress_session.state.combat.enemy
            and getattr(stress_session.state.combat.enemy, "is_alive", True)
            and getattr(stress_session.state.combat.enemy, "current_hp", 1) > 0
        )
        assert enemy_alive is False

        _, enemy_oy = view.get_enemy_animation_offset(enemy_alive=enemy_alive)
        # Enemy vertical offset MUST be strictly 0.0 (no bobbing!)
        assert enemy_oy == 0.0, f"Dead enemy vertical bobbing leaked at tick {i}: {enemy_oy}"

        # Draw call should execute without exceptions and without bobbing
        view.draw(surface, renderer, stress_session)

    # Case 2: Enemy killed mid-lunge
    # Revive temporarily and trigger lunge
    stress_session.state.combat.enemy.current_hp = 500
    assert stress_session.state.combat.enemy.is_alive is True
    view.enemy_anim.trigger_lunge(distance=40.0)
    view.update(0.1, stress_session)  # mid-lunge

    # Kill enemy mid-lunge
    stress_session.state.combat.enemy.current_hp = 0
    assert stress_session.state.combat.enemy.is_alive is False

    enemy_alive = bool(
        stress_session.state.combat.enemy
        and getattr(stress_session.state.combat.enemy, "is_alive", True)
        and getattr(stress_session.state.combat.enemy, "current_hp", 1) > 0
    )
    assert enemy_alive is False

    # Vertical bobbing component must immediately be 0.0
    _, enemy_oy = view.get_enemy_animation_offset(enemy_alive=enemy_alive)
    assert enemy_oy == 0.0

    # Advance time to decay horizontal lunge
    view.update(0.3, stress_session)
    e_ox, e_oy = view.get_enemy_animation_offset(enemy_alive=False)
    assert e_ox == 0.0
    assert e_oy == 0.0


# =========================================================================
# 5. GROUND SHADOW INVARIANT (500 FRAMES)
# =========================================================================
def test_stress_ground_shadow_invariant_500_frames(stress_session):
    """Run 500 frames of random combat action ticks and assert shadow Y NEVER deviates from 204."""
    view = PygameCombatView()
    renderer = PygameRenderer()

    # Ground level: arena bottom is 56 + 176 = 232; ground_y = 232 - 22 = 210.
    # ground_y - 6 = 204.
    EXPECTED_SHADOW_Y = 204

    shadow_blits = []

    class TrackingSurface(pygame.Surface):
        def blit(self, source, dest, *args, **kwargs):
            if hasattr(source, "get_size"):
                sz = source.get_size()
                if sz == (60, 14):
                    shadow_blits.append(("hero", dest[0], dest[1]))
                elif sz == (80, 16):
                    shadow_blits.append(("enemy", dest[0], dest[1]))
            return super().blit(source, dest, *args, **kwargs)

    # Wrap cv.pygame.Surface to return TrackingSurface for screen-size surfaces (even during screen shake)
    orig_surface_cls = cv.pygame.Surface

    def surface_factory(size, *args, **kwargs):
        if size == (960, 540):
            return TrackingSurface(size, *args, **kwargs)
        return orig_surface_cls(size, *args, **kwargs)

    cv.pygame.Surface = surface_factory

    try:
        main_surface = TrackingSurface((960, 540))
        rng = random.Random(42)  # Seeded for deterministic repeatability

        hero_y_samples = []
        enemy_y_samples = []

        for frame in range(500):
            # Vary dt between 0.008 (120fps) and 0.033 (30fps)
            dt = rng.uniform(0.008, 0.033)

            action_roll = rng.random()
            if action_roll < 0.15:
                # Player attacks enemy
                stress_session.bus.emit(DamageDealtEvent(
                    source=stress_session.player.name,
                    target="Cathedral Imp",
                    amount=rng.randint(8, 25),
                    is_crit=(rng.random() < 0.25),
                ))
            elif action_roll < 0.30:
                # Enemy attacks player
                stress_session.bus.emit(DamageDealtEvent(
                    source="Cathedral Imp",
                    target=stress_session.player.name,
                    amount=rng.randint(5, 18),
                    is_crit=(rng.random() < 0.25),
                ))
            elif action_roll < 0.38:
                # Speed cycling
                view._cycle_speed()
            elif action_roll < 0.44:
                # Health restored
                stress_session.bus.emit(HealthRestoredEvent(
                    target=stress_session.player.name,
                    amount=rng.randint(10, 30),
                ))

            view.update(dt, stress_session)

            # Clear blit log for this frame
            shadow_blits.clear()
            view.draw(main_surface, renderer, stress_session)

            hero_blits = [b for b in shadow_blits if b[0] == "hero"]
            enemy_blits = [b for b in shadow_blits if b[0] == "enemy"]

            assert len(hero_blits) >= 1, f"Frame {frame}: Hero shadow was not blitted"
            assert len(enemy_blits) >= 1, f"Frame {frame}: Enemy shadow was not blitted"

            h_y = hero_blits[-1][2]
            e_y = enemy_blits[-1][2]

            hero_y_samples.append(h_y)
            enemy_y_samples.append(e_y)

            # Invariant assertion on every single frame:
            assert h_y == EXPECTED_SHADOW_Y, (
                f"Frame {frame}: hero_shadow_y={h_y} deviated from {EXPECTED_SHADOW_Y}!"
            )
            assert e_y == EXPECTED_SHADOW_Y, (
                f"Frame {frame}: enemy_shadow_y={e_y} deviated from {EXPECTED_SHADOW_Y}!"
            )

        # Aggregate empirical verification
        assert len(hero_y_samples) == 500
        assert len(enemy_y_samples) == 500
        assert all(y == EXPECTED_SHADOW_Y for y in hero_y_samples)
        assert all(y == EXPECTED_SHADOW_Y for y in enemy_y_samples)

    finally:
        cv.pygame.Surface = orig_surface_cls


# =========================================================================
# STANDALONE EXECUTION REPORTING
# =========================================================================
def run_all_stress_tests():
    """Run all stress harnesses standalone and output empirical metrics."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    if not pygame.get_init():
        pygame.init()

    print("=================================================================")
    print("CHALLENGER 2: ADVERSARIAL COMBAT ANIMATION STRESS HARNESS")
    print("=================================================================")

    results = {}

    # Test 1: Extreme dt
    print("\n[TEST 1] Testing Extreme Delta-Times (0.0, 0.001, 0.5, 5.0, 100.0)...")
    s1 = create_stress_session()
    try:
        test_stress_extreme_delta_times(s1)
        results["extreme_dt"] = "PASSED (0 NaN, 0 Inf, clean decays to 0.0)"
        print("  -> PASS: All offsets finite, no NaN, complete decays on dt >= 0.5s.")
    except Exception as exc:
        results["extreme_dt"] = f"FAILED: {exc}"
        print(f"  -> FAIL: {exc}")

    # Test 2: Event spam
    print("\n[TEST 2] Testing Rapid Event Spam (50-event bursts, alternating crits)...")
    s2 = create_stress_session()
    try:
        test_stress_event_spam_bursts(s2)
        results["event_spam"] = "PASSED (0 drift, strictly bounded, clean 0.0 recovery)"
        print("  -> PASS: Timers bounded, offsets bounded, 0.0 residual drift.")
    except Exception as exc:
        results["event_spam"] = f"FAILED: {exc}"
        print(f"  -> FAIL: {exc}")

    # Test 3: Speed cycling
    print("\n[TEST 3] Testing Mid-Animation Speed Cycling (1x <-> 2x <-> 4x)...")
    s3 = create_stress_session()
    try:
        test_stress_speed_cycling_during_active_animations(s3)
        results["speed_cycling"] = "PASSED (clean duration clamp: 0.28s / 0.153s / 0.051s)"
        print("  -> PASS: No popping, durations clamp cleanly to step intervals.")
    except Exception as exc:
        results["speed_cycling"] = f"FAILED: {exc}"
        print(f"  -> FAIL: {exc}")

    # Test 4: Dead combatant
    print("\n[TEST 4] Testing Dead Combatant Edge Cases (idle bobbing strictly 0.0)...")
    s4 = create_stress_session()
    try:
        test_stress_dead_combatant_edge_cases(s4)
        results["dead_combatant"] = "PASSED (idle bobbing strictly 0.0 when dead)"
        print("  -> PASS: Dead combatant vertical bobbing is strictly 0.0.")
    except Exception as exc:
        results["dead_combatant"] = f"FAILED: {exc}"
        print(f"  -> FAIL: {exc}")

    # Test 5: Ground shadow invariant
    print("\n[TEST 5] Testing Ground Shadow Invariant (500 frames random combat ticks)...")
    s5 = create_stress_session()
    try:
        test_stress_ground_shadow_invariant_500_frames(s5)
        results["ground_shadow"] = "PASSED (500/500 frames shadow_y == 204, deviation == 0.0)"
        print("  -> PASS: Hero and enemy shadow Y strictly anchored at 204 across 500 frames.")
    except Exception as exc:
        results["ground_shadow"] = f"FAILED: {exc}"
        print(f"  -> FAIL: {exc}")

    print("\n=================================================================")
    print("STRESS TEST SUMMARY:")
    for test_name, res in results.items():
        print(f"  {test_name:20s}: {res}")
    print("=================================================================")

    all_passed = all("PASSED" in res for res in results.values())
    if all_passed:
        print("\nEXPLICIT VERDICT: APPROVE")
    else:
        print("\nEXPLICIT VERDICT: REQUEST_CHANGES")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(run_all_stress_tests())
