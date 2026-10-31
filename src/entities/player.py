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
        # Preserve saved IDs from previous names for this promotion.
        self.class_id = {"assassin": "venomancer", "envenomator": "venomancer"}.get(class_id, class_id)
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
        self._active_stances: set[str] = set()
        self.signature_passive = None
        self.promotion_due = False
        self.shield: int = 0

        from src.data.abilities import get_ability_by_id
        for ab_id in class_def.starting_abilities:
            ability = get_ability_by_id(ab_id)
            if ability:
                self.abilities.add_ability(ability)

    @property
    def all_passives(self):
        """Equipped passives plus the permanent promotion signature."""
        return [*self.abilities.passive, *([self.signature_passive] if self.signature_passive else [])]

    def activate_stance(self, stance_id: str) -> None:
        self._active_stances.add(stance_id)

    def has_stance(self, stance_id: str) -> bool:
        return stance_id in self._active_stances

    def consume_stance(self, stance_id: str) -> bool:
        if stance_id not in self._active_stances:
            return False
        self._active_stances.remove(stance_id)
        combat = getattr(self, "combat_ref", None)
        if combat:
            combat.on_player_stance_consumed(stance_id)
        return True

    @property
    def class_name(self) -> str:
        from src.core.i18n import t
        return t(f"class_{self.class_id}_name")

    @property
    def effective_stats(self) -> Stats:
        """Base stats combined with active equipment bonuses and passive abilities."""
        equip_bonuses = self.inventory.get_equipment_stats()
        stats = self.base_stats.add(equip_bonuses).add(self.stat_modifiers)
        for passive in self.all_passives:
            stats = passive.modify_stats(stats)
            stats = passive.modify_actor_stats(self, stats)

        # Colossus stance check
        has_colossus = any(a.id == "colossus_stance" for a in self.all_passives)
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
        previous_hp = self.current_hp
        if getattr(self, "_reckless_assault_vulnerable", False):
            raw_damage = int(raw_damage * 1.10)
        for passive in self.all_passives:
            raw_damage = passive.on_damage_taken(self, raw_damage)

        effective_defense = max(0, self.effective_stats.defense)
        mitigated = calculate_damage(raw_damage, effective_defense, defense_penetration)

        if getattr(self, "shield", 0) > 0 and mitigated > 0:
            absorbed = min(self.shield, mitigated)
            self.shield -= absorbed
            mitigated -= absorbed
            combat = getattr(self, "combat_ref", None)
            if combat:
                from src.core.i18n import t
                combat.combat_logs.append(
                    t("combat_archmage_shield_absorbed", actor=self.name, absorbed=absorbed, remaining=self.shield)
                )

        has_undying_will = any(a.id == "undying_will" for a in self.all_passives)
        if has_undying_will and self.current_hp - mitigated <= 0 and not getattr(self, "undying_will_used", False):
            self.undying_will_used = True
            self.current_hp = int(self.max_hp * 0.4)
            return 0

        actual_damage = min(self.current_hp, mitigated)
        self.current_hp -= actual_damage

        # Shadow Step triggers only when the player actually loses HP, not on fully mitigated hits.
        if actual_damage > 0 and any(a.id == "shadow_step" for a in self.all_passives):
            combat = getattr(self, "combat_ref", None)
            if combat:
                combat.player_gauge = min(100, combat.player_gauge + 15)

        if actual_damage > 0 and self.consume_stance("riposte") and self.is_alive:
            combat = getattr(self, "combat_ref", None)
            if combat and combat.enemy.is_alive:
                counter = int(self.effective_stats.attack * 0.50)
                dealt = combat.damage_enemy(counter)
                from src.core.i18n import t
                combat.combat_logs.append(t("combat_riposte_counter", actor=self.name, damage=dealt))

        combat = getattr(self, "combat_ref", None)
        if actual_damage > 0 and combat:
            combat.on_player_damaged(previous_hp, actual_damage)

        return actual_damage

    def gain_experience(self, amount: int, foe_type: str | None = None) -> bool:
        """Add experience points and process level-ups. Returns True if leveled up."""
        from src.core.math_utils import calculate_exp_threshold
        if amount <= 0:
            return False

        self.experience += int(amount * self.exp_multiplier)
        leveled_up = False

        while self.level < 20 and self.experience >= self.exp_to_next_level and not self.promotion_due:
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
        self.heal(int(self.max_hp * 0.50))
        self.stat_points += 2
        if self.available_promotions():
            self.promotion_due = True

    def _check_ability_milestone(self) -> None:
        if self.level in (4, 8, 12, 16):
            self.pending_ability_choices.append("STANDARD")
        elif self.level in (10, 20):
            self.pending_ability_choices.append("EPIC")

    def available_promotions(self) -> list[str]:
        """List promotions reachable from the current class."""
        if self.level >= 10:
            return CLASS_REGISTRY[self.class_id].promotions
        return []

    def promote(self, target_class_id: str) -> bool:
        """Promote hero to a higher class tier if eligible."""
        if target_class_id in self.available_promotions():
            new_class_def = CLASS_REGISTRY[target_class_id]
            self.class_id = target_class_id
            self.exp_multiplier = new_class_def.exp_multiplier
            from src.data.abilities import get_ability_by_id
            self.signature_passive = get_ability_by_id(new_class_def.signature_passive)
            self.heal(int(self.max_hp * 0.50))
            self.promotion_due = False
            # The level-10 Epic draft is the promotion's additional ability reward.
            # Bring it forward before any other queued level-up drafts.
            if "EPIC" in self.pending_ability_choices:
                self.pending_ability_choices.remove("EPIC")
            self.pending_ability_choices.insert(0, "EPIC")
            while self.level < 20 and self.experience >= self.exp_to_next_level:
                self.experience -= self.exp_to_next_level
                self.level += 1
                from src.core.math_utils import calculate_exp_threshold
                self.exp_to_next_level = calculate_exp_threshold(self.level)
                self._apply_level_up_bonuses()
                self._check_ability_milestone()
            return True
        return False
