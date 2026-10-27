"""View switching architecture including CombatView, MapView, and InventoryView."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pyxel

from src.config import (
    COLOR_BLACK,
    COLOR_CYAN,
    COLOR_DARK_BLUE,
    COLOR_GRAY,
    COLOR_GREEN,
    COLOR_LIGHT_BLUE,
    COLOR_NAVY,
    COLOR_ORANGE,
    COLOR_PINK,
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from src.core.game_state import GameMode
from src.core.i18n import t, i18n
from src.ui.renderer import Renderer
from src.ui.views.base import View

if TYPE_CHECKING:
    from src.core.game_state import GameState


# =============================================================================
# BIOME ENEMY SPRITE COORDINATE MAP (Bank 0)
# =============================================================================
class EventsView(View):
    """Renders non-combat room encounters featuring gothic modal framing, treasure scenes, and centered event text."""

    def update(self, game_state: GameState) -> None:
        event = getattr(game_state, "current_event", None)

        if event is None or event.resolved_text:
            # Resolved state
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or Renderer.is_clicked(0, 0, SCREEN_WIDTH,
                                                                                                  SCREEN_HEIGHT):
                pyxel.play(0, 3)
                game_state.current_event = None
                game_state.switch_mode(GameMode.MAP)
        else:
            # Decision state
            box_x, box_y, box_w, box_h = 18, 42, SCREEN_WIDTH - 36, 198
            btn_w, btn_h = 260, 18
            btn_x = SCREEN_WIDTH // 2 - btn_w // 2
            btn_y_start = box_y + 112 + 40

            for i, choice in enumerate(event.choices[:3]):
                is_avail = choice.is_available(game_state)
                btn_y = btn_y_start + i * 22

                # Check for click on button or key press
                clicked = Renderer.is_clicked(btn_x, btn_y, btn_w, btn_h)
                key_pressed = False
                if i == 0 and (pyxel.btnp(pyxel.KEY_1) or pyxel.btnp(pyxel.KEY_KP_1)): key_pressed = True
                if i == 1 and (pyxel.btnp(pyxel.KEY_2) or pyxel.btnp(pyxel.KEY_KP_2)): key_pressed = True
                if i == 2 and (pyxel.btnp(pyxel.KEY_3) or pyxel.btnp(pyxel.KEY_KP_3)): key_pressed = True

                if (clicked or key_pressed) and is_avail:
                    pyxel.play(0, 3)
                    outcome = choice.action_hook(game_state)
                    event.resolved_text = outcome
                    break

    def _draw_event_scene(self, box_x: int, box_y: int, box_w: int, text: str, scene_type: str = "DEFAULT") -> None:
        """Render bespoke scene art: glowing ornate chest or holy sanctuary shrine."""
        fc = pyxel.frame_count
        cy = box_y + 60
        is_shrine = scene_type in ("SHRINE", "ALTAR")
        is_forge = scene_type == "FORGE"
        is_portal = scene_type == "PORTAL"
        is_corpse = scene_type == "CORPSE"

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

        if is_forge:
            # --- FORGE ENCOUNTER ---
            sx = SCREEN_WIDTH // 2
            # Anvil Base
            pyxel.rect(sx - 16, cy + 8, 32, 12, COLOR_NAVY)
            pyxel.rect(sx - 12, cy - 4, 24, 12, COLOR_DARK_BLUE)
            # Anvil Top
            pyxel.rect(sx - 18, cy - 8, 36, 6, COLOR_LIGHT_BLUE)
            pyxel.rect(sx + 18, cy - 6, 8, 4, COLOR_LIGHT_BLUE)  # Horn
            # Glowing slag
            pyxel.rect(sx - 4, cy - 10, 12, 4, COLOR_ORANGE)
            pyxel.rect(sx - 2, cy - 11, 8, 2, COLOR_RED)
            # Embers
            for i in range(5):
                if (fc + i * 10) % 30 < 15:
                    ex = sx - 10 + (i * 8)
                    ey = cy - 15 - ((fc + i * 5) % 20)
                    pyxel.pset(ex, ey, COLOR_YELLOW if i % 2 == 0 else COLOR_ORANGE)
        elif is_portal:
            # --- PORTAL ENCOUNTER ---
            sx = SCREEN_WIDTH // 2
            # Outer Swirl
            for i in range(36):
                angle = (i * 10 + fc * 2) * math.pi / 180
                px = sx + math.cos(angle) * 30
                py = cy - 5 + math.sin(angle) * 20
                pyxel.pset(px, py, COLOR_PURPLE)
            # Inner Swirl
            for i in range(24):
                angle = (i * 15 - fc * 3) * math.pi / 180
                px = sx + math.cos(angle) * 20
                py = cy - 5 + math.sin(angle) * 12
                pyxel.pset(px, py, COLOR_CYAN)
            # Core
            pyxel.elli(sx - 10, cy - 12, 20, 14, COLOR_WHITE)
            pyxel.elli(sx - 6, cy - 9, 12, 8, COLOR_LIGHT_BLUE)
        elif is_corpse:
            # --- CORPSE ENCOUNTER ---
            sx = SCREEN_WIDTH // 2
            # Tangled Briars
            pyxel.circ(sx, cy + 5, 18, COLOR_NAVY)
            for i in range(0, 360, 45):
                angle = i * math.pi / 180
                bx = sx + math.cos(angle) * 15
                by = cy + 5 + math.sin(angle) * 10
                pyxel.line(sx, cy + 5, bx, by, COLOR_GREEN)
                if i % 90 == 0:
                    pyxel.pset(bx, by, COLOR_RED)  # Blood/Roses
            # Silhouette
            pyxel.rect(sx - 8, cy - 5, 16, 10, COLOR_DARK_BLUE)
            pyxel.elli(sx - 5, cy - 12, 10, 8, COLOR_DARK_BLUE)
        elif is_shrine:
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

        event = getattr(game_state, "current_event", None)
        header_title = event.title if event else t("room_encounter_header")
        renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(header_title) // 2, py + 6, header_title,
                           COLOR_YELLOW)

        # =====================================================================
        # 3. BESPOKE SCENE ILLUSTRATION
        # =====================================================================
        event_raw_text = game_state.current_event_text or ""
        scene_type = event.scene_type if event else "DEFAULT"
        self._draw_event_scene(box_x, box_y, box_w, event_raw_text, scene_type)

        # =====================================================================
        # 4. CENTERED NARRATIVE & REWARD TEXT
        # =====================================================================
        is_resolved = event is not None and event.resolved_text != ""
        display_text = event.resolved_text if is_resolved else event_raw_text

        lines = renderer.wrap_text(display_text, max_chars_per_line=34)
        if not lines:
            lines = [header_title]

        txt_start_y = box_y + 112
        for li, line in enumerate(lines[:3]):
            tw = renderer.get_text_width(line)
            tx = SCREEN_WIDTH // 2 - tw // 2

            if is_resolved:
                renderer.draw_text(tx, txt_start_y + li * 12, line, COLOR_YELLOW)
            else:
                is_reward = any(
                    k in line.lower() for k in ("gold", "oro", "heal", "cura", "obtained", "obtenido", "gained"))
                renderer.draw_text(tx, txt_start_y + li * 12, line, COLOR_YELLOW if is_reward else COLOR_WHITE)

        # =====================================================================
        # 5. ACTIONS OR CONTINUE BUTTON
        # =====================================================================
        if event is not None and not is_resolved:
            # Action Controls (Unresolved)
            btn_w, btn_h = 260, 18
            btn_x = SCREEN_WIDTH // 2 - btn_w // 2
            btn_y_start = txt_start_y + 40

            for i, choice in enumerate(event.choices[:3]):
                btn_y = btn_y_start + i * 22
                is_avail = choice.is_available(game_state)

                bg_col = COLOR_NAVY if is_avail else COLOR_BLACK
                border_col = COLOR_LIGHT_BLUE if is_avail else COLOR_GRAY
                text_col = COLOR_WHITE if is_avail else COLOR_GRAY

                pyxel.rect(btn_x, btn_y, btn_w, btn_h, bg_col)
                pyxel.rectb(btn_x, btn_y, btn_w, btn_h, border_col)

                label = f"[{i + 1}] {choice.label}"
                renderer.draw_text(btn_x + 8, btn_y + 6, label, text_col)
        else:
            # Ornate [CONTINUE] Button (Resolved or No Event)
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
