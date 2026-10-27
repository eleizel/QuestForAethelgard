import os
import sys

import pytest

# Ensure the src directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.entities.actor import Stats, Actor


@pytest.fixture
def base_stats():
    return Stats(max_hp=100, attack=10, defense=5, speed=5)


@pytest.fixture
def actor(base_stats):
    return Actor("TestActor", base_stats)


def test_stats_add_normal():
    """Test combining two sets of stats normally."""
    base = Stats(max_hp=100, attack=20, defense=10, speed=15, crit_chance=0.1)
    bonus = Stats(max_hp=50, attack=5, defense=2, speed=3, crit_chance=0.05)

    result = base.add(bonus)

    assert result.max_hp == 150
    assert result.attack == 25
    assert result.defense == 12
    assert result.speed == 18
    assert result.crit_chance == pytest.approx(0.15)


def test_stats_add_lower_bounds():
    """Test that stat additions clamp correctly to their lower bounds."""
    base = Stats(max_hp=10, attack=5, defense=5, speed=5, crit_chance=0.05)
    penalty = Stats(max_hp=-20, attack=-10, defense=-10, speed=-10, crit_chance=-0.1)

    result = base.add(penalty)

    assert result.max_hp == 1
    assert result.attack == 0
    assert result.defense == 0
    assert result.speed == 1
    assert result.crit_chance == 0.0


def test_stats_add_upper_bounds_crit():
    """Test that crit_chance is clamped correctly to its upper bound of 1.0."""
    base = Stats(max_hp=10, attack=5, defense=5, speed=5, crit_chance=0.9)
    bonus = Stats(max_hp=0, attack=0, defense=0, speed=0, crit_chance=0.5)

    result = base.add(bonus)

    assert result.crit_chance == 1.0


def test_heal_normal_amount(actor):
    """Test healing a normal amount without exceeding max HP."""
    actor.current_hp = 50
    restored = actor.heal(20)
    assert restored == 20
    assert actor.current_hp == 70


def test_heal_dead_actor(actor):
    """Test that a dead actor (HP <= 0) cannot be healed."""
    actor.current_hp = 0
    restored = actor.heal(50)
    assert restored == 0
    assert actor.current_hp == 0

    actor.current_hp = -10
    restored = actor.heal(50)
    assert restored == 0
    assert actor.current_hp == -10


def test_heal_negative_amount(actor):
    """Test that healing with a negative amount returns 0 and does not change HP."""
    actor.current_hp = 50
    restored = actor.heal(-20)
    assert restored == 0
    assert actor.current_hp == 50


def test_heal_zero_amount(actor):
    """Test that healing with 0 amount returns 0 and does not change HP."""
    actor.current_hp = 50
    restored = actor.heal(0)
    assert restored == 0
    assert actor.current_hp == 50


def test_heal_exceeds_max_hp(actor):
    """Test that healing does not exceed max HP and returns the actual restored amount."""
    actor.current_hp = 80
    restored = actor.heal(50)
    assert restored == 20
    assert actor.current_hp == 100


def test_heal_at_max_hp(actor):
    """Test that healing an actor already at max HP returns 0 and does not change HP."""
    actor.current_hp = 100
    restored = actor.heal(50)
    assert restored == 0
    assert actor.current_hp == 100


def create_actor(max_hp: int, defense: int) -> Actor:
    stats = Stats(max_hp=max_hp, attack=10, defense=defense, speed=10)
    return Actor("Test Actor", stats)


def test_take_damage_no_defense():
    """Test taking damage with 0 defense."""
    actor = create_actor(max_hp=100, defense=0)

    # Raw damage 20 -> Mitigated 20 -> Actual 20
    actual_damage = actor.take_damage(20)

    assert actual_damage == 20
    assert actor.current_hp == 80


def test_take_damage_with_defense():
    """Test taking damage with positive defense."""
    actor = create_actor(max_hp=100, defense=10)

    # Defense 10 -> mitigation 5. Raw damage 20 -> Mitigated 15 -> Actual 15
    actual_damage = actor.take_damage(20)

    assert actual_damage == 16
    assert actor.current_hp == 84


def test_take_damage_minimum_one():
    """Test that taking damage always results in at least 1 damage, regardless of high defense."""
    actor = create_actor(max_hp=100, defense=100)

    # Defense 100 -> mitigation 50. Raw damage 20 -> Mitigated max(1, 20 - 50) = 1 -> Actual 1
    actual_damage = actor.take_damage(20)

    assert actual_damage == 1
    assert actor.current_hp == 99


def test_take_damage_fatal():
    """Test taking damage that exceeds current HP."""
    actor = create_actor(max_hp=50, defense=10)

    # Defense 10 -> mitigation 5. Raw damage 100 -> Mitigated 95
    # Actual should be min(50, 95) = 50
    actual_damage = actor.take_damage(100)

    assert actual_damage == 50
    assert actor.current_hp == 0
    assert not actor.is_alive


def test_take_damage_negative_defense_ignored():
    """Test that negative defense acts like 0 defense."""
    actor = create_actor(max_hp=100, defense=-10)

    # Defense -10 -> effective_defense max(0, -10) = 0
    # Mitigation 0. Raw damage 20 -> Mitigated 20 -> Actual 20
    actual_damage = actor.take_damage(20)

    assert actual_damage == 20
    assert actor.current_hp == 80


def test_take_damage_zero_raw_damage():
    """Test taking 0 raw damage still causes 1 mitigated damage because max(1, raw_damage - defense // 2)"""
    actor = create_actor(max_hp=100, defense=10)

    # Defense 10 -> mitigation 5. Raw damage 0 -> Mitigated max(1, 0 - 5) = 1 -> Actual 1
    actual_damage = actor.take_damage(0)

    assert actual_damage == 1
    assert actor.current_hp == 99
