def calculate_damage(
    raw_dmg: int,
    defense: int,
    defense_penetration: float = 0.0,
) -> int:
    penetration = max(0.0, min(1.0, defense_penetration))
    effective_defense = max(0, int(defense * (1 - penetration)))

    flat_reduction = effective_defense // 5
    remaining_damage = max(0, raw_dmg - flat_reduction)

    mitigation = min(
        0.60,
        effective_defense / (effective_defense + 100)
    )

    return max(1, int(remaining_damage * (1 - mitigation)))


def calculate_exp_threshold(level: int) -> int:
    return int(50 + 15 * (level - 1) + 7 * (level - 1) ** 2)
