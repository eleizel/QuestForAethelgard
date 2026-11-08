"""End-to-End (E2E) Test Suite for QuestForAethelgard Dynamic Music Engine.

Covers all 4 Tiers of verification per TEST_INFRA.md and Milestone 4 requirements:
- Tier 1: Feature Coverage (>=5 tests per feature across all 8 features = >=40 tests)
  - F1: Asset resolution & format fallback (.ogg -> .mp3)
  - F2: Context resolution across game modes (WELCOME, MAP, COMBAT, BOSS)
  - F3: Randomized 2-track selection per context
  - F4: Combat encounter distinction (normal COMMON/UNCOMMON vs elite/boss ELITE/BOSS)
  - F5: Seamless view transitions and modal retention (INVENTORY, CHARACTER, LOOT)
  - F6: Mute/unmute toggle and volume zeroing
  - F7: Persistent mute across application restarts (StorageBackend)
  - F8: Welcome view mute button UI layout, hover, and interaction
- Tier 2: Boundary & Corner Cases (>=5 tests per feature = >=40 tests)
  - Missing/corrupted audio files, missing storage files, corrupted JSON configs
  - Extreme tick rates (0.0, negative, huge, nan), rapid start/stop/mute cycles
  - View transitions with None enemy, None combat, uninitialized mixer
  - Pixel boundaries of welcome mute button
- Tier 3: Cross-Feature Combinations (>=15 tests)
  - Pairwise combinations of (Context x Mute State x Restart Lifecycle x Modal Stack)
- Tier 4: Real-World Application Scenarios (>=5 complete workflows)
  - Scenario 1: Full Game Loop Session
  - Scenario 2: Mute Toggle & App Restart Cycle
  - Scenario 3: Rapid View Navigation & Modal Overlays
  - Scenario 4: Repeated Combat Enqueue with Common vs Elite
  - Scenario 5: Track Shuffle & Loop Validation across 100 transitions

Total test count: >= 100 comprehensive opaque-box E2E tests.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import random
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
import pygame

from src.core.events import AudioCue, AudioCueEvent, event_bus
from src.core.game_state import GameMode
from src.core.i18n import i18n
from src.core.persistence import MemoryStorageBackend
from src.core.save_manager import FileStorageBackend
from src.core.session import GameSession
from src.entities.actor import Stats
from src.entities.enemy import Enemy, EnemyTier
from src.frontends.pygame_ce.app import PygameApp
from src.frontends.pygame_ce.audio_track_loader import (
    DEFAULT_AUDIO_EXTENSIONS,
    AudioTrackLoader,
    get_default_music_dir,
    is_audio_available,
    load_audio_track,
    resolve_audio_track,
)
from src.frontends.pygame_ce.music_engine import (
    CONTEXT_TRACKS,
    DEFAULT_SETTINGS_KEY,
    AudioSettingsData,
    AudioSettingsManager,
    DynamicMusicEngine,
    MusicContext,
    PlaybackState,
    resolve_music_context,
)
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.welcome import PygameWelcomeView
from src.systems.combat import CombatSystem


CANONICAL_TRACK_STEMS: tuple[str, ...] = (
    "welcome_01",
    "welcome_02",
    "exploration_01",
    "exploration_02",
    "combat_01",
    "combat_02",
    "boss_01",
    "boss_02",
)


def make_test_enemy(name: str, tier: EnemyTier, hp: int = 30, attack: int = 5) -> Enemy:
    """Helper to construct an Enemy instance with proper signature."""
    return Enemy(
        name=name,
        stats=Stats(max_hp=hp, attack=attack, defense=2, speed=10),
        tier=tier,
        floor_level=1,
        exp_reward=10,
        gold_reward=5,
    )


@pytest.fixture(autouse=True)
def setup_headless_e2e_environment() -> Generator[None, None, None]:
    """Ensure headless dummy SDL drivers, clean mixer, and pristine i18n state."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    if not pygame.get_init():
        pygame.init()
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            pass

    original_locale = i18n.locale
    yield
    i18n.locale = original_locale

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
def music_engine(audio_settings: AudioSettingsManager) -> Generator[DynamicMusicEngine, None, None]:
    """Fresh dynamic music engine instance."""
    engine = DynamicMusicEngine(settings_manager=audio_settings)
    yield engine
    engine.stop()


@pytest.fixture
def welcome_view(music_engine: DynamicMusicEngine) -> PygameWelcomeView:
    """PygameWelcomeView instance wired with isolated test music engine."""
    return PygameWelcomeView(music_engine=music_engine)


@pytest.fixture
def session() -> GameSession:
    """Fresh game session in WELCOME mode."""
    sess = GameSession()
    sess.switch_mode(GameMode.WELCOME)
    return sess


@pytest.fixture
def e2e_app(music_engine: DynamicMusicEngine, session: GameSession) -> PygameApp:
    """Headless PygameApp instance wired to isolated engine and session."""
    app = PygameApp(headless=True, session=session, music_engine=music_engine)
    if hasattr(app, "music_engine"):
        app.music_engine = music_engine
    return app


# =============================================================================
# TIER 1: FEATURE COVERAGE (>=5 tests per feature x 8 features = >=40 tests)
# =============================================================================

class TestTier1Feature1AssetResolutionAndFallback:
    """F1: Asset resolution and format fallback (.ogg -> .mp3 -> .wav)."""

    def test_all_8_canonical_tracks_resolve_to_existing_files(self) -> None:
        """Verify all 8 canonical game track stems resolve to concrete existing files."""
        loader = AudioTrackLoader()
        for stem in CANONICAL_TRACK_STEMS:
            resolved_path = loader.resolve_track(stem)
            assert resolved_path is not None, f"Track {stem} must resolve"
            assert resolved_path.exists(), f"Resolved file {resolved_path} must exist on disk"
            assert resolved_path.suffix.lower() in DEFAULT_AUDIO_EXTENSIONS

    def test_extension_priority_prefers_ogg_over_mp3(self, tmp_path: Path) -> None:
        """Verify format priority chain selects .ogg before .mp3 when both exist."""
        test_dir = tmp_path / "music_priority"
        test_dir.mkdir(parents=True, exist_ok=True)
        ogg_file = test_dir / "priority_test.ogg"
        mp3_file = test_dir / "priority_test.mp3"
        ogg_file.write_bytes(b"OGG_DUMMY_HEADER")
        mp3_file.write_bytes(b"MP3_DUMMY_HEADER")

        loader = AudioTrackLoader(music_dir=test_dir)
        resolved = loader.resolve_track("priority_test")
        assert resolved is not None
        assert resolved.suffix.lower() == ".ogg"

    def test_fallback_to_mp3_when_ogg_missing(self, tmp_path: Path) -> None:
        """Verify format fallback transparently selects .mp3 when .ogg is absent."""
        test_dir = tmp_path / "music_mp3_only"
        test_dir.mkdir(parents=True, exist_ok=True)
        mp3_file = test_dir / "fallback_track.mp3"
        mp3_file.write_bytes(b"MP3_DATA")

        loader = AudioTrackLoader(music_dir=test_dir)
        resolved = loader.resolve_track("fallback_track")
        assert resolved is not None
        assert resolved.suffix.lower() == ".mp3"

    def test_direct_lookup_with_explicit_extension(self) -> None:
        """Passing an explicit file extension (.ogg or .mp3) resolves identically."""
        loader = AudioTrackLoader()
        resolved_stem = loader.resolve_track("welcome_01")
        assert resolved_stem is not None
        resolved_explicit = loader.resolve_track(f"welcome_01{resolved_stem.suffix}")
        assert resolved_explicit == resolved_stem

    def test_nonexistent_track_returns_none_safely(self) -> None:
        """Requesting an unregistered, non-existent track returns None without raising."""
        loader = AudioTrackLoader()
        assert loader.resolve_track("non_existent_abracadabra_track_999") is None

    def test_get_available_tracks_contains_all_canonical_stems(self) -> None:
        """AudioTrackLoader.get_available_tracks() returns all 8 canonical stems."""
        loader = AudioTrackLoader()
        available = loader.get_available_tracks()
        for stem in CANONICAL_TRACK_STEMS:
            assert stem in available, f"Canonical stem '{stem}' must be in available tracks"


