"""Pygame-CE Ability Draft & Skill Card Selection View."""

from __future__ import annotations

from typing import TYPE_CHECKING
import pygame

from src.core.commands import ChooseAbilityCommand, SkipAbilityDraftCommand
from src.core.game_state import GameMode
from src.core.theme import ThemeToken
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


class PygameAbilityChoiceView(PygameView):
    """Ability draft screen offering 3 synergistic skill cards with slot replacement support."""

    def __init__(self) -> None:
        self.selected_card_idx: int = 0
        self.replacing_slot: int = 0  # 0 or 1 for slot replacement
        self._hovered_btn: str | None = None

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        offered = getattr(session.state, "offered_abilities", [])

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                idx = event.key - pygame.K_1
                if 0 <= idx < len(offered):
                    self.selected_card_idx = idx
                    self._pick_ability(session, offered[idx])
            elif event.key in (pygame.K_s, pygame.K_ESCAPE):
                session.dispatch(SkipAbilityDraftCommand())
                session.state.continue_after_rewards()
            elif event.key == pygame.K_TAB:
                self.replacing_slot = 1 - self.replacing_slot

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            # Check card clicks
            for idx in range(len(offered)):
                card_rect = pygame.Rect(70 + idx * 280, 110, 260, 320)
                if card_rect.collidepoint(pos):
                    self.selected_card_idx = idx
                    self._pick_ability(session, offered[idx])
                    return

            # Skip button
            skip_rect = pygame.Rect(380, 460, 200, 40)
            if skip_rect.collidepoint(pos):
                session.dispatch(SkipAbilityDraftCommand())
                session.state.continue_after_rewards()

    def _pick_ability(self, session: GameSession, ability) -> None:
        """Apply chosen ability draft command and advance route."""
        session.dispatch(ChooseAbilityCommand(ability=ability, replace_index=self.replacing_slot))
        session.state.continue_after_rewards()

    def update(self, dt: float, session: GameSession) -> None:
        pos = pygame.mouse.get_pos()
        skip_rect = pygame.Rect(380, 460, 200, 40)
        self._hovered_btn = "skip" if skip_rect.collidepoint(pos) else None

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        biome = getattr(session.state, "current_biome", "cathedral")
        assets.draw_background(surface, biome, vignette_alpha=145)

        w = surface.get_width()

        renderer.draw_text(
            surface,
            "SKILL MASTERY DRAFT",
            w // 2,
            35,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=28,
            bold=True,
            align="center",
        )
        renderer.draw_text(
            surface,
            "Choose a new combat technique to enhance your deck and battle readiness",
            w // 2,
            70,
            token=ThemeToken.TEXT_MUTED,
            size=13,
            align="center",
        )

        offered = getattr(session.state, "offered_abilities", [])
        pos = pygame.mouse.get_pos()

        for idx, ab in enumerate(offered[:3]):
            card_rect = pygame.Rect(70 + idx * 280, 110, 260, 320)
            is_hovered = card_rect.collidepoint(pos)

            renderer.draw_panel(
                surface,
                card_rect,
                bg_token=ThemeToken.PANEL_BG,
                border_token=ThemeToken.ACCENT_PRIMARY if is_hovered else ThemeToken.BORDER,
                border_width=2 if is_hovered else 1,
                border_radius=8,
            )

            # Ability Type Badge
            type_label = ab.ability_type.name if hasattr(ab, "ability_type") else "SKILL"
            type_color = ThemeToken.ACCENT_PRIMARY if type_label == "ACTIVE" else ThemeToken.ACCENT_SECONDARY
            renderer.draw_text(surface, f"[{type_label}]", card_rect.centerx, card_rect.y + 20, token=type_color, size=13, bold=True, align="center")

            # Ability Name
            renderer.draw_text(surface, f"[{idx+1}] {ab.name}", card_rect.centerx, card_rect.y + 50, token=ThemeToken.TEXT_HIGHLIGHT, size=16, bold=True, align="center")

            # Cooldown / Cost
            cd_val = getattr(ab, "cooldown", 0)
            cd_text = f"Cooldown: {cd_val} turns" if cd_val > 0 else "Passive (Always Active)"
            renderer.draw_text(surface, cd_text, card_rect.centerx, card_rect.y + 78, token=ThemeToken.TEXT_MUTED, size=12, align="center")

            # Description (word wrapped)
            desc = ab.description
            words = desc.split(" ")
            lines = []
            curr_line = ""
            for word in words:
                if len(curr_line) + len(word) < 28:
                    curr_line += word + " "
                else:
                    lines.append(curr_line)
                    curr_line = word + " "
            if curr_line:
                lines.append(curr_line)

            for l_idx, line in enumerate(lines[:6]):
                renderer.draw_text(surface, line.strip(), card_rect.centerx, card_rect.y + 115 + l_idx * 18, token=ThemeToken.TEXT_NORMAL, size=12, align="center")

            # Learn Button
            btn_rect = pygame.Rect(card_rect.centerx - 70, card_rect.bottom - 45, 140, 32)
            renderer.draw_button(surface, btn_rect, f"LEARN [{idx+1}]", is_hovered=is_hovered, accent_token=ThemeToken.TEXT_SUCCESS, font_size=12)

        # Skip Button
        skip_rect = pygame.Rect(380, 460, 200, 40)
        renderer.draw_button(surface, skip_rect, "SKIP DRAFT [S]", is_hovered=(self._hovered_btn == "skip"), accent_token=ThemeToken.BORDER_MUTED, font_size=13)
