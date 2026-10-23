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
from src.core.game_state import GameMode
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.core.game_state import GameState
from src.systems.combat import ACTION_THRESHOLD
from src.systems.inventory import EquipSlot, MAX_BELT_SLOTS, MAX_POUCH_SLOTS
from src.systems.abilities import Ability, AbilityRarity, AbilityType, get_random_abilities
from src.systems.map_gen import NodeType
from src.ui.renderer import Renderer


class View:
    """Base abstract interface for game screens."""

    def update(self, game_state: GameState) -> None:
        pass

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pass


class MapView(View):
    """Visualizes the Spire node tree and node selection."""

    def update(self, game_state: GameState) -> None:
        available = game_state.map_graph.get_available_nodes()
        for idx, node in enumerate(available):
            key = getattr(pyxel, f"KEY_{idx + 1}", None)
            if key and pyxel.btnp(key):
                pyxel.play(0, 3)  # Sound 3: Menu Click
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
                else:
                    pyxel.text(x_pos + 4, y_pos + 3, icon_char, color if not is_curr else COLOR_BLACK)

                if is_avail:
                    pyxel.text(x_pos + 3, y_pos - 7, f"[{option_index}]", COLOR_YELLOW)
                    option_index += 1


class CombatView(View):
    """Renders active auto-battle arena, sprites, tick gauges, and battle logs."""

    def update(self, game_state: GameState) -> None:
        if game_state.combat is None:
            return

        # In-combat quick belt triggers: Keys [1, 2, 3]
        for idx, key in enumerate((pyxel.KEY_1, pyxel.KEY_2, pyxel.KEY_3)):
            if pyxel.btnp(key):
                if game_state.player.inventory.use_belt_item(idx, game_state.player):
                    pyxel.play(1, 2)  # Sound 2: Potion Heal chime
                    game_state.combat.combat_logs.append(
                        f"{game_state.player.name} used belt slot [{idx+1}]!"
                    )

        # Active Abilities: Keys [4, 5] (with 3-tick cooldown)
        for idx, key in enumerate((pyxel.KEY_4, pyxel.KEY_5)):
            if pyxel.btnp(key) and idx < len(game_state.player.abilities.active):
                if game_state.combat.ability_cooldown <= 0:
                    game_state.combat.queued_ability = game_state.player.abilities.active[idx]
                    game_state.combat.ability_cooldown = 3
                    game_state.combat.combat_logs.append(f"Queued {game_state.player.abilities.active[idx].name}!")
                else:
                    game_state.combat.combat_logs.append(f"Ability on cooldown ({game_state.combat.ability_cooldown} turns)!")

        # Advance combat: space or auto-tick
        if pyxel.btnp(pyxel.KEY_SPACE) or (pyxel.frame_count % 15 == 0):
            game_state.update_combat()

    def _get_enemy_sprite_u(self, enemy_name: str, tier_val: int) -> int:
        name_lower = enemy_name.lower()
        if tier_val >= 4 or "lich" in name_lower or "dragon" in name_lower:
            return 48  # Boss sprite
        if "goblin" in name_lower or "scavenger" in name_lower or "cultist" in name_lower:
            return 32  # Goblin sprite
        return 16      # Skeleton Warrior sprite

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
        )
        # Hero sprite
        pyxel.blt(100, 32, 0, 0, 0, 16, 16, 0)

        # Enemy Stat Panel
        renderer.draw_stat_panel(
            x=134,
            y=28,
            w=112,
            h=78,
            title=f"{combat.enemy.name}",
            stats=combat.enemy.base_stats,
            hp=combat.enemy.current_hp,
            max_hp=combat.enemy.max_hp,
            color_scheme=COLOR_RED if combat.enemy.tier.value >= 3 else COLOR_NAVY,
        )
        # Enemy sprite
        enemy_u = self._get_enemy_sprite_u(combat.enemy.name, combat.enemy.tier.value)
        pyxel.blt(224, 32, 0, enemy_u, 0, 16, 16, 0)

        # Action Tick Meter (Player vs Enemy)
        pyxel.text(10, 110, "Tick Gauges:", COLOR_YELLOW)
        renderer.draw_bar(10, 118, 112, 5, combat.player_gauge, ACTION_THRESHOLD, fill_col=COLOR_LIGHT_BLUE, bg_col=COLOR_BLACK)
        renderer.draw_bar(134, 118, 112, 5, combat.enemy_gauge, ACTION_THRESHOLD, fill_col=COLOR_ORANGE, bg_col=COLOR_BLACK)

        # In-Combat Quick Belt Display
        renderer.draw_box(10, 128, SCREEN_WIDTH - 20, 32, bg_col=COLOR_NAVY, border_col=COLOR_DARK_BLUE)
        pyxel.text(14, 131, "BELT:", COLOR_YELLOW)
        inv = game_state.player.inventory
        for b_idx in range(MAX_BELT_SLOTS):
            bx = 42 + b_idx * 70
            b_item = inv.belt[b_idx]
            name = b_item.name[:7] if b_item else "Empty"
            pyxel.text(bx, 132, f"[{b_idx+1}]", COLOR_YELLOW)
            if b_item:
                pyxel.blt(bx + 14, 130, 0, 64, 0, 8, 8, 0)  # Potion sprite
                pyxel.text(bx + 24, 132, name, COLOR_WHITE)
                pyxel.text(bx + 24, 140, f"+{b_item.heal_amount}HP", COLOR_LIME)
            else:
                pyxel.text(bx + 14, 132, name, COLOR_GRAY)

        # Abilities panel
        # Placed under the belt hotkeys
        pyxel.text(14, 148, "SKILLS:", COLOR_YELLOW)
        for a_idx, active_ab in enumerate(game_state.player.abilities.active):
            x_pos = 46 + a_idx * 95
            key_label = "4" if a_idx == 0 else "5"
            queued_marker = "*" if game_state.combat and game_state.combat.queued_ability == active_ab else " "
            pyxel.text(x_pos, 148, f"[{key_label}]{queued_marker} {active_ab.name[:15]}", COLOR_LIME)

        # Combat activity logs
        renderer.draw_combat_logs(
            logs=combat.combat_logs,
            x=10,
            y=164,
            w=SCREEN_WIDTH - 20,
            h=84,
            max_entries=7,
        )


class InventoryView(View):
    """Renders 6+2 Equipment, 10-slot Pouch, and 3-slot Belt."""

    def __init__(self) -> None:
        self.active_pane: str = "POUCH" # "POUCH" or "EQUIPMENT"
        self.pouch_cursor: int = 0
        self.equip_cursor: int = 0
        self.feedback_message: str = ""

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.KEY_I):
            game_state.toggle_inventory()
            return

        if pyxel.btnp(pyxel.KEY_TAB):
            self.active_pane = "EQUIPMENT" if self.active_pane == "POUCH" else "POUCH"
            self.feedback_message = ""
            return

        up_pressed = pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W)
        down_pressed = pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btnp(pyxel.KEY_S)

        from src.systems.inventory import EquipmentItem, ConsumableItem, EquipSlot
        inv = game_state.player.inventory

        if self.active_pane == "POUCH":
            if up_pressed:
                self.pouch_cursor = max(0, self.pouch_cursor - 1)
                self.feedback_message = ""
            elif down_pressed:
                self.pouch_cursor = min(MAX_POUCH_SLOTS - 1, self.pouch_cursor + 1)
                self.feedback_message = ""

            if pyxel.btnp(pyxel.KEY_E):
                if self.pouch_cursor < len(inv.pouch):
                    item = inv.pouch[self.pouch_cursor]
                    if isinstance(item, EquipmentItem):
                        success, msg = inv.equip_from_pouch(self.pouch_cursor, game_state.player)
                        self.feedback_message = msg
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
                        if success:
                            pyxel.play(0, 3)

            if pyxel.btnp(pyxel.KEY_D):
                if self.pouch_cursor < len(inv.pouch):
                    success, msg = inv.drop_from_pouch(self.pouch_cursor)
                    self.feedback_message = msg
                    if success:
                        pyxel.play(0, 3)

            # Assign to belt 1, 2, 3
            for idx, key in enumerate((pyxel.KEY_1, pyxel.KEY_2, pyxel.KEY_3)):
                if pyxel.btnp(key):
                    if self.pouch_cursor < len(inv.pouch):
                        success, msg = inv.assign_pouch_to_belt(self.pouch_cursor, idx)
                        self.feedback_message = msg
                        if success:
                            pyxel.play(0, 3)

        elif self.active_pane == "EQUIPMENT":
            if up_pressed:
                self.equip_cursor = max(0, self.equip_cursor - 1)
                self.feedback_message = ""
            elif down_pressed:
                self.equip_cursor = min(len(EquipSlot) - 1, self.equip_cursor + 1)
                self.feedback_message = ""

            if pyxel.btnp(pyxel.KEY_U):
                slots = list(EquipSlot)
                target_slot = slots[self.equip_cursor]
                if inv.equipment[target_slot] is not None:
                    success, msg = inv.unequip_to_pouch(target_slot)
                    self.feedback_message = msg
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
        pyxel.text(10, 32, "-- Equipment --", equip_title_col)

        equip_order = list(EquipSlot)
        for i, slot in enumerate(equip_order):
            col = i % 2
            row = i // 2
            x = 10 + col * 118
            y = 44 + row * 12

            cursor_str = "> " if self.active_pane == "EQUIPMENT" and self.equip_cursor == i else "  "

            item = inv.equipment.get(slot)
            item_name = item.name if item else "(Empty)"
            slot_label = slot.name.replace("_", " ").title()[:10]

            # Highlight if selected
            label_col = COLOR_WHITE if self.active_pane == "EQUIPMENT" and self.equip_cursor == i else COLOR_GRAY
            pyxel.text(x, y, f"{cursor_str}{slot_label}:", label_col)
            pyxel.text(x + 50, y, item_name[:10], COLOR_LIME if item else COLOR_DARK_BLUE)

        # 3-Slot Belt
        pyxel.text(10, 96, "-- Belt --", COLOR_YELLOW)
        for b_idx in range(MAX_BELT_SLOTS):
            x = 10 + b_idx * 78
            y = 106
            b_item = inv.belt[b_idx]
            name = b_item.name if b_item else "Empty"
            renderer.draw_box(x, y, 74, 18, bg_col=COLOR_NAVY, border_col=COLOR_WHITE)
            pyxel.text(x + 4, y + 3, f"[{b_idx+1}]", COLOR_YELLOW)
            if b_item:
                pyxel.text(x + 18, y + 3, name[:8], COLOR_WHITE)
                pyxel.text(x + 18, y + 10, f"+{b_item.heal_amount}HP", COLOR_LIME)
            else:
                pyxel.text(x + 18, y + 6, name, COLOR_GRAY)

        # 10-Slot Pouch
        pouch_title_col = COLOR_YELLOW if self.active_pane == "POUCH" else COLOR_GRAY
        pyxel.text(10, 130, f"-- Pouch ({len(inv.pouch)}/{MAX_POUCH_SLOTS}) --", pouch_title_col)
        for p_idx in range(MAX_POUCH_SLOTS):
            col = p_idx % 2
            row = p_idx // 2
            x = 10 + col * 118
            y = 142 + row * 14

            cursor_str = "> " if self.active_pane == "POUCH" and self.pouch_cursor == p_idx else "  "

            if p_idx < len(inv.pouch):
                p_item = inv.pouch[p_idx]
                item_col = COLOR_WHITE if self.active_pane == "POUCH" and self.pouch_cursor == p_idx else COLOR_GRAY
                pyxel.text(x, y, f"{cursor_str}{p_item.name[:12]}", item_col)

                # Show stats if equipment, heal if consumable
                stats_str = ""
                if isinstance(p_item, EquipmentItem):
                    if p_item.stats_bonus.attack > 0: stats_str += f"A{p_item.stats_bonus.attack}"
                    if p_item.stats_bonus.defense > 0: stats_str += f" D{p_item.stats_bonus.defense}"
                    if p_item.stats_bonus.max_hp > 0: stats_str += f" H{p_item.stats_bonus.max_hp}"
                elif isinstance(p_item, ConsumableItem):
                    stats_str = f"+{p_item.heal_amount}HP"

                if stats_str:
                    pyxel.text(x + 12, y + 6, stats_str, COLOR_LIME)
            else:
                pyxel.text(x, y, f"{cursor_str}[Empty]", COLOR_DARK_BLUE)

        # Bottom Panel Context Hints
        y_bottom = 224
        renderer.draw_box(10, y_bottom, SCREEN_WIDTH - 20, 24, bg_col=COLOR_NAVY, border_col=COLOR_WHITE)
        if self.active_pane == "POUCH":
            pyxel.text(14, y_bottom + 4, "[TAB] Focus Equip | [E] Equip/Use", COLOR_PEACH)
            pyxel.text(14, y_bottom + 12, "[D] Drop | [1-3] Belt | [ESC] Close", COLOR_PEACH)
        else:
            pyxel.text(14, y_bottom + 4, "[TAB] Focus Pouch | [U] Unequip", COLOR_PEACH)
            pyxel.text(14, y_bottom + 12, "[ESC] Close", COLOR_PEACH)

        # Feedback Message
        if self.feedback_message:
            msg_col = COLOR_RED if "!" in self.feedback_message and "Equipped" not in self.feedback_message else COLOR_LIME
            pyxel.text(14, y_bottom - 10, self.feedback_message, msg_col)


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
            game_state.__init__()

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


