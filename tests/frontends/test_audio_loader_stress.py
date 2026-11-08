"""Adversarial stress tests for AudioTrackLoader and music asset boundaries.

Stress tests include:
- Invalid types and adversarial payloads (None, int, float, empty, whitespace, null bytes, special chars, path traversal)
- Resolution in secondary search paths and subdirectories
- Case sensitivity and case variation testing across platforms
- Thread concurrency stress for track resolution, cache updates, and cache invalidation
- Clean None return and memory leak stress testing on non-existent tracks
- Asset budget validation (<5MB per file, <30MB total)
"""

from __future__ import annotations

import gc
import os
from pathlib import Path
import threading
import time
import tracemalloc
import pytest
import pygame

from src.frontends.pygame_ce.audio_track_loader import (
    AudioTrackLoader,
    get_default_music_dir,
    load_audio_track,
    resolve_audio_track,
)


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


class TestAdversarialInputsAndTypes:
    """Stress tests invalid types, corrupt strings, and malicious path payloads."""

    @pytest.mark.parametrize(
        "invalid_input",
        [
            None,
            "",
            "   ",
            "\t\n\r  ",
            123,
            0,
            -999,
            3.14159,
            True,
            False,
            [],
            {},
            (),
            object(),
        ],
    )
    def test_invalid_types_do_not_crash(self, invalid_input):
        """Loader must handle invalid types gracefully without uncaught exceptions."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        try:
            result = loader.resolve_track(invalid_input)
            assert result is None
        except Exception as exc:
            pytest.fail(f"resolve_track crashed on input {repr(invalid_input)}: {type(exc).__name__}: {exc}")

        try:
            load_result = loader.load_track(invalid_input)
            assert load_result is False
        except Exception as exc:
            pytest.fail(f"load_track crashed on input {repr(invalid_input)}: {type(exc).__name__}: {exc}")

    @pytest.mark.parametrize(
        "special_payload",
        [
            "track<>:\"/\\|?*",
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "LPT1",
            "../../../../../../etc/passwd",
            "..\\..\\..\\..\\windows\\system32\\calc.exe",
            "foo\x00bar",
            "\x00",
            "track/../..//track",
            "?" * 500,
            "A" * 1000,
            "unicode_\U0001f3b5_\u03a9_\u697d",
            "track with spaces and #!@$%^&*()_+.ogg",
        ],
    )
    def test_special_characters_and_path_payloads(self, special_payload):
        """Loader must handle malicious, reserved, or invalid filenames safely."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        try:
            result = loader.resolve_track(special_payload)
            if result is not None:
                assert isinstance(result, Path)
                assert result.is_file()
            else:
                assert result is None
        except (ValueError, OSError) as exc:
            pytest.fail(f"resolve_track raised uncaught {type(exc).__name__} on {repr(special_payload)}: {exc}")


