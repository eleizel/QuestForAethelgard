"""Automated asset generator for Quest for Aethelgard.

Generates `assets/game.pyxres` containing:
- 16x16 character & monster sprites (Hero, Skeleton, Goblin, Boss)
- 8x8 item & map icons (Potion, Sword, Shield, Chest, Campfire)
- 8-bit sound effects (Hit, Crit, Heal, Click, Victory, Defeat)
"""

from pathlib import Path
import pyxel


def build_assets() -> None:
    # Initialize in headless mode so no display window is required
    pyxel.init(256, 256, title="Asset Builder", headless=True)

    # Resolve project root (two levels up from src/tools/)
    project_root = Path(__file__).resolve().parent.parent.parent
    assets_dir = project_root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    output_path = assets_dir / "game.pyxres"

    # =========================================================================
    # 1. SPRITES (Image Bank 0)
    # =========================================================================

    # Hero (16x16) at (0, 0)
    hero_sprite = [
        "00000aaa00000000",
        "0000aaaaa0000000",
        "0000077700000000",
        "0000776770000000",
        "0000700070000000",
        "0000777770000000",
        "0008811188000000",
        "0088716178870000",
        "0888766678877000",
        "08086666680a7000",
        "080865556800a000",
        "0000555550000000",
        "0000550550000000",
        "0000660660000000",
        "0000660660000000",
        "0000550550000000",
    ]
    pyxel.images[0].set(0, 0, hero_sprite)

    # Skeleton Warrior (16x16) at (16, 0)
    skeleton_sprite = [
        "0000077700000000",
        "0000777770000000",
        "0000787870000000",
        "0000777770000000",
        "0000070700000000",
        "0000007000000000",
        "0055077705000000",
        "0566570756500000",
        "0566577705600000",
        "0055070700560000",
        "0000077700044000",
        "0000007000000000",
        "0000070700000000",
        "0000070700000000",
        "0000070700000000",
        "0000550550000000",
    ]
    pyxel.images[0].set(16, 0, skeleton_sprite)

    # Goblin Scavenger (16x16) at (32, 0)
    goblin_sprite = [
        "0000000000000000",
        "0030000000030000",
        "03b30bbbb03b3000",
        "03bbbbbbbbb30000",
        "003bb8bb8bb30000",
        "000bbbaabbb00000",
        "0000bbbb00000000",
        "0004444440000000",
        "004444e444070000",
        "0444444444460000",
        "00044444440a0000",
        "0004000040000000",
        "0033000033000000",
        "0033000033000000",
        "0044000044000000",
        "0000000000000000",
    ]
    pyxel.images[0].set(32, 0, goblin_sprite)

    # Boss: Lich King (16x16) at (48, 0)
    boss_sprite = [
        "000a0000000a0000",
        "000aa00a00aa0000",
        "0002aaaaaaa20000",
        "0022222222220000",
        "0222222222222000",
        "0222c2222c222000",
        "022ccc22ccc22000",
        "0022c0220c220000",
        "0002227722200000",
        "0022211112220000",
        "0222111111222000",
        "022111a111122000",
        "02211aaaa1122000",
        "0021111111120000",
        "0022111111220000",
        "0002222222200000",
    ]
    pyxel.images[0].set(48, 0, boss_sprite)

    # Health Potion (8x8) at (64, 0)
    potion_sprite = [
        "00044000",
        "00077000",
        "00766700",
        "07888870",
        "07878870",
        "07888870",
        "00788700",
        "00077000",
    ]
    pyxel.images[0].set(64, 0, potion_sprite)

    # Iron Sword (8x8) at (72, 0)
    sword_sprite = [
        "00000007",
        "00000076",
        "00000760",
        "00007600",
        "0a076000",
        "00aa0000",
        "0400a000",
        "40000000",
    ]
    pyxel.images[0].set(72, 0, sword_sprite)

    # Shield (8x8) at (80, 0)
    shield_sprite = [
        "0aaaaaa0",
        "a111111a",
        "a11c111a",
        "a1ccc11a",
        "a11c111a",
        "0a1111a0",
        "00a11a00",
        "000aa000",
    ]
    pyxel.images[0].set(80, 0, shield_sprite)

    # Campfire (8x8) at (88, 0)
    campfire_sprite = [
        "000a0000",
        "00aaa000",
        "009a9a00",
        "098a8900",
        "09888900",
        "00444000",
        "04444400",
        "44000440",
    ]
    pyxel.images[0].set(88, 0, campfire_sprite)


    # Game Title Text / Pixel Art (64x16) at (0, 112)
    game_title_sprite = [
        "0000000000000000000000000000000000000000000000000000000000000000",
        "0000a000000000000000000a0000000000000000000000000000000000000000",
        "0000aa0000000a00000000aa0000000000000000000000000000000000000000",
        "0000aaa00000aa0000000aaa0000000000000000000000000000000000000000",
        "0000aaaa000aaa000000aaaa0000000000000000000000000000000000000000",
        "0000aaaa000aaa000000aaaa0000000000000000000000000000000000000000",
        "0000aaaa000aaa000000aaaa0000000000000000000000000000000000000000",
        "0000aaaaaaaaaa000000aaaa0000000000000000000000000000000000000000",
        "0000aaaaaaaaaa000000aaaa0000000000000000000000000000000000000000",
        "0000aaaa000aaa000000aaaa0000000000000000000000000000000000000000",
        "0000aaaa000aaa000000aaaa0000000000000000000000000000000000000000",
        "0000aaaa000aaa000000aaaa0000000000000000000000000000000000000000",
        "0000aaa00000aa0000000aaa0000000000000000000000000000000000000000",
        "0000aa0000000a00000000aa0000000000000000000000000000000000000000",
        "0000a000000000000000000a0000000000000000000000000000000000000000",
        "0000000000000000000000000000000000000000000000000000000000000000",
    ]
    pyxel.images[0].set(0, 112, game_title_sprite)

    # Treasure Chest (8x8) at (96, 0)
    chest_sprite = [
        "00444400",
        "04444440",
        "04aaaa40",
        "044aa440",
        "444aa444",
        "44444444",
        "44444444",
        "04444400",
    ]
    pyxel.images[0].set(96, 0, chest_sprite)

    # =========================================================================
    # 2. SOUND EFFECTS (Notes limited strictly to octaves 0 through 4)
    # =========================================================================

    # Sound 0: Normal Attack (Slash / Impact)
    pyxel.sounds[0].set("g2c2", "n", "74", "s", 6)

    # Sound 1: Critical Hit (High chime - notes adjusted to max octave 4)
    pyxel.sounds[1].set("c3g3c4", "t", "777", "n", 4)

    # Sound 2: Potion Use (Ascending heal arpeggio)
    pyxel.sounds[2].set("c3e3g3c4", "p", "5567", "f", 7)

    # Sound 3: Menu / Node Selection click
    pyxel.sounds[3].set("g3c4", "p", "45", "n", 3)

    # Sound 4: Victory Fanfare
    pyxel.sounds[4].set("c3e3g3c4e4g4", "t", "666777", "v", 12)

    # Sound 5: Defeat Sting
    pyxel.sounds[5].set("f3e3d3c3", "s", "7654", "f", 16)

    # =========================================================================
    # 3. SAVE RESOURCE FILE
    # =========================================================================
    pyxel.save(str(output_path))
    print(f"Successfully generated prototype asset package: {output_path}")


if __name__ == "__main__":
    build_assets()