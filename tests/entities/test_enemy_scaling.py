import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.enemies import ENEMY_CATALOG
from src.entities.enemy import (
    ACT_3_BOSS_ATK_MULT,
    ACT_3_BOSS_HP_MULT,
    COMMON_ENEMY_SPEED_BONUS,
    EnemyTier,
    generate_enemy,
)


def test_act_3_boss_uses_reduced_scaling_from_floor_25() -> None:
    before_act_3 = generate_enemy(
        tier=EnemyTier.BOSS,
        floor=24,
        biome_id="observatory",
        rng=random.Random(11),
    )
    act_3_boss = generate_enemy(
        tier=EnemyTier.BOSS,
        floor=25,
        biome_id="observatory",
        rng=random.Random(11),
    )
    archetype = ENEMY_CATALOG[act_3_boss.archetype_id]

    assert act_3_boss.archetype_id == before_act_3.archetype_id
    assert act_3_boss.max_hp == int(
        archetype.base_hp * (1 + (25 - 1) * 0.045) * ACT_3_BOSS_HP_MULT
    )
    assert act_3_boss.base_stats.attack == int(
        archetype.base_atk * (1 + (25 - 1) * 0.030) * ACT_3_BOSS_ATK_MULT
    )
    assert before_act_3.max_hp > act_3_boss.max_hp
    assert before_act_3.base_stats.attack > act_3_boss.base_stats.attack


def test_non_boss_act_3_enemies_keep_standard_tier_scaling() -> None:
    enemy = generate_enemy(
        tier=EnemyTier.COMMON,
        floor=25,
        biome_id="observatory",
        rng=random.Random(11),
    )
    archetype = ENEMY_CATALOG[enemy.archetype_id]

    assert enemy.max_hp == int(archetype.base_hp * (1 + (25 - 1) * 0.045) * 1.25)
    assert enemy.base_stats.attack == int(archetype.base_atk * (1 + (25 - 1) * 0.030))


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
