"""View switching architecture including CombatView, MapView, and InventoryView."""

from __future__ import annotations

import pyxel

from src.config import (
    COLOR_BLACK,
    COLOR_CYAN,
    COLOR_DARK_BLUE,
    COLOR_GRAY,
    COLOR_GREEN,
    COLOR_LIGHT_BLUE,
    COLOR_LIME,
    COLOR_NAVY,
    COLOR_ORANGE,
    COLOR_PEACH,
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    SCREEN_HEIGHT,
    SCREEN_WIDTH, COLOR_BROWN,
)
from src.core.game_state import GameMode
from typing import TYPE_CHECKING

from src.entities import Enemy

if TYPE_CHECKING:
    from src.core.game_state import GameState
from src.systems.combat import ACTION_THRESHOLD
from src.systems.inventory import EquipSlot, MAX_BELT_SLOTS, MAX_POUCH_SLOTS
from src.systems.abilities import Ability, AbilityRarity, AbilityType, get_random_abilities
from src.systems.map_gen import NodeType
from src.ui.renderer import Renderer
from src.core.i18n import i18n, t

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
            pyxel.play(0, 3) # SND_CLICK
            game_state.advance_act(target_biome_id=biome_a_id)
        elif pyxel.btnp(pyxel.KEY_2) or Renderer.is_clicked(132, 42, 116, 172):
            pyxel.play(0, 3) # SND_CLICK
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
            renderer.draw_text(x_offset + 6, curr_y, biome.name[:17], COLOR_YELLOW)
            curr_y += 11

            # Tags
            for tag_line in renderer.wrap_text(biome.theme_tags, max_chars_per_line=18):
                renderer.draw_text(x_offset + 6, curr_y, tag_line, 3) # COLOR_CYAN / 3
                curr_y += 9
            curr_y += 3

            # Description
            for desc_line in renderer.wrap_text(biome.description, max_chars_per_line=18):
                renderer.draw_text(x_offset + 6, curr_y, desc_line, COLOR_WHITE)
                curr_y += 9
            curr_y += 4

            # Threats
            renderer.draw_text(x_offset + 6, curr_y, t("biome_threats"), COLOR_ORANGE)
            curr_y += 9

            from src.entities.enemy import ENEMY_CATALOG
            for e_id in biome.basic_enemies[:2]:
                e_name = ENEMY_CATALOG[e_id].name[:16] if e_id in ENEMY_CATALOG else e_id.replace('_', ' ').title()[:16]
                renderer.draw_text(x_offset + 8, curr_y, f"- {e_name}", COLOR_GRAY)
                curr_y += 9
            curr_y += 4

            # Bosses
            renderer.draw_text(x_offset + 6, curr_y, t("biome_bosses"), 14) # COLOR_PINK / 14
            curr_y += 9
            for b_id in biome.bosses:
                b_name = ENEMY_CATALOG[b_id].name[:16] if b_id in ENEMY_CATALOG else b_id.replace('_', ' ').title()[:16]
                renderer.draw_text(x_offset + 8, curr_y, f"- {b_name}", COLOR_GRAY)
                curr_y += 9

            renderer.draw_button(x_offset + 10, 42 + 172 - 22, 96, 16, t("btn_choose_route"), bg_col=COLOR_BLACK, text_col=COLOR_WHITE)


class MapView(View):
    """Visualizes the Spire node tree and node selection."""

    def update(self, game_state: GameState) -> None:
        if Renderer.is_clicked(18, 44, 200, 10):
            game_state.toggle_inventory()
            return

        available = game_state.map_graph.available_nodes

        floors = game_state.map_graph.floors
        total_floors = len(floors)
        lane_w = (SCREEN_WIDTH - 60) // 4

        for f_idx, floor in enumerate(floors):
            y_pos = 200 - int((f_idx / max(1, total_floors - 1)) * 140)
            for node in floor:
                x_pos = 35 + node.lane * lane_w
                if node in available and Renderer.is_clicked(x_pos - 2, y_pos - 2, 17, 15):
                    pyxel.play(0, 3)
                    game_state.select_map_node(node.id)
                    return

        for idx, node in enumerate(available):
            key = getattr(pyxel, f"KEY_{idx + 1}", None)
            if key and pyxel.btnp(key):
                pyxel.play(0, 3)  # Sound 3: Menu Click
                game_state.select_map_node(node.id)
                break

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        renderer.draw_box(10, 28, SCREEN_WIDTH - 20, SCREEN_HEIGHT - 38, bg_col=COLOR_BLACK, border_col=COLOR_DARK_BLUE)
        from src.data.biomes import get_biome
        biome = get_biome(game_state.current_biome)
        if biome:
            renderer.draw_text(18, 34, t("act_header", act=game_state.act, biome_name=biome.name), COLOR_YELLOW)
        else:
            renderer.draw_text(18, 34, t("spire_header"), COLOR_YELLOW)
        renderer.draw_text(18, 44, t("select_path_prompt"), COLOR_GRAY)

        floors = game_state.map_graph.floors
        available_ids = {n.id for n in game_state.map_graph.available_nodes}
        current_id = game_state.map_graph.current_node_id

        total_floors = len(floors)
        lane_w = (SCREEN_WIDTH - 60) // 4

        # Connection lines
        for f_idx, floor in enumerate(floors):
            y_pos = 200 - int((f_idx / max(1, total_floors - 1)) * 140)
            for node in floor:
                x_pos = 35 + node.lane * lane_w
                for out_id in node.outgoing_ids:
                    out_node = game_state.map_graph.nodes_by_id.get(out_id)
                    if out_node:
                        out_y = 200 - int((out_node.floor / max(1, total_floors - 1)) * 140)
                        out_x = 35 + out_node.lane * lane_w
                        line_col = COLOR_WHITE if (node.id == current_id or node.id in available_ids) else COLOR_NAVY
                        pyxel.line(x_pos + 6, y_pos + 4, out_x + 6, out_y + 4, line_col)

        node_icons = {
            NodeType.COMBAT: ("M", COLOR_RED),
            NodeType.ELITE: ("E", COLOR_PURPLE),
            NodeType.REST: ("R", COLOR_GREEN),
            NodeType.SHOP: ("$", COLOR_YELLOW),
            NodeType.TREASURE: ("T", COLOR_ORANGE),
            NodeType.EVENT: ("?", COLOR_CYAN if hasattr(pyxel, "COLOR_CYAN") else COLOR_LIGHT_BLUE),
            NodeType.BOSS: ("B", COLOR_PEACH),
        }

        option_index = 1
        for f_idx, floor in enumerate(floors):
            y_pos = 200 - int((f_idx / max(1, total_floors - 1)) * 140)
            for node in floor:
                x_pos = 35 + node.lane * lane_w
                icon_char, color = node_icons.get(node.node_type, ("?", COLOR_WHITE))

                is_curr = node.id == current_id
                is_avail = node.id in available_ids

                bg_c = COLOR_WHITE if is_curr else (COLOR_DARK_BLUE if is_avail else COLOR_BLACK)
                border_c = COLOR_YELLOW if is_avail else COLOR_GRAY

                pyxel.rect(x_pos, y_pos, 13, 11, bg_c)
                pyxel.rectb(x_pos, y_pos, 13, 11, border_c)

                # 8x8 icons for Rest & Treasure; text fallback for others
                if node.node_type == NodeType.REST and not is_curr:
                    pyxel.blt(x_pos + 3, y_pos + 1, 0, 88, 0, 8, 8, 0)
                elif node.node_type == NodeType.TREASURE and not is_curr:
                    pyxel.blt(x_pos + 3, y_pos + 1, 0, 96, 0, 8, 8, 0)
                elif node.node_type == NodeType.SHOP and not is_curr:
                    pyxel.blt(x_pos + 3, y_pos + 1, 0, 104, 0, 8, 8, 0)
                else:
                    renderer.draw_text(x_pos + 4, y_pos + 3, icon_char, color if not is_curr else COLOR_BLACK)

                if is_avail:
                    renderer.draw_text(x_pos + 3, y_pos - 9, f"[{option_index}]", COLOR_YELLOW)
                    option_index += 1


