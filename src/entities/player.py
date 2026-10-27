"""Player hero entity with class promotion trees and inventory management."""

from __future__ import annotations

from dataclasses import replace

import src.systems.inventory
from src.data.classes import CLASS_REGISTRY
from src.entities.actor import Actor, Stats
from src.systems.abilities import PlayerAbilities


class Player(Actor):
    """The player-controlled champion venturing through Aethelgard."""

    def __init__(self, name: str = "Sir Aethelgard", class_id: str = "warrior") -> None:
        self.class_id = class_id
        class_def = CLASS_REGISTRY[self.class_id]

        # Each run needs its own mutable stats; events permanently modify these.
        super().__init__(name=name, base_stats=replace(class_def.base_stats))

        self.level: int = 1
        self.experience: int = 0
        self.exp_to_next_level: int = 50
        self.gold: int = 0
        self.stat_points: int = 0
        self.inventory: 'src.systems.inventory.Inventory' = src.systems.inventory.Inventory()
        self.exp_multiplier: float = class_def.exp_multiplier
        self.pending_ability_choices: list[str] = []  # "STANDARD" or "EPIC"
        self.combat_def_buff: int = 0
        self.abilities = PlayerAbilities()

        from src.data.abilities import get_ability_by_id
        for ab_id in class_def.starting_abilities:
            ability = get_ability_by_id(ab_id)
            if ability:
                self.abilities.add_ability(ability)

    @property
    def class_name(self) -> str:
        from src.core.i18n import t
        return t(f"class_{self.class_id}_name")

    @property
    def effective_stats(self) -> Stats:
        """Base stats combined with active equipment bonuses and passive abilities."""
        equip_bonuses = self.inventory.get_equipment_stats()
        stats = self.base_stats.add(equip_bonuses).add(self.stat_modifiers)
        for passive in self.abilities.passive:
            stats = passive.modify_stats(stats)
            stats = passive.modify_actor_stats(self, stats)

        # Colossus stance check
        has_colossus = any(a.id == "colossus_stance" for a in self.abilities.passive)
        if has_colossus and self.current_hp < stats.max_hp * 0.35:
            bonus_atk = int(stats.attack * 0.3)
            from src.entities.actor import Stats
            stats = stats.add(Stats(max_hp=0, attack=bonus_atk, defense=0, speed=0, crit_chance=0.0))

        if self.combat_def_buff > 0:
            from src.entities.actor import Stats
            stats = stats.add(Stats(max_hp=0, attack=0, defense=self.combat_def_buff, speed=0, crit_chance=0.0))

        return stats

    @property
    def max_hp(self) -> int:
        """Total maximum HP including equipment modifiers."""
        return self.effective_stats.max_hp

    def take_damage(self, raw_damage: int, defense_penetration: float = 0.0) -> int:
        """Apply damage mitigated by defense and passive abilities."""
        from src.core.math_utils import calculate_damage
        if getattr(self, "_reckless_assault_vulnerable", False):
            raw_damage = int(raw_damage * 1.10)
        for passive in self.abilities.passive:
            raw_damage = passive.on_damage_taken(self, raw_damage)

        effective_defense = max(0, self.effective_stats.defense)
        mitigated = calculate_damage(raw_damage, effective_defense, defense_penetration)

        has_undying_will = any(a.id == "undying_will" for a in self.abilities.passive)
        if has_undying_will and self.current_hp - mitigated <= 0 and not getattr(self, "undying_will_used", False):
            self.undying_will_used = True
            self.current_hp = int(self.max_hp * 0.4)
            return 0

        actual_damage = min(self.current_hp, mitigated)
        self.current_hp -= actual_damage

        # Shadow Step triggers only when the player actually loses HP, not on fully mitigated hits.
        if actual_damage > 0 and any(a.id == "shadow_step" for a in self.abilities.passive):
            combat = getattr(self, "combat_ref", None)
            if combat:
                combat.player_gauge = min(100, combat.player_gauge + 15)

        return actual_damage

    def gain_experience(self, amount: int, foe_type: str | None = None) -> bool:
        """Add experience points and process level-ups. Returns True if leveled up."""
        from src.core.math_utils import calculate_exp_threshold
        if amount <= 0:
            return False

        self.experience += int(amount * self.exp_multiplier)
        leveled_up = False

        while self.level < 20 and self.experience >= self.exp_to_next_level:
            self.experience -= self.exp_to_next_level
            self.level += 1
            self.exp_to_next_level = calculate_exp_threshold(self.level)
            self._apply_level_up_bonuses()
            self._check_ability_milestone()
            leveled_up = True

        if self.level == 20 and self.experience > self.exp_to_next_level:
            self.experience = self.exp_to_next_level

        return leveled_up

    def _apply_level_up_bonuses(self) -> None:
        """Grant stat boosts on leveling."""
        class_def = CLASS_REGISTRY[self.class_id]
        self.base_stats = self.base_stats.add(class_def.growth_per_level)
        self.current_hp = self.max_hp
        self.stat_points += 2

    def _check_ability_milestone(self) -> None:
        if self.level in (4, 8, 12, 16):
            self.pending_ability_choices.append("STANDARD")
        elif self.level in (10, 20):
            self.pending_ability_choices.append("EPIC")

    def available_promotions(self) -> list[str]:
        """List promotions reachable from the current class."""
        min_level_required = 15
        if self.level >= min_level_required:
            return CLASS_REGISTRY[self.class_id].promotions
        return []

    def promote(self, target_class_id: str) -> bool:
        """Promote hero to a higher class tier if eligible."""
        if target_class_id in self.available_promotions():
            new_class_def = CLASS_REGISTRY[target_class_id]
            # When promoting, replace base stats but we might want to keep the old leveled up stat bonuses.
            # In standard RPG promotion often gives a fixed boost or sets new base.
            # We'll calculate stat diff from old base to new base, and add to current base_stats to keep level-up gains.
            old_base = CLASS_REGISTRY[self.class_id].base_stats

            # Stat diff is (new_base - old_base), handling negatives by direct replacement of stat calculation
            diff_hp = max(0, new_class_def.base_stats.max_hp - old_base.max_hp)
            diff_atk = max(0, new_class_def.base_stats.attack - old_base.attack)
            diff_def = max(0, new_class_def.base_stats.defense - old_base.defense)
            diff_spd = max(0, new_class_def.base_stats.speed - old_base.speed)
            diff_crit = max(0, new_class_def.base_stats.crit_chance - old_base.crit_chance)

            bonus = Stats(
                max_hp=diff_hp, attack=diff_atk, defense=diff_def, speed=diff_spd, crit_chance=diff_crit
            )
            self.base_stats = self.base_stats.add(bonus)
            self.current_hp = self.max_hp
            self.class_id = target_class_id
            return True
        return False
