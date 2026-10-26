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
class EventsView(View):
    """Renders non-combat room encounters featuring gothic modal framing, treasure scenes, and centered event text."""

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or Renderer.is_clicked(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT):
            pyxel.play(0, 3)
            game_state.switch_mode(GameMode.MAP)

    def _draw_event_scene(self, box_x: int, box_y: int, box_w: int, text: str) -> None:
        """Render bespoke scene art: glowing ornate chest or holy sanctuary shrine."""
        fc = pyxel.frame_count
        cy = box_y + 60
        is_shrine = any(k in text.lower() for k in ("shrine", "sanctuary", "santuario", "altar", "pray", "rezar"))

        # Cobblestone ground at bottom of art frame
        ground_y = cy + 18
        pyxel.rect(box_x + 4, ground_y, box_w - 8, 22, COLOR_DARK_BLUE)
        for gx in range(box_x + 8, box_x + box_w - 12, 12):
            pyxel.line(gx, ground_y + 4, gx + 6, ground_y + 4, COLOR_NAVY)
            pyxel.line(gx + 6, ground_y + 11, gx + 11, ground_y + 11, COLOR_NAVY)

        # Ruined stone columns in background
        col_x_list = [box_x + 16, box_x + 36, box_x + box_w - 48, box_x + box_w - 28]
        for col_x in col_x_list:
            pyxel.rect(col_x, cy - 26, 12, 44, COLOR_NAVY)
            for my in range(cy - 22, cy + 18, 7):
                pyxel.line(col_x, my, col_x + 11, my, COLOR_DARK_BLUE)
                pyxel.pset(col_x + ((my // 3) % 8), my + 2, COLOR_LIGHT_BLUE)

        if is_shrine:
            # --- SANCTUARY / SHRINE ENCOUNTER ---
            sx = SCREEN_WIDTH // 2
            # Stone Altar Base
            pyxel.rect(sx - 24, cy + 4, 48, 16, COLOR_NAVY)
            pyxel.rectb(sx - 24, cy + 4, 48, 16, COLOR_LIGHT_BLUE)
            # Glowing Runestone Monolith
            pyxel.rect(sx - 14, cy - 24, 28, 30, COLOR_DARK_BLUE)
            pyxel.rectb(sx - 14, cy - 24, 28, 30, COLOR_CYAN)
            # Carved Holy Cross / Rune
            pyxel.line(sx, cy - 18, sx, cy - 2, COLOR_WHITE)
            pyxel.line(sx - 7, cy - 10, sx + 7, cy - 10, COLOR_WHITE)
            # Altar candles
            for cx in [sx - 20, sx + 20]:
                pyxel.rect(cx, cy - 1, 3, 5, COLOR_WHITE)
                pyxel.pset(cx + 1, cy - 3, COLOR_YELLOW if fc % 4 < 2 else COLOR_ORANGE)
            # Radiant healing aura
            if fc % 6 < 3:
                pyxel.circb(sx, cy - 10, 18, COLOR_CYAN)
        else:
            # --- ORNATE TREASURE CHEST ENCOUNTER ---
            cx = SCREEN_WIDTH // 2 - 24

            # Shadow beneath chest
            pyxel.elli(cx - 12, cy + 16, 72, 8, COLOR_NAVY)

            # Open Chest Lid (angled back)
            pyxel.rect(cx + 2, cy - 8, 44, 13, COLOR_NAVY)
            pyxel.rectb(cx + 2, cy - 8, 44, 13, COLOR_YELLOW)
            pyxel.line(cx + 12, cy - 8, cx + 12, cy + 4, COLOR_YELLOW)
            pyxel.line(cx + 34, cy - 8, cx + 34, cy + 4, COLOR_YELLOW)

            # Chest Base
            pyxel.rect(cx, cy + 6, 48, 16, COLOR_NAVY)
            pyxel.rectb(cx, cy + 6, 48, 16, COLOR_YELLOW)
            pyxel.line(cx, cy + 14, cx + 47, cy + 14, COLOR_DARK_BLUE)
            pyxel.line(cx + 10, cy + 6, cx + 10, cy + 21, COLOR_YELLOW)
            pyxel.line(cx + 37, cy + 6, cx + 37, cy + 21, COLOR_YELLOW)

            # Golden lock & keyhole
            pyxel.rect(cx + 21, cy + 8, 6, 8, COLOR_YELLOW)
            pyxel.pset(cx + 23, cy + 11, COLOR_BLACK)
            pyxel.pset(cx + 24, cy + 11, COLOR_BLACK)
            pyxel.pset(cx + 23, cy + 12, COLOR_BLACK)

            # Overflowing gold pile inside chest
            pyxel.rect(cx + 4, cy + 2, 40, 5, COLOR_YELLOW)
            pyxel.pset(cx + 8, cy + 3, COLOR_ORANGE)
            pyxel.pset(cx + 16, cy + 4, COLOR_ORANGE)
            pyxel.pset(cx + 28, cy + 3, COLOR_ORANGE)

            # Center Ruby Gem
            pyxel.rect(cx + 20, cy + 1, 5, 5, COLOR_RED)
            pyxel.pset(cx + 21, cy + 2, COLOR_WHITE)
            pyxel.pset(cx + 22, cy + 3, COLOR_PINK)

            # Steel sword blade embedded in gold
            pyxel.line(cx + 34, cy + 5, cx + 42, cy - 5, COLOR_WHITE)
            pyxel.line(cx + 35, cy + 4, cx + 43, cy - 4, COLOR_CYAN)
            pyxel.line(cx + 39, cy - 6, cx + 44, cy - 1, COLOR_YELLOW)

            # Piles of gold coins on cobblestone floor
            pyxel.rect(cx - 16, cy + 16, 14, 6, COLOR_YELLOW)
            pyxel.rect(cx - 8, cy + 14, 10, 5, COLOR_YELLOW)
            pyxel.rect(cx + 46, cy + 15, 16, 6, COLOR_YELLOW)
            pyxel.rect(cx + 42, cy + 18, 10, 4, COLOR_YELLOW)
            pyxel.rect(cx + 10, cy + 20, 8, 3, COLOR_YELLOW)
            pyxel.rect(cx + 26, cy + 21, 10, 3, COLOR_YELLOW)
            pyxel.pset(cx - 12, cy + 18, COLOR_ORANGE)
            pyxel.pset(cx - 5, cy + 16, COLOR_ORANGE)
            pyxel.pset(cx + 50, cy + 17, COLOR_ORANGE)
            pyxel.pset(cx + 56, cy + 19, COLOR_ORANGE)

            # Animated golden sparkle stars
            sparkle_coords = [
                (cx - 6, cy - 4), (cx - 14, cy + 8),
                (cx + 14, cy - 12), (cx + 56, cy - 5), (cx + 48, cy + 10)
            ]
            for si, (sx, sy) in enumerate(sparkle_coords):
                if (fc + si * 5) % 18 < 10:
                    pyxel.pset(sx, sy, COLOR_WHITE)
                    pyxel.pset(sx - 1, sy, COLOR_YELLOW)
                    pyxel.pset(sx + 1, sy, COLOR_YELLOW)
                    pyxel.pset(sx, sy - 1, COLOR_YELLOW)
                    pyxel.pset(sx, sy + 1, COLOR_YELLOW)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        box_x, box_y, box_w, box_h = 18, 42, SCREEN_WIDTH - 36, 198

        # =====================================================================
        # 1. OUTER MODAL FRAME & GOTHIC CORNER ACCENTS
        # =====================================================================
        pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)
        pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_LIGHT_BLUE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_NAVY)

        # Ornate Corner Crosses
        for cx, cy in [
            (box_x + 1, box_y + 1),
            (box_x + box_w - 2, box_y + 1),
            (box_x + 1, box_y + box_h - 2),
            (box_x + box_w - 2, box_y + box_h - 2),
        ]:
            pyxel.pset(cx, cy, COLOR_LIGHT_BLUE)
            pyxel.pset(cx - 1, cy, COLOR_DARK_BLUE)
            pyxel.pset(cx + 1, cy, COLOR_DARK_BLUE)
            pyxel.pset(cx, cy - 1, COLOR_DARK_BLUE)
            pyxel.pset(cx, cy + 1, COLOR_DARK_BLUE)

        # =====================================================================
        # 2. HEADER BANNER PLAQUE (-- Room Encounter --)
        # =====================================================================
        pw, ph = 184, 18
        px = (SCREEN_WIDTH - pw) // 2
        py = box_y + 8

        renderer.draw_box(px, py, pw, ph, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE)
        pyxel.rectb(px + 1, py + 1, pw - 2, ph - 2, COLOR_NAVY)

        # Corner ticks on Plaque
        pyxel.line(px + 3, py + 3, px + 6, py + 3, COLOR_LIGHT_BLUE)
        pyxel.line(px + 3, py + 3, px + 3, py + 6, COLOR_LIGHT_BLUE)
        pyxel.line(px + pw - 4, py + 3, px + pw - 7, py + 3, COLOR_LIGHT_BLUE)
        pyxel.line(px + pw - 4, py + 3, px + pw - 4, py + 6, COLOR_LIGHT_BLUE)

        # Star emblems on left & right
        for star_x in [px + 10, px + pw - 12]:
            pyxel.pset(star_x, py + 9, COLOR_WHITE)
            pyxel.pset(star_x - 1, py + 9, COLOR_CYAN)
            pyxel.pset(star_x + 1, py + 9, COLOR_CYAN)
            pyxel.pset(star_x, py + 8, COLOR_CYAN)
            pyxel.pset(star_x, py + 10, COLOR_CYAN)

        header_title = t("room_encounter_header")
        renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(header_title) // 2, py + 6, header_title, COLOR_YELLOW)

        # =====================================================================
        # 3. BESPOKE SCENE ILLUSTRATION
        # =====================================================================
        event_raw_text = game_state.current_event_text or ""
        self._draw_event_scene(box_x, box_y, box_w, event_raw_text)

        # =====================================================================
        # 4. CENTERED NARRATIVE & REWARD TEXT
        # =====================================================================
        lines = renderer.wrap_text(event_raw_text, max_chars_per_line=34)
        if not lines:
            lines = [t("room_encounter_header")]

        txt_start_y = box_y + 112
        for li, line in enumerate(lines[:3]):
            tw = renderer.get_text_width(line)
            tx = SCREEN_WIDTH // 2 - tw // 2
            # Highlight rewards line
            is_reward = any(k in line.lower() for k in ("gold", "oro", "heal", "cura", "obtained", "obtenido", "gained"))
            renderer.draw_text(tx, txt_start_y + li * 12, line, COLOR_YELLOW if is_reward else COLOR_WHITE)

        # =====================================================================
        # 5. ORNATE [CONTINUE] BUTTON WITH CORNER BRACKETS
        # =====================================================================
        btn_w, btn_h = 92, 18
        btn_x = (SCREEN_WIDTH - btn_w) // 2
        btn_y = box_y + box_h - 30

        pyxel.rect(btn_x, btn_y, btn_w, btn_h, COLOR_BLACK)
        pyxel.rectb(btn_x, btn_y, btn_w, btn_h, COLOR_LIGHT_BLUE)

        # Decorative Corner Ticks protruding from button
        pyxel.line(btn_x - 2, btn_y - 2, btn_x + 3, btn_y - 2, COLOR_LIGHT_BLUE)
        pyxel.line(btn_x - 2, btn_y - 2, btn_x - 2, btn_y + 3, COLOR_LIGHT_BLUE)

        pyxel.line(btn_x + btn_w + 1, btn_y - 2, btn_x + btn_w - 4, btn_y - 2, COLOR_LIGHT_BLUE)
        pyxel.line(btn_x + btn_w + 1, btn_y - 2, btn_x + btn_w + 1, btn_y + 3, COLOR_LIGHT_BLUE)

        pyxel.line(btn_x - 2, btn_y + btn_h + 1, btn_x + 3, btn_y + btn_h + 1, COLOR_LIGHT_BLUE)
        pyxel.line(btn_x - 2, btn_y + btn_h + 1, btn_x - 2, btn_y + btn_h - 4, COLOR_LIGHT_BLUE)

        pyxel.line(btn_x + btn_w + 1, btn_y + btn_h + 1, btn_x + btn_w - 4, btn_y + btn_h + 1, COLOR_LIGHT_BLUE)
        pyxel.line(btn_x + btn_w + 1, btn_y + btn_h + 1, btn_x + btn_w + 1, btn_y + btn_h - 4, COLOR_LIGHT_BLUE)

        btn_label = "[CONTINUE]" if i18n.locale == "en" else "[CONTINUAR]"
        renderer.draw_text(btn_x + (btn_w - renderer.get_text_width(btn_label)) // 2, btn_y + 6, btn_label, COLOR_WHITE)
