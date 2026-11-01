"""Pygame-CE Welcome / Title Screen View."""

from __future__ import annotations

from typing import TYPE_CHECKING
import pygame

from src.core.game_state import GameMode
from src.core.i18n import i18n, t
from src.core.theme import ThemeToken
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


class PygameWelcomeView(PygameView):
    """Gothic title screen with New Game, Continue, Credits, and live language toggle."""

    def __init__(self) -> None:
        self._hovered_btn: str | None = None

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Handle keyboard shortcuts and mouse clicks."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_1, pygame.K_n, pygame.K_RETURN, pygame.K_SPACE):
                session.switch_mode(GameMode.CLASS_SELECT)
            elif event.key in (pygame.K_2, pygame.K_c):
                if session.has_saved_game():
                    session.load_game()
            elif event.key in (pygame.K_3, pygame.K_r):
                session.switch_mode(GameMode.CREDITS)
            elif event.key == pygame.K_l:
                i18n.toggle_language()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            new_rect = pygame.Rect(360, 260, 240, 48)
            cont_rect = pygame.Rect(360, 320, 240, 44)
            cred_rect = pygame.Rect(360, 376, 240, 40)
            lang_rect = pygame.Rect(360, 428, 240, 36)

            if new_rect.collidepoint(pos):
                session.switch_mode(GameMode.CLASS_SELECT)
            elif cont_rect.collidepoint(pos) and session.has_saved_game():
                session.load_game()
            elif cred_rect.collidepoint(pos):
                session.switch_mode(GameMode.CREDITS)
            elif lang_rect.collidepoint(pos):
                i18n.toggle_language()

    def update(self, dt: float, session: GameSession) -> None:
        """Track mouse hover over menu options."""
        pos = pygame.mouse.get_pos()
        new_rect = pygame.Rect(360, 260, 240, 48)
        cont_rect = pygame.Rect(360, 320, 240, 44)
        cred_rect = pygame.Rect(360, 376, 240, 40)
        lang_rect = pygame.Rect(360, 428, 240, 36)

        if new_rect.collidepoint(pos):
            self._hovered_btn = "new"
        elif cont_rect.collidepoint(pos) and session.has_saved_game():
            self._hovered_btn = "continue"
        elif cred_rect.collidepoint(pos):
            self._hovered_btn = "credits"
        elif lang_rect.collidepoint(pos):
            self._hovered_btn = "language"
        else:
            self._hovered_btn = None

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render painted gothic citadel background and title options."""
        assets.draw_background(surface, "welcome", vignette_alpha=110)

        w = surface.get_width()

        renderer.draw_text(
            surface,
            "QUEST FOR AETHELGARD",
            w // 2,
            75,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=40,
            bold=True,
            align="center",
        )
        renderer.draw_text(
            surface,
            "A GOTHIC ROGUELIKE DECKBUILDER",
            w // 2,
            125,
            token=ThemeToken.TEXT_MUTED,
            size=16,
            bold=True,
            align="center",
        )

        new_rect = pygame.Rect(360, 260, 240, 48)
        renderer.draw_button(
            surface,
            new_rect,
            f"[1] {t('menu_new_game')}",
            is_hovered=(self._hovered_btn == "new"),
            accent_token=ThemeToken.TEXT_SUCCESS,
            font_size=16,
        )

        has_save = session.has_saved_game()
        cont_rect = pygame.Rect(360, 320, 240, 44)
        renderer.draw_button(
            surface,
            cont_rect,
            f"[2] {t('menu_load_game')}" if has_save else f"[2] {t('menu_no_save')}",
            is_hovered=(self._hovered_btn == "continue" and has_save),
            is_selected=False,
            accent_token=ThemeToken.ACCENT_SECONDARY if has_save else ThemeToken.BORDER_MUTED,
            font_size=15,
        )

        cred_rect = pygame.Rect(360, 376, 240, 40)
        renderer.draw_button(
            surface,
            cred_rect,
            f"[3] {t('menu_credits')}",
            is_hovered=(self._hovered_btn == "credits"),
            accent_token=ThemeToken.ACCENT_PRIMARY,
            font_size=14,
        )

        lang_name = "ENGLISH" if getattr(i18n, "locale", "en") == "en" else "ESPAÑOL"
        lang_rect = pygame.Rect(360, 428, 240, 36)
        renderer.draw_button(
            surface,
            lang_rect,
            f"[L] LANG: {lang_name}",
            is_hovered=(self._hovered_btn == "language"),
            accent_token=ThemeToken.TEXT_HIGHLIGHT,
            font_size=13,
        )

        renderer.draw_text(
            surface,
            "16-Bit SNES Golden Age Edition  |  [L] Language  |  [ENTER] Select",
            w // 2,
            500,
            token=ThemeToken.TEXT_MUTED,
            size=12,
            align="center",
        )
