import pytest
import sys
import os

# Ensure the src directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from entities.actor import Stats

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
