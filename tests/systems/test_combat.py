import os
import sys

import pytest

# Ensure the src directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src')))

from src.systems.combat import CombatSystem, CombatResult
from src.entities.player import Player
from src.entities.enemy import Enemy, EnemyTier
from src.entities.actor import Stats
from src.systems.status import StatusEffect, StatusTrigger, StatusType


class MockRNG:
    def __init__(self, random_val=0.5, uniform_val=1.0):
        self.random_val = random_val
        self.uniform_val = uniform_val

    def random(self):
        return self.random_val

    def uniform(self, a, b):
        return self.uniform_val


@pytest.fixture
def base_player():
    player = Player(name="Hero", class_id="warrior")
    # override stats for deterministic testing
    player.base_stats = Stats(max_hp=100, attack=10, defense=0, speed=10, crit_chance=0.0)
    player.current_hp = 100
    return player


@pytest.fixture
def base_enemy():
    stats = Stats(max_hp=50, attack=5, defense=0, speed=5, crit_chance=0.0)
    return Enemy(
        name="Goblin",
        stats=stats,
        tier=EnemyTier.COMMON,
        floor_level=1,
        exp_reward=10,
        gold_reward=5
    )


def test_combat_init(base_player, base_enemy):
    combat = CombatSystem(player=base_player, enemy=base_enemy, seed=42)
    assert combat.is_active()
    assert combat.result == CombatResult.IN_PROGRESS
    assert combat.player_gauge == 0
    assert combat.enemy_gauge == 0


def test_speed_determines_turn(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    # Player speed 100, Enemy speed 10
    base_player.base_stats.speed = 100
    base_enemy.base_stats.speed = 10

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    combat.rng = MockRNG(random_val=0.5, uniform_val=1.0)  # no crit, 1.0 variance

    combat.step()

    assert combat.player_gauge == 0
    assert combat.enemy_gauge == 10
    assert base_enemy.current_hp == 40


def test_resolve_all_player_victory(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.base_stats.attack = 50
    base_player.base_stats.speed = 100
    base_enemy.base_stats.speed = 10

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    combat.rng = MockRNG(uniform_val=1.0)  # guaranteed 50 damage -> exactly enemy max_hp

    result = combat.resolve_all(max_ticks=10)

    assert result == CombatResult.PLAYER_VICTORY
    assert not base_enemy.is_alive
    assert base_player.gold == 5  # 0 + 5 from base_enemy gold reward


def test_resolve_all_player_defeat(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.base_stats.speed = 10
    base_enemy.base_stats.attack = 100
    base_enemy.base_stats.speed = 100

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    combat.rng = MockRNG(uniform_val=1.0)  # guaranteed 100 damage -> exactly player max_hp

    result = combat.resolve_all(max_ticks=10)

    assert result == CombatResult.PLAYER_DEFEAT
    assert not base_player.is_alive


def test_stun_status_prevents_action(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.base_stats.speed = 100
    base_enemy.base_stats.speed = 10

    stun_effect = StatusEffect(
        id="stun",
        name="Stun",
        badge="STN",
        color=8,
        status_type=StatusType.DEBUFF,
        trigger=StatusTrigger.PRE_ACTION,
        duration=1
    )
    base_player.apply_status(stun_effect)

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    combat.rng = MockRNG(uniform_val=1.0)

    combat.step()

    # Player gauge reached 100, but is stunned, so action is skipped, gauge is reset to 0, stun duration decreased
    assert combat.player_gauge == 0
    assert combat.enemy_gauge == 10
    # No damage taken by enemy
    assert base_enemy.current_hp == 50
    # Stun duration decreased to 0 and removed
    assert len(base_player.statuses) == 0


def test_combat_crit(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.base_stats.speed = 100
    base_player.base_stats.crit_chance = 1.0  # Guarantee crit

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    # mock rng random to return 0.0 (less than 1.0) -> is_crit is True
    # mock rng uniform to return 1.0
    combat.rng = MockRNG(random_val=0.0, uniform_val=1.0)

    combat.step()

    # damage should be 10 * 1.5 = 15
    assert base_enemy.current_hp == 35


def test_blind_status_miss(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.base_stats.speed = 100

    blind_effect = StatusEffect(
        id="blind",
        name="Blind",
        badge="BLN",
        color=8,
        status_type=StatusType.DEBUFF,
        trigger=StatusTrigger.ON_TICK,
        duration=2
    )
    base_player.apply_status(blind_effect)

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    combat.rng = MockRNG(random_val=0.1, uniform_val=1.0)  # rng < 0.50 triggers miss

    combat.step()

    # Enemy should take no damage
    assert base_enemy.current_hp == 50


def test_vulnerable_status_extra_damage(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.base_stats.speed = 100
    base_player.base_stats.attack = 10  # with uniform_val=1.0, raw_dmg = 10

    vuln_effect = StatusEffect(
        id="vulnerable",
        name="Vulnerable",
        badge="VUL",
        color=8,
        status_type=StatusType.DEBUFF,
        trigger=StatusTrigger.ON_TICK,
        duration=2
    )
    base_enemy.apply_status(vuln_effect)

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    combat.rng = MockRNG(random_val=0.5, uniform_val=1.0)

    combat.step()

    # damage should be int(10 * 1.30) = 13
    assert base_enemy.current_hp == 37


def test_enemy_attacks_player(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_enemy.base_stats.speed = 100
    base_player.base_stats.speed = 10

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    combat.rng = MockRNG(random_val=0.5, uniform_val=1.0)

    combat.step()

    assert combat.enemy_gauge == 0
    assert combat.player_gauge == 10
    # Player takes damage: enemy attack (5) - player def (0) = 5
    assert base_player.current_hp == 95
