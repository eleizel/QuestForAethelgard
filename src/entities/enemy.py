"""Biomed Enemy Archetypes with specialized tier balance."""

from __future__ import annotations

import random
from enum import Enum

from src.entities.actor import Actor, Stats


class EnemyTier(Enum):
    COMMON = 1
    UNCOMMON = 2
    ELITE = 3
    BOSS = 4


from src.data.enemies import ENEMY_CATALOG


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
        if archetype:
            self.on_hit_status: str | None = archetype.on_hit_status
            self.status_chance: float = archetype.status_chance
        else:
            self.on_hit_status: str | None = None
            self.status_chance: float = 0.0

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
) -> Enemy:
    """Generate a tier-scaled enemy tailored to the current biome and floor."""
    from src.data.biomes import BIOME_REGISTRY

    rand = rng if rng is not None else random.Random()
    biome = BIOME_REGISTRY.get(biome_id, BIOME_REGISTRY["arboretum"])

    if tier == EnemyTier.BOSS:
        arch_id = rand.choice(biome.bosses)
        multiplier = 1.0 + (floor * 0.05)
    elif tier == EnemyTier.ELITE:
        arch_id = rand.choice(biome.elites)
        multiplier = 1.0 + (floor * 0.04)
    else:  # COMMON or UNCOMMON
        arch_id = rand.choice(biome.basic_enemies)
        tier_mult = 1.0 if tier == EnemyTier.COMMON else 1.25
        multiplier = tier_mult * (1.0 + (floor - 1) * 0.035)

    template = ENEMY_CATALOG.get(arch_id, ENEMY_CATALOG["thornvein_creeper"])

    scaled_stats = Stats(
        max_hp=int(template.base_hp * multiplier),
        attack=int(template.base_atk * multiplier),
        defense=int(template.base_def * multiplier),
        speed=max(1, int(template.base_spd * (1.0 + floor * 0.015))),
        crit_chance=template.base_crit,
    )

    exp_reward = int(50 * multiplier * tier.value)
    gold_reward = int(rand.randint(6, 16) * multiplier * tier.value)

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