class WelcomeView(View):
    """Renders the game's welcome screen."""

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_1):
            game_state.__init__()
            game_state.switch_mode(GameMode.MAP)
        elif pyxel.btnp(pyxel.KEY_2):
            pass  # Load game out of scope
        elif pyxel.btnp(pyxel.KEY_3):
            game_state.switch_mode(GameMode.CREDITS)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT

        # Display Title
        pyxel.blt(w // 2 - 32, 30, 0, 0, 112, 64, 16, 0)

        # Draw some pixel art sprites from game.pyxres (e.g. hero and enemy sprites)
        # Assuming typical sprites based on existing CombatView usages:
        # Hero sprite is at 0, 0
        pyxel.blt(w // 2 - 24, 70, 0, 0, 0, 16, 16, 0)
        # Enemy sprite (like a goblin or skeleton)
        pyxel.blt(w // 2 + 8, 70, 0, 16, 0, 16, 16, 0)

        # Menu Options
        renderer.draw_box(40, 120, w - 80, 80, bg_col=COLOR_NAVY, border_col=COLOR_WHITE)
        pyxel.text(50, 135, "[1] New Game", COLOR_WHITE)
        pyxel.text(50, 155, "[2] Load Game", COLOR_GRAY)
        pyxel.text(50, 175, "[3] Credits", COLOR_WHITE)


class CreditsView(View):
    """Renders the game's credits screen."""

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_ESCAPE):
            game_state.switch_mode(GameMode.WELCOME)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT

        renderer.draw_box(20, 60, w - 40, 120, bg_col=COLOR_NAVY, border_col=COLOR_YELLOW)
        pyxel.text(w // 2 - 20, 80, "CREDITS", COLOR_YELLOW)
        pyxel.text(35, 110, "Developed by Sergio Esperalta", COLOR_WHITE)
        pyxel.text(35, 130, "Assisted by AI (Gemini)", COLOR_WHITE)

        pyxel.text(w // 2 - 45, 160, "Press [ENTER] to Return", COLOR_LIME)



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
        self.choices = get_random_abilities(rarity_enum, known, count=2)

    def update(self, game_state: GameState) -> None:
        if not self.choices and game_state.player.pending_ability_choices:
            self._init_choices(game_state)

        if self.replace_mode and self.selected_ability:
            if pyxel.btnp(pyxel.KEY_1):
                game_state.player.abilities.replace_ability(self.selected_ability, 0)
                self._finish_choice(game_state)
            elif pyxel.btnp(pyxel.KEY_2):
                game_state.player.abilities.replace_ability(self.selected_ability, 1)
                self._finish_choice(game_state)
            elif pyxel.btnp(pyxel.KEY_ESCAPE):
                self.replace_mode = False
                self.selected_ability = None
            return

        if pyxel.btnp(pyxel.KEY_ESCAPE):
            self._finish_choice(game_state)
            return

        if pyxel.btnp(pyxel.KEY_1) and len(self.choices) > 0:
            self._handle_selection(game_state, self.choices[0])
        elif pyxel.btnp(pyxel.KEY_2) and len(self.choices) > 1:
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
                    next_floors = 18 if game_state.act == 3 else 12
                    from src.systems.map_gen import generate_spire_map
                    game_state.map_graph = generate_spire_map(num_floors=next_floors, width_lanes=4)
                    game_state.player.heal(9999) # Full heal between acts
                    game_state.switch_mode(GameMode.MAP)
                else:
                    game_state.switch_mode(GameMode.VICTORY)
            else:
                game_state.switch_mode(GameMode.MAP)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT

        renderer.draw_box(20, 20, w - 40, h - 40, bg_col=COLOR_NAVY, border_col=COLOR_YELLOW)

        if self.replace_mode and self.selected_ability:
            pyxel.text(30, 30, f"Replace a {self.selected_ability.ability_type.name} ability:", COLOR_YELLOW)
            pyxel.text(30, 45, f"New: {self.selected_ability.name}", COLOR_LIME)

            target_list = game_state.player.abilities.active if self.selected_ability.ability_type == AbilityType.ACTIVE else game_state.player.abilities.passive
            for i, ab in enumerate(target_list):
                pyxel.text(40, 70 + (i * 30), f"[{i+1}] {ab.name}: {ab.description[:30]}...", COLOR_WHITE)

            pyxel.text(30, h - 40, "Press [1] or [2] to replace. [ESC] to cancel.", COLOR_PEACH)
            return

        pyxel.text(30, 30, f"LEVEL UP! {self.pending_rarity} ABILITY CHOICE", COLOR_YELLOW)

        for i, ab in enumerate(self.choices):
            y_offset = 60 + (i * 60)
            renderer.draw_box(30, y_offset, w - 60, 50, bg_col=COLOR_DARK_BLUE, border_col=COLOR_WHITE)
            pyxel.text(40, y_offset + 5, f"[{i+1}] {ab.name} ({ab.ability_type.name})", COLOR_LIME)

            # Simple text wrap for description
            desc = ab.description
            if len(desc) > 35:
                pyxel.text(40, y_offset + 18, desc[:35], COLOR_WHITE)
                pyxel.text(40, y_offset + 28, desc[35:70], COLOR_WHITE)
            else:
                pyxel.text(40, y_offset + 18, desc, COLOR_WHITE)

        pyxel.text(30, h - 35, "Press [1] or [2] to select. [ESC] to skip.", COLOR_PEACH)


class LootView(View):
    """Renders the post-combat loot screen."""

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_1) and len(game_state.pending_loot) > 0:
            self._take_loot(game_state, 0)
        elif pyxel.btnp(pyxel.KEY_2) and len(game_state.pending_loot) > 1:
            self._take_loot(game_state, 1)
        elif pyxel.btnp(pyxel.KEY_3) and len(game_state.pending_loot) > 2:
            self._take_loot(game_state, 2)
        elif pyxel.btnp(pyxel.KEY_SPACE):
            # Take all that can fit
            for i in range(len(game_state.pending_loot) - 1, -1, -1):
                self._take_loot(game_state, i, play_sound=False)
            pyxel.play(0, 3) # Play click sound once for take all
        elif pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_C):
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
                next_floors = 18 if game_state.act == 3 else 12
                from src.systems.map_gen import generate_spire_map
                game_state.map_graph = generate_spire_map(num_floors=next_floors, width_lanes=4)
                game_state.player.heal(9999) # Full heal between acts
                game_state.switch_mode(GameMode.MAP)
            else:
                game_state.switch_mode(GameMode.VICTORY)
        else:
            game_state.switch_mode(GameMode.MAP)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT
        renderer.draw_hud(game_state.player, game_state.floor)

        renderer.draw_box(10, 30, w - 20, h - 40, bg_col=COLOR_NAVY, border_col=COLOR_YELLOW)
        pyxel.text(w // 2 - 40, 35, "VICTORY! Spoils of Battle", COLOR_YELLOW)

        # Summary box
        pyxel.text(20, 55, f"EXP Gained: {game_state.last_exp_earned}", COLOR_WHITE)
        pyxel.text(120, 55, f"Gold: {game_state.last_gold_earned}", COLOR_YELLOW)

        pouch_len = len(game_state.player.inventory.pouch)
        from src.systems.inventory import MAX_POUCH_SLOTS
        color = COLOR_RED if pouch_len >= MAX_POUCH_SLOTS else COLOR_LIME
        pyxel.text(20, 70, f"Pouch Space: {pouch_len}/{MAX_POUCH_SLOTS}", color)

        if pouch_len >= MAX_POUCH_SLOTS:
            pyxel.text(140, 70, "Pouch Full!", COLOR_RED)

        # Loot List
        y_offset = 90
        for i, item in enumerate(game_state.pending_loot):
            renderer.draw_box(20, y_offset, w - 40, 25, bg_col=COLOR_DARK_BLUE, border_col=COLOR_WHITE)
            pyxel.text(25, y_offset + 5, f"[{i+1}] {item.name}", COLOR_LIME)

            from src.systems.inventory import EquipmentItem, ConsumableItem
            if isinstance(item, EquipmentItem):
                pyxel.text(25, y_offset + 15, f"{item.slot.value}", COLOR_GRAY)
                # Display basic stats
                stats = ""
                if item.stats_bonus.attack > 0: stats += f" ATK+{item.stats_bonus.attack}"
                if item.stats_bonus.defense > 0: stats += f" DEF+{item.stats_bonus.defense}"
                if item.stats_bonus.speed > 0: stats += f" SPD+{item.stats_bonus.speed}"
                pyxel.text(90, y_offset + 15, stats, COLOR_WHITE)
            elif isinstance(item, ConsumableItem):
                pyxel.text(25, y_offset + 15, "Consumable", COLOR_GRAY)
                pyxel.text(90, y_offset + 15, f"Heals {item.heal_amount} HP", COLOR_GREEN)

            y_offset += 30

        if not game_state.pending_loot:
            pyxel.text(20, y_offset, "No items remaining.", COLOR_GRAY)

        pyxel.text(20, h - 25, "[1-3] Take Item | [SPACE] Take All", COLOR_PEACH)
        pyxel.text(20, h - 15, "[ENTER]/[C] Continue", COLOR_PEACH)


class ViewManager:
    """Manages view selection and delegates update/render calls."""

    def __init__(self) -> None:
        self.views: dict[GameMode, View] = {
            GameMode.WELCOME: WelcomeView(),
            GameMode.CREDITS: CreditsView(),
            GameMode.MAP: MapView(),
            GameMode.COMBAT: CombatView(),
            GameMode.INVENTORY: InventoryView(),
            GameMode.EVENTS: EventsView(),
            GameMode.GAME_OVER: EndGameView(is_victory=False),
            GameMode.VICTORY: EndGameView(is_victory=True),
            GameMode.ABILITY_CHOICE: AbilityChoiceView(),
            GameMode.LOOT: LootView(),
        }

    def update(self, game_state: GameState) -> None:
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