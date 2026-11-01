"""Pygame-CE Class Selection & Route Customization View."""

from __future__ import annotations

from typing import TYPE_CHECKING
import pygame

from src.core.game_state import GameMode
from src.core.i18n import t
from src.core.theme import ThemeToken
from src.data.classes import CLASS_REGISTRY
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


class PygameClassSelectView(PygameView):
    """Class selection screen pulling dynamically from CLASS_REGISTRY with portraits and route toggle."""

    STARTER_CLASSES = ["warrior", "rogue", "mage"]

    def __init__(self) -> None:
        self.selected_index: int = 0
        self.route_mode: str = "FATE"  # "FATE" or "PATHFINDER"
        self._hovered_btn: str | None = None

    @property
    def selected_class_id(self) -> str:
        return self.STARTER_CLASSES[self.selected_index]

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Handle keyboard shortcuts and mouse clicks."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                session.switch_mode(GameMode.WELCOME)
            elif event.key == pygame.K_1:
                self.selected_index = 0
            elif event.key == pygame.K_2:
                self.selected_index = 1
            elif event.key == pygame.K_3:
                self.selected_index = 2
            elif event.key == pygame.K_LEFT:
                self.selected_index = (self.selected_index - 1) % len(self.STARTER_CLASSES)
            elif event.key == pygame.K_RIGHT:
                self.selected_index = (self.selected_index + 1) % len(self.STARTER_CLASSES)
            elif event.key in (pygame.K_b, pygame.K_t):
                self.route_mode = "PATHFINDER" if self.route_mode == "FATE" else "FATE"
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._confirm_selection(session)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            # Class card clicks
            for idx in range(3):
                card_rect = pygame.Rect(70 + idx * 280, 110, 260, 310)
                if card_rect.collidepoint(pos):
                    self.selected_index = idx
                    return

            # Route toggle button
            route_rect = pygame.Rect(260, 440, 200, 42)
            if route_rect.collidepoint(pos):
                self.route_mode = "PATHFINDER" if self.route_mode == "FATE" else "FATE"
                return

            # Start Journey button
            start_rect = pygame.Rect(480, 440, 220, 42)
            if start_rect.collidepoint(pos):
                self._confirm_selection(session)
                return

            # Back button
            back_rect = pygame.Rect(50, 440, 120, 42)
            if back_rect.collidepoint(pos):
                session.switch_mode(GameMode.WELCOME)
                return

    def _confirm_selection(self, session: GameSession) -> None:
        """Begin new run and advance to Map or Biome Selection."""
        session.start_new_game(class_id=self.selected_class_id, route_mode=self.route_mode)
        if self.route_mode == "PATHFINDER":
            session.switch_mode(GameMode.BIOME_SELECT)
        else:
            session.switch_mode(GameMode.MAP)

    def update(self, dt: float, session: GameSession) -> None:
        """Track mouse hover over buttons."""
        pos = pygame.mouse.get_pos()
        route_rect = pygame.Rect(260, 440, 200, 42)
        start_rect = pygame.Rect(480, 440, 220, 42)
        back_rect = pygame.Rect(50, 440, 120, 42)

        if route_rect.collidepoint(pos):
            self._hovered_btn = "route"
        elif start_rect.collidepoint(pos):
            self._hovered_btn = "start"
        elif back_rect.collidepoint(pos):
            self._hovered_btn = "back"
        else:
            self._hovered_btn = None

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render class cards with authentic pixel portraits and stats."""
        # 1. Background image
        assets.draw_background(surface, "welcome", vignette_alpha=140)

        w = surface.get_width()

        # Title
        renderer.draw_text(
            surface,
            t("class_select_title") if t("class_select_title") != "class_select_title" else "CHOOSE YOUR CHAMPION",
            w // 2,
            35,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=26,
            bold=True,
            align="center",
        )
        renderer.draw_text(
            surface,
            "Each archetype possesses distinct stat masteries and promotions at Level 10",
            w // 2,
            70,
            token=ThemeToken.TEXT_MUTED,
            size=14,
            align="center",
        )

        # 2. Render the 3 Starter Class Cards
        pos = pygame.mouse.get_pos()
        for idx, cid in enumerate(self.STARTER_CLASSES):
            cdef = CLASS_REGISTRY[cid]
            card_rect = pygame.Rect(70 + idx * 280, 110, 260, 310)
            is_selected = (self.selected_index == idx)
            is_hovered = card_rect.collidepoint(pos)

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

            # Class Portrait (96x128)
            portrait = assets.get_class_portrait(cid, scale=2)
            if portrait:
                surface.blit(portrait, (card_rect.centerx - 48, card_rect.y + 16))

            # Class Name
            name_text = f"[{idx+1}] {cdef.localized_name.upper()}"
            renderer.draw_text(
                surface,
                name_text,
                card_rect.centerx,
                card_rect.y + 150,
                token=ThemeToken.TEXT_HIGHLIGHT if is_selected else ThemeToken.TEXT_NORMAL,
                size=16,
                bold=True,
                align="center",
            )

            # Class Description
            renderer.draw_text(
                surface,
                cdef.localized_description,
                card_rect.centerx,
                card_rect.y + 175,
                token=ThemeToken.TEXT_MUTED,
                size=11,
                align="center",
            )

            # Base Stats Box
            stats = cdef.base_stats
            stat_y = card_rect.y + 205
            stat_lines = [
                f"HP: {stats.max_hp}    ATK: {stats.attack}    DEF: {stats.defense}",
                f"SPD: {stats.speed}   CRIT: {int(stats.crit_chance * 100)}%   GROWTH: +{cdef.growth_per_level.attack} ATK/lvl",
            ]
            for s_idx, line in enumerate(stat_lines):
                renderer.draw_text(
                    surface,
                    line,
                    card_rect.centerx,
                    stat_y + s_idx * 18,
                    token=ThemeToken.TEXT_NORMAL,
                    size=12,
                    bold=True,
                    align="center",
                )

            # Promotions Preview
            promo_names = " / ".join(p.capitalize() for p in cdef.promotions)
            renderer.draw_text(
                surface,
                f"Promotes: {promo_names}",
                card_rect.centerx,
                card_rect.y + 265,
                token=ThemeToken.ACCENT_SECONDARY,
                size=11,
                bold=True,
                align="center",
            )

        # 3. Bottom Controls Bar
        back_rect = pygame.Rect(50, 440, 120, 42)
        renderer.draw_button(
            surface,
            back_rect,
            "[ESC] BACK",
            is_hovered=(self._hovered_btn == "back"),
            accent_token=ThemeToken.BORDER_MUTED,
            font_size=13,
        )

        route_label = f"[B] ROUTE: {self.route_mode}"
        route_rect = pygame.Rect(260, 440, 200, 42)
        renderer.draw_button(
            surface,
            route_rect,
            route_label,
            is_hovered=(self._hovered_btn == "route"),
            accent_token=ThemeToken.ACCENT_SECONDARY,
            font_size=13,
        )

        start_rect = pygame.Rect(480, 440, 220, 42)
        renderer.draw_button(
            surface,
            start_rect,
            "START JOURNEY [ENTER]",
            is_hovered=(self._hovered_btn == "start"),
            accent_token=ThemeToken.TEXT_SUCCESS,
            font_size=14,
        )
