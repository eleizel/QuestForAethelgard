"""Comprehensive integration test suite for View Mode transitions and MusicContext resolution in PygameApp.

Covers Milestone 3 requirements:
- View mode transitions triggering correct MusicContext (WELCOME, MAP, COMBAT, BOSS).
- Context preservation across welcome, class select, biome select, and credits.
- Normal combat encounter (COMMON, UNCOMMON) triggering MusicContext.COMBAT.
- Elite and boss combat encounter (ELITE, BOSS) triggering MusicContext.BOSS.
- Modal views (INVENTORY, CHARACTER, LOOT) retaining active music context without reset.
- PygameApp update loop driving DynamicMusicEngine.update(dt).
- Headless CI execution safety under dummy audio/video drivers.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest
import pygame

from src.core.game_state import GameMode
from src.core.persistence import MemoryStorageBackend
from src.core.session import GameSession
from src.entities.actor import Stats
from src.entities.enemy import Enemy, EnemyTier
from src.frontends.pygame_ce.app import PygameApp
from src.frontends.pygame_ce.music_engine import (
    AudioSettingsManager,
    DynamicMusicEngine,
    MusicContext,
    resolve_music_context,
)
from src.systems.combat import CombatSystem


@pytest.fixture(autouse=True)
def ensure_headless_env():
    """Ensure headless SDL dummy drivers and clean mixer state."""
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
    """In-memory isolated storage backend."""
    return MemoryStorageBackend()


@pytest.fixture
def audio_settings(memory_backend: MemoryStorageBackend) -> AudioSettingsManager:
    """AudioSettingsManager backed by MemoryStorageBackend."""
    return AudioSettingsManager(backend=memory_backend)


@pytest.fixture
def music_engine(audio_settings: AudioSettingsManager) -> DynamicMusicEngine:
    """DynamicMusicEngine instance with isolated storage."""
    eng = DynamicMusicEngine(settings_manager=audio_settings)
    yield eng
    eng.stop()


@pytest.fixture
def test_app(music_engine: DynamicMusicEngine) -> PygameApp:
    """PygameApp instance injected with test music engine."""
    app = PygameApp(headless=True, session=GameSession(), music_engine=music_engine)
    if hasattr(app, "music_engine"):
        app.music_engine = music_engine
    else:
        setattr(app, "music_engine", music_engine)
    return app


# =============================================================================
# 1. VIEW MODE MUSIC CONTEXT TRANSITIONS
# =============================================================================
class TestViewModeMusicTransitions:
    """Tests for PygameApp view mode transitions triggering correct MusicContext."""

    def test_initial_launch_triggers_welcome_context(self, test_app: PygameApp):
        """Application launch in WELCOME mode triggers MusicContext.WELCOME."""
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.WELCOME
        assert test_app.music_engine.get_current_track() in ("welcome_01", "welcome_02")

    def test_welcome_to_class_select_preserves_track(self, test_app: PygameApp):
        """Transitioning from WELCOME to CLASS_SELECT preserves active track without restarting."""
        test_app.update(0.016)
        initial_track = test_app.music_engine.get_current_track()
        assert initial_track is not None

        test_app.session.switch_mode(GameMode.CLASS_SELECT)
        test_app.update(0.016)

        assert test_app.music_engine.get_current_context() == MusicContext.WELCOME
        assert test_app.music_engine.get_current_track() == initial_track

    def test_class_select_to_biome_select_preserves_track(self, test_app: PygameApp):
        """Transitioning to BIOME_SELECT retains MusicContext.WELCOME."""
        test_app.session.switch_mode(GameMode.CLASS_SELECT)
        test_app.update(0.016)
        track = test_app.music_engine.get_current_track()

        test_app.session.switch_mode(GameMode.BIOME_SELECT)
        test_app.update(0.016)

        assert test_app.music_engine.get_current_context() == MusicContext.WELCOME
        assert test_app.music_engine.get_current_track() == track

    def test_welcome_to_credits_preserves_track(self, test_app: PygameApp):
        """Transitioning to CREDITS retains MusicContext.WELCOME."""
        test_app.update(0.016)
        track = test_app.music_engine.get_current_track()

        test_app.session.switch_mode(GameMode.CREDITS)
        test_app.update(0.016)

        assert test_app.music_engine.get_current_context() == MusicContext.WELCOME
        assert test_app.music_engine.get_current_track() == track

    def test_transition_welcome_to_map_starts_exploration(self, test_app: PygameApp):
        """Switching mode to MAP transitions context to MusicContext.MAP."""
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.WELCOME

        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)

        assert test_app.music_engine.get_current_context() == MusicContext.MAP
        assert test_app.music_engine.get_current_track() in ("exploration_01", "exploration_02")

    def test_transition_map_to_combat_common(self, test_app: PygameApp):
        """Initiating combat with COMMON enemy transitions to MusicContext.COMBAT."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)

        # Set up COMMON enemy combat
        enemy = Enemy(
            name="Imp",
            tier=EnemyTier.COMMON,
            stats=Stats(max_hp=20, attack=5, defense=2, speed=10),
            floor_level=1,
            exp_reward=10,
            gold_reward=5,
        )
        test_app.session.state.combat = CombatSystem(player=test_app.session.player, enemy=enemy)
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)

        assert test_app.music_engine.get_current_context() == MusicContext.COMBAT
        assert test_app.music_engine.get_current_track() in ("combat_01", "combat_02")

    def test_transition_map_to_combat_uncommon(self, test_app: PygameApp):
        """Initiating combat with UNCOMMON enemy transitions to MusicContext.COMBAT."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)

        # Set up UNCOMMON enemy combat
        enemy = Enemy(
            name="Bat",
            tier=EnemyTier.UNCOMMON,
            stats=Stats(max_hp=30, attack=8, defense=3, speed=10),
            floor_level=1,
            exp_reward=15,
            gold_reward=8,
        )
        test_app.session.state.combat = CombatSystem(player=test_app.session.player, enemy=enemy)
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)

        assert test_app.music_engine.get_current_context() == MusicContext.COMBAT
        assert test_app.music_engine.get_current_track() in ("combat_01", "combat_02")

    def test_transition_map_to_combat_elite(self, test_app: PygameApp):
        """Initiating combat with ELITE enemy transitions to MusicContext.BOSS."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)

        # Set up ELITE enemy combat
        enemy = Enemy(
            name="Gargoyle",
            tier=EnemyTier.ELITE,
            stats=Stats(max_hp=80, attack=15, defense=8, speed=10),
            floor_level=1,
            exp_reward=35,
            gold_reward=20,
        )
        test_app.session.state.combat = CombatSystem(player=test_app.session.player, enemy=enemy)
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)

        assert test_app.music_engine.get_current_context() == MusicContext.BOSS
        assert test_app.music_engine.get_current_track() in ("boss_01", "boss_02")

    def test_transition_map_to_combat_boss(self, test_app: PygameApp):
        """Initiating combat with BOSS enemy transitions to MusicContext.BOSS."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)

        # Set up BOSS enemy combat
        enemy = Enemy(
            name="Archon",
            tier=EnemyTier.BOSS,
            stats=Stats(max_hp=200, attack=25, defense=12, speed=10),
            floor_level=1,
            exp_reward=100,
            gold_reward=50,
        )
        test_app.session.state.combat = CombatSystem(player=test_app.session.player, enemy=enemy)
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)

        assert test_app.music_engine.get_current_context() == MusicContext.BOSS
        assert test_app.music_engine.get_current_track() in ("boss_01", "boss_02")

    def test_combat_victory_returns_to_map_exploration(self, test_app: PygameApp):
        """Returning to MAP after combat switches back to exploration music."""
        # Combat -> Map
        enemy = Enemy(
            name="Imp",
            tier=EnemyTier.COMMON,
            stats=Stats(max_hp=20, attack=5, defense=2, speed=10),
            floor_level=1,
            exp_reward=10,
            gold_reward=5,
        )
        test_app.session.state.combat = CombatSystem(player=test_app.session.player, enemy=enemy)
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.COMBAT

        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.MAP
        assert test_app.music_engine.get_current_track() in ("exploration_01", "exploration_02")

    def test_full_game_loop_sequential_music_transitions(self, test_app: PygameApp):
        """Execute full journey: WELCOME -> CLASS_SELECT -> MAP -> COMBAT(COMMON) -> MAP -> COMBAT(BOSS) -> WELCOME."""
        # 1. Title
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.WELCOME

        # 2. Class Select
        test_app.session.switch_mode(GameMode.CLASS_SELECT)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.WELCOME

        # 3. Map
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.MAP

        # 4. Common Combat
        c_enemy = Enemy(
            name="Imp",
            tier=EnemyTier.COMMON,
            stats=Stats(max_hp=20, attack=5, defense=2, speed=10),
            floor_level=1,
            exp_reward=10,
            gold_reward=5,
        )
        test_app.session.state.combat = CombatSystem(player=test_app.session.player, enemy=c_enemy)
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.COMBAT

        # 5. Return to Map
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.MAP

        # 6. Boss Combat
        b_enemy = Enemy(
            name="Lord",
            tier=EnemyTier.BOSS,
            stats=Stats(max_hp=150, attack=20, defense=10, speed=10),
            floor_level=1,
            exp_reward=100,
            gold_reward=50,
        )
        test_app.session.state.combat = CombatSystem(player=test_app.session.player, enemy=b_enemy)
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.BOSS

        # 7. Reset to Title
        test_app.session.switch_mode(GameMode.WELCOME)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.WELCOME


# =============================================================================
# 2. MODAL VIEW AUDIO PRESERVATION
# =============================================================================
class TestModalViewAudioPreservation:
    """Tests that modal overlay views retain active background music without reset."""

    def test_inventory_modal_from_map_preserves_exploration_music(self, test_app: PygameApp):
        """Opening inventory modal while on map retains MAP music context and track."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        map_track = test_app.music_engine.get_current_track()

        test_app.session.switch_mode(GameMode.INVENTORY)
        test_app.update(0.016)

        assert test_app.music_engine.get_current_context() == MusicContext.MAP
        assert test_app.music_engine.get_current_track() == map_track

        # Close inventory back to map
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        assert test_app.music_engine.get_current_context() == MusicContext.MAP
        assert test_app.music_engine.get_current_track() == map_track

    def test_character_modal_from_map_preserves_exploration_music(self, test_app: PygameApp):
        """Opening character modal while on map retains MAP music context."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        map_track = test_app.music_engine.get_current_track()

        test_app.session.switch_mode(GameMode.CHARACTER)
        test_app.update(0.016)

        assert test_app.music_engine.get_current_context() == MusicContext.MAP
        assert test_app.music_engine.get_current_track() == map_track

    def test_inventory_modal_during_combat_preserves_combat_music(self, test_app: PygameApp):
        """Opening inventory during combat preserves COMBAT music context."""
        enemy = Enemy(
            name="Imp",
            tier=EnemyTier.COMMON,
            stats=Stats(max_hp=20, attack=5, defense=2, speed=10),
            floor_level=1,
            exp_reward=10,
            gold_reward=5,
        )
        test_app.session.state.combat = CombatSystem(player=test_app.session.player, enemy=enemy)
        test_app.session.switch_mode(GameMode.COMBAT)
        test_app.update(0.016)
        combat_track = test_app.music_engine.get_current_track()

        test_app.session.switch_mode(GameMode.INVENTORY)
        test_app.update(0.016)

        assert test_app.music_engine.get_current_context() == MusicContext.COMBAT
        assert test_app.music_engine.get_current_track() == combat_track

    @pytest.mark.parametrize(
        "modal_mode",
        [
            GameMode.LOOT,
            GameMode.SHOP,
            GameMode.ABILITY_CHOICE,
            GameMode.PROMOTION,
            GameMode.EVENTS,
        ],
    )
    def test_secondary_views_preserve_active_music(self, test_app: PygameApp, modal_mode: GameMode):
        """Secondary/intermediate game modes preserve current music stream."""
        test_app.session.switch_mode(GameMode.MAP)
        test_app.update(0.016)
        active_track = test_app.music_engine.get_current_track()

        test_app.session.switch_mode(modal_mode)
        test_app.update(0.016)

        assert test_app.music_engine.get_current_context() == MusicContext.MAP
        assert test_app.music_engine.get_current_track() == active_track


# =============================================================================
# 3. CONTEXT RESOLUTION UNIT TESTS
# =============================================================================
class TestResolveMusicContextUnit:
    """Isolated unit tests for resolve_music_context function."""

    @pytest.mark.parametrize(
        "mode,expected_context",
        [
            (GameMode.WELCOME, MusicContext.WELCOME),
            (GameMode.CLASS_SELECT, MusicContext.WELCOME),
            (GameMode.BIOME_SELECT, MusicContext.WELCOME),
            (GameMode.CREDITS, MusicContext.WELCOME),
            (GameMode.MAP, MusicContext.MAP),
        ],
    )
    def test_static_view_context_resolution(self, mode: GameMode, expected_context: MusicContext):
        """Static game modes resolve directly to their expected context."""
        session = GameSession()
        session.switch_mode(mode)
        assert resolve_music_context(session) == expected_context

    @pytest.mark.parametrize(
        "tier,expected_context",
        [
            (EnemyTier.COMMON, MusicContext.COMBAT),
            (EnemyTier.UNCOMMON, MusicContext.COMBAT),
            (EnemyTier.ELITE, MusicContext.BOSS),
            (EnemyTier.BOSS, MusicContext.BOSS),
        ],
    )
    def test_combat_tier_context_resolution(self, tier: EnemyTier, expected_context: MusicContext):
        """Combat mode inspects enemy tier and selects COMBAT vs BOSS."""
        session = GameSession()
        enemy = Enemy(
            name="Target",
            tier=tier,
            stats=Stats(max_hp=50, attack=10, defense=5, speed=10),
            floor_level=1,
            exp_reward=10,
            gold_reward=5,
        )
        session.state.combat = CombatSystem(player=session.player, enemy=enemy)
        session.switch_mode(GameMode.COMBAT)
        assert resolve_music_context(session) == expected_context

    def test_combat_without_enemy_defaults_to_combat_context(self):
        """Defensive fallback when combat has no enemy attached."""
        session = GameSession()
        session.state.combat = None
        session.switch_mode(GameMode.COMBAT)
        assert resolve_music_context(session) == MusicContext.COMBAT

    @pytest.mark.parametrize(
        "unmapped_mode",
        [
            GameMode.INVENTORY,
            GameMode.CHARACTER,
            GameMode.LOOT,
            GameMode.SHOP,
            GameMode.ABILITY_CHOICE,
            GameMode.PROMOTION,
            GameMode.EVENTS,
            GameMode.GAME_OVER,
            GameMode.VICTORY,
        ],
    )
    def test_unmapped_modes_return_none_for_preservation(self, unmapped_mode: GameMode):
        """Unmapped or overlay modes return None so music continues uninterrupted."""
        session = GameSession()
        session.switch_mode(unmapped_mode)
        assert resolve_music_context(session) is None


# =============================================================================
# 4. PYGAME APP LIFECYCLE & STABILITY
# =============================================================================
class TestPygameAppMusicEngineLifecycle:
    """Tests for PygameApp lifecycle, update invocation, and headless resilience."""

    def test_app_update_calls_music_engine_update(self, test_app: PygameApp):
        """Calling PygameApp.update advances the music engine timer."""
        with patch.object(test_app.music_engine, "update", wraps=test_app.music_engine.update) as spy_update:
            test_app.update(0.016)
            spy_update.assert_called_with(0.016)

    def test_rapid_view_transitions_stability(self, test_app: PygameApp):
        """Rapid cycling across modes does not crash or corrupt audio state."""
        modes = [
            GameMode.WELCOME,
            GameMode.CLASS_SELECT,
            GameMode.MAP,
            GameMode.INVENTORY,
            GameMode.MAP,
            GameMode.CREDITS,
            GameMode.WELCOME,
        ]
        for _ in range(5):
            for mode in modes:
                test_app.session.switch_mode(mode)
                test_app.update(0.016)
                assert test_app.music_engine.get_current_context() is not None
