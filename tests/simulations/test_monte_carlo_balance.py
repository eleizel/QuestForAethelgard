"""Opt-in Monte Carlo balance run across playable classes and route modes.

Run from the project root with PowerShell:

    $env:RUN_BALANCE_SIMULATION = "1"
    $env:AETHELGARD_MC_TRIALS = "100"
    pytest -s tests/simulations/test_monte_carlo_balance.py

The simulation uses the real map, enemy, combat, level, reward, and loot systems.
Its automated policy picks the safest available biome in PATHFINDER mode, chooses
map nodes using a survivability/reward heuristic, takes generated gear upgrades,
uses healing items/skills when hurt, and selects randomly from ability drafts.
During combat it uses the ready damaging ability with the highest expected damage
per cooldown cycle; permanent stat elixirs are consumed as soon as they are found.
The developer-only `pw_kill` ability is excluded from balance runs.
Events choose the option with the strongest estimated player-state value; shops
buy/equip useful upgrades, stat elixirs, and healing supplies when affordable.
Opt-in runs print route/trial progress; set AETHELGARD_MC_VERBOSE=1 for each fight.
FATE and PATHFINDER receive the same trial seed for each class. Biome selection
uses a separate seeded stream so FATE's random biome draw does not shift the
shared economy/event random stream before the first encounter.
"""

from __future__ import annotations

import os
import random
import statistics
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PLAYABLE_CLASSES = ("warrior", "rogue", "mage")
ROUTE_MODES = ("FATE", "PATHFINDER")
DEFAULT_TRIALS = 30
MAX_COMBAT_TICKS = 5_000
ACT_COMPLETION_TARGETS = {1: (0.80, 0.80), 2: (0.50, 0.60), 3: (0.20, 0.30)}


def _biome_threat_score(biome_id: str, act: int) -> float:
    """Estimate route danger from generated, act-scaled enemies and their abilities."""
    from src.data.biomes import BIOME_REGISTRY
    from src.entities.enemy import EnemyTier, generate_enemy

    class FixedArchetypeRng:
        def __init__(self, archetype_id: str) -> None:
            self.archetype_id = archetype_id

        def choice(self, options: tuple[str, ...]) -> str:
            return self.archetype_id if self.archetype_id in options else options[0]

        def randint(self, minimum: int, _maximum: int) -> int:
            return minimum

    biome = BIOME_REGISTRY[biome_id]
    representative_floor = {1: 6, 2: 18, 3: 33}[act]
    weighted_threat = 0.0
    total_weight = 0
    # Approximate the map's encounter mix, with extra weight for the boss
    # because a wrong route estimate can decide the act-ending fight.
    encounter_groups = (
        (EnemyTier.COMMON, biome.basic_enemies, 5),
        (EnemyTier.ELITE, biome.elites, 2),
        (EnemyTier.BOSS, biome.bosses, 3),
    )

    for tier, archetype_ids, encounter_weight in encounter_groups:
        tier_scores = []
        for archetype_id in archetype_ids:
            enemy = generate_enemy(
                tier=tier,
                floor=representative_floor,
                biome_id=biome_id,
                rng=FixedArchetypeRng(archetype_id),
            )
            stats = enemy.effective_stats
            score = (
                enemy.max_hp
                + 3 * stats.attack
                + 2 * stats.defense
                + 1.5 * stats.speed
                + 30 * stats.crit_chance
            )
            if enemy.on_hit_status:
                score += 20 * enemy.status_chance
            for skill in enemy.skills:
                if skill.kind == "attack":
                    score += (
                        3
                        * stats.attack
                        * max(0.0, skill.damage_multiplier - 1.0)
                        / max(1, skill.cooldown)
                    )
                elif skill.kind == "heal":
                    score += enemy.max_hp * skill.heal_fraction / max(1, skill.cooldown)
            tier_scores.append(score)

        weighted_threat += statistics.mean(tier_scores) * encounter_weight
        total_weight += encounter_weight

    return weighted_threat / total_weight


def _choose_pathfinder_biome(act: int) -> str:
    from src.data.biomes import ACT_BIOMES

    return min(ACT_BIOMES[act], key=lambda biome_id: _biome_threat_score(biome_id, act))


def _is_biome_choice(options: Any, biome_choice_sets: set[tuple[str, ...]]) -> bool:
    """Recognize biome ID choices without hashing arbitrary loot objects."""
    option_tuple = tuple(options)
    return all(isinstance(option, str) for option in option_tuple) and option_tuple in biome_choice_sets


def test_biome_rng_filter_ignores_unhashable_loot_items() -> None:
    biome_choices = {("arboretum", "crypt")}

    assert _is_biome_choice(["arboretum", "crypt"], biome_choices)
    assert not _is_biome_choice([["healing potion"]], biome_choices)


def _choose_map_node(available: list[Any], state: Any, rng: random.Random) -> Any:
    """Prefer healing when needed, then useful rewards and manageable fights."""
    from src.systems.map_gen import NodeType

    hp_ratio = state.player.current_hp / max(1, state.player.max_hp)
    base_scores = {
        NodeType.REST: 1.0 + 3.0 * (1.0 - hp_ratio),
        NodeType.TREASURE: 1.6,
        NodeType.COMBAT: 1.4,
        NodeType.EVENT: 0.8,
        NodeType.SHOP: 0.6,
        NodeType.ELITE: 2.0 if hp_ratio >= 0.75 else 0.2,
        NodeType.BOSS: 10.0,
    }
    return max(available, key=lambda node: base_scores[node.node_type] + rng.random() * 0.05)


def _gear_score(item: Any) -> float:
    bonus = item.stats_bonus
    return (
        0.15 * bonus.max_hp
        + bonus.attack
        + 1.2 * bonus.defense
        + 0.5 * bonus.speed
        + 50 * bonus.crit_chance
    )


def _player_policy_score(player: Any) -> float:
    """Estimate a player's combat value and useful resources for event choices."""
    from src.data.items import StatPotion
    from src.entities.item import ConsumableItem, EquipmentItem

    stats = player.effective_stats
    score = (
        stats.attack * 1.5
        + stats.defense * 1.2
        + stats.speed * 1.5
        + stats.max_hp * 0.25
        + player.current_hp * 0.45
        + stats.crit_chance * 100
        + player.gold * 0.03
        + len(player.pending_ability_choices) * 18
    )
    for item in player.inventory.pouch:
        if isinstance(item, EquipmentItem):
            current = player.inventory.equipment.get(item.slot)
            score += max(0.0, _gear_score(item) - (_gear_score(current) if current else 0.0)) * 0.25
        elif isinstance(item, StatPotion):
            bonus = item.stat_bonus
            score += (
                bonus.attack * 1.5
                + bonus.defense * 1.2
                + bonus.speed * 1.5
                + bonus.max_hp * 0.25
                + bonus.crit_chance * 100
            )
        elif isinstance(item, ConsumableItem):
            score += 6 + min(item.heal_amount, max(0, player.max_hp - player.current_hp)) * 0.1
            if item.cleanses_debuffs and player.statuses:
                score += 3
    for status in player.statuses:
        if getattr(status, "id", "") in {"poison", "burn", "bleed"}:
            score -= status.potency * status.duration * 0.5
    return score


def _resolve_simulated_event(state: Any) -> str | None:
    """Choose the available event option with the best simulated player outcome."""
    event = state.current_event
    if event is None:
        return None
    choices = [choice for choice in event.choices if choice.is_available(state)]
    if not choices:
        return None

    from_state = random.getstate()
    scored_choices: list[tuple[float, int, Any]] = []
    for index, choice in enumerate(choices):
        random.setstate(from_state)
        trial_player = deepcopy(state.player)
        choice.action_hook(SimpleNamespace(player=trial_player))
        score = _player_policy_score(trial_player)
        scored_choices.append((score, -index, choice))
    random.setstate(from_state)

    _score, _order, selected = max(scored_choices, key=lambda row: (row[0], row[1]))
    event.resolved_text = selected.action_hook(state)
    return event.id


def _equip_pouch_upgrades(state: Any) -> int:
    """Equip newly acquired pouch gear when it improves that slot."""
    from src.entities.item import EquipmentItem

    inventory = state.player.inventory
    equipped = 0
    for index in range(len(inventory.pouch) - 1, -1, -1):
        item = inventory.pouch[index]
        if not isinstance(item, EquipmentItem):
            continue
        if item.required_class is not None and item.required_class != state.player.class_id:
            continue
        current = inventory.equipment.get(item.slot)
        if current is not None and _gear_score(item) <= _gear_score(current):
            continue
        can_equip, _reason = inventory.can_equip(item, state.player)
        if not can_equip:
            continue
        inventory.remove_from_pouch(index)
        old_item = inventory.equip(item)
        if old_item is not None:
            inventory.add_to_pouch(old_item)
        equipped += 1
    return equipped


def _shop_item_utility(player: Any, item: Any, price: int) -> float:
    from src.data.items import StatPotion
    from src.entities.item import ConsumableItem, EquipmentItem

    if isinstance(item, EquipmentItem):
        current = player.inventory.equipment.get(item.slot)
        gain = _gear_score(item) - (_gear_score(current) if current else 0.0)
        return gain - price * 0.03
    if isinstance(item, StatPotion):
        bonus = item.stat_bonus
        gain = (
            bonus.attack * 1.5
            + bonus.defense * 1.2
            + bonus.speed * 1.5
            + bonus.max_hp * 0.25
            + bonus.crit_chance * 100
        )
        gain += min(item.heal_amount, max(0, player.max_hp - player.current_hp)) * 0.2
        return gain - price * 0.03
    if isinstance(item, ConsumableItem) and item.heal_amount > 0:
        has_healing = any(belt_item and belt_item.heal_amount > 0 for belt_item in player.inventory.belt)
        has_healing = has_healing or any(
            getattr(pouch_item, "heal_amount", 0) > 0 for pouch_item in player.inventory.pouch
        )
        if not has_healing:
            return item.heal_amount * 0.2 - price * 0.04
    return float("-inf")


