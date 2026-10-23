from typing import Final
from src.systems.inventory import ConsumableItem, EquipmentItem, EquipSlot, Item, WeaponType
from src.entities.actor import Stats

ITEM_CATALOG: Final[dict[str, Item]] = {
    # Warrior Starter Gear
    "bronze_sword": EquipmentItem(
        id="bronze_sword", name="Bronze Blade", description="A dependable starting sword.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.ONE_HANDED,
        stats_bonus=Stats(max_hp=0, attack=1, defense=0, speed=0, crit_chance=0.05)
    ),
    "bronze_shield": EquipmentItem(
        id="bronze_shield", name="Bronze Shield", description="A dependable starting shield.",
        slot=EquipSlot.OFF_HAND, weapon_type=WeaponType.SHIELD,
        stats_bonus=Stats(max_hp=1, attack=0, defense=1, speed=0, crit_chance=0.0)
    ),
    "bronze_helmet": EquipmentItem(
        id="bronze_helmet", name="Bronze Helmet", description="A dependable starting helmet.",
        slot=EquipSlot.HEAD, stats_bonus=Stats(max_hp=0, attack=0, defense=1, speed=0, crit_chance=0.05)
    ),
    "bronze_chestplate": EquipmentItem(
        id="bronze_chestplate", name="Bronze Chestplate", description="A dependable starting chestplate.",
        slot=EquipSlot.CHEST, stats_bonus=Stats(max_hp=1, attack=0, defense=1, speed=0, crit_chance=0.0)
    ),
    "leather_gloves": EquipmentItem(
        id="leather_gloves", name="Leather Gloves", description="A pair of dependable starting gloves.",
        slot=EquipSlot.HANDS, stats_bonus=Stats(max_hp=0, attack=0, defense=0, speed=0, crit_chance=0.05)
    ),
    "leather_pants": EquipmentItem(
        id="leather_pants", name="Leather Pants", description="A pair of dependable starting pants.",
        slot=EquipSlot.LEGS, stats_bonus=Stats(max_hp=0, attack=0, defense=0, speed=1, crit_chance=0.0)
    ),
    "health_potion": ConsumableItem(
        id="health_potion", name="Health Draught", description="Restores 35 hit points.", heal_amount=35
    ),

    # Consumables
    "major_health_flask": ConsumableItem(
        id="major_health_flask", name="Major Health Flask", description="Restores 80 hit points.", heal_amount=80
    ),
    # Quickness elixir needs custom handling or an empty Item if it's just meant for later mechanics,
    # but requirement states (+3 SPD). Let's make it a consumable that heals and maybe later we'll add buffing.
    # For now, it's just a Consumable. We don't have buffs yet.
    "elixir_of_quickness": ConsumableItem(
        id="elixir_of_quickness", name="Elixir of Quickness", description="Restores 10 hit points. (+3 SPD)", heal_amount=10
    ),

    # Armor - Shoulders & Waist
    "leather_mantle": EquipmentItem(
        id="leather_mantle", name="Leather Mantle", description="Basic shoulder protection.",
        slot=EquipSlot.SHOULDERS, stats_bonus=Stats(max_hp=5, attack=0, defense=1, speed=1, crit_chance=0.0)
    ),
    "bronze_pauldrons": EquipmentItem(
        id="bronze_pauldrons", name="Bronze Pauldrons", description="Heavy shoulder guards.",
        slot=EquipSlot.SHOULDERS, stats_bonus=Stats(max_hp=10, attack=0, defense=3, speed=0, crit_chance=0.0)
    ),
    "leather_belt": EquipmentItem(
        id="leather_belt", name="Leather Belt", description="A simple waist sash.",
        slot=EquipSlot.WAIST, stats_bonus=Stats(max_hp=5, attack=0, defense=0, speed=2, crit_chance=0.0)
    ),
    "iron_girdle": EquipmentItem(
        id="iron_girdle", name="Iron Girdle", description="A sturdy iron waist guard.",
        slot=EquipSlot.WAIST, stats_bonus=Stats(max_hp=15, attack=0, defense=4, speed=0, crit_chance=0.0)
    ),

    # Rogue/Mage Weapons
    "bandit_dagger": EquipmentItem(
        id="bandit_dagger", name="Bandit Dagger", description="A swift, sharp blade.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.ONE_HANDED, required_class="rogue",
        stats_bonus=Stats(max_hp=0, attack=4, defense=0, speed=5, crit_chance=0.1)
    ),
    "apprentice_wand": EquipmentItem(
        id="apprentice_wand", name="Apprentice Wand", description="A basic magical focus.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.ONE_HANDED, required_class="mage",
        stats_bonus=Stats(max_hp=0, attack=6, defense=0, speed=2, crit_chance=0.0)
    ),
    "arcane_grimoire": EquipmentItem(
        id="arcane_grimoire", name="Arcane Grimoire", description="A tome of spells.",
        slot=EquipSlot.OFF_HAND, weapon_type=WeaponType.FOCUS, required_class="mage",
        stats_bonus=Stats(max_hp=0, attack=3, defense=0, speed=0, crit_chance=0.05)
    ),
    "staff_of_embers": EquipmentItem(
        id="staff_of_embers", name="Staff of Embers", description="A glowing two-handed staff.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.TWO_HANDED, required_class="mage",
        stats_bonus=Stats(max_hp=0, attack=12, defense=0, speed=1, crit_chance=0.05)
    ),
    "iron_claymore": EquipmentItem(
        id="iron_claymore", name="Iron Claymore", description="A massive two-handed sword.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.TWO_HANDED, required_class="warrior",
        stats_bonus=Stats(max_hp=0, attack=10, defense=0, speed=0, crit_chance=0.0)
    )
}

def get_item(item_id: str) -> Item | None:
    return ITEM_CATALOG.get(item_id)

def get_catalog() -> dict[str, Item]:
    return ITEM_CATALOG.copy()
