"""Biomed Enemy Archetypes with specialized tier balance."""

from __future__ import annotations

import random
from statistics import mean
from enum import Enum
from math import ceil

from src.entities.actor import Actor, Stats


class EnemyTier(Enum):
    COMMON = 1
    UNCOMMON = 2
    ELITE = 3
    BOSS = 4

TIER_HP_MULT: dict[EnemyTier, float] = {
    EnemyTier.COMMON:   1.25,
    EnemyTier.UNCOMMON: 1.15,
    EnemyTier.ELITE:    1.80,
    EnemyTier.BOSS:     3.00,
}

TIER_ATK_MULT: dict[EnemyTier, float] = {
    EnemyTier.COMMON:   1.00,
    EnemyTier.UNCOMMON: 1.10,
    EnemyTier.ELITE:    1.25,
    EnemyTier.BOSS:     1.35,
}

ACT_2_START_FLOOR = 13
ACT_3_START_FLOOR = 25
ACT_2_BOSS_HP_OVER_ELITE_RATIO = 1.25
ACT_2_BOSS_ATK_MULT = 1.20
ACT_3_BOSS_HP_OVER_ELITE_RATIO = 1.25
ACT_3_BOSS_ATK_MULT = 1.20
BOSS_HP_OVER_ELITE_RATIO = 1.50
ACT_1_ENEMY_HP_MULT = 1.15
ACT_1_ENEMY_ATK_MULT = 1.15
ACT_1_ENEMY_DEF_MULT = 1.15
ACT_2_ENEMY_HP_MULT = 1.25
ACT_2_ENEMY_ATK_MULT = 1.25
ACT_2_ENEMY_DEF_MULT = 1.25
ACT_3_ENEMY_HP_MULT = 1.25
ACT_3_ENEMY_ATK_MULT = 1.25
ACT_3_ENEMY_DEF_MULT = 1.25
ENEMY_HP_GROWTH_PER_FLOOR = 0.045
ENEMY_ATK_GROWTH_PER_FLOOR = 0.050
ENEMY_DEF_GROWTH_PER_FLOOR = 0.050
COMMON_ENEMY_SPEED_BONUS = 2
MIN_ENEMY_SPEED_RATIO = 0.80

# Reward scaling is kept explicit so enum values do not implicitly set economy balance.
TIER_REWARD_MULT: dict[EnemyTier, float] = {
    EnemyTier.COMMON: 1.0,
    EnemyTier.UNCOMMON: 2.0,
    EnemyTier.ELITE: 3.0,
    EnemyTier.BOSS: 4.0,
}

from src.data.enemies import ENEMY_CATALOG, EnemyHook, EnemySkill, ENEMY_SKILLS


# Complete Archetype Registry: 24 Commons/Uncommons + 12 Elites + 12 Bosses = 48 Total


class Enemy(Actor):
    """An adversary encountered in combat."""

    def __init__(
            self,
            name: str,
            stats: Stats,
            tier: EnemyTier,
            floor_level: int,
            exp_reward: int,
            gold_reward: int,
            archetype_id: str = "skeleton_warrior",
    ) -> None:
        super().__init__(name=name, base_stats=stats)
        self.tier: EnemyTier = tier
        self.floor_level: int = floor_level
        self.exp_reward: int = exp_reward
        self.gold_reward: int = gold_reward
        self.archetype_id: str = archetype_id

        archetype = ENEMY_CATALOG.get(archetype_id)
        self.archetype = archetype
        if archetype:
            self.on_hit_status: str | None = archetype.on_hit_status
            self.status_chance: float = archetype.status_chance
            self.on_death_hook: EnemyHook = archetype.on_death_hook
            self.half_hp_hook: EnemyHook = archetype.half_hp_hook
            self.quarter_hp_hook: EnemyHook = archetype.quarter_hp_hook
            self.phase_style: str = archetype.phase_style
            if tier == EnemyTier.BOSS:
                skill_ids = archetype.boss_skills
            elif tier in (EnemyTier.UNCOMMON, EnemyTier.ELITE):
                skill_ids = (archetype.uncommon_skill,)
            else:
                skill_ids = ()
            self.skills: tuple[EnemySkill, ...] = tuple(
                ENEMY_SKILLS[skill_id] for skill_id in skill_ids if skill_id in ENEMY_SKILLS
            )
        else:
            self.on_hit_status: str | None = None
            self.status_chance: float = 0.0
            self.on_death_hook = EnemyHook(
                event="death", effect="concept_death", dialogue_key="enemy_death_hook",
            )
            self.half_hp_hook = EnemyHook(event="threshold", effect="phase", threshold=0.50)
            self.quarter_hp_hook = EnemyHook(event="threshold", effect="signature", threshold=0.25,
                                             skill_id="signature_attack")
            self.phase_style = "enrage"
            self.skills = ()

    @property
    def display_name(self) -> str:
        from src.core.i18n import t
        prefix = ""
        if self.tier == EnemyTier.ELITE:
            prefix = t("prefix_elite")
        elif self.tier == EnemyTier.UNCOMMON:
            prefix = t("prefix_uncommon")
        arch = ENEMY_CATALOG.get(self.archetype_id)
        base_name = arch.localized_name if arch else self.name
        return f"{prefix}{base_name}"

    @property
    def effective_stats(self) -> Stats:
        return self.base_stats.add(self.stat_modifiers)


