"""View switching architecture including CombatView, MapView, and InventoryView."""

from __future__ import annotations

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
from src.systems.inventory import MAX_BELT_SLOTS, MAX_POUCH_SLOTS
from src.systems.map_gen import NodeType
from src.ui.renderer import Renderer

if TYPE_CHECKING:
    from src.core.game_state import GameState

# =============================================================================
# BIOME ENEMY SPRITE COORDINATE MAP (Bank 0)
# =============================================================================
ENEMY_SPRITE_COORDS: dict[str, tuple[int, int]] = {
    # Act 1A: The Wilted Arboretum (y=48)
    "thornvein_creeper": (0, 48),
    "spore_pod": (16, 48),
    "bramble_hound": (32, 48),
    "rotting_woodwose": (48, 48),
    "mandragora_matron": (64, 48),
    "corpse_treant": (80, 48),
    "malignant_belladonna": (96, 48),
    "verdant_abomination": (112, 48),

    # Act 1B: The Desecrated Cathedral (y=64)
    "cathedral_imp": (0, 64),
    "possessed_grimoire": (16, 64),
    "candelabra_fiend": (32, 64),
    "penitent_zealot": (48, 64),
    "belltower_gargoyle": (64, 64),
    "inquisitor_automaton": (80, 64),
    "blind_archbishop": (96, 64),
    "chorus_of_damned": (112, 64),

    # Act 2A: The Drowned Ossuary (y=80)
    "mire_ghoul": (0, 80),
    "drowned_skulls": (16, 80),
    "leech_husk": (32, 80),
    "crypt_lurker": (48, 80),
    "tide_gravekeeper": (64, 80),
    "carrion_behemoth": (80, 80),
    "drowned_patriarch": (96, 80),
    "scylla_bone_weaver": (112, 80),

    # Act 2B: The Foundry of Torment (y=96)
    "slag_homunculus": (0, 96),
    "cinder_sprite": (16, 96),
    "clockwork_flayer": (32, 96),
    "ashen_overseer": (48, 96),
    "furnace_warden": (64, 96),
    "retching_alchemist": (80, 96),
    "ironforge_tyrant": (96, 96),
    "molten_sovereign": (112, 96),

    # Act 3A: The Astral Observatory (y=112)
    "void_mirror": (0, 112),
    "stareater_wisp": (16, 112),
    "comet_stalker": (32, 112),
    "celestial_hermit": (48, 112),
    "rift_warden": (64, 112),
    "null_singularity": (80, 112),
    "chronomancer_praetor": (96, 112),
    "devouring_constellation": (112, 112),

    # Act 3B: The Blood Sanctum (y=128)
    "sanguine_thrall": (0, 128),
    "crimson_gargoyle": (16, 128),
    "hemomancer_acolyte": (32, 128),
    "flayed_duelist": (48, 128),
    "baroness_vespera": (64, 128),
    "amalgam_of_veins": (80, 128),
    "high_lord_carmilla": (96, 128),
    "blood_god_avatar": (112, 128),
}

SPEED_INTERVALS = [15, 7, 2]
SPEED_LABELS = ["1x", "2x", "3x"]


@dataclass
class CombatPopup:
    x: int
    y: int
    text: str
    color: int
    lifetime: int = 18


class View:
    """Base abstract interface for game screens."""

    def update(self, game_state: GameState) -> None:
        pass

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pass


class BiomeSelectView(View):
    """Renders the biome route selection screen."""

    def update(self, game_state: GameState) -> None:
        from src.data.biomes import ACT_BIOMES
        if game_state.act not in ACT_BIOMES:
            return

        biome_a_id, biome_b_id = ACT_BIOMES[game_state.act]

        if pyxel.btnp(pyxel.KEY_1) or Renderer.is_clicked(8, 42, 116, 172):
            pyxel.play(0, 3)  # SND_CLICK
            game_state.advance_act(target_biome_id=biome_a_id)
        elif pyxel.btnp(pyxel.KEY_2) or Renderer.is_clicked(132, 42, 116, 172):
            pyxel.play(0, 3)  # SND_CLICK
            game_state.advance_act(target_biome_id=biome_b_id)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)

        # Header
        renderer.draw_box(0, 12, SCREEN_WIDTH, 20, bg_col=COLOR_NAVY, border_col=COLOR_GRAY)
        title = t("biome_select_header", act=game_state.act)
        renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(title) // 2, 18, title, COLOR_YELLOW)

        from src.data.biomes import ACT_BIOMES, get_biome
        if game_state.act not in ACT_BIOMES:
            return

        biome_a_id, biome_b_id = ACT_BIOMES[game_state.act]
        biome_a = get_biome(biome_a_id)
        biome_b = get_biome(biome_b_id)

        biomes = [(biome_a, 8), (biome_b, 132)]

        for biome, x_offset in biomes:
            if not biome:
                continue

            # Card
            renderer.draw_box(x_offset, 42, 116, 172, bg_col=COLOR_DARK_BLUE, border_col=biome.ambient_color)

            # Dynamic Card Layout
            curr_y = 42 + 8
            renderer.draw_text(x_offset + 6, curr_y, biome.localized_name[:17], COLOR_YELLOW)
            curr_y += 11

            # Tags
            for tag_line in renderer.wrap_text(biome.localized_tags, max_chars_per_line=18):
                renderer.draw_text(x_offset + 6, curr_y, tag_line, 3)
                curr_y += 9
            curr_y += 3

            # Description
            for desc_line in renderer.wrap_text(biome.localized_description, max_chars_per_line=18):
                renderer.draw_text(x_offset + 6, curr_y, desc_line, COLOR_WHITE)
                curr_y += 9
            curr_y += 4

            # Threats
            renderer.draw_text(x_offset + 6, curr_y, t("biome_threats"), COLOR_ORANGE)
            curr_y += 9

            from src.entities.enemy import ENEMY_CATALOG
            for e_id in biome.basic_enemies[:2]:
                e_name = ENEMY_CATALOG[e_id].localized_name[:16] if e_id in ENEMY_CATALOG else e_id.replace('_',
                                                                                                            ' ').title()[
                    :16]
                renderer.draw_text(x_offset + 8, curr_y, f"- {e_name}", COLOR_GRAY)
                curr_y += 9
            curr_y += 4

            # Bosses
            renderer.draw_text(x_offset + 6, curr_y, t("biome_bosses"), 14)
            curr_y += 9
            for b_id in biome.bosses:
                b_name = ENEMY_CATALOG[b_id].localized_name[:16] if b_id in ENEMY_CATALOG else b_id.replace('_',
                                                                                                            ' ').title()[
                    :16]
                renderer.draw_text(x_offset + 8, curr_y, f"- {b_name}", COLOR_GRAY)
                curr_y += 9

            renderer.draw_button(x_offset + 10, 42 + 172 - 22, 96, 16, t("btn_choose_route"), bg_col=COLOR_BLACK,
                                 text_col=COLOR_WHITE)


