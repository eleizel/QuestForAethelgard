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
    SCREEN_WIDTH,
)
from src.core.game_state import GameMode, GameState
from src.systems.combat import ACTION_THRESHOLD
from src.systems.inventory import EquipSlot, MAX_BELT_SLOTS, MAX_POUCH_SLOTS
from src.systems.map_gen import NodeType
from src.ui.renderer import Renderer


class View:
    """Base abstract interface for game screens."""

    def update(self, game_state: GameState) -> None:
        """Handle screen-specific input and state logic."""
        pass

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        """Render screen contents."""
        pass


class MapView(View):
    """Visualizes the Spire node tree and node selection."""

    def update(self, game_state: GameState) -> None:
        available = game_state.map_graph.get_available_nodes()
        # Allow selecting next node via number keys 1-9
        for idx, node in enumerate(available):
            key = getattr(pyxel, f"KEY_{idx + 1}", None)
            if key and pyxel.btnp(key):
                game_state.select_map_node(node.id)
                break

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        renderer.draw_box(10, 28, SCREEN_WIDTH - 20, SCREEN_HEIGHT - 38, bg_col=COLOR_BLACK, border_col=COLOR_DARK_BLUE)
        pyxel.text(18, 34, "-- Spire of Aethelgard --", COLOR_YELLOW)
        pyxel.text(18, 44, "Select path: [1-4] Choose Node | [I] Inventory", COLOR_GRAY)

        floors = game_state.map_graph.floors
        available_ids = {n.id for n in game_state.map_graph.get_available_nodes()}
        current_id = game_state.map_graph.current_node_id

        # Render connection lines between floors
        total_floors = len(floors)
        lane_w = (SCREEN_WIDTH - 60) // 4

        for f_idx, floor in enumerate(floors):
            # Display bottom floor near bottom, top floor near top
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

        # Render node icons
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
                pyxel.text(x_pos + 4, y_pos + 3, icon_char, color if not is_curr else COLOR_BLACK)

                if is_avail:
                    pyxel.text(x_pos + 3, y_pos - 7, f"[{option_index}]", COLOR_YELLOW)
                    option_index += 1


class CombatView(View):
    """Renders active auto-battle arena, tick gauges, and battle logs."""

    def update(self, game_state: GameState) -> None:
        if game_state.combat is None:
            return

        # Advance combat: space or auto-tick
        if pyxel.btnp(pyxel.KEY_SPACE) or (pyxel.frame_count % 15 == 0):
            game_state.update_combat()

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        if game_state.combat is None:
            return

        combat = game_state.combat

        # Player Stat Panel
        renderer.draw_stat_panel(
            x=10,
            y=30,
            w=112,
            h=80,
            title=f"{game_state.player.name}",
            stats=game_state.player.effective_stats,
            hp=game_state.player.current_hp,
            max_hp=game_state.player.max_hp,
            color_scheme=COLOR_DARK_BLUE,
        )

        # Enemy Stat Panel
        renderer.draw_stat_panel(
            x=134,
            y=30,
            w=112,
            h=80,
            title=f"{combat.enemy.name}",
            stats=combat.enemy.base_stats,
            hp=combat.enemy.current_hp,
            max_hp=combat.enemy.max_hp,
            color_scheme=COLOR_RED if combat.enemy.tier.value >= 3 else COLOR_NAVY,
        )

        # Action Tick Meter (Player vs Enemy)
        pyxel.text(10, 116, "Tick Gauges:", COLOR_YELLOW)
        renderer.draw_bar(10, 126, 112, 6, combat.player_gauge, ACTION_THRESHOLD, fill_col=COLOR_LIGHT_BLUE, bg_col=COLOR_BLACK)
        renderer.draw_bar(134, 126, 112, 6, combat.enemy_gauge, ACTION_THRESHOLD, fill_col=COLOR_ORANGE, bg_col=COLOR_BLACK)

        # Combat activity logs
        renderer.draw_combat_logs(
            logs=combat.combat_logs,
            x=10,
            y=138,
            w=SCREEN_WIDTH - 20,
            h=108,
            max_entries=10,
        )


