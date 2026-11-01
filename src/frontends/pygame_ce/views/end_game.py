"""Pygame-CE Game Over & Ascension Victory View."""

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


class PygameEndGameView(PygameView):
    """End-game tombstone or victory ascension summary screen."""

    def __init__(self) -> None:
        self._hovered: bool = False

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
            session.reset_to_title()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            btn_rect = pygame.Rect(380, 440, 200, 42)
            if btn_rect.collidepoint(event.pos):
                session.reset_to_title()

    def update(self, dt: float, session: GameSession) -> None:
        pos = pygame.mouse.get_pos()
        btn_rect = pygame.Rect(380, 440, 200, 42)
        self._hovered = btn_rect.collidepoint(pos)

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        assets.draw_background(surface, "welcome", vignette_alpha=165)
        w = surface.get_width()

        is_victory = (session.current_mode == GameMode.VICTORY)
        title = "ASCENSION ACHIEVED" if is_victory else "HERO DEFEATED"
        title_color = ThemeToken.TEXT_HIGHLIGHT if is_victory else ThemeToken.TEXT_ALERT

        renderer.draw_text(surface, title, w // 2, 50, token=title_color, size=32, bold=True, align="center")

        sub = "You have vanquished the darkness and conquered the Spire!" if is_victory else "Your bones join the endless catacombs beneath Aethelgard..."
        renderer.draw_text(surface, sub, w // 2, 95, token=ThemeToken.TEXT_MUTED, size=14, align="center")

        panel_rect = pygame.Rect(240, 140, 480, 260)
        renderer.draw_panel(surface, panel_rect, border_token=ThemeToken.BORDER)

        player = session.player
        stats = [
            ("Champion", f"{player.name} ({player.class_id.capitalize()})"),
            ("Level Achieved", f"Level {player.level}"),
            ("Furthest Floor", f"Act {session.state.act} - Floor {session.state.floor}"),
            ("Gold Amassed", f"{player.gold} Gold"),
            ("Status", "Triumphant" if is_victory else "Fallen in battle"),
        ]

        for idx, (label, val) in enumerate(stats):
            y = panel_rect.y + 30 + idx * 42
            renderer.draw_text(surface, label.upper(), panel_rect.x + 30, y, token=ThemeToken.TEXT_MUTED, size=13, bold=True)
            renderer.draw_text(surface, val, panel_rect.right - 30, y, token=ThemeToken.TEXT_HIGHLIGHT, size=13, bold=True, align="right")

        btn_rect = pygame.Rect(380, 440, 200, 42)
        renderer.draw_button(
            surface,
            btn_rect,
            "PLAY AGAIN [SPACE]",
            is_hovered=self._hovered,
            accent_token=ThemeToken.TEXT_SUCCESS if is_victory else ThemeToken.ACCENT_PRIMARY,
            font_size=13,
        )
