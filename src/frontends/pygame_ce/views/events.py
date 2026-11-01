"""Pygame-CE Narrative Events & Shrine Encounter View."""

from __future__ import annotations

from typing import TYPE_CHECKING
import pygame

from src.core.game_state import GameMode
from src.core.theme import ThemeToken
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


class PygameEventsView(PygameView):
    """Narrative dungeon event view presenting choices and consequences."""

    def __init__(self) -> None:
        self._hovered_btn: str | None = None

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                session.state.continue_after_rewards()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cont_rect = pygame.Rect(380, 430, 200, 42)
            if cont_rect.collidepoint(event.pos):
                session.state.continue_after_rewards()

    def update(self, dt: float, session: GameSession) -> None:
        pos = pygame.mouse.get_pos()
        cont_rect = pygame.Rect(380, 430, 200, 42)
        self._hovered_btn = "continue" if cont_rect.collidepoint(pos) else None

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        # If rest event, use rest background, else biome background
        biome = getattr(session.state, "current_biome", "cathedral")
        bg_name = "rest" if "rest" in getattr(session.state, "current_event_text", "").lower() else biome
        assets.draw_background(surface, bg_name, vignette_alpha=140)

        w = surface.get_width()

        renderer.draw_text(
            surface,
            "ENCOUNTER IN THE DARK",
            w // 2,
            50,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=28,
            bold=True,
            align="center",
        )

        panel_rect = pygame.Rect(180, 110, 600, 290)
        renderer.draw_panel(surface, panel_rect, border_token=ThemeToken.BORDER)

        event_text = getattr(session.state, "current_event_text", "You find a moment of eerie silence in the ruins.")
        words = event_text.split(" ")
        lines = []
        curr = ""
        for word in words:
            if len(curr) + len(word) < 46:
                curr += word + " "
            else:
                lines.append(curr)
                curr = word + " "
        if curr:
            lines.append(curr)

        for idx, line in enumerate(lines[:8]):
            renderer.draw_text(
                surface,
                line.strip(),
                panel_rect.centerx,
                panel_rect.y + 40 + idx * 24,
                token=ThemeToken.TEXT_NORMAL,
                size=14,
                align="center",
            )

        cont_rect = pygame.Rect(380, 430, 200, 42)
        renderer.draw_button(
            surface,
            cont_rect,
            "CONTINUE [SPACE]",
            is_hovered=(self._hovered_btn == "continue"),
            accent_token=ThemeToken.TEXT_SUCCESS,
            font_size=13,
        )
