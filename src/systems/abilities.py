from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, TYPE_CHECKING, Any

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


@dataclass
class Ability:
    """Core dataclass representing a skill or passive effect."""
    id: str
    name: str
    description: str
    ability_type: AbilityType
    rarity: AbilityRarity

    # Active hook
    execute_hook: Callable[[CombatSystem], tuple[str, int, bool]] | None = None

    # Passive hooks
    modify_stats_hook: Callable[[Stats], Stats] | None = None
    on_damage_taken_hook: Callable[[Actor, int], int] | None = None
    on_attack_dealt_hook: Callable[[Actor, Actor, int, bool], None] | None = None

    def execute(self, combat_state: CombatSystem) -> tuple[str, int, bool]:
        """Invokes the active ability effect, returning a combat log string."""
        if self.ability_type == AbilityType.ACTIVE and self.execute_hook:
            return self.execute_hook(combat_state)
        return "", 0, False

    def modify_stats(self, stats: Stats) -> Stats:
        """Applies passive stat modifications."""
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


@dataclass
class PlayerAbilities:
    """Manages the player's active and passive ability loadout."""
    active: list[Ability] = field(default_factory=list)
    passive: list[Ability] = field(default_factory=list)

    def add_ability(self, ability: Ability) -> bool:
        """Attempt to add an ability. Returns True if successfully added without replacing."""
        target_list = self.active if ability.ability_type == AbilityType.ACTIVE else self.passive
        if len(target_list) < 2:
            target_list.append(ability)
            return True
        return False

    def replace_ability(self, ability: Ability, slot_index: int) -> None:
        """Replaces an ability in the specified slot."""
        target_list = self.active if ability.ability_type == AbilityType.ACTIVE else self.passive
        if 0 <= slot_index < len(target_list):
            target_list[slot_index] = ability


# ---------------------------------------------------------
# Default Active Ability
# ---------------------------------------------------------

def execute_cross_cut(combat: CombatSystem) -> tuple[str, int, bool]:
    raw_dmg1, crit1 = combat.player.calculate_attack(combat.rng)
    raw_dmg2, crit2 = combat.player.calculate_attack(combat.rng)

    dmg1 = int(raw_dmg1 * 0.90)
    dmg2 = int(raw_dmg2 * 0.90)

    total_dmg = combat.enemy.take_damage(dmg1) + combat.enemy.take_damage(dmg2)
    any_crit = crit1 or crit2

    return f"{combat.player.name} uses Cross Cut! Deals {total_dmg} total damage!", total_dmg, any_crit

CROSS_CUT = Ability(
    id="cross_cut",
    name="Cross Cut",
    description="Strikes 2 times at 90% ATK.",
    ability_type=AbilityType.ACTIVE,
    rarity=AbilityRarity.STANDARD,
    execute_hook=execute_cross_cut
)

# ---------------------------------------------------------

def execute_pw_kill(combat: CombatSystem) -> tuple[str, int, bool]:
    actual_dmg = combat.enemy.take_damage(999999)
    return f"{combat.player.name} uses PW: Kill! Insta-kills enemy for {actual_dmg} damage!", actual_dmg, True

PW_KILL = Ability(
    id="pw_kill",
    name="PW: Kill",
    description="Insta-kill the enemy for debugging.",
    ability_type=AbilityType.ACTIVE,
    rarity=AbilityRarity.STANDARD,
    execute_hook=execute_pw_kill
)

# Standard Pool Abilities
# ---------------------------------------------------------

def execute_shield_bash(combat: CombatSystem) -> tuple[str, int, bool]:
    dmg = int(combat.player.effective_stats.attack * 0.8)
    actual_dmg = combat.enemy.take_damage(dmg)
    combat.enemy_gauge = max(0, combat.enemy_gauge - 35)
    return f"{combat.player.name} uses Shield Bash! Deals {actual_dmg} damage and reduces enemy gauge by 35.", actual_dmg, False

def execute_rallying_cry(combat: CombatSystem) -> tuple[str, int, bool]:
    heal_amount = int(combat.player.max_hp * 0.15)
    actual_heal = combat.player.heal(heal_amount)
    combat.player.combat_def_buff += 4
    return f"{combat.player.name} uses Rallying Cry! Restores {actual_heal} HP and gains +4 DEF for battle.", 0, False

def execute_cleave(combat: CombatSystem) -> tuple[str, int, bool]:
    dmg = int(combat.player.effective_stats.attack * 1.6)
    actual_dmg = combat.enemy.take_damage(dmg)
    return f"{combat.player.name} uses Cleave! Deals a heavy {actual_dmg} damage.", actual_dmg, False

