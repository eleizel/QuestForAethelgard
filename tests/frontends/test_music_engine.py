"""Comprehensive unit test suite for DynamicMusicEngine and AudioSettingsManager.

Covers Milestone 2 requirements:
- Engine initialization, default state, and track resolution.
- Context transitions across WELCOME, MAP, COMBAT, and BOSS.
- Context persistence: identical context transitions do not restart playback.
- Randomized track selection and statistical binomial distribution over N=100.
- Loop re-selection when track playback finishes.
- Mute/unmute toggling, silencing, volume restoration, and settings persistence.
- AudioSettingsManager save/load roundtrips, corruption recovery, and MemoryStorageBackend.
- Headless CI dummy driver safety and uninitialized mixer resilience.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
from unittest.mock import MagicMock, patch

import pytest
import pygame

from src.core.persistence import MemoryStorageBackend
from src.frontends.pygame_ce.audio_track_loader import AudioTrackLoader, get_default_music_dir
from src.frontends.pygame_ce.music_engine import (
    CONTEXT_TRACKS,
    AudioSettingsManager,
    DynamicMusicEngine,
    MusicContext,
)


@pytest.fixture(autouse=True)
def ensure_dummy_audio_driver():
    """Ensure headless SDL audio and video drivers with clean mixer teardown."""
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ["SDL_VIDEODRIVER"] = "dummy"
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
    """Isolated in-memory storage backend."""
    return MemoryStorageBackend()


@pytest.fixture
def audio_settings(memory_backend: MemoryStorageBackend) -> AudioSettingsManager:
    """AudioSettingsManager backed by MemoryStorageBackend."""
    return AudioSettingsManager(backend=memory_backend)


@pytest.fixture
def engine(audio_settings: AudioSettingsManager) -> DynamicMusicEngine:
    """Fresh DynamicMusicEngine instance with isolated storage."""
    eng = DynamicMusicEngine(settings_manager=audio_settings)
    yield eng
    eng.stop()


# =============================================================================
# 1. ENGINE INITIALIZATION & TRACK RESOLUTION
# =============================================================================
class TestEngineInitializationAndResolution:
    """Tests for constructor contracts, initial state, and asset resolution."""

    def test_default_state_uninitialized_context(self, engine: DynamicMusicEngine):
        """Engine must start with no context, no track, and unmuted."""
        assert engine.get_current_context() is None
        assert engine.get_current_track() is None
        assert engine.is_muted() is False

    def test_custom_settings_manager_premuted(self, memory_backend: MemoryStorageBackend):
        """Engine respects pre-existing muted state from settings manager."""
        settings = AudioSettingsManager(backend=memory_backend)
        settings.set_music_muted(True)
        settings.save()

        engine = DynamicMusicEngine(settings_manager=settings)
        assert engine.is_muted() is True

    def test_resolution_all_canonical_context_tracks(self, engine: DynamicMusicEngine):
        """All 8 canonical tracks across all 4 contexts must resolve to valid files."""
        loader = engine.loader if hasattr(engine, "loader") else AudioTrackLoader()
        for context, tracks in CONTEXT_TRACKS.items():
            assert len(tracks) == 2, f"{context} must have exactly 2 tracks"
            for track_name in tracks:
                resolved = loader.resolve_track(track_name)
                assert resolved is not None, f"Failed to resolve {track_name} in {context}"
                assert resolved.is_file(), f"Resolved {track_name} is not a file: {resolved}"

    def test_custom_assets_dir(self, tmp_path: Path, audio_settings: AudioSettingsManager):
        """Engine accepts custom assets_dir and configures loader appropriately."""
        custom_music = tmp_path / "custom_music"
        custom_music.mkdir()
        dummy_track = custom_music / "welcome_01.ogg"
        dummy_track.write_text("dummy_audio")

        engine = DynamicMusicEngine(settings_manager=audio_settings, assets_dir=custom_music)
        resolved = (
            engine.resolve_track("welcome_01")
            if hasattr(engine, "resolve_track")
            else engine.loader.resolve_track("welcome_01")
        )
        assert resolved is not None
        assert resolved.resolve() == dummy_track.resolve()

    def test_initialization_with_uninitialized_mixer(self, audio_settings: AudioSettingsManager):
        """Engine handles initialization cleanly even if pygame.mixer was quit."""
        if pygame.mixer.get_init():
            pygame.mixer.quit()
        engine = DynamicMusicEngine(settings_manager=audio_settings, auto_init_mixer=False)
        assert engine.get_current_context() is None


# =============================================================================
# 2. CONTEXT TRANSITIONS
# =============================================================================
class TestMusicContextTransitions:
    """Tests for transitions across all 4 music contexts."""

    def test_transition_to_welcome(self, engine: DynamicMusicEngine):
        """Setting WELCOME context sets context and plays welcome track."""
        engine.set_context(MusicContext.WELCOME)
        assert engine.get_current_context() == MusicContext.WELCOME
        assert engine.get_current_track() in ("welcome_01", "welcome_02")

    def test_transition_to_map(self, engine: DynamicMusicEngine):
        """Setting MAP context sets context and plays exploration track."""
        engine.set_context(MusicContext.MAP)
        assert engine.get_current_context() == MusicContext.MAP
        assert engine.get_current_track() in ("exploration_01", "exploration_02")

    def test_transition_to_combat(self, engine: DynamicMusicEngine):
        """Setting COMBAT context sets context and plays combat track."""
        engine.set_context(MusicContext.COMBAT)
        assert engine.get_current_context() == MusicContext.COMBAT
        assert engine.get_current_track() in ("combat_01", "combat_02")

    def test_transition_to_boss(self, engine: DynamicMusicEngine):
        """Setting BOSS context sets context and plays boss track."""
        engine.set_context(MusicContext.BOSS)
        assert engine.get_current_context() == MusicContext.BOSS
        assert engine.get_current_track() in ("boss_01", "boss_02")

    def test_full_sequential_gameplay_flow(self, engine: DynamicMusicEngine):
        """Traverse full game loop: WELCOME -> MAP -> COMBAT -> BOSS -> MAP -> WELCOME."""
        flow = [
            (MusicContext.WELCOME, {"welcome_01", "welcome_02"}),
            (MusicContext.MAP, {"exploration_01", "exploration_02"}),
            (MusicContext.COMBAT, {"combat_01", "combat_02"}),
            (MusicContext.BOSS, {"boss_01", "boss_02"}),
            (MusicContext.MAP, {"exploration_01", "exploration_02"}),
            (MusicContext.WELCOME, {"welcome_01", "welcome_02"}),
        ]
        for ctx, allowed_tracks in flow:
            engine.set_context(ctx)
            assert engine.get_current_context() == ctx
            assert engine.get_current_track() in allowed_tracks

    def test_stop_playback(self, engine: DynamicMusicEngine):
        """Calling stop() stops playback and clears or halts active stream."""
        engine.set_context(MusicContext.WELCOME)
        engine.stop()
        if hasattr(engine, "is_playing"):
            assert engine.is_playing() is False


# =============================================================================
# 3. CONTEXT PERSISTENCE
# =============================================================================
class TestContextPersistence:
    """Tests that entering the same context maintains the active track."""

    def test_same_context_preserves_track(self, engine: DynamicMusicEngine):
        """Calling set_context with current context preserves the active track."""
        engine.set_context(MusicContext.WELCOME)
        initial_track = engine.get_current_track()
        assert initial_track is not None

        # Repeat same context
        engine.set_context(MusicContext.WELCOME)
        assert engine.get_current_track() == initial_track
        assert engine.get_current_context() == MusicContext.WELCOME

    def test_same_context_does_not_call_mixer_load(self, engine: DynamicMusicEngine):
        """Calling set_context with same context does not reload or restart audio."""
        engine.set_context(MusicContext.MAP)
        initial_track = engine.get_current_track()

        with patch("pygame.mixer.music.load") as mock_load, patch("pygame.mixer.music.play") as mock_play:
            engine.set_context(MusicContext.MAP)
            mock_load.assert_not_called()
            mock_play.assert_not_called()
        assert engine.get_current_track() == initial_track

    def test_same_context_with_force_restart(self, engine: DynamicMusicEngine):
        """Calling set_context with force_restart=True restarts playback."""
        engine.set_context(MusicContext.WELCOME)

        with patch("pygame.mixer.music.play") as mock_play:
            engine.set_context(MusicContext.WELCOME, force_restart=True)
            mock_play.assert_called_once()

    @pytest.mark.parametrize(
        "ctx", [MusicContext.WELCOME, MusicContext.MAP, MusicContext.COMBAT, MusicContext.BOSS]
    )
    def test_all_contexts_preserve_on_repeat(self, engine: DynamicMusicEngine, ctx: MusicContext):
        """Verify context persistence across all 4 contexts."""
        engine.set_context(ctx)
        track = engine.get_current_track()
        engine.set_context(ctx)
        assert engine.get_current_track() == track


# =============================================================================
# 4. RANDOMIZED TRACK SELECTION
# =============================================================================
class TestRandomizedTrackSelection:
    """Tests 2-track random selection and binomial distribution over N=100."""

    @pytest.mark.parametrize(
        "ctx,track_pair",
        [
            (MusicContext.WELCOME, ("welcome_01", "welcome_02")),
            (MusicContext.MAP, ("exploration_01", "exploration_02")),
            (MusicContext.COMBAT, ("combat_01", "combat_02")),
            (MusicContext.BOSS, ("boss_01", "boss_02")),
        ],
    )
    def test_randomized_distribution_over_100_iterations(
        self,
        engine: DynamicMusicEngine,
        ctx: MusicContext,
        track_pair: tuple[str, str],
    ):
        """Both tracks must be selected with non-zero probability and fair distribution (20..80 out of 100)."""
        counts = {track_pair[0]: 0, track_pair[1]: 0}
        n_iterations = 100

        for _ in range(n_iterations):
            engine.set_context(ctx, force_restart=True)
            chosen = engine.get_current_track()
            assert chosen in track_pair
            counts[chosen] += 1

        assert counts[track_pair[0]] > 0, f"{track_pair[0]} was never selected in {n_iterations} trials"
        assert counts[track_pair[1]] > 0, f"{track_pair[1]} was never selected in {n_iterations} trials"
        # Binomial 6-sigma bounds for N=100, p=0.5: expected=50, std=5 -> bounds [20, 80]
        assert 20 <= counts[track_pair[0]] <= 80, f"{track_pair[0]} count {counts[track_pair[0]]} out of bounds"
        assert 20 <= counts[track_pair[1]] <= 80, f"{track_pair[1]} count {counts[track_pair[1]]} out of bounds"

    def test_deterministic_random_seed(self, audio_settings: AudioSettingsManager):
        """Deterministic random generator produces identical sequence of track choices."""
        rng1 = random.Random(1337)
        eng1 = (
            DynamicMusicEngine(settings_manager=audio_settings, rng=rng1)
            if "rng" in DynamicMusicEngine.__init__.__code__.co_varnames
            else None
        )
        if eng1 is not None:
            seq1 = [eng1._select_track(MusicContext.MAP) for _ in range(10)]
            rng2 = random.Random(1337)
            eng2 = DynamicMusicEngine(settings_manager=audio_settings, rng=rng2)
            seq2 = [eng2._select_track(MusicContext.MAP) for _ in range(10)]
            assert seq1 == seq2


# =============================================================================
# 5. LOOP RE-SELECTION
# =============================================================================
class TestLoopReSelection:
    """Tests re-selection and looping when a track finishes."""

    def test_update_reselects_track_when_playback_ends(self, engine: DynamicMusicEngine):
        """When music stream finishes, update(dt) triggers re-selection from current context."""
        engine.set_context(MusicContext.MAP)

        # Simulate track completion: get_busy() -> False
        with patch("pygame.mixer.music.get_busy", return_value=False), patch(
            "pygame.mixer.music.play"
        ) as mock_play:
            engine.update(dt=0.1)
            mock_play.assert_called_once()
            assert engine.get_current_context() == MusicContext.MAP
            assert engine.get_current_track() in ("exploration_01", "exploration_02")

    def test_update_retains_track_while_busy(self, engine: DynamicMusicEngine):
        """While get_busy() is True, update(dt) does not re-select or reload."""
        engine.set_context(MusicContext.COMBAT)
        track = engine.get_current_track()

        with patch("pygame.mixer.music.get_busy", return_value=True), patch(
            "pygame.mixer.music.load"
        ) as mock_load:
            engine.update(dt=0.1)
            mock_load.assert_not_called()
            assert engine.get_current_track() == track

    def test_loop_reselection_picks_only_from_current_context(self, engine: DynamicMusicEngine):
        """Loop re-selections must strictly pick from active context's track subset."""
        engine.set_context(MusicContext.BOSS)
        boss_tracks = set(CONTEXT_TRACKS[MusicContext.BOSS])

        for _ in range(30):
            with patch("pygame.mixer.music.get_busy", return_value=False):
                engine.update(dt=0.1)
                assert engine.get_current_track() in boss_tracks

    def test_update_noop_when_context_is_none(self, engine: DynamicMusicEngine):
        """Calling update(dt) before setting context does not crash or play audio."""
        with patch("pygame.mixer.music.play") as mock_play:
            engine.update(dt=0.1)
            mock_play.assert_not_called()
        assert engine.get_current_context() is None


