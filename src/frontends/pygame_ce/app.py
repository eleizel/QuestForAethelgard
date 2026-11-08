"""Pygame-CE Master Application Controller supporting all 14 game screens with 16-bit SNES aesthetics."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import pygame

from src.core.game_state import GameMode
from src.core.session import GameSession
from src.frontends.pygame_ce.audio_adapter import PygameAudioAdapter
from src.frontends.pygame_ce.music_engine import DynamicMusicEngine, resolve_music_context
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.base import PygameView

# Views
from src.frontends.pygame_ce.views.welcome import PygameWelcomeView
from src.frontends.pygame_ce.views.class_select import PygameClassSelectView
from src.frontends.pygame_ce.views.biome_select import PygameBiomeSelectView
from src.frontends.pygame_ce.views.map_view import PygameMapView
from src.frontends.pygame_ce.views.combat_view import PygameCombatView
from src.frontends.pygame_ce.views.loot import PygameLootView
from src.frontends.pygame_ce.views.shop import PygameShopView
from src.frontends.pygame_ce.views.ability_choice import PygameAbilityChoiceView
from src.frontends.pygame_ce.views.promotion import PygamePromotionView
from src.frontends.pygame_ce.views.events import PygameEventsView
from src.frontends.pygame_ce.views.inventory_modal import PygameInventoryModalView
from src.frontends.pygame_ce.views.character_modal import PygameCharacterModalView
from src.frontends.pygame_ce.views.end_game import PygameEndGameView
from src.frontends.pygame_ce.views.credits import PygameCreditsView


logger = logging.getLogger(__name__)


class PygameApp:
    """Master application controller driving the Pygame-CE lifecycle and view routing."""

    def __init__(
        self,
        width: int = 960,
        height: int = 540,
        headless: bool = False,
        fullscreen: bool = False,
        maximized: bool = False,
        session: GameSession | None = None,
        music_engine: DynamicMusicEngine | None = None,
        audio_adapter: PygameAudioAdapter | None = None,
    ) -> None:
        self.width: int = width
        self.height: int = height
        self.headless: bool = headless
        self.fullscreen: bool = fullscreen
        self.maximized: bool = maximized
        self.is_running: bool = False
        self.last_error: Exception | None = None

        if self.headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            os.environ["SDL_AUDIODRIVER"] = "dummy"

        try:
            pygame.init()
        except Exception:
            pass

        if self.headless:
            self.screen: pygame.Surface = pygame.Surface((self.width, self.height))
        else:
            pygame.display.set_caption("Quest for Aethelgard — 16-Bit SNES Golden Age Edition")
            icon_path = Path(__file__).resolve().parents[3] / "assets" / "icon-192.png"
            if icon_path.exists():
                try:
                    pygame.display.set_icon(pygame.image.load(str(icon_path)))
                except Exception:
                    pass

            flags = pygame.DOUBLEBUF | pygame.SCALED | pygame.RESIZABLE
            if self.fullscreen:
                flags |= pygame.FULLSCREEN

            self.screen = pygame.display.set_mode((self.width, self.height), flags)

            if self.maximized and not self.fullscreen:
                try:
                    from pygame.window import Window

                    win = Window.from_display_module()
                    win.maximize()
                except Exception:
                    pass

        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.session: GameSession = session if session is not None else GameSession()
        self.renderer: PygameRenderer = PygameRenderer()

        # Dynamic Music Engine & Audio Adapter Initialization
        if audio_adapter is not None:
            self.audio_adapter = audio_adapter
            self.music_engine = (
                music_engine
                if music_engine is not None
                else getattr(audio_adapter, "music_engine", None) or DynamicMusicEngine()
            )
        else:
            self.music_engine = music_engine if music_engine is not None else DynamicMusicEngine()
            self.audio_adapter = PygameAudioAdapter(
                bus=self.session.bus, music_engine=self.music_engine
            )

        # Complete Registry for All 14 Operational Game Modes
        self.views: dict[GameMode, PygameView] = {
            GameMode.WELCOME: PygameWelcomeView(music_engine=self.music_engine),
            GameMode.CLASS_SELECT: PygameClassSelectView(),
            GameMode.BIOME_SELECT: PygameBiomeSelectView(),
            GameMode.MAP: PygameMapView(),
            GameMode.COMBAT: PygameCombatView(),
            GameMode.LOOT: PygameLootView(),
            GameMode.SHOP: PygameShopView(),
            GameMode.ABILITY_CHOICE: PygameAbilityChoiceView(),
            GameMode.PROMOTION: PygamePromotionView(),
            GameMode.EVENTS: PygameEventsView(),
            GameMode.INVENTORY: PygameInventoryModalView(),
            GameMode.CHARACTER: PygameCharacterModalView(),
            GameMode.GAME_OVER: PygameEndGameView(),
            GameMode.VICTORY: PygameEndGameView(),
            GameMode.CREDITS: PygameCreditsView(),
        }

        # Initialize music context for the starting game mode
        self.update_music_context()

    def update_music_context(self, force_restart: bool = False) -> None:
        """Synchronize dynamic music context with the active GameSession mode and state."""
        target_context = resolve_music_context(self.session)
        if target_context is not None:
            self.music_engine.set_context(target_context, force_restart=force_restart)

    def get_active_view(self) -> PygameView:
        """Resolve active view for the current GameSession operational mode."""
        mode = self.session.current_mode
        return self.views.get(mode, self.views[GameMode.WELCOME])

    def handle_events(self) -> None:
        """Poll and dispatch Pygame window and input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
                return

            if event.type == pygame.KEYDOWN:
                # F11 or Alt+Enter toggles fullscreen without restarting or distorting
                if event.key == pygame.K_F11 or (
                    event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT)
                ):
                    try:
                        pygame.display.toggle_fullscreen()
                        self.fullscreen = not self.fullscreen
                    except Exception:
                        pass
                    continue

            self.music_engine.handle_event(event)

            active_view = self.get_active_view()
            active_view.handle_event(event, self.session)

    def update(self, dt: float) -> None:
        """Advance view logic, timers, and dynamic background music."""
        # Synchronize dynamic music context and advance playback transitions
        self.update_music_context()
        self.music_engine.update(dt)

        # Global promotion safeguard matching Pyxel ViewManager
        if self.session.current_mode not in (
            GameMode.LOOT,
            GameMode.GAME_OVER,
            GameMode.VICTORY,
            GameMode.WELCOME,
            GameMode.CLASS_SELECT,
            GameMode.PROMOTION,
            GameMode.ABILITY_CHOICE,
        ) and getattr(self.session.player, "promotion_due", False):
            self.session.state.begin_promotion(self.session.current_mode)

        active_view = self.get_active_view()
        active_view.update(dt, self.session)

    def draw(self) -> None:
        """Render active frame onto screen."""
        self.screen.fill((10, 12, 16))

        # If modal overlay is active (Inventory or Character), draw the underlying view first!
        mode = self.session.current_mode
        if mode in (GameMode.INVENTORY, GameMode.CHARACTER):
            prev_mode = self.session.previous_mode
            if prev_mode in self.views and prev_mode not in (
                GameMode.INVENTORY,
                GameMode.CHARACTER,
            ):
                self.views[prev_mode].draw(self.screen, self.renderer, self.session)

        active_view = self.get_active_view()
        active_view.draw(self.screen, self.renderer, self.session)

        if not self.headless:
            pygame.display.flip()

    def _render_emergency_fallback(self, error_msg: str) -> None:
        """Render a minimal fallback crash screen when an unhandled frame exception occurs."""
        try:
            self.screen.fill((20, 20, 25))
            if hasattr(self, "renderer") and self.renderer is not None:
                self.renderer.draw_text(
                    self.screen,
                    "An unexpected frame failure occurred.",
                    40,
                    50,
                    color=(220, 50, 50),
                    size=24,
                )
                self.renderer.draw_text(
                    self.screen,
                    f"Error: {error_msg[:120]}",
                    40,
                    100,
                    color=(200, 200, 200),
                    size=16,
                )
                self.renderer.draw_text(
                    self.screen,
                    "Run data has been preserved. Check logs for complete details.",
                    40,
                    140,
                    color=(160, 160, 160),
                    size=14,
                )
            pygame.display.flip()
        except Exception:
            pass

    def _handle_frame_failure(self, error: Exception) -> None:
        """Record a fatal frame error and terminate the loop safely.

        Continuing after a failed update or draw can render mutated state every
        frame and create an unbounded stream of tracebacks. If display is active,
        attempts to render a fallback diagnostics banner before exiting.
        """
        self.last_error = error
        self.is_running = False
        logger.exception("Fatal Pygame frame failure; stopping the application loop: %s", error)

        if not self.headless and getattr(self, "screen", None) is not None:
            self._render_emergency_fallback(str(error))

    def run(self, max_frames: int | None = None) -> None:
        """Run application main loop."""
        self.is_running = True
        frames_rendered = 0

        try:
            while self.is_running:
                dt = self.clock.tick(60) / 1000.0  # 60 FPS
                try:
                    self.handle_events()
                    self.update(dt)
                    self.draw()
                except Exception as error:
                    self._handle_frame_failure(error)
                    break

                frames_rendered += 1
                if max_frames is not None and frames_rendered >= max_frames:
                    break
        finally:
            self.music_engine.stop()
            if not self.headless:
                pygame.quit()

    async def run_async(self, max_frames: int | None = None) -> None:
        """Run the asynchronous main loop used by WebAssembly and event loops."""
        import asyncio

        self.is_running = True
        frames_rendered = 0

        try:
            while self.is_running:
                dt = self.clock.tick(60) / 1000.0  # 60 FPS
                try:
                    self.handle_events()
                    self.update(dt)
                    self.draw()
                except Exception as error:
                    self._handle_frame_failure(error)
                    break

                frames_rendered += 1
                if max_frames is not None and frames_rendered >= max_frames:
                    break
                await asyncio.sleep(0)
        finally:
            self.music_engine.stop()
            if not self.headless:
                pygame.quit()
