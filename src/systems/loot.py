import random
from src.entities.enemy import EnemyTier
from src.entities.player import Player
from src.systems.inventory import ConsumableItem, EquipmentItem, Item
from src.data.items import get_catalog

def generate_combat_loot(enemy_tier: EnemyTier, floor: int, player: Player) -> list[Item]:
    catalog = get_catalog()

    # Separate into equipment and consumables
    equipment_pool = [item for item in catalog.values() if isinstance(item, EquipmentItem)]
    consumable_pool = [item for item in catalog.values() if isinstance(item, ConsumableItem)]

    # Filter out class-restricted gear that doesn't match
    valid_equip = []
    for eq in equipment_pool:
        if eq.required_class is not None and eq.required_class != player.class_id:
            continue
        # Duplicate prevention (don't offer gear already equipped)
        is_equipped = False
        for equipped_item in player.inventory.equipment.values():
            if equipped_item is not None and equipped_item.id == eq.id:
                is_equipped = True
                break
        if not is_equipped:
            valid_equip.append(eq)

    loot = []

    if enemy_tier == EnemyTier.COMMON:
        if random.random() < 0.40 and consumable_pool:
            loot.append(random.choice(consumable_pool))
        if random.random() < 0.25 and valid_equip:
            loot.append(random.choice(valid_equip))
    elif enemy_tier == EnemyTier.ELITE:
        if consumable_pool:
            loot.append(random.choice(consumable_pool))
        if valid_equip:
            loot.append(random.choice(valid_equip))
    elif enemy_tier == EnemyTier.BOSS:
        # 2-3 guaranteed high tier equipment pieces + consumables
        num_equip = random.randint(2, 3)
        if valid_equip:
            # We can sample without replacement if we have enough items
            sample_size = min(num_equip, len(valid_equip))
            loot.extend(random.sample(valid_equip, sample_size))

        num_consumables = random.randint(1, 2)
        if consumable_pool:
            for _ in range(num_consumables):
                loot.append(random.choice(consumable_pool))

    return loot
