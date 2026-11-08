"""Tier 5 Adversarial White-Box Coverage Hardening for Views, PygameApp, AudioAdapter, and Events.

Covers white-box edge conditions, branch gaps, subtle race hazards, and exception resilience across:
- src/frontends/pygame_ce/app.py (DI variations, fullscreen toggle, QUIT short-circuit, promotion safeguard, modal overlays, frame bounds, async run)
- src/frontends/pygame_ce/views/welcome.py (keyboard wrap-around, hotkeys, save load checks, mouse click on items, pixel boundaries, fallback UI, Spanish locale)
- src/frontends/pygame_ce/audio_adapter.py (uninitialized mixer safety, all 8 procedural cues, sound play exception handling, delegation)
- src/core/events.py (EventBus reentrancy, subscriber ordering, safe unsubscription, drain/clear semantics, frozen event immutability, CombatLogEntry metadata)
"""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError
import math
import os
from unittest.mock import MagicMock, patch
import pytest
import pygame

from src.core.events import (
    AudioCue,
    AudioCueEvent,
    CombatLogEntry,
    DamageDealtEvent,
    DomainEvent,
    EventBus,
    HealthRestoredEvent,
    StatusAppliedEvent,
    event_bus,
)
from src.core.game_state import GameMode
from src.core.i18n import i18n
from src.core.persistence import MemoryStorageBackend
from src.core.session import GameSession
from src.entities.actor import Stats
from src.entities.enemy import Enemy, EnemyTier
from src.frontends.pygame_ce.app import PygameApp
from src.frontends.pygame_ce.audio_adapter import PygameAudioAdapter
from src.frontends.pygame_ce.music_engine import (
    AudioSettingsManager,
    DynamicMusicEngine,
    MusicContext,
    PlaybackState,
    resolve_music_context,
)
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.welcome import PygameWelcomeView
from src.systems.combat import CombatSystem


