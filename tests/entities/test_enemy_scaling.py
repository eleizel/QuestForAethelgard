import random
import sys
from math import ceil
from pathlib import Path
from statistics import mean

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.enemies import ENEMY_CATALOG
from src.data.biomes import BIOME_REGISTRY
from src.entities.enemy import (
    ACT_2_BOSS_ATK_MULT,
    ACT_2_BOSS_HP_OVER_ELITE_RATIO,
    ACT_3_BOSS_ATK_MULT,
    ACT_3_BOSS_HP_OVER_ELITE_RATIO,
    ACT_3_ENEMY_ATK_MULT,
    ACT_3_ENEMY_DEF_MULT,
    ACT_3_ENEMY_HP_MULT,
    BOSS_HP_OVER_ELITE_RATIO,
    COMMON_ENEMY_SPEED_BONUS,
    ENEMY_ATK_GROWTH_PER_FLOOR,
    ENEMY_DEF_GROWTH_PER_FLOOR,
    ENEMY_HP_GROWTH_PER_FLOOR,
    MIN_ENEMY_SPEED_RATIO,
    TIER_HP_MULT,
    EnemyTier,
    generate_enemy,
)


def test_boss_health_is_normalized_to_one_and_a_half_times_biome_elite_average() -> None:
    act_3_boss = generate_enemy(
        tier=EnemyTier.BOSS,
        floor=25,
        biome_id="observatory",
        rng=random.Random(11),
    )
    archetype = ENEMY_CATALOG[act_3_boss.archetype_id]
    biome = BIOME_REGISTRY["observatory"]
    elite_mean_hp = sum(ENEMY_CATALOG[enemy_id].base_hp for enemy_id in biome.elites) / len(biome.elites)
    boss_mean_hp = sum(ENEMY_CATALOG[enemy_id].base_hp for enemy_id in biome.bosses) / len(biome.bosses)
    expected_hp_multiplier = (
        TIER_HP_MULT[EnemyTier.ELITE]
        * ACT_3_BOSS_HP_OVER_ELITE_RATIO
        * elite_mean_hp
        / boss_mean_hp
        * ACT_3_ENEMY_HP_MULT
    )

    assert act_3_boss.max_hp == int(
        archetype.base_hp * (1 + (25 - 1) * ENEMY_HP_GROWTH_PER_FLOOR) * expected_hp_multiplier
    )
    assert act_3_boss.base_stats.attack == int(
        archetype.base_atk
        * (1 + (25 - 1) * ENEMY_ATK_GROWTH_PER_FLOOR)
        * ACT_3_BOSS_ATK_MULT
        * ACT_3_ENEMY_ATK_MULT
    )
    assert BOSS_HP_OVER_ELITE_RATIO == 1.5
    assert ACT_2_BOSS_HP_OVER_ELITE_RATIO == 1.25
    assert ACT_2_BOSS_ATK_MULT == 1.20
    assert ACT_3_BOSS_HP_OVER_ELITE_RATIO == 1.25
    assert ACT_3_BOSS_ATK_MULT == 1.20
    assert (ACT_3_ENEMY_HP_MULT, ACT_3_ENEMY_ATK_MULT, ACT_3_ENEMY_DEF_MULT) == (
        0.90,
        0.90,
        0.90,
    )


def test_generated_act_3_boss_health_averages_one_and_a_quarter_times_elites() -> None:
    class FixedChoiceRng:
        def __init__(self, selected_id: str) -> None:
            self.selected_id = selected_id

        def choice(self, options: tuple[str, ...]) -> str:
            assert self.selected_id in options
            return self.selected_id

        def randint(self, _minimum: int, _maximum: int) -> int:
            return 10

    for biome in BIOME_REGISTRY.values():
        elite_health = [
            generate_enemy(
                tier=EnemyTier.ELITE,
                floor=30,
                biome_id=biome.id,
                rng=FixedChoiceRng(enemy_id),
            ).max_hp
            for enemy_id in biome.elites
        ]
        boss_health = [
            generate_enemy(
                tier=EnemyTier.BOSS,
                floor=30,
                biome_id=biome.id,
                rng=FixedChoiceRng(enemy_id),
            ).max_hp
            for enemy_id in biome.bosses
        ]

        assert mean(boss_health) / mean(elite_health) == pytest.approx(
            ACT_3_BOSS_HP_OVER_ELITE_RATIO, abs=0.01
        )


