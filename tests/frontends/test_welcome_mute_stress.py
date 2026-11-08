"""Adversarial stress and boundary verification tests for PygameWelcomeView mute UI.

Milestone 3 Challenger 2: Welcome Mute UI & Interaction Stress
Verification targets:
1. Rapid alternating clicks, 'M' keypresses, and mouse movements (200+ events and 500-event randomized fuzzing stream).
2. Boundary coordinate precision: precisely on the edge (820, 16), 1 pixel outside (819, 16), (944, 52), (945, 52), corners and edges.
3. Multi-instance persistence race conditions: multiple AudioSettingsManager and PygameWelcomeView instances sharing backend.
4. Corrupted backend JSON data handling and graceful recovery (truncated, malformed, invalid types, binary junk).
5. Zero crashes, zero memory leaks, and 100% correct mute state reflection across all draw/update cycles.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import tracemalloc
from typing import Any
from unittest.mock import patch
import pytest
import pygame

from src.core.events import AudioCue, AudioCueEvent, event_bus
from src.core.game_state import GameMode
from src.core.persistence import MemoryStorageBackend
from src.core.save_manager import FileStorageBackend
from src.core.session import GameSession
from src.frontends.pygame_ce.music_engine import (
    AudioSettingsData,
    AudioSettingsManager,
    DynamicMusicEngine,
    DEFAULT_SETTINGS_KEY,
)
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.welcome import PygameWelcomeView


@pytest.fixture(autouse=True)
def ensure_headless_env():
    """Ensure headless SDL drivers and clean mixer state."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    if not pygame.get_init():
        pygame.init()
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            pass
    from src.core.i18n import i18n
    prev_locale = i18n.locale
    yield
    i18n.locale = prev_locale
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
def music_engine(audio_settings: AudioSettingsManager) -> DynamicMusicEngine:
    """DynamicMusicEngine instance with isolated storage."""
    eng = DynamicMusicEngine(settings_manager=audio_settings)
    yield eng
    eng.stop()


@pytest.fixture
def welcome_view(music_engine: DynamicMusicEngine) -> PygameWelcomeView:
    """PygameWelcomeView wired to dynamic music engine."""
    return PygameWelcomeView(music_engine=music_engine)


@pytest.fixture
def session() -> GameSession:
    """Clean GameSession fixture."""
    return GameSession()


