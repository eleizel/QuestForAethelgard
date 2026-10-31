"""Unit tests for the standalone QTE system (src/systems/qte.py)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "src")))

from src.entities.actor import Stats
from src.entities.enemy import Enemy, EnemyTier
from src.entities.player import Player
from src.systems.combat import CombatSystem
from src.systems.qte import (
    QTE_MAX_SHRINK_SPEED,
    QTE_MIN_SHRINK_SPEED,
    QTE_OVERSHOOT_GRACE,
    QTETarget,
    classify_qte_tier,
)


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
    player.base_stats = Stats(max_hp=100, attack=10, defense=0, speed=10, crit_chance=0.0)
    player.current_hp = 100
    return player


def test_qte_target_shrink_speed_and_step_shrink():
    target = QTETarget(x=100, y=100, number=2, button_radius=10, start_radius=32.0, current_radius=32.0, shrink_speed=1.0)
    assert target.current_accuracy() == 0
    while not target.step_shrink():
        pass
    assert target.current_radius < target.button_radius - QTE_OVERSHOOT_GRACE
    assert classify_qte_tier(15) == "failed"
    assert classify_qte_tier(35) == "good"
    assert classify_qte_tier(55) == "nice"
    assert classify_qte_tier(75) == "amazing"
    assert classify_qte_tier(95) == "perfect"


def test_qte_triggers_on_elite_and_boss_thresholds(base_player, monkeypatch):
    import pyxel

    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    elite = Enemy(
        name="Orc Warlord",
        stats=Stats(max_hp=100, attack=15, defense=0, speed=10, crit_chance=0.0),
        tier=EnemyTier.ELITE,
        floor_level=5,
        exp_reward=25,
        gold_reward=15,
    )
    combat_elite = CombatSystem(player=base_player, enemy=elite, seed=10)
    # Crossing 50% HP triggers QTE on Elite
    combat_elite.damage_enemy(55)
    assert combat_elite.is_qte_active()
    assert 3 <= len(combat_elite.active_qte.targets) <= 5
    for target in combat_elite.active_qte.targets:
        assert 40 <= target.x <= 216
        assert 58 <= target.y <= 178
        assert target.number in (1, 2, 3)
        assert QTE_MIN_SHRINK_SPEED <= target.shrink_speed <= QTE_MAX_SHRINK_SPEED
        assert target.current_accuracy() == 0
        target.current_radius = float(target.button_radius)
        assert target.current_accuracy() == 100

    combat_elite.dismiss_qte_summary()
    # Crossing 25% HP does NOT trigger a second QTE on an Elite
    combat_elite.damage_enemy(30)
    assert not combat_elite.is_qte_active()

    boss = Enemy(
        name="Dragon",
        stats=Stats(max_hp=100, attack=20, defense=0, speed=10, crit_chance=0.0),
        tier=EnemyTier.BOSS,
        floor_level=10,
        exp_reward=100,
        gold_reward=50,
    )
    combat_boss = CombatSystem(player=base_player, enemy=boss, seed=20)
    combat_boss.damage_enemy(55)  # 100 -> 45 (50% threshold)
    assert combat_boss.is_qte_active()
    combat_boss.dismiss_qte_summary()
    combat_boss.damage_enemy(25)  # 45 -> 20 (25% threshold)
    assert combat_boss.is_qte_active()


@pytest.mark.parametrize(
    "scores,expected_avg,expected_tier",
    [
        ([10, 20, 15], 15, "failed"),
        ([30, 40, 35], 35, "good"),
        ([50, 50, 50], 50, "nice"),
        ([60, 70, 80, 40], 62, "amazing"),
        ([90, 85, 95], 90, "perfect"),
    ],
)
def test_qte_resolution_tiers_and_cumulative_bonuses(
    base_player, monkeypatch, scores, expected_avg, expected_tier
):
    import pyxel

    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.base_stats = Stats(max_hp=100, attack=20, defense=20, speed=10, crit_chance=0.0)
    base_player.current_hp = 60

    boss = Enemy(
        name="Archdemon",
        stats=Stats(max_hp=200, attack=30, defense=0, speed=10, crit_chance=0.0),
        tier=EnemyTier.BOSS,
        floor_level=12,
        exp_reward=100,
        gold_reward=50,
    )
    combat = CombatSystem(player=base_player, enemy=boss, seed=99)
    combat.start_qte_sequence(count=len(scores))

    for score in scores:
        combat.resolve_qte_target(score)
        combat.advance_qte_after_feedback()

    assert combat.active_qte.summary_active is True
    assert combat.active_qte.final_score == expected_avg
    assert combat.active_qte.final_tier == expected_tier

    if expected_avg <= 20:
        assert combat.qte_next_damage_mitigation == 0.0
        assert base_player.combat_def_buff == 0
        assert boss.base_stats.attack == 30
        assert boss.current_hp == 200
        assert base_player.current_hp == 60
    elif expected_avg <= 40:
        assert pytest.approx(combat.qte_next_damage_mitigation) == expected_avg / 100.0
        assert base_player.combat_def_buff == 0
        assert boss.base_stats.attack == 30
    elif expected_avg <= 60:
        assert pytest.approx(combat.qte_next_damage_mitigation) == expected_avg / 100.0
        assert base_player.combat_def_buff == 2  # +10% of 20 DEF
        assert boss.base_stats.attack == 30
    elif expected_avg <= 80:
        assert pytest.approx(combat.qte_next_damage_mitigation) == expected_avg / 100.0
        assert base_player.combat_def_buff == 2  # +10% of 20 DEF
        assert boss.base_stats.attack == 27  # -10% of 30 ATK
        assert boss.current_hp == 200
    else:
        assert pytest.approx(combat.qte_next_damage_mitigation) == expected_avg / 100.0
        assert base_player.combat_def_buff == 2  # +10% of 20 DEF
        assert boss.base_stats.attack == 27  # -10% of 30 ATK
        # Immediate counterattack: 50% of 20 ATK = 10 dmg, heals half (5 HP)
        assert boss.current_hp == 190
        assert base_player.current_hp == 65

    # Verify next-hit damage mitigation reduces the next enemy attack and is then consumed
    if expected_avg >= 21:
        combat.rng = MockRNG(random_val=0.5, uniform_val=1.0)
        hp_before_hit = base_player.current_hp
        combat.enemy_gauge = 100
        combat._execute_enemy_attack()
        assert combat.qte_next_damage_mitigation == 0.0
        assert base_player.current_hp > hp_before_hit - boss.base_stats.attack
