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
class EndGameView(View):
    """Renders atmospheric Game Over or Victory screens with gothic catacomb art, fallen heroes, and ornate frames."""

    def __init__(self, is_victory: bool) -> None:
        self.is_victory: bool = is_victory

    def update(self, game_state: GameState) -> None:
        # Restart on Enter, Space, or clicking the Restart button
        btn_w, btn_h = 104, 18
        btn_x = (SCREEN_WIDTH - btn_w) // 2
        btn_y = 196
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE) or Renderer.is_clicked(btn_x, btn_y, btn_w, btn_h):
            pyxel.play(0, 3)
            game_state.__init__()

    def _draw_bold_letter(self, x: int, y: int, char: str, col: int) -> int:
        """Render chunky 7x10 retro title characters for the death headline."""
        FONT = {
            'Y': ["#.....#", "#.....#", ".#...#.", "..#.#..", "...#...", "...#...", "...#...", "...#...", "...#..."],
            'O': [".#####.", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", ".#####."],
            'U': ["#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", ".#####."],
            'D': ["######.", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "######."],
            'I': ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
            'E': ["######", "#.....", "#.....", "#####.", "#.....", "#.....", "#.....", "#.....", "######"],
        }
        bitmap = FONT.get(char)
        if not bitmap:
            return 6

        w = len(bitmap[0])
        # Drop shadow
        for r, row in enumerate(bitmap):
            for c, bit in enumerate(row):
                if bit == '#':
                    pyxel.pset(x + c + 1, y + r + 1, COLOR_BLACK)
                    pyxel.pset(x + c, y + r, col)
        return w

    def _draw_death_scene(self, box_x: int, box_y: int, box_w: int, box_h: int) -> None:
        """Draw the catacomb chamber, fallen hero, braziers, and skeletal remains."""
        fc = pyxel.frame_count

        # Stone arch and background masonry
        for my in range(box_y + 16, box_y + 148, 8):
            pyxel.line(box_x + 8, my, box_x + box_w - 9, my, COLOR_NAVY)
            pyxel.pset(box_x + 24 + ((my * 3) % 40), my + 4, COLOR_DARK_BLUE)
            pyxel.pset(box_x + box_w - 44 - ((my * 5) % 40), my + 4, COLOR_DARK_BLUE)

        # Distant central arch
        arch_x = SCREEN_WIDTH // 2
        pyxel.rect(arch_x - 48, box_y + 14, 96, 120, COLOR_NAVY)
        pyxel.tri(arch_x - 48, box_y + 14, arch_x, box_y + 2, arch_x + 47, box_y + 14, COLOR_NAVY)
        pyxel.rect(arch_x - 44, box_y + 18, 88, 116, COLOR_BLACK)
        pyxel.tri(arch_x - 44, box_y + 18, arch_x, box_y + 6, arch_x + 43, box_y + 18, COLOR_BLACK)

        # Hanging crimson banners on left and right
        for bx in [box_x + 16, box_x + box_w - 32]:
            pyxel.rect(bx, box_y + 16, 16, 38, COLOR_RED)
            pyxel.tri(bx, box_y + 54, bx + 8, box_y + 64, bx + 15, box_y + 54, COLOR_RED)
            pyxel.rectb(bx, box_y + 16, 16, 38, COLOR_BLACK)
            pyxel.line(bx + 7, box_y + 24, bx + 7, box_y + 44, COLOR_BLACK)
            pyxel.line(bx + 8, box_y + 24, bx + 8, box_y + 44, COLOR_BLACK)
            pyxel.line(bx + 3, box_y + 30, bx + 12, box_y + 30, COLOR_BLACK)

        # Cobblestone ground
        ground_y = box_y + 144
        pyxel.rect(box_x + 4, ground_y, box_w - 8, box_h - 148, COLOR_DARK_BLUE)
        for gy in range(ground_y + 2, box_y + box_h - 6, 7):
            pyxel.line(box_x + 6, gy, box_x + box_w - 7, gy, COLOR_NAVY)
            for gx in range(box_x + 12 + ((gy // 7) % 2) * 10, box_x + box_w - 12, 18):
                pyxel.line(gx, gy, gx, gy + 6, COLOR_BLACK)

        # Flanking stone braziers on pedestals
        for tx in [box_x + 24, box_x + box_w - 32]:
            pyxel.rect(tx - 2, ground_y - 28, 9, 28, COLOR_NAVY)
            pyxel.rectb(tx - 3, ground_y - 32, 11, 5, COLOR_LIGHT_BLUE)
            pyxel.tri(tx - 2, ground_y - 32, tx + 2, ground_y - 44, tx + 6, ground_y - 32, COLOR_RED)
            pyxel.tri(tx - 1, ground_y - 32, tx + 2, ground_y - 40, tx + 5, ground_y - 32, COLOR_ORANGE)
            pyxel.pset(tx + 2, ground_y - 36, COLOR_YELLOW if fc % 4 < 2 else COLOR_WHITE)
            if fc % 3 == 0:
                pyxel.pset(tx + (fc % 3), ground_y - 46, COLOR_YELLOW)

        # Left: Fallen column & skull
        pyxel.rect(box_x + 42, ground_y - 20, 16, 22, COLOR_NAVY)
        pyxel.line(box_x + 45, ground_y - 20, box_x + 45, ground_y + 1, COLOR_DARK_BLUE)
        pyxel.line(box_x + 50, ground_y - 20, box_x + 50, ground_y + 1, COLOR_DARK_BLUE)
        pyxel.line(box_x + 54, ground_y - 20, box_x + 54, ground_y + 1, COLOR_DARK_BLUE)
        sk1_x, sk1_y = box_x + 38, ground_y + 2
        pyxel.circ(sk1_x, sk1_y, 6, COLOR_LIGHT_BLUE)
        pyxel.rect(sk1_x - 3, sk1_y + 3, 7, 4, COLOR_LIGHT_BLUE)
        pyxel.pset(sk1_x - 2, sk1_y, COLOR_BLACK)
        pyxel.pset(sk1_x + 2, sk1_y, COLOR_BLACK)
        pyxel.pset(sk1_x, sk1_y + 2, COLOR_BLACK)

        # Right: Embedded blade & skull with bone
        sw_x, sw_y = box_x + box_w - 52, ground_y - 18
        pyxel.line(sw_x, sw_y, sw_x + 5, sw_y + 24, COLOR_LIGHT_BLUE)
        pyxel.line(sw_x - 3, sw_y + 4, sw_x + 4, sw_y + 2, COLOR_WHITE)
        pyxel.rect(sw_x - 4, sw_y + 18, 12, 6, COLOR_NAVY)
        sk2_x, sk2_y = box_x + box_w - 38, ground_y + 2
        pyxel.circ(sk2_x, sk2_y, 6, COLOR_LIGHT_BLUE)
        pyxel.rect(sk2_x - 3, sk2_y + 3, 7, 4, COLOR_LIGHT_BLUE)
        pyxel.pset(sk2_x - 2, sk2_y, COLOR_BLACK)
        pyxel.pset(sk2_x + 2, sk2_y, COLOR_BLACK)
        pyxel.line(sk2_x - 10, sk2_y + 9, sk2_x - 2, sk2_y + 9, COLOR_LIGHT_BLUE)
        pyxel.pset(sk2_x - 11, sk2_y + 8, COLOR_LIGHT_BLUE)
        pyxel.pset(sk2_x - 11, sk2_y + 10, COLOR_LIGHT_BLUE)
        pyxel.pset(sk2_x - 1, sk2_y + 8, COLOR_LIGHT_BLUE)
        pyxel.pset(sk2_x - 1, sk2_y + 10, COLOR_LIGHT_BLUE)

        # Fallen Hero Body
        hx = SCREEN_WIDTH // 2 - 4
        hy = ground_y - 4

        # Blood pool
        pyxel.elli(hx - 24, hy + 4, 52, 9, COLOR_RED)
        pyxel.elli(hx - 16, hy + 6, 36, 6, COLOR_PURPLE)
        pyxel.pset(hx - 26, hy + 6, COLOR_RED)
        pyxel.pset(hx + 28, hy + 7, COLOR_RED)
        pyxel.pset(hx + 18, hy + 11, COLOR_RED)

        # Body
        pyxel.circ(hx + 4, hy - 1, 7, COLOR_NAVY)
        pyxel.circb(hx + 4, hy - 1, 7, COLOR_RED)
        pyxel.pset(hx + 2, hy + 2, COLOR_PEACH)
        pyxel.pset(hx + 3, hy + 2, COLOR_PEACH)
        pyxel.rect(hx - 12, hy - 2, 12, 8, COLOR_DARK_BLUE)
        pyxel.line(hx - 12, hy + 2, hx, hy + 2, COLOR_NAVY)
        pyxel.pset(hx - 16, hy + 3, COLOR_PEACH)
        pyxel.pset(hx - 15, hy + 4, COLOR_PEACH)
        pyxel.rect(hx - 20, hy + 1, 7, 4, COLOR_BROWN)

        # Dropped dagger
        pyxel.line(hx + 14, hy + 8, hx + 26, hy + 11, COLOR_WHITE)
        pyxel.line(hx + 14, hy + 9, hx + 25, hy + 12, COLOR_CYAN)
        pyxel.line(hx + 12, hy + 7, hx + 14, hy + 11, COLOR_YELLOW)
        pyxel.pset(hx + 10, hy + 7, COLOR_BROWN)

        # Blood motes
        motes = [
            (hx - 14, hy - 16), (hx + 2, hy - 24),
            (hx + 18, hy - 14), (hx - 4, hy - 32)
        ]
        for mi, (mx, my) in enumerate(motes):
            float_y = my - ((fc + mi * 7) % 24)
            if float_y > box_y + 30:
                pyxel.pset(mx, float_y, COLOR_RED if mi % 2 == 0 else COLOR_PINK)

    def _draw_death_header(self, box_x: int, box_y: int, box_w: int, renderer: Renderer) -> None:
        """Draw the grim skull crest, title banner, and epitaph text."""
        cx = SCREEN_WIDTH // 2

        # Grim Skull Emblem
        sk_y = box_y + 12
        pyxel.circ(cx, sk_y + 6, 7, COLOR_RED)
        pyxel.rect(cx - 4, sk_y + 9, 9, 5, COLOR_RED)
        pyxel.pset(cx - 3, sk_y + 6, COLOR_BLACK)
        pyxel.pset(cx + 3, sk_y + 6, COLOR_BLACK)
        pyxel.pset(cx, sk_y + 8, COLOR_BLACK)
        pyxel.line(cx - 2, sk_y + 12, cx - 2, sk_y + 13, COLOR_BLACK)
        pyxel.line(cx, sk_y + 12, cx, sk_y + 13, COLOR_BLACK)
        pyxel.line(cx + 2, sk_y + 12, cx + 2, sk_y + 13, COLOR_BLACK)

        # Banner bars
        pyxel.line(cx - 40, sk_y + 8, cx - 12, sk_y + 8, COLOR_RED)
        pyxel.line(cx - 40, sk_y + 11, cx - 12, sk_y + 11, COLOR_RED)
        pyxel.line(cx + 12, sk_y + 8, cx + 40, sk_y + 8, COLOR_RED)
        pyxel.line(cx + 12, sk_y + 11, cx + 40, sk_y + 11, COLOR_RED)
        pyxel.pset(cx - 42, sk_y + 9, COLOR_RED)
        pyxel.pset(cx + 42, sk_y + 9, COLOR_RED)

        # Chunky "YOU DIED" Title
        title_y = box_y + 32
        text_w = 78
        start_x = cx - text_w // 2

        curr_x = start_x
        for char in "YOU DIED":
            if char == ' ':
                curr_x += 6
            else:
                w = self._draw_bold_letter(curr_x, title_y, char, COLOR_RED)
                curr_x += w + 2

        # Diamond Separator Line
        div_y = title_y + 16
        pyxel.line(cx - 52, div_y, cx + 52, div_y, COLOR_RED)
        pyxel.pset(cx, div_y - 2, COLOR_RED)
        pyxel.line(cx - 2, div_y, cx + 2, div_y, COLOR_RED)
        pyxel.pset(cx, div_y + 2, COLOR_RED)
        pyxel.pset(cx, div_y, COLOR_WHITE)

        # Epitaph Text
        if i18n.locale == "es":
            line1 = "Tus huesos se unen a la"
            line2 = "mazmorra eterna..."
        else:
            line1 = "Your bones join the"
            line2 = "endless dungeon..."

        renderer.draw_text(cx - renderer.get_text_width(line1) // 2, div_y + 8, line1, COLOR_WHITE)
        renderer.draw_text(cx - renderer.get_text_width(line2) // 2, div_y + 18, line2, COLOR_WHITE)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        box_x, box_y, box_w, box_h = 10, 28, SCREEN_WIDTH - 20, 220
        fc = pyxel.frame_count

        if not self.is_victory:
            # =================================================================
            # GAME OVER / DEATH SCREEN
            # =================================================================
            pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

            # Scene Backdrop & Fallen Champion
            self._draw_death_scene(box_x, box_y, box_w, box_h)

            # Header, Skull, Big Title & Epitaph
            self._draw_death_header(box_x, box_y, box_w, renderer)

            # Outer Red Border with Corner Ornaments
            pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_RED)
            pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_RED)

            for cx, cy in [
                (box_x + 3, box_y + 3),
                (box_x + box_w - 4, box_y + 3),
                (box_x + 3, box_y + box_h - 4),
                (box_x + box_w - 4, box_y + box_h - 4),
            ]:
                pyxel.pset(cx, cy, COLOR_RED)
                pyxel.pset(cx - 1, cy, COLOR_RED)
                pyxel.pset(cx + 1, cy, COLOR_RED)
                pyxel.pset(cx, cy - 1, COLOR_RED)
                pyxel.pset(cx, cy + 1, COLOR_RED)

            # Restart Button with Corner Bracket Ticks
            btn_w, btn_h = 104, 18
            btn_x = (SCREEN_WIDTH - btn_w) // 2
            btn_y = 196

            pyxel.rect(btn_x, btn_y, btn_w, btn_h, COLOR_BLACK)
            pyxel.rectb(btn_x, btn_y, btn_w, btn_h, COLOR_RED)

            pyxel.line(btn_x - 2, btn_y - 2, btn_x + 3, btn_y - 2, COLOR_RED)
            pyxel.line(btn_x - 2, btn_y - 2, btn_x - 2, btn_y + 3, COLOR_RED)
            pyxel.line(btn_x + btn_w + 1, btn_y - 2, btn_x + btn_w - 4, btn_y - 2, COLOR_RED)
            pyxel.line(btn_x + btn_w + 1, btn_y - 2, btn_x + btn_w + 1, btn_y + 3, COLOR_RED)
            pyxel.line(btn_x - 2, btn_y + btn_h + 1, btn_x + 3, btn_y + btn_h + 1, COLOR_RED)
            pyxel.line(btn_x - 2, btn_y + btn_h + 1, btn_x - 2, btn_y + btn_h - 4, COLOR_RED)
            pyxel.line(btn_x + btn_w + 1, btn_y + btn_h + 1, btn_x + btn_w - 4, btn_y + btn_h + 1, COLOR_RED)
            pyxel.line(btn_x + btn_w + 1, btn_y + btn_h + 1, btn_x + btn_w + 1, btn_y + btn_h - 4, COLOR_RED)

            btn_label = "[ RESTART ]" if i18n.locale == "en" else "[ REINICIAR ]"
            renderer.draw_text(btn_x + (btn_w - renderer.get_text_width(btn_label)) // 2, btn_y + 6, btn_label, COLOR_WHITE)

        else:
            # =================================================================
            # TRIUMPHANT VICTORY SCREEN
            # =================================================================
            pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

            # Golden Spire Cathedral backdrop
            cx = SCREEN_WIDTH // 2
            for my in range(box_y + 16, box_y + 148, 8):
                pyxel.line(box_x + 8, my, box_x + box_w - 9, my, COLOR_NAVY)

            # Golden Crown of Aethelgard at top
            crown_y = box_y + 16
            pyxel.rect(cx - 10, crown_y + 4, 20, 8, COLOR_YELLOW)
            pyxel.tri(cx - 10, crown_y + 4, cx - 10, crown_y - 4, cx - 4, crown_y + 4, COLOR_YELLOW)
            pyxel.tri(cx - 4, crown_y + 4, cx, crown_y - 6, cx + 4, crown_y + 4, COLOR_YELLOW)
            pyxel.tri(cx + 4, crown_y + 4, cx + 10, crown_y - 4, cx + 10, crown_y + 4, COLOR_YELLOW)
            pyxel.pset(cx, crown_y - 2, COLOR_WHITE)
            pyxel.pset(cx - 5, crown_y + 8, COLOR_RED)
            pyxel.pset(cx + 5, crown_y + 8, COLOR_CYAN)

            # Radiating gold sunburst laurels
            if (fc // 6) % 2 == 0:
                pyxel.circb(cx, crown_y + 6, 24, COLOR_YELLOW)

            # Victory Title & Subtitle
            vic_title = t("victory_achieved")
            renderer.draw_text(cx - renderer.get_text_width(vic_title) // 2, box_y + 48, vic_title, COLOR_YELLOW)

            v_lines = renderer.wrap_text(t("victory_desc"), max_chars_per_line=34)
            for li, line in enumerate(v_lines):
                renderer.draw_text(cx - renderer.get_text_width(line) // 2, box_y + 68 + li * 12, line, COLOR_WHITE)

            # Hero standing victorious on pedestal
            sprite_coords = {"warrior": (0, 0), "rogue": (0, 32), "mage": (16, 32)}
            pu, pv = sprite_coords.get(game_state.player.class_id, (0, 0))
            pyxel.elli(cx - 12, box_y + 160, 24, 6, COLOR_NAVY)
            pyxel.blt(cx - 8, box_y + 144, 0, pu, pv, 16, 16, 0)
            pyxel.line(cx + 6, box_y + 150, cx + 14, box_y + 142, COLOR_CYAN)
            pyxel.line(cx + 7, box_y + 150, cx + 15, box_y + 142, COLOR_WHITE)

            # Double Gold Frame
            pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_YELLOW)
            pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_ORANGE)

            # Restart / Play Again Button
            btn_w, btn_h = 104, 18
            btn_x = (SCREEN_WIDTH - btn_w) // 2
            btn_y = 196
            renderer.draw_button(btn_x, btn_y, btn_w, btn_h, t("btn_restart"), bg_col=COLOR_BLACK, border_col=COLOR_YELLOW, text_col=COLOR_YELLOW)
