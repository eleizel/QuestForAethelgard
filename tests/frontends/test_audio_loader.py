"""Unit tests for AudioTrackLoader and audio asset verification.

Validates track resolution, format fallback, headless / uninitialized mixer
safety, and asset compression limits.
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest
import pygame

from src.frontends.pygame_ce.audio_track_loader import (
    DEFAULT_AUDIO_EXTENSIONS,
    AudioTrackLoader,
    get_default_music_dir,
    is_audio_available,
    load_audio_track,
    resolve_audio_track,
)
from src.frontends.pygame_ce.music_engine import (
    AudioTrackLoader as ExportedAudioTrackLoader,
    CONTEXT_TRACKS,
    MusicContext,
    resolve_audio_track as exported_resolve_audio_track,
    load_audio_track as exported_load_audio_track,
    is_audio_available as exported_is_audio_available,
)

CANONICAL_TRACKS = [
    "welcome_01",
    "welcome_02",
    "exploration_01",
    "exploration_02",
    "combat_01",
    "combat_02",
    "boss_01",
    "boss_02",
]


@pytest.fixture(autouse=True)
def ensure_dummy_audio_driver():
    """Ensure headless SDL audio driver for test isolation."""
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    yield
    if pygame.mixer.get_init():
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass


class TestAudioTrackResolution:
    """Tests track path resolution and fallback mechanisms."""

    def test_resolution_all_8_game_tracks(self):
        """All 8 canonical game tracks must resolve to real files."""
        loader = AudioTrackLoader()
        for track_name in CANONICAL_TRACKS:
            resolved = loader.resolve_track(track_name)
            assert resolved is not None, f"Failed to resolve track: {track_name}"
            assert resolved.is_file(), f"Resolved path is not a file: {resolved}"

    def test_resolution_with_explicit_and_legacy_extensions(self):
        """Explicit extensions and legacy .wav references must resolve cleanly."""
        loader = AudioTrackLoader()
        # Explicit existing extensions
        assert loader.resolve_track("welcome_01.mp3") is not None
        assert loader.resolve_track("exploration_01.ogg") is not None
        assert loader.resolve_track("combat_01.ogg") is not None
        assert loader.resolve_track("boss_01.ogg") is not None

        # Legacy .wav reference fallback: WAV was converted to OGG, so .wav falls back to .ogg
        legacy_wav = loader.resolve_track("exploration_01.wav")
        assert legacy_wav is not None
        assert legacy_wav.suffix == ".ogg"

        legacy_boss_wav = loader.resolve_track("boss_01.wav")
        assert legacy_boss_wav is not None
        assert legacy_boss_wav.suffix == ".ogg"

    def test_fallback_priority_chain(self, tmp_path: Path):
        """Loader must follow strict fallback chain: .ogg -> .mp3 -> .wav."""
        music_dir = tmp_path / "music"
        music_dir.mkdir()

        # Case 1: All three exist -> .ogg is preferred
        (music_dir / "track_a.ogg").write_text("ogg")
        (music_dir / "track_a.mp3").write_text("mp3")
        (music_dir / "track_a.wav").write_text("wav")

        # Case 2: Only .mp3 and .wav exist -> .mp3 is preferred
        (music_dir / "track_b.mp3").write_text("mp3")
        (music_dir / "track_b.wav").write_text("wav")

        # Case 3: Only .wav exists -> .wav is used
        (music_dir / "track_c.wav").write_text("wav")

        loader = AudioTrackLoader(music_dir=music_dir, auto_init_mixer=False)

        res_a = loader.resolve_track("track_a")
        assert res_a is not None and res_a.name == "track_a.ogg"

        res_b = loader.resolve_track("track_b")
        assert res_b is not None and res_b.name == "track_b.mp3"

        res_c = loader.resolve_track("track_c")
        assert res_c is not None and res_c.name == "track_c.wav"

        # Explicit extension overrides default priority if it exists
        res_a_mp3 = loader.resolve_track("track_a.mp3")
        assert res_a_mp3 is not None and res_a_mp3.name == "track_a.mp3"

    def test_non_existent_tracks_return_none(self):
        """Non-existent or empty track names must return None without raising."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        assert loader.resolve_track("completely_missing_track_xyz") is None
        assert loader.resolve_track("") is None
        assert loader.resolve_track(None) is None

        # Functional API helper
        assert resolve_audio_track("completely_missing_track_xyz") is None
        assert resolve_audio_track("") is None
        assert resolve_audio_track(None) is None

    def test_resolution_caching_and_invalidation(self):
        """Resolution results must be cached and clearable."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        assert len(loader._cache) == 0

        p1 = loader.resolve_track("welcome_01")
        assert p1 is not None
        assert "welcome_01" in loader._cache

        # Cached call
        p2 = loader.resolve_track("welcome_01")
        assert p1 == p2

        loader.clear_cache()
        assert len(loader._cache) == 0

    def test_get_available_tracks(self):
        """Available tracks dictionary should contain all canonical tracks."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        available = loader.get_available_tracks()
        for track in CANONICAL_TRACKS:
            assert track in available, f"Track {track} missing from available_tracks"