# =============================================================================
# 1. RAPID ALTERNATING INPUTS & ADVERSARIAL EVENT STREAM
# =============================================================================
class TestRapidAlternatingInputStress:
    """Stress tests rapid alternating inputs, keypresses, mouse events, and unhandled window events."""

    def test_250_rapid_alternating_clicks_keys_and_movements(
        self, welcome_view: PygameWelcomeView, session: GameSession, music_engine: DynamicMusicEngine
    ):
        """250 rapid alternating clicks on button, 'M' keypresses, and mouse motion.

        Verifies 100% synchronization of is_muted(), visual text, and settings persistence
        at every single transition without desync or memory explosion.
        """
        rect = welcome_view.get_mute_button_rect()
        inside_pos = rect.center
        outside_pos = (50, 50)

        expected_muted = False
        assert welcome_view.is_muted() == expected_muted
        assert welcome_view.get_mute_button_label() == "[♫ MUTE]"

        for i in range(250):
            phase = i % 4
            if phase == 0:
                # Left click inside button -> toggles mute
                ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=inside_pos)
                welcome_view.handle_event(ev, session)
                expected_muted = not expected_muted
            elif phase == 1:
                # Keypress 'M' -> toggles mute
                ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m)
                welcome_view.handle_event(ev, session)
                expected_muted = not expected_muted
            elif phase == 2:
                # Mouse motion inside button -> updates hover, does NOT toggle mute
                ev = pygame.event.Event(pygame.MOUSEMOTION, pos=inside_pos)
                welcome_view.handle_event(ev, session)
                assert welcome_view.is_mute_hovered is True
            elif phase == 3:
                # Mouse motion outside button -> updates hover, does NOT toggle mute
                ev = pygame.event.Event(pygame.MOUSEMOTION, pos=outside_pos)
                welcome_view.handle_event(ev, session)
                assert welcome_view.is_mute_hovered is False

            # Strict Invariants after every single operation
            assert welcome_view.is_muted() == expected_muted, f"Failed at iteration {i}"
            assert music_engine.is_muted() == expected_muted
            assert welcome_view.settings_manager.is_music_muted() == expected_muted
            expected_label = "[♫ UNMUTE]" if expected_muted else "[♫ MUTE]"
            assert welcome_view.get_mute_button_label() == expected_label
            assert welcome_view.mute_button_text == expected_label

    def test_500_randomized_mixed_input_fuzzing(
        self, welcome_view: PygameWelcomeView, session: GameSession, music_engine: DynamicMusicEngine
    ):
        """Adversarial fuzzing with 500 pseudo-random events from a deterministic seed.

        Includes clicks inside/outside, right clicks, middle clicks, scroll wheel,
        valid 'M' keys, unmapped keys, off-screen clicks, and motions.
        """
        rng = random.Random(1337)
        rect = welcome_view.get_mute_button_rect()
        inside_point = rect.center
        outside_points = [
            (0, 0),
            (100, 100),
            (819, 16),
            (944, 52),
            (-500, -500),
            (2500, 2500),
        ]
        other_keys = [
            pygame.K_UP,
            pygame.K_DOWN,
            pygame.K_w,
            pygame.K_s,
            pygame.K_RETURN,
            pygame.K_SPACE,
            pygame.K_ESCAPE,
            pygame.K_a,
            pygame.K_z,
            pygame.K_1,
            pygame.K_2,
        ]

        expected_muted = False
        click_cue_count = 0

        def cue_listener(ev: AudioCueEvent) -> None:
            nonlocal click_cue_count
            if ev.cue == AudioCue.CLICK:
                click_cue_count += 1

        event_bus.subscribe(AudioCueEvent, cue_listener)

        try:
            for step in range(500):
                action = rng.choice(
                    [
                        "click_inside",
                        "click_outside",
                        "right_click_inside",
                        "middle_click_inside",
                        "wheel_inside",
                        "key_m",
                        "key_other",
                        "motion_inside",
                        "motion_outside",
                        "motion_extreme",
                    ]
                )

                if action == "click_inside":
                    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=inside_point)
                    welcome_view.handle_event(ev, session)
                    expected_muted = not expected_muted

                elif action == "click_outside":
                    pt = rng.choice(outside_points)
                    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pt)
                    welcome_view.handle_event(ev, session)

                elif action == "right_click_inside":
                    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=inside_point)
                    welcome_view.handle_event(ev, session)

                elif action == "middle_click_inside":
                    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=2, pos=inside_point)
                    welcome_view.handle_event(ev, session)

                elif action == "wheel_inside":
                    btn = rng.choice([4, 5])
                    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=btn, pos=inside_point)
                    welcome_view.handle_event(ev, session)

                elif action == "key_m":
                    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m)
                    welcome_view.handle_event(ev, session)
                    expected_muted = not expected_muted

                elif action == "key_other":
                    k = rng.choice(other_keys)
                    ev = pygame.event.Event(pygame.KEYDOWN, key=k)
                    welcome_view.handle_event(ev, session)

                elif action == "motion_inside":
                    ev = pygame.event.Event(pygame.MOUSEMOTION, pos=inside_point)
                    welcome_view.handle_event(ev, session)
                    assert welcome_view.is_mute_hovered is True

                elif action == "motion_outside":
                    pt = rng.choice(outside_points)
                    ev = pygame.event.Event(pygame.MOUSEMOTION, pos=pt)
                    welcome_view.handle_event(ev, session)
                    assert welcome_view.is_mute_hovered is False

                elif action == "motion_extreme":
                    ev = pygame.event.Event(pygame.MOUSEMOTION, pos=(-9999, 9999))
                    welcome_view.handle_event(ev, session)
                    assert welcome_view.is_mute_hovered is False

                # Invariant verification at every single step
                assert welcome_view.is_muted() == expected_muted, (
                    f"Fuzz step {step} ({action}) desynchronized! Expected {expected_muted}, got {welcome_view.is_muted()}"
                )
                assert music_engine.is_muted() == expected_muted
                assert welcome_view.settings_manager.is_music_muted() == expected_muted
                label = welcome_view.get_mute_button_label()
                assert label == ("[♫ UNMUTE]" if expected_muted else "[♫ MUTE]")
        finally:
            event_bus.unsubscribe(AudioCueEvent, cue_listener)

    def test_simultaneous_click_and_key_in_same_frame(
        self, welcome_view: PygameWelcomeView, session: GameSession
    ):
        """Dispatches click and key 'M' in immediate succession without intermediate update.

        Two toggles in the same frame should cleanly flip from False -> True -> False.
        """
        rect = welcome_view.get_mute_button_rect()
        click_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        key_ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m)

        assert welcome_view.is_muted() is False

        # Dispatch both sequentially in same frame
        welcome_view.handle_event(click_ev, session)
        assert welcome_view.is_muted() is True
        welcome_view.handle_event(key_ev, session)
        assert welcome_view.is_muted() is False

        # Advance frame
        welcome_view.update(0.016, session)
        assert welcome_view.is_muted() is False
        assert welcome_view.get_mute_button_label() == "[♫ MUTE]"

    def test_rapid_window_focus_resize_and_unhandled_events(
        self, welcome_view: PygameWelcomeView, session: GameSession
    ):
        """Unhandled OS and window events (resize, focus, text, custom) cause zero crash or state change."""
        assert welcome_view.is_muted() is False

        unhandled_events = [
            pygame.event.Event(pygame.VIDEORESIZE, size=(1280, 720), w=1280, h=720),
            pygame.event.Event(pygame.ACTIVEEVENT, gain=1, state=1),
            pygame.event.Event(pygame.ACTIVEEVENT, gain=0, state=1),
            pygame.event.Event(pygame.WINDOWFOCUSGAINED),
            pygame.event.Event(pygame.WINDOWFOCUSLOST),
            pygame.event.Event(pygame.WINDOWMOVED, x=100, y=100),
            pygame.event.Event(pygame.KEYUP, key=pygame.K_m),
            pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=welcome_view.get_mute_button_rect().center),
            pygame.event.Event(pygame.TEXTINPUT, text="M"),
        ]

        for ev in unhandled_events:
            welcome_view.handle_event(ev, session)
            assert welcome_view.is_muted() is False
            assert welcome_view.get_mute_button_label() == "[♫ MUTE]"