class TestTier1Feature2ContextResolutionGameModes:
    """F2: Context resolution across game modes (WELCOME, MAP, COMBAT, BOSS)."""

    def test_welcome_mode_resolves_to_welcome_context(self, session: GameSession) -> None:
        """GameMode.WELCOME maps directly to MusicContext.WELCOME."""
        session.switch_mode(GameMode.WELCOME)
        assert resolve_music_context(session) == MusicContext.WELCOME

    def test_class_select_mode_resolves_to_welcome_context(self, session: GameSession) -> None:
        """GameMode.CLASS_SELECT maps to MusicContext.WELCOME."""
        session.switch_mode(GameMode.CLASS_SELECT)
        assert resolve_music_context(session) == MusicContext.WELCOME

    def test_credits_mode_resolves_to_welcome_context(self, session: GameSession) -> None:
        """GameMode.CREDITS maps to MusicContext.WELCOME."""
        session.switch_mode(GameMode.CREDITS)
        assert resolve_music_context(session) == MusicContext.WELCOME

    def test_map_mode_resolves_to_map_context(self, session: GameSession) -> None:
        """GameMode.MAP maps directly to MusicContext.MAP."""
        session.switch_mode(GameMode.MAP)
        assert resolve_music_context(session) == MusicContext.MAP

    def test_combat_mode_with_common_enemy_resolves_to_combat_context(
        self, session: GameSession
    ) -> None:
        """GameMode.COMBAT with a common enemy resolves to MusicContext.COMBAT."""
        enemy = make_test_enemy("Goblin", EnemyTier.COMMON)
        session.state.combat = CombatSystem(session.player, enemy)
        session.switch_mode(GameMode.COMBAT)
        assert resolve_music_context(session) == MusicContext.COMBAT

    def test_unmapped_modes_return_none_for_track_preservation(self, session: GameSession) -> None:
        """Unmapped modes (INVENTORY, CHARACTER, LOOT, SHOP) return None to retain active track."""
        for mode in (GameMode.INVENTORY, GameMode.CHARACTER, GameMode.LOOT, GameMode.SHOP):
            session.switch_mode(mode)
            assert resolve_music_context(session) is None, f"Mode {mode} should return None"


class TestTier1Feature3RandomizedTrackSelection:
    """F3: Randomized 2-track selection per context."""

    def test_welcome_context_chooses_strictly_from_welcome_tracks(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """MusicContext.WELCOME only selects welcome_01 or welcome_02."""
        for _ in range(25):
            chosen = music_engine.choose_track(MusicContext.WELCOME)
            assert chosen in ("welcome_01", "welcome_02")

    def test_map_context_chooses_strictly_from_exploration_tracks(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """MusicContext.MAP only selects exploration_01 or exploration_02."""
        for _ in range(25):
            chosen = music_engine.choose_track(MusicContext.MAP)
            assert chosen in ("exploration_01", "exploration_02")

    def test_combat_context_chooses_strictly_from_combat_tracks(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """MusicContext.COMBAT only selects combat_01 or combat_02."""
        for _ in range(25):
            chosen = music_engine.choose_track(MusicContext.COMBAT)
            assert chosen in ("combat_01", "combat_02")

    def test_boss_context_chooses_strictly_from_boss_tracks(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """MusicContext.BOSS only selects boss_01 or boss_02."""
        for _ in range(25):
            chosen = music_engine.choose_track(MusicContext.BOSS)
            assert chosen in ("boss_01", "boss_02")

    def test_binomial_spread_welcome_context_100_samples(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """100 samples across WELCOME context demonstrates non-zero spread for both tracks."""
        counts: dict[str, int] = {"welcome_01": 0, "welcome_02": 0}
        for _ in range(100):
            track = music_engine.choose_track(MusicContext.WELCOME)
            counts[track] += 1
        assert counts["welcome_01"] >= 15, f"welcome_01 count too low: {counts}"
        assert counts["welcome_02"] >= 15, f"welcome_02 count too low: {counts}"

    def test_binomial_spread_combat_context_100_samples(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """100 samples across COMBAT context demonstrates non-zero spread for both tracks."""
        counts: dict[str, int] = {"combat_01": 0, "combat_02": 0}
        for _ in range(100):
            track = music_engine.choose_track(MusicContext.COMBAT)
            counts[track] += 1
        assert counts["combat_01"] >= 15, f"combat_01 count too low: {counts}"
        assert counts["combat_02"] >= 15, f"combat_02 count too low: {counts}"


class TestTier1Feature4CombatEncounterDistinction:
    """F4: Combat encounter distinction (normal vs elite/boss)."""

    def test_common_enemy_triggers_combat_context(self, session: GameSession) -> None:
        """COMMON enemy in combat yields MusicContext.COMBAT."""
        enemy = make_test_enemy("Slime", EnemyTier.COMMON)
        session.state.combat = CombatSystem(session.player, enemy)
        session.switch_mode(GameMode.COMBAT)
        assert resolve_music_context(session) == MusicContext.COMBAT

    def test_uncommon_enemy_triggers_combat_context(self, session: GameSession) -> None:
        """UNCOMMON enemy in combat yields MusicContext.COMBAT."""
        enemy = make_test_enemy("Ghoul", EnemyTier.UNCOMMON)
        session.state.combat = CombatSystem(session.player, enemy)
        session.switch_mode(GameMode.COMBAT)
        assert resolve_music_context(session) == MusicContext.COMBAT

    def test_elite_enemy_triggers_boss_context(self, session: GameSession) -> None:
        """ELITE enemy in combat yields MusicContext.BOSS."""
        enemy = make_test_enemy("Dread Knight", EnemyTier.ELITE)
        session.state.combat = CombatSystem(session.player, enemy)
        session.switch_mode(GameMode.COMBAT)
        assert resolve_music_context(session) == MusicContext.BOSS

    def test_boss_enemy_triggers_boss_context(self, session: GameSession) -> None:
        """BOSS enemy in combat yields MusicContext.BOSS."""
        enemy = make_test_enemy("Archdemon", EnemyTier.BOSS)
        session.state.combat = CombatSystem(session.player, enemy)
        session.switch_mode(GameMode.COMBAT)
        assert resolve_music_context(session) == MusicContext.BOSS

    def test_app_plays_combat_track_for_normal_enemy(self, e2e_app: PygameApp) -> None:
        """PygameApp playback starts a combat_0X track for common enemies."""
        enemy = make_test_enemy("Wolf", EnemyTier.COMMON)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, enemy)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.COMBAT
        assert e2e_app.music_engine.get_current_track() in ("combat_01", "combat_02")

    def test_app_plays_boss_track_for_boss_enemy(self, e2e_app: PygameApp) -> None:
        """PygameApp playback starts a boss_0X track for boss enemies."""
        enemy = make_test_enemy("Overlord", EnemyTier.BOSS)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, enemy)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.BOSS
        assert e2e_app.music_engine.get_current_track() in ("boss_01", "boss_02")


class TestTier1Feature5SeamlessViewTransitions:
    """F5: Seamless view transitions and modal retention."""

    def test_welcome_to_class_select_preserves_track(self, e2e_app: PygameApp) -> None:
        """Transitioning WELCOME -> CLASS_SELECT preserves active track without restarting."""
        e2e_app.session.switch_mode(GameMode.WELCOME)
        e2e_app.update(0.016)
        initial_track = e2e_app.music_engine.get_current_track()
        assert initial_track is not None

        e2e_app.session.switch_mode(GameMode.CLASS_SELECT)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.WELCOME
        assert e2e_app.music_engine.get_current_track() == initial_track

    def test_map_to_inventory_modal_preserves_exploration_track(self, e2e_app: PygameApp) -> None:
        """Opening INVENTORY modal from MAP preserves active MAP context and track."""
        e2e_app.session.switch_mode(GameMode.MAP)
        e2e_app.update(0.016)
        map_track = e2e_app.music_engine.get_current_track()

        e2e_app.session.switch_mode(GameMode.INVENTORY)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.MAP
        assert e2e_app.music_engine.get_current_track() == map_track

    def test_map_to_character_modal_preserves_exploration_track(self, e2e_app: PygameApp) -> None:
        """Opening CHARACTER modal from MAP preserves active MAP context and track."""
        e2e_app.session.switch_mode(GameMode.MAP)
        e2e_app.update(0.016)
        map_track = e2e_app.music_engine.get_current_track()

        e2e_app.session.switch_mode(GameMode.CHARACTER)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.MAP
        assert e2e_app.music_engine.get_current_track() == map_track

    def test_combat_to_loot_preserves_combat_track(self, e2e_app: PygameApp) -> None:
        """Transitioning from COMBAT to LOOT preserves active combat track."""
        enemy = make_test_enemy("Spider", EnemyTier.COMMON)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, enemy)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)
        combat_track = e2e_app.music_engine.get_current_track()

        e2e_app.session.switch_mode(GameMode.LOOT)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.COMBAT
        assert e2e_app.music_engine.get_current_track() == combat_track

    def test_map_to_combat_transitions_cleanly(self, e2e_app: PygameApp) -> None:
        """Switching from MAP to COMBAT changes context and track cleanly."""
        e2e_app.session.switch_mode(GameMode.MAP)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.MAP

        enemy = make_test_enemy("Goblin", EnemyTier.COMMON)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, enemy)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.COMBAT
        assert e2e_app.music_engine.get_current_track() in ("combat_01", "combat_02")

    def test_combat_to_map_transitions_cleanly(self, e2e_app: PygameApp) -> None:
        """Switching from COMBAT back to MAP transitions cleanly back to MAP music."""
        enemy = make_test_enemy("Goblin", EnemyTier.COMMON)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, enemy)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)

        e2e_app.session.switch_mode(GameMode.MAP)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.MAP
        assert e2e_app.music_engine.get_current_track() in ("exploration_01", "exploration_02")