def _purchase_simulated_shop_items(state: Any) -> tuple[int, int, list[str]]:
    """Buy affordable upgrades and reserve healing, applying them as a player can."""
    from src.data.items import StatPotion
    from src.entities.item import ConsumableItem, EquipmentItem
    from src.systems.inventory import MAX_POUCH_SLOTS

    inventory = state.player.inventory
    bought = 0
    gold_spent = 0
    stat_potions_used: list[str] = []
    stock = state.merchant_stock
    while stock and len(inventory.pouch) < MAX_POUCH_SLOTS:
        candidates = [
            (_shop_item_utility(state.player, item, price), index, item, price)
            for index, (item, price) in enumerate(stock)
            if price <= state.player.gold
        ]
        if not candidates:
            break
        utility, index, item, price = max(candidates, key=lambda row: (row[0], -row[1]))
        if utility <= 0:
            break

        state.player.gold -= price
        gold_spent += price
        bought += 1
        stock.pop(index)
        if isinstance(item, EquipmentItem):
            old_item = inventory.equip(item)
            if old_item is not None:
                inventory.add_to_pouch(old_item)
        elif isinstance(item, StatPotion):
            if item.use(state.player):
                stat_potions_used.append(item.id)
        elif isinstance(item, ConsumableItem) and item.heal_amount > 0:
            empty_slot = next((i for i, belt_item in enumerate(inventory.belt) if belt_item is None), None)
            if empty_slot is not None:
                inventory.belt[empty_slot] = item
            else:
                inventory.add_to_pouch(item)
    state.merchant_stock = []
    return bought, gold_spent, stat_potions_used


def _collect_loot_and_ability_drafts(
    state: Any, rng: random.Random
) -> tuple[int, int, int, list[str], list[str], list[str]]:
    from src.data.abilities import get_random_abilities
    from src.data.items import StatPotion
    from src.entities.item import ConsumableItem, EquipmentItem
    from src.systems.abilities import AbilityRarity

    inventory = state.player.inventory
    loot_count = len(state.pending_loot)
    equipment_upgrades = 0
    equipment_selected: list[str] = []
    stat_potions_used: list[str] = []
    for item in state.pending_loot:
        if isinstance(item, EquipmentItem):
            current = inventory.equipment[item.slot]
            if current is None or _gear_score(item) > _gear_score(current):
                previous = inventory.equip(item)
                equipment_upgrades += 1
                equipment_selected.append(item.id)
                if previous is not None and len(inventory.pouch) < 10:
                    inventory.pouch.append(previous)
        elif isinstance(item, StatPotion):
            if item.use(state.player):
                stat_potions_used.append(item.id)
        elif isinstance(item, ConsumableItem):
            if not inventory.add_to_pouch(item):
                continue
            if item.heal_amount > 0 and inventory.belt[0] is None:
                inventory.belt[0] = item
                inventory.pouch.remove(item)
    state.pending_loot.clear()

    # Model the level-10 promotion and its separate ability reward in each run.
    if state.player.promotion_due:
        promotions = state.player.available_promotions()
        affinity_scores = {
            class_id: sum(ability.affinities.count(class_id) for ability in
                          (*state.player.abilities.active, *state.player.abilities.passive))
            for class_id in promotions
        }
        promoted_class = max(promotions, key=lambda class_id: (affinity_scores[class_id], -promotions.index(class_id)))
        state.player.promote(promoted_class)

    ability_drafts = 0
    abilities_selected: list[str] = []
    while state.player.pending_ability_choices:
        choice = state.player.pending_ability_choices.pop(0)
        rarity = AbilityRarity.EPIC if choice == "EPIC" else AbilityRarity.STANDARD
        known = [ability.id for ability in (*state.player.abilities.active, *state.player.all_passives)]
        draft = get_random_abilities(
            rarity=rarity,
            known_abilities=known,
            player_class=state.player.class_id,
            count=2,
        )
        if not draft:
            continue
        ability_drafts += 1
        selected = rng.choice(draft)
        abilities_selected.append(selected.id)
        target = (
            state.player.abilities.active
            if selected.ability_type.name == "ACTIVE"
            else state.player.abilities.passive
        )
        if len(target) < 2:
            state.player.abilities.add_ability(selected)
        else:
            state.player.abilities.replace_ability(selected, 1)

    return (
        loot_count,
        equipment_upgrades,
        ability_drafts,
        equipment_selected,
        abilities_selected,
        stat_potions_used,
    )


def _increment(groups: tuple[dict[str, Any], ...], key: str, amount: float = 1) -> None:
    for group in groups:
        group[key] = group.get(key, 0) + amount


def _record_stat_potions(groups: tuple[dict[str, Any], ...], item_ids: list[str]) -> None:
    for group in groups:
        group["stat_potions_used"] = group.get("stat_potions_used", 0) + len(item_ids)
        used_by_id = group.setdefault("stat_potion_ids_used", {})
        for item_id in item_ids:
            used_by_id[item_id] = used_by_id.get(item_id, 0) + 1


def _record_max(groups: tuple[dict[str, Any], ...], key: str, value: float) -> None:
    for group in groups:
        group[key] = max(group.get(key, 0), value)


def _new_act_record() -> dict[str, Any]:
    return {
        "nodes": {},
        "floors_visited": [],
        "combat_tiers": {},
        "damage_dealt": 0,
        "damage_taken": 0,
        "largest_hit_dealt": 0,
        "largest_hit_taken": 0,
        "largest_status_tick_dealt": 0,
        "largest_status_tick_taken": 0,
        "status_damage_dealt": 0,
        "status_damage_taken": 0,
        "hp_restored_in_combat": 0,
        "hp_restored_on_level_up": 0,
        "rest_healing": 0,
        "act_transition_healing": 0,
        "xp_awarded": 0,
        "gold_awarded": 0,
        "player_actions": 0,
        "enemy_actions": 0,
        "combat_ticks": 0,
        "player_actions_skipped_by_stun": 0,
        "enemy_actions_skipped_by_stun": 0,
        "potions_used": 0,
        "stat_potions_used": 0,
        "stat_potion_ids_used": {},
        "potion_hp_restored": 0,
        "events_resolved": 0,
        "shop_items_bought": 0,
        "shop_gold_spent": 0,
        "ability_uses": {},
    }


def _instrument_combat(combat: Any, run: dict[str, Any], act: dict[str, Any], encounter: dict[str, Any]) -> None:
    """Measure damage/action deltas around the real combat action hooks."""
    original_player_action = combat._execute_player_attack
    original_enemy_action = combat._execute_enemy_attack
    original_status_ticks = combat._process_status_ticks
    original_rewards = combat._distribute_rewards
    original_enemy_take_damage = combat.enemy.take_damage
    tracking_player_strike = False

    def tracked_enemy_take_damage(raw_damage: int, defense_penetration: float = 0.0) -> int:
        nonlocal tracking_player_strike
        damage = original_enemy_take_damage(raw_damage, defense_penetration)
        if tracking_player_strike and damage > 0:
            encounter["player_damage_hits"] += 1
            if not combat.enemy.is_alive:
                encounter["player_direct_kill"] = True
        return damage

    def player_action() -> None:
        nonlocal tracking_player_strike
        ability = combat.queued_ability
        was_stunned = combat.player.has_status("stun")
        player_hp_before = combat.player.current_hp
        enemy_hp_before = combat.enemy.current_hp
        tracking_player_strike = True
        try:
            original_player_action()
        finally:
            tracking_player_strike = False
        _increment(
            (run, act, encounter),
            "player_actions" if not was_stunned else "player_actions_skipped_by_stun",
        )
        _increment(
            (run, act, encounter),
            "damage_dealt",
            max(0, enemy_hp_before - combat.enemy.current_hp),
        )
        _record_max(
            (run, act, encounter),
            "largest_hit_dealt",
            max(0, enemy_hp_before - combat.enemy.current_hp),
        )
        _increment(
            (run, act, encounter),
            "hp_restored_in_combat",
            max(0, combat.player.current_hp - player_hp_before),
        )
        if ability is not None and combat.queued_ability is None:
            ability_id = ability.id
            run["ability_uses"][ability_id] = run["ability_uses"].get(ability_id, 0) + 1
            act["ability_uses"][ability_id] = act["ability_uses"].get(ability_id, 0) + 1
            encounter["ability_uses"][ability_id] = encounter["ability_uses"].get(ability_id, 0) + 1
            for group in (run, act, encounter):
                result = group.setdefault("ability_effectiveness", {}).setdefault(
                    ability_id, {"uses": 0, "damage": 0, "hp_restored": 0}
                )
                result["uses"] += 1
                result["damage"] += max(0, enemy_hp_before - combat.enemy.current_hp)
                result["hp_restored"] += max(0, combat.player.current_hp - player_hp_before)

    def enemy_action() -> None:
        was_stunned = combat.enemy.has_status("stun")
        player_hp_before = combat.player.current_hp
        original_enemy_action()
        _increment(
            (run, act, encounter),
            "enemy_actions" if not was_stunned else "enemy_actions_skipped_by_stun",
        )
        _increment(
            (run, act, encounter),
            "damage_taken",
            max(0, player_hp_before - combat.player.current_hp),
        )
        _increment(
            (run, act, encounter),
            "hp_restored_in_combat",
            max(0, combat.player.current_hp - player_hp_before),
        )
        _record_max(
            (run, act, encounter),
            "largest_hit_taken",
            max(0, player_hp_before - combat.player.current_hp),
        )

    def status_ticks(actor: Any) -> None:
        hp_before = actor.current_hp
        player_hp_before = combat.player.current_hp
        original_status_ticks(actor)
        hp_lost = max(0, hp_before - actor.current_hp)
        if actor is combat.player:
            _increment((run, act, encounter), "status_damage_taken", hp_lost)
            _record_max((run, act, encounter), "largest_status_tick_taken", hp_lost)
        elif actor is combat.enemy:
            _increment((run, act, encounter), "status_damage_dealt", hp_lost)
            _record_max((run, act, encounter), "largest_status_tick_dealt", hp_lost)
        _increment(
            (run, act, encounter),
            "hp_restored_in_combat",
            max(0, combat.player.current_hp - player_hp_before),
        )

    def distribute_rewards() -> None:
        hp_before = combat.player.current_hp
        original_rewards()
        _increment(
            (run, act, encounter),
            "hp_restored_on_level_up",
            max(0, combat.player.current_hp - hp_before),
        )

    combat._execute_player_attack = player_action
    combat._execute_enemy_attack = enemy_action
    combat._process_status_ticks = status_ticks
    combat._distribute_rewards = distribute_rewards
    combat.enemy.take_damage = tracked_enemy_take_damage