# =============================================================================
# 2. BOUNDARY COORDINATE PRECISION & HOVER COLLISION
# =============================================================================
class TestBoundaryCoordinateClicks:
    """Micro-precision boundary tests for MUTE_BUTTON_RECT = Rect(820, 16, 124, 36).

    In Pygame, Rect(x, y, w, h) covers points [x, x+w) horizontally and [y, y+h) vertically:
    - Left boundary: 820 (inclusive)
    - Right boundary: 820 + 124 = 944 (exclusive: 943 is inside, 944 is outside)
    - Top boundary: 16 (inclusive)
    - Bottom boundary: 16 + 36 = 52 (exclusive: 51 is inside, 52 is outside)
    """

    @pytest.mark.parametrize(
        "inside_coord, description",
        [
            ((820, 16), "Top-left corner exact edge"),
            ((943, 16), "Top-right pixel inside rect"),
            ((820, 51), "Bottom-left pixel inside rect"),
            ((943, 51), "Bottom-right pixel inside rect"),
            ((882, 16), "Top edge midpoint"),
            ((882, 51), "Bottom edge midpoint inside"),
            ((820, 34), "Left edge midpoint"),
            ((943, 34), "Right edge midpoint inside"),
            ((882, 34), "Rect geometric center"),
        ],
    )
    def test_inside_boundary_clicks_toggle_mute(
        self,
        welcome_view: PygameWelcomeView,
        session: GameSession,
        inside_coord: tuple[int, int],
        description: str,
    ):
        """Clicking exactly on inclusive inner edges must toggle mute."""
        welcome_view.set_muted(False)
        assert welcome_view.is_muted() is False

        # Click inside
        ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=inside_coord)
        welcome_view.handle_event(ev, session)
        assert welcome_view.is_muted() is True, f"Failed inside toggle for {description} at {inside_coord}"

        # Click inside again to unmute
        welcome_view.handle_event(ev, session)
        assert welcome_view.is_muted() is False, f"Failed second inside toggle for {description} at {inside_coord}"

    @pytest.mark.parametrize(
        "outside_coord, description",
        [
            ((819, 16), "1 pixel left of top-left edge"),
            ((820, 15), "1 pixel above top-left edge"),
            ((819, 15), "1 pixel diagonally outside top-left"),
            ((944, 16), "On right boundary line at top"),
            ((945, 16), "1 pixel past right boundary line at top"),
            ((944, 51), "On right boundary line at bottom inside pixel height"),
            ((944, 52), "Precisely on outer bottom-right corner boundary"),
            ((945, 52), "1 pixel horizontally outside bottom-right corner"),
            ((944, 53), "1 pixel vertically outside bottom-right corner"),
            ((945, 53), "1 pixel diagonally outside bottom-right corner"),
            ((820, 52), "On bottom boundary line below left edge"),
            ((819, 52), "1 pixel outside bottom-left corner"),
            ((882, 15), "1 pixel above top edge midpoint"),
            ((882, 52), "On bottom boundary line at midpoint"),
            ((882, 53), "1 pixel below bottom boundary at midpoint"),
        ],
    )
    def test_outside_boundary_clicks_ignored(
        self,
        welcome_view: PygameWelcomeView,
        session: GameSession,
        outside_coord: tuple[int, int],
        description: str,
    ):
        """Clicking 1 pixel outside or on exclusive outer boundaries must NOT toggle mute."""
        welcome_view.set_muted(False)
        assert welcome_view.is_muted() is False

        ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=outside_coord)
        welcome_view.handle_event(ev, session)
        assert welcome_view.is_muted() is False, f"Erroneously toggled mute for {description} at {outside_coord}"

    def test_hover_state_matches_boundary_precision(
        self, welcome_view: PygameWelcomeView, session: GameSession
    ):
        """Hover state updates with exact 1-pixel boundary precision via MOUSEMOTION and update()."""
        # (820, 16) is inside -> hover True
        welcome_view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(820, 16)), session)
        assert welcome_view.is_mute_hovered is True

        # (819, 16) is outside -> hover False
        welcome_view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(819, 16)), session)
        assert welcome_view.is_mute_hovered is False

        # (943, 51) is inside -> hover True
        welcome_view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(943, 51)), session)
        assert welcome_view.is_mute_hovered is True

        # (944, 52) is outside -> hover False
        welcome_view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(944, 52)), session)
        assert welcome_view.is_mute_hovered is False

        # (945, 52) is outside -> hover False
        welcome_view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(945, 52)), session)
        assert welcome_view.is_mute_hovered is False

        # Also test via pygame.mouse.get_pos() in update()
        with patch("pygame.mouse.get_pos", return_value=(820, 16)):
            welcome_view.update(0.016, session)
            assert welcome_view.is_mute_hovered is True

        with patch("pygame.mouse.get_pos", return_value=(819, 16)):
            welcome_view.update(0.016, session)
            assert welcome_view.is_mute_hovered is False

        with patch("pygame.mouse.get_pos", return_value=(944, 52)):
            welcome_view.update(0.016, session)
            assert welcome_view.is_mute_hovered is False


