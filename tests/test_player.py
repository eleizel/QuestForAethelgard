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
