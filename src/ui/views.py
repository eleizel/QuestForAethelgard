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
            pyxel.play(0, 3)
            game_state.advance_act(target_biome_id=biome_a_id)
        elif pyxel.btnp(pyxel.KEY_2) or Renderer.is_clicked(132, 42, 116, 172):
            pyxel.play(0, 3)
            game_state.advance_act(target_biome_id=biome_b_id)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)

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

            renderer.draw_box(x_offset, 42, 116, 172, bg_col=COLOR_DARK_BLUE, border_col=biome.ambient_color)

            curr_y = 42 + 8
            renderer.draw_text(x_offset + 6, curr_y, biome.localized_name[:17], COLOR_YELLOW)
            curr_y += 11

            for tag_line in renderer.wrap_text(biome.localized_tags, max_chars_per_line=18):
                renderer.draw_text(x_offset + 6, curr_y, tag_line, 3)
                curr_y += 9
            curr_y += 3

            for desc_line in renderer.wrap_text(biome.localized_description, max_chars_per_line=18):
                renderer.draw_text(x_offset + 6, curr_y, desc_line, COLOR_WHITE)
                curr_y += 9
            curr_y += 4

            renderer.draw_text(x_offset + 6, curr_y, t("biome_threats"), COLOR_ORANGE)
            curr_y += 9

            from src.entities.enemy import ENEMY_CATALOG
            for e_id in biome.basic_enemies[:2]:
                e_name = ENEMY_CATALOG[e_id].localized_name[:16] if e_id in ENEMY_CATALOG else e_id.replace('_', ' ').title()[:16]
                renderer.draw_text(x_offset + 8, curr_y, f"- {e_name}", COLOR_GRAY)
                curr_y += 9
            curr_y += 4

            renderer.draw_text(x_offset + 6, curr_y, t("biome_bosses"), 14)
            curr_y += 9
            for b_id in biome.bosses:
                b_name = ENEMY_CATALOG[b_id].localized_name[:16] if b_id in ENEMY_CATALOG else b_id.replace('_', ' ').title()[:16]
                renderer.draw_text(x_offset + 8, curr_y, f"- {b_name}", COLOR_GRAY)
                curr_y += 9

            renderer.draw_button(x_offset + 10, 42 + 172 - 22, 96, 16, t("btn_choose_route"), bg_col=COLOR_BLACK, text_col=COLOR_WHITE)


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
                pyxel.play(0, 3)
                game_state.select_map_node(node.id)
                return

        for idx, node in enumerate(available):
            key = getattr(pyxel, f"KEY_{idx + 1}", None)
            if key and pyxel.btnp(key):
                pyxel.play(0, 3)
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