class CombatView(View):
    """Renders active auto-battle arena, sprites, tick gauges, and battle logs."""

    def update(self, game_state: GameState) -> None:
        if game_state.combat is None:
            return

        # Advance combat: space, auto-tick, or tap anywhere on arena / combat log
        if pyxel.btnp(pyxel.KEY_SPACE) or (pyxel.frame_count % 15 == 0) or Renderer.is_clicked(0, 166, SCREEN_WIDTH, 82) or Renderer.is_clicked(0, 20, SCREEN_WIDTH, 100):
            game_state.update_combat()

        # In-combat quick belt triggers: Keys [1, 2, 3] or Tap
        slot_positions = [40, 110, 180]
        for idx, key in enumerate((pyxel.KEY_1, pyxel.KEY_2, pyxel.KEY_3)):
            bx = slot_positions[idx] if idx < len(slot_positions) else 40 + idx * 70
            if pyxel.btnp(key) or Renderer.is_clicked(bx, 130, 66, 18):
                if game_state.player.inventory.use_belt_item(idx, game_state.player):
                    pyxel.play(1, 2)  # Sound 2: Potion Heal chime
                    game_state.combat.combat_logs.append(
                        t("combat_belt_use", player=game_state.player.name, slot=idx+1)
                    )

        # Active Abilities: Keys [4, 5] or Tap
        for idx, key in enumerate((pyxel.KEY_4, pyxel.KEY_5)):
            x_pos = 46 + idx * 95
            if (pyxel.btnp(key) or Renderer.is_clicked(x_pos - 4, 146, 90, 14)) and idx < len(game_state.player.abilities.active):
                if game_state.combat.ability_cooldown <= 0:
                    game_state.combat.queued_ability = game_state.player.abilities.active[idx]
                    game_state.combat.ability_cooldown = 3
                    game_state.combat.combat_logs.append(t("combat_queued", ability=game_state.player.abilities.active[idx].name))
                else:
                    game_state.combat.combat_logs.append(t("combat_cooldown", cooldown=game_state.combat.ability_cooldown))

    def _get_enemy_sprite(self, enemy: Enemy) -> tuple[int, int]:
        """Resolve Bank 0 (u, v) tile coordinates for any enemy instance."""
        arch_id = getattr(enemy, "archetype_id", None)
        if arch_id and arch_id in ENEMY_SPRITE_COORDS:
            return ENEMY_SPRITE_COORDS[arch_id]

        name_lower = enemy.name.lower()
        for key, coords in ENEMY_SPRITE_COORDS.items():
            if key.replace("_", " ") in name_lower:
                return coords

        # 3. Fallback to default legacy row (y=0)
        tier_val = enemy.tier.value if hasattr(enemy.tier, "value") else int(enemy.tier)
        if tier_val >= 4 or "lich" in name_lower or "dragon" in name_lower:
            return (48, 0)
        if "goblin" in name_lower or "scavenger" in name_lower or "cultist" in name_lower:
            return (32, 0)
        return (16, 0)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        if game_state.combat is None:
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

        # Hero sprite
        sprite_map = {
            "warrior": (0, 0),
            "rogue": (0, 32),
            "mage": (16, 32),
        }
        pu, pv = sprite_map.get(game_state.player.class_id, (0, 0))
        pyxel.blt(100, 32, 0, pu, pv, 16, 16, 0)

        # Enemy Stat Panel
        enemy_display = combat.enemy.name if len(combat.enemy.name) <= 14 else combat.enemy.name[:13] + "."
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

        # Dynamic Biome Enemy Sprite
        eu, ev = self._get_enemy_sprite(combat.enemy)
        pyxel.blt(224, 32, 0, eu, ev, 16, 16, 0)

        # Action Tick Meter (Player vs Enemy)
        renderer.draw_text(10, 110, t("tick_gauges"), COLOR_YELLOW)
        renderer.draw_bar(10, 118, 112, 5, combat.player_gauge, ACTION_THRESHOLD, fill_col=COLOR_LIGHT_BLUE,
                          bg_col=COLOR_BLACK)
        renderer.draw_bar(134, 118, 112, 5, combat.enemy_gauge, ACTION_THRESHOLD, fill_col=COLOR_ORANGE,
                          bg_col=COLOR_BLACK)

        # In-Combat Quick Belt Display
        renderer.draw_box(10, 126, SCREEN_WIDTH - 20, 36, bg_col=COLOR_NAVY, border_col=COLOR_DARK_BLUE)
        renderer.draw_text(14, 129, t("belt"), COLOR_YELLOW)
        inv = game_state.player.inventory

        slot_positions = [40, 110, 180]

        for b_idx in range(MAX_BELT_SLOTS):
            if b_idx < len(slot_positions):
                bx = slot_positions[b_idx]
            else:
                bx = 40 + b_idx * 70

            b_item = inv.belt[b_idx]
            name = b_item.name[:9] if b_item else t("empty_slot_short")

            # Line 1: [i+1] and Item Name
            renderer.draw_text(bx, 129, f"[{b_idx+1}] {name}", COLOR_WHITE if b_item else COLOR_GRAY)

            # Line 2: Heal effect (if present)
            if b_item:
                renderer.draw_text(bx, 137, f"+{b_item.heal_amount}HP", COLOR_LIME)

        # Abilities panel
        # Placed under the belt hotkeys
        renderer.draw_text(14, 148, t("skills"), COLOR_YELLOW)
        for a_idx, active_ab in enumerate(game_state.player.abilities.active):
            x_pos = 46 + a_idx * 95
            key_label = "4" if a_idx == 0 else "5"
            queued_marker = "*" if game_state.combat and game_state.combat.queued_ability == active_ab else " "
            renderer.draw_text(x_pos, 148, f"[{key_label}]{queued_marker} {active_ab.name[:14]}", COLOR_LIME)

        # Combat activity logs
        renderer.draw_combat_logs(
            logs=combat.combat_logs,
            x=10,
            y=166,
            w=SCREEN_WIDTH - 20,
            h=82,
            max_entries=7,
        )