# =============================================================================
# 3. MULTI-INSTANCE PERSISTENCE RACE CONDITIONS
# =============================================================================
class TestMultiInstancePersistenceRaces:
    """Adversarial multi-instance persistence, synchronization, and race condition tests."""

    def test_two_views_sharing_same_engine_synchronize_immediately(
        self, music_engine: DynamicMusicEngine, session: GameSession
    ):
        """Two PygameWelcomeView instances sharing an engine reflect toggles immediately."""
        view_1 = PygameWelcomeView(music_engine=music_engine)
        view_2 = PygameWelcomeView(music_engine=music_engine)

        assert view_1.is_muted() is False
        assert view_2.is_muted() is False
        assert view_1.get_mute_button_label() == "[♫ MUTE]"
        assert view_2.get_mute_button_label() == "[♫ MUTE]"

        # Toggle on view 1
        rect_1 = view_1.get_mute_button_rect()
        view_1.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect_1.center), session)

        assert view_1.is_muted() is True
        assert view_2.is_muted() is True
        assert view_1.get_mute_button_label() == "[♫ UNMUTE]"
        assert view_2.get_mute_button_label() == "[♫ UNMUTE]"

        # Toggle on view 2
        rect_2 = view_2.get_mute_button_rect()
        view_2.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect_2.center), session)

        assert view_1.is_muted() is False
        assert view_2.is_muted() is False
        assert view_1.get_mute_button_label() == "[♫ MUTE]"
        assert view_2.get_mute_button_label() == "[♫ MUTE]"

    def test_multiple_managers_sharing_same_storage_backend(
        self, memory_backend: MemoryStorageBackend, session: GameSession
    ):
        """Multiple independent AudioSettingsManager instances reading/writing to common backend."""
        # Manager A sets muted
        mgr_a = AudioSettingsManager(backend=memory_backend)
        mgr_b = AudioSettingsManager(backend=memory_backend)

        assert mgr_a.is_music_muted() is False
        assert mgr_b.is_music_muted() is False

        mgr_a.set_music_muted(True)
        assert mgr_a.is_music_muted() is True

        # Manager B reloads and observes persisted state
        assert mgr_b.load() is True
        assert mgr_b.is_music_muted() is True

        # Manager B toggles to unmuted
        mgr_b.toggle_music_muted()
        assert mgr_b.is_music_muted() is False

        # Manager A reloads and observes unmuted
        assert mgr_a.load() is True
        assert mgr_a.is_music_muted() is False

    def test_interleaved_multi_view_rapid_toggles(
        self, memory_backend: MemoryStorageBackend, session: GameSession
    ):
        """100 rapid interleaved toggles across 3 independent view instances."""
        views = []
        for _ in range(3):
            mgr = AudioSettingsManager(backend=memory_backend)
            eng = DynamicMusicEngine(settings_manager=mgr)
            v = PygameWelcomeView(music_engine=eng)
            views.append(v)

        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=views[0].get_mute_button_rect().center)

        current_state = False
        for i in range(100):
            chosen_view_idx = i % 3
            view = views[chosen_view_idx]
            view.handle_event(click, session)
            current_state = not current_state

            assert view.is_muted() == current_state

            # Sync other views via reload
            for other_idx, other_view in enumerate(views):
                if other_idx != chosen_view_idx:
                    other_view.settings_manager.load()
                    assert other_view.is_muted() == current_state
                    expected_label = "[♫ UNMUTE]" if current_state else "[♫ MUTE]"
                    assert other_view.get_mute_button_label() == expected_label

    def test_file_storage_backend_atomic_persistence_across_instances(
        self, tmp_path: Path, session: GameSession
    ):
        """FileStorageBackend on real disk survives rapid multi-instance re-launches."""
        backend_dir = str(tmp_path / "saves")

        for cycle in range(20):
            # Create fresh storage and manager (simulating process start)
            file_backend = FileStorageBackend(save_dir=backend_dir)
            settings = AudioSettingsManager(backend=file_backend)
            engine = DynamicMusicEngine(settings_manager=settings)
            view = PygameWelcomeView(music_engine=engine)

            expected_before = (cycle % 2 == 1)
            assert view.is_muted() == expected_before, f"Cycle {cycle} boot state mismatch"

            # Toggle state
            view.handle_event(
                pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=view.get_mute_button_rect().center),
                session,
            )
            expected_after = not expected_before
            assert view.is_muted() == expected_after

            # Verify saved file on disk is valid JSON
            save_file = tmp_path / "saves" / f"{DEFAULT_SETTINGS_KEY}.json"
            assert save_file.exists()
            content = json.loads(save_file.read_text(encoding="utf-8"))
            assert content["music_muted"] == expected_after


