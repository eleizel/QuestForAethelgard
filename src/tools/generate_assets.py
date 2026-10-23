"""Automated asset generator for Quest for Aethelgard.

Generates `assets/game.pyxres` containing:
- Bank 0: 16x16 characters & monsters, 8x8 item icons, basic map markers
- Bank 1: High-detail title screen art:
    - (0, 0, 144, 32):  Unified Gilded Title Plaque (No split, no bisecting sword)
    - (144, 0, 24, 28): Humanoid Gothic Lich / Necromancer in flowing robes
    - (168, 0, 24, 32): Stone Gargoyle on Battlement
    - (192, 0, 8, 8):   Gothic Corner Skull
    - (200, 0, 8, 8):   Glowing Sword Cursor
- 8-bit sound effects (Hit, Crit, Heal, Click, Victory, Defeat)
"""

from pathlib import Path
import pyxel


def build_assets() -> None:
    pyxel.init(256, 256, title="Asset Builder", headless=True)

    project_root = Path(__file__).resolve().parent.parent.parent
    assets_dir = project_root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    output_path = assets_dir / "game.pyxres"

    # =========================================================================
    # IMAGE BANK 0: CHARACTERS, ITEMS & MAP MARKERS
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

    # Item & Map Icons
    pyxel.images[0].set(64, 0, ["00044000","00077000","00766700","07888870","07878870","07888870","00788700","00077000"])
    pyxel.images[0].set(72, 0, ["00000007","000000aa","00000a90","00009400","05094000","00550000","04005000","40000000"])
    pyxel.images[0].set(80, 0, ["0aaaaaa0","a999999a","a949949a","a949949a","a994499a","0a9999a0","00a99a00","000aa000"])
    pyxel.images[0].set(88, 0, ["000a0000","00aaa000","009a9a00","098a8900","09888900","00444000","04444400","44000440"])
    pyxel.images[0].set(96, 0, ["00444400","04444440","04aaaa40","044aa440","444aa444","44444444","44444444","04444400"])

    pyxel.images[0].set(64, 8, ["000aa000","00077000","00788700","07888870","78788887","7888e887","07888870","00777700"])
    pyxel.images[0].set(72, 8, ["0c0770c0","00077000","007cc700","07cccc70","07c7cc70","07cccc70","007cc700","00077000"])
    pyxel.images[0].set(80, 8, ["000aa000","00aaaa00","0a9999a0","0a9449a0","0aaaaaa0","0a0440a0","00044000","00000000"])
    pyxel.images[0].set(88, 8, ["0a0000a0","aa9999aa","a99aa99a","a9aaaa9a","09a99a90","09999990","0a9999a0","00aaaa00"])
    pyxel.images[0].set(96, 8, ["00000000","04000000","04400440","0f4004f0","0ff44ff0","04ffff40","004ff400","00444400"])
    pyxel.images[0].set(104, 8, ["0aaaaaa0","04ffff40","04ffff40","04400440","04f00f40","04f00f40","04f00f40","04400440"])

    pyxel.images[0].set(0, 16, ["00ffff00","0ffffff0","4fffffff","44ffffff","44400444","44000044","04000040","00000000"])
    pyxel.images[0].set(8, 16, ["0aaa0aaa","a99aa99a","a94aa94a","aa4aaa4a","0aa00aa0","00000000","00000000","00000000"])
    pyxel.images[0].set(16, 16, ["00000000","00000000","44444444","ffffffff","ffaaaa4f","ffaaaa4f","ffffffff","44444444"])
    pyxel.images[0].set(24, 16, ["00000000","00000000","55555555","66666666","66755766","66555566","55555555","05555550"])
    pyxel.images[0].set(32, 16, ["00000007","00000067","00000650","00006500","00555000","02050000","20000000","00000000"])
    pyxel.images[0].set(40, 16, ["000000cc","00000ccc","00000cc0","00004000","00040000","00400000","04000000","40000000"])
    pyxel.images[0].set(48, 16, ["02222220","2aaaaaa2","2a2222a2","2a2c22a2","2a2cc2a2","2a2c22a2","2a2222a2","07777770"])
    pyxel.images[0].set(56, 16, ["00000989","000008e8","00000989","00004000","00040000","00400000","04000000","40000000"])
    pyxel.images[0].set(64, 16, ["00000077","00000766","00007660","00076600","05766000","55550000","04005000","40000000"])

    # =========================================================================
    # IMAGE BANK 1: REFINED GOTHIC TITLE ASSETS
    # =========================================================================

    # 1. Unified Gilded Title Plaque (144x32 at 0, 0 in Bank 1)
    def create_title_banner():
        W, H = 144, 32
        g = [["0" for _ in range(W)] for _ in range(H)]

        # Solid dark navy background
        for y in range(2, 30):
            for x in range(4, W - 4):
                g[y][x] = "1"

        # Outer gold border
        for x in range(4, W - 4):
            g[2][x] = "a"; g[3][x] = "9"
            g[28][x] = "9"; g[29][x] = "a"
        for y in range(2, 30):
            g[y][4] = "a"; g[y][5] = "9"
            g[y][W - 6] = "9"; g[y][W - 5] = "a"

        # Inner etched border
        for x in range(8, W - 8):
            g[5][x] = "4"; g[26][x] = "4"
        for y in range(5, 27):
            g[y][8] = "4"; g[y][W - 9] = "4"

        # Corner jewels
        for cy, cx in [(2, 4), (2, W - 6), (28, 4), (28, W - 6)]:
            g[cy][cx] = "7"

        # Side filigree accents
        for dx in range(12):
            g[16][12 + dx] = "a" if dx % 2 == 0 else "9"
            g[16][W - 13 - dx] = "a" if dx % 2 == 0 else "9"

        # "QUEST FOR" centered on line 1
        FONT_4x5 = {
            'Q': ["aaa0", "a0aa", "a0aa", "aaa0", "00aa"],
            'U': ["a00a", "a00a", "a00a", "a00a", "0aa0"],
            'E': ["aaaa", "a000", "aaaa", "a000", "aaaa"],
            'S': ["0aaa", "a000", "aaaa", "000a", "aaa0"],
            'T': ["aaaa", "0aa0", "0aa0", "0aa0", "0aa0"],
            ' ': ["0000", "0000", "0000", "0000", "0000"],
            'F': ["aaaa", "a000", "aaaa", "a000", "a000"],
            'O': ["0aa0", "a00a", "a00a", "a00a", "0aa0"],
            'R': ["aaa0", "a00a", "aaaa", "a0aa", "a00a"],
        }
        qx = 50
        for ch in "QUEST FOR":
            bm = FONT_4x5[ch]
            for r in range(5):
                for c in range(4):
                    if bm[r][c] != '0':
                        g[8 + r + 1][qx + c + 1] = "4"
                        g[8 + r][qx + c] = bm[r][c]
            qx += 5

        # "AETHELGARD" as a unified single continuous word on line 2
        FONT_5x7 = {
            'A': ["07770", "70007", "70007", "77777", "70007", "70007", "70007"],
            'E': ["77777", "70000", "77770", "70000", "70000", "70000", "77777"],
            'T': ["77777", "00700", "00700", "00700", "00700", "00700", "00700"],
            'H': ["70007", "70007", "70007", "77777", "70007", "70007", "70007"],
            'L': ["70000", "70000", "70000", "70000", "70000", "70000", "77777"],
            'G': ["07777", "70000", "70000", "70777", "70007", "70007", "07777"],
            'R': ["77770", "70007", "70007", "77770", "70700", "70070", "70007"],
            'D': ["77770", "70007", "70007", "70007", "70007", "70007", "77770"],
        }
        ax = 43
        for ch in "AETHELGARD":
            bm = FONT_5x7[ch]
            for r in range(7):
                for c in range(5):
                    if bm[r][c] != '0':
                        g[17 + r + 1][ax + c + 1] = "5"
                        g[17 + r][ax + c] = bm[r][c]
            ax += 6

        return ["".join(row) for row in g]

    pyxel.images[1].set(0, 0, create_title_banner())

    # 2. Humanoid Gothic Lich / Necromancer (24x28 at 144, 0 in Bank 1)
    def create_humanoid_lich():
        W, H = 24, 28
        g = [["0" for _ in range(W)] for _ in range(H)]

        # Crystal Staff on right
        g[2][20] = "c"; g[2][21] = "7"; g[1][20] = "c"; g[1][21] = "c"
        g[3][19] = "a"; g[3][22] = "a"; g[4][20] = "a"; g[4][21] = "a"
        for sy in range(5, 27):
            g[sy][21] = "4"
        g[13][21] = "7"; g[14][21] = "7"  # Bony hand gripping staff

        # Dark Cowl / Hood
        for x in range(9, 14): g[3][x] = "1"
        for x in range(8, 15): g[4][x] = "1"
        g[4][10] = "2"; g[4][11] = "2"; g[4][12] = "2"
        g[2][11] = "1"; g[1][11] = "a"

        # Inner shadow
        for y in range(5, 10):
            for x in range(9, 14):
                g[y][x] = "0"

        # Bone Skull
        g[5][10] = "7"; g[5][11] = "7"; g[5][12] = "7"
        g[6][10] = "e"; g[6][11] = "7"; g[6][12] = "e"  # Glowing red/pink eye sockets
        g[7][10] = "7"; g[7][11] = "0"; g[7][12] = "7"
        g[8][10] = "7"; g[8][11] = "5"; g[8][12] = "7"

        # Shoulder mantle & golden clasp
        for y in range(9, 12):
            w = (y - 8) * 3 + 2
            for x in range(11 - w // 2, 11 + w // 2 + 1):
                if 0 <= x < W and g[y][x] == "0":
                    g[y][x] = "2" if (x + y) % 2 == 0 else "1"
        g[10][11] = "a"; g[11][11] = "9"

        # Outstretched skeletal arm casting cyan sparks
        g[11][7] = "2"; g[11][6] = "1"; g[12][6] = "2"; g[12][5] = "1"
        g[13][5] = "2"; g[13][4] = "1"
        g[12][3] = "7"; g[12][4] = "7"
        g[11][2] = "7"; g[12][1] = "c"; g[13][2] = "7"
        g[11][0] = "c"; g[12][0] = "7"; g[13][1] = "c"

        # Flowing Robes
        for y in range(12, 18):
            for x in range(8, 15):
                if g[y][x] == "0":
                    g[y][x] = "1" if (x == 8 or x == 14) else "2"
        for y in range(14, 26):
            g[y][11] = "0"
            g[y][9] = "1"; g[y][13] = "1"

        for y in range(18, 27):
            half_w = 4 + int((y - 18) * 0.7)
            for x in range(11 - half_w, 11 + half_w + 1):
                if 0 <= x < W and g[y][x] == "0":
                    g[y][x] = "2" if (x + y) % 3 != 0 else "1"

        # Tattered hem
        for x in range(4, 19):
            if (x * 7) % 3 == 0:
                g[26][x] = "0"; g[27][x] = "0"
            elif g[26][x] != "0":
                g[27][x] = "1"

        return ["".join(row) for row in g]

    pyxel.images[1].set(144, 0, create_humanoid_lich())

    # 3. Stone Gargoyle on Battlement (24x32 at 168, 0 in Bank 1)
    def create_gargoyle():
        W, H = 24, 32
        g = [["0" for _ in range(W)] for _ in range(H)]
        for y in range(22, 32):
            for x in range(2, 22):
                g[y][x] = "5"
        for x in range(2, 22):
            g[22][x] = "6"; g[31][x] = "1"
        for y in range(23, 31):
            g[y][2] = "6"; g[y][21] = "1"
            if y == 27:
                for x in range(2, 22): g[y][x] = "1"

        beast_rows = [
            (2, 8, "0500050"),
            (3, 7, "0550550"),
            (4, 6, "5665665"),
            (5, 5, "56666665"),
            (6, 6, "5866685"),
            (7, 6, "5566655"),
            (8, 7, "55555"),
            (9, 4, "5665555665"),
            (10, 3, "566665566665"),
            (11, 2, "5666666556666665"),
            (12, 2, "5655666556665565"),
            (13, 2, "5500566666650055"),
            (14, 6, "56655665"),
            (15, 6, "56655665"),
            (16, 6, "55555555"),
            (17, 5, "565000565"),
            (18, 5, "565000565"),
            (19, 4, "5555005555"),
            (20, 3, "666666666666"),
            (21, 2, "55555555555555"),
        ]
        for y, start_x, row in beast_rows:
            for i, ch in enumerate(row):
                if ch != '0':
                    g[y][start_x + i] = ch

        return ["".join(row) for row in g]

    pyxel.images[1].set(168, 0, create_gargoyle())

    # 4. Corner Skull (8x8 at 192, 0 in Bank 1)
    pyxel.images[1].set(192, 0, [
        "07777770", "77777777", "78777787", "70777707",
        "07700770", "00777700", "00755700", "00000000"
    ])

    # 5. Glowing Sword Cursor (8x8 at 200, 0 in Bank 1)
    pyxel.images[1].set(200, 0, [
        "00000007", "0000007c", "000007c0", "0a007c00",
        "0aa7c000", "00aa0000", "040aa000", "4000a000"
    ])

    # Sound Effects
    pyxel.sounds[0].set("g2c2", "n", "74", "s", 6)
    pyxel.sounds[1].set("c3g3c4", "t", "777", "n", 4)
    pyxel.sounds[2].set("c3e3g3c4", "p", "5567", "f", 7)
    pyxel.sounds[3].set("g3c4", "p", "45", "n", 3)
    pyxel.sounds[4].set("c3e3g3c4e4g4", "t", "666777", "v", 12)
    pyxel.sounds[5].set("f3e3d3c3", "s", "7654", "f", 16)

    pyxel.save(str(output_path))
    print(f"Successfully generated asset package: {output_path}")


if __name__ == "__main__":
    build_assets()