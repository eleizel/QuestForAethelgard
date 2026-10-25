"""HUD, combat logs, and stat panel rendering using Pyxel graphics primitives."""

from __future__ import annotations

import pyxel
import os
from src.core.i18n import t
from src.config import (
    COLOR_BLACK,
    COLOR_DARK_BLUE,
    COLOR_GRAY,
    COLOR_GREEN,
    COLOR_LIME,
    COLOR_NAVY,
    COLOR_PEACH,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    SCREEN_WIDTH,
)
from src.entities.actor import Stats
from src.entities.player import Player


class Renderer:
    """Provides modular UI rendering utilities for game screens."""

    def __init__(self):
        bdf_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets",
            "spleen-5x8.bdf",
        )
        self.font = pyxel.Font(bdf_path) if os.path.exists(bdf_path) else None

    def draw_text(self, x: int, y: int, text: str, col: int) -> None:
        if self.font:
            pyxel.text(x, y, text, col, self.font)
        else:
            pyxel.text(x, y, text, col)

    @staticmethod
    def is_clicked(x: int, y: int, w: int, h: int) -> bool:
        """Return True if left click / tap occurred within the bounding box."""
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            return (x <= pyxel.mouse_x < x + w) and (y <= pyxel.mouse_y < y + h)
        return False

    def get_text_width(self, text: str) -> int:
        """Return pixel width of text based on current font."""
        char_w = 6 if self.font else 4
        return len(text) * char_w

    def draw_button(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        label: str,
        bg_col: int = COLOR_NAVY,
        border_col: int = COLOR_WHITE,
        text_col: int = COLOR_YELLOW,
    ) -> bool:
        """Draw a touch button and return True if clicked/tapped this frame."""
        clicked = self.is_clicked(x, y, w, h)
        fill = COLOR_DARK_BLUE if clicked else bg_col
        pyxel.rect(x, y, w, h, fill)
        pyxel.rectb(x, y, w, h, border_col)
        tw = self.get_text_width(label)
        text_x = x + max(1, (w - tw) // 2)
        text_y = y + (h - 8) // 2
        self.draw_text(text_x, text_y, label, text_col)
        return clicked

    def draw_box(self, x: int, y: int, w: int, h: int, bg_col: int = COLOR_NAVY, border_col: int = COLOR_WHITE) -> None:
        """Render a bordered rectangular dialog frame."""
        pyxel.rect(x, y, w, h, bg_col)
        pyxel.rectb(x, y, w, h, border_col)

    def draw_bar(self, x: int, y: int, w: int, h: int, current: int, maximum: int, fill_col: int = COLOR_LIME, bg_col: int = COLOR_RED) -> None:
        """Render a percentage-filled meter bar (e.g., HP gauge, tick meter)."""
        pyxel.rect(x, y, w, h, bg_col)
        if maximum > 0:
            pct = max(0.0, min(1.0, current / maximum))
            filled_w = int(w * pct)
            if filled_w > 0:
                pyxel.rect(x, y, filled_w, h, fill_col)
        pyxel.rectb(x, y, w, h, COLOR_WHITE)

    def draw_hud(self, player: Player, floor: int) -> None:
        """Render persistent top status banner."""
        self.draw_box(0, 0, SCREEN_WIDTH, 22, bg_col=COLOR_DARK_BLUE, border_col=COLOR_GRAY)

        # Hero name, class, and level
        title_text = f"{player.name} ({player.class_name}) Lv.{player.level}"
        self.draw_text(6, 4, title_text, COLOR_YELLOW)

        # Health bar
        hp_str = t("stat_hp", current=player.current_hp, max=player.max_hp)
        self.draw_text(6, 13, hp_str, COLOR_WHITE)
        self.draw_bar(68, 13, 54, 6, player.current_hp, player.max_hp, fill_col=COLOR_GREEN, bg_col=COLOR_RED)

        # Gold & Dungeon Floor
        gold_text = t("hud_gold", gold=player.gold)
        self.draw_text(128, 13, gold_text, COLOR_YELLOW)
        floor_text = t("hud_floor", floor=floor)
        self.draw_text(174, 4, floor_text, COLOR_PEACH)

        # Draw Inventory Button
        self.draw_button(222, 3, 30, 16, t("inv_title"))

    def draw_stat_panel(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        title: str,
        stats: Stats,
        hp: int,
        max_hp: int,
        color_scheme: int = COLOR_NAVY,
        statuses: list | None = None,
    ) -> None:
        """Render actor statistics box."""
        self.draw_box(x, y, w, h, bg_col=color_scheme, border_col=COLOR_WHITE)
        self.draw_text(x + 6, y + 6, title, COLOR_YELLOW)

        # HP bar
        self.draw_bar(x + 6, y + 18, w - 12, 6, hp, max_hp, fill_col=COLOR_GREEN, bg_col=COLOR_RED)
        self.draw_text(x + 6, y + 26, t("stat_hp", current=hp, max=max_hp), COLOR_WHITE)

        if statuses:
            badge_x = x + 58
            for s in statuses[:2]:
                tag = f"[{s.badge}{s.duration}]"
                self.draw_text(badge_x, y + 26, tag, s.color)
                badge_x += len(tag) * 6 + 2

        # Attributes
        self.draw_text(x + 6, y + 36, t("stat_atk", val=stats.attack), COLOR_WHITE)
        self.draw_text(x + 6, y + 46, t("stat_def", val=stats.defense), COLOR_WHITE)
        self.draw_text(x + 6, y + 56, t("stat_spd", val=stats.speed), COLOR_WHITE)
        crit_pct = int(stats.crit_chance * 100)
        self.draw_text(x + 6, y + 66, t("stat_crit", val=crit_pct), COLOR_WHITE)

    @staticmethod
    def wrap_text(text: str, max_chars_per_line: int = 38) -> list[str]:
        words = text.split(" ")
        wrapped_lines: list[str] = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + (1 if current_line else 0) <= max_chars_per_line:
                current_line = f"{current_line} {word}".strip()
            else:
                if current_line:
                    wrapped_lines.append(current_line)
                current_line = word
        if current_line:
            wrapped_lines.append(current_line)
        return wrapped_lines

    def draw_combat_logs(
        self,
        logs: list[str],
        x: int,
        y: int,
        w: int,
        h: int,
        max_entries: int = 7,
    ) -> None:
        """Render recent battle activity feed."""
        self.draw_box(x, y, w, h, bg_col=COLOR_BLACK, border_col=COLOR_GRAY)
        self.draw_text(x + 6, y + 4, t("combat_log_header"), COLOR_YELLOW)

        recent_logs = logs if logs else [t("combat_awaiting")]
        wrapped_logs = []
        for log in recent_logs:
            wrapped_logs.extend(self.wrap_text(log))

        recent = wrapped_logs[-max_entries:] if wrapped_logs else []
        line_y = y + 14
        for disp in recent:
            self.draw_text(x + 6, line_y, disp, COLOR_WHITE)
            line_y += 9