class InventoryView(View):
    """Renders 6+2 Equipment, 10-slot Pouch, and 3-slot Belt."""

    def update(self, game_state: GameState) -> None:
        # Toggle inventory or use belt item [1-3]
        if pyxel.btnp(pyxel.KEY_1):
            game_state.player.inventory.use_belt_item(0, game_state.player)
        elif pyxel.btnp(pyxel.KEY_2):
            game_state.player.inventory.use_belt_item(1, game_state.player)
        elif pyxel.btnp(pyxel.KEY_3):
            game_state.player.inventory.use_belt_item(2, game_state.player)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        renderer.draw_box(10, 26, SCREEN_WIDTH - 20, SCREEN_HEIGHT - 32, bg_col=COLOR_BLACK, border_col=COLOR_GRAY)
        pyxel.text(18, 32, "-- Equipment (6 Primary + 2 Accessory) --", COLOR_YELLOW)

        inv = game_state.player.inventory

        # Draw 6+2 Equipment layout
        # 6 Primary Slots: Head, Chest, Hands, Legs, Main Hand, Off Hand
        # 2 Accessory Slots: Ring, Amulet
        equip_order = [
            EquipSlot.HEAD, EquipSlot.CHEST,
            EquipSlot.HANDS, EquipSlot.LEGS,
            EquipSlot.MAIN_HAND, EquipSlot.OFF_HAND,
            EquipSlot.RING, EquipSlot.AMULET,
        ]

        for i, slot in enumerate(equip_order):
            col = i % 2
            row = i // 2
            x = 18 + col * 114
            y = 44 + row * 16
            item = inv.equipment.get(slot)
            item_name = item.name if item else "(Empty)"
            tag = "[Acc]" if slot in (EquipSlot.RING, EquipSlot.AMULET) else ""
            slot_label = slot.name.replace("_", " ").title()
            pyxel.text(x, y, f"{slot_label} {tag}:", COLOR_GRAY)
            pyxel.text(x + 56, y, item_name[:10], COLOR_WHITE if item else COLOR_DARK_BLUE)

        # 3-Slot Belt
        pyxel.text(18, 116, "-- Belt (3 Quick Slots: Press [1-3] to Use) --", COLOR_YELLOW)
        for b_idx in range(MAX_BELT_SLOTS):
            x = 18 + b_idx * 76
            y = 128
            b_item = inv.belt[b_idx]
            name = b_item.name if b_item else "Empty"
            renderer.draw_box(x, y, 70, 18, bg_col=COLOR_NAVY, border_col=COLOR_WHITE)
            pyxel.text(x + 4, y + 3, f"[{b_idx+1}]", COLOR_YELLOW)
            pyxel.text(x + 18, y + 3, name[:8], COLOR_WHITE)
            if b_item:
                pyxel.text(x + 18, y + 10, f"+{b_item.heal_amount}HP", COLOR_LIME)

        # 10-Slot Pouch
        pyxel.text(18, 154, f"-- Pouch ({len(inv.pouch)}/{MAX_POUCH_SLOTS} Slots) --", COLOR_YELLOW)
        for p_idx in range(MAX_POUCH_SLOTS):
            col = p_idx % 2
            row = p_idx // 2
            x = 18 + col * 114
            y = 166 + row * 13
            if p_idx < len(inv.pouch):
                p_item = inv.pouch[p_idx]
                pyxel.text(x, y, f"{p_idx+1}. {p_item.name}", COLOR_WHITE)
            else:
                pyxel.text(x, y, f"{p_idx+1}. [Empty]", COLOR_DARK_BLUE)

        pyxel.text(18, 236, "Press [I] or [ESC] to close inventory.", COLOR_PEACH)


class EventsView(View):
    """Renders non-combat room encounters (sanctuary, treasure, merchant)."""

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            game_state.switch_mode(GameMode.MAP)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        renderer.draw_box(20, 50, SCREEN_WIDTH - 40, 140, bg_col=COLOR_DARK_BLUE, border_col=COLOR_WHITE)
        pyxel.text(30, 65, "-- Room Encounter --", COLOR_YELLOW)
        pyxel.text(30, 90, game_state.current_event_text, COLOR_WHITE)

        pyxel.text(30, 150, "Press [SPACE] or [ENTER] to return to Map.", COLOR_LIME)


class EndGameView(View):
    """Renders Game Over or Victory screens."""

    def __init__(self, is_victory: bool) -> None:
        self.is_victory: bool = is_victory

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN):
            # Restart game state
            game_state.__init__()  # Reinitialize state

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT

        if self.is_victory:
            renderer.draw_box(20, 60, w - 40, 120, bg_col=COLOR_NAVY, border_col=COLOR_YELLOW)
            pyxel.text(w // 2 - 40, 80, "VICTORY ACHIEVED!", COLOR_YELLOW)
            pyxel.text(35, 110, "You conquered the Spire of Aethelgard!", COLOR_WHITE)
        else:
            renderer.draw_box(20, 60, w - 40, 120, bg_col=COLOR_RED, border_col=COLOR_WHITE)
            pyxel.text(w // 2 - 24, 80, "YOU DIED", COLOR_WHITE)
            pyxel.text(35, 110, "Your bones join the endless dungeon...", COLOR_PEACH)

        pyxel.text(w // 2 - 45, 150, "Press [ENTER] to Restart", COLOR_WHITE)


class ViewManager:
    """Manages view selection and delegates update/render calls."""

    def __init__(self) -> None:
        self.views: dict[GameMode, View] = {
            GameMode.MAP: MapView(),
            GameMode.COMBAT: CombatView(),
            GameMode.INVENTORY: InventoryView(),
            GameMode.EVENTS: EventsView(),
            GameMode.GAME_OVER: EndGameView(is_victory=False),
            GameMode.VICTORY: EndGameView(is_victory=True),
        }

    def update(self, game_state: GameState) -> None:
        # Global key listener for toggling inventory
        if pyxel.btnp(pyxel.KEY_I) or (game_state.current_mode == GameMode.INVENTORY and pyxel.btnp(pyxel.KEY_ESCAPE)):
            game_state.toggle_inventory()
            return

        view = self.views.get(game_state.current_mode)
        if view:
            view.update(game_state)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        view = self.views.get(game_state.current_mode)
        if view:
            view.draw(game_state, renderer)
