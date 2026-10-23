"""HUD, combat logs, and stat panel rendering using Pyxel graphics primitives."""

from __future__ import annotations

import pyxel

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

    @staticmethod
    def draw_box(x: int, y: int, w: int, h: int, bg_col: int = COLOR_NAVY, border_col: int = COLOR_WHITE) -> None:
        """Render a bordered rectangular dialog frame."""
        pyxel.rect(x, y, w, h, bg_col)
        pyxel.rectb(x, y, w, h, border_col)

    @staticmethod
    def draw_bar(x: int, y: int, w: int, h: int, current: int, maximum: int, fill_col: int = COLOR_LIME, bg_col: int = COLOR_RED) -> None:
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
        pyxel.text(6, 4, title_text, COLOR_YELLOW)

        # Health bar
        hp_str = f"HP {player.current_hp}/{player.max_hp}"
        pyxel.text(6, 13, hp_str, COLOR_WHITE)
        self.draw_bar(70, 13, 60, 6, player.current_hp, player.max_hp, fill_col=COLOR_GREEN, bg_col=COLOR_RED)

        # Gold & Dungeon Floor
        gold_text = f"Gold: {player.gold}"
        pyxel.text(145, 13, gold_text, COLOR_YELLOW)
        floor_text = f"Floor {floor}"
        pyxel.text(210, 4, floor_text, COLOR_PEACH)

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
    ) -> None:
        """Render actor statistics box."""
        self.draw_box(x, y, w, h, bg_col=color_scheme, border_col=COLOR_WHITE)
        pyxel.text(x + 6, y + 6, title, COLOR_YELLOW)

        # HP bar
        self.draw_bar(x + 6, y + 18, w - 12, 6, hp, max_hp, fill_col=COLOR_GREEN, bg_col=COLOR_RED)
        pyxel.text(x + 6, y + 26, f"HP: {hp}/{max_hp}", COLOR_WHITE)

        # Attributes
        pyxel.text(x + 6, y + 36, f"ATK: {stats.attack}", COLOR_WHITE)
        pyxel.text(x + 6, y + 46, f"DEF: {stats.defense}", COLOR_WHITE)
        pyxel.text(x + 6, y + 56, f"SPD: {stats.speed}", COLOR_WHITE)
        crit_pct = int(stats.crit_chance * 100)
        pyxel.text(x + 6, y + 66, f"CRIT: {crit_pct}%", COLOR_WHITE)

    def draw_combat_logs(
        self,
        logs: list[str],
        x: int,
        y: int,
        w: int,
        h: int,
        max_entries: int = 5,
    ) -> None:
        """Render recent battle activity feed."""
        self.draw_box(x, y, w, h, bg_col=COLOR_BLACK, border_col=COLOR_GRAY)
        pyxel.text(x + 6, y + 4, "-- Combat Log --", COLOR_YELLOW)

        recent = logs[-max_entries:] if logs else ["Awaiting action..."]
        line_y = y + 14
        for line in recent:
            # Clip or wrap line to fit within width
            disp = line if len(line) <= 52 else line[:49] + "..."
            pyxel.text(x + 6, line_y, disp, COLOR_WHITE)
            line_y += 9
