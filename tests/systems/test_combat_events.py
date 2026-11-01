"""Unit tests for Phase 4: Structured Combat Events & Log Decoupling."""

import pytest
from src.core.events import (
    DamageDealtEvent,
    HealthRestoredEvent,
    StatusAppliedEvent,
    CombatLogEntry,
)
from src.entities.player import Player
from src.entities.enemy import Enemy, EnemyTier
from src.entities.actor import Stats
from src.systems.combat import CombatSystem


def create_combat() -> CombatSystem:
    player = Player(name="Hero", class_id="warrior")
    player.base_stats = Stats(max_hp=100, attack=20, defense=10, speed=10, crit_chance=0.0)
    player.current_hp = 100

    enemy = Enemy(
        name="Goblin",
        stats=Stats(max_hp=100, attack=15, defense=5, speed=8, crit_chance=0.0),
        tier=EnemyTier.COMMON,
        floor_level=1,
        exp_reward=10,
        gold_reward=5,
    )
    enemy.current_hp = 100
    return CombatSystem(player=player, enemy=enemy)


def test_combat_emits_damage_dealt_event():
    """Executing an attack enqueues a DamageDealtEvent with accurate values."""
    combat = create_combat()
    assert combat.drain_events() == []

    # Execute player attack
    combat._execute_player_attack()

    events = combat.drain_events()
    damage_events = [e for e in events if isinstance(e, DamageDealtEvent)]
    assert len(damage_events) >= 1

    ev = damage_events[0]
    assert ev.source == "Hero"
    assert ev.target == "Goblin"
    assert ev.amount > 0
    assert isinstance(ev.is_crit, bool)

    # Queue should be drained
    assert combat.drain_events() == []


def test_combat_enemy_attack_emits_damage_event():
    """Enemy attacks emit DamageDealtEvent with player as target."""
    combat = create_combat()
    combat.drain_events()

    combat._execute_enemy_attack()

    events = combat.drain_events()
    damage_events = [e for e in events if isinstance(e, DamageDealtEvent)]
    assert len(damage_events) >= 1

    ev = damage_events[0]
    assert ev.source == "Goblin"
    assert ev.target == "Hero"
    assert ev.amount > 0


def test_combat_log_entry_is_str_compatible():
    """CombatLogEntry behaves as a standard str while retaining structured key/params."""
    entry = CombatLogEntry("Hero hits Goblin for 15 damage!", key="combat_hit", params={"dmg": 15})

    # String operations work identically
    assert isinstance(entry, str)
    assert "Goblin" in entry
    assert entry.startswith("Hero")
    assert entry == "Hero hits Goblin for 15 damage!"

    # Structured metadata is accessible
    assert entry.key == "combat_hit"
    assert entry.params == {"dmg": 15}
    assert entry.category == "combat"
