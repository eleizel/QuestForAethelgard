from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class EnemyArchetype:
    id: str
    name: str
    base_hp: int
    base_atk: int
    base_def: int
    base_spd: int
    base_crit: float
    description: str
    on_hit_status: str | None = None
    status_chance: float = 0.0

    @property
    def localized_name(self) -> str:
        from src.core.i18n import t
        return t(f"enemy_{self.id}_name")

    @property
    def localized_description(self) -> str:
        from src.core.i18n import t
        return t(f"enemy_{self.id}_desc")


ENEMY_CATALOG: Final[dict[str, EnemyArchetype]] = {
    # -------------------------------------------------------------------------
    # 1A. THE WILTED ARBORETUM (Act 1)
    # -------------------------------------------------------------------------
    "thornvein_creeper": EnemyArchetype(
        id="thornvein_creeper", name="Thornvein Creeper",
        base_hp=28, base_atk=7, base_def=1, base_spd=10, base_crit=0.06,
        description="Barbed vine tendril that lashes targets swiftly.", on_hit_status="bleed", status_chance=0.35,
    ),
    "spore_pod": EnemyArchetype(
        id="spore_pod", name="Spore-Spitting Pod",
        base_hp=34, base_atk=10, base_def=2, base_spd=6, base_crit=0.02,
        description="Swollen fungus emitting pressurized toxic clouds.", on_hit_status="poison", status_chance=0.45,
    ),
    "bramble_hound": EnemyArchetype(
        id="bramble_hound", name="Bramble Hound",
        base_hp=24, base_atk=9, base_def=0, base_spd=14, base_crit=0.18,
        description="Fast briar-formed predatory hound.",
    ),
    "rotting_woodwose": EnemyArchetype(
        id="rotting_woodwose", name="Rotting Woodwose",
        base_hp=48, base_atk=8, base_def=4, base_spd=5, base_crit=0.01,
        description="Lumbering hollow tree golem with regenerative bark.",
    ),
    "mandragora_matron": EnemyArchetype(
        id="mandragora_matron", name="Mandragora Matron",
        base_hp=85, base_atk=14, base_def=5, base_spd=8, base_crit=0.05,
        description="Screeching bulb that stuns action gauges and shields itself.", on_hit_status="stun",
        status_chance=0.25,
    ),
    "corpse_treant": EnemyArchetype(
        id="corpse_treant", name="Corpse-Root Treant",
        base_hp=110, base_atk=16, base_def=7, base_spd=5, base_crit=0.04,
        description="Massive corrupted timber construct that slams the floor.",
    ),
    "malignant_belladonna": EnemyArchetype(
        id="malignant_belladonna", name="Malignant Belladonna",
        base_hp=220, base_atk=20, base_def=8, base_spd=9, base_crit=0.08,
        description="Giant carnivorous floral queen that siphons life.", on_hit_status="poison", status_chance=0.60,
    ),
    "verdant_abomination": EnemyArchetype(
        id="verdant_abomination", name="The Verdant Abomination",
        base_hp=250, base_atk=18, base_def=10, base_spd=8, base_crit=0.12,
        description="Mutated tangle of rot that grows fiercer as health dwindles.",
    ),

    # -------------------------------------------------------------------------
    # 1B. THE DESECRATED CATHEDRAL (Act 1)
    # -------------------------------------------------------------------------
    "cathedral_imp": EnemyArchetype(
        id="cathedral_imp", name="Cathedral Imp",
        base_hp=22, base_atk=8, base_def=0, base_spd=15, base_crit=0.10,
        description="Flighty demon chucking cinders to disrupt turns.", on_hit_status="burn", status_chance=0.40,
    ),
    "possessed_grimoire": EnemyArchetype(
        id="possessed_grimoire", name="Possessed Grimoire",
        base_hp=26, base_atk=11, base_def=3, base_spd=8, base_crit=0.05,
        description="Floating ritual tome casting defense-piercing cantrips.",
    ),
    "candelabra_fiend": EnemyArchetype(
        id="candelabra_fiend", name="Candelabra Fiend",
        base_hp=36, base_atk=9, base_def=3, base_spd=7, base_crit=0.04,
        description="Brass construct that splashes burning wax on contact.", on_hit_status="burn", status_chance=0.50,
    ),
    "penitent_zealot": EnemyArchetype(
        id="penitent_zealot", name="Penitent Zealot",
        base_hp=32, base_atk=12, base_def=1, base_spd=11, base_crit=0.14,
        description="Maddened cultist with reckless, bleeding flail strikes.", on_hit_status="bleed",
        status_chance=0.35,
    ),
    "belltower_gargoyle": EnemyArchetype(
        id="belltower_gargoyle", name="Belltower Gargoyle",
        base_hp=95, base_atk=15, base_def=9, base_spd=7, base_crit=0.06,
        description="Hardened granite guardian diving from cathedral rafters.", on_hit_status="stun",
        status_chance=0.30,
    ),
    "inquisitor_automaton": EnemyArchetype(
        id="inquisitor_automaton", name="Inquisitor Automaton",
        base_hp=80, base_atk=16, base_def=4, base_spd=13, base_crit=0.15,
        description="Clockwork iron maiden equipped with spinning blades.",
    ),
    "blind_archbishop": EnemyArchetype(
        id="blind_archbishop", name="The Blind Archbishop",
        base_hp=210, base_atk=24, base_def=7, base_spd=8, base_crit=0.10,
        description="Corrupted high priest commanding unmitigated divine smites.",
    ),
    "chorus_of_damned": EnemyArchetype(
        id="chorus_of_damned", name="Chorus of the Damned",
        base_hp=240, base_atk=22, base_def=6, base_spd=10, base_crit=0.15,
        description="Spectral choir shrieking harmonized mental agonies.",
    ),

    # -------------------------------------------------------------------------
    # 2A. THE DROWNED OSSUARY (Act 2)
    # -------------------------------------------------------------------------
    "mire_ghoul": EnemyArchetype(
        id="mire_ghoul", name="Mire Ghoul",
        base_hp=52, base_atk=13, base_def=3, base_spd=8, base_crit=0.04,
        description="Waterlogged corpse inflicting necrotic wounds that hinder heals.", on_hit_status="weaken",
        status_chance=0.40,
    ),
    "drowned_skulls": EnemyArchetype(
        id="drowned_skulls", name="Drowned Skull-Cluster",
        base_hp=40, base_atk=18, base_def=1, base_spd=12, base_crit=0.05,
        description="Floating raft of skulls charging a suicide explosion.",
    ),
    "leech_husk": EnemyArchetype(
        id="leech_husk", name="Leech-Swarm Husk",
        base_hp=48, base_atk=14, base_def=2, base_spd=10, base_crit=0.08,
        description="Swollen cadaver siphoning vitality with every bite.",
    ),
    "crypt_lurker": EnemyArchetype(
        id="crypt_lurker", name="Crypt Lurker",
        base_hp=44, base_atk=16, base_def=2, base_spd=16, base_crit=0.20,
        description="Blind cave arthropod ambushing from water pools.", on_hit_status="poison", status_chance=0.40,
    ),
    "tide_gravekeeper": EnemyArchetype(
        id="tide_gravekeeper", name="Tide-Risen Gravekeeper",
        base_hp=140, base_atk=22, base_def=8, base_spd=7, base_crit=0.08,
        description="Brine-crusted giant swinging a ship anchor that wipes action meters.", on_hit_status="stun",
        status_chance=0.35,
    ),
    "carrion_behemoth": EnemyArchetype(
        id="carrion_behemoth", name="Carrion Behemoth",
        base_hp=170, base_atk=19, base_def=6, base_spd=6, base_crit=0.04,
        description="Undead mound of muck and bones with enormous staying power.",
    ),
    "drowned_patriarch": EnemyArchetype(
        id="drowned_patriarch", name="The Drowned Patriarch",
        base_hp=340, base_atk=28, base_def=11, base_spd=9, base_crit=0.10,
        description="Submerged king flooding the room to drown player action speed.",
    ),
    "scylla_bone_weaver": EnemyArchetype(
        id="scylla_bone_weaver", name="Scylla, the Bone-Weaver",
        base_hp=310, base_atk=32, base_def=9, base_spd=12, base_crit=0.18,
        description="Multi-limbed skeletal matriarch locking players in rib cages.",
    ),

    # -------------------------------------------------------------------------
    # 2B. THE FOUNDRY OF TORMENT (Act 2)
    # -------------------------------------------------------------------------
    "slag_homunculus": EnemyArchetype(
        id="slag_homunculus", name="Slagforged Homunculus",
        base_hp=56, base_atk=14, base_def=5, base_spd=7, base_crit=0.02,
        description="Walking molten brick that inflicts lingering burn damage.", on_hit_status="burn",
        status_chance=0.50,
    ),
    "cinder_sprite": EnemyArchetype(
        id="cinder_sprite", name="Cinder Sprite",
        base_hp=35, base_atk=17, base_def=1, base_spd=18, base_crit=0.15,
        description="Fast-skittering flame wisp that detonates on death.", on_hit_status="burn", status_chance=0.40,
    ),
    "clockwork_flayer": EnemyArchetype(
        id="clockwork_flayer", name="Clockwork Flayer",
        base_hp=46, base_atk=15, base_def=4, base_spd=13, base_crit=0.10,
        description="Mechanical saw drone systematically stripping armor.", on_hit_status="weaken", status_chance=0.40,
    ),
    "ashen_overseer": EnemyArchetype(
        id="ashen_overseer", name="Ashen Overseer",
        base_hp=60, base_atk=16, base_def=3, base_spd=9, base_crit=0.06,
        description="Cruel taskmaster gaining attack power whenever foes suffer.",
    ),
    "furnace_warden": EnemyArchetype(
        id="furnace_warden", name="Furnace Warden",
        base_hp=160, base_atk=23, base_def=12, base_spd=6, base_crit=0.05,
        description="Reinforced boiler golem venting scalding steam clouds.", on_hit_status="blind", status_chance=0.40,
    ),
    "retching_alchemist": EnemyArchetype(
        id="retching_alchemist", name="Retching Alchemist",
        base_hp=125, base_atk=26, base_def=4, base_spd=11, base_crit=0.16,
        description="Crazed chemist throwing volatile mutagen and acid vials.",
    ),
    "ironforge_tyrant": EnemyArchetype(
        id="ironforge_tyrant", name="The Ironforge Tyrant",
        base_hp=360, base_atk=34, base_def=14, base_spd=7, base_crit=0.12,
        description="Colossal plate-clad blacksmith hammering shockwaves through stone.",
    ),
    "molten_sovereign": EnemyArchetype(
        id="molten_sovereign", name="Molten Sovereign",
        base_hp=320, base_atk=38, base_def=8, base_spd=10, base_crit=0.15,
        description="Sentient lava colossus that vents lethal magma cascades.",
    ),

    # -------------------------------------------------------------------------
    # 3A. THE ASTRAL OBSERVATORY (Act 3)
    # -------------------------------------------------------------------------
    "void_mirror": EnemyArchetype(
        id="void_mirror", name="Void Mirror",
        base_hp=70, base_atk=20, base_def=6, base_spd=9, base_crit=0.05,
        description="Floating quartz prism reflecting back a portion of skill damage.", on_hit_status="vulnerable",
        status_chance=0.40,
    ),
    "stareater_wisp": EnemyArchetype(
        id="stareater_wisp", name="Star-Eater Wisp",
        base_hp=60, base_atk=22, base_def=3, base_spd=15, base_crit=0.12,
        description="Cosmic spark siphoning player gauge to fuel rapid turns.",
    ),
    "comet_stalker": EnemyArchetype(
        id="comet_stalker", name="Comet Stalker",
        base_hp=65, base_atk=25, base_def=4, base_spd=17, base_crit=0.28,
        description="Interdimensional panther striking with precision criticals.",
    ),
    "celestial_hermit": EnemyArchetype(
        id="celestial_hermit", name="Celestial Hermit",
        base_hp=80, base_atk=24, base_def=5, base_spd=10, base_crit=0.08,
        description="Mad star-priest warping gravity thresholds.",
    ),
    "rift_warden": EnemyArchetype(
        id="rift_warden", name="Rift Warden",
        base_hp=210, base_atk=32, base_def=8, base_spd=12, base_crit=0.15,
        description="Void swordmaster carving tears in spacetime.",
    ),
    "null_singularity": EnemyArchetype(
        id="null_singularity", name="The Null Singularity",
        base_hp=190, base_atk=35, base_def=10, base_spd=8, base_crit=0.10,
        description="Concentrated gravitational sphere that compresses enemy stats.", on_hit_status="weaken",
        status_chance=0.50,
    ),
    "chronomancer_praetor": EnemyArchetype(
        id="chronomancer_praetor", name="Chronomancer Praetor",
        base_hp=440, base_atk=42, base_def=12, base_spd=13, base_crit=0.20,
        description="Time lord capable of rewinding mortality and stalling cooldowns.", on_hit_status="stun",
        status_chance=0.30,
    ),
    "devouring_constellation": EnemyArchetype(
        id="devouring_constellation", name="The Devouring Constellation",
        base_hp=490, base_atk=45, base_def=11, base_spd=11, base_crit=0.18,
        description="Cosmic god shifting between solar fire, lunar freeze, and void rot.",
    ),

    # -------------------------------------------------------------------------
    # 3B. THE BLOOD SANCTUM (Act 3)
    # -------------------------------------------------------------------------
    "sanguine_thrall": EnemyArchetype(
        id="sanguine_thrall", name="Sanguine Thrall",
        base_hp=75, base_atk=24, base_def=3, base_spd=14, base_crit=0.12,
        description="Frenzied cannibal striking twice per turn and ramping attack.", on_hit_status="bleed",
        status_chance=0.45,
    ),
    "crimson_gargoyle": EnemyArchetype(
        id="crimson_gargoyle", name="Crimson Gargoyle",
        base_hp=95, base_atk=22, base_def=8, base_spd=8, base_crit=0.15,
        description="Bloodstone statue that leeches life on critical blows.",
    ),
    "hemomancer_acolyte": EnemyArchetype(
        id="hemomancer_acolyte", name="Hemomancer Acolyte",
        base_hp=65, base_atk=30, base_def=2, base_spd=11, base_crit=0.18,
        description="Blood cultist sacrificing health to fire raw unmitigated blasts.", on_hit_status="vulnerable",
        status_chance=0.40,
    ),
    "flayed_duelist": EnemyArchetype(
        id="flayed_duelist", name="Flayed Duelist",
        base_hp=70, base_atk=26, base_def=4, base_spd=18, base_crit=0.32,
        description="Cursed fencing master boasting devastating critical ripostes.", on_hit_status="bleed",
        status_chance=0.50,
    ),
    "baroness_vespera": EnemyArchetype(
        id="baroness_vespera", name="Baroness Vespera",
        base_hp=220, base_atk=36, base_def=6, base_spd=16, base_crit=0.25,
        description="Airborne vampiress raining blood daggers while evading attacks.",
    ),
    "amalgam_of_veins": EnemyArchetype(
        id="amalgam_of_veins", name="Amalgam of Veins",
        base_hp=260, base_atk=28, base_def=10, base_spd=7, base_crit=0.08,
        description="Gargantuan meat colossus that retaliates with whiplash tendrils.",
    ),
    "high_lord_carmilla": EnemyArchetype(
        id="high_lord_carmilla", name="High Lord Carmilla",
        base_hp=460, base_atk=46, base_def=12, base_spd=14, base_crit=0.25,
        description="Ancient vampire queen possessing mist form and lethal executes.", on_hit_status="vulnerable",
        status_chance=0.50,
    ),
    "blood_god_avatar": EnemyArchetype(
        id="blood_god_avatar", name="The Blood-God Avatar",
        base_hp=520, base_atk=50, base_def=10, base_spd=12, base_crit=0.20,
        description="Monolithic deity dealing accelerating bleed damage in a strict race.",
    ),
}
