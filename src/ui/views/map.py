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
from src.core.audio import audio
from src.core.i18n import i18n
from src.systems.map_gen import NodeType
from src.ui.renderer import Renderer
from src.ui.views.base import View

if TYPE_CHECKING:
    from src.core.game_state import GameState


# =============================================================================
# BIOME ENEMY SPRITE COORDINATE MAP (Bank 0)
# =============================================================================
class MapView(View):
    """Visualizes the Spire node tree with atmospheric dungeon scenery, dotted trails, and custom icons."""

    def _get_node_pos(self, node, total_floors: int) -> tuple[int, int]:
        v_span = 156
        y_pos = 214 - int((node.floor / max(1, total_floors - 1)) * v_span)

        if node.floor == total_floors - 1:
            return SCREEN_WIDTH // 2, y_pos

        lane_w = (SCREEN_WIDTH - 84) // 3
        base_x = 42 + node.lane * lane_w
        offset_x = int(math.sin(node.floor * 1.7 + node.lane * 2.3) * 5)
        return base_x + offset_x, y_pos

    def update(self, game_state: GameState) -> None:
        available = game_state.map_graph.available_nodes
        floors = game_state.map_graph.floors
        total_floors = len(floors)

        for node in available:
            nx, ny = self._get_node_pos(node, total_floors)
            if Renderer.is_clicked(nx - 8, ny - 8, 16, 26):
                audio.play_sfx( 3)
                game_state.select_map_node(node.id)
                return

        for idx, node in enumerate(available):
            key = getattr(pyxel, f"KEY_{idx + 1}", None)
            if key and pyxel.btnp(key):
                audio.play_sfx( 3)
                game_state.select_map_node(node.id)
                break

    def _draw_node_icon(self, nx: int, ny: int, node_type: NodeType) -> None:
        if node_type == NodeType.COMBAT:
            pyxel.line(nx - 3, ny - 3, nx + 3, ny + 3, COLOR_PINK)
            pyxel.line(nx + 3, ny - 3, nx - 3, ny + 3, COLOR_PINK)
            pyxel.pset(nx, ny, COLOR_WHITE)
            pyxel.pset(nx - 3, ny - 2, COLOR_RED)
            pyxel.pset(nx + 3, ny + 2, COLOR_RED)
            pyxel.pset(nx - 3, ny + 2, COLOR_RED)
            pyxel.pset(nx + 3, ny - 2, COLOR_RED)

        elif node_type == NodeType.ELITE:
            pyxel.rect(nx - 2, ny - 1, 5, 4, COLOR_PURPLE)
            pyxel.pset(nx - 2, ny - 3, COLOR_PURPLE)
            pyxel.pset(nx + 2, ny - 3, COLOR_PURPLE)
            pyxel.pset(nx - 1, ny - 2, COLOR_PINK)
            pyxel.pset(nx + 1, ny - 2, COLOR_PINK)
            pyxel.pset(nx - 1, ny, COLOR_WHITE)
            pyxel.pset(nx + 1, ny, COLOR_WHITE)
            pyxel.pset(nx, ny + 2, COLOR_BLACK)

        elif node_type == NodeType.REST:
            pyxel.pset(nx, ny - 3, COLOR_YELLOW)
            pyxel.pset(nx - 1, ny - 2, COLOR_YELLOW)
            pyxel.pset(nx, ny - 2, COLOR_WHITE)
            pyxel.pset(nx + 1, ny - 2, COLOR_YELLOW)
            pyxel.pset(nx - 2, ny - 1, COLOR_ORANGE)
            pyxel.pset(nx - 1, ny - 1, COLOR_YELLOW)
            pyxel.pset(nx, ny - 1, COLOR_WHITE)
            pyxel.pset(nx + 1, ny - 1, COLOR_YELLOW)
            pyxel.pset(nx + 2, ny - 1, COLOR_ORANGE)
            pyxel.rect(nx - 2, ny, 5, 2, COLOR_RED)
            pyxel.pset(nx - 1, ny, COLOR_ORANGE)
            pyxel.pset(nx, ny, COLOR_YELLOW)
            pyxel.pset(nx + 1, ny, COLOR_ORANGE)
            pyxel.line(nx - 2, ny + 2, nx + 2, ny + 2, COLOR_BROWN)

        elif node_type == NodeType.TREASURE:
            pyxel.rect(nx - 3, ny - 2, 7, 5, COLOR_YELLOW)
            pyxel.rectb(nx - 3, ny - 2, 7, 5, COLOR_BROWN)
            pyxel.line(nx - 3, ny, nx + 3, ny, COLOR_BROWN)
            pyxel.pset(nx, ny, COLOR_WHITE)

        elif node_type == NodeType.SHOP:
            pyxel.pset(nx, ny - 3, COLOR_YELLOW)
            pyxel.rect(nx - 2, ny - 2, 5, 5, COLOR_BROWN)
            pyxel.line(nx - 3, ny, nx + 3, ny + 2, COLOR_PEACH)
            pyxel.pset(nx - 1, ny - 1, COLOR_YELLOW)

        elif node_type == NodeType.EVENT:
            pyxel.line(nx - 1, ny - 3, nx + 1, ny - 3, COLOR_CYAN)
            pyxel.pset(nx + 2, ny - 2, COLOR_CYAN)
            pyxel.pset(nx + 1, ny - 1, COLOR_CYAN)
            pyxel.pset(nx, ny, COLOR_CYAN)
            pyxel.pset(nx, ny + 2, COLOR_CYAN)

        elif node_type == NodeType.BOSS:
            pyxel.rect(nx - 4, ny - 1, 9, 4, COLOR_YELLOW)
            pyxel.pset(nx - 4, ny - 3, COLOR_YELLOW)
            pyxel.pset(nx, ny - 4, COLOR_WHITE)
            pyxel.pset(nx + 4, ny - 3, COLOR_YELLOW)
            pyxel.pset(nx - 2, ny, COLOR_RED)
            pyxel.pset(nx + 2, ny, COLOR_RED)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        box_x, box_y, box_w, box_h = 4, 25, SCREEN_WIDTH - 8, SCREEN_HEIGHT - 28

        # Background scenery
        pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

        pyxel.rect(198, 48, 8, 38, COLOR_NAVY)
        pyxel.rect(214, 48, 8, 38, COLOR_NAVY)
        pyxel.rect(198, 44, 24, 6, COLOR_NAVY)
        pyxel.tri(198, 44, 210, 36, 222, 44, COLOR_NAVY)

        moon_x, moon_y = 208, 48
        pyxel.circ(moon_x, moon_y, 8, COLOR_PEACH)
        pyxel.circ(moon_x - 1, moon_y - 1, 7, COLOR_WHITE)
        pyxel.pset(moon_x + 2, moon_y - 2, COLOR_PEACH)
        pyxel.pset(moon_x - 1, moon_y + 3, COLOR_PEACH)

        for ly in range(40, 230, 16):
            w_left = int(math.sin(ly * 0.08) * 10) + 20
            pyxel.rect(box_x + 2, ly, w_left, 12, COLOR_NAVY)
            pyxel.pset(box_x + w_left + 1, ly + 2, COLOR_PURPLE)
            pyxel.pset(box_x + w_left + 3, ly + 5, COLOR_PINK)

        for ry in range(45, 230, 18):
            w_right = int(math.cos(ry * 0.09) * 8) + 18
            rx = box_x + box_w - 2 - w_right
            pyxel.rect(rx, ry, w_right, 14, COLOR_NAVY)
            pyxel.pset(rx - 2, ry + 4, COLOR_PURPLE)
            pyxel.pset(rx - 4, ry + 8, COLOR_PINK)

        fc = pyxel.frame_count
        motes = [(56, 70), (84, 110), (180, 85), (145, 140), (72, 175), (195, 185)]
        for idx, (mx, my) in enumerate(motes):
            if (fc + idx * 7) % 30 < 15:
                pyxel.pset(mx, my, COLOR_CYAN if idx % 2 == 0 else COLOR_YELLOW)

        pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_DARK_BLUE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_NAVY)

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

        from src.data.biomes import get_biome
        biome = get_biome(game_state.current_biome)

        icon_box_x, icon_box_y = 10, 29
        pyxel.rect(icon_box_x, icon_box_y, 16, 16, COLOR_NAVY)
        pyxel.rectb(icon_box_x, icon_box_y, 16, 16, COLOR_LIGHT_BLUE)

        tx, ty = icon_box_x + 8, icon_box_y + 13
        pyxel.line(tx, ty, tx, ty - 5, COLOR_LIGHT_BLUE)
        pyxel.line(tx - 1, ty - 2, tx - 3, ty - 6, COLOR_LIGHT_BLUE)
        pyxel.line(tx + 1, ty - 2, tx + 3, ty - 6, COLOR_LIGHT_BLUE)
        pyxel.line(tx - 2, ty - 5, tx - 4, ty - 9, COLOR_CYAN)
        pyxel.line(tx, ty - 5, tx, ty - 9, COLOR_CYAN)
        pyxel.line(tx + 2, ty - 5, tx + 4, ty - 9, COLOR_CYAN)

        act_title = f"Act {game_state.act}: {biome.localized_name if biome else 'Aethelgard'}"
        renderer.draw_text(30, 31, act_title, COLOR_YELLOW)
        subtitle = "Elige un camino [1-4]" if i18n.locale == "es" else "Select a path [1-4]"
        renderer.draw_text(30, 40, subtitle, COLOR_WHITE)

        floors = game_state.map_graph.floors
        available_ids = {n.id for n in game_state.map_graph.available_nodes}
        current_id = game_state.map_graph.current_node_id
        total_floors = len(floors)

        for floor in floors:
            for node in floor:
                x1, y1 = self._get_node_pos(node, total_floors)
                for out_id in node.outgoing_ids:
                    out_node = game_state.map_graph.nodes_by_id.get(out_id)
                    if out_node:
                        x2, y2 = self._get_node_pos(out_node, total_floors)
                        is_active_path = (node.id == current_id and out_node.id in available_ids) or \
                                         (current_id is None and node.floor == 0 and out_node.id in available_ids)

                        dot_col = COLOR_YELLOW if is_active_path else COLOR_DARK_BLUE

                        dx = x2 - x1
                        dy = y2 - y1
                        dist = math.hypot(dx, dy)
                        if dist > 0:
                            step = 4.0
                            num_dots = int(dist / step)
                            for s in range(2, num_dots - 1):
                                px = int(x1 + (dx / dist) * (s * step))
                                py = int(y1 + (dy / dist) * (s * step))
                                pyxel.pset(px, py, dot_col)

        option_index = 1
        pulse = (pyxel.frame_count // 6) % 2

        for floor in floors:
            for node in floor:
                nx, ny = self._get_node_pos(node, total_floors)
                is_curr = node.id == current_id
                is_avail = node.id in available_ids

                bg_col = COLOR_NAVY if is_avail else COLOR_BLACK
                border_col = COLOR_YELLOW if is_avail else (COLOR_LIME if is_curr else COLOR_DARK_BLUE)

                pyxel.circ(nx, ny, 6, bg_col)
                pyxel.circb(nx, ny, 6, border_col)

                if is_avail:
                    pyxel.circb(nx, ny, 7, COLOR_YELLOW)
                    if pulse == 1:
                        pyxel.circb(nx, ny, 8, COLOR_ORANGE)

                self._draw_node_icon(nx, ny, node.node_type)

                if is_curr:
                    pyxel.circb(nx, ny, 7, COLOR_LIME)

                if is_avail:
                    badge_x = nx - 6
                    badge_y = ny + 8
                    pyxel.rect(badge_x, badge_y, 13, 9, COLOR_NAVY)
                    pyxel.rectb(badge_x, badge_y, 13, 9, COLOR_YELLOW)
                    num_str = str(option_index)
                    tw = renderer.get_text_width(num_str)
                    renderer.draw_text(badge_x + (13 - tw) // 2 + 1, badge_y + 1, num_str, COLOR_WHITE)
                    option_index += 1

        div_y = box_y + box_h - 16
        pyxel.line(box_x + 2, div_y, box_x + box_w - 3, div_y, COLOR_NAVY)

        is_es = (i18n.locale == "es")
        legend_items = [
            (NodeType.COMBAT, "Lucha" if is_es else "Combat"),
            (NodeType.EVENT, "Evento" if is_es else "Event"),
            (NodeType.TREASURE, "Tesoro" if is_es else "Chest"),
            (NodeType.REST, "Acampar" if is_es else "Rest"),
            (NodeType.ELITE, "Elite" if is_es else "Elite"),
            (NodeType.SHOP, "Tienda" if is_es else "Shop"),
        ]

        leg_x = box_x + 6
        spacing = (box_w - 12) // len(legend_items)
        leg_y = div_y + 7

        for n_type, label in legend_items:
            self._draw_node_icon(leg_x + 4, leg_y, n_type)
            renderer.draw_text(leg_x + 11, leg_y - 3, label, COLOR_WHITE)
            leg_x += spacing
