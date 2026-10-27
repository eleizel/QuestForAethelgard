from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from src.entities.actor import Stats

if TYPE_CHECKING:
    from src.entities.actor import Actor


class ItemType(Enum):
    EQUIPMENT = auto()
    CONSUMABLE = auto()
    MATERIAL = auto()


class EquipSlot(Enum):
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
    id: str
    name: str
    description: str
    item_type: ItemType = ItemType.MATERIAL
    gold_value: int = 10

    @property
    def localized_name(self) -> str:
        from src.core.i18n import t
        return t(f"item_{self.id}_name")

    @property
    def localized_description(self) -> str:
        from src.core.i18n import t
        return t(f"item_{self.id}_desc")


@dataclass
class EquipmentItem(Item):
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
    heal_amount: int = 25
    item_type: ItemType = ItemType.CONSUMABLE
    cleanses_debuffs: bool = False
    applied_status: str | None = None
    status_duration: int = 0
    status_potency: int = 0

    def use(self, target: Actor) -> bool:
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
