"""Player hero entity with class promotion trees and inventory management."""

from __future__ import annotations

from enum import Enum
from typing import Final

from src.entities.actor import Actor, Stats
from src.systems.inventory import Inventory


class ClassPromotion(Enum):
    """Hero class promotion hierarchy."""

    NOVICE = "Novice"
    # Tier 1 Promotions
    WARRIOR = "Warrior"
    MAGE = "Mage"
    ROGUE = "Rogue"
    # Tier 2 Advanced Promotions
    PALADIN = "Paladin"
    ARCHMAGE = "Archmage"
    ASSASSIN = "Assassin"


# Available promotion paths per current class
PROMOTION_PATHS: Final[dict[ClassPromotion, list[ClassPromotion]]] = {
    ClassPromotion.NOVICE: [
        ClassPromotion.WARRIOR,
        ClassPromotion.MAGE,
        ClassPromotion.ROGUE,
    ],
    ClassPromotion.WARRIOR: [ClassPromotion.PALADIN],
    ClassPromotion.MAGE: [ClassPromotion.ARCHMAGE],
    ClassPromotion.ROGUE: [ClassPromotion.ASSASSIN],
    ClassPromotion.PALADIN: [],
    ClassPromotion.ARCHMAGE: [],
    ClassPromotion.ASSASSIN: [],
}

# Stat bonuses applied upon promotion
PROMOTION_STAT_BONUSES: Final[dict[ClassPromotion, Stats]] = {
    ClassPromotion.WARRIOR: Stats(max_hp=30, attack=6, defense=5, speed=1, crit_chance=0.02),
    ClassPromotion.MAGE: Stats(max_hp=10, attack=12, defense=1, speed=2, crit_chance=0.05),
    ClassPromotion.ROGUE: Stats(max_hp=15, attack=8, defense=2, speed=5, crit_chance=0.10),
    ClassPromotion.PALADIN: Stats(max_hp=60, attack=10, defense=12, speed=2, crit_chance=0.03),
    ClassPromotion.ARCHMAGE: Stats(max_hp=25, attack=24, defense=3, speed=4, crit_chance=0.08),
    ClassPromotion.ASSASSIN: Stats(max_hp=30, attack=18, defense=4, speed=10, crit_chance=0.18),
}


class Player(Actor):
    """The player-controlled champion venturing through Aethelgard."""

    def __init__(self, name: str = "Aethelgard Hero") -> None:
        initial_stats = Stats(max_hp=100, attack=12, defense=4, speed=10, crit_chance=0.05)
        super().__init__(name=name, base_stats=initial_stats)

        self.promotion: ClassPromotion = ClassPromotion.NOVICE
        self.level: int = 1
        self.experience: int = 0
        self.exp_to_next_level: int = 50
        self.gold: int = 0
        self.stat_points: int = 0
        self.inventory: Inventory = Inventory()

    @property
    def effective_stats(self) -> Stats:
        """Base stats combined with active equipment bonuses."""
        equip_bonuses = self.inventory.get_equipment_stats()
        return self.base_stats.add(equip_bonuses)

    @property
    def max_hp(self) -> int:
        """Total maximum HP including equipment modifiers."""
        return self.effective_stats.max_hp

    def gain_experience(self, amount: int) -> bool:
        """Add experience points and process level-ups. Returns True if leveled up."""
        if amount <= 0:
            return False

        self.experience += amount
        leveled_up = False
        while self.experience >= self.exp_to_next_level:
            self.experience -= self.exp_to_next_level
            self.level += 1
            self.exp_to_next_level = int(self.exp_to_next_level * 1.5)
            self._apply_level_up_bonuses()
            leveled_up = True
        return leveled_up

    def _apply_level_up_bonuses(self) -> None:
        """Grant stat boosts on leveling."""
        self.base_stats = self.base_stats.add(
            Stats(max_hp=15, attack=2, defense=1, speed=1, crit_chance=0.005)
        )
        self.current_hp = self.max_hp
        self.stat_points += 2

    def available_promotions(self) -> list[ClassPromotion]:
        """List promotions reachable from the current class."""
        min_level_required = 5 if self.promotion == ClassPromotion.NOVICE else 15
        if self.level >= min_level_required:
            return PROMOTION_PATHS.get(self.promotion, [])
        return []

    def promote(self, target_class: ClassPromotion) -> bool:
        """Promote hero to a higher class tier if eligible."""
        if target_class in self.available_promotions():
            bonus = PROMOTION_STAT_BONUSES.get(
                target_class,
                Stats(max_hp=0, attack=0, defense=0, speed=0, crit_chance=0.0),
            )
            self.base_stats = self.base_stats.add(bonus)
            self.current_hp = self.max_hp
            self.promotion = target_class
            return True
        return False
