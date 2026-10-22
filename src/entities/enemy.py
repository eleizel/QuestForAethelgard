"""Enemy entity generation, tier scaling, and encounter balancing."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Final

from src.entities.actor import Actor, Stats


class EnemyTier(Enum):
    """Enemy danger tier."""

    COMMON = 1
    UNCOMMON = 2
    ELITE = 3
    BOSS = 4


@dataclass
class EnemyArchetype:
    """Base template for generating distinct enemy varieties."""

    name: str
    base_hp: int
    base_atk: int
    base_def: int
    base_spd: int
    base_crit: float


ARCHETYPES: Final[list[EnemyArchetype]] = [
    EnemyArchetype("Goblin Scavenger", base_hp=30, base_atk=6, base_def=1, base_spd=11, base_crit=0.08),
    EnemyArchetype("Skeleton Warrior", base_hp=45, base_atk=8, base_def=3, base_spd=7, base_crit=0.04),
    EnemyArchetype("Corrupted Cultist", base_hp=35, base_atk=12, base_def=2, base_spd=9, base_crit=0.10),
    EnemyArchetype("Cave Troll", base_hp=80, base_atk=14, base_def=6, base_spd=4, base_crit=0.02),
    EnemyArchetype("Shadow Assassin", base_hp=40, base_atk=16, base_def=2, base_spd=14, base_crit=0.20),
    EnemyArchetype("Iron Golem", base_hp=100, base_atk=11, base_def=10, base_spd=3, base_crit=0.01),
]

BOSS_ARCHETYPES: Final[list[EnemyArchetype]] = [
    EnemyArchetype("Aethelgard Lich King", base_hp=220, base_atk=22, base_def=8, base_spd=8, base_crit=0.12),
    EnemyArchetype("Ancient Red Dragon", base_hp=300, base_atk=26, base_def=12, base_spd=10, base_crit=0.15),
]


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
    ) -> None:
        super().__init__(name=name, base_stats=stats)
        self.tier: EnemyTier = tier
        self.floor_level: int = floor_level
        self.exp_reward: int = exp_reward
        self.gold_reward: int = gold_reward


def generate_enemy(
    tier: EnemyTier = EnemyTier.COMMON,
    floor: int = 1,
    rng: random.Random | None = None,
) -> Enemy:
    """Generate a tier-scaled enemy tailored to the current dungeon floor."""
    rand = rng if rng is not None else random.Random()

    if tier == EnemyTier.BOSS:
        template = rand.choice(BOSS_ARCHETYPES)
        multiplier = 1.0 + (floor * 0.15)
    else:
        template = rand.choice(ARCHETYPES)
        tier_multipliers = {
            EnemyTier.COMMON: 1.0,
            EnemyTier.UNCOMMON: 1.3,
            EnemyTier.ELITE: 1.8,
        }
        multiplier = tier_multipliers.get(tier, 1.0) * (1.0 + (floor - 1) * 0.08)

    scaled_stats = Stats(
        max_hp=int(template.base_hp * multiplier),
        attack=int(template.base_atk * multiplier),
        defense=int(template.base_def * multiplier),
        speed=max(1, int(template.base_spd * (1.0 + floor * 0.02))),
        crit_chance=template.base_crit,
    )

    exp_reward = int(20 * multiplier * tier.value)
    gold_reward = int(rand.randint(5, 15) * multiplier * tier.value)

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
    )
