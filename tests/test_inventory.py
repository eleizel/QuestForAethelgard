import pytest
from src.systems.inventory import Inventory, ConsumableItem, EquipmentItem, EquipSlot
from src.entities.actor import Actor, Stats

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

    item = ConsumableItem(id="antidote", name="Antidote", description="Cleanses debuffs", heal_amount=0, cleanses_debuffs=True)

    used = item.use(target)

    assert used is True
    assert len(target.statuses) == 0

def test_consumable_use_apply_status():
    """Verify that a consumable item correctly applies a status effect (buff)."""
    stats = Stats(max_hp=100, attack=10, defense=10, speed=10)
    target = Actor("Hero", stats)

    item = ConsumableItem(id="haste_pot", name="Potion of Haste", description="Grants haste", heal_amount=0, applied_status="haste", status_duration=5, status_potency=3)

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

    item = ConsumableItem(id="water", name="Water", description="Just water", heal_amount=0, cleanses_debuffs=False, applied_status=None)

    used = item.use(target)

    assert used is False
