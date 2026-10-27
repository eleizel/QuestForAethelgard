"""Biome definitions and encounter rosters across all three Acts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class BiomeDefinition:
    id: str
    act: int
    name: str
    description: str
    theme_tags: str
    ambient_color: int  # Primary Pyxel palette color for borders/atmosphere
    basic_enemies: tuple[str, ...]
    elites: tuple[str, ...]
    bosses: tuple[str, ...]

    @property
    def localized_name(self) -> str:
        from src.core.i18n import t
        return t(f"biome_{self.id}_name")

    @property
    def localized_description(self) -> str:
        from src.core.i18n import t
        return t(f"biome_{self.id}_desc")

    @property
    def localized_tags(self) -> str:
        from src.core.i18n import t
        return t(f"biome_{self.id}_tags")


BIOME_REGISTRY: Final[dict[str, BiomeDefinition]] = {
    # =========================================================================
    # ACT 1: THE DESCENT (Floors 1-12)
    # =========================================================================
    "arboretum": BiomeDefinition(
        id="arboretum",
        act=1,
        name="The Wilted Arboretum",
        description="A lightless conservatory choked with parasitic vines, toxic spores, and briar-beasts.",
        theme_tags="[Poison / Bleed / Root Stalls]",
        ambient_color=3,  # COLOR_GREEN
        basic_enemies=("thornvein_creeper", "spore_pod", "bramble_hound", "rotting_woodwose"),
        elites=("mandragora_matron", "corpse_treant"),
        bosses=("malignant_belladonna", "verdant_abomination"),
    ),
    "cathedral": BiomeDefinition(
        id="cathedral",
        act=1,
        name="The Desecrated Cathedral",
        description="Ruined gothic naves echoing with blasphemous chants, impish flames, and flying tomes.",
        theme_tags="[Fire / Arcane Missiles / Reflective Wards]",
        ambient_color=2,  # COLOR_PURPLE
        basic_enemies=("cathedral_imp", "possessed_grimoire", "candelabra_fiend", "penitent_zealot"),
        elites=("belltower_gargoyle", "inquisitor_automaton"),
        bosses=("blind_archbishop", "chorus_of_damned"),
    ),

    # =========================================================================
    # ACT 2: THE UNDERBELLY (Floors 13-24)
    # =========================================================================
    "ossuary": BiomeDefinition(
        id="ossuary",
        act=2,
        name="The Drowned Ossuary",
        description="Subterranean catacombs flooded with stagnant brine, drifting ribcages, and blood leeches.",
        theme_tags="[Lifesteal / Gauge Siphon / Turn Bombs]",
        ambient_color=5,  # COLOR_DARK_BLUE
        basic_enemies=("mire_ghoul", "drowned_skulls", "leech_husk", "crypt_lurker"),
        elites=("tide_gravekeeper", "carrion_behemoth"),
        bosses=("drowned_patriarch", "scylla_bone_weaver"),
    ),
    "foundry": BiomeDefinition(
        id="foundry",
        act=2,
        name="The Foundry of Torment",
        description="An infernal machinery hall of clanking gears, liquid iron vats, and furnace wardens.",
        theme_tags="[Burn / Armor Shred / Steam Blinds]",
        ambient_color=9,  # COLOR_ORANGE
        basic_enemies=("slag_homunculus", "cinder_sprite", "clockwork_flayer", "ashen_overseer"),
        elites=("furnace_warden", "retching_alchemist"),
        bosses=("ironforge_tyrant", "molten_sovereign"),
    ),

    # =========================================================================
    # ACT 3: THE SUMMIT (Floors 25-42; this act uses 18 map floors)
    # =========================================================================
    "observatory": BiomeDefinition(
        id="observatory",
        act=3,
        name="The Astral Observatory",
        description="A shattered spire roof exposed to cosmic tears, falling star fragments, and space rifts.",
        theme_tags="[Magic Reflection / Gauge Steal / Rewind Turns]",
        ambient_color=12,  # COLOR_CYAN
        basic_enemies=("void_mirror", "stareater_wisp", "comet_stalker", "celestial_hermit"),
        elites=("rift_warden", "null_singularity"),
        bosses=("chronomancer_praetor", "devouring_constellation"),
    ),
    "sanctum": BiomeDefinition(
        id="sanctum",
        act=3,
        name="The Blood Sanctum",
        description="Velvet-draped vampire halls slick with coagulated ichor and aristocrats wielding rapiers.",
        theme_tags="[Burst Crits / Heavy Bleed / Accelerating DPS Race]",
        ambient_color=8,  # COLOR_RED
        basic_enemies=("sanguine_thrall", "crimson_gargoyle", "hemomancer_acolyte", "flayed_duelist"),
        elites=("baroness_vespera", "amalgam_of_veins"),
        bosses=("high_lord_carmilla", "blood_god_avatar"),
    ),
}

ACT_BIOMES: Final[dict[int, tuple[str, str]]] = {
    1: ("arboretum", "cathedral"),
    2: ("ossuary", "foundry"),
    3: ("observatory", "sanctum"),
}


def get_biome(biome_id: str) -> BiomeDefinition | None:
    return BIOME_REGISTRY.get(biome_id)
