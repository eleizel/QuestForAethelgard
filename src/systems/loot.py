import random

from src.data.items import get_catalog
from src.entities.enemy import EnemyTier
from src.entities.player import Player
from src.systems.inventory import ConsumableItem, EquipmentItem, Item


def get_target_tier_for_floor(floor: int, enemy_tier: EnemyTier = EnemyTier.COMMON) -> int:
    """Determine appropriate equipment tier (1..3) based on floor and encounter severity."""
    if floor <= 6:
        base_tier = 1
    elif floor <= 12:
        base_tier = 2
    else:
        base_tier = 3

    # Elites and Bosses have a small chance to roll a piece of +1 tier gear
    if enemy_tier in (EnemyTier.ELITE, EnemyTier.BOSS) and random.random() < 0.35:
        return min(3, base_tier + 1)
    return base_tier


def filter_equipment_pool(
    catalog: dict[str, Item],
    player: Player,
    target_tier: int,
) -> list[EquipmentItem]:
    """Return valid unequipped gear matching player class and target tier (or falling back to lower tiers)."""
    equipment_pool = [item for item in catalog.values() if isinstance(item, EquipmentItem)]
    equipped_ids = {
        equipped.id
        for equipped in player.inventory.equipment.values()
        if equipped is not None
    }

    # First attempt: exact tier match
    tier_matches = [
        eq for eq in equipment_pool
        if eq.tier == target_tier
        and (eq.required_class is None or eq.required_class == player.class_id)
        and eq.id not in equipped_ids
    ]
    if tier_matches:
        return tier_matches

    # Fallback: any valid tier <= target_tier
    fallback = [
        eq for eq in equipment_pool
        if eq.tier <= target_tier
        and (eq.required_class is None or eq.required_class == player.class_id)
        and eq.id not in equipped_ids
    ]
    if fallback:
        return fallback

    # Ultimate fallback: all valid class gear
    return [
        eq for eq in equipment_pool
        if (eq.required_class is None or eq.required_class == player.class_id)
        and eq.id not in equipped_ids
    ]


def generate_combat_loot(enemy_tier: EnemyTier, floor: int, player: Player) -> list[Item]:
    catalog = get_catalog()

    consumable_pool = [item for item in catalog.values() if isinstance(item, ConsumableItem)]
    target_tier = get_target_tier_for_floor(floor, enemy_tier)
    valid_equip = filter_equipment_pool(catalog, player, target_tier)

    loot: list[Item] = []

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
        # 2-3 guaranteed tier-appropriate equipment pieces + consumables
        num_equip = random.randint(2, 3)
        if valid_equip:
            sample_size = min(num_equip, len(valid_equip))
            loot.extend(random.sample(valid_equip, sample_size))

        num_consumables = random.randint(1, 2)
        if consumable_pool:
            for _ in range(num_consumables):
                loot.append(random.choice(consumable_pool))

    return loot


def generate_merchant_stock(floor: int, player: Player) -> list[tuple[Item, int]]:
    """Generates the merchant's inventory and corresponding prices scaled by floor and tier."""
    catalog = get_catalog()
    stock: list[tuple[Item, int]] = []

    # 1. Consumables
    num_consumables = random.randint(1, 2)
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

    # 2. Equipment (Tier appropriate)
    target_tier = get_target_tier_for_floor(floor)
    valid_equip = filter_equipment_pool(catalog, player, target_tier)

    num_equip = random.randint(2, 3)
    if valid_equip:
        sample_size = min(num_equip, len(valid_equip))
        sampled = random.sample(valid_equip, sample_size)
        for eq in sampled:
            price = max(20, int(eq.gold_value * (1.0 + floor * 0.1)))
            stock.append((eq, price))

    # 3. Rare/Quirky Item
    quirky_ids = ["suspicious_pie", "goblin_cheese_wheel"]
    quirky_id = random.choice(quirky_ids)
    if quirky_id in catalog:
        item = catalog[quirky_id]
        price = max(20, int(item.gold_value * (1.0 + floor * 0.1)))
        if quirky_id == "suspicious_pie":
            price = 45
        stock.append((item, price))

    return stock