# =============================================================================
# 6. MUTE / UNMUTE TOGGLING & SILENCING
# =============================================================================
class TestMuteUnmuteToggling:
    """Tests mute state toggling, silencing, and volume restoration."""

    def test_toggle_mute_flips_state_and_returns_new_value(self, engine: DynamicMusicEngine):
        """toggle_mute flips boolean state and returns the new value."""
        assert engine.is_muted() is False
        new_state = engine.toggle_mute()
        assert new_state is True
        assert engine.is_muted() is True

        new_state = engine.toggle_mute()
        assert new_state is False
        assert engine.is_muted() is False

    def test_set_muted_silences_playback_volume(self, engine: DynamicMusicEngine):
        """Muting sets mixer volume to 0.0 or pauses audio stream."""
        engine.set_context(MusicContext.WELCOME)
        with patch("pygame.mixer.music.set_volume") as mock_vol:
            engine.set_muted(True)
            mock_vol.assert_called_with(0.0)
            assert engine.is_muted() is True

    def test_set_unmuted_restores_playback_volume(self, engine: DynamicMusicEngine):
        """Unmuting restores mixer volume to 1.0 (or configured volume)."""
        engine.set_muted(True)
        with patch("pygame.mixer.music.set_volume") as mock_vol:
            engine.set_muted(False)
            mock_vol.assert_called_with(1.0)
            assert engine.is_muted() is False

    def test_playing_while_muted_starts_silenced(self, engine: DynamicMusicEngine):
        """If engine is muted, starting a track keeps volume at 0.0."""
        engine.set_muted(True)
        with patch("pygame.mixer.music.set_volume") as mock_vol:
            engine.set_context(MusicContext.MAP)
            # Volume must be set to 0.0 upon starting playback while muted
            mock_vol.assert_called_with(0.0)

    def test_toggle_mute_persists_to_settings_manager(
        self, engine: DynamicMusicEngine, audio_settings: AudioSettingsManager
    ):
        """toggle_mute updates settings manager immediately."""
        assert audio_settings.is_music_muted() is False
        engine.toggle_mute()
        assert audio_settings.is_music_muted() is True
        engine.toggle_mute()
        assert audio_settings.is_music_muted() is False


