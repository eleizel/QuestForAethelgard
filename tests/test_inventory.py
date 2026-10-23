import pytest
from src.systems.inventory import Inventory, ConsumableItem, EquipmentItem, EquipSlot

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