def test_non_boss_act_3_enemies_keep_standard_tier_scaling() -> None:
    enemy = generate_enemy(
        tier=EnemyTier.COMMON,
        floor=25,
        biome_id="observatory",
        rng=random.Random(11),
    )
    archetype = ENEMY_CATALOG[enemy.archetype_id]

    assert enemy.max_hp == int(
        archetype.base_hp
        * (1 + (25 - 1) * ENEMY_HP_GROWTH_PER_FLOOR)
        * TIER_HP_MULT[EnemyTier.COMMON]
        * ACT_3_ENEMY_HP_MULT
    )
    assert enemy.base_stats.attack == int(
        archetype.base_atk
        * (1 + (25 - 1) * ENEMY_ATK_GROWTH_PER_FLOOR)
        * ACT_3_ENEMY_ATK_MULT
    )
    assert enemy.base_stats.defense == int(
        archetype.base_def
        * (1 + (25 - 1) * ENEMY_DEF_GROWTH_PER_FLOOR)
        * ACT_3_ENEMY_DEF_MULT
    )


def test_common_enemy_has_25_percent_health_buffer() -> None:
    enemy = generate_enemy(
        tier=EnemyTier.COMMON,
        floor=1,
        biome_id="arboretum",
        rng=random.Random(11),
    )
    archetype = ENEMY_CATALOG[enemy.archetype_id]

    assert enemy.max_hp == int(archetype.base_hp * 1.25)
    assert enemy.base_stats.speed == min(25, archetype.base_spd + COMMON_ENEMY_SPEED_BONUS)


def test_non_common_enemies_do_not_get_common_speed_bonus() -> None:
    enemy = generate_enemy(
        tier=EnemyTier.ELITE,
        floor=1,
        biome_id="arboretum",
        rng=random.Random(11),
    )
    archetype = ENEMY_CATALOG[enemy.archetype_id]

    assert enemy.base_stats.speed == archetype.base_spd


def test_enemy_speed_never_lags_player_natural_speed_by_over_twenty_percent() -> None:
    natural_player_speed = 50
    minimum_enemy_speed = ceil(natural_player_speed * MIN_ENEMY_SPEED_RATIO)

    for tier in EnemyTier:
        enemy = generate_enemy(
            tier=tier,
            floor=12,
            biome_id="arboretum",
            rng=random.Random(21),
            player_speed=natural_player_speed,
        )

        assert enemy.base_stats.speed >= minimum_enemy_speed


def test_targeted_act_1_and_act_3_boss_tuning() -> None:
    assert ENEMY_CATALOG["chorus_of_damned"].base_hp == 190
    assert ENEMY_CATALOG["malignant_belladonna"].status_chance == 0.40

    chronomancer = ENEMY_CATALOG["chronomancer_praetor"]
    assert (chronomancer.base_hp, chronomancer.base_atk, chronomancer.status_chance) == (
        400,
        39,
        0.20,
    )

    carmilla = ENEMY_CATALOG["high_lord_carmilla"]
    assert (carmilla.base_hp, carmilla.base_atk) == (420, 42)

    blood_god = ENEMY_CATALOG["blood_god_avatar"]
    assert (blood_god.base_hp, blood_god.base_atk) == (450, 46)


def test_enemy_attack_and_defense_keep_scaling_at_high_floors() -> None:
    enemy = generate_enemy(
        tier=EnemyTier.ELITE,
        floor=42,
        biome_id="observatory",
        rng=random.Random(11),
    )
    archetype = ENEMY_CATALOG[enemy.archetype_id]

    assert enemy.base_stats.attack == int(
        archetype.base_atk * (1 + (42 - 1) * ENEMY_ATK_GROWTH_PER_FLOOR) * 1.25
    )
    assert enemy.base_stats.defense == int(
        archetype.base_def * (1 + (42 - 1) * ENEMY_DEF_GROWTH_PER_FLOOR)
    )
    assert ENEMY_ATK_GROWTH_PER_FLOOR == 0.05
    assert ENEMY_DEF_GROWTH_PER_FLOOR == 0.05
