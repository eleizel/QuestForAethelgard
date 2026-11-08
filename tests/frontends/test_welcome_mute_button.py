"""Comprehensive unit and integration test suite for the Welcome Screen Mute Button.

Covers Milestone 3 requirements:
- Welcome screen visual mute/unmute button bounding box, dimensions, and positioning.
- Layout isolation: zero collision with title logo and main menu frame.
- Mouse click interaction toggling mute state on engine and AudioSettingsManager.
- Audio feedback: clicking emits AudioCue.CLICK on event_bus.
- Mouse hover tracking and visual state updates.
- Keyboard shortcut 'M' (pygame.K_m) toggling mute state.
- Dynamic visual text reflection: '[♫ MUTE]' when unmuted vs '[♫ UNMUTE]' when muted.
- Settings persistence across mock application restart cycles.
- Headless CI execution resilience with uninitialized mixer and dummy drivers.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest
import pygame

from src.core.events import AudioCue, AudioCueEvent, event_bus
from src.core.game_state import GameMode
from src.core.persistence import MemoryStorageBackend
from src.core.session import GameSession
from src.frontends.pygame_ce.app import PygameApp
from src.frontends.pygame_ce.music_engine import (
    AudioSettingsManager,
    DynamicMusicEngine,
)
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.welcome import PygameWelcomeView


@pytest.fixture(autouse=True)
def ensure_headless_env():
    """Ensure headless SDL dummy drivers and clean mixer teardown."""
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
    """PygameWelcomeView instance wired with test music engine."""
    view = PygameWelcomeView(music_engine=music_engine)
    if hasattr(view, "music_engine"):
        view.music_engine = music_engine
    else:
        setattr(view, "music_engine", music_engine)
    return view


def get_mute_rect(view: PygameWelcomeView) -> pygame.Rect:
    """Helper resolving mute button bounding box across naming conventions."""
    if hasattr(view, "mute_rect"):
        return view.mute_rect
    elif hasattr(view, "mute_button_rect"):
        return view.mute_button_rect
    raise AttributeError("PygameWelcomeView missing 'mute_rect' or 'mute_button_rect' attribute")


def get_mute_label(view: PygameWelcomeView) -> str:
    """Helper resolving visual mute button label across naming conventions."""
    if hasattr(view, "get_mute_button_label"):
        return view.get_mute_button_label()
    elif hasattr(view, "mute_button_text"):
        return view.mute_button_text
    elif hasattr(view, "is_muted"):
        return "[♫ UNMUTE]" if view.is_muted() else "[♫ MUTE]"
    raise AttributeError("PygameWelcomeView missing label helper or is_muted property")


# =============================================================================
# 1. MUTE BUTTON BOUNDING BOX & LAYOUT
# =============================================================================
class TestWelcomeMuteButtonLayout:
    """Tests for button dimensions, coordinates, and non-overlapping positioning."""

    def test_mute_button_rect_dimensions(self, welcome_view: PygameWelcomeView):
        """Button rect has positive dimensions and conforms to UI button proportions."""
        rect = get_mute_rect(welcome_view)
        assert isinstance(rect, pygame.Rect)
        assert 80 <= rect.width <= 200, f"Button width {rect.width} out of expected range [80, 200]"
        assert 24 <= rect.height <= 60, f"Button height {rect.height} out of expected range [24, 60]"

    def test_mute_button_placement_top_right(self, welcome_view: PygameWelcomeView):
        """Button is placed in top-right area of 960x540 viewport."""
        rect = get_mute_rect(welcome_view)
        assert rect.left >= 0 and rect.top >= 0
        assert rect.right <= 960 and rect.bottom <= 540
        assert rect.right >= 800, f"Button right {rect.right} should be near right edge"
        assert rect.top <= 100, f"Button top {rect.top} should be near top edge"

    def test_mute_button_no_collision_with_menu_frame(self, welcome_view: PygameWelcomeView):
        """Mute button bounding box does not overlap central ornate menu frame."""
        rect = get_mute_rect(welcome_view)
        frame_rect = pygame.Rect((960 - 360) // 2, 172, 360, 260)
        assert not rect.colliderect(frame_rect), "Mute button overlaps main menu frame!"

    def test_mute_button_no_collision_with_title_logo(self, welcome_view: PygameWelcomeView):
        """Mute button bounding box does not overlap top title logo area."""
        rect = get_mute_rect(welcome_view)
        logo_rect = pygame.Rect((960 - 640) // 2, 40, 640, 90)
        assert not rect.colliderect(logo_rect), "Mute button overlaps title logo!"

    def test_mute_button_rendering_no_crash(self, welcome_view: PygameWelcomeView):
        """Calling draw on welcome view renders the mute button cleanly."""
        surface = pygame.Surface((960, 540))
        renderer = PygameRenderer()
        session = GameSession()
        welcome_view.draw(surface, renderer, session)


# =============================================================================
# 2. MOUSE CLICK & HOVER INTERACTION
# =============================================================================
class TestWelcomeMuteButtonMouseInteraction:
    """Tests for mouse click collisions, toggling mute, and hover states."""

    def test_mouse_click_inside_button_toggles_mute(
        self, welcome_view: PygameWelcomeView, music_engine: DynamicMusicEngine
    ):
        """Left click inside mute rect toggles is_muted from False to True."""
        session = GameSession()
        rect = get_mute_rect(welcome_view)
        assert music_engine.is_muted() is False

        click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        welcome_view.handle_event(click_event, session)

        assert music_engine.is_muted() is True
        assert music_engine.settings_manager.is_music_muted() is True

    def test_second_mouse_click_toggles_unmute(
        self, welcome_view: PygameWelcomeView, music_engine: DynamicMusicEngine
    ):
        """Second left click inside mute rect toggles is_muted back to False."""
        session = GameSession()
        rect = get_mute_rect(welcome_view)

        # 1st click -> muted
        click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        welcome_view.handle_event(click_event, session)
        assert music_engine.is_muted() is True

        # 2nd click -> unmuted
        welcome_view.handle_event(click_event, session)
        assert music_engine.is_muted() is False
        assert music_engine.settings_manager.is_music_muted() is False

    def test_mouse_click_outside_button_ignored(
        self, welcome_view: PygameWelcomeView, music_engine: DynamicMusicEngine
    ):
        """Click outside mute rect does not toggle mute state."""
        session = GameSession()
        assert music_engine.is_muted() is False

        click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 10))
        welcome_view.handle_event(click_event, session)

        assert music_engine.is_muted() is False

    def test_mouse_right_click_ignored(
        self, welcome_view: PygameWelcomeView, music_engine: DynamicMusicEngine
    ):
        """Right click (button=3) inside mute rect does not toggle mute state."""
        session = GameSession()
        rect = get_mute_rect(welcome_view)
        assert music_engine.is_muted() is False

        right_click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=rect.center)
        welcome_view.handle_event(right_click, session)

        assert music_engine.is_muted() is False

    def test_mouse_click_emits_audio_cue(
        self, welcome_view: PygameWelcomeView
    ):
        """Clicking the mute button emits AudioCue.CLICK on event_bus."""
        session = GameSession()
        rect = get_mute_rect(welcome_view)
        captured_cues: list[AudioCue] = []

        def cue_listener(ev: AudioCueEvent) -> None:
            captured_cues.append(ev.cue)

        event_bus.subscribe(AudioCueEvent, cue_listener)
        try:
            click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
            welcome_view.handle_event(click_event, session)
            assert AudioCue.CLICK in captured_cues
        finally:
            event_bus.unsubscribe(AudioCueEvent, cue_listener)

    def test_mouse_hover_tracking(self, welcome_view: PygameWelcomeView):
        """Hover state is updated when mouse position is inside the button."""
        session = GameSession()
        rect = get_mute_rect(welcome_view)

        with patch("pygame.mouse.get_pos", return_value=rect.center):
            welcome_view.update(0.016, session)
            assert getattr(welcome_view, "mute_hovered", False) is True

        with patch("pygame.mouse.get_pos", return_value=(0, 0)):
            welcome_view.update(0.016, session)
            assert getattr(welcome_view, "mute_hovered", False) is False


# =============================================================================
# 3. KEYBOARD SHORTCUT INTERACTION
# =============================================================================
class TestWelcomeMuteButtonKeyboardInteraction:
    """Tests for keyboard shortcut 'M' toggling mute state."""

    def test_key_m_toggles_mute(
        self, welcome_view: PygameWelcomeView, music_engine: DynamicMusicEngine
    ):
        """Pressing 'M' key toggles is_muted from False to True."""
        session = GameSession()
        assert music_engine.is_muted() is False

        event_m = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m)
        welcome_view.handle_event(event_m, session)

        assert music_engine.is_muted() is True
        assert music_engine.settings_manager.is_music_muted() is True

    def test_key_m_second_press_unmutes(
        self, welcome_view: PygameWelcomeView, music_engine: DynamicMusicEngine
    ):
        """Pressing 'M' key again toggles is_muted back to False."""
        session = GameSession()
        event_m = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m)

        # 1st press
        welcome_view.handle_event(event_m, session)
        assert music_engine.is_muted() is True

        # 2nd press
        welcome_view.handle_event(event_m, session)
        assert music_engine.is_muted() is False

    def test_other_keys_do_not_toggle_mute(
        self, welcome_view: PygameWelcomeView, music_engine: DynamicMusicEngine
    ):
        """Keys other than 'M' (e.g. SPACE, RETURN, UP, 1) do not toggle mute."""
        session = GameSession()
        for key in (pygame.K_SPACE, pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s):
            welcome_view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key), session)
            assert music_engine.is_muted() is False


# =============================================================================
# 4. VISUAL STATE STRING UPDATING
# =============================================================================
class TestWelcomeMuteButtonVisualState:
    """Tests verifying visual label updates reflecting mute/unmute state."""

    def test_visual_text_unmuted_state(
        self, welcome_view: PygameWelcomeView, music_engine: DynamicMusicEngine
    ):
        """When unmuted, label displays '[♫ MUTE]'."""
        music_engine.set_muted(False)
        label = get_mute_label(welcome_view)
        assert "MUTE" in label and "UNMUTE" not in label
        assert label == "[♫ MUTE]"

    def test_visual_text_muted_state(
        self, welcome_view: PygameWelcomeView, music_engine: DynamicMusicEngine
    ):
        """When muted, label updates to '[♫ UNMUTE]'."""
        music_engine.set_muted(True)
        label = get_mute_label(welcome_view)
        assert "UNMUTE" in label
        assert label == "[♫ UNMUTE]"

    def test_drawing_both_visual_states_no_error(
        self, welcome_view: PygameWelcomeView, music_engine: DynamicMusicEngine
    ):
        """Renders cleanly in both unmuted and muted visual states."""
        surface = pygame.Surface((960, 540))
        renderer = PygameRenderer()
        session = GameSession()

        # Unmuted draw
        music_engine.set_muted(False)
        welcome_view.draw(surface, renderer, session)

        # Muted draw
        music_engine.set_muted(True)
        welcome_view.draw(surface, renderer, session)


# =============================================================================
# 5. MUTE PERSISTENCE ACROSS RE-LAUNCH
# =============================================================================
class TestWelcomeMuteButtonPersistence:
    """Tests for mute persistence across mock game restarts."""

    def test_mute_persists_across_mock_relaunch(
        self, memory_backend: MemoryStorageBackend
    ):
        """Toggling mute in session 1 persists to session 2 on mock re-launch."""
        # --- Session 1: Launch unmuted, click mute ---
        settings_1 = AudioSettingsManager(backend=memory_backend)
        engine_1 = DynamicMusicEngine(settings_manager=settings_1)
        view_1 = PygameWelcomeView()
        setattr(view_1, "music_engine", engine_1)
        session_1 = GameSession()

        assert engine_1.is_muted() is False
        assert get_mute_label(view_1) == "[♫ MUTE]"

        # Click mute
        rect_1 = get_mute_rect(view_1)
        view_1.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect_1.center), session_1)
        assert engine_1.is_muted() is True
        assert get_mute_label(view_1) == "[♫ UNMUTE]"

        # --- Session 2: Fresh mock re-launch with same storage backend ---
        settings_2 = AudioSettingsManager(backend=memory_backend)
        engine_2 = DynamicMusicEngine(settings_manager=settings_2)
        view_2 = PygameWelcomeView()
        setattr(view_2, "music_engine", engine_2)
        session_2 = GameSession()

        assert engine_2.is_muted() is True
        assert get_mute_label(view_2) == "[♫ UNMUTE]"

    def test_unmute_persists_across_mock_relaunch(
        self, memory_backend: MemoryStorageBackend
    ):
        """Unmuting in session 1 persists as unmuted in session 2."""
        # Pre-seed muted
        initial_settings = AudioSettingsManager(backend=memory_backend)
        initial_settings.set_music_muted(True)
        initial_settings.save()

        # Session 1: Launches muted, clicks unmute
        engine_1 = DynamicMusicEngine(settings_manager=AudioSettingsManager(backend=memory_backend))
        view_1 = PygameWelcomeView()
        setattr(view_1, "music_engine", engine_1)
        assert engine_1.is_muted() is True

        rect_1 = get_mute_rect(view_1)
        view_1.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect_1.center), GameSession())
        assert engine_1.is_muted() is False

        # Session 2: Mock re-launch
        engine_2 = DynamicMusicEngine(settings_manager=AudioSettingsManager(backend=memory_backend))
        view_2 = PygameWelcomeView()
        setattr(view_2, "music_engine", engine_2)
        assert engine_2.is_muted() is False
        assert get_mute_label(view_2) == "[♫ MUTE]"


# =============================================================================
# 6. EDGE CASES & STRESS
# =============================================================================
class TestWelcomeMuteButtonEdgeCases:
    """Tests for standalone instantiation, uninitialized mixer, and rapid toggling."""

    def test_standalone_view_instantiation_without_engine(self):
        """PygameWelcomeView can be instantiated standalone without crashing."""
        view = PygameWelcomeView()
        rect = get_mute_rect(view)
        assert rect is not None
        label = get_mute_label(view)
        assert "MUTE" in label

    def test_rapid_mouse_clicks_stability(
        self, welcome_view: PygameWelcomeView, music_engine: DynamicMusicEngine
    ):
        """50 rapid clicks alternate mute state reliably without desynchronization."""
        session = GameSession()
        rect = get_mute_rect(welcome_view)
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)

        expected = False
        for _ in range(50):
            welcome_view.handle_event(click, session)
            expected = not expected
            assert music_engine.is_muted() == expected
            assert music_engine.settings_manager.is_music_muted() == expected

    def test_uninitialized_mixer_safety(self, memory_backend: MemoryStorageBackend):
        """Clicking mute button when mixer is uninitialized updates settings safely."""
        was_init = bool(pygame.mixer.get_init())
        if was_init:
            pygame.mixer.quit()

        try:
            settings = AudioSettingsManager(backend=memory_backend)
            engine = DynamicMusicEngine(settings_manager=settings, auto_init_mixer=False)
            view = PygameWelcomeView()
            setattr(view, "music_engine", engine)
            session = GameSession()

            rect = get_mute_rect(view)
            click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
            view.handle_event(click, session)

            assert settings.is_music_muted() is True
        finally:
            if was_init and not pygame.mixer.get_init():
                try:
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                except Exception:
                    pass