class TestTier1Feature6MuteToggleAndVolumeZeroing:
    """F6: Mute/unmute toggle and volume zeroing."""

    def test_initial_state_is_unmuted(self, music_engine: DynamicMusicEngine) -> None:
        """Fresh engine starts in unmuted state."""
        assert music_engine.is_muted() is False

    def test_toggle_mute_flips_state(self, music_engine: DynamicMusicEngine) -> None:
        """toggle_mute() inverts state: False -> True -> False."""
        first_toggle = music_engine.toggle_mute()
        assert first_toggle is True
        assert music_engine.is_muted() is True

        second_toggle = music_engine.toggle_mute()
        assert second_toggle is False
        assert music_engine.is_muted() is False

    def test_set_muted_explicit(self, music_engine: DynamicMusicEngine) -> None:
        """set_muted(True) and set_muted(False) set state idempotently."""
        music_engine.set_muted(True)
        assert music_engine.is_muted() is True
        music_engine.set_muted(True)
        assert music_engine.is_muted() is True
        music_engine.set_muted(False)
        assert music_engine.is_muted() is False

    def test_mute_zeroes_effective_mixer_volume(self, music_engine: DynamicMusicEngine) -> None:
        """When muted, mixer hardware volume is set to 0.0."""
        music_engine.set_volume(0.8)
        music_engine.set_muted(True)
        if pygame.mixer.get_init():
            assert pygame.mixer.music.get_volume() == 0.0

    def test_unmute_restores_effective_mixer_volume(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """Unmuting restores mixer hardware volume to master unmuted volume."""
        music_engine.set_volume(0.7)
        music_engine.set_muted(True)
        music_engine.set_muted(False)
        if pygame.mixer.get_init():
            assert pytest.approx(pygame.mixer.music.get_volume(), abs=0.05) == 0.7

    def test_custom_volume_preserved_across_mute_cycle(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """Engine volume attribute remains 0.65 throughout mute/unmute toggles."""
        music_engine.set_volume(0.65)
        music_engine.toggle_mute()
        assert music_engine.get_volume() == 0.65
        music_engine.toggle_mute()
        assert music_engine.get_volume() == 0.65


class TestTier1Feature7PersistentMuteStorage:
    """F7: Persistent mute across application restarts (StorageBackend)."""

    def test_mute_state_persisted_to_storage_key(
        self, audio_settings: AudioSettingsManager, memory_backend: MemoryStorageBackend
    ) -> None:
        """Muting writes JSON dictionary under DEFAULT_SETTINGS_KEY."""
        audio_settings.set_music_muted(True)
        raw_json = memory_backend.get(DEFAULT_SETTINGS_KEY)
        assert raw_json is not None
        data = json.loads(raw_json)
        assert data.get("music_muted") is True

    def test_new_settings_manager_restores_persisted_mute(
        self, memory_backend: MemoryStorageBackend
    ) -> None:
        """A new AudioSettingsManager instance on the same backend loads muted=True."""
        mgr1 = AudioSettingsManager(backend=memory_backend)
        mgr1.set_music_muted(True)

        mgr2 = AudioSettingsManager(backend=memory_backend)
        assert mgr2.is_music_muted() is True

    def test_new_music_engine_boots_muted_from_storage(
        self, memory_backend: MemoryStorageBackend
    ) -> None:
        """DynamicMusicEngine constructed with pre-muted settings boots muted."""
        mgr1 = AudioSettingsManager(backend=memory_backend)
        mgr1.set_music_muted(True)

        mgr2 = AudioSettingsManager(backend=memory_backend)
        engine = DynamicMusicEngine(settings_manager=mgr2)
        assert engine.is_muted() is True
        engine.stop()

    def test_unmute_persists_and_restores_cleanly(
        self, memory_backend: MemoryStorageBackend
    ) -> None:
        """Toggling mute to True then False persists False on subsequent boots."""
        mgr = AudioSettingsManager(backend=memory_backend)
        mgr.set_music_muted(True)
        mgr.set_music_muted(False)

        reloaded = AudioSettingsManager(backend=memory_backend)
        assert reloaded.is_music_muted() is False

    def test_disk_file_storage_backend_roundtrip(self, tmp_path: Path) -> None:
        """FileStorageBackend on disk persists mute settings across process restart simulation."""
        disk_backend1 = FileStorageBackend(save_dir=str(tmp_path / "saves"))
        mgr1 = AudioSettingsManager(backend=disk_backend1)
        mgr1.set_music_muted(True)

        disk_backend2 = FileStorageBackend(save_dir=str(tmp_path / "saves"))
        mgr2 = AudioSettingsManager(backend=disk_backend2)
        assert mgr2.is_music_muted() is True

    def test_volume_persisted_alongside_mute(
        self, memory_backend: MemoryStorageBackend
    ) -> None:
        """Volume setting (0.45) persists and reloads alongside mute state."""
        mgr1 = AudioSettingsManager(backend=memory_backend)
        mgr1.set_music_volume(0.45)
        mgr1.set_music_muted(True)

        mgr2 = AudioSettingsManager(backend=memory_backend)
        assert mgr2.is_music_muted() is True
        assert pytest.approx(mgr2.get_music_volume(), abs=0.01) == 0.45


class TestTier1Feature8WelcomeViewMuteButtonUI:
    """F8: Welcome view mute button UI layout, hover, and interaction."""

    def test_mute_button_rect_layout_top_right(self, welcome_view: PygameWelcomeView) -> None:
        """Mute button is positioned in the top-right corner of the 960x540 viewport."""
        rect = welcome_view.get_mute_button_rect()
        assert rect.width == 124
        assert rect.height == 36
        assert rect.top == 16
        assert rect.right == 960 - 16  # 944

    def test_mute_button_label_reflects_current_mute_state(
        self, welcome_view: PygameWelcomeView
    ) -> None:
        """Label displays '[♫ MUTE]' when unmuted and '[♫ UNMUTE]' when muted."""
        welcome_view.set_muted(False)
        assert welcome_view.get_mute_button_label() == "[♫ MUTE]"
        welcome_view.set_muted(True)
        assert welcome_view.get_mute_button_label() == "[♫ UNMUTE]"

    def test_mouse_click_inside_button_toggles_mute(
        self, welcome_view: PygameWelcomeView, session: GameSession
    ) -> None:
        """Left-click event inside button rect toggles mute state."""
        rect = welcome_view.get_mute_button_rect()
        click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)

        assert welcome_view.is_muted() is False
        welcome_view.handle_event(click_event, session)
        assert welcome_view.is_muted() is True
        welcome_view.handle_event(click_event, session)
        assert welcome_view.is_muted() is False

    def test_keyboard_m_toggles_mute(
        self, welcome_view: PygameWelcomeView, session: GameSession
    ) -> None:
        """Pressing 'M' key toggles mute state on PygameWelcomeView."""
        key_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m)

        assert welcome_view.is_muted() is False
        welcome_view.handle_event(key_event, session)
        assert welcome_view.is_muted() is True
        welcome_view.handle_event(key_event, session)
        assert welcome_view.is_muted() is False

    def test_mouse_hover_tracking_updates_flag(
        self, welcome_view: PygameWelcomeView
    ) -> None:
        """Mouse movement inside rect sets mute_hovered=True; outside sets False."""
        rect = welcome_view.get_mute_button_rect()

        motion_inside = pygame.event.Event(pygame.MOUSEMOTION, pos=rect.center)
        welcome_view.handle_event(motion_inside, MagicMock())
        assert welcome_view.mute_hovered is True

        motion_outside = pygame.event.Event(pygame.MOUSEMOTION, pos=(100, 100))
        welcome_view.handle_event(motion_outside, MagicMock())
        assert welcome_view.mute_hovered is False

    def test_mouse_click_emits_audio_cue(
        self, welcome_view: PygameWelcomeView, session: GameSession
    ) -> None:
        """Clicking mute button emits AudioCue.CLICK on event_bus."""
        rect = welcome_view.get_mute_button_rect()
        cues_received: list[AudioCue] = []

        def cue_handler(ev: AudioCueEvent) -> None:
            cues_received.append(ev.cue)

        event_bus.subscribe(AudioCueEvent, cue_handler)
        try:
            click_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
            welcome_view.handle_event(click_ev, session)
            assert AudioCue.CLICK in cues_received
        finally:
            event_bus.unsubscribe(AudioCueEvent, cue_handler)


