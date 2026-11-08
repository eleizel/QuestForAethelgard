"""Adversarial stress and robustness test suite for PygameApp view mode transitions and audio playback.

Milestone 3 Challenger 1 Suite:
1. 100+ rapid randomized mode transitions across all 15 operational GameMode screens.
2. Deeply nested modal transitions (e.g. MAP -> INVENTORY -> CHARACTER -> LOOT -> MAP) ensuring track preservation.
3. Normal combat (COMMON, UNCOMMON) vs elite/boss combat (ELITE, BOSS) transitions and post-combat resolution.
4. Extreme tick values (dt = 0.0, dt = 10.0, dt = -0.01, dt = inf, dt = nan) and rapid stop/start/mute cycles.
5. Multithreaded concurrency stress, zero unhandled exceptions, and zero memory/resource leaks.
"""

from __future__ import annotations

import gc
import math
import os
import random
import sys
import threading
import time
from typing import Final
from unittest.mock import patch
import pytest
import pygame

from src.core.game_state import GameMode
from src.core.persistence import MemoryStorageBackend
from src.core.session import GameSession
from src.entities.actor import Stats
from src.entities.enemy import Enemy, EnemyTier
from src.frontends.pygame_ce.app import PygameApp
from src.frontends.pygame_ce.music_engine import (
    CONTEXT_TRACKS,
    AudioSettingsManager,
    DynamicMusicEngine,
    MusicContext,
    PlaybackState,
    resolve_music_context,
)
from src.systems.combat import CombatResult, CombatSystem


