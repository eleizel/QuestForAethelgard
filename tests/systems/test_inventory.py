"""Tests for the inventory system, focusing on equipment management."""

import pytest

from src.entities.player import Player
from src.entities.actor import Actor, Stats
from src.systems.inventory import Inventory, ConsumableItem, EquipmentItem, EquipSlot, Item, MAX_POUCH_SLOTS


def test_get_equipment_stats_empty():
    """Test get_equipment_stats returns zero stats when empty."""
    inventory = Inventory()
    stats = inventory.get_equipment_stats()
    assert stats.max_hp == 0
    assert stats.attack == 0
    assert stats.defense == 0
    assert stats.speed == 0
    assert stats.crit_chance == 0.0


def test_get_equipment_stats_combined():
    """Test get_equipment_stats aggregates bonuses from multiple items."""
    inventory = Inventory()
    helm = EquipmentItem(
        id="helm_1", name="Iron Helm", description="A helm",
        slot=EquipSlot.HEAD, stats_bonus=Stats(max_hp=10, attack=0, defense=5, speed=0, crit_chance=0.0)
    )
    sword = EquipmentItem(
        id="sword_1", name="Iron Sword", description="A sword",
        slot=EquipSlot.MAIN_HAND, stats_bonus=Stats(max_hp=0, attack=15, defense=0, speed=2, crit_chance=0.05)
    )

    inventory.equip(helm)
    inventory.equip(sword)

    stats = inventory.get_equipment_stats()
    assert stats.max_hp == 10
    assert stats.attack == 15
    assert stats.defense == 5
    assert stats.speed == 3  # (max(1, 0+0) + 2) -> max(1, 1 + 2) == 3 because of max(1) and initial 0 speed in Stats() defaults to 1.
    assert stats.crit_chance == 0.05


def test_equip_empty_slot():
    """Test equipping an item to an empty slot returns None."""
    inventory = Inventory()
    sword = EquipmentItem(id="s1", name="Sword", description="...", slot=EquipSlot.MAIN_HAND)

    previous = inventory.equip(sword)

    assert previous is None
    assert inventory.equipment[EquipSlot.MAIN_HAND] is sword


def test_equip_occupied_slot():
    """Test equipping an item to an occupied slot returns the previous item."""
    inventory = Inventory()
    sword1 = EquipmentItem(id="s1", name="Sword 1", description="...", slot=EquipSlot.MAIN_HAND)
    sword2 = EquipmentItem(id="s2", name="Sword 2", description="...", slot=EquipSlot.MAIN_HAND)

    inventory.equip(sword1)
    previous = inventory.equip(sword2)

    assert previous is sword1
    assert inventory.equipment[EquipSlot.MAIN_HAND] is sword2


def test_unequip_success_pouch_space():
    """Test unequipping an item when the pouch has space adds it to pouch and returns it."""
    inventory = Inventory()
    sword = EquipmentItem(id="s1", name="Sword", description="...", slot=EquipSlot.MAIN_HAND)
    inventory.equip(sword)

    # Pre-condition: pouch is empty
    assert len(inventory.pouch) == 0

    unequipped = inventory.unequip(EquipSlot.MAIN_HAND)

    assert unequipped is sword
    assert inventory.equipment[EquipSlot.MAIN_HAND] is None
    assert len(inventory.pouch) == 1
    assert inventory.pouch[0] is sword


def test_unequip_failure_pouch_full():
    """Test unequipping fails if the pouch is full; item stays equipped."""
    inventory = Inventory()
    sword = EquipmentItem(id="s1", name="Sword", description="...", slot=EquipSlot.MAIN_HAND)
    inventory.equip(sword)

    # Fill pouch
    for i in range(MAX_POUCH_SLOTS):
        inventory.add_to_pouch(Item(id=f"i{i}", name="junk", description="junk"))

    assert len(inventory.pouch) == MAX_POUCH_SLOTS

    unequipped = inventory.unequip(EquipSlot.MAIN_HAND)

    assert unequipped is None
    assert inventory.equipment[EquipSlot.MAIN_HAND] is sword
    assert len(inventory.pouch) == MAX_POUCH_SLOTS


def test_unequip_empty_slot():
    """Test unequipping an empty slot returns None."""
    inventory = Inventory()

    unequipped = inventory.unequip(EquipSlot.MAIN_HAND)

    assert unequipped is None
    assert inventory.equipment[EquipSlot.MAIN_HAND] is None


def test_add_to_pouch_success():
    """Test adding an item to the pouch when there is space."""
    inventory = Inventory()
    item = Item(id="test_item", name="Test Item", description="A test item")

    success = inventory.add_to_pouch(item)

    assert success is True
    assert len(inventory.pouch) == 1
    assert inventory.pouch[0] is item


