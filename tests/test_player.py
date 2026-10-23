import pytest
from src.entities.player import Player, ClassPromotion, PROMOTION_STAT_BONUSES
from src.entities.actor import Stats



def test_available_promotions_novice_underleveled():
    player = Player()
    player.promotion = ClassPromotion.NOVICE # Explicitly set for testing
    # Default level is 1
    assert player.promotion == ClassPromotion.NOVICE
    assert player.level == 1
    assert player.available_promotions() == []

def test_available_promotions_novice_leveled():
    player = Player()
    player.promotion = ClassPromotion.NOVICE # Explicitly set for testing
    player.level = 5
    assert player.promotion == ClassPromotion.NOVICE
    promotions = player.available_promotions()
    assert ClassPromotion.WARRIOR in promotions
    assert ClassPromotion.MAGE in promotions
    assert ClassPromotion.ROGUE in promotions
    assert len(promotions) == 3

def test_available_promotions_tier1_underleveled():
    player = Player()
    player.promotion = ClassPromotion.WARRIOR
    player.level = 14
    assert player.available_promotions() == []

def test_available_promotions_tier1_leveled():
    player = Player()
    player.promotion = ClassPromotion.WARRIOR
    player.level = 15
    promotions = player.available_promotions()
    assert ClassPromotion.PALADIN in promotions
    assert len(promotions) == 1

def test_available_promotions_max_tier():
    player = Player()
    player.promotion = ClassPromotion.PALADIN
    player.level = 20
    assert player.available_promotions() == []

def test_promote_ineligible_class():
    player = Player()
    player.promotion = ClassPromotion.NOVICE
    player.level = 5
    # Novice cannot promote directly to Paladin
    assert not player.promote(ClassPromotion.PALADIN)
    assert player.promotion == ClassPromotion.NOVICE

def test_promote_underleveled():
    player = Player()
    player.promotion = ClassPromotion.NOVICE
    player.level = 4
    # Novice under level 5 cannot promote to Warrior
    assert not player.promote(ClassPromotion.WARRIOR)
    assert player.promotion == ClassPromotion.NOVICE

def test_promote_success():
    player = Player()
    player.promotion = ClassPromotion.NOVICE
    player.level = 5

    # Store initial stats to compare against bonuses
    initial_base_stats = player.base_stats

    # Promote to WARRIOR
    assert player.promote(ClassPromotion.WARRIOR)

    assert player.promotion == ClassPromotion.WARRIOR

    # Check stat bonuses applied
    bonus = PROMOTION_STAT_BONUSES[ClassPromotion.WARRIOR]

    expected_stats = initial_base_stats.add(bonus)
    assert player.base_stats.max_hp == expected_stats.max_hp
    assert player.base_stats.attack == expected_stats.attack
    assert player.base_stats.defense == expected_stats.defense
    assert player.base_stats.speed == expected_stats.speed
    assert player.base_stats.crit_chance == expected_stats.crit_chance

    # HP is restored to max
    assert player.current_hp == player.max_hp

def test_promote_no_bonus_fallback():
    # If a class doesn't have a bonus in PROMOTION_STAT_BONUSES, it shouldn't crash
    # and should use empty stats.
    # Currently all classes have bonuses in PROMOTION_STAT_BONUSES, but let's test
    # the fallback path by modifying the map temporarily.

    player = Player()
    player.promotion = ClassPromotion.NOVICE
    player.level = 5

    # We can mock available promotions to allow promoting to NOVICE to trigger fallback
    # or just trust the standard logic. Let's do it cleanly by temporarily removing a bonus

    original_bonus = PROMOTION_STAT_BONUSES.pop(ClassPromotion.WARRIOR, None)
    try:
        initial_base_stats = player.base_stats
        assert player.promote(ClassPromotion.WARRIOR)
        assert player.promotion == ClassPromotion.WARRIOR

        # Base stats should not have changed
        assert player.base_stats.max_hp == initial_base_stats.max_hp
        assert player.base_stats.attack == initial_base_stats.attack
    finally:
        if original_bonus:
            PROMOTION_STAT_BONUSES[ClassPromotion.WARRIOR] = original_bonus

