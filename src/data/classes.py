from dataclasses import dataclass, field
from typing import Final

from src.entities.actor import Stats


@dataclass
class ClassDefinition:
    id: str
    name: str
    tier: int
    base_stats: Stats
    growth_per_level: Stats
    promotions: list[str]
    description: str
    starting_abilities: list[str] = field(default_factory=list)
    exp_multiplier: float = 1.0
    signature_passive: str | None = None

    @property
    def localized_name(self) -> str:
        from src.core.i18n import t
        return t(f"class_{self.id}_name")

    @property
    def localized_description(self) -> str:
        from src.core.i18n import t
        return t(f"class_{self.id}_desc")


CLASS_REGISTRY: Final[dict[str, ClassDefinition]] = {
    "warrior": ClassDefinition(
        id="warrior",
        name="Warrior",
        tier=1,
        base_stats=Stats(max_hp=120, attack=12, defense=10, speed=10, crit_chance=0.05),
        growth_per_level=Stats(max_hp=15, attack=2, defense=3, speed=1, crit_chance=0.005),
        promotions=["paladin", "berserker"],
        description="A resilient fighter focused on martial combat.",
        starting_abilities=["cross_cut","mend_wound"]
    ),
    "rogue": ClassDefinition(
        id="rogue",
        name="Rogue",
        tier=1,
        base_stats=Stats(max_hp=105, attack=15, defense=8, speed=15, crit_chance=0.05),
        growth_per_level=Stats(max_hp=12, attack=3, defense=2, speed=1, crit_chance=0.01),
        promotions=["venomancer", "duelist"],
        description="A nimble and deadly striking expert.",
        starting_abilities=["shadow_strike","mend_wound"]
    ),
    "mage": ClassDefinition(
        id="mage",
        name="Mage",
        tier=1,
        base_stats=Stats(max_hp=100, attack=18, defense=8, speed=10, crit_chance=0.05),
        growth_per_level=Stats(max_hp=10, attack=4, defense=2, speed=1, crit_chance=0.005),
        promotions=["archmage", "warlock"],
        description="A fragile but destructive spellcaster.",
        starting_abilities=["arcane_bolt","mend_wound"]
    ),
    "paladin": ClassDefinition(
        id="paladin",
        name="Paladin",
        tier=2,
        base_stats=Stats(max_hp=160, attack=22, defense=16, speed=12, crit_chance=0.08),
        growth_per_level=Stats(max_hp=18, attack=3, defense=3, speed=1, crit_chance=0.005),
        promotions=[],
        description="A holy knight blending high defense and healing.",
        signature_passive="paladin_oath"
    ),
    "berserker": ClassDefinition(
        id="berserker",
        name="Berserker",
        tier=2,
        base_stats=Stats(max_hp=130, attack=30, defense=6, speed=14, crit_chance=0.15),
        growth_per_level=Stats(max_hp=20, attack=5, defense=1, speed=3, crit_chance=0.01),
        promotions=[],
        description="A furious warrior who sacrifices defense for raw power.",
        signature_passive="berserker_rage"
    ),
    "venomancer": ClassDefinition(
        id="venomancer",
        name="Venomancer",
        tier=2,
        base_stats=Stats(max_hp=125, attack=27, defense=8, speed=18, crit_chance=0.10),
        growth_per_level=Stats(max_hp=16, attack=4, defense=3, speed=2, crit_chance=0.005),
        promotions=[],
        description="A patient poisoner who weakens foes and turns lingering toxins into sudden damage.",
        signature_passive="venomancer_mastery"
    ),
    "duelist": ClassDefinition(
        id="duelist",
        name="Duelist",
        tier=2,
        base_stats=Stats(max_hp=120, attack=26, defense=10, speed=20, crit_chance=0.18),
        growth_per_level=Stats(max_hp=15, attack=5, defense=2, speed=2, crit_chance=0.015),
        promotions=[],
        description="A swift fencer combining speed with parrying techniques.",
        signature_passive="duelist_precision"
    ),
    "archmage": ClassDefinition(
        id="archmage",
        name="Archmage",
        tier=2,
        base_stats=Stats(max_hp=95, attack=42, defense=4, speed=12, crit_chance=0.13),
        growth_per_level=Stats(max_hp=10, attack=5, defense=1, speed=2, crit_chance=0.01),
        promotions=[],
        description="An unparalleled master of arcane forces.",
        signature_passive="archmage_focus"
    ),
    "warlock": ClassDefinition(
        id="warlock",
        name="Warlock",
        tier=2,
        base_stats=Stats(max_hp=110, attack=35, defense=8, speed=10, crit_chance=0.10),
        growth_per_level=Stats(max_hp=15, attack=5, defense=3, speed=1, crit_chance=0.005),
        promotions=[],
        description="A dark spellcaster who draws power from their own life force.",
        signature_passive="warlock_pact"
    )
}
