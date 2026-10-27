"""View switching architecture including CombatView, MapView, and InventoryView."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pyxel

from src.config import (
    COLOR_BLACK,
    COLOR_BROWN,
    COLOR_CYAN,
    COLOR_DARK_BLUE,
    COLOR_LIGHT_BLUE,
    COLOR_NAVY,
    COLOR_ORANGE,
    COLOR_PEACH,
    COLOR_PINK,
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    SCREEN_WIDTH,
)
from src.core.i18n import i18n
from src.ui.renderer import Renderer
from src.ui.views.base import View

if TYPE_CHECKING:
    from src.core.game_state import GameState


class EndGameView(View):
    """Renders atmospheric Game Over or Victory screens with gothic catacomb art, fallen heroes, and ornate frames."""

    def __init__(self, is_victory: bool) -> None:
        self.is_victory: bool = is_victory

    def update(self, game_state: GameState) -> None:
        btn_w, btn_h = 104, 18
        btn_x = (SCREEN_WIDTH - btn_w) // 2
        btn_y = 206 if self.is_victory else 196
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE) or Renderer.is_clicked(btn_x, btn_y, btn_w,
                                                                                              btn_h):
            pyxel.play(0, 3)
            game_state.__init__()

    def _draw_bold_letter(self, x: int, y: int, char: str, col: int) -> int:
        """Render chunky 6x9 retro title characters for headlines with drop-shadow."""
        FONT: dict[str, list[str]] = {
            'Y': ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#..", "..#.."],
            'O': [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
            'U': ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
            'D': ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
            'I': ["###", ".#.", ".#.", ".#.", ".#.", ".#.", ".#.", "###"],
            'E': ["####", "#...", "#...", "###.", "#...", "#...", "#...", "####"],
            'V': ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", ".#.#.", "..#.."],
            'C': [".####", "#....", "#....", "#....", "#....", "#....", "#....", ".####"],
            'T': ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
            'R': ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#", "#...#"],
            'A': [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#", "#...#"],
            'H': ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#", "#...#"],
            'B': ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "#...#", "####."],
            'N': ["#...#", "##..#", "#.#.#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
            '!': ["#", "#", "#", "#", "#", "#", ".", "#"],
            '¡': ["#", ".", "#", "#", "#", "#", "#", "#"],
        }
        bitmap = FONT.get(char)
        if not bitmap:
            return 5

        w = len(bitmap[0])
        for r, row in enumerate(bitmap):
            for c, bit in enumerate(row):
                if bit == '#':
                    pyxel.pset(x + c + 1, y + r + 1, COLOR_BLACK)
                    pyxel.pset(x + c, y + r, col)
        return w

    def _draw_death_scene(self, box_x: int, box_y: int, box_w: int, box_h: int) -> None:
        """Draw the catacomb chamber, fallen hero, braziers, and skeletal remains."""
        fc = pyxel.frame_count

        for my in range(box_y + 16, box_y + 148, 8):
            pyxel.line(box_x + 8, my, box_x + box_w - 9, my, COLOR_NAVY)
            pyxel.pset(box_x + 24 + ((my * 3) % 40), my + 4, COLOR_DARK_BLUE)
            pyxel.pset(box_x + box_w - 44 - ((my * 5) % 40), my + 4, COLOR_DARK_BLUE)

        arch_x = SCREEN_WIDTH // 2
        pyxel.rect(arch_x - 48, box_y + 14, 96, 120, COLOR_NAVY)
        pyxel.tri(arch_x - 48, box_y + 14, arch_x, box_y + 2, arch_x + 47, box_y + 14, COLOR_NAVY)
        pyxel.rect(arch_x - 44, box_y + 18, 88, 116, COLOR_BLACK)
        pyxel.tri(arch_x - 44, box_y + 18, arch_x, box_y + 6, arch_x + 43, box_y + 18, COLOR_BLACK)

        for bx in [box_x + 16, box_x + box_w - 32]:
            pyxel.rect(bx, box_y + 16, 16, 38, COLOR_RED)
            pyxel.tri(bx, box_y + 54, bx + 8, box_y + 64, bx + 15, box_y + 54, COLOR_RED)
            pyxel.rectb(bx, box_y + 16, 16, 38, COLOR_BLACK)
            pyxel.line(bx + 7, box_y + 24, bx + 7, box_y + 44, COLOR_BLACK)
            pyxel.line(bx + 8, box_y + 24, bx + 8, box_y + 44, COLOR_BLACK)
            pyxel.line(bx + 3, box_y + 30, bx + 12, box_y + 30, COLOR_BLACK)

        ground_y = box_y + 144
        pyxel.rect(box_x + 4, ground_y, box_w - 8, box_h - 148, COLOR_DARK_BLUE)
        for gy in range(ground_y + 2, box_y + box_h - 6, 7):
            pyxel.line(box_x + 6, gy, box_x + box_w - 7, gy, COLOR_NAVY)
            for gx in range(box_x + 12 + ((gy // 7) % 2) * 10, box_x + box_w - 12, 18):
                pyxel.line(gx, gy, gx, gy + 6, COLOR_BLACK)

        for tx in [box_x + 24, box_x + box_w - 32]:
            pyxel.rect(tx - 2, ground_y - 28, 9, 28, COLOR_NAVY)
            pyxel.rectb(tx - 3, ground_y - 32, 11, 5, COLOR_LIGHT_BLUE)
            pyxel.tri(tx - 2, ground_y - 32, tx + 2, ground_y - 44, tx + 6, ground_y - 32, COLOR_RED)
            pyxel.tri(tx - 1, ground_y - 32, tx + 2, ground_y - 40, tx + 5, ground_y - 32, COLOR_ORANGE)
            pyxel.pset(tx + 2, ground_y - 36, COLOR_YELLOW if fc % 4 < 2 else COLOR_WHITE)
            if fc % 3 == 0:
                pyxel.pset(tx + (fc % 3), ground_y - 46, COLOR_YELLOW)

        # Left column & skull
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

        # Right blade & skull
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

        pyxel.elli(hx - 24, hy + 4, 52, 9, COLOR_RED)
        pyxel.elli(hx - 16, hy + 6, 36, 6, COLOR_PURPLE)
        pyxel.pset(hx - 26, hy + 6, COLOR_RED)
        pyxel.pset(hx + 28, hy + 7, COLOR_RED)
        pyxel.pset(hx + 18, hy + 11, COLOR_RED)

        pyxel.circ(hx + 4, hy - 1, 7, COLOR_NAVY)
        pyxel.circb(hx + 4, hy - 1, 7, COLOR_RED)
        pyxel.pset(hx + 2, hy + 2, COLOR_PEACH)
        pyxel.pset(hx + 3, hy + 2, COLOR_PEACH)
        pyxel.rect(hx - 12, hy - 2, 12, 8, COLOR_DARK_BLUE)
        pyxel.line(hx - 12, hy + 2, hx, hy + 2, COLOR_NAVY)
        pyxel.pset(hx - 16, hy + 3, COLOR_PEACH)
        pyxel.pset(hx - 15, hy + 4, COLOR_PEACH)
        pyxel.rect(hx - 20, hy + 1, 7, 4, COLOR_BROWN)

        pyxel.line(hx + 14, hy + 8, hx + 26, hy + 11, COLOR_WHITE)
        pyxel.line(hx + 14, hy + 9, hx + 25, hy + 12, COLOR_CYAN)
        pyxel.line(hx + 12, hy + 7, hx + 14, hy + 11, COLOR_YELLOW)
        pyxel.pset(hx + 10, hy + 7, COLOR_BROWN)

        motes = [(hx - 14, hy - 16), (hx + 2, hy - 24), (hx + 18, hy - 14), (hx - 4, hy - 32)]
        for mi, (mx, my) in enumerate(motes):
            float_y = my - ((fc + mi * 7) % 24)
            if float_y > box_y + 30:
                pyxel.pset(mx, float_y, COLOR_RED if mi % 2 == 0 else COLOR_PINK)

    def _draw_death_header(self, box_x: int, box_y: int, box_w: int, renderer: Renderer) -> None:
        """Draw the grim skull crest, title banner, and epitaph text."""
        cx = SCREEN_WIDTH // 2

        sk_y = box_y + 12
        pyxel.circ(cx, sk_y + 6, 7, COLOR_RED)
        pyxel.rect(cx - 4, sk_y + 9, 9, 5, COLOR_RED)
        pyxel.pset(cx - 3, sk_y + 6, COLOR_BLACK)
        pyxel.pset(cx + 3, sk_y + 6, COLOR_BLACK)
        pyxel.pset(cx, sk_y + 8, COLOR_BLACK)
        pyxel.line(cx - 2, sk_y + 12, cx - 2, sk_y + 13, COLOR_BLACK)
        pyxel.line(cx, sk_y + 12, cx, sk_y + 13, COLOR_BLACK)
        pyxel.line(cx + 2, sk_y + 12, cx + 2, sk_y + 13, COLOR_BLACK)

        pyxel.line(cx - 40, sk_y + 8, cx - 12, sk_y + 8, COLOR_RED)
        pyxel.line(cx - 40, sk_y + 11, cx - 12, sk_y + 11, COLOR_RED)
        pyxel.line(cx + 12, sk_y + 8, cx + 40, sk_y + 8, COLOR_RED)
        pyxel.line(cx + 12, sk_y + 11, cx + 40, sk_y + 11, COLOR_RED)
        pyxel.pset(cx - 42, sk_y + 9, COLOR_RED)
        pyxel.pset(cx + 42, sk_y + 9, COLOR_RED)

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

        div_y = title_y + 16
        pyxel.line(cx - 52, div_y, cx + 52, div_y, COLOR_RED)
        pyxel.pset(cx, div_y - 2, COLOR_RED)
        pyxel.line(cx - 2, div_y, cx + 2, div_y, COLOR_RED)
        pyxel.pset(cx, div_y + 2, COLOR_RED)
        pyxel.pset(cx, div_y, COLOR_WHITE)

        if i18n.locale == "es":
            line1 = "Tus huesos se unen a la"
            line2 = "mazmorra eterna..."
        else:
            line1 = "Your bones join the"
            line2 = "endless dungeon..."

        renderer.draw_text(cx - renderer.get_text_width(line1) // 2, div_y + 8, line1, COLOR_WHITE)
        renderer.draw_text(cx - renderer.get_text_width(line2) // 2, div_y + 18, line2, COLOR_WHITE)

    def _draw_victory_scene(self, box_x: int, box_y: int, box_w: int, box_h: int, game_state: GameState) -> None:
        """Render the grand cathedral hall, god rays, dais steps, and victorious hero."""
        fc = pyxel.frame_count
        cx = SCREEN_WIDTH // 2

        # 1. Background Vaulted Cathedral Architecture
        for my in range(box_y + 14, box_y + 148, 8):
            pyxel.line(box_x + 8, my, box_x + box_w - 9, my, COLOR_NAVY)
            pyxel.pset(box_x + 22 + ((my * 3) % 36), my + 4, COLOR_DARK_BLUE)
            pyxel.pset(box_x + box_w - 40 - ((my * 5) % 36), my + 4, COLOR_DARK_BLUE)

        # Distant nave vaulted arch
        pyxel.rect(cx - 54, box_y + 16, 108, 126, COLOR_NAVY)
        pyxel.tri(cx - 54, box_y + 16, cx, box_y + 3, cx + 53, box_y + 16, COLOR_NAVY)
        pyxel.rect(cx - 50, box_y + 20, 100, 122, COLOR_BLACK)
        pyxel.tri(cx - 50, box_y + 20, cx, box_y + 7, cx + 49, box_y + 20, COLOR_BLACK)

        # Flanking Massive Stone Columns
        for col_x in [box_x + 10, box_x + box_w - 24]:
            pyxel.rect(col_x, box_y + 12, 14, 150, COLOR_NAVY)
            pyxel.rectb(col_x - 2, box_y + 12, 18, 6, COLOR_DARK_BLUE)
            for cy_line in range(box_y + 18, box_y + 160, 6):
                pyxel.line(col_x, cy_line, col_x + 13, cy_line, COLOR_DARK_BLUE)
                pyxel.line(col_x + 3, cy_line, col_x + 3, cy_line + 5, COLOR_BLACK)
                pyxel.line(col_x + 10, cy_line, col_x + 10, cy_line + 5, COLOR_BLACK)

        # Hanging Crimson Cathedral Banners with Golden Crosses
        for bx in [box_x + 20, box_x + box_w - 38]:
            pyxel.rect(bx, box_y + 16, 18, 64, COLOR_RED)
            pyxel.tri(bx, box_y + 80, bx + 9, box_y + 92, bx + 17, box_y + 80, COLOR_RED)
            pyxel.rectb(bx, box_y + 16, 18, 64, COLOR_ORANGE)
            pyxel.line(bx, box_y + 80, bx + 9, box_y + 92, COLOR_ORANGE)
            pyxel.line(bx + 17, box_y + 80, bx + 9, box_y + 92, COLOR_ORANGE)
            # Golden Fleur-de-lis / Royal Cross
            pyxel.line(bx + 8, box_y + 30, bx + 8, box_y + 54, COLOR_YELLOW)
            pyxel.line(bx + 9, box_y + 30, bx + 9, box_y + 54, COLOR_YELLOW)
            pyxel.line(bx + 4, box_y + 38, bx + 13, box_y + 38, COLOR_YELLOW)
            pyxel.line(bx + 4, box_y + 44, bx + 13, box_y + 44, COLOR_YELLOW)
            pyxel.pset(bx + 8, box_y + 27, COLOR_WHITE)
            pyxel.pset(bx + 9, box_y + 27, COLOR_WHITE)

        # 2. Celestial God Rays Beaming Down
        for gy in range(box_y + 58, box_y + 155):
            progress = (gy - (box_y + 58)) / 97.0
            beam_half = int(14 + progress * 34)
            for bx_ray in range(cx - beam_half, cx + beam_half + 1):
                d_center = abs(bx_ray - cx)
                if (bx_ray * 3 + gy * 7) % 5 == 0:
                    if d_center < beam_half // 3:
                        pyxel.pset(bx_ray, gy, COLOR_WHITE if (fc + bx_ray) % 8 < 4 else COLOR_YELLOW)
                    elif d_center < (beam_half * 2) // 3:
                        pyxel.pset(bx_ray, gy, COLOR_YELLOW if (bx_ray + gy) % 2 == 0 else COLOR_PEACH)
                    else:
                        if (bx_ray + gy + fc // 4) % 3 == 0:
                            pyxel.pset(bx_ray, gy, COLOR_PEACH)

        # 3. Flanking Braziers on Stone Pedestals
        for tx in [box_x + 36, box_x + box_w - 48]:
            base_y = box_y + 158
            pyxel.rect(tx - 3, base_y - 28, 12, 28, COLOR_NAVY)
            pyxel.rectb(tx - 4, base_y - 32, 14, 5, COLOR_LIGHT_BLUE)
            # Roaring sacred flame
            pyxel.tri(tx - 3, base_y - 32, tx + 3, base_y - 48, tx + 9, base_y - 32, COLOR_RED)
            pyxel.tri(tx - 1, base_y - 32, tx + 3, base_y - 44, tx + 7, base_y - 32, COLOR_ORANGE)
            pyxel.pset(tx + 3, base_y - 38, COLOR_YELLOW if fc % 4 < 2 else COLOR_WHITE)
            if fc % 3 == 0:
                pyxel.pset(tx + (fc % 4), base_y - 50, COLOR_YELLOW)

        # 4. Stone Dias Steps & Royal Red Runner Carpet
        # Step 4 (bottom): y=190..198
        pyxel.rect(cx - 78, box_y + 174, 156, 12, COLOR_NAVY)
        pyxel.line(cx - 78, box_y + 174, cx + 77, box_y + 174, COLOR_DARK_BLUE)
        # Step 3: y=182..190
        pyxel.rect(cx - 62, box_y + 164, 124, 11, COLOR_NAVY)
        pyxel.line(cx - 62, box_y + 164, cx + 61, box_y + 164, COLOR_DARK_BLUE)
        # Step 2: y=174..182
        pyxel.rect(cx - 48, box_y + 154, 96, 11, COLOR_NAVY)
        pyxel.line(cx - 48, box_y + 154, cx + 47, box_y + 154, COLOR_DARK_BLUE)
        # Step 1 (top platform): y=166..174
        pyxel.rect(cx - 36, box_y + 144, 72, 11, COLOR_DARK_BLUE)
        pyxel.line(cx - 36, box_y + 144, cx + 35, box_y + 144, COLOR_LIGHT_BLUE)

        # Rubble / Carved masonry blocks on outer sides
        for block_x, block_y in [
            (box_x + 8, box_y + 178), (box_x + 22, box_y + 182),
            (box_x + box_w - 32, box_y + 178), (box_x + box_w - 46, box_y + 182)
        ]:
            pyxel.rect(block_x, block_y, 14, 10, COLOR_NAVY)
            pyxel.rectb(block_x, block_y, 14, 10, COLOR_DARK_BLUE)

        # Royal Red Runner Carpet cascading down the steps
        carpet_half = 18
        for cy_step in range(box_y + 144, box_y + 186):
            pyxel.rect(cx - carpet_half, cy_step, carpet_half * 2 + 1, 1, COLOR_RED)
            # Gold fringe border on edges
            pyxel.pset(cx - carpet_half, cy_step, COLOR_YELLOW)
            pyxel.pset(cx - carpet_half + 1, cy_step, COLOR_ORANGE)
            pyxel.pset(cx + carpet_half, cy_step, COLOR_YELLOW)
            pyxel.pset(cx + carpet_half - 1, cy_step, COLOR_ORANGE)

        # Golden Insignia Emblem on the carpet face
        crest_y = box_y + 158
        pyxel.line(cx, crest_y, cx, crest_y + 14, COLOR_YELLOW)
        pyxel.line(cx - 1, crest_y, cx - 1, crest_y + 14, COLOR_YELLOW)
        pyxel.line(cx - 4, crest_y + 5, cx + 4, crest_y + 5, COLOR_YELLOW)
        pyxel.line(cx - 3, crest_y + 9, cx + 3, crest_y + 9, COLOR_YELLOW)
        pyxel.pset(cx, crest_y - 2, COLOR_WHITE)
        pyxel.pset(cx - 1, crest_y - 2, COLOR_WHITE)

        # 5. Victorious Champion Standing with Raised Arm
        hx = cx - 2
        hy = box_y + 130
        cls_id = getattr(game_state.player, "class_id", "rogue")

        # Victor Shadow
        pyxel.elli(hx - 8, hy + 13, 18, 5, COLOR_BLACK)

        if cls_id == "warrior":
            # Golden Hair & Circlet
            pyxel.rect(hx - 4, hy - 4, 9, 8, COLOR_YELLOW)
            pyxel.rect(hx - 3, hy - 1, 7, 6, COLOR_PEACH)
            pyxel.pset(hx - 1, hy + 1, COLOR_BLACK)
            pyxel.pset(hx + 2, hy + 1, COLOR_BLACK)
            # Armor Torso
            pyxel.rect(hx - 5, hy + 4, 11, 8, COLOR_LIGHT_BLUE)
            pyxel.line(hx - 5, hy + 7, hx + 5, hy + 7, COLOR_NAVY)
            # Red flowing cape
            pyxel.tri(hx - 7, hy + 5, hx - 4, hy + 5, hx - 10, hy + 14, COLOR_RED)
            # Boots
            pyxel.rect(hx - 4, hy + 12, 4, 3, COLOR_BROWN)
            pyxel.rect(hx + 1, hy + 12, 4, 3, COLOR_BROWN)
            # Raised Right Arm holding aloft gleaming claymore
            pyxel.line(hx + 5, hy + 6, hx + 10, hy - 1, COLOR_LIGHT_BLUE)
            pyxel.rect(hx + 9, hy - 2, 4, 2, COLOR_YELLOW)  # Crossguard
            pyxel.line(hx + 11, hy - 2, hx + 16, hy - 17, COLOR_WHITE)  # Gleaming blade
            pyxel.line(hx + 12, hy - 2, hx + 17, hy - 17, COLOR_CYAN)
            pyxel.pset(hx + 17, hy - 18, COLOR_WHITE)

        elif cls_id == "mage":
            # Purple Wizard Hat
            pyxel.tri(hx - 6, hy - 1, hx, hy - 13, hx + 6, hy - 1, COLOR_PURPLE)
            pyxel.rect(hx - 8, hy - 1, 17, 3, COLOR_PURPLE)
            pyxel.rect(hx - 4, hy + 1, 9, 5, COLOR_PEACH)
            pyxel.pset(hx - 1, hy + 3, COLOR_CYAN)
            pyxel.pset(hx + 2, hy + 3, COLOR_CYAN)
            # Violet Robes
            pyxel.rect(hx - 6, hy + 6, 13, 9, COLOR_PURPLE)
            pyxel.line(hx, hy + 6, hx, hy + 14, COLOR_YELLOW)
            # Boots
            pyxel.rect(hx - 4, hy + 13, 4, 2, COLOR_BROWN)
            pyxel.rect(hx + 1, hy + 13, 4, 2, COLOR_BROWN)
            # Raised Right Arm holding aloft radiant archmage staff
            pyxel.line(hx + 5, hy + 6, hx + 10, hy - 1, COLOR_PURPLE)
            pyxel.line(hx + 10, hy + 10, hx + 14, hy - 14, COLOR_BROWN)
            pyxel.circ(hx + 14, hy - 15, 4, COLOR_CYAN)
            pyxel.circb(hx + 14, hy - 15, 4, COLOR_WHITE)
            pyxel.pset(hx + 14, hy - 15, COLOR_WHITE)

        else:  # rogue (default from screenshot)
            # Dark hooded head with red face wrap
            pyxel.circ(hx + 1, hy - 1, 6, COLOR_NAVY)
            pyxel.rect(hx - 3, hy + 1, 9, 4, COLOR_PEACH)
            pyxel.pset(hx - 1, hy + 2, COLOR_BLACK)
            pyxel.pset(hx + 2, hy + 2, COLOR_BLACK)
            pyxel.rect(hx - 4, hy + 4, 11, 2, COLOR_RED)  # Red scarf
            # Leather armor torso
            pyxel.rect(hx - 5, hy + 6, 11, 6, COLOR_DARK_BLUE)
            pyxel.line(hx - 5, hy + 9, hx + 5, hy + 9, COLOR_NAVY)
            # Capelet
            pyxel.rect(hx - 8, hy + 6, 3, 8, COLOR_RED)
            # Boots
            pyxel.rect(hx - 4, hy + 12, 4, 3, COLOR_BROWN)
            pyxel.rect(hx + 1, hy + 12, 4, 3, COLOR_BROWN)
            # Raised Right Arm holding aloft gleaming blade
            pyxel.line(hx + 5, hy + 6, hx + 10, hy - 1, COLOR_DARK_BLUE)
            pyxel.rect(hx + 9, hy - 2, 4, 2, COLOR_YELLOW)  # Guard
            pyxel.line(hx + 11, hy - 2, hx + 16, hy - 16, COLOR_WHITE)  # Gleaming blade
            pyxel.line(hx + 12, hy - 2, hx + 17, hy - 16, COLOR_CYAN)
            pyxel.pset(hx + 17, hy - 17, COLOR_WHITE)

        # 6. Radiant Twinkling Stars & Sparkles
        sparkles = [
            (hx - 32, hy - 2), (hx - 22, hy - 20), (hx - 12, hy + 8),
            (hx + 18, hy - 32), (hx + 30, hy - 16), (hx + 24, hy + 4),
            (hx - 40, hy + 14), (hx + 38, hy + 14), (hx, hy - 24)
        ]
        for si, (sx, sy) in enumerate(sparkles):
            if (fc + si * 4) % 16 < 9:
                pyxel.pset(sx, sy, COLOR_WHITE)
                pyxel.pset(sx - 1, sy, COLOR_YELLOW)
                pyxel.pset(sx + 1, sy, COLOR_YELLOW)
                pyxel.pset(sx, sy - 1, COLOR_YELLOW)
                pyxel.pset(sx, sy + 1, COLOR_YELLOW)

    def _draw_victory_header(self, box_x: int, box_y: int, box_w: int, renderer: Renderer) -> None:
        """Draw the golden crown, radiating sunburst, bold VICTORY headline, and subtitle."""
        fc = pyxel.frame_count
        cx = SCREEN_WIDTH // 2

        # 1. Radiating Sunburst Rays behind Crown
        crown_center_y = box_y + 24
        ray_angles = [0, 22, 45, 68, 90, 112, 135, 158, 180]
        for ang in ray_angles:
            rad = math.radians(ang)
            r_inner = 18
            r_outer = 32 + (4 if (fc // 6 + ang) % 2 == 0 else 0)
            x1 = cx + int(math.cos(rad) * r_inner)
            y1 = crown_center_y - int(math.sin(rad) * r_inner)
            x2 = cx + int(math.cos(rad) * r_outer)
            y2 = crown_center_y - int(math.sin(rad) * r_outer)
            pyxel.line(x1, y1, x2, y2, COLOR_YELLOW if ang % 45 == 0 else COLOR_ORANGE)

        # 2. Golden Crown of Aethelgard
        cr_y = box_y + 15
        cr_w = 40
        cr_x = cx - cr_w // 2

        # Crown Base & Spikes
        pyxel.rect(cr_x + 4, cr_y + 12, cr_w - 8, 8, COLOR_YELLOW)
        pyxel.line(cr_x + 4, cr_y + 19, cr_x + cr_w - 5, cr_y + 19, COLOR_ORANGE)
        # Five Crown Spikes
        pyxel.tri(cr_x + 4, cr_y + 12, cr_x + 5, cr_y + 2, cr_x + 10, cr_y + 12, COLOR_YELLOW)
        pyxel.tri(cr_x + 10, cr_y + 12, cr_x + 13, cr_y + 5, cr_x + 17, cr_y + 12, COLOR_YELLOW)
        pyxel.tri(cr_x + 17, cr_y + 12, cr_x + 20, cr_y - 2, cr_x + 23, cr_y + 12, COLOR_YELLOW)  # Center tall spike
        pyxel.tri(cr_x + 23, cr_y + 12, cr_x + 27, cr_y + 5, cr_x + 30, cr_y + 12, COLOR_YELLOW)
        pyxel.tri(cr_x + 30, cr_y + 12, cr_x + 35, cr_y + 2, cr_x + 36, cr_y + 12, COLOR_YELLOW)

        # Crown Highlights & Jewels
        pyxel.pset(cr_x + 20, cr_y - 2, COLOR_WHITE)
        pyxel.pset(cr_x + 10, cr_y + 15, COLOR_RED)  # Ruby
        pyxel.pset(cr_x + 20, cr_y + 15, COLOR_WHITE)  # Diamond
        pyxel.pset(cr_x + 30, cr_y + 15, COLOR_CYAN)  # Sapphire

        # 3. Flanking Golden Banner Horizontal Bars
        bar_y = box_y + 44
        pyxel.line(cx - 86, bar_y, cx - 14, bar_y, COLOR_YELLOW)
        pyxel.line(cx - 86, bar_y + 1, cx - 14, bar_y + 1, COLOR_ORANGE)
        pyxel.line(cx + 14, bar_y, cx + 86, bar_y, COLOR_YELLOW)
        pyxel.line(cx + 14, bar_y + 1, cx + 86, bar_y + 1, COLOR_ORANGE)
        # Diamond studs on bars
        for dx in [-88, -50, 50, 88]:
            pyxel.pset(cx + dx, bar_y, COLOR_WHITE)
            pyxel.pset(cx + dx, bar_y + 1, COLOR_YELLOW)

        # 4. Chunky Retro "VICTORY ACHIEVED!" Title
        title_y = box_y + 49
        title_str = "VICTORY ACHIEVED!" if i18n.locale == "en" else "¡VICTORIA OBTENIDA!"

        # Measure title width
        total_w = 0
        for char in title_str:
            if char == ' ':
                total_w += 4
            else:
                total_w += (self._draw_bold_letter(0, 0, char, 0) + 1)

        start_x = cx - total_w // 2
        curr_x = start_x
        for char in title_str:
            if char == ' ':
                curr_x += 4
            else:
                w = self._draw_bold_letter(curr_x, title_y, char, COLOR_YELLOW)
                curr_x += w + 1

        # 5. Golden Diamond Separator
        div_y = title_y + 14
        pyxel.line(cx - 68, div_y, cx + 68, div_y, COLOR_YELLOW)
        pyxel.line(cx - 68, div_y + 1, cx + 68, div_y + 1, COLOR_ORANGE)
        # Center Diamond
        pyxel.pset(cx, div_y - 2, COLOR_YELLOW)
        pyxel.line(cx - 2, div_y, cx + 2, div_y, COLOR_YELLOW)
        pyxel.pset(cx, div_y + 2, COLOR_YELLOW)
        pyxel.pset(cx, div_y, COLOR_WHITE)

        # 6. Two-line Subtitle
        if i18n.locale == "es":
            sub1 = "¡Has conquistado la Aguja de"
            sub2 = "Aethelgard!"
        else:
            sub1 = "You conquered the Spire of"
            sub2 = "Aethelgard!"

        renderer.draw_text(cx - renderer.get_text_width(sub1) // 2, div_y + 6, sub1, COLOR_WHITE)
        renderer.draw_text(cx - renderer.get_text_width(sub2) // 2, div_y + 16, sub2, COLOR_WHITE)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        box_x, box_y, box_w, box_h = 10, 28, SCREEN_WIDTH - 20, 220

        if not self.is_victory:
            # =================================================================
            # GAME OVER / DEATH SCREEN
            # =================================================================
            pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

            self._draw_death_scene(box_x, box_y, box_w, box_h)
            self._draw_death_header(box_x, box_y, box_w, renderer)

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
            renderer.draw_text(btn_x + (btn_w - renderer.get_text_width(btn_label)) // 2, btn_y + 6, btn_label,
                               COLOR_WHITE)

        else:
            # =================================================================
            # TRIUMPHANT VICTORY SCREEN (Aligned with concept art)
            # =================================================================
            pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

            # 1. Cathedral Architecture, Braziers, Dais, God Rays & Hero
            self._draw_victory_scene(box_x, box_y, box_w, box_h, game_state)

            # 2. Golden Crown, Rays, Chunky VICTORY Headline & Subtitle
            self._draw_victory_header(box_x, box_y, box_w, renderer)

            # 3. Outer Ornate Golden Double Border with Fleurons
            pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_YELLOW)
            pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_ORANGE)

            for cx, cy in [
                (box_x + 3, box_y + 3),
                (box_x + box_w - 4, box_y + 3),
                (box_x + 3, box_y + box_h - 4),
                (box_x + box_w - 4, box_y + box_h - 4),
            ]:
                pyxel.pset(cx, cy, COLOR_YELLOW)
                pyxel.pset(cx - 1, cy, COLOR_ORANGE)
                pyxel.pset(cx + 1, cy, COLOR_ORANGE)
                pyxel.pset(cx, cy - 1, COLOR_ORANGE)
                pyxel.pset(cx, cy + 1, COLOR_ORANGE)

            # 4. Centered Ornate [RESTART] Button with Corner Ticks
            btn_w, btn_h = 104, 18
            btn_x = (SCREEN_WIDTH - btn_w) // 2
            btn_y = 206

            pyxel.rect(btn_x, btn_y, btn_w, btn_h, COLOR_BLACK)
            pyxel.rectb(btn_x, btn_y, btn_w, btn_h, COLOR_YELLOW)

            # Corner ticks on button
            pyxel.line(btn_x - 2, btn_y - 2, btn_x + 3, btn_y - 2, COLOR_YELLOW)
            pyxel.line(btn_x - 2, btn_y - 2, btn_x - 2, btn_y + 3, COLOR_YELLOW)
            pyxel.line(btn_x + btn_w + 1, btn_y - 2, btn_x + btn_w - 4, btn_y - 2, COLOR_YELLOW)
            pyxel.line(btn_x + btn_w + 1, btn_y - 2, btn_x + btn_w + 1, btn_y + 3, COLOR_YELLOW)
            pyxel.line(btn_x - 2, btn_y + btn_h + 1, btn_x + 3, btn_y + btn_h + 1, COLOR_YELLOW)
            pyxel.line(btn_x - 2, btn_y + btn_h + 1, btn_x - 2, btn_y + btn_h - 4, COLOR_YELLOW)
            pyxel.line(btn_x + btn_w + 1, btn_y + btn_h + 1, btn_x + btn_w - 4, btn_y + btn_h + 1, COLOR_YELLOW)
            pyxel.line(btn_x + btn_w + 1, btn_y + btn_h + 1, btn_x + btn_w + 1, btn_y + btn_h - 4, COLOR_YELLOW)

            btn_label = "[RESTART]" if i18n.locale == "en" else "[REINICIAR]"
            renderer.draw_text(btn_x + (btn_w - renderer.get_text_width(btn_label)) // 2, btn_y + 6, btn_label,
                               COLOR_YELLOW)