def test_gain_experience_zero_or_negative():
    player = Player()
    initial_exp = player.experience
    initial_level = player.level

    assert not player.gain_experience(0)
    assert player.experience == initial_exp
    assert player.level == initial_level

    assert not player.gain_experience(-10)
    assert player.experience == initial_exp
    assert player.level == initial_level

def test_gain_experience_no_level_up():
    player = Player()
    initial_level = player.level

    assert not player.gain_experience(10)
    assert player.experience == 10
    assert player.level == initial_level

def test_gain_experience_single_level_up():
    player = Player()
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
    # Next level exp calculation: int(50 + 25 * (2 - 1) + 8 * (2 - 1) ** 2) = 50 + 25 + 8 = 83
    assert player.exp_to_next_level == 83

    # Check stat bonuses
    assert player.max_hp == initial_max_hp + 15
    assert player.base_stats.attack == initial_attack + 2
    assert player.base_stats.defense == initial_defense + 2
    assert player.base_stats.speed == initial_speed + 1
    assert player.base_stats.crit_chance == pytest.approx(initial_crit + 0.005)

    # Check HP restoration
    assert player.current_hp == player.max_hp

    # Check stat points
    assert player.stat_points == initial_stat_points + 2

def test_gain_experience_multiple_level_ups():
    player = Player()
    # Level 1 to 2 requires 50
    # Level 2 to 3 requires 83 (total 133)
    # Level 3 to 4 requires int(50 + 25*2 + 8*4) = 50 + 50 + 32 = 132 (total 265)
    assert player.gain_experience(140)
    assert player.level == 3
    assert player.experience == 7 # 140 - 50 - 83 = 7

def test_gain_experience_max_level():
    player = Player()
    player.level = 19
    player.experience = 0
    # Level 19 to 20 requires: 50 + 25*18 + 8*(18**2) = 50 + 450 + 8*324 = 500 + 2592 = 3092
    assert player.exp_to_next_level == 50 # Default initialized, let's trigger update
    # Need to manually set the exp_to_next_level to the right value as if the player just reached level 19
    player.exp_to_next_level = int(50 + 25 * 18 + 8 * 18 ** 2) # 3092

    # Give enough exp to reach 20 and overflow
    assert player.gain_experience(4000)
    assert player.level == 20
    # The code caps experience to exp_to_next_level *after* exp_to_next_level has been updated for level 20
    # exp_to_next_level at level 20 = 50 + 25*(20-1) + 8*(20-1)**2 = 50 + 475 + 8*361 = 525 + 2888 = 3413
    # Wait, the code for cap is:
    # if self.level == 20 and self.experience > self.exp_to_next_level:
    #     self.experience = self.exp_to_next_level
    # Since we gave 4000 exp, experience goes to 4000. It levels to 20, exp becomes 4000 - 3092 = 908.
    # The new exp_to_next_level is 3413.
    # 908 is not > 3413, so experience remains 908!
    assert player.experience == 908
    assert player.exp_to_next_level == 3413

    # Now let's try to gain past the cap
    assert not player.gain_experience(4000) # Doesn't level up
    assert player.level == 20
    assert player.experience == player.exp_to_next_level
    assert player.experience == 3413

    # Giving more exp at level 20 shouldn't level up
    assert not player.gain_experience(100)
    assert player.level == 20
    assert player.experience == player.exp_to_next_level

def test_gain_experience_milestones():
    player = Player()

    # Standard milestone at level 4
    # Set to level 3, exp 0
    player.level = 3
    player.exp_to_next_level = int(50 + 25 * 2 + 8 * 2 ** 2) # 132
    assert player.gain_experience(132)
    assert player.level == 4
    assert "STANDARD" in player.pending_ability_choices

    # Epic milestone at level 10
    player.level = 9
    player.exp_to_next_level = int(50 + 25 * 8 + 8 * 8 ** 2) # 50 + 200 + 512 = 762
    assert player.gain_experience(762)
    assert player.level == 10
    assert "EPIC" in player.pending_ability_choices

def test_gain_experience_multiplier():
    player = Player()
    player.exp_multiplier = 1.5

    # 34 * 1.5 = 51 > 50 (level up)
    assert player.gain_experience(34)
    assert player.level == 2
    assert player.experience == 1 # 51 - 50 = 1