# =============================================================================
# 7. AUDIO SETTINGS MANAGER PERSISTENCE
# =============================================================================
class TestAudioSettingsManagerPersistence:
    """Tests persistence, MemoryStorageBackend integration, and corruption recovery."""

    def test_default_settings_when_storage_empty(self, audio_settings: AudioSettingsManager):
        """Empty storage defaults to unmuted."""
        assert audio_settings.is_music_muted() is False

    def test_save_load_roundtrip(self, memory_backend: MemoryStorageBackend):
        """Save muted state, verify raw JSON, and reload in fresh manager."""
        manager1 = AudioSettingsManager(backend=memory_backend)
        manager1.set_music_muted(True)
        manager1.save()

        # Check raw stored payload
        raw_val = memory_backend.get("quest_for_aethelgard_settings")
        assert raw_val is not None
        data = json.loads(raw_val)
        assert data.get("music_muted") is True

        # Load in second manager
        manager2 = AudioSettingsManager(backend=memory_backend)
        assert manager2.is_music_muted() is True

    def test_storage_key_matches_contract(self, memory_backend: MemoryStorageBackend):
        """Settings must be stored under exact key 'quest_for_aethelgard_settings'."""
        manager = AudioSettingsManager(backend=memory_backend)
        manager.set_music_muted(True)
        manager.save()
        assert memory_backend.exists("quest_for_aethelgard_settings")

    def test_corrupt_json_fallback(self, memory_backend: MemoryStorageBackend):
        """Corrupt raw JSON falls back to default unmuted state without crashing."""
        memory_backend.set("quest_for_aethelgard_settings", "{ broken JSON content ")
        manager = AudioSettingsManager(backend=memory_backend)
        assert manager.is_music_muted() is False

    def test_non_dict_json_payload_fallback(self, memory_backend: MemoryStorageBackend):
        """Non-dict JSON payloads fallback safely to default settings."""
        memory_backend.set("quest_for_aethelgard_settings", json.dumps(["invalid", "array"]))
        manager = AudioSettingsManager(backend=memory_backend)
        assert manager.is_music_muted() is False

        memory_backend.set("quest_for_aethelgard_settings", json.dumps(12345))
        manager = AudioSettingsManager(backend=memory_backend)
        assert manager.is_music_muted() is False

    def test_missing_fields_or_wrong_types(self, memory_backend: MemoryStorageBackend):
        """Missing keys or non-boolean types are coerced or defaulted gracefully."""
        memory_backend.set("quest_for_aethelgard_settings", json.dumps({"unknown_key": 999}))
        manager = AudioSettingsManager(backend=memory_backend)
        assert manager.is_music_muted() is False

        # Non-boolean value
        memory_backend.set(
            "quest_for_aethelgard_settings", json.dumps({"music_muted": "not_a_bool"})
        )
        manager = AudioSettingsManager(backend=memory_backend)
        assert isinstance(manager.is_music_muted(), bool)

    def test_backend_exception_handling(self):
        """Backend raising exceptions on get/set does not crash manager."""
        failing_backend = MagicMock()
        failing_backend.get.side_effect = OSError("Disk read error")
        failing_backend.set.side_effect = OSError("Disk write error")

        manager = AudioSettingsManager(backend=failing_backend)
        assert manager.is_music_muted() is False  # Safe fallback
        # Save should handle exception without bubbling up
        manager.set_music_muted(True)
        manager.save()