class TestMixerDegradationAndHeadless:
    """Tests audio loading and playback under headless and uninitialized mixer states."""

    def test_uninitialized_mixer_graceful_degradation(self):
        """When mixer is uninitialized and auto_init is disabled, calls must fail safely."""
        # Force mixer shutdown
        if pygame.mixer.get_init():
            pygame.mixer.quit()

        loader = AudioTrackLoader(auto_init_mixer=False)
        assert not loader.is_mixer_available()

        # Filesystem resolution still works
        assert loader.resolve_track("welcome_01") is not None

        # Loading and playing return False without crashing or raising pygame.error
        assert loader.load_track("welcome_01") is False
        assert loader.play_track("welcome_01") is False
        loader.stop()  # Must not raise

    def test_headless_dummy_driver_playback(self):
        """Under SDL dummy audio driver, load and play must succeed."""
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        loader = AudioTrackLoader(auto_init_mixer=True)
        assert loader.is_mixer_available()

        assert loader.load_track("welcome_01") is True
        assert loader.current_track == "welcome_01"
        assert loader.current_path is not None

        assert loader.play_track("welcome_01", loops=-1, fade_ms=100) is True
        loader.stop(fade_ms=50)

    def test_load_and_play_non_existent_tracks(self):
        """Loading or playing a non-existent track returns False without raising."""
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        loader = AudioTrackLoader(auto_init_mixer=True)
        assert loader.load_track("missing_track_abc") is False
        assert loader.play_track("missing_track_abc") is False
        assert loader.load_track(None) is False
        assert loader.play_track(None) is False

    def test_standalone_functions(self):
        """Standalone functional helpers must operate correctly."""
        res = resolve_audio_track("combat_01")
        assert res is not None and res.is_file()

        if not pygame.mixer.get_init():
            pygame.mixer.init()
        assert is_audio_available() is True
        assert load_audio_track("combat_01") is True
        assert load_audio_track("invalid_track") is False


class TestAssetDirectoryCompliance:
    """Verifies physical audio asset file sizes, total directory footprint, and format hygiene."""

    def test_each_audio_asset_under_5mb(self):
        """Every audio file in assets/music must be strictly < 5 MB (5,242,880 bytes)."""
        music_dir = get_default_music_dir()
        assert music_dir.is_dir(), f"Music directory {music_dir} does not exist"

        tracks = list(music_dir.glob("*.*"))
        assert len(tracks) >= 8, f"Expected at least 8 tracks, found {len(tracks)}"

        for track_file in tracks:
            size_bytes = track_file.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            assert (
                size_bytes < 5 * 1024 * 1024
            ), f"Track {track_file.name} is {size_mb:.2f} MB, exceeding 5.0 MB limit"

    def test_total_audio_directory_under_30mb(self):
        """Total size of assets/music must be strictly < 30 MB (31,457,280 bytes)."""
        music_dir = get_default_music_dir()
        tracks = list(music_dir.glob("*.*"))
        total_bytes = sum(t.stat().st_size for t in tracks)
        total_mb = total_bytes / (1024 * 1024)
        assert (
            total_bytes < 30 * 1024 * 1024
        ), f"Total music directory size is {total_mb:.2f} MB, exceeding 30.0 MB limit"

    def test_zero_uncompressed_wav_files_remain(self):
        """Zero .wav files must remain in assets/music/ to protect Pygbag package size."""
        music_dir = get_default_music_dir()
        wav_files = list(music_dir.glob("*.wav"))
        assert len(wav_files) == 0, f"Found uncompressed WAV files in assets/music: {wav_files}"

    def test_all_canonical_stems_present(self):
        """All 8 canonical tracks must exist in either .ogg or .mp3 format."""
        music_dir = get_default_music_dir()
        existing_stems = {f.stem.lower() for f in music_dir.glob("*.*")}
        for canonical in CANONICAL_TRACKS:
            assert (
                canonical in existing_stems
            ), f"Canonical track '{canonical}' not found in {existing_stems}"


class TestMusicEngineReExports:
    """Verifies re-exports and contracts in src/frontends/pygame_ce/music_engine.py."""

    def test_exports_identical_to_audio_track_loader(self):
        assert ExportedAudioTrackLoader is AudioTrackLoader
        assert exported_resolve_audio_track is resolve_audio_track
        assert exported_load_audio_track is load_audio_track
        assert exported_is_audio_available is is_audio_available

    def test_music_contexts_defined(self):
        assert MusicContext.WELCOME in CONTEXT_TRACKS
        assert MusicContext.MAP in CONTEXT_TRACKS
        assert MusicContext.COMBAT in CONTEXT_TRACKS
        assert MusicContext.BOSS in CONTEXT_TRACKS

        # Verify all mapped tracks in CONTEXT_TRACKS are members of CANONICAL_TRACKS
        for ctx, tracks in CONTEXT_TRACKS.items():
            assert len(tracks) == 2, f"Expected 2 tracks for {ctx}, got {tracks}"
            for t in tracks:
                assert t in CANONICAL_TRACKS
