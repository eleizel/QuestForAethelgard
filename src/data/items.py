"""Comprehensive Item Catalog for Quest for Aethelgard.

Includes:
- Starter kits for Warrior, Rogue, and Mage
- Permanent stat-enhancing elixirs (+1/+3 stats, +10/+25 HP)
- Curated progression tiers (Common, Uncommon, Rare, Epic, Legendary)
- Exactly two Legendaries per archetype (1 weapon + 1 armor piece)
- Class-restricted gear for Warrior, Rogue, and Mage
- Universal/Generic gear and humorous dungeon oddities
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from src.entities.actor import Actor, Stats
from src.systems.inventory import ConsumableItem, EquipSlot, EquipmentItem, Item, WeaponType


@dataclass
class StatPotion(ConsumableItem):
    """Consumable that permanently increases an actor's base attributes upon consumption."""

    stat_bonus: Stats = field(default_factory=lambda: Stats(0, 0, 0, 0, 0.0))

    def use(self, target: Actor) -> bool:
        if not target.is_alive:
            return False
        if self.heal_amount > 0:
            target.heal(self.heal_amount)
        # Apply permanent increase to base stats
        target.base_stats = target.base_stats.add(self.stat_bonus)
        if self.stat_bonus.max_hp > 0:
            target.current_hp = min(target.max_hp, target.current_hp + self.stat_bonus.max_hp)
        return True


