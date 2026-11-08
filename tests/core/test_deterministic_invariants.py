"""Deterministic property and invariant tests for Quest for Aethelgard.







Verifies mathematical reproducibility across combat simulation, spire map topology,



equipment stat aggregation, and save/load state round-trips.



"""

import copy


import random


import pytest


from src.core.game_state import GameMode, GameState


from src.core.save_manager import (
    FileStorageBackend,
    SaveManager,
    create_run_memento,
    restore_from_memento,
)


from src.data.items import get_item


from src.entities.actor import Stats


from src.entities.enemy import Enemy, EnemyTier


from src.entities.player import Player


from src.systems.combat import CombatResult, CombatSystem


from src.systems.map_gen import generate_spire_map


def test_deterministic_combat_replay():
    """Given identical seeds, combat simulation produces strictly identical tick sequences and logs."""

    seed = 4294967295

    # Combatant 1

    p1 = Player(name="Sir Aethelgard", class_id="warrior")

    e1 = Enemy(
        name="Ancient Wraith",
        tier=EnemyTier.ELITE,
        stats=Stats(max_hp=120, attack=22, defense=8, speed=12),
        floor_level=3,
        exp_reward=50,
        gold_reward=35,
    )

    combat1 = CombatSystem(player=p1, enemy=e1, seed=seed)

    # Combatant 2

    p2 = Player(name="Sir Aethelgard", class_id="warrior")

    e2 = Enemy(
        name="Ancient Wraith",
        tier=EnemyTier.ELITE,
        stats=Stats(max_hp=120, attack=22, defense=8, speed=12),
        floor_level=3,
        exp_reward=50,
        gold_reward=35,
    )

    combat2 = CombatSystem(player=p2, enemy=e2, seed=seed)

    ticks1 = 0

    ticks2 = 0

    while combat1.is_active() and ticks1 < 1000:
        combat1.step()

        ticks1 += 1

    while combat2.is_active() and ticks2 < 1000:
        combat2.step()

        ticks2 += 1

    assert ticks1 == ticks2, "Step count drifted between identical seed replays"

    assert combat1.result == combat2.result, "Combat results drifted"

    assert p1.current_hp == p2.current_hp, "Final player HP drifted"

    assert e1.current_hp == e2.current_hp, "Final enemy HP drifted"

    assert len(combat1.combat_logs) == len(combat2.combat_logs), "Log count drifted"

    for l1, l2 in zip(combat1.combat_logs, combat2.combat_logs):
        assert str(l1) == str(l2), f"Log entry mismatch: '{l1}' != '{l2}'"


def test_spire_map_structural_invariants():
    """All generated spire maps across varying seeds maintain topological invariants."""

    for seed in [1, 42, 1337, 88888, 999999]:
        graph = generate_spire_map(num_floors=12, width_lanes=4, seed=seed)

        assert len(graph.floors) == 12, "Incorrect total floor count"

        # Invariant 1: Floor 0 has available nodes

        assert len(graph.floors[0]) >= 1, "Floor 0 must have at least one starting node"

        # Invariant 2: Node floors strictly match their floor index

        for f_idx, floor in enumerate(graph.floors):
            for node in floor:
                assert node.floor == f_idx, (
                    f"Node {node.id} floor {node.floor} mismatch with {f_idx}"
                )

        # Invariant 3: Outgoing edges only point to the immediate next floor

        for f_idx, floor in enumerate(graph.floors[:-1]):
            for node in floor:
                for out_id in node.outgoing_ids:
                    target = graph.nodes_by_id.get(out_id)

                    assert target is not None, f"Node {node.id} points to missing node {out_id}"

                    assert target.floor == f_idx + 1, (
                        f"Edge {node.id} (F{node.floor}) -> {out_id} (F{target.floor}) violates floor progression"
                    )

        # Invariant 4: Boss floor (last floor) contains exactly 1 boss node

        boss_floor = graph.floors[-1]

        assert len(boss_floor) == 1, "Boss floor must contain exactly 1 node"

        assert boss_floor[0].node_type.name == "BOSS", "Final node must be of type BOSS"


def test_inventory_equipment_invariants():
    """Equipping items modifies effective stats additively; unequipping strictly restores baseline."""

    player = Player(name="Sir Aethelgard", class_id="warrior")

    base_atk = player.base_stats.attack

    base_def = player.base_stats.defense

    base_hp = player.base_stats.max_hp

    sword = get_item("bronze_sword")

    shield = get_item("bronze_shield")

    assert sword is not None and shield is not None

    # Equip sword

    player.inventory.equip(sword)

    assert player.effective_stats.attack == base_atk + sword.stats_bonus.attack

    # Equip shield

    player.inventory.equip(shield)

    assert (
        player.effective_stats.defense
        == base_def + sword.stats_bonus.defense + shield.stats_bonus.defense
    )

    # Unequip both

    from src.entities.item import EquipSlot

    player.inventory.unequip(EquipSlot.MAIN_HAND)

    player.inventory.unequip(EquipSlot.OFF_HAND)

    assert player.effective_stats.attack == base_atk

    assert player.effective_stats.defense == base_def

    assert player.effective_stats.max_hp == base_hp


def test_save_load_memento_invariants(tmp_path):
    """Full GameState serialization through RunMemento strictly preserves all attributes."""

    state = GameState()

    state.start_new_game(class_id="mage", route_mode="FATE")

    state.player.gold = 350

    state.player.gain_experience(120)

    state.floor = 4

    state.act = 2

    state.run_seed = 987654321

    sword = get_item("bronze_sword")

    if sword:
        state.player.inventory.equip(sword)

    memento = create_run_memento(state)

    fresh_state = GameState()

    restored = restore_from_memento(fresh_state, memento)

    assert restored is True

    assert fresh_state.player.name == state.player.name

    assert fresh_state.player.class_id == "mage"

    assert fresh_state.player.gold == 350

    assert fresh_state.player.experience == state.player.experience

    assert fresh_state.floor == 4

    assert fresh_state.act == 2

    assert fresh_state.run_seed == 987654321

    assert fresh_state.player.effective_stats.attack == state.player.effective_stats.attack
