"""Advanced class promotion selection screen matching gothic visual standards."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pyxel

from src.config import (
    COLOR_BLACK,
    COLOR_BROWN,
    COLOR_CYAN,
    COLOR_DARK_BLUE,
    COLOR_GRAY,
    COLOR_GREEN,
    COLOR_LIGHT_BLUE,
    COLOR_LIME,
    COLOR_NAVY,
    COLOR_ORANGE,
    COLOR_PEACH,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SND_CLICK,
    SND_VICTORY, COLOR_PURPLE, COLOR_PINK,
)
from src.core.audio import audio
from src.core.game_state import GameMode
from src.core.i18n import i18n
from src.ui.renderer import Renderer
from src.ui.views.base import View

if TYPE_CHECKING:
    from src.core.game_state import GameState

PROMOTION_PASSIVES: dict[str, str] = {
    "paladin": "paladin_guard",
    "berserker": "blood_frenzy",
    "venomancer": "venomous_accumulation",
    "duelist": "whirlwind_defense",
    "archmage": "arcane_reservoir",
    "warlock": "summon_imp",
}


class PromotionView(View):
    """Advanced-class promotion selection with dual showcase cards and gothic framing."""

    def __init__(self) -> None:
        self.selected_index: int | None = None

    def _select_or_promote(self, game_state: GameState, index: int, class_id: str) -> bool:
        if self.selected_index != index:
            self.selected_index = index
            audio.play_sfx(SND_CLICK)
            return False
        if game_state.player.promote(class_id):
            audio.play_sfx(SND_VICTORY)
            game_state.switch_mode(GameMode.ABILITY_CHOICE)
            return True
        return False

    def _recommended_class(self, game_state: GameState) -> str:
        promotions = game_state.player.available_promotions()
        scores = {class_id: 0 for class_id in promotions}
        for ability in (*game_state.player.abilities.active, *game_state.player.abilities.passive):
            for class_id in promotions:
                scores[class_id] += ability.affinities.count(class_id)
        if not scores:
            return ""
        return max(promotions, key=lambda cid: (scores[cid], -promotions.index(cid)))

    def update(self, game_state: GameState) -> None:
        promotions = game_state.player.available_promotions()
        if not promotions:
            return_mode = getattr(game_state, "promotion_return_mode", None)
            game_state.promotion_return_mode = None
            if return_mode == GameMode.LOOT or return_mode is None:
                if hasattr(game_state, "continue_after_rewards"):
                    game_state.continue_after_rewards()
                else:
                    game_state.switch_mode(GameMode.MAP)
            else:
                game_state.switch_mode(return_mode)
            return

        if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
            self.selected_index = 0
            audio.play_sfx(SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
            self.selected_index = 1 if len(promotions) > 1 else 0
            audio.play_sfx(SND_CLICK)

        card_w, card_h = 116, 178
        card_y = 49
        for index, class_id in enumerate(promotions[:2]):
            card_x = 8 if index == 0 else 132
            clicked = Renderer.is_clicked(card_x, card_y, card_w, card_h)
            pressed = (index == 0 and (pyxel.btnp(pyxel.KEY_1) or pyxel.btnp(pyxel.KEY_KP_1))) or (
                    index == 1 and (pyxel.btnp(pyxel.KEY_2) or pyxel.btnp(pyxel.KEY_KP_2))
            )
            if (clicked or pressed) and self._select_or_promote(game_state, index, class_id):
                return

        if (pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE)) and self.selected_index < len(promotions):
            class_id = promotions[self.selected_index]
            self._select_or_promote(game_state, self.selected_index, class_id)

    def _draw_stat_icon(self, x: int, y: int, stat_type: str) -> None:
        """Render distinct 5x5 stat glyphs matching HUD aesthetic."""
        if stat_type == "hp":
            pyxel.pset(x + 1, y, COLOR_RED)
            pyxel.pset(x + 3, y, COLOR_RED)
            pyxel.rect(x, y + 1, 5, 2, COLOR_RED)
            pyxel.pset(x + 1, y + 3, COLOR_RED)
            pyxel.pset(x + 2, y + 3, COLOR_RED)
            pyxel.pset(x + 3, y + 3, COLOR_RED)
            pyxel.pset(x + 2, y + 4, COLOR_RED)
            pyxel.pset(x + 1, y + 1, COLOR_PINK)
        elif stat_type == "atk":
            pyxel.line(x, y, x + 4, y + 4, COLOR_WHITE)
            pyxel.line(x + 4, y, x, y + 4, COLOR_RED)
            pyxel.pset(x + 2, y + 2, COLOR_WHITE)
        elif stat_type == "def":
            pyxel.rect(x + 1, y, 3, 3, COLOR_CYAN)
            pyxel.pset(x, y + 1, COLOR_CYAN)
            pyxel.pset(x + 4, y + 1, COLOR_CYAN)
            pyxel.pset(x + 2, y + 4, COLOR_CYAN)
            pyxel.line(x + 1, y + 3, x + 3, y + 3, COLOR_CYAN)
            pyxel.pset(x + 2, y + 2, COLOR_WHITE)
        elif stat_type == "spd":
            pyxel.rect(x + 1, y, 2, 4, COLOR_YELLOW)
            pyxel.rect(x + 1, y + 3, 4, 2, COLOR_YELLOW)
            pyxel.pset(x + 4, y + 4, COLOR_WHITE)
        elif stat_type == "crit":
            pyxel.pset(x + 2, y, COLOR_YELLOW)
            pyxel.line(x, y + 2, x + 4, y + 2, COLOR_YELLOW)
            pyxel.pset(x + 2, y + 4, COLOR_YELLOW)
            pyxel.pset(x + 2, y + 2, COLOR_WHITE)

    def _draw_vignette_motif(self, mx: int, my: int, class_id: str) -> None:
        """Render distinct thematic vignette motifs to the left of the character bust."""
        fc = pyxel.frame_count
        if class_id == "venomancer":
            # Glass potion flask with bubbling lime acid fumes
            pyxel.rect(mx + 3, my + 10, 8, 9, COLOR_LIME)
            pyxel.rectb(mx + 3, my + 10, 8, 9, COLOR_GREEN)
            pyxel.rect(mx + 5, my + 7, 4, 3, COLOR_WHITE)
            pyxel.pset(mx + 5, my + 6, COLOR_BROWN)
            pyxel.pset(mx + 6, my + 6, COLOR_BROWN)
            pyxel.pset(mx + 5, my + 12, COLOR_WHITE)
            # Rising bubbling motes
            for i in range(4):
                bx = mx + 2 + ((fc * 2 + i * 5) % 11)
                by = my + 7 - ((fc + i * 4) % 12)
                pyxel.pset(bx, by, COLOR_LIME if i % 2 == 0 else COLOR_CYAN)

        elif class_id == "duelist":
            # Glistening blue parrying water-drop / blade glint
            pyxel.circ(mx + 6, my + 13, 5, COLOR_CYAN)
            pyxel.tri(mx + 6, my + 6, mx + 2, my + 13, mx + 10, my + 13, COLOR_CYAN)
            pyxel.pset(mx + 6, my + 12, COLOR_WHITE)
            pyxel.pset(mx + 7, my + 11, COLOR_LIGHT_BLUE)
            if (fc // 5) % 2 == 0:
                pyxel.pset(mx + 1, my + 8, COLOR_WHITE)
                pyxel.pset(mx + 11, my + 16, COLOR_CYAN)

        elif class_id == "paladin":
            # Consecrated holy golden chalice & sunburst
            pyxel.rect(mx + 3, my + 10, 8, 6, COLOR_YELLOW)
            pyxel.line(mx + 6, my + 16, mx + 7, my + 16, COLOR_YELLOW)
            pyxel.line(mx + 4, my + 18, mx + 9, my + 18, COLOR_YELLOW)
            pyxel.pset(mx + 6, my + 12, COLOR_WHITE)
            for i, ang in enumerate((0, 45, 90, 135, 180)):
                rad = math.radians(ang)
                px = mx + 6 + int(math.cos(rad) * 9)
                py = my + 10 - int(math.sin(rad) * 9)
                if (fc // 4 + i) % 2 == 0:
                    pyxel.pset(px, py, COLOR_YELLOW)

        elif class_id == "berserker":
            # Blazing crimson war skull & embers
            pyxel.rect(mx + 3, my + 9, 8, 7, COLOR_RED)
            pyxel.rect(mx + 4, my + 16, 6, 3, COLOR_RED)
            pyxel.pset(mx + 5, my + 12, COLOR_BLACK)
            pyxel.pset(mx + 8, my + 12, COLOR_BLACK)
            pyxel.pset(mx + 6, my + 14, COLOR_ORANGE)
            if (fc // 3) % 2 == 0:
                pyxel.pset(mx + 2, my + 7, COLOR_YELLOW)
                pyxel.pset(mx + 10, my + 6, COLOR_ORANGE)

        elif class_id == "archmage":
            # Swirling astral arcane orb
            pyxel.circ(mx + 6, my + 12, 5, COLOR_PURPLE)
            pyxel.circb(mx + 6, my + 12, 5, COLOR_CYAN)
            pyxel.pset(mx + 6, my + 12, COLOR_WHITE)
            for i in range(3):
                ox = mx + 6 + int(math.cos((fc * 0.15 + i * 2.1)) * 7)
                oy = my + 12 + int(math.sin((fc * 0.15 + i * 2.1)) * 4)
                pyxel.pset(ox, oy, COLOR_WHITE if i == 0 else COLOR_CYAN)

        else:  # warlock
            # Dark demonic skull with soulfire
            pyxel.rect(mx + 3, my + 10, 8, 6, COLOR_PURPLE)
            pyxel.pset(mx + 4, my + 12, COLOR_RED)
            pyxel.pset(mx + 8, my + 12, COLOR_RED)
            pyxel.pset(mx + 6, my + 8, COLOR_PINK if (fc // 4) % 2 == 0 else COLOR_PURPLE)

    def _draw_card(self, renderer: Renderer, class_id: str,
                   index: int, card_x: int, recommended: str) -> None:
        from src.data.abilities import get_ability_by_id
        from src.data.classes import CLASS_REGISTRY
        from src.tools.generate_assets import get_ability_icon, get_class_portrait

        fc = pyxel.frame_count
        pulse = (fc // 6) % 2

        card_y, card_w, card_h = 49, 116, 178
        is_recommended = (class_id == recommended)
        is_selected = (index == self.selected_index)

        border_col = COLOR_YELLOW if is_selected else (COLOR_CYAN if is_recommended else COLOR_LIGHT_BLUE)
        bg_col = COLOR_DARK_BLUE if is_selected else COLOR_BLACK
        renderer.draw_box(card_x, card_y, card_w, card_h, bg_col=bg_col, border_col=border_col)

        # Selected Gold Double Frame & Fleurons
        if is_selected:
            pyxel.rectb(card_x + 1, card_y + 1, card_w - 2, card_h - 2,
                        COLOR_YELLOW if pulse == 0 else COLOR_ORANGE)
            for cx, cy in ((card_x + 2, card_y + 2), (card_x + card_w - 3, card_y + 2),
                           (card_x + 2, card_y + card_h - 3), (card_x + card_w - 3, card_y + card_h - 3)):
                pyxel.pset(cx, cy, COLOR_WHITE)
                pyxel.pset(cx - 1, cy, COLOR_ORANGE)
                pyxel.pset(cx + 1, cy, COLOR_ORANGE)
                pyxel.pset(cx, cy - 1, COLOR_ORANGE)
                pyxel.pset(cx, cy + 1, COLOR_ORANGE)
        else:
            for cx, cy in ((card_x + 2, card_y + 2), (card_x + card_w - 3, card_y + 2),
                           (card_x + 2, card_y + card_h - 3), (card_x + card_w - 3, card_y + card_h - 3)):
                pyxel.pset(cx, cy, COLOR_LIGHT_BLUE)

        # ---------------------------------------------------------------------
        # 1. TOP VIGNETTE ART WINDOW (x+4, y+4, w=108, h=58)
        # ---------------------------------------------------------------------
        vx, vy, vw, vh = card_x + 4, card_y + 4, card_w - 8, 58
        pyxel.rect(vx, vy, vw, vh, COLOR_BLACK)
        pyxel.rectb(vx, vy, vw, vh, COLOR_DARK_BLUE)

        # Stone archway background
        arch_cx = vx + 64
        pyxel.rect(arch_cx - 24, vy + 4, 48, vh - 4, COLOR_NAVY)
        pyxel.tri(arch_cx - 24, vy + 4, arch_cx, vy - 2, arch_cx + 23, vy + 4, COLOR_NAVY)
        pyxel.rect(arch_cx - 20, vy + 8, 40, vh - 8, COLOR_BLACK)
        pyxel.tri(arch_cx - 20, vy + 8, arch_cx, vy + 1, arch_cx + 19, vy + 8, COLOR_BLACK)
        for col_x in [vx + 32, vx + 92]:
            pyxel.rect(col_x, vy + 4, 8, vh - 4, COLOR_NAVY)
            for py_line in range(vy + 8, vy + vh - 4, 8):
                pyxel.line(col_x, py_line, col_x + 7, py_line, COLOR_DARK_BLUE)

        # Left Thematic Vignette Motif
        self._draw_vignette_motif(vx + 6, vy + 12, class_id)

        # Character 48x64 Bust Portrait (centered right)
        portrait_bank, portrait_u, portrait_v = get_class_portrait(class_id)
        pyxel.blt(vx + 42, vy - 2, portrait_bank, portrait_u, portrait_v, 48, 60, 0)

        # ---------------------------------------------------------------------
        # 2. CLASS TITLE BANNER
        # ---------------------------------------------------------------------
        class_def = CLASS_REGISTRY[class_id]
        pw, ph = card_w - 8, 14
        px, py_banner = card_x + 4, card_y + 64

        banner_border = COLOR_YELLOW if is_selected else COLOR_LIGHT_BLUE
        pyxel.rect(px, py_banner, pw, ph, COLOR_BLACK)
        pyxel.rectb(px, py_banner, pw, ph, banner_border)

        # Corner and diamond tick endpoints on banner
        pyxel.line(px - 2, py_banner + 6, px + 1, py_banner + 6, banner_border)
        pyxel.line(px + pw - 2, py_banner + 6, px + pw + 1, banner_border)
        pyxel.pset(px + 2, py_banner + 2, COLOR_WHITE)
        pyxel.pset(px + pw - 3, py_banner + 2, COLOR_WHITE)

        title_str = f"[{index + 1}] {class_def.localized_name.upper()}"
        renderer.draw_text(card_x + (card_w - renderer.get_text_width(title_str)) // 2,
                           py_banner + 4, title_str, COLOR_YELLOW if is_selected else COLOR_WHITE)

        # ---------------------------------------------------------------------
        # 3. RECOMMENDED BADGE / SUBTITLE
        # ---------------------------------------------------------------------
        sub_y = card_y + 80
        if is_recommended:
            rec_str = "✦ RECOMMENDED ✦" if i18n.locale == "en" else "✦ RECOMENDADA ✦"
            renderer.draw_text(card_x + (card_w - renderer.get_text_width(rec_str)) // 2,
                               sub_y, rec_str, COLOR_CYAN)

        # ---------------------------------------------------------------------
        # 4. CLASS LORE DESCRIPTION (Centered)
        # ---------------------------------------------------------------------
        desc_lines = renderer.wrap_text(class_def.localized_description, max_chars_per_line=24)
        desc_start_y = card_y + 88
        for li, line in enumerate(desc_lines[:3]):
            tw = renderer.get_text_width(line)
            renderer.draw_text(card_x + (card_w - tw) // 2, desc_start_y + li * 8, line, COLOR_WHITE)

        # ---------------------------------------------------------------------
        # 5. FIRST DIAMOND DIVIDER
        # ---------------------------------------------------------------------
        div1_y = card_y + 114
        pyxel.line(card_x + 8, div1_y, card_x + card_w - 9, div1_y, COLOR_NAVY)
        mid_x = card_x + card_w // 2
        pyxel.pset(mid_x, div1_y - 1, COLOR_PEACH)
        pyxel.pset(mid_x, div1_y + 1, COLOR_PEACH)
        pyxel.pset(mid_x - 1, div1_y, COLOR_PEACH)
        pyxel.pset(mid_x + 1, div1_y, COLOR_PEACH)
        pyxel.pset(mid_x, div1_y, COLOR_WHITE)

        # ---------------------------------------------------------------------
        # 6. GROWTH / LEVEL (2-Column Stat Grid with Pixel Glyphs)
        # ---------------------------------------------------------------------
        growth_title = "GROWTH / LEVEL" if i18n.locale == "en" else "CRECIMIENTO / NIVEL"
        renderer.draw_text(card_x + 8, card_y + 118, growth_title, COLOR_PEACH)

        growth = class_def.growth_per_level
        col1_x = card_x + 8
        col2_x = card_x + 62

        # Row 1
        self._draw_stat_icon(col1_x, card_y + 127, "hp")
        renderer.draw_text(col1_x + 8, card_y + 127, f"HP   +{growth.max_hp}", COLOR_WHITE)
        self._draw_stat_icon(col2_x, card_y + 127, "spd")
        renderer.draw_text(col2_x + 8, card_y + 127, f"SPD  +{growth.speed}", COLOR_WHITE)

        # Row 2
        self._draw_stat_icon(col1_x, card_y + 136, "atk")
        renderer.draw_text(col1_x + 8, card_y + 136, f"ATK  +{growth.attack}", COLOR_WHITE)
        self._draw_stat_icon(col2_x, card_y + 136, "crit")
        renderer.draw_text(col2_x + 8, card_y + 136, f"CRIT +{growth.crit_chance * 100:.1f}%", COLOR_WHITE)

        # Row 3
        self._draw_stat_icon(col1_x, card_y + 145, "def")
        renderer.draw_text(col1_x + 8, card_y + 145, f"DEF  +{growth.defense}", COLOR_WHITE)

        # ---------------------------------------------------------------------
        # 7. SECOND DIAMOND DIVIDER
        # ---------------------------------------------------------------------
        div2_y = card_y + 153
        pyxel.line(card_x + 8, div2_y, card_x + card_w - 9, div2_y, COLOR_NAVY)
        pyxel.pset(mid_x, div2_y - 1, COLOR_PEACH)
        pyxel.pset(mid_x, div2_y + 1, COLOR_PEACH)
        pyxel.pset(mid_x - 1, div2_y, COLOR_PEACH)
        pyxel.pset(mid_x + 1, div2_y, COLOR_PEACH)
        pyxel.pset(mid_x, div2_y, COLOR_WHITE)

        # ---------------------------------------------------------------------
        # 8. SIGNATURE PASSIVE (16x16 Icon Frame + Details)
        # ---------------------------------------------------------------------
        passive_title = "SIGNATURE PASSIVE" if i18n.locale == "en" else "PASIVA EMBLEMATICA"
        renderer.draw_text(card_x + 8, card_y + 156, passive_title, COLOR_PEACH)

        passive_id = getattr(class_def, "signature_passive", None) or PROMOTION_PASSIVES.get(class_id, "")
        ability = get_ability_by_id(passive_id) if passive_id else None

        icon_x = card_x + 7
        icon_y = card_y + 165
        pyxel.rect(icon_x, icon_y, 16, 16, COLOR_NAVY)
        pyxel.rectb(icon_x, icon_y, 16, 16, COLOR_LIGHT_BLUE if is_selected else COLOR_DARK_BLUE)

        if ability:
            bank, u, v = get_ability_icon(ability.id)
            pyxel.blt(icon_x, icon_y, bank, u, v, 16, 16, 0)
            renderer.draw_text(icon_x + 19, icon_y, ability.localized_name[:18], COLOR_CYAN)
            p_lines = renderer.wrap_text(ability.localized_description, max_chars_per_line=18)
            for li, pline in enumerate(p_lines[:2]):
                renderer.draw_text(icon_x + 19, icon_y + 8 + li * 7, pline, COLOR_WHITE)
        else:
            renderer.draw_text(icon_x + 19, icon_y + 4, "None", COLOR_GRAY)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        box_x, box_y = 4, 25
        box_w, box_h = SCREEN_WIDTH - 8, SCREEN_HEIGHT - 28
        fc = pyxel.frame_count

        pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

        # Flanking wall pillars
        for col_x in [14, 44, SCREEN_WIDTH - 52, SCREEN_WIDTH - 22]:
            pyxel.rect(col_x, box_y + 2, 8, 22, COLOR_NAVY)
            pyxel.line(col_x, box_y + 8, col_x + 7, box_y + 8, COLOR_DARK_BLUE)
            pyxel.line(col_x, box_y + 16, col_x + 7, box_y + 16, COLOR_DARK_BLUE)

        # Flanking Animated Wall Torches
        for tx in [12, SCREEN_WIDTH - 16]:
            ty = box_y + 5
            pyxel.rect(tx - 1, ty + 6, 4, 3, COLOR_BROWN)
            pyxel.rect(tx - 1, ty + 2, 4, 4, COLOR_ORANGE)
            pyxel.pset(tx + (1 if fc % 4 < 2 else 0), ty, COLOR_YELLOW)
            pyxel.pset(tx + 1, ty + 1, COLOR_WHITE)
            if fc % 3 == 0:
                pyxel.pset(tx + (fc % 3) - 1, ty - 2, COLOR_YELLOW)

        # Blue Wall Banners with Golden Crosses
        for bx in [28, SCREEN_WIDTH - 40]:
            pyxel.rect(bx, box_y + 3, 12, 19, COLOR_NAVY)
            pyxel.tri(bx, box_y + 22, bx + 6, box_y + 26, bx + 11, box_y + 22, COLOR_NAVY)
            pyxel.rectb(bx, box_y + 3, 12, 19, COLOR_LIGHT_BLUE)
            # Golden cross emblem
            pyxel.line(bx + 5, box_y + 7, bx + 6, box_y + 7, COLOR_YELLOW)
            pyxel.line(bx + 4, box_y + 9, bx + 7, box_y + 9, COLOR_YELLOW)
            pyxel.line(bx + 5, box_y + 10, bx + 6, box_y + 15, COLOR_YELLOW)

        # Central Header Plaque: [❖ CHOOSE YOUR PROMOTION ❖]
        pw, ph = 160, 18
        px = (SCREEN_WIDTH - pw) // 2
        py = box_y + 3

        renderer.draw_box(px, py, pw, ph, bg_col=COLOR_BLACK, border_col=COLOR_YELLOW)
        pyxel.rectb(px + 1, py + 1, pw - 2, ph - 2, COLOR_ORANGE)

        # Corner ticks
        for cx, cy in [(px + 2, py + 2), (px + pw - 3, py + 2), (px + 2, py + ph - 3), (px + pw - 3, py + ph - 3)]:
            pyxel.pset(cx, cy, COLOR_WHITE)

        title = "❖ CHOOSE YOUR PROMOTION ❖" if i18n.locale == "en" else "❖ ELIGE TU PROMOCION ❖"
        renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(title) // 2, py + 6, title, COLOR_YELLOW)

        # Dual Promotion Cards
        recommended = self._recommended_class(game_state)
        promotions = game_state.player.available_promotions()[:2]
        for index, (class_id, card_x) in enumerate(zip(promotions, (8, 132))):
            self._draw_card(renderer, class_id, index, card_x, recommended)

        # Bottom Action Bar: [❖ Choose with [1] or [2] ❖]
        bw, bh = 176, 16
        bx_bot = (SCREEN_WIDTH - bw) // 2
        by_bot = 232

        renderer.draw_box(bx_bot, by_bot, bw, bh, bg_col=COLOR_BLACK, border_col=COLOR_YELLOW)
        pyxel.rectb(bx_bot + 1, by_bot + 1, bw - 2, bh - 2, COLOR_NAVY)

        # Diamond ticks on bottom bar
        for tx in [bx_bot + 10, bx_bot + bw - 12]:
            pyxel.pset(tx, by_bot + 8, COLOR_YELLOW)
            pyxel.pset(tx - 1, by_bot + 8, COLOR_PEACH)
            pyxel.pset(tx + 1, by_bot + 8, COLOR_PEACH)
            pyxel.pset(tx, by_bot + 7, COLOR_PEACH)
            pyxel.pset(tx, by_bot + 9, COLOR_PEACH)

        hint = "Choose with [1] or [2]" if i18n.locale == "en" else "Elige con [1] o [2]"
        renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(hint) // 2, by_bot + 5, hint, COLOR_WHITE)

        # Outer Room Border
        pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_DARK_BLUE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_NAVY)