@pytest.fixture(autouse=True)
def ensure_headless_env():
    """Ensure headless SDL dummy drivers and clean mixer state for each test."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    if not pygame.get_init():
        pygame.init()
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            pass
    yield
    if pygame.mixer.get_init():
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass


@pytest.fixture
def memory_backend() -> MemoryStorageBackend:
    """Isolated memory storage backend."""
    return MemoryStorageBackend()


@pytest.fixture
def audio_settings(memory_backend: MemoryStorageBackend) -> AudioSettingsManager:
    """Isolated audio settings manager."""
    return AudioSettingsManager(backend=memory_backend)


@pytest.fixture
def music_engine(audio_settings: AudioSettingsManager) -> DynamicMusicEngine:
    """Isolated DynamicMusicEngine instance."""
    eng = DynamicMusicEngine(settings_manager=audio_settings)
    yield eng
    eng.stop()


@pytest.fixture
def test_app(music_engine: DynamicMusicEngine) -> PygameApp:
    """Headless PygameApp instance initialized with fresh GameSession and music engine."""
    app = PygameApp(headless=True, session=GameSession(), music_engine=music_engine)
    app.session.start_new_game()
    return app


# =============================================================================
# 1. 100+ RAPID RANDOMIZED MODE TRANSITIONS ACROSS ALL 15 MODES
# =============================================================================
class TestRapidRandomModeTransitions:
    """Stress tests verifying stability under rapid randomized transitions across all 15 modes."""

    def test_150_rapid_randomized_mode_transitions_across_all_15_modes(
        self, test_app: PygameApp
    ):
        """Execute 150 randomized mode transitions across all 15 GameModes under varying dt values.

        Verifies:
        - All 15 GameModes transition cleanly without unhandled exceptions.
        - app.update(dt) and app.draw() execute smoothly for every state.
        - Mapped modes establish correct MusicContext (WELCOME, MAP, COMBAT, BOSS).
        - Unmapped/modal modes retain the preceding MusicContext without corruption.
        - Active track is always a non-empty string and valid candidate.
        """
        all_modes = list(GameMode)
        assert len(all_modes) == 15, f"Expected 15 game modes, found {len(all_modes)}"

        rng = random.Random(1337)
        previous_context = test_app.music_engine.get_current_context()

        # Track mode coverage to ensure all 15 modes are exercised repeatedly
        mode_counts = {m: 0 for m in all_modes}
        dt_candidates = [0.001, 0.016, 0.033, 0.05, 0.0]

        for step in range(150):
            target_mode = rng.choice(all_modes)
            mode_counts[target_mode] += 1

            if test_app.session.current_mode in (
                GameMode.GAME_OVER,
                GameMode.VICTORY,
            ) and target_mode not in (
                test_app.session.current_mode,
                GameMode.WELCOME,
                GameMode.CREDITS,
            ):
                test_app.session.reset_to_title()
                test_app.update(0.0)
                previous_context = test_app.music_engine.get_current_context()

            # When entering COMBAT, test varied enemy tiers and fallback states
            if target_mode == GameMode.COMBAT:
                tier_choice = rng.choice(["common", "uncommon", "elite", "boss", "none"])
                if tier_choice == "none":
                    test_app.session.state.combat = None
                else:
                    tier_map = {
                        "common": EnemyTier.COMMON,
                        "uncommon": EnemyTier.UNCOMMON,
                        "elite": EnemyTier.ELITE,
                        "boss": EnemyTier.BOSS,
                    }
                    tier = tier_map[tier_choice]
                    enemy = Enemy(
                        name=f"Enemy_{step}",
                        tier=tier,
                        stats=Stats(max_hp=50, attack=10, defense=5, speed=10),
                        floor_level=1,
                        exp_reward=20,
                        gold_reward=10,
                    )
                    test_app.session.state.combat = CombatSystem(
                        player=test_app.session.player, enemy=enemy
                    )

            test_app.session.switch_mode(target_mode)
            dt = rng.choice(dt_candidates)

            # Advance engine and render frame
            test_app.update(dt)
            test_app.draw()

            current_ctx = test_app.music_engine.get_current_context()
            current_track = test_app.music_engine.get_current_track()

            assert current_ctx is not None, f"Step {step}: MusicContext dropped to None in mode {target_mode}"
            assert current_track is not None and len(current_track) > 0, (
                f"Step {step}: Track dropped to None in mode {target_mode}"
            )
            assert current_track in CONTEXT_TRACKS[current_ctx], (
                f"Step {step}: Track '{current_track}' not in valid tracks for context {current_ctx}"
            )

            # Context validation rules
            if target_mode in (
                GameMode.WELCOME,
                GameMode.CLASS_SELECT,
                GameMode.BIOME_SELECT,
                GameMode.CREDITS,
            ):
                assert current_ctx == MusicContext.WELCOME
            elif target_mode == GameMode.MAP:
                assert current_ctx == MusicContext.MAP
            elif target_mode == GameMode.COMBAT:
                combat = test_app.session.combat
                if combat and combat.enemy and combat.enemy.tier in (EnemyTier.ELITE, EnemyTier.BOSS):
                    assert current_ctx == MusicContext.BOSS
                else:
                    assert current_ctx == MusicContext.COMBAT
            else:
                # Modal/unmapped mode: must strictly preserve the previous context
                assert current_ctx == previous_context, (
                    f"Step {step}: Modal mode {target_mode} mutated context from {previous_context} to {current_ctx}"
                )

            previous_context = current_ctx

        # Confirm all 15 modes were tested
        for m, count in mode_counts.items():
            assert count >= 3, f"Mode {m} was only exercised {count} times (minimum 3 required)"

    def test_rapid_thrashing_between_polarized_contexts(self, test_app: PygameApp):
        """Rapidly toggle 100 times between WELCOME, MAP, COMBAT, and BOSS contexts.

        Verifies that rapid context switches update immediately without stream deadlock.
        """
        for i in range(25):
            # 1. WELCOME
            test_app.session.switch_mode(GameMode.WELCOME)
            test_app.update(0.016)
            assert test_app.music_engine.get_current_context() == MusicContext.WELCOME
            assert test_app.music_engine.get_current_track() in ("welcome_01", "welcome_02")

            # 2. MAP
            test_app.session.switch_mode(GameMode.MAP)
            test_app.update(0.016)
            assert test_app.music_engine.get_current_context() == MusicContext.MAP
            assert test_app.music_engine.get_current_track() in ("exploration_01", "exploration_02")

            # 3. COMBAT (COMMON)
            c_enemy = Enemy(
                name="Snoop",
                tier=EnemyTier.COMMON,
                stats=Stats(max_hp=20, attack=5, defense=2, speed=10),
                floor_level=1,
                exp_reward=10,
                gold_reward=5,
            )
            test_app.session.state.combat = CombatSystem(
                player=test_app.session.player, enemy=c_enemy
            )
            test_app.session.switch_mode(GameMode.COMBAT)
            test_app.update(0.016)
            assert test_app.music_engine.get_current_context() == MusicContext.COMBAT
            assert test_app.music_engine.get_current_track() in ("combat_01", "combat_02")

            # 4. BOSS (BOSS)
            b_enemy = Enemy(
                name="Dragon",
                tier=EnemyTier.BOSS,
                stats=Stats(max_hp=200, attack=25, defense=15, speed=10),
                floor_level=1,
                exp_reward=100,
                gold_reward=50,
            )
            test_app.session.state.combat = CombatSystem(
                player=test_app.session.player, enemy=b_enemy
            )
            test_app.session.switch_mode(GameMode.COMBAT)
            test_app.update(0.016)
            assert test_app.music_engine.get_current_context() == MusicContext.BOSS
            assert test_app.music_engine.get_current_track() in ("boss_01", "boss_02")

    def test_mode_transitions_under_high_tick_rate_simulation(self, test_app: PygameApp):
        """Simulate high frame rates (120 FPS and 240 FPS) with rapid transitions."""
        # 120 FPS: dt = ~0.00833
        dt_120 = 1.0 / 120.0
        # 240 FPS: dt = ~0.00416
        dt_240 = 1.0 / 240.0

        for _ in range(30):
            test_app.session.switch_mode(GameMode.MAP)
            test_app.update(dt_120)
            assert test_app.music_engine.get_current_context() == MusicContext.MAP

            test_app.session.switch_mode(GameMode.INVENTORY)
            test_app.update(dt_240)
            assert test_app.music_engine.get_current_context() == MusicContext.MAP

            test_app.session.switch_mode(GameMode.WELCOME)
            test_app.update(dt_120)
            assert test_app.music_engine.get_current_context() == MusicContext.WELCOME


# =============================================================================
# 2. DEEPLY NESTED MODAL TRANSITIONS & TRACK PRESERVATION
# =============================================================================
class TestDeeplyNestedModalTransitions:
    """Tests verifying track preservation across complex and deeply nested modal view stacks."""

    def test_explicit_nested_modal_chain_preserves_track(self, test_app: PygameApp):
        """Verify explicit prompt requirement: MAP -> INVENTORY -> CHARACTER -> LOOT -> MAP.

        The active exploration track selected on entering MAP must remain exactly identical
        across all intermediate modal views and upon returning to MAP.
        """
        # Step 1: Establish MAP context
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        initial_context = test_app.music_engine.get_current_context()
        initial_track = test_app.music_engine.get_current_track()
        assert initial_context == MusicContext.MAP
        assert initial_track in ("exploration_01", "exploration_02")

        # Step 2: Open INVENTORY
        test_app.session.switch_mode(GameMode.INVENTORY)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.MAP
        assert test_app.music_engine.get_current_track() == initial_track

        # Step 3: Open CHARACTER
        test_app.session.switch_mode(GameMode.CHARACTER)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.MAP
        assert test_app.music_engine.get_current_track() == initial_track

        # Step 4: Open LOOT
        test_app.session.switch_mode(GameMode.LOOT)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.MAP
        assert test_app.music_engine.get_current_track() == initial_track

        # Step 5: Return to MAP
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.MAP
        assert test_app.music_engine.get_current_track() == initial_track

    def test_deeply_nested_combat_modal_chain_preserves_combat_track(self, test_app: PygameApp):
        """Verify modal chain in combat: COMBAT -> INVENTORY -> CHARACTER -> LOOT -> SHOP -> COMBAT."""
        c_enemy = Enemy(
            name="Goblin",
            tier=EnemyTier.COMMON,
            stats=Stats(max_hp=30, attack=6, defense=2, speed=10),
            floor_level=1,
            exp_reward=15,
            gold_reward=5,
        )
        test_app.session.state.combat = CombatSystem(
            player=test_app.session.player, enemy=c_enemy
        )
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)

        combat_ctx = test_app.music_engine.get_current_context()
        combat_track = test_app.music_engine.get_current_track()
        assert combat_ctx == MusicContext.COMBAT

        chain = [
            GameMode.INVENTORY,
            GameMode.CHARACTER,
            GameMode.LOOT,
            GameMode.SHOP,
            GameMode.ABILITY_CHOICE,
            GameMode.PROMOTION,
            GameMode.EVENTS,
            GameMode.COMBAT,
        ]

        for target in chain:
            test_app.session.switch_mode(target)
            test_app.update(0.016)
            assert test_app.music_engine.get_current_context() == MusicContext.COMBAT
            assert test_app.music_engine.get_current_track() == combat_track

    def test_deeply_nested_boss_modal_chain_preserves_boss_track(self, test_app: PygameApp):
        """Verify modal chain in boss combat: COMBAT(BOSS) -> INVENTORY -> CHARACTER -> PROMOTION -> COMBAT."""
        b_enemy = Enemy(
            name="Overlord",
            tier=EnemyTier.BOSS,
            stats=Stats(max_hp=250, attack=30, defense=15, speed=10),
            floor_level=1,
            exp_reward=150,
            gold_reward=75,
        )
        test_app.session.state.combat = CombatSystem(
            player=test_app.session.player, enemy=b_enemy
        )
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)

        boss_ctx = test_app.music_engine.get_current_context()
        boss_track = test_app.music_engine.get_current_track()
        assert boss_ctx == MusicContext.BOSS

        chain = [
            GameMode.INVENTORY,
            GameMode.CHARACTER,
            GameMode.PROMOTION,
            GameMode.EVENTS,
            GameMode.COMBAT,
        ]

        for target in chain:
            test_app.session.switch_mode(target)
            test_app.update(0.016)
            assert test_app.music_engine.get_current_context() == MusicContext.BOSS
            assert test_app.music_engine.get_current_track() == boss_track

    def test_overlay_stack_push_pop_preserves_track(self, test_app: PygameApp):
        """Verify stack push/pop via toggle_inventory and toggle_character preserves music."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        base_track = test_app.music_engine.get_current_track()

        # Push Inventory
        test_app.session.toggle_inventory()
        test_app.update(0.016)
        assert test_app.session.current_mode == GameMode.INVENTORY
        assert test_app.music_engine.get_current_track() == base_track

        # Push Character overlay on top
        test_app.session.toggle_character()
        test_app.update(0.016)
        assert test_app.session.current_mode == GameMode.CHARACTER
        assert test_app.music_engine.get_current_track() == base_track

        # Pop Character overlay (returns to Inventory)
        test_app.session.toggle_character()
        test_app.update(0.016)
        assert test_app.session.current_mode == GameMode.INVENTORY
        assert test_app.music_engine.get_current_track() == base_track

        # Pop Inventory overlay (returns to Map)
        test_app.session.toggle_inventory()
        test_app.update(0.016)
        assert test_app.session.current_mode == GameMode.MAP
        assert test_app.music_engine.get_current_track() == base_track

    def test_rapid_modal_thrashing_50_iterations(self, test_app: PygameApp):
        """Rapidly thrash 50 times between MAP and various modals without track reset."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        base_track = test_app.music_engine.get_current_track()

        modals = [
            GameMode.INVENTORY,
            GameMode.CHARACTER,
            GameMode.LOOT,
            GameMode.SHOP,
            GameMode.ABILITY_CHOICE,
            GameMode.PROMOTION,
            GameMode.EVENTS,
        ]

        for i in range(50):
            target_modal = modals[i % len(modals)]
            test_app.session.switch_mode(target_modal)
            test_app.update(0.016)
            assert test_app.music_engine.get_current_context() == MusicContext.MAP
            assert test_app.music_engine.get_current_track() == base_track

            test_app.session.switch_mode(GameMode.MAP)
            test_app.update(0.016)
            assert test_app.music_engine.get_current_context() == MusicContext.MAP
            assert test_app.music_engine.get_current_track() == base_track


# =============================================================================
# 3. NORMAL COMBAT VS ELITE/BOSS COMBAT & POST-COMBAT RESOLUTION
# =============================================================================
class TestCombatTierTransitionsAndResolution:
    """Stress tests verifying combat tier resolution, post-combat flow, and edge cases."""

    @pytest.mark.parametrize("tier", [EnemyTier.COMMON, EnemyTier.UNCOMMON])
    def test_normal_combat_tiers_trigger_combat_context(
        self, test_app: PygameApp, tier: EnemyTier
    ):
        """COMMON and UNCOMMON enemies must resolve strictly to MusicContext.COMBAT."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)

        enemy = Enemy(
            name=f"Minion_{tier.name}",
            tier=tier,
            stats=Stats(max_hp=40, attack=8, defense=3, speed=10),
            floor_level=1,
            exp_reward=20,
            gold_reward=10,
        )
        test_app.session.state.combat = CombatSystem(
            player=test_app.session.player, enemy=enemy
        )
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)

        assert test_app.music_engine.get_current_context() == MusicContext.COMBAT
        assert test_app.music_engine.get_current_track() in ("combat_01", "combat_02")

    @pytest.mark.parametrize("tier", [EnemyTier.ELITE, EnemyTier.BOSS])
    def test_elite_and_boss_tiers_trigger_boss_context(
        self, test_app: PygameApp, tier: EnemyTier
    ):
        """ELITE and BOSS enemies must resolve strictly to MusicContext.BOSS."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)

        enemy = Enemy(
            name=f"Titan_{tier.name}",
            tier=tier,
            stats=Stats(max_hp=150, attack=20, defense=10, speed=10),
            floor_level=1,
            exp_reward=80,
            gold_reward=40,
        )
        test_app.session.state.combat = CombatSystem(
            player=test_app.session.player, enemy=enemy
        )
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)

        assert test_app.music_engine.get_current_context() == MusicContext.BOSS
        assert test_app.music_engine.get_current_track() in ("boss_01", "boss_02")

    def test_full_combat_victory_post_combat_resolution_lifecycle(self, test_app: PygameApp):
        """Execute complete combat victory lifecycle: MAP -> COMBAT -> VICTORY -> LOOT -> MAP.

        Ensures:
        - COMBAT triggers combat music.
        - LOOT retains combat music (no reset or silence).
        - Returning to MAP seamlessly resumes exploration music.
        """
        # 1. MAP Exploration
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.MAP

        # 2. Engage Normal Enemy
        enemy = Enemy(
            name="Skeleton",
            tier=EnemyTier.COMMON,
            stats=Stats(max_hp=25, attack=5, defense=2, speed=10),
            floor_level=1,
            exp_reward=10,
            gold_reward=5,
        )
        test_app.session.state.combat = CombatSystem(
            player=test_app.session.player, enemy=enemy
        )
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.COMBAT
        combat_track = test_app.music_engine.get_current_track()

        # 3. Simulate Battle Victory
        enemy.take_damage(999)
        test_app.session.state.combat.result = CombatResult.PLAYER_VICTORY
        test_app.session.state.combat.completion_delay_ticks = 0
        test_app.session.state.update_combat()

        # Mode transitions to LOOT
        assert test_app.session.current_mode == GameMode.LOOT
        test_app.update(0.016)

        # LOOT retains combat music
        assert test_app.music_engine.get_current_context() == MusicContext.COMBAT
        assert test_app.music_engine.get_current_track() == combat_track

        # 4. Return to Map
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)

        # Map exploration resumes
        assert test_app.music_engine.get_current_context() == MusicContext.MAP
        assert test_app.music_engine.get_current_track() in ("exploration_01", "exploration_02")

    def test_boss_combat_victory_post_combat_resolution_lifecycle(self, test_app: PygameApp):
        """Execute boss combat victory lifecycle: MAP -> BOSS COMBAT -> LOOT -> MAP."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)

        # Engage Boss
        enemy = Enemy(
            name="Ancient Wyrm",
            tier=EnemyTier.BOSS,
            stats=Stats(max_hp=300, attack=30, defense=15, speed=10),
            floor_level=1,
            exp_reward=150,
            gold_reward=75,
        )
        test_app.session.state.combat = CombatSystem(
            player=test_app.session.player, enemy=enemy
        )
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.BOSS
        boss_track = test_app.music_engine.get_current_track()

        # Defeat Boss
        enemy.take_damage(999)
        test_app.session.state.combat.result = CombatResult.PLAYER_VICTORY
        test_app.session.state.combat.completion_delay_ticks = 0
        test_app.session.state.update_combat()

        assert test_app.session.current_mode == GameMode.LOOT
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.BOSS
        assert test_app.music_engine.get_current_track() == boss_track

        # Return to Map
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.MAP

    def test_combat_player_defeat_lifecycle(self, test_app: PygameApp):
        """Execute defeat lifecycle: MAP -> COMBAT -> DEFEAT -> GAME_OVER -> WELCOME."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)

        enemy = Enemy(
            name="Reaper",
            tier=EnemyTier.ELITE,
            stats=Stats(max_hp=100, attack=50, defense=10, speed=10),
            floor_level=1,
            exp_reward=50,
            gold_reward=25,
        )
        test_app.session.state.combat = CombatSystem(
            player=test_app.session.player, enemy=enemy
        )
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.BOSS

        # Player Defeat
        test_app.session.player.current_hp = 0
        test_app.session.state.combat.result = CombatResult.PLAYER_DEFEAT
        test_app.session.state.combat.completion_delay_ticks = 0
        test_app.session.state.update_combat()

        assert test_app.session.current_mode == GameMode.GAME_OVER
        test_app.update(0.016)
        # GAME_OVER is unmapped; retains previous context
        assert test_app.music_engine.get_current_context() == MusicContext.BOSS

        # Reset to title
        test_app.session.reset_to_title()
        test_app.update(0.016)
        assert test_app.session.current_mode == GameMode.WELCOME
        assert test_app.music_engine.get_current_context() == MusicContext.WELCOME

    def test_rapid_alternating_combat_tiers_30_iterations(self, test_app: PygameApp):
        """Rapidly alternate 30 times between normal and boss combat tiers."""
        c_enemy = Enemy(
            name="Goblin",
            tier=EnemyTier.COMMON,
            stats=Stats(max_hp=20, attack=5, defense=2, speed=10),
            floor_level=1,
            exp_reward=10,
            gold_reward=5,
        )
        b_enemy = Enemy(
            name="Lord",
            tier=EnemyTier.BOSS,
            stats=Stats(max_hp=100, attack=20, defense=10, speed=10),
            floor_level=1,
            exp_reward=50,
            gold_reward=25,
        )

        for _ in range(15):
            # Normal
            test_app.session.state.combat = CombatSystem(
                player=test_app.session.player, enemy=c_enemy
            )
            test_app.session.switch_mode(GameMode.COMBAT)
            test_app.update_music_context(force_restart=True)
            test_app.update(0.016)
            assert test_app.music_engine.get_current_context() == MusicContext.COMBAT

            # Boss
            test_app.session.state.combat = CombatSystem(
                player=test_app.session.player, enemy=b_enemy
            )
            test_app.session.switch_mode(GameMode.COMBAT)
            test_app.update_music_context(force_restart=True)
            test_app.update(0.016)
            assert test_app.music_engine.get_current_context() == MusicContext.BOSS

    def test_combat_defensive_fallbacks_no_crashes(self, test_app: PygameApp):
        """Test degenerate combat configurations: None combat, None enemy, None tier."""
        # Case A: combat is None
        test_app.session.state.combat = None
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.COMBAT

        # Case B: combat.enemy is None on an active CombatSystem
        enemy = Enemy(
            name="Temp",
            tier=EnemyTier.COMMON,
            stats=Stats(max_hp=10, attack=1, defense=1, speed=10),
            floor_level=1,
            exp_reward=1,
            gold_reward=1,
        )
        test_app.session.state.combat = CombatSystem(
            player=test_app.session.player, enemy=enemy
        )
        test_app.session.state.combat.enemy = None  # type: ignore
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.COMBAT

        # Case C: enemy.tier is None
        dummy_enemy = Enemy(
            name="Phantom",
            tier=EnemyTier.COMMON,
            stats=Stats(max_hp=10, attack=1, defense=1, speed=10),
            floor_level=1,
            exp_reward=1,
            gold_reward=1,
        )
        dummy_enemy.tier = None  # type: ignore
        test_app.session.state.combat = CombatSystem(
            player=test_app.session.player, enemy=dummy_enemy
        )
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.COMBAT


# =============================================================================
# 4. EXTREME TICK VALUES (dt) AND PLAYBACK STOP/START CYCLES
# =============================================================================
class TestExtremeTickValuesAndPlaybackCycles:
    """Stress tests verifying audio resilience under degenerate dt values and rapid controls."""

    def test_zero_dt_tick_stability(self, test_app: PygameApp):
        """Advance 100 consecutive frames with dt = 0.0 (simulating paused clock or zero-delta)."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        track = test_app.music_engine.get_current_track()

        for _ in range(100):
            test_app.update(0.0)
            assert test_app.music_engine.get_current_context() == MusicContext.MAP
            assert test_app.music_engine.get_current_track() == track

    def test_massive_dt_tick_stability(self, test_app: PygameApp):
        """Advance with massive time jumps (10.0, 100.0, 10000.0, float('inf'))."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)

        massive_dts = [10.0, 100.0, 10000.0, float("inf")]
        for dt in massive_dts:
            test_app.update(dt)
            assert test_app.music_engine.get_current_context() == MusicContext.MAP
            assert test_app.music_engine.get_current_track() is not None

    def test_negative_dt_tick_stability(self, test_app: PygameApp):
        """Advance with negative dt values (-0.01, -1.0, -999.0) verifying defensive clamp."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        track = test_app.music_engine.get_current_track()

        negative_dts = [-0.01, -0.1, -1.0, -999.0]
        for dt in negative_dts:
            test_app.update(dt)
            assert test_app.music_engine.get_current_context() == MusicContext.MAP
            assert test_app.music_engine.get_current_track() == track

    def test_nan_dt_tick_stability(self, test_app: PygameApp):
        """Advance with NaN dt without throwing uncaught exceptions or corrupting state."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        test_app.update(float("nan"))
        assert test_app.music_engine.get_current_context() == MusicContext.MAP

    def test_100_rapid_stop_and_update_cycles(self, test_app: PygameApp):
        """Execute 100 rapid cycles of stop() followed immediately by app.update(0.016).

        Verifies that an external stop is cleanly detected and re-established by
        app.update_music_context() without crash or stream corruption.
        """
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.MAP

        for _ in range(100):
            test_app.music_engine.stop()
            assert test_app.music_engine.playback_state == PlaybackState.STOPPED
            test_app.update(0.016)
            # update_music_context detects stopped engine and restarts active context
            assert test_app.music_engine.playback_state == PlaybackState.PLAYING
            assert test_app.music_engine.get_current_track() in ("exploration_01", "exploration_02")

    def test_rapid_stop_fadeout_and_forced_restart(self, test_app: PygameApp):
        """Execute 30 rapid cycles of stop(fade_ms=10) with immediate forced restart."""
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)

        for _ in range(30):
            test_app.music_engine.stop(fade_ms=10)
            test_app.update(0.016)
            test_app.update_music_context(force_restart=True)
            test_app.update(0.016)
            assert test_app.music_engine.get_current_context() == MusicContext.COMBAT
            assert test_app.music_engine.get_current_track() in ("combat_01", "combat_02")

    def test_rapid_mute_unmute_cycles(self, test_app: PygameApp):
        """Execute 100 rapid toggle_mute() cycles and confirm persistence and volume sync."""
        for i in range(100):
            expected_mute = (i % 2 == 0)
            test_app.music_engine.set_muted(expected_mute)
            test_app.update(0.016)

            assert test_app.music_engine.is_muted() == expected_mute
            assert test_app.music_engine.settings_manager.is_music_muted() == expected_mute

    def test_rapid_pause_unpause_cycles(self, test_app: PygameApp):
        """Execute 50 rapid pause() and unpause() cycles while updating."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)

        for _ in range(50):
            test_app.music_engine.pause()
            test_app.update(0.016)
            assert test_app.music_engine.is_paused()

            test_app.music_engine.unpause()
            test_app.update(0.016)
            assert test_app.music_engine.is_playing()


