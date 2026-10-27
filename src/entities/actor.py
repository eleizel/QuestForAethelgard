"""Base entity class for stats, health points, and combat calculations."""

from __future__ import annotations

import random
import secrets
from dataclasses import dataclass


@dataclass
class Stats:
    """Core numeric attributes for combatants."""

    max_hp: int
    attack: int
    defense: int
    speed: int
    crit_chance: float = 0.05  # 5% baseline critical strike chance

    def add(self, other: Stats) -> Stats:
        """Combine two Stats instances, e.g., base stats plus equipment bonuses."""
        return Stats(
            max_hp=max(1, self.max_hp + other.max_hp),
            attack=max(0, self.attack + other.attack),
            defense=max(0, self.defense + other.defense),
            speed=max(1, self.speed + other.speed),
            crit_chance=max(0.0, min(1.0, self.crit_chance + other.crit_chance)),
        )


class Actor:
    """Base actor representing any combat-capable creature."""

    def __init__(self, name: str, base_stats: Stats) -> None:
        self.name: str = name
        self.base_stats: Stats = base_stats
        self.current_hp: int = base_stats.max_hp
        from src.systems.status import StatusEffect
        self.statuses: list[StatusEffect] = []

    def apply_status(self, effect: 'src.systems.status.StatusEffect') -> None:
        # Check for immunities from equipment if player
        if hasattr(self, "inventory"):
            immune = []
            for slot in ['Head', 'Shoulders', 'Chest', 'Waist', 'Hands', 'Legs', 'Main Hand', 'Off Hand', 'Ring',
                         'Amulet']:
                item = self.inventory.get_equipment_in_slot(slot)
                if item and getattr(item, "immune_statuses", None):
                    immune.extend(item.immune_statuses)
            if effect.id in immune:
                return

        for existing in self.statuses:
            if existing.id == effect.id:
                existing.duration = max(existing.duration, effect.duration)
                existing.potency = max(existing.potency, effect.potency)
                return
        self.statuses.append(effect.clone())

    def remove_status(self, status_id: str) -> bool:
        for s in self.statuses:
            if s.id == status_id:
                self.statuses.remove(s)
                return True
        return False

    def cleanse_debuffs(self) -> int:
        from src.systems.status import StatusType
        before = len(self.statuses)
        self.statuses = [s for s in self.statuses if s.status_type == StatusType.BUFF]
        return before - len(self.statuses)

    def has_status(self, status_id: str) -> bool:
        return any(s.id == status_id for s in self.statuses)

    @property
    def stat_modifiers(self) -> Stats:
        from src.systems.status import StatusTrigger
        mod_atk, mod_def, mod_spd = 0, 0, 0
        for s in self.statuses:
            if s.trigger == StatusTrigger.STAT_MOD:
                if s.id == "fortify":
                    mod_def += s.potency
                elif s.id == "weaken":
                    mod_atk -= s.potency
                elif s.id == "haste":
                    mod_spd += s.potency
        return Stats(max_hp=0, attack=mod_atk, defense=mod_def, speed=mod_spd, crit_chance=0.0)

    @property
    def is_alive(self) -> bool:
        """Check if the actor's HP is greater than zero."""
        return self.current_hp > 0

    @property
    def max_hp(self) -> int:
        """Get the current maximum HP."""
        return self.base_stats.max_hp

    def take_damage(self, raw_damage: int) -> int:
        """Apply damage mitigated by defense. Returns actual damage suffered."""
        from src.core.math_utils import calculate_damage
        effective_defense = max(0, self.base_stats.defense)
        mitigated = calculate_damage(raw_damage, effective_defense)
        actual_damage = min(self.current_hp, mitigated)
        self.current_hp -= actual_damage
        return actual_damage

    def heal(self, amount: int) -> int:
        """Restore health up to max HP. Returns actual amount restored."""
        if not self.is_alive or amount <= 0:
            return 0
        missing_hp = self.max_hp - self.current_hp
        restored = min(missing_hp, amount)
        self.current_hp += restored
        return restored

    def calculate_attack(self, rng: random.Random | None = None) -> tuple[int, bool]:
        """Compute outgoing damage and whether the attack was a critical hit."""
        rand = rng if rng is not None else secrets.SystemRandom()
        is_crit = rand.random() < self.base_stats.crit_chance
        variance = rand.uniform(0.9, 1.1)
        dmg = int(self.base_stats.attack * variance)
        if is_crit:
            dmg = int(dmg * 1.5)
        return max(1, dmg), is_crit
