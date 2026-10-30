from __future__ import annotations

import random
from typing import TYPE_CHECKING

from src.entities.actor import Actor, Stats
from src.data.classes import CLASS_REGISTRY
from src.systems.abilities import Ability, AbilityType, AbilityRarity

if TYPE_CHECKING:
    from src.systems.combat import CombatSystem


# =============================================================================
# 1. STARTER ACTIVE ABILITIES (1 Per Class + Debug)
# =============================================================================
# --- Common Starter: Mend Wound
def execute_mend_wound (combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    heal = combat.player.effective_stats.max_hp * 0.10
    combat.player.heal(int(heal))
    return t("log_mend_wound", player=combat.player.name, heal=heal), heal, False

MEND_WOUND = Ability(
    id="mend_wound",
    name="Mend Wound",
    description="Heals for 10% max HP",
    ability_type=AbilityType.ACTIVE,
    rarity=AbilityRarity.STANDARD,
    execute_hook=execute_mend_wound,
    on_attack_dealt_hook=None,
    cooldown=1,
)
# --- Warrior Starter: Cross Cut ---
def execute_cross_cut(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    from src.systems.status import get_status_by_id
    attack = combat.player.effective_stats.attack
    raw_dmg1, crit1 = combat.player.calculate_attack(combat.rng)
    raw_dmg2, crit2 = combat.player.calculate_attack(combat.rng)
    dmg1 = int(raw_dmg1 * 0.90)
    dmg2 = int(raw_dmg2 * 0.90)
    total_dmg = combat.damage_enemy(dmg1) + combat.damage_enemy(dmg2)
    any_crit = crit1 or crit2
    if combat.enemy.current_hp > 0:
        can_stack = any(a.id == "thousand_cuts" for a in combat.player.all_passives)

        bleed = get_status_by_id("bleed", duration=5, potency=max(1, int(attack * 0.20)),
                                  max_stacks=3 if can_stack else 1)
        if bleed:
            combat.enemy.apply_status(bleed)
    combat.enemy_gauge = max(0, combat.enemy_gauge - 30)
    return t("log_cross_cut", player=combat.player.name, dmg1=dmg1, dmg2=dmg2), total_dmg, any_crit


CROSS_CUT = Ability(
    id="cross_cut",
    name="Cross Cut",
    description="Strikes 2 times at 90% ATK each.",
    ability_type=AbilityType.ACTIVE,
    rarity=AbilityRarity.STANDARD,
    required_class="warrior",
    execute_hook=execute_cross_cut,
    on_attack_dealt_hook=None,
    cooldown=1,
)


# --- Rogue Starter: Shadow Strike ---
def execute_shadow_strike(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import i18n, t
    rng = combat.rng
    crit_chance = combat.player.effective_stats.crit_chance + 0.15
    is_crit = rng.random() < crit_chance
    dmg = combat.player.effective_stats.attack * 115 // 100
    if is_crit:
        dmg = int(dmg * 1.5)
        combat.player_gauge = min(100, combat.player_gauge + 15)
    actual_dmg = combat.damage_enemy(dmg)
    crit_msg = (" (¡EMBOSCADA CRÍTICA!)" if i18n.locale == "es" else " (CRITICAL AMBUSH!)") if is_crit else ""
    return t("log_shadow_strike", player=combat.player.name, dmg=actual_dmg, crit=crit_msg), actual_dmg, is_crit


SHADOW_STRIKE = Ability(
    id="shadow_strike",
    name="Shadow Strike",
    description="Deals 115% ATK (+15% Crit). Crits refund 15 gauge.",
    ability_type=AbilityType.ACTIVE,
    rarity=AbilityRarity.STANDARD,
    required_class="rogue",
    execute_hook=execute_shadow_strike,
    cooldown=1,
)


# --- Mage Starter: Arcane Bolt ---
def execute_arcane_bolt(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import i18n, t
    rng = combat.rng
    is_crit = rng.random() < combat.player.effective_stats.crit_chance
    raw_dmg = int(combat.player.effective_stats.attack * 1.10)
    if is_crit:
        raw_dmg = int(raw_dmg * 1.5)
    actual_dmg = combat.damage_enemy(raw_dmg, defense_penetration=0.20)
    crit_msg = (" (¡ARCANA DESATADA!)" if i18n.locale == "es" else " (SURGING ARCANA!)") if is_crit else ""
    return t("log_arcane_bolt", player=combat.player.name, dmg=actual_dmg, crit=crit_msg), actual_dmg, is_crit


ARCANE_BOLT = Ability(
    id="arcane_bolt",
    name="Arcane Bolt",
    description="Piercing bolt dealing 110% ATK (ignores 20% DEF).",
    ability_type=AbilityType.ACTIVE,
    rarity=AbilityRarity.STANDARD,
    required_class="mage",
    execute_hook=execute_arcane_bolt,
    cooldown=1,
)


# --- Debug Tool ---
def execute_pw_kill(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    actual_dmg = combat.damage_enemy(999999)
    return t("log_pw_kill", player=combat.player.name, dmg=actual_dmg), actual_dmg, True


PW_KILL = Ability(
    id="pw_kill",
    name="PW: Kill",
    description="Insta-kill enemy for testing.",
    ability_type=AbilityType.ACTIVE,
    rarity=AbilityRarity.STANDARD,
    execute_hook=execute_pw_kill,
    cooldown=0,
)


# =============================================================================
# 2. WARRIOR STANDARD SKILLS (3 Actives, 3 Passives)
# =============================================================================

def execute_shield_bash(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    dmg = int(combat.player.effective_stats.attack * 0.85)
    actual_dmg = combat.damage_enemy(dmg)
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
    actual_dmg = combat.damage_enemy(dmg)
    return t("log_cleave", player=combat.player.name, dmg=actual_dmg), actual_dmg, False


def modify_iron_skin(stats: Stats) -> Stats:
    bonus_def = int(stats.defense * 0.15)
    return stats.add(type(stats)(max_hp=0, attack=0, defense=bonus_def, speed=0, crit_chance=0.0))


def hook_iron_skin(actor: Actor, raw_damage: int) -> int:
    """Reduce incoming damage by 10%, retaining a minimum of 1 damage."""
    return max(1, int(raw_damage * 0.90))


def modify_veterans_instincts(stats: Stats) -> Stats:
    return stats.add(type(stats)(max_hp=0, attack=0, defense=0, speed=0, crit_chance=0.05))


def hook_bloodlust(actor: Actor, target: Actor, damage: int, is_crit: bool) -> None:
    if damage > 0:
        actor.heal(int(damage * 0.20))


def execute_shieldbreaker_strike(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    stats = combat.player.effective_stats
    raw_damage = int(stats.attack + stats.defense * 0.50)
    actual_damage = combat.damage_enemy(raw_damage)
    return t("log_shieldbreaker_strike", player=combat.player.name, dmg=actual_damage), actual_damage, False


def hook_paladin_guard(actor: Actor, raw_damage: int) -> int:
    affinities = getattr(actor, "_last_ability_affinities", ())
    if "paladin" in affinities:
        return max(1, int(raw_damage * 0.90))
    return raw_damage


def execute_reckless_assault(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    raw_damage = int(combat.player.effective_stats.attack * 1.50)
    actual_damage = combat.damage_enemy(raw_damage, defense_penetration=0.25)
    combat.player._reckless_assault_vulnerable = True
    return t("log_reckless_assault", player=combat.player.name, dmg=actual_damage), actual_damage, False


def modify_blood_frenzy(actor: Actor, stats: Stats) -> Stats:
    """Gain 5% ATK per 10% of max HP missing, up to 40%."""
    max_hp = max(1, stats.max_hp)
    missing_ratio = max(0.0, min(1.0, (max_hp - actor.current_hp) / max_hp))
    bonus_ratio = min(0.40, int(missing_ratio * 10) * 0.05)
    bonus_attack = int(stats.attack * bonus_ratio)
    return stats.add(type(stats)(max_hp=0, attack=bonus_attack, defense=0, speed=0, crit_chance=0.0))


def hook_toxic_blood(actor: Actor, raw_damage: int) -> int:
    """Take 10% less damage while the current enemy is poisoned."""
    combat = getattr(actor, "combat_ref", None)
    if combat and combat.enemy.has_status("poison"):
        return max(1, int(raw_damage * 0.90))
    return raw_damage


# =============================================================================
# 3. ROGUE STANDARD SKILLS (3 Actives, 3 Passives)
# =============================================================================

def execute_poison_shiv(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    from src.systems.status import get_status_by_id
    attack = combat.player.effective_stats.attack
    actual_dmg = combat.damage_enemy(int(attack * 1.05))
    if combat.enemy.current_hp > 0:
        can_stack = any(a.id == "venomous_accumulation" for a in combat.player.all_passives)
        poison = get_status_by_id("poison", duration=5, potency=max(1, int(attack * 0.10)),
                                  max_stacks=3 if can_stack else 1)
        if poison:
            combat.enemy.apply_status(poison)
    combat.enemy_gauge = max(0, combat.enemy_gauge - 30)
    return t("log_poison_shiv", player=combat.player.name, dmg=actual_dmg), actual_dmg, False


def execute_venomous_extraction(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    poison = next((status for status in combat.enemy.statuses if status.id == "poison"), None)
    stacks = poison.stacks if poison else 0
    attack = combat.player.effective_stats.attack
    actual = combat.damage_enemy(int(attack * (0.60 + 0.30 * stacks)))
    if poison:
        combat.enemy.remove_status("poison")
    return t("log_venomous_extraction", player=combat.player.name, dmg=actual, stacks=stacks), actual, False


def execute_dirty_tricks(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    from src.systems.status import get_status_by_id
    actual = combat.damage_enemy(int(combat.player.effective_stats.attack * 0.70))
    blinded = False
    if combat.enemy.is_alive:
        vulnerable = get_status_by_id("vulnerable", duration=10)
        if vulnerable:
            combat.enemy.apply_status(vulnerable)
        if combat.rng.random() < 0.40:
            blind = get_status_by_id("blind", duration=1)
            if blind:
                combat.enemy.apply_status(blind)
                blinded = True
    return t("log_dirty_tricks", player=combat.player.name, dmg=actual,
             blind=t("log_dirty_tricks_blind_suffix") if blinded else t("log_empty_suffix")), actual, False


def execute_hilt_strike(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    from src.systems.status import get_status_by_id
    actual = combat.damage_enemy(int(combat.player.effective_stats.attack * 0.80))
    stunned = False
    if combat.enemy.is_alive and combat.rng.random() < 0.40:
        stun = get_status_by_id("stun", duration=1)
        if stun:
            combat.enemy.apply_status(stun)
            stunned = True
    return t("log_hilt_strike", player=combat.player.name, dmg=actual,
             stunned=t("log_hilt_strike_stun_suffix") if stunned else t("log_empty_suffix")), actual, False


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
        total_dmg += combat.damage_enemy(dmg)
    return t("log_flurry_of_daggers", player=combat.player.name, dmg=total_dmg), total_dmg, any_crit


def modify_nimble_reflexes(stats: Stats) -> Stats:
    added_defense = stats.defense * 0.05
    added_speed = stats.speed * 0.10
    return stats.add(type(stats)(max_hp=0, attack=0, defense=added_defense, speed=added_speed, crit_chance=0.05))


def hook_exposed_weakness(actor: Actor, target: Actor, damage: int, is_crit: bool) -> None:
    """A critical hit empowers the player's next damaging strike by 25%."""
    if is_crit and damage > 0 and hasattr(actor, "base_stats"):
        setattr(actor, "_next_strike_bonus", True)


def modify_whirlwind_defense(stats: Stats) -> Stats:
    added = stats.defense * 0.10
    return stats.add(type(stats)(max_hp=0, attack=0, defense=added, speed=0, crit_chance=0.0))


def hook_whirlwind_defense(actor: Actor, target: Actor, damage: int, is_crit: bool) -> None:
    if is_crit and damage > 0:
        actor.activate_stance("whirlwind_defense")


# =============================================================================
# 4. MAGE STANDARD SKILLS
# =============================================================================

def execute_fireball(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    raw_dmg = int(combat.player.effective_stats.attack * 1.85)
    actual_dmg = combat.damage_enemy(raw_dmg)
    return t("log_fireball", player=combat.player.name, dmg=actual_dmg), actual_dmg, False


def execute_chain_lightning(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import i18n, t
    rng = combat.rng
    is_crit = rng.random() < combat.player.effective_stats.crit_chance
    mult = 1.95 if is_crit else 1.30
    dmg = int(combat.player.effective_stats.attack * mult)
    actual_dmg = combat.damage_enemy(dmg)
    if is_crit:
        combat.player_gauge = min(100, combat.player_gauge + 40)
    crit_msg = (" (¡SOBRECARGA!)" if i18n.locale == "es" else " (OVERCHARGED SURGE!)") if is_crit else ""
    return t("log_chain_lightning", player=combat.player.name, dmg=actual_dmg, crit=crit_msg), actual_dmg, is_crit


def execute_creeping_hands(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    from src.systems.status import get_status_by_id

    attack = combat.player.effective_stats.attack
    actual_damage = combat.damage_enemy(int(attack * 0.70))
    if combat.enemy.is_alive:
        vulnerable = get_status_by_id("vulnerable", duration=10, potency=15)
        if vulnerable:
            combat.enemy.apply_status(vulnerable)
    return t("log_creeping_hands", player=combat.player.name, dmg=actual_damage), actual_damage, False


def execute_soul_siphon(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t

    is_burning = combat.enemy.has_status("burn")
    raw_damage = int(combat.player.effective_stats.attack * 1.00)
    actual_damage = combat.damage_enemy(raw_damage)
    healing_ratio = 0.50 if is_burning else 0.30
    healed = combat.player.heal(int(actual_damage * healing_ratio))
    return t("log_soul_siphon", player=combat.player.name, dmg=actual_damage, heal=healed), actual_damage, False


def hook_bone_barrier(actor: Actor, raw_damage: int) -> int:
    """Reduce incoming damage by 20%."""
    return max(1, int(raw_damage * 0.80))


def hook_soulfire(actor: Actor, target: Actor, damage: int, is_crit: bool) -> None:
    """Basic attacks have a 30% chance to add one stack of Burn."""
    from src.systems.status import get_status_by_id
    combat = getattr(actor, "combat_ref", None)
    if damage > 0 and combat and target.current_hp > 0 and combat.rng.random() < 0.30:
        burn = get_status_by_id("burn", duration=8, potency=1)
        if burn:
            target.apply_status(burn)


def hook_ice_shards(actor: Actor, raw_damage: int) -> int:
    """Reduce incoming damage by 10%; direct-hit reflection is handled by combat."""
    return max(1, int(raw_damage * 0.90))


def modify_arcane_reservoir(actor: Actor, stats: Stats) -> Stats:
    combat = getattr(actor, "combat_ref", None)
    charges = min(3, getattr(combat, "arcane_reservoir_charges", 0))
    if charges <= 0:
        return stats
    return stats.add(type(stats)(
        max_hp=0, attack=stats.attack * 0.05 * charges, defense=0, speed=0, crit_chance=0.0
    ))


def hook_arcane_reservoir(actor: Actor, target: Actor, damage: int, is_crit: bool) -> None:
    """Build one charge per damaging Archmage cast, then discharge at three."""
    combat = getattr(actor, "combat_ref", None)
    if (
        damage <= 0
        or combat is None
        or getattr(combat, "_current_player_action_is_basic", True)
        or "archmage" not in getattr(actor, "_last_ability_affinities", ())
    ):
        return

    if not target.is_alive:
        combat.arcane_reservoir_charges = 0
        return

    combat.arcane_reservoir_charges = min(3, combat.arcane_reservoir_charges + 1)
    if combat.arcane_reservoir_charges < 3:
        from src.core.i18n import t
        combat.log_attack_proc(
            t("combat_arcane_reservoir_charge", actor=actor.name,
              charges=combat.arcane_reservoir_charges,
              attack_bonus=combat.arcane_reservoir_charges * 5)
        )
        return

    # Capture ATK with all three +5% charges before consuming them.
    attack = actor.effective_stats.attack
    raw_damage = int(attack * 1.10)
    critical = combat.rng.random() < actor.effective_stats.crit_chance
    if critical:
        raw_damage = int(raw_damage * 1.5)
    combat.arcane_reservoir_charges = 0

    actual_damage = combat.damage_enemy(raw_damage)
    from src.core.i18n import t
    log_key = "combat_arcane_reservoir_crit" if critical else "combat_arcane_reservoir_hit"
    combat.log_attack_proc(
        t(log_key, actor=actor.name, target=target.name, damage=actual_damage)
    )
    if actual_damage > 0:
        combat.trigger_player_attack_passives(
            actual_damage,
            critical,
            is_basic_attack=False,
            skip_ids={"arcane_reservoir", "spell_echo"},
        )


def hook_spell_echo(actor: Actor, target: Actor, damage: int, is_crit: bool) -> None:
    """Each damaging Archmage hit has a 20% chance to echo 35% of its raw damage."""
    combat = getattr(actor, "combat_ref", None)
    if (
        damage <= 0
        or not target.is_alive
        or combat is None
        or getattr(combat, "_current_player_action_is_basic", True)
        or "archmage" not in getattr(actor, "_last_ability_affinities", ())
        or combat.rng.random() >= 0.20
    ):
        return

    raw_damage = int(getattr(combat, "_last_player_hit_raw_damage", damage) * 0.35)
    if raw_damage <= 0:
        return
    echoed_damage = combat.damage_enemy(raw_damage)
    if echoed_damage > 0:
        from src.core.i18n import t
        combat.log_attack_proc(
            t("combat_spell_echo", actor=actor.name, target=target.name, damage=echoed_damage)
        )


def execute_arcane_missiles(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t

    total_damage = 0
    landed = 0
    any_crit = False
    combat._passives_handled_per_hit = True
    for _ in range(3):
        if not combat.enemy.is_alive:
            break
        attack = combat.player.effective_stats.attack
        critical = combat.rng.random() < combat.player.effective_stats.crit_chance
        raw_damage = int(attack * 0.70)
        if critical:
            raw_damage = int(raw_damage * 1.5)
        actual_damage = combat.damage_enemy(raw_damage)
        if actual_damage <= 0:
            continue

        landed += 1
        total_damage += actual_damage
        any_crit = any_crit or critical
        combat.trigger_player_attack_passives(
            actual_damage,
            critical,
            is_basic_attack=False,
            skip_ids={"arcane_reservoir"},
        )

    if total_damage > 0:
        # Reservoir advances once for the spell cast, not once per missile.
        combat.trigger_player_attack_passives(
            total_damage,
            any_crit,
            is_basic_attack=False,
            only_ids={"arcane_reservoir"},
        )
    return t("log_arcane_missiles", player=combat.player.name, hits=landed, dmg=total_damage), total_damage, any_crit


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
        total_dmg += combat.damage_enemy(dmg)
    return t("log_blade_storm", player=combat.player.name, dmg=total_dmg), total_dmg, any_crit


def hook_undying_will(actor: Actor, raw_damage: int) -> int:
    return raw_damage


def execute_executioners_might(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    mult = 5.0 if combat.enemy.current_hp < combat.enemy.max_hp * 0.40 else 2.5
    dmg = int(combat.player.effective_stats.attack * mult)
    actual_dmg = combat.damage_enemy(dmg)
    return t("log_executioners_might", player=combat.player.name, dmg=actual_dmg), actual_dmg, False


# --- Rogue Epics ---
def execute_assassinate(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import i18n, t
    rng = combat.rng
    crit_chance = combat.player.effective_stats.crit_chance + 0.35
    is_crit = rng.random() < crit_chance
    mult = 3.80 if is_crit else 2.00
    dmg = int(combat.player.effective_stats.attack * mult)
    actual_dmg = combat.damage_enemy(dmg)
    crit_str = (" (¡EJECUCIÓN LETAL!)" if i18n.locale == "es" else " (LETHAL EXECUTION!)") if is_crit else ""
    return t("log_assassinate", player=combat.player.name, dmg=actual_dmg, crit=crit_str), actual_dmg, is_crit


def execute_fan_of_knives(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    total_dmg = 0
    delays = 0
    rng = combat.rng
    for _ in range(5):
        dmg = int(combat.player.effective_stats.attack * 0.50)
        total_dmg += combat.damage_enemy(dmg)
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
    actual_dmg = combat.damage_enemy(raw_dmg)
    combat.enemy_gauge = 0
    return t("log_meteor", player=combat.player.name, dmg=actual_dmg), actual_dmg, True


def execute_time_stop(combat: CombatSystem) -> tuple[str, int, bool]:
    from src.core.i18n import t
    combat.player_gauge = 100
    combat.enemy_gauge = 0
    return t("log_time_stop", player=combat.player.name), 0, False


def modify_time_dilation(stats: Stats) -> Stats:
    return stats.add(type(stats)(max_hp=0, attack=stats.attack*0.25, defense=0, speed=stats.speed*0.30, crit_chance=0.25))


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
    MEND_WOUND,
    CROSS_CUT,
    SHADOW_STRIKE,
    ARCANE_BOLT,

    # Warrior Standard
    Ability(id="shield_bash", name="Shield Bash", description="Deals 85% ATK, delays enemy gauge by 35.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="warrior",
            execute_hook=execute_shield_bash,cooldown=3, affinities=("paladin",)),
    Ability(id="rallying_cry", name="Rallying Cry", description="Restores 15% Max HP, +4 DEF for battle.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="warrior",
            execute_hook=execute_rallying_cry,cooldown=2, affinities=("paladin",)),
    Ability(id="cleave", name="Cleave", description="Heavy cleave dealing 160% ATK damage.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="warrior",
            execute_hook=execute_cleave,cooldown=3, affinities=("berserker",)),
    Ability(id="iron_skin", name="Iron Skin", description="+15% DEF, -10% damage taken.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="warrior",
            modify_stats_hook=modify_iron_skin, on_damage_taken_hook=hook_iron_skin,),
    Ability(id="veterans_instincts", name="Veteran's Instincts", description="+5% CRIT; crits refund +20 Action Gauge.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="warrior",
            modify_stats_hook=modify_veterans_instincts,),
    Ability(id="bloodlust", name="Bloodlust", description="Heal for 20% of physical damage dealt.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="warrior",
            on_attack_dealt_hook=hook_bloodlust,),
    Ability(id="shieldbreaker_strike", name="Shieldbreaker Strike",
            description="Deals damage equal to 100% ATK plus 50% DEF.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="warrior",
            execute_hook=execute_shieldbreaker_strike, cooldown=3, affinities=("paladin",)),
    Ability(id="defensive_superiority", name="Defensive Superiority",
            description="Gain DEF-based armor penetration, up to 75%, when your DEF exceeds the enemy's.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="warrior",
            affinities=("paladin",)),
    Ability(id="paladin_guard", name="Paladin Guard",
            description="Take 10% less damage while your last active ability had Paladin affinity.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="warrior",
            on_damage_taken_hook=hook_paladin_guard, affinities=("paladin",)),
    Ability(id="reckless_assault", name="Reckless Assault",
            description="Deals 150% ATK, ignores 25% DEF, but you take 10% more damage until your next action.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="warrior",
            execute_hook=execute_reckless_assault, cooldown=3, affinities=("berserker",)),
    Ability(id="blood_frenzy", name="Blood Frenzy",
            description="Gain 5% ATK per 10% of Max HP missing, up to +40% ATK.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="warrior",
            modify_actor_stats_hook=modify_blood_frenzy, affinities=("berserker",)),
    Ability(id="cull_the_weak", name="Cull the Weak",
            description="Deal 30% more damage to enemies below 30% Max HP.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="warrior",
            affinities=("berserker",)),

    # Rogue Standard
    Ability(id="poison_shiv", name="Poison Shiv", description="Deals 105% ATK, applies 5 ticks of poison, and drains 30 enemy gauge.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="rogue",
            execute_hook=execute_poison_shiv, cooldown=3, affinities=("venomancer",)),
    Ability(id="dirty_tricks", name="Dirty Tricks",
            description="Deals 70% ATK, applies Vulnerable for 10 ticks, and has a 40% chance to Blind for 1 tick.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="rogue",
            execute_hook=execute_dirty_tricks, cooldown=4),
    Ability(id="flurry_of_daggers", name="Flurry of Daggers",
            description="3 strikes at 55% ATK (+15% Crit chance each).", ability_type=AbilityType.ACTIVE,
            rarity=AbilityRarity.STANDARD, required_class="rogue",
            execute_hook=execute_flurry_of_daggers, cooldown=3, affinities=("duelist",)),
    Ability(id="nimble_reflexes", name="Nimble Reflexes", description="+10% Speed, +5% Crit Chance, +5% Defense.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="rogue",
            modify_stats_hook=modify_nimble_reflexes, affinities=("duelist",)),
    Ability(id="exposed_weakness", name="Exposed Weakness",
            description="Critical hits empower your next damaging strike by 25%.", ability_type=AbilityType.PASSIVE,
            rarity=AbilityRarity.STANDARD, required_class="rogue",
            on_attack_dealt_hook=hook_exposed_weakness, affinities=("duelist",)),
    Ability(id="shadow_step", name="Shadow Step", description="When you lose HP, gain 15 player action gauge.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="rogue"),

    Ability(id="venomous_accumulation", name="Venomous Accumulation",
            description="Poison applications stack up to 3 times and refresh its 5-tick duration.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="rogue",
            affinities=("venomancer",)),
    Ability(id="toxic_blood", name="Toxic Blood",
            description="Take 10% less damage while your enemy is poisoned.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="rogue",
            on_damage_taken_hook=hook_toxic_blood, affinities=("venomancer",)),
    Ability(id="venomous_extraction", name="Venomous Extraction",
            description="Deals 60% ATK plus 30% ATK per Poison stack, then consumes Poison. 4-turn cooldown.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="rogue",
            execute_hook=execute_venomous_extraction, cooldown=4, affinities=("venomancer",)),
    Ability(id="riposte", name="Riposte",
            description="25% chance to block an attack. A block prepares a 50% ATK counter on the next damage taken.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="rogue",
            affinities=("duelist",), is_stance=True),
    Ability(id="whirlwind_defense", name="Whirlwind Defense",
            description="+10% DEF. A critical hit prepares a stance: the next basic attack adds a 25% ATK strike that can crit.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="rogue",
            modify_stats_hook=modify_whirlwind_defense, on_attack_dealt_hook=hook_whirlwind_defense,
            affinities=("duelist",), is_stance=True),
    Ability(id="hilt_strike", name="Hilt Strike",
            description="Deals 80% ATK and has a 40% chance to stun for 1 turn. 4-turn cooldown.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="rogue",
            execute_hook=execute_hilt_strike, cooldown=4, affinities=("duelist",)),

    # Mage Standard
    Ability(id="fireball", name="Fireball", description="High-impact blast dealing 185% ATK fire damage.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="mage",
            execute_hook=execute_fireball, cooldown=2, affinities=("archmage",)),
    Ability(id="chain_lightning", name="Chain Lightning", description="Deals 130% ATK. Crits refund 40 player gauge.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="mage",
            execute_hook=execute_chain_lightning, cooldown=3, affinities=("archmage",)),
    Ability(id="creeping_hands", name="Creeping Hands",
            description="Deals 70% ATK and makes the enemy take 15% more damage for 10 ticks. 4-turn cooldown.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="mage",
            execute_hook=execute_creeping_hands, cooldown=4, affinities=("warlock",)),
    Ability(id="soulfire", name="Soulfire", description="Basic attacks have a 30% chance to add a Burn stack.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="mage",
            on_attack_dealt_hook=hook_soulfire, affinities=("warlock",)),
    Ability(id="bone_barrier", name="Bone Barrier", description="Reduces incoming damage by 20%.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="mage",
            on_damage_taken_hook=hook_bone_barrier, affinities=("warlock",)),
    Ability(id="summon_imp", name="Summon Imp",
            description="Basic attacks gain a separate 50% ATK imp strike with an independent critical chance and a 50% chance to Burn.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="mage",
            affinities=("warlock",)),
    Ability(id="soul_siphon", name="Soul Siphon",
            description="Deals 100% ATK and heals for 30% of damage dealt, or 50% if the target is Burning. 4-turn cooldown.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="mage",
            execute_hook=execute_soul_siphon, cooldown=4, affinities=("warlock",)),
    Ability(id="pact_of_pain", name="Pact of Pain",
            description="Warlock active abilities cost 5% of Max HP per cast and deal 10% more damage. The cost cannot reduce you below 1 HP.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="mage",
            affinities=("warlock",)),
    Ability(id="ice_shards", name="Ice Shards",
            description="Reduces incoming damage by 10% and reflects 10% of direct damage taken.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="mage",
            on_damage_taken_hook=hook_ice_shards, affinities=("archmage",)),
    Ability(id="arcane_missiles", name="Arcane Missiles",
            description="Fires 3 missiles at 70% ATK each; each can critically hit. 4-turn cooldown.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.STANDARD, required_class="mage",
            execute_hook=execute_arcane_missiles, cooldown=4, affinities=("archmage",)),
    Ability(id="arcane_reservoir", name="Arcane Reservoir",
            description="Damaging Archmage abilities grant 1 charge. Each charge adds 5% ATK; at 3, consume them to strike for 110% of boosted ATK, which can critically hit.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="mage",
            modify_actor_stats_hook=modify_arcane_reservoir,
            on_attack_dealt_hook=hook_arcane_reservoir, affinities=("archmage",)),
    Ability(id="spell_echo", name="Spell Echo",
            description="Each damaging Archmage hit has a 20% chance to echo 35% of its damage. Echoes cannot critically hit or trigger passives.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.STANDARD, required_class="mage",
            on_attack_dealt_hook=hook_spell_echo, affinities=("archmage",)),
]

EPIC_ABILITIES: list[Ability] = [
    # Warrior Epic
    Ability(id="colossus_stance", name="Colossus Stance",
            description="When HP < 35%, incoming damage halved & +30% ATK.", ability_type=AbilityType.PASSIVE,
            rarity=AbilityRarity.EPIC, required_class="warrior", on_damage_taken_hook=hook_colossus_stance_dmg,),
    Ability(id="blade_storm", name="Blade Storm", description="4 rapid slashes at 60% ATK with +20% bonus Crit.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.EPIC, required_class="warrior",
            execute_hook=execute_blade_storm,cooldown=4,),
    Ability(id="undying_will", name="Undying Will", description="Survive lethal blow once per combat at 40% HP.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.EPIC, required_class="warrior",
            on_damage_taken_hook=hook_undying_will,),
    Ability(id="executioners_might", name="Executioner's Might",
            description="250% ATK damage; doubles if enemy < 40% HP.", ability_type=AbilityType.ACTIVE,
            rarity=AbilityRarity.EPIC, required_class="warrior", execute_hook=execute_executioners_might,cooldown=6,),

    # Rogue Epic
    Ability(id="assassinate", name="Assassinate", description="200% ATK strike (+35% Crit). Crits deal 380% ATK.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.EPIC, required_class="rogue",
            execute_hook=execute_assassinate,cooldown=5,),
    Ability(id="fan_of_knives", name="Fan of Knives", description="5 blades deal 50% ATK each with turn-stall chances.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.EPIC, required_class="rogue",
            execute_hook=execute_fan_of_knives,cooldown=4,),
    Ability(id="shadow_dance", name="Shadow Dance",
            description="Grants a permanent 30% chance to completely evade any hit.", ability_type=AbilityType.PASSIVE,
            rarity=AbilityRarity.EPIC, required_class="rogue", on_damage_taken_hook=hook_shadow_dance_defense,),
    Ability(id="death_dealer", name="Death Dealer", description="+15% Crit Chance, +5 ATK, +4 SPD.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.EPIC, required_class="rogue",
            modify_stats_hook=modify_death_dealer,),

    # Mage Epic
    Ability(id="meteor", name="Meteor", description="Calls down a meteor for 320% ATK; resets enemy turn to 0.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.EPIC, required_class="mage",
            execute_hook=execute_meteor,cooldown=6,),
    Ability(id="time_stop", name="Time Stop",
            description="Freezes time: resets enemy to 0 gauge and grants instant turn.",
            ability_type=AbilityType.ACTIVE, rarity=AbilityRarity.EPIC, required_class="mage",
            execute_hook=execute_time_stop,cooldown=6,),
    Ability(id="time_dilation", name="Time Dilation", description="+25% ATK, +30% Speed, +25% Crit Chance.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.EPIC, required_class="mage",
            modify_stats_hook=modify_time_dilation),
    Ability(id="phoenix_rebirth", name="Phoenix Rebirth", description="Once per combat, lethal blow heals to 50% HP.",
            ability_type=AbilityType.PASSIVE, rarity=AbilityRarity.EPIC, required_class="mage",
            on_damage_taken_hook=hook_phoenix_rebirth),
]

SIGNATURE_ABILITIES: list[Ability] = [
    Ability("paladin_oath", "Consecrated Strikes",
            "Basic attacks add a crit-capable 50% ATK strike that heals for half its damage.",
            AbilityType.PASSIVE, AbilityRarity.EPIC),
    Ability("berserker_rage", "Deathless Onslaught",
            "Once per combat below 30% HP, gain a bonus action. Your next damaging action deals double damage and heals for half, up to 25% max HP.",
            AbilityType.PASSIVE, AbilityRarity.EPIC),
    Ability("venomancer_mastery", "Perfect Toxin",
            "Every fourth Poison tick detonates for an additional 200% of that tick's damage, ignoring defense.",
            AbilityType.PASSIVE, AbilityRarity.EPIC),
    Ability("duelist_precision", "Flowing Steel",
            "Consuming a stance empowers your next basic attack with two crit-capable 50% ATK hits.",
            AbilityType.PASSIVE, AbilityRarity.EPIC),
    Ability("archmage_focus", "Arcane Momentum",
            "Archmage and hybrid active skills gain 10% damage per cast, stacking up to 50% for the combat.",
            AbilityType.PASSIVE, AbilityRarity.EPIC),
    Ability("warlock_pact", "Daemonic Pact",
            "Taking damage burns the enemy once per enemy action. The first two ticks of each Burn stack heal half their damage.",
            AbilityType.PASSIVE, AbilityRarity.EPIC),
]


# Complete Catalog. Signature passives are retrievable but excluded from random ability pools.
ABILITY_REGISTRY: dict[str, Ability] = {
    ab.id: ab for ab in (STANDARD_ABILITIES + EPIC_ABILITIES + SIGNATURE_ABILITIES + [PW_KILL])
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
    parent_class = next(
        (class_id for class_id, class_def in CLASS_REGISTRY.items()
         if player_class in class_def.promotions),
        None,
    )

    available = [
        ab for ab in pool
        if ab.id not in known_abilities
           and (ab.required_class is None or player_class is None
                or ab.required_class == player_class or player_class in ab.affinities
                or (rarity == AbilityRarity.EPIC and ab.required_class == parent_class))
    ]

    return random.sample(available, min(count, len(available)))
