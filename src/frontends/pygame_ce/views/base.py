"""Base protocol for Pygame-CE view components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


class PygameView(ABC):
    """Abstract base view handling events, updates, and rendering in Pygame-CE."""

    @abstractmethod
    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Process user input event (keyboard, mouse, touch)."""
        ...

    @abstractmethod
    def update(self, dt: float, session: GameSession) -> None:
        """Advance time-based view logic, animations, or countdowns."""
        ...

    @abstractmethod
    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render presentation components onto target surface."""
        ...