# =============================================================================
# 5. CONCURRENCY, RESOURCE LEAKS, AND STABILITY HARNESS
# =============================================================================
class TestConcurrencyAndZeroLeakStability:
    """Stress tests verifying thread-safety, garbage collection, and leak-free execution."""

    def test_concurrent_multithreaded_transitions_and_updates(self, test_app: PygameApp):
        """Concurrently drive session mode transitions and audio controls from a worker thread.

        A background worker thread continuously changes modes and toggles mute
        while the main thread executes update(dt) and draw().
        Verifies zero race condition exceptions, deadlocks, or crashes.
        """
        all_modes = list(GameMode)
        stop_event = threading.Event()
        worker_errors: list[Exception] = []

        def background_worker():
            rng = random.Random(42)
            while not stop_event.is_set():
                try:
                    mode = rng.choice(all_modes)
                    test_app.session.switch_mode(mode)
                    if rng.random() < 0.2:
                        test_app.music_engine.toggle_mute()
                    time.sleep(0.001)
                except Exception as exc:
                    worker_errors.append(exc)

        worker_thread = threading.Thread(target=background_worker, name="ModeFuzzer")
        worker_thread.start()

        main_errors: list[Exception] = []
        for _ in range(150):
            try:
                test_app.update(0.016)
                test_app.draw()
                time.sleep(0.001)
            except Exception as exc:
                main_errors.append(exc)

        stop_event.set()
        worker_thread.join(timeout=3.0)

        assert not worker_thread.is_alive(), "Worker thread deadlocked and failed to terminate!"
        assert len(worker_errors) == 0, f"Worker thread encountered {len(worker_errors)} errors: {worker_errors[:3]}"
        assert len(main_errors) == 0, f"Main thread encountered {len(main_errors)} errors: {main_errors[:3]}"

    def test_zero_leaks_under_high_volume_transitions(self, test_app: PygameApp):
        """Execute 300 rapid mode transitions and confirm garbage collection and leak resilience."""
        gc.collect()
        initial_gc_counts = len(gc.get_objects())

        all_modes = list(GameMode)
        rng = random.Random(777)

        for _ in range(300):
            mode = rng.choice(all_modes)
            test_app.session.switch_mode(mode)
            test_app.update(0.016)
            test_app.draw()

        gc.collect()
        final_gc_counts = len(gc.get_objects())
        growth = final_gc_counts - initial_gc_counts

        # Confirm no unbounded explosion in object retention
        assert growth < 5000, f"Excessive object retention detected: grew by {growth} objects over 300 transitions"
