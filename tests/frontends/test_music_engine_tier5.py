"""Tier 5 Adversarial Coverage and Robustness Test Suite for Music Engine & Track Loader.

Milestone 4 Phase 2 Challenger 1:
Exhaustive white-box hardening targeting edge conditions, error handling,
security boundaries, concurrency, and lifecycle state transitions across:
- src/frontends/pygame_ce/audio_track_loader.py
- src/frontends/pygame_ce/music_engine.py
"""

from __future__ import annotations

from collections import OrderedDict
import math
import os
from pathlib import Path
import random
import sys
import threading
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import pygame

from src.core.game_state import GameMode
from src.core.persistence import MemoryStorageBackend
from src.entities.enemy import EnemyTier
from src.frontends.pygame_ce.audio_track_loader import (
    DEFAULT_AUDIO_EXTENSIONS,
    DEFAULT_MAX_CACHE_SIZE,
    DOS_DEVICES,
    AudioTrackLoader,
    get_default_music_dir,
    is_audio_available,
    load_audio_track,
    resolve_audio_track,
)
from src.frontends.pygame_ce.music_engine import (
    CONTEXT_TRACKS,
    DEFAULT_SETTINGS_KEY,
    SETTINGS_SCHEMA_VERSION,
    AudioSettingsData,
    AudioSettingsManager,
    DynamicMusicEngine,
    MusicContext,
    PlaybackState,
    resolve_music_context,
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
    """Isolated memory storage backend."""
    return MemoryStorageBackend()


@pytest.fixture
def audio_settings(memory_backend: MemoryStorageBackend) -> AudioSettingsManager:
    """Isolated AudioSettingsManager."""
    return AudioSettingsManager(backend=memory_backend)


@pytest.fixture
def engine(audio_settings: AudioSettingsManager) -> DynamicMusicEngine:
    """Fresh DynamicMusicEngine with isolated storage."""
    eng = DynamicMusicEngine(settings_manager=audio_settings)
    yield eng
    eng.stop()


# =============================================================================
# PART 1: AUDIO TRACK LOADER ADVERSARIAL COVERAGE
# =============================================================================


class TestTier5LoaderDiscoveryAndPaths:
    """White-box tests for get_default_music_dir and candidate discovery."""

    def test_get_default_music_dir_pyinstaller_frozen_found(self, tmp_path: Path):
        """Simulate PyInstaller single-file bundle with existing assets/music in _MEIPASS."""
        fake_meipass = tmp_path / "_MEIPASS_dir"
        meipass_music = fake_meipass / "assets" / "music"
        meipass_music.mkdir(parents=True)

        with patch.object(sys, "frozen", True, create=True), patch.object(
            sys, "_MEIPASS", str(fake_meipass), create=True
        ):
            discovered = get_default_music_dir()
            assert discovered == meipass_music

    def test_get_default_music_dir_pyinstaller_frozen_missing_falls_through(self, tmp_path: Path):
        """If _MEIPASS exists but assets/music is missing, fall through to source tree."""
        fake_meipass = tmp_path / "_MEIPASS_empty"
        fake_meipass.mkdir()

        with patch.object(sys, "frozen", True, create=True), patch.object(
            sys, "_MEIPASS", str(fake_meipass), create=True
        ):
            discovered = get_default_music_dir()
            assert discovered.name == "music"

    def test_get_default_music_dir_cwd_fallback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """When source tree assets/music is not found, discover CWD assets/music."""
        fake_cwd = tmp_path / "app_cwd"
        cwd_music = fake_cwd / "assets" / "music"
        cwd_music.mkdir(parents=True)
        monkeypatch.chdir(fake_cwd)

        fake_src_file = tmp_path / "fake_src" / "frontends" / "pygame_ce" / "audio_track_loader.py"
        fake_src_file.parent.mkdir(parents=True)
        fake_src_file.write_text("# dummy")

        with patch("src.frontends.pygame_ce.audio_track_loader.__file__", str(fake_src_file)):
            discovered = get_default_music_dir()
            assert discovered.resolve() == cwd_music.resolve()



class TestTier5LoaderExtensionNormalizationAndConfig:
    """Tests for extensions normalization, cache clamping, and priority order."""

    def test_extension_normalization_without_leading_dots(self):
        """Extensions passed without leading dot must be normalized with a leading dot."""
        loader = AudioTrackLoader(extensions=["ogg", "mp3", ".wav"], auto_init_mixer=False)
        assert loader.extensions == (".ogg", ".mp3", ".wav")

    def test_max_cache_size_clamping(self):
        """Non-positive max_cache_size values must be clamped to at least 1."""
        loader_zero = AudioTrackLoader(max_cache_size=0, auto_init_mixer=False)
        assert loader_zero._max_cache_size == 1

        loader_neg = AudioTrackLoader(max_cache_size=-50, auto_init_mixer=False)
        assert loader_neg._max_cache_size == 1

    def test_custom_music_dir_has_highest_search_priority(self, tmp_path: Path):
        """Custom music directory must appear first in search directories list."""
        custom_dir = tmp_path / "custom_prio"
        custom_dir.mkdir()
        loader = AudioTrackLoader(music_dir=custom_dir, auto_init_mixer=False)
        search_dirs = loader.get_search_directories()
        assert len(search_dirs) >= 1
        assert search_dirs[0].resolve() == custom_dir.resolve()


class TestTier5LoaderLruCacheAndEviction:
    """White-box tests for AudioTrackLoader LRU cache mechanics and negative caching."""

    def test_lru_cache_eviction_when_capacity_reached(self, tmp_path: Path):
        """LRU cache with capacity 2 must evict the least recently used entry."""
        music_dir = tmp_path / "music_lru"
        music_dir.mkdir()
        (music_dir / "track_a.ogg").write_text("a")
        (music_dir / "track_b.ogg").write_text("b")
        (music_dir / "track_c.ogg").write_text("c")

        loader = AudioTrackLoader(music_dir=music_dir, max_cache_size=2, auto_init_mixer=False)

        # 1. Query track_a, then track_b
        res_a = loader.resolve_track("track_a")
        res_b = loader.resolve_track("track_b")
        assert res_a is not None and res_b is not None
        assert "track_a" in loader._cache
        assert "track_b" in loader._cache
        assert len(loader._cache) == 2

        # 2. Query track_c -> track_a should be evicted
        res_c = loader.resolve_track("track_c")
        assert res_c is not None
        assert "track_a" not in loader._cache
        assert "track_b" in loader._cache
        assert "track_c" in loader._cache
        assert len(loader._cache) == 2

    def test_lru_cache_access_refresh_prevents_eviction(self, tmp_path: Path):
        """Accessing track_a refreshes its recency, so track_b is evicted instead."""
        music_dir = tmp_path / "music_lru_refresh"
        music_dir.mkdir()
        (music_dir / "track_a.ogg").write_text("a")
        (music_dir / "track_b.ogg").write_text("b")
        (music_dir / "track_c.ogg").write_text("c")

        loader = AudioTrackLoader(music_dir=music_dir, max_cache_size=2, auto_init_mixer=False)

        loader.resolve_track("track_a")
        loader.resolve_track("track_b")

        # Refresh track_a by accessing it again
        hit, val = loader._get_from_cache("track_a")
        assert hit is True and val is not None

        # Add track_c -> track_b should now be evicted
        loader.resolve_track("track_c")
        assert "track_a" in loader._cache
        assert "track_c" in loader._cache
        assert "track_b" not in loader._cache

    def test_negative_caching_for_nonexistent_tracks(self, tmp_path: Path):
        """Resolving a non-existent track caches None to prevent repeated disk queries."""
        music_dir = tmp_path / "empty_dir"
        music_dir.mkdir()
        loader = AudioTrackLoader(music_dir=music_dir, auto_init_mixer=False)

        res = loader.resolve_track("missing_track")
        assert res is None
        assert "missing_track" in loader._cache
        assert loader._cache["missing_track"] is None

        # Subsequent retrieval hits cache
        hit, cached_val = loader._get_from_cache("missing_track")
        assert hit is True
        assert cached_val is None

    def test_clear_cache_flushes_all_entries(self, tmp_path: Path):
        """clear_cache() must completely empty the resolution cache."""
        music_dir = tmp_path / "music_clear"
        music_dir.mkdir()
        (music_dir / "test.ogg").write_text("audio")
        loader = AudioTrackLoader(music_dir=music_dir, auto_init_mixer=False)

        loader.resolve_track("test")
        loader.resolve_track("missing")
        assert len(loader._cache) == 2

        loader.clear_cache()
        assert len(loader._cache) == 0


class TestTier5LoaderConcurrentCacheStress:
    """Stress-test thread safety of AudioTrackLoader cache under concurrent access."""

    def test_multithreaded_concurrent_cache_queries(self, tmp_path: Path):
        """10 threads concurrently resolving tracks must not trigger race conditions or corruption."""
        music_dir = tmp_path / "music_concurrent"
        music_dir.mkdir()
        for i in range(10):
            (music_dir / f"track_{i}.ogg").write_text("data")

        loader = AudioTrackLoader(music_dir=music_dir, max_cache_size=8, auto_init_mixer=False)
        errors: list[Exception] = []

        def worker(thread_id: int):
            try:
                rng = random.Random(thread_id)
                for _ in range(50):
                    idx = rng.randint(0, 15)  # some exist, some don't
                    loader.resolve_track(f"track_{idx}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent cache access failed with errors: {errors}"
        assert len(loader._cache) <= loader._max_cache_size


class TestTier5LoaderSecurityAndPathTraversals:
    """Adversarial input hardening against malicious track identifiers."""

    @pytest.mark.parametrize(
        "malicious_input",
        [
            None,
            123,
            ["not", "a", "path"],
            {"key": "val"},
            "",
            "   ",
            "\t\n",
            "welcome_01\x00.ogg",
            r"welcome_01\x00extra",
            "//malicious-server/share/audio.ogg",
            r"\\malicious-server\share\audio.ogg",
            "../outside.ogg",
            r"..\outside.ogg",
            "sub/../../outside.ogg",
            "assets/../../../root.ogg",
            "con",
            "con.ogg",
            "prn",
            "aux",
            "nul",
            "com1",
            "com9",
            "lpt1",
            "lpt9",
            "CON.WAV",
            "NUL.mp3",
        ],
    )
    def test_malicious_or_invalid_track_inputs_return_none(
        self,
        malicious_input: Any,
    ):
        """All invalid, traversal, UNC, null-byte, and DOS device tracks return None safely."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        result = loader.resolve_track(malicious_input)
        assert result is None


class TestTier5LoaderBoundaryAndContainment:
    """Tests ensuring file resolution strictly respects directory containment and case-insensitivity."""

    def test_file_outside_search_directories_is_rejected(self, tmp_path: Path):
        """Direct absolute path to a file outside search directories must return None."""
        outside_dir = tmp_path / "outside_dir"
        outside_dir.mkdir()
        outside_file = outside_dir / "secret.ogg"
        outside_file.write_text("secret_audio")

        inside_dir = tmp_path / "inside_dir"
        inside_dir.mkdir()

        loader = AudioTrackLoader(music_dir=inside_dir, auto_init_mixer=False)
        # Attempt to resolve absolute path pointing outside search dirs
        assert loader.resolve_track(outside_file) is None

    def test_direct_file_path_inside_search_directory_resolves(self, tmp_path: Path):
        """Direct absolute path to a file inside the search directory resolves correctly."""
        music_dir = tmp_path / "music_inside"
        music_dir.mkdir()
        valid_file = music_dir / "valid_track.ogg"
        valid_file.write_text("valid_audio")

        loader = AudioTrackLoader(music_dir=music_dir, auto_init_mixer=False)
        resolved = loader.resolve_track(valid_file)
        assert resolved is not None
        assert resolved.resolve() == valid_file.resolve()

    def test_case_insensitive_filesystem_fallback(self, tmp_path: Path):
        """File saved as UPPERCASE_NAME.OGG resolves when requested in lowercase or mixed case."""
        music_dir = tmp_path / "case_test"
        music_dir.mkdir()
        upper_file = music_dir / "SPECIAL_COMBAT_01.OGG"
        upper_file.write_text("uppercase_audio")

        loader = AudioTrackLoader(music_dir=music_dir, auto_init_mixer=False)

        resolved_lower = loader.resolve_track("special_combat_01")
        assert resolved_lower is not None
        assert resolved_lower.resolve() == upper_file.resolve()

        resolved_mixed = loader.resolve_track("Special_Combat_01.ogg")
        assert resolved_mixed is not None
        assert resolved_mixed.resolve() == upper_file.resolve()

    def test_extension_priority_fallback_chain(self, tmp_path: Path):
        """When user requests .wav but only .ogg exists, fallback chain finds the .ogg track."""
        music_dir = tmp_path / "ext_fallback"
        music_dir.mkdir()
        ogg_file = music_dir / "track_alpha.ogg"
        ogg_file.write_text("ogg_data")

        loader = AudioTrackLoader(music_dir=music_dir, auto_init_mixer=False)
        # Request with .wav extension
        resolved = loader.resolve_track("track_alpha.wav")
        assert resolved is not None
        assert resolved.resolve() == ogg_file.resolve()

    def test_get_available_tracks_scans_and_indexes_stems(self, tmp_path: Path):
        """get_available_tracks() returns a dictionary of stem -> Path."""
        music_dir = tmp_path / "avail_test"
        music_dir.mkdir()
        (music_dir / "battle_01.ogg").write_text("data")
        (music_dir / "theme_02.mp3").write_text("data")

        loader = AudioTrackLoader(music_dir=music_dir, auto_init_mixer=False)
        available = loader.get_available_tracks()
        assert "battle_01" in available
        assert "theme_02" in available


class TestTier5LoaderErrorResilienceAndMixerLifecycle:
    """Tests verifying loader methods handle mixer and pygame errors gracefully."""

    def test_load_track_with_uninitialized_mixer_auto_init_fails(self):
        """When mixer is uninitialized and init_mixer fails, load_track returns False."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        with patch.object(loader, "is_mixer_available", return_value=False), patch.object(
            loader, "init_mixer", return_value=False
        ):
            assert loader.load_track("welcome_01") is False

    def test_load_track_pygame_error_handled_safely(self):
        """When pygame.mixer.music.load raises pygame.error, load_track returns False."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        with patch.object(loader, "is_mixer_available", return_value=True), patch.object(
            loader, "resolve_track", return_value=Path("mock_track.ogg")
        ), patch("pygame.mixer.music.load", side_effect=pygame.error("Mock corrupt format")):
            assert loader.load_track("mock_track") is False

    def test_play_track_when_load_fails_returns_false(self):
        """play_track returns False immediately when load_track fails."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        with patch.object(loader, "load_track", return_value=False):
            assert loader.play_track("failing_track") is False

    def test_play_track_when_play_raises_pygame_error(self):
        """play_track catches pygame.error during music.play and returns False."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        with patch.object(loader, "load_track", return_value=True), patch(
            "pygame.mixer.music.play", side_effect=pygame.error("Mixer busy/failed")
        ):
            assert loader.play_track("mock_track", fade_ms=500) is False

    def test_stop_with_uninitialized_mixer_is_noop(self):
        """Calling stop(fade_ms=500) when mixer is unavailable executes safely."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        with patch.object(loader, "is_mixer_available", return_value=False):
            loader.stop(fade_ms=500)
            loader.stop(fade_ms=0)

    def test_init_mixer_catches_pygame_error(self):
        """init_mixer catches pygame.error and returns False without raising."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        with patch.object(loader, "is_mixer_available", return_value=False), patch(
            "pygame.mixer.init", side_effect=pygame.error("No sound card")
        ):
            assert loader.init_mixer() is False


class TestTier5LoaderStandaloneApi:
    """Tests for standalone functional helpers in audio_track_loader."""

    def test_resolve_audio_track_function(self):
        """resolve_audio_track returns a valid Path for existing track."""
        path = resolve_audio_track("welcome_01")
        assert path is not None
        assert path.is_file()

    def test_resolve_audio_track_missing_returns_none(self):
        """resolve_audio_track returns None for non-existent track."""
        assert resolve_audio_track("completely_missing_xyz") is None

    def test_is_audio_available_returns_bool(self):
        """is_audio_available() returns a boolean indicating mixer status."""
        assert isinstance(is_audio_available(), bool)


# =============================================================================
# PART 2: DYNAMIC MUSIC ENGINE & PERSISTENCE ADVERSARIAL COVERAGE
# =============================================================================


class TestTier5SettingsDataDefensiveSanitization:
    """Tests for AudioSettingsData serialization, deserialization, and boundary defense."""

    def test_from_dict_with_non_dict_payload(self):
        """Non-dict inputs to from_dict return default AudioSettingsData."""
        for bad_payload in [None, "invalid_str", [1, 2, 3], 42, 3.14]:
            settings = AudioSettingsData.from_dict(bad_payload)
            assert isinstance(settings, AudioSettingsData)
            assert settings.version == SETTINGS_SCHEMA_VERSION
            assert settings.music_muted is False
            assert settings.music_volume == 1.0

    def test_from_dict_corrupted_version_fallback(self):
        """Invalid version type in dict defaults to SETTINGS_SCHEMA_VERSION."""
        settings = AudioSettingsData.from_dict({"version": "corrupted_string"})
        assert settings.version == SETTINGS_SCHEMA_VERSION

    def test_from_dict_non_bool_mute_flags_fallback(self):
        """Non-boolean music_muted or sfx_muted fallback to False."""
        settings = AudioSettingsData.from_dict(
            {"music_muted": "true", "sfx_muted": 1}
        )
        assert settings.music_muted is False
        assert settings.sfx_muted is False

    def test_from_dict_volume_extreme_values(self):
        """Verify nan, inf, and out-of-range floats fallback or clamp correctly."""
        # NaN and Inf -> 1.0
        data_nan = AudioSettingsData.from_dict({"music_volume": float("nan")})
        assert data_nan.music_volume == 1.0

        data_inf = AudioSettingsData.from_dict({"music_volume": float("inf")})
        assert data_inf.music_volume == 1.0

        data_ninf = AudioSettingsData.from_dict({"music_volume": float("-inf")})
        assert data_ninf.music_volume == 1.0

        # Clamping
        data_clamp_low = AudioSettingsData.from_dict({"music_volume": -10.0, "sfx_volume": -0.5})
        assert data_clamp_low.music_volume == 0.0
        assert data_clamp_low.sfx_volume == 0.0

        data_clamp_high = AudioSettingsData.from_dict({"music_volume": 10.0, "sfx_volume": 2.5})
        assert data_clamp_high.music_volume == 1.0
        assert data_clamp_high.sfx_volume == 1.0

    def test_to_dict_type_preservation_and_clamping(self):
        """to_dict produces cleanly sanitized dictionary with clamped numbers."""
        data = AudioSettingsData(
            version=1,
            music_muted=True,
            music_volume=1.5,
            sfx_muted=False,
            sfx_volume=-0.2,
        )
        d = data.to_dict()
        assert d["version"] == 1
        assert d["music_muted"] is True
        assert d["music_volume"] == 1.0
        assert d["sfx_muted"] is False
        assert d["sfx_volume"] == 0.0


class TestTier5SettingsManagerErrorHandling:
    """Tests for AudioSettingsManager error resilience and non-autosave operations."""

    def test_auto_save_false_mutates_memory_without_backend_write(
        self,
        memory_backend: MemoryStorageBackend,
    ):
        """Passing auto_save=False mutates settings in memory without writing to storage backend."""
        mgr = AudioSettingsManager(backend=memory_backend, auto_load=False)
        assert memory_backend.get(DEFAULT_SETTINGS_KEY) is None

        mgr.set_music_muted(True, auto_save=False)
        assert mgr.is_music_muted() is True
        assert memory_backend.get(DEFAULT_SETTINGS_KEY) is None

        mgr.set_music_volume(0.42, auto_save=False)
        assert mgr.get_music_volume() == 0.42
        assert memory_backend.get(DEFAULT_SETTINGS_KEY) is None

        mgr.set_sfx_muted(True, auto_save=False)
        assert mgr.get_sfx_muted() is True
        assert memory_backend.get(DEFAULT_SETTINGS_KEY) is None

        mgr.set_sfx_volume(0.88, auto_save=False)
        assert mgr.get_sfx_volume() == 0.88
        assert memory_backend.get(DEFAULT_SETTINGS_KEY) is None

    def test_save_handles_backend_exception_gracefully(self):
        """When storage backend raises an exception during save(), save() returns False."""
        mock_backend = MagicMock()
        mock_backend.set.side_effect = RuntimeError("Disk full / I/O error")

        mgr = AudioSettingsManager(backend=mock_backend, auto_load=False)
        assert mgr.save() is False

    def test_load_handles_backend_exception_gracefully(self):
        """When storage backend raises an exception during load(), load() returns False and resets defaults."""
        mock_backend = MagicMock()
        mock_backend.get.side_effect = OSError("Read permission error")

        mgr = AudioSettingsManager(backend=mock_backend, auto_load=False)
        mgr.data.music_muted = True
        assert mgr.load() is False
        assert mgr.is_music_muted() is False  # reset to default


class TestTier5EngineStateMachineTransitions:
    """White-box tests for DynamicMusicEngine context switching and state machine edge cases."""

    def test_set_context_none_is_noop(self, engine: DynamicMusicEngine):
        """Calling set_context(None) retains current context and track without changes."""
        engine.set_context(MusicContext.MAP)
        initial_track = engine.get_current_track()
        assert initial_track is not None

        engine.set_context(None)
        assert engine.get_current_context() == MusicContext.MAP
        assert engine.get_current_track() == initial_track

    def test_same_context_when_stopped_starts_playback(self, engine: DynamicMusicEngine):
        """Calling set_context for the same context while STOPPED restarts playback for that context."""
        engine.set_context(MusicContext.WELCOME)
        assert engine.playback_state == PlaybackState.PLAYING

        engine.stop()
        assert engine.playback_state == PlaybackState.STOPPED
        assert engine.get_current_context() == MusicContext.WELCOME

        # Setting same context again when STOPPED
        engine.set_context(MusicContext.WELCOME)
        assert engine.playback_state == PlaybackState.PLAYING
        assert engine.get_current_track() in CONTEXT_TRACKS[MusicContext.WELCOME]

    def test_context_switch_during_fadeout_starts_new_context_immediately(
        self,
        engine: DynamicMusicEngine,
    ):
        """Switching to a new context while FADING_OUT immediately starts the new context."""
        engine.set_context(MusicContext.WELCOME)
        engine.stop(fade_ms=1000)
        assert engine.playback_state == PlaybackState.FADING_OUT

        # Switch to COMBAT while still fading
        engine.set_context(MusicContext.COMBAT)
        assert engine.get_current_context() == MusicContext.COMBAT
        assert engine.playback_state == PlaybackState.PLAYING
        assert engine.get_current_track() in CONTEXT_TRACKS[MusicContext.COMBAT]

    def test_unknown_or_empty_context_stops_engine(self, engine: DynamicMusicEngine):
        """Setting an unrecognized context or one with no tracks transitions to STOPPED."""
        engine.set_context(MusicContext.WELCOME)

        # Mock context not in CONTEXT_TRACKS
        class FakeContext:
            name = "FAKE_CONTEXT"

        engine.set_context(FakeContext())  # type: ignore
        assert engine.playback_state == PlaybackState.STOPPED
        assert engine.get_current_track() is None


class TestTier5EnginePlaybackFailures:
    """Tests verifying behavior when underlying loader fails to play tracks."""

    def test_play_track_failure_sets_stopped_state(self, engine: DynamicMusicEngine):
        """When loader.play_track returns False, engine transitions to STOPPED and clears track."""
        with patch.object(engine.loader, "play_track", return_value=False):
            engine.set_context(MusicContext.MAP)
            assert engine.playback_state == PlaybackState.STOPPED
            assert engine.get_current_track() is None

    def test_mixer_unavailable_during_volume_application(self, engine: DynamicMusicEngine):
        """_apply_volume executes safely without error when mixer is unavailable."""
        with patch.object(engine.loader, "is_mixer_available", return_value=False):
            engine.set_volume(0.5)
            engine.set_muted(True)
            engine.toggle_mute()

    def test_is_music_busy_catches_mixer_exceptions(self, engine: DynamicMusicEngine):
        """_is_music_busy catches exceptions and returns False."""
        with patch.object(engine.loader, "is_mixer_available", return_value=True), patch(
            "pygame.mixer.music.get_busy", side_effect=pygame.error("Mixer failure")
        ):
            assert engine._is_music_busy() is False


class TestTier5EngineFadeoutAndPendingTrackQueue:
    """Tests verifying fadeout timer decrement and pending track consumption in update(dt)."""

    def test_pending_track_consumed_after_fadeout_timer_expires(
        self,
        engine: DynamicMusicEngine,
    ):
        """When FADING_OUT with a _pending_track, expiring the timer starts playback of the pending track."""
        engine.set_context(MusicContext.WELCOME)
        engine.stop(fade_ms=500)
        assert engine.playback_state == PlaybackState.FADING_OUT

        # Queue a pending track
        engine._pending_track = "exploration_01"
        engine._pending_context = MusicContext.MAP
        engine._fade_duration = 0.5
        engine._fade_timer = 0.5

        # Advance timer past expiration with music not busy
        with patch("pygame.mixer.music.get_busy", return_value=False):
            engine.update(dt=0.6)

        assert engine.playback_state == PlaybackState.PLAYING
        assert engine.get_current_track() == "exploration_01"
        assert engine._pending_track is None

    def test_fadeout_without_pending_track_transitions_to_stopped(
        self,
        engine: DynamicMusicEngine,
    ):
        """When FADING_OUT without a pending track, expiring the timer transitions to STOPPED."""
        engine.set_context(MusicContext.WELCOME)
        engine.stop(fade_ms=500)
        assert engine.playback_state == PlaybackState.FADING_OUT

        with patch("pygame.mixer.music.get_busy", return_value=False):
            engine.update(dt=0.6)

        assert engine.playback_state == PlaybackState.STOPPED
        assert engine.get_current_track() is None


class TestTier5EngineEndEventSystem:
    """White-box tests for set_end_event and handle_event contracts."""

    def test_set_end_event_clears_when_none(self, engine: DynamicMusicEngine):
        """set_end_event(None) calls pygame.mixer.music.set_endevent() with no arguments."""
        with patch("pygame.mixer.music.set_endevent") as mock_set:
            engine.set_end_event(pygame.USEREVENT + 1)
            mock_set.assert_called_with(pygame.USEREVENT + 1)

            engine.set_end_event(None)
            mock_set.assert_called_with()

    def test_set_end_event_catches_mixer_exceptions(self, engine: DynamicMusicEngine):
        """set_end_event catches exceptions from pygame.mixer without crashing."""
        with patch("pygame.mixer.music.set_endevent", side_effect=pygame.error("Event queue error")):
            engine.set_end_event(pygame.USEREVENT + 1)

    def test_handle_event_ignored_when_mixer_busy(self, engine: DynamicMusicEngine):
        """handle_event ignores endevent if the stream is still busy."""
        custom_ev = pygame.USEREVENT + 5
        engine.set_end_event(custom_ev)
        engine.set_context(MusicContext.MAP)
        initial_track = engine.get_current_track()

        fake_event = pygame.event.Event(custom_ev)
        with patch.object(engine, "_is_music_busy", return_value=True):
            engine.handle_event(fake_event)
            assert engine.get_current_track() == initial_track

    def test_handle_event_ignored_when_not_playing(self, engine: DynamicMusicEngine):
        """handle_event ignores endevent if engine is PAUSED or STOPPED."""
        custom_ev = pygame.USEREVENT + 6
        engine.set_end_event(custom_ev)
        engine.set_context(MusicContext.MAP)
        engine.pause()

        fake_event = pygame.event.Event(custom_ev)
        with patch.object(engine, "_handle_track_finished") as mock_finish:
            engine.handle_event(fake_event)
            mock_finish.assert_not_called()

    def test_handle_event_with_event_lacking_type_attribute(self, engine: DynamicMusicEngine):
        """handle_event safely handles objects without a 'type' attribute."""
        engine.set_end_event(pygame.USEREVENT + 7)
        engine.handle_event(object())  # type: ignore


class TestTier5EnginePauseUnpauseStopChaos:
    """Stress tests on pause, unpause, and stop transitions under various states."""

    def test_pause_idempotency_and_invalid_states(self, engine: DynamicMusicEngine):
        """pause() is idempotent when PLAYING and a no-op when STOPPED or FADING_OUT."""
        # 1. When STOPPED
        engine.stop()
        engine.pause()
        assert engine.playback_state == PlaybackState.STOPPED

        # 2. When PLAYING -> PAUSED
        engine.set_context(MusicContext.MAP)
        engine.pause()
        assert engine.playback_state == PlaybackState.PAUSED
        # Repeated pause is idempotent
        engine.pause()
        assert engine.playback_state == PlaybackState.PAUSED

        # 3. When FADING_OUT
        engine.unpause()
        engine.stop(fade_ms=500)
        assert engine.playback_state == PlaybackState.FADING_OUT
        engine.pause()
        assert engine.playback_state == PlaybackState.FADING_OUT

    def test_unpause_idempotency_and_invalid_states(self, engine: DynamicMusicEngine):
        """unpause() is idempotent when PLAYING and a no-op when STOPPED."""
        engine.stop()
        engine.unpause()
        assert engine.playback_state == PlaybackState.STOPPED

        engine.set_context(MusicContext.MAP)
        assert engine.playback_state == PlaybackState.PLAYING
        engine.unpause()
        assert engine.playback_state == PlaybackState.PLAYING

    def test_stop_with_fade_when_paused_does_hard_stop(self, engine: DynamicMusicEngine):
        """stop(fade_ms=500) while PAUSED immediately transitions to STOPPED (not FADING_OUT)."""
        engine.set_context(MusicContext.WELCOME)
        engine.pause()
        assert engine.playback_state == PlaybackState.PAUSED

        engine.stop(fade_ms=500)
        assert engine.playback_state == PlaybackState.STOPPED
        assert engine.get_current_track() is None


class TestTier5EngineVolumeAndMuteInteractions:
    """Tests for volume clamping, muting behavior, and hardware volume application resilience."""

    def test_set_volume_while_muted_maintains_zero_effective_volume(
        self,
        engine: DynamicMusicEngine,
    ):
        """Changing volume while muted updates target volume without un-silencing the mixer."""
        engine.set_context(MusicContext.WELCOME)
        engine.set_muted(True)
        assert engine.is_muted() is True

        with patch("pygame.mixer.music.set_volume") as mock_set_vol:
            engine.set_volume(0.8)
            # Mixer hardware volume must still be set to 0.0 because muted
            mock_set_vol.assert_called_with(0.0)
            assert engine.get_volume() == 0.8

            # Unmuting restores the 0.8 volume to mixer
            engine.set_muted(False)
            mock_set_vol.assert_called_with(0.8)

    def test_mixer_music_set_volume_catches_exception(self, engine: DynamicMusicEngine):
        """_apply_volume catches pygame.error during set_volume without raising."""
        with patch("pygame.mixer.music.set_volume", side_effect=pygame.error("Set volume failed")):
            engine.set_volume(0.5)


class TestTier5ContextResolutionExhaustive:
    """Exhaustive tests for resolve_music_context across all valid and invalid game sessions."""

    def test_resolve_music_context_all_welcome_modes(self):
        """WELCOME, CLASS_SELECT, BIOME_SELECT, and CREDITS all resolve to MusicContext.WELCOME."""
        modes = [GameMode.WELCOME, GameMode.CLASS_SELECT]
        if hasattr(GameMode, "BIOME_SELECT"):
            modes.append(GameMode.BIOME_SELECT)
        if hasattr(GameMode, "CREDITS"):
            modes.append(GameMode.CREDITS)

        for mode in modes:
            session = MagicMock()
            session.current_mode = mode
            assert resolve_music_context(session) == MusicContext.WELCOME

    def test_resolve_music_context_combat_all_enemy_tiers(self):
        """Combat resolves to MusicContext.BOSS for ELITE and BOSS, and COMBAT for others."""
        # COMMON and UNCOMMON -> COMBAT
        for normal_tier in [EnemyTier.COMMON, EnemyTier.UNCOMMON]:
            session = MagicMock()
            session.current_mode = GameMode.COMBAT
            session.combat.enemy.tier = normal_tier
            assert resolve_music_context(session) == MusicContext.COMBAT

        # ELITE and BOSS -> BOSS
        for boss_tier in [EnemyTier.ELITE, EnemyTier.BOSS]:
            session = MagicMock()
            session.current_mode = GameMode.COMBAT
            session.combat.enemy.tier = boss_tier
            assert resolve_music_context(session) == MusicContext.BOSS

    def test_resolve_music_context_non_combat_modes_return_none(self):
        """Modals and non-mapped game modes return None to preserve current music track."""
        other_modes = [
            getattr(GameMode, "INVENTORY", None),
            getattr(GameMode, "CHARACTER_SHEET", None),
            getattr(GameMode, "DEATH", None),
            getattr(GameMode, "VICTORY", None),
            getattr(GameMode, "LEVEL_UP", None),
            getattr(GameMode, "DIALOGUE", None),
        ]
        for mode in other_modes:
            if mode is not None:
                session = MagicMock()
                session.current_mode = mode
                assert resolve_music_context(session) is None