ITEM_CATALOG: Final[dict[str, Item]] = {
    # =========================================================================
    # 1. WARRIOR STARTER KIT (Preserved)
    # =========================================================================
    "bronze_sword": EquipmentItem(
        id="bronze_sword", name="Bronze Blade", description="A dependable starting sword.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.ONE_HANDED,
        stats_bonus=Stats(max_hp=0, attack=1, defense=0, speed=0, crit_chance=0.05),
    ),
    "bronze_shield": EquipmentItem(
        id="bronze_shield", name="Bronze Shield", description="A dependable starting shield.",
        slot=EquipSlot.OFF_HAND, weapon_type=WeaponType.SHIELD,
        stats_bonus=Stats(max_hp=1, attack=0, defense=1, speed=0, crit_chance=0.0),
    ),
    "bronze_helmet": EquipmentItem(
        id="bronze_helmet", name="Bronze Helmet", description="A dependable starting helmet.",
        slot=EquipSlot.HEAD, stats_bonus=Stats(max_hp=0, attack=0, defense=1, speed=0, crit_chance=0.05),
    ),
    "bronze_chestplate": EquipmentItem(
        id="bronze_chestplate", name="Bronze Chestplate", description="A dependable starting chestplate.",
        slot=EquipSlot.CHEST, stats_bonus=Stats(max_hp=1, attack=0, defense=1, speed=0, crit_chance=0.0),
    ),
    "leather_gloves": EquipmentItem(
        id="leather_gloves", name="Leather Gloves", description="A pair of dependable starting gloves.",
        slot=EquipSlot.HANDS, stats_bonus=Stats(max_hp=0, attack=0, defense=0, speed=0, crit_chance=0.05),
    ),
    "leather_pants": EquipmentItem(
        id="leather_pants", name="Leather Pants", description="A pair of dependable starting pants.",
        slot=EquipSlot.LEGS, stats_bonus=Stats(max_hp=0, attack=0, defense=0, speed=1, crit_chance=0.0),
    ),

    # =========================================================================
    # 2. ROGUE STARTER KIT
    # =========================================================================
    "worn_dagger": EquipmentItem(
        id="worn_dagger", name="Worn Dagger", description="A light, well-balanced blade showing signs of frequent use.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.ONE_HANDED, required_class="rogue",
        stats_bonus=Stats(max_hp=0, attack=2, defense=0, speed=1, crit_chance=0.06),
    ),
    "rusty_parrying_dirk": EquipmentItem(
        id="rusty_parrying_dirk", name="Parrying Dirk", description="A notched off-hand dagger meant to deflect thrusts and riposte.",
        slot=EquipSlot.OFF_HAND, weapon_type=WeaponType.ONE_HANDED, required_class="rogue",
        stats_bonus=Stats(max_hp=0, attack=1, defense=1, speed=1, crit_chance=0.04),
    ),
    "shadow_cowl": EquipmentItem(
        id="shadow_cowl", name="Rogue's Cowl", description="A simple dark linen hood that obscures facial features.",
        slot=EquipSlot.HEAD, required_class="rogue",
        stats_bonus=Stats(max_hp=1, attack=0, defense=1, speed=1, crit_chance=0.03),
    ),
    "padded_leather_vest": EquipmentItem(
        id="padded_leather_vest", name="Padded Leather Vest", description="Light cuirass made of boiled leather with quiet stitching.",
        slot=EquipSlot.CHEST, required_class="rogue",
        stats_bonus=Stats(max_hp=2, attack=0, defense=1, speed=1, crit_chance=0.02),
    ),
    "cutpurse_gloves": EquipmentItem(
        id="cutpurse_gloves", name="Cutpurse Gloves", description="Fingerless suede gloves granting nimble finger dexterity.",
        slot=EquipSlot.HANDS, required_class="rogue",
        stats_bonus=Stats(max_hp=0, attack=1, defense=0, speed=1, crit_chance=0.05),
    ),
    "rogue_breeches": EquipmentItem(
        id="rogue_breeches", name="Stalker Breeches", description="Flexible trousers allowing for silent and low movement.",
        slot=EquipSlot.LEGS, required_class="rogue",
        stats_bonus=Stats(max_hp=0, attack=0, defense=0, speed=2, crit_chance=0.03),
    ),

    # =========================================================================
    # 3. MAGE STARTER KIT
    # =========================================================================
    "gnarled_wand": EquipmentItem(
        id="gnarled_wand", name="Gnarled Wand", description="A simple yew branch vibrating faintly with ambient arcane hum.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.ONE_HANDED, required_class="mage",
        stats_bonus=Stats(max_hp=0, attack=3, defense=0, speed=1, crit_chance=0.02),
    ),
    "tattered_grimoire": EquipmentItem(
        id="tattered_grimoire", name="Tattered Grimoire", description="A battered parchment notebook filled with handwritten basic cantrips.",
        slot=EquipSlot.OFF_HAND, weapon_type=WeaponType.FOCUS, required_class="mage",
        stats_bonus=Stats(max_hp=1, attack=1, defense=1, speed=0, crit_chance=0.03),
    ),
    "apprentice_cowl": EquipmentItem(
        id="apprentice_cowl", name="Novice Cowl", description="A soft felt hood steeped in the scent of candle wax and brimstone.",
        slot=EquipSlot.HEAD, required_class="mage",
        stats_bonus=Stats(max_hp=2, attack=1, defense=0, speed=0, crit_chance=0.03),
    ),
    "apprentice_robes": EquipmentItem(
        id="apprentice_robes", name="Apprentice Robes", description="Simple indigo academy vestments hemmed with protective silver thread.",
        slot=EquipSlot.CHEST, required_class="mage",
        stats_bonus=Stats(max_hp=3, attack=1, defense=1, speed=0, crit_chance=0.0),
    ),
    "cloth_handwraps": EquipmentItem(
        id="cloth_handwraps", name="Mana Wraps", description="Linen bandages inscribed with runic seals to prevent magical backlash.",
        slot=EquipSlot.HANDS, required_class="mage",
        stats_bonus=Stats(max_hp=0, attack=1, defense=0, speed=1, crit_chance=0.02),
    ),
    "woven_pantaloons": EquipmentItem(
        id="woven_pantaloons", name="Woven Pantaloons", description="Comfortable scholar breeches designed for long hours of dungeon study.",
        slot=EquipSlot.LEGS, required_class="mage",
        stats_bonus=Stats(max_hp=1, attack=0, defense=1, speed=1, crit_chance=0.0),
    ),

    # =========================================================================
    # 4. RESTORATIVE & STAT-BOOSTING CONSUMABLES
    # =========================================================================
    "health_potion": ConsumableItem(
        id="health_potion", name="Health Draught", description="Restores 35 hit points.", heal_amount=35,
    ),
    "major_health_flask": ConsumableItem(
        id="major_health_flask", name="Major Health Flask", description="Restores 80 hit points.", heal_amount=80,
    ),
    "divine_nectar": ConsumableItem(
        id="divine_nectar", name="Divine Nectar", description="Restores 180 hit points.", heal_amount=180,
    ),

    # --- Minor Permanent Elixirs (+1 Stat / +10 HP) ---
    "elixir_vitality_minor": StatPotion(
        id="elixir_vitality_minor", name="Minor Vitality Draught",
        description="Permanently grants +10 Max HP.", heal_amount=10,
        stat_bonus=Stats(max_hp=10, attack=0, defense=0, speed=0, crit_chance=0.0),
    ),
    "elixir_strength_minor": StatPotion(
        id="elixir_strength_minor", name="Minor Brawn Draught",
        description="Permanently grants +1 Attack.", heal_amount=0,
        stat_bonus=Stats(max_hp=0, attack=1, defense=0, speed=0, crit_chance=0.0),
    ),
    "elixir_iron_minor": StatPotion(
        id="elixir_iron_minor", name="Minor Ironbark Draught",
        description="Permanently grants +1 Defense.", heal_amount=0,
        stat_bonus=Stats(max_hp=0, attack=0, defense=1, speed=0, crit_chance=0.0),
    ),
    "elixir_celerity_minor": StatPotion(
        id="elixir_celerity_minor", name="Minor Windstride Draught",
        description="Permanently grants +1 Speed.", heal_amount=0,
        stat_bonus=Stats(max_hp=0, attack=0, defense=0, speed=1, crit_chance=0.0),
    ),
    "elixir_precision_minor": StatPotion(
        id="elixir_precision_minor", name="Minor Eagle-Eye Draught",
        description="Permanently grants +1% Crit Chance.", heal_amount=0,
        stat_bonus=Stats(max_hp=0, attack=0, defense=0, speed=0, crit_chance=0.01),
    ),

    # --- Greater Permanent Elixirs (+3 Stats / +25 HP) ---
    "elixir_vitality_greater": StatPotion(
        id="elixir_vitality_greater", name="Greater Draught of Colossi",
        description="Permanently grants +25 Max HP.", heal_amount=25,
        stat_bonus=Stats(max_hp=25, attack=0, defense=0, speed=0, crit_chance=0.0),
    ),
    "elixir_strength_greater": StatPotion(
        id="elixir_strength_greater", name="Greater Draught of Warlords",
        description="Permanently grants +3 Attack.", heal_amount=0,
        stat_bonus=Stats(max_hp=0, attack=3, defense=0, speed=0, crit_chance=0.0),
    ),
    "elixir_iron_greater": StatPotion(
        id="elixir_iron_greater", name="Greater Draught of Bastions",
        description="Permanently grants +3 Defense.", heal_amount=0,
        stat_bonus=Stats(max_hp=0, attack=0, defense=3, speed=0, crit_chance=0.0),
    ),
    "elixir_celerity_greater": StatPotion(
        id="elixir_celerity_greater", name="Greater Draught of Tempests",
        description="Permanently grants +3 Speed.", heal_amount=0,
        stat_bonus=Stats(max_hp=0, attack=0, defense=0, speed=3, crit_chance=0.0),
    ),
    "elixir_precision_greater": StatPotion(
        id="elixir_precision_greater", name="Greater Draught of Killers",
        description="Permanently grants +3% Crit Chance.", heal_amount=0,
        stat_bonus=Stats(max_hp=0, attack=0, defense=0, speed=0, crit_chance=0.03),
    ),
    "elixir_of_quickness": StatPotion(
        id="elixir_of_quickness", name="Elixir of Quickness",
        description="Heals 10 HP and permanently grants +3 SPD.", heal_amount=10,
        stat_bonus=Stats(max_hp=0, attack=0, defense=0, speed=3, crit_chance=0.0),
    ),

    # =========================================================================
    # 5. WARRIOR ARSENAL & ARMOR
    # =========================================================================
    # Common / Uncommon
    "iron_broadsword": EquipmentItem(
        id="iron_broadsword", name="Iron Broadsword", description="A solid iron martial blade.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.ONE_HANDED, required_class="warrior",
        stats_bonus=Stats(max_hp=0, attack=5, defense=1, speed=0, crit_chance=0.04),
    ),
    "iron_claymore": EquipmentItem(
        id="iron_claymore", name="Iron Claymore", description="A massive two-handed sword.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.TWO_HANDED, required_class="warrior",
        stats_bonus=Stats(max_hp=0, attack=10, defense=0, speed=0, crit_chance=0.0),
    ),
    "iron_tower_shield": EquipmentItem(
        id="iron_tower_shield", name="Iron Tower Shield", description="Thick iron slab that blocks crushing blows.",
        slot=EquipSlot.OFF_HAND, weapon_type=WeaponType.SHIELD, required_class="warrior",
        stats_bonus=Stats(max_hp=15, attack=0, defense=6, speed=-1, crit_chance=0.0),
    ),
    "bronze_pauldrons": EquipmentItem(
        id="bronze_pauldrons", name="Bronze Pauldrons", description="Heavy shoulder guards.",
        slot=EquipSlot.SHOULDERS, stats_bonus=Stats(max_hp=10, attack=0, defense=3, speed=0, crit_chance=0.0),
    ),
    "iron_girdle": EquipmentItem(
        id="iron_girdle", name="Iron Girdle", description="A sturdy iron waist guard.",
        slot=EquipSlot.WAIST, stats_bonus=Stats(max_hp=15, attack=0, defense=4, speed=0, crit_chance=0.0),
    ),
    "iron_plate_greaves": EquipmentItem(
        id="iron_plate_greaves", name="Iron Greaves", description="Articulated iron leg armor.",
        slot=EquipSlot.LEGS, required_class="warrior",
        stats_bonus=Stats(max_hp=10, attack=0, defense=5, speed=0, crit_chance=0.0),
    ),

    # Rare / Epic
    "dwarven_warhammer": EquipmentItem(
        id="dwarven_warhammer", name="Dwarven Warhammer", description="Heavy anvil-headed mallet built to shatter bone.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.TWO_HANDED, required_class="warrior",
        stats_bonus=Stats(max_hp=0, attack=18, defense=3, speed=-2, crit_chance=0.08),
    ),
    "knights_bastion": EquipmentItem(
        id="knights_bastion", name="Knight's Bastion", description="Polished steel kite shield emblazoned with a griffon.",
        slot=EquipSlot.OFF_HAND, weapon_type=WeaponType.SHIELD, required_class="warrior",
        stats_bonus=Stats(max_hp=25, attack=1, defense=10, speed=0, crit_chance=0.02),
    ),
    "spiked_steel_pauldrons": EquipmentItem(
        id="spiked_steel_pauldrons", name="Spiked Pauldrons", description="Fierce shoulder plates equipped with counter-spikes.",
        slot=EquipSlot.SHOULDERS, required_class="warrior",
        stats_bonus=Stats(max_hp=15, attack=3, defense=6, speed=0, crit_chance=0.03),
    ),
    "blacksteel_harness": EquipmentItem(
        id="blacksteel_harness", name="Blacksteel Harness", description="Tempered blackened plate cuirass.",
        slot=EquipSlot.CHEST, required_class="warrior",
        stats_bonus=Stats(max_hp=40, attack=0, defense=14, speed=-1, crit_chance=0.0),
    ),
    "warlords_visage": EquipmentItem(
        id="warlords_visage", name="Warlord's Visage", description="Menacing full-face horned helm.",
        slot=EquipSlot.HEAD, required_class="warrior",
        stats_bonus=Stats(max_hp=20, attack=4, defense=8, speed=0, crit_chance=0.05),
    ),

    # --- WARRIOR LEGENDARIES (1 Weapon, 1 Armor) ---
    "legendary_worldbreaker": EquipmentItem(
        id="legendary_worldbreaker", name="Worldbreaker Greatsword",
        description="A gargantuan slab of consecrated obsidian said to crack castle gates in a single blow.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.TWO_HANDED, required_class="warrior",
        stats_bonus=Stats(max_hp=30, attack=35, defense=8, speed=2, crit_chance=0.15),
    ),
    "legendary_colossus_cuirass": EquipmentItem(
        id="legendary_colossus_cuirass", name="Cuirass of the Immortal Colossus",
        description="Forged in mountain heart-fire; blows against it ring out like hammer taps on bedrock.",
        slot=EquipSlot.CHEST, required_class="warrior",
        stats_bonus=Stats(max_hp=80, attack=4, defense=28, speed=0, crit_chance=0.05),
    ),

    # =========================================================================
    # 6. ROGUE ARSENAL & ARMOR
    # =========================================================================
    # Common / Uncommon
    "bandit_dagger": EquipmentItem(
        id="bandit_dagger", name="Bandit Dagger", description="A swift, sharp blade.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.ONE_HANDED, required_class="rogue",
        stats_bonus=Stats(max_hp=0, attack=4, defense=0, speed=5, crit_chance=0.10),
    ),
    "serrated_parrying_dagger": EquipmentItem(
        id="serrated_parrying_dagger", name="Parrying Stiletto", description="Designed to catch enemy blades and riposte.",
        slot=EquipSlot.OFF_HAND, weapon_type=WeaponType.ONE_HANDED, required_class="rogue",
        stats_bonus=Stats(max_hp=0, attack=3, defense=3, speed=4, crit_chance=0.08),
    ),
    "thief_cowl": EquipmentItem(
        id="thief_cowl", name="Thief's Cowl", description="Conceals the eyes in velvety blackness.",
        slot=EquipSlot.HEAD, required_class="rogue",
        stats_bonus=Stats(max_hp=5, attack=1, defense=1, speed=3, crit_chance=0.06),
    ),
    "shadow_tunic": EquipmentItem(
        id="shadow_tunic", name="Shadowweave Tunic", description="Muffles sound and blends into dungeon stone.",
        slot=EquipSlot.CHEST, required_class="rogue",
        stats_bonus=Stats(max_hp=15, attack=2, defense=3, speed=6, crit_chance=0.05),
    ),
    "padded_stalker_boots": EquipmentItem(
        id="padded_stalker_boots", name="Stalker Boots", description="Silent soles that leave no trace.",
        slot=EquipSlot.LEGS, required_class="rogue",
        stats_bonus=Stats(max_hp=5, attack=0, defense=1, speed=7, crit_chance=0.04),
    ),

    # Rare / Epic
    "widowmaker_dirk": EquipmentItem(
        id="widowmaker_dirk", name="Widowmaker Dirk", description="Dripping with virulent necro-toxin.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.ONE_HANDED, required_class="rogue",
        stats_bonus=Stats(max_hp=0, attack=14, defense=0, speed=8, crit_chance=0.22),
    ),
    "assassins_twinblade": EquipmentItem(
        id="assassins_twinblade", name="Whispering Sai", description="Needle-thin sai for lightning-fast thrusts.",
        slot=EquipSlot.OFF_HAND, weapon_type=WeaponType.ONE_HANDED, required_class="rogue",
        stats_bonus=Stats(max_hp=10, attack=8, defense=2, speed=6, crit_chance=0.15),
    ),
    "duelists_buckler": EquipmentItem(
        id="duelists_buckler", name="Steel Buckler", description="Small shield designed for agile deflection.",
        slot=EquipSlot.OFF_HAND, weapon_type=WeaponType.SHIELD, required_class="rogue",
        stats_bonus=Stats(max_hp=15, attack=2, defense=8, speed=3, crit_chance=0.05),
    ),
    "nightstalker_vest": EquipmentItem(
        id="nightstalker_vest", name="Nightstalker Vest", description="Studded hardened wyvern hide.",
        slot=EquipSlot.CHEST, required_class="rogue",
        stats_bonus=Stats(max_hp=25, attack=6, defense=7, speed=10, crit_chance=0.12),
    ),

    # --- ROGUE LEGENDARIES (1 Weapon, 1 Armor) ---
    "legendary_whisper_void": EquipmentItem(
        id="legendary_whisper_void", name="Whisper of the Void",
        description="A translucent dagger formed from frozen moonlight. Strikes ignore armor and tear reality.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.ONE_HANDED, required_class="rogue",
        stats_bonus=Stats(max_hp=15, attack=28, defense=2, speed=18, crit_chance=0.35),
    ),
    "legendary_shadowmeld_cloak": EquipmentItem(
        id="legendary_shadowmeld_cloak", name="Mantle of the Ghost Phantom",
        description="A diaphanous cape that shifts between dimensions, making the wearer nearly intangible.",
        slot=EquipSlot.SHOULDERS, required_class="rogue",
        stats_bonus=Stats(max_hp=45, attack=8, defense=14, speed=15, crit_chance=0.18),
    ),

    # =========================================================================
    # 7. MAGE ARSENAL & ARMOR
    # =========================================================================
    # Common / Uncommon
    "apprentice_wand": EquipmentItem(
        id="apprentice_wand", name="Apprentice Wand", description="A basic magical focus.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.ONE_HANDED, required_class="mage",
        stats_bonus=Stats(max_hp=0, attack=6, defense=0, speed=2, crit_chance=0.0),
    ),
    "arcane_grimoire": EquipmentItem(
        id="arcane_grimoire", name="Arcane Grimoire", description="A tome of spells.",
        slot=EquipSlot.OFF_HAND, weapon_type=WeaponType.FOCUS, required_class="mage",
        stats_bonus=Stats(max_hp=0, attack=3, defense=0, speed=0, crit_chance=0.05),
    ),
    "staff_of_embers": EquipmentItem(
        id="staff_of_embers", name="Staff of Embers", description="A glowing two-handed staff.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.TWO_HANDED, required_class="mage",
        stats_bonus=Stats(max_hp=0, attack=12, defense=0, speed=1, crit_chance=0.05),
    ),
    "scholar_cap": EquipmentItem(
        id="scholar_cap", name="Scholar's Pointed Cap", description="A brimmed cloth cap charged with static mana.",
        slot=EquipSlot.HEAD, required_class="mage",
        stats_bonus=Stats(max_hp=0, attack=4, defense=1, speed=1, crit_chance=0.04),
    ),
    "spellweaver_robe": EquipmentItem(
        id="spellweaver_robe", name="Spellweaver Robe", description="Silken vestments embroidered with protective runes.",
        slot=EquipSlot.CHEST, required_class="mage",
        stats_bonus=Stats(max_hp=10, attack=5, defense=3, speed=2, crit_chance=0.03),
    ),

    # Rare / Epic
    "crystal_channeler_wand": EquipmentItem(
        id="crystal_channeler_wand", name="Glimmering Quartz Wand", description="Channels raw elemental fury.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.ONE_HANDED, required_class="mage",
        stats_bonus=Stats(max_hp=5, attack=16, defense=0, speed=3, crit_chance=0.10),
    ),
    "skull_of_the_heretic": EquipmentItem(
        id="skull_of_the_heretic", name="Heretic's Scrying Skull", description="Whispers forbidden incantations from the void.",
        slot=EquipSlot.OFF_HAND, weapon_type=WeaponType.FOCUS, required_class="mage",
        stats_bonus=Stats(max_hp=0, attack=10, defense=2, speed=2, crit_chance=0.12),
    ),
    "archmages_staff": EquipmentItem(
        id="archmages_staff", name="Spire of the Archmage", description="Carved from petrified mana-trees of Eld.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.TWO_HANDED, required_class="mage",
        stats_bonus=Stats(max_hp=15, attack=26, defense=2, speed=3, crit_chance=0.08),
    ),
    "voidstrider_robes": EquipmentItem(
        id="voidstrider_robes", name="Voidstrider Vestments", description="Draped in shadows that siphon ambient kinetic force.",
        slot=EquipSlot.CHEST, required_class="mage",
        stats_bonus=Stats(max_hp=25, attack=14, defense=6, speed=4, crit_chance=0.07),
    ),

    # --- MAGE LEGENDARIES (1 Weapon, 1 Armor) ---
    "legendary_cataclysm_staff": EquipmentItem(
        id="legendary_cataclysm_staff", name="Calamity, Staff of the Supernova",
        description="A staff holding a trapped dying star at its apex. Radiates blinding thermal magic.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.TWO_HANDED, required_class="mage",
        stats_bonus=Stats(max_hp=20, attack=44, defense=4, speed=5, crit_chance=0.20),
    ),
    "legendary_astral_cowl": EquipmentItem(
        id="legendary_astral_cowl", name="Astral Archon's Diadem",
        description="A floating coronet of starlight that illuminates truth and bends incoming hostile sorcery.",
        slot=EquipSlot.HEAD, required_class="mage",
        stats_bonus=Stats(max_hp=50, attack=16, defense=18, speed=6, crit_chance=0.12),
    ),

    # =========================================================================
    # 8. UNIVERSAL & GENERIC GEAR (Wearable by All Classes)
    # =========================================================================
    # Shoulders
    "leather_mantle": EquipmentItem(
        id="leather_mantle", name="Leather Mantle", description="Basic shoulder protection.",
        slot=EquipSlot.SHOULDERS, stats_bonus=Stats(max_hp=5, attack=0, defense=1, speed=1, crit_chance=0.0),
    ),
    "fur_lined_capelet": EquipmentItem(
        id="fur_lined_capelet", name="Wolf-Fur Capelet", description="Warm animal pelt that shields against dungeon drafts.",
        slot=EquipSlot.SHOULDERS, stats_bonus=Stats(max_hp=12, attack=1, defense=2, speed=1, crit_chance=0.02),
    ),
    "iron_scaled_epaulets": EquipmentItem(
        id="iron_scaled_epaulets", name="Scale Epaulets", description="Overlapping iron scales protecting the neck.",
        slot=EquipSlot.SHOULDERS, stats_bonus=Stats(max_hp=15, attack=0, defense=5, speed=0, crit_chance=0.0),
    ),

    # Waist
    "leather_belt": EquipmentItem(
        id="leather_belt", name="Leather Belt", description="A simple waist sash.",
        slot=EquipSlot.WAIST, stats_bonus=Stats(max_hp=5, attack=0, defense=0, speed=2, crit_chance=0.0),
    ),
    "plated_war_belt": EquipmentItem(
        id="plated_war_belt", name="Plated War-Belt", description="Heavy studded brass cincher.",
        slot=EquipSlot.WAIST, stats_bonus=Stats(max_hp=18, attack=2, defense=3, speed=1, crit_chance=0.01),
    ),
    "runic_sash": EquipmentItem(
        id="runic_sash", name="Runic Silk Sash", description="Infused with glyphs of deflection.",
        slot=EquipSlot.WAIST, stats_bonus=Stats(max_hp=10, attack=3, defense=2, speed=3, crit_chance=0.03),
    ),

    # Hands
    "brawler_handwraps": EquipmentItem(
        id="brawler_handwraps", name="Brawler Handwraps", description="Rough cloth bindings stained with old blood.",
        slot=EquipSlot.HANDS, stats_bonus=Stats(max_hp=0, attack=3, defense=0, speed=2, crit_chance=0.06),
    ),
    "chainmail_mitts": EquipmentItem(
        id="chainmail_mitts", name="Chainmail Mitts", description="Flexible steel interlocking rings.",
        slot=EquipSlot.HANDS, stats_bonus=Stats(max_hp=10, attack=1, defense=4, speed=-1, crit_chance=0.0),
    ),
    "assassins_gloves": EquipmentItem(
        id="assassins_gloves", name="Grip of the Executioner", description="Supple leather gloves with steel knuckle-studs.",
        slot=EquipSlot.HANDS, stats_bonus=Stats(max_hp=5, attack=4, defense=2, speed=3, crit_chance=0.08),
    ),

    # Legs
    "iron_shod_treads": EquipmentItem(
        id="iron_shod_treads", name="Iron-Shod Treads", description="Heavy boots that grip rocky terrain firmly.",
        slot=EquipSlot.LEGS, stats_bonus=Stats(max_hp=10, attack=1, defense=3, speed=1, crit_chance=0.0),
    ),
    "quicksilver_greaves": EquipmentItem(
        id="quicksilver_greaves", name="Quicksilver Sabatons", description="Imbued with mercury enchantments for rapid steps.",
        slot=EquipSlot.LEGS, stats_bonus=Stats(max_hp=10, attack=2, defense=4, speed=6, crit_chance=0.04),
    ),

    # Head
    "iron_sallet": EquipmentItem(
        id="iron_sallet", name="Iron Sallet", description="Standard medieval infantry helmet.",
        slot=EquipSlot.HEAD, stats_bonus=Stats(max_hp=10, attack=0, defense=4, speed=0, crit_chance=0.02),
    ),
    "circlet_of_clarity": EquipmentItem(
        id="circlet_of_clarity", name="Circlet of Clarity", description="A silver circlet that sharpens focus and reflexes.",
        slot=EquipSlot.HEAD, stats_bonus=Stats(max_hp=15, attack=3, defense=2, speed=3, crit_chance=0.05),
    ),

    # =========================================================================
    # 9. FUNNY, QUIRKY & STRANGE DUNGEON FINDS
    # =========================================================================
    "suspicious_pie": ConsumableItem(
        id="suspicious_pie", name="Suspicious Meat Pie",
        description="Warm, moist, and smells like dungeon lichen. Restores 45 HP (probably).", heal_amount=45,
    ),
    "goblin_cheese_wheel": ConsumableItem(
        id="goblin_cheese_wheel", name="Goblin Stink-Cheese",
        description="So pungent it makes your eyes water. Restores 15 HP and grants +1 ATK from pure rage.",
        heal_amount=15,
    ),
    "tax_audit_scroll": EquipmentItem(
        id="tax_audit_scroll", name="Unpaid Aethelgard Tax Notice",
        description="Wielding this terrifying parchment terrifies enemies into hesitation.",
        slot=EquipSlot.OFF_HAND, weapon_type=WeaponType.FOCUS,
        stats_bonus=Stats(max_hp=0, attack=1, defense=5, speed=2, crit_chance=0.0),
    ),
    "rusty_spork_of_doom": EquipmentItem(
        id="rusty_spork_of_doom", name="Rusty Spork of Doom",
        description="An antique utensil repurposed for heroic stabbing. Oddly lethal.",
        slot=EquipSlot.MAIN_HAND, weapon_type=WeaponType.ONE_HANDED,
        stats_bonus=Stats(max_hp=0, attack=7, defense=0, speed=4, crit_chance=0.15),
    ),
    "tinfoil_coif": EquipmentItem(
        id="tinfoil_coif", name="Paranoid's Shiny Coif",
        description="Crafted from hammered silver leaf. Completely deflects mind rays and bad vibes.",
        slot=EquipSlot.HEAD,
        stats_bonus=Stats(max_hp=0, attack=0, defense=2, speed=2, crit_chance=0.07),
    ),
    "lead_balloon_boots": EquipmentItem(
        id="lead_balloon_boots", name="Boots of Extreme Gravity",
        description="Ridiculously heavy boots. You can barely move, but nothing can knock you down.",
        slot=EquipSlot.LEGS,
        stats_bonus=Stats(max_hp=35, attack=0, defense=12, speed=-4, crit_chance=0.0),
    ),
    "ring_of_mild_disappointment": EquipmentItem(
        id="ring_of_mild_disappointment", name="Ring of Modest Hopes",
        description="It glows with a magnificent celestial aura, but only gives +1 HP.",
        slot=EquipSlot.WAIST,
        stats_bonus=Stats(max_hp=1, attack=0, defense=0, speed=0, crit_chance=0.001),
    ),
}

