def calculate_damage(raw_attack: int, defense: int) -> int:
    return max(1, raw_attack - (defense // 2))


def calculate_exp_threshold(level: int) -> int:
    return int(50 + 15 * (level - 1) + 7 * (level - 1) ** 2)