def test_combat_instrumentation_counts_real_damage_hits() -> None:
    class DummyActor:
        def __init__(self, hp: int) -> None:
            self.current_hp = hp

        @property
        def is_alive(self) -> bool:
            return self.current_hp > 0

        def has_status(self, _status_id: str) -> bool:
            return False

        def take_damage(self, raw_damage: int, _defense_penetration: float = 0.0) -> int:
            damage = min(self.current_hp, raw_damage)
            self.current_hp -= damage
            return damage

    class DummyCombat:
        def __init__(self) -> None:
            self.player = DummyActor(100)
            self.enemy = DummyActor(10)
            self.queued_ability = None

        def _execute_player_attack(self) -> None:
            self.enemy.take_damage(6)
            self.enemy.take_damage(4)

        def _execute_enemy_attack(self) -> None:
            return None

        def _process_status_ticks(self, _actor: Any) -> None:
            return None

        def _distribute_rewards(self) -> None:
            return None

    combat = DummyCombat()
    encounter = {
        "player_actions": 0,
        "player_actions_skipped_by_stun": 0,
        "damage_dealt": 0,
        "largest_hit_dealt": 0,
        "hp_restored_in_combat": 0,
        "player_damage_hits": 0,
        "player_direct_kill": False,
        "ability_uses": {},
    }
    _instrument_combat(combat, {}, {}, encounter)

    combat._execute_player_attack()

    assert encounter["player_damage_hits"] == 2
    assert encounter["player_direct_kill"] is True


def _expected_ability_damage(combat: Any, ability: Any, samples: int = 5) -> float:
    """Estimate direct damage on isolated copies using repeatable RNG samples."""
    damage_samples: list[int] = []
    seed_base = sum((index + 1) * ord(char) for index, char in enumerate(ability.id))
    for sample in range(max(1, samples)):
        player = deepcopy(combat.player)
        enemy = deepcopy(combat.enemy)
        # Combat instrumentation wraps this method per encounter; restore the
        # class implementation on the copy so a forecast cannot affect metrics.
        take_damage_impl = getattr(type(enemy), "take_damage", None)
        if take_damage_impl is not None:
            enemy.take_damage = take_damage_impl.__get__(enemy, type(enemy))
        affinities = tuple(getattr(ability, "affinities", ()))
        if hasattr(player, "_active_stances") and hasattr(player, "abilities"):
            from src.systems.combat import CombatSystem

            # Real entities use full combat rules, isolated from the live run.
            scratch = CombatSystem(
                player=player,
                enemy=enemy,
                seed=seed_base + sample * 104729,
            )
            scratch._current_action_affinities = affinities
            scratch._current_player_action_is_basic = False
            scratch._pact_of_pain_active = (
                "warlock" in affinities
                and any(passive.id == "pact_of_pain" for passive in player.all_passives)
            )
            # Forecast an Archmage cast with the stack it grants before dealing damage.
            if (
                ability.id != "pw_kill"
                and "archmage" in affinities
                and any(passive.id == "archmage_focus" for passive in player.all_passives)
            ):
                scratch.arcane_momentum_stacks = min(
                    5, getattr(combat, "arcane_momentum_stacks", 0) + 1
                )
        else:
            # Lightweight policy tests use small stand-ins rather than entities.
            scratch = SimpleNamespace(
                player=player,
                enemy=enemy,
                rng=random.Random(seed_base + sample * 104729),
            )
            scratch.damage_enemy = lambda raw_damage, defense_penetration=0.0: enemy.take_damage(
                raw_damage, defense_penetration=defense_penetration
            )

        scratch.player_gauge = getattr(combat, "player_gauge", 0)
        scratch.enemy_gauge = getattr(combat, "enemy_gauge", 0)
        if hasattr(player, "_last_ability_affinities"):
            player._last_ability_affinities = affinities
        _log, damage, _crit = ability.execute(scratch)
        damage_samples.append(max(0, int(damage)))
    return statistics.mean(damage_samples)


def _ability_damage_per_action(combat: Any, ability: Any) -> float:
    # Cooldowns decrement on each player action; after using cooldown N, the
    # skill is available again after N further actions, so the cycle is N+1.
    def stat_key(actor: Any) -> tuple[Any, ...]:
        stats = actor.effective_stats
        return (stats.max_hp, stats.attack, stats.defense, stats.speed, stats.crit_chance)

    status_key = tuple(
        sorted(
            (status.id, status.potency)
            for actor in (combat.player, combat.enemy)
            for status in actor.statuses
        )
    )
    cache_key = (
        ability.id,
        stat_key(combat.player),
        stat_key(combat.enemy),
        status_key,
        int(4 * combat.enemy.current_hp / max(1, combat.enemy.max_hp)),
        combat.enemy.current_hp < combat.enemy.max_hp * 0.40,
        tuple(sorted(passive.id for passive in getattr(combat.player, "all_passives", ()))),
        getattr(combat, "arcane_momentum_stacks", 0),
    )
    cache = getattr(combat, "_mc_ability_damage_cache", None)
    if cache is None:
        cache = {}
        combat._mc_ability_damage_cache = cache
    if cache_key not in cache:
        cache[cache_key] = _expected_ability_damage(combat, ability)
    return cache[cache_key] / (max(0, ability.cooldown) + 1)


def _queue_ability_if_ready(combat: Any, rng: random.Random) -> None:
    if combat.queued_ability is not None:
        return
    projected_player_gauge = combat.player_gauge + combat.player.effective_stats.speed
    if projected_player_gauge < 100:
        return

    ready = [
        ability
        for ability in combat.player.abilities.active
        if ability.id != "pw_kill"
        and (ability.required_class is None or ability.required_class == combat.player.class_id)
        and combat.is_ability_ready(ability)
    ]
    if not ready:
        return

    hp_ratio = combat.player.current_hp / max(1, combat.player.max_hp)
    healing = [ability for ability in ready if ability.id == "rallying_cry"]
    if healing and hp_ratio <= 0.70:
        combat.queued_ability = healing[0]
        return

    offensive_or_control = [ability for ability in ready if ability.id != "rallying_cry"]
    if offensive_or_control:
        ranked = [
            (_ability_damage_per_action(combat, ability), ability.id, ability)
            for ability in offensive_or_control
        ]
        # Stable ID tie-break keeps the policy reproducible across runs.
        best_damage, _ability_id, best_ability = max(ranked, key=lambda row: (row[0], row[1]))
        if best_damage > 0:
            combat.queued_ability = best_ability
        else:
            combat.queued_ability = min(offensive_or_control, key=lambda ability: ability.id)


def test_combat_bot_prefers_highest_damage_per_cooldown_cycle() -> None:
    class DummyEnemy:
        def __init__(self) -> None:
            self.current_hp = 100
            self.max_hp = 100
            self.statuses: list[Any] = []
            self.effective_stats = SimpleNamespace(
                max_hp=100, attack=10, defense=0, speed=10, crit_chance=0.0
            )

        def take_damage(self, damage: int, defense_penetration: float = 0.0) -> int:
            return damage

    def skill(skill_id: str, damage: int, cooldown: int) -> Any:
        return SimpleNamespace(
            id=skill_id,
            cooldown=cooldown,
            required_class="warrior",
            execute=lambda _combat: ("", damage, False),
        )

    slower_burst = skill("slower_burst", 40, 3)  # 10 expected damage/action
    faster_damage = skill("faster_damage", 30, 1)  # 15 expected damage/action
    player = SimpleNamespace(
        class_id="warrior",
        current_hp=100,
        max_hp=100,
        effective_stats=SimpleNamespace(
            max_hp=100, attack=10, defense=0, speed=100, crit_chance=0.0
        ),
        statuses=[],
        abilities=SimpleNamespace(active=[slower_burst, faster_damage]),
    )
    combat = SimpleNamespace(
        queued_ability=None,
        player_gauge=0,
        enemy_gauge=0,
        player=player,
        enemy=DummyEnemy(),
        is_ability_ready=lambda _ability: True,
    )

    _queue_ability_if_ready(combat, random.Random(1))

    assert combat.queued_ability is faster_damage


