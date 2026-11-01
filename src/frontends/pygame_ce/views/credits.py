"""Pygame-CE Credits View."""

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


class PygameCreditsView(PygameView):
    """Credits screen honoring the development and design of Quest for Aethelgard."""

    def __init__(self) -> None:
        self._hovered: bool = False

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
            session.switch_mode(GameMode.WELCOME)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            back_rect = pygame.Rect(380, 440, 200, 42)
            if back_rect.collidepoint(event.pos):
                session.switch_mode(GameMode.WELCOME)

    def update(self, dt: float, session: GameSession) -> None:
        pos = pygame.mouse.get_pos()
        back_rect = pygame.Rect(380, 440, 200, 42)
        self._hovered = back_rect.collidepoint(pos)

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        assets.draw_background(surface, "welcome", vignette_alpha=160)
        w = surface.get_width()

        renderer.draw_text(
            surface,
            "QUEST FOR AETHELGARD",
            w // 2,
            60,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=30,
            bold=True,
            align="center",
        )
        renderer.draw_text(
            surface,
            "CREDITS & ACKNOWLEDGMENTS",
            w // 2,
            105,
            token=ThemeToken.TEXT_MUTED,
            size=15,
            bold=True,
            align="center",
        )

        panel_rect = pygame.Rect(200, 150, 560, 260)
        renderer.draw_panel(surface, panel_rect, border_token=ThemeToken.BORDER)

        lines = [
            ("Game Design & Programming", "Sergio / Eleizel"),
            ("Art Direction & Aesthetic", "16-Bit SNES Golden Age (Terranigma, Secret of Evermore)"),
            ("Core Architecture", "Pure Python Domain Decoupling & Clean Architecture"),
            ("Audio Synthesis", "8-Bit Procedural Waveform Engine & Pyxel Chiptunes"),
            ("Special Thanks", "To daughter, family, and retro RPG creators of the 90s"),
        ]

        for idx, (title, author) in enumerate(lines):
            y = panel_rect.y + 24 + idx * 44
            renderer.draw_text(surface, title.upper(), panel_rect.centerx, y, token=ThemeToken.TEXT_HIGHLIGHT, size=13, bold=True, align="center")
            renderer.draw_text(surface, author, panel_rect.centerx, y + 18, token=ThemeToken.TEXT_NORMAL, size=13, align="center")

        back_rect = pygame.Rect(380, 440, 200, 42)
        renderer.draw_button(surface, back_rect, "[ESC] BACK TO TITLE", is_hovered=self._hovered, accent_token=ThemeToken.ACCENT_PRIMARY, font_size=13)
