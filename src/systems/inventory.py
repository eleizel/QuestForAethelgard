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
    SHOULDERS = "Shoulders"
    CHEST = "Chest"
    WAIST = "Waist"
    HANDS = "Hands"
    LEGS = "Legs"
    MAIN_HAND = "Main Hand"
    OFF_HAND = "Off Hand"


class WeaponType(Enum):
    ONE_HANDED = auto()
    TWO_HANDED = auto()
    SHIELD = auto()
    FOCUS = auto()
    WAND = auto()


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
    weapon_type: WeaponType | None = None
    required_class: str | None = None
    on_hit_status: str | None = None
    on_hit_chance: float = 0.0
    immune_statuses: list[str] = field(default_factory=list)


@dataclass
class ConsumableItem(Item):
    """Items usable from pouch or the 3-slot belt."""

    heal_amount: int = 25
    item_type: ItemType = ItemType.CONSUMABLE
    cleanses_debuffs: bool = False
    applied_status: str | None = None
    status_duration: int = 0
    status_potency: int = 0

    def use(self, target: Actor) -> bool:
        """Apply the item effect on an actor."""
        if not target.is_alive:
            return False

        used = False
        if self.heal_amount > 0:
            target.heal(self.heal_amount)
            used = True

        if self.cleanses_debuffs:
            cleansed = target.cleanse_debuffs()
            used = True

        if self.applied_status:
            from src.systems.status import get_status_by_id
            effect = get_status_by_id(self.applied_status, duration=self.status_duration, potency=self.status_potency)
            if effect:
                target.apply_status(effect)
                used = True

        return used


class Inventory:
    """Player inventory containing 8 equipment, 10-slot pouch, and 3-slot belt."""

    def __init__(self) -> None:
        self.equipment: dict[EquipSlot, EquipmentItem | None] = {
            slot: None for slot in EquipSlot
        }
        self._cached_stats: Stats | None = None
        self.pouch: list[Item] = []
        self.belt: list[ConsumableItem | None] = [None] * MAX_BELT_SLOTS

    def get_equipment_in_slot(self, slot_name: str) -> EquipmentItem | None:
        """Get the equipment item currently in the specified slot name."""
        try:
            slot = EquipSlot(slot_name)
            return self.equipment.get(slot)
        except ValueError:
            return None

    def get_equipment_stats(self) -> Stats:
        """Aggregate stat bonuses from all currently equipped gear."""
        if self._cached_stats is not None:
            return self._cached_stats

        total = Stats(max_hp=0, attack=0, defense=0, speed=0, crit_chance=0.0)
        for gear in self.equipment.values():
            if gear is not None:
                total = total.add(gear.stats_bonus)

        self._cached_stats = total
        return total

    def equip(self, item: EquipmentItem) -> EquipmentItem | None:
        """Equip an item into its designated slot. Returns previously equipped gear if any."""
        slot = item.slot
        previous = self.equipment[slot]
        self.equipment[slot] = item
        self._cached_stats = None
        return previous

    def unequip(self, slot: EquipSlot) -> EquipmentItem | None:
        """Unequip item from a slot and return it."""
        current = self.equipment[slot]
        if current is not None:
            if len(self.pouch) < MAX_POUCH_SLOTS:
                self.equipment[slot] = None
                self._cached_stats = None
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

    def can_equip(self, item: EquipmentItem, player: Actor | None = None) -> tuple[bool, str]:
        if item.required_class is not None and player is not None:
            if getattr(player, "class_id", None) != item.required_class:
                return (False, f"Requires {item.required_class.capitalize()}!")

        if item.weapon_type == WeaponType.TWO_HANDED and self.equipment[EquipSlot.OFF_HAND] is not None:
            if len(self.pouch) >= MAX_POUCH_SLOTS:
                return (False, "Pouch full! Cannot unequip off-hand.")

        return (True, "OK")

    def equip_from_pouch(self, pouch_index: int, player: Actor | None = None) -> tuple[bool, str]:
        from src.core.i18n import t
        if not (0 <= pouch_index < len(self.pouch)):
            return (False, t("msg_invalid_pouch"))

        item = self.pouch[pouch_index]
        if not isinstance(item, EquipmentItem):
            return (False, t("msg_not_equipment"))

        success, message = self.can_equip(item, player)
        if not success:
            return (success, message)

        # For Two Handed weapon equipping logic
        if item.weapon_type == WeaponType.TWO_HANDED and item.slot == EquipSlot.MAIN_HAND:
            # First unequip off hand if there is something
            off_hand = self.equipment[EquipSlot.OFF_HAND]
            if off_hand is not None:
                self.equipment[EquipSlot.OFF_HAND] = None
                self._cached_stats = None
                self.pouch.append(off_hand)

        # If we are equipping something in MAIN_HAND or OFF_HAND, check if we had a TWO_HANDED weapon
        # Wait, doing it in steps is safer. We will pop first anyway.
        popped_item = self.pouch.pop(pouch_index)

        if popped_item.slot in (EquipSlot.MAIN_HAND, EquipSlot.OFF_HAND):
            current_main = self.equipment[EquipSlot.MAIN_HAND]
            if current_main is not None and current_main.weapon_type == WeaponType.TWO_HANDED:
                self.equipment[EquipSlot.MAIN_HAND] = None
                self._cached_stats = None
                self.pouch.append(current_main)

        # Standard equip
        old_item = self.equipment[popped_item.slot]
        self.equipment[popped_item.slot] = popped_item
        self._cached_stats = None
        if old_item is not None:
            self.pouch.append(old_item)

        return (True, t("msg_equipped", item=popped_item.name))

    def unequip_to_pouch(self, slot: EquipSlot) -> tuple[bool, str]:
        item = self.equipment[slot]
        if item is None:
            return (False, "Slot is empty.")

        if len(self.pouch) >= MAX_POUCH_SLOTS:
            return (False, "Pouch full!")

        self.equipment[slot] = None
        self._cached_stats = None
        self.pouch.append(item)
        return (True, f"Unequipped {item.name}.")

    def drop_from_pouch(self, pouch_index: int) -> tuple[bool, str]:
        if not (0 <= pouch_index < len(self.pouch)):
            return (False, "Invalid pouch index.")
        item = self.pouch.pop(pouch_index)
        return (True, f"Discarded {item.name}.")

    def assign_pouch_to_belt(self, pouch_index: int, belt_index: int) -> tuple[bool, str]:
        if not (0 <= belt_index < MAX_BELT_SLOTS):
            return (False, "Invalid belt index.")
        if not (0 <= pouch_index < len(self.pouch)):
            return (False, "Invalid pouch index.")

        item = self.pouch[pouch_index]
        if not isinstance(item, ConsumableItem):
            return (False, "Not a consumable.")

        self.pouch.pop(pouch_index)
        old_belt_item = self.belt[belt_index]
        self.belt[belt_index] = item
        if old_belt_item is not None:
            self.pouch.append(old_belt_item)

        return (True, f"Assigned {item.name} to Belt [{belt_index + 1}].")

    def use_belt_item(self, belt_index: int, target: Actor) -> bool:
        """Consume an item from the specified belt slot."""
        if not (0 <= belt_index < MAX_BELT_SLOTS):
            return False
        item = self.belt[belt_index]
        if item is not None and item.use(target):
            self.belt[belt_index] = None
            return True
        return False
