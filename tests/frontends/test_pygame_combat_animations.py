"""Automated test suite for Phase 1 procedural JRPG combat animations in PygameCombatView."""

from __future__ import annotations

import math
import os
import pytest
import pygame

from src.core.events import DamageDealtEvent
from src.core.game_state import GameMode
from src.core.session import GameSession
from src.entities.actor import Stats
from src.entities.enemy import Enemy, EnemyTier
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.combat_view import CombatantAnimationState, PygameCombatView
from src.systems.combat import CombatSystem


@pytest.fixture(scope="module", autouse=True)
def setup_headless_sdl():
    """Ensure headless SDL environment for testing."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    if not pygame.get_init():
        pygame.init()
    yield


@pytest.fixture
def combat_session():
    """Create a test session initialized into active combat."""
    session = GameSession()
    session.start_new_game(class_id="warrior")
    enemy = Enemy(
        name="Cathedral Imp",
        stats=Stats(max_hp=50, attack=8, defense=2, speed=10, crit_chance=0.05),
        tier=EnemyTier.COMMON,
        floor_level=1,
        exp_reward=15,
        gold_reward=8,
    )
    session.state.combat = CombatSystem(session.player, enemy)
    session.switch_mode(GameMode.COMBAT)
    return session


def test_combatant_animation_state_defaults_and_lunge_math():
    """Verify CombatantAnimationState lunge advancement and sine-arc trajectory."""
    hero_state = CombatantAnimationState(is_hero=True)
    assert hero_state.get_lunge_offset_x() == 0.0

    # Trigger lunge for hero
    hero_state.trigger_lunge(max_duration=0.28, distance=40.0)
    assert hero_state.lunge_timer == 0.28
    assert hero_state.lunge_duration == 0.28

    # At start (progress = 0): displacement is 0.0
    assert hero_state.get_lunge_offset_x() == pytest.approx(0.0, abs=1e-5)

    # At midpoint (progress = 0.5): displacement peaks at +distance (rightward)
    hero_state.update(0.14)
    assert hero_state.lunge_timer == pytest.approx(0.14, abs=1e-5)
    assert hero_state.get_lunge_offset_x() == pytest.approx(40.0, abs=1e-2)

    # At end (progress = 1.0): displacement returns to 0.0
    hero_state.update(0.14)
    assert hero_state.lunge_timer == 0.0
    assert hero_state.get_lunge_offset_x() == 0.0

    # Further updates stay at 0.0
    hero_state.update(0.1)
    assert hero_state.get_lunge_offset_x() == 0.0

    # Symmetrical check for enemy (-X displacement, leftward toward hero)
    enemy_state = CombatantAnimationState(is_hero=False)
    enemy_state.trigger_lunge(max_duration=0.28, distance=40.0)
    enemy_state.update(0.14)
    assert enemy_state.get_lunge_offset_x() == pytest.approx(-40.0, abs=1e-2)
    enemy_state.update(0.14)
    assert enemy_state.get_lunge_offset_x() == 0.0


def test_combatant_animation_state_recoil_and_crit_amplification():
    """Verify recoil knockback, high-frequency wobble, flinch, and 1.5x crit scaling."""
    hero_state = CombatantAnimationState(is_hero=True)
    assert hero_state.get_recoil_offsets() == (0.0, 0.0)

    # Non-crit recoil for hero
    hero_state.trigger_recoil(is_crit=False, max_duration=0.24)
    assert hero_state.recoil_timer == 0.24
    assert not hero_state.recoil_is_crit

    # Initial frame (progress=0, decay=1.0): knockback = -16.0, wobble = 0.0, flinch = 0.0
    rx, ry = hero_state.get_recoil_offsets()
    assert rx == pytest.approx(-16.0, abs=1e-4)
    assert ry == pytest.approx(0.0, abs=1e-4)

    # Midpoint frame: flinch is upward (negative Y), knockback decays, wobble oscillates
    hero_state.update(0.12)
    rx_mid, ry_mid = hero_state.get_recoil_offsets()
    assert rx_mid < 0.0  # Hero pushed backward to the left
    assert ry_mid <= 0.0  # Upward flinch impact

    # Expired recoil returns to (0, 0)
    hero_state.update(0.12)
    assert hero_state.get_recoil_offsets() == (0.0, 0.0)

    # Critical hit recoil (1.5x amplification)
    hero_crit = CombatantAnimationState(is_hero=True)
    hero_crit.trigger_recoil(is_crit=True, max_duration=0.28)
    assert hero_crit.recoil_is_crit
    rx_crit, _ = hero_crit.get_recoil_offsets()
    assert rx_crit == pytest.approx(-24.0, abs=1e-4)  # -16.0 * 1.5 = -24.0

    # Enemy recoil pushes backward to the right (+X)
    enemy_state = CombatantAnimationState(is_hero=False)
    enemy_state.trigger_recoil(is_crit=False, max_duration=0.24)
    e_rx, _ = enemy_state.get_recoil_offsets()
    assert e_rx == pytest.approx(16.0, abs=1e-4)

    enemy_crit = CombatantAnimationState(is_hero=False)
    enemy_crit.trigger_recoil(is_crit=True, max_duration=0.28)
    e_rx_crit, _ = enemy_crit.get_recoil_offsets()
    assert e_rx_crit == pytest.approx(24.0, abs=1e-4)


def test_duration_clamping_for_game_speeds():
    """Verify animation durations clamp cleanly across 1x, 2x, and 4x combat speeds."""
    state = CombatantAnimationState(is_hero=True)

    # 1x speed (step_interval = 0.40): cap is min(0.28, 0.40 * 0.85 = 0.34) -> 0.28
    cap_1x = min(0.28, 0.40 * 0.85)
    state.trigger_lunge(max_duration=cap_1x)
    assert state.lunge_duration == pytest.approx(0.28, abs=1e-4)

    # 2x speed (step_interval = 0.18): cap is min(0.28, 0.18 * 0.85 = 0.153) -> 0.153
    cap_2x = min(0.28, 0.18 * 0.85)
    state.trigger_lunge(max_duration=cap_2x)
    assert state.lunge_duration == pytest.approx(0.153, abs=1e-4)

    # 4x speed (step_interval = 0.06): cap is min(0.28, 0.06 * 0.85 = 0.051) -> 0.051
    cap_4x = min(0.28, 0.06 * 0.85)
    state.trigger_lunge(max_duration=cap_4x)
    assert state.lunge_duration == pytest.approx(0.051, abs=1e-4)

    # In 4x speed, updating by 0.052s fully completes the animation
    state.update(0.052)
    assert state.lunge_timer == 0.0
    assert state.get_lunge_offset_x() == 0.0


def test_idle_bobbing_oscillation_and_phase_difference(combat_session):
    """Verify idle breathing vertical oscillation, amplitude bounds, and phase inversion."""
    view = PygameCombatView()

    # Initial state (idle_timer = 0.0)
    h_ox, h_oy = view.get_hero_animation_offset()
    assert h_ox == 0.0
    assert h_oy == pytest.approx(0.0, abs=1e-4)

    # Advance time by 0.5s
    view.update(0.5, combat_session)
    assert view.idle_timer == pytest.approx(0.5, abs=1e-4)

    h_ox, h_oy = view.get_hero_animation_offset()
    e_ox, e_oy = view.get_enemy_animation_offset(enemy_alive=True)

    # Amplitude bounds [-2.5, 2.5]
    assert -2.5 <= h_oy <= 2.5
    assert -2.5 <= e_oy <= 2.5

    # Hero and enemy idle bobbing must be out of phase (opposite vertical movement)
    expected_hero_y = math.sin(0.5 * 3.0) * 2.5
    expected_enemy_y = math.sin(0.5 * 3.0 + math.pi) * 2.5
    assert h_oy == pytest.approx(expected_hero_y, abs=1e-4)
    assert e_oy == pytest.approx(expected_enemy_y, abs=1e-4)
    assert h_oy * e_oy < 0.0  # One is positive, one is negative

    # When enemy is dead, enemy idle bobbing drops strictly to 0.0
    combat_session.state.combat.enemy.current_hp = 0
    _, dead_enemy_oy = view.get_enemy_animation_offset(enemy_alive=False)
    assert dead_enemy_oy == 0.0


def test_hero_attack_lunge_advancement_and_recovery(combat_session):
    """Verify hero lunges right (+X) on attack and enemy recoils right (+X)."""
    view = PygameCombatView()

    # Enqueue a player attack event
    combat_session.bus.emit(DamageDealtEvent(
        source=combat_session.player.name,
        target="Cathedral Imp",
        amount=14,
        is_crit=False,
    ))

    # Single frame update processes event
    view.update(0.016, combat_session)

    # Hero lunge is active and moving forward (+X)
    assert view.player_anim.lunge_timer > 0.0
    hero_ox, _ = view.get_hero_animation_offset()
    assert hero_ox > 0.0  # Lunging rightward toward enemy

    # Enemy recoil is active and knocked backward (+X, away from hero)
    assert view.enemy_anim.recoil_timer > 0.0
    assert view.enemy_flash == 3
    enemy_ox, _ = view.get_enemy_animation_offset(enemy_alive=True)
    assert enemy_ox > 0.0

    # Advance time beyond animation duration
    view.update(0.35, combat_session)
    assert view.player_anim.lunge_timer == 0.0
    assert view.enemy_anim.recoil_timer == 0.0
    assert view.player_anim.get_lunge_offset_x() == 0.0
    assert view.enemy_anim.get_recoil_offsets() == (0.0, 0.0)


def test_enemy_attack_lunge_and_hero_recoil(combat_session):
    """Verify enemy lunges left (-X) on attack and hero recoils left (-X)."""
    view = PygameCombatView()

    # Enqueue enemy attack event
    combat_session.bus.emit(DamageDealtEvent(
        source="Cathedral Imp",
        target=combat_session.player.name,
        amount=9,
        is_crit=False,
    ))

    # Single frame update
    view.update(0.016, combat_session)

    # Enemy lunge is active and moving forward (-X, leftward toward hero)
    assert view.enemy_anim.lunge_timer > 0.0
    enemy_lunge_x = view.enemy_anim.get_lunge_offset_x()
    assert enemy_lunge_x < 0.0

    # Hero recoil is active and knocked backward (-X, leftward away from enemy)
    assert view.player_anim.recoil_timer > 0.0
    assert view.player_flash == 3
    hero_recoil_x, _ = view.player_anim.get_recoil_offsets()
    assert hero_recoil_x < 0.0

    # Advance past duration
    view.update(0.35, combat_session)
    assert view.enemy_anim.lunge_timer == 0.0
    assert view.player_anim.recoil_timer == 0.0


def test_critical_hit_triggers_screen_shake_and_amplified_recoil(combat_session):
    """Verify critical hits trigger screen shake and 1.5x amplified recoil."""
    view = PygameCombatView()

    # Critical hit against player
    combat_session.bus.emit(DamageDealtEvent(
        source="Cathedral Imp",
        target=combat_session.player.name,
        amount=22,
        is_crit=True,
    ))

    view.update(0.016, combat_session)
    assert view.shake_frames == 5
    assert view.player_anim.recoil_is_crit is True

    # Initial crit recoil magnitude has 1.5x multiplier on knockback and wobble
    rx, _ = view.player_anim.get_recoil_offsets()
    assert rx < -16.0  # Significantly amplified beyond normal initial knockback of ~-11.8


def test_non_damaging_action_triggers_lunge(combat_session):
    """Verify queued ability consumption and non-damaging enemy actions trigger lunges."""
    view = PygameCombatView()
    combat = combat_session.state.combat

    # Set player gauge ready and queue an active ability
    active_skills = combat_session.player.abilities.active
    assert len(active_skills) > 0
    combat.queued_ability = active_skills[0]
    combat.player_gauge = 100.0
    combat.enemy_gauge = 0.0

    # Advance tick - consumes queued ability and triggers player lunge
    view._tick_combat(combat_session)
    assert view.player_anim.lunge_timer > 0.0

    # Reset animation timers and set enemy gauge ready
    view.player_anim.lunge_timer = 0.0
    view.enemy_anim.lunge_timer = 0.0
    combat.player_gauge = 0.0
    combat.enemy_gauge = 100.0

    view._tick_combat(combat_session)
    assert view.enemy_anim.lunge_timer > 0.0


def test_composite_rendering_headless_stability(combat_session):
    """Verify headless rendering with composite animations executes stably with grounded shadows."""
    view = PygameCombatView()
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    # Trigger multiple concurrent effects
    view.idle_timer = 1.35
    view.player_anim.trigger_lunge(distance=40.0)
    view.enemy_anim.trigger_recoil(is_crit=True)
    view.player_flash = 3
    view.enemy_flash = 3
    view.shake_frames = 4

    # Render across 30 consecutive frames
    for _ in range(30):
        view.update(0.016, combat_session)
        view.draw(surface, renderer, combat_session)

        # Offsets must be real numbers, not NaN or infinite
        h_ox, h_oy = view.get_hero_animation_offset()
        e_ox, e_oy = view.get_enemy_animation_offset(enemy_alive=True)
        assert math.isfinite(h_ox)
        assert math.isfinite(h_oy)
        assert math.isfinite(e_ox)
        assert math.isfinite(e_oy)


def test_grounded_shadows_remain_on_ground_plane(combat_session):
    """Verify that combatant shadows stay strictly anchored at ground_y - 6 across frames."""
    view = PygameCombatView()
    renderer = PygameRenderer()

    class TrackingSurface(pygame.Surface):
        def blit(self, source, dest, *args, **kwargs):
            if not hasattr(self, "blitted_coords"):
                self.blitted_coords = []
            self.blitted_coords.append((dest[0], dest[1]))
            return super().blit(source, dest, *args, **kwargs)

    tracking_surface = TrackingSurface((960, 540))

    # Trigger idle bobbing + lunging
    view.idle_timer = 2.0
    view.player_anim.trigger_lunge(distance=40.0)
    view.player_anim.update(0.14)  # At max lunge

    view.draw(tracking_surface, renderer, combat_session)

    # Arena ground_y = 56 + 176 - 22 = 210. Expected shadow Y = 210 - 6 = 204.
    expected_ground_y = (view.arena_rect.bottom - 22) - 6
    assert expected_ground_y == 204

    # Check shadow coordinates: hero shadow (center_x - 30 + off_x, ground_y - 6)
    shadow_positions = [pos for pos in tracking_surface.blitted_coords if pos[1] == expected_ground_y]
    assert len(shadow_positions) >= 2  # Hero and Enemy shadows
    # Verify hero shadow moved horizontally with lunge (+40px)
    hero_shadow_x = shadow_positions[0][0]
    assert hero_shadow_x == 280 - 30 + 40  # 290


def test_speed_cycling_and_lunge_bounds(combat_session):
    """Verify cycling speeds updates step_interval and bounds lunge duration."""
    view = PygameCombatView()
    assert view.step_interval == 0.40

    # 1x -> 2x
    view._cycle_speed()
    assert view.step_interval == 0.18
    dur_2x = min(0.28, view.step_interval * 0.85)
    view.player_anim.trigger_lunge(max_duration=dur_2x)
    assert view.player_anim.lunge_duration == pytest.approx(0.153, abs=1e-4)

    # 2x -> 4x
    view._cycle_speed()
    assert view.step_interval == 0.06
    dur_4x = min(0.28, view.step_interval * 0.85)
    view.player_anim.trigger_lunge(max_duration=dur_4x)
    assert view.player_anim.lunge_duration == pytest.approx(0.051, abs=1e-4)

    # 4x -> 1x
    view._cycle_speed()
    assert view.step_interval == 0.40


def test_out_of_combat_and_victory_animation_stability(combat_session):
    """Verify animation updates survive combat conclusion and victory transitions."""
    view = PygameCombatView()
    combat = combat_session.state.combat

    # Trigger victory
    combat.enemy.current_hp = 0
    view.update(0.1, combat_session)
    assert view.victory_active is True

    # Idle timer and animation state continue cleanly
    assert view.idle_timer == pytest.approx(0.1, abs=1e-4)
    surface = pygame.Surface((960, 540))
    renderer = PygameRenderer()
    view.draw(surface, renderer, combat_session)