class InventoryView(View):
    """Renders 6+2 Equipment, 10-slot Pouch, and 3-slot Belt."""

    def __init__(self) -> None:
        self.active_pane: str = "POUCH" # "POUCH" or "EQUIPMENT"
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

        from src.systems.inventory import EquipmentItem, ConsumableItem, EquipSlot
        inv = game_state.player.inventory

        # Direct item selection by tapping
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
                        # Find empty belt slot
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

            # Assign to belt 1, 2, 3
            for idx, key in enumerate((pyxel.KEY_1, pyxel.KEY_2, pyxel.KEY_3)):
                if pyxel.btnp(key) or Renderer.is_clicked(100 + idx*20, 228, 16, 16):
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

        # Still allow using belt items from anywhere just for convenience?
        # Actually, instructions specify belt assignments via [1-3] in pouch mode.
        # It doesn't explicitly restrict use_belt_item when not in pouch mode but we can ignore it
        # or leave the default update if we wanted. But the prompt says "When in Pouch Pane: [1-3]: Assign selected consumable"
        # In Map/Combat we might use belt items. In inventory, [1-3] are used for assignment.

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        renderer.draw_box(5, 26, SCREEN_WIDTH - 10, SCREEN_HEIGHT - 32, bg_col=COLOR_BLACK, border_col=COLOR_GRAY)

        inv = game_state.player.inventory
        from src.systems.inventory import EquipSlot, EquipmentItem, ConsumableItem

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
            item_name = item.name if item else f"({t('empty_slot_short')})"
            slot_label_map = {
                "HEAD": t("slot_head_short"), "SHOULDERS": t("slot_shld_short"), "CHEST": t("slot_chest_short"),
                "WAIST": t("slot_waist_short"), "HANDS": t("slot_hands_short"), "LEGS": t("slot_legs_short"),
                "MAIN_HAND": t("slot_main_short"), "OFF_HAND": t("slot_off_short")
            }
            slot_label = slot_label_map.get(slot.name, slot.name)

            # Highlight if selected
            label_col = COLOR_WHITE if self.active_pane == "EQUIPMENT" and self.equip_cursor == i else COLOR_GRAY
            renderer.draw_text(x, y, f"{cursor_str}{slot_label}", label_col)
            renderer.draw_text(x + 40, y, item_name[:11], COLOR_LIME if item else COLOR_DARK_BLUE)

        # 3-Slot Belt
        renderer.draw_text(10, 96, t("belt_header"), COLOR_YELLOW)
        for b_idx in range(MAX_BELT_SLOTS):
            x = 10 + b_idx * 78
            y = 106
            b_item = inv.belt[b_idx]
            name = b_item.name if b_item else t("empty_slot_short")
            renderer.draw_box(x, y, 74, 18, bg_col=COLOR_NAVY, border_col=COLOR_WHITE)
            renderer.draw_text(x + 4, y + 3, f"[{b_idx+1}]", COLOR_YELLOW)
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
                renderer.draw_text(x, y, f"{cursor_str}{p_item.name[:10]}", item_col)

                # Show stats if equipment, heal if consumable
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

        # Bottom Panel Context Hints
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

        # Feedback Message
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

        # Check for card clicks
        card_w, card_h = 74, 84
        x_offsets = [10, 91, 172]
        card_y = 34

        for i, card_x in enumerate(x_offsets):
            if Renderer.is_clicked(card_x, card_y, card_w, card_h):
                if self.selected_index == i:
                    # Double click / confirm
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

        # Header
        renderer.draw_box(0, 10, SCREEN_WIDTH, 20, bg_col=COLOR_NAVY, border_col=COLOR_GRAY)
        title = t("choose_hero")
        renderer.draw_text(SCREEN_WIDTH // 2 - len(title) * 2, 16, title, COLOR_YELLOW)

        # Class Cards
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
            renderer.draw_text(card_x + 6, card_y + 6, cls_def.name, COLOR_YELLOW)

            archetype = ""
            if cls_id == "warrior":
                archetype = t("arch_warrior")
            elif cls_id == "rogue":
                archetype = t("arch_rogue")
            elif cls_id == "mage":
                archetype = t("arch_mage")

            renderer.draw_text(card_x + 6, card_y + 16, archetype, COLOR_GRAY)

            sprite_map = {
                "warrior": (0, 0),
                "rogue": (0, 32),
                "mage": (16, 32),
            }
            pu, pv = sprite_map.get(cls_id, (0, 0))
            pyxel.blt(card_x + 29, card_y + 32, 0, pu, pv, 16, 16, 0)

            if is_selected:
                pyxel.rectb(card_x + 1, card_y + 1, card_w - 2, card_h - 2, 9) # COLOR_YELLOW is 9

        # Detail Panel
        detail_y = 122
        renderer.draw_box(10, detail_y, 236, 104, bg_col=COLOR_NAVY, border_col=COLOR_WHITE)

        sel_cls_id = self.classes[self.selected_index]
        sel_cls_def = CLASS_REGISTRY[sel_cls_id]

        renderer.draw_text(16, detail_y + 4, sel_cls_def.name, COLOR_YELLOW)

        # Word wrap description
        desc_lines = renderer.wrap_text(sel_cls_def.description, max_chars_per_line=36)
        for i, line in enumerate(desc_lines):
            renderer.draw_text(16, detail_y + 14 + (i * 9), line, COLOR_WHITE)

        stats = sel_cls_def.base_stats
        growth = sel_cls_def.growth_per_level
        renderer.draw_text(16, detail_y + 34, t("stat_hp_atk", max_hp=stats.max_hp, g_hp=growth.max_hp, atk=stats.attack, g_atk=growth.attack), COLOR_GRAY)
        renderer.draw_text(16, detail_y + 43, t("stat_def_spd", def_=stats.defense, g_def=growth.defense, spd=stats.speed, g_spd=growth.speed), COLOR_GRAY)
        renderer.draw_text(16, detail_y + 52, t("stat_crit_val", crit=int(stats.crit_chance * 100)), COLOR_GRAY)

        from src.systems.abilities import get_ability_by_id
        starting_skill_id = sel_cls_def.starting_abilities[0] if sel_cls_def.starting_abilities else "None"
        skill = get_ability_by_id(starting_skill_id)
        if skill:
            renderer.draw_text(16, detail_y + 62, t("stat_skill", skill_name=skill.name), COLOR_LIME)
            skill_lines = renderer.wrap_text(skill.description, max_chars_per_line=36)
            for i, line in enumerate(skill_lines):
                renderer.draw_text(16, detail_y + 71 + (i * 9), line, COLOR_WHITE)

        promotions = ", ".join(p.capitalize() for p in sel_cls_def.promotions)
        renderer.draw_text(16, detail_y + 83, t("class_promotions", promotions=promotions), COLOR_PEACH)

        # Footer
        renderer.draw_button(6, 230, 44, 18, t("btn_back"), bg_col=COLOR_BLACK, border_col=COLOR_GRAY)

        mode_label = t("route_fate") if self.route_mode == "FATE" else t("route_pathfinder")
        renderer.draw_button(54, 230, 104, 18, mode_label, bg_col=COLOR_BLACK, text_col=COLOR_YELLOW if self.route_mode == "PATHFINDER" else COLOR_WHITE)

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
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT
        fc = pyxel.frame_count

        # =============================================================
        # 1. MOONLIT SKY GRADIENT & CELESTIALS
        # =============================================================
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

        # Twinkling Stars
        stars = [(18, 38), (60, 46), (82, 36), (110, 42), (180, 40), (210, 48), (145, 50)]
        for idx, (sx, sy) in enumerate(stars):
            col = COLOR_WHITE if (fc + idx * 7) % 24 < 12 else COLOR_YELLOW
            pyxel.pset(sx, sy, col)

        # =============================================================
        # 2. DETAILED GOTHIC FORTRESS SKYLINE
        # =============================================================
        # Distant curtain wall
        pyxel.rect(48, 86, 160, 40, COLOR_NAVY)
        for wx in range(48, 208, 8):
            pyxel.rect(wx, 82, 4, 4, COLOR_NAVY)  # Battlements

        # Midground Gothic Citadel Towers
        citadel_towers = [
            # (x, base_y, width, height, has_spire, spire_h)
            (62, 126, 18, 48, True, 18),
            (84, 126, 22, 60, True, 22),
            (110, 126, 36, 72, True, 26),  # Central Great Cathedral
            (150, 126, 20, 56, True, 20),
            (174, 126, 18, 44, True, 16),
        ]

        for tx, ty, tw, th, has_spire, sh in citadel_towers:
            wall_top = ty - th
            # Tower body
            pyxel.rect(tx, wall_top, tw, th, COLOR_DARK_BLUE)
            # Stone brick mortar lines
            for my in range(wall_top + 4, ty, 6):
                pyxel.line(tx, my, tx + tw - 1, my, COLOR_NAVY)
                offset = 3 if (my // 6) % 2 == 0 else tw // 2
                pyxel.pset(tx + offset, my + 3, COLOR_GRAY)

            # Crenellations on parapet
            for cx in range(tx, tx + tw, 4):
                pyxel.rect(cx, wall_top - 3, 2, 3, COLOR_DARK_BLUE)

            # Spire cone
            if has_spire:
                spire_top = wall_top - sh - 3
                pyxel.tri(tx - 1, wall_top - 3, tx + tw // 2, spire_top, tx + tw + 1, wall_top - 3, COLOR_DARK_BLUE)
                # Golden / Iron Finial
                pyxel.line(tx + tw // 2, spire_top - 3, tx + tw // 2, spire_top, COLOR_YELLOW)

        # Great Cathedral Pointed Gothic Window (on central keep)
        gw_x, gw_y = 124, 76
        pyxel.rect(gw_x, gw_y + 4, 8, 12, COLOR_YELLOW if (fc // 15) % 2 == 0 else COLOR_ORANGE)
        pyxel.tri(gw_x, gw_y + 4, gw_x + 4, gw_y, gw_x + 7, gw_y + 4, COLOR_YELLOW)
        # Stone mullions forming a gothic window cross
        pyxel.line(gw_x + 3, gw_y + 1, gw_x + 3, gw_y + 15, COLOR_DARK_BLUE)
        pyxel.line(gw_x + 4, gw_y + 1, gw_x + 4, gw_y + 15, COLOR_DARK_BLUE)
        pyxel.line(gw_x, gw_y + 8, gw_x + 7, gw_y + 8, COLOR_DARK_BLUE)

        # Narrow arrow-slits on side towers
        pyxel.rect(70, 92, 2, 6, COLOR_ORANGE if (fc // 10) % 3 != 0 else COLOR_YELLOW)
        pyxel.rect(94, 82, 2, 7, COLOR_YELLOW if (fc // 10) % 2 == 0 else COLOR_ORANGE)
        pyxel.rect(159, 86, 2, 6, COLOR_ORANGE if (fc // 12) % 2 == 0 else COLOR_YELLOW)

        # =============================================================
        # 3. FLANKING STONE PILLARS WITH GARGOYLES & TORCHES
        # =============================================================
        # Left stone pillar
        pyxel.rect(0, 52, 24, 74, COLOR_DARK_BLUE)
        for py in range(52, 126, 6):
            pyxel.line(0, py, 23, py, COLOR_NAVY)
            stagger = 4 if (py // 6) % 2 == 0 else 14
            pyxel.pset(stagger, py + 3, COLOR_GRAY)
        pyxel.line(24, 52, 24, 126, COLOR_BLACK)

        # Left wall torch
        pyxel.rect(18, 92, 3, 2, COLOR_BROWN)
        pyxel.pset(19, 90, COLOR_ORANGE if (fc % 4 < 2) else COLOR_YELLOW)

        # Left gargoyle
        pyxel.blt(0, 22, 1, 168, 0, 24, 32, 0)

        # Right stone pillar
        pyxel.rect(w - 24, 52, 24, 74, COLOR_DARK_BLUE)
        for py in range(52, 126, 6):
            pyxel.line(w - 24, py, w, py, COLOR_NAVY)
            stagger = 4 if (py // 6) % 2 == 0 else 14
            pyxel.pset(w - 24 + stagger, py + 3, COLOR_GRAY)
        pyxel.line(w - 25, 52, w - 25, 126, COLOR_BLACK)

        # Right wall torch
        pyxel.rect(w - 21, 92, 3, 2, COLOR_BROWN)
        pyxel.pset(w - 20, 90, COLOR_YELLOW if (fc % 4 < 2) else COLOR_ORANGE)

        # Right gargoyle (flipped horizontally)
        pyxel.blt(w - 24, 22, 1, 168, 0, -24, 32, 0)

        # =============================================================
        # 4. RUGGED CRAG LEDGE, CHARACTERS & CAMPFIRE
        # =============================================================
        # Rocky cliff platform (textured, no harsh zebra stripes)
        pyxel.rect(16, 126, w - 32, 20, COLOR_BROWN)
        pyxel.line(16, 126, w - 16, 126, COLOR_PEACH)
        for rx in range(18, w - 18, 8):
            pyxel.pset(rx, 127, COLOR_BROWN)
            if rx % 16 == 0:
                pyxel.line(rx, 128, rx + 2, 134, COLOR_BLACK)

        # Campfire stone ring & warm light
        fire_x, fire_y = 114, 118
        pyxel.rect(fire_x - 3, fire_y + 7, 14, 2, COLOR_GRAY)
        pyxel.rect(fire_x - 1, fire_y + 8, 10, 1, COLOR_DARK_BLUE)
        # Warm ambient light on ground
        for ox in range(-12, 13):
            dist = abs(ox)
            if dist < 6:
                pyxel.pset(fire_x + 4 + ox, 126, COLOR_YELLOW)
            elif dist < 11:
                pyxel.pset(fire_x + 4 + ox, 126, COLOR_ORANGE if (fc + ox) % 2 == 0 else COLOR_PEACH)

        # Burning fire sprite
        pyxel.blt(fire_x, fire_y, 0, 88, 0, 8, 8, 0)
        # Rising spark particles
        for i in range(3):
            px = fire_x + 3 + ((fc * 2 + i * 5) % 5) - 2
            py = fire_y - ((fc + i * 7) % 10)
            pyxel.pset(px, py, COLOR_YELLOW if i % 2 == 0 else COLOR_ORANGE)

        # Hero Knight on left facing right
        pyxel.blt(76, 110, 0, 0, 0, 16, 16, 0)
        # Knight's drawn glowing blade
        pyxel.line(90, 116, 100, 106, COLOR_CYAN)
        pyxel.line(91, 116, 101, 106, COLOR_WHITE)

        # Humanoid Gothic Lich on right facing left
        pyxel.blt(148, 98, 1, 144, 0, 24, 28, 0)

        # =============================================================
        # 5. UNIFIED GILDED TITLE BANNER
        # =============================================================
        # Bank 1, 0, 0, 144, 32 centered at x = (256 - 144) // 2 = 56, y = 8
        pyxel.blt(56, 8, 1, 0, 0, 144, 32, 0)

        # =============================================================
        # 6. GOTHIC MENU DIALOG BOX
        # =============================================================
        box_x, box_y, box_w, box_h = 36, 148, 184, 78
        renderer.draw_box(box_x, box_y, box_w, box_h, bg_col=COLOR_NAVY, border_col=COLOR_WHITE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_YELLOW)

        # Four Corner Skulls
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

        # Flashing Footer Prompt
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
            count=2
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
            renderer.draw_text(30, 45, t("replace_ability_new", name=self.selected_ability.name), COLOR_LIME)

            target_list = game_state.player.abilities.active if self.selected_ability.ability_type == AbilityType.ACTIVE else game_state.player.abilities.passive
            for i, ab in enumerate(target_list):
                y_pos = 70 + (i * 30)
                renderer.draw_box(30, y_pos, w - 60, 25, bg_col=COLOR_DARK_BLUE, border_col=COLOR_WHITE)
                renderer.draw_text(40, y_pos + 8, f"[{i+1}] {ab.name}: {ab.description[:30]}...", COLOR_WHITE)

            renderer.draw_button(w - 80, h - 30, 70, 16, t("btn_cancel"), bg_col=COLOR_BLACK, text_col=COLOR_PEACH)
            renderer.draw_text(30, h - 30, t("replace_ability_instruction"), COLOR_PEACH)
            return

        renderer.draw_text(30, 30, t("levelup_ability_choice", rarity=self.pending_rarity), COLOR_YELLOW)

        for i, ab in enumerate(self.choices):
            y_offset = 60 + (i * 60)
            renderer.draw_box(30, y_offset, w - 60, 50, bg_col=COLOR_DARK_BLUE, border_col=COLOR_WHITE)
            renderer.draw_text(40, y_offset + 5, f"[{i+1}] {ab.name} ({ab.ability_type.name})", COLOR_LIME)

            # Simple text wrap for description
            desc = ab.description
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

            # Row selection & direct double-tap purchase
            for i in range(len(stock)):
                y = 75 + i * 16
                if Renderer.is_clicked(8, y, SCREEN_WIDTH - 24, 16):
                    if self.buy_cursor == i:
                        buy_action = True
                    else:
                        self.buy_cursor = i
                        self.feedback_msg = ""
                        buy_action = False # Prevent accidental buy on first tap

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
                        self.feedback_msg = t("shop_purchased", item=item.name)
                        self.feedback_success = True
                        if self.buy_cursor >= len(stock):
                            self.buy_cursor = max(0, len(stock) - 1)

        elif self.active_tab == "SELL":
            pouch = game_state.player.inventory.pouch

            sell_action = pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_S) or Renderer.is_clicked(12, 230, 40, 16)

            # Row selection & direct double-tap sale
            for i in range(len(pouch)):
                y = 75 + i * 14
                if Renderer.is_clicked(8, y, SCREEN_WIDTH - 24, 14):
                    if self.sell_cursor == i:
                        sell_action = True
                    else:
                        self.sell_cursor = i
                        self.feedback_msg = ""
                        sell_action = False # Prevent accidental sell on first tap

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
                        self.feedback_msg = t("shop_sold", item=popped.name, val=sell_value)
                        self.feedback_success = True
                        if self.sell_cursor >= len(game_state.player.inventory.pouch):
                            self.sell_cursor = max(0, len(game_state.player.inventory.pouch) - 1)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        # Header Box (y=24 to 52)
        renderer.draw_box(4, 24, SCREEN_WIDTH - 8, 28, bg_col=COLOR_NAVY, border_col=COLOR_GRAY)
        pyxel.blt(12, 28, 0, 32, 32, 16, 16, 0) # Merchant Sprite
        renderer.draw_text(32, 30, t("wandering_merchant"), COLOR_YELLOW)
        renderer.draw_text(32, 40, t("merchant_quote"), COLOR_WHITE)

        # Main Listing Frame (y=56 to 216)
        renderer.draw_box(4, 56, SCREEN_WIDTH - 8, 160, bg_col=COLOR_BLACK, border_col=COLOR_GRAY)

        # Tab Indicator
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
                    renderer.draw_text(16, y, item.name, color)

                    # Try to display some stats/info if equipment
                    from src.systems.inventory import EquipmentItem, ConsumableItem
                    if isinstance(item, EquipmentItem):
                        slot_str = t(f"slot_{item.slot.name.lower()}")
                        renderer.draw_text(16, y + 8, f"[{slot_str}]", COLOR_GRAY)
                    elif isinstance(item, ConsumableItem):
                        renderer.draw_text(16, y + 8, t("merchant_heals", amount=item.heal_amount), COLOR_LIME)

                    # Price
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
                    renderer.draw_text(16, y, item.name, color)

                    sell_value = max(5, item.gold_value // 2)
                    renderer.draw_text(190, y, f"{sell_value}G", COLOR_YELLOW)

        # Footer Panel (y=222 to 252)
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
            # Take all that can fit
            for i in range(len(game_state.pending_loot) - 1, -1, -1):
                self._take_loot(game_state, i, play_sound=False)
            pyxel.play(0, 3) # Play click sound once for take all
        elif pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_C) or Renderer.is_clicked(170, SCREEN_HEIGHT - 30, 74, 16):
            self._exit_loot(game_state)

    def _take_loot(self, game_state: GameState, index: int, play_sound: bool = True) -> None:
        item = game_state.pending_loot[index]
        if game_state.player.inventory.add_to_pouch(item):
            game_state.pending_loot.pop(index)
            if play_sound:
                pyxel.play(0, 3) # SND_CLICK

    def _exit_loot(self, game_state: GameState) -> None:
        # Check transition priority
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

        # Summary box
        renderer.draw_text(20, 55, t("spoils_exp", exp=game_state.last_exp_earned), COLOR_WHITE)
        renderer.draw_text(120, 55, t("spoils_gold", gold=game_state.last_gold_earned), COLOR_YELLOW)

        pouch_len = len(game_state.player.inventory.pouch)
        from src.systems.inventory import MAX_POUCH_SLOTS
        color = COLOR_RED if pouch_len >= MAX_POUCH_SLOTS else COLOR_LIME
        renderer.draw_text(20, 70, t("spoils_pouch_space", current=pouch_len, max=MAX_POUCH_SLOTS), color)

        if pouch_len >= MAX_POUCH_SLOTS:
            renderer.draw_text(140, 70, t("spoils_pouch_full"), COLOR_RED)

        # Loot List
        y_offset = 90
        for i, item in enumerate(game_state.pending_loot):
            renderer.draw_box(20, y_offset, w - 40, 25, bg_col=COLOR_DARK_BLUE, border_col=COLOR_WHITE)
            renderer.draw_text(25, y_offset + 5, f"[{i+1}] {item.name}", COLOR_LIME)

            from src.systems.inventory import EquipmentItem, ConsumableItem
            if isinstance(item, EquipmentItem):
                renderer.draw_text(25, y_offset + 15, t(f"slot_{item.slot.name.lower()}"), COLOR_GRAY)
                # Display basic stats
                stats = ""
                if item.stats_bonus.attack > 0: stats += f" ATK+{item.stats_bonus.attack}"
                if item.stats_bonus.defense > 0: stats += f" DEF+{item.stats_bonus.defense}"
                if item.stats_bonus.speed > 0: stats += f" SPD+{item.stats_bonus.speed}"
                renderer.draw_text(90, y_offset + 15, stats, COLOR_WHITE)
            elif isinstance(item, ConsumableItem):
                from src.data.items import StatPotion
                if isinstance(item, StatPotion):
                    renderer.draw_text(25, y_offset + 15, t("spoils_perm_elixir"), 15) # COLOR_PEACH / 15
                    bonus_str = ""
                    if item.stat_bonus.attack > 0: bonus_str = f"+{item.stat_bonus.attack} ATK"
                    elif item.stat_bonus.defense > 0: bonus_str = f"+{item.stat_bonus.defense} DEF"
                    elif item.stat_bonus.speed > 0: bonus_str = f"+{item.stat_bonus.speed} SPD"
                    elif item.stat_bonus.max_hp > 0: bonus_str = f"+{item.stat_bonus.max_hp} HP"
                    elif item.stat_bonus.crit_chance > 0: bonus_str = f"+{int(item.stat_bonus.crit_chance * 100)}% CRIT"
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
        # Check for inventory toggle only if in gameplay modes where HUD is shown
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