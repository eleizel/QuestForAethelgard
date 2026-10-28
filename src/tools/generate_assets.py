"""Automated asset generator for Quest for Aethelgard.

Generates `assets/game.pyxres` containing:
- Bank 0:
    - 16x16 Playable Characters & NPCs:
        - Warrior (Hero):      (0, 0)
        - Rogue:               (0, 32)
        - Mage:                (16, 32)
        - Wandering Merchant:  (32, 32)
    - 16x16 Biome Enemy Roster (48 Enemies total):
        - Row y=48:  Act 1A - The Wilted Arboretum (8 enemies)
        - Row y=64:  Act 1B - The Desecrated Cathedral (8 enemies)
        - Row y=80:  Act 2A - The Drowned Ossuary (8 enemies)
        - Row y=96:  Act 2B - The Foundry of Torment (8 enemies)
        - Row y=112: Act 3A - The Astral Observatory (8 enemies)
        - Row y=128: Act 3B - The Blood Sanctum (8 enemies)
    - 8x8 Item, Currency & Map Icons:
        - Row y=0:  Potion (64, 0), Sword (72, 0), Shield (80, 0), Campfire (88, 0), Chest (96, 0), Shop Pouch (104, 0)
        - Row y=8:  Flask (64, 8), Elixir (72, 8), Helmet (80, 8), Chestplate (88, 8), Gloves (96, 8), Pants (104, 8)
        - Row y=16: Mantle (0, 16), Pauldrons (8, 16), Belt (16, 16), Girdle (24, 16), Dagger (32, 16), Wand (40, 16), Grimoire (48, 16), Staff (56, 16), Claymore (64, 16)
        - Row y=24: Worn Dagger (0, 24), Parrying Dirk (8, 24), Gnarled Wand (16, 24), Tattered Grimoire (24, 24), Stat Elixir (32, 24), Gold Coin (40, 24)
- Bank 1: High-detail gothic title screen art (Plaque, Lich, Gargoyle, Skulls, Cursor)
- 8-bit sound effects (Hit, Crit, Heal, Click, Victory, Defeat)
"""

from pathlib import Path
from typing import Final

import pyxel

# =============================================================================
# ENEMY SPRITE COORDINATES (Image Bank 0)
# =============================================================================
ENEMY_SPRITE_COORDS: Final[dict[str, tuple[int, int]]] = {
    # 1A. The Wilted Arboretum (y=48)
    "thornvein_creeper": (0, 48),
    "spore_pod": (16, 48),
    "bramble_hound": (32, 48),
    "rotting_woodwose": (48, 48),
    "mandragora_matron": (64, 48),
    "corpse_treant": (80, 48),
    "malignant_belladonna": (96, 48),
    "verdant_abomination": (112, 48),

    # 1B. The Desecrated Cathedral (y=64)
    "cathedral_imp": (0, 64),
    "possessed_grimoire": (16, 64),
    "candelabra_fiend": (32, 64),
    "penitent_zealot": (48, 64),
    "belltower_gargoyle": (64, 64),
    "inquisitor_automaton": (80, 64),
    "blind_archbishop": (96, 64),
    "chorus_of_damned": (112, 64),

    # 2A. The Drowned Ossuary (y=80)
    "mire_ghoul": (0, 80),
    "drowned_skulls": (16, 80),
    "leech_husk": (32, 80),
    "crypt_lurker": (48, 80),
    "tide_gravekeeper": (64, 80),
    "carrion_behemoth": (80, 80),
    "drowned_patriarch": (96, 80),
    "scylla_bone_weaver": (112, 80),

    # 2B. The Foundry of Torment (y=96)
    "slag_homunculus": (0, 96),
    "cinder_sprite": (16, 96),
    "clockwork_flayer": (32, 96),
    "ashen_overseer": (48, 96),
    "furnace_warden": (64, 96),
    "retching_alchemist": (80, 96),
    "ironforge_tyrant": (96, 96),
    "molten_sovereign": (112, 96),

    # 3A. The Astral Observatory (y=112)
    "void_mirror": (0, 112),
    "stareater_wisp": (16, 112),
    "comet_stalker": (32, 112),
    "celestial_hermit": (48, 112),
    "rift_warden": (64, 112),
    "null_singularity": (80, 112),
    "chronomancer_praetor": (96, 112),
    "devouring_constellation": (112, 112),

    # 3B. The Blood Sanctum (y=128)
    "sanguine_thrall": (0, 128),
    "crimson_gargoyle": (16, 128),
    "hemomancer_acolyte": (32, 128),
    "flayed_duelist": (48, 128),
    "baroness_vespera": (64, 128),
    "amalgam_of_veins": (80, 128),
    "high_lord_carmilla": (96, 128),
    "blood_god_avatar": (112, 128),
}

# =============================================================================
# CLASS PORTRAIT COORDINATES (Image Bank 0: 48x64 pixels)
# =============================================================================
CLASS_PORTRAIT_COORDS: Final[dict[str, tuple[int, int]]] = {
    "warrior": (0, 144),
    "rogue": (48, 144),
    "mage": (96, 144),
}

# =============================================================================
# ABILITY ICON SPRITE COORDINATES (Image Bank 1: 16x16 pixels)
# =============================================================================

ABILITY_ICON_COORDS: Final[dict[str, tuple[int, int]]] = {
    # Starters (Row y=32)
    "cross_cut": (0, 32),
    "shadow_strike": (16, 32),
    "arcane_bolt": (32, 32),
    "pw_kill": (48, 32),
    # Warrior Standard (Row y=32 continuing & Row y=48)
    "shield_bash": (64, 32),
    "rallying_cry": (80, 32),
    "cleave": (96, 32),
    "iron_skin": (112, 32),
    "veterans_instincts": (128, 32),
    "bloodlust": (144, 32),
    "shieldbreaker_strike": (160, 32),
    "defensive_superiority": (176, 32),
    "paladin_guard": (192, 32),
    "reckless_assault": (208, 32),
    "blood_frenzy": (224, 32),
    "cull_the_weak": (240, 32),
    # Rogue Standard (Row y=48)
    "poison_shiv": (0, 48),
    "dirty_tricks": (16, 48),
    "flurry_of_daggers": (32, 48),
    "nimble_reflexes": (48, 48),
    "exposed_weakness": (64, 48),
    "shadow_step": (80, 48),
    "venomous_accumulation": (96, 48),
    "toxic_blood": (112, 48),
    "venomous_extraction": (128, 48),
    "riposte": (144, 48),
    "whirlwind_defense": (160, 48),
    "hilt_strike": (176, 48),
    # Mage Standard (Row y=48 continuing & Row y=64)
    "fireball": (192, 48),
    "chain_lightning": (208, 48),
    "creeping_hands": (224, 48),
    "soulfire": (240, 48),
    "bone_barrier": (0, 64),
    "summon_imp": (16, 64),
    "soul_siphon": (32, 64),
    "pact_of_pain": (48, 64),
    "ice_shards": (64, 64),
    "arcane_missiles": (80, 64),
    "arcane_reservoir": (96, 64),
    "spell_echo": (112, 64),
    # Warrior Epic (Row y=64 continuing)
    "colossus_stance": (128, 64),
    "blade_storm": (144, 64),
    "undying_will": (160, 64),
    "executioners_might": (176, 64),
    # Rogue Epic (Row y=64 continuing & Row y=80)
    "assassinate": (192, 64),
    "fan_of_knives": (208, 64),
    "shadow_dance": (224, 64),
    "death_dealer": (240, 64),
    # Mage Epic (Row y=80)
    "meteor": (0, 80),
    "time_stop": (16, 80),
    "time_dilation": (32, 80),
    "phoenix_rebirth": (48, 80),
    # Fallback / Default
    "default": (64, 80),
}


def build_assets() -> None:
    pyxel.init(256, 256, title="Asset Builder", headless=True)

    project_root = Path(__file__).resolve().parent.parent.parent
    assets_dir = project_root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    output_path = assets_dir / "game.pyxres"

    # =========================================================================
    # IMAGE BANK 0: CHARACTERS, NPCS & ITEMS
    # =========================================================================
    def create_warrior_portrait() -> list[str]:
        """Generates 48x64 detailed portrait for Warrior (Hero)."""
        W, H = 48, 64
        g = [["0"] * W for _ in range(H)]

        # Gothic Halo Arch in background
        for y in range(4, 38):
            for x in range(6, 42):
                dx = x - 24
                dy = y - 20
                d2 = dx * dx + dy * dy
                if 144 <= d2 <= 289:
                    g[y][x] = "1"
                elif 290 <= d2 <= 360 and (x + y) % 2 == 0:
                    g[y][x] = "5"

        # Red Mantle / Cloak draped behind shoulders
        for y in range(24, 64):
            w_cloak = min(22, int((y - 20) * 0.7) + 6)
            for x in range(24 - w_cloak, 24 + w_cloak + 1):
                if 0 <= x < W:
                    g[y][x] = "8"
                    if x < 12 or x > 35:
                        g[y][x] = "2" if (x + y) % 3 == 0 else "8"
                    elif x in (24 - w_cloak, 24 + w_cloak):
                        g[y][x] = "2"

        # Golden Swept Hair & Volume
        hair_coords = [
            (6, 20, 28), (7, 18, 30), (8, 16, 32), (9, 15, 33), (10, 14, 34),
            (11, 13, 35), (12, 13, 35), (13, 12, 36), (14, 12, 36), (15, 12, 36),
            (16, 12, 36), (17, 12, 36), (18, 12, 36), (19, 13, 35), (20, 13, 35),
            (21, 14, 34), (22, 14, 34), (23, 15, 33), (24, 16, 32), (25, 17, 31)
        ]
        for y, x1, x2 in hair_coords:
            for x in range(x1, x2 + 1):
                g[y][x] = "a"
                if y < 10 or x < 20:
                    g[y][x] = "7" if (x + y) % 4 == 0 else "a"
                elif y > 18 or x > 30:
                    g[y][x] = "9" if (x + y) % 2 == 0 else "4"

        # Face & Skin
        face_rows = [
            (16, 17, 31), (17, 17, 31), (18, 17, 31), (19, 16, 32),
            (20, 16, 32), (21, 16, 32), (22, 16, 32), (23, 17, 31),
            (24, 17, 31), (25, 18, 30), (26, 18, 30), (27, 19, 29),
            (28, 19, 29), (29, 20, 28), (30, 21, 27), (31, 22, 26),
            (32, 22, 26), (33, 23, 25), (34, 23, 25)
        ]
        for y, x1, x2 in face_rows:
            for x in range(x1, x2 + 1):
                g[y][x] = "f"
                if x >= x2 - 2:
                    g[y][x] = "e"

        # Neck
        for y in range(34, 43):
            for x in range(20, 29):
                g[y][x] = "f"
                if x in (20, 28) or y > 38:
                    g[y][x] = "e"

        # Forehead Bangs
        bangs = [
            (14, 16, "aaaaa99aaaaa"),
            (15, 15, "7aaaaa99aaaaa9"),
            (16, 15, "7aa99aaa99aaaa"),
            (17, 14, "aa999     99aa"),
            (18, 14, "a99         9a"),
            (19, 13, "a9           9"),
        ]
        for y, sx, row in bangs:
            for i, ch in enumerate(row):
                if ch != " ":
                    g[y][sx + i] = ch

        # Circlet & Gem
        for x in range(16, 33):
            g[17][x] = "a"
        g[17][24] = "7"
        g[16][24] = "c"
        g[17][23] = "9"
        g[17][25] = "9"

        # Eyes & Eyebrows
        for x in range(18, 22): g[19][x] = "9"
        for x in range(27, 31): g[19][x] = "9"
        g[21][19] = "7"
        g[21][20] = "5"
        g[22][19] = "5"
        g[22][20] = "0"
        g[21][28] = "5"
        g[21][29] = "7"
        g[22][28] = "0"
        g[22][29] = "5"

        # Nose & Mouth
        g[24][24] = "e"
        g[25][24] = "e"
        g[26][23] = "e"
        g[26][24] = "f"
        g[26][25] = "e"
        g[27][24] = "4"
        for x in range(22, 27): g[29][x] = "e"
        g[29][23] = "4"
        g[29][24] = "4"
        g[29][25] = "4"
        g[30][24] = "e"

        # Steel Armor Plate & Pauldrons
        for y in range(40, 64):
            span = min(22, int((y - 38) * 1.4) + 6)
            for x in range(24 - span, 24 + span + 1):
                if 0 <= x < W:
                    g[y][x] = "6"
                    if x < 24 - span + 3 or x > 24 + span - 3:
                        g[y][x] = "5"
                    elif x in (24 - span, 24 + span):
                        g[y][x] = "1"

        # Golden Gorget
        for y in range(40, 45):
            for x in range(18, 31):
                g[y][x] = "a"
                if x in (18, 30) or y == 44: g[y][x] = "9"
        g[42][24] = "7"

        # Breastplate Lion Crest
        for y in range(46, 58):
            g[y][24] = "a"
            g[y][23] = "9"
            g[y][25] = "9"
        for x in range(19, 30):
            g[49][x] = "a"
            g[50][x] = "9"
        g[49][24] = "7"

        # Steel Plate Highlights
        for y in range(45, 60):
            g[y][15] = "7"
            g[y][16] = "7"
            g[y][13] = "6"
            g[y][14] = "6"
            g[y][17] = "6"
            g[y][20] = "5"
            g[y][21] = "1"
            g[y][27] = "1"
            g[y][28] = "5"

        # Pauldron Trim
        for y in range(45, 64):
            g[y][6] = "a"
            g[y][7] = "9"
            g[y][8] = "7"
            g[y][9] = "6"
            g[y][40] = "9"
            g[y][41] = "a"
            g[y][38] = "6"
            g[y][39] = "7"

        # Outer Cape Folds
        for y in range(42, 64):
            g[y][3] = "8"
            g[y][4] = "8"
            g[y][5] = "2"
            g[y][42] = "2"
            g[y][43] = "8"
            g[y][44] = "8"

        return ["".join(row) for row in g]

    def create_rogue_portrait() -> list[str]:
        """Generates 48x64 detailed portrait for Rogue."""
        W, H = 48, 64
        g = [["0"] * W for _ in range(H)]

        # Background Shadow Smoke
        for y in range(4, 40):
            for x in range(4, 44):
                dx = x - 24
                dy = y - 22
                d2 = dx * dx + dy * dy
                if 144 <= d2 <= 320:
                    if (x * 2 + y * 3) % 7 == 0:
                        g[y][x] = "1"
                    elif (x + y) % 6 == 0:
                        g[y][x] = "2"

        # Hood Contour
        hood_profile = [
            (4, 23, 25), (5, 22, 26), (6, 21, 27), (7, 20, 28), (8, 19, 29),
            (9, 18, 30), (10, 17, 31), (11, 16, 32), (12, 15, 33), (13, 14, 34),
            (14, 13, 35), (15, 12, 36), (16, 11, 37), (17, 11, 37), (18, 10, 38),
            (19, 10, 38), (20, 10, 38), (21, 10, 38), (22, 11, 37), (23, 11, 37),
            (24, 11, 37), (25, 12, 36), (26, 12, 36), (27, 13, 35), (28, 13, 35)
        ]
        for y, x1, x2 in hood_profile:
            for x in range(x1, x2 + 1):
                g[y][x] = "1"
                if x in (x1, x1 + 1):
                    g[y][x] = "5" if (x + y) % 2 == 0 else "6"
                elif x in (x2 - 1, x2):
                    g[y][x] = "0"

        # Deep Shadow Interior Cavity
        for y in range(16, 32):
            cav_w = min(11, int((y - 14) * 0.9) + 4)
            for x in range(24 - cav_w, 24 + cav_w + 1):
                g[y][x] = "0"

        # Glowing Red Eyes
        g[20][18] = "8"
        g[20][19] = "e"
        g[20][20] = "8"
        g[21][18] = "8"
        g[21][19] = "7"
        g[21][20] = "8"
        g[22][19] = "8"
        g[20][27] = "8"
        g[20][28] = "e"
        g[20][29] = "8"
        g[21][27] = "8"
        g[21][28] = "7"
        g[21][29] = "8"
        g[22][28] = "8"

        # Nose Bridge & Cheek Highlight
        g[25][24] = "f"
        g[26][24] = "f"
        g[27][24] = "e"
        g[24][16] = "f"
        g[25][17] = "f"
        g[26][18] = "e"

        # Dark Face Mask
        for y in range(28, 38):
            mw = min(7, int((37 - y) * 0.8) + 4)
            for x in range(24 - mw, 24 + mw + 1):
                g[y][x] = "2"
                if x in (24 - mw, 24 - mw + 1):
                    g[y][x] = "5"
                elif x in (24 + mw - 1, 24 + mw):
                    g[y][x] = "0"
                elif (x + y) % 4 == 0:
                    g[y][x] = "1"

        # Crimson Scarf Collar
        for y in range(36, 45):
            sw = min(12, int((y - 34) * 1.2) + 6)
            for x in range(24 - sw, 24 + sw + 1):
                g[y][x] = "8"
                if x < 24 - sw + 2:
                    g[y][x] = "e"
                elif x > 24 + sw - 2:
                    g[y][x] = "2"
        clasp = [(40, 23, "9a9"), (41, 23, "a7a"), (42, 23, "9a9")]
        for y, sx, row in clasp:
            for i, ch in enumerate(row): g[y][sx + i] = ch

        # Studded Leather Armor
        for y in range(44, 64):
            span = min(22, int((y - 42) * 1.3) + 7)
            for x in range(24 - span, 24 + span + 1):
                if 0 <= x < W:
                    g[y][x] = "4"
                    if x < 24 - span + 3 or x > 24 + span - 3:
                        g[y][x] = "0"
                    elif x in (24 - span + 3, 24 - span + 4):
                        g[y][x] = "d"
                    elif (x + y) % 5 == 0:
                        g[y][x] = "5"

        # Silver Rivets
        stud_points = [
            (48, 10), (52, 9), (56, 8), (60, 7),
            (48, 38), (52, 39), (56, 40), (60, 41),
            (46, 18), (50, 18), (54, 19), (58, 20),
            (46, 30), (50, 29), (54, 28), (58, 27)
        ]
        for sy, sx in stud_points:
            g[sy][sx] = "7"
            g[sy][sx + 1] = "6"

        # Diagonal Baldric Strap
        for i in range(16):
            bx = 12 + int(i * 1.5)
            by = 46 + i
            if 0 <= bx < W - 2 and 0 <= by < H:
                g[by][bx] = "d"
                g[by][bx + 1] = "4"
                g[by][bx + 2] = "0"
                if i in (4, 10):
                    g[by][bx] = "a"
                    g[by][bx + 1] = "7"

        # Strapped Dagger
        dagger = [
            (43, 34, "7c7"), (44, 33, "aa9"), (45, 34, "00"),
            (46, 34, "44"), (47, 34, "44"), (48, 32, "9aaaa9"),
            (49, 34, "66"), (50, 34, "55"), (51, 34, "55"),
        ]
        for y, sx, row in dagger:
            for i, ch in enumerate(row):
                if 0 <= sx + i < W and 0 <= y < H:
                    g[y][sx + i] = ch

        return ["".join(row) for row in g]

    def create_mage_portrait() -> list[str]:
        """Generates 48x64 detailed portrait for Mage."""
        W, H = 48, 64
        g = [["0"] * W for _ in range(H)]

        # Arcane Mana Sparkles
        sparkles = [
            (8, 8), (14, 5), (6, 38), (12, 42), (24, 4), (28, 44),
            (38, 6), (44, 18), (4, 18), (42, 38), (7, 44), (40, 50)
        ]
        for sy, sx in sparkles:
            if 0 <= sx < W and 0 <= sy < H:
                g[sy][sx] = "c"
                if sx + 1 < W: g[sy][sx + 1] = "7"
                if sy + 1 < H: g[sy + 1][sx] = "6"

        # Pointed Wizard Hat
        hat_tip = [
            (2, 32, "22"), (3, 30, "221"), (4, 28, "2221"), (5, 26, "22211"),
            (6, 25, "222211"), (7, 24, "222211"), (8, 23, "2222211"), (9, 22, "2222211"),
            (10, 21, "22222211"), (11, 20, "222222211"), (12, 19, "2222222211"),
            (13, 18, "22222222211"), (14, 17, "222222222211"), (15, 16, "2222222222211"),
            (16, 15, "22222222222211"), (17, 14, "222222222222211"),
        ]
        for y, sx, row in hat_tip:
            for i, ch in enumerate(row):
                if 0 <= sx + i < W:
                    g[y][sx + i] = ch

        # Hat Band & Buckle
        for y in range(18, 21):
            for x in range(13, 37):
                g[y][x] = "c" if y == 19 else "1"
        for y in range(18, 21):
            g[y][22] = "9"
            g[y][23] = "a"
            g[y][24] = "7"
            g[y][25] = "a"
            g[y][26] = "9"
        g[19][24] = "c"

        # Wide Hat Brim
        for y, x1, x2 in [(21, 10, 38), (22, 7, 41), (23, 6, 42), (24, 7, 41)]:
            for x in range(x1, x2 + 1):
                g[y][x] = "2"
                if y == 21:
                    g[y][x] = "e" if (x + y) % 3 == 0 else "2"
                elif y == 24 or x in (x1, x2):
                    g[y][x] = "1"

        # Flowing Silver Hair
        for y in range(25, 54):
            for x in range(11, 18):
                g[y][x] = "7"
                if x == 11 or (x + y) % 3 == 0:
                    g[y][x] = "d"
                elif (x + y) % 5 == 0:
                    g[y][x] = "6"
            for x in range(31, 38):
                g[y][x] = "7"
                if x == 37 or (x + y) % 3 == 0:
                    g[y][x] = "d"
                elif (x + y) % 5 == 0:
                    g[y][x] = "6"

        # Face & Skin
        face_rows = [
            (25, 17, 31), (26, 17, 31), (27, 17, 31), (28, 17, 31),
            (29, 18, 30), (30, 18, 30), (31, 18, 30), (32, 19, 29),
            (33, 19, 29), (34, 20, 28), (35, 20, 28), (36, 21, 27),
            (37, 21, 27), (38, 22, 26), (39, 23, 25), (40, 23, 25)
        ]
        for y, x1, x2 in face_rows:
            for x in range(x1, x2 + 1):
                g[y][x] = "f"
                if x in (x1, x2):
                    g[y][x] = "e"

        # Neck
        for y in range(40, 47):
            for x in range(22, 27):
                g[y][x] = "f" if x in (23, 24, 25) else "e"

        # Eyebrows & Glowing Cyan Eyes
        for x in range(18, 22): g[26][x] = "d"
        for x in range(27, 31): g[26][x] = "d"
        g[28][19] = "c"
        g[28][20] = "7"
        g[29][19] = "1"
        g[29][20] = "c"
        g[28][28] = "7"
        g[28][29] = "c"
        g[29][28] = "c"
        g[29][29] = "1"

        # Nose & Mouth
        g[31][24] = "e"
        g[32][24] = "e"
        g[33][23] = "e"
        g[33][24] = "f"
        g[34][24] = "e"
        g[36][23] = "e"
        g[36][24] = "8"
        g[36][25] = "e"
        g[37][24] = "e"

        # High Ornate Collar
        collar = [
            (42, 14, "221"), (42, 31, "122"),
            (43, 15, "22a"), (43, 30, "a22"),
            (44, 16, "2aa"), (44, 29, "aa2"),
        ]
        for y, sx, row in collar:
            for i, ch in enumerate(row): g[y][sx + i] = ch

        # Robe Body
        for y in range(46, 64):
            span = min(22, int((y - 44) * 1.3) + 7)
            for x in range(24 - span, 24 + span + 1):
                if 0 <= x < W:
                    g[y][x] = "2"
                    if x < 24 - span + 2 or x > 24 + span - 2:
                        g[y][x] = "1"
                    elif (x + y) % 6 == 0:
                        g[y][x] = "e"

        # Brooch Gem at Throat
        g[47][24] = "a"
        g[48][23] = "a"
        g[48][24] = "c"
        g[48][25] = "a"
        g[49][22] = "9"
        g[49][23] = "c"
        g[49][24] = "7"
        g[49][25] = "c"
        g[49][26] = "9"
        g[50][23] = "a"
        g[50][24] = "c"
        g[50][25] = "a"
        g[51][24] = "9"

        # Runic Embroidery down Front
        for y in range(52, 64):
            g[y][21] = "a"
            g[y][27] = "a"
            if y % 3 == 0:
                g[y][23] = "c"
                g[y][25] = "c"
                g[y][24] = "7"
            else:
                g[y][24] = "1"

        # Mantle Gold Embroidery
        for y in range(50, 64):
            lx = 24 - int((y - 44) * 1.1)
            rx = 24 + int((y - 44) * 1.1)
            if 8 <= lx < W: g[y][lx] = "a"
            if 0 <= rx < 40: g[y][rx] = "a"

        return ["".join(row) for row in g]

    # 48x64 Character Portraits in Bank 0 at Row y=144
    pyxel.images[0].set(0, 144, create_warrior_portrait())
    pyxel.images[0].set(48, 144, create_rogue_portrait())
    pyxel.images[0].set(96, 144, create_mage_portrait())

    # Warrior Hero (16x16) at (0, 0)
    hero_sprite = [
        "00000aaa00000000", "0000aaaaa0000000", "0000077700000000", "0000776770000000",
        "0000700070000000", "0000777770000000", "0008811188000000", "0088716178870000",
        "0888766678877000", "08086666680a7000", "080865556800a000", "0000555550000000",
        "0000550550000000", "0000660660000000", "0000660660000000", "0000550550000000",
    ]
    pyxel.images[0].set(0, 0, hero_sprite)

    # Legacy Monster Fallbacks (16x16) at (16, 0), (32, 0), (48, 0)
    skeleton_sprite = [
        "0000077700000000", "0000777770000000", "0000787870000000", "0000777770000000",
        "0000070700000000", "0000007000000000", "0055077705000000", "0566570756500000",
        "0566577705600000", "0055070700560000", "0000077700044000", "0000007000000000",
        "0000070700000000", "0000070700000000", "0000070700000000", "0000550550000000",
    ]
    pyxel.images[0].set(16, 0, skeleton_sprite)

    goblin_sprite = [
        "0000000000000000", "0030000000030000", "03b30bbbb03b3000", "03bbbbbbbbb30000",
        "003bb8bb8bb30000", "000bbbaabbb00000", "0000bbbb00000000", "0004444440000000",
        "004444e444070000", "0444444444460000", "00044444440a0000", "0004000040000000",
        "0033000033000000", "0033000033000000", "0044000044000000", "0000000000000000",
    ]
    pyxel.images[0].set(32, 0, goblin_sprite)

    boss_sprite = [
        "000a0000000a0000", "000aa00a00aa0000", "0002aaaaaaa20000", "0022222222220000",
        "0222222222222000", "0222c2222c222000", "022ccc22ccc22000", "0022c0220c220000",
        "0002227722200000", "0022211112220000", "0222111111222000", "022111a111122000",
        "02211aaaa1122000", "0021111111120000", "0022111111220000", "0002222222200000",
    ]
    pyxel.images[0].set(48, 0, boss_sprite)

    # Rogue Character Sprite (16x16) at (0, 32)
    rogue_sprite = [
        "0000011100000000", "0000111110000000", "0000155510000000", "0001180811000000",
        "0001155511000000", "0000111110000000", "0070444440070000", "07604ff440067000",
        "0070444440070000", "0000544450000000", "0000444440000000", "0000550550000000",
        "0000110110000000", "0000110110000000", "0000550550000000", "0000000000000000",
    ]
    pyxel.images[0].set(0, 32, rogue_sprite)

    # Mage Character Sprite (16x16) at (16, 32)
    mage_sprite = [
        "0000002000000000", "0000022200000000", "0000022200000000", "0000222220000000",
        "0002aaaaa2000000", "002222222220c000", "000077777000c700", "00007878700a4a00",
        "0000777770004000", "00022ccc22004000", "00222ccc22204000", "0022222222204000",
        "0002220222004000", "0002220222004000", "0001110111004000", "0000000000000000",
    ]
    pyxel.images[0].set(16, 32, mage_sprite)

    # Wandering Merchant NPC Sprite (16x16) at (32, 32)
    merchant_sprite = [
        "0000444400000000", "0004ffff44400000", "0000022204440000", "0000222220440000",
        "00002ff220440000", "0000f0f0f0440000", "0000777770000000", "0000077700000000",
        "00022a2220a00000", "00222a2222aa0000", "0022222222000000", "0002222220000000",
        "0004400440000000", "0004400440000000", "0005500550000000", "0000000000000000",
    ]
    pyxel.images[0].set(32, 32, merchant_sprite)

    # 8x8 Item, Currency & Map Icons
    pyxel.images[0].set(64, 0, ["00044000", "00077000", "00766700", "07888870", "07878870", "07888870", "00788700",
                                "00077000"])  # Potion
    pyxel.images[0].set(72, 0, ["00000007", "000000aa", "00000a90", "00009400", "05094000", "00550000", "04005000",
                                "40000000"])  # Sword
    pyxel.images[0].set(80, 0, ["0aaaaaa0", "a999999a", "a949949a", "a949949a", "a994499a", "0a9999a0", "00a99a00",
                                "000aa000"])  # Shield
    pyxel.images[0].set(88, 0, ["000a0000", "00aaa000", "009a9a00", "098a8900", "09888900", "00444000", "04444400",
                                "44000440"])  # Campfire
    pyxel.images[0].set(96, 0, ["00444400", "04444440", "04aaaa40", "044aa440", "444aa444", "44444444", "44444444",
                                "04444400"])  # Chest
    pyxel.images[0].set(104, 0, ["00044000", "004aa400", "04a99a40", "4a9999a4", "4a9aa9a4", "4a9999a4", "04aaaa40",
                                 "00444400"])  # Shop Pouch

    pyxel.images[0].set(64, 8, ["000aa000", "00077000", "00788700", "07888870", "78788887", "7888e887", "07888870",
                                "00777700"])
    pyxel.images[0].set(72, 8, ["0c0770c0", "00077000", "007cc700", "07cccc70", "07c7cc70", "07cccc70", "007cc700",
                                "00077000"])
    pyxel.images[0].set(80, 8, ["000aa000", "00aaaa00", "0a9999a0", "0a9449a0", "0aaaaaa0", "0a0440a0", "00044000",
                                "00000000"])
    pyxel.images[0].set(88, 8, ["0a0000a0", "aa9999aa", "a99aa99a", "a9aaaa9a", "09a99a90", "09999990", "0a9999a0",
                                "00aaaa00"])
    pyxel.images[0].set(96, 8, ["00000000", "04000000", "04400440", "0f4004f0", "0ff44ff0", "04ffff40", "004ff400",
                                "00444400"])
    pyxel.images[0].set(104, 8, ["0aaaaaa0", "04ffff40", "04ffff40", "04400440", "04f00f40", "04f00f40", "04f00f40",
                                 "04400440"])

    pyxel.images[0].set(0, 16, ["00ffff00", "0ffffff0", "4fffffff", "44ffffff", "44400444", "44000044", "04000040",
                                "00000000"])
    pyxel.images[0].set(8, 16, ["0aaa0aaa", "a99aa99a", "a94aa94a", "aa4aaa4a", "0aa00aa0", "00000000", "00000000",
                                "00000000"])
    pyxel.images[0].set(16, 16, ["00000000", "00000000", "44444444", "ffffffff", "ffaaaa4f", "ffaaaa4f", "ffffffff",
                                 "44444444"])
    pyxel.images[0].set(24, 16, ["00000000", "00000000", "55555555", "66666666", "66755766", "66555566", "55555555",
                                 "05555550"])
    pyxel.images[0].set(32, 16, ["00000007", "00000067", "00000650", "00006500", "00555000", "02050000", "20000000",
                                 "00000000"])
    pyxel.images[0].set(40, 16, ["000000cc", "00000ccc", "00000cc0", "00004000", "00040000", "00400000", "04000000",
                                 "40000000"])
    pyxel.images[0].set(48, 16, ["02222220", "2aaaaaa2", "2a2222a2", "2a2c22a2", "2a2cc2a2", "2a2c22a2", "2a2222a2",
                                 "07777770"])
    pyxel.images[0].set(56, 16, ["00000989", "000008e8", "00000989", "00004000", "00040000", "00400000", "04000000",
                                 "40000000"])
    pyxel.images[0].set(64, 16, ["00000077", "00000766", "00007660", "00076600", "05766000", "55550000", "04005000",
                                 "40000000"])

    pyxel.images[0].set(0, 24, ["00000007", "00000067", "00000650", "00006500", "00444000", "04040000", "40000000",
                                "00000000"])
    pyxel.images[0].set(8, 24, ["00000006", "00000056", "00000550", "00505500", "00055000", "05555500", "00400500",
                                "04000000"])
    pyxel.images[0].set(16, 24, ["000000cc", "00000cc7", "000004c0", "00004000", "00040000", "00400000", "04000000",
                                 "40000000"])
    pyxel.images[0].set(24, 24, ["04444440", "4fffffff", "4f44444f", "4f4cc44f", "4f4cc44f", "4f44444f", "4fffffff",
                                 "04444440"])
    pyxel.images[0].set(32, 24, ["00077000", "000aa000", "00799700", "07aaaa70", "07a7aa70", "07aaaa70", "007aa700",
                                 "00077000"])
    pyxel.images[0].set(40, 24, ["00aaaa00", "0a7aaa90", "a7aaaaa9", "a7a44aa9", "a7a44aa9", "a7aaaaa9", "0a999990",
                                 "00999900"])

    # =========================================================================
    # 48 BIOME ENEMY SPRITES (Bank 0: Rows y=48 to y=128)
    # =========================================================================

    # -------------------------------------------------------------------------
    # Row y=48: Act 1A - The Wilted Arboretum
    # -------------------------------------------------------------------------
    pyxel.images[0].set(0, 48, [  # thornvein_creeper
        "0000003300000000", "000003b300000000", "00003bb380000000", "0003bbb300000000",
        "0083bbb300000000", "00003bb380000000", "000003bb30000000", "000083bb30000000",
        "000003bbb3008000", "00003bbbb3300000", "0033bb33bbb30000", "03bb30003bbb3000",
        "03b3800003bb3800", "00300000003b3000", "0000000000030000", "0000000000000000",
    ])
    pyxel.images[0].set(16, 48, [  # spore_pod
        "00000b000b000000", "000000b0b0000000", "0000022220000000", "000022bb22000000",
        "00022bbbb2200000", "00222bbbb2220000", "0222222222222000", "0223322223322000",
        "2223b3223b322200", "2222332223322200", "2222222222222200", "0222222222222000",
        "0044444444440000", "0004344443400000", "0033333333330000", "0000000000000000",
    ])
    pyxel.images[0].set(32, 48, [  # bramble_hound
        "0000000000000000", "0400000004000000", "0440000044000000", "0344444444000000",
        "0038448443800000", "0034444443000000", "0003444433000000", "0034444444300000",
        "0344444444438000", "0344334443443000", "0033003330033000", "0040000400004000",
        "0040000400004000", "0340000340003400", "0000000000000000", "0000000000000000",
    ])
    pyxel.images[0].set(48, 48, [  # rotting_woodwose
        "0000044444000000", "0000444334400000", "0004483384400000", "0004443344400000",
        "0000444444000000", "0044443344440000", "0443443344344000", "043b344443b34000",
        "0443444444344000", "0044443344440000", "0004443344400000", "0004400004400000",
        "0044400004440000", "0044400004440000", "03b30000003b3000", "0000000000000000",
    ])
    pyxel.images[0].set(64, 48, [  # mandragora_matron (Elite)
        "0000003b30000000", "000003bbb3000000", "00003bbbbb300000", "000004fff4000000",
        "00004fffff400000", "0004ff8f8ff40000", "0004fffffff40000", "0004f88888f40000",
        "00004f000f400000", "00044fffff440000", "00444fffff444000", "044044fff4404400",
        "0400044444000400", "0000034443000000", "0000330003300000", "0000000000000000",
    ])
    pyxel.images[0].set(80, 48, [  # corpse_treant (Elite)
        "0004400000440000", "0044440004444000", "0004444444440000", "0004474474440000",
        "0004484484440000", "0044444444444000", "0443444444344000", "443b3447743b3440",
        "4443447774434440", "0444444744444400", "0044444444440000", "0004444444400000",
        "0004440044400000", "0044440044440000", "0444400004444000", "0000000000000000",
    ])
    pyxel.images[0].set(96, 48, [  # malignant_belladonna (Boss)
        "0000220000220000", "0002ee2002ee2000", "002eeee22eeee200", "002eeee88eeee200",
        "0002ee8778ee2000", "0000287777820000", "0002870770782000", "0028770770778200",
        "0028777777778200", "0002877777782000", "0000287777820000", "000003bbbb300000",
        "00003b3333b30000", "0003b300003b3000", "003b30000003b300", "0033000000003300",
    ])
    pyxel.images[0].set(112, 48, [  # verdant_abomination (Boss)
        "0003b000000b3000", "003bb304403bb300", "03bbbb4444bbbb30", "03b3bb4884bb3b30",
        "0004448888444000", "0044744884474400", "0447744444477440", "4444744334474444",
        "43b4443bb3444b34", "43b443bbbb344b34", "0444443bb3444440", "0044444334444400",
        "0004440000444000", "003b44000044b300", "03bb44000044bb30", "0000000000000000",
    ])

    # -------------------------------------------------------------------------
    # Row y=64: Act 1B - The Desecrated Cathedral
    # -------------------------------------------------------------------------
    pyxel.images[0].set(0, 64, [  # cathedral_imp
        "0800000000000080", "0880000000000880", "0088088888808800", "0008888888888000",
        "00088a8888a88000", "0008808888088000", "0000888888880000", "0800088888800080",
        "8880888888880888", "8888888888888888", "0888888888888880", "0000888888880000",
        "0000880000880000", "0000880000880000", "0008880000888000", "0000000000000000",
    ])
    pyxel.images[0].set(16, 64, [  # possessed_grimoire
        "0000000000000000", "000000cc00000000", "0000cccccccc0000", "000c444cc444c000",
        "00c47774c47774c0", "0c4711174711174c", "0471111171111174", "0471c1117111c174",
        "0471111171111174", "0471111171111174", "0047777747777740", "0004444444444400",
        "0000222222220000", "0000022002200000", "0000000000000000", "0000000000000000",
    ])
    pyxel.images[0].set(32, 64, [  # candelabra_fiend
        "0090000090000090", "09a90009a90009a9", "0070000070000070", "0070000070000070",
        "0aaa000aaa000aaa", "0aaaa00aaa00aaaa", "00aaaa0aaa0aaaa0", "000aaaaaaaaaaa00",
        "00000aaaaaaa0000", "0000008aaa800000", "0000000aaa000000", "0000000aaa000000",
        "0000000aaa000000", "000000aaaaa00000", "00000aaaaaaa0000", "0000000000000000",
    ])
    pyxel.images[0].set(48, 64, [  # penitent_zealot
        "0000044440000000", "0000444444000000", "0000404404000000", "0000444444000000",
        "0000044440000000", "0080444444008800", "088044884408d800", "008048888400d000",
        "000044884400d000", "000044444400d000", "000044444400d000", "000044004408d800",
        "0000440044008800", "0004440044400000", "0004400004400000", "0000000000000000",
    ])
    pyxel.images[0].set(64, 64, [  # belltower_gargoyle (Elite)
        "0d000000000000d0", "0dd0000000000dd0", "00dd05dddd50dd00", "000dddddddddd000",
        "000dd8dddd8dd000", "000dd0dddd0dd000", "0000dddddddd0000", "0d000dddddd000d0",
        "ddd0dddddddd0ddd", "dddddddddddddddd", "0dddddddddddddd0", "0000dddddddd0000",
        "0000dd0000dd0000", "0000dd0000dd0000", "000ddd0000ddd000", "0000000000000000",
    ])
    pyxel.images[0].set(80, 64, [  # inquisitor_automaton (Elite)
        "000000dd00000000", "00000dddd0000000", "0000d7dd7d000000", "0000dddddd000000",
        "00000d88d0000000", "0770dddddd077000", "7dd7d8dd8d7dd700", "0770dddddd077000",
        "0000dd88dd000000", "0000dddddd000000", "0000d8dd8d000000", "0000dddddd000000",
        "0000dd00dd000000", "0000dd00dd000000", "000ddd00ddd00000", "0000000000000000",
    ])
    pyxel.images[0].set(96, 64, [  # blind_archbishop (Boss)
        "0000000a00000000", "000000aaa0000000", "00000aaaaa000000", "00000a9a9a000000",
        "00000aaaaa000000", "0000077777000000", "0000088888000000", "0000077777000000",
        "000aa22222aa0000", "00aaa2a2a2aaa000", "0aaaa2a2a2aaaa00", "000aa22222aa0000",
        "0000a22222a00000", "0000222222200000", "0000222222200000", "0000000000000000",
    ])
    pyxel.images[0].set(112, 64, [  # chorus_of_damned (Boss)
        "000cc000000cc000", "00c77c0000c77c00", "0c7070c00c7070c0", "0c7707c00c7707c0",
        "00c77c0cc0c77c00", "000cc0c77c0cc000", "00000c7070c00000", "0cc00c7707c00cc0",
        "c77c00c77c00c77c", "7070c00cc00c7070", "7707c0cccc0c7707", "c77ccccccccccc7c",
        "0cccccccccccccc0", "00cc00cccc00cc00", "000c000cc000c000", "0000000000000000",
    ])

    # -------------------------------------------------------------------------
    # Row y=80: Act 2A - The Drowned Ossuary
    # -------------------------------------------------------------------------
    pyxel.images[0].set(0, 80, [  # mire_ghoul
        "0000005500000000", "000005d550000000", "00005dddd5000000", "0005dd8dd8500000",
        "0005dddddd500000", "00005d000d500000", "00555ddddd555000", "05dd5ddddd5dd500",
        "5ddd5ddddd5ddd50", "5d555ddddd555d50", "05005ddddd500500", "00005ddddd500000",
        "0000550005500000", "0005d50005d50000", "0005500000550000", "0000000000000000",
    ])
    pyxel.images[0].set(16, 80, [  # drowned_skulls
        "0005500000550000", "0057750005775000", "0570705057070500", "0577775057777500",
        "0057750550577500", "0005505775055000", "0000057070500000", "0000057777500000",
        "0550005775000550", "5775000550005775", "7070505555057070", "7777555555557777",
        "5775555555555775", "0555555555555550", "0005550000555000", "0000000000000000",
    ])
    pyxel.images[0].set(32, 80, [  # leech_husk
        "0000008800000000", "0000081180000000", "0000810018000000", "0000811118000000",
        "0008818818800000", "0081188881180000", "0818818818818000", "0818888888818000",
        "0811881188118000", "0081188881180000", "0008818818800000", "0000811118000000",
        "0000810018000000", "0000081180000000", "0000008800000000", "0000000000000000",
    ])
    pyxel.images[0].set(48, 80, [  # crypt_lurker
        "0000000000000000", "0500005500005000", "005005dd50050000", "00055dddd5500000",
        "0005d8dd8d500000", "0555dddddd555000", "5dd55dddd55dd500", "0555dddddd555000",
        "0005dddddd500000", "0055dddddd550000", "05055dddd5505000", "500055dd55000500",
        "0000055550000000", "0000550055000000", "0005000000500000", "0000000000000000",
    ])
    pyxel.images[0].set(64, 80, [  # tide_gravekeeper (Elite)
        "00000777000dd000", "0000777770dddd00", "00007575700dd000", "00007777700dd000",
        "00055707550dd000", "00555777555dd000", "05555555555dd000", "55555555555dd000",
        "05555555555dd000", "00555555550dd000", "00055555500dd000", "0005500550d55d00",
        "0055500555d00d00", "0055500555dddd00", "00550000550dd000", "0000000000000000",
    ])
    pyxel.images[0].set(80, 80, [  # carrion_behemoth (Elite)
        "0000555555000000", "00055d5d55500000", "0055ddddd5550000", "055d7dd7dd555000",
        "055dd8d8dd555000", "555ddddddd555500", "5577dd5dd7755500", "5577d555d7755550",
        "555d55555d555550", "5555555555555550", "0555575575555500", "0555575575555500",
        "0055555555555000", "0005550055500000", "0055550055550000", "0000000000000000",
    ])
    pyxel.images[0].set(96, 80, [  # drowned_patriarch (Boss)
        "000c00c00c00c000", "000cc0c00c0cc000", "000cccccccccc000", "0005555555555000",
        "0055555555555500", "0055e555555e5500", "0055555005555500", "0005550000555000",
        "0011555555551100", "0111155555511110", "01c1111111111c10", "0111111111111110",
        "0011111111111100", "0001110000111000", "0001110000111000", "0000000000000000",
    ])
    pyxel.images[0].set(112, 80, [  # scylla_bone_weaver (Boss)
        "0700000770000070", "0770007777000770", "0077077557707700", "0007778558777000",
        "0000777777700000", "0777077777077700", "7777777777777770", "0777070770707770",
        "0000700770070000", "0007700770077000", "0077000770007700", "0770007777000770",
        "0700077007700070", "7000770000770007", "0007700000077000", "0000000000000000",
    ])

    # -------------------------------------------------------------------------
    # Row y=96: Act 2B - The Foundry of Torment
    # -------------------------------------------------------------------------
    pyxel.images[0].set(0, 96, [  # slag_homunculus
        "0000044440000000", "0000449944000000", "000449ee94400000", "0004499994400000",
        "0000444444000000", "0044499994440000", "044949ee94944000", "4499499994994400",
        "4499444444994400", "0444449944444000", "000449ee94400000", "0004499994400000",
        "0004440044400000", "0049440044940000", "0044400004440000", "0000000000000000",
    ])
    pyxel.images[0].set(16, 96, [  # cinder_sprite
        "0000009000000000", "000009a900000000", "00009aaa90000000", "0009a77a90000000",
        "009a7ff7a9000000", "009a7ff7a9000000", "09a77ff77a900000", "09affffffa900000",
        "09affffffa900000", "009a7ff7a9000000", "0009a77a90000000", "00909aaa90900000",
        "090009a900090000", "0000009000000000", "0000000000000000", "0000000000000000",
    ])
    pyxel.images[0].set(32, 96, [  # clockwork_flayer
        "0000dd0000dd0000", "000dddd00dddd000", "0000dddddddd0000", "00dd04aaaa40dd00",
        "0dd04aaaaaa40dd0", "0004aa8aa8aa4000", "0004aaaaaaaa4000", "0004aa8888aa4000",
        "0004aaaaaaaa4000", "0dd04aaaaaa40dd0", "00dd04aaaa40dd00", "0000dddddddd0000",
        "000dddd00dddd000", "0000dd0000dd0000", "0000000000000000", "0000000000000000",
    ])
    pyxel.images[0].set(48, 96, [  # ashen_overseer
        "000000dd00000000", "00000dddd0000000", "0000d8dd8d000000", "0000dddddd000000",
        "00000dddd0000000", "0004444444400000", "0044499944409000", "0444499944440900",
        "0444444444440090", "0044444444400099", "0004444444000900", "0004400044009000",
        "0004400044090000", "0044400044400000", "0044400044400000", "0000000000000000",
    ])
    pyxel.images[0].set(64, 96, [  # furnace_warden (Elite)
        "00000dddd0000000", "00000d44d0000000", "0000dddddd000000", "000dddddddd00000",
        "000dd9aa9dd00000", "000dd9aa9dd00000", "00dddddddddd0000", "0dddd9999dddd000",
        "0dddd9aa9dddd000", "00ddd9aa9ddd0000", "00ddd9999ddd0000", "000dddddddd00000",
        "000dd0000dd00000", "000dd0000dd00000", "00ddd0000ddd0000", "0000000000000000",
    ])
    pyxel.images[0].set(80, 96, [  # retching_alchemist (Elite)
        "0000022200000000", "0000222220000000", "0002233222000000", "0002233222000000",
        "0000222220000000", "0000222220000000", "0030222220030000", "03b32222203b3000",
        "0030222220030000", "0000222220000000", "0002222222000000", "0002200022000000",
        "0002200022000000", "0004400044000000", "0044400044400000", "0000000000000000",
    ])
    pyxel.images[0].set(96, 96, [  # ironforge_tyrant (Boss)
        "0000007700000000", "0000078870000000", "000078ee87000000", "0000788887000000",
        "0004444444440000", "0049944449940000", "049ee9449ee94000", "049ee9449ee94077",
        "00499444499407aa", "00044444444007aa", "0004444444400077", "0004400004400040",
        "0004400004400040", "0044400004440040", "0044400004440040", "0000000000000000",
    ])
    pyxel.images[0].set(112, 96, [  # molten_sovereign (Boss)
        "0009009900900000", "009a99aa99a90000", "009aaaaaa9a90000", "0009aeeea9000000",
        "0009afffa9000000", "0099afffa9900000", "09a9afffa9a90000", "9aaaaeeeaaaa9000",
        "9aa9999999aa9000", "09aa9999aa900000", "009aaaaaa9000000", "0009aaaa90000000",
        "00099aa990000000", "0099000099000000", "0990000009900000", "0000000000000000",
    ])

    # -------------------------------------------------------------------------
    # Row y=112: Act 3A - The Astral Observatory
    # -------------------------------------------------------------------------
    pyxel.images[0].set(0, 112, [  # void_mirror
        "0000000700000000", "0000007c70000000", "000007cc70000000", "00007ccc70000000",
        "0007cc1cc7000000", "007cc111cc700000", "07cc11111cc70000", "7cc1111111cc7000",
        "07cc11111cc70000", "007cc111cc700000", "0007cc1cc7000000", "00007ccc70000000",
        "000007cc70000000", "0000007c70000000", "0000000700000000", "0000000000000000",
    ])
    pyxel.images[0].set(16, 112, [  # stareater_wisp
        "0000000c00000000", "000c00c7c00c0000", "0000c7777c000000", "000c771177c00000",
        "0c0771001770c000", "00c71000017c0000", "c771000000177c00", "00c71000017c0000",
        "0c0771001770c000", "000c771177c00000", "0000c7777c000000", "000c00c7c00c0000",
        "0000000c00000000", "0000000000000000", "0000000000000000", "0000000000000000",
    ])
    pyxel.images[0].set(32, 112, [  # comet_stalker
        "0000000000000000", "000c0000000c0000", "00cc000000cc0000", "00cccccccccccc00",
        "00c7cc7cc7cc7c00", "00cccccccccccc00", "000cccccccccc000", "0000cccccccc0000",
        "000cccccccccc000", "00ccccccccccc700", "0ccccccccccccc70", "0cc0cc0000cc0cc0",
        "0c00c000000c00c0", "0700700000070070", "0000000000000000", "0000000000000000",
    ])
    pyxel.images[0].set(48, 112, [  # celestial_hermit
        "00000055000c0000", "0000055550c7c000", "000055c5550c0000", "000055c555050000",
        "0000055550050000", "0000555555050000", "000551c155050000", "005551c155550000",
        "005555c555550000", "000555c555050000", "0005555555050000", "0005500055050000",
        "0005500055050000", "0055500055550000", "0055000005550000", "0000000000000000",
    ])
    pyxel.images[0].set(64, 112, [  # rift_warden (Elite)
        "0000007700000000", "0000075570000000", "000075c557000000", "0000755557000000",
        "0005555555500000", "0c0555c55500c000", "0cc55ccc555cc000", "0cc555c5555cc000",
        "0c0555555500c000", "0c0555555500c000", "0c0055555000c000", "0000550550000000",
        "0000550550000000", "0005550555000000", "0005500055000000", "0000000000000000",
    ])
    pyxel.images[0].set(80, 112, [  # null_singularity (Elite)
        "0000007700000000", "000077cc77000000", "0007c5555c700000", "007c522225c70000",
        "07c52000025c7000", "0752000000257000", "7c5200000025c700", "7c5200000025c700",
        "7c5200000025c700", "0752000000257000", "07c52000025c7000", "007c522225c70000",
        "0007c5555c700000", "000077cc77000000", "0000007700000000", "0000000000000000",
    ])
    pyxel.images[0].set(96, 112, [  # chronomancer_praetor (Boss)
        "000000cc00000000", "00000cccc0000000", "0000cc77cc000000", "000cc7117cc00000",
        "000cc7117cc00000", "0000cc77cc000000", "000aa0cc00aa0000", "00aaaa00aaaa0000",
        "0aa77aaaa77aa000", "00aaaa00aaaa0000", "000aa1111aa00000", "0000111111000000",
        "0001111111100000", "0001110011100000", "0001100001100000", "0000000000000000",
    ])
    pyxel.images[0].set(112, 112, [  # devouring_constellation (Boss)
        "0c000007000000c0", "00c0007770000c00", "000c07c7c700c000", "0000c77777c00000",
        "0007722222770000", "007c2200022c7000", "07c220770022c700", "7722007700022770",
        "07c220000022c700", "007c2200022c7000", "0007722222770000", "0000c77777c00000",
        "000c07c7c700c000", "00c0007770000c00", "0c000007000000c0", "0000000000000000",
    ])

    # -------------------------------------------------------------------------
    # Row y=128: Act 3B - The Blood Sanctum
    # -------------------------------------------------------------------------
    pyxel.images[0].set(0, 128, [  # sanguine_thrall
        "0000077700000000", "0000777770000000", "0000787870000000", "0000778770000000",
        "0000078700000000", "0080077700800000", "0888222228880000", "0888228228880000",
        "0080228220800000", "0000288820000000", "0000222220000000", "0000220220000000",
        "0000220220000000", "0000770770000000", "0000880880000000", "0000000000000000",
    ])
    pyxel.images[0].set(16, 128, [  # crimson_gargoyle
        "0800000000000080", "0880000000000880", "0088028888208800", "0008888888888000",
        "00088e8888e88000", "0008808888088000", "0000888888880000", "0800088888800080",
        "8880888888880888", "8888888888888888", "0888888888888880", "0000888888880000",
        "0000880000880000", "0000880000880000", "0008880000888000", "0000000000000000",
    ])
    pyxel.images[0].set(32, 128, [  # hemomancer_acolyte
        "0000008800000000", "0000088880000000", "0000887788000000", "0000887788000000",
        "0000088880000000", "0000222222000000", "0080228822008000", "08e828ee8208e800",
        "0080228822008000", "0000222222000000", "0002222222200000", "0002200002200000",
        "0002200002200000", "0008800008800000", "0088800008880000", "0000000000000000",
    ])
    pyxel.images[0].set(48, 128, [  # flayed_duelist
        "0000007700000000", "0000077770000000", "0000778877000000", "0000778877000000",
        "0000077770000000", "0000882288000000", "0008882288807000", "0088882288887700",
        "0000882288000770", "0000888888000070", "0000888888000070", "0000220022000070",
        "0000220022000000", "0008880088800000", "0008800008800000", "0000000000000000",
    ])
    pyxel.images[0].set(64, 128, [  # baroness_vespera (Elite)
        "0800000000000080", "0880007770000880", "0888077777008880", "0088778787788800",
        "0008777877788000", "0000778877000000", "0800888888000800", "8888822228888880",
        "8888228822888880", "0880228822008800", "0000288882000000", "0000222222000000",
        "0000222222000000", "0000220022000000", "0008880088800000", "0000000000000000",
    ])
    pyxel.images[0].set(80, 128, [  # amalgam_of_veins (Elite)
        "0008800000880000", "008ee80008ee8000", "08eeee808eeee800", "08eeee888eeee800",
        "008ee88888ee8000", "0888888888888800", "888888ee88888880", "88888eeee8888880",
        "888ee8ee8ee88880", "0888888888888800", "0088888888888000", "0880088888008800",
        "8800088008800880", "8000888008880080", "0000880000880000", "0000000000000000",
    ])
    pyxel.images[0].set(96, 128, [  # high_lord_carmilla (Boss)
        "0080000000008000", "0888000000088800", "0888807770888800", "0088877777888000",
        "0008778787780000", "0000777877700000", "0000078870000000", "0000888888000000",
        "0008822228800000", "0088228822880000", "0082228822280000", "0002228822200000",
        "0002222222200000", "0002222222200000", "0000220022000000", "0000000000000000",
    ])
    pyxel.images[0].set(112, 128, [  # blood_god_avatar (Boss)
        "0800000000000080", "0880008888000880", "0888088888808880", "0088888888888800",
        "000888e88e888000", "0008880880888000", "0008888888888000", "0008888888888000",
        "0088888888888800", "0888888888888880", "8888888888888888", "8888888888888888",
        "0888888888888880", "0088880000888800", "0088800000088800", "0000000000000000",
    ])

    # =========================================================================
    # IMAGE BANK 1: REFINED GOTHIC TITLE ASSETS
    # =========================================================================

    def create_title_banner():
        W, H = 144, 32
        g = [["0" for _ in range(W)] for _ in range(H)]
        for y in range(2, 30):
            for x in range(4, W - 4): g[y][x] = "1"
        for x in range(4, W - 4):
            g[2][x] = "a"
            g[3][x] = "9"
            g[28][x] = "9"
            g[29][x] = "a"
        for y in range(2, 30):
            g[y][4] = "a"
            g[y][5] = "9"
            g[y][W - 6] = "9"
            g[y][W - 5] = "a"
        for x in range(8, W - 8):
            g[5][x] = "4"
            g[26][x] = "4"
        for y in range(5, 27):
            g[y][8] = "4"
            g[y][W - 9] = "4"
        for cy, cx in [(2, 4), (2, W - 6), (28, 4), (28, W - 6)]:
            g[cy][cx] = "7"
        for dx in range(12):
            g[16][12 + dx] = "a" if dx % 2 == 0 else "9"
            g[16][W - 13 - dx] = "a" if dx % 2 == 0 else "9"

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

    # =========================================================================
    # IMAGE BANK 1: ABILITY ICONS ASSETS
    # =========================================================================

    ABILITY_SPRITES: Final[dict[str, list[str]]] = {
        "cross_cut": [
            "0000000000007c00", "000000000007c000", "7c000000007c0000", "07c0000007c00000",
            "007c00007c000000", "0007c007c0000000", "00007c7c00000000", "0000077000000000",
            "00007c7c00000000", "0007c007c0000000", "007c00007c000000", "07c0000007c00000",
            "7c000000007c0000", "0000000000007c00", "00000000000007c0", "000000000000007c",
        ],
        "shadow_strike": [
            "0000000000000000", "00000000000007c0", "0000000000007c70", "000000000007c500",
            "00000000007c5000", "0000000007c50000", "000000007c500000", "00002207c5000000",
            "0002127c50000000", "0021125500000000", "0211200000000000", "0022000000000000",
            "0000000000000000", "0000000000000000", "0000000000000000", "0000000000000000",
        ],
        "arcane_bolt": [
            "0000000000000000", "0000000000000070", "00000000000007c7", "0000000000007cc7",
            "000000000007cc70", "00000000007cc700", "0000000007cc7000", "00000c007cc70000",
            "0000cc07cc700000", "000c6c7cc7000000", "000676cc70000000", "000c67c700000000",
            "0000c6c000000000", "00000c0000000000", "0000000000000000", "0000000000000000",
        ],
        "pw_kill": [
            "0000008888000000", "000088eeee880000", "0008e88ee88e8000", "008eeeeeeeeee800",
            "008e00eeee00e800", "008e08eeee08e800", "008eeeeeeeeee800", "0008ee0ee0ee8000",
            "0008ee0000ee8000", "00008eeeeee80000", "000808e88e808000", "0088008888008800",
            "0800000000000080", "0080000000000800", "0008000000008000", "0000000000000000",
        ],
        "shield_bash": [
            "0000000000000000", "0066666600000000", "0677777760070000", "6776666776007000",
            "6766556676000700", "6765115676777770", "6765115676000700", "6766556676007000",
            "0676666760070000", "0067667600000000", "0006776000000000", "0000660000000000",
            "0000000000000000", "0000000000000000", "0000000000000000", "0000000000000000",
        ],
        "rallying_cry": [
            "0000000000000000", "00000000aa900000", "0000000a77a90000", "000000a7aa7a90a0",
            "00000a7aaaa7a90a", "0000a7aaaaaa7a00", "000aa7aaaaaa7a0a", "00a88aaaaaaa7a00",
            "0a8888aaaaaa7a0a", "a888888aaaaa7a00", "0a8888aaaaa7a900", "00a88aaaaa7a9000",
            "000aaaaaaaa90000", "0000000000000000", "0000000000000000", "0000000000000000",
        ],
        "cleave": [
            "0000000000000000", "0000000766000000", "0000007766500000", "0000077886550000",
            "0000778888650000", "0007788888865000", "0077888888886500", "0778888888888650",
            "0000004440000000", "0000004440000000", "0000004440000000", "0000004440000000",
            "0000004440000000", "0000004440000000", "0000000000000000", "0000000000000000",
        ],
        "iron_skin": [
            "0000000000000000", "0000555555550000", "0005666666665000", "0056777667776500",
            "0567777667777650", "0567777667777650", "0566777667776650", "0566677667766650",
            "0056667667666500", "0056666666666500", "0005666666665000", "0000566666650000",
            "0000056666500000", "0000005665000000", "0000000550000000", "0000000000000000",
        ],
        "veterans_instincts": [
            "000000aaaa000000", "00000a7777a00000", "0000a7aaaa7a0000", "000a7aaaaaaaa000",
            "00aa99999999aa00", "0a997779977799a0", "0a97c77997c779a0", "0a977779977779a0",
            "0aa999999999aa00", "00aa99a99a99aa00", "000a99a99a99a000", "000a99aaaa99a000",
            "0000aa9999aa0000", "000000aaaa000000", "0000000000000000", "0000000000000000",
        ],
        "bloodlust": [
            "0000000800000000", "0000008e80000000", "000008eee8000000", "00008ee7ee800000",
            "0008ee77eee80000", "008eeeeeeeeee800", "08eeeeeeeeeeee80", "8eeeeeeeeeeeeee8",
            "8eeeeeeeeeeeeee8", "8eeeeeeeeeeeeee8", "08eeeeeeeeeeee80", "0088eeeeeeee8800",
            "0000888888880000", "0000000000000000", "0000000000000000", "0000000000000000",
        ],
        "shieldbreaker_strike": [
            "0000000000000000", "0000066600000000", "0000677660000000", "0006776660000000",
            "0006766660aa0000", "000066600a77a000", "0000000a7777a000", "000000a77a77a000",
            "000000a7a0a7a000", "00000a7a00a7a000", "00000aa0000aa000", "0000440000000000",
            "0004400000000000", "0044000000000000", "0440000000000000", "0000000000000000",
        ],
        "defensive_superiority": [
            "000000aaaa000000", "00000a7777a00000", "000aa77aa77aa000", "00a77aaaaaa77a00",
            "00a7aa5555aa7a00", "00a7a566665a7a00", "00aaa567765aaa00", "000a56677665a000",
            "000a56666665a000", "000a56666665a000", "000a55666655a000", "0000a556655a0000",
            "00000a5555a00000", "000000aaaa000000", "0000000000000000", "0000000000000000",
        ],
        "paladin_guard": [
            "0000000000000000", "000000aaaa000000", "00000a7777a00000", "0000a777777a0000",
            "0000a771177a0000", "0000a771177a0000", "000a71111117a000", "000a71111117a000",
            "0000a771177a0000", "0000a771177a0000", "0000a771177a0000", "00000a7777a00000",
            "000000aaaa000000", "0000000000000000", "0000000000000000", "0000000000000000",
        ],
        "reckless_assault": [
            "0000000000000000", "0078800000088700", "0788880000888870", "0888888008888880",
            "0088888888888800", "0008888888888000", "0000888888880000", "0000088888800000",
            "0000088888800000", "0000880440880000", "0008800440088000", "0088000440008800",
            "0800000440000080", "0000000440000000", "0000000000000000", "0000000000000000",
        ],
        "blood_frenzy": [
            "0000000000000000", "0080000000000800", "08e8000000008e80", "08ee80000008ee80",
            "08eee888888eee80", "008eeeeeeeeee800", "008e00eeee00e800", "008e00eeee00e800",
            "008eeeeeeeeee800", "0008e77ee77e8000", "0008e77ee77e8000", "00008eeeeee80000",
            "0000088888800000", "0000000000000000", "0000000000000000", "0000000000000000",
        ],
        "cull_the_weak": [
            "0000000000000000", "0000077777770000", "0000776666677000", "0007765555667000",
            "0077655000567000", "0776550000567000", "0765500004440000", "0055000044400000",
            "0000000444000000", "0000004440000000", "0000044400000000", "0000444000000000",
            "0004440000000000", "0044400000000000", "0000000000000000", "0000000000000000",
        ],
        "poison_shiv": [
            "0000000000000000", "0000000000000b00", "000000000000b3b0", "000000000007b3b0",
            "00000000007cb000", "0000000007cb0000", "000000007cb00000", "00000007cb000000",
            "0000007cb0000000", "000007cb00000000", "000022b000000000", "0002120000000000",
            "0021120000000000", "0211200000000000", "0022000000000000", "0000000000000000",
        ],
        "dirty_tricks": [
            "0000000000000000", "0000000dd0000000", "000000dddd000000", "0000000dd0000000",
            "0000004444000000", "000004ffff400000", "00004ffffff40000", "0004ffffffff4000",
            "0004ffffffff4000", "00004ffffff40000", "0000044444400000", "00aaa000000aaa00",
            "0a777a0000a777a0", "00aaa000000aaa00", "0000000000000000", "0000000000000000",
        ],
        "flurry_of_daggers": [
            "000000000000007c", "00000007c00007c0", "0000007c00007c00", "07c0007c0007c000",
            "07c007c00007c000", "007c07c0007c0000", "007c7c00007c0000", "0007c00007c00000",
            "0007c00007c00000", "007c00007c000000", "007c00007c000000", "07c00007c0000000",
            "07c00007c0000000", "7c00007c00000000", "0000000000000000", "0000000000000000",
        ],
        "nimble_reflexes": [
            "0000000000000000", "0000000000000770", "00000000000077c0", "0000000000077c00",
            "000000000077c000", "00000000077c0000", "0000000077c00000", "000000077c000000",
            "00000077c0000000", "0000077c00000000", "000077c000000000", "00077c0000000000",
            "0077c00000000000", "077c000000000000", "0000000000000000", "0000000000000000",
        ],
        "exposed_weakness": [
            "0000000800000000", "0000000800000000", "0000888888800000", "0008eeeeeee80000",
            "008eeeeeeeee8000", "008eeeeeeeee8000", "08eeeeeeeeeee800", "8888888788888888",
            "08eeeeeeeeeee800", "008eeeeeeeee8000", "008eeeeeeeee8000", "0008eeeeeee80000",
            "0000888888800000", "0000000800000000", "0000000800000000", "0000000000000000",
        ],
        "shadow_step": [
            "0000000000000000", "0000000000000000", "0000002220000000", "0000021112000000",
            "0000211111200000", "0000211111200000", "0000021112000000", "0000002220000000",
            "0022200000000000", "0211120000000000", "2111112000000000", "2111112000000000",
            "0211120000000000", "0022200000000000", "0000000000000000", "0000000000000000",
        ],
        "venomous_accumulation": [
            "0000000dd0000000", "0000000dd0000000", "0000003bb3000000", "000003bbbb300000",
            "00003bbbbbb30000", "0003bbbbbbbb3000", "003bbbbbbbbbb300", "003bb7bb7bbbb300",
            "003bbbbbbbbbb300", "003bb7bb7bbbb300", "003bbbbbbbbbb300", "00033bbbbbb33000",
            "0000033333300000", "0000000000000000", "0000000000000000", "0000000000000000",
        ],
        "toxic_blood": [
            "0000000b00000000", "000000b3b0000000", "00000b383b000000", "0000b38883b00000",
            "000b38eee83b0000", "00b38eeeee83b000", "0b38eeeeeee83b00", "b38eeeeeeeee83b0",
            "b38eeeeeeeee83b0", "b38eeeeeeeee83b0", "0b38eeeeeee83b00", "00b38eeeee83b000",
            "000b3888883b0000", "0000b33333b00000", "0000000000000000", "0000000000000000",
        ],
        "venomous_extraction": [
            "0000000000000000", "0000000000000770", "0000000000007b70", "000000000007b700",
            "00000000007b7000", "0000000007b70000", "000000007b700000", "00000007b7000000",
            "0000007b70000000", "000007b700000000", "00007b7000000000", "0007b70000000000",
            "007b700000000000", "07b7000000000000", "7b70000000000000", "0000000000000000",
        ],
        "riposte": [
            "0000000000000000", "0000000000000070", "0000000000000700", "0000000000007000",
            "0000000000070000", "0000000000700000", "0000000aaa000000", "000000a777a00000",
            "0000000aaa000000", "0000070000000000", "0000700000000000", "0007000000000000",
            "0070000000000000", "0700000000000000", "7000000000000000", "0000000000000000",
        ],
        "whirlwind_defense": [
            "0000007777000000", "0000776666770000", "0077660000667700", "0766000000006670",
            "7600007777000067", "7600077667700067", "7600760000670067", "7600760000670067",
            "7600760000670067", "7600760000670067", "7600077667700067", "7600007777000067",
            "0766000000006670", "0077660000667700", "0000776666770000", "0000007777000000",
        ],
        "hilt_strike": [
            "0000000000000000", "0000000000000000", "0000000770000000", "0000007667000000",
            "0000076666700000", "0000766666670000", "0000076666700000", "0000007667000000",
            "0000000770000000", "0000000aa0000000", "0000000aa0000000", "0000000aa0000000",
            "000000a77a000000", "0000000aa0000000", "0000000000000000", "0000000000000000",
        ],
        "fireball": [
            "0000000000000000", "0000000880000000", "0000008998000000", "0000089aa9800000",
            "000089a77a980000", "00089a7777a98000", "0089a777777a9800", "089a77777777a980",
            "089a77777777a980", "0089a777777a9800", "00089a7777a98000", "000089a77a980000",
            "0000089aa9800000", "0000008998000000", "0000000880000000", "0000000000000000",
        ],
        "chain_lightning": [
            "0000000000000000", "000000000aa00000", "00000000a7a00000", "0000000a7a000000",
            "000000a7a0000000", "00000a7aaaaa0000", "000000a777a00000", "00000a7aaaa00000",
            "0000a7a000000000", "000a7a0000000000", "00a7a0aa00000000", "0a7aaa7a00000000",
            "00a7a7a000000000", "000aa7a000000000", "00000a0000000000", "0000000000000000",
        ],
        "creeping_hands": [
            "0000000000000000", "0020020000200200", "0212021202120212", "0212021202120212",
            "0211221122112212", "0021111111111120", "0021111111111120", "0002111111111200",
            "0000211111112000", "0000021111120000", "0000002111200000", "0000002111200000",
            "0000021111120000", "0000211111112000", "0000000000000000", "0000000000000000",
        ],
        "soulfire": [
            "0000000000000000", "0000000c00000000", "000000c7c0000000", "00000c777c000000",
            "0000c77177c00000", "000c7711177c0000", "00c771111177c000", "0c77111111177c00",
            "0c77111111177c00", "00c771111177c000", "000c7711177c0000", "0000c77177c00000",
            "00000c777c000000", "000000c7c0000000", "0000000c00000000", "0000000000000000",
        ],
        "bone_barrier": [
            "0000000000000000", "0077000000007700", "0766700000076670", "0766707777076670",
            "0077076666707700", "0000766556670000", "0000765115670000", "0000765115670000",
            "0000766556670000", "0077076666707700", "0766707777076670", "0766700000076670",
            "0077000000007700", "0000000000000000", "0000000000000000", "0000000000000000",
        ],
        "summon_imp": [
            "0000000000000000", "0800000000000080", "0880000000000880", "0088008888008800",
            "0008888888888000", "00088a8888a88000", "0008808888088000", "0008888888888000",
            "0008887777888000", "0000888888880000", "0000088888800000", "0000008888000000",
            "0000000880000000", "0000000000000000", "0000000000000000", "0000000000000000",
        ],
        "soul_siphon": [
            "0000000000000000", "000000cccc000000", "0000cc7777cc0000", "00cc77111177cc00",
            "0c771100001177c0", "0c710000000017c0", "c71000cc0000017c", "c71000cc0000017c",
            "c710000000cc017c", "0c71000000cc17c0", "0c771100001177c0", "00cc77111177cc00",
            "0000cc7777cc0000", "000000cccc000000", "0000000000000000", "0000000000000000",
        ],
        "pact_of_pain": [
            "0000000880000000", "0000008888000000", "0000088888800000", "0000888ee8880000",
            "000888eeee888000", "00888ee77ee88800", "0888ee7777ee8880", "8888ee7777ee8888",
            "0888ee7777ee8880", "00888ee77ee88800", "000888eeee888000", "0000888ee8880000",
            "0000088888800000", "0000008888000000", "0000000880000000", "0000000000000000",
        ],
        "ice_shards": [
            "0000000000000000", "000c00000000c000", "007c00000007c000", "07cc000c0007cc00",
            "07cc007c0007cc00", "07cc07cc0007cc00", "07cc07cc0007cc00", "07c607cc0007c600",
            "07c607c60007c600", "00c607c60000c600", "00c600c60000c600", "000600c600000600",
            "0006000600000600", "0000000600000000", "0000000000000000", "0000000000000000",
        ],
        "arcane_missiles": [
            "0000000000000000", "0000000000007c00", "000000000007cc70", "00007c0000007c00",
            "0007cc7000000000", "00007c0000000000", "0000000000000000", "0000000000007c00",
            "000000000007cc70", "0000000000007c00", "0000000000000000", "00007c0000000000",
            "0007cc7000000000", "00007c0000000000", "0000000000000000", "0000000000000000",
        ],
        "arcane_reservoir": [
            "0000000000000000", "00000007c0000000", "0000007cc7000000", "00000007c0000000",
            "0000000000000000", "0000000cc0000000", "00000cccccc00000", "07c0cccccccc07c0",
            "7cc7cccccccc7cc7", "07c0cccccccc07c0", "00000cccccc00000", "0000000cc0000000",
            "0000000000000000", "00000007c0000000", "0000007cc7000000", "00000007c0000000",
        ],
        "spell_echo": [
            "0000000000000000", "000000cccc000000", "0000cc7777cc0000", "00cc77000077cc00",
            "0c770000000077c0", "0c7000cccc0007c0", "c7000cc77cc0007c", "c700c700007c007c",
            "c700c700007c007c", "c7000cc77cc0007c", "0c7000cccc0007c0", "0c770000000077c0",
            "00cc77000077cc00", "0000cc7777cc0000", "000000cccc000000", "0000000000000000",
        ],
        "colossus_stance": [
            "0000000000000000", "0000005555000000", "0000056666500000", "0000567777650000",
            "0000567117650000", "0005671111765000", "0056711111176500", "0567111111117650",
            "0567111111117650", "0567111111117650", "0056711111176500", "0005671111765000",
            "0000567117650000", "0000567777650000", "0000056666500000", "0000005555000000",
        ],
        "blade_storm": [
            "0000000700000000", "0000007c70000000", "0700007c70000700", "07c000070000c700",
            "007c0000000c7000", "0007c00000c70000", "00007c000c700000", "777707c0c7077777",
            "77770c707c077777", "00000c707c000000", "0000c70007c00000", "000c7000007c0000",
            "00c700000007c000", "07c0000700007c00", "0700007c70000700", "0000000700000000",
        ],
        "undying_will": [
            "0000000000000000", "00a0000000000a00", "0aa0000aa0000aa0", "0aaa00aaaa00aaa0",
            "0aaaa0aaaa0aaaa0", "0aaaa888888aaaa0", "00aa88eeee88aa00", "00088ee77ee88000",
            "0008ee7777ee8000", "0008ee7777ee8000", "00008ee77ee80000", "0000088ee8800000",
            "0000000880000000", "0000000000000000", "0000000000000000", "0000000000000000",
        ],
        "executioners_might": [
            "0000000000000000", "0004444444444400", "0047777777777400", "0047666666667400",
            "0047655555567400", "0047650000567400", "0047650000567400", "0047655555567400",
            "0047666666667400", "0047777777777400", "0004448888444000", "0000088888800000",
            "000088eeee880000", "0000088888800000", "0000000000000000", "0000000000000000",
        ],
        "assassinate": [
            "0000000000000000", "0000000000000000", "0000001111000000", "0000011111100000",
            "0000111111110000", "0001110000111000", "0001180000811000", "0001110000111000",
            "0000111111110000", "0000011111100000", "0000888888880000", "00088eeeeee88000",
            "0088ee7777ee8800", "00088eeeeee88000", "0000000000000000", "0000000000000000",
        ],
        "fan_of_knives": [
            "0000000000000000", "07c00007c00007c0", "07c00007c00007c0", "007c00007c007c00",
            "007c0007c0007c00", "0007c007c007c000", "0007c007c007c000", "00007c07c07c0000",
            "00007c07c07c0000", "000007c7c7c00000", "0000007770000000", "0000004440000000",
            "0000004440000000", "0000000400000000", "0000000000000000", "0000000000000000",
        ],
        "shadow_dance": [
            "0000000000000000", "0000002222000000", "0000021111200000", "0000211111120000",
            "0000211001120000", "0000021111200000", "0020002222000200", "0212021111202120",
            "2111211111121112", "0212021111202120", "0020021111200200", "0000211001120000",
            "0000210000120000", "0002100000012000", "0000000000000000", "0000000000000000",
        ],
        "death_dealer": [
            "0000000000000000", "0000007777000000", "0000077777700000", "0000770770770000",
            "0000770770770000", "0000077777700000", "0000070770700000", "0000007777000000",
            "0770000000000770", "0077000000007700", "0007700000077000", "0000770000770000",
            "0000077007700000", "0000007777000000", "0000000000000000", "0000000000000000",
        ],
        "meteor": [
            "0000000000000880", "0000000000089800", "0000000000898000", "0000000008980000",
            "0000000089800000", "0000000898000000", "0000008980000000", "0000089800000000",
            "0000898000000000", "0004449800000000", "0049aa9800000000", "049a77a980000000",
            "049a77a980000000", "0049aa9800000000", "0004440000000000", "0000000000000000",
        ],
        "time_stop": [
            "0000000aa0000000", "000000a77a000000", "0000000aa0000000", "0000aaaaaa000000",
            "000a77cccc7a0000", "00a7cc0000cc7a00", "0a7c00000000c7a0", "0a7c00070000c7a0",
            "0a7c00077700c7a0", "0a7c00000000c7a0", "00a7cc0000cc7a00", "000a77cccc7a0000",
            "0000aaaaaa000000", "0000000000000000", "0000000000000000", "0000000000000000",
        ],
        "time_dilation": [
            "0000000000000000", "0000000cc0000000", "000000c77c000000", "0000000cc0000000",
            "0000cccccc000000", "000c77aaaa7c0000", "00c7aa0000aa7c00", "0c7a00000000a7c0",
            "0c7a000c0000a7c0", "0c7a000cc700a7c0", "00c7aa0000aa7c00", "000c77aaaa7c0000",
            "0000cccccc000000", "0000000000000000", "0000000000000000", "0000000000000000",
        ],
        "phoenix_rebirth": [
            "0000000000000000", "0a000000000000a0", "09a0000aa0000a90", "089a00aaaa00a980",
            "0089a0aaaa0a9800", "00089aaaaaa98000", "000089a77a980000", "000089a77a980000",
            "0000089aa9800000", "0000008998000000", "0000000880000000", "0000008998000000",
            "0000089aa9800000", "000089a77a980000", "0000000000000000", "0000000000000000",
        ],
        "default": [
            "0000000000000000", "0000000aa0000000", "000000a77a000000", "00000a7cc7a00000",
            "0000a7cccc7a0000", "000a7cccccc7a000", "00a7cccccccc7a00", "0a7cccccccccc7a0",
            "0a7cccccccccc7a0", "00a7cccccccc7a00", "000a7cccccc7a000", "0000a7cccc7a0000",
            "00000a7cc7a00000", "000000a77a000000", "0000000aa0000000", "0000000000000000",
        ],
    }

    # 16x16 Ability Icons in Bank 1 (y=32..96)
    for aid, (u, v) in ABILITY_ICON_COORDS.items():
        sprite = ABILITY_SPRITES.get(aid, ABILITY_SPRITES["default"])
        pyxel.images[1].set(u, v, sprite)

    def create_humanoid_lich():
        W, H = 24, 28
        g = [["0" for _ in range(W)] for _ in range(H)]
        g[2][20] = "c"
        g[2][21] = "7"
        g[1][20] = "c"
        g[1][21] = "c"
        g[3][19] = "a"
        g[3][22] = "a"
        g[4][20] = "a"
        g[4][21] = "a"
        for sy in range(5, 27): g[sy][21] = "4"
        g[13][21] = "7"
        g[14][21] = "7"

        for x in range(9, 14): g[3][x] = "1"
        for x in range(8, 15): g[4][x] = "1"
        g[4][10] = "2"
        g[4][11] = "2"
        g[4][12] = "2"
        g[2][11] = "1"
        g[1][11] = "a"

        for y in range(5, 10):
            for x in range(9, 14): g[y][x] = "0"

        g[5][10] = "7"
        g[5][11] = "7"
        g[5][12] = "7"
        g[6][10] = "e"
        g[6][11] = "7"
        g[6][12] = "e"
        g[7][10] = "7"
        g[7][11] = "0"
        g[7][12] = "7"
        g[8][10] = "7"
        g[8][11] = "5"
        g[8][12] = "7"

        for y in range(9, 12):
            w = (y - 8) * 3 + 2
            for x in range(11 - w // 2, 11 + w // 2 + 1):
                if 0 <= x < W and g[y][x] == "0":
                    g[y][x] = "2" if (x + y) % 2 == 0 else "1"
        g[10][11] = "a"
        g[11][11] = "9"

        g[11][7] = "2"
        g[11][6] = "1"
        g[12][6] = "2"
        g[12][5] = "1"
        g[13][5] = "2"
        g[13][4] = "1"
        g[12][3] = "7"
        g[12][4] = "7"
        g[11][2] = "7"
        g[12][1] = "c"
        g[13][2] = "7"
        g[11][0] = "c"
        g[12][0] = "7"
        g[13][1] = "c"

        for y in range(12, 18):
            for x in range(8, 15):
                if g[y][x] == "0":
                    g[y][x] = "1" if (x == 8 or x == 14) else "2"
        for y in range(14, 26):
            g[y][11] = "0"
            g[y][9] = "1"
            g[y][13] = "1"

        for y in range(18, 27):
            half_w = 4 + int((y - 18) * 0.7)
            for x in range(11 - half_w, 11 + half_w + 1):
                if 0 <= x < W and g[y][x] == "0":
                    g[y][x] = "2" if (x + y) % 3 != 0 else "1"

        for x in range(4, 19):
            if (x * 7) % 3 == 0:
                g[26][x] = "0"
                g[27][x] = "0"
            elif g[26][x] != "0":
                g[27][x] = "1"

        return ["".join(row) for row in g]

    pyxel.images[1].set(144, 0, create_humanoid_lich())

    def create_gargoyle():
        W, H = 24, 32
        g = [["0" for _ in range(W)] for _ in range(H)]
        for y in range(22, 32):
            for x in range(2, 22): g[y][x] = "5"
        for x in range(2, 22):
            g[22][x] = "6"
            g[31][x] = "1"
        for y in range(23, 31):
            g[y][2] = "6"
            g[y][21] = "1"
            if y == 27:
                for x in range(2, 22): g[y][x] = "1"

        beast_rows = [
            (2, 8, "0500050"), (3, 7, "0550550"), (4, 6, "5665665"), (5, 5, "56666665"),
            (6, 6, "5866685"), (7, 6, "5566655"), (8, 7, "55555"), (9, 4, "5665555665"),
            (10, 3, "566665566665"), (11, 2, "5666666556666665"), (12, 2, "5655666556665565"),
            (13, 2, "5500566666650055"), (14, 6, "56655665"), (15, 6, "56655665"),
            (16, 6, "55555555"), (17, 5, "565000565"), (18, 5, "565000565"),
            (19, 4, "5555005555"), (20, 3, "666666666666"), (21, 2, "55555555555555"),
        ]
        for y, start_x, row in beast_rows:
            for i, ch in enumerate(row):
                if ch != '0': g[y][start_x + i] = ch

        return ["".join(row) for row in g]

    pyxel.images[1].set(168, 0, create_gargoyle())

    # Corner Skull at (192, 0)
    pyxel.images[1].set(192, 0, [
        "07777770", "77777777", "78777787", "70777707",
        "07700770", "00777700", "00755700", "00000000"
    ])

    # Sword Cursor at (200, 0)
    pyxel.images[1].set(200, 0, [
        "00000007", "0000007c", "000007c0", "0a007c00",
        "0aa7c000", "00aa0000", "040aa000", "4000a000"
    ])

    # =========================================================================
    # SOUND EFFECTS (Channel 3, IDs 0-7)
    # =========================================================================
    pyxel.sounds[0].set("g2c2", "n", "74", "s", 6)  # 0: Hit
    pyxel.sounds[1].set("c3g3c4", "t", "777", "n", 4)  # 1: Crit
    pyxel.sounds[2].set("c3e3g3c4", "p", "5567", "f", 7)  # 2: Heal
    pyxel.sounds[3].set("g3c4", "p", "45", "n", 3)  # 3: Click
    pyxel.sounds[4].set("c3e3g3c4e4g4", "t", "666777", "v", 12)  # 4: Victory
    pyxel.sounds[5].set("f3e3d3c3", "s", "7654", "f", 16)  # 5: Defeat
    pyxel.sounds[6].set("c2e2g2b2d3", "s", "65543", "s", 5)  # 6: Chest open / latch
    pyxel.sounds[7].set("g1d2g2c3", "t", "7654", "f", 9)  # 7: Shop door / chime

    # =========================================================================
    # COMPOSITION SOUND SECTIONS (Bank Sounds 10-40)
    # =========================================================================
    # Drums & Rhythm
    pyxel.sounds[10].set("c2c2", "n", "72", "f", 8)  # Kick
    pyxel.sounds[11].set("g2", "n", "6", "f", 8)  # Snare
    pyxel.sounds[12].set("d3", "n", "3", "f", 4)  # Hi-hat

    # Title Theme Phrases
    pyxel.sounds[13].set("a2c3e3a3 g2b2d3g3", "p", "6666 5555", "v", 12)  # Title Lead A
    pyxel.sounds[14].set("f2a2c3f3 e2g2b2e3", "p", "6666 5555", "v", 12)  # Title Lead B
    pyxel.sounds[15].set("a1r a1r g1r g1r", "t", "70 70 70 70", "n", 12)  # Title Bass A
    pyxel.sounds[16].set("f1r f1r e1r e1r", "t", "70 70 70 70", "n", 12)  # Title Bass B

    # Combat Theme Phrases
    pyxel.sounds[17].set("a2a2c3d3 e3d3c3a2", "s", "7777 6666", "n", 6)  # Combat Lead A
    pyxel.sounds[18].set("g2g2b2c3 d3c3b2g2", "s", "7777 6666", "n", 6)  # Combat Lead B
    pyxel.sounds[19].set("a1a1a1a1 a1a1a1a1", "t", "7655 7655", "n", 6)  # Combat Bass A
    pyxel.sounds[20].set("g1g1g1g1 g1g1g1g1", "t", "7655 7655", "n", 6)  # Combat Bass B

    # Boss Theme Phrases (High Tempo)
    pyxel.sounds[21].set("d3d3f3g3 a3g3f3d3", "s", "7777 7777", "s", 4)  # Boss Lead A
    pyxel.sounds[22].set("c3c3e3f3 g3f3e3c3", "s", "7777 7777", "s", 4)  # Boss Lead B
    pyxel.sounds[23].set("d1d1d1d1 d1d1d1d1", "t", "7777 7777", "n", 4)  # Boss Bass A
    pyxel.sounds[24].set("a0a0a0a0 a0a0a0a0", "t", "7777 7777", "n", 4)  # Boss Bass B

    # Biome Exploration Phrases
    # Arboretum (Wilted organic minor)
    pyxel.sounds[25].set("c3e3g3b3 a3f3d3b2", "p", "5555 4444", "v", 14)
    pyxel.sounds[26].set("a1r e2r c2r e1r", "t", "60 50 60 50", "f", 14)
    # Cathedral (Sacred organ / solemn bell)
    pyxel.sounds[27].set("e3g3b3e4 d3f3a3d4", "s", "6666 5555", "n", 16)
    pyxel.sounds[28].set("e1e2e1e2 d1d2d1d2", "t", "7777 6666", "f", 16)
    # Ossuary (Submerged water drop dissonance)
    pyxel.sounds[29].set("f3r c3r g2r e3r", "p", "60 50 60 50", "v", 16)
    pyxel.sounds[30].set("f1c2 f1c2 e1b1 e1b1", "t", "66 66 66 66", "n", 16)
    # Foundry (Heavy clanking industrial pulse)
    pyxel.sounds[31].set("d2d2f2d2 a2d2f2d2", "s", "7676 7676", "n", 8)
    pyxel.sounds[32].set("d1r d1r d1r d1r", "t", "70 70 70 70", "n", 8)
    # Observatory (Celestial D Dorian arpeggios)
    pyxel.sounds[33].set("d3f3a3c4 e4c4a3f3", "p", "5555 5555", "v", 10)
    pyxel.sounds[34].set("d1r a1r d2r a1r", "t", "60 50 60 50", "f", 10)
    # Sanctum (Vampiric baroque minor)
    pyxel.sounds[35].set("a2d3f3a3 g3e3c3b2", "s", "7777 6666", "s", 8)
    pyxel.sounds[36].set("a1r d2r a1r d2r", "t", "70 60 70 60", "n", 8)

    # =========================================================================
    # MUSIC TRACKS (Channels 0, 1, 2)
    # Note: Pyxel supports 8 hardware music slots (0-7).
    # Audio playback for all 9 tracks is managed via audio.py using sound banks.
    # =========================================================================
    # 0: Title Theme
    pyxel.musics[0].set([13, 14], [15, 16], [])
    # 1: Standard Combat
    pyxel.musics[1].set([17, 18], [19, 20], [10, 11, 10, 12])
    # 2: Boss Battle
    pyxel.musics[2].set([21, 22], [23, 24], [10, 11, 10, 11])
    # 3: Arboretum Map
    pyxel.musics[3].set([25], [26], [])
    # 4: Cathedral Map
    pyxel.musics[4].set([27], [28], [])
    # 5: Ossuary Map
    pyxel.musics[5].set([29], [30], [12])
    # 6: Foundry Map
    pyxel.musics[6].set([31], [32], [10, 11])
    # 7: Observatory Map
    pyxel.musics[7].set([33], [34], [])
    # (Removed pyxel.musics[8] to avoid the 8-slot IndexError)

    pyxel.save(str(output_path))
    print(f"Successfully generated asset package: {output_path}")


def get_enemy_sprite(archetype_id: str) -> tuple[int, int]:
    """Retrieve Bank 0 (u, v) tile coordinates for any enemy archetype."""
    return ENEMY_SPRITE_COORDS.get(archetype_id, (16, 0))


def get_class_portrait(class_id: str) -> tuple[int, int]:
    """Retrieve Bank 0 (u, v) tile coordinates for a class portrait (48x64)."""
    return CLASS_PORTRAIT_COORDS.get(class_id, (0, 144))


def get_ability_icon(ability_id: str) -> tuple[int, int, int]:
    """Retrieve (image_bank, u, v) tile coordinates for an ability icon (16x16) with safe fallback."""
    u, v = ABILITY_ICON_COORDS.get(ability_id, ABILITY_ICON_COORDS["default"])
    return (1, u, v)


if __name__ == "__main__":
    build_assets()
