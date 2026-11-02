"""Pygame-CE Title & Class Selection View."""

from __future__ import annotations

from typing import TYPE_CHECKING
import pygame

from src.core.game_state import GameMode
from src.core.theme import ThemeToken
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


class PygameTitleView(PygameView):
    """Title view supporting archetype selection and new/continue run initialization."""

    CLASSES = [
        ("warrior", "Warrior", "High Armor & Brutal Cleaves", "HP: 60  ATK: 8  DEF: 5"),
        ("rogue", "Rogue", "Lethal Daggers & Toxic Venoms", "HP: 45  ATK: 10 DEF: 2"),
        ("mage", "Mage", "Arcane Spells & Barrier Shields", "HP: 40  ATK: 12 DEF: 1"),
    ]

    def __init__(self) -> None:
        self.selected_class: str = "warrior"
        self._hovered_btn: str | None = None

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Handle keyboard navigation and mouse clicks."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.selected_class = "warrior"
            elif event.key == pygame.K_2:
                self.selected_class = "rogue"
            elif event.key == pygame.K_3:
                self.selected_class = "mage"
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._start_game(session)
            elif event.key == pygame.K_c and session.has_saved_game():
                session.load_game()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            # Check class card clicks
            for idx, (cid, _, _, _) in enumerate(self.CLASSES):
                card_rect = pygame.Rect(180 + idx * 210, 240, 190, 140)
                if card_rect.collidepoint(mouse_pos):
                    self.selected_class = cid
                    return

            # Check Start Button click
            start_btn_rect = pygame.Rect(380, 420, 200, 48)
            if start_btn_rect.collidepoint(mouse_pos):
                self._start_game(session)
                return

            # Check Continue Button click
            if session.has_saved_game():
                cont_btn_rect = pygame.Rect(380, 480, 200, 36)
                if cont_btn_rect.collidepoint(mouse_pos):
                    session.load_game()
                    return

    def _start_game(self, session: GameSession) -> None:
        """Begin new run and transition to the Spire Map."""
        session.start_new_game(class_id=self.selected_class)
        session.switch_mode(GameMode.MAP)

    def update(self, dt: float, session: GameSession) -> None:
        """Update button hover state based on mouse position."""
        mouse_pos = pygame.mouse.get_pos()
        start_btn_rect = pygame.Rect(380, 420, 200, 48)
        cont_btn_rect = pygame.Rect(380, 480, 200, 36)

        if start_btn_rect.collidepoint(mouse_pos):
            self._hovered_btn = "start"
        elif session.has_saved_game() and cont_btn_rect.collidepoint(mouse_pos):
            self._hovered_btn = "continue"
        else:
            self._hovered_btn = None

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render high-resolution gothic title screen."""
        surface_w = surface.get_width()

        # Title and Subtitle
        renderer.draw_text(
            surface,
            "QUEST FOR AETHELGARD",
            surface_w // 2,
            70,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=36,
            bold=True,
            align="center",
        )
        renderer.draw_text(
            surface,
            "A Gothic Roguelike Deckbuilder & Tactical Spire Crawler",
            surface_w // 2,
            120,
            token=ThemeToken.TEXT_MUTED,
            size=16,
            align="center",
        )

        renderer.draw_text(
            surface,
            "CHOOSE YOUR CHAMPION",
            surface_w // 2,
            195,
            token=ThemeToken.TEXT_NORMAL,
            size=18,
            bold=True,
            align="center",
        )

        # Class Cards
        mouse_pos = pygame.mouse.get_pos()
        for idx, (cid, name, desc, stats) in enumerate(self.CLASSES):
            card_rect = pygame.Rect(180 + idx * 210, 240, 190, 140)
            is_selected = (self.selected_class == cid)
            is_hovered = card_rect.collidepoint(mouse_pos)

            border_tok = (
                ThemeToken.ACCENT_PRIMARY if is_selected else
                (ThemeToken.ACCENT_SECONDARY if is_hovered else ThemeToken.BORDER_MUTED)
            )

            renderer.draw_panel(
                surface,
                card_rect,
                bg_token=ThemeToken.PANEL_BG,
                border_token=border_tok,
                border_width=3 if is_selected else (2 if is_hovered else 1),
                border_radius=8,
            )

            # Class Title
            renderer.draw_text(
                surface,
                f"[{idx+1}] {name.upper()}",
                card_rect.centerx,
                card_rect.y + 16,
                token=ThemeToken.TEXT_HIGHLIGHT if is_selected else ThemeToken.TEXT_NORMAL,
                size=18,
                bold=True,
                align="center",
            )

            # Class Description
            renderer.draw_text(
                surface,
                desc,
                card_rect.centerx,
                card_rect.y + 54,
                token=ThemeToken.TEXT_MUTED,
                size=12,
                align="center",
            )

            # Base Stats
            renderer.draw_text(
                surface,
                stats,
                card_rect.centerx,
                card_rect.y + 98,
                token=ThemeToken.TEXT_NORMAL,
                size=12,
                bold=True,
                align="center",
            )

        # Start Journey Button
        start_rect = pygame.Rect(380, 420, 200, 48)
        renderer.draw_button(
            surface,
            start_rect,
            "START JOURNEY [SPACE]",
            is_hovered=(self._hovered_btn == "start"),
            accent_token=ThemeToken.TEXT_SUCCESS,
            font_size=15,
        )

        # Continue Saved Run Button (if available)
        if session.has_saved_game():
            cont_rect = pygame.Rect(380, 480, 200, 36)
            renderer.draw_button(
                surface,
                cont_rect,
                "CONTINUE RUN [C]",
                is_hovered=(self._hovered_btn == "continue"),
                accent_token=ThemeToken.ACCENT_SECONDARY,
                font_size=13,
            )
