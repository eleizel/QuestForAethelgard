"""Ability framework for Quest for Aethelgard.

Provides:
- Active & Passive ability models with combat execution hooks
- 11 abilities per base class (Warrior, Rogue, Mage):
    - 1 Default Starter Active
    - 3 Standard Actives
    - 3 Standard Passives
    - 2 Epic Actives
    - 2 Epic Passives
- Total of 33 production abilities + debug commands
- Registry lookups and milestone draft generators
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from src.entities.actor import Actor, Stats
    from src.systems.combat import CombatSystem


class AbilityType(Enum):
    """Classification of an ability."""

    ACTIVE = auto()
    PASSIVE = auto()


class AbilityRarity(Enum):
    """Rarity of an ability."""

    STANDARD = auto()
    EPIC = auto()


class Ability:
    """Core class representing an active skill or passive effect."""

    def __init__(
            self,
            id: str,
            name: str,
            description: str,
            ability_type: AbilityType,
            rarity: AbilityRarity,
            required_class: str | None = None,  # None = Universal, or 'warrior', 'rogue', 'mage'
            cooldown: int = 0,
            execute_hook: Callable[[CombatSystem], tuple[str, int, bool]] | None = None,
            modify_stats_hook: Callable[[Stats], Stats] | None = None,
            on_damage_taken_hook: Callable[[Actor, int], int] | None = None,
            on_attack_dealt_hook: Callable[[Actor, Actor, int, bool], None] | None = None,
            modify_actor_stats_hook: Callable[[Actor, Stats], Stats] | None = None,
            affinities: tuple[str, ...] = (),
            is_stance: bool = False,
    ) -> None:
        self.id: str = id
        self._raw_name: str = name
        self._raw_description: str = description
        self.ability_type: AbilityType = ability_type
        self.rarity: AbilityRarity = rarity
        self.required_class: str | None = required_class
        self.cooldown: int = cooldown
        self.execute_hook = execute_hook
        self.modify_stats_hook = modify_stats_hook
        self.on_damage_taken_hook = on_damage_taken_hook
        self.on_attack_dealt_hook = on_attack_dealt_hook
        self.modify_actor_stats_hook = modify_actor_stats_hook
        self.affinities: tuple[str, ...] = tuple(affinities)
        self.is_stance: bool = is_stance

    @property
    def name(self) -> str:
        from src.core.i18n import t
        trans = t(f"ability_{self.id}_name")
        return trans if trans != f"ability_{self.id}_name" else self._raw_name

    @name.setter
    def name(self, value: str) -> None:
        self._raw_name = value

    @property
    def description(self) -> str:
        from src.core.i18n import t
        trans = t(f"ability_{self.id}_desc")
        return trans if trans != f"ability_{self.id}_desc" else self._raw_description

    @description.setter
    def description(self, value: str) -> None:
        self._raw_description = value

    @property
    def localized_name(self) -> str:
        return self.name

    @property
    def localized_description(self) -> str:
        return self.description

    @property
    def localized_type(self) -> str:
        from src.core.i18n import t
        key = "ability_type_active" if self.ability_type == AbilityType.ACTIVE else "ability_type_passive"
        return t(key)

    @property
    def localized_rarity(self) -> str:
        from src.core.i18n import t
        key = "rarity_standard" if self.rarity == AbilityRarity.STANDARD else "rarity_epic"
        return t(key)

    def execute(self, combat_state: CombatSystem) -> tuple[str, int, bool]:
        """Invoke active ability effect, returning combat log string and outcome."""
        if self.ability_type == AbilityType.ACTIVE and self.execute_hook:
            return self.execute_hook(combat_state)
        return "", 0, False

    def modify_stats(self, stats: Stats) -> Stats:
        """Apply passive stat modifications."""
        if self.ability_type == AbilityType.PASSIVE and self.modify_stats_hook:
            return self.modify_stats_hook(stats)
        return stats

    def modify_actor_stats(self, actor: Actor, stats: Stats) -> Stats:
        """Apply passive stat modifications that depend on the actor's current state."""
        if self.ability_type == AbilityType.PASSIVE and self.modify_actor_stats_hook:
            return self.modify_actor_stats_hook(actor, stats)
        return stats

    def on_damage_taken(self, actor: Actor, raw_damage: int) -> int:
        """Hook triggered before damage is finalized."""
        if self.ability_type == AbilityType.PASSIVE and self.on_damage_taken_hook:
            return self.on_damage_taken_hook(actor, raw_damage)
        return raw_damage

    def on_attack_dealt(self, actor: Actor, target: Actor, damage: int, is_crit: bool) -> None:
        """Hook triggered after damage is dealt."""
        if self.ability_type == AbilityType.PASSIVE and self.on_attack_dealt_hook:
            self.on_attack_dealt_hook(actor, target, damage, is_crit)

    def __repr__(self) -> str:
        return f"Ability(id={self.id!r}, name={self.name!r}, ability_type={self.ability_type}, rarity={self.rarity})"


@dataclass
class PlayerAbilities:
    """Manages player equipped active and passive skills."""

    active: list[Ability] = field(default_factory=list)
    passive: list[Ability] = field(default_factory=list)
    has_veterans_instincts: bool = field(default=False, init=False)

    def _update_cached_flags(self) -> None:
        self.has_veterans_instincts = any(a.id == "veterans_instincts" for a in self.passive)

    def add_ability(self, ability: Ability) -> bool:
        """Attempt to add an ability. Returns True if added without replacing."""
        target_list = self.active if ability.ability_type == AbilityType.ACTIVE else self.passive
        if len(target_list) < 2:
            target_list.append(ability)
            self._update_cached_flags()
            return True
        return False

    def replace_ability(self, ability: Ability, slot_index: int) -> None:
        """Replace ability in specified slot."""
        target_list = self.active if ability.ability_type == AbilityType.ACTIVE else self.passive
        if 0 <= slot_index < len(target_list):
            target_list[slot_index] = ability
            self._update_cached_flags()
