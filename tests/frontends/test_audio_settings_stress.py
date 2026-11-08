"""Adversarial stress and corruption recovery tests for AudioSettingsManager and DynamicMusicEngine.

Scope: Challenger 2 — Persistence Stress, Data Corruption & Mute Restoration
Verification areas:
1. Corrupted JSON payloads (truncated strings, binary junk, invalid unicode, deeply nested structures, nulls, type confusion).
2. Extreme volume values (NaN, Inf, negative, huge numbers, non-numerics) clamped to [0.0, 1.0].
3. Read-only storage and storage exceptions: engine remains 100% operational in memory when storage fails.
4. Process restart simulation: 50 successive manager instances writing and reading mute state with random toggles, verifying 100% consistency.
5. Pre-muted boot restoration and DynamicMusicEngine mute lifecycle.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import random
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import pygame

from src.core.persistence import MemoryStorageBackend
from src.core.save_manager import FileStorageBackend, StorageBackend
from src.frontends.pygame_ce.music_engine import (
    AudioSettingsData,
    AudioSettingsManager,
    DynamicMusicEngine,
    MusicContext,
    DEFAULT_SETTINGS_KEY,
    SETTINGS_SCHEMA_VERSION,
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
    """Fresh in-memory storage backend."""
    return MemoryStorageBackend()


# =============================================================================
# 1. CORRUPTED JSON PAYLOAD STRESS
# =============================================================================
class TestCorruptedJsonPayloadStress:
    """Stress tests corrupted, truncated, binary, and adversarial payloads."""

    @pytest.mark.parametrize(
        "truncated_payload",
        [
            '{"version": 1, "music_muted": tr',
            '{"music_volume": 0.',
            '{"music_muted": true',
            '{"',
            '{"version":',
            '{"sfx_volume":',
            '{"music_muted": true, "music_volume": 0.5',
            '{"version": 1, "music_muted": false, "music_volume":',
            '{"version": 1, "music_muted": [',
            '{"version": 1, "nested": {"a":',
            "{",
            "}",
            "{ broken json string without closing quote",
        ],
    )
    def test_truncated_json_payloads_fallback_to_defaults(
        self, memory_backend: MemoryStorageBackend, truncated_payload: str
    ):
        """Truncated JSON strings must not raise exceptions and must safely reset to defaults."""
        memory_backend.set(DEFAULT_SETTINGS_KEY, truncated_payload)
        manager = AudioSettingsManager(backend=memory_backend)

        assert manager.load() is False
        assert manager.is_music_muted() is False
        assert manager.get_music_volume() == 1.0
        assert manager.get_sfx_muted() is False
        assert manager.get_sfx_volume() == 1.0

    @pytest.mark.parametrize(
        "binary_payload",
        [
            "\x00\x01\x02\x03\x04\xff\xfe",
            "\x00" * 512,
            "\x01\x02\x08\x0b\x0c\x0e\x1f",
            "\x80\x90\xa0\xb0\xc0\xd0\xe0\xf0\xff",
            "!@#$%^&*()_+~|}{[]:;?><,./",
            "\x00" + json.dumps({"music_muted": True}),
            json.dumps({"music_muted": True}) + "\x00",
            "\xff\xfe" + json.dumps({"music_muted": True}),
        ],
    )
    def test_binary_and_control_junk_payloads_fallback_to_defaults(
        self, memory_backend: MemoryStorageBackend, binary_payload: str
    ):
        """Binary junk, null bytes, and unescaped control chars fall back cleanly."""
        memory_backend.set(DEFAULT_SETTINGS_KEY, binary_payload)
        manager = AudioSettingsManager(backend=memory_backend)

        assert manager.load() is False
        assert manager.is_music_muted() is False
        assert manager.get_music_volume() == 1.0

    def test_file_storage_invalid_utf8_bytes_fallback(self, tmp_path: Path):
        """FileStorageBackend encountering raw invalid UTF-8 bytes falls back safely."""
        file_backend = FileStorageBackend(save_dir=str(tmp_path))
        settings_file = tmp_path / f"{DEFAULT_SETTINGS_KEY}.json"

        # Write invalid raw UTF-8 bytes to file
        settings_file.write_bytes(b"\x80\x81\x82\x83\xff\xfe\x00\xaa\xbb\xcc")

        manager = AudioSettingsManager(backend=file_backend)
        assert manager.is_music_muted() is False
        assert manager.get_music_volume() == 1.0

        # Manager should still be able to save new valid data overwriting corrupt file
        manager.set_music_muted(True)
        assert manager.save() is True

        # Reload in a new manager
        manager2 = AudioSettingsManager(backend=file_backend)
        assert manager2.is_music_muted() is True

    @pytest.mark.parametrize(
        "nested_payload",
        [
            # Deeply nested lists (50 levels)
            "[" * 50 + "1" + "]" * 50,
            # Deeply nested dicts
            json.dumps({"a": {"b": {"c": {"d": {"e": {"f": {"music_muted": True}}}}}}}),
            # Nested array as field value
            json.dumps({"music_muted": [[[[True]]]]}),
            json.dumps({"music_volume": [[[[[0.5]]]]]}),
            json.dumps({"sfx_muted": {"inner": True}}),
            json.dumps({"version": [1, 2, 3]}),
        ],
    )
    def test_deeply_nested_structures_fallback_to_defaults(
        self, memory_backend: MemoryStorageBackend, nested_payload: str
    ):
        """Deeply nested structures do not cause recursion errors or type crashes."""
        memory_backend.set(DEFAULT_SETTINGS_KEY, nested_payload)
        manager = AudioSettingsManager(backend=memory_backend)

        # Fields must remain sanitized and valid
        assert isinstance(manager.is_music_muted(), bool)
        assert isinstance(manager.get_music_volume(), float)
        assert 0.0 <= manager.get_music_volume() <= 1.0
        assert manager.is_music_muted() is False  # Non-bool fell back to False
        assert manager.get_music_volume() == 1.0  # Non-float fell back to 1.0

    @pytest.mark.parametrize(
        "null_payload",
        [
            "null",
            json.dumps({"music_muted": None}),
            json.dumps({"music_volume": None}),
            json.dumps({"sfx_muted": None}),
            json.dumps({"sfx_volume": None}),
            json.dumps({"version": None}),
            json.dumps(
                {
                    "version": None,
                    "music_muted": None,
                    "music_volume": None,
                    "sfx_muted": None,
                    "sfx_volume": None,
                }
            ),
            "",
            "   ",
        ],
    )
    def test_null_and_empty_payloads_fallback_to_defaults(
        self, memory_backend: MemoryStorageBackend, null_payload: str
    ):
        """JSON nulls or partial null fields are safely coerced to valid default values."""
        memory_backend.set(DEFAULT_SETTINGS_KEY, null_payload)
        manager = AudioSettingsManager(backend=memory_backend)

        assert isinstance(manager.is_music_muted(), bool)
        assert manager.is_music_muted() is False
        assert manager.get_music_volume() == 1.0
        assert manager.get_sfx_muted() is False
        assert manager.get_sfx_volume() == 1.0

    @pytest.mark.parametrize(
        "scalar_payload",
        [
            "true",
            "false",
            "12345",
            "-99.99",
            '"just_a_string"',
            "[]",
        ],
    )
    def test_scalar_and_non_dict_json_payloads(
        self, memory_backend: MemoryStorageBackend, scalar_payload: str
    ):
        """Non-dict JSON primitives fall back safely to default AudioSettingsData."""
        memory_backend.set(DEFAULT_SETTINGS_KEY, scalar_payload)
        manager = AudioSettingsManager(backend=memory_backend)

        assert manager.is_music_muted() is False
        assert manager.get_music_volume() == 1.0

    @pytest.mark.parametrize(
        "confused_data,expected_muted,expected_vol",
        [
            # Integer 1/0 for boolean
            ({"music_muted": 1, "music_volume": "0.5"}, False, 0.5),
            ({"music_muted": 0, "music_volume": 0.8}, False, 0.8),
            # String representation of booleans
            ({"music_muted": "true", "music_volume": "1.0"}, False, 1.0),
            ({"music_muted": "False", "music_volume": "0.0"}, False, 0.0),
            # Boolean passed as volume (float(True) == 1.0, float(False) == 0.0)
            ({"music_muted": True, "music_volume": True}, True, 1.0),
            ({"music_muted": False, "music_volume": False}, False, 0.0),
            # Random extra unknown keys
            ({"unknown_key": "data", "music_muted": True, "music_volume": 0.75}, True, 0.75),
        ],
    )
    def test_type_confusion_coercion(
        self,
        memory_backend: MemoryStorageBackend,
        confused_data: dict[str, Any],
        expected_muted: bool,
        expected_vol: float,
    ):
        """Type confusion in fields is handled defensively without exceptions."""
        memory_backend.set(DEFAULT_SETTINGS_KEY, json.dumps(confused_data))
        manager = AudioSettingsManager(backend=memory_backend)

        assert manager.is_music_muted() == expected_muted
        assert manager.get_music_volume() == pytest.approx(expected_vol)


# =============================================================================
# 2. EXTREME VOLUME VALUES & CLAMPING
# =============================================================================
class TestExtremeVolumeValuesClamping:
    """Stress tests boundary and extreme volume inputs (NaN, Inf, negatives, huge numbers)."""

    @pytest.mark.parametrize(
        "extreme_val,expected_vol",
        [
            (float("nan"), 1.0),
            (float("-nan"), 1.0),
            (float("inf"), 1.0),
            (float("-inf"), 1.0),
            (-0.0, 0.0),
            (-0.00001, 0.0),
            (-1.0, 0.0),
            (-999.0, 0.0),
            (-1e308, 0.0),
            (-float("inf"), 1.0),
            (1.0, 1.0),
            (1.00001, 1.0),
            (2.0, 1.0),
            (999.0, 1.0),
            (1e308, 1.0),
            (1e-320, 1e-320),  # Subnormal float in range
            (0.5, 0.5),
        ],
    )
    def test_set_music_volume_extreme_values(
        self, memory_backend: MemoryStorageBackend, extreme_val: float, expected_vol: float
    ):
        """set_music_volume strictly sanitizes and clamps values to [0.0, 1.0]."""
        manager = AudioSettingsManager(backend=memory_backend)
        manager.set_music_volume(extreme_val)

        vol = manager.get_music_volume()
        assert not math.isnan(vol)
        assert not math.isinf(vol)
        assert 0.0 <= vol <= 1.0
        assert vol == pytest.approx(expected_vol, abs=1e-6)

    @pytest.mark.parametrize(
        "extreme_val,expected_vol",
        [
            (float("nan"), 1.0),
            (float("inf"), 1.0),
            (float("-inf"), 1.0),
            (-100.0, 0.0),
            (100.0, 1.0),
        ],
    )
    def test_set_sfx_volume_extreme_values(
        self, memory_backend: MemoryStorageBackend, extreme_val: float, expected_vol: float
    ):
        """set_sfx_volume strictly sanitizes and clamps values to [0.0, 1.0]."""
        manager = AudioSettingsManager(backend=memory_backend)
        manager.set_sfx_volume(extreme_val)

        vol = manager.get_sfx_volume()
        assert not math.isnan(vol)
        assert not math.isinf(vol)
        assert 0.0 <= vol <= 1.0
        assert vol == pytest.approx(expected_vol)

    @pytest.mark.parametrize(
        "invalid_volume",
        [
            "invalid_string",
            None,
            [],
            {},
            complex(1, 2),
            "NaN",
            "Infinity",
            "-Infinity",
        ],
    )
    def test_set_music_volume_non_numeric_graceful_handling(
        self, memory_backend: MemoryStorageBackend, invalid_volume: Any
    ):
        """Non-numeric or string inputs fall back to 1.0 without crashing."""
        manager = AudioSettingsManager(backend=memory_backend)
        manager.set_music_volume(invalid_volume)  # type: ignore

        vol = manager.get_music_volume()
        assert vol == 1.0

    @pytest.mark.parametrize(
        "stored_vol_repr,expected_vol",
        [
            ('"NaN"', 1.0),
            ('"Infinity"', 1.0),
            ('"-Infinity"', 1.0),
            ("-999.0", 0.0),
            ("999.0", 1.0),
            ("1e308", 1.0),
            ("-1e308", 0.0),
            ('"0.42"', 0.42),
        ],
    )
    def test_deserialization_of_extreme_stored_volumes(
        self, memory_backend: MemoryStorageBackend, stored_vol_repr: str, expected_vol: float
    ):
        """Deserialization from raw JSON correctly clamps extreme stored volume values."""
        payload = f'{{"version": 1, "music_volume": {stored_vol_repr}}}'
        memory_backend.set(DEFAULT_SETTINGS_KEY, payload)

        manager = AudioSettingsManager(backend=memory_backend)
        vol = manager.get_music_volume()
        assert not math.isnan(vol)
        assert not math.isinf(vol)
        assert 0.0 <= vol <= 1.0
        assert vol == pytest.approx(expected_vol)

    def test_to_dict_serialization_always_json_compliant(self):
        """Even with directly tampered dataclass fields, to_dict() produces strict JSON."""
        data = AudioSettingsData(
            music_volume=float("nan"),
            sfx_volume=float("inf"),
        )
        as_dict = data.to_dict()

        # Strict JSON dump (allow_nan=False raises ValueError if NaN or Inf are present)
        serialized = json.dumps(as_dict, allow_nan=False)
        assert serialized is not None
        assert 0.0 <= as_dict["music_volume"] <= 1.0
        assert 0.0 <= as_dict["sfx_volume"] <= 1.0


# =============================================================================
# 3. STORAGE FAILURE & IN-MEMORY ENGINE RESILIENCE
# =============================================================================
class TestStorageFailureAndEngineMemoryResilience:
    """Stress tests engine stability when storage backend fails or is read-only."""

    def test_read_only_backend_returns_false_and_does_not_crash(self):
        """Storage backend where set() returns False does not crash manager or engine."""
        read_only_backend = MagicMock(spec=StorageBackend)
        read_only_backend.get.return_value = None
        read_only_backend.set.return_value = False  # Write fails
        read_only_backend.exists.return_value = False

        manager = AudioSettingsManager(backend=read_only_backend)
        engine = DynamicMusicEngine(settings_manager=manager)

        # Mute toggle should succeed in memory despite write failure
        new_state = engine.toggle_mute()
        assert new_state is True
        assert engine.is_muted() is True
        assert manager.is_music_muted() is True

        # Toggle back
        new_state = engine.toggle_mute()
        assert new_state is False
        assert engine.is_muted() is False
        assert manager.is_music_muted() is False

    @pytest.mark.parametrize(
        "exception_type",
        [
            PermissionError("Read-only filesystem"),
            OSError("Disk full / QuotaExceededError"),
            TimeoutError("Storage I/O timeout"),
            RuntimeError("Unexpected storage exception"),
        ],
    )
    def test_storage_raising_exceptions_engine_remains_100_percent_operational(
        self, exception_type: Exception
    ):
        """When storage throws arbitrary exceptions on get/set, engine remains 100% operational in memory."""
        failing_backend = MagicMock(spec=StorageBackend)
        failing_backend.get.side_effect = exception_type
        failing_backend.set.side_effect = exception_type

        manager = AudioSettingsManager(backend=failing_backend)
        engine = DynamicMusicEngine(settings_manager=manager)

        # 1. Verification of default in-memory state
        assert engine.is_muted() is False
        assert engine.get_volume() == 1.0

        # 2. Toggle mute in memory
        with patch("pygame.mixer.music.set_volume") as mock_set_vol:
            toggled = engine.toggle_mute()
            assert toggled is True
            assert engine.is_muted() is True
            mock_set_vol.assert_called_with(0.0)

        # 3. Context switches and playback while muted
        engine.set_context(MusicContext.MAP)
        assert engine.get_current_context() == MusicContext.MAP
        assert engine.get_current_track() in ("exploration_01", "exploration_02")

        # 4. In-memory volume adjustments while muted
        engine.set_volume(0.6)
        assert engine.get_volume() == pytest.approx(0.6)

        # 5. Unmute restores in-memory adjusted volume
        with patch("pygame.mixer.music.set_volume") as mock_set_vol:
            toggled = engine.toggle_mute()
            assert toggled is False
            assert engine.is_muted() is False
            mock_set_vol.assert_called_with(0.6)

        # 6. Update frames and loop transitions
        with patch("pygame.mixer.music.get_busy", return_value=False), patch(
            "pygame.mixer.music.play"
        ) as mock_play:
            engine.update(dt=0.1)
            mock_play.assert_called_once()

        # 7. Playback controls: pause, unpause, stop
        engine.pause()
        assert engine.is_paused() is True
        engine.unpause()
        assert engine.is_playing() is True
        engine.stop()
        assert engine.is_playing() is False


# =============================================================================
# 4. PROCESS RESTART SIMULATION (50 ITERATIONS)
# =============================================================================
class TestProcessRestartSimulation:
    """Simulates 50 successive process reloads with randomized mute toggles."""

    def test_process_restart_simulation_in_memory(self, memory_backend: MemoryStorageBackend):
        """50 successive manager instances writing and reading mute state with random toggles."""
        rng = random.Random(42)
        expected_mute = False
        expected_volume = 1.0

        # Initial baseline check
        init_mgr = AudioSettingsManager(backend=memory_backend)
        assert init_mgr.is_music_muted() == expected_mute
        assert init_mgr.get_music_volume() == expected_volume

        for step in range(50):
            # 1. Simulate process launch: create fresh manager reading existing storage
            mgr = AudioSettingsManager(backend=memory_backend)

            # 2. Strict assertion: State must match oracle
            assert mgr.is_music_muted() == expected_mute, (
                f"Step {step}: Mute mismatch! Expected {expected_mute}, got {mgr.is_music_muted()}"
            )
            assert mgr.get_music_volume() == pytest.approx(expected_volume), (
                f"Step {step}: Volume mismatch! Expected {expected_volume}, got {mgr.get_music_volume()}"
            )

            # 3. Perform randomized action
            action = rng.choice(["toggle_mute", "set_mute", "set_volume", "none"])

            if action == "toggle_mute":
                new_mute = mgr.toggle_music_muted()
                expected_mute = new_mute
            elif action == "set_mute":
                new_mute = rng.choice([True, False])
                mgr.set_music_muted(new_mute)
                expected_mute = new_mute
            elif action == "set_volume":
                new_vol = round(rng.uniform(0.0, 1.0), 2)
                mgr.set_music_volume(new_vol)
                expected_volume = new_vol
            elif action == "none":
                pass

            # 4. Simulate process exit (dispose manager instance)
            del mgr

        # Final verification: reload in step 51
        final_mgr = AudioSettingsManager(backend=memory_backend)
        assert final_mgr.is_music_muted() == expected_mute
        assert final_mgr.get_music_volume() == pytest.approx(expected_volume)

    def test_process_restart_simulation_with_disk_file_backend(self, tmp_path: Path):
        """50 successive manager instances writing and reading from real FileStorageBackend on disk."""
        rng = random.Random(1337)
        file_backend = FileStorageBackend(save_dir=str(tmp_path))

        expected_mute = False
        expected_volume = 1.0

        for step in range(50):
            # Create fresh manager referencing disk file backend
            mgr = AudioSettingsManager(backend=file_backend)

            # State check against oracle
            assert mgr.is_music_muted() == expected_mute, f"Disk step {step}: Mute mismatch"
            assert mgr.get_music_volume() == pytest.approx(expected_volume), f"Disk step {step}: Vol mismatch"

            # Random state modification
            action = rng.choice(["toggle", "set_mute", "set_volume"])
            if action == "toggle":
                expected_mute = mgr.toggle_music_muted()
            elif action == "set_mute":
                expected_mute = rng.choice([True, False])
                mgr.set_music_muted(expected_mute)
            elif action == "set_volume":
                expected_volume = round(rng.uniform(0.0, 1.0), 2)
                mgr.set_music_volume(expected_volume)

            # Ensure file exists and contains valid JSON
            save_path = tmp_path / f"{DEFAULT_SETTINGS_KEY}.json"
            assert save_path.exists()
            content = json.loads(save_path.read_text(encoding="utf-8"))
            assert content["music_muted"] == expected_mute
            assert content["music_volume"] == pytest.approx(expected_volume)

            del mgr


# =============================================================================
# 5. PRE-MUTED BOOT RESTORATION & ENGINE LIFECYCLE
# =============================================================================
class TestPreMutedBootRestorationAndLifecycle:
    """Tests engine instantiation when pre-muted in storage."""

    def test_boot_with_pre_muted_storage_starts_silenced(
        self, memory_backend: MemoryStorageBackend
    ):
        """If storage has music_muted=True, DynamicMusicEngine initializes silenced."""
        # Pre-seed storage
        memory_backend.set(
            DEFAULT_SETTINGS_KEY,
            json.dumps({"version": 1, "music_muted": True, "music_volume": 0.8}),
        )

        with patch("pygame.mixer.music.set_volume") as mock_set_vol:
            mgr = AudioSettingsManager(backend=memory_backend)
            engine = DynamicMusicEngine(settings_manager=mgr)

            assert engine.is_muted() is True
            # Hardware volume must immediately be silenced to 0.0 upon boot
            mock_set_vol.assert_called_with(0.0)

            # When starting track in pre-muted engine, track plays silenced
            engine.set_context(MusicContext.WELCOME)
            mock_set_vol.assert_called_with(0.0)

            # When unmuting, restores saved volume (0.8)
            engine.toggle_mute()
            assert engine.is_muted() is False
            mock_set_vol.assert_called_with(0.8)

    def test_rapid_mute_toggle_hammering(self, memory_backend: MemoryStorageBackend):
        """Rapidly hammering toggle_mute 500 times preserves perfect binary alternating state."""
        mgr = AudioSettingsManager(backend=memory_backend)
        engine = DynamicMusicEngine(settings_manager=mgr)

        for i in range(1, 501):
            new_state = engine.toggle_mute()
            expected = (i % 2 == 1)
            assert new_state == expected
            assert engine.is_muted() == expected
            assert mgr.is_music_muted() == expected

        # Storage must reflect final state (500 is even -> False)
        assert mgr.is_music_muted() is False
        reloaded = AudioSettingsManager(backend=memory_backend)
        assert reloaded.is_music_muted() is False
