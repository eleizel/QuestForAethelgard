import timeit

setup_code = """
from src.systems.inventory import Inventory, EquipmentItem, EquipSlot
from src.entities.actor import Stats

inv = Inventory()
items = []
for slot in EquipSlot:
    item = EquipmentItem(
        id=f"item_{slot.name}",
        name=f"{slot.name} item",
        description="test",
        slot=slot,
        stats_bonus=Stats(max_hp=10, attack=5, defense=2, speed=1, crit_chance=0.01)
    )
    inv.equipment[slot] = item
"""

test_code = """
inv.get_equipment_stats()
"""

# Run it
N = 100000
time_taken = timeit.timeit(stmt=test_code, setup=setup_code, number=N)

print(f"Time taken for {N} calls: {time_taken:.4f} seconds")
