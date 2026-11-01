"""Pygame-CE Level 10 Class Promotion View."""

from __future__ import annotations

from typing import TYPE_CHECKING
import pygame

from src.core.commands import PromoteClassCommand
from src.core.game_state import GameMode
from src.core.theme import ThemeToken
from src.data.classes import CLASS_REGISTRY
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


class PygamePromotionView(PygameView):
    """Level 10 class specialization screen with promoted portraits and signature passives."""

    def __init__(self) -> None:
        self.selected_index: int = 0
        self._hovered_btn: str | None = None

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        promos = session.player.available_promotions() if hasattr(session.player, "available_promotions") else []

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_1, pygame.K_LEFT, pygame.K_a):
                self.selected_index = 0
            elif event.key in (pygame.K_2, pygame.K_RIGHT, pygame.K_d):
                self.selected_index = 1
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if 0 <= self.selected_index < len(promos):
                    self._confirm_promotion(session, promos[self.selected_index])

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for idx in range(len(promos)):
                card_rect = pygame.Rect(110 + idx * 390, 110, 350, 330)
                if card_rect.collidepoint(pos):
                    self.selected_index = idx
                    self._confirm_promotion(session, promos[idx])
                    return

    def _confirm_promotion(self, session: GameSession, promo_id: str) -> None:
        """Promote hero class and resume previous route mode."""
        session.dispatch(PromoteClassCommand(class_id=promo_id))
        return_mode = getattr(session.state, "promotion_return_mode", None)
        if return_mode:
            session.switch_mode(return_mode)
        else:
            session.switch_mode(GameMode.MAP)

    def update(self, dt: float, session: GameSession) -> None:
        pass

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        assets.draw_background(surface, "welcome", vignette_alpha=145)
        w = surface.get_width()

        renderer.draw_text(
            surface,
            "ASCENSION: LEVEL 10 PROMOTION",
            w // 2,
            35,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=28,
            bold=True,
            align="center",
        )
        renderer.draw_text(
            surface,
            "Your champion has reached mastery. Choose an elite specialization and claim its signature power",
            w // 2,
            70,
            token=ThemeToken.TEXT_MUTED,
            size=13,
            align="center",
        )

        promos = session.player.available_promotions() if hasattr(session.player, "available_promotions") else []
        pos = pygame.mouse.get_pos()

        for idx, pid in enumerate(promos[:2]):
            cdef = CLASS_REGISTRY.get(pid)
            if not cdef:
                continue

            card_rect = pygame.Rect(110 + idx * 390, 110, 350, 330)
            is_selected = (self.selected_index == idx)
            is_hovered = card_rect.collidepoint(pos)

            renderer.draw_panel(
                surface,
                card_rect,
                bg_token=ThemeToken.PANEL_BG,
                border_token=ThemeToken.ACCENT_PRIMARY if (is_selected or is_hovered) else ThemeToken.BORDER,
                border_width=3 if is_selected else 2,
                border_radius=8,
            )

            # Promoted Class Portrait (96x128)
            portrait = assets.get_class_portrait(pid, scale=2)
            if portrait:
                surface.blit(portrait, (card_rect.centerx - 48, card_rect.y + 16))

            # Class Name
            renderer.draw_text(
                surface,
                f"[{idx+1}] {cdef.localized_name.upper()}",
                card_rect.centerx,
                card_rect.y + 152,
                token=ThemeToken.TEXT_HIGHLIGHT if is_selected else ThemeToken.TEXT_NORMAL,
                size=18,
                bold=True,
                align="center",
            )

            # Description
            renderer.draw_text(
                surface,
                cdef.localized_description,
                card_rect.centerx,
                card_rect.y + 180,
                token=ThemeToken.TEXT_MUTED,
                size=12,
                align="center",
            )

            # Signature passive label
            sig_name = getattr(cdef, "signature_passive", "Mastery")
            renderer.draw_text(
                surface,
                f"Signature: {sig_name.replace('_', ' ').capitalize()}",
                card_rect.centerx,
                card_rect.y + 215,
                token=ThemeToken.ACCENT_SECONDARY,
                size=12,
                bold=True,
                align="center",
            )

            # Growth summary
            stats = cdef.growth_per_level
            renderer.draw_text(
                surface,
                f"Growth: +{stats.max_hp} HP  +{stats.attack} ATK  +{stats.defense} DEF / lvl",
                card_rect.centerx,
                card_rect.y + 238,
                token=ThemeToken.TEXT_NORMAL,
                size=11,
                align="center",
            )

            # Select Button
            btn_rect = pygame.Rect(card_rect.centerx - 80, card_rect.bottom - 45, 160, 34)
            renderer.draw_button(
                surface,
                btn_rect,
                f"PROMOTE [{idx+1}]",
                is_hovered=is_hovered,
                accent_token=ThemeToken.TEXT_SUCCESS if is_selected else ThemeToken.ACCENT_PRIMARY,
                font_size=13,
            )

        # Footnote
        renderer.draw_text(
            surface,
            "[1 / 2] Choose Specialization  |  [ENTER] Confirm Promotion",
            w // 2,
            475,
            token=ThemeToken.TEXT_MUTED,
            size=13,
            align="center",
        )