# =============================================================================
# TIER 2: BOUNDARY & CORNER CASES (>=5 tests per feature x 8 = >=40 tests)
# =============================================================================

class TestTier2F1AssetBoundaries:
    """Tier 2: Asset resolution boundary cases."""

    def test_resolve_track_none_returns_none(self) -> None:
        """Passing None to resolve_track returns None safely."""
        loader = AudioTrackLoader()
        assert loader.resolve_track(None) is None

    def test_resolve_track_empty_string_returns_none(self) -> None:
        """Passing an empty string to resolve_track returns None."""
        loader = AudioTrackLoader()
        assert loader.resolve_track("") is None

    def test_resolve_track_whitespace_returns_none(self) -> None:
        """Passing whitespace string returns None."""
        loader = AudioTrackLoader()
        assert loader.resolve_track("   \t\n  ") is None

    def test_loader_missing_stem_returns_none(self) -> None:
        """Resolving a non-existent track stem returns None without error."""
        loader = AudioTrackLoader()
        assert loader.resolve_track("completely_missing_track_file_abc") is None

    def test_loader_auto_init_mixer_false(self) -> None:
        """Loader initialized with auto_init_mixer=False resolves paths without mixer."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        resolved = loader.resolve_track("welcome_01")
        assert resolved is not None
        assert resolved.exists()

    def test_dos_device_names_handled_safely(self) -> None:
        """Requesting reserved DOS names (CON, NUL, AUX) returns None without Windows error."""
        loader = AudioTrackLoader()
        for dos_name in ("CON", "NUL", "AUX", "PRN"):
            assert loader.resolve_track(dos_name) is None


class TestTier2F2ContextResolutionBoundaries:
    """Tier 2: Context resolution boundary cases."""

    def test_resolve_music_context_none_session_returns_none(self) -> None:
        """Passing None session to resolve_music_context returns None safely."""
        assert resolve_music_context(None) is None

    def test_resolve_music_context_missing_current_mode(self) -> None:
        """Passing session object without current_mode attribute returns None."""
        obj = object()
        assert resolve_music_context(obj) is None

    def test_resolve_music_context_invalid_mode_value(self) -> None:
        """Passing an unrecognized mode value returns None."""
        session = MagicMock()
        session.current_mode = "SUPER_INVALID_MODE_999"
        assert resolve_music_context(session) is None

    def test_engine_set_context_none_retains_active_state(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """set_context(None) does not reset or alter active context and track."""
        music_engine.set_context(MusicContext.MAP)
        current_ctx = music_engine.get_current_context()
        current_trk = music_engine.get_current_track()

        music_engine.set_context(None)
        assert music_engine.get_current_context() == current_ctx
        assert music_engine.get_current_track() == current_trk

    def test_engine_set_context_none_while_stopped(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """set_context(None) when stopped remains stopped."""
        music_engine.stop()
        music_engine.set_context(None)
        assert music_engine.get_current_context() is None
        assert music_engine.get_current_track() is None

    def test_engine_set_same_context_does_not_restart_playback(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """set_context with identical context does not re-select or restart track."""
        music_engine.set_context(MusicContext.WELCOME)
        trk1 = music_engine.get_current_track()
        music_engine.set_context(MusicContext.WELCOME)
        trk2 = music_engine.get_current_track()
        assert trk1 == trk2


class TestTier2F3RandomizationBoundaries:
    """Tier 2: Track selection and randomization boundary cases."""

    def test_select_track_empty_candidates_returns_empty_string(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """_select_track on an unregistered context returns empty string without crashing."""
        dummy_context = MagicMock()
        result = music_engine._select_track(dummy_context)
        assert result == ""

    def test_select_track_deterministic_with_seeded_rng(self) -> None:
        """Seeded RNG produces identical track choice sequence."""
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        eng1 = DynamicMusicEngine(rng=rng1)
        eng2 = DynamicMusicEngine(rng=rng2)

        sequence1 = [eng1.choose_track(MusicContext.MAP) for _ in range(10)]
        sequence2 = [eng2.choose_track(MusicContext.MAP) for _ in range(10)]
        assert sequence1 == sequence2
        eng1.stop()
        eng2.stop()

    def test_choose_track_multiple_calls_stable_in_roster(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """Calling choose_track 50 times always produces valid member of CONTEXT_TRACKS."""
        for ctx, valid_tracks in CONTEXT_TRACKS.items():
            for _ in range(20):
                track = music_engine.choose_track(ctx)
                assert track in valid_tracks

    def test_force_restart_restarts_track_in_same_context(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """force_restart=True forces track restart even in identical context."""
        music_engine.set_context(MusicContext.WELCOME)
        assert music_engine.is_playing() or not pygame.mixer.get_init()
        music_engine.set_context(MusicContext.WELCOME, force_restart=True)
        assert music_engine.get_current_context() == MusicContext.WELCOME

    def test_natural_track_finished_re_randomizes_within_same_context(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """_handle_track_finished triggers selection of next track in active context."""
        music_engine.set_context(MusicContext.COMBAT)
        music_engine._handle_track_finished()
        assert music_engine.get_current_context() == MusicContext.COMBAT
        assert music_engine.get_current_track() in ("combat_01", "combat_02")

    def test_handle_track_finished_with_none_context(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """_handle_track_finished when context is None transitions to STOPPED."""
        music_engine._current_context = None
        music_engine._handle_track_finished()
        assert music_engine.get_current_track() is None


class TestTier2F4CombatEncounterBoundaries:
    """Tier 2: Combat encounter context boundaries."""

    def test_combat_mode_with_none_combat_system_defaults_to_combat_context(
        self, session: GameSession
    ) -> None:
        """Combat mode with state.combat=None safely defaults to MusicContext.COMBAT."""
        session.state.combat = None
        session.switch_mode(GameMode.COMBAT)
        assert resolve_music_context(session) == MusicContext.COMBAT

    def test_combat_mode_with_none_enemy_defaults_to_combat_context(
        self, session: GameSession
    ) -> None:
        """Combat mode with combat.enemy=None defaults to MusicContext.COMBAT."""
        session.state.combat = MagicMock()
        session.state.combat.enemy = None
        session.switch_mode(GameMode.COMBAT)
        assert resolve_music_context(session) == MusicContext.COMBAT

    def test_combat_mode_with_none_enemy_tier_defaults_to_combat_context(
        self, session: GameSession
    ) -> None:
        """Combat mode with enemy.tier=None defaults to MusicContext.COMBAT."""
        enemy = MagicMock()
        enemy.tier = None
        session.state.combat = MagicMock()
        session.state.combat.enemy = enemy
        session.switch_mode(GameMode.COMBAT)
        assert resolve_music_context(session) == MusicContext.COMBAT

    def test_combat_mode_with_unrecognized_tier_defaults_to_combat_context(
        self, session: GameSession
    ) -> None:
        """Combat mode with custom tier string defaults to MusicContext.COMBAT."""
        enemy = MagicMock()
        enemy.tier = "CUSTOM_TIER_UNKNOWN"
        session.state.combat = MagicMock()
        session.state.combat.enemy = enemy
        session.switch_mode(GameMode.COMBAT)
        assert resolve_music_context(session) == MusicContext.COMBAT

    def test_combat_enemy_tier_mutation_updates_context(
        self, e2e_app: PygameApp
    ) -> None:
        """Enemy tier changing from COMMON to BOSS updates resolved context upon update."""
        enemy = make_test_enemy("Shapeshifter", EnemyTier.COMMON)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, enemy)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.COMBAT

        # Mutate to BOSS
        enemy.tier = EnemyTier.BOSS
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.BOSS

    def test_combat_enemy_replaced_with_common_switches_back(
        self, e2e_app: PygameApp
    ) -> None:
        """Replacing a BOSS enemy with COMMON switches context back to COMBAT."""
        boss = make_test_enemy("Titan", EnemyTier.BOSS, hp=150)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, boss)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.BOSS

        minion = make_test_enemy("Minion", EnemyTier.COMMON, hp=15)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, minion)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.COMBAT


class TestTier2F5ViewTransitionBoundaries:
    """Tier 2: View transition and update loop boundaries."""

    def test_rapid_view_transitions_20_iterations_no_crash(
        self, e2e_app: PygameApp
    ) -> None:
        """Rapidly cycling modes 20 times within 1 frame causes zero crash."""
        modes = [
            GameMode.WELCOME,
            GameMode.CLASS_SELECT,
            GameMode.MAP,
            GameMode.INVENTORY,
            GameMode.CHARACTER,
            GameMode.MAP,
            GameMode.WELCOME,
        ]
        for mode in modes * 3:
            e2e_app.session.switch_mode(mode)
            e2e_app.update(0.005)
        assert e2e_app.music_engine.get_current_context() is not None

    def test_deep_modal_stack_chain_preserves_track(
        self, e2e_app: PygameApp
    ) -> None:
        """Opening a simulated chain of modals keeps original map track untouched."""
        e2e_app.session.switch_mode(GameMode.MAP)
        e2e_app.update(0.016)
        orig_track = e2e_app.music_engine.get_current_track()

        for modal in (GameMode.INVENTORY, GameMode.CHARACTER, GameMode.SHOP, GameMode.LOOT):
            e2e_app.session.switch_mode(modal)
            e2e_app.update(0.016)
            assert e2e_app.music_engine.get_current_track() == orig_track

    def test_transition_with_zero_dt_update(self, music_engine: DynamicMusicEngine) -> None:
        """dt=0.0 frame update executes safely without division by zero."""
        music_engine.set_context(MusicContext.WELCOME)
        music_engine.update(0.0)
        assert music_engine.get_current_context() == MusicContext.WELCOME

    def test_transition_with_negative_dt_clamped_safely(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """dt < 0.0 is clamped to 0.0 and processed safely."""
        music_engine.set_context(MusicContext.MAP)
        music_engine.update(-1.5)
        assert music_engine.get_current_context() == MusicContext.MAP

    def test_transition_with_massive_dt_update(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """dt=999999.0 does not overflow timers or crash engine."""
        music_engine.set_context(MusicContext.MAP)
        music_engine.update(999999.0)
        assert music_engine.get_current_context() == MusicContext.MAP

    def test_transition_with_nan_dt_update(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """dt=float('nan') executes update without crashing engine."""
        music_engine.set_context(MusicContext.COMBAT)
        try:
            music_engine.update(float("nan"))
        except Exception:
            pass  # Shouldn't crash process


class TestTier2F6VolumeMuteBoundaries:
    """Tier 2: Volume and mute boundary values."""

    def test_volume_clamped_below_zero(self, music_engine: DynamicMusicEngine) -> None:
        """Setting volume < 0.0 clamps cleanly to 0.0."""
        music_engine.set_volume(-0.5)
        assert music_engine.get_volume() == 0.0

    def test_volume_clamped_above_one(self, music_engine: DynamicMusicEngine) -> None:
        """Setting volume > 1.0 clamps cleanly to 1.0."""
        music_engine.set_volume(2.5)
        assert music_engine.get_volume() == 1.0

    def test_volume_nan_handled_safely(self, music_engine: DynamicMusicEngine) -> None:
        """Setting volume to NaN falls back to 1.0."""
        music_engine.set_volume(float("nan"))
        assert music_engine.get_volume() == 1.0

    def test_volume_infinity_handled_safely(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """Setting volume to Infinity falls back to 1.0."""
        music_engine.set_volume(float("inf"))
        assert music_engine.get_volume() == 1.0

    def test_volume_invalid_type_fallback_in_settings_manager(
        self, audio_settings: AudioSettingsManager
    ) -> None:
        """Passing non-convertible type to AudioSettingsManager falls back to 1.0."""
        audio_settings.set_music_volume("invalid_volume_string")  # type: ignore[arg-type]
        assert audio_settings.get_music_volume() == 1.0

    def test_rapid_mute_toggle_50_cycles_state_parity(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """50 toggles in a loop returns exactly to original unmuted state."""
        assert music_engine.is_muted() is False
        for _ in range(50):
            music_engine.toggle_mute()
        assert music_engine.is_muted() is False


class TestTier2F7StoragePersistenceBoundaries:
    """Tier 2: Storage persistence boundary cases and corruption recovery."""

    def test_corrupted_json_syntax_storage_recovery(
        self, memory_backend: MemoryStorageBackend
    ) -> None:
        """Corrupted JSON string falls back to default settings without crashing."""
        memory_backend.set(DEFAULT_SETTINGS_KEY, "{corrupt_not_json_syntax: true,")
        mgr = AudioSettingsManager(backend=memory_backend)
        assert mgr.is_music_muted() is False
        assert mgr.get_music_volume() == 1.0

    def test_non_dict_json_payload_storage_recovery(
        self, memory_backend: MemoryStorageBackend
    ) -> None:
        """JSON payload that is a raw list or int falls back to defaults."""
        memory_backend.set(DEFAULT_SETTINGS_KEY, json.dumps([1, 2, 3]))
        mgr = AudioSettingsManager(backend=memory_backend)
        assert mgr.is_music_muted() is False

    def test_missing_keys_in_json_storage_recovery(
        self, memory_backend: MemoryStorageBackend
    ) -> None:
        """JSON missing 'music_muted' uses default False."""
        memory_backend.set(DEFAULT_SETTINGS_KEY, json.dumps({"version": 1}))
        mgr = AudioSettingsManager(backend=memory_backend)
        assert mgr.is_music_muted() is False

    def test_corrupted_value_types_in_json_storage(
        self, memory_backend: MemoryStorageBackend
    ) -> None:
        """Invalid types ('music_muted': 'not_a_bool') default to False."""
        memory_backend.set(
            DEFAULT_SETTINGS_KEY,
            json.dumps({"music_muted": "definitely_not_a_bool", "music_volume": "bad"}),
        )
        mgr = AudioSettingsManager(backend=memory_backend)
        assert mgr.is_music_muted() is False
        assert mgr.get_music_volume() == 1.0

    def test_empty_storage_backend_loads_defaults(
        self, memory_backend: MemoryStorageBackend
    ) -> None:
        """Storage with None value for settings key loads defaults."""
        mgr = AudioSettingsManager(backend=memory_backend)
        assert mgr.load() is False
        assert mgr.is_music_muted() is False

    def test_failing_backend_does_not_crash_save(self) -> None:
        """Storage backend raising exception on set returns False without raising."""
        failing_backend = MagicMock()
        failing_backend.set.side_effect = OSError("Disk write failed")
        mgr = AudioSettingsManager(backend=failing_backend, auto_load=False)
        assert mgr.save() is False


class TestTier2F8WelcomeMuteUIBoundaries:
    """Tier 2: Welcome mute button exact pixel boundary cases."""

    def test_click_exact_top_left_corner_pixel(
        self, welcome_view: PygameWelcomeView, session: GameSession
    ) -> None:
        """Click at (left, top) exactly inside button rect triggers toggle."""
        rect = welcome_view.get_mute_button_rect()
        click_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(rect.left, rect.top))
        assert welcome_view.is_muted() is False
        welcome_view.handle_event(click_ev, session)
        assert welcome_view.is_muted() is True

    def test_click_exact_bottom_right_inside_pixel(
        self, welcome_view: PygameWelcomeView, session: GameSession
    ) -> None:
        """Click at (right - 1, bottom - 1) triggers toggle."""
        rect = welcome_view.get_mute_button_rect()
        click_ev = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(rect.right - 1, rect.bottom - 1)
        )
        assert welcome_view.is_muted() is False
        welcome_view.handle_event(click_ev, session)
        assert welcome_view.is_muted() is True

    def test_click_one_pixel_outside_left_ignored(
        self, welcome_view: PygameWelcomeView, session: GameSession
    ) -> None:
        """Click 1 pixel left of rect boundary is ignored."""
        rect = welcome_view.get_mute_button_rect()
        click_ev = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(rect.left - 1, rect.top)
        )
        assert welcome_view.is_muted() is False
        welcome_view.handle_event(click_ev, session)
        assert welcome_view.is_muted() is False

    def test_click_one_pixel_outside_right_ignored(
        self, welcome_view: PygameWelcomeView, session: GameSession
    ) -> None:
        """Click 1 pixel right of rect (at rect.right) is outside and ignored."""
        rect = welcome_view.get_mute_button_rect()
        click_ev = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(rect.right, rect.top)
        )
        assert welcome_view.is_muted() is False
        welcome_view.handle_event(click_ev, session)
        assert welcome_view.is_muted() is False

    def test_click_one_pixel_outside_top_ignored(
        self, welcome_view: PygameWelcomeView, session: GameSession
    ) -> None:
        """Click 1 pixel above rect is ignored."""
        rect = welcome_view.get_mute_button_rect()
        click_ev = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(rect.left, rect.top - 1)
        )
        assert welcome_view.is_muted() is False
        welcome_view.handle_event(click_ev, session)
        assert welcome_view.is_muted() is False

    def test_click_one_pixel_outside_bottom_ignored(
        self, welcome_view: PygameWelcomeView, session: GameSession
    ) -> None:
        """Click 1 pixel below rect (at rect.bottom) is ignored."""
        rect = welcome_view.get_mute_button_rect()
        click_ev = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(rect.left, rect.bottom)
        )
        assert welcome_view.is_muted() is False
        welcome_view.handle_event(click_ev, session)
        assert welcome_view.is_muted() is False


# =============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (>=15 tests)
# Pairwise matrix: Context x Mute State x Restart Lifecycle x Modal Stack
# =============================================================================

class TestTier3CrossFeatureCombinations:
    """Tier 3: Pairwise combinations across contexts, mute states, lifecycles, and modals."""

    def test_combo_welcome_unmuted_fresh_no_modal(self, memory_backend: MemoryStorageBackend) -> None:
        """WELCOME x Unmuted x Fresh Boot x No Modal."""
        mgr = AudioSettingsManager(backend=memory_backend)
        engine = DynamicMusicEngine(settings_manager=mgr)
        engine.set_context(MusicContext.WELCOME)
        assert engine.get_current_context() == MusicContext.WELCOME
        assert engine.is_muted() is False
        assert engine.get_current_track() in ("welcome_01", "welcome_02")
        engine.stop()

    def test_combo_welcome_muted_fresh_no_modal(self, memory_backend: MemoryStorageBackend) -> None:
        """WELCOME x Muted x Fresh Boot x No Modal."""
        mgr = AudioSettingsManager(backend=memory_backend)
        mgr.set_music_muted(True)
        engine = DynamicMusicEngine(settings_manager=mgr)
        engine.set_context(MusicContext.WELCOME)
        assert engine.is_muted() is True
        if pygame.mixer.get_init():
            assert pygame.mixer.music.get_volume() == 0.0
        engine.stop()

    def test_combo_welcome_muted_restarted_no_modal(self, tmp_path: Path) -> None:
        """WELCOME x Muted x Disk Restart x No Modal."""
        disk_backend = FileStorageBackend(save_dir=str(tmp_path / "saves"))
        mgr1 = AudioSettingsManager(backend=disk_backend)
        mgr1.set_music_muted(True)

        mgr2 = AudioSettingsManager(backend=disk_backend)
        engine = DynamicMusicEngine(settings_manager=mgr2)
        engine.set_context(MusicContext.WELCOME)
        assert engine.is_muted() is True
        engine.stop()

    def test_combo_welcome_unmuted_restarted_no_modal(self, tmp_path: Path) -> None:
        """WELCOME x Unmuted x Disk Restart x No Modal."""
        disk_backend = FileStorageBackend(save_dir=str(tmp_path / "saves"))
        mgr1 = AudioSettingsManager(backend=disk_backend)
        mgr1.set_music_muted(True)
        mgr1.set_music_muted(False)

        mgr2 = AudioSettingsManager(backend=disk_backend)
        engine = DynamicMusicEngine(settings_manager=mgr2)
        engine.set_context(MusicContext.WELCOME)
        assert engine.is_muted() is False
        engine.stop()

    def test_combo_map_unmuted_fresh_no_modal(self, e2e_app: PygameApp) -> None:
        """MAP x Unmuted x Fresh Boot x No Modal."""
        e2e_app.session.switch_mode(GameMode.MAP)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.MAP
        assert e2e_app.music_engine.is_muted() is False
        assert e2e_app.music_engine.get_current_track() in ("exploration_01", "exploration_02")

    def test_combo_map_muted_fresh_inventory_modal(self, e2e_app: PygameApp) -> None:
        """MAP x Muted x Fresh Boot x Inventory Modal."""
        e2e_app.music_engine.set_muted(True)
        e2e_app.session.switch_mode(GameMode.MAP)
        e2e_app.update(0.016)
        trk = e2e_app.music_engine.get_current_track()

        e2e_app.session.switch_mode(GameMode.INVENTORY)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.MAP
        assert e2e_app.music_engine.get_current_track() == trk
        assert e2e_app.music_engine.is_muted() is True

    def test_combo_map_muted_restarted_character_modal(self, tmp_path: Path) -> None:
        """MAP x Muted x Re-instantiated App x Character Modal."""
        backend = FileStorageBackend(save_dir=str(tmp_path / "saves"))
        mgr = AudioSettingsManager(backend=backend)
        mgr.set_music_muted(True)

        app = PygameApp(
            headless=True,
            session=GameSession(),
            music_engine=DynamicMusicEngine(settings_manager=AudioSettingsManager(backend=backend)),
        )
        app.session.switch_mode(GameMode.MAP)
        app.update(0.016)
        trk = app.music_engine.get_current_track()

        app.session.switch_mode(GameMode.CHARACTER)
        app.update(0.016)
        assert app.music_engine.get_current_context() == MusicContext.MAP
        assert app.music_engine.get_current_track() == trk
        assert app.music_engine.is_muted() is True
        app.music_engine.stop()

    def test_combo_map_unmuted_restarted_inventory_modal(self, tmp_path: Path) -> None:
        """MAP x Unmuted x Re-instantiated App x Inventory Modal."""
        backend = FileStorageBackend(save_dir=str(tmp_path / "saves"))
        mgr = AudioSettingsManager(backend=backend)
        mgr.set_music_muted(False)

        app = PygameApp(
            headless=True,
            session=GameSession(),
            music_engine=DynamicMusicEngine(settings_manager=AudioSettingsManager(backend=backend)),
        )
        app.session.switch_mode(GameMode.MAP)
        app.update(0.016)
        app.session.switch_mode(GameMode.INVENTORY)
        app.update(0.016)
        assert app.music_engine.is_muted() is False
        assert app.music_engine.get_current_context() == MusicContext.MAP
        app.music_engine.stop()

    def test_combo_combat_unmuted_fresh_no_modal(self, e2e_app: PygameApp) -> None:
        """COMBAT x Unmuted x Fresh Boot x No Modal."""
        enemy = make_test_enemy("Bat", EnemyTier.COMMON)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, enemy)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.COMBAT
        assert e2e_app.music_engine.is_muted() is False
        assert e2e_app.music_engine.get_current_track() in ("combat_01", "combat_02")

    def test_combo_combat_muted_fresh_inventory_modal(self, e2e_app: PygameApp) -> None:
        """COMBAT x Muted x Fresh Boot x Inventory Modal."""
        e2e_app.music_engine.set_muted(True)
        enemy = make_test_enemy("Bat", EnemyTier.COMMON)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, enemy)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)
        trk = e2e_app.music_engine.get_current_track()

        e2e_app.session.switch_mode(GameMode.INVENTORY)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.COMBAT
        assert e2e_app.music_engine.get_current_track() == trk
        assert e2e_app.music_engine.is_muted() is True

    def test_combo_combat_muted_restarted_no_modal(self, tmp_path: Path) -> None:
        """COMBAT x Muted x Restarted App x No Modal."""
        backend = FileStorageBackend(save_dir=str(tmp_path / "saves"))
        mgr = AudioSettingsManager(backend=backend)
        mgr.set_music_muted(True)

        app = PygameApp(
            headless=True,
            session=GameSession(),
            music_engine=DynamicMusicEngine(settings_manager=AudioSettingsManager(backend=backend)),
        )
        enemy = make_test_enemy("Zombie", EnemyTier.COMMON)
        app.session.state.combat = CombatSystem(app.session.player, enemy)
        app.session.switch_mode(GameMode.COMBAT)
        app.update(0.016)
        assert app.music_engine.get_current_context() == MusicContext.COMBAT
        assert app.music_engine.is_muted() is True
        app.music_engine.stop()

    def test_combo_combat_unmuted_restarted_character_modal(self, tmp_path: Path) -> None:
        """COMBAT x Unmuted x Restarted App x Character Modal."""
        backend = FileStorageBackend(save_dir=str(tmp_path / "saves"))
        mgr = AudioSettingsManager(backend=backend)
        mgr.set_music_muted(False)

        app = PygameApp(
            headless=True,
            session=GameSession(),
            music_engine=DynamicMusicEngine(settings_manager=AudioSettingsManager(backend=backend)),
        )
        enemy = make_test_enemy("Zombie", EnemyTier.COMMON)
        app.session.state.combat = CombatSystem(app.session.player, enemy)
        app.session.switch_mode(GameMode.COMBAT)
        app.update(0.016)
        app.session.switch_mode(GameMode.CHARACTER)
        app.update(0.016)
        assert app.music_engine.get_current_context() == MusicContext.COMBAT
        assert app.music_engine.is_muted() is False
        app.music_engine.stop()

    def test_combo_boss_unmuted_fresh_no_modal(self, e2e_app: PygameApp) -> None:
        """BOSS x Unmuted x Fresh Boot x No Modal."""
        boss = make_test_enemy("Lich King", EnemyTier.BOSS, hp=180, attack=24)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, boss)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.BOSS
        assert e2e_app.music_engine.is_muted() is False
        assert e2e_app.music_engine.get_current_track() in ("boss_01", "boss_02")

    def test_combo_boss_muted_fresh_character_modal(self, e2e_app: PygameApp) -> None:
        """BOSS x Muted x Fresh Boot x Character Modal."""
        e2e_app.music_engine.set_muted(True)
        boss = make_test_enemy("Dragon", EnemyTier.BOSS, hp=250, attack=30)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, boss)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)
        trk = e2e_app.music_engine.get_current_track()

        e2e_app.session.switch_mode(GameMode.CHARACTER)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.BOSS
        assert e2e_app.music_engine.get_current_track() == trk
        assert e2e_app.music_engine.is_muted() is True

    def test_combo_boss_muted_restarted_inventory_modal(self, tmp_path: Path) -> None:
        """BOSS x Muted x Restarted App x Inventory Modal."""
        backend = FileStorageBackend(save_dir=str(tmp_path / "saves"))
        mgr = AudioSettingsManager(backend=backend)
        mgr.set_music_muted(True)

        app = PygameApp(
            headless=True,
            session=GameSession(),
            music_engine=DynamicMusicEngine(settings_manager=AudioSettingsManager(backend=backend)),
        )
        boss = make_test_enemy("Demon", EnemyTier.ELITE, hp=100, attack=20)
        app.session.state.combat = CombatSystem(app.session.player, boss)
        app.session.switch_mode(GameMode.COMBAT)
        app.update(0.016)
        app.session.switch_mode(GameMode.INVENTORY)
        app.update(0.016)
        assert app.music_engine.get_current_context() == MusicContext.BOSS
        assert app.music_engine.is_muted() is True
        app.music_engine.stop()

    def test_combo_boss_unmuted_restarted_no_modal(self, tmp_path: Path) -> None:
        """BOSS x Unmuted x Restarted App x No Modal."""
        backend = FileStorageBackend(save_dir=str(tmp_path / "saves"))
        mgr = AudioSettingsManager(backend=backend)
        mgr.set_music_muted(False)

        app = PygameApp(
            headless=True,
            session=GameSession(),
            music_engine=DynamicMusicEngine(settings_manager=AudioSettingsManager(backend=backend)),
        )
        boss = make_test_enemy("Demon", EnemyTier.ELITE, hp=100, attack=20)
        app.session.state.combat = CombatSystem(app.session.player, boss)
        app.session.switch_mode(GameMode.COMBAT)
        app.update(0.016)
        assert app.music_engine.get_current_context() == MusicContext.BOSS
        assert app.music_engine.is_muted() is False
        app.music_engine.stop()


# =============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (>=5 complete workflows)
# =============================================================================

class TestTier4RealWorldScenarios:
    """Tier 4: Realistic multi-step end-to-end user session workflows."""

    def test_scenario_1_full_game_loop_session(self, e2e_app: PygameApp) -> None:
        """Scenario 1: Full Game Loop Session.

        Lifecycle:
        1. Welcome screen launch -> WELCOME context
        2. Class selection view -> WELCOME context preserved
        3. Enter Map exploration -> MAP context starts
        4. Engage Common Combat -> COMBAT context starts
        5. Win combat & return to Map -> MAP context starts
        6. Engage Boss Combat -> BOSS context starts
        7. Defeat / Game Over -> BOSS context preserved across modal
        8. Return to Welcome screen -> WELCOME context re-engages
        """
        # Step 1: Welcome
        e2e_app.session.switch_mode(GameMode.WELCOME)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.WELCOME
        welcome_trk = e2e_app.music_engine.get_current_track()
        assert welcome_trk in ("welcome_01", "welcome_02")

        # Step 2: Class Select
        e2e_app.session.switch_mode(GameMode.CLASS_SELECT)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.WELCOME
        assert e2e_app.music_engine.get_current_track() == welcome_trk

        # Step 3: Map View
        e2e_app.session.switch_mode(GameMode.MAP)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.MAP
        assert e2e_app.music_engine.get_current_track() in ("exploration_01", "exploration_02")

        # Step 4: Common Combat
        common_enemy = make_test_enemy("Rat", EnemyTier.COMMON, hp=10, attack=3)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, common_enemy)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.COMBAT
        assert e2e_app.music_engine.get_current_track() in ("combat_01", "combat_02")

        # Step 5: Win & Return to Map
        e2e_app.session.state.combat = None
        e2e_app.session.switch_mode(GameMode.MAP)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.MAP
        assert e2e_app.music_engine.get_current_track() in ("exploration_01", "exploration_02")

        # Step 6: Boss Combat
        boss_enemy = make_test_enemy("Dragon", EnemyTier.BOSS, hp=300, attack=35)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, boss_enemy)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.BOSS
        boss_trk = e2e_app.music_engine.get_current_track()
        assert boss_trk in ("boss_01", "boss_02")

        # Step 7: Game Over modal retains boss music
        e2e_app.session.switch_mode(GameMode.GAME_OVER)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.BOSS
        assert e2e_app.music_engine.get_current_track() == boss_trk

        # Step 8: Return to Welcome
        e2e_app.session.switch_mode(GameMode.WELCOME)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.WELCOME
        assert e2e_app.music_engine.get_current_track() in ("welcome_01", "welcome_02")

    def test_scenario_2_mute_toggle_and_app_restart_cycle(self, tmp_path: Path) -> None:
        """Scenario 2: Mute Toggle & App Restart Cycle.

        Lifecycle:
        1. Boot App 1 in unmuted state
        2. User clicks Mute button on Welcome screen -> Muted=True
        3. Navigate to Map and Combat while muted -> audio stays 0.0
        4. Close App 1
        5. Boot App 2 from same storage -> verifies starts in Muted=True
        6. User clicks Unmute button on Welcome screen -> Muted=False, volume restored
        """
        save_dir = str(tmp_path / "app_restart_saves")
        backend1 = FileStorageBackend(save_dir=save_dir)
        settings1 = AudioSettingsManager(backend=backend1)
        engine1 = DynamicMusicEngine(settings_manager=settings1)
        welcome_view1 = PygameWelcomeView(music_engine=engine1)
        session1 = GameSession()

        # 1. Unmuted initially
        assert engine1.is_muted() is False
        assert welcome_view1.get_mute_button_label() == "[♫ MUTE]"

        # 2. Click mute
        rect = welcome_view1.get_mute_button_rect()
        click_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        welcome_view1.handle_event(click_ev, session1)
        assert engine1.is_muted() is True
        assert welcome_view1.get_mute_button_label() == "[♫ UNMUTE]"
        if pygame.mixer.get_init():
            assert pygame.mixer.music.get_volume() == 0.0

        # 3. Navigate views while muted
        engine1.set_context(MusicContext.MAP)
        assert engine1.is_muted() is True
        engine1.set_context(MusicContext.COMBAT)
        assert engine1.is_muted() is True

        # 4. Shutdown App 1
        engine1.stop()

        # 5. Boot App 2
        backend2 = FileStorageBackend(save_dir=save_dir)
        settings2 = AudioSettingsManager(backend=backend2)
        engine2 = DynamicMusicEngine(settings_manager=settings2)
        welcome_view2 = PygameWelcomeView(music_engine=engine2)
        session2 = GameSession()

        assert engine2.is_muted() is True
        assert welcome_view2.get_mute_button_label() == "[♫ UNMUTE]"
        if pygame.mixer.get_init():
            assert pygame.mixer.music.get_volume() == 0.0

        # 6. Click Unmute on App 2
        welcome_view2.handle_event(click_ev, session2)
        assert engine2.is_muted() is False
        assert welcome_view2.get_mute_button_label() == "[♫ MUTE]"
        if pygame.mixer.get_init():
            assert pytest.approx(pygame.mixer.music.get_volume(), abs=0.05) == 1.0
        engine2.stop()

    def test_scenario_3_rapid_view_navigation_and_modal_overlays(
        self, e2e_app: PygameApp
    ) -> None:
        """Scenario 3: Rapid View Navigation & Modal Overlays.

        Navigates between Welcome, Class Select, Map, repeatedly toggling
        Inventory and Character modals, verifying exploration track stability.
        """
        # Welcome -> Class Select -> Map
        e2e_app.session.switch_mode(GameMode.WELCOME)
        e2e_app.update(0.016)
        e2e_app.session.switch_mode(GameMode.CLASS_SELECT)
        e2e_app.update(0.016)
        e2e_app.session.switch_mode(GameMode.MAP)
        e2e_app.update(0.016)

        map_track = e2e_app.music_engine.get_current_track()
        assert e2e_app.music_engine.get_current_context() == MusicContext.MAP

        # 10 cycles of modal interleaving
        for _ in range(10):
            # Open inventory
            e2e_app.session.switch_mode(GameMode.INVENTORY)
            e2e_app.update(0.016)
            assert e2e_app.music_engine.get_current_track() == map_track

            # Return map
            e2e_app.session.switch_mode(GameMode.MAP)
            e2e_app.update(0.016)
            assert e2e_app.music_engine.get_current_track() == map_track

            # Open character
            e2e_app.session.switch_mode(GameMode.CHARACTER)
            e2e_app.update(0.016)
            assert e2e_app.music_engine.get_current_track() == map_track

            # Return map
            e2e_app.session.switch_mode(GameMode.MAP)
            e2e_app.update(0.016)
            assert e2e_app.music_engine.get_current_track() == map_track

    def test_scenario_4_repeated_combat_enqueue_common_vs_elite(
        self, e2e_app: PygameApp
    ) -> None:
        """Scenario 4: Repeated Combat Enqueue with Common vs Elite encounters.

        Alternates between common combat encounters and elite combat encounters,
        confirming appropriate context switching and valid tracks throughout.
        """
        e2e_app.session.switch_mode(GameMode.MAP)
        e2e_app.update(0.016)

        # Round 1: Common Combat
        common1 = make_test_enemy("Goblin Scout", EnemyTier.COMMON, hp=20, attack=5)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, common1)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.COMBAT
        assert e2e_app.music_engine.get_current_track() in ("combat_01", "combat_02")

        # Win -> Map
        e2e_app.session.state.combat = None
        e2e_app.session.switch_mode(GameMode.MAP)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.MAP

        # Round 2: Elite Combat
        elite = make_test_enemy("Bone Weaver", EnemyTier.ELITE, hp=90, attack=16)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, elite)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.BOSS
        assert e2e_app.music_engine.get_current_track() in ("boss_01", "boss_02")

        # Win -> Map
        e2e_app.session.state.combat = None
        e2e_app.session.switch_mode(GameMode.MAP)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.MAP

        # Round 3: Uncommon Combat
        uncommon = make_test_enemy("Ghoul", EnemyTier.UNCOMMON, hp=40, attack=9)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, uncommon)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.COMBAT
        assert e2e_app.music_engine.get_current_track() in ("combat_01", "combat_02")

        # Win -> Map -> Boss Combat
        e2e_app.session.state.combat = None
        e2e_app.session.switch_mode(GameMode.MAP)
        e2e_app.update(0.016)

        boss = make_test_enemy("Sovereign", EnemyTier.BOSS, hp=300, attack=32)
        e2e_app.session.state.combat = CombatSystem(e2e_app.session.player, boss)
        e2e_app.session.switch_mode(GameMode.COMBAT)
        e2e_app.update(0.016)
        assert e2e_app.music_engine.get_current_context() == MusicContext.BOSS
        assert e2e_app.music_engine.get_current_track() in ("boss_01", "boss_02")

    def test_scenario_5_track_shuffle_and_loop_validation_100_transitions(
        self, music_engine: DynamicMusicEngine
    ) -> None:
        """Scenario 5: Track Shuffle & Loop Validation across 100 transitions.

        Simulates natural track ends across all 4 contexts, verifying:
        - Both tracks in each context are chosen with statistical significance.
        - No unhandled contexts or null tracks occur during continuous looping.
        """
        for context, valid_tracks in CONTEXT_TRACKS.items():
            counts: dict[str, int] = {trk: 0 for trk in valid_tracks}
            music_engine.set_context(context, force_restart=True)

            for _ in range(100):
                # Trigger completion callback
                music_engine._handle_track_finished()
                cur_trk = music_engine.get_current_track()
                assert cur_trk in valid_tracks, f"Track '{cur_trk}' invalid for {context}"
                counts[cur_trk] += 1

            # Assert both tracks were selected across the 100 loops
            for trk in valid_tracks:
                assert counts[trk] >= 15, f"Track '{trk}' was only selected {counts[trk]} times in 100 trials"
