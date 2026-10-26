"""View switching architecture including CombatView, MapView, and InventoryView."""

from __future__ import annotations
from src.ui.views.base import View, CombatPopup, ENEMY_SPRITE_COORDS, SPEED_INTERVALS, SPEED_LABELS

import math
import random
from dataclasses import dataclass
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
    COLOR_PINK,
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from src.core.game_state import GameMode
from src.core.i18n import i18n, t
from src.entities import Enemy
from src.systems.abilities import Ability, AbilityRarity, AbilityType, get_random_abilities
from src.systems.combat import ACTION_THRESHOLD
from src.systems.inventory import MAX_BELT_SLOTS, MAX_POUCH_SLOTS, EquipSlot
from src.systems.map_gen import NodeType
from src.ui import renderer
from src.ui.renderer import Renderer

if TYPE_CHECKING:
    from src.core.game_state import GameState

# =============================================================================
# BIOME ENEMY SPRITE COORDINATE MAP (Bank 0)
# =============================================================================
class BiomeSelectView(View):
    """Renders the expedition route selection screen with panoramic biome vistas, threat icons, and gold frames."""

    def __init__(self) -> None:
        self.selected_index: int = 0

    def update(self, game_state: GameState) -> None:
        from src.config import SND_CLICK, SND_VICTORY
        from src.data.biomes import ACT_BIOMES
        if game_state.act not in ACT_BIOMES:
            return

        biome_a_id, biome_b_id = ACT_BIOMES[game_state.act]
        target_id = biome_a_id if self.selected_index == 0 else biome_b_id

        # Keyboard directional toggle
        if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
            self.selected_index = 0
            pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
            self.selected_index = 1
            pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_1) or pyxel.btnp(pyxel.KEY_KP_1):
            if self.selected_index == 0:
                pyxel.play(0, SND_VICTORY)
                game_state.advance_act(target_biome_id=biome_a_id)
            else:
                self.selected_index = 0
                pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_2) or pyxel.btnp(pyxel.KEY_KP_2):
            if self.selected_index == 1:
                pyxel.play(0, SND_VICTORY)
                game_state.advance_act(target_biome_id=biome_b_id)
            else:
                self.selected_index = 1
                pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            pyxel.play(0, SND_VICTORY)
            game_state.advance_act(target_biome_id=target_id)

        # Mouse / Tap click on cards
        card_w, card_h = 119, 184
        if Renderer.is_clicked(7, 50, card_w, card_h):
            if self.selected_index == 0:
                pyxel.play(0, SND_VICTORY)
                game_state.advance_act(target_biome_id=biome_a_id)
            else:
                self.selected_index = 0
                pyxel.play(0, SND_CLICK)
        elif Renderer.is_clicked(130, 50, card_w, card_h):
            if self.selected_index == 1:
                pyxel.play(0, SND_VICTORY)
                game_state.advance_act(target_biome_id=biome_b_id)
            else:
                self.selected_index = 1
                pyxel.play(0, SND_CLICK)

    def _draw_threat_icon(self, x: int, y: int, icon_type: str) -> None:
        """Render distinct 6x6 pixel glyphs for biome threats."""
        t_lower = icon_type.lower()
        if any(k in t_lower for k in ("creeper", "root", "hound", "bramble")):
            # Green sprout / vine
            pyxel.line(x + 2, y + 5, x + 2, y + 2, COLOR_GREEN)
            pyxel.pset(x + 1, y + 1, COLOR_LIME)
            pyxel.pset(x + 3, y, COLOR_LIME)
            pyxel.pset(x, y + 3, COLOR_GREEN)
            pyxel.pset(x + 4, y + 3, COLOR_GREEN)
        elif any(k in t_lower for k in ("spore", "pod", "mushroom")):
            # Purple & pink poison mushroom
            pyxel.rect(x + 1, y, 5, 3, COLOR_PURPLE)
            pyxel.pset(x + 2, y + 1, COLOR_PINK)
            pyxel.pset(x + 4, y + 1, COLOR_PINK)
            pyxel.rect(x + 2, y + 3, 3, 3, COLOR_WHITE)
        elif any(k in t_lower for k in ("imp", "cinder", "burn", "flame")):
            # Flame ember
            pyxel.pset(x + 2, y, COLOR_YELLOW)
            pyxel.rect(x + 1, y + 1, 3, 3, COLOR_ORANGE)
            pyxel.pset(x + 2, y + 2, COLOR_YELLOW)
            pyxel.rect(x + 1, y + 4, 3, 2, COLOR_RED)
        elif any(k in t_lower for k in ("grimoire", "tome", "book")):
            # Grimoire spellbook
            pyxel.rect(x, y + 1, 6, 5, COLOR_LIGHT_BLUE)
            pyxel.line(x + 2, y + 1, x + 2, y + 5, COLOR_NAVY)
            pyxel.pset(x + 1, y + 2, COLOR_WHITE)
            pyxel.pset(x + 4, y + 2, COLOR_WHITE)
        elif any(k in t_lower for k in ("ward", "arcane", "missile", "fiend", "candelabra")):
            # Arcane diamond spark
            pyxel.pset(x + 2, y, COLOR_CYAN)
            pyxel.line(x, y + 2, x + 4, y + 2, COLOR_CYAN)
            pyxel.pset(x + 2, y + 4, COLOR_CYAN)
            pyxel.pset(x + 2, y + 2, COLOR_WHITE)
        else:
            # Danger skull
            pyxel.rect(x + 1, y, 4, 3, COLOR_WHITE)
            pyxel.pset(x + 2, y + 1, COLOR_BLACK)
            pyxel.pset(x + 3, y + 1, COLOR_BLACK)
            pyxel.rect(x + 2, y + 3, 2, 2, COLOR_WHITE)

    def _draw_boss_icon(self, x: int, y: int, boss_name: str) -> None:
        """Render distinct 6x6 pixel glyphs for act bosses."""
        b_lower = boss_name.lower()
        if "archbishop" in b_lower:
            # High priest mitre hood
            pyxel.tri(x + 2, y, x, y + 5, x + 4, y + 5, COLOR_PINK)
            pyxel.line(x + 2, y + 1, x + 2, y + 4, COLOR_YELLOW)
            pyxel.pset(x + 1, y + 3, COLOR_YELLOW)
            pyxel.pset(x + 3, y + 3, COLOR_YELLOW)
        elif any(k in b_lower for k in ("choir", "chorus", "rite", "damned")):
            # Sunburst / Damned crest
            pyxel.circ(x + 2, y + 2, 2, COLOR_RED)
            pyxel.pset(x + 2, y + 2, COLOR_YELLOW)
            pyxel.pset(x + 2, y, COLOR_ORANGE)
            pyxel.pset(x + 2, y + 4, COLOR_ORANGE)
            pyxel.pset(x, y + 2, COLOR_ORANGE)
            pyxel.pset(x + 4, y + 2, COLOR_ORANGE)
        else:
            # Pink horned boss skull
            pyxel.rect(x + 1, y + 1, 4, 3, COLOR_PINK)
            pyxel.pset(x, y, COLOR_RED)
            pyxel.pset(x + 4, y, COLOR_RED)
            pyxel.pset(x + 2, y + 2, COLOR_BLACK)
            pyxel.pset(x + 3, y + 2, COLOR_BLACK)
            pyxel.rect(x + 2, y + 4, 2, 1, COLOR_PINK)

    def _draw_biome_vista(self, vx: int, vy: int, vw: int, vh: int, biome_id: str) -> None:
        """Render detailed procedural landscape vistas inside the card window."""
        fc = pyxel.frame_count

        if biome_id == "arboretum":
            pyxel.rect(vx, vy, vw, vh, COLOR_DARK_BLUE)
            # Three vaulted greenhouse windows
            for cx in [vx + 18, vx + 56, vx + 94]:
                pyxel.rect(cx - 13, vy + 4, 26, 22, COLOR_NAVY)
                pyxel.tri(cx - 13, vy + 4, cx, vy - 1, cx + 12, vy + 4, COLOR_NAVY)
                pyxel.rect(cx - 11, vy + 6, 22, 20, COLOR_LIGHT_BLUE)
                pyxel.tri(cx - 11, vy + 6, cx, vy + 1, cx + 10, vy + 6, COLOR_LIGHT_BLUE)
                pyxel.line(cx, vy + 1, cx, vy + 25, COLOR_NAVY)
                pyxel.line(cx - 11, vy + 14, cx + 10, vy + 14, COLOR_NAVY)
                pyxel.pset(cx - 5, vy + 9, COLOR_CYAN)
                pyxel.pset(cx + 5, vy + 9, COLOR_CYAN)

            # Central fountain basin
            pyxel.rect(vx + 48, vy + 22, 16, 9, COLOR_NAVY)
            pyxel.rect(vx + 52, vy + 18, 8, 4, COLOR_DARK_BLUE)
            pyxel.pset(vx + 55, vy + 16, COLOR_CYAN)
            pyxel.pset(vx + 56, vy + 16, COLOR_WHITE)

            # Cobblestone pathway
            for fy in range(vy + 25, vy + vh):
                pyxel.line(vx + 34, fy, vx + vw - 35, fy, COLOR_NAVY if fy % 2 == 0 else COLOR_BLACK)

            # Hanging vines with leaves
            for ix in range(vx + 4, vx + vw - 4, 8):
                ih = 3 + (ix % 4)
                pyxel.line(ix, vy, ix, vy + ih, COLOR_GREEN)
                pyxel.pset(ix, vy + ih, COLOR_LIME)

            # Purple mushroom clusters
            for mx, my in [(vx + 6, vy + 31), (vx + 14, vy + 33), (vx + vw - 16, vy + 31), (vx + vw - 8, vy + 33)]:
                pyxel.rect(mx, my, 4, 3, COLOR_PURPLE)
                pyxel.pset(mx + 1, my, COLOR_PINK)
                pyxel.pset(mx + 2, my, COLOR_WHITE)
                pyxel.rect(mx + 1, my + 3, 2, 2, COLOR_WHITE)

        elif biome_id == "cathedral":
            pyxel.rect(vx, vy, vw, vh, COLOR_BLACK)

            # Vaulted gothic arch
            pyxel.rect(vx + 40, vy + 3, 32, 34, COLOR_NAVY)
            pyxel.tri(vx + 40, vy + 3, vx + 56, vy - 2, vx + 71, vy + 3, COLOR_NAVY)

            # Stained glass rose window
            rw_x, rw_y = vx + 56, vy + 12
            pyxel.circ(rw_x, rw_y, 8, COLOR_RED)
            pyxel.circb(rw_x, rw_y, 8, COLOR_DARK_BLUE)
            pyxel.line(rw_x - 7, rw_y, rw_x + 7, rw_y, COLOR_DARK_BLUE)
            pyxel.line(rw_x, rw_y - 7, rw_x, rw_y + 7, COLOR_DARK_BLUE)
            pyxel.pset(rw_x, rw_y, COLOR_YELLOW)
            for px_val, py_val in [(rw_x - 3, rw_y - 3), (rw_x + 3, rw_y - 3), (rw_x - 3, rw_y + 3), (rw_x + 3, rw_y + 3)]:
                pyxel.pset(px_val, py_val, COLOR_PINK)

            # Flanking lancet stained glass windows
            for wx in [vx + 14, vx + vw - 22]:
                pyxel.rect(wx, vy + 6, 8, 22, COLOR_RED)
                pyxel.tri(wx, vy + 6, wx + 4, vy + 1, wx + 7, vy + 6, COLOR_RED)
                pyxel.line(wx + 3, vy + 1, wx + 3, vy + 27, COLOR_NAVY)

            # Iron cage lanterns
            for lx in [vx + 26, vx + vw - 32]:
                pyxel.line(lx + 2, vy, lx + 2, vy + 5, COLOR_GRAY)
                pyxel.rectb(lx, vy + 5, 5, 7, COLOR_BROWN)
                pyxel.pset(lx + 2, vy + 8, COLOR_YELLOW if fc % 4 < 2 else COLOR_ORANGE)

            # Altar candles
            for cx, cy in [(vx + 6, vy + 30), (vx + 10, vy + 28), (vx + vw - 14, vy + 28), (vx + vw - 10, vy + 30)]:
                pyxel.line(cx, cy, cx, cy + 5, COLOR_WHITE)
                pyxel.pset(cx, cy - 1, COLOR_YELLOW)

            # Altar skull
            pyxel.circ(vx + vw - 14, vy + 35, 2, COLOR_PEACH)
            pyxel.pset(vx + vw - 14, vy + 35, COLOR_BLACK)

        elif biome_id == "ossuary":
            pyxel.rect(vx, vy, vw, vh, COLOR_DARK_BLUE)
            for ay in range(vy + 3, vy + 20, 5):
                pyxel.line(vx + 4, ay, vx + vw - 5, ay, COLOR_NAVY)
            pyxel.rect(vx, vy + 22, vw, vh - 22, COLOR_BLACK)
            for wy in range(vy + 24, vy + vh, 3):
                pyxel.line(vx + 12, wy, vx + vw - 13, wy, COLOR_CYAN if wy % 2 == 0 else COLOR_DARK_BLUE)
            pyxel.circ(vx + 42, vy + 28, 3, COLOR_WHITE)
            pyxel.circ(vx + 78, vy + 30, 3, COLOR_WHITE)

        elif biome_id == "foundry":
            pyxel.rect(vx, vy, vw, vh, COLOR_BLACK)
            pyxel.rect(vx + 34, vy + 6, 44, 26, COLOR_RED)
            pyxel.tri(vx + 34, vy + 6, vx + 56, vy + 1, vx + 77, vy + 6, COLOR_RED)
            pyxel.rect(vx + 42, vy + 13, 28, 19, COLOR_ORANGE)
            pyxel.rect(vx + 48, vy + 18, 16, 14, COLOR_YELLOW)
            pyxel.line(vx + 56, vy + 13, vx + 56, vy + vh, COLOR_WHITE)

        elif biome_id == "observatory":
            pyxel.rect(vx, vy, vw, vh, COLOR_NAVY)
            for sx in range(vx + 6, vx + vw - 6, 14):
                sy = vy + 3 + (sx * 7) % 20
                pyxel.pset(sx, sy, COLOR_WHITE if (fc + sx) % 18 < 9 else COLOR_CYAN)
            pyxel.line(vx + 38, vy + 32, vx + 76, vy + 8, COLOR_BROWN)
            pyxel.line(vx + 39, vy + 32, vx + 77, vy + 8, COLOR_YELLOW)
            pyxel.circ(vx + 78, vy + 7, 3, COLOR_CYAN)

        else:  # sanctum
            pyxel.rect(vx, vy, vw, vh, COLOR_BLACK)
            pyxel.circ(vx + 56, vy + 12, 9, COLOR_RED)
            pyxel.circ(vx + 55, vy + 11, 8, COLOR_PINK)
            pyxel.rect(vx + 4, vy, 16, vh, COLOR_RED)
            pyxel.rect(vx + vw - 20, vy, 16, vh, COLOR_RED)
            pyxel.rectb(vx + 4, vy, 16, vh, COLOR_ORANGE)
            pyxel.rectb(vx + vw - 20, vy, 16, vh, COLOR_ORANGE)

        pyxel.rectb(vx, vy, vw, vh, COLOR_DARK_BLUE)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        box_x, box_y, box_w, box_h = 4, 25, SCREEN_WIDTH - 8, SCREEN_HEIGHT - 28
        fc = pyxel.frame_count
        pulse = (fc // 6) % 2

        # =====================================================================
        # 1. GOTHIC CHAMBER BACKDROP (y=25..49)
        # =====================================================================
        pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

        # Masonry stone wall columns in header section
        for px in [16, 44, SCREEN_WIDTH - 52, SCREEN_WIDTH - 24]:
            pyxel.rect(px, box_y + 1, 8, 20, COLOR_NAVY)
            pyxel.line(px, box_y + 6, px + 7, box_y + 6, COLOR_DARK_BLUE)
            pyxel.line(px, box_y + 14, px + 7, box_y + 14, COLOR_DARK_BLUE)

        # Banners (capped strictly above cards at y=43)
        for bx in [10, SCREEN_WIDTH - 22]:
            pyxel.rect(bx, box_y + 2, 12, 13, COLOR_RED)
            pyxel.tri(bx, box_y + 15, bx + 6, box_y + 18, bx + 11, box_y + 15, COLOR_RED)
            pyxel.rectb(bx, box_y + 2, 12, 13, COLOR_ORANGE)
            pyxel.pset(bx + 5, box_y + 7, COLOR_YELLOW)
            pyxel.pset(bx + 6, box_y + 7, COLOR_YELLOW)

        # Torches (capped strictly above cards at y=41)
        for tx in [30, SCREEN_WIDTH - 38]:
            ty = box_y + 4
            pyxel.rect(tx - 1, ty + 6, 4, 3, COLOR_BROWN)
            pyxel.rect(tx - 1, ty + 2, 4, 4, COLOR_ORANGE)
            pyxel.pset(tx + (1 if fc % 4 < 2 else 0), ty, COLOR_YELLOW)
            pyxel.pset(tx + 1, ty + 1, COLOR_WHITE)

        # =====================================================================
        # 2. HEADER BANNER PLAQUE (EXPEDITION ROUTE)
        # =====================================================================
        pw, ph = 156, 18
        px = (SCREEN_WIDTH - pw) // 2
        py = box_y + 3

        renderer.draw_box(px, py, pw, ph, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE)
        pyxel.rectb(px + 1, py + 1, pw - 2, ph - 2, COLOR_NAVY)

        act_str = f"✦ ACT {game_state.act} ✦" if i18n.locale == "en" else f"✦ ACTO {game_state.act} ✦"
        renderer.draw_text(SCREEN_WIDTH // 2 - len(act_str) * 2, py + 3, act_str, COLOR_LIGHT_BLUE)

        route_title = "❖ EXPEDITION ROUTE ❖" if i18n.locale == "en" else "❖ RUTA DE EXPEDICIÓN ❖"
        renderer.draw_text(SCREEN_WIDTH // 2 - len(route_title) * 2, py + 10, route_title, COLOR_YELLOW)

        # =====================================================================
        # 3. DUAL BIOME EXPEDITION CARDS (y=50..234)
        # =====================================================================
        from src.data.biomes import ACT_BIOMES, get_biome
        if game_state.act not in ACT_BIOMES:
            return

        biome_a_id, biome_b_id = ACT_BIOMES[game_state.act]
        biome_a = get_biome(biome_a_id)
        biome_b = get_biome(biome_b_id)

        card_w, card_h = 119, 184
        card_y = 50
        cards = [(biome_a, 7, 0), (biome_b, 130, 1)]

        for biome, card_x, idx in cards:
            if not biome:
                continue

            is_sel = (self.selected_index == idx)
            border_col = COLOR_YELLOW if is_sel else (COLOR_PINK if idx == 1 else COLOR_LIGHT_BLUE)
            fill_col = COLOR_DARK_BLUE if is_sel else COLOR_BLACK

            renderer.draw_box(card_x, card_y, card_w, card_h, bg_col=fill_col, border_col=border_col)

            if is_sel:
                pyxel.rectb(card_x + 1, card_y + 1, card_w - 2, card_h - 2, COLOR_YELLOW if pulse == 0 else COLOR_ORANGE)
                pyxel.pset(card_x + 2, card_y + 2, COLOR_WHITE)
                pyxel.pset(card_x + card_w - 3, card_y + 2, COLOR_WHITE)
                pyxel.pset(card_x + 2, card_y + card_h - 3, COLOR_WHITE)
                pyxel.pset(card_x + card_w - 3, card_y + card_h - 3, COLOR_WHITE)

            # 1. Scenic Landscape Vista Window (113x40)
            vw, vh = card_w - 6, 40
            vx, vy = card_x + 3, card_y + 3
            self._draw_biome_vista(vx, vy, vw, vh, biome.id)

            # 2. Biome Full Name (Single line, complete)
            renderer.draw_text(card_x + 5, card_y + 46, biome.localized_name, COLOR_YELLOW)

            # 3. Formatted Archetype Tags (Single line)
            tag_color = COLOR_CYAN if idx == 0 else COLOR_PINK
            tags_clean = biome.localized_tags.replace("Root Stalls", "Roots").replace("Missiles / Wards", "Wards")
            renderer.draw_text(card_x + 5, card_y + 55, tags_clean, tag_color)

            # 4. Biome Lore Description (4 lines, complete, 25 chars per line)
            desc_lines = renderer.wrap_text(biome.localized_description, max_chars_per_line=25)
            for li, line in enumerate(desc_lines[:4]):
                renderer.draw_text(card_x + 5, card_y + 64 + li * 7, line, COLOR_WHITE)

            # Divider 1
            pyxel.line(card_x + 4, card_y + 94, card_x + card_w - 5, card_y + 94, COLOR_NAVY)

            # 5. Threats List (Full names, complete)
            renderer.draw_text(card_x + 5, card_y + 97, t("biome_threats"), COLOR_ORANGE)
            from src.entities.enemy import ENEMY_CATALOG

            threat_names = []
            for e_id in biome.basic_enemies[:3]:
                if e_id in ENEMY_CATALOG:
                    threat_names.append(ENEMY_CATALOG[e_id].localized_name)
                else:
                    threat_names.append(e_id.replace('_', ' ').title())

            for ti, tname in enumerate(threat_names[:3]):
                ty = card_y + 105 + ti * 8
                self._draw_threat_icon(card_x + 5, ty, tname)
                renderer.draw_text(card_x + 13, ty, tname, COLOR_WHITE)

            # Divider 2
            pyxel.line(card_x + 4, card_y + 130, card_x + card_w - 5, card_y + 130, COLOR_NAVY)

            # 6. Bosses List (Full names, complete)
            renderer.draw_text(card_x + 5, card_y + 133, t("biome_bosses"), COLOR_PEACH)
            boss_names = []
            for b_id in biome.bosses[:2]:
                if b_id in ENEMY_CATALOG:
                    boss_names.append(ENEMY_CATALOG[b_id].localized_name)
                else:
                    boss_names.append(b_id.replace('_', ' ').title())

            for bi, bname in enumerate(boss_names[:2]):
                by_pos = card_y + 141 + bi * 8
                self._draw_boss_icon(card_x + 5, by_pos, bname)
                renderer.draw_text(card_x + 13, by_pos, bname, COLOR_WHITE)

            # 7. Choose Route Button
            btn_w = 100
            btn_h = 15
            btn_x = card_x + (card_w - btn_w) // 2
            btn_y = card_y + card_h - 19

            btn_label = "[ CHOOSE ROUTE ]" if i18n.locale == "en" else "[ ELEGIR RUTA ]"

            if is_sel:
                pyxel.tri(btn_x - 6, btn_y + 3, btn_x - 6, btn_y + 11, btn_x - 2, btn_y + 7, COLOR_YELLOW)
                pyxel.rect(btn_x, btn_y, btn_w, btn_h, COLOR_BLACK)
                pyxel.rectb(btn_x, btn_y, btn_w, btn_h, COLOR_YELLOW)
                renderer.draw_text(btn_x + (btn_w - len(btn_label) * 4) // 2, btn_y + 4, btn_label, COLOR_YELLOW)
            else:
                pyxel.rect(btn_x, btn_y, btn_w, btn_h, COLOR_BLACK)
                pyxel.rectb(btn_x, btn_y, btn_w, btn_h, COLOR_LIGHT_BLUE)
                renderer.draw_text(btn_x + (btn_w - len(btn_label) * 4) // 2, btn_y + 4, btn_label, COLOR_WHITE)

        # =====================================================================
        # 4. BOTTOM EXPEDITION FOOTER PROMPT (y=240)
        # =====================================================================
        prompt_txt = "Choose a route to continue your journey." if i18n.locale == "en" else "Elige una ruta para continuar tu viaje."
        tw = len(prompt_txt) * 4
        prompt_x = max(10, (SCREEN_WIDTH - tw) // 2)
        renderer.draw_text(prompt_x, 240, prompt_txt, COLOR_WHITE)

        # Outer Gothic Room Double Border
        pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_DARK_BLUE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_NAVY)

        # Decorative Corner Crosses
        for corner_x, corner_y in [
            (box_x + 1, box_y + 1),
            (box_x + box_w - 2, box_y + 1),
            (box_x + 1, box_y + box_h - 2),
            (box_x + box_w - 2, box_y + box_h - 2),
        ]:
            pyxel.pset(corner_x, corner_y, COLOR_LIGHT_BLUE)
            pyxel.pset(corner_x - 1, corner_y, COLOR_DARK_BLUE)
            pyxel.pset(corner_x + 1, corner_y, COLOR_DARK_BLUE)
            pyxel.pset(corner_x, corner_y - 1, COLOR_DARK_BLUE)
            pyxel.pset(corner_x, corner_y + 1, COLOR_DARK_BLUE)