class MapView(View):
    """Visualizes the Spire node tree with atmospheric dungeon scenery, dotted trails, and custom icons."""

    def _get_node_pos(self, node, total_floors: int) -> tuple[int, int]:
        """Compute organic x, y position with natural trail curves."""
        # Vertical span from y=58 (boss) down to y=214 (starting floor)
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

        # Click detection covering both the circular medallion and the number badge beneath it
        for node in available:
            nx, ny = self._get_node_pos(node, total_floors)
            if Renderer.is_clicked(nx - 8, ny - 8, 16, 26):
                pyxel.play(0, 3)
                game_state.select_map_node(node.id)
                return

        # Numeric hotkeys [1..4]
        for idx, node in enumerate(available):
            key = getattr(pyxel, f"KEY_{idx + 1}", None)
            if key and pyxel.btnp(key):
                pyxel.play(0, 3)
                game_state.select_map_node(node.id)
                break

    def _draw_node_icon(self, nx: int, ny: int, node_type: NodeType) -> None:
        """Render distinct thematic pixel symbols inside the medallion circle."""
        if node_type == NodeType.COMBAT:
            # Crossed pink/red blades
            pyxel.line(nx - 3, ny - 3, nx + 3, ny + 3, COLOR_PINK)
            pyxel.line(nx + 3, ny - 3, nx - 3, ny + 3, COLOR_PINK)
            pyxel.pset(nx, ny, COLOR_WHITE)
            pyxel.pset(nx - 3, ny - 2, COLOR_RED)
            pyxel.pset(nx + 3, ny + 2, COLOR_RED)
            pyxel.pset(nx - 3, ny + 2, COLOR_RED)
            pyxel.pset(nx + 3, ny - 2, COLOR_RED)

        elif node_type == NodeType.ELITE:
            # Purple horned demon crest
            pyxel.rect(nx - 2, ny - 1, 5, 4, COLOR_PURPLE)
            pyxel.pset(nx - 2, ny - 3, COLOR_PURPLE)
            pyxel.pset(nx + 2, ny - 3, COLOR_PURPLE)
            pyxel.pset(nx - 1, ny - 2, COLOR_PINK)
            pyxel.pset(nx + 1, ny - 2, COLOR_PINK)
            pyxel.pset(nx - 1, ny, COLOR_WHITE)
            pyxel.pset(nx + 1, ny, COLOR_WHITE)
            pyxel.pset(nx, ny + 2, COLOR_BLACK)

        elif node_type == NodeType.REST:
            # Campfire flame
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
            # Golden treasure chest
            pyxel.rect(nx - 3, ny - 2, 7, 5, COLOR_YELLOW)
            pyxel.rectb(nx - 3, ny - 2, 7, 5, COLOR_BROWN)
            pyxel.line(nx - 3, ny, nx + 3, ny, COLOR_BROWN)
            pyxel.pset(nx, ny, COLOR_WHITE)

        elif node_type == NodeType.SHOP:
            # Leather coin pouch
            pyxel.pset(nx, ny - 3, COLOR_YELLOW)
            pyxel.rect(nx - 2, ny - 2, 5, 5, COLOR_BROWN)
            pyxel.line(nx - 3, ny, nx + 3, ny + 2, COLOR_PEACH)
            pyxel.pset(nx - 1, ny - 1, COLOR_YELLOW)

        elif node_type == NodeType.EVENT:
            # Cyan mystery rune
            pyxel.line(nx - 1, ny - 3, nx + 1, ny - 3, COLOR_CYAN)
            pyxel.pset(nx + 2, ny - 2, COLOR_CYAN)
            pyxel.pset(nx + 1, ny - 1, COLOR_CYAN)
            pyxel.pset(nx, ny, COLOR_CYAN)
            pyxel.pset(nx, ny + 2, COLOR_CYAN)

        elif node_type == NodeType.BOSS:
            # Golden Crown of Aethelgard
            pyxel.rect(nx - 4, ny - 1, 9, 4, COLOR_YELLOW)
            pyxel.pset(nx - 4, ny - 3, COLOR_YELLOW)
            pyxel.pset(nx, ny - 4, COLOR_WHITE)
            pyxel.pset(nx + 4, ny - 3, COLOR_YELLOW)
            pyxel.pset(nx - 2, ny, COLOR_RED)
            pyxel.pset(nx + 2, ny, COLOR_RED)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        box_x, box_y, box_w, box_h = 4, 25, SCREEN_WIDTH - 8, SCREEN_HEIGHT - 28

        # =====================================================================
        # 1. MOOD SCENERY & BACKGROUND ART
        # =====================================================================
        pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

        # Distant ruins / stone arches in top-right
        pyxel.rect(198, 48, 8, 38, COLOR_NAVY)
        pyxel.rect(214, 48, 8, 38, COLOR_NAVY)
        pyxel.rect(198, 44, 24, 6, COLOR_NAVY)
        pyxel.tri(198, 44, 210, 36, 222, 44, COLOR_NAVY)

        # Pale glowing moon
        moon_x, moon_y = 208, 48
        pyxel.circ(moon_x, moon_y, 8, COLOR_PEACH)
        pyxel.circ(moon_x - 1, moon_y - 1, 7, COLOR_WHITE)
        pyxel.pset(moon_x + 2, moon_y - 2, COLOR_PEACH)
        pyxel.pset(moon_x - 1, moon_y + 3, COLOR_PEACH)

        # Forest canopy silhouettes on sides
        for ly in range(40, 230, 16):
            w_left = int(math.sin(ly * 0.08) * 10) + 20
            pyxel.rect(box_x + 2, ly, w_left, 12, COLOR_NAVY)
            # Foliage leaf accents
            pyxel.pset(box_x + w_left + 1, ly + 2, COLOR_PURPLE)
            pyxel.pset(box_x + w_left + 3, ly + 5, COLOR_PINK)

        for ry in range(45, 230, 18):
            w_right = int(math.cos(ry * 0.09) * 8) + 18
            rx = box_x + box_w - 2 - w_right
            pyxel.rect(rx, ry, w_right, 14, COLOR_NAVY)
            pyxel.pset(rx - 2, ry + 4, COLOR_PURPLE)
            pyxel.pset(rx - 4, ry + 8, COLOR_PINK)

        # Twinkling star / firefly particles
        fc = pyxel.frame_count
        motes = [(56, 70), (84, 110), (180, 85), (145, 140), (72, 175), (195, 185)]
        for idx, (mx, my) in enumerate(motes):
            if (fc + idx * 7) % 30 < 15:
                pyxel.pset(mx, my, COLOR_CYAN if idx % 2 == 0 else COLOR_YELLOW)

        # Double gothic border
        pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_DARK_BLUE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_NAVY)

        # Decorative Corner Crosses
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
        # 2. BIOME HEADER
        # =====================================================================
        from src.data.biomes import get_biome
        biome = get_biome(game_state.current_biome)

        # Left Biome Icon Badge (Rounded box with stylized tree)
        icon_box_x, icon_box_y = 10, 29
        pyxel.rect(icon_box_x, icon_box_y, 16, 16, COLOR_NAVY)
        pyxel.rectb(icon_box_x, icon_box_y, 16, 16, COLOR_LIGHT_BLUE)

        # Stylized Ancient Tree
        tx, ty = icon_box_x + 8, icon_box_y + 13
        pyxel.line(tx, ty, tx, ty - 5, COLOR_LIGHT_BLUE)
        pyxel.line(tx - 1, ty - 2, tx - 3, ty - 6, COLOR_LIGHT_BLUE)
        pyxel.line(tx + 1, ty - 2, tx + 3, ty - 6, COLOR_LIGHT_BLUE)
        pyxel.line(tx - 2, ty - 5, tx - 4, ty - 9, COLOR_CYAN)
        pyxel.line(tx, ty - 5, tx, ty - 9, COLOR_CYAN)
        pyxel.line(tx + 2, ty - 5, tx + 4, ty - 9, COLOR_CYAN)

        # Header Titles
        act_title = f"Act {game_state.act}: {biome.localized_name if biome else 'Aethelgard'}"
        renderer.draw_text(30, 31, act_title, COLOR_YELLOW)
        subtitle = "Elige un camino [1-4]" if i18n.locale == "es" else "Select a path [1-4]"
        renderer.draw_text(30, 40, subtitle, COLOR_WHITE)

        # =====================================================================
        # 3. DOTTED PATH CONNECTIONS
        # =====================================================================
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

                        # Dotted stepped lines
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

        # =====================================================================
        # 4. CIRCULAR MEDALLION NODES & SELECTION PILLS
        # =====================================================================
        option_index = 1
        pulse = (pyxel.frame_count // 6) % 2

        for floor in floors:
            for node in floor:
                nx, ny = self._get_node_pos(node, total_floors)
                is_curr = node.id == current_id
                is_avail = node.id in available_ids

                # Node Base Medallion
                bg_col = COLOR_NAVY if is_avail else COLOR_BLACK
                border_col = COLOR_YELLOW if is_avail else (COLOR_LIME if is_curr else COLOR_DARK_BLUE)

                pyxel.circ(nx, ny, 6, bg_col)
                pyxel.circb(nx, ny, 6, border_col)

                # Available Node Golden Glow
                if is_avail:
                    pyxel.circb(nx, ny, 7, COLOR_YELLOW)
                    if pulse == 1:
                        pyxel.circb(nx, ny, 8, COLOR_ORANGE)

                # Render Node Icon
                self._draw_node_icon(nx, ny, node.node_type)

                # Hero Position Halo
                if is_curr:
                    pyxel.circb(nx, ny, 7, COLOR_LIME)

                # Selection Pill Box under Available Node
                if is_avail:
                    badge_x = nx - 6
                    badge_y = ny + 8
                    pyxel.rect(badge_x, badge_y, 13, 9, COLOR_NAVY)
                    pyxel.rectb(badge_x, badge_y, 13, 9, COLOR_YELLOW)
                    num_str = str(option_index)
                    tw = renderer.get_text_width(num_str)
                    renderer.draw_text(badge_x + (13 - tw) // 2 + 1, badge_y + 1, num_str, COLOR_WHITE)
                    option_index += 1

        # =====================================================================
        # 5. BOTTOM LEGEND BAR
        # =====================================================================
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
            # Draw compact symbol
            self._draw_node_icon(leg_x + 4, leg_y, n_type)
            # Draw text
            renderer.draw_text(leg_x + 11, leg_y - 3, label, COLOR_WHITE)
            leg_x += spacing


class CombatView(View):
    """Renders active auto-battle arena, sprites, tick gauges, visual effects, and battle logs."""

    def __init__(self) -> None:
        self.popups: list[CombatPopup] = []
        self.player_flash: int = 0
        self.enemy_flash: int = 0
        self.shake_frames: int = 0
        self.speed_index: int = 0

    def _detect_combat_deltas(self, game_state: GameState, old_p_hp: int, old_e_hp: int) -> None:
        if game_state.combat is None:
            return

        combat = game_state.combat
        new_p_hp = game_state.player.current_hp
        new_e_hp = combat.enemy.current_hp

        # Player took damage
        if new_p_hp < old_p_hp:
            dmg = old_p_hp - new_p_hp
            is_crit = any("CRIT" in log or "CRÍTICO" in log for log in combat.combat_logs[-2:])
            txt = f"-{dmg}!" if is_crit else f"-{dmg}"
            col = COLOR_RED if is_crit else COLOR_PEACH
            self.popups.append(CombatPopup(x=104, y=26, text=txt, color=col))
            self.player_flash = 3
            if is_crit:
                self.shake_frames = 5

        # Player was healed
        elif new_p_hp > old_p_hp:
            heal = new_p_hp - old_p_hp
            self.popups.append(CombatPopup(x=104, y=26, text=f"+{heal}", color=COLOR_LIME))

        # Enemy took damage
        if new_e_hp < old_e_hp:
            dmg = old_e_hp - new_e_hp
            is_crit = any("CRIT" in log or "CRÍTICO" in log for log in combat.combat_logs[-2:])
            txt = f"-{dmg}!" if is_crit else f"-{dmg}"
            col = COLOR_YELLOW if is_crit else COLOR_WHITE
            self.popups.append(CombatPopup(x=224, y=26, text=txt, color=col))
            self.enemy_flash = 3
            if is_crit:
                self.shake_frames = 6

    def update(self, game_state: GameState) -> None:
        if game_state.combat is None:
            self.popups.clear()
            return

        # Floating Popups physics
        for p in self.popups:
            if p.lifetime % 2 == 0:
                p.y -= 1
            p.lifetime -= 1
        self.popups = [p for p in self.popups if p.lifetime > 0]

        # Speed toggle: button click at (214, 106, 32, 10) or [Z] key
        if pyxel.btnp(pyxel.KEY_Z) or Renderer.is_clicked(214, 106, 32, 10):
            self.speed_index = (self.speed_index + 1) % len(SPEED_INTERVALS)
            pyxel.play(0, 3)
            return

        speed_frames = SPEED_INTERVALS[self.speed_index]

        # Advance combat
        if pyxel.btnp(pyxel.KEY_SPACE) or (pyxel.frame_count % speed_frames == 0) or Renderer.is_clicked(0, 166,
                                                                                                         SCREEN_WIDTH,
                                                                                                         82) or Renderer.is_clicked(
                0, 20, 210, 88):
            old_p_hp = game_state.player.current_hp
            old_e_hp = game_state.combat.enemy.current_hp
            game_state.update_combat()
            self._detect_combat_deltas(game_state, old_p_hp, old_e_hp)

        if game_state.combat is None:
            return

        # In-combat quick belt triggers: Keys [1, 2, 3] or Tap
        slot_positions = [40, 110, 180]
        for idx, key in enumerate((pyxel.KEY_1, pyxel.KEY_2, pyxel.KEY_3)):
            bx = slot_positions[idx] if idx < len(slot_positions) else 40 + idx * 70
            if pyxel.btnp(key) or Renderer.is_clicked(bx, 130, 66, 18):
                old_p_hp = game_state.player.current_hp
                if game_state.player.inventory.use_belt_item(idx, game_state.player):
                    pyxel.play(1, 2)
                    game_state.combat.combat_logs.append(
                        t("combat_belt_use", player=game_state.player.name, slot=idx + 1)
                    )
                    self._detect_combat_deltas(game_state, old_p_hp, game_state.combat.enemy.current_hp)

        # Active Abilities: Keys [4, 5] or Tap
        for idx, key in enumerate((pyxel.KEY_4, pyxel.KEY_5)):
            x_pos = 46 + idx * 95
            if (pyxel.btnp(key) or Renderer.is_clicked(x_pos - 4, 146, 90, 14)) and idx < len(
                    game_state.player.abilities.active):
                if game_state.combat.ability_cooldown <= 0:
                    game_state.combat.queued_ability = game_state.player.abilities.active[idx]
                    game_state.combat.ability_cooldown = 3
                    game_state.combat.combat_logs.append(
                        t("combat_queued", ability=game_state.player.abilities.active[idx].name))
                else:
                    game_state.combat.combat_logs.append(
                        t("combat_cooldown", cooldown=game_state.combat.ability_cooldown))

    def _get_enemy_sprite(self, enemy: Enemy) -> tuple[int, int]:
        """Resolve Bank 0 (u, v) tile coordinates for any enemy instance."""
        arch_id = getattr(enemy, "archetype_id", None)
        if arch_id and arch_id in ENEMY_SPRITE_COORDS:
            return ENEMY_SPRITE_COORDS[arch_id]

        name_lower = enemy.name.lower()
        for key, coords in ENEMY_SPRITE_COORDS.items():
            if key.replace("_", " ") in name_lower:
                return coords

        tier_val = enemy.tier.value if hasattr(enemy.tier, "value") else int(enemy.tier)
        if tier_val >= 4 or "lich" in name_lower or "dragon" in name_lower:
            return (48, 0)
        if "goblin" in name_lower or "scavenger" in name_lower or "cultist" in name_lower:
            return (32, 0)
        return (16, 0)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        # Screen Shake
        if self.shake_frames > 0:
            sx = random.randint(-2, 2)
            sy = random.randint(-2, 2)
            pyxel.camera(sx, sy)
            self.shake_frames -= 1
        else:
            pyxel.camera(0, 0)

        renderer.draw_hud(game_state.player, game_state.floor)

        if game_state.combat is None:
            pyxel.camera(0, 0)
            return

        combat = game_state.combat

        # Player Stat Panel
        renderer.draw_stat_panel(
            x=10,
            y=28,
            w=112,
            h=78,
            title=f"{game_state.player.name}",
            stats=game_state.player.effective_stats,
            hp=game_state.player.current_hp,
            max_hp=game_state.player.max_hp,
            color_scheme=COLOR_DARK_BLUE,
            statuses=game_state.player.statuses,
        )

        # Hero sprite (with Hit Flash)
        sprite_map = {
            "warrior": (0, 0),
            "rogue": (0, 32),
            "mage": (16, 32),
        }
        pu, pv = sprite_map.get(game_state.player.class_id, (0, 0))
        if self.player_flash > 0:
            self.player_flash -= 1
            for c in range(16):
                pyxel.pal(c, COLOR_WHITE)
            pyxel.blt(100, 32, 0, pu, pv, 16, 16, 0)
            pyxel.pal()
        else:
            pyxel.blt(100, 32, 0, pu, pv, 16, 16, 0)

        # Enemy Stat Panel
        enemy_display = combat.enemy.display_name if len(
            combat.enemy.display_name) <= 14 else combat.enemy.display_name[:13] + "."
        renderer.draw_stat_panel(
            x=134,
            y=28,
            w=112,
            h=78,
            title=enemy_display,
            stats=combat.enemy.effective_stats,
            hp=combat.enemy.current_hp,
            max_hp=combat.enemy.max_hp,
            color_scheme=COLOR_RED if combat.enemy.tier.value >= 3 else COLOR_NAVY,
            statuses=combat.enemy.statuses,
        )

        # Dynamic Biome Enemy Sprite (with Hit Flash)
        eu, ev = self._get_enemy_sprite(combat.enemy)
        if self.enemy_flash > 0:
            self.enemy_flash -= 1
            for c in range(16):
                pyxel.pal(c, COLOR_WHITE)
            pyxel.blt(224, 32, 0, eu, ev, 16, 16, 0)
            pyxel.pal()
        else:
            pyxel.blt(224, 32, 0, eu, ev, 16, 16, 0)

        # Action Tick Meters
        renderer.draw_text(10, 110, t("tick_gauges"), COLOR_YELLOW)
        renderer.draw_bar(10, 118, 112, 5, combat.player_gauge, ACTION_THRESHOLD, fill_col=COLOR_LIGHT_BLUE,
                          bg_col=COLOR_BLACK)
        renderer.draw_bar(134, 118, 112, 5, combat.enemy_gauge, ACTION_THRESHOLD, fill_col=COLOR_ORANGE,
                          bg_col=COLOR_BLACK)

        # Battle Speed Toggle Button
        renderer.draw_button(214, 106, 32, 10, f"[{SPEED_LABELS[self.speed_index]}]", bg_col=COLOR_BLACK,
                             text_col=COLOR_YELLOW)

        # Floating Combat Popups
        for pop in self.popups:
            renderer.draw_text(pop.x, pop.y, pop.text, pop.color)

        # In-Combat Quick Belt Display
        renderer.draw_box(10, 126, SCREEN_WIDTH - 20, 36, bg_col=COLOR_NAVY, border_col=COLOR_DARK_BLUE)
        renderer.draw_text(14, 129, t("belt"), COLOR_YELLOW)
        inv = game_state.player.inventory

        slot_positions = [40, 110, 180]
        for b_idx in range(MAX_BELT_SLOTS):
            bx = slot_positions[b_idx] if b_idx < len(slot_positions) else 40 + b_idx * 70
            b_item = inv.belt[b_idx]
            name = b_item.localized_name[:9] if b_item else t("empty_slot_short")

            renderer.draw_text(bx, 129, f"[{b_idx + 1}] {name}", COLOR_WHITE if b_item else COLOR_GRAY)
            if b_item:
                renderer.draw_text(bx, 137, f"+{b_item.heal_amount}HP", COLOR_LIME)

        # Abilities Hotkeys
        renderer.draw_text(14, 148, t("skills"), COLOR_YELLOW)
        for a_idx, active_ab in enumerate(game_state.player.abilities.active):
            x_pos = 46 + a_idx * 95
            key_label = "4" if a_idx == 0 else "5"
            queued_marker = "*" if game_state.combat and game_state.combat.queued_ability == active_ab else " "
            renderer.draw_text(x_pos, 148, f"[{key_label}]{queued_marker} {active_ab.name[:14]}", COLOR_LIME)

        # Combat Activity Feed
        renderer.draw_combat_logs(
            logs=combat.combat_logs,
            x=10,
            y=166,
            w=SCREEN_WIDTH - 20,
            h=82,
            max_entries=7,
        )

        # Reset camera after drawing
        pyxel.camera(0, 0)


class InventoryView(View):
    """Renders 6+2 Equipment, 10-slot Pouch, and 3-slot Belt."""

    def __init__(self) -> None:
        self.active_pane: str = "POUCH"
        self.pouch_cursor: int = 0
        self.equip_cursor: int = 0
        self.feedback_message: str = ""
        self.feedback_success: bool = False

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.KEY_I) or Renderer.is_clicked(SCREEN_WIDTH - 60, 228, 50,
                                                                                          16):
            game_state.toggle_inventory()
            return

        if pyxel.btnp(pyxel.KEY_TAB) or Renderer.is_clicked(10, 32, 100, 10):
            self.active_pane = "EQUIPMENT"
            self.feedback_message = ""
        elif Renderer.is_clicked(10, 130, 100, 10):
            self.active_pane = "POUCH"
            self.feedback_message = ""

        up_pressed = pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W)
        down_pressed = pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btnp(pyxel.KEY_S)

        from src.systems.inventory import ConsumableItem, EquipmentItem, EquipSlot
        inv = game_state.player.inventory

        # Equipment click inspection
        for i in range(len(EquipSlot)):
            col = i % 2
            row = i // 2
            x = 10 + col * 118
            y = 44 + row * 12
            if Renderer.is_clicked(x, y, 100, 10):
                self.active_pane = "EQUIPMENT"
                self.equip_cursor = i
                self.feedback_message = ""

        # Pouch click inspection
        for p_idx in range(MAX_POUCH_SLOTS):
            col = p_idx % 2
            row = p_idx // 2
            x = 10 + col * 118
            y = 142 + row * 15
            if Renderer.is_clicked(x, y, 100, 12):
                self.active_pane = "POUCH"
                self.pouch_cursor = p_idx
                self.feedback_message = ""

        if self.active_pane == "POUCH":
            if up_pressed:
                self.pouch_cursor = max(0, self.pouch_cursor - 1)
                self.feedback_message = ""
            elif down_pressed:
                self.pouch_cursor = min(MAX_POUCH_SLOTS - 1, self.pouch_cursor + 1)
                self.feedback_message = ""

            if pyxel.btnp(pyxel.KEY_E) or Renderer.is_clicked(14, 228, 80, 16):
                if self.pouch_cursor < len(inv.pouch):
                    item = inv.pouch[self.pouch_cursor]
                    if isinstance(item, EquipmentItem):
                        success, msg = inv.equip_from_pouch(self.pouch_cursor, game_state.player)
                        self.feedback_message = msg
                        self.feedback_success = success
                        if success:
                            pyxel.play(0, 3)
                    elif isinstance(item, ConsumableItem):
                        target_belt = -1
                        for i in range(MAX_BELT_SLOTS):
                            if inv.belt[i] is None:
                                target_belt = i
                                break
                        if target_belt == -1:
                            target_belt = 0

                        success, msg = inv.assign_pouch_to_belt(self.pouch_cursor, target_belt)
                        self.feedback_message = msg
                        self.feedback_success = success
                        if success:
                            pyxel.play(0, 3)

            if pyxel.btnp(pyxel.KEY_D) or Renderer.is_clicked(160, 228, 46, 16):
                if self.pouch_cursor < len(inv.pouch):
                    success, msg = inv.drop_from_pouch(self.pouch_cursor)
                    self.feedback_message = msg
                    self.feedback_success = success
                    if success:
                        pyxel.play(0, 3)

            # Assign to belt slots
            for idx, key in enumerate((pyxel.KEY_1, pyxel.KEY_2, pyxel.KEY_3)):
                if pyxel.btnp(key) or Renderer.is_clicked(100 + idx * 20, 228, 16, 16):
                    if self.pouch_cursor < len(inv.pouch):
                        success, msg = inv.assign_pouch_to_belt(self.pouch_cursor, idx)
                        self.feedback_message = msg
                        self.feedback_success = success
                        if success:
                            pyxel.play(0, 3)

        elif self.active_pane == "EQUIPMENT":
            if up_pressed:
                self.equip_cursor = max(0, self.equip_cursor - 1)
                self.feedback_message = ""
            elif down_pressed:
                self.equip_cursor = min(len(EquipSlot) - 1, self.equip_cursor + 1)
                self.feedback_message = ""

            if pyxel.btnp(pyxel.KEY_U) or Renderer.is_clicked(14, 228, 70, 16):
                slots = list(EquipSlot)
                target_slot = slots[self.equip_cursor]
                if inv.equipment[target_slot] is not None:
                    success, msg = inv.unequip_to_pouch(target_slot)
                    self.feedback_message = msg
                    self.feedback_success = success
                    if success:
                        pyxel.play(0, 3)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        renderer.draw_box(5, 26, SCREEN_WIDTH - 10, SCREEN_HEIGHT - 32, bg_col=COLOR_BLACK, border_col=COLOR_GRAY)

        inv = game_state.player.inventory
        from src.systems.inventory import ConsumableItem, EquipmentItem, EquipSlot

        # Equipment Section
        equip_title_col = COLOR_YELLOW if self.active_pane == "EQUIPMENT" else COLOR_GRAY
        renderer.draw_text(10, 32, t("equip_header"), equip_title_col)

        equip_order = list(EquipSlot)
        for i, slot in enumerate(equip_order):
            col = i % 2
            row = i // 2
            x = 10 + col * 118
            y = 44 + row * 12

            cursor_str = "> " if self.active_pane == "EQUIPMENT" and self.equip_cursor == i else "  "

            item = inv.equipment.get(slot)
            item_name = item.localized_name if item else f"({t('empty_slot_short')})"
            slot_label_map = {
                "HEAD": t("slot_head_short"), "SHOULDERS": t("slot_shld_short"), "CHEST": t("slot_chest_short"),
                "WAIST": t("slot_waist_short"), "HANDS": t("slot_hands_short"), "LEGS": t("slot_legs_short"),
                "MAIN_HAND": t("slot_main_short"), "OFF_HAND": t("slot_off_short")
            }
            slot_label = slot_label_map.get(slot.name, slot.name)

            label_col = COLOR_WHITE if self.active_pane == "EQUIPMENT" and self.equip_cursor == i else COLOR_GRAY
            renderer.draw_text(x, y, f"{cursor_str}{slot_label}", label_col)
            renderer.draw_text(x + 40, y, item_name[:11], COLOR_LIME if item else COLOR_DARK_BLUE)

        # 3-Slot Belt
        renderer.draw_text(10, 96, t("belt_header"), COLOR_YELLOW)
        for b_idx in range(MAX_BELT_SLOTS):
            x = 10 + b_idx * 78
            y = 106
            b_item = inv.belt[b_idx]
            name = b_item.localized_name[:11] if b_item else t("empty_slot_short")
            renderer.draw_box(x, y, 74, 18, bg_col=COLOR_NAVY, border_col=COLOR_WHITE)
            renderer.draw_text(x + 4, y + 3, f"[{b_idx + 1}]", COLOR_YELLOW)
            if b_item:
                renderer.draw_text(x + 18, y + 3, name[:11], COLOR_WHITE)
                renderer.draw_text(x + 18, y + 9, f"+{b_item.heal_amount}HP", COLOR_LIME)
            else:
                renderer.draw_text(x + 18, y + 6, name, COLOR_GRAY)

        # 10-Slot Pouch
        pouch_title_col = COLOR_YELLOW if self.active_pane == "POUCH" else COLOR_GRAY
        renderer.draw_text(10, 130, t("pouch_header", current=len(inv.pouch), max=MAX_POUCH_SLOTS), pouch_title_col)
        for p_idx in range(MAX_POUCH_SLOTS):
            col = p_idx % 2
            row = p_idx // 2
            x = 10 + col * 118
            y = 142 + row * 15

            cursor_str = "> " if self.active_pane == "POUCH" and self.pouch_cursor == p_idx else "  "

            if p_idx < len(inv.pouch):
                p_item = inv.pouch[p_idx]
                item_col = COLOR_WHITE if self.active_pane == "POUCH" and self.pouch_cursor == p_idx else COLOR_GRAY
                renderer.draw_text(x, y, f"{cursor_str}{p_item.localized_name[:10]}", item_col)

                stats_str = ""
                if isinstance(p_item, EquipmentItem):
                    if p_item.stats_bonus.attack > 0: stats_str += f"A{p_item.stats_bonus.attack}"
                    if p_item.stats_bonus.defense > 0: stats_str += f" D{p_item.stats_bonus.defense}"
                    if p_item.stats_bonus.max_hp > 0: stats_str += f" H{p_item.stats_bonus.max_hp}"
                elif isinstance(p_item, ConsumableItem):
                    stats_str = f"+{p_item.heal_amount}HP"

                if stats_str:
                    renderer.draw_text(x + 12, y + 8, stats_str, COLOR_LIME)
            else:
                renderer.draw_text(x, y, f"{cursor_str}{t('empty_slot')}", COLOR_DARK_BLUE)

        # Bottom Panel Controls
        y_bottom = 224
        renderer.draw_box(10, y_bottom, SCREEN_WIDTH - 20, 24, bg_col=COLOR_NAVY, border_col=COLOR_WHITE)
        if self.active_pane == "POUCH":
            renderer.draw_button(14, y_bottom + 4, 80, 16, t("btn_equip_use"), bg_col=COLOR_BLACK, text_col=COLOR_PEACH)
            renderer.draw_button(100, y_bottom + 4, 16, 16, t("btn_belt_1"), bg_col=COLOR_BLACK, text_col=COLOR_PEACH)
            renderer.draw_button(120, y_bottom + 4, 16, 16, t("btn_belt_2"), bg_col=COLOR_BLACK, text_col=COLOR_PEACH)
            renderer.draw_button(140, y_bottom + 4, 16, 16, t("btn_belt_3"), bg_col=COLOR_BLACK, text_col=COLOR_PEACH)
            renderer.draw_button(160, y_bottom + 4, 46, 16, t("btn_drop"), bg_col=COLOR_BLACK, text_col=COLOR_PEACH)
        else:
            renderer.draw_button(14, y_bottom + 4, 70, 16, t("btn_unequip"), bg_col=COLOR_BLACK, text_col=COLOR_PEACH)

        renderer.draw_button(SCREEN_WIDTH - 60, y_bottom + 4, 50, 16, t("btn_close"), bg_col=COLOR_BLACK,
                             text_col=COLOR_PEACH)

        # Feedback Message
        if self.feedback_message:
            msg_col = COLOR_LIME if self.feedback_success else COLOR_RED
            renderer.draw_text(14, y_bottom - 10, self.feedback_message, msg_col)


