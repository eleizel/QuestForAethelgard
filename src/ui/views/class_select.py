"""View switching architecture including CombatView, MapView, and InventoryView."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyxel

from src.config import (
    COLOR_BLACK,
    COLOR_BROWN,
    COLOR_CYAN,
    COLOR_DARK_BLUE,
    COLOR_GRAY,
    COLOR_LIGHT_BLUE,
    COLOR_LIME,
    COLOR_NAVY,
    COLOR_ORANGE,
    COLOR_PEACH,
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    SCREEN_WIDTH,
)
from src.core.game_state import GameMode
from src.core.i18n import i18n, t
from src.data.abilities import get_random_abilities
from src.ui.renderer import Renderer
from src.ui.views.base import View

if TYPE_CHECKING:
    from src.core.game_state import GameState


# =============================================================================
# BIOME ENEMY SPRITE COORDINATE MAP (Bank 0)
# =============================================================================
class ClassSelectView(View):
    """Interactive class selection screen featuring panoramic backdrop, hero cards, and stat alcove."""

    def __init__(self) -> None:
        self.classes: list[str] = ["warrior", "rogue", "mage"]
        self.selected_index: int = 0
        self.route_mode: str = "FATE"

    def update(self, game_state: GameState) -> None:
        from src.config import SND_CLICK, SND_VICTORY

        # Toggle route mode
        if pyxel.btnp(pyxel.KEY_B) or pyxel.btnp(pyxel.KEY_T) or Renderer.is_clicked(70, 230, 96, 18):
            self.route_mode = "PATHFINDER" if self.route_mode == "FATE" else "FATE"
            pyxel.play(0, SND_CLICK)

        card_w, card_h = 78, 80
        x_offsets = [6, 89, 172]
        card_y = 28

        for i, card_x in enumerate(x_offsets):
            if Renderer.is_clicked(card_x, card_y, card_w, card_h):
                if self.selected_index == i:
                    pyxel.play(0, SND_VICTORY)
                    game_state.start_new_game(self.classes[self.selected_index], route_mode=self.route_mode)
                    return
                else:
                    self.selected_index = i
                    pyxel.play(0, SND_CLICK)

        if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
            self.selected_index = (self.selected_index - 1) % len(self.classes)
            pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
            self.selected_index = (self.selected_index + 1) % len(self.classes)
            pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_1):
            self.selected_index = 0
            pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_2):
            self.selected_index = 1
            pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_3):
            self.selected_index = 2
            pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE) or Renderer.is_clicked(172, 230, 78, 18):
            pyxel.play(0, SND_VICTORY)
            game_state.start_new_game(self.classes[self.selected_index], route_mode=self.route_mode)
        elif pyxel.btnp(pyxel.KEY_ESCAPE) or Renderer.is_clicked(6, 230, 58, 18):
            game_state.switch_mode(GameMode.WELCOME)

    def _draw_stat_icon(self, x: int, y: int, stat_type: str) -> None:
        """Draw small 5x5 stat glyphs matching the reference HUD."""
        if stat_type == "hp":
            # Green Heart
            pyxel.pset(x + 1, y, COLOR_LIME)
            pyxel.pset(x + 3, y, COLOR_LIME)
            pyxel.rect(x, y + 1, 5, 2, COLOR_LIME)
            pyxel.pset(x + 1, y + 3, COLOR_LIME)
            pyxel.pset(x + 2, y + 3, COLOR_LIME)
            pyxel.pset(x + 3, y + 3, COLOR_LIME)
            pyxel.pset(x + 2, y + 4, COLOR_LIME)
        elif stat_type == "atk":
            # Red Crossed Blades
            pyxel.line(x, y, x + 4, y + 4, COLOR_RED)
            pyxel.line(x + 4, y, x, y + 4, COLOR_RED)
            pyxel.pset(x + 2, y + 2, COLOR_WHITE)
        elif stat_type == "def":
            # Blue Shield
            pyxel.rect(x + 1, y, 3, 3, COLOR_CYAN)
            pyxel.pset(x, y + 1, COLOR_CYAN)
            pyxel.pset(x + 4, y + 1, COLOR_CYAN)
            pyxel.pset(x + 2, y + 4, COLOR_CYAN)
            pyxel.line(x + 1, y + 3, x + 3, y + 3, COLOR_CYAN)
        elif stat_type == "spd":
            # Yellow Speed Boot
            pyxel.rect(x + 1, y, 2, 4, COLOR_YELLOW)
            pyxel.rect(x + 1, y + 3, 4, 2, COLOR_YELLOW)
            pyxel.pset(x + 4, y + 4, COLOR_WHITE)
        elif stat_type == "crit":
            # Orange Star
            pyxel.pset(x + 2, y, COLOR_ORANGE)
            pyxel.line(x, y + 2, x + 4, y + 2, COLOR_ORANGE)
            pyxel.pset(x + 2, y + 4, COLOR_ORANGE)
            pyxel.pset(x + 2, y + 2, COLOR_YELLOW)

    def _draw_skill_glyph(self, x: int, y: int, skill_id: str) -> None:
        """Render distinct skill art inside the skill thumbnail box."""
        fc = pyxel.frame_count
        if "cross_cut" in skill_id:
            # Dual cyan sword slashes
            pyxel.line(x + 2, y + 2, x + 9, y + 9, COLOR_CYAN)
            pyxel.line(x + 3, y + 2, x + 10, y + 9, COLOR_WHITE)
            pyxel.line(x + 8, y + 2, x + 1, y + 9, COLOR_CYAN)
            pyxel.line(x + 9, y + 2, x + 2, y + 9, COLOR_WHITE)
        elif "shadow" in skill_id:
            # Shadow crescent with twin blade glints
            pyxel.circ(x + 6, y + 6, 4, COLOR_PURPLE)
            pyxel.circ(x + 8, y + 5, 3, COLOR_NAVY)
            pyxel.line(x + 2, y + 8, x + 9, y + 2, COLOR_WHITE)
        elif "arcane" in skill_id:
            # Pulsing arcane energy orb
            pyxel.circ(x + 6, y + 6, 3, COLOR_CYAN)
            pyxel.pset(x + 6, y + 6, COLOR_WHITE)
            if (fc // 6) % 2 == 0:
                pyxel.pset(x + 2, y + 2, COLOR_LIGHT_BLUE)
                pyxel.pset(x + 9, y + 9, COLOR_LIGHT_BLUE)
        else:
            # Default star burst
            pyxel.circ(x + 6, y + 6, 3, COLOR_YELLOW)
            pyxel.pset(x + 6, y + 6, COLOR_WHITE)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        fc = pyxel.frame_count

        # =====================================================================
        # 1. TOP PANORAMIC BACKDROP & TITLE
        # =====================================================================
        # Sky & Mountain Silhouette
        pyxel.rect(0, 0, SCREEN_WIDTH, 26, COLOR_NAVY)
        for my in range(14, 26):
            step = (my - 14) / 12.0
            for mx in range(SCREEN_WIDTH):
                if (mx + my) % 2 == 0 or (mx * 3 + my * 5) % 7 > int(step * 7):
                    pyxel.pset(mx, my, COLOR_DARK_BLUE)

        # Distant Spire Towers & Citadel Peaks
        pyxel.tri(188, 14, 194, 2, 200, 14, COLOR_BLACK)
        pyxel.tri(204, 14, 212, 0, 220, 14, COLOR_BLACK)
        pyxel.tri(222, 14, 230, 4, 238, 14, COLOR_BLACK)

        # Pale Moon at top right
        pyxel.circ(180, 8, 5, COLOR_PEACH)
        pyxel.circ(179, 7, 4, COLOR_WHITE)
        pyxel.pset(181, 6, COLOR_PEACH)

        # Ambient Pine Tree Silhouettes
        for tx in range(24, SCREEN_WIDTH - 24, 14):
            th = 6 + (tx % 5)
            pyxel.tri(tx, 18, tx + 4, 18 - th, tx + 8, 18, COLOR_BLACK)

        # Hanging Crimson Banners on Far Left & Right
        for bx in [8, SCREEN_WIDTH - 18]:
            pyxel.rect(bx, 0, 10, 22, COLOR_RED)
            pyxel.tri(bx, 22, bx + 5, 26, bx + 9, 22, COLOR_RED)
            pyxel.rectb(bx, 0, 10, 22, COLOR_ORANGE)
            pyxel.pset(bx + 4, 8, COLOR_YELLOW)
            pyxel.pset(bx + 5, 8, COLOR_YELLOW)
            pyxel.pset(bx + 4, 9, COLOR_YELLOW)
            pyxel.pset(bx + 5, 9, COLOR_YELLOW)

        # Flanking Wall Sconces with Animated Fire
        for tx, ty in [(3, 14), (SCREEN_WIDTH - 7, 14)]:
            pyxel.rect(tx, ty + 4, 4, 3, COLOR_BROWN)
            pyxel.rect(tx, ty, 4, 4, COLOR_ORANGE)
            pyxel.pset(tx + (1 if fc % 4 < 2 else 2), ty, COLOR_YELLOW)
            pyxel.pset(tx + 1, ty + 1, COLOR_WHITE)

        # Central Golden Title Frame
        title_text = t("choose_hero")
        tt_w = renderer.get_text_width(title_text)
        tb_w = tt_w + 24
        tb_x = SCREEN_WIDTH // 2 - tb_w // 2
        renderer.draw_box(tb_x, 3, tb_w, 18, bg_col=COLOR_BLACK, border_col=COLOR_YELLOW)
        pyxel.rectb(tb_x + 1, 4, tb_w - 2, 16, COLOR_ORANGE)
        renderer.draw_text(SCREEN_WIDTH // 2 - tt_w // 2, 8, title_text, COLOR_YELLOW)

        # =====================================================================
        # 2. THREE HERO SELECTION CARDS (y=28 to y=108)
        # =====================================================================
        card_w, card_h = 78, 80
        x_offsets = [6, 89, 172]
        card_y = 28

        from src.data.classes import CLASS_REGISTRY

        # Class weapon badge icons in Bank 0
        weapon_badges = {
            "warrior": (72, 0),  # Sword
            "rogue": (32, 16),  # Dagger
            "mage": (56, 16),  # Staff with orb
        }
        sprite_coords = {
            "warrior": (0, 0),
            "rogue": (0, 32),
            "mage": (16, 32),
        }

        pulse = (fc // 6) % 2

        for i, cls_id in enumerate(self.classes):
            card_x = x_offsets[i]
            is_selected = (i == self.selected_index)
            border_col = COLOR_YELLOW if is_selected else COLOR_LIGHT_BLUE
            fill_col = COLOR_DARK_BLUE if is_selected else COLOR_BLACK

            renderer.draw_box(card_x, card_y, card_w, card_h, bg_col=fill_col, border_col=border_col)

            # Selected Gold Studs & Double Border
            if is_selected:
                pyxel.rectb(card_x + 1, card_y + 1, card_w - 2, card_h - 2,
                            COLOR_YELLOW if pulse == 0 else COLOR_ORANGE)
                # Corner accents
                pyxel.pset(card_x + 2, card_y + 2, COLOR_WHITE)
                pyxel.pset(card_x + card_w - 3, card_y + 2, COLOR_WHITE)
                pyxel.pset(card_x + 2, card_y + card_h - 3, COLOR_WHITE)
                pyxel.pset(card_x + card_w - 3, card_y + card_h - 3, COLOR_WHITE)

            # Top-Left Icon Badge Box (14x14)
            badge_x, badge_y = card_x + 4, card_y + 4
            pyxel.rect(badge_x, badge_y, 14, 14, COLOR_NAVY)
            pyxel.rectb(badge_x, badge_y, 14, 14, COLOR_LIGHT_BLUE if not is_selected else COLOR_YELLOW)
            wu, wv = weapon_badges.get(cls_id, (72, 0))
            pyxel.blt(badge_x + 3, badge_y + 3, 0, wu, wv, 8, 8, 0)

            # Class Name & Archetype
            cls_def = CLASS_REGISTRY[cls_id]
            renderer.draw_text(card_x + 22, card_y + 5, cls_def.localized_name,
                               COLOR_YELLOW if is_selected else COLOR_WHITE)
            archetype = t(f"arch_{cls_id}")
            renderer.draw_text(card_x + 22, card_y + 13, archetype, COLOR_GRAY)

            # Stone Floor & Champion Cast Shadow
            floor_y = card_y + card_h - 14
            pyxel.line(card_x + 6, floor_y + 6, card_x + card_w - 7, floor_y + 6, COLOR_NAVY)
            pyxel.elli(card_x + card_w // 2 - 12, floor_y + 2, 24, 6, COLOR_NAVY)

            # Hero Sprite
            pu, pv = sprite_coords.get(cls_id, (0, 0))
            sprite_x = card_x + (card_w - 16) // 2
            sprite_y = card_y + 40
            pyxel.blt(sprite_x, sprite_y, 0, pu, pv, 16, 16, 0)

            # Drawn weapons/effects
            if cls_id == "warrior":
                pyxel.line(sprite_x + 14, sprite_y + 6, sprite_x + 21, sprite_y - 1, COLOR_CYAN)
                pyxel.line(sprite_x + 15, sprite_y + 6, sprite_x + 22, sprite_y - 1, COLOR_WHITE)
            elif cls_id == "rogue":
                pyxel.line(sprite_x - 3, sprite_y + 11, sprite_x + 1, sprite_y + 7, COLOR_WHITE)
                pyxel.line(sprite_x + 15, sprite_y + 7, sprite_x + 19, sprite_y + 11, COLOR_WHITE)
            elif cls_id == "mage":
                pyxel.line(sprite_x + 13, sprite_y + 14, sprite_x + 19, sprite_y + 2, COLOR_BROWN)
                pyxel.circ(sprite_x + 19, sprite_y + 2, 2, COLOR_CYAN)
                pyxel.pset(sprite_x + 19, sprite_y + 2, COLOR_WHITE)
                if (fc // 6) % 2 == 0:
                    pyxel.pset(sprite_x + 23, sprite_y + 5, COLOR_CYAN)
                    pyxel.pset(sprite_x - 4, sprite_y + 10, COLOR_CYAN)

        # =====================================================================
        # 3. DUAL-CHAMBER DETAIL PANEL (y=112 to y=222)
        # =====================================================================
        panel_x, panel_y, panel_w, panel_h = 6, 112, SCREEN_WIDTH - 12, 110
        renderer.draw_box(panel_x, panel_y, panel_w, panel_h, bg_col=COLOR_DARK_BLUE, border_col=COLOR_LIGHT_BLUE)
        pyxel.rectb(panel_x + 1, panel_y + 1, panel_w - 2, panel_h - 2, COLOR_NAVY)

        sel_cls_id = self.classes[self.selected_index]
        sel_cls_def = CLASS_REGISTRY[sel_cls_id]

        # --- LEFT ALCOVE: Stone Chamber with Hero Standing ---
        # =====================================================================
        # 3. DUAL-CHAMBER DETAIL PANEL (y=112 to y=222)
        # =====================================================================
        panel_x, panel_y, panel_w, panel_h = 6, 112, SCREEN_WIDTH - 12, 110
        renderer.draw_box(panel_x, panel_y, panel_w, panel_h, bg_col=COLOR_DARK_BLUE, border_col=COLOR_LIGHT_BLUE)
        pyxel.rectb(panel_x + 1, panel_y + 1, panel_w - 2, panel_h - 2, COLOR_NAVY)

        sel_cls_id = self.classes[self.selected_index]
        sel_cls_def = CLASS_REGISTRY[sel_cls_id]

        # --- LEFT ALCOVE: Detailed Character Portrait & Hero Plaque ---
        alcove_w = 58
        pyxel.rect(panel_x + 2, panel_y + 2, alcove_w, panel_h - 4, COLOR_NAVY)

        # Ornate Portrait Framing (52x68 frame for 48x64 sprite)
        port_w, port_h = 48, 64
        port_x = panel_x + 2 + (alcove_w - port_w) // 2  # x = 13 (centered)
        port_y = panel_y + 6  # y = 118

        frame_x = port_x - 2  # x = 11
        frame_y = port_y - 2  # y = 116
        frame_w = port_w + 4  # w = 52
        frame_h = port_h + 4  # h = 68

        pyxel.rect(frame_x, frame_y, frame_w, frame_h, COLOR_BLACK)
        pyxel.rectb(frame_x, frame_y, frame_w, frame_h, COLOR_LIGHT_BLUE)
        pyxel.rectb(frame_x + 1, frame_y + 1, frame_w - 2, frame_h - 2, COLOR_YELLOW if pulse == 0 else COLOR_ORANGE)

        # Corner Studs on Portrait Frame
        pyxel.pset(frame_x + 1, frame_y + 1, COLOR_WHITE)
        pyxel.pset(frame_x + frame_w - 2, frame_y + 1, COLOR_WHITE)
        pyxel.pset(frame_x + 1, frame_y + frame_h - 2, COLOR_WHITE)
        pyxel.pset(frame_x + frame_w - 2, frame_y + frame_h - 2, COLOR_WHITE)

        # Blit 48x64 Portrait from Bank 0
        from src.tools.generate_assets import get_class_portrait
        port_u, port_v = get_class_portrait(sel_cls_id)
        pyxel.blt(port_x, port_y, 0, port_u, port_v, port_w, port_h, 0)

        # Hero Plaque below Portrait (y = 188..216)
        plaque_x = frame_x
        plaque_y = frame_y + frame_h + 4
        plaque_w = frame_w
        plaque_h = (panel_y + panel_h - 4) - plaque_y

        renderer.draw_box(plaque_x, plaque_y, plaque_w, plaque_h, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE)
        pyxel.rectb(plaque_x + 1, plaque_y + 1, plaque_w - 2, plaque_h - 2, COLOR_NAVY)

        # Centered Name and Role Tag
        p_name = sel_cls_def.localized_name
        p_arch = t(f"arch_{sel_cls_id}")
        tw_name = renderer.get_text_width(p_name)
        tw_arch = renderer.get_text_width(p_arch)

        renderer.draw_text(plaque_x + max(2, (plaque_w - tw_name) // 2), plaque_y + 4, p_name, COLOR_YELLOW)
        renderer.draw_text(plaque_x + max(2, (plaque_w - tw_arch) // 2), plaque_y + 13, p_arch, COLOR_GRAY)

        # Vertical Divider Line between Left Alcove and Right Stats
        div_x = panel_x + alcove_w + 3
        pyxel.line(div_x, panel_y + 4, div_x, panel_y + panel_h - 5, COLOR_LIGHT_BLUE)

        # --- RIGHT DETAILS: Name, Description, Stats & Skills ---
        content_x = div_x + 6

        # Class Name & Description
        renderer.draw_text(content_x, panel_y + 6, sel_cls_def.localized_name, COLOR_YELLOW)
        for i, line in enumerate(renderer.wrap_text(sel_cls_def.localized_description, max_chars_per_line=36)):
            renderer.draw_text(content_x, panel_y + 16 + (i * 9), line, COLOR_WHITE)

        # --- ATTRIBUTES (Left sub-column) ---
        stat_x = content_x
        stats = sel_cls_def.base_stats
        growth = sel_cls_def.growth_per_level

        # HP
        self._draw_stat_icon(stat_x, panel_y + 36, "hp")
        renderer.draw_text(stat_x + 8, panel_y + 36, f"HP:  {stats.max_hp} (+{growth.max_hp}/lvl)", COLOR_WHITE)

        # ATK
        self._draw_stat_icon(stat_x, panel_y + 46, "atk")
        renderer.draw_text(stat_x + 8, panel_y + 46, f"ATK: {stats.attack} (+{growth.attack})", COLOR_WHITE)

        # DEF
        self._draw_stat_icon(stat_x, panel_y + 56, "def")
        renderer.draw_text(stat_x + 8, panel_y + 56, f"DEF: {stats.defense} (+{growth.defense})", COLOR_WHITE)

        # SPD
        self._draw_stat_icon(stat_x, panel_y + 66, "spd")
        renderer.draw_text(stat_x + 8, panel_y + 66, f"SPD: {stats.speed} (+{growth.speed})", COLOR_WHITE)

        # CRIT
        self._draw_stat_icon(stat_x, panel_y + 76, "crit")
        crit_pct = int(stats.crit_chance * 100)
        renderer.draw_text(stat_x + 8, panel_y + 76, f"CRIT: {crit_pct}%", COLOR_WHITE)

        # Vertical Sub-divider
        sub_div_x = stat_x + 94
        pyxel.line(sub_div_x, panel_y + 34, sub_div_x, panel_y + 86, COLOR_NAVY)

        # --- STARTING SKILL (Right sub-column) ---
        skill_x = sub_div_x + 6
        from src.data.abilities import get_ability_by_id
        starting_skill_id = sel_cls_def.starting_abilities[0] if sel_cls_def.starting_abilities else "None"
        skill = get_ability_by_id(starting_skill_id)

        if skill:
            renderer.draw_text(skill_x, panel_y + 36, f"Skill: {skill.localized_name}", COLOR_CYAN)

            # Skill Thumbnail Frame (14x14)
            sbox_x, sbox_y = skill_x, panel_y + 47
            pyxel.rect(sbox_x, sbox_y, 14, 14, COLOR_NAVY)
            pyxel.rectb(sbox_x, sbox_y, 14, 14, COLOR_LIGHT_BLUE)
            self._draw_skill_glyph(sbox_x + 1, sbox_y + 1, skill.id)

            # Skill Description
            s_lines = renderer.wrap_text(skill.localized_description, max_chars_per_line=13)
            for si, sline in enumerate(s_lines[:3]):
                renderer.draw_text(sbox_x + 18, sbox_y + (si * 9), sline, COLOR_WHITE)

        # Best For / Promotions Footer Line
        promos_str = ", ".join(t(f"class_{p}_name") for p in sel_cls_def.promotions)
        promo_label = f"Promociones: {promos_str}" if i18n.locale == "es" else f"Best for: {promos_str}"
        renderer.draw_text(content_x, panel_y + panel_h - 13, promo_label, COLOR_PEACH)

        # =====================================================================
        # 4. BOTTOM ACTION CONTROL BAR (y=228 to y=248)
        # =====================================================================
        # Back Button with Left Arrow
        renderer.draw_button(6, 228, 58, 18, "◄ [ BACK ]" if i18n.locale == "en" else "◄ [ VOLVER ]",
                             bg_col=COLOR_BLACK, border_col=COLOR_GRAY, text_col=COLOR_WHITE)

        # Central Route Selection Toggle
        mode_label = t("route_fate") if self.route_mode == "FATE" else t("route_pathfinder")
        renderer.draw_button(70, 228, 96, 18, mode_label, bg_col=COLOR_BLACK, border_col=COLOR_DARK_BLUE,
                             text_col=COLOR_YELLOW if self.route_mode == "PATHFINDER" else COLOR_WHITE)

        # Begin Journey Button with Golden Border and Play Triangle
        b_label = "► [ BEGIN ]" if i18n.locale == "en" else "► [ INICIAR ]"
        renderer.draw_button(172, 228, 78, 18, b_label, bg_col=COLOR_BLACK, border_col=COLOR_YELLOW,
                             text_col=COLOR_YELLOW)
