import random

from src.data.items import get_catalog
from src.entities.enemy import EnemyTier
from src.entities.player import Player
from src.systems.inventory import ConsumableItem, EquipmentItem, Item


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


def generate_merchant_stock(floor: int, player: Player) -> list[tuple[Item, int]]:
    """Generates the merchant's inventory and corresponding prices."""
    catalog = get_catalog()
    stock: list[tuple[Item, int]] = []

    # 1. Consumables
    consumable_pool = [item for item in catalog.values() if isinstance(item, ConsumableItem)]
    num_consumables = random.randint(1, 2)

    # Try to include health potions or stat elixirs
    for _ in range(num_consumables):
        item_id = random.choice([
            "health_potion", "major_health_flask",
            "elixir_vitality_minor", "elixir_strength_minor", "elixir_iron_minor", "elixir_celerity_minor",
            "elixir_precision_minor",
            "elixir_vitality_greater", "elixir_strength_greater", "elixir_iron_greater", "elixir_celerity_greater",
            "elixir_precision_greater",
            "elixir_of_quickness"
        ])
        if item_id in catalog:
            item = catalog[item_id]
            price = max(20, int(item.gold_value * (1.0 + floor * 0.1)))
            if "minor" in item_id or "greater" in item_id or "quickness" in item_id:
                price = random.randint(75, 120)
            elif item_id == "health_potion":
                price = 25
            elif item_id == "major_health_flask":
                price = 55
            stock.append((item, price))

    # 2. Equipment
    equipment_pool = [item for item in catalog.values() if isinstance(item, EquipmentItem)]
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

    num_equip = random.randint(2, 3)
    if valid_equip:
        sample_size = min(num_equip, len(valid_equip))
        sampled = random.sample(valid_equip, sample_size)
        for eq in sampled:
            price = max(20, int(eq.gold_value * (1.0 + floor * 0.1)))
            stock.append((eq, price))

    # 3. Rare/Quirky Item
    quirky_ids = ["suspicious_pie", "goblin_cheese_wheel", "tax_audit_scroll"]
    quirky_id = random.choice(quirky_ids)
    if quirky_id in catalog:
        item = catalog[quirky_id]
        price = max(20, int(item.gold_value * (1.0 + floor * 0.1)))
        if quirky_id == "suspicious_pie":
            price = 45
        stock.append((item, price))

    return stock
