"""Master state machine coordinating Map, Combat, Inventory, and Events."""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

from src.entities.enemy import EnemyTier, generate_enemy
from src.entities.player import Player
from src.systems.combat import CombatResult, CombatSystem
from src.systems.inventory import ConsumableItem, EquipSlot, EquipmentItem
from src.systems.map_gen import MapGraph, MapNode, NodeType, generate_spire_map

if TYPE_CHECKING:
    pass


class GameMode(Enum):
    """Core operational modes of the game engine."""

    WELCOME = auto()
    CREDITS = auto()
    MAP = auto()
    COMBAT = auto()
    INVENTORY = auto()
    EVENTS = auto()
    GAME_OVER = auto()
    VICTORY = auto()
    ABILITY_CHOICE = auto()


class GameState:
    """Master state container managing active subsystems and screen transitions."""

    def __init__(self) -> None:
        self.player: Player = Player(name="Sir Aethelgard")
        self.map_graph: MapGraph = generate_spire_map(num_floors=8, width_lanes=4)
        self.current_mode: GameMode = GameMode.WELCOME
        self.previous_mode: GameMode = GameMode.WELCOME

        self.combat: CombatSystem | None = None
        self.current_event_text: str = ""
        self.floor: int = 1

        self._seed_starter_kit()

    def _seed_starter_kit(self) -> None:
        """Provide initial gear and consumables for the journey."""
        sword = EquipmentItem(
            id="bronze_sword",
            name="Bronze Blade",
            description="A dependable starting sword.",
            slot=EquipSlot.MAIN_HAND,
        )
        self.player.inventory.equip(sword)

        potion = ConsumableItem(
            id="health_potion",
            name="Health Draught",
            description="Restores 35 hit points.",
            heal_amount=35,
        )
        self.player.inventory.belt[0] = potion

    def switch_mode(self, new_mode: GameMode) -> None:
        """Transition the active game mode."""
        self.previous_mode = self.current_mode
        self.current_mode = new_mode

    def toggle_inventory(self) -> None:
        """Open or close the inventory screen."""
        if self.current_mode == GameMode.INVENTORY:
            self.switch_mode(self.previous_mode)
        elif self.current_mode in (GameMode.MAP, GameMode.EVENTS):
            self.switch_mode(GameMode.INVENTORY)

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
        if node.node_type in (NodeType.COMBAT, NodeType.ELITE, NodeType.BOSS):
            tier = EnemyTier.COMMON
            if node.node_type == NodeType.ELITE:
                tier = EnemyTier.ELITE
            elif node.node_type == NodeType.BOSS:
                tier = EnemyTier.BOSS

            enemy = generate_enemy(tier=tier, floor=self.floor)
            self.combat = CombatSystem(player=self.player, enemy=enemy)
            self.switch_mode(GameMode.COMBAT)

        elif node.node_type == NodeType.REST:
            healed = self.player.heal(40)
            self.current_event_text = (
                f"You discovered a sanctuary campfire. Resting restores {healed} HP."
            )
            self.switch_mode(GameMode.EVENTS)

        elif node.node_type == NodeType.TREASURE:
            self.player.gold += 35
            self.current_event_text = (
                "You cracked open an ornate chest! Obtained 35 Gold."
            )
            self.switch_mode(GameMode.EVENTS)

        elif node.node_type == NodeType.SHOP:
            self.current_event_text = (
                "A wandering merchant greets you: 'Stay safe traveler.'"
            )
            self.switch_mode(GameMode.EVENTS)

        else:  # NodeType.EVENT
            self.current_event_text = (
                "An ancient shrine hums with mystical energy as you pass by."
            )
            self.switch_mode(GameMode.EVENTS)

    def update_combat(self) -> None:
        """Tick combat simulation when in COMBAT mode."""
        if self.combat is None or not self.combat.is_active():
            return

        result = self.combat.step()
        if result == CombatResult.PLAYER_VICTORY:
            if self.player.pending_ability_choices:
                self.switch_mode(GameMode.ABILITY_CHOICE)
                return

            current_node = self.map_graph.current_node
            if current_node and current_node.node_type == NodeType.BOSS:
                self.switch_mode(GameMode.VICTORY)
            else:
                self.switch_mode(GameMode.MAP)
        elif result == CombatResult.PLAYER_DEFEAT:
            self.switch_mode(GameMode.GAME_OVER)
