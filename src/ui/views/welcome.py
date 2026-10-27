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
    COLOR_LIME,
    COLOR_NAVY,
    COLOR_ORANGE,
    COLOR_PEACH,
    COLOR_WHITE,
    COLOR_YELLOW,
    SCREEN_WIDTH,
)
from src.core.game_state import GameMode
from src.core.i18n import i18n, t
from src.ui.renderer import Renderer
from src.ui.views.base import View

if TYPE_CHECKING:
    from src.core.game_state import GameState


# =============================================================================
# BIOME ENEMY SPRITE COORDINATE MAP (Bank 0)
# =============================================================================
class WelcomeView(View):
    """Renders the high-atmosphere gothic fantasy title screen."""

    def update(self, game_state: GameState) -> None:
        from src.config import SND_CLICK
        if Renderer.is_clicked(6, 6, 44, 14) or pyxel.btnp(pyxel.KEY_L):
            i18n.toggle_language()
            pyxel.play(0, 3)
        elif pyxel.btnp(pyxel.KEY_1) or Renderer.is_clicked(36, 158, 184, 16):
            pyxel.play(0, SND_CLICK)
            game_state.switch_mode(GameMode.CLASS_SELECT)
        elif pyxel.btnp(pyxel.KEY_2) or Renderer.is_clicked(36, 178, 184, 16):
            pass
        elif pyxel.btnp(pyxel.KEY_3) or Renderer.is_clicked(36, 198, 184, 16):
            pyxel.play(0, 3)
            game_state.switch_mode(GameMode.CREDITS)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        w = SCREEN_WIDTH
        fc = pyxel.frame_count

        pyxel.rect(0, 0, w, 52, COLOR_NAVY)
        for y in range(52, 72):
            step = (y - 52) / 20.0
            for x in range(w):
                if (x + y) % 2 == 0 or (x * 3 + y * 7) % 5 > int(step * 5):
                    pyxel.pset(x, y, COLOR_NAVY)
                else:
                    pyxel.pset(x, y, COLOR_BLACK)

        pyxel.circ(38, 44, 8, COLOR_WHITE)
        pyxel.circ(41, 43, 7, COLOR_NAVY)

        stars = [(18, 38), (60, 46), (82, 36), (110, 42), (180, 40), (210, 48), (145, 50)]
        for idx, (sx, sy) in enumerate(stars):
            col = COLOR_WHITE if (fc + idx * 7) % 24 < 12 else COLOR_YELLOW
            pyxel.pset(sx, sy, col)

        pyxel.rect(48, 86, 160, 40, COLOR_NAVY)
        for wx in range(48, 208, 8):
            pyxel.rect(wx, 82, 4, 4, COLOR_NAVY)

        citadel_towers = [
            (62, 126, 18, 48, True, 18),
            (84, 126, 22, 60, True, 22),
            (110, 126, 36, 72, True, 26),
            (150, 126, 20, 56, True, 20),
            (174, 126, 18, 44, True, 16),
        ]
        for tx, ty, tw, th, has_spire, sh in citadel_towers:
            wall_top = ty - th
            pyxel.rect(tx, wall_top, tw, th, COLOR_DARK_BLUE)
            for my in range(wall_top + 4, ty, 6):
                pyxel.line(tx, my, tx + tw - 1, my, COLOR_NAVY)
                offset = 3 if (my // 6) % 2 == 0 else tw // 2
                pyxel.pset(tx + offset, my + 3, COLOR_GRAY)
            for cx in range(tx, tx + tw, 4):
                pyxel.rect(cx, wall_top - 3, 2, 3, COLOR_DARK_BLUE)
            if has_spire:
                spire_top = wall_top - sh - 3
                pyxel.tri(tx - 1, wall_top - 3, tx + tw // 2, spire_top, tx + tw + 1, wall_top - 3, COLOR_DARK_BLUE)
                pyxel.line(tx + tw // 2, spire_top - 3, tx + tw // 2, spire_top, COLOR_YELLOW)

        gw_x, gw_y = 124, 76
        pyxel.rect(gw_x, gw_y + 4, 8, 12, COLOR_YELLOW if (fc // 15) % 2 == 0 else COLOR_ORANGE)
        pyxel.tri(gw_x, gw_y + 4, gw_x + 4, gw_y, gw_x + 7, gw_y + 4, COLOR_YELLOW)
        pyxel.line(gw_x + 3, gw_y + 1, gw_x + 3, gw_y + 15, COLOR_DARK_BLUE)
        pyxel.line(gw_x + 4, gw_y + 1, gw_x + 4, gw_y + 15, COLOR_DARK_BLUE)
        pyxel.line(gw_x, gw_y + 8, gw_x + 7, gw_y + 8, COLOR_DARK_BLUE)

        pyxel.rect(70, 92, 2, 6, COLOR_ORANGE if (fc // 10) % 3 != 0 else COLOR_YELLOW)
        pyxel.rect(94, 82, 2, 7, COLOR_YELLOW if (fc // 10) % 2 == 0 else COLOR_ORANGE)
        pyxel.rect(159, 86, 2, 6, COLOR_ORANGE if (fc // 12) % 2 == 0 else COLOR_YELLOW)

        pyxel.rect(0, 52, 24, 74, COLOR_DARK_BLUE)
        for py in range(52, 126, 6):
            pyxel.line(0, py, 23, py, COLOR_NAVY)
            stagger = 4 if (py // 6) % 2 == 0 else 14
            pyxel.pset(stagger, py + 3, COLOR_GRAY)
        pyxel.line(24, 52, 24, 126, COLOR_BLACK)
        pyxel.rect(18, 92, 3, 2, COLOR_BROWN)
        pyxel.pset(19, 90, COLOR_ORANGE if (fc % 4 < 2) else COLOR_YELLOW)
        pyxel.blt(0, 22, 1, 168, 0, 24, 32, 0)

        pyxel.rect(w - 24, 52, 24, 74, COLOR_DARK_BLUE)
        for py in range(52, 126, 6):
            pyxel.line(w - 24, py, w, py, COLOR_NAVY)
            stagger = 4 if (py // 6) % 2 == 0 else 14
            pyxel.pset(w - 24 + stagger, py + 3, COLOR_GRAY)
        pyxel.line(w - 25, 52, w - 25, 126, COLOR_BLACK)
        pyxel.rect(w - 21, 92, 3, 2, COLOR_BROWN)
        pyxel.pset(w - 20, 90, COLOR_YELLOW if (fc % 4 < 2) else COLOR_ORANGE)
        pyxel.blt(w - 24, 22, 1, 168, 0, -24, 32, 0)

        pyxel.rect(16, 126, w - 32, 20, COLOR_BROWN)
        pyxel.line(16, 126, w - 16, 126, COLOR_PEACH)
        for rx in range(18, w - 18, 8):
            pyxel.pset(rx, 127, COLOR_BROWN)
            if rx % 16 == 0:
                pyxel.line(rx, 128, rx + 2, 134, COLOR_BLACK)

        fire_x, fire_y = 114, 118
        pyxel.rect(fire_x - 3, fire_y + 7, 14, 2, COLOR_GRAY)
        pyxel.rect(fire_x - 1, fire_y + 8, 10, 1, COLOR_DARK_BLUE)
        for ox in range(-12, 13):
            dist = abs(ox)
            if dist < 6:
                pyxel.pset(fire_x + 4 + ox, 126, COLOR_YELLOW)
            elif dist < 11:
                pyxel.pset(fire_x + 4 + ox, 126, COLOR_ORANGE if (fc + ox) % 2 == 0 else COLOR_PEACH)

        pyxel.blt(fire_x, fire_y, 0, 88, 0, 8, 8, 0)
        for i in range(3):
            px = fire_x + 3 + ((fc * 2 + i * 5) % 5) - 2
            py = fire_y - ((fc + i * 7) % 10)
            pyxel.pset(px, py, COLOR_YELLOW if i % 2 == 0 else COLOR_ORANGE)

        pyxel.blt(76, 110, 0, 0, 0, 16, 16, 0)
        pyxel.line(90, 116, 100, 106, COLOR_CYAN)
        pyxel.line(91, 116, 101, 106, COLOR_WHITE)
        pyxel.blt(148, 98, 1, 144, 0, 24, 28, 0)

        pyxel.blt(56, 8, 1, 0, 0, 144, 32, 0)

        box_x, box_y, box_w, box_h = 36, 148, 184, 78
        renderer.draw_box(box_x, box_y, box_w, box_h, bg_col=COLOR_NAVY, border_col=COLOR_WHITE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_YELLOW)

        pyxel.blt(box_x - 3, box_y - 3, 1, 192, 0, 8, 8, 0)
        pyxel.blt(box_x + box_w - 5, box_y - 3, 1, 192, 0, 8, 8, 0)
        pyxel.blt(box_x - 3, box_y + box_h - 5, 1, 192, 0, 8, 8, 0)
        pyxel.blt(box_x + box_w - 5, box_y + box_h - 5, 1, 192, 0, 8, 8, 0)

        cursor_pulse = (fc // 6 % 2) * 2
        pyxel.blt(48 + cursor_pulse, 162, 1, 200, 0, 8, 8, 0)

        renderer.draw_button(46, 158, 164, 16, t("menu_new_game"), bg_col=COLOR_NAVY)
        renderer.draw_button(46, 178, 164, 16, t("menu_load_game"), bg_col=COLOR_NAVY, text_col=COLOR_GRAY)
        renderer.draw_button(46, 198, 164, 16, t("menu_credits"), bg_col=COLOR_NAVY, text_col=COLOR_WHITE)

        if (fc // 15) % 2 == 0:
            prompt = t("menu_prompt")
            renderer.draw_text(w // 2 - len(prompt) * 2, 236, prompt, COLOR_LIME)

        renderer.draw_button(
            6, 6, 44, 14,
            f"[{i18n.locale.upper()}]",
            bg_col=COLOR_NAVY,
            border_col=COLOR_WHITE,
            text_col=COLOR_YELLOW,
        )
