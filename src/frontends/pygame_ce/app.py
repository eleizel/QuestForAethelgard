"""Pygame-CE Master Application Controller supporting all 14 game screens with 16-bit SNES aesthetics."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING
import pygame

from src.core.game_state import GameMode
from src.core.session import GameSession
from src.frontends.pygame_ce.audio_adapter import PygameAudioAdapter
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
    ) -> None:
        self.width: int = width
        self.height: int = height
        self.headless: bool = headless
        self.fullscreen: bool = fullscreen
        self.maximized: bool = maximized
        self.is_running: bool = False

        if self.headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            os.environ["SDL_AUDIODRIVER"] = "dummy"

        if not pygame.get_init():
            pygame.init()

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
        self.audio_adapter: PygameAudioAdapter = PygameAudioAdapter(bus=self.session.bus)

        # Complete Registry for All 14 Operational Game Modes
        self.views: dict[GameMode, PygameView] = {
            GameMode.WELCOME: PygameWelcomeView(),
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
                if event.key == pygame.K_F11 or (event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT)):
                    try:
                        pygame.display.toggle_fullscreen()
                        self.fullscreen = not self.fullscreen
                    except Exception:
                        pass
                    continue

            active_view = self.get_active_view()
            active_view.handle_event(event, self.session)

    def update(self, dt: float) -> None:
        """Advance view logic and timers."""
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
            if prev_mode in self.views and prev_mode not in (GameMode.INVENTORY, GameMode.CHARACTER):
                self.views[prev_mode].draw(self.screen, self.renderer, self.session)

        active_view = self.get_active_view()
        active_view.draw(self.screen, self.renderer, self.session)

        if not self.headless:
            pygame.display.flip()

    def run(self, max_frames: int | None = None) -> None:
        """Run application main loop."""
        self.is_running = True
        frames_rendered = 0

        while self.is_running:
            dt = self.clock.tick(60) / 1000.0  # 60 FPS
            self.handle_events()
            self.update(dt)
            self.draw()

            frames_rendered += 1
            if max_frames is not None and frames_rendered >= max_frames:
                break

        if not self.headless:
            pygame.quit()

    async def run_async(self, max_frames: int | None = None) -> None:
        """Run asynchronous application main loop for WebAssembly (Pygbag) and event loops."""
        import asyncio

        self.is_running = True
        frames_rendered = 0

        while self.is_running:
            dt = self.clock.tick(60) / 1000.0  # 60 FPS
            self.handle_events()
            self.update(dt)
            self.draw()

            frames_rendered += 1
            if max_frames is not None and frames_rendered >= max_frames:
                break
            await asyncio.sleep(0)

        if not self.headless:
            pygame.quit()
