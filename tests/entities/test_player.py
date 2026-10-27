import pytest

from src.data.classes import CLASS_REGISTRY
from src.entities.actor import Stats
from src.entities.player import Player
from src.systems.abilities import Ability, AbilityType, AbilityRarity


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


def test_effective_stats_base():
    player = Player(class_id="warrior")
    stats = player.effective_stats
    assert stats.max_hp == player.base_stats.max_hp
    assert stats.attack == player.base_stats.attack
    assert stats.defense == player.base_stats.defense
    assert stats.speed == player.base_stats.speed
    assert stats.crit_chance == pytest.approx(player.base_stats.crit_chance)


def test_effective_stats_with_equipment(monkeypatch):
    player = Player(class_id="warrior")

    def mock_get_equipment_stats():
        return Stats(max_hp=20, attack=10, defense=5, speed=2, crit_chance=0.05)

    monkeypatch.setattr(player.inventory, "get_equipment_stats", mock_get_equipment_stats)

    stats = player.effective_stats
    assert stats.max_hp == player.base_stats.max_hp + 20
    assert stats.attack == player.base_stats.attack + 10
    assert stats.defense == player.base_stats.defense + 5
    assert stats.speed == player.base_stats.speed + 2
    assert stats.crit_chance == pytest.approx(player.base_stats.crit_chance + 0.05)


def test_effective_stats_with_passive():
    player = Player(class_id="warrior")

    def modify_stats_hook(stats: Stats) -> Stats:
        return stats.add(Stats(max_hp=15, attack=8, defense=4, speed=3, crit_chance=0.10))

    passive_ability = Ability(
        id="mock_passive",
        name="Mock Passive",
        description="A mocked passive ability for testing.",
        ability_type=AbilityType.PASSIVE,
        rarity=AbilityRarity.STANDARD,
        modify_stats_hook=modify_stats_hook
    )

    player.abilities.passive.append(passive_ability)

    stats = player.effective_stats
    assert stats.max_hp == player.base_stats.max_hp + 15
    assert stats.attack == player.base_stats.attack + 8
    assert stats.defense == player.base_stats.defense + 4
    assert stats.speed == player.base_stats.speed + 3
    assert stats.crit_chance == pytest.approx(player.base_stats.crit_chance + 0.10)


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


def test_gain_experience_negative_or_zero():
    player = Player(class_id="warrior")
    assert player.experience == 0

    assert not player.gain_experience(0)
    assert player.experience == 0

    assert not player.gain_experience(-10)
    assert player.experience == 0


def test_gain_experience_no_level_up():
    player = Player(class_id="warrior")
    assert player.level == 1
    assert player.experience == 0

    # 50 exp to next level. Let's give less than that.
    # Base multiplier for warrior is 1.0
    assert not player.gain_experience(40)
    assert player.experience == 40
    assert player.level == 1


def test_gain_experience_multiplier():
    player = Player(class_id="warrior")
    # Change multiplier for test
    player.exp_multiplier = 1.5

    assert not player.gain_experience(10)
    # 10 * 1.5 = 15
    assert player.experience == 15


def test_gain_experience_multiple_level_ups():
    player = Player(class_id="warrior")
    assert player.level == 1
    initial_hp = player.max_hp

    # From level 1, calculate exp thresholds for next few levels
    # Lvl 1->2: 50 + 25(0) + 8(0) = 50
    # Lvl 2->3: 50 + 25(1) + 8(1) = 83
    # Total needed for Lvl 3 = 133

    assert player.gain_experience(150)
    assert player.level == 3
    assert player.experience == 150 - 133  # 17


def test_gain_experience_max_level_cap():
    player = Player(class_id="warrior")
    # Artificially set to level 19
    player.level = 19

    # Calculate exp needed for level 19 to 20
    from src.core.math_utils import calculate_exp_threshold
    needed = calculate_exp_threshold(19)
    player.exp_to_next_level = needed
    player.experience = 0

    # Give enough to reach level 20 and overflow greatly
    assert player.gain_experience(needed + 50000)

    assert player.level == 20
    # Experience should be capped at exp_to_next_level when max level is reached
    assert player.experience == player.exp_to_next_level


def test_gain_experience_ability_milestones():
    player = Player(class_id="warrior")

    # At level 1, no milestones
    assert player.pending_ability_choices == []

    # Reach level 4 ("STANDARD")
    player.level = 3
    player.experience = 0
    from src.core.math_utils import calculate_exp_threshold
    needed = calculate_exp_threshold(3)
    player.exp_to_next_level = needed

    player.gain_experience(needed)
    assert player.level == 4
    assert player.pending_ability_choices == ["STANDARD"]

    # Clear and reach level 10 ("EPIC")
    player.pending_ability_choices.clear()
    player.level = 9
    player.experience = 0
    needed = calculate_exp_threshold(9)
    player.exp_to_next_level = needed

    player.gain_experience(needed)
    assert player.level == 10
    assert player.pending_ability_choices == ["EPIC"]

    # Check a level without milestone logic (level 11)
    player.pending_ability_choices.clear()
    player.level = 11
    player._check_ability_milestone()
    assert player.pending_ability_choices == []

    player.level = 8
    player._check_ability_milestone()
    assert player.pending_ability_choices == ["STANDARD"]

    player.level = 20
    player.pending_ability_choices.clear()
    player._check_ability_milestone()
    assert player.pending_ability_choices == ["EPIC"]