def test_add_to_pouch_full():
    """Test adding an item fails when the pouch is full."""
    inventory = Inventory()

    # Fill pouch
    for i in range(MAX_POUCH_SLOTS):
        inventory.add_to_pouch(Item(id=f"i{i}", name="junk", description="junk"))

    assert len(inventory.pouch) == MAX_POUCH_SLOTS

    overflow_item = Item(id="overflow", name="Overflow Item", description="Won't fit")
    success = inventory.add_to_pouch(overflow_item)

    assert success is False
    assert len(inventory.pouch) == MAX_POUCH_SLOTS
    assert overflow_item not in inventory.pouch


def test_remove_from_pouch_success():
    """Test removing an item from a valid pouch index."""
    inventory = Inventory()
    item1 = Item(id="test1", name="Test 1", description="1")
    item2 = Item(id="test2", name="Test 2", description="2")
    inventory.add_to_pouch(item1)
    inventory.add_to_pouch(item2)

    removed = inventory.remove_from_pouch(0)

    assert removed is item1
    assert len(inventory.pouch) == 1
    assert inventory.pouch[0] is item2


def test_remove_from_pouch_invalid_index():
    """Test removing an item from an invalid pouch index returns None."""
    inventory = Inventory()
    item = Item(id="test1", name="Test 1", description="1")
    inventory.add_to_pouch(item)

    # Negative index
    removed_neg = inventory.remove_from_pouch(-1)
    assert removed_neg is None
    assert len(inventory.pouch) == 1

    # Out of bounds index
    removed_out = inventory.remove_from_pouch(1)
    assert removed_out is None
    assert len(inventory.pouch) == 1


def test_drop_from_pouch_success():
    """Test dropping an item from a valid pouch index."""
    inventory = Inventory()
    item = Item(id="test1", name="Test 1", description="1")
    inventory.add_to_pouch(item)

    success, message = inventory.drop_from_pouch(0)

    assert success is True
    assert message == "Discarded Test 1."
    assert len(inventory.pouch) == 0


def test_drop_from_pouch_invalid_index():
    """Test dropping an item from an invalid pouch index."""
    inventory = Inventory()
    item = Item(id="test1", name="Test 1", description="1")
    inventory.add_to_pouch(item)

    success, message = inventory.drop_from_pouch(5)

    assert success is False
    assert message == "Invalid pouch index."
    assert len(inventory.pouch) == 1


def test_assign_to_belt_success():
    """Verify a consumable item can be assigned to an empty belt slot."""
    inv = Inventory()
    item = ConsumableItem(id="pot_1", name="Health Potion", description="Heals HP", heal_amount=25)

    # Add to pouch first
    inv.add_to_pouch(item)

    # Assign from pouch (index 0) to belt (index 0)
    assert inv.assign_to_belt(0, 0) is True

    # Verify the item is on the belt
    assert inv.belt[0] == item

    # Verify the item was removed from the pouch
    assert len(inv.pouch) == 0


def test_assign_to_belt_swap():
    """Verify a consumable item on the belt can be swapped with another from the pouch."""
    inv = Inventory()
    item1 = ConsumableItem(id="pot_1", name="Health Potion", description="Heals HP", heal_amount=25)
    item2 = ConsumableItem(id="pot_2", name="Greater Potion", description="Heals HP", heal_amount=50)

    # Setup: item1 is on the belt, item2 is in the pouch
    inv.add_to_pouch(item1)
    inv.assign_to_belt(0, 0)
    inv.add_to_pouch(item2)

    # Swap item2 (pouch index 0) with item1 (belt index 0)
    assert inv.assign_to_belt(0, 0) is True

    # Verify item2 is on the belt
    assert inv.belt[0] == item2

    # Verify item1 is back in the pouch
    assert len(inv.pouch) == 1
    assert inv.pouch[0] == item1


def test_assign_to_belt_invalid_belt_index():
    """Verify returning False when belt_index is out of bounds."""
    inv = Inventory()
    item = ConsumableItem(id="pot_1", name="Health Potion", description="Heals HP", heal_amount=25)
    inv.add_to_pouch(item)

    # belt_index < 0
    assert inv.assign_to_belt(0, -1) is False
    assert len(inv.pouch) == 1

    # belt_index >= MAX_BELT_SLOTS (3)
    assert inv.assign_to_belt(0, 3) is False
    assert len(inv.pouch) == 1


def test_assign_to_belt_invalid_pouch_index():
    """Verify returning False when pouch_index is out of bounds."""
    inv = Inventory()
    item = ConsumableItem(id="pot_1", name="Health Potion", description="Heals HP", heal_amount=25)
    inv.add_to_pouch(item)

    # pouch_index < 0
    assert inv.assign_to_belt(-1, 0) is False
    assert inv.belt[0] is None

    # pouch_index >= len(pouch)
    assert inv.assign_to_belt(1, 0) is False
    assert inv.belt[0] is None


