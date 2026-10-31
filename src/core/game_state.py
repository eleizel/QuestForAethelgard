"""Master state machine coordinating Map, Combat, Inventory, and Events."""

from __future__ import annotations

import random
from enum import Enum, auto
from typing import TYPE_CHECKING

from src.entities.enemy import EnemyTier, generate_enemy
from src.entities.player import Player
from src.systems.combat import CombatResult, CombatSystem
from src.systems.inventory import Item
from src.systems.map_gen import MapGraph, MapNode, NodeType, generate_spire_map

if TYPE_CHECKING:
    from src.data.events import GameEvent


class GameMode(Enum):
    """Core operational modes of the game engine."""

    WELCOME = auto()
    CLASS_SELECT = auto()
    CREDITS = auto()
    BIOME_SELECT = auto()
    MAP = auto()
    COMBAT = auto()
    INVENTORY = auto()
    CHARACTER = auto()
    EVENTS = auto()
    GAME_OVER = auto()
    VICTORY = auto()
    ABILITY_CHOICE = auto()
    LOOT = auto()
    SHOP = auto()
    PROMOTION = auto()


class GameState:
    """Master state container managing active subsystems and screen transitions."""

    def __init__(self) -> None:
        self.player: Player = Player(name="Sir Aethelgard")
        self.map_graph: MapGraph | None = None
        self.current_mode: GameMode = GameMode.WELCOME
        self.previous_mode: GameMode = GameMode.WELCOME

        self.combat: CombatSystem | None = None
        self.current_event: GameEvent | None = None
        self.current_event_text: str = ""
        self.floor: int = 1
        self.act: int = 1
        self.biome_route_mode: str = "FATE"
        self.current_biome: str = "arboretum"

        self.pending_loot: list[Item] = []
        self.merchant_stock: list[tuple[Item, int]] = []
        self.last_gold_earned: int = 0
        self.last_exp_earned: int = 0
        self.promotion_return_mode: GameMode | None = None
        self.overlay_return_modes: list[GameMode] = []

    def start_new_game(
            self, class_id: str = "warrior", route_mode: str = "FATE"
    ) -> None:
        """Initialize a new journey with the specified character class."""
        self.player = Player(name="Sir Aethelgard", class_id=class_id)
        self.biome_route_mode = route_mode

        from src.data.items import get_starter_kit, get_item

        starter_items = get_starter_kit(class_id)
        for item in starter_items:
            self.player.inventory.equip(item)

        potion = get_item("health_potion")
        if potion:
            self.player.inventory.belt[0] = potion

        self.floor = 1
        self.act = 1
        self.combat = None
        self.pending_loot = []
        self.promotion_return_mode = None
        self.overlay_return_modes.clear()

        if self.biome_route_mode == "FATE":
            from src.data.biomes import ACT_BIOMES

            self.current_biome = random.choice(ACT_BIOMES[1])
            self.map_graph = generate_spire_map(num_floors=12, width_lanes=4)
            self.switch_mode(GameMode.MAP)
            from src.core.save_manager import save_manager
            save_manager.save_game(self)
        elif self.biome_route_mode == "PATHFINDER":
            self.switch_mode(GameMode.BIOME_SELECT)

    def advance_act(self, target_biome_id: str | None = None) -> None:
        """Advance to the next act and select the biome."""
        if target_biome_id is not None:
            self.current_biome = target_biome_id
        elif self.biome_route_mode == "FATE":
            from src.data.biomes import ACT_BIOMES

            self.current_biome = random.choice(ACT_BIOMES[self.act])

        self.player.heal(int(self.player.max_hp * 0.50))
        num_floors = 18 if self.act == 3 else 12
        self.map_graph = generate_spire_map(num_floors=num_floors, width_lanes=4)
        self.switch_mode(GameMode.MAP)
        from src.core.save_manager import save_manager
        save_manager.save_game(self)

    def begin_promotion(self, return_mode: GameMode | None = None) -> bool:
        if not self.player.promotion_due or not self.player.available_promotions():
            return False
        if return_mode is not None:
            self.promotion_return_mode = return_mode
        elif self.current_mode == GameMode.ABILITY_CHOICE:
            # AbilityChoiceView already owns the post-choice route and must not
            # be restored with an empty queue after promotion.
            self.promotion_return_mode = None
        else:
            self.promotion_return_mode = self.current_mode
        self.switch_mode(GameMode.PROMOTION)
        return True

    def continue_after_rewards(self) -> None:
        """Resume the route after loot and all queued reward choices are complete."""
        current_node = self.map_graph.current_node if self.map_graph else None
        if current_node and current_node.node_type == NodeType.BOSS:
            if self.act < 3:
                self.act += 1
                self.floor = 1
                if self.biome_route_mode == "PATHFINDER":
                    self.switch_mode(GameMode.BIOME_SELECT)
                else:
                    self.advance_act()
            else:
                from src.core.save_manager import save_manager
                save_manager.delete_save()
                self.switch_mode(GameMode.VICTORY)
        else:
            self.switch_mode(GameMode.MAP)
            from src.core.save_manager import save_manager
            save_manager.save_game(self)

    def switch_mode(self, new_mode: GameMode) -> None:
        """Transition the active game mode."""
        self.previous_mode = self.current_mode
        self.current_mode = new_mode

    def _toggle_menu_overlay(self, target: GameMode) -> None:
        """Open an inventory or character overlay, or return to its previous view."""
        if self.current_mode == target:
            destination = self.overlay_return_modes.pop() if self.overlay_return_modes else self.previous_mode
            self.switch_mode(destination)
            if destination == GameMode.MAP:
                from src.core.save_manager import save_manager
                save_manager.save_game(self)
            return

        self.overlay_return_modes.append(self.current_mode)
        self.switch_mode(target)

    def toggle_inventory(self) -> None:
        """Open or close the inventory screen."""
        self._toggle_menu_overlay(GameMode.INVENTORY)

    def toggle_character(self) -> None:
        """Open or close the character sheet."""
        self._toggle_menu_overlay(GameMode.CHARACTER)

    def select_map_node(self, node_id: int) -> bool:
        """Enter a map node and transition to its associated gameplay mode."""
        node = self.map_graph.nodes_by_id.get(node_id)
        if node is None or not node.available:
            return False

        if not self.map_graph.select_node(node_id):
            return False

        self.floor = node.floor + 1
        self._trigger_node_encounter(node)
        return True

    def _trigger_node_encounter(self, node: MapNode) -> None:
        """Initialize encounter state corresponding to node type."""
        from src.core.i18n import t
        if node.node_type in (NodeType.COMBAT, NodeType.ELITE, NodeType.BOSS):
            tier = EnemyTier.COMMON
            if node.node_type == NodeType.ELITE:
                tier = EnemyTier.ELITE
            elif node.node_type == NodeType.BOSS:
                tier = EnemyTier.BOSS

            effective_floor = self.floor + (
                12 if self.act == 2 else (24 if self.act == 3 else 0)
            )
            enemy = generate_enemy(
                tier=tier,
                floor=effective_floor,
                biome_id=self.current_biome,
                player_speed=self.player.base_stats.speed,
            )
            self.combat = CombatSystem(player=self.player, enemy=enemy)
            self.combat.normalize_speeds()
            self.switch_mode(GameMode.COMBAT)

        elif node.node_type == NodeType.REST:
            healed = self.player.heal(random.randint(25, 40))
            self.current_event_text = t("event_rest", healed=healed)
            self.switch_mode(GameMode.EVENTS)

        elif node.node_type == NodeType.TREASURE:
            gold = random.randint(25, 40)
            self.player.gold += gold
            self.current_event_text = t("event_treasure", gold=gold)
            self.switch_mode(GameMode.EVENTS)

        elif node.node_type == NodeType.SHOP:
            from src.systems.loot import generate_merchant_stock

            self.merchant_stock = generate_merchant_stock(self.floor, self.player)
            self.switch_mode(GameMode.SHOP)

        else:  # NodeType.EVENT
            from src.data.events import get_random_event
            self.current_event = get_random_event(self.current_biome)
            self.current_event_text = self.current_event.description
            self.switch_mode(GameMode.EVENTS)

    def update_combat(self) -> None:
        """Tick combat simulation when in COMBAT mode."""
        if self.combat is None:
            return

        if self.combat.is_active():
            result = self.combat.step()
        else:
            result = self.combat.result

        # Leave a short arena beat for the death-hook speech bubble and its effect
        # popup to be seen before changing to the reward or defeat screen.
        if result != CombatResult.IN_PROGRESS and self.combat.completion_delay_ticks > 0:
            self.combat.completion_delay_ticks -= 1
            return

        if result == CombatResult.PLAYER_VICTORY:
            # Rewards already processed in combat.py, but we can capture the specific amounts to show in LOOT mode
            self.last_exp_earned = self.combat.enemy.exp_reward
            self.last_gold_earned = self.combat.enemy.gold_reward

            # Generate loot
            from src.systems.loot import generate_combat_loot
            from src.entities.enemy import EnemyTier

            current_node = self.map_graph.current_node

            tier = EnemyTier.COMMON
            if current_node:
                if current_node.node_type == NodeType.ELITE:
                    tier = EnemyTier.ELITE
                elif current_node.node_type == NodeType.BOSS:
                    tier = EnemyTier.BOSS

            self.pending_loot = generate_combat_loot(tier, self.floor, self.player)
            self.switch_mode(GameMode.LOOT)

        elif result == CombatResult.PLAYER_DEFEAT:
            from src.core.save_manager import save_manager
            save_manager.delete_save()
            self.switch_mode(GameMode.GAME_OVER)
