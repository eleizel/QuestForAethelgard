"""Tests for the inventory system, focusing on equipment management."""

import pytest
from src.entities.actor import Stats
from src.systems.inventory import Inventory, EquipmentItem, EquipSlot, Item, MAX_POUCH_SLOTS


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
