"""Pygame-CE 16-bit SNES Level 10 Class Promotion View."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame

from src.core.commands import PromoteClassCommand
from src.core.events import AudioCue, AudioCueEvent, event_bus
from src.core.game_state import GameMode
from src.core.theme import ThemeToken
from src.data.classes import CLASS_REGISTRY
from src.data.abilities import get_ability_by_id
from src.systems.progression_service import ProgressionService
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.components.top_hud import TopHUDComponent
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


PROMOTION_PASSIVES: dict[str, str] = {
    "paladin": "paladin_guard",
    "berserker": "blood_frenzy",
    "venomancer": "venomous_accumulation",
    "duelist": "whirlwind_defense",
    "archmage": "arcane_reservoir",
    "warlock": "summon_imp",
}


class PygamePromotionView(PygameView):
    """Level 10 class specialization screen with promoted portraits, stats, and signature passives."""

    def __init__(self) -> None:
        self.top_hud = TopHUDComponent()
        self.selected_index: int | None = None
        self._hovered_card: int | None = None
        self._hovered_btn: int | None = None

        # Display Rectangles (960x540 display)
        self.outer_rect = pygame.Rect(36, 56, 888, 472)
        self.card1_rect = pygame.Rect(64, 120, 400, 396)
        self.card2_rect = pygame.Rect(496, 120, 400, 396)

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Handle keyboard navigation and mouse clicks for class promotion."""
        if session.current_mode != GameMode.PROMOTION:
            return

        if self.top_hud.handle_event(event, session):
            return

        promos = session.player.available_promotions() if hasattr(session.player, "available_promotions") else []
        if not promos:
            self._exit_without_promo(session)
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_1, pygame.K_KP1) and len(promos) > 0:
                self._select_or_promote(session, 0, promos[0])
            elif event.key in (pygame.K_2, pygame.K_KP2) and len(promos) > 1:
                self._select_or_promote(session, 1, promos[1])
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.selected_index = 0
            elif event.key in (pygame.K_RIGHT, pygame.K_d) and len(promos) > 1:
                self.selected_index = 1
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                idx = self.selected_index if self.selected_index is not None else 0
                if 0 <= idx < len(promos):
                    self._confirm_promotion(session, promos[idx])

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            cards = [(self.card1_rect, 0), (self.card2_rect, 1)]
            for card_rect, idx in cards:
                if idx < len(promos) and card_rect.collidepoint(pos):
                    self._select_or_promote(session, idx, promos[idx])
                    return

    def _select_or_promote(self, session: GameSession, index: int, class_id: str) -> bool:
        """Select class card on first click/key, confirm promotion on second."""
        if self.selected_index != index:
            self.selected_index = index
            event_bus.emit_audio(AudioCue.CLICK)
            return False

        return self._confirm_promotion(session, class_id)

    def _confirm_promotion(self, session: GameSession, promo_id: str) -> bool:
        """Promote hero class and advance directly to the Level 10 Epic ability draft."""
        res = session.dispatch(PromoteClassCommand(class_id=promo_id))
        if res.success:
            # Level 10 Epic Draft is tied to class promotion - switch directly to ABILITY_CHOICE
            session.switch_mode(GameMode.ABILITY_CHOICE)
            return True
        return False

    def _exit_without_promo(self, session: GameSession) -> None:
        """Fallback exit if no promotions available."""
        ret_mode = getattr(session.state, "promotion_return_mode", None)
        session.state.promotion_return_mode = None
        if ret_mode == GameMode.LOOT or ret_mode is None:
            session.state.continue_after_rewards()
        else:
            session.switch_mode(ret_mode)

    def update(self, dt: float, session: GameSession) -> None:
        """Update hover state."""
        pos = pygame.mouse.get_pos()
        self._hovered_card = 0 if self.card1_rect.collidepoint(pos) else (1 if self.card2_rect.collidepoint(pos) else None)

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render 16-bit SNES class promotion screen."""
        # 1. Dimmed Biome Background
        biome = getattr(session.state, "current_biome", "cathedral")
        assets.draw_background(surface, biome, vignette_alpha=150)

        # 2. Top HUD Bar
        self.top_hud.draw(surface, renderer, session)

        # 3. Outer Ornate Golden Frame
        assets.draw_frame(surface, "frame_gold_ornate_hollow", self.outer_rect, margin=54)

        # 4. Header Titles
        renderer.draw_text(
            surface,
            "HERO CLASS PROMOTION",
            self.outer_rect.centerx,
            self.outer_rect.y + 20,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=22,
            bold=True,
            align="center",
        )
        renderer.draw_text(
            surface,
            "Ascend beyond mortal limits. Choose your elite specialization and claim its signature power",
            self.outer_rect.centerx,
            self.outer_rect.y + 44,
            token=ThemeToken.TEXT_MUTED,
            size=13,
            align="center",
        )

        promos = session.player.available_promotions() if hasattr(session.player, "available_promotions") else []
        rec_class = ProgressionService.get_recommended_promotion(session.player)

        cards = [(self.card1_rect, 0), (self.card2_rect, 1)]
        for card_rect, idx in cards:
            if idx >= len(promos):
                continue
            cid = promos[idx]
            is_selected = (self.selected_index == idx)
            is_hovered = (self._hovered_card == idx)
            is_rec = (cid == rec_class)
            self._render_promotion_card(
                surface, renderer, card_rect, cid, idx + 1, is_selected, is_hovered, is_rec
            )

    def _render_promotion_card(
        self,
        surface: pygame.Surface,
        renderer: PygameRenderer,
        rect: pygame.Rect,
        class_id: str,
        num_key: int,
        is_selected: bool,
        is_hovered: bool,
        is_recommended: bool,
    ) -> None:
        """Render dual class card with portrait, crest, stats, and signature passive."""
        cdef = CLASS_REGISTRY.get(class_id)
        if not cdef:
            return

        # 1. Dark Card Backdrop
        bg_surf = pygame.Surface((rect.width - 8, rect.height - 8), pygame.SRCALPHA)
        bg_surf.fill((16, 20, 32, 240))
        surface.blit(bg_surf, (rect.x + 4, rect.y + 4))

        # 2. Card Frame
        assets.draw_frame(surface, "frame_gold_clean", rect, margin=24)

        if is_selected or is_hovered:
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            alpha = 55 if is_selected else 35
            glow_col = (255, 215, 0, alpha) if is_selected else (200, 200, 255, alpha)
            pygame.draw.rect(glow, glow_col, glow.get_rect(), border_radius=6)
            surface.blit(glow, rect.topleft)

        # 3. Top Art Window (Portrait & Crest)
        art_w, art_h = 130, 140
        art_rect = pygame.Rect(rect.x + 16, rect.y + 14, art_w, art_h)
        pygame.draw.rect(surface, (10, 12, 18), art_rect)
        pygame.draw.rect(surface, (218, 165, 32) if is_selected else (70, 80, 100), art_rect, width=1)

        portrait = assets.get_class_portrait(class_id, size=(art_w - 6, art_h - 6))
        if portrait:
            surface.blit(portrait, (art_rect.x + 3, art_rect.y + 3))

        # Info column next to portrait
        info_x = rect.x + 158
        renderer.draw_text(
            surface,
            f"[{num_key}] {cdef.localized_name.upper()}",
            info_x,
            rect.y + 14,
            token=ThemeToken.TEXT_HIGHLIGHT if is_selected else ThemeToken.TEXT_NORMAL,
            size=19,
            bold=True,
        )

        # Crest icon
        crest = assets.get_class_crest(class_id, size=(32, 32))
        if crest:
            surface.blit(crest, (rect.right - 48, rect.y + 10))

        # Recommended Badge
        if is_recommended:
            rec_rect = pygame.Rect(info_x, rect.y + 38, 130, 20)
            pygame.draw.rect(surface, (20, 60, 70), rec_rect, border_radius=3)
            pygame.draw.rect(surface, (80, 220, 240), rec_rect, width=1, border_radius=3)
            renderer.draw_text(
                surface,
                "RECOMMENDED",
                rec_rect.centerx,
                rec_rect.centery - 5,
                color=(120, 240, 255),
                size=11,
                bold=True,
                align="center",
            )

        # Lore description (compact)
        desc = cdef.description or "An elite class specialization."
        words = desc.split(" ")
        lines = []
        curr = ""
        for word in words:
            if len(curr) + len(word) < 28:
                curr += word + " "
            else:
                lines.append(curr.strip())
                curr = word + " "
        if curr:
            lines.append(curr.strip())

        desc_y = rect.y + 64 if is_recommended else rect.y + 42
        for li, line in enumerate(lines[:4]):
            renderer.draw_text(
                surface,
                line,
                info_x,
                desc_y + li * 18,
                token=ThemeToken.TEXT_MUTED,
                size=12,
            )

        # Divider line
        pygame.draw.line(surface, (80, 70, 50), (rect.x + 16, rect.y + 162), (rect.right - 16, rect.y + 162), width=1)

        # 4. Stat Growth Affinities (2 columns)
        growth = cdef.growth_per_level
        renderer.draw_text(
            surface,
            "GROWTH PER LEVEL",
            rect.x + 16,
            rect.y + 168,
            color=(240, 180, 80),
            size=12,
            bold=True,
        )

        col1_x = rect.x + 16
        col2_x = rect.x + 200

        # Row 1: HP & SPD
        hp_icon = assets.get_stat_icon("hp", size=(16, 16))
        if hp_icon:
            surface.blit(hp_icon, (col1_x, rect.y + 188))
        renderer.draw_text(surface, f"HP   +{growth.max_hp}", col1_x + 22, rect.y + 190, token=ThemeToken.TEXT_NORMAL, size=13)

        spd_icon = assets.get_stat_icon("spd", size=(16, 16))
        if spd_icon:
            surface.blit(spd_icon, (col2_x, rect.y + 188))
        renderer.draw_text(surface, f"SPD  +{growth.speed}", col2_x + 22, rect.y + 190, token=ThemeToken.TEXT_NORMAL, size=13)

        # Row 2: ATK & DEF
        atk_icon = assets.get_stat_icon("atk", size=(16, 16))
        if atk_icon:
            surface.blit(atk_icon, (col1_x, rect.y + 210))
        renderer.draw_text(surface, f"ATK  +{growth.attack}", col1_x + 22, rect.y + 212, token=ThemeToken.TEXT_NORMAL, size=13)

        def_icon = assets.get_stat_icon("def", size=(16, 16))
        if def_icon:
            surface.blit(def_icon, (col2_x, rect.y + 210))
        renderer.draw_text(surface, f"DEF  +{growth.defense}", col2_x + 22, rect.y + 212, token=ThemeToken.TEXT_NORMAL, size=13)

        # Row 3: CRIT
        crit_icon = assets.get_stat_icon("crit", size=(16, 16))
        if crit_icon:
            surface.blit(crit_icon, (col1_x, rect.y + 232))
        renderer.draw_text(surface, f"CRIT +{growth.crit_chance * 100:.1f}%", col1_x + 22, rect.y + 234, token=ThemeToken.TEXT_NORMAL, size=13)

        # Divider line
        pygame.draw.line(surface, (80, 70, 50), (rect.x + 16, rect.y + 256), (rect.right - 16, rect.y + 256), width=1)

        # 5. Signature Passive
        renderer.draw_text(
            surface,
            "SIGNATURE PASSIVE",
            rect.x + 16,
            rect.y + 262,
            color=(240, 180, 80),
            size=12,
            bold=True,
        )

        passive_id = getattr(cdef, "signature_passive", None) or PROMOTION_PASSIVES.get(class_id, "")
        p_ability = get_ability_by_id(passive_id) if passive_id else None

        if p_ability:
            p_icon = assets.get_ability_icon(passive_id, (36, 36))
            if p_icon:
                surface.blit(p_icon, (rect.x + 16, rect.y + 280))

            renderer.draw_text(
                surface,
                p_ability.name,
                rect.x + 58,
                rect.y + 280,
                token=ThemeToken.TEXT_HIGHLIGHT,
                size=15,
                bold=True,
            )

            p_desc = p_ability.description or "Unique passive ability granted upon class promotion."
            p_words = p_desc.split(" ")
            p_lines = []
            p_curr = ""
            for word in p_words:
                if len(p_curr) + len(word) < 44:
                    p_curr += word + " "
                else:
                    p_lines.append(p_curr.strip())
                    p_curr = word + " "
            if p_curr:
                p_lines.append(p_curr.strip())

            for pli, pline in enumerate(p_lines[:3]):
                renderer.draw_text(
                    surface,
                    pline,
                    rect.x + 58,
                    rect.y + 300 + pli * 17,
                    token=ThemeToken.TEXT_MUTED,
                    size=12,
                )

        # 6. Action Button at Bottom
        btn_rect = pygame.Rect(rect.x + 20, rect.bottom - 46, rect.width - 40, 36)
        assets.draw_frame(surface, "frame_button_gold", btn_rect, margin=20)
        if is_selected or is_hovered:
            bglow = pygame.Surface(btn_rect.size, pygame.SRCALPHA)
            bglow.fill((255, 215, 0, 50))
            surface.blit(bglow, btn_rect.topleft)

        btn_label = f"ASCEND TO {cdef.localized_name.upper()} [{num_key}]"
        renderer.draw_text(
            surface,
            btn_label,
            btn_rect.centerx,
            btn_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if is_selected else ThemeToken.TEXT_NORMAL,
            size=14,
            bold=True,
            align="center",
        )