def test_assign_to_belt_non_consumable():
    """Verify returning False when trying to assign an EquipmentItem to the belt."""
    inv = Inventory()
    sword = EquipmentItem(id="sword_1", name="Iron Sword", description="A basic sword", slot=EquipSlot.MAIN_HAND)

    # Add equipment to pouch
    inv.add_to_pouch(sword)

    # Try to assign to belt
    assert inv.assign_to_belt(0, 0) is False

    # Verify it was not moved
    assert inv.belt[0] is None
    assert len(inv.pouch) == 1
    assert inv.pouch[0] == sword


def test_consumable_use_heal():
    """Verify that a consumable item correctly heals the target."""
    stats = Stats(max_hp=100, attack=10, defense=10, speed=10)
    target = Actor("Hero", stats)
    target.current_hp = 50  # Missing 50 HP

    item = ConsumableItem(id="pot_1", name="Health Potion", description="Heals HP", heal_amount=25)

    used = item.use(target)

    assert used is True
    assert target.current_hp == 75


def test_consumable_use_dead_target():
    """Verify that a consumable item cannot be used on a dead target."""
    stats = Stats(max_hp=100, attack=10, defense=10, speed=10)
    target = Actor("Hero", stats)
    target.current_hp = 0  # Target is dead

    item = ConsumableItem(id="pot_1", name="Health Potion", description="Heals HP", heal_amount=25)

    used = item.use(target)

    assert used is False
    assert target.current_hp == 0


def test_consumable_use_cleanse():
    """Verify that a consumable item correctly cleanses debuffs."""
    stats = Stats(max_hp=100, attack=10, defense=10, speed=10)
    target = Actor("Hero", stats)

    from src.systems.status import create_poison
    poison = create_poison(duration=3, potency=2)
    target.apply_status(poison)

    assert len(target.statuses) == 1

    item = ConsumableItem(id="antidote", name="Antidote", description="Cleanses debuffs", heal_amount=0,
                          cleanses_debuffs=True)

    used = item.use(target)

    assert used is True
    assert len(target.statuses) == 0


def test_consumable_use_apply_status():
    """Verify that a consumable item correctly applies a status effect (buff)."""
    stats = Stats(max_hp=100, attack=10, defense=10, speed=10)
    target = Actor("Hero", stats)

    item = ConsumableItem(id="haste_pot", name="Potion of Haste", description="Grants haste", heal_amount=0,
                          applied_status="haste", status_duration=5, status_potency=3)

    used = item.use(target)

    assert used is True
    assert len(target.statuses) == 1
    assert target.statuses[0].id == "haste"
    assert target.statuses[0].duration == 5
    assert target.statuses[0].potency == 3


def test_consumable_use_no_effect():
    """Verify that a consumable item without effects returns False when used."""
    stats = Stats(max_hp=100, attack=10, defense=10, speed=10)
    target = Actor("Hero", stats)

    item = ConsumableItem(id="water", name="Water", description="Just water", heal_amount=0, cleanses_debuffs=False,
                          applied_status=None)

    used = item.use(target)

    assert used is False


@pytest.mark.parametrize(
    ("parent_class", "advanced_class"),
    [
        ("warrior", "paladin"),
        ("warrior", "berserker"),
        ("rogue", "venomancer"),
        ("rogue", "duelist"),
        ("mage", "archmage"),
        ("mage", "warlock"),
    ],
)
def test_promoted_class_can_equip_parent_class_gear(parent_class, advanced_class):
    player = Player(class_id=advanced_class)
    inventory = Inventory()
    parent_gear = EquipmentItem(
        id=f"{parent_class}_gear",
        name="Parent Class Gear",
        description="",
        slot=EquipSlot.MAIN_HAND,
        required_class=parent_class,
    )
    inventory.add_to_pouch(parent_gear)

    success, _message = inventory.equip_from_pouch(0, player)

    assert success is True
    assert inventory.equipment[EquipSlot.MAIN_HAND] is parent_gear


@pytest.mark.parametrize(
    ("advanced_class", "unrelated_class"),
    [
        ("paladin", "rogue"),
        ("berserker", "mage"),
        ("venomancer", "warrior"),
        ("duelist", "mage"),
        ("archmage", "rogue"),
        ("warlock", "warrior"),
    ],
)
def test_promoted_class_cannot_equip_unrelated_class_gear(advanced_class, unrelated_class):
    player = Player(class_id=advanced_class)
    inventory = Inventory()
    unrelated_gear = EquipmentItem(
        id=f"{unrelated_class}_gear",
        name="Unrelated Class Gear",
        description="",
        slot=EquipSlot.MAIN_HAND,
        required_class=unrelated_class,
    )

    can_equip, _message = inventory.can_equip(unrelated_gear, player)

    assert can_equip is False