# =============================================================================
# 4. CORRUPTED BACKEND JSON DATA & GRACEFUL RECOVERY
# =============================================================================
class TestCorruptedBackendDataAndRecovery:
    """Stress tests verifying corrupt JSON handling, graceful fallbacks, and recovery on mute toggle."""

    @pytest.mark.parametrize(
        "corrupted_raw, description",
        [
            ("not json at all {[[", "Arbitrary non-JSON string"),
            ('{"version": 1, "music_muted": tr', "Truncated boolean literal"),
            ('{"music_muted": true,}', "Trailing comma syntax error"),
            ("", "Empty string"),
            ("   \n\t  ", "Whitespace only"),
            ("null", "JSON null primitive"),
            ("undefined", "JS undefined token"),
            ("12345", "JSON integer primitive"),
            ('"just a string"', "JSON string literal instead of object"),
            ("[true, false, 1]", "JSON list instead of object"),
            (
                '{"version": "BAD", "music_muted": "NOT_A_BOOL", "music_volume": "HIGH"}',
                "Type-confused dictionary payload",
            ),
            (
                '{"version": 999, "music_muted": 12345, "sfx_muted": "yes"}',
                "Integer and string mute values",
            ),
            (
                '{"music_volume": "NaN", "sfx_volume": "Infinity"}',
                "Stringified float specials",
            ),
            (
                "\x00\x01\x02\x03\xff\xfe\xca\xfe\xba\xbe",
                "Binary junk bytes",
            ),
            (
                "{" + '"key": "val", ' * 1000 + '"broken":',
                "Large broken dictionary payload",
            ),
        ],
    )
    def test_corrupted_payload_defaults_safely_and_recovers_on_toggle(
        self,
        memory_backend: MemoryStorageBackend,
        session: GameSession,
        corrupted_raw: str,
        description: str,
    ):
        """Corrupted storage payload must never crash welcome view, defaults safely, and heals on toggle."""
        # 1. Pre-seed corrupt data
        memory_backend.set(DEFAULT_SETTINGS_KEY, corrupted_raw)

        # 2. Instantiate AudioSettingsManager, engine, and welcome view
        settings = AudioSettingsManager(backend=memory_backend)
        engine = DynamicMusicEngine(settings_manager=settings)
        view = PygameWelcomeView(music_engine=engine)

        # Must safely default to unmuted
        assert view.is_muted() is False, f"Failed safe default for {description}"
        assert view.get_mute_button_label() == "[♫ MUTE]"

        # 3. Interacting with the mute button must heal the backend
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=view.get_mute_button_rect().center)
        view.handle_event(click, session)

        # New state must be muted
        assert view.is_muted() is True
        assert view.get_mute_button_label() == "[♫ UNMUTE]"

        # Backend must now hold 100% valid parseable JSON
        persisted_raw = memory_backend.get(DEFAULT_SETTINGS_KEY)
        assert persisted_raw is not None
        parsed = json.loads(persisted_raw)
        assert isinstance(parsed, dict)
        assert parsed.get("music_muted") is True
        assert isinstance(parsed.get("version"), int)
        assert parsed.get("version") >= 1

        # 4. Second toggle back to unmuted
        view.handle_event(click, session)
        assert view.is_muted() is False
        assert view.get_mute_button_label() == "[♫ MUTE]"

        parsed_2 = json.loads(memory_backend.get(DEFAULT_SETTINGS_KEY))
        assert parsed_2.get("music_muted") is False

    def test_mid_session_storage_corruption_recovery(
        self, welcome_view: PygameWelcomeView, memory_backend: MemoryStorageBackend, session: GameSession
    ):
        """If storage is corrupted mid-session while view is alive, subsequent load/save handles it gracefully."""
        assert welcome_view.is_muted() is False

        # External corruption occurs
        memory_backend.set(DEFAULT_SETTINGS_KEY, "CORRUPTED_MID_SESSION!@#$%^")

        # Reload settings
        assert welcome_view.settings_manager.load() is False
        assert welcome_view.is_muted() is False
        assert welcome_view.get_mute_button_label() == "[♫ MUTE]"

        # User presses 'M' -> heals storage
        welcome_view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m), session)
        assert welcome_view.is_muted() is True

        repaired_data = json.loads(memory_backend.get(DEFAULT_SETTINGS_KEY))
        assert repaired_data["music_muted"] is True


