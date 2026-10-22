"""Inventory management system for Quest for Aethelgard.

Provides:
- 6+2 Equipment layout (6 primary slots + 2 accessory slots)
- 10-slot Pouch for storage
- 3-slot Belt for quick consumable items
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Final

from src.entities.actor import Stats

if TYPE_CHECKING:
    from src.entities.actor import Actor

MAX_POUCH_SLOTS: Final[int] = 10
MAX_BELT_SLOTS: Final[int] = 3


class ItemType(Enum):
    """Categorization of items in the game world."""

    EQUIPMENT = auto()
    CONSUMABLE = auto()
    MATERIAL = auto()


class EquipSlot(Enum):
    """Equipment slots: 6 primary slots + 2 accessory slots (Ring and Amulet)."""

    # 6 Primary Slots
    HEAD = "Head"
    CHEST = "Chest"
    HANDS = "Hands"
    LEGS = "Legs"
    MAIN_HAND = "Main Hand"
    OFF_HAND = "Off Hand"

    # +2 Accessory Slots
    RING = "Ring"
    AMULET = "Amulet"


@dataclass
class Item:
    """Base item structure."""

    id: str
    name: str
    description: str
    item_type: ItemType = ItemType.MATERIAL
    gold_value: int = 10


@dataclass
class EquipmentItem(Item):
    """Gear that can be slotted into the 6+2 equipment framework."""

    slot: EquipSlot = EquipSlot.MAIN_HAND
    stats_bonus: Stats = field(default_factory=lambda: Stats(max_hp=0, attack=0, defense=0, speed=0, crit_chance=0.0))
    item_type: ItemType = ItemType.EQUIPMENT


@dataclass
class ConsumableItem(Item):
    """Items usable from pouch or the 3-slot belt."""

    heal_amount: int = 25
    item_type: ItemType = ItemType.CONSUMABLE

    def use(self, target: Actor) -> bool:
        """Apply the item effect on an actor."""
        if not target.is_alive:
            return False
        if self.heal_amount > 0:
            target.heal(self.heal_amount)
            return True
        return False


class Inventory:
    """Player inventory containing 6+2 equipment, 10-slot pouch, and 3-slot belt."""

    def __init__(self) -> None:
        # 6 Primary + 2 Accessory slots
        self.equipment: dict[EquipSlot, EquipmentItem | None] = {
            slot: None for slot in EquipSlot
        }
        # 10 general pouch slots
        self.pouch: list[Item] = []
        # 3 quick-use belt slots
        self.belt: list[ConsumableItem | None] = [None] * MAX_BELT_SLOTS

    def get_equipment_stats(self) -> Stats:
        """Aggregate stat bonuses from all currently equipped gear."""
        total = Stats(max_hp=0, attack=0, defense=0, speed=0, crit_chance=0.0)
        for gear in self.equipment.values():
            if gear is not None:
                total = total.add(gear.stats_bonus)
        return total

    def equip(self, item: EquipmentItem) -> EquipmentItem | None:
        """Equip an item into its designated slot. Returns previously equipped gear if any."""
        slot = item.slot
        previous = self.equipment[slot]
        self.equipment[slot] = item
        return previous

    def unequip(self, slot: EquipSlot) -> EquipmentItem | None:
        """Unequip item from a slot and return it."""
        current = self.equipment[slot]
        if current is not None:
            if len(self.pouch) < MAX_POUCH_SLOTS:
                self.equipment[slot] = None
                self.pouch.append(current)
                return current
        return None

    def add_to_pouch(self, item: Item) -> bool:
        """Add an item into the 10-slot pouch if space permits."""
        if len(self.pouch) < MAX_POUCH_SLOTS:
            self.pouch.append(item)
            return True
        return False

    def remove_from_pouch(self, index: int) -> Item | None:
        """Remove and return item at specified pouch index."""
        if 0 <= index < len(self.pouch):
            return self.pouch.pop(index)
        return None

    def assign_to_belt(self, pouch_index: int, belt_index: int) -> bool:
        """Move a consumable item from pouch to one of the 3 belt slots."""
        if not (0 <= belt_index < MAX_BELT_SLOTS):
            return False
        if not (0 <= pouch_index < len(self.pouch)):
            return False

        item = self.pouch[pouch_index]
        if not isinstance(item, ConsumableItem):
            return False

        # Pop from pouch and swap with current belt occupant
        self.pouch.pop(pouch_index)
        old_belt_item = self.belt[belt_index]
        self.belt[belt_index] = item
        if old_belt_item is not None:
            self.pouch.append(old_belt_item)
        return True

    def use_belt_item(self, belt_index: int, target: Actor) -> bool:
        """Consume an item from the specified belt slot."""
        if not (0 <= belt_index < MAX_BELT_SLOTS):
            return False
        item = self.belt[belt_index]
        if item is not None and item.use(target):
            self.belt[belt_index] = None
            return True
        return False
