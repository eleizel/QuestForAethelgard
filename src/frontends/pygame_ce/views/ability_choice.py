"""Pygame-CE 16-bit SNES Ability Draft and Skill Card Selection View."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame

from src.core.commands import ChooseAbilityCommand, SkipAbilityDraftCommand
from src.core.game_state import GameMode
from src.core.theme import ThemeToken
from src.systems.abilities import Ability, AbilityRarity, AbilityType
from src.systems.draft_service import DraftService
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.components.top_hud import TopHUDComponent
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


class PygameAbilityChoiceView(PygameView):
    """Ability draft screen offering 2 synergistic skill cards with slot replacement support."""

    def __init__(self) -> None:
        self.top_hud = TopHUDComponent()
        self.choices: list[Ability] = []
        self.pending_rarity: str = ""
        self.replace_mode: bool = False
        self.selected_ability: Ability | None = None
        self._hovered_card: int | None = None
        self._hovered_btn: str | None = None

        # Layout Rectangles (960x540 display)
        self.outer_rect = pygame.Rect(36, 56, 888, 472)
        self.card1_rect = pygame.Rect(72, 130, 390, 310)
        self.card2_rect = pygame.Rect(498, 130, 390, 310)
        self.skip_btn_rect = pygame.Rect(380, 458, 200, 40)

        # Replacement mode rects
        self.rep_card1_rect = pygame.Rect(72, 130, 390, 240)
        self.rep_card2_rect = pygame.Rect(498, 130, 390, 240)
        self.cancel_rep_rect = pygame.Rect(380, 468, 200, 38)

    def _init_choices(self, session: GameSession) -> None:
        """Query DraftService for synergistic candidate abilities or check offered_abilities test hook."""
        offered_override = getattr(session.state, "offered_abilities", None)
        if offered_override is not None and len(offered_override) > 0:
            self.choices = list(offered_override)
            return

        if not session.player.pending_ability_choices:
            self.choices = []
            return

        self.pending_rarity = session.player.pending_ability_choices[0]
        self.choices = DraftService.generate_draft(session.player, count=2)

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Handle mouse clicks and keyboard shortcuts for draft selection."""
        if self.top_hud.handle_event(event, session):
            return

        if not self.choices and (session.player.pending_ability_choices or getattr(session.state, "offered_abilities", None)):
            self._init_choices(session)

        if self.replace_mode and self.selected_ability:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_1, pygame.K_KP1):
                    self._apply_replacement(session, 0)
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    self._apply_replacement(session, 1)
                elif event.key == pygame.K_ESCAPE:
                    self.replace_mode = False
                    self.selected_ability = None
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if self.rep_card1_rect.collidepoint(pos):
                    self._apply_replacement(session, 0)
                elif self.rep_card2_rect.collidepoint(pos):
                    self._apply_replacement(session, 1)
                elif self.cancel_rep_rect.collidepoint(pos):
                    self.replace_mode = False
                    self.selected_ability = None
            return

        # Standard Draft Mode
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_1, pygame.K_KP1) and len(self.choices) > 0:
                self._handle_choice(session, self.choices[0])
            elif event.key in (pygame.K_2, pygame.K_KP2) and len(self.choices) > 1:
                self._handle_choice(session, self.choices[1])
            elif event.key in (pygame.K_s, pygame.K_ESCAPE):
                self._skip_draft(session)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if len(self.choices) > 0 and self.card1_rect.collidepoint(pos):
                self._handle_choice(session, self.choices[0])
            elif len(self.choices) > 1 and self.card2_rect.collidepoint(pos):
                self._handle_choice(session, self.choices[1])
            elif self.skip_btn_rect.collidepoint(pos):
                self._skip_draft(session)

    def _handle_choice(self, session: GameSession, chosen: Ability) -> None:
        """Apply chosen ability or enter replacement mode if slots full."""
        res = session.dispatch(ChooseAbilityCommand(ability=chosen))
        if res.success:
            self._finish_choice(session)
        else:
            self.replace_mode = True
            self.selected_ability = chosen

    def _apply_replacement(self, session: GameSession, slot_idx: int) -> None:
        """Replace ability in target slot and finish current draft choice."""
        if not self.selected_ability:
            return
        res = session.dispatch(ChooseAbilityCommand(ability=self.selected_ability, replace_index=slot_idx))
        if res.success:
            self._finish_choice(session)

    def _skip_draft(self, session: GameSession) -> None:
        """Discard active draft token and proceed."""
        session.dispatch(SkipAbilityDraftCommand())
        self._finish_choice(session)

    def _finish_choice(self, session: GameSession) -> None:
        """Route to next pending draft or resume spire route."""
        self.choices = []
        self.replace_mode = False
        self.selected_ability = None

        if session.player.pending_ability_choices:
            self._init_choices(session)
        elif getattr(session.state, "promotion_return_mode", None) is not None:
            ret_mode = session.state.promotion_return_mode
            session.state.promotion_return_mode = None
            if ret_mode == GameMode.LOOT:
                session.state.continue_after_rewards()
            else:
                session.switch_mode(ret_mode)
        else:
            session.state.continue_after_rewards()

    def update(self, dt: float, session: GameSession) -> None:
        """Ensure choices are initialized and update hover states."""
        if not self.choices and (session.player.pending_ability_choices or getattr(session.state, "offered_abilities", None)):
            self._init_choices(session)

        pos = pygame.mouse.get_pos()
        if self.replace_mode:
            self._hovered_card = 0 if self.rep_card1_rect.collidepoint(pos) else (1 if self.rep_card2_rect.collidepoint(pos) else None)
            self._hovered_btn = "cancel" if self.cancel_rep_rect.collidepoint(pos) else None
        else:
            self._hovered_card = 0 if self.card1_rect.collidepoint(pos) else (1 if self.card2_rect.collidepoint(pos) else None)
            self._hovered_btn = "skip" if self.skip_btn_rect.collidepoint(pos) else None

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render 16-bit SNES ability selection with ornate golden cards."""
        # 1. Dimmed Biome Background
        biome = getattr(session.state, "current_biome", "cathedral")
        assets.draw_background(surface, biome, vignette_alpha=150)

        # 2. Top HUD Bar
        self.top_hud.draw(surface, renderer, session)

        # 3. Outer Ornate Golden Container
        assets.draw_frame(surface, "frame_gold_ornate_hollow", self.outer_rect, margin=54)

        # 4. Header Plaque & Subtitle
        rarity_str = self.pending_rarity if self.pending_rarity else "STANDARD"
        if self.replace_mode and self.selected_ability:
            header_txt = "LOADOUT FULL: REPLACE ABILITY"
            target_type = self.selected_ability.ability_type.name.upper()
            subtitle = f"Select which {target_type} ability to replace with '{self.selected_ability.name}'"
        else:
            header_txt = f"LEVEL UP! {rarity_str} ABILITY CHOICE"
            subtitle = "Choose a combat technique to enhance your deck and battle readiness"

        renderer.draw_text(
            surface,
            header_txt,
            self.outer_rect.centerx,
            self.outer_rect.y + 24,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=22,
            bold=True,
            align="center",
        )
        renderer.draw_text(
            surface,
            subtitle,
            self.outer_rect.centerx,
            self.outer_rect.y + 48,
            token=ThemeToken.TEXT_MUTED,
            size=13,
            align="center",
        )

        # 5. Content Rendering
        if self.replace_mode and self.selected_ability:
            self._draw_replace_mode(surface, renderer, session)
        else:
            self._draw_draft_mode(surface, renderer, session)

    def _draw_draft_mode(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render candidate ability cards side-by-side."""
        cards = [(self.card1_rect, 0), (self.card2_rect, 1)]

        for card_rect, idx in cards:
            if idx >= len(self.choices):
                continue
            ab = self.choices[idx]
            is_hovered = (self._hovered_card == idx)
            self._render_ability_card(surface, renderer, card_rect, ab, idx + 1, is_hovered)

        # Skip Button
        is_skip_hovered = (self._hovered_btn == "skip")
        assets.draw_frame(surface, "frame_button_gold", self.skip_btn_rect, margin=20)
        if is_skip_hovered:
            glow = pygame.Surface(self.skip_btn_rect.size, pygame.SRCALPHA)
            glow.fill((255, 215, 0, 40))
            surface.blit(glow, self.skip_btn_rect.topleft)

        renderer.draw_text(
            surface,
            "[ S ] SKIP DRAFT",
            self.skip_btn_rect.centerx,
            self.skip_btn_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if is_skip_hovered else ThemeToken.TEXT_NORMAL,
            size=14,
            bold=True,
            align="center",
        )

    def _render_ability_card(
        self,
        surface: pygame.Surface,
        renderer: PygameRenderer,
        rect: pygame.Rect,
        ab: Ability,
        num_key: int,
        is_hovered: bool,
    ) -> None:
        """Render an individual 16-bit SNES stylized ability card."""
        # Dark backing
        bg_surf = pygame.Surface((rect.width - 8, rect.height - 8), pygame.SRCALPHA)
        bg_surf.fill((16, 20, 32, 235))
        surface.blit(bg_surf, (rect.x + 4, rect.y + 4))

        # Gold frame
        assets.draw_frame(surface, "frame_gold_clean", rect, margin=24)

        if is_hovered:
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(glow, (255, 215, 0, 45), glow.get_rect(), border_radius=6)
            surface.blit(glow, rect.topleft)

        # 1. Header Banner & Icon
        icon_size = 44
        icon_rect = pygame.Rect(rect.x + 16, rect.y + 16, icon_size, icon_size)
        pygame.draw.rect(surface, (10, 12, 18), icon_rect)
        pygame.draw.rect(surface, (218, 165, 32), icon_rect, width=1)

        icon_surf = assets.get_ability_icon(ab.id, (icon_size, icon_size))
        if icon_surf:
            surface.blit(icon_surf, icon_rect.topleft)

        # Ability Name & Key
        renderer.draw_text(
            surface,
            f"[{num_key}] {ab.name}",
            rect.x + 70,
            rect.y + 16,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=18,
            bold=True,
        )

        # Type & Rarity Badges
        type_str = ab.ability_type.name.upper()
        rarity_str = ab.rarity.name.upper()
        type_col = ThemeToken.ACCENT_PRIMARY if type_str == "ACTIVE" else ThemeToken.ACCENT_SECONDARY
        rarity_col = (255, 215, 0) if rarity_str == "EPIC" else (180, 200, 220)

        renderer.draw_text(
            surface,
            f"[{type_str}]",
            rect.x + 70,
            rect.y + 38,
            token=type_col,
            size=12,
            bold=True,
        )
        renderer.draw_text(
            surface,
            f"[{rarity_str}]",
            rect.x + 130,
            rect.y + 38,
            color=rarity_col,
            size=12,
            bold=True,
        )

        # Divider line
        pygame.draw.line(surface, (80, 70, 50), (rect.x + 16, rect.y + 68), (rect.right - 16, rect.y + 68), width=1)

        # 2. Cooldown & Mechanics Tag
        cd_val = getattr(ab, "cooldown", 0)
        if type_str == "ACTIVE":
            cd_text = f"Cooldown: {cd_val} turns" if cd_val > 0 else "Instant / No Cooldown"
        else:
            cd_text = "Passive: Always Active"

        renderer.draw_text(
            surface,
            cd_text,
            rect.x + 16,
            rect.y + 76,
            token=ThemeToken.TEXT_NORMAL,
            size=13,
            bold=True,
        )

        # Affinities if present
        if ab.affinities:
            aff_str = "Synergy: " + ", ".join(a.capitalize() for a in ab.affinities[:2])
            renderer.draw_text(
                surface,
                aff_str,
                rect.right - 16,
                rect.y + 76,
                token=ThemeToken.TEXT_MUTED,
                size=12,
                align="right",
            )

        # 3. Description (Word-wrapped)
        desc = ab.description or "A potent ability granting battlefield advantage."
        words = desc.split(" ")
        lines = []
        curr = ""
        for word in words:
            if len(curr) + len(word) < 42:
                curr += word + " "
            else:
                lines.append(curr.strip())
                curr = word + " "
        if curr:
            lines.append(curr.strip())

        for l_idx, line in enumerate(lines[:6]):
            renderer.draw_text(
                surface,
                line,
                rect.x + 16,
                rect.y + 104 + l_idx * 20,
                token=ThemeToken.TEXT_MUTED if not is_hovered else ThemeToken.TEXT_NORMAL,
                size=13,
            )

        # 4. Action Button at Bottom of Card
        btn_rect = pygame.Rect(rect.x + 20, rect.bottom - 46, rect.width - 40, 34)
        assets.draw_frame(surface, "frame_button_gold", btn_rect, margin=16)
        if is_hovered:
            btn_glow = pygame.Surface(btn_rect.size, pygame.SRCALPHA)
            btn_glow.fill((255, 215, 0, 50))
            surface.blit(btn_glow, btn_rect.topleft)

        renderer.draw_text(
            surface,
            f"SELECT [{num_key}]",
            btn_rect.centerx,
            btn_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if is_hovered else ThemeToken.TEXT_NORMAL,
            size=14,
            bold=True,
            align="center",
        )

    def _draw_replace_mode(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render slot replacement view when active or passive loadout is full."""
        if not self.selected_ability:
            return

        is_active = (self.selected_ability.ability_type == AbilityType.ACTIVE)
        equipped = session.player.abilities.active if is_active else session.player.abilities.passive

        cards = [(self.rep_card1_rect, 0), (self.rep_card2_rect, 1)]

        for card_rect, idx in cards:
            if idx >= len(equipped):
                continue
            ab = equipped[idx]
            is_hovered = (self._hovered_card == idx)

            # Draw card
            bg_surf = pygame.Surface((card_rect.width - 8, card_rect.height - 8), pygame.SRCALPHA)
            bg_surf.fill((16, 20, 32, 235))
            surface.blit(bg_surf, (card_rect.x + 4, card_rect.y + 4))

            assets.draw_frame(surface, "frame_gold_clean", card_rect, margin=24)

            if is_hovered:
                glow = pygame.Surface(card_rect.size, pygame.SRCALPHA)
                pygame.draw.rect(glow, (255, 140, 40, 45), glow.get_rect(), border_radius=6)
                surface.blit(glow, card_rect.topleft)

            # Slot label
            renderer.draw_text(
                surface,
                f"CURRENT SLOT {idx + 1}",
                card_rect.x + 16,
                card_rect.y + 14,
                token=ThemeToken.TEXT_MUTED,
                size=12,
                bold=True,
            )

            # Icon & Name
            icon_surf = assets.get_ability_icon(ab.id, (40, 40))
            if icon_surf:
                surface.blit(icon_surf, (card_rect.x + 16, card_rect.y + 32))

            renderer.draw_text(
                surface,
                ab.name,
                card_rect.x + 64,
                card_rect.y + 32,
                token=ThemeToken.TEXT_HIGHLIGHT,
                size=17,
                bold=True,
            )

            cd_txt = f"Cooldown: {ab.cooldown} turns" if ab.cooldown > 0 else "Passive"
            renderer.draw_text(
                surface,
                cd_txt,
                card_rect.x + 64,
                card_rect.y + 54,
                token=ThemeToken.TEXT_NORMAL,
                size=12,
            )

            # Short desc
            renderer.draw_text(
                surface,
                ab.description[:80] + ("..." if len(ab.description) > 80 else ""),
                card_rect.x + 16,
                card_rect.y + 80,
                token=ThemeToken.TEXT_MUTED,
                size=12,
            )

            # Replace button
            btn_rect = pygame.Rect(card_rect.x + 20, card_rect.bottom - 44, card_rect.width - 40, 34)
            assets.draw_frame(surface, "frame_button_gold", btn_rect, margin=16)
            if is_hovered:
                bglow = pygame.Surface(btn_rect.size, pygame.SRCALPHA)
                bglow.fill((255, 140, 40, 50))
                surface.blit(bglow, btn_rect.topleft)

            renderer.draw_text(
                surface,
                f"[ {idx + 1} ] REPLACE THIS SLOT",
                btn_rect.centerx,
                btn_rect.centery - 6,
                token=ThemeToken.TEXT_HIGHLIGHT if is_hovered else ThemeToken.TEXT_NORMAL,
                size=14,
                bold=True,
                align="center",
            )

        # Candidate Preview Plaque
        cand_rect = pygame.Rect(180, 386, 600, 68)
        pygame.draw.rect(surface, (20, 24, 38), cand_rect, border_radius=6)
        pygame.draw.rect(surface, (218, 165, 32), cand_rect, width=1, border_radius=6)

        c_icon = assets.get_ability_icon(self.selected_ability.id, (44, 44))
        if c_icon:
            surface.blit(c_icon, (cand_rect.x + 14, cand_rect.y + 12))

        renderer.draw_text(
            surface,
            f"NEW ABILITY: {self.selected_ability.name}",
            cand_rect.x + 68,
            cand_rect.y + 14,
            color=(255, 215, 0),
            size=16,
            bold=True,
        )
        renderer.draw_text(
            surface,
            self.selected_ability.description[:90] + ("..." if len(self.selected_ability.description) > 90 else ""),
            cand_rect.x + 68,
            cand_rect.y + 38,
            token=ThemeToken.TEXT_NORMAL,
            size=12,
        )

        # Cancel Button
        is_cancel_hovered = (self._hovered_btn == "cancel")
        assets.draw_frame(surface, "frame_button_gold", self.cancel_rep_rect, margin=16)
        if is_cancel_hovered:
            cglow = pygame.Surface(self.cancel_rep_rect.size, pygame.SRCALPHA)
            cglow.fill((255, 215, 0, 40))
            surface.blit(cglow, self.cancel_rep_rect.topleft)

        renderer.draw_text(
            surface,
            "[ ESC ] CANCEL REPLACEMENT",
            self.cancel_rep_rect.centerx,
            self.cancel_rep_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if is_cancel_hovered else ThemeToken.TEXT_NORMAL,
            size=13,
            bold=True,
            align="center",
        )