class TestSecondaryPathsAndSubdirectories:
    """Tests resolution across secondary search paths and subdirectories."""

    def test_resolution_in_secondary_custom_directory(self, tmp_path: Path):
        """Loader must resolve tracks present only in secondary search paths."""
        secondary_dir = tmp_path / "secondary"
        secondary_dir.mkdir()

        (secondary_dir / "secret_theme.ogg").write_text("ogg_secondary")

        loader = AudioTrackLoader(music_dir=secondary_dir, auto_init_mixer=False)
        res = loader.resolve_track("secret_theme")
        assert res is not None
        assert res.name == "secret_theme.ogg"
        assert res.parent.resolve() == secondary_dir.resolve()

    def test_resolution_in_fallback_assets_directory(self, tmp_path: Path):
        """Loader resolves tracks from secondary assets fallback directory."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        search_dirs = loader.get_search_directories()
        assert len(search_dirs) >= 2, f"Expected secondary search directories, found {search_dirs}"

        # The secondary fallback is the root assets/ directory
        assets_dir = search_dirs[1] if len(search_dirs) > 1 else search_dirs[0]
        test_file = assets_dir / "temp_secondary_track.ogg"
        test_file.write_text("dummy")
        try:
            res = loader.resolve_track("temp_secondary_track")
            assert res is not None
            assert res.resolve() == test_file.resolve()
        finally:
            if test_file.exists():
                test_file.unlink()

    def test_resolution_in_subdirectory_subpath(self, tmp_path: Path):
        """CRITICAL CHALLENGE: Resolution when a track exists in a subdirectory.

        When a track is located at `music_dir / 'ambient' / 'cave_01.ogg'`, querying
        'ambient/cave_01' should resolve to `sub_dir / 'cave_01.ogg'`.
        Current AudioTrackLoader strips raw_path.parent and looks only at the root
        directory, failing with None.
        """
        base_dir = tmp_path / "music"
        sub_dir = base_dir / "ambient"
        sub_dir.mkdir(parents=True)

        (sub_dir / "cave_01.ogg").write_text("ogg_cave")

        loader = AudioTrackLoader(music_dir=base_dir, auto_init_mixer=False)
        res_subpath = loader.resolve_track("ambient/cave_01")
        assert res_subpath is not None, (
            "BUG: Failed to resolve 'ambient/cave_01' in subdirectory. "
            "AudioTrackLoader strips raw_path.parent and discards subdirectory paths."
        )
        assert res_subpath.name == "cave_01.ogg"

    def test_subpath_does_not_collide_with_root_file(self, tmp_path: Path):
        """CRITICAL CHALLENGE: Subpath query must not resolve to root file of same stem.

        When `root / 'theme.ogg'` and `root / 'sub' / 'theme.ogg'` both exist,
        querying 'sub/theme' must resolve to `sub/theme.ogg`, NOT `root/theme.ogg`.
        Current AudioTrackLoader strips 'sub/' and wrongly returns `root/theme.ogg`.
        """
        base_dir = tmp_path / "music"
        sub_dir = base_dir / "sub"
        sub_dir.mkdir(parents=True)

        (base_dir / "theme.ogg").write_text("root_theme")
        (sub_dir / "theme.ogg").write_text("sub_theme")

        loader = AudioTrackLoader(music_dir=base_dir, auto_init_mixer=False)
        res = loader.resolve_track("sub/theme")
        assert res is not None, "Query 'sub/theme' returned None"
        assert res.parent.resolve() == sub_dir.resolve(), (
            f"BUG: Query 'sub/theme' resolved to {res} in root instead of {sub_dir}!"
        )
        assert res.read_text() == "sub_theme"


class TestCaseVariationsAndSensitivity:
    """Tests case variations in track queries and filesystem entries."""

    @pytest.mark.parametrize(
        "query,expected_stem",
        [
            ("EXPLORATION_01", "exploration_01"),
            ("exploration_01", "exploration_01"),
            ("Exploration_01", "exploration_01"),
            ("ExPlOrAtIoN_01", "exploration_01"),
            ("Combat_01.OGG", "combat_01"),
            ("COMBAT_01.ogg", "combat_01"),
            ("combat_01.OGG", "combat_01"),
            ("WELCOME_01.MP3", "welcome_01"),
            ("Welcome_02.mp3", "welcome_02"),
            ("BOSS_01.WAV", "boss_01"),
        ],
    )
    def test_case_variation_resolution(self, query, expected_stem):
        """Case variations in track name and extension must resolve correctly."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        resolved = loader.resolve_track(query)
        assert resolved is not None, f"Failed to resolve case variation: '{query}'"
        assert resolved.stem.lower() == expected_stem
        assert resolved.is_file()

    def test_case_insensitive_filesystem_search_on_linux_simulation(self, tmp_path: Path):
        """Simulate case mismatch where physical file is uppercase on disk."""
        music_dir = tmp_path / "music"
        music_dir.mkdir()

        (music_dir / "DUNGEON_DEEP.OGG").write_text("ogg_dungeon")

        loader = AudioTrackLoader(music_dir=music_dir, auto_init_mixer=False)

        res1 = loader.resolve_track("dungeon_deep")
        assert res1 is not None
        assert res1.name == "DUNGEON_DEEP.OGG"

        res2 = loader.resolve_track("Dungeon_Deep.ogg")
        assert res2 is not None
        assert res2.name == "DUNGEON_DEEP.OGG"