def generate_enemy(
        tier: EnemyTier = EnemyTier.COMMON,
        floor: int = 1,
        biome_id: str = "arboretum",
        rng: random.Random | None = None,
        player_speed: int | None = None,
) -> Enemy:
    """Generate a tier-scaled enemy, optionally keeping pace with player base speed."""
    from src.data.biomes import BIOME_REGISTRY

    rand = rng if rng is not None else random.Random()
    biome = BIOME_REGISTRY.get(biome_id, BIOME_REGISTRY["arboretum"])

    if tier == EnemyTier.BOSS:
        arch_id = rand.choice(biome.bosses)
    elif tier == EnemyTier.ELITE:
        arch_id = rand.choice(biome.elites)
    else:  # COMMON or UNCOMMON
        arch_id = rand.choice(biome.basic_enemies)

    template = ENEMY_CATALOG.get(arch_id, ENEMY_CATALOG["thornvein_creeper"])

    floor_offset = max(0, floor - 1)
    reward_multiplier = (1.0 + floor_offset * 0.04) * TIER_REWARD_MULT[tier]

    hp_mult = TIER_HP_MULT[tier]
    atk_mult = TIER_ATK_MULT[tier]
    act_hp_mult = 1.0
    act_atk_mult = 1.0
    act_def_mult = 1.0
    if floor >= ACT_3_START_FLOOR:
        act_hp_mult = ACT_3_ENEMY_HP_MULT
        act_atk_mult = ACT_3_ENEMY_ATK_MULT
        act_def_mult = ACT_3_ENEMY_DEF_MULT
    elif floor >= ACT_2_START_FLOOR:
        act_hp_mult = ACT_2_ENEMY_HP_MULT
        act_atk_mult = ACT_2_ENEMY_ATK_MULT
        act_def_mult = ACT_2_ENEMY_DEF_MULT
    else:
        act_hp_mult = ACT_1_ENEMY_HP_MULT
        act_atk_mult = ACT_1_ENEMY_ATK_MULT
        act_def_mult = ACT_1_ENEMY_DEF_MULT
    if tier == EnemyTier.BOSS:
        # Normalize average boss HP against average Elite HP, then apply an
        # act-specific premium while preserving each archetype's relative size.
        elite_mean_hp = mean(ENEMY_CATALOG[enemy_id].base_hp for enemy_id in biome.elites)
        boss_mean_hp = mean(ENEMY_CATALOG[enemy_id].base_hp for enemy_id in biome.bosses)
        boss_hp_ratio = BOSS_HP_OVER_ELITE_RATIO
        if floor >= ACT_3_START_FLOOR:
            boss_hp_ratio = ACT_3_BOSS_HP_OVER_ELITE_RATIO
            atk_mult = ACT_3_BOSS_ATK_MULT
        elif floor >= ACT_2_START_FLOOR:
            boss_hp_ratio = ACT_2_BOSS_HP_OVER_ELITE_RATIO
            atk_mult = ACT_2_BOSS_ATK_MULT
        hp_mult = (
            TIER_HP_MULT[EnemyTier.ELITE]
            * boss_hp_ratio
            * elite_mean_hp
            / boss_mean_hp
        )

    enemy_speed = min(
        25,
        template.base_spd
        + floor_offset // 5
        + (COMMON_ENEMY_SPEED_BONUS if tier == EnemyTier.COMMON else 0),
    )
    if player_speed is not None:
        # Equipment and temporary buffs are excluded: this floor follows natural
        # class/level progression so enemy speed does not lag by over 20%.
        enemy_speed = max(enemy_speed, ceil(max(1, player_speed) * MIN_ENEMY_SPEED_RATIO))

    scaled_stats = Stats(
        max_hp=max(1, int(template.base_hp * (1 + floor_offset * ENEMY_HP_GROWTH_PER_FLOOR) * hp_mult * act_hp_mult)),
        attack=max(1, int(template.base_atk * (1 + floor_offset * ENEMY_ATK_GROWTH_PER_FLOOR) * atk_mult * act_atk_mult)),
        defense=max(0, int(template.base_def * (1 + floor_offset * ENEMY_DEF_GROWTH_PER_FLOOR) * act_def_mult)),
        speed=enemy_speed,
        crit_chance=template.base_crit,
    )

    exp_reward = int(70 * reward_multiplier)
    gold_reward = int(rand.randint(6, 16) * reward_multiplier)

    title_prefix = ""
    if tier == EnemyTier.ELITE:
        title_prefix = "Elite "
    elif tier == EnemyTier.UNCOMMON:
        title_prefix = "Vicious "

    return Enemy(
        name=f"{title_prefix}{template.name}",
        stats=scaled_stats,
        tier=tier,
        floor_level=floor,
        exp_reward=exp_reward,
        gold_reward=gold_reward,
        archetype_id=template.id,
    )