def _simulate_trial(class_id: str, route_mode: str, seed: int, monkeypatch: Any) -> dict[str, Any]:
    import pyxel
    import src.core.game_state as game_state_module
    from src.core.game_state import GameMode, GameState
    from src.entities.enemy import generate_enemy as original_generate_enemy
    from src.systems.combat import CombatSystem as OriginalCombatSystem
    from src.systems.map_gen import generate_spire_map as original_generate_spire_map
    from src.data.biomes import ACT_BIOMES

    random_state = random.getstate()
    random.seed(seed)
    rng = random.Random(seed)
    metrics: dict[str, Any] = {
        "seed": seed,
        "victory": False,
        "acts_cleared": 0,
        "fights": 0,
        "bosses_killed": 0,
        "timeout": False,
        "encounters": [],
        "acts": {},
        "ability_uses": {},
        "ability_effectiveness": {},
        "abilities_selected": {},
        "signature_procs": {},
        "equipment_selected": {},
        "nodes": {},
        "loot_items": 0,
        "equipment_upgrades": 0,
        "ability_drafts": 0,
        "potions_used": 0,
        "stat_potions_used": 0,
        "stat_potion_ids_used": {},
        "potion_hp_restored": 0,
        "gold_from_nodes": 0,
        "events_resolved": 0,
        "shop_items_bought": 0,
        "shop_gold_spent": 0,
        "event_choices": {},
        "death": None,
        "damage_dealt": 0,
        "damage_taken": 0,
        "status_damage_dealt": 0,
        "status_damage_taken": 0,
        "hp_restored_in_combat": 0,
        "hp_restored_on_level_up": 0,
        "largest_hit_dealt": 0,
        "largest_hit_taken": 0,
        "largest_status_tick_dealt": 0,
        "largest_status_tick_taken": 0,
        "rest_healing": 0,
        "act_transition_healing": 0,
        "xp_awarded": 0,
        "gold_awarded": 0,
        "player_actions": 0,
        "enemy_actions": 0,
        "combat_ticks": 0,
        "player_actions_skipped_by_stun": 0,
        "enemy_actions_skipped_by_stun": 0,
    }

    try:
        monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)
        with monkeypatch.context() as patcher:
            original_random_choice = random.choice
            biome_choice_sets = {tuple(options) for options in ACT_BIOMES.values()}
            biome_rng = random.Random(seed ^ 0xB10B1E)

            def isolated_biome_choice(options: Any) -> Any:
                option_tuple = tuple(options)
                # Loot pools contain unhashable item dataclasses; only biome IDs
                # are string tuples and should use the isolated biome RNG.
                if _is_biome_choice(option_tuple, biome_choice_sets):
                    return biome_rng.choice(option_tuple)
                return original_random_choice(options)

            def seeded_map(*args: Any, **kwargs: Any) -> Any:
                kwargs["seed"] = rng.randrange(0, 2**32)
                return original_generate_spire_map(*args, **kwargs)

            def seeded_enemy(*args: Any, **kwargs: Any) -> Any:
                kwargs["rng"] = rng
                return original_generate_enemy(*args, **kwargs)

            def seeded_combat(player: Any, enemy: Any) -> Any:
                return OriginalCombatSystem(player, enemy, seed=rng.randrange(0, 2**32))

            patcher.setattr(game_state_module, "generate_spire_map", seeded_map)
            patcher.setattr(game_state_module, "generate_enemy", seeded_enemy)
            patcher.setattr(game_state_module, "CombatSystem", seeded_combat)
            patcher.setattr(game_state_module.random, "choice", isolated_biome_choice)

            state = GameState()
            state.start_new_game(class_id=class_id, route_mode=route_mode)
            # This is a developer kill command in the shipped catalog, not a balance skill.
            state.player.abilities.active[:] = [
                ability for ability in state.player.abilities.active if ability.id != "pw_kill"
            ]
            if route_mode == "PATHFINDER":
                state.advance_act(target_biome_id=_choose_pathfinder_biome(1))

            while state.act <= 3 and state.player.is_alive:
                act_record = metrics["acts"].setdefault(str(state.act), _new_act_record())
                while state.map_graph and state.map_graph.available_nodes:
                    node = _choose_map_node(state.map_graph.available_nodes, state, rng)
                    node_type = node.node_type.name
                    metrics["nodes"][node_type] = metrics["nodes"].get(node_type, 0) + 1
                    act_record["nodes"][node_type] = act_record["nodes"].get(node_type, 0) + 1
                    if node.floor + 1 not in act_record["floors_visited"]:
                        act_record["floors_visited"].append(node.floor + 1)
                    gold_before_node = state.player.gold
                    hp_before_node = state.player.current_hp
                    state.select_map_node(node.id)
                    if node.node_type.name == "REST":
                        healed = max(0, state.player.current_hp - hp_before_node)
                        _increment((metrics, act_record), "rest_healing", healed)
                    if node.node_type.name == "TREASURE":
                        _increment(
                            (metrics, act_record),
                            "gold_from_nodes",
                            state.player.gold - gold_before_node,
                        )

                    if state.current_mode == GameMode.EVENTS and state.current_event is not None:
                        event_id = _resolve_simulated_event(state)
                        if event_id is not None:
                            _increment((metrics, act_record), "events_resolved")
                            metrics["event_choices"][event_id] = metrics["event_choices"].get(event_id, 0) + 1
                            (
                                event_loot,
                                event_upgrades,
                                event_drafts,
                                event_equipment,
                                event_abilities,
                                event_stat_potions,
                            ) = _collect_loot_and_ability_drafts(state, rng)
                            _record_stat_potions((metrics, act_record), event_stat_potions)
                            _increment((metrics, act_record), "loot_items", event_loot)
                            _increment((metrics, act_record), "ability_drafts", event_drafts)
                            for item_id in event_equipment:
                                metrics["equipment_selected"][item_id] = metrics["equipment_selected"].get(item_id, 0) + 1
                            for ability_id in event_abilities:
                                metrics["abilities_selected"][ability_id] = metrics["abilities_selected"].get(ability_id, 0) + 1
                        event_upgrades += _equip_pouch_upgrades(state)
                        _increment((metrics, act_record), "equipment_upgrades", event_upgrades)
                        state.current_event = None
                        state.switch_mode(GameMode.MAP)
                    elif state.current_mode == GameMode.SHOP:
                        bought, gold_spent, shop_stat_potions = _purchase_simulated_shop_items(state)
                        _record_stat_potions((metrics, act_record), shop_stat_potions)
                        _increment((metrics, act_record), "shop_items_bought", bought)
                        _increment((metrics, act_record), "shop_gold_spent", gold_spent)
                        state.switch_mode(GameMode.MAP)

                    if state.combat is None or state.current_mode != GameMode.COMBAT:
                        continue

                    current_node = state.map_graph.current_node
                    metrics["fights"] += 1
                    enemy = state.combat.enemy
                    tier = enemy.tier.name
                    act_record["combat_tiers"][tier] = act_record["combat_tiers"].get(tier, 0) + 1
                    encounter = {
                        "act": state.act,
                        "floor": state.floor,
                        "tier": tier,
                        "enemy_id": enemy.archetype_id,
                        "enemy_name": enemy.name,
                        "enemy_hp": enemy.max_hp,
                        "enemy_attack": enemy.base_stats.attack,
                        "enemy_speed": enemy.base_stats.speed,
                        "player_hp_start": state.player.current_hp,
                        "player_max_hp_start": state.player.max_hp,
                        "player_speed_start": state.player.effective_stats.speed,
                        "won": False,
                        "ticks": 0,
                        "player_actions": 0,
                        "enemy_actions": 0,
                        "player_actions_skipped_by_stun": 0,
                        "enemy_actions_skipped_by_stun": 0,
                        "damage_dealt": 0,
                        "damage_taken": 0,
                        "status_damage_dealt": 0,
                        "status_damage_taken": 0,
                        "hp_restored_in_combat": 0,
                        "largest_hit_dealt": 0,
                        "largest_hit_taken": 0,
                        "largest_status_tick_dealt": 0,
                        "largest_status_tick_taken": 0,
                        "player_damage_hits": 0,
                        "player_direct_kill": False,
                        "ability_uses": {},
                    }
                    metrics["encounters"].append(encounter)
                    _instrument_combat(state.combat, metrics, act_record, encounter)
                    xp_awarded = int(enemy.exp_reward * state.player.exp_multiplier)
                    gold_awarded = enemy.gold_reward
                    level_before_fight = state.player.level

                    while state.combat.is_active() and state.combat.current_tick < MAX_COMBAT_TICKS:
                        if (
                            state.player.current_hp <= state.player.max_hp * 0.40
                            and any(state.player.inventory.belt)
                        ):
                            for belt_index, item in enumerate(state.player.inventory.belt):
                                if item is not None and item.heal_amount > 0:
                                    hp_before_potion = state.player.current_hp
                                    if state.player.inventory.use_belt_item(belt_index, state.player):
                                        _increment((metrics, act_record, encounter), "potions_used")
                                        _increment(
                                            (metrics, act_record, encounter),
                                            "potion_hp_restored",
                                            state.player.current_hp - hp_before_potion,
                                        )
                                    break

                        _queue_ability_if_ready(state.combat, rng)
                        state.update_combat()
                        encounter["ticks"] += 1
                        metrics["combat_ticks"] += 1
                        act_record["combat_ticks"] += 1

                        if state.current_mode == GameMode.GAME_OVER:
                            break

                    if os.getenv("AETHELGARD_MC_VERBOSE") == "1":
                        outcome = (
                            "game_over"
                            if state.current_mode == GameMode.GAME_OVER
                            else "timeout"
                            if state.combat.is_active()
                            else state.combat.result.name.lower()
                        )
                        print(
                            f"[MC]   fight={metrics['fights']} act={state.act} floor={state.floor} "
                            f"enemy={enemy.name} result={outcome} ticks={encounter['ticks']} "
                            f"player_hp={state.player.current_hp}/{state.player.max_hp}",
                            flush=True,
                        )

                    encounter_signature_procs = dict(
                        getattr(state.combat, "signature_proc_counts", {})
                    )
                    encounter["signature_procs"] = encounter_signature_procs
                    for signature_id, proc_count in encounter_signature_procs.items():
                        metrics["signature_procs"][signature_id] = (
                            metrics["signature_procs"].get(signature_id, 0) + proc_count
                        )

                    if state.current_mode == GameMode.GAME_OVER:
                        encounter["won"] = False
                        encounter["player_hp_end"] = state.player.current_hp
                        metrics["death"] = {
                            "act": state.act,
                            "floor": state.floor,
                            "tier": tier,
                            "enemy_id": enemy.archetype_id,
                            "enemy_name": enemy.name,
                            "level": state.player.level,
                            "statuses": [status.id for status in state.player.statuses],
                        }
                        break
                    if state.combat.is_active():
                        metrics["timeout"] = True
                        encounter["won"] = False
                        encounter["player_hp_end"] = state.player.current_hp
                        break

                    if state.combat.result.name != "PLAYER_VICTORY":
                        break

                    encounter["won"] = True
                    encounter["player_hp_end"] = state.player.current_hp
                    encounter["xp_awarded"] = xp_awarded
                    encounter["gold_awarded"] = gold_awarded
                    encounter["levels_gained"] = state.player.level - level_before_fight
                    _increment((metrics, act_record), "xp_awarded", xp_awarded)
                    _increment((metrics, act_record), "gold_awarded", gold_awarded)

                    if current_node and current_node.node_type.name == "BOSS":
                        metrics["bosses_killed"] += 1
                        metrics["acts_cleared"] += 1

                    (
                        loot_count,
                        equipment_upgrades,
                        ability_drafts,
                        equipment_selected,
                        abilities_selected,
                        stat_potions,
                    ) = _collect_loot_and_ability_drafts(state, rng)
                    _record_stat_potions((metrics, act_record), stat_potions)
                    metrics["loot_items"] += loot_count
                    metrics["equipment_upgrades"] += equipment_upgrades
                    metrics["ability_drafts"] += ability_drafts
                    for item_id in equipment_selected:
                        metrics["equipment_selected"][item_id] = metrics["equipment_selected"].get(item_id, 0) + 1
                    for ability_id in abilities_selected:
                        metrics["abilities_selected"][ability_id] = metrics["abilities_selected"].get(ability_id, 0) + 1
                    _increment((act_record,), "loot_items", loot_count)
                    _increment((act_record,), "equipment_upgrades", equipment_upgrades)
                    _increment((act_record,), "ability_drafts", ability_drafts)

                    if current_node and current_node.node_type.name == "BOSS":
                        if state.act == 3:
                            metrics["victory"] = True
                            break
                        hp_before_transition = state.player.current_hp
                        state.act += 1
                        state.floor = 1
                        if route_mode == "PATHFINDER":
                            state.advance_act(target_biome_id=_choose_pathfinder_biome(state.act))
                        else:
                            state.advance_act()
                        transition_healing = max(0, state.player.current_hp - hp_before_transition)
                        _increment((metrics, act_record), "act_transition_healing", transition_healing)
                        break

                    state.switch_mode(GameMode.MAP)

                if metrics["victory"] or metrics["timeout"] or state.current_mode == GameMode.GAME_OVER:
                    break
                if state.map_graph and not state.map_graph.available_nodes:
                    # Reaching this state without the final boss indicates a malformed route graph.
                    break

            metrics.update(
                level=state.player.level,
                hp_ratio=state.player.current_hp / max(1, state.player.max_hp),
                gold=state.player.gold,
                experience=state.player.experience,
                act_reached=state.act,
                final_floor=state.floor,
                signature_id=(
                    state.player.signature_passive.id
                    if state.player.signature_passive is not None
                    else None
                ),
                final_status=(
                    "victory"
                    if metrics["victory"]
                    else "death"
                    if metrics["death"] is not None
                    else "timeout"
                    if metrics["timeout"]
                    else "stalled"
                ),
            )
            return metrics
    finally:
        random.setstate(random_state)