class TestCacheConcurrencyAndInvalidation:
    """Stress tests cache thread safety and cache clearing under concurrent operations."""

    def test_concurrent_resolution_and_cache_access(self):
        """Multiple concurrent threads querying tracks and clearing cache simultaneously."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        tracks_to_query = [
            "welcome_01",
            "welcome_02",
            "exploration_01",
            "exploration_02",
            "combat_01",
            "combat_02",
            "boss_01",
            "boss_02",
            "non_existent_01",
            "non_existent_02",
            "EXPLORATION_01",
            "Combat_01.OGG",
        ]

        errors: list[Exception] = []
        stop_event = threading.Event()

        def worker_resolver(thread_id: int):
            try:
                for i in range(200):
                    track = tracks_to_query[(i + thread_id) % len(tracks_to_query)]
                    res = loader.resolve_track(track)
                    if "non_existent" in track:
                        assert res is None
                    else:
                        assert res is not None and res.is_file()
            except Exception as exc:
                errors.append(exc)

        def worker_clearer():
            try:
                while not stop_event.is_set():
                    time.sleep(0.005)
                    loader.clear_cache()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker_resolver, args=(i,)) for i in range(10)]
        clearer_thread = threading.Thread(target=worker_clearer)

        for t in threads:
            t.start()
        clearer_thread.start()

        for t in threads:
            t.join()

        stop_event.set()
        clearer_thread.join()

        assert len(errors) == 0, f"Thread concurrency errors encountered: {errors}"

    def test_cache_invalidation_reflects_new_filesystem_files(self, tmp_path: Path):
        """Clearing cache must allow newly created files to be discovered."""
        music_dir = tmp_path / "music"
        music_dir.mkdir()

        loader = AudioTrackLoader(music_dir=music_dir, auto_init_mixer=False)

        assert loader.resolve_track("new_dynamic_track") is None
        assert "new_dynamic_track" in loader._cache
        assert loader._cache["new_dynamic_track"] is None

        (music_dir / "new_dynamic_track.ogg").write_text("ogg_new")

        # Cached negative result remains
        assert loader.resolve_track("new_dynamic_track") is None

        # After cache invalidation, discovers new file
        loader.clear_cache()
        assert len(loader._cache) == 0
        resolved = loader.resolve_track("new_dynamic_track")
        assert resolved is not None
        assert resolved.name == "new_dynamic_track.ogg"


class TestNegativeCachingAndMemory:
    """Stress tests unbounded queries to observe cache memory growth and leak potential."""

    def test_negative_caching_and_cache_growth(self):
        """Querying distinct non-existent tracks stores entries in cache."""
        loader = AudioTrackLoader(auto_init_mixer=False)
        initial_cache_size = len(loader._cache)

        count = 500
        for i in range(count):
            res = loader.resolve_track(f"non_existent_unique_track_{i}")
            assert res is None

        assert len(loader._cache) == initial_cache_size + count
        loader.clear_cache()
        assert len(loader._cache) == 0

    def test_memory_stability_repeated_loads(self):
        """Repeated loading of valid and invalid tracks must not leak memory."""
        import logging
        loader_logger = logging.getLogger("src.frontends.pygame_ce.audio_track_loader")
        prev_level = loader_logger.level
        loader_logger.setLevel(logging.CRITICAL)
        try:
            loader = AudioTrackLoader(auto_init_mixer=True)
            tracemalloc.start()
            gc.collect()
            snap1 = tracemalloc.take_snapshot()

            for _ in range(200):
                loader.load_track("welcome_01")
                loader.load_track("combat_01")
                loader.load_track("non_existent_track")

            gc.collect()
            snap2 = tracemalloc.take_snapshot()
            diff = sum(s.size_diff for s in snap2.compare_to(snap1, "lineno"))
            # Memory growth across 200 cycles must be minimal (< 20 KB)
            assert diff < 20 * 1024, f"Potential memory leak detected: {diff / 1024:.2f} KB growth"
        finally:
            loader_logger.setLevel(prev_level)


class TestAssetBudgetBoundaries:
    """Rigorous verification of audio asset sizes against strict project budget limits."""

    SINGLE_FILE_LIMIT_BYTES = 5_242_880  # Strictly < 5 MB (5,242,880 B)
    TOTAL_FOLDER_LIMIT_BYTES = 31_457_280  # Strictly < 30 MB (31,457,280 B)

    def test_all_individual_audio_assets_strictly_under_5mb(self):
        music_dir = get_default_music_dir()
        assert music_dir.is_dir()

        audio_files = [f for f in music_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
        assert len(audio_files) >= 8, f"Expected at least 8 tracks, found {len(audio_files)}"

        for f in audio_files:
            size = f.stat().st_size
            assert size < self.SINGLE_FILE_LIMIT_BYTES, (
                f"File {f.name} ({size:,} bytes, {size / (1024*1024):.2f} MB) "
                f"exceeds single file budget of {self.SINGLE_FILE_LIMIT_BYTES:,} bytes (5 MB)"
            )

    def test_total_music_folder_strictly_under_30mb(self):
        music_dir = get_default_music_dir()
        audio_files = [f for f in music_dir.iterdir() if f.is_file() and not f.name.startswith(".")]

        total_bytes = sum(f.stat().st_size for f in audio_files)
        assert total_bytes < self.TOTAL_FOLDER_LIMIT_BYTES, (
            f"Total music folder size ({total_bytes:,} bytes, {total_bytes / (1024*1024):.2f} MB) "
            f"exceeds total budget of {self.TOTAL_FOLDER_LIMIT_BYTES:,} bytes (30 MB)"
        )

    def test_zero_wav_files_remain(self):
        music_dir = get_default_music_dir()
        wavs = list(music_dir.glob("*.wav"))
        assert len(wavs) == 0, f"Found WAV files in music directory: {wavs}"
