import pytest

from src.entities.actor import Actor, Stats


@pytest.fixture
def base_stats():
    return Stats(max_hp=100, attack=10, defense=5, speed=5)


@pytest.fixture
def actor(base_stats):
    return Actor("TestActor", base_stats)


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
