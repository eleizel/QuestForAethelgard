"""Pygame-CE Master Application Controller."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING
import pygame

from src.core.game_state import GameMode
from src.core.session import GameSession
from src.frontends.pygame_ce.audio_adapter import PygameAudioAdapter
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.base import PygameView
from src.frontends.pygame_ce.views.title_view import PygameTitleView
from src.frontends.pygame_ce.views.map_view import PygameMapView
from src.frontends.pygame_ce.views.combat_view import PygameCombatView


class PygameApp:
    """Master application controller driving the Pygame-CE lifecycle and view routing."""

    def __init__(
        self,
        width: int = 960,
        height: int = 540,
        headless: bool = False,
        session: GameSession | None = None,
    ) -> None:
        self.width: int = width
        self.height: int = height
        self.headless: bool = headless
        self.is_running: bool = False

        if self.headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            os.environ["SDL_AUDIODRIVER"] = "dummy"

        if not pygame.get_init():
            pygame.init()

        if self.headless:
            self.screen: pygame.Surface = pygame.Surface((self.width, self.height))
        else:
            pygame.display.set_caption("Quest for Aethelgard — Pygame-CE High-DPI Client")
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF)

        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.session: GameSession = session if session is not None else GameSession()
        self.renderer: PygameRenderer = PygameRenderer()
        self.audio_adapter: PygameAudioAdapter = PygameAudioAdapter(bus=self.session.bus)

        # Core View Registry
        self.views: dict[GameMode, PygameView] = {
            GameMode.WELCOME: PygameTitleView(),
            GameMode.MAP: PygameMapView(),
            GameMode.COMBAT: PygameCombatView(),
        }

    def get_active_view(self) -> PygameView:
        """Resolve active view for the current GameSession operational mode."""
        mode = self.session.current_mode
        if mode in self.views:
            return self.views[mode]
        elif mode in (GameMode.LOOT, GameMode.SHOP, GameMode.EVENTS):
            # For encounter wrap-ups in vertical slice, map view gracefully handles state
            return self.views[GameMode.MAP]
        return self.views[GameMode.WELCOME]

    def handle_events(self) -> None:
        """Poll and dispatch Pygame window and input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
                return

            active_view = self.get_active_view()
            active_view.handle_event(event, self.session)

    def update(self, dt: float) -> None:
        """Advance view logic and timers."""
        active_view = self.get_active_view()
        active_view.update(dt, self.session)

    def draw(self) -> None:
        """Render frame onto target surface."""
        # Deep gothic dark background
        self.screen.fill((12, 14, 20))

        active_view = self.get_active_view()
        active_view.draw(self.screen, self.renderer, self.session)

        if not self.headless:
            pygame.display.flip()

    def run(self, max_frames: int | None = None) -> None:
        """Run application main loop."""
        self.is_running = True
        frames_rendered = 0

        while self.is_running:
            dt = self.clock.tick(60) / 1000.0  # Cap at 60 FPS
            self.handle_events()
            self.update(dt)
            self.draw()

            frames_rendered += 1
            if max_frames is not None and frames_rendered >= max_frames:
                break

        if not self.headless:
            pygame.quit()