def modify_iron_skin(stats: Stats) -> Stats:
    from src.entities.actor import Stats
    bonus_def = int(stats.defense * 0.15)
    return stats.add(Stats(max_hp=0, attack=0, defense=bonus_def, speed=0, crit_chance=0.0))

def hook_iron_skin(actor: Actor, raw_damage: int) -> int:
    return max(1, raw_damage - 2)

def modify_veterans_instincts(stats: Stats) -> Stats:
    from src.entities.actor import Stats
    return stats.add(Stats(max_hp=0, attack=0, defense=0, speed=0, crit_chance=0.05))

def hook_bloodlust(actor: Actor, target: Actor, damage: int, is_crit: bool) -> None:
    if damage > 0:
        heal_amt = int(damage * 0.2)
        actor.heal(heal_amt)

# ---------------------------------------------------------
# Epic Pool Abilities
# ---------------------------------------------------------

def hook_colossus_stance_dmg(actor: Actor, raw_damage: int) -> int:
    if actor.current_hp < actor.max_hp * 0.35:
        return max(1, int(raw_damage * 0.5))
    return raw_damage

def execute_blade_storm(combat: CombatSystem) -> tuple[str, int, bool]:
    total_dmg = 0
    import random
    rng = random.Random()
    crit_chance = combat.player.effective_stats.crit_chance + 0.2
    any_crit = False
    for _ in range(4):
        dmg = int(combat.player.effective_stats.attack * 0.6)
        is_crit = rng.random() < crit_chance
        if is_crit:
            dmg = int(dmg * 1.5)
            any_crit = True
        total_dmg += combat.enemy.take_damage(dmg)
    return f"{combat.player.name} uses Blade Storm! Deals {total_dmg} total damage across 4 strikes.", total_dmg, any_crit

def hook_undying_will(actor: Actor, raw_damage: int) -> int:
    return raw_damage # Handled in take_damage directly after defense mitigation

def execute_executioners_might(combat: CombatSystem) -> tuple[str, int, bool]:
    mult = 2.5
    if combat.enemy.current_hp < combat.enemy.max_hp * 0.4:
        mult = 5.0
    dmg = int(combat.player.effective_stats.attack * mult)
    actual_dmg = combat.enemy.take_damage(dmg)
    return f"{combat.player.name} uses Executioner's Might! Deals {actual_dmg} damage.", actual_dmg, False


STANDARD_ABILITIES = [
    CROSS_CUT,
    Ability(id="shield_bash", name="Shield Bash", description="Deals 80% ATK, reduces enemy Action Gauge by 35", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, execute_hook=execute_shield_bash),
    Ability(id="rallying_cry", name="Rallying Cry", description="Restores 15% Max HP, +4 DEF for battle", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, execute_hook=execute_rallying_cry),
    Ability(id="cleave", name="Cleave", description="Heavy attack dealing 160% ATK", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, execute_hook=execute_cleave),
    Ability(id="iron_skin", name="Iron Skin", description="+15% DEF, flat -2 damage taken", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, modify_stats_hook=modify_iron_skin, on_damage_taken_hook=hook_iron_skin),
    Ability(id="veterans_instincts", name="Veteran's Instincts", description="+5% CRIT; crits grant +20 Action Gauge", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, modify_stats_hook=modify_veterans_instincts),
    Ability(id="bloodlust", name="Bloodlust", description="Heal for 20% of physical damage dealt", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, on_attack_dealt_hook=hook_bloodlust)
]

EPIC_ABILITIES = [
    Ability(id="colossus_stance", name="Colossus Stance", description="When HP < 35%, reduce damage by 50% and +30% ATK", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.EPIC, on_damage_taken_hook=hook_colossus_stance_dmg), # Stats buff requires dynamic application
    Ability(id="blade_storm", name="Blade Storm", description="4 strikes at 60% ATK with +20% bonus crit chance", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.EPIC, execute_hook=execute_blade_storm),
    Ability(id="undying_will", name="Undying Will", description="Survive lethal blow once per combat at 40% HP", ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.EPIC, on_damage_taken_hook=hook_undying_will),
    Ability(id="executioners_might", name="Executioner's Might", description="250% ATK damage; doubles if enemy < 40% HP", ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.EPIC, execute_hook=execute_executioners_might)
]

def get_random_abilities(rarity: AbilityRarity, count: int = 2) -> list[Ability]:
    import random
    pool = STANDARD_ABILITIES if rarity == AbilityRarity.STANDARD else EPIC_ABILITIES
    return random.sample(pool, min(count, len(pool)))
