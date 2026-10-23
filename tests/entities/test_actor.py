import pytest
from src.entities.actor import Actor, Stats

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

    assert actual_damage == 15
    assert actor.current_hp == 85

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