# =============================================================================
# 5. ZERO CRASHES, MEMORY LEAKS & 100% VISUAL STATE INVARIANTS
# =============================================================================
class TestMemoryLeakAndRenderingStress:
    """Stress tests rendering, memory stability, floating point pulse timers, and invariant consistency."""

    def test_300_draw_cycles_memory_stability(
        self, welcome_view: PygameWelcomeView, session: GameSession
    ):
        """300 render cycles while alternating mute states and hover states must not leak memory."""
        surface = pygame.Surface((960, 540))
        renderer = PygameRenderer()

        tracemalloc.start()
        try:
            # Warm up initial allocations (assets, fonts)
            for _ in range(50):
                welcome_view.draw(surface, renderer, session)

            snapshot_warm = tracemalloc.take_snapshot()

            # Execute 300 intensive draw cycles with state flips
            for i in range(300):
                welcome_view.set_muted(i % 2 == 0)
                welcome_view.mute_hovered = (i % 3 == 0)
                welcome_view.pulse_timer += 0.016
                welcome_view.draw(surface, renderer, session)

            snapshot_final = tracemalloc.take_snapshot()
            stats = snapshot_final.compare_to(snapshot_warm, "lineno")
            total_diff_kb = sum(stat.size_diff for stat in stats) / 1024.0

            # Memory growth between iteration 50 and 350 must be negligible (< 750 KB)
            assert total_diff_kb < 750, f"Possible memory leak detected: {total_diff_kb:.2f} KB growth"
        finally:
            tracemalloc.stop()

    def test_pulse_timer_floating_point_and_dt_stress(
        self, welcome_view: PygameWelcomeView, session: GameSession
    ):
        """Update pulse timer over 10,000 frames with extreme dt values (zero, negative, huge, tiny).

        Verifies no math domain errors, NaN, or overflow in math.sin calculations.
        """
        surface = pygame.Surface((960, 540))
        renderer = PygameRenderer()

        extreme_dts = [0.0, 0.016, 0.033, 1000.0, 0.00001, -0.5, 1e-6]

        for step, dt in enumerate(extreme_dts * 1500):  # 10,500 iterations
            welcome_view.update(dt, session)
            assert not (welcome_view.pulse_timer != welcome_view.pulse_timer), "pulse_timer became NaN"

        # Ensure draw renders without math domain crash after extreme pulse timer
        welcome_view.draw(surface, renderer, session)

    def test_view_alias_property_invariants(
        self, welcome_view: PygameWelcomeView, music_engine: DynamicMusicEngine
    ):
        """Verifies property aliases remain strictly synchronized in all states.

        - mute_button_rect == mute_rect == get_mute_button_rect()
        - is_mute_hovered == mute_hovered
        - mute_button_text == get_mute_button_label()
        """
        for state in (False, True):
            welcome_view.set_muted(state)
            assert welcome_view.is_muted() == state
            assert (welcome_view.mute_button_text == "[♫ UNMUTE]") if state else (welcome_view.mute_button_text == "[♫ MUTE]")
            assert welcome_view.mute_button_text == welcome_view.get_mute_button_label()

        for hover in (False, True):
            welcome_view.is_mute_hovered = hover
            assert welcome_view.mute_hovered == hover
            assert welcome_view.is_mute_hovered == hover

        assert welcome_view.mute_button_rect == welcome_view.mute_rect
        assert welcome_view.get_mute_button_rect() == welcome_view.mute_rect