class EventsView(View):
    """Renders non-combat room encounters (sanctuary, treasure, merchant)."""

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or Renderer.is_clicked(0, 0, SCREEN_WIDTH,
                                                                                              SCREEN_HEIGHT):
            game_state.switch_mode(GameMode.MAP)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        renderer.draw_box(20, 50, SCREEN_WIDTH - 40, 140, bg_col=COLOR_DARK_BLUE, border_col=COLOR_WHITE)
        renderer.draw_text(30, 65, t("room_encounter_header"), COLOR_YELLOW)
        renderer.draw_text(30, 90, game_state.current_event_text, COLOR_WHITE)

        renderer.draw_button(SCREEN_WIDTH // 2 - 40, 150, 80, 16, t("btn_continue"), bg_col=COLOR_NAVY,
                             text_col=COLOR_LIME)


class EndGameView(View):
    """Renders Game Over or Victory screens."""

    def __init__(self, is_victory: bool) -> None:
        self.is_victory: bool = is_victory

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or Renderer.is_clicked(SCREEN_WIDTH // 2 - 45, 145, 90, 16):
            game_state.__init__()

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT

        if self.is_victory:
            renderer.draw_box(20, 60, w - 40, 120, bg_col=COLOR_NAVY, border_col=COLOR_YELLOW)
            renderer.draw_text(w // 2 - 40, 80, t("victory_achieved"), COLOR_YELLOW)
            renderer.draw_text(35, 110, t("victory_desc"), COLOR_WHITE)
        else:
            renderer.draw_box(20, 60, w - 40, 120, bg_col=COLOR_RED, border_col=COLOR_WHITE)
            renderer.draw_text(w // 2 - 24, 80, t("you_died"), COLOR_WHITE)
            renderer.draw_text(35, 110, t("death_desc"), COLOR_PEACH)

        renderer.draw_button(w // 2 - 45, 145, 90, 16, t("btn_restart"), bg_col=COLOR_BLACK, border_col=COLOR_WHITE,
                             text_col=COLOR_WHITE)


class ClassSelectView(View):
    """Interactive class selection screen allowing players to inspect and choose their hero."""

    def __init__(self) -> None:
        self.classes: list[str] = ["warrior", "rogue", "mage"]
        self.selected_index: int = 0
        self.route_mode: str = "FATE"

    def update(self, game_state: GameState) -> None:
        from src.config import SND_CLICK, SND_VICTORY

        # Toggle Route Mode
        if pyxel.btnp(pyxel.KEY_B) or pyxel.btnp(pyxel.KEY_T) or Renderer.is_clicked(54, 230, 104, 18):
            self.route_mode = "PATHFINDER" if self.route_mode == "FATE" else "FATE"
            pyxel.play(0, SND_CLICK)

        card_w, card_h = 74, 84
        x_offsets = [10, 91, 172]
        card_y = 34

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
        elif pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE) or Renderer.is_clicked(162, 230, 88, 18):
            pyxel.play(0, SND_VICTORY)
            game_state.start_new_game(self.classes[self.selected_index], route_mode=self.route_mode)
        elif pyxel.btnp(pyxel.KEY_ESCAPE) or Renderer.is_clicked(6, 230, 44, 18):
            game_state.switch_mode(GameMode.WELCOME)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)

        renderer.draw_box(0, 10, SCREEN_WIDTH, 20, bg_col=COLOR_NAVY, border_col=COLOR_GRAY)
        title = t("choose_hero")
        renderer.draw_text(SCREEN_WIDTH // 2 - len(title) * 2, 16, title, COLOR_YELLOW)

        card_y = 34
        card_w, card_h = 74, 84
        x_offsets = [10, 91, 172]

        from src.data.classes import CLASS_REGISTRY

        for i, cls_id in enumerate(self.classes):
            card_x = x_offsets[i]
            is_selected = (i == self.selected_index)
            border_col = COLOR_WHITE if is_selected else COLOR_GRAY

            renderer.draw_box(card_x, card_y, card_w, card_h, bg_col=COLOR_NAVY, border_col=border_col)

            cls_def = CLASS_REGISTRY[cls_id]
            renderer.draw_text(card_x + 6, card_y + 6, cls_def.localized_name, COLOR_YELLOW)

            archetype = t(f"arch_{cls_id}")
            renderer.draw_text(card_x + 6, card_y + 16, archetype, COLOR_GRAY)

            sprite_map = {
                "warrior": (0, 0),
                "rogue": (0, 32),
                "mage": (16, 32),
            }
            pu, pv = sprite_map.get(cls_id, (0, 0))
            pyxel.blt(card_x + 29, card_y + 32, 0, pu, pv, 16, 16, 0)

            if is_selected:
                pyxel.rectb(card_x + 1, card_y + 1, card_w - 2, card_h - 2, 9)

        # Detail Panel
        detail_y = 122
        renderer.draw_box(10, detail_y, 236, 104, bg_col=COLOR_NAVY, border_col=COLOR_WHITE)

        sel_cls_id = self.classes[self.selected_index]
        sel_cls_def = CLASS_REGISTRY[sel_cls_id]

        renderer.draw_text(16, detail_y + 4, sel_cls_def.localized_name, COLOR_YELLOW)

        desc_lines = renderer.wrap_text(sel_cls_def.localized_description, max_chars_per_line=36)
        for i, line in enumerate(desc_lines):
            renderer.draw_text(16, detail_y + 14 + (i * 9), line, COLOR_WHITE)

        stats = sel_cls_def.base_stats
        growth = sel_cls_def.growth_per_level
        renderer.draw_text(16, detail_y + 34,
                           t("stat_hp_atk", max_hp=stats.max_hp, g_hp=growth.max_hp, atk=stats.attack,
                             g_atk=growth.attack), COLOR_GRAY)
        renderer.draw_text(16, detail_y + 43,
                           t("stat_def_spd", def_=stats.defense, g_def=growth.defense, spd=stats.speed,
                             g_spd=growth.speed), COLOR_GRAY)
        renderer.draw_text(16, detail_y + 52, t("stat_crit_val", crit=int(stats.crit_chance * 100)), COLOR_GRAY)

        from src.systems.abilities import get_ability_by_id
        starting_skill_id = sel_cls_def.starting_abilities[0] if sel_cls_def.starting_abilities else "None"
        skill = get_ability_by_id(starting_skill_id)
        if skill:
            renderer.draw_text(16, detail_y + 62, t("stat_skill", skill_name=skill.name), COLOR_LIME)
            skill_lines = renderer.wrap_text(skill.description, max_chars_per_line=36)
            for i, line in enumerate(skill_lines):
                renderer.draw_text(16, detail_y + 71 + (i * 9), line, COLOR_WHITE)

        promotions = ", ".join(t(f"class_{p}_name") for p in sel_cls_def.promotions)
        renderer.draw_text(16, detail_y + 83, t("class_promotions", promotions=promotions), COLOR_PEACH)

        # Footer
        renderer.draw_button(6, 230, 44, 18, t("btn_back"), bg_col=COLOR_BLACK, border_col=COLOR_GRAY)
        mode_label = t("route_fate") if self.route_mode == "FATE" else t("route_pathfinder")
        renderer.draw_button(54, 230, 104, 18, mode_label, bg_col=COLOR_BLACK,
                             text_col=COLOR_YELLOW if self.route_mode == "PATHFINDER" else COLOR_WHITE)
        renderer.draw_button(162, 230, 88, 18, t("btn_start_journey"), bg_col=COLOR_DARK_BLUE, border_col=COLOR_YELLOW)


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

        # Sky Gradient
        pyxel.rect(0, 0, w, 52, COLOR_NAVY)
        for y in range(52, 72):
            step = (y - 52) / 20.0
            for x in range(w):
                if (x + y) % 2 == 0 or (x * 3 + y * 7) % 5 > int(step * 5):
                    pyxel.pset(x, y, COLOR_NAVY)
                else:
                    pyxel.pset(x, y, COLOR_BLACK)

        # Crescent Moon
        pyxel.circ(38, 44, 8, COLOR_WHITE)
        pyxel.circ(41, 43, 7, COLOR_NAVY)

        # Stars
        stars = [(18, 38), (60, 46), (82, 36), (110, 42), (180, 40), (210, 48), (145, 50)]
        for idx, (sx, sy) in enumerate(stars):
            col = COLOR_WHITE if (fc + idx * 7) % 24 < 12 else COLOR_YELLOW
            pyxel.pset(sx, sy, col)

        # Gothic Fortress
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

        # Windows
        gw_x, gw_y = 124, 76
        pyxel.rect(gw_x, gw_y + 4, 8, 12, COLOR_YELLOW if (fc // 15) % 2 == 0 else COLOR_ORANGE)
        pyxel.tri(gw_x, gw_y + 4, gw_x + 4, gw_y, gw_x + 7, gw_y + 4, COLOR_YELLOW)
        pyxel.line(gw_x + 3, gw_y + 1, gw_x + 3, gw_y + 15, COLOR_DARK_BLUE)
        pyxel.line(gw_x + 4, gw_y + 1, gw_x + 4, gw_y + 15, COLOR_DARK_BLUE)
        pyxel.line(gw_x, gw_y + 8, gw_x + 7, gw_y + 8, COLOR_DARK_BLUE)

        # Side slit windows
        pyxel.rect(70, 92, 2, 6, COLOR_ORANGE if (fc // 10) % 3 != 0 else COLOR_YELLOW)
        pyxel.rect(94, 82, 2, 7, COLOR_YELLOW if (fc // 10) % 2 == 0 else COLOR_ORANGE)
        pyxel.rect(159, 86, 2, 6, COLOR_ORANGE if (fc // 12) % 2 == 0 else COLOR_YELLOW)

        # Left Stone Pillar & Gargoyle
        pyxel.rect(0, 52, 24, 74, COLOR_DARK_BLUE)
        for py in range(52, 126, 6):
            pyxel.line(0, py, 23, py, COLOR_NAVY)
            stagger = 4 if (py // 6) % 2 == 0 else 14
            pyxel.pset(stagger, py + 3, COLOR_GRAY)
        pyxel.line(24, 52, 24, 126, COLOR_BLACK)
        pyxel.rect(18, 92, 3, 2, COLOR_BROWN)
        pyxel.pset(19, 90, COLOR_ORANGE if (fc % 4 < 2) else COLOR_YELLOW)
        pyxel.blt(0, 22, 1, 168, 0, 24, 32, 0)

        # Right Stone Pillar & Gargoyle
        pyxel.rect(w - 24, 52, 24, 74, COLOR_DARK_BLUE)
        for py in range(52, 126, 6):
            pyxel.line(w - 24, py, w, py, COLOR_NAVY)
            stagger = 4 if (py // 6) % 2 == 0 else 14
            pyxel.pset(w - 24 + stagger, py + 3, COLOR_GRAY)
        pyxel.line(w - 25, 52, w - 25, 126, COLOR_BLACK)
        pyxel.rect(w - 21, 92, 3, 2, COLOR_BROWN)
        pyxel.pset(w - 20, 90, COLOR_YELLOW if (fc % 4 < 2) else COLOR_ORANGE)
        pyxel.blt(w - 24, 22, 1, 168, 0, -24, 32, 0)

        # Platform ledge & Campfire
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

        # Title Banner
        pyxel.blt(56, 8, 1, 0, 0, 144, 32, 0)

        # Dialog Box
        box_x, box_y, box_w, box_h = 36, 148, 184, 78
        renderer.draw_box(box_x, box_y, box_w, box_h, bg_col=COLOR_NAVY, border_col=COLOR_WHITE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_YELLOW)

        # Corner Skulls
        pyxel.blt(box_x - 3, box_y - 3, 1, 192, 0, 8, 8, 0)
        pyxel.blt(box_x + box_w - 5, box_y - 3, 1, 192, 0, 8, 8, 0)
        pyxel.blt(box_x - 3, box_y + box_h - 5, 1, 192, 0, 8, 8, 0)
        pyxel.blt(box_x + box_w - 5, box_y + box_h - 5, 1, 192, 0, 8, 8, 0)

        # Animated Sword Cursor
        cursor_pulse = (fc // 6 % 2) * 2
        pyxel.blt(48 + cursor_pulse, 162, 1, 200, 0, 8, 8, 0)

        # Menu Options
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


class CreditsView(View):
    """Renders the game's credits screen."""

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_ESCAPE) or Renderer.is_clicked(0, 0, SCREEN_WIDTH,
                                                                                               SCREEN_HEIGHT):
            game_state.switch_mode(GameMode.WELCOME)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT

        renderer.draw_box(20, 60, w - 40, 120, bg_col=COLOR_NAVY, border_col=COLOR_YELLOW)
        renderer.draw_text(w // 2 - 20, 80, t("credits_title"), COLOR_YELLOW)
        renderer.draw_text(35, 110, t("credits_dev"), COLOR_WHITE)
        renderer.draw_text(35, 130, t("credits_ai"), COLOR_WHITE)

        renderer.draw_button(w // 2 - 50, 155, 100, 16, t("btn_back"), bg_col=COLOR_NAVY, text_col=COLOR_LIME)


class AbilityChoiceView(View):
    """Renders the ability selection screen when hitting milestone levels."""

    def __init__(self) -> None:
        self.choices: list[Ability] = []
        self.pending_rarity: str = ""
        self.replace_mode = False
        self.selected_ability: Ability | None = None

    def _init_choices(self, game_state: GameState) -> None:
        if not game_state.player.pending_ability_choices:
            return

        self.pending_rarity = game_state.player.pending_ability_choices[0]
        rarity_enum = AbilityRarity.STANDARD if self.pending_rarity == "STANDARD" else AbilityRarity.EPIC
        known = [a.id for a in game_state.player.abilities.active + game_state.player.abilities.passive]
        self.choices = get_random_abilities(
            rarity_enum,
            known,
            player_class=game_state.player.class_id,
            count=2,
        )

    def update(self, game_state: GameState) -> None:
        if not self.choices and game_state.player.pending_ability_choices:
            self._init_choices(game_state)

        if self.replace_mode and self.selected_ability:
            if pyxel.btnp(pyxel.KEY_1) or Renderer.is_clicked(30, 70, SCREEN_WIDTH - 60, 25):
                game_state.player.abilities.replace_ability(self.selected_ability, 0)
                self._finish_choice(game_state)
            elif pyxel.btnp(pyxel.KEY_2) or Renderer.is_clicked(30, 100, SCREEN_WIDTH - 60, 25):
                game_state.player.abilities.replace_ability(self.selected_ability, 1)
                self._finish_choice(game_state)
            elif pyxel.btnp(pyxel.KEY_ESCAPE) or Renderer.is_clicked(SCREEN_WIDTH - 80, SCREEN_HEIGHT - 30, 70, 16):
                self.replace_mode = False
                self.selected_ability = None
            return

        if pyxel.btnp(pyxel.KEY_ESCAPE) or Renderer.is_clicked(SCREEN_WIDTH - 80, SCREEN_HEIGHT - 30, 70, 16):
            self._finish_choice(game_state)
            return

        if (pyxel.btnp(pyxel.KEY_1) or Renderer.is_clicked(30, 60, SCREEN_WIDTH - 60, 50)) and len(self.choices) > 0:
            self._handle_selection(game_state, self.choices[0])
        elif (pyxel.btnp(pyxel.KEY_2) or Renderer.is_clicked(30, 120, SCREEN_WIDTH - 60, 50)) and len(self.choices) > 1:
            self._handle_selection(game_state, self.choices[1])

    def _handle_selection(self, game_state: GameState, chosen: Ability) -> None:
        added = game_state.player.abilities.add_ability(chosen)
        if added:
            self._finish_choice(game_state)
        else:
            self.replace_mode = True
            self.selected_ability = chosen

    def _finish_choice(self, game_state: GameState) -> None:
        game_state.player.pending_ability_choices.pop(0)
        self.choices = []
        self.replace_mode = False
        self.selected_ability = None

        if game_state.player.pending_ability_choices:
            self._init_choices(game_state)
        else:
            current_node = game_state.map_graph.current_node
            if current_node and current_node.node_type == NodeType.BOSS:
                if game_state.act < 3:
                    game_state.act += 1
                    game_state.floor = 1
                    if game_state.biome_route_mode == "PATHFINDER":
                        game_state.switch_mode(GameMode.BIOME_SELECT)
                    else:
                        game_state.advance_act()
                else:
                    game_state.switch_mode(GameMode.VICTORY)
            else:
                game_state.switch_mode(GameMode.MAP)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT

        renderer.draw_box(20, 20, w - 40, h - 40, bg_col=COLOR_NAVY, border_col=COLOR_YELLOW)

        if self.replace_mode and self.selected_ability:
            renderer.draw_text(30, 30, t("replace_ability_prompt", type=self.selected_ability.ability_type.name),
                               COLOR_YELLOW)
            renderer.draw_text(30, 45, t("replace_ability_new", name=self.selected_ability.localized_name), COLOR_LIME)

            target_list = game_state.player.abilities.active if self.selected_ability.ability_type == AbilityType.ACTIVE else game_state.player.abilities.passive
            for i, ab in enumerate(target_list):
                y_pos = 70 + (i * 30)
                renderer.draw_box(30, y_pos, w - 60, 25, bg_col=COLOR_DARK_BLUE, border_col=COLOR_WHITE)
                renderer.draw_text(40, y_pos + 8, f"[{i + 1}] {ab.localized_name}: {ab.localized_description[:30]}...",
                                   COLOR_WHITE)

            renderer.draw_button(w - 80, h - 30, 70, 16, t("btn_cancel"), bg_col=COLOR_BLACK, text_col=COLOR_PEACH)
            renderer.draw_text(30, h - 30, t("replace_ability_instruction"), COLOR_PEACH)
            return

        renderer.draw_text(30, 30, t("levelup_ability_choice", rarity=self.pending_rarity), COLOR_YELLOW)

        for i, ab in enumerate(self.choices):
            y_offset = 60 + (i * 60)
            renderer.draw_box(30, y_offset, w - 60, 50, bg_col=COLOR_DARK_BLUE, border_col=COLOR_WHITE)
            renderer.draw_text(40, y_offset + 5, f"[{i + 1}] {ab.localized_name} ({ab.ability_type.name})", COLOR_LIME)

            desc = ab.localized_description
            if len(desc) > 35:
                renderer.draw_text(40, y_offset + 18, desc[:35], COLOR_WHITE)
                renderer.draw_text(40, y_offset + 28, desc[35:70], COLOR_WHITE)
            else:
                renderer.draw_text(40, y_offset + 18, desc, COLOR_WHITE)

        renderer.draw_button(w - 80, h - 30, 70, 16, t("btn_skip"), bg_col=COLOR_BLACK, text_col=COLOR_PEACH)
        renderer.draw_text(30, h - 30, t("select_ability_instruction"), COLOR_PEACH)


class ShopView(View):
    """Interactive Merchant Shop View."""

    def __init__(self) -> None:
        self.active_tab: str = "BUY"
        self.buy_cursor: int = 0
        self.sell_cursor: int = 0
        self.feedback_msg: str = ""
        self.feedback_success = False

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.KEY_SPACE) or Renderer.is_clicked(SCREEN_WIDTH - 90, 230,
                                                                                              80, 16):
            game_state.switch_mode(GameMode.MAP)
            return

        if pyxel.btnp(pyxel.KEY_TAB) or Renderer.is_clicked(60, 60, 20, 10):
            self.active_tab = "BUY"
            self.feedback_msg = ""
        elif Renderer.is_clicked(88, 60, 24, 10):
            self.active_tab = "SELL"
            self.feedback_msg = ""

        up_pressed = pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W)
        down_pressed = pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btnp(pyxel.KEY_S)

        if self.active_tab == "BUY":
            stock = game_state.merchant_stock
            buy_action = pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_B) or Renderer.is_clicked(12, 230, 40, 16)

            for i in range(len(stock)):
                y = 75 + i * 16
                if Renderer.is_clicked(8, y, SCREEN_WIDTH - 24, 16):
                    if self.buy_cursor == i:
                        buy_action = True
                    else:
                        self.buy_cursor = i
                        self.feedback_msg = ""
                        buy_action = False

            if up_pressed:
                self.buy_cursor = max(0, self.buy_cursor - 1)
            elif down_pressed:
                self.buy_cursor = min(max(0, len(stock) - 1), self.buy_cursor + 1)

            if len(stock) > 0 and buy_action:
                if 0 <= self.buy_cursor < len(stock):
                    item, price = stock[self.buy_cursor]
                    if game_state.player.gold < price:
                        self.feedback_msg = t("shop_no_gold")
                        self.feedback_success = False
                    elif len(game_state.player.inventory.pouch) >= MAX_POUCH_SLOTS:
                        self.feedback_msg = t("msg_pouch_full")
                        self.feedback_success = False
                    else:
                        game_state.player.gold -= price
                        game_state.player.inventory.add_to_pouch(item)
                        stock.pop(self.buy_cursor)
                        pyxel.play(0, 3)
                        self.feedback_msg = t("shop_purchased", item=item.localized_name)
                        self.feedback_success = True
                        if self.buy_cursor >= len(stock):
                            self.buy_cursor = max(0, len(stock) - 1)

        elif self.active_tab == "SELL":
            pouch = game_state.player.inventory.pouch
            sell_action = pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_S) or Renderer.is_clicked(12, 230, 40,
                                                                                                         16)

            for i in range(len(pouch)):
                y = 75 + i * 14
                if Renderer.is_clicked(8, y, SCREEN_WIDTH - 24, 14):
                    if self.sell_cursor == i:
                        sell_action = True
                    else:
                        self.sell_cursor = i
                        self.feedback_msg = ""
                        sell_action = False

            if up_pressed:
                self.sell_cursor = max(0, self.sell_cursor - 1)
            elif down_pressed:
                self.sell_cursor = min(max(0, len(pouch) - 1), self.sell_cursor + 1)

            if len(pouch) > 0 and sell_action:
                if 0 <= self.sell_cursor < len(pouch):
                    item = pouch[self.sell_cursor]
                    sell_value = max(5, item.gold_value // 2)
                    popped = game_state.player.inventory.remove_from_pouch(self.sell_cursor)
                    if popped:
                        game_state.player.gold += sell_value
                        pyxel.play(0, 3)
                        self.feedback_msg = t("shop_sold", item=popped.localized_name, val=sell_value)
                        self.feedback_success = True
                        if self.sell_cursor >= len(game_state.player.inventory.pouch):
                            self.sell_cursor = max(0, len(game_state.player.inventory.pouch) - 1)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        renderer.draw_box(4, 24, SCREEN_WIDTH - 8, 28, bg_col=COLOR_NAVY, border_col=COLOR_GRAY)
        pyxel.blt(12, 28, 0, 32, 32, 16, 16, 0)
        renderer.draw_text(32, 30, t("wandering_merchant"), COLOR_YELLOW)
        renderer.draw_text(32, 40, t("merchant_quote"), COLOR_WHITE)

        renderer.draw_box(4, 56, SCREEN_WIDTH - 8, 160, bg_col=COLOR_BLACK, border_col=COLOR_GRAY)

        buy_color = COLOR_YELLOW if self.active_tab == "BUY" else COLOR_GRAY
        sell_color = COLOR_YELLOW if self.active_tab == "SELL" else COLOR_GRAY
        renderer.draw_text(12, 60, t("merchant_tab_mode"), COLOR_WHITE)
        renderer.draw_text(60, 60, t("btn_buy"), buy_color)
        renderer.draw_text(82, 60, "|", COLOR_WHITE)
        renderer.draw_text(88, 60, t("btn_sell"), sell_color)
        pyxel.line(4, 70, SCREEN_WIDTH - 5, 70, COLOR_GRAY)

        if self.active_tab == "BUY":
            stock = game_state.merchant_stock
            if not stock:
                renderer.draw_text(12, 80, t("merchant_out_of_stock"), COLOR_GRAY)
            else:
                for i, (item, price) in enumerate(stock):
                    y = 75 + i * 16
                    color = COLOR_WHITE
                    if i == self.buy_cursor:
                        renderer.draw_text(8, y, ">", COLOR_YELLOW)
                        color = COLOR_YELLOW
                    renderer.draw_text(16, y, item.localized_name, color)

                    from src.systems.inventory import ConsumableItem, EquipmentItem
                    if isinstance(item, EquipmentItem):
                        slot_str = t(f"slot_{item.slot.name.lower()}")
                        renderer.draw_text(16, y + 8, f"[{slot_str}]", COLOR_GRAY)
                    elif isinstance(item, ConsumableItem):
                        renderer.draw_text(16, y + 8, t("merchant_heals", amount=item.heal_amount), COLOR_LIME)

                    pyxel.blt(190, y, 0, 40, 24, 8, 8, 0)
                    renderer.draw_text(200, y + 1, f"{price}G", COLOR_YELLOW)

        elif self.active_tab == "SELL":
            pouch = game_state.player.inventory.pouch
            if not pouch:
                renderer.draw_text(12, 80, t("merchant_empty_pouch"), COLOR_GRAY)
            else:
                for i, item in enumerate(pouch):
                    y = 75 + i * 14
                    color = COLOR_WHITE
                    if i == self.sell_cursor:
                        renderer.draw_text(8, y, ">", COLOR_YELLOW)
                        color = COLOR_YELLOW
                    renderer.draw_text(16, y, item.localized_name, color)

                    sell_value = max(5, item.gold_value // 2)
                    renderer.draw_text(190, y, f"{sell_value}G", COLOR_YELLOW)

        renderer.draw_box(4, 220, SCREEN_WIDTH - 8, 32, bg_col=COLOR_NAVY, border_col=COLOR_GRAY)

        msg_color = COLOR_LIME if self.feedback_success else COLOR_RED
        if self.feedback_msg:
            renderer.draw_text(12, 224, self.feedback_msg, msg_color)

        if self.active_tab == "BUY":
            renderer.draw_button(12, 230, 40, 16, t("btn_buy"), bg_col=COLOR_BLACK, text_col=COLOR_PEACH)
            renderer.draw_text(60, 234, t("merchant_sell_tab"), COLOR_GRAY)
        else:
            renderer.draw_button(12, 230, 40, 16, t("btn_sell"), bg_col=COLOR_BLACK, text_col=COLOR_PEACH)
            renderer.draw_text(60, 234, t("merchant_buy_tab"), COLOR_GRAY)

        renderer.draw_button(SCREEN_WIDTH - 90, 230, 80, 16, t("btn_leave_shop"), bg_col=COLOR_BLACK,
                             text_col=COLOR_PEACH)


class LootView(View):
    """Renders the post-combat loot screen."""

    def update(self, game_state: GameState) -> None:
        if (pyxel.btnp(pyxel.KEY_1) or Renderer.is_clicked(20, 90, SCREEN_WIDTH - 40, 25)) and len(
                game_state.pending_loot) > 0:
            self._take_loot(game_state, 0)
        elif (pyxel.btnp(pyxel.KEY_2) or Renderer.is_clicked(20, 120, SCREEN_WIDTH - 40, 25)) and len(
                game_state.pending_loot) > 1:
            self._take_loot(game_state, 1)
        elif (pyxel.btnp(pyxel.KEY_3) or Renderer.is_clicked(20, 150, SCREEN_WIDTH - 40, 25)) and len(
                game_state.pending_loot) > 2:
            self._take_loot(game_state, 2)
        elif pyxel.btnp(pyxel.KEY_SPACE) or Renderer.is_clicked(96, SCREEN_HEIGHT - 30, 68, 16):
            for i in range(len(game_state.pending_loot) - 1, -1, -1):
                self._take_loot(game_state, i, play_sound=False)
            pyxel.play(0, 3)
        elif pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_C) or Renderer.is_clicked(170, SCREEN_HEIGHT - 30, 74,
                                                                                            16):
            self._exit_loot(game_state)

    def _take_loot(self, game_state: GameState, index: int, play_sound: bool = True) -> None:
        item = game_state.pending_loot[index]
        if game_state.player.inventory.add_to_pouch(item):
            game_state.pending_loot.pop(index)
            if play_sound:
                pyxel.play(0, 3)

    def _exit_loot(self, game_state: GameState) -> None:
        if game_state.player.pending_ability_choices:
            game_state.switch_mode(GameMode.ABILITY_CHOICE)
            return

        current_node = game_state.map_graph.current_node
        if current_node and current_node.node_type == NodeType.BOSS:
            if game_state.act < 3:
                game_state.act += 1
                game_state.floor = 1
                if game_state.biome_route_mode == "PATHFINDER":
                    game_state.switch_mode(GameMode.BIOME_SELECT)
                else:
                    game_state.advance_act()
            else:
                game_state.switch_mode(GameMode.VICTORY)
        else:
            game_state.switch_mode(GameMode.MAP)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT
        renderer.draw_hud(game_state.player, game_state.floor)

        renderer.draw_box(10, 30, w - 20, h - 40, bg_col=COLOR_NAVY, border_col=COLOR_YELLOW)
        renderer.draw_text(w // 2 - 40, 35, t("spoils_title"), COLOR_YELLOW)

        renderer.draw_text(20, 55, t("spoils_exp", exp=game_state.last_exp_earned), COLOR_WHITE)
        renderer.draw_text(120, 55, t("spoils_gold", gold=game_state.last_gold_earned), COLOR_YELLOW)

        pouch_len = len(game_state.player.inventory.pouch)
        from src.systems.inventory import MAX_POUCH_SLOTS
        color = COLOR_RED if pouch_len >= MAX_POUCH_SLOTS else COLOR_LIME
        renderer.draw_text(20, 70, t("spoils_pouch_space", current=pouch_len, max=MAX_POUCH_SLOTS), color)

        if pouch_len >= MAX_POUCH_SLOTS:
            renderer.draw_text(140, 70, t("spoils_pouch_full"), COLOR_RED)

        y_offset = 90
        for i, item in enumerate(game_state.pending_loot):
            renderer.draw_box(20, y_offset, w - 40, 25, bg_col=COLOR_DARK_BLUE, border_col=COLOR_WHITE)
            renderer.draw_text(25, y_offset + 5, f"[{i + 1}] {item.localized_name}", COLOR_LIME)

            from src.systems.inventory import ConsumableItem, EquipmentItem
            if isinstance(item, EquipmentItem):
                renderer.draw_text(25, y_offset + 15, t(f"slot_{item.slot.name.lower()}"), COLOR_GRAY)
                stats = ""
                if item.stats_bonus.attack > 0: stats += f" ATK+{item.stats_bonus.attack}"
                if item.stats_bonus.defense > 0: stats += f" DEF+{item.stats_bonus.defense}"
                if item.stats_bonus.speed > 0: stats += f" SPD+{item.stats_bonus.speed}"
                renderer.draw_text(90, y_offset + 15, stats, COLOR_WHITE)
            elif isinstance(item, ConsumableItem):
                from src.data.items import StatPotion
                if isinstance(item, StatPotion):
                    renderer.draw_text(25, y_offset + 15, t("spoils_perm_elixir"), 15)
                    bonus_str = ""
                    if item.stat_bonus.attack > 0:
                        bonus_str = f"+{item.stat_bonus.attack} ATK"
                    elif item.stat_bonus.defense > 0:
                        bonus_str = f"+{item.stat_bonus.defense} DEF"
                    elif item.stat_bonus.speed > 0:
                        bonus_str = f"+{item.stat_bonus.speed} SPD"
                    elif item.stat_bonus.max_hp > 0:
                        bonus_str = f"+{item.stat_bonus.max_hp} HP"
                    elif item.stat_bonus.crit_chance > 0:
                        bonus_str = f"+{int(item.stat_bonus.crit_chance * 100)}% CRIT"
                    renderer.draw_text(110, y_offset + 15, bonus_str, COLOR_LIME)
                else:
                    renderer.draw_text(25, y_offset + 15, t("spoils_consumable"), COLOR_GRAY)
                    renderer.draw_text(90, y_offset + 15, t("merchant_heals", amount=f"{item.heal_amount} HP"),
                                       COLOR_GREEN)

            y_offset += 30

        if not game_state.pending_loot:
            renderer.draw_text(20, y_offset, t("spoils_no_items"), COLOR_GRAY)

        renderer.draw_text(14, h - 30, t("spoils_take_item"), COLOR_PEACH)
        renderer.draw_button(96, h - 30, 68, 16, t("btn_take_all"), bg_col=COLOR_BLACK, text_col=COLOR_PEACH)
        renderer.draw_button(170, h - 30, 74, 16, t("btn_continue"), bg_col=COLOR_BLACK, text_col=COLOR_PEACH)


class ViewManager:
    """Manages view selection and delegates update/render calls."""

    def __init__(self) -> None:
        self.views: dict[GameMode, View] = {
            GameMode.WELCOME: WelcomeView(),
            GameMode.CLASS_SELECT: ClassSelectView(),
            GameMode.CREDITS: CreditsView(),
            GameMode.BIOME_SELECT: BiomeSelectView(),
            GameMode.MAP: MapView(),
            GameMode.COMBAT: CombatView(),
            GameMode.INVENTORY: InventoryView(),
            GameMode.EVENTS: EventsView(),
            GameMode.GAME_OVER: EndGameView(is_victory=False),
            GameMode.VICTORY: EndGameView(is_victory=True),
            GameMode.ABILITY_CHOICE: AbilityChoiceView(),
            GameMode.LOOT: LootView(),
            GameMode.SHOP: ShopView(),
        }

    def update(self, game_state: GameState) -> None:
        if game_state.current_mode in (GameMode.MAP, GameMode.COMBAT, GameMode.EVENTS, GameMode.INVENTORY,
                                       GameMode.LOOT, GameMode.SHOP):
            inv_clicked = Renderer.is_clicked(222, 3, 30, 16)
            if pyxel.btnp(pyxel.KEY_I) or inv_clicked or (
                    game_state.current_mode == GameMode.INVENTORY and pyxel.btnp(pyxel.KEY_ESCAPE)):
                game_state.toggle_inventory()
                return

        view = self.views.get(game_state.current_mode)
        if view:
            view.update(game_state)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        view = self.views.get(game_state.current_mode)
        if view:
            view.draw(game_state, renderer)