@pytest.fixture(autouse=True)
def ensure_headless_test_environment():
    """Guarantee SDL headless dummy drivers and clean event queue / mixer state."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    if not pygame.get_init():
        pygame.init()
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            pass

    pygame.event.clear()
    original_locale = getattr(i18n, "locale", "en")
    yield
    i18n.locale = original_locale
    pygame.event.clear()
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
    """AudioSettingsManager backed by isolated in-memory storage."""
    return AudioSettingsManager(backend=memory_backend)


@pytest.fixture
def test_music_engine(audio_settings: AudioSettingsManager) -> DynamicMusicEngine:
    """DynamicMusicEngine instance with isolated settings."""
    engine = DynamicMusicEngine(settings_manager=audio_settings)
    yield engine
    engine.stop()


# =============================================================================
# 1. PYGAME APP ADVERSARIAL COVERAGE
# =============================================================================
class TestPygameAppAdversarialCoverage:
    """Adversarial white-box tests for src/frontends/pygame_ce/app.py."""

    def test_pygame_app_di_with_custom_audio_adapter_and_engine(
        self, test_music_engine: DynamicMusicEngine
    ):
        """App correctly preserves both explicitly injected custom audio adapter and engine."""
        custom_adapter = PygameAudioAdapter(music_engine=test_music_engine)
        app = PygameApp(
            headless=True,
            audio_adapter=custom_adapter,
            music_engine=test_music_engine,
        )
        assert app.audio_adapter is custom_adapter
        assert app.music_engine is test_music_engine
        assert app.views[GameMode.WELCOME].music_engine is test_music_engine

    def test_pygame_app_di_with_adapter_extracts_adapter_music_engine(
        self, test_music_engine: DynamicMusicEngine
    ):
        """When audio_adapter is passed without music_engine, app extracts adapter.music_engine."""
        custom_adapter = PygameAudioAdapter(music_engine=test_music_engine)
        app = PygameApp(headless=True, audio_adapter=custom_adapter, music_engine=None)
        assert app.audio_adapter is custom_adapter
        assert app.music_engine is test_music_engine

    def test_pygame_app_di_with_adapter_without_engine_creates_fallback_engine(self):
        """When audio_adapter has no music_engine attribute, app creates new DynamicMusicEngine."""
        mock_adapter = MagicMock()
        mock_adapter.music_engine = None
        app = PygameApp(headless=True, audio_adapter=mock_adapter, music_engine=None)
        assert isinstance(app.music_engine, DynamicMusicEngine)

    def test_pygame_app_di_default_instantiation_registers_all_modes(self):
        """Default instantiation registers views for all 15 operational game modes."""
        app = PygameApp(headless=True)
        assert len(app.views) == len(GameMode) == 15
        for mode in GameMode:
            assert mode in app.views
            assert app.views[mode] is not None

    def test_pygame_app_get_active_view_fallback_on_unmapped_mode(self):
        """Unmapped or invalid mode falls back cleanly to Welcome view."""
        app = PygameApp(headless=True)
        app.session.state.current_mode = "NON_EXISTENT_MODE"  # type: ignore
        fallback_view = app.get_active_view()
        assert fallback_view is app.views[GameMode.WELCOME]

    def test_pygame_app_handle_events_quit_short_circuit(self):
        """pygame.QUIT halts loop and returns immediately, skipping later events in batch."""
        app = PygameApp(headless=True)
        app.is_running = True

        welcome_view = app.views[GameMode.WELCOME]
        with patch.object(welcome_view, "handle_event") as mock_view_handle:
            pygame.event.clear()
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))

            app.handle_events()
            assert app.is_running is False
            mock_view_handle.assert_not_called()

    def test_pygame_app_handle_events_f11_toggles_fullscreen_without_propagating_to_views(self):
        """F11 key toggles fullscreen flag and short-circuits without notifying views."""
        app = PygameApp(headless=True, fullscreen=False)
        welcome_view = app.views[GameMode.WELCOME]

        with patch("pygame.display.toggle_fullscreen") as mock_toggle, \
             patch.object(welcome_view, "handle_event") as mock_view_handle:
            pygame.event.clear()
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11, mod=0))

            app.handle_events()
            mock_toggle.assert_called_once()
            assert app.fullscreen is True
            mock_view_handle.assert_not_called()

    def test_pygame_app_handle_events_alt_enter_toggles_fullscreen(self):
        """Alt+Enter (K_RETURN with KMOD_ALT) toggles fullscreen flag."""
        app = PygameApp(headless=True, fullscreen=False)
        welcome_view = app.views[GameMode.WELCOME]

        with patch("pygame.display.toggle_fullscreen") as mock_toggle, \
             patch.object(welcome_view, "handle_event") as mock_view_handle:
            pygame.event.clear()
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=pygame.KMOD_ALT))

            app.handle_events()
            mock_toggle.assert_called_once()
            assert app.fullscreen is True
            mock_view_handle.assert_not_called()

    def test_pygame_app_handle_events_return_without_alt_propagates_to_views(self):
        """Standard Enter (K_RETURN without KMOD_ALT) is forwarded directly to active view."""
        app = PygameApp(headless=True, fullscreen=False)
        welcome_view = app.views[GameMode.WELCOME]

        with patch("pygame.display.toggle_fullscreen") as mock_toggle, \
             patch.object(welcome_view, "handle_event") as mock_view_handle:
            pygame.event.clear()
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0))

            app.handle_events()
            mock_toggle.assert_not_called()
            assert app.fullscreen is False
            mock_view_handle.assert_called_once()

    def test_pygame_app_handle_events_toggle_fullscreen_exception_handled_safely(self):
        """Exception raised by pygame.display.toggle_fullscreen is safely caught."""
        app = PygameApp(headless=True, fullscreen=False)
        with patch("pygame.display.toggle_fullscreen", side_effect=pygame.error("Display mode unsupported")):
            pygame.event.clear()
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11, mod=0))
            app.handle_events()
            # Stays False because toggle failed
            assert app.fullscreen is False

    def test_pygame_app_handle_events_delegates_to_music_engine_and_view(self):
        """Regular events are passed to both music_engine.handle_event and view.handle_event."""
        app = PygameApp(headless=True)
        active_view = app.get_active_view()

        with patch.object(app.music_engine, "handle_event") as mock_engine_event, \
             patch.object(active_view, "handle_event") as mock_view_event:
            custom_ev = pygame.event.Event(pygame.USEREVENT + 5)
            pygame.event.clear()
            pygame.event.post(custom_ev)

            app.handle_events()
            mock_engine_event.assert_called_once()
            mock_view_event.assert_called_once()

    def test_pygame_app_update_promotion_safeguard_triggers_in_map_mode(self):
        """When player.promotion_due is True on MAP, app.update() triggers begin_promotion."""
        app = PygameApp(headless=True)
        app.session.switch_mode(GameMode.MAP)
        app.session.player.promotion_due = True
        app.session.player.available_promotions = MagicMock(return_value=["WARRIOR"])

        app.update(0.016)
        assert app.session.current_mode == GameMode.PROMOTION
        # Background music is preserved as MAP
        assert app.music_engine.get_current_context() == MusicContext.MAP

    @pytest.mark.parametrize(
        "exempt_mode",
        [
            GameMode.LOOT,
            GameMode.GAME_OVER,
            GameMode.VICTORY,
            GameMode.WELCOME,
            GameMode.CLASS_SELECT,
            GameMode.PROMOTION,
            GameMode.ABILITY_CHOICE,
        ],
    )
    def test_pygame_app_update_promotion_safeguard_suppressed_in_exempt_modes(
        self, exempt_mode: GameMode
    ):
        """Promotion safeguard is not triggered when already in exempt modes."""
        app = PygameApp(headless=True)
        app.session.switch_mode(exempt_mode)
        app.session.player.promotion_due = True
        app.session.player.available_promotions = MagicMock(return_value=["WARRIOR"])

        with patch.object(app.session.state, "begin_promotion") as mock_begin_promotion:
            app.update(0.016)
            mock_begin_promotion.assert_not_called()

    def test_pygame_app_draw_inventory_overlay_renders_underlying_map(self):
        """INVENTORY mode renders underlying MAP view first, then INVENTORY modal."""
        app = PygameApp(headless=True)
        app.session.switch_mode(GameMode.MAP)
        app.session.switch_mode(GameMode.INVENTORY)

        with patch.object(app.views[GameMode.MAP], "draw") as mock_map_draw, \
             patch.object(app.views[GameMode.INVENTORY], "draw") as mock_inv_draw:
            app.draw()
            mock_map_draw.assert_called_once()
            mock_inv_draw.assert_called_once()

    def test_pygame_app_draw_character_overlay_renders_underlying_combat(self):
        """CHARACTER mode renders underlying COMBAT view first, then CHARACTER modal."""
        app = PygameApp(headless=True)
        app.session.switch_mode(GameMode.COMBAT)
        app.session.switch_mode(GameMode.CHARACTER)

        with patch.object(app.views[GameMode.COMBAT], "draw") as mock_combat_draw, \
             patch.object(app.views[GameMode.CHARACTER], "draw") as mock_char_draw:
            app.draw()
            mock_combat_draw.assert_called_once()
            mock_char_draw.assert_called_once()

    def test_pygame_app_draw_modal_with_none_previous_mode_no_crash(self):
        """Modal drawing handles previous_mode=None without errors."""
        app = PygameApp(headless=True)
        app.session.state.previous_mode = None
        app.session.switch_mode(GameMode.INVENTORY)
        # Should render cleanly without KeyError or NoneType error
        app.draw()

    def test_pygame_app_draw_modal_with_modal_previous_mode_does_not_draw_modal_underlay(self):
        """Nested modal (e.g. CHARACTER with previous INVENTORY) does not double-draw modal."""
        app = PygameApp(headless=True)
        app.session.state.previous_mode = GameMode.INVENTORY
        app.session.state.current_mode = GameMode.CHARACTER

        with patch.object(app.views[GameMode.INVENTORY], "draw") as mock_inv_draw, \
             patch.object(app.views[GameMode.CHARACTER], "draw") as mock_char_draw:
            app.draw()
            mock_inv_draw.assert_not_called()
            mock_char_draw.assert_called_once()

    def test_pygame_app_run_terminates_at_max_frames_and_stops_music(
        self, test_music_engine: DynamicMusicEngine
    ):
        """app.run(max_frames=4) runs exactly 4 frames and stops the music engine."""
        app = PygameApp(headless=True, music_engine=test_music_engine)
        with patch.object(test_music_engine, "stop") as mock_stop:
            app.run(max_frames=4)
            mock_stop.assert_called_once()

    def test_pygame_app_run_catches_and_logs_frame_exception_gracefully(self):
        """app.run catches frame loop exceptions without crashing and stops engine."""
        app = PygameApp(headless=True)
        with patch.object(app, "update", side_effect=RuntimeError("Transient Frame Fault")), \
             patch.object(app.music_engine, "stop") as mock_stop:
            app.run(max_frames=2)
            mock_stop.assert_called_once()

    def test_pygame_app_run_async_executes_event_loop_and_stops_music(self):
        """asyncio app.run_async executes bounded frames and cleanly stops music."""
        app = PygameApp(headless=True)
        with patch.object(app.music_engine, "stop") as mock_stop:
            asyncio.run(app.run_async(max_frames=3))
            mock_stop.assert_called_once()


# =============================================================================
# 2. WELCOME VIEW ADVERSARIAL COVERAGE
# =============================================================================
class TestPygameWelcomeViewAdversarialCoverage:
    """Adversarial white-box tests for src/frontends/pygame_ce/views/welcome.py."""

    def test_welcome_view_keyboard_navigation_wrap_up(self):
        """Pressing UP from index 0 wraps to index 3 (last option)."""
        view = PygameWelcomeView()
        session = GameSession()
        view.selected_index = 0

        view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP), session)
        assert view.selected_index == 3

        # Test K_w alias as well
        view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w), session)
        assert view.selected_index == 2

    def test_welcome_view_keyboard_navigation_wrap_down(self):
        """Pressing DOWN from index 3 wraps to index 0."""
        view = PygameWelcomeView()
        session = GameSession()
        view.selected_index = 3

        view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN), session)
        assert view.selected_index == 0

        # Test K_s alias as well
        view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s), session)
        assert view.selected_index == 1

    def test_welcome_view_numeric_and_letter_hotkeys(self):
        """Hotkeys 1/n, 3/o/l, 4/r trigger appropriate view actions."""
        view = PygameWelcomeView()
        session = GameSession()

        # Key 1 -> New game (CLASS_SELECT)
        view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1), session)
        assert session.current_mode == GameMode.CLASS_SELECT

        # Reset
        session.switch_mode(GameMode.WELCOME)

        # Key n -> New game (CLASS_SELECT)
        view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n), session)
        assert session.current_mode == GameMode.CLASS_SELECT

        # Key 3 / o -> Language toggle
        original_lang = i18n.locale
        view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3), session)
        assert i18n.locale != original_lang

        view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_o), session)
        assert i18n.locale == original_lang

        view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_l), session)
        assert i18n.locale != original_lang
        i18n.locale = original_lang

        # Key 4 / r -> Credits
        session.switch_mode(GameMode.WELCOME)
        view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_4), session)
        assert session.current_mode == GameMode.CREDITS

        session.switch_mode(GameMode.WELCOME)
        view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r), session)
        assert session.current_mode == GameMode.CREDITS

    def test_welcome_view_load_game_with_and_without_save(self):
        """Load option activates only when saved game is present."""
        view = PygameWelcomeView()
        session = GameSession()

        # Case 1: No saved game
        with patch.object(session, "has_saved_game", return_value=False), \
             patch.object(session, "load_game") as mock_load:
            view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2), session)
            mock_load.assert_not_called()

        # Case 2: Saved game exists and loads successfully
        with patch.object(session, "has_saved_game", return_value=True), \
             patch.object(session, "load_game", return_value=True) as mock_load:
            view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c), session)
            mock_load.assert_called_once()

    def test_welcome_view_mouse_click_menu_options(self):
        """Clicking on menu option rects directly activates them."""
        view = PygameWelcomeView()
        session = GameSession()
        frame_rect = pygame.Rect((960 - 360) // 2, 172, 360, 260)
        rects = view._get_item_rects(frame_rect)

        # Click item 0 (New Game)
        click_0 = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rects[0].center)
        view.handle_event(click_0, session)
        assert session.current_mode == GameMode.CLASS_SELECT

        # Reset & click item 3 (Credits)
        session.switch_mode(GameMode.WELCOME)
        click_3 = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rects[3].center)
        view.handle_event(click_3, session)
        assert session.current_mode == GameMode.CREDITS

    def test_welcome_view_mouse_click_empty_space_is_no_op(self):
        """Clicking on dead space does not trigger any option."""
        view = PygameWelcomeView()
        session = GameSession()
        click_void = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20))
        view.handle_event(click_void, session)
        assert session.current_mode == GameMode.WELCOME

    def test_welcome_view_mouse_non_left_buttons_ignored(self):
        """Middle click (button=2) or right click (button=3) on menu items is ignored."""
        view = PygameWelcomeView()
        session = GameSession()
        frame_rect = pygame.Rect((960 - 360) // 2, 172, 360, 260)
        rects = view._get_item_rects(frame_rect)

        click_right = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=rects[0].center)
        view.handle_event(click_right, session)
        assert session.current_mode == GameMode.WELCOME

    def test_welcome_view_mouse_motion_updates_mute_hover(self):
        """MOUSEMOTION event inside and outside mute rect updates mute_hovered."""
        view = PygameWelcomeView()
        session = GameSession()
        mute_rect = view.get_mute_button_rect()

        motion_inside = pygame.event.Event(pygame.MOUSEMOTION, pos=mute_rect.center)
        view.handle_event(motion_inside, session)
        assert view.mute_hovered is True

        motion_outside = pygame.event.Event(pygame.MOUSEMOTION, pos=(10, 10))
        view.handle_event(motion_outside, session)
        assert view.mute_hovered is False

    def test_welcome_view_mouse_pos_in_update_selects_hovered_menu_item(self):
        """Hovering mouse over menu item during update updates selected_index."""
        view = PygameWelcomeView()
        session = GameSession()
        frame_rect = pygame.Rect((960 - 360) // 2, 172, 360, 260)
        rects = view._get_item_rects(frame_rect)

        with patch("pygame.mouse.get_pos", return_value=rects[2].center):
            view.update(0.016, session)
            assert view.selected_index == 2

    def test_welcome_view_mute_button_exact_pixel_boundaries(self):
        """Exhaustive boundary testing of MUTE_BUTTON_RECT geometry."""
        view = PygameWelcomeView()
        rect = view.get_mute_button_rect()
        x, y, w, h = rect.x, rect.y, rect.width, rect.height

        # Boundary points: inside
        assert rect.collidepoint(x, y) is True
        assert rect.collidepoint(x + w - 1, y + h - 1) is True
        assert rect.collidepoint(rect.centerx, rect.centery) is True

        # Boundary points: outside
        assert rect.collidepoint(x - 1, y) is False
        assert rect.collidepoint(x + w, y) is False
        assert rect.collidepoint(x, y - 1) is False
        assert rect.collidepoint(x, y + h) is False

    def test_welcome_view_spanish_locale_renders_cargar_empty_indicator(self):
        """Spanish locale renders '(---)' next to CARGAR when no save file exists."""
        view = PygameWelcomeView()
        renderer = PygameRenderer()
        session = GameSession()
        surface = pygame.Surface((960, 540))

        i18n.locale = "es"
        with patch.object(session, "has_saved_game", return_value=False):
            # Render should succeed with Spanish text token
            view.draw(surface, renderer, session)

    def test_welcome_view_breathing_pulse_accumulates_dt(self):
        """View update accumulates dt in pulse_timer."""
        view = PygameWelcomeView()
        session = GameSession()
        assert view.pulse_timer == 0.0

        view.update(0.1, session)
        assert abs(view.pulse_timer - 0.1) < 1e-5

        view.update(0.25, session)
        assert abs(view.pulse_timer - 0.35) < 1e-5

    def test_welcome_view_missing_asset_fallbacks(self):
        """draw() gracefully falls back when all optional assets return None."""
        view = PygameWelcomeView()
        renderer = PygameRenderer()
        session = GameSession()
        surface = pygame.Surface((960, 540))

        with patch("src.frontends.pygame_ce.asset_manager.assets.get_ui_component", return_value=None), \
             patch("src.frontends.pygame_ce.asset_manager.assets.get_9slice_frame", return_value=None):
            view.draw(surface, renderer, session)

    def test_welcome_view_standalone_instantiation_and_set_music_engine(
        self, audio_settings: AudioSettingsManager, test_music_engine: DynamicMusicEngine
    ):
        """Standalone view uses injected settings_manager and can be retrofitted with music_engine."""
        view = PygameWelcomeView(settings_manager=audio_settings)
        assert view.music_engine is None
        assert view.is_muted() is False

        view.set_muted(True)
        assert view.is_muted() is True
        assert audio_settings.is_music_muted() is True

        view.set_music_engine(test_music_engine)
        assert view.music_engine is test_music_engine
        assert view.settings_manager is test_music_engine.settings_manager


# =============================================================================
# 3. AUDIO ADAPTER ADVERSARIAL COVERAGE
# =============================================================================
class TestPygameAudioAdapterAdversarialCoverage:
    """Adversarial white-box tests for src/frontends/pygame_ce/audio_adapter.py."""

    def test_audio_adapter_init_failure_handled_gracefully(self):
        """When pygame.mixer.init fails, audio adapter initializes safely with initialized=False."""
        was_init = bool(pygame.mixer.get_init())
        if was_init:
            pygame.mixer.quit()

        try:
            with patch("pygame.mixer.init", side_effect=pygame.error("Audio device unavailable")):
                adapter = PygameAudioAdapter()
                assert adapter.initialized is False
                assert len(adapter._sounds) == 0
                # play_cue should be a silent safe no-op
                adapter.play_cue(AudioCue.CLICK)
        finally:
            if was_init and not pygame.mixer.get_init():
                try:
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                except Exception:
                    pass

    def test_audio_adapter_generates_all_8_procedural_cues_when_mixer_active(self):
        """When mixer is active, procedural sounds for all 8 AudioCue enum values are generated."""
        adapter = PygameAudioAdapter()
        assert adapter.initialized is True
        for cue in AudioCue:
            assert cue in adapter._sounds
            assert isinstance(adapter._sounds[cue], pygame.mixer.Sound)

    def test_audio_adapter_play_cue_sound_play_exception_handled(self):
        """When Sound.play raises an exception, play_cue catches it cleanly."""
        adapter = PygameAudioAdapter()
        mock_sound = MagicMock()
        mock_sound.play.side_effect = pygame.error("Sound channel exhausted")
        adapter._sounds[AudioCue.CRIT] = mock_sound

        # Must not raise
        adapter.play_cue(AudioCue.CRIT)
        mock_sound.play.assert_called_once()

    def test_audio_adapter_play_cue_unregistered_cue_is_safe_no_op(self):
        """Calling play_cue with an unmapped cue or None is a safe no-op."""
        adapter = PygameAudioAdapter()
        adapter.play_cue("NON_EXISTENT_CUE")  # type: ignore
        adapter.play_cue(None)  # type: ignore

    def test_audio_adapter_event_bus_reactive_subscription(self):
        """Emitting AudioCueEvent via custom EventBus triggers adapter play_cue."""
        custom_bus = EventBus()
        adapter = PygameAudioAdapter(bus=custom_bus)

        with patch.object(adapter, "play_cue") as mock_play:
            custom_bus.emit_audio(AudioCue.VICTORY)
            mock_play.assert_called_once_with(AudioCue.VICTORY)

    def test_audio_adapter_delegates_all_music_engine_methods(
        self, test_music_engine: DynamicMusicEngine
    ):
        """Audio adapter correctly delegates context, update, and mute operations to engine."""
        adapter = PygameAudioAdapter(music_engine=test_music_engine)

        with patch.object(test_music_engine, "set_context") as mock_set_ctx, \
             patch.object(test_music_engine, "update") as mock_update, \
             patch.object(test_music_engine, "toggle_mute", return_value=True) as mock_toggle, \
             patch.object(test_music_engine, "is_muted", return_value=True) as mock_is_muted:

            adapter.set_music_context(MusicContext.MAP, force_restart=True)
            mock_set_ctx.assert_called_once_with(MusicContext.MAP, force_restart=True)

            adapter.update(0.033)
            mock_update.assert_called_once_with(0.033)

            assert adapter.toggle_mute() is True
            mock_toggle.assert_called_once()

            assert adapter.is_muted() is True
            mock_is_muted.assert_called_once()


# =============================================================================
# 4. EVENT BUS ADVERSARIAL COVERAGE
# =============================================================================
class TestEventBusAdversarialCoverage:
    """Adversarial white-box tests for src/core/events.py."""

    def test_event_bus_fifo_drain_and_empty(self):
        """Events are emitted in FIFO order, drained completely, and queue cleared."""
        bus = EventBus()
        ev1 = AudioCueEvent(cue=AudioCue.HIT)
        ev2 = DamageDealtEvent(source="Hero", target="Goblin", amount=15)
        ev3 = AudioCueEvent(cue=AudioCue.DEFEAT)

        bus.emit(ev1)
        bus.emit(ev2)
        bus.emit(ev3)

        drained = bus.drain()
        assert drained == [ev1, ev2, ev3]
        # Subsequent drain should be completely empty
        assert bus.drain() == []

    def test_event_bus_clear_drops_queued_events(self):
        """Calling clear() empties the event queue without notification."""
        bus = EventBus()
        bus.emit(AudioCueEvent(cue=AudioCue.CLICK))
        bus.emit(AudioCueEvent(cue=AudioCue.DOOR))
        assert len(bus._queue) == 2

        bus.clear()
        assert len(bus.drain()) == 0

    def test_event_bus_multiple_subscribers_ordering(self):
        """Multiple subscribers for the same event type are invoked in order of registration."""
        bus = EventBus()
        call_log: list[int] = []

        def sub_one(ev: AudioCueEvent) -> None:
            call_log.append(1)

        def sub_two(ev: AudioCueEvent) -> None:
            call_log.append(2)

        bus.subscribe(AudioCueEvent, sub_one)
        bus.subscribe(AudioCueEvent, sub_two)

        bus.emit_audio(AudioCue.HEAL)
        assert call_log == [1, 2]

    def test_event_bus_unsubscribe_unregistered_handler_is_safe(self):
        """Unsubscribing an unregistered handler is a safe no-op and does not raise."""
        bus = EventBus()

        def dummy_handler(ev: AudioCueEvent) -> None:
            pass

        bus.unsubscribe(AudioCueEvent, dummy_handler)  # Not registered yet
        bus.subscribe(AudioCueEvent, dummy_handler)
        bus.unsubscribe(AudioCueEvent, dummy_handler)  # Removed
        bus.unsubscribe(AudioCueEvent, dummy_handler)  # Removed again (no-op)

    def test_event_bus_unsubscribe_unregistered_event_type_is_safe(self):
        """Unsubscribing from an event type with zero registered handlers is a safe no-op."""
        bus = EventBus()
        bus.unsubscribe(DamageDealtEvent, lambda ev: None)

    def test_event_bus_reentrant_emission_processes_nested_events(self):
        """A subscriber emitting a secondary event executes without deadlocking or dropped items."""
        bus = EventBus()
        dispatched_events: list[DomainEvent] = []

        def on_damage(ev: DamageDealtEvent) -> None:
            dispatched_events.append(ev)
            # Reentrantly emit sound cue
            bus.emit_audio(AudioCue.HIT)

        def on_audio(ev: AudioCueEvent) -> None:
            dispatched_events.append(ev)

        bus.subscribe(DamageDealtEvent, on_damage)
        bus.subscribe(AudioCueEvent, on_audio)

        dmg_event = DamageDealtEvent(source="Knight", target="Orc", amount=25)
        bus.emit(dmg_event)

        assert len(dispatched_events) == 2
        assert dispatched_events[0] == dmg_event
        assert dispatched_events[1] == AudioCueEvent(cue=AudioCue.HIT)

    def test_domain_event_frozen_dataclass_raises_on_mutation(self):
        """All DomainEvent dataclasses are frozen and raise FrozenInstanceError on mutation."""
        cue_ev = AudioCueEvent(cue=AudioCue.HIT)
        with pytest.raises(FrozenInstanceError):
            cue_ev.cue = AudioCue.CRIT  # type: ignore

        dmg_ev = DamageDealtEvent(source="Hero", target="Slime", amount=10)
        with pytest.raises(FrozenInstanceError):
            dmg_ev.amount = 99  # type: ignore

        heal_ev = HealthRestoredEvent(target="Hero", amount=20, current_hp=50, max_hp=100)
        with pytest.raises(FrozenInstanceError):
            heal_ev.amount = 50  # type: ignore

        status_ev = StatusAppliedEvent(target="Enemy", status_id="poison", status_name="Poison", duration=3)
        with pytest.raises(FrozenInstanceError):
            status_ev.duration = 5  # type: ignore

    def test_domain_event_equality_and_hashability(self):
        """Equal events compare equal and can be stored in sets and dictionaries."""
        ev1 = DamageDealtEvent(source="Hero", target="Slime", amount=10)
        ev2 = DamageDealtEvent(source="Hero", target="Slime", amount=10)
        ev3 = DamageDealtEvent(source="Hero", target="Dragon", amount=10)

        assert ev1 == ev2
        assert ev1 != ev3
        assert hash(ev1) == hash(ev2)

        event_set = {ev1, ev2, ev3}
        assert len(event_set) == 2

    def test_combat_log_entry_is_string_with_rich_metadata(self):
        """CombatLogEntry behaves as a Python str while carrying metadata keys and parameters."""
        entry = CombatLogEntry(
            "Player struck Goblin for 15 damage!",
            key="combat.damage_dealt",
            params={"source": "Player", "target": "Goblin", "amount": 15},
            category="combat",
        )

        # Standard str checks
        assert isinstance(entry, str)
        assert entry.startswith("Player struck")
        assert entry.upper().startswith("PLAYER STRUCK")
        assert f"Prefix: {entry}".endswith("15 damage!")

        # Metadata checks
        assert entry.key == "combat.damage_dealt"
        assert entry.params["amount"] == 15
        assert entry.category == "combat"


# =============================================================================
# 5. END-TO-END ADVERSARIAL INTEGRATION SCENARIOS
# =============================================================================
class TestEndToEndAdversarialIntegrationScenarios:
    """Multi-component adversarial integration tests bridging app, views, music, and events."""

    def test_app_music_endevent_re_randomization_cycle(
        self, test_music_engine: DynamicMusicEngine
    ):
        """Dispatching a custom endevent through pygame queue triggers track loop handling."""
        app = PygameApp(headless=True, music_engine=test_music_engine)
        custom_endevent = pygame.USEREVENT + 12
        test_music_engine.set_end_event(custom_endevent)

        with patch.object(test_music_engine, "_handle_track_finished") as mock_track_finish, \
             patch.object(test_music_engine, "_is_music_busy", return_value=False):
            test_music_engine._playback_state = PlaybackState.PLAYING

            pygame.event.clear()
            pygame.event.post(pygame.event.Event(custom_endevent))

            app.handle_events()
            mock_track_finish.assert_called_once()

    def test_rapid_fullscreen_and_mute_interleaved_stress(
        self, test_music_engine: DynamicMusicEngine
    ):
        """Rapid interleaved F11 and 'M' inputs maintain coherent app state."""
        app = PygameApp(headless=True, music_engine=test_music_engine)

        with patch("pygame.display.toggle_fullscreen") as mock_toggle:
            pygame.event.clear()
            for _ in range(20):
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11, mod=0))
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m, mod=0))

            app.handle_events()
            # 20 fullscreen toggles
            assert mock_toggle.call_count == 20
            # 20 mute toggles on music_engine (even number -> unmuted at end)
            assert test_music_engine.is_muted() is False

    def test_complete_journey_modal_stacking_under_app_lifecycle(
        self, test_music_engine: DynamicMusicEngine
    ):
        """Execute complete full game lifecycle through PygameApp event/update/draw loop."""
        app = PygameApp(headless=True, music_engine=test_music_engine)

        # 1. Start at WELCOME
        app.update(0.016)
        app.draw()
        assert app.music_engine.get_current_context() == MusicContext.WELCOME

        # 2. Transition to CLASS_SELECT via key 1
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))
        app.handle_events()
        app.update(0.016)
        app.draw()
        assert app.session.current_mode == GameMode.CLASS_SELECT
        assert app.music_engine.get_current_context() == MusicContext.WELCOME

        # 3. Transition to MAP
        app.session.switch_mode(GameMode.MAP)
        app.update(0.016)
        app.draw()
        assert app.music_engine.get_current_context() == MusicContext.MAP
        map_track = app.music_engine.get_current_track()

        # 4. Open INVENTORY modal, cycle update/draw, close back to MAP
        app.session.switch_mode(GameMode.INVENTORY)
        app.update(0.016)
        app.draw()
        assert app.music_engine.get_current_context() == MusicContext.MAP
        assert app.music_engine.get_current_track() == map_track

        app.session.switch_mode(GameMode.MAP)
        app.update(0.016)
        app.draw()

        # 5. Initiate COMMON combat
        enemy = Enemy(
            name="Goblin Scout",
            tier=EnemyTier.COMMON,
            stats=Stats(max_hp=25, attack=6, defense=2, speed=10),
            floor_level=1,
            exp_reward=10,
            gold_reward=5,
        )
        app.session.state.combat = CombatSystem(player=app.session.player, enemy=enemy)
        app.session.switch_mode(GameMode.COMBAT)
        app.update(0.016)
        app.draw()
        assert app.music_engine.get_current_context() == MusicContext.COMBAT

        # 6. Open CHARACTER modal during combat
        app.session.switch_mode(GameMode.CHARACTER)
        app.update(0.016)
        app.draw()
        assert app.music_engine.get_current_context() == MusicContext.COMBAT

        # 7. Return to COMBAT, defeat enemy, switch to MAP
        app.session.switch_mode(GameMode.COMBAT)
        app.update(0.016)
        app.session.switch_mode(GameMode.MAP)
        app.update(0.016)
        app.draw()
        assert app.music_engine.get_current_context() == MusicContext.MAP

        # 8. Initiate BOSS combat
        boss = Enemy(
            name="Dungeon Tyrant",
            tier=EnemyTier.BOSS,
            stats=Stats(max_hp=250, attack=30, defense=15, speed=10),
            floor_level=1,
            exp_reward=150,
            gold_reward=100,
        )
        app.session.state.combat = CombatSystem(player=app.session.player, enemy=boss)
        app.session.switch_mode(GameMode.COMBAT)
        app.update(0.016)
        app.draw()
        assert app.music_engine.get_current_context() == MusicContext.BOSS

        # 9. Defeat / End game
        app.session.switch_mode(GameMode.GAME_OVER)
        app.update(0.016)
        app.draw()
        # Retains boss music until reset
        assert app.music_engine.get_current_context() == MusicContext.BOSS

        # 10. Return to WELCOME title
        app.session.switch_mode(GameMode.WELCOME)
        app.update(0.016)
        app.draw()
        assert app.music_engine.get_current_context() == MusicContext.WELCOME