# =============================================================================
# STARTER KITS REGISTRY (Class ID -> List of item IDs)
# =============================================================================
STARTER_KITS: Final[dict[str, list[str]]] = {
    "warrior": [
        "bronze_sword",
        "bronze_shield",
        "bronze_helmet",
        "bronze_chestplate",
        "leather_gloves",
        "leather_pants",
    ],
    "rogue": [
        "worn_dagger",
        "rusty_parrying_dirk",
        "shadow_cowl",
        "padded_leather_vest",
        "cutpurse_gloves",
        "rogue_breeches",
    ],
    "mage": [
        "gnarled_wand",
        "tattered_grimoire",
        "apprentice_cowl",
        "apprentice_robes",
        "cloth_handwraps",
        "woven_pantaloons",
    ],
}


def get_item(item_id: str) -> Item | None:
    """Retrieve an item by its unique catalog ID."""
    return ITEM_CATALOG.get(item_id)


def get_catalog() -> dict[str, Item]:
    """Return a shallow copy of the entire item catalog."""
    return ITEM_CATALOG.copy()


def get_starter_kit(class_id: str) -> list[EquipmentItem]:
    """Retrieve all starter equipment pieces for a given class ID."""
    item_ids = STARTER_KITS.get(class_id, STARTER_KITS["warrior"])
    items: list[EquipmentItem] = []
    for item_id in item_ids:
        item = get_item(item_id)
        if isinstance(item, EquipmentItem):
            items.append(item)
    return items