"""Pygame-CE 16-bit SNES Hero Character Sheet & Spellbook Modal View."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame

from src.core.game_state import GameMode
from src.core.i18n import t, i18n
from src.core.theme import ThemeToken
from src.systems.abilities import Ability, AbilityType
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.components.top_hud import TopHUDComponent
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


def format_stat_val(val: float | int) -> str:
    """Format combat stat numbers cleanly without floating artifacts."""
    rounded = round(float(val), 1)
    if rounded.is_integer():
        return str(int(rounded))
    return f"{rounded:.1f}"


class PygameCharacterModalView(PygameView):
    """Authentic 16-bit SNES hero character sheet with attributes, hero alcove, and spellbook."""

    def __init__(self) -> None:
        self.top_hud = TopHUDComponent()
        self._hovered_btn: str | None = None
        self._hovered_ability: str | None = None

        # Display Rectangles (960x540 display)
        self.outer_rect = pygame.Rect(28, 54, 904, 474)
        self.close_btn_rect = pygame.Rect(self.outer_rect.right - 80, self.outer_rect.y + 12, 48, 28)
        self.header_rect = pygame.Rect(self.outer_rect.centerx - 220, self.outer_rect.y + 8, 440, 36)

        self.left_rect = pygame.Rect(self.outer_rect.x + 16, self.outer_rect.y + 50, 388, 410)
        self.active_rect = pygame.Rect(self.outer_rect.x + 414, self.outer_rect.y + 50, 474, 196)
        self.passive_rect = pygame.Rect(self.outer_rect.x + 414, self.outer_rect.y + 254, 474, 206)

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Process keyboard shortcuts and mouse clicks for closing the character modal."""
        # Top HUD interactions
        if self.top_hud.handle_event(event, session):
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_c, pygame.K_ESCAPE):
                session.toggle_character()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.close_btn_rect.inflate(10, 10).collidepoint(pos):
                session.toggle_character()
            elif pos[1] >= 56 and not self.outer_rect.collidepoint(pos):
                # Clicked outside modal frame: close overlay
                session.toggle_character()

    def update(self, dt: float, session: GameSession) -> None:
        """Update button and ability card hover states."""
        pos = pygame.mouse.get_pos()
        self._hovered_btn = "close" if self.close_btn_rect.collidepoint(pos) else None

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render 16-bit SNES character sheet over dimmed underlying view."""
        w, h = surface.get_width(), surface.get_height()
        player = session.player
        stats = player.effective_stats

        # 1. Dimmed Backdrop Overlay
        backdrop = pygame.Surface((w, h), pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, 165))
        surface.blit(backdrop, (0, 0))

        # 2. Top HUD Bar
        self.top_hud.draw(surface, renderer, session)

        # 3. Main Modal Background & Outer Ornate Golden Frame
        bg_surf = pygame.Surface((self.outer_rect.width - 12, self.outer_rect.height - 12), pygame.SRCALPHA)
        bg_surf.fill((14, 16, 26, 248))
        surface.blit(bg_surf, (self.outer_rect.x + 6, self.outer_rect.y + 6))

        assets.draw_frame(surface, "frame_gold_ornate_hollow", self.outer_rect, margin=54)

        # 4. Header Plaque & Close Button
        assets.draw_frame(surface, "frame_button_gold", self.header_rect, margin=18)
        header_title = t("character_title")
        if header_title.startswith("character_"):
            header_title = "CHAMPION ATTRIBUTES & SPELLBOOK"

        renderer.draw_text(
            surface,
            header_title.upper(),
            self.header_rect.centerx,
            self.header_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=15,
            bold=True,
            align="center",
        )

        is_close_hovered = (self._hovered_btn == "close")
        assets.draw_frame(surface, "frame_button_gold", self.close_btn_rect, margin=14)
        if is_close_hovered:
            glow = pygame.Surface(self.close_btn_rect.size, pygame.SRCALPHA)
            glow.fill((255, 215, 0, 45))
            surface.blit(glow, self.close_btn_rect.topleft)

        renderer.draw_text(
            surface,
            "[ C ]",
            self.close_btn_rect.centerx,
            self.close_btn_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if is_close_hovered else ThemeToken.TEXT_NORMAL,
            size=13,
            bold=True,
            align="center",
        )

        # 5. Left Column: Hero Identity & Attributes
        self._draw_left_column(surface, renderer, session, player, stats)

        # 6. Right Column: Active Techniques & Passive Masteries
        self._draw_active_panel(surface, renderer, player)
        self._draw_passive_panel(surface, renderer, player)

    def _draw_left_column(
        self,
        surface: pygame.Surface,
        renderer: PygameRenderer,
        session: GameSession,
        player,
        stats,
    ) -> None:
        """Render hero bust alcove, identification, and effective attribute ratings."""
        rect = self.left_rect

        # Panel frame
        p_bg = pygame.Surface((rect.width - 8, rect.height - 8), pygame.SRCALPHA)
        p_bg.fill((18, 20, 32, 240))
        surface.blit(p_bg, (rect.x + 4, rect.y + 4))
        assets.draw_frame(surface, "frame_gold_clean", rect, margin=24)

        # A. Hero Bust Alcove
        alcove_rect = pygame.Rect(rect.x + 16, rect.y + 16, 114, 142)
        pygame.draw.rect(surface, (10, 12, 18), alcove_rect)
        pygame.draw.rect(surface, (218, 165, 32), alcove_rect, width=1)

        portrait = assets.get_class_portrait(player.class_id, size=(108, 136))
        if portrait:
            surface.blit(portrait, (alcove_rect.x + 3, alcove_rect.y + 3))

        # Identity Details (right of bust)
        idx_x = rect.x + 140
        crest = assets.get_class_crest(player.class_id, size=(34, 34))
        if crest:
            surface.blit(crest, (rect.right - 48, rect.y + 14))

        renderer.draw_text(
            surface,
            player.name.upper(),
            idx_x,
            rect.y + 16,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=17,
            bold=True,
        )

        class_name = getattr(player, "class_name", player.class_id.capitalize())
        renderer.draw_text(
            surface,
            f"Lv.{player.level} {class_name}",
            idx_x,
            rect.y + 40,
            token=ThemeToken.TEXT_NORMAL,
            size=14,
            bold=True,
        )

        # EXP Info & Bar
        exp_next = max(1, getattr(player, "exp_to_next_level", 100))
        exp_curr = getattr(player, "experience", 0)
        renderer.draw_text(
            surface,
            f"EXP: {exp_curr} / {exp_next}",
            idx_x,
            rect.y + 64,
            token=ThemeToken.TEXT_MUTED,
            size=12,
        )

        bar_rect = pygame.Rect(idx_x, rect.y + 82, 180, 8)
        pygame.draw.rect(surface, (25, 28, 42), bar_rect, border_radius=2)
        ratio = min(1.0, max(0.0, exp_curr / exp_next))
        if ratio > 0:
            fill_w = max(2, int(bar_rect.width * ratio))
            pygame.draw.rect(surface, (41, 173, 255), (bar_rect.x, bar_rect.y, fill_w, bar_rect.height), border_radius=2)
        pygame.draw.rect(surface, (120, 130, 160), bar_rect, width=1, border_radius=2)

        # Gold & Dungeon Floor
        renderer.draw_text(
            surface,
            f"Gold: {player.gold} G",
            idx_x,
            rect.y + 100,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=13,
            bold=True,
        )

        floor_num = getattr(session.state, "floor", 1)
        act_num = getattr(session.state, "act", 1)
        renderer.draw_text(
            surface,
            f"Floor: {floor_num} (Act {act_num})",
            idx_x,
            rect.y + 122,
            token=ThemeToken.TEXT_MUTED,
            size=12,
        )

        # Divider line
        div_y = rect.y + 168
        pygame.draw.line(surface, (80, 70, 50), (rect.x + 16, div_y), (rect.right - 16, div_y), width=1)

        # B. Effective Attributes Section
        renderer.draw_text(
            surface,
            "EFFECTIVE ATTRIBUTES",
            rect.x + 16,
            div_y + 8,
            color=(240, 185, 80),
            size=13,
            bold=True,
        )

        # Health Gauge Bar
        hp_y = div_y + 30
        hp_icon = assets.get_stat_icon("hp", (16, 16))
        if hp_icon:
            surface.blit(hp_icon, (rect.x + 16, hp_y))

        renderer.draw_text(
            surface,
            f"HP: {player.current_hp} / {stats.max_hp}",
            rect.x + 38,
            hp_y,
            token=ThemeToken.TEXT_NORMAL,
            size=13,
            bold=True,
        )

        hp_bar_rect = pygame.Rect(rect.x + 16, hp_y + 20, rect.width - 32, 10)
        pygame.draw.rect(surface, (30, 18, 24), hp_bar_rect, border_radius=2)
        hp_ratio = min(1.0, max(0.0, player.current_hp / max(1, stats.max_hp)))
        if hp_ratio > 0:
            hp_fill_w = max(2, int(hp_bar_rect.width * hp_ratio))
            pygame.draw.rect(surface, (230, 48, 64), (hp_bar_rect.x, hp_bar_rect.y, hp_fill_w, hp_bar_rect.height), border_radius=2)
        pygame.draw.rect(surface, (140, 70, 80), hp_bar_rect, width=1, border_radius=2)

        # Stat Grid (2 Columns with Icons)
        col1_x = rect.x + 16
        col2_x = rect.x + 200

        # Row 1: Attack & Speed
        r1_y = hp_y + 42
        atk_icon = assets.get_stat_icon("atk", (16, 16))
        if atk_icon:
            surface.blit(atk_icon, (col1_x, r1_y))
        renderer.draw_text(surface, f"ATK:  {format_stat_val(stats.attack)}", col1_x + 24, r1_y, token=ThemeToken.TEXT_NORMAL, size=13, bold=True)

        spd_icon = assets.get_stat_icon("spd", (16, 16))
        if spd_icon:
            surface.blit(spd_icon, (col2_x, r1_y))
        renderer.draw_text(surface, f"SPD:  {format_stat_val(stats.speed)}", col2_x + 24, r1_y, token=ThemeToken.TEXT_NORMAL, size=13, bold=True)

        # Row 2: Defense & Critical Chance
        r2_y = r1_y + 28
        def_icon = assets.get_stat_icon("def", (16, 16))
        if def_icon:
            surface.blit(def_icon, (col1_x, r2_y))
        renderer.draw_text(surface, f"DEF:  {format_stat_val(stats.defense)}", col1_x + 24, r2_y, token=ThemeToken.TEXT_NORMAL, size=13, bold=True)

        crit_icon = assets.get_stat_icon("crit", (16, 16))
        if crit_icon:
            surface.blit(crit_icon, (col2_x, r2_y))
        renderer.draw_text(surface, f"CRIT: {int(round(stats.crit_chance * 100))}%", col2_x + 24, r2_y, token=ThemeToken.TEXT_NORMAL, size=13, bold=True)

        # Row 3: Evade Charges & Stat Points
        r3_y = r2_y + 28
        renderer.draw_text(
            surface,
            f"EVADE: {getattr(player, 'evade_charges', 0)} Charges",
            col1_x,
            r3_y,
            token=ThemeToken.TEXT_MUTED,
            size=12,
        )

        stat_pts = getattr(player, "stat_points", 0)
        renderer.draw_text(
            surface,
            f"STAT PTS: {stat_pts}",
            col2_x,
            r3_y,
            token=ThemeToken.TEXT_HIGHLIGHT if stat_pts > 0 else ThemeToken.TEXT_MUTED,
            size=12,
            bold=(stat_pts > 0),
        )

        # Hint at bottom of left panel
        renderer.draw_text(
            surface,
            "[C] or [ESC] to return to journey",
            rect.centerx,
            rect.bottom - 22,
            token=ThemeToken.TEXT_MUTED,
            size=11,
            align="center",
        )

    def _draw_active_panel(
        self,
        surface: pygame.Surface,
        renderer: PygameRenderer,
        player,
    ) -> None:
        """Render equipped active technique cards with multi-line description wrap."""
        rect = self.active_rect

        # Panel frame
        p_bg = pygame.Surface((rect.width - 8, rect.height - 8), pygame.SRCALPHA)
        p_bg.fill((18, 20, 32, 240))
        surface.blit(p_bg, (rect.x + 4, rect.y + 4))
        assets.draw_frame(surface, "frame_gold_clean", rect, margin=24)

        # Header Title & Pill
        renderer.draw_text(
            surface,
            "ACTIVE TECHNIQUES (2 SLOTS)",
            rect.x + 16,
            rect.y + 12,
            color=(240, 185, 80),
            size=13,
            bold=True,
        )
        renderer.draw_text(
            surface,
            "[ACTIVE]",
            rect.right - 70,
            rect.y + 12,
            token=ThemeToken.ACCENT_PRIMARY,
            size=11,
            bold=True,
        )

        actives = getattr(player.abilities, "active", [])
        slot_h = 68
        for slot_idx in range(2):
            s_rect = pygame.Rect(rect.x + 14, rect.y + 36 + slot_idx * (slot_h + 8), rect.width - 28, slot_h)
            pygame.draw.rect(surface, (12, 14, 22), s_rect, border_radius=4)
            pygame.draw.rect(surface, (60, 65, 85), s_rect, width=1, border_radius=4)

            if slot_idx < len(actives):
                ab = actives[slot_idx]
                icon = assets.get_ability_icon(ab.id, (36, 36))
                if icon:
                    surface.blit(icon, (s_rect.x + 10, s_rect.y + 12))

                renderer.draw_text(
                    surface,
                    f"Slot {slot_idx + 1}: {ab.name}",
                    s_rect.x + 54,
                    s_rect.y + 8,
                    token=ThemeToken.TEXT_HIGHLIGHT,
                    size=14,
                    bold=True,
                )

                cd_txt = f"Cooldown: {ab.cooldown} turns" if ab.cooldown > 0 else "Instant / No Cooldown"
                renderer.draw_text(
                    surface,
                    cd_txt,
                    s_rect.right - 12,
                    s_rect.y + 8,
                    token=ThemeToken.TEXT_MUTED,
                    size=11,
                    align="right",
                )

                # Wrapped description
                desc = ab.description or "Active combat technique."
                words = desc.split(" ")
                lines = []
                curr = ""
                for word in words:
                    if len(curr) + len(word) < 52:
                        curr += word + " "
                    else:
                        lines.append(curr.strip())
                        curr = word + " "
                if curr:
                    lines.append(curr.strip())

                for li, line in enumerate(lines[:2]):
                    renderer.draw_text(
                        surface,
                        line,
                        s_rect.x + 54,
                        s_rect.y + 28 + li * 16,
                        token=ThemeToken.TEXT_NORMAL,
                        size=12,
                    )
            else:
                renderer.draw_text(
                    surface,
                    f"Slot {slot_idx + 1}: (Empty Slot)",
                    s_rect.centerx,
                    s_rect.centery - 6,
                    token=ThemeToken.TEXT_MUTED,
                    size=12,
                    align="center",
                )

    def _draw_passive_panel(
        self,
        surface: pygame.Surface,
        renderer: PygameRenderer,
        player,
    ) -> None:
        """Render signature passive and all learned passive masteries with multi-line description wrap."""
        rect = self.passive_rect

        # Panel frame
        p_bg = pygame.Surface((rect.width - 8, rect.height - 8), pygame.SRCALPHA)
        p_bg.fill((18, 20, 32, 240))
        surface.blit(p_bg, (rect.x + 4, rect.y + 4))
        assets.draw_frame(surface, "frame_gold_clean", rect, margin=24)

        # Header Title & Pill
        renderer.draw_text(
            surface,
            "PASSIVE MASTERIES & SIGNATURE",
            rect.x + 16,
            rect.y + 12,
            color=(240, 185, 80),
            size=13,
            bold=True,
        )
        renderer.draw_text(
            surface,
            "[PASSIVE]",
            rect.right - 70,
            rect.y + 12,
            token=ThemeToken.ACCENT_SECONDARY,
            size=11,
            bold=True,
        )

        all_passives = player.all_passives
        sig = player.signature_passive

        if not all_passives:
            renderer.draw_text(
                surface,
                "No passive abilities learned yet.",
                rect.centerx,
                rect.centery - 6,
                token=ThemeToken.TEXT_MUTED,
                size=12,
                align="center",
            )
            return

        slot_h = 52
        for p_idx, ab in enumerate(all_passives[:3]):
            s_rect = pygame.Rect(rect.x + 14, rect.y + 34 + p_idx * (slot_h + 6), rect.width - 28, slot_h)
            pygame.draw.rect(surface, (12, 14, 22), s_rect, border_radius=4)
            is_sig = (sig is not None and ab.id == sig.id)
            pygame.draw.rect(
                surface,
                (218, 165, 32) if is_sig else (60, 65, 85),
                s_rect,
                width=1,
                border_radius=4,
            )

            p_icon = assets.get_ability_icon(ab.id, (32, 32))
            if p_icon:
                surface.blit(p_icon, (s_rect.x + 8, s_rect.y + 10))

            renderer.draw_text(
                surface,
                ab.name,
                s_rect.x + 48,
                s_rect.y + 6,
                token=ThemeToken.TEXT_HIGHLIGHT if is_sig else ThemeToken.TEXT_NORMAL,
                size=13,
                bold=True,
            )

            if is_sig:
                renderer.draw_text(
                    surface,
                    "SIGNATURE",
                    s_rect.right - 12,
                    s_rect.y + 6,
                    color=(255, 200, 100),
                    size=11,
                    bold=True,
                    align="right",
                )

            # Wrapped description
            desc = ab.description or "Passive trait."
            words = desc.split(" ")
            lines = []
            curr = ""
            for word in words:
                if len(curr) + len(word) < 58:
                    curr += word + " "
                else:
                    lines.append(curr.strip())
                    curr = word + " "
            if curr:
                lines.append(curr.strip())

            for li, line in enumerate(lines[:2]):
                renderer.draw_text(
                    surface,
                    line,
                    s_rect.x + 48,
                    s_rect.y + 24 + li * 14,
                    token=ThemeToken.TEXT_MUTED,
                    size=11,
                )