def _wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return (0.0, 0.0)
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * ((proportion * (1 - proportion) / total + z * z / (4 * total * total)) ** 0.5) / denominator
    return (max(0.0, center - margin), min(1.0, center + margin))


def _summarize_act_completion(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize act clears both across all runs and conditional on reaching each act."""
    total = len(rows)
    cleared_counts = {
        act: sum(row["acts_cleared"] >= act for row in rows)
        for act in (1, 2, 3)
    }
    eligible_counts = {
        1: total,
        2: cleared_counts[1],
        3: cleared_counts[2],
    }
    conditional_rates = {
        act: cleared_counts[act] / eligible_counts[act] if eligible_counts[act] else 0.0
        for act in (1, 2, 3)
    }
    conditional_ci = {
        act: _wilson_interval(cleared_counts[act], eligible_counts[act])
        for act in (1, 2, 3)
    }
    return {
        "cleared_counts": cleared_counts,
        "eligible_counts": eligible_counts,
        "conditional_rates": conditional_rates,
        "conditional_ci": conditional_ci,
    }


def test_act_completion_targets_use_reached_act_denominators() -> None:
    rows = [{"acts_cleared": clears} for clears in [0, 0, 1, 1, 1, 1, 2, 2, 2, 3]]
    summary = _summarize_act_completion(rows)

    assert summary["eligible_counts"] == {1: 10, 2: 8, 3: 4}
    assert summary["cleared_counts"] == {1: 8, 2: 4, 3: 1}
    assert summary["conditional_rates"] == {1: 0.8, 2: 0.5, 3: 0.25}


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = round((len(ordered) - 1) * percentile)
    return ordered[index]


def _paired_delta_interval(deltas: list[float]) -> tuple[float, float, float]:
    """Return mean difference and an approximate paired 95% t interval."""
    if not deltas:
        return (0.0, 0.0, 0.0)
    mean_delta = statistics.mean(deltas)
    if len(deltas) < 2:
        return (mean_delta, mean_delta, mean_delta)
    margin = 1.96 * statistics.stdev(deltas) / (len(deltas) ** 0.5)
    return (mean_delta, mean_delta - margin, mean_delta + margin)


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    victory_count = sum(row["victory"] for row in rows)
    act_completion = _summarize_act_completion(rows)
    levels = [float(row["level"]) for row in rows]
    hp_ratios = [float(row["hp_ratio"]) for row in rows]
    return {
        "runs": total,
        "victories": victory_count,
        "victory_rate": victory_count / total,
        "victory_ci": _wilson_interval(victory_count, total),
        "act_clear_counts": act_completion["cleared_counts"],
        "act_clear_rates": {
            act: count / total for act, count in act_completion["cleared_counts"].items()
        },
        "act_clear_ci": {
            act: _wilson_interval(count, total)
            for act, count in act_completion["cleared_counts"].items()
        },
        "act_conditional_eligible_counts": act_completion["eligible_counts"],
        "act_conditional_clear_counts": act_completion["cleared_counts"],
        "act_conditional_clear_rates": act_completion["conditional_rates"],
        "act_conditional_clear_ci": act_completion["conditional_ci"],
        "timeout_rate": sum(row["timeout"] for row in rows) / total,
        "death_rate": sum(row["death"] is not None for row in rows) / total,
        "stalled_rate": sum(row["final_status"] == "stalled" for row in rows) / total,
        "mean_act_reached": statistics.mean(row["act_reached"] for row in rows),
        "mean_level": statistics.mean(levels),
        "level_p10_p50_p90": tuple(_percentile(levels, p) for p in (0.10, 0.50, 0.90)),
        "mean_hp_ratio": statistics.mean(hp_ratios),
        "hp_p10_p50_p90": tuple(_percentile(hp_ratios, p) for p in (0.10, 0.50, 0.90)),
        "mean_fights": statistics.mean(row["fights"] for row in rows),
        "mean_bosses": statistics.mean(row["bosses_killed"] for row in rows),
        "mean_ticks": statistics.mean(row["combat_ticks"] for row in rows),
        "mean_player_damage": statistics.mean(row["damage_dealt"] for row in rows),
        "mean_status_damage_dealt": statistics.mean(row["status_damage_dealt"] for row in rows),
        "mean_damage_taken": statistics.mean(row["damage_taken"] for row in rows),
        "mean_status_damage_taken": statistics.mean(row["status_damage_taken"] for row in rows),
        "mean_total_damage_dealt": statistics.mean(
            row["damage_dealt"] + row["status_damage_dealt"] for row in rows
        ),
        "mean_total_damage_taken": statistics.mean(
            row["damage_taken"] + row["status_damage_taken"] for row in rows
        ),
        "largest_hit_taken_p90": _percentile(
            [float(row["largest_hit_taken"]) for row in rows], 0.90
        ),
        "mean_combat_hp_restored": statistics.mean(row["hp_restored_in_combat"] for row in rows),
        "mean_levelup_hp_restored": statistics.mean(row["hp_restored_on_level_up"] for row in rows),
        "mean_rest_healing": statistics.mean(row["rest_healing"] for row in rows),
        "mean_act_transition_healing": statistics.mean(
            row["act_transition_healing"] for row in rows
        ),
        "mean_potions": statistics.mean(row["potions_used"] for row in rows),
        "mean_stat_potions": statistics.mean(row["stat_potions_used"] for row in rows),
        "mean_potion_hp_restored": statistics.mean(row["potion_hp_restored"] for row in rows),
        "mean_equipment_upgrades": statistics.mean(row["equipment_upgrades"] for row in rows),
        "mean_ability_drafts": statistics.mean(row["ability_drafts"] for row in rows),
        "mean_gold": statistics.mean(row["gold"] for row in rows),
        "mean_gold_awarded": statistics.mean(row["gold_awarded"] for row in rows),
        "mean_gold_from_nodes": statistics.mean(row["gold_from_nodes"] for row in rows),
        "mean_events_resolved": statistics.mean(row["events_resolved"] for row in rows),
        "mean_shop_items_bought": statistics.mean(row["shop_items_bought"] for row in rows),
        "mean_shop_gold_spent": statistics.mean(row["shop_gold_spent"] for row in rows),
        "mean_xp_awarded": statistics.mean(row["xp_awarded"] for row in rows),
        "mean_xp_remainder": statistics.mean(row["experience"] for row in rows),
        "mean_player_actions": statistics.mean(row["player_actions"] for row in rows),
        "mean_enemy_actions": statistics.mean(row["enemy_actions"] for row in rows),
        "mean_player_actions_lost_to_stun": statistics.mean(
            row["player_actions_skipped_by_stun"] for row in rows
        ),
    }


def _print_detailed_tables(
    summaries: list[tuple[str, str, list[dict[str, Any]], dict[str, Any]]],
    paired_rows: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]],
) -> None:
    print("\n=== CAMPAÑA POR CLASE Y RUTA ===")
    print(
        "class,route,runs,victories,victory%,victory_95ci,act1%,act1_95ci,act2%,act2_95ci,"
        "act3%,act3_95ci,death%,timeout%,stalled%,mean_act,level_mean_p10_p50_p90,hp_mean_p10_p50_p90"
    )
    for class_id, route, rows, summary in summaries:
        act_rates = summary["act_clear_rates"]
        act_ci = summary["act_clear_ci"]
        level_dist = "/".join(f"{value:.1f}" for value in summary["level_p10_p50_p90"])
        hp_dist = "/".join(f"{value:.0%}" for value in summary["hp_p10_p50_p90"])
        print(
            f"{class_id},{route},{summary['runs']},{summary['victories']},"
            f"{summary['victory_rate']:.1%},{summary['victory_ci'][0]:.1%}-{summary['victory_ci'][1]:.1%},"
            f"{act_rates[1]:.1%},{act_ci[1][0]:.1%}-{act_ci[1][1]:.1%},"
            f"{act_rates[2]:.1%},{act_ci[2][0]:.1%}-{act_ci[2][1]:.1%},"
            f"{act_rates[3]:.1%},{act_ci[3][0]:.1%}-{act_ci[3][1]:.1%},"
            f"{summary['death_rate']:.1%},{summary['timeout_rate']:.1%},"
            f"{summary['stalled_rate']:.1%},"
            f"{summary['mean_act_reached']:.2f},"
            f"{level_dist},{hp_dist}"
        )

    print("\n=== COMPLETADO CONDICIONAL POR ACTO VS OBJETIVO ===")
    print("class,route,act,runs_reached_act,act_clears,conditional_clear%,clear_95ci,target,gap_pp")
    for class_id, route, _rows, summary in summaries:
        rates = summary["act_conditional_clear_rates"]
        intervals = summary["act_conditional_clear_ci"]
        eligible = summary["act_conditional_eligible_counts"]
        clears = summary["act_conditional_clear_counts"]
        for act in (1, 2, 3):
            target_low, target_high = ACT_COMPLETION_TARGETS[act]
            rate = rates[act]
            gap = (rate - target_low) * 100 if target_low == target_high else (
                (rate - target_low) * 100 if rate < target_low else
                (rate - target_high) * 100 if rate > target_high else 0.0
            )
            target = (
                f"{target_low:.0%}"
                if target_low == target_high
                else f"{target_low:.0%}-{target_high:.0%}"
            )
            ci = intervals[act]
            print(
                f"{class_id},{route},{act},{eligible[act]},{clears[act]},"
                f"{rate:.1%},{ci[0]:.1%}-{ci[1]:.1%},{target},{gap:+.1f}"
            )

    print("\n=== ECONOMÍA, DAÑO Y ACCIONES (MEDIAS POR PARTIDA) ===")
    print(
        "class,route,fights,bosses,ticks,damage_dealt,status_dealt,total_dealt,"
        "damage_taken,status_taken,total_taken,"
        "combat_hp_restored,levelup_hp_restored,potion_hp_restored,rest_healing,"
        "act_transition_healing,potions,stat_elixirs_used,"
        "equipment_upgrades,ability_drafts,events_resolved,shop_items_bought,shop_gold_spent,"
        "xp_awarded,xp_remainder,gold_held,gold_awarded,gold_from_nodes,"
        "player_actions,enemy_actions,stun_skips,max_hit_taken_p90"
    )
    for class_id, route, _rows, summary in summaries:
        print(
            f"{class_id},{route},{summary['mean_fights']:.2f},{summary['mean_bosses']:.2f},"
            f"{summary['mean_ticks']:.1f},{summary['mean_player_damage']:.1f},"
            f"{summary['mean_status_damage_dealt']:.1f},{summary['mean_total_damage_dealt']:.1f},"
            f"{summary['mean_damage_taken']:.1f},{summary['mean_status_damage_taken']:.1f},"
            f"{summary['mean_total_damage_taken']:.1f},"
            f"{summary['mean_combat_hp_restored']:.1f},{summary['mean_levelup_hp_restored']:.1f},"
            f"{summary['mean_potion_hp_restored']:.1f},{summary['mean_rest_healing']:.1f},"
            f"{summary['mean_act_transition_healing']:.1f},"
            f"{summary['mean_potions']:.2f},{summary['mean_stat_potions']:.2f},"
            f"{summary['mean_equipment_upgrades']:.2f},"
            f"{summary['mean_ability_drafts']:.2f},{summary['mean_events_resolved']:.2f},"
            f"{summary['mean_shop_items_bought']:.2f},{summary['mean_shop_gold_spent']:.1f},"
            f"{summary['mean_xp_awarded']:.1f},"
            f"{summary['mean_xp_remainder']:.1f},{summary['mean_gold']:.1f},"
            f"{summary['mean_gold_awarded']:.1f},{summary['mean_gold_from_nodes']:.1f},"
            f"{summary['mean_player_actions']:.1f},"
            f"{summary['mean_enemy_actions']:.1f},{summary['mean_player_actions_lost_to_stun']:.2f},"
            f"{summary['largest_hit_taken_p90']:.1f}"
        )

    print("\n=== RESULTADOS POR ACTO ===")
    print(
        "class,route,act,clear%,clear_95ci,mean_floor,max_floor,nodes_mean_by_type,combat_tiers_mean,"
        "damage_dealt,damage_taken,status_taken,hp_restored,levelup_hp,potion_hp,rest_healing,"
        "act_transition_healing,events,shop_items,shop_gold_spent,"
        "xp,gold,potions,upgrades"
    )
    for class_id, route, rows, _summary in summaries:
        for act_number in (1, 2, 3):
            act_rows = [row["acts"].get(str(act_number)) for row in rows]
            clear_count = sum(row["acts_cleared"] >= act_number for row in rows)
            clear_ci = _wilson_interval(clear_count, len(rows))
            reached = [act for act in act_rows if act is not None]
            floors = [floor for act in reached for floor in act["floors_visited"]]
            mean_floor = statistics.mean([max(act["floors_visited"], default=0) for act in reached]) if reached else 0
            tiers: dict[str, int] = {}
            nodes: dict[str, int] = {}
            for act in reached:
                for tier, count in act["combat_tiers"].items():
                    tiers[tier] = tiers.get(tier, 0) + count
                for node_type, count in act["nodes"].items():
                    nodes[node_type] = nodes.get(node_type, 0) + count
            node_text = "|".join(
                f"{key}:{value / len(rows):.2f}" for key, value in sorted(nodes.items())
            ) or "none"
            tier_text = "|".join(
                f"{key}:{value / len(rows):.2f}" for key, value in sorted(tiers.items())
            ) or "none"

            def mean_act_metric(key: str) -> float:
                return statistics.mean(act.get(key, 0) for act in reached) if reached else 0.0
            print(
                f"{class_id},{route},{act_number},{clear_count / len(rows):.1%},"
                f"{clear_ci[0]:.1%}-{clear_ci[1]:.1%},{mean_floor:.2f},"
                f"{max(floors, default=0)},{node_text},{tier_text},"
                f"{mean_act_metric('damage_dealt'):.1f},{mean_act_metric('damage_taken'):.1f},"
                f"{mean_act_metric('status_damage_taken'):.1f},"
                f"{mean_act_metric('hp_restored_in_combat'):.1f},"
                f"{mean_act_metric('hp_restored_on_level_up'):.1f},"
                f"{mean_act_metric('potion_hp_restored'):.1f},{mean_act_metric('rest_healing'):.1f},"
                f"{mean_act_metric('act_transition_healing'):.1f},"
                f"{mean_act_metric('events_resolved'):.2f},{mean_act_metric('shop_items_bought'):.2f},"
                f"{mean_act_metric('shop_gold_spent'):.1f},"
                f"{mean_act_metric('xp_awarded'):.1f},{mean_act_metric('gold_awarded'):.1f},"
                f"{mean_act_metric('potions_used'):.2f},{mean_act_metric('equipment_upgrades'):.2f}"
            )

    print("\n=== ELIXIRES PERMANENTES USADOS ===")
    print("class,route,item_id,uses,uses_per_run")
    for class_id, route, rows, _summary in summaries:
        item_counts: dict[str, int] = {}
        for row in rows:
            for item_id, count in row.get("stat_potion_ids_used", {}).items():
                item_counts[item_id] = item_counts.get(item_id, 0) + count
        for item_id, count in sorted(item_counts.items()):
            print(f"{class_id},{route},{item_id},{count},{count / len(rows):.2f}")

    print("\n=== COMBATES POR TIER ===")
    print("class,route,tier,encounters,win%,win_95ci,mean_ticks,damage_dealt,damage_taken,status_taken")
    for class_id, route, rows, _summary in summaries:
        encounters = [encounter for row in rows for encounter in row["encounters"]]
        for tier in ("COMMON", "ELITE", "BOSS"):
            selected = [encounter for encounter in encounters if encounter["tier"] == tier]
            if not selected:
                continue
            wins = sum(encounter["won"] for encounter in selected)
            win_ci = _wilson_interval(wins, len(selected))
            print(
                f"{class_id},{route},{tier},{len(selected)},"
                f"{wins / len(selected):.1%},{win_ci[0]:.1%}-{win_ci[1]:.1%},"
                f"{statistics.mean(encounter['ticks'] for encounter in selected):.1f},"
                f"{statistics.mean(encounter['damage_dealt'] for encounter in selected):.1f},"
                f"{statistics.mean(encounter['damage_taken'] for encounter in selected):.1f},"
                f"{statistics.mean(encounter['status_damage_taken'] for encounter in selected):.1f}"
            )

    print("\n=== DESGASTE EN COMBATES COMUNES POR ACTO ===")
    print(
        "class,route,act,encounters,one_hit_kill%,enemy_acted%,"
        "mean_player_hits,mean_player_actions,mean_enemy_actions,mean_damage_taken"
    )
    for class_id, route, rows, _summary in summaries:
        common_encounters = [
            encounter
            for row in rows
            for encounter in row["encounters"]
            if encounter["tier"] == "COMMON"
        ]
        for act in (1, 2, 3):
            selected = [encounter for encounter in common_encounters if encounter["act"] == act]
            if not selected:
                continue
            one_hit_kills = sum(
                encounter["won"]
                and encounter["player_direct_kill"]
                and encounter["player_damage_hits"] == 1
                for encounter in selected
            )
            enemy_acted = sum(encounter["enemy_actions"] > 0 for encounter in selected)
            print(
                f"{class_id},{route},{act},{len(selected)},"
                f"{one_hit_kills / len(selected):.1%},{enemy_acted / len(selected):.1%},"
                f"{statistics.mean(encounter['player_damage_hits'] for encounter in selected):.2f},"
                f"{statistics.mean(encounter['player_actions'] for encounter in selected):.2f},"
                f"{statistics.mean(encounter['enemy_actions'] for encounter in selected):.2f},"
                f"{statistics.mean(encounter['damage_taken'] + encounter['status_damage_taken'] for encounter in selected):.1f}"
            )

    print("\n=== ENEMIGOS COMUNES QUE NO LLEGAN A ATACAR ===")
    print(
        "class,route,act,enemy_id,encounters,one_hit_kill%,enemy_acted%,"
        "enemy_speed,player_speed,mean_player_hits,mean_enemy_actions,mean_damage_taken"
    )
    for class_id, route, rows, _summary in summaries:
        common = [
            encounter
            for row in rows
            for encounter in row["encounters"]
            if encounter["tier"] == "COMMON"
        ]
        archetypes = sorted({encounter["enemy_id"] for encounter in common})
        for act in (1, 2, 3):
            for enemy_id in archetypes:
                selected = [
                    encounter
                    for encounter in common
                    if encounter["act"] == act and encounter["enemy_id"] == enemy_id
                ]
                if not selected:
                    continue
                attacked = sum(encounter["enemy_actions"] > 0 for encounter in selected)
                one_hit_kills = sum(
                    encounter["won"]
                    and encounter["player_direct_kill"]
                    and encounter["player_damage_hits"] == 1
                    for encounter in selected
                )
                print(
                    f"{class_id},{route},{act},{enemy_id},{len(selected)},"
                    f"{one_hit_kills / len(selected):.1%},{attacked / len(selected):.1%},"
                    f"{statistics.mean(encounter['enemy_speed'] for encounter in selected):.1f},"
                    f"{statistics.mean(encounter['player_speed_start'] for encounter in selected):.1f},"
                    f"{statistics.mean(encounter['player_damage_hits'] for encounter in selected):.2f},"
                    f"{statistics.mean(encounter['enemy_actions'] for encounter in selected):.2f},"
                    f"{statistics.mean(encounter['damage_taken'] + encounter['status_damage_taken'] for encounter in selected):.1f}"
                )

    print("\n=== TASA CONDICIONAL DE VICTORIA CONTRA JEFE POR ACTO ===")
    print("class,route,act,boss_encounters,wins,win%,win_95ci")
    for class_id, route, rows, _summary in summaries:
        boss_encounters = [
            encounter
            for row in rows
            for encounter in row["encounters"]
            if encounter["tier"] == "BOSS"
        ]
        for act in (1, 2, 3):
            selected = [encounter for encounter in boss_encounters if encounter["act"] == act]
            if not selected:
                continue
            wins = sum(encounter["won"] for encounter in selected)
            win_ci = _wilson_interval(wins, len(selected))
            print(
                f"{class_id},{route},{act},{len(selected)},{wins},"
                f"{wins / len(selected):.1%},{win_ci[0]:.1%}-{win_ci[1]:.1%}"
            )

    print("\n=== JEFES POR ACTO Y ARQUETIPO ===")
    print(
        "class,route,act,boss_id,encounters,wins,win%,win_95ci,mean_ticks,"
        "boss_hp, boss_atk,player_hp_start,player_hp_after_win,damage_taken,status_taken"
    )
    for class_id, route, rows, _summary in summaries:
        encounters = [
            encounter
            for row in rows
            for encounter in row["encounters"]
            if encounter["tier"] == "BOSS"
        ]
        groups: dict[tuple[int, str], list[dict[str, Any]]] = {}
        for encounter in encounters:
            groups.setdefault((encounter["act"], encounter["enemy_id"]), []).append(encounter)
        for (act, enemy_id), selected in sorted(groups.items()):
            wins = sum(encounter["won"] for encounter in selected)
            win_ci = _wilson_interval(wins, len(selected))
            winning_hp = [
                encounter["player_hp_end"]
                for encounter in selected
                if encounter["won"]
            ]
            print(
                f"{class_id},{route},{act},{enemy_id},{len(selected)},{wins},"
                f"{wins / len(selected):.1%},{win_ci[0]:.1%}-{win_ci[1]:.1%},"
                f"{statistics.mean(encounter['ticks'] for encounter in selected):.1f},"
                f"{statistics.mean(encounter['enemy_hp'] for encounter in selected):.1f},"
                f"{statistics.mean(encounter['enemy_attack'] for encounter in selected):.1f},"
                f"{statistics.mean(encounter['player_hp_start'] for encounter in selected):.1f},"
                f"{statistics.mean(winning_hp) if winning_hp else 0:.1f},"
                f"{statistics.mean(encounter['damage_taken'] for encounter in selected):.1f},"
                f"{statistics.mean(encounter['status_damage_taken'] for encounter in selected):.1f}"
            )

    print("\n=== ENEMIGOS QUE MÁS DERROTAS CAUSAN ===")
    print("class,route,act,floor,tier,enemy_id,statuses,deaths,example_seeds")
    for class_id, route, rows, _summary in summaries:
        deaths: dict[tuple[int, int, str, str, str], list[int]] = {}
        for row in rows:
            death = row["death"]
            if death:
                key = (
                    death["act"],
                    death["floor"],
                    death["tier"],
                    death["enemy_id"],
                    "+".join(death["statuses"]) or "none",
                )
                deaths.setdefault(key, []).append(row["seed"])
        for (act, floor, tier, enemy_id, statuses), seeds in sorted(
            deaths.items(), key=lambda item: (-len(item[1]), item[0])
        )[:5]:
            seed_examples = "/".join(str(seed) for seed in seeds[:3])
            print(
                f"{class_id},{route},{act},{floor},{tier},{enemy_id},{statuses},"
                f"{len(seeds)},{seed_examples}"
            )

    print("\n=== ARQUETIPOS CON MÁS DAÑO RECIBIDO ===")
    print("class,route,enemy_id,encounters,win%,mean_damage_taken,mean_status_taken,mean_ticks")
    for class_id, route, rows, _summary in summaries:
        encounters = [encounter for row in rows for encounter in row["encounters"]]
        enemy_ids = sorted({encounter["enemy_id"] for encounter in encounters})
        ranked = []
        for enemy_id in enemy_ids:
            selected = [encounter for encounter in encounters if encounter["enemy_id"] == enemy_id]
            ranked.append((
                statistics.mean(encounter["damage_taken"] + encounter["status_damage_taken"] for encounter in selected),
                enemy_id,
                selected,
            ))
        for _mean_taken, enemy_id, selected in sorted(ranked, reverse=True)[:5]:
            wins = sum(encounter["won"] for encounter in selected)
            print(
                f"{class_id},{route},{enemy_id},{len(selected)},{wins / len(selected):.1%},"
                f"{statistics.mean(encounter['damage_taken'] for encounter in selected):.1f},"
                f"{statistics.mean(encounter['status_damage_taken'] for encounter in selected):.1f},"
                f"{statistics.mean(encounter['ticks'] for encounter in selected):.1f}"
            )

    print("\n=== HABILIDADES: SELECCIÓN Y EFICACIA EN COMBATE ===")
    print("class,route,ability_id,drafts_selected,activations,damage_per_activation,hp_restored_per_activation")
    for class_id, route, rows, _summary in summaries:
        uses: dict[str, int] = {}
        selected_counts: dict[str, int] = {}
        effectiveness: dict[str, dict[str, int]] = {}
        for row in rows:
            for ability_id, count in row["ability_uses"].items():
                uses[ability_id] = uses.get(ability_id, 0) + count
            for ability_id, count in row["abilities_selected"].items():
                selected_counts[ability_id] = selected_counts.get(ability_id, 0) + count
            for ability_id, values in row["ability_effectiveness"].items():
                total = effectiveness.setdefault(ability_id, {"uses": 0, "damage": 0, "hp_restored": 0})
                for key in total:
                    total[key] += values[key]
        all_abilities = set(uses) | set(selected_counts)
        for ability_id in sorted(all_abilities):
            result = effectiveness.get(ability_id, {"uses": 0, "damage": 0, "hp_restored": 0})
            activations = uses.get(ability_id, 0)
            damage_per_use = result["damage"] / activations if activations else 0
            healing_per_use = result["hp_restored"] / activations if activations else 0
            print(
                f"{class_id},{route},{ability_id},{selected_counts.get(ability_id, 0)},"
                f"{activations},{damage_per_use:.1f},{healing_per_use:.1f}"
            )

    print("\n=== EQUIPO MEJORADO Y EQUIPADO ===")
    print("class,route,item_id,upgrades")
    for class_id, route, rows, _summary in summaries:
        selected_counts: dict[str, int] = {}
        for row in rows:
            for item_id, count in row["equipment_selected"].items():
                selected_counts[item_id] = selected_counts.get(item_id, 0) + count
        for item_id, count in sorted(selected_counts.items(), key=lambda item: (-item[1], item[0])):
            print(f"{class_id},{route},{item_id},{count}")

    print("\n=== ACTIVACIÓN DE HABILIDADES DE FIRMA ===")
    print("class,route,signature_id,promoted_runs,runs_with_proc,total_procs,procs_per_promoted_run")
    for class_id, route, rows, _summary in summaries:
        by_signature: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            signature_id = row.get("signature_id")
            if signature_id:
                by_signature.setdefault(signature_id, []).append(row)
        for signature_id, promoted_rows in sorted(by_signature.items()):
            total_procs = sum(
                sum(row.get("signature_procs", {}).values()) for row in promoted_rows
            )
            runs_with_proc = sum(
                sum(row.get("signature_procs", {}).values()) > 0 for row in promoted_rows
            )
            print(
                f"{class_id},{route},{signature_id},{len(promoted_rows)},{runs_with_proc},"
                f"{total_procs},{total_procs / len(promoted_rows):.2f}"
            )

    print("\n=== DIFERENCIA PAREADA DE RUTA (PATHFINDER - FATE) ===")
    print("class,metric,n,fate_mean,pathfinder_mean,delta,delta_95ci,pathfinder_better,tie,fate_better")
    paired_metrics = (
        ("victory", "victory_rate", True),
        ("act1_clear", "act1_clear_rate", True),
        ("act2_clear", "act2_clear_rate", True),
        ("act3_clear", "act3_clear_rate", True),
        ("fights", "mean_fights", False),
        ("damage_taken", "mean_total_damage_taken", False),
        ("xp_awarded", "mean_xp_awarded", False),
    )
    for class_id, matched_runs in paired_rows.items():
        for metric, _summary_key, is_rate in paired_metrics:
            def metric_value(run: dict[str, Any]) -> float:
                if metric == "victory":
                    return float(run["victory"])
                if metric == "act1_clear":
                    return float(run["acts_cleared"] >= 1)
                if metric == "act2_clear":
                    return float(run["acts_cleared"] >= 2)
                if metric == "act3_clear":
                    return float(run["acts_cleared"] >= 3)
                if metric == "damage_taken":
                    return float(run["damage_taken"] + run["status_damage_taken"])
                return float(run[metric])

            fate_values = [metric_value(fate) for fate, _pathfinder in matched_runs]
            path_values = [metric_value(pathfinder) for _fate, pathfinder in matched_runs]
            deltas = [path - fate for fate, path in zip(fate_values, path_values)]
            mean_delta, ci_low, ci_high = _paired_delta_interval(deltas)
            fate_mean = statistics.mean(fate_values)
            path_mean = statistics.mean(path_values)
            if is_rate:
                fate_mean *= 100
                path_mean *= 100
                mean_delta *= 100
                ci_low *= 100
                ci_high *= 100
            path_better = sum(delta > 0 for delta in deltas)
            ties = sum(delta == 0 for delta in deltas)
            fate_better = sum(delta < 0 for delta in deltas)
            print(
                f"{class_id},{metric},{len(deltas)},{fate_mean:.3f},"
                f"{path_mean:.3f},{mean_delta:.3f},"
                f"{ci_low:.3f}..{ci_high:.3f},{path_better},{ties},{fate_better}"
            )


@pytest.mark.skipif(
    os.getenv("RUN_BALANCE_SIMULATION") != "1",
    reason="Set RUN_BALANCE_SIMULATION=1 to run the opt-in Monte Carlo balance simulation.",
)
def test_monte_carlo_balance_by_class_and_route(monkeypatch: Any) -> None:
    trials = max(1, int(os.getenv("AETHELGARD_MC_TRIALS", str(DEFAULT_TRIALS))))
    master_seed = int(os.getenv("AETHELGARD_MC_SEED", "20261027"))
    summaries: list[tuple[str, str, list[dict[str, Any]], dict[str, Any]]] = []
    paired_rows: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    total_runs = trials * len(PLAYABLE_CLASSES) * len(ROUTE_MODES)
    completed_runs = 0
    print(
        f"[MC] Starting {total_runs} runs "
        f"({trials} trials x {len(PLAYABLE_CLASSES)} classes x {len(ROUTE_MODES)} routes); "
        f"master seed={master_seed}. Set AETHELGARD_MC_VERBOSE=1 for fight-by-fight logs.",
        flush=True,
    )

    for class_index, class_id in enumerate(PLAYABLE_CLASSES):
        route_rows = {route_mode: [] for route_mode in ROUTE_MODES}
        matched: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for trial in range(trials):
            # The identical seed is run under both route policies for a matched comparison.
            seed = master_seed + class_index * 100_000 + trial
            current_pair: dict[str, dict[str, Any]] = {}
            for route_mode in ROUTE_MODES:
                run_number = completed_runs + 1
                print(
                    f"[MC] [{run_number}/{total_runs}] START "
                    f"class={class_id} route={route_mode} trial={trial + 1}/{trials} seed={seed}",
                    flush=True,
                )
                row = _simulate_trial(
                    class_id=class_id,
                    route_mode=route_mode,
                    seed=seed,
                    monkeypatch=monkeypatch,
                )
                completed_runs += 1
                outcome = "victory" if row["victory"] else "death" if row["death"] else "timeout" if row["timeout"] else "stalled"
                print(
                    f"[MC] [{completed_runs}/{total_runs}] DONE "
                    f"class={class_id} route={route_mode} trial={trial + 1}/{trials} "
                    f"result={outcome} acts={row['acts_cleared']} fights={row['fights']} "
                    f"ticks={row['combat_ticks']} floor={row['final_floor']}",
                    flush=True,
                )
                route_rows[route_mode].append(row)
                current_pair[route_mode] = row
            matched.append((current_pair["FATE"], current_pair["PATHFINDER"]))

        for route_mode in ROUTE_MODES:
            rows = route_rows[route_mode]
            summaries.append((class_id, route_mode, rows, _summarize(rows)))
        paired_rows[class_id] = matched

    _print_detailed_tables(summaries, paired_rows)

    assert len(summaries) == len(PLAYABLE_CLASSES) * len(ROUTE_MODES)
    assert all(0.0 <= summary["victory_rate"] <= 1.0 for _, _, _, summary in summaries)
    assert all(summary["mean_fights"] > 0 for _, _, _, summary in summaries)


def test_expected_ability_damage_uses_real_combat_damage_hooks() -> None:
    from src.data.abilities import get_ability_by_id
    from src.entities.actor import Stats
    from src.entities.enemy import Enemy, EnemyTier
    from src.entities.player import Player
    from src.systems.combat import CombatSystem

    player = Player(name="ForecastTester", class_id="warrior")
    player.base_stats = Stats(100, 40, 10, 10, 0.0)
    enemy = Enemy(
        name="ForecastTarget",
        stats=Stats(500, 10, 5, 10, 0.0),
        tier=EnemyTier.COMMON,
        floor_level=1,
        exp_reward=0,
        gold_reward=0,
    )
    combat = CombatSystem(player, enemy, seed=7)
    ability = get_ability_by_id("cross_cut")

    assert ability is not None
    assert _expected_ability_damage(combat, ability, samples=2) > 0
