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

import random
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
        execute_hook: Callable[[CombatSystem], tuple[str, int, bool]] | None = None,
        modify_stats_hook: Callable[[Stats], Stats] | None = None,
        on_damage_taken_hook: Callable[[Actor, int], int] | None = None,
        on_attack_dealt_hook: Callable[[Actor, Actor, int, bool], None] | None = None,
    ) -> None:
        self.id: str = id
        self._raw_name: str = name
        self._raw_description: str = description
        self.ability_type: AbilityType = ability_type
        self.rarity: AbilityRarity = rarity
        self.required_class: str | None = required_class

        self.execute_hook = execute_hook
        self.modify_stats_hook = modify_stats_hook
        self.on_damage_taken_hook = on_damage_taken_hook
        self.on_attack_dealt_hook = on_attack_dealt_hook

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


# =============================================================================
# 1. STARTER ACTIVE ABILITIES (1 Per Class + Debug)
# =============================================================================

# --- Warrior Starter: Cross Cut ---
def execute_cross_cut(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    raw_dmg1, crit1 = combat.player.calculate_attack(combat.rng)
    raw_dmg2, crit2 = combat.player.calculate_attack(combat.rng)
    dmg1 = int(raw_dmg1 * 0.90)
    dmg2 = int(raw_dmg2 * 0.90)
    total_dmg = combat.enemy.take_damage(dmg1) + combat.enemy.take_damage(dmg2)
    any_crit = crit1 or crit2
    return t("log_cross_cut", player=combat.player.name, dmg=total_dmg), total_dmg, any_crit

CROSS_CUT = Ability(
    id="cross_cut",
    name="Cross Cut",
    description="Strikes 2 times at 90% ATK each.",
    ability_type=AbilityType.ACTIVE,
    rarity=AbilityRarity.STANDARD,
    required_class="warrior",
    execute_hook=execute_cross_cut,
)

# --- Rogue Starter: Shadow Strike ---
def execute_shadow_strike(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import i18n, t
    rng = combat.rng
    crit_chance = combat.player.effective_stats.crit_chance + 0.25
    is_crit = rng.random() < crit_chance
    dmg = int(combat.player.effective_stats.attack * 1.35)
    if is_crit:
        dmg = int(dmg * 1.5)
        combat.player_gauge = min(100, combat.player_gauge + 25)
    actual_dmg = combat.enemy.take_damage(dmg)
    crit_msg = (" (¡EMBOSCADA CRÍTICA!)" if i18n.locale == "es" else " (CRITICAL AMBUSH!)") if is_crit else ""
    return t("log_shadow_strike", player=combat.player.name, dmg=actual_dmg, crit=crit_msg), actual_dmg, is_crit

SHADOW_STRIKE = Ability(
    id="shadow_strike",
    name="Shadow Strike",
    description="Deals 135% ATK (+25% Crit). Crits refund 25 gauge.",
    ability_type=AbilityType.ACTIVE,
    rarity=AbilityRarity.STANDARD,
    required_class="rogue",
    execute_hook=execute_shadow_strike,
)

# --- Mage Starter: Arcane Bolt ---
def execute_arcane_bolt(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import i18n, t
    rng = combat.rng
    is_crit = rng.random() < combat.player.effective_stats.crit_chance
    raw_dmg = int(combat.player.effective_stats.attack * 1.50)
    if is_crit:
        raw_dmg = int(raw_dmg * 1.5)
    mitigated_dmg = max(1, raw_dmg - (combat.enemy.base_stats.defense // 4))
    actual_dmg = combat.enemy.take_damage(mitigated_dmg)
    crit_msg = (" (¡ARCANA DESATADA!)" if i18n.locale == "es" else " (SURGING ARCANA!)") if is_crit else ""
    return t("log_arcane_bolt", player=combat.player.name, dmg=actual_dmg, crit=crit_msg), actual_dmg, is_crit

ARCANE_BOLT = Ability(
    id="arcane_bolt",
    name="Arcane Bolt",
    description="Piercing bolt dealing 150% ATK (ignores 50% DEF).",
    ability_type=AbilityType.ACTIVE,
    rarity=AbilityRarity.STANDARD,
    required_class="mage",
    execute_hook=execute_arcane_bolt,
)

# --- Debug Tool ---
def execute_pw_kill(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    actual_dmg = combat.enemy.take_damage(999999)
    return t("log_pw_kill", player=combat.player.name, dmg=actual_dmg), actual_dmg, True

PW_KILL = Ability(
    id="pw_kill",
    name="PW: Kill",
    description="Insta-kill enemy for testing.",
    ability_type=AbilityType.ACTIVE,
    rarity=AbilityRarity.STANDARD,
    execute_hook=execute_pw_kill,
)


# =============================================================================
# 2. WARRIOR STANDARD SKILLS (3 Actives, 3 Passives)
# =============================================================================

def execute_shield_bash(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    dmg = int(combat.player.effective_stats.attack * 0.85)
    actual_dmg = combat.enemy.take_damage(dmg)
    combat.enemy_gauge = max(0, combat.enemy_gauge - 35)
    return t("log_shield_bash", player=combat.player.name, dmg=actual_dmg), actual_dmg, False

def execute_rallying_cry(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    heal_amount = int(combat.player.max_hp * 0.15)
    actual_heal = combat.player.heal(heal_amount)
    combat.player.combat_def_buff += 4
    return t("log_rallying_cry", player=combat.player.name, heal=actual_heal), 0, False

def execute_cleave(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    dmg = int(combat.player.effective_stats.attack * 1.60)
    actual_dmg = combat.enemy.take_damage(dmg)
    return t("log_cleave", player=combat.player.name, dmg=actual_dmg), actual_dmg, False

def modify_iron_skin(stats: Stats) -> Stats:
    bonus_def = int(stats.defense * 0.15)
    return stats.add(type(stats)(max_hp=0, attack=0, defense=bonus_def, speed=0, crit_chance=0.0))

def hook_iron_skin(actor: Actor, raw_damage: int) -> int:
    return max(1, raw_damage - 2)

def modify_veterans_instincts(stats: Stats) -> Stats:
    return stats.add(type(stats)(max_hp=0, attack=0, defense=0, speed=0, crit_chance=0.05))

def hook_bloodlust(actor: Actor, target: Actor, damage: int, is_crit: bool) -> None:
    if damage > 0:
        actor.heal(int(damage * 0.20))


# =============================================================================
# 3. ROGUE STANDARD SKILLS (3 Actives, 3 Passives)
# =============================================================================

def execute_poison_shiv(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    dmg = int(combat.player.effective_stats.attack * 1.05)
    actual_dmg = combat.enemy.take_damage(dmg)
    combat.enemy_gauge = max(0, combat.enemy_gauge - 30)
    return t("log_poison_shiv", player=combat.player.name, dmg=actual_dmg), actual_dmg, False

def execute_smoke_bomb(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    combat.enemy_gauge = max(0, combat.enemy_gauge - 50)
    combat.player_gauge = min(100, combat.player_gauge + 25)
    return t("log_smoke_bomb", player=combat.player.name), 0, False

def execute_flurry_of_daggers(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    total_dmg = 0
    rng = combat.rng
    crit_chance = combat.player.effective_stats.crit_chance + 0.15
    any_crit = False
    for _ in range(3):
        is_crit = rng.random() < crit_chance
        dmg = int(combat.player.effective_stats.attack * 0.55)
        if is_crit:
            dmg = int(dmg * 1.5)
            any_crit = True
        total_dmg += combat.enemy.take_damage(dmg)
    return t("log_flurry_of_daggers", player=combat.player.name, dmg=total_dmg), total_dmg, any_crit

def modify_nimble_reflexes(stats: Stats) -> Stats:
    return stats.add(type(stats)(max_hp=0, attack=0, defense=1, speed=3, crit_chance=0.06))

def hook_exposed_weakness(actor: Actor, target: Actor, damage: int, is_crit: bool) -> None:
    if is_crit and hasattr(actor, "base_stats"):
        setattr(actor, "_next_strike_bonus", True)

def hook_shadow_step_gauge(actor: Actor, raw_damage: int) -> int:
    if raw_damage > 0:
        combat = getattr(actor, "combat_ref", None)
        if combat:
            combat.player_gauge = min(100, combat.player_gauge + 15)
    return raw_damage


# =============================================================================
# 4. MAGE STANDARD SKILLS (3 Actives, 3 Passives)
# =============================================================================

def execute_fireball(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    raw_dmg = int(combat.player.effective_stats.attack * 1.85)
    actual_dmg = combat.enemy.take_damage(raw_dmg)
    return t("log_fireball", player=combat.player.name, dmg=actual_dmg), actual_dmg, False

def execute_frost_nova(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    dmg = int(combat.player.effective_stats.attack * 0.95)
    actual_dmg = combat.enemy.take_damage(dmg)
    combat.enemy_gauge = max(0, combat.enemy_gauge - 45)
    return t("log_frost_nova", player=combat.player.name, dmg=actual_dmg), actual_dmg, False

def execute_chain_lightning(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import i18n, t
    rng = combat.rng
    is_crit = rng.random() < combat.player.effective_stats.crit_chance
    mult = 1.95 if is_crit else 1.30
    dmg = int(combat.player.effective_stats.attack * mult)
    actual_dmg = combat.enemy.take_damage(dmg)
    if is_crit:
        combat.player_gauge = min(100, combat.player_gauge + 40)
    crit_msg = (" (¡SOBRECARGA!)" if i18n.locale == "es" else " (OVERCHARGED SURGE!)") if is_crit else ""
    return t("log_chain_lightning", player=combat.player.name, dmg=actual_dmg, crit=crit_msg), actual_dmg, is_crit

def modify_arcane_ward(stats: Stats) -> Stats:
    return stats.add(type(stats)(max_hp=20, attack=2, defense=3, speed=0, crit_chance=0.02))

def hook_mana_barrier(actor: Actor, raw_damage: int) -> int:
    return max(1, raw_damage - 3)

def hook_pyromania(actor: Actor, target: Actor, damage: int, is_crit: bool) -> None:
    if damage > 0 and random.random() < 0.30:
        burn = max(2, int(actor.effective_stats.attack * 0.40))  # type: ignore
        target.take_damage(burn)


# =============================================================================
# 5. EPIC ABILITIES (2 Actives & 2 Passives Per Class)
# =============================================================================

# --- Warrior Epics ---
def hook_colossus_stance_dmg(actor: Actor, raw_damage: int) -> int:
    if actor.current_hp < actor.max_hp * 0.35:
        return max(1, int(raw_damage * 0.50))
    return raw_damage

def execute_blade_storm(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    total_dmg = 0
    rng = combat.rng
    crit_chance = combat.player.effective_stats.crit_chance + 0.20
    any_crit = False
    for _ in range(4):
        dmg = int(combat.player.effective_stats.attack * 0.60)
        is_crit = rng.random() < crit_chance
        if is_crit:
            dmg = int(dmg * 1.5)
            any_crit = True
        total_dmg += combat.enemy.take_damage(dmg)
    return t("log_blade_storm", player=combat.player.name, dmg=total_dmg), total_dmg, any_crit

def hook_undying_will(actor: Actor, raw_damage: int) -> int:
    return raw_damage

def execute_executioners_might(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    mult = 5.0 if combat.enemy.current_hp < combat.enemy.max_hp * 0.40 else 2.5
    dmg = int(combat.player.effective_stats.attack * mult)
    actual_dmg = combat.enemy.take_damage(dmg)
    return t("log_executioners_might", player=combat.player.name, dmg=actual_dmg), actual_dmg, False

# --- Rogue Epics ---
def execute_assassinate(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import i18n, t
    rng = combat.rng
    crit_chance = combat.player.effective_stats.crit_chance + 0.35
    is_crit = rng.random() < crit_chance
    mult = 3.80 if is_crit else 2.00
    dmg = int(combat.player.effective_stats.attack * mult)
    actual_dmg = combat.enemy.take_damage(dmg)
    crit_str = (" (¡EJECUCIÓN LETAL!)" if i18n.locale == "es" else " (LETHAL EXECUTION!)") if is_crit else ""
    return t("log_assassinate", player=combat.player.name, dmg=actual_dmg, crit=crit_str), actual_dmg, is_crit

def execute_fan_of_knives(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    total_dmg = 0
    delays = 0
    rng = combat.rng
    for _ in range(5):
        dmg = int(combat.player.effective_stats.attack * 0.50)
        total_dmg += combat.enemy.take_damage(dmg)
        if rng.random() < 0.30:
            delays += 15
    combat.enemy_gauge = max(0, combat.enemy_gauge - delays)
    return t("log_fan_of_knives", player=combat.player.name, dmg=total_dmg, delays=delays), total_dmg, False

def hook_shadow_dance_defense(actor: Actor, raw_damage: int) -> int:
    if random.random() < 0.30:
        return 0
    return raw_damage

def modify_death_dealer(stats: Stats) -> Stats:
    return stats.add(type(stats)(max_hp=0, attack=5, defense=0, speed=4, crit_chance=0.15))

# --- Mage Epics ---
def execute_meteor(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    raw_dmg = int(combat.player.effective_stats.attack * 3.20)
    actual_dmg = combat.enemy.take_damage(raw_dmg)
    combat.enemy_gauge = 0
    return t("log_meteor", player=combat.player.name, dmg=actual_dmg), actual_dmg, True

def execute_time_stop(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    combat.player_gauge = 100
    combat.enemy_gauge = 0
    return t("log_time_stop", player=combat.player.name), 0, False

def modify_time_dilation(stats: Stats) -> Stats:
    return stats.add(type(stats)(max_hp=0, attack=8, defense=0, speed=6, crit_chance=0.10))

def hook_phoenix_rebirth(actor: Actor, raw_damage: int) -> int:
    if actor.current_hp - raw_damage <= 0 and not getattr(actor, "_phoenix_used", False):
        setattr(actor, "_phoenix_used", True)
        actor.current_hp = int(actor.max_hp * 0.50)
        return 0
    return raw_damage


# =============================================================================
# 6. MASTER POOLS & REGISTRY CATALOG
# =============================================================================

STANDARD_ABILITIES: list[Ability] = [
    # Starters
    CROSS_CUT,
    SHADOW_STRIKE,
    ARCANE_BOLT,

    # Warrior Standard
    Ability(id="shield_bash", name="Shield Bash", description="Deals 85% ATK, delays enemy gauge by 35.", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="warrior", execute_hook=execute_shield_bash),
    Ability(id="rallying_cry", name="Rallying Cry", description="Restores 15% Max HP, +4 DEF for battle.", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="warrior", execute_hook=execute_rallying_cry),
    Ability(id="cleave", name="Cleave", description="Heavy cleave dealing 160% ATK damage.", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="warrior", execute_hook=execute_cleave),
    Ability(id="iron_skin", name="Iron Skin", description="+15% DEF, flat -2 damage taken.", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="warrior", modify_stats_hook=modify_iron_skin, on_damage_taken_hook=hook_iron_skin),
    Ability(id="veterans_instincts", name="Veteran's Instincts", description="+5% CRIT; crits refund +20 Action Gauge.", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="warrior", modify_stats_hook=modify_veterans_instincts),
    Ability(id="bloodlust", name="Bloodlust", description="Heal for 20% of physical damage dealt.", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="warrior", on_attack_dealt_hook=hook_bloodlust),

    # Rogue Standard
    Ability(id="poison_shiv", name="Poison Shiv", description="Deals 105% ATK and drains 30 enemy gauge.", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="rogue", execute_hook=execute_poison_shiv),
    Ability(id="smoke_bomb", name="Smoke Bomb", description="Stalls enemy by 50 gauge; grants +25 player gauge.", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="rogue", execute_hook=execute_smoke_bomb),
    Ability(id="flurry_of_daggers", name="Flurry of Daggers", description="3 strikes at 55% ATK (+15% Crit chance each).", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="rogue", execute_hook=execute_flurry_of_daggers),
    Ability(id="nimble_reflexes", name="Nimble Reflexes", description="+3 Speed, +6% Crit Chance, +1 Defense.", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="rogue", modify_stats_hook=modify_nimble_reflexes),
    Ability(id="exposed_weakness", name="Exposed Weakness", description="Crits expose enemy vitals for devastating follow-ups.", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="rogue", on_attack_dealt_hook=hook_exposed_weakness),
    Ability(id="shadow_step", name="Shadow Step", description="Taking damage accelerates player gauge by +15.", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="rogue", on_damage_taken_hook=hook_shadow_step_gauge),

    # Mage Standard
    Ability(id="fireball", name="Fireball", description="High-impact blast dealing 185% ATK fire damage.", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="mage", execute_hook=execute_fireball),
    Ability(id="frost_nova", name="Frost Nova", description="Deals 95% ATK and freezes 45 enemy action gauge.", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="mage", execute_hook=execute_frost_nova),
    Ability(id="chain_lightning", name="Chain Lightning", description="Deals 130% ATK. Crits refund 40 player gauge.", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="mage", execute_hook=execute_chain_lightning),
    Ability(id="arcane_ward", name="Arcane Ward", description="+20 Max HP, +2 ATK, +3 DEF.", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="mage", modify_stats_hook=modify_arcane_ward),
    Ability(id="mana_barrier", name="Mana Barrier", description="Kinetic barrier absorbs 3 damage from all attacks.", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="mage", on_damage_taken_hook=hook_mana_barrier),
    Ability(id="pyromania", name="Pyromania", description="Attacks have a 30% chance to ignite foe for 40% ATK.", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="mage", on_attack_dealt_hook=hook_pyromania),
]

EPIC_ABILITIES: list[Ability] = [
    # Warrior Epic
    Ability(id="colossus_stance", name="Colossus Stance", description="When HP < 35%, incoming damage halved & +30% ATK.", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.EPIC, required_class="warrior", on_damage_taken_hook=hook_colossus_stance_dmg),
    Ability(id="blade_storm", name="Blade Storm", description="4 rapid slashes at 60% ATK with +20% bonus Crit.", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.EPIC, required_class="warrior", execute_hook=execute_blade_storm),
    Ability(id="undying_will", name="Undying Will", description="Survive lethal blow once per combat at 40% HP.", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.EPIC, required_class="warrior", on_damage_taken_hook=hook_undying_will),
    Ability(id="executioners_might", name="Executioner's Might", description="250% ATK damage; doubles if enemy < 40% HP.", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.EPIC, required_class="warrior", execute_hook=execute_executioners_might),

    # Rogue Epic
    Ability(id="assassinate", name="Assassinate", description="200% ATK strike (+35% Crit). Crits deal 380% ATK.", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.EPIC, required_class="rogue", execute_hook=execute_assassinate),
    Ability(id="fan_of_knives", name="Fan of Knives", description="5 blades deal 50% ATK each with turn-stall chances.", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.EPIC, required_class="rogue", execute_hook=execute_fan_of_knives),
    Ability(id="shadow_dance", name="Shadow Dance", description="Grants a permanent 30% chance to completely evade any hit.", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.EPIC, required_class="rogue", on_damage_taken_hook=hook_shadow_dance_defense),
    Ability(id="death_dealer", name="Death Dealer", description="+15% Crit Chance, +5 ATK, +4 SPD.", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.EPIC, required_class="rogue", modify_stats_hook=modify_death_dealer),

    # Mage Epic
    Ability(id="meteor", name="Meteor", description="Calls down a meteor for 320% ATK; resets enemy turn to 0.", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.EPIC, required_class="mage", execute_hook=execute_meteor),
    Ability(id="time_stop", name="Time Stop", description="Freezes time: resets enemy to 0 gauge and grants instant turn.", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.EPIC, required_class="mage", execute_hook=execute_time_stop),
    Ability(id="time_dilation", name="Time Dilation", description="+8 ATK, +6 Speed, +10% Crit Chance.", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.EPIC, required_class="mage", modify_stats_hook=modify_time_dilation),
    Ability(id="phoenix_rebirth", name="Phoenix Rebirth", description="Once per combat, lethal blow heals to 50% HP.", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.EPIC, required_class="mage", on_damage_taken_hook=hook_phoenix_rebirth),
]

# Complete Catalog
ABILITY_REGISTRY: dict[str, Ability] = {
    ab.id: ab for ab in (STANDARD_ABILITIES + EPIC_ABILITIES + [PW_KILL])
}


def get_ability_by_id(ability_id: str) -> Ability | None:
    """Retrieve an ability by its catalog ID."""
    return ABILITY_REGISTRY.get(ability_id)


def get_random_abilities(
    rarity: AbilityRarity,
    known_abilities: list[str],
    player_class: str | None = None,
    count: int = 2,
) -> list[Ability]:
    """Retrieve random available abilities matching rarity and class criteria."""
    pool = STANDARD_ABILITIES if rarity == AbilityRarity.STANDARD else EPIC_ABILITIES

    available = [
        ab for ab in pool
        if ab.id not in known_abilities
        and (ab.required_class is None or player_class is None or ab.required_class == player_class)
    ]

    if len(available) < count:
        available = [ab for ab in pool if ab.id not in known_abilities]

    return random.sample(available, min(count, len(available)))