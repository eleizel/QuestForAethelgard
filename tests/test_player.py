import pytest
from src.entities.player import Player
from src.entities.actor import Stats
from src.data.classes import CLASS_REGISTRY

def test_available_promotions_underleveled():
    player = Player(class_id="warrior")
    assert player.level == 1
    assert player.available_promotions() == []

def test_available_promotions_leveled():
    player = Player(class_id="warrior")
    player.level = 15
    promotions = player.available_promotions()
    assert "paladin" in promotions
    assert "berserker" in promotions
    assert len(promotions) == 2

def test_available_promotions_max_tier():
    player = Player(class_id="paladin")
    player.level = 20
    assert player.available_promotions() == []

def test_promote_ineligible_class():
    player = Player(class_id="warrior")
    player.level = 15
    # Warrior cannot promote to Assassin
    assert not player.promote("assassin")
    assert player.class_id == "warrior"

def test_promote_underleveled():
    player = Player(class_id="warrior")
    player.level = 14
    # Warrior under level 15 cannot promote
    assert not player.promote("paladin")
    assert player.class_id == "warrior"

def test_promote_success():
    player = Player(class_id="warrior")
    player.level = 15

    # Give a level up bonus first to ensure it's retained
    player.base_stats = player.base_stats.add(Stats(max_hp=5, attack=2, defense=1, speed=0, crit_chance=0))
    initial_base_stats = player.base_stats

    # Promote to paladin
    assert player.promote("paladin")

    assert player.class_id == "paladin"

    # Check stat bonuses applied based on the diff
    old_base = CLASS_REGISTRY["warrior"].base_stats
    new_base = CLASS_REGISTRY["paladin"].base_stats

    diff_hp = max(0, new_base.max_hp - old_base.max_hp)
    diff_atk = max(0, new_base.attack - old_base.attack)
    diff_def = max(0, new_base.defense - old_base.defense)
    diff_spd = max(0, new_base.speed - old_base.speed)
    diff_crit = max(0, new_base.crit_chance - old_base.crit_chance)

    expected_stats = initial_base_stats.add(Stats(diff_hp, diff_atk, diff_def, diff_spd, diff_crit))
    assert player.base_stats.max_hp == expected_stats.max_hp
    assert player.base_stats.attack == expected_stats.attack
    assert player.base_stats.defense == expected_stats.defense
    assert player.base_stats.speed == expected_stats.speed
    assert player.base_stats.crit_chance == pytest.approx(expected_stats.crit_chance)

    # HP is restored to max
    assert player.current_hp == player.max_hp

def test_gain_experience_single_level_up():
    player = Player(class_id="warrior")
    initial_max_hp = player.max_hp
    initial_attack = player.base_stats.attack
    initial_defense = player.base_stats.defense
    initial_speed = player.base_stats.speed
    initial_crit = player.base_stats.crit_chance
    initial_stat_points = player.stat_points

    # Damage the player to verify HP restoration
    player.current_hp = player.max_hp - 10

    # Level 1 to 2 requires 50 exp
    assert player.exp_to_next_level == 50
    assert player.gain_experience(50)
    assert player.level == 2
    assert player.experience == 0

    class_def = CLASS_REGISTRY["warrior"]

    # Check stat bonuses
    assert player.max_hp == initial_max_hp + class_def.growth_per_level.max_hp
    assert player.base_stats.attack == initial_attack + class_def.growth_per_level.attack
    assert player.base_stats.defense == initial_defense + class_def.growth_per_level.defense
    assert player.base_stats.speed == initial_speed + class_def.growth_per_level.speed
    assert player.base_stats.crit_chance == pytest.approx(initial_crit + class_def.growth_per_level.crit_chance)

    # Check HP restoration
    assert player.current_hp == player.max_hp

    # Check stat points
    assert player.stat_points == initial_stat_points + 2