class CombatView(View):
    """Renders retro dungeon combat arena, detailed stat cards, split command panel, and battle log."""

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

        # Player damage / heal
        if new_p_hp < old_p_hp:
            dmg = old_p_hp - new_p_hp
            is_crit = any("CRIT" in log or "CRÍTICO" in log for log in combat.combat_logs[-2:])
            txt = f"-{dmg}!" if is_crit else f"-{dmg}"
            col = COLOR_RED if is_crit else COLOR_PEACH
            self.popups.append(CombatPopup(x=62, y=44, text=txt, color=col))
            self.player_flash = 3
            if is_crit:
                self.shake_frames = 5
        elif new_p_hp > old_p_hp:
            heal = new_p_hp - old_p_hp
            self.popups.append(CombatPopup(x=62, y=44, text=f"+{heal}", color=COLOR_LIME))

        # Enemy damage / heal
        if new_e_hp < old_e_hp:
            dmg = old_e_hp - new_e_hp
            is_crit = any("CRIT" in log or "CRÍTICO" in log for log in combat.combat_logs[-2:])
            txt = f"-{dmg}!" if is_crit else f"-{dmg}"
            col = COLOR_YELLOW if is_crit else COLOR_WHITE
            self.popups.append(CombatPopup(x=184, y=44, text=txt, color=col))
            self.enemy_flash = 3
            if is_crit:
                self.shake_frames = 6

    def update(self, game_state: GameState) -> None:
        if game_state.combat is None:
            self.popups.clear()
            return

        for p in self.popups:
            if p.lifetime % 2 == 0:
                p.y -= 1
            p.lifetime -= 1
        self.popups = [p for p in self.popups if p.lifetime > 0]

        # Speed toggle [Z] or click at bottom-right corner of dungeon arena (222, 79, 28, 11)
        if pyxel.btnp(pyxel.KEY_Z) or Renderer.is_clicked(222, 79, 28, 11):
            self.speed_index = (self.speed_index + 1) % len(SPEED_INTERVALS)
            pyxel.play(0, 3)
            return

        speed_frames = SPEED_INTERVALS[self.speed_index]

        # Advance combat (auto-tick, space, or tap on arena/log)
        if pyxel.btnp(pyxel.KEY_SPACE) or (pyxel.frame_count % speed_frames == 0) or Renderer.is_clicked(0, 24, SCREEN_WIDTH, 68) or Renderer.is_clicked(0, 202, SCREEN_WIDTH, 54):
            old_p_hp = game_state.player.current_hp
            old_e_hp = game_state.combat.enemy.current_hp
            game_state.update_combat()
            self._detect_combat_deltas(game_state, old_p_hp, old_e_hp)

        if game_state.combat is None:
            return

        # Belt hotkeys: [1, 2, 3] or click on command panel
        belt_y_positions = [162, 174, 186]
        for idx, key in enumerate((pyxel.KEY_1, pyxel.KEY_2, pyxel.KEY_3)):
            by = belt_y_positions[idx]
            if pyxel.btnp(key) or Renderer.is_clicked(6, by, 114, 11):
                old_p_hp = game_state.player.current_hp
                if game_state.player.inventory.use_belt_item(idx, game_state.player):
                    pyxel.play(1, 2)
                    game_state.combat.combat_logs.append(
                        t("combat_belt_use", player=game_state.player.name, slot=idx + 1)
                    )
                    self._detect_combat_deltas(game_state, old_p_hp, game_state.combat.enemy.current_hp)

        # Ability hotkeys: [4, 5] or click on right action panel
        for idx, key in enumerate((pyxel.KEY_4, pyxel.KEY_5)):
            ay = 164 + idx * 16
            if (pyxel.btnp(key) or Renderer.is_clicked(130, ay, 118, 14)) and idx < len(
                    game_state.player.abilities.active):
                if game_state.combat.ability_cooldown <= 0:
                    game_state.combat.queued_ability = game_state.player.abilities.active[idx]
                    game_state.combat.ability_cooldown = 3
                    game_state.combat.combat_logs.append(
                        t("combat_queued", ability=game_state.player.abilities.active[idx].name)
                    )
                else:
                    game_state.combat.combat_logs.append(
                        t("combat_cooldown", cooldown=game_state.combat.ability_cooldown)
                    )

    def _get_enemy_sprite(self, enemy: Enemy) -> tuple[int, int]:
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
        # Camera screen shake
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
        fc = pyxel.frame_count

        # =====================================================================
        # 1. RETRO DUNGEON STAGE ARENA (y=24 to y=92)
        # =====================================================================
        arena_x, arena_y, arena_w, arena_h = 4, 24, SCREEN_WIDTH - 8, 68
        pyxel.rect(arena_x, arena_y, arena_w, arena_h, COLOR_BLACK)

        # Stone wall masonry & vaulted arch columns
        for col_x in [12, 44, 94, 150, 200, 232]:
            pyxel.rect(col_x, arena_y, 8, arena_h - 14, COLOR_NAVY)
            for by in range(arena_y + 4, arena_y + arena_h - 14, 8):
                pyxel.line(col_x, by, col_x + 7, by, COLOR_DARK_BLUE)
                pyxel.pset(col_x + ((by // 4) % 6), by + 3, COLOR_LIGHT_BLUE)

        # Central arched entryway
        pyxel.rect(114, arena_y + 12, 28, arena_h - 26, COLOR_DARK_BLUE)
        pyxel.tri(114, arena_y + 12, 128, arena_y + 2, 141, arena_y + 12, COLOR_DARK_BLUE)
        pyxel.rect(118, arena_y + 16, 20, arena_h - 30, COLOR_BLACK)
        pyxel.tri(118, arena_y + 16, 128, arena_y + 8, 137, arena_y + 16, COLOR_BLACK)

        # Left Torch Sconce & Flame
        ltx, lty = 22, 38
        pyxel.rect(ltx - 1, lty + 6, 4, 3, COLOR_BROWN)
        pyxel.pset(ltx, lty + 9, COLOR_DARK_BLUE)
        pyxel.rect(ltx - 1, lty + 2, 4, 4, COLOR_ORANGE)
        pyxel.pset(ltx, lty + (1 if fc % 4 < 2 else 0), COLOR_YELLOW)
        pyxel.pset(ltx + 1, lty + 2, COLOR_WHITE)
        if fc % 3 == 0:
            pyxel.pset(ltx + (fc % 3) - 1, lty - 2, COLOR_YELLOW)

        # Right Torch Sconce & Flame
        rtx, rty = 230, 38
        pyxel.rect(rtx - 1, rty + 6, 4, 3, COLOR_BROWN)
        pyxel.pset(rtx, rty + 9, COLOR_DARK_BLUE)
        pyxel.rect(rtx - 1, rty + 2, 4, 4, COLOR_ORANGE)
        pyxel.pset(rtx, rty + (0 if fc % 4 < 2 else 1), COLOR_YELLOW)
        pyxel.pset(rtx - 1, rty + 2, COLOR_WHITE)
        if fc % 3 == 1:
            pyxel.pset(rtx - (fc % 3) + 1, rty - 2, COLOR_YELLOW)

        # Cobblestone ground
        ground_y = arena_y + arena_h - 14
        pyxel.rect(arena_x, ground_y, arena_w, 14, COLOR_DARK_BLUE)
        for gx in range(arena_x + 2, arena_x + arena_w - 4, 12):
            pyxel.line(gx, ground_y + 3, gx + 6, ground_y + 3, COLOR_NAVY)
            pyxel.line(gx + 6, ground_y + 8, gx + 11, ground_y + 8, COLOR_NAVY)

        # Status Badges Behind Player (Left of Hero: x=14..48)
        if game_state.player.statuses:
            status_y = 52
            for s in game_state.player.statuses[:3]:
                tag = f"{s.badge} {s.duration}"
                tw = renderer.get_text_width(tag)
                pill_w = tw + 6
                pill_x = 14
                pyxel.rect(pill_x, status_y - 1, pill_w, 9, COLOR_BLACK)
                pyxel.rectb(pill_x, status_y - 1, pill_w, 9, s.color)
                renderer.draw_text(pill_x + 3, status_y, tag, s.color)
                status_y += 11

        # Status Badges Behind Enemy (Right of Enemy: x=204..238)
        if combat.enemy.statuses:
            status_y = 52
            for s in combat.enemy.statuses[:3]:
                tag = f"{s.badge} {s.duration}"
                tw = renderer.get_text_width(tag)
                pill_w = tw + 6
                pill_x = arena_x + arena_w - pill_w - 6
                pyxel.rect(pill_x, status_y - 1, pill_w, 9, COLOR_BLACK)
                pyxel.rectb(pill_x, status_y - 1, pill_w, 9, s.color)
                renderer.draw_text(pill_x + 3, status_y, tag, s.color)
                status_y += 11

        # Combatant Ground Shadows
        pyxel.elli(56, 75, 20, 5, COLOR_NAVY)
        pyxel.elli(176, 75, 22, 5, COLOR_NAVY)

        # Animated Hero Character on Left
        sprite_map = {
            "warrior": (0, 0),
            "rogue": (0, 32),
            "mage": (16, 32),
        }
        pu, pv = sprite_map.get(game_state.player.class_id, (0, 0))
        hero_x, hero_y = 58, 62

        if self.player_flash > 0:
            self.player_flash -= 1
            for c in range(16):
                pyxel.pal(c, COLOR_WHITE)
            pyxel.blt(hero_x, hero_y, 0, pu, pv, 16, 16, 0)
            pyxel.pal()
        else:
            pyxel.blt(hero_x, hero_y, 0, pu, pv, 16, 16, 0)

        # Drawn hero blade
        pyxel.line(hero_x + 14, hero_y + 6, hero_x + 21, hero_y - 1, COLOR_CYAN)
        pyxel.line(hero_x + 15, hero_y + 6, hero_x + 22, hero_y - 1, COLOR_WHITE)

        # Animated Enemy Sprite on Right
        eu, ev = self._get_enemy_sprite(combat.enemy)
        enemy_x, enemy_y = 178, 62

        if self.enemy_flash > 0:
            self.enemy_flash -= 1
            for c in range(16):
                pyxel.pal(c, COLOR_WHITE)
            pyxel.blt(enemy_x, enemy_y, 0, eu, ev, 16, 16, 0)
            pyxel.pal()
        else:
            pyxel.blt(enemy_x, enemy_y, 0, eu, ev, 16, 16, 0)

        # Ambient floating magic/spore motes around enemy
        spore_coords = [(172, 56), (180, 50), (192, 52), (198, 58), (175, 66), (196, 68)]
        for s_idx, (sx, sy) in enumerate(spore_coords):
            sy_float = sy + int(math.sin((fc + s_idx * 5) * 0.2) * 2)
            if (fc + s_idx * 4) % 20 < 12:
                pyxel.pset(sx, sy_float, COLOR_CYAN if s_idx % 2 == 0 else COLOR_LIME)

        # Floating combat damage popups
        for pop in self.popups:
            renderer.draw_text(pop.x, pop.y, pop.text, pop.color)

        # Speed Button in the bottom-right corner of the dungeon arena
        renderer.draw_button(222, 79, 28, 11, f"[{SPEED_LABELS[self.speed_index]}]", bg_col=COLOR_BLACK, border_col=COLOR_YELLOW, text_col=COLOR_YELLOW)

        # Arena Outer Border
        pyxel.rectb(arena_x, arena_y, arena_w, arena_h, COLOR_DARK_BLUE)

        # =====================================================================
        # 2. STAT & PORTRAIT CARDS (y=94 to y=140)
        # =====================================================================
        card_w, card_h = 122, 46

        # --- PLAYER CARD (Left) ---
        pc_x, pc_y = 4, 94
        renderer.draw_box(pc_x, pc_y, card_w, card_h, bg_col=COLOR_DARK_BLUE, border_col=COLOR_LIGHT_BLUE)

        # Portrait Frame & Hero Sprite
        pyxel.rect(pc_x + 3, pc_y + 3, 20, 20, COLOR_NAVY)
        pyxel.rectb(pc_x + 3, pc_y + 3, 20, 20, COLOR_LIGHT_BLUE)
        pyxel.blt(pc_x + 5, pc_y + 5, 0, pu, pv, 16, 16, 0)

        # Player Name & HP Bar
        p_name = game_state.player.name[:14]
        renderer.draw_text(pc_x + 27, pc_y + 4, p_name, COLOR_YELLOW)
        renderer.draw_bar(pc_x + 27, pc_y + 13, 90, 5, game_state.player.current_hp, game_state.player.max_hp, fill_col=COLOR_GREEN, bg_col=COLOR_RED)

        # Numeric Stats
        p_stats = game_state.player.effective_stats
        renderer.draw_text(pc_x + 27, pc_y + 20, f"HP:  {game_state.player.current_hp}/{game_state.player.max_hp}", COLOR_WHITE)
        renderer.draw_text(pc_x + 27, pc_y + 28, f"ATK: {p_stats.attack:<3} DEF: {p_stats.defense}", COLOR_WHITE)
        crit_pct = int(p_stats.crit_chance * 100)
        renderer.draw_text(pc_x + 27, pc_y + 36, f"SPD: {p_stats.speed:<3} CRIT: {crit_pct}%", COLOR_WHITE)

        # --- ENEMY CARD (Right) ---
        ec_x, ec_y = 130, 94
        border_col = COLOR_RED if combat.enemy.tier.value >= 3 else COLOR_LIGHT_BLUE
        renderer.draw_box(ec_x, ec_y, card_w, card_h, bg_col=COLOR_DARK_BLUE, border_col=border_col)

        # Portrait Frame & Enemy Sprite
        pyxel.rect(ec_x + 3, ec_y + 3, 20, 20, COLOR_NAVY)
        pyxel.rectb(ec_x + 3, ec_y + 3, 20, 20, border_col)
        pyxel.blt(ec_x + 5, ec_y + 5, 0, eu, ev, 16, 16, 0)

        # Enemy Name & HP Bar
        e_name = combat.enemy.display_name if len(combat.enemy.display_name) <= 14 else combat.enemy.display_name[:13] + "."
        renderer.draw_text(ec_x + 27, ec_y + 4, e_name, COLOR_YELLOW)
        renderer.draw_bar(ec_x + 27, ec_y + 13, 90, 5, combat.enemy.current_hp, combat.enemy.max_hp, fill_col=COLOR_GREEN, bg_col=COLOR_RED)

        # Numeric Stats
        e_stats = combat.enemy.effective_stats
        renderer.draw_text(ec_x + 27, ec_y + 20, f"HP:  {combat.enemy.current_hp}/{combat.enemy.max_hp}", COLOR_WHITE)
        renderer.draw_text(ec_x + 27, ec_y + 28, f"ATK: {e_stats.attack:<3} DEF: {e_stats.defense}", COLOR_WHITE)
        e_crit = int(e_stats.crit_chance * 100)
        renderer.draw_text(ec_x + 27, ec_y + 36, f"SPD: {e_stats.speed:<3} CRIT: {e_crit}%", COLOR_WHITE)

        # =====================================================================
        # 3. ACTION TICK GAUGES (y=142 to y=156)
        # =====================================================================
        renderer.draw_text(4, 142, t("tick_gauges"), COLOR_YELLOW)

        # Player meter aligned with player card (x=4, w=122); Enemy meter aligned with enemy card (x=130, w=122)
        renderer.draw_bar(4, 150, 122, 5, combat.player_gauge, ACTION_THRESHOLD, fill_col=COLOR_LIGHT_BLUE, bg_col=COLOR_NAVY)
        renderer.draw_bar(130, 150, 122, 5, combat.enemy_gauge, ACTION_THRESHOLD, fill_col=COLOR_ORANGE, bg_col=COLOR_NAVY)

        # =====================================================================
        # 4. SPLIT ACTION COMMAND PANEL (y=158 to y=198)
        # =====================================================================
        cmd_x, cmd_y, cmd_w, cmd_h = 4, 158, SCREEN_WIDTH - 8, 42
        renderer.draw_box(cmd_x, cmd_y, cmd_w, cmd_h, bg_col=COLOR_NAVY, border_col=COLOR_LIGHT_BLUE)

        # Vertical Column Divider
        div_x = cmd_x + 120
        pyxel.line(div_x, cmd_y + 2, div_x, cmd_y + cmd_h - 3, COLOR_LIGHT_BLUE)

        # --- LEFT COLUMN: Belt Quick-Items ---
        inv = game_state.player.inventory
        for b_idx in range(MAX_BELT_SLOTS):
            b_item = inv.belt[b_idx]
            sy = cmd_y + 4 + b_idx * 12

            if b_idx == 0:
                pyxel.tri(cmd_x + 3, sy + 3, cmd_x + 3, sy + 7, cmd_x + 6, sy + 5, COLOR_YELLOW)

            if b_item:
                pyxel.rectb(cmd_x + 8, sy - 1, 108, 10, COLOR_LIGHT_BLUE if b_idx == 0 else COLOR_NAVY)
                renderer.draw_text(cmd_x + 11, sy, f"{b_idx+1}. {b_item.localized_name[:10]}", COLOR_WHITE)
                renderer.draw_text(cmd_x + 78, sy, f"[+{b_item.heal_amount} HP]", COLOR_LIME)
            else:
                renderer.draw_text(cmd_x + 11, sy, f"{b_idx+1}. {t('empty_slot_short')}", COLOR_GRAY)

        # --- RIGHT COLUMN: Active Skills ---
        skills = game_state.player.abilities.active
        for a_idx in range(2):
            sy = cmd_y + 7 + a_idx * 16
            if a_idx < len(skills):
                ab = skills[a_idx]
                is_queued = (combat.queued_ability == ab)

                if a_idx == 0:
                    pyxel.line(div_x + 4, sy + 1, div_x + 8, sy + 5, COLOR_WHITE)
                    pyxel.line(div_x + 8, sy + 1, div_x + 4, sy + 5, COLOR_WHITE)
                else:
                    pyxel.rect(div_x + 4, sy + 1, 5, 4, COLOR_WHITE)
                    pyxel.pset(div_x + 5, sy + 2, COLOR_BLACK)
                    pyxel.pset(div_x + 7, sy + 2, COLOR_BLACK)

                ab_name = f"{a_idx+4}. {ab.localized_name[:12]}"
                renderer.draw_text(div_x + 12, sy, ab_name, COLOR_YELLOW if is_queued else COLOR_WHITE)

                tag = "WAIT" if is_queued else "CAST"
                tag_col = COLOR_YELLOW if is_queued else COLOR_LIGHT_BLUE
                renderer.draw_text(cmd_x + cmd_w - 28, sy, tag, tag_col)
            else:
                renderer.draw_text(div_x + 12, sy, f"{a_idx+4}. (Empty)", COLOR_GRAY)

        # =====================================================================
        # 5. GOTHIC COMBAT ACTIVITY LOG (y=202 to y=254)
        # =====================================================================
        log_x, log_y, log_w, log_h = 4, 202, SCREEN_WIDTH - 8, 52
        renderer.draw_box(log_x, log_y, log_w, log_h, bg_col=COLOR_BLACK, border_col=COLOR_DARK_BLUE)
        pyxel.rectb(log_x + 1, log_y + 1, log_w - 2, log_h - 2, COLOR_NAVY)

        for cx, cy in [
            (log_x + 2, log_y + 2),
            (log_x + log_w - 3, log_y + 2),
            (log_x + 2, log_y + log_h - 3),
            (log_x + log_w - 3, log_y + log_h - 3),
        ]:
            pyxel.pset(cx, cy, COLOR_LIGHT_BLUE)

        renderer.draw_text(log_x + 8, log_y + 3, t("combat_log_header"), COLOR_YELLOW)

        recent_logs = combat.combat_logs if combat.combat_logs else [t("combat_awaiting")]
        wrapped_logs = []
        for line in recent_logs:
            wrapped_logs.extend(renderer.wrap_text(line, max_chars_per_line=39))

        display_entries = wrapped_logs[-4:] if wrapped_logs else []
        line_y = log_y + 13
        for disp in display_entries:
            if "CRIT" in disp or "CRÍTICO" in disp:
                renderer.draw_text(log_x + 8, line_y, disp, COLOR_YELLOW)
            elif "dmg" in disp or "daño" in disp:
                renderer.draw_text(log_x + 8, line_y, disp, COLOR_WHITE)
            elif "defeated" in disp or "derrotado" in disp:
                renderer.draw_text(log_x + 8, line_y, disp, COLOR_LIME)
            else:
                renderer.draw_text(log_x + 8, line_y, disp, COLOR_GRAY)
            line_y += 9

        if len(wrapped_logs) > 4:
            ind_x, ind_y = log_x + log_w - 8, log_y + log_h - 7
            pyxel.tri(ind_x - 2, ind_y, ind_x + 2, ind_y, ind_x, ind_y + 3, COLOR_YELLOW)

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
        if pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.KEY_I) or Renderer.is_clicked(SCREEN_WIDTH - 60, 228, 50, 16):
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

        for i in range(len(EquipSlot)):
            col = i % 2
            row = i // 2
            x = 10 + col * 118
            y = 44 + row * 12
            if Renderer.is_clicked(x, y, 100, 10):
                self.active_pane = "EQUIPMENT"
                self.equip_cursor = i
                self.feedback_message = ""

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

        renderer.draw_button(SCREEN_WIDTH - 60, y_bottom + 4, 50, 16, t("btn_close"), bg_col=COLOR_BLACK, text_col=COLOR_PEACH)

        if self.feedback_message:
            msg_col = COLOR_LIME if self.feedback_success else COLOR_RED
            renderer.draw_text(14, y_bottom - 10, self.feedback_message, msg_col)


class EventsView(View):
    """Renders non-combat room encounters (sanctuary, treasure, merchant)."""

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or Renderer.is_clicked(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT):
            game_state.switch_mode(GameMode.MAP)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        renderer.draw_box(20, 50, SCREEN_WIDTH - 40, 140, bg_col=COLOR_DARK_BLUE, border_col=COLOR_WHITE)
        renderer.draw_text(30, 65, t("room_encounter_header"), COLOR_YELLOW)
        renderer.draw_text(30, 90, game_state.current_event_text, COLOR_WHITE)

        renderer.draw_button(SCREEN_WIDTH // 2 - 40, 150, 80, 16, t("btn_continue"), bg_col=COLOR_NAVY, text_col=COLOR_LIME)


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

        renderer.draw_button(w // 2 - 45, 145, 90, 16, t("btn_restart"), bg_col=COLOR_BLACK, border_col=COLOR_WHITE, text_col=COLOR_WHITE)


class ClassSelectView(View):
    """Interactive class selection screen featuring panoramic backdrop, hero cards, and stat alcove."""

    def __init__(self) -> None:
        self.classes: list[str] = ["warrior", "rogue", "mage"]
        self.selected_index: int = 0
        self.route_mode: str = "FATE"

    def update(self, game_state: GameState) -> None:
        from src.config import SND_CLICK, SND_VICTORY

        # Toggle route mode
        if pyxel.btnp(pyxel.KEY_B) or pyxel.btnp(pyxel.KEY_T) or Renderer.is_clicked(70, 230, 96, 18):
            self.route_mode = "PATHFINDER" if self.route_mode == "FATE" else "FATE"
            pyxel.play(0, SND_CLICK)

        card_w, card_h = 78, 80
        x_offsets = [6, 89, 172]
        card_y = 28

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
        elif pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE) or Renderer.is_clicked(172, 230, 78, 18):
            pyxel.play(0, SND_VICTORY)
            game_state.start_new_game(self.classes[self.selected_index], route_mode=self.route_mode)
        elif pyxel.btnp(pyxel.KEY_ESCAPE) or Renderer.is_clicked(6, 230, 58, 18):
            game_state.switch_mode(GameMode.WELCOME)

    def _draw_stat_icon(self, x: int, y: int, stat_type: str) -> None:
        """Draw small 5x5 stat glyphs matching the reference HUD."""
        if stat_type == "hp":
            # Green Heart
            pyxel.pset(x + 1, y, COLOR_LIME)
            pyxel.pset(x + 3, y, COLOR_LIME)
            pyxel.rect(x, y + 1, 5, 2, COLOR_LIME)
            pyxel.pset(x + 1, y + 3, COLOR_LIME)
            pyxel.pset(x + 2, y + 3, COLOR_LIME)
            pyxel.pset(x + 3, y + 3, COLOR_LIME)
            pyxel.pset(x + 2, y + 4, COLOR_LIME)
        elif stat_type == "atk":
            # Red Crossed Blades
            pyxel.line(x, y, x + 4, y + 4, COLOR_RED)
            pyxel.line(x + 4, y, x, y + 4, COLOR_RED)
            pyxel.pset(x + 2, y + 2, COLOR_WHITE)
        elif stat_type == "def":
            # Blue Shield
            pyxel.rect(x + 1, y, 3, 3, COLOR_CYAN)
            pyxel.pset(x, y + 1, COLOR_CYAN)
            pyxel.pset(x + 4, y + 1, COLOR_CYAN)
            pyxel.pset(x + 2, y + 4, COLOR_CYAN)
            pyxel.line(x + 1, y + 3, x + 3, y + 3, COLOR_CYAN)
        elif stat_type == "spd":
            # Yellow Speed Boot
            pyxel.rect(x + 1, y, 2, 4, COLOR_YELLOW)
            pyxel.rect(x + 1, y + 3, 4, 2, COLOR_YELLOW)
            pyxel.pset(x + 4, y + 4, COLOR_WHITE)
        elif stat_type == "crit":
            # Orange Star
            pyxel.pset(x + 2, y, COLOR_ORANGE)
            pyxel.line(x, y + 2, x + 4, y + 2, COLOR_ORANGE)
            pyxel.pset(x + 2, y + 4, COLOR_ORANGE)
            pyxel.pset(x + 2, y + 2, COLOR_YELLOW)

    def _draw_skill_glyph(self, x: int, y: int, skill_id: str) -> None:
        """Render distinct skill art inside the skill thumbnail box."""
        fc = pyxel.frame_count
        if "cross_cut" in skill_id:
            # Dual cyan sword slashes
            pyxel.line(x + 2, y + 2, x + 9, y + 9, COLOR_CYAN)
            pyxel.line(x + 3, y + 2, x + 10, y + 9, COLOR_WHITE)
            pyxel.line(x + 8, y + 2, x + 1, y + 9, COLOR_CYAN)
            pyxel.line(x + 9, y + 2, x + 2, y + 9, COLOR_WHITE)
        elif "shadow" in skill_id:
            # Shadow crescent with twin blade glints
            pyxel.circ(x + 6, y + 6, 4, COLOR_PURPLE)
            pyxel.circ(x + 8, y + 5, 3, COLOR_NAVY)
            pyxel.line(x + 2, y + 8, x + 9, y + 2, COLOR_WHITE)
        elif "arcane" in skill_id:
            # Pulsing arcane energy orb
            pyxel.circ(x + 6, y + 6, 3, COLOR_CYAN)
            pyxel.pset(x + 6, y + 6, COLOR_WHITE)
            if (fc // 6) % 2 == 0:
                pyxel.pset(x + 2, y + 2, COLOR_LIGHT_BLUE)
                pyxel.pset(x + 9, y + 9, COLOR_LIGHT_BLUE)
        else:
            # Default star burst
            pyxel.circ(x + 6, y + 6, 3, COLOR_YELLOW)
            pyxel.pset(x + 6, y + 6, COLOR_WHITE)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        fc = pyxel.frame_count

        # =====================================================================
        # 1. TOP PANORAMIC BACKDROP & TITLE
        # =====================================================================
        # Sky & Mountain Silhouette
        pyxel.rect(0, 0, SCREEN_WIDTH, 26, COLOR_NAVY)
        for my in range(14, 26):
            step = (my - 14) / 12.0
            for mx in range(SCREEN_WIDTH):
                if (mx + my) % 2 == 0 or (mx * 3 + my * 5) % 7 > int(step * 7):
                    pyxel.pset(mx, my, COLOR_DARK_BLUE)

        # Distant Spire Towers & Citadel Peaks
        pyxel.tri(188, 14, 194, 2, 200, 14, COLOR_BLACK)
        pyxel.tri(204, 14, 212, 0, 220, 14, COLOR_BLACK)
        pyxel.tri(222, 14, 230, 4, 238, 14, COLOR_BLACK)

        # Pale Moon at top right
        pyxel.circ(180, 8, 5, COLOR_PEACH)
        pyxel.circ(179, 7, 4, COLOR_WHITE)
        pyxel.pset(181, 6, COLOR_PEACH)

        # Ambient Pine Tree Silhouettes
        for tx in range(24, SCREEN_WIDTH - 24, 14):
            th = 6 + (tx % 5)
            pyxel.tri(tx, 18, tx + 4, 18 - th, tx + 8, 18, COLOR_BLACK)

        # Hanging Crimson Banners on Far Left & Right
        for bx in [8, SCREEN_WIDTH - 18]:
            pyxel.rect(bx, 0, 10, 22, COLOR_RED)
            pyxel.tri(bx, 22, bx + 5, 26, bx + 9, 22, COLOR_RED)
            pyxel.rectb(bx, 0, 10, 22, COLOR_ORANGE)
            pyxel.pset(bx + 4, 8, COLOR_YELLOW)
            pyxel.pset(bx + 5, 8, COLOR_YELLOW)
            pyxel.pset(bx + 4, 9, COLOR_YELLOW)
            pyxel.pset(bx + 5, 9, COLOR_YELLOW)

        # Flanking Wall Sconces with Animated Fire
        for tx, ty in [(3, 14), (SCREEN_WIDTH - 7, 14)]:
            pyxel.rect(tx, ty + 4, 4, 3, COLOR_BROWN)
            pyxel.rect(tx, ty, 4, 4, COLOR_ORANGE)
            pyxel.pset(tx + (1 if fc % 4 < 2 else 2), ty, COLOR_YELLOW)
            pyxel.pset(tx + 1, ty + 1, COLOR_WHITE)

        # Central Golden Title Frame
        title_text = t("choose_hero")
        tt_w = renderer.get_text_width(title_text)
        tb_w = tt_w + 24
        tb_x = SCREEN_WIDTH // 2 - tb_w // 2
        renderer.draw_box(tb_x, 3, tb_w, 18, bg_col=COLOR_BLACK, border_col=COLOR_YELLOW)
        pyxel.rectb(tb_x + 1, 4, tb_w - 2, 16, COLOR_ORANGE)
        renderer.draw_text(SCREEN_WIDTH // 2 - tt_w // 2, 8, title_text, COLOR_YELLOW)

        # =====================================================================
        # 2. THREE HERO SELECTION CARDS (y=28 to y=108)
        # =====================================================================
        card_w, card_h = 78, 80
        x_offsets = [6, 89, 172]
        card_y = 28

        from src.data.classes import CLASS_REGISTRY

        # Class weapon badge icons in Bank 0
        weapon_badges = {
            "warrior": (72, 0),   # Sword
            "rogue": (32, 16),    # Dagger
            "mage": (56, 16),     # Staff with orb
        }
        sprite_coords = {
            "warrior": (0, 0),
            "rogue": (0, 32),
            "mage": (16, 32),
        }

        pulse = (fc // 6) % 2

        for i, cls_id in enumerate(self.classes):
            card_x = x_offsets[i]
            is_selected = (i == self.selected_index)
            border_col = COLOR_YELLOW if is_selected else COLOR_LIGHT_BLUE
            fill_col = COLOR_DARK_BLUE if is_selected else COLOR_BLACK

            renderer.draw_box(card_x, card_y, card_w, card_h, bg_col=fill_col, border_col=border_col)

            # Selected Gold Studs & Double Border
            if is_selected:
                pyxel.rectb(card_x + 1, card_y + 1, card_w - 2, card_h - 2, COLOR_YELLOW if pulse == 0 else COLOR_ORANGE)
                # Corner accents
                pyxel.pset(card_x + 2, card_y + 2, COLOR_WHITE)
                pyxel.pset(card_x + card_w - 3, card_y + 2, COLOR_WHITE)
                pyxel.pset(card_x + 2, card_y + card_h - 3, COLOR_WHITE)
                pyxel.pset(card_x + card_w - 3, card_y + card_h - 3, COLOR_WHITE)

            # Top-Left Icon Badge Box (14x14)
            badge_x, badge_y = card_x + 4, card_y + 4
            pyxel.rect(badge_x, badge_y, 14, 14, COLOR_NAVY)
            pyxel.rectb(badge_x, badge_y, 14, 14, COLOR_LIGHT_BLUE if not is_selected else COLOR_YELLOW)
            wu, wv = weapon_badges.get(cls_id, (72, 0))
            pyxel.blt(badge_x + 3, badge_y + 3, 0, wu, wv, 8, 8, 0)

            # Class Name & Archetype
            cls_def = CLASS_REGISTRY[cls_id]
            renderer.draw_text(card_x + 22, card_y + 5, cls_def.localized_name, COLOR_YELLOW if is_selected else COLOR_WHITE)
            archetype = t(f"arch_{cls_id}")
            renderer.draw_text(card_x + 22, card_y + 13, archetype, COLOR_GRAY)

            # Stone Floor & Champion Cast Shadow
            floor_y = card_y + card_h - 14
            pyxel.line(card_x + 6, floor_y + 6, card_x + card_w - 7, floor_y + 6, COLOR_NAVY)
            pyxel.elli(card_x + card_w // 2 - 12, floor_y + 2, 24, 6, COLOR_NAVY)

            # Hero Sprite
            pu, pv = sprite_coords.get(cls_id, (0, 0))
            sprite_x = card_x + (card_w - 16) // 2
            sprite_y = card_y + 40
            pyxel.blt(sprite_x, sprite_y, 0, pu, pv, 16, 16, 0)

            # Drawn weapons/effects
            if cls_id == "warrior":
                pyxel.line(sprite_x + 14, sprite_y + 6, sprite_x + 21, sprite_y - 1, COLOR_CYAN)
                pyxel.line(sprite_x + 15, sprite_y + 6, sprite_x + 22, sprite_y - 1, COLOR_WHITE)
            elif cls_id == "rogue":
                pyxel.line(sprite_x - 3, sprite_y + 11, sprite_x + 1, sprite_y + 7, COLOR_WHITE)
                pyxel.line(sprite_x + 15, sprite_y + 7, sprite_x + 19, sprite_y + 11, COLOR_WHITE)
            elif cls_id == "mage":
                pyxel.line(sprite_x + 13, sprite_y + 14, sprite_x + 19, sprite_y + 2, COLOR_BROWN)
                pyxel.circ(sprite_x + 19, sprite_y + 2, 2, COLOR_CYAN)
                pyxel.pset(sprite_x + 19, sprite_y + 2, COLOR_WHITE)
                if (fc // 6) % 2 == 0:
                    pyxel.pset(sprite_x + 23, sprite_y + 5, COLOR_CYAN)
                    pyxel.pset(sprite_x - 4, sprite_y + 10, COLOR_CYAN)

        # =====================================================================
        # 3. DUAL-CHAMBER DETAIL PANEL (y=112 to y=222)
        # =====================================================================
        panel_x, panel_y, panel_w, panel_h = 6, 112, SCREEN_WIDTH - 12, 110
        renderer.draw_box(panel_x, panel_y, panel_w, panel_h, bg_col=COLOR_DARK_BLUE, border_col=COLOR_LIGHT_BLUE)
        pyxel.rectb(panel_x + 1, panel_y + 1, panel_w - 2, panel_h - 2, COLOR_NAVY)

        sel_cls_id = self.classes[self.selected_index]
        sel_cls_def = CLASS_REGISTRY[sel_cls_id]

        # --- LEFT ALCOVE: Stone Chamber with Hero Standing ---
        alcove_w = 58
        pyxel.rect(panel_x + 2, panel_y + 2, alcove_w, panel_h - 4, COLOR_NAVY)
        # Masonry stone lines
        for ay in range(panel_y + 6, panel_y + panel_h - 10, 8):
            pyxel.line(panel_x + 2, ay, panel_x + 1 + alcove_w, ay, COLOR_DARK_BLUE)
            offset = 4 if (ay // 8) % 2 == 0 else alcove_w // 2
            pyxel.pset(panel_x + 2 + offset, ay + 4, COLOR_GRAY)

        # Hanging Crimson Wall Banner in Alcove
        hbx, hby = panel_x + 6, panel_y + 6
        pyxel.rect(hbx, hby, 12, 24, COLOR_RED)
        pyxel.tri(hbx, hby + 24, hbx + 6, hby + 30, hbx + 11, hby + 24, COLOR_RED)
        pyxel.rectb(hbx, hby, 12, 24, COLOR_ORANGE)
        pyxel.pset(hbx + 5, hby + 10, COLOR_YELLOW)
        pyxel.pset(hbx + 6, hby + 10, COLOR_YELLOW)

        # Stone Pedestal & Shadow
        ped_x = panel_x + 14
        ped_y = panel_y + panel_h - 22
        pyxel.elli(ped_x, ped_y + 10, 32, 8, COLOR_BLACK)

        # Selected Hero Sprite in Alcove
        pu, pv = sprite_coords.get(sel_cls_id, (0, 0))
        hx = ped_x + 8
        hy = ped_y - 4
        pyxel.blt(hx, hy, 0, pu, pv, 16, 16, 0)

        if sel_cls_id == "warrior":
            pyxel.line(hx + 14, hy + 6, hx + 21, hy - 1, COLOR_CYAN)
            pyxel.line(hx + 15, hy + 6, hx + 22, hy - 1, COLOR_WHITE)
        elif sel_cls_id == "rogue":
            pyxel.line(hx - 3, hy + 11, hx + 1, hy + 7, COLOR_WHITE)
            pyxel.line(hx + 15, hy + 7, hx + 19, hy + 11, COLOR_WHITE)
        elif sel_cls_id == "mage":
            pyxel.line(hx + 13, hy + 14, hx + 19, hy + 2, COLOR_BROWN)
            pyxel.circ(hx + 19, hy + 2, 2, COLOR_CYAN)
            pyxel.pset(hx + 19, hy + 2, COLOR_WHITE)

        # Vertical Divider Line
        div_x = panel_x + alcove_w + 3
        pyxel.line(div_x, panel_y + 4, div_x, panel_y + panel_h - 5, COLOR_LIGHT_BLUE)

        # --- RIGHT DETAILS: Name, Description, Stats & Skills ---
        content_x = div_x + 6

        # Class Name & Description
        renderer.draw_text(content_x, panel_y + 6, sel_cls_def.localized_name, COLOR_YELLOW)
        for i, line in enumerate(renderer.wrap_text(sel_cls_def.localized_description, max_chars_per_line=36)):
            renderer.draw_text(content_x, panel_y + 16 + (i * 9), line, COLOR_WHITE)

        # --- ATTRIBUTES (Left sub-column) ---
        stat_x = content_x
        stats = sel_cls_def.base_stats
        growth = sel_cls_def.growth_per_level

        # HP
        self._draw_stat_icon(stat_x, panel_y + 36, "hp")
        renderer.draw_text(stat_x + 8, panel_y + 36, f"HP:  {stats.max_hp} (+{growth.max_hp}/lvl)", COLOR_WHITE)

        # ATK
        self._draw_stat_icon(stat_x, panel_y + 46, "atk")
        renderer.draw_text(stat_x + 8, panel_y + 46, f"ATK: {stats.attack} (+{growth.attack})", COLOR_WHITE)

        # DEF
        self._draw_stat_icon(stat_x, panel_y + 56, "def")
        renderer.draw_text(stat_x + 8, panel_y + 56, f"DEF: {stats.defense} (+{growth.defense})", COLOR_WHITE)

        # SPD
        self._draw_stat_icon(stat_x, panel_y + 66, "spd")
        renderer.draw_text(stat_x + 8, panel_y + 66, f"SPD: {stats.speed} (+{growth.speed})", COLOR_WHITE)

        # CRIT
        self._draw_stat_icon(stat_x, panel_y + 76, "crit")
        crit_pct = int(stats.crit_chance * 100)
        renderer.draw_text(stat_x + 8, panel_y + 76, f"CRIT: {crit_pct}%", COLOR_WHITE)

        # Vertical Sub-divider
        sub_div_x = stat_x + 94
        pyxel.line(sub_div_x, panel_y + 34, sub_div_x, panel_y + 86, COLOR_NAVY)

        # --- STARTING SKILL (Right sub-column) ---
        skill_x = sub_div_x + 6
        from src.systems.abilities import get_ability_by_id
        starting_skill_id = sel_cls_def.starting_abilities[0] if sel_cls_def.starting_abilities else "None"
        skill = get_ability_by_id(starting_skill_id)

        if skill:
            renderer.draw_text(skill_x, panel_y + 36, f"Skill: {skill.localized_name}", COLOR_CYAN)

            # Skill Thumbnail Frame (14x14)
            sbox_x, sbox_y = skill_x, panel_y + 47
            pyxel.rect(sbox_x, sbox_y, 14, 14, COLOR_NAVY)
            pyxel.rectb(sbox_x, sbox_y, 14, 14, COLOR_LIGHT_BLUE)
            self._draw_skill_glyph(sbox_x + 1, sbox_y + 1, skill.id)

            # Skill Description
            s_lines = renderer.wrap_text(skill.localized_description, max_chars_per_line=13)
            for si, sline in enumerate(s_lines[:3]):
                renderer.draw_text(sbox_x + 18, sbox_y + (si * 9), sline, COLOR_WHITE)

        # Best For / Promotions Footer Line
        promos_str = ", ".join(t(f"class_{p}_name") for p in sel_cls_def.promotions)
        promo_label = f"Promociones: {promos_str}" if i18n.locale == "es" else f"Best for: {promos_str}"
        renderer.draw_text(content_x, panel_y + panel_h - 13, promo_label, COLOR_PEACH)

        # =====================================================================
        # 4. BOTTOM ACTION CONTROL BAR (y=228 to y=248)
        # =====================================================================
        # Back Button with Left Arrow
        renderer.draw_button(6, 228, 58, 18, "◄ [ BACK ]" if i18n.locale == "en" else "◄ [ VOLVER ]", bg_col=COLOR_BLACK, border_col=COLOR_GRAY, text_col=COLOR_WHITE)

        # Central Route Selection Toggle
        mode_label = t("route_fate") if self.route_mode == "FATE" else t("route_pathfinder")
        renderer.draw_button(70, 228, 96, 18, mode_label, bg_col=COLOR_BLACK, border_col=COLOR_DARK_BLUE, text_col=COLOR_YELLOW if self.route_mode == "PATHFINDER" else COLOR_WHITE)

        # Begin Journey Button with Golden Border and Play Triangle
        b_label = "► [ BEGIN ]" if i18n.locale == "en" else "► [ INICIAR ]"
        renderer.draw_button(172, 228, 78, 18, b_label, bg_col=COLOR_BLACK, border_col=COLOR_YELLOW, text_col=COLOR_YELLOW)


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


class CreditsView(View):
    """Renders the game's credits screen."""

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_ESCAPE) or Renderer.is_clicked(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT):
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
            renderer.draw_text(30, 30, t("replace_ability_prompt", type=self.selected_ability.ability_type.name), COLOR_YELLOW)
            renderer.draw_text(30, 45, t("replace_ability_new", name=self.selected_ability.localized_name), COLOR_LIME)

            target_list = game_state.player.abilities.active if self.selected_ability.ability_type == AbilityType.ACTIVE else game_state.player.abilities.passive
            for i, ab in enumerate(target_list):
                y_pos = 70 + (i * 30)
                renderer.draw_box(30, y_pos, w - 60, 25, bg_col=COLOR_DARK_BLUE, border_col=COLOR_WHITE)
                renderer.draw_text(40, y_pos + 8, f"[{i + 1}] {ab.localized_name}: {ab.localized_description[:30]}...", COLOR_WHITE)

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
        if pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.KEY_SPACE) or Renderer.is_clicked(SCREEN_WIDTH - 90, 230, 80, 16):
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
            sell_action = pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_S) or Renderer.is_clicked(12, 230, 40, 16)

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

        renderer.draw_button(SCREEN_WIDTH - 90, 230, 80, 16, t("btn_leave_shop"), bg_col=COLOR_BLACK, text_col=COLOR_PEACH)


class LootView(View):
    """Renders the post-combat loot screen."""

    def update(self, game_state: GameState) -> None:
        if (pyxel.btnp(pyxel.KEY_1) or Renderer.is_clicked(20, 90, SCREEN_WIDTH - 40, 25)) and len(game_state.pending_loot) > 0:
            self._take_loot(game_state, 0)
        elif (pyxel.btnp(pyxel.KEY_2) or Renderer.is_clicked(20, 120, SCREEN_WIDTH - 40, 25)) and len(game_state.pending_loot) > 1:
            self._take_loot(game_state, 1)
        elif (pyxel.btnp(pyxel.KEY_3) or Renderer.is_clicked(20, 150, SCREEN_WIDTH - 40, 25)) and len(game_state.pending_loot) > 2:
            self._take_loot(game_state, 2)
        elif pyxel.btnp(pyxel.KEY_SPACE) or Renderer.is_clicked(96, SCREEN_HEIGHT - 30, 68, 16):
            for i in range(len(game_state.pending_loot) - 1, -1, -1):
                self._take_loot(game_state, i, play_sound=False)
            pyxel.play(0, 3)
        elif pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_C) or Renderer.is_clicked(170, SCREEN_HEIGHT - 30, 74, 16):
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
                if item.stats_bonus.attack > 0:
                    bonus_str = f"+{item.stats_bonus.attack} ATK"
                elif item.stats_bonus.defense > 0:
                    bonus_str = f"+{item.stats_bonus.defense} DEF"
                elif item.stats_bonus.speed > 0:
                    bonus_str = f"+{item.stats_bonus.speed} SPD"
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
                    renderer.draw_text(90, y_offset + 15, t("merchant_heals", amount=f"{item.heal_amount} HP"), COLOR_GREEN)

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
        if game_state.current_mode in (GameMode.MAP, GameMode.COMBAT, GameMode.EVENTS, GameMode.INVENTORY, GameMode.LOOT, GameMode.SHOP):
            inv_clicked = Renderer.is_clicked(222, 3, 30, 16)
            if pyxel.btnp(pyxel.KEY_I) or inv_clicked or (game_state.current_mode == GameMode.INVENTORY and pyxel.btnp(pyxel.KEY_ESCAPE)):
                game_state.toggle_inventory()
                return

        view = self.views.get(game_state.current_mode)
        if view:
            view.update(game_state)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        view = self.views.get(game_state.current_mode)
        if view:
            view.draw(game_state, renderer)