"""Pygame-CE Biome Selection View for Pathfinder expedition routes."""

from __future__ import annotations

from typing import TYPE_CHECKING
import pygame

from src.core.game_state import GameMode
from src.core.i18n import t
from src.core.theme import ThemeToken
from src.data.biomes import ACT_BIOMES, BIOME_REGISTRY
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


class PygameBiomeSelectView(PygameView):
    """Panoramic biome selection screen displaying Act expedition branches in SNES pixel art."""

    def __init__(self) -> None:
        self.selected_index: int = 0
        self._hovered_index: int | None = None

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Handle keyboard navigation and mouse clicks."""
        act = session.state.act
        if act not in ACT_BIOMES:
            session.switch_mode(GameMode.MAP)
            return

        biome_a_id, biome_b_id = ACT_BIOMES[act]

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_1):
                self.selected_index = 0
            elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_2):
                self.selected_index = 1
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                chosen_id = biome_a_id if self.selected_index == 0 else biome_b_id
                session.state.advance_act(target_biome_id=chosen_id)
                session.switch_mode(GameMode.MAP)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            card_a_rect = pygame.Rect(110, 110, 350, 330)
            card_b_rect = pygame.Rect(500, 110, 350, 330)

            if card_a_rect.collidepoint(pos):
                self.selected_index = 0
                session.state.advance_act(target_biome_id=biome_a_id)
                session.switch_mode(GameMode.MAP)
            elif card_b_rect.collidepoint(pos):
                self.selected_index = 1
                session.state.advance_act(target_biome_id=biome_b_id)
                session.switch_mode(GameMode.MAP)

    def update(self, dt: float, session: GameSession) -> None:
        """Track mouse hover."""
        pos = pygame.mouse.get_pos()
        card_a_rect = pygame.Rect(110, 110, 350, 330)
        card_b_rect = pygame.Rect(500, 110, 350, 330)

        if card_a_rect.collidepoint(pos):
            self._hovered_index = 0
        elif card_b_rect.collidepoint(pos):
            self._hovered_index = 1
        else:
            self._hovered_index = None

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render side-by-side 16-bit SNES biome vista cards."""
        act = session.state.act
        if act not in ACT_BIOMES:
            return

        biome_a_id, biome_b_id = ACT_BIOMES[act]
        b_a = BIOME_REGISTRY[biome_a_id]
        b_b = BIOME_REGISTRY[biome_b_id]

        # Draw neutral welcome background
        assets.draw_background(surface, "welcome", vignette_alpha=150)

        w = surface.get_width()

        # Title
        renderer.draw_text(
            surface,
            f"ACT {act} EXPEDITION ROUTE",
            w // 2,
            35,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=26,
            bold=True,
            align="center",
        )
        renderer.draw_text(
            surface,
            "Pathfinder choice: select which perilous territory your champion shall traverse",
            w // 2,
            70,
            token=ThemeToken.TEXT_MUTED,
            size=14,
            align="center",
        )

        for idx, (bdef, card_rect) in enumerate([
            (b_a, pygame.Rect(110, 110, 350, 330)),
            (b_b, pygame.Rect(500, 110, 350, 330)),
        ]):
            is_selected = (self.selected_index == idx)
            is_hovered = (self._hovered_index == idx)

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

            # Biome Thumbnail Art (scaled 320x150)
            thumb = assets.get_background(bdef.id, width=320, height=140)
            if thumb:
                surface.blit(thumb, (card_rect.x + 15, card_rect.y + 15))
                pygame.draw.rect(surface, renderer.color(ThemeToken.BORDER), pygame.Rect(card_rect.x + 15, card_rect.y + 15, 320, 140), width=1)

            # Biome Name
            renderer.draw_text(
                surface,
                f"[{idx+1}] {bdef.localized_name.upper()}",
                card_rect.centerx,
                card_rect.y + 168,
                token=ThemeToken.TEXT_HIGHLIGHT if is_selected else ThemeToken.TEXT_NORMAL,
                size=16,
                bold=True,
                align="center",
            )

            # Threat Tags
            renderer.draw_text(
                surface,
                bdef.localized_tags,
                card_rect.centerx,
                card_rect.y + 196,
                token=ThemeToken.TEXT_ALERT,
                size=12,
                bold=True,
                align="center",
            )

            # Biome Description
            desc_lines = [bdef.localized_description[i:i+40] for i in range(0, len(bdef.localized_description), 40)]
            for line_idx, line in enumerate(desc_lines[:3]):
                renderer.draw_text(
                    surface,
                    line,
                    card_rect.centerx,
                    card_rect.y + 225 + line_idx * 18,
                    token=ThemeToken.TEXT_MUTED,
                    size=12,
                    align="center",
                )

            # Select button prompt
            btn_rect = pygame.Rect(card_rect.centerx - 80, card_rect.y + 285, 160, 32)
            renderer.draw_button(
                surface,
                btn_rect,
                "SELECT ROUTE",
                is_hovered=is_hovered,
                accent_token=ThemeToken.TEXT_SUCCESS if is_selected else ThemeToken.ACCENT_PRIMARY,
                font_size=12,
            )

        # Footnote
        renderer.draw_text(
            surface,
            "[1 / 2] Select Biome  |  [ENTER] Confirm Expedition",
            w // 2,
            490,
            token=ThemeToken.TEXT_MUTED,
            size=13,
            align="center",
        )