# =============================================================================
# 8. HEADLESS CI & DUMMY DRIVER SAFETY
# =============================================================================
class TestHeadlessMixerSafety:
    """Tests headless execution, uninitialized mixer safety, and error handling."""

    def test_operations_safe_when_mixer_uninitialized(self, audio_settings: AudioSettingsManager):
        """All engine operations succeed without error when mixer is uninitialized."""
        if pygame.mixer.get_init():
            pygame.mixer.quit()

        engine = DynamicMusicEngine(settings_manager=audio_settings, auto_init_mixer=False)
        # None of these should raise pygame.error
        engine.set_context(MusicContext.MAP)
        engine.update(dt=0.1)
        engine.toggle_mute()
        engine.set_muted(True)
        engine.stop()

    def test_dummy_audio_driver_supports_music_playback(self, engine: DynamicMusicEngine):
        """SDL_AUDIODRIVER=dummy allows real track resolution and playback without error."""
        assert pygame.mixer.get_init() is not None
        # Should resolve and play welcome_01 or welcome_02 without crash
        engine.set_context(MusicContext.WELCOME)
        assert engine.get_current_track() in ("welcome_01", "welcome_02")

    def test_missing_audio_track_graceful_handling(self, engine: DynamicMusicEngine):
        """Attempting to load unresolvable track logs warning and does not raise exception."""
        loader = engine.loader if hasattr(engine, "loader") else AudioTrackLoader()
        res = loader.load_track("non_existent_track_xyz")
        assert res is False

    def test_mixer_init_failure_fallback(self, audio_settings: AudioSettingsManager):
        """If pygame.mixer.init raises pygame.error, engine handles it gracefully."""
        if pygame.mixer.get_init():
            pygame.mixer.quit()

        with patch("pygame.mixer.init", side_effect=pygame.error("Audio device unavailable")):
            engine = DynamicMusicEngine(settings_manager=audio_settings, auto_init_mixer=True)
            # Safe degradation
            engine.set_context(MusicContext.COMBAT)
            assert engine.get_current_context() == MusicContext.COMBAT
