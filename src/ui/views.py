"""View switching architecture including CombatView, MapView, and InventoryView."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pyxel

from src.config import (
    COLOR_BLACK,
    COLOR_BROWN,
    COLOR_CYAN,
    COLOR_DARK_BLUE,
    COLOR_GRAY,
    COLOR_GREEN,
    COLOR_LIGHT_BLUE,
    COLOR_LIME,
    COLOR_NAVY,
    COLOR_ORANGE,
    COLOR_PEACH,
    COLOR_PINK,
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from src.core.game_state import GameMode
from src.core.i18n import i18n, t
from src.entities import Enemy
from src.systems.abilities import Ability, AbilityRarity, AbilityType, get_random_abilities
from src.systems.combat import ACTION_THRESHOLD
from src.systems.inventory import MAX_BELT_SLOTS, MAX_POUCH_SLOTS, EquipSlot
from src.systems.map_gen import NodeType
from src.ui import renderer
from src.ui.renderer import Renderer

if TYPE_CHECKING:
    from src.core.game_state import GameState

# =============================================================================
# BIOME ENEMY SPRITE COORDINATE MAP (Bank 0)
# =============================================================================
ENEMY_SPRITE_COORDS: dict[str, tuple[int, int]] = {
    # Act 1A: The Wilted Arboretum (y=48)
    "thornvein_creeper": (0, 48),
    "spore_pod": (16, 48),
    "bramble_hound": (32, 48),
    "rotting_woodwose": (48, 48),
    "mandragora_matron": (64, 48),
    "corpse_treant": (80, 48),
    "malignant_belladonna": (96, 48),
    "verdant_abomination": (112, 48),

    # Act 1B: The Desecrated Cathedral (y=64)
    "cathedral_imp": (0, 64),
    "possessed_grimoire": (16, 64),
    "candelabra_fiend": (32, 64),
    "penitent_zealot": (48, 64),
    "belltower_gargoyle": (64, 64),
    "inquisitor_automaton": (80, 64),
    "blind_archbishop": (96, 64),
    "chorus_of_damned": (112, 64),

    # Act 2A: The Drowned Ossuary (y=80)
    "mire_ghoul": (0, 80),
    "drowned_skulls": (16, 80),
    "leech_husk": (32, 80),
    "crypt_lurker": (48, 80),
    "tide_gravekeeper": (64, 80),
    "carrion_behemoth": (80, 80),
    "drowned_patriarch": (96, 80),
    "scylla_bone_weaver": (112, 80),

    # Act 2B: The Foundry of Torment (y=96)
    "slag_homunculus": (0, 96),
    "cinder_sprite": (16, 96),
    "clockwork_flayer": (32, 96),
    "ashen_overseer": (48, 96),
    "furnace_warden": (64, 96),
    "retching_alchemist": (80, 96),
    "ironforge_tyrant": (96, 96),
    "molten_sovereign": (112, 96),

    # Act 3A: The Astral Observatory (y=112)
    "void_mirror": (0, 112),
    "stareater_wisp": (16, 112),
    "comet_stalker": (32, 112),
    "celestial_hermit": (48, 112),
    "rift_warden": (64, 112),
    "null_singularity": (80, 112),
    "chronomancer_praetor": (96, 112),
    "devouring_constellation": (112, 112),

    # Act 3B: The Blood Sanctum (y=128)
    "sanguine_thrall": (0, 128),
    "crimson_gargoyle": (16, 128),
    "hemomancer_acolyte": (32, 128),
    "flayed_duelist": (48, 128),
    "baroness_vespera": (64, 128),
    "amalgam_of_veins": (80, 128),
    "high_lord_carmilla": (96, 128),
    "blood_god_avatar": (112, 128),
}

SPEED_INTERVALS = [15, 7, 2]
SPEED_LABELS = ["1x", "2x", "3x"]


@dataclass
class CombatPopup:
    x: int
    y: int
    text: str
    color: int
    lifetime: int = 18


class View:
    """Base abstract interface for game screens."""

    def update(self, game_state: GameState) -> None:
        pass

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pass

class BiomeSelectView(View):
    """Renders the expedition route selection screen with panoramic biome vistas, threat icons, and gold frames."""

    def __init__(self) -> None:
        self.selected_index: int = 0

    def update(self, game_state: GameState) -> None:
        from src.config import SND_CLICK, SND_VICTORY
        from src.data.biomes import ACT_BIOMES
        if game_state.act not in ACT_BIOMES:
            return

        biome_a_id, biome_b_id = ACT_BIOMES[game_state.act]
        target_id = biome_a_id if self.selected_index == 0 else biome_b_id

        # Keyboard directional toggle
        if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
            self.selected_index = 0
            pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
            self.selected_index = 1
            pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_1) or pyxel.btnp(pyxel.KEY_KP_1):
            if self.selected_index == 0:
                pyxel.play(0, SND_VICTORY)
                game_state.advance_act(target_biome_id=biome_a_id)
            else:
                self.selected_index = 0
                pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_2) or pyxel.btnp(pyxel.KEY_KP_2):
            if self.selected_index == 1:
                pyxel.play(0, SND_VICTORY)
                game_state.advance_act(target_biome_id=biome_b_id)
            else:
                self.selected_index = 1
                pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            pyxel.play(0, SND_VICTORY)
            game_state.advance_act(target_biome_id=target_id)

        # Mouse / Tap click on cards
        card_w, card_h = 119, 184
        if Renderer.is_clicked(7, 50, card_w, card_h):
            if self.selected_index == 0:
                pyxel.play(0, SND_VICTORY)
                game_state.advance_act(target_biome_id=biome_a_id)
            else:
                self.selected_index = 0
                pyxel.play(0, SND_CLICK)
        elif Renderer.is_clicked(130, 50, card_w, card_h):
            if self.selected_index == 1:
                pyxel.play(0, SND_VICTORY)
                game_state.advance_act(target_biome_id=biome_b_id)
            else:
                self.selected_index = 1
                pyxel.play(0, SND_CLICK)

    def _draw_threat_icon(self, x: int, y: int, icon_type: str) -> None:
        """Render distinct 6x6 pixel glyphs for biome threats."""
        t_lower = icon_type.lower()
        if any(k in t_lower for k in ("creeper", "root", "hound", "bramble")):
            # Green sprout / vine
            pyxel.line(x + 2, y + 5, x + 2, y + 2, COLOR_GREEN)
            pyxel.pset(x + 1, y + 1, COLOR_LIME)
            pyxel.pset(x + 3, y, COLOR_LIME)
            pyxel.pset(x, y + 3, COLOR_GREEN)
            pyxel.pset(x + 4, y + 3, COLOR_GREEN)
        elif any(k in t_lower for k in ("spore", "pod", "mushroom")):
            # Purple & pink poison mushroom
            pyxel.rect(x + 1, y, 5, 3, COLOR_PURPLE)
            pyxel.pset(x + 2, y + 1, COLOR_PINK)
            pyxel.pset(x + 4, y + 1, COLOR_PINK)
            pyxel.rect(x + 2, y + 3, 3, 3, COLOR_WHITE)
        elif any(k in t_lower for k in ("imp", "cinder", "burn", "flame")):
            # Flame ember
            pyxel.pset(x + 2, y, COLOR_YELLOW)
            pyxel.rect(x + 1, y + 1, 3, 3, COLOR_ORANGE)
            pyxel.pset(x + 2, y + 2, COLOR_YELLOW)
            pyxel.rect(x + 1, y + 4, 3, 2, COLOR_RED)
        elif any(k in t_lower for k in ("grimoire", "tome", "book")):
            # Grimoire spellbook
            pyxel.rect(x, y + 1, 6, 5, COLOR_LIGHT_BLUE)
            pyxel.line(x + 2, y + 1, x + 2, y + 5, COLOR_NAVY)
            pyxel.pset(x + 1, y + 2, COLOR_WHITE)
            pyxel.pset(x + 4, y + 2, COLOR_WHITE)
        elif any(k in t_lower for k in ("ward", "arcane", "missile", "fiend", "candelabra")):
            # Arcane diamond spark
            pyxel.pset(x + 2, y, COLOR_CYAN)
            pyxel.line(x, y + 2, x + 4, y + 2, COLOR_CYAN)
            pyxel.pset(x + 2, y + 4, COLOR_CYAN)
            pyxel.pset(x + 2, y + 2, COLOR_WHITE)
        else:
            # Danger skull
            pyxel.rect(x + 1, y, 4, 3, COLOR_WHITE)
            pyxel.pset(x + 2, y + 1, COLOR_BLACK)
            pyxel.pset(x + 3, y + 1, COLOR_BLACK)
            pyxel.rect(x + 2, y + 3, 2, 2, COLOR_WHITE)

    def _draw_boss_icon(self, x: int, y: int, boss_name: str) -> None:
        """Render distinct 6x6 pixel glyphs for act bosses."""
        b_lower = boss_name.lower()
        if "archbishop" in b_lower:
            # High priest mitre hood
            pyxel.tri(x + 2, y, x, y + 5, x + 4, y + 5, COLOR_PINK)
            pyxel.line(x + 2, y + 1, x + 2, y + 4, COLOR_YELLOW)
            pyxel.pset(x + 1, y + 3, COLOR_YELLOW)
            pyxel.pset(x + 3, y + 3, COLOR_YELLOW)
        elif any(k in b_lower for k in ("choir", "chorus", "rite", "damned")):
            # Sunburst / Damned crest
            pyxel.circ(x + 2, y + 2, 2, COLOR_RED)
            pyxel.pset(x + 2, y + 2, COLOR_YELLOW)
            pyxel.pset(x + 2, y, COLOR_ORANGE)
            pyxel.pset(x + 2, y + 4, COLOR_ORANGE)
            pyxel.pset(x, y + 2, COLOR_ORANGE)
            pyxel.pset(x + 4, y + 2, COLOR_ORANGE)
        else:
            # Pink horned boss skull
            pyxel.rect(x + 1, y + 1, 4, 3, COLOR_PINK)
            pyxel.pset(x, y, COLOR_RED)
            pyxel.pset(x + 4, y, COLOR_RED)
            pyxel.pset(x + 2, y + 2, COLOR_BLACK)
            pyxel.pset(x + 3, y + 2, COLOR_BLACK)
            pyxel.rect(x + 2, y + 4, 2, 1, COLOR_PINK)

    def _draw_biome_vista(self, vx: int, vy: int, vw: int, vh: int, biome_id: str) -> None:
        """Render detailed procedural landscape vistas inside the card window."""
        fc = pyxel.frame_count

        if biome_id == "arboretum":
            pyxel.rect(vx, vy, vw, vh, COLOR_DARK_BLUE)
            # Three vaulted greenhouse windows
            for cx in [vx + 18, vx + 56, vx + 94]:
                pyxel.rect(cx - 13, vy + 4, 26, 22, COLOR_NAVY)
                pyxel.tri(cx - 13, vy + 4, cx, vy - 1, cx + 12, vy + 4, COLOR_NAVY)
                pyxel.rect(cx - 11, vy + 6, 22, 20, COLOR_LIGHT_BLUE)
                pyxel.tri(cx - 11, vy + 6, cx, vy + 1, cx + 10, vy + 6, COLOR_LIGHT_BLUE)
                pyxel.line(cx, vy + 1, cx, vy + 25, COLOR_NAVY)
                pyxel.line(cx - 11, vy + 14, cx + 10, vy + 14, COLOR_NAVY)
                pyxel.pset(cx - 5, vy + 9, COLOR_CYAN)
                pyxel.pset(cx + 5, vy + 9, COLOR_CYAN)

            # Central fountain basin
            pyxel.rect(vx + 48, vy + 22, 16, 9, COLOR_NAVY)
            pyxel.rect(vx + 52, vy + 18, 8, 4, COLOR_DARK_BLUE)
            pyxel.pset(vx + 55, vy + 16, COLOR_CYAN)
            pyxel.pset(vx + 56, vy + 16, COLOR_WHITE)

            # Cobblestone pathway
            for fy in range(vy + 25, vy + vh):
                pyxel.line(vx + 34, fy, vx + vw - 35, fy, COLOR_NAVY if fy % 2 == 0 else COLOR_BLACK)

            # Hanging vines with leaves
            for ix in range(vx + 4, vx + vw - 4, 8):
                ih = 3 + (ix % 4)
                pyxel.line(ix, vy, ix, vy + ih, COLOR_GREEN)
                pyxel.pset(ix, vy + ih, COLOR_LIME)

            # Purple mushroom clusters
            for mx, my in [(vx + 6, vy + 31), (vx + 14, vy + 33), (vx + vw - 16, vy + 31), (vx + vw - 8, vy + 33)]:
                pyxel.rect(mx, my, 4, 3, COLOR_PURPLE)
                pyxel.pset(mx + 1, my, COLOR_PINK)
                pyxel.pset(mx + 2, my, COLOR_WHITE)
                pyxel.rect(mx + 1, my + 3, 2, 2, COLOR_WHITE)

        elif biome_id == "cathedral":
            pyxel.rect(vx, vy, vw, vh, COLOR_BLACK)

            # Vaulted gothic arch
            pyxel.rect(vx + 40, vy + 3, 32, 34, COLOR_NAVY)
            pyxel.tri(vx + 40, vy + 3, vx + 56, vy - 2, vx + 71, vy + 3, COLOR_NAVY)

            # Stained glass rose window
            rw_x, rw_y = vx + 56, vy + 12
            pyxel.circ(rw_x, rw_y, 8, COLOR_RED)
            pyxel.circb(rw_x, rw_y, 8, COLOR_DARK_BLUE)
            pyxel.line(rw_x - 7, rw_y, rw_x + 7, rw_y, COLOR_DARK_BLUE)
            pyxel.line(rw_x, rw_y - 7, rw_x, rw_y + 7, COLOR_DARK_BLUE)
            pyxel.pset(rw_x, rw_y, COLOR_YELLOW)
            for px_val, py_val in [(rw_x - 3, rw_y - 3), (rw_x + 3, rw_y - 3), (rw_x - 3, rw_y + 3), (rw_x + 3, rw_y + 3)]:
                pyxel.pset(px_val, py_val, COLOR_PINK)

            # Flanking lancet stained glass windows
            for wx in [vx + 14, vx + vw - 22]:
                pyxel.rect(wx, vy + 6, 8, 22, COLOR_RED)
                pyxel.tri(wx, vy + 6, wx + 4, vy + 1, wx + 7, vy + 6, COLOR_RED)
                pyxel.line(wx + 3, vy + 1, wx + 3, vy + 27, COLOR_NAVY)

            # Iron cage lanterns
            for lx in [vx + 26, vx + vw - 32]:
                pyxel.line(lx + 2, vy, lx + 2, vy + 5, COLOR_GRAY)
                pyxel.rectb(lx, vy + 5, 5, 7, COLOR_BROWN)
                pyxel.pset(lx + 2, vy + 8, COLOR_YELLOW if fc % 4 < 2 else COLOR_ORANGE)

            # Altar candles
            for cx, cy in [(vx + 6, vy + 30), (vx + 10, vy + 28), (vx + vw - 14, vy + 28), (vx + vw - 10, vy + 30)]:
                pyxel.line(cx, cy, cx, cy + 5, COLOR_WHITE)
                pyxel.pset(cx, cy - 1, COLOR_YELLOW)

            # Altar skull
            pyxel.circ(vx + vw - 14, vy + 35, 2, COLOR_PEACH)
            pyxel.pset(vx + vw - 14, vy + 35, COLOR_BLACK)

        elif biome_id == "ossuary":
            pyxel.rect(vx, vy, vw, vh, COLOR_DARK_BLUE)
            for ay in range(vy + 3, vy + 20, 5):
                pyxel.line(vx + 4, ay, vx + vw - 5, ay, COLOR_NAVY)
            pyxel.rect(vx, vy + 22, vw, vh - 22, COLOR_BLACK)
            for wy in range(vy + 24, vy + vh, 3):
                pyxel.line(vx + 12, wy, vx + vw - 13, wy, COLOR_CYAN if wy % 2 == 0 else COLOR_DARK_BLUE)
            pyxel.circ(vx + 42, vy + 28, 3, COLOR_WHITE)
            pyxel.circ(vx + 78, vy + 30, 3, COLOR_WHITE)

        elif biome_id == "foundry":
            pyxel.rect(vx, vy, vw, vh, COLOR_BLACK)
            pyxel.rect(vx + 34, vy + 6, 44, 26, COLOR_RED)
            pyxel.tri(vx + 34, vy + 6, vx + 56, vy + 1, vx + 77, vy + 6, COLOR_RED)
            pyxel.rect(vx + 42, vy + 13, 28, 19, COLOR_ORANGE)
            pyxel.rect(vx + 48, vy + 18, 16, 14, COLOR_YELLOW)
            pyxel.line(vx + 56, vy + 13, vx + 56, vy + vh, COLOR_WHITE)

        elif biome_id == "observatory":
            pyxel.rect(vx, vy, vw, vh, COLOR_NAVY)
            for sx in range(vx + 6, vx + vw - 6, 14):
                sy = vy + 3 + (sx * 7) % 20
                pyxel.pset(sx, sy, COLOR_WHITE if (fc + sx) % 18 < 9 else COLOR_CYAN)
            pyxel.line(vx + 38, vy + 32, vx + 76, vy + 8, COLOR_BROWN)
            pyxel.line(vx + 39, vy + 32, vx + 77, vy + 8, COLOR_YELLOW)
            pyxel.circ(vx + 78, vy + 7, 3, COLOR_CYAN)

        else:  # sanctum
            pyxel.rect(vx, vy, vw, vh, COLOR_BLACK)
            pyxel.circ(vx + 56, vy + 12, 9, COLOR_RED)
            pyxel.circ(vx + 55, vy + 11, 8, COLOR_PINK)
            pyxel.rect(vx + 4, vy, 16, vh, COLOR_RED)
            pyxel.rect(vx + vw - 20, vy, 16, vh, COLOR_RED)
            pyxel.rectb(vx + 4, vy, 16, vh, COLOR_ORANGE)
            pyxel.rectb(vx + vw - 20, vy, 16, vh, COLOR_ORANGE)

        pyxel.rectb(vx, vy, vw, vh, COLOR_DARK_BLUE)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        box_x, box_y, box_w, box_h = 4, 25, SCREEN_WIDTH - 8, SCREEN_HEIGHT - 28
        fc = pyxel.frame_count
        pulse = (fc // 6) % 2

        # =====================================================================
        # 1. GOTHIC CHAMBER BACKDROP (y=25..49)
        # =====================================================================
        pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

        # Masonry stone wall columns in header section
        for px in [16, 44, SCREEN_WIDTH - 52, SCREEN_WIDTH - 24]:
            pyxel.rect(px, box_y + 1, 8, 20, COLOR_NAVY)
            pyxel.line(px, box_y + 6, px + 7, box_y + 6, COLOR_DARK_BLUE)
            pyxel.line(px, box_y + 14, px + 7, box_y + 14, COLOR_DARK_BLUE)

        # Banners (capped strictly above cards at y=43)
        for bx in [10, SCREEN_WIDTH - 22]:
            pyxel.rect(bx, box_y + 2, 12, 13, COLOR_RED)
            pyxel.tri(bx, box_y + 15, bx + 6, box_y + 18, bx + 11, box_y + 15, COLOR_RED)
            pyxel.rectb(bx, box_y + 2, 12, 13, COLOR_ORANGE)
            pyxel.pset(bx + 5, box_y + 7, COLOR_YELLOW)
            pyxel.pset(bx + 6, box_y + 7, COLOR_YELLOW)

        # Torches (capped strictly above cards at y=41)
        for tx in [30, SCREEN_WIDTH - 38]:
            ty = box_y + 4
            pyxel.rect(tx - 1, ty + 6, 4, 3, COLOR_BROWN)
            pyxel.rect(tx - 1, ty + 2, 4, 4, COLOR_ORANGE)
            pyxel.pset(tx + (1 if fc % 4 < 2 else 0), ty, COLOR_YELLOW)
            pyxel.pset(tx + 1, ty + 1, COLOR_WHITE)

        # =====================================================================
        # 2. HEADER BANNER PLAQUE (EXPEDITION ROUTE)
        # =====================================================================
        pw, ph = 156, 18
        px = (SCREEN_WIDTH - pw) // 2
        py = box_y + 3

        renderer.draw_box(px, py, pw, ph, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE)
        pyxel.rectb(px + 1, py + 1, pw - 2, ph - 2, COLOR_NAVY)

        act_str = f"✦ ACT {game_state.act} ✦" if i18n.locale == "en" else f"✦ ACTO {game_state.act} ✦"
        renderer.draw_text(SCREEN_WIDTH // 2 - len(act_str) * 2, py + 3, act_str, COLOR_LIGHT_BLUE)

        route_title = "❖ EXPEDITION ROUTE ❖" if i18n.locale == "en" else "❖ RUTA DE EXPEDICIÓN ❖"
        renderer.draw_text(SCREEN_WIDTH // 2 - len(route_title) * 2, py + 10, route_title, COLOR_YELLOW)

        # =====================================================================
        # 3. DUAL BIOME EXPEDITION CARDS (y=50..234)
        # =====================================================================
        from src.data.biomes import ACT_BIOMES, get_biome
        if game_state.act not in ACT_BIOMES:
            return

        biome_a_id, biome_b_id = ACT_BIOMES[game_state.act]
        biome_a = get_biome(biome_a_id)
        biome_b = get_biome(biome_b_id)

        card_w, card_h = 119, 184
        card_y = 50
        cards = [(biome_a, 7, 0), (biome_b, 130, 1)]

        for biome, card_x, idx in cards:
            if not biome:
                continue

            is_sel = (self.selected_index == idx)
            border_col = COLOR_YELLOW if is_sel else (COLOR_PINK if idx == 1 else COLOR_LIGHT_BLUE)
            fill_col = COLOR_DARK_BLUE if is_sel else COLOR_BLACK

            renderer.draw_box(card_x, card_y, card_w, card_h, bg_col=fill_col, border_col=border_col)

            if is_sel:
                pyxel.rectb(card_x + 1, card_y + 1, card_w - 2, card_h - 2, COLOR_YELLOW if pulse == 0 else COLOR_ORANGE)
                pyxel.pset(card_x + 2, card_y + 2, COLOR_WHITE)
                pyxel.pset(card_x + card_w - 3, card_y + 2, COLOR_WHITE)
                pyxel.pset(card_x + 2, card_y + card_h - 3, COLOR_WHITE)
                pyxel.pset(card_x + card_w - 3, card_y + card_h - 3, COLOR_WHITE)

            # 1. Scenic Landscape Vista Window (113x40)
            vw, vh = card_w - 6, 40
            vx, vy = card_x + 3, card_y + 3
            self._draw_biome_vista(vx, vy, vw, vh, biome.id)

            # 2. Biome Full Name (Single line, complete)
            renderer.draw_text(card_x + 5, card_y + 46, biome.localized_name, COLOR_YELLOW)

            # 3. Formatted Archetype Tags (Single line)
            tag_color = COLOR_CYAN if idx == 0 else COLOR_PINK
            tags_clean = biome.localized_tags.replace("Root Stalls", "Roots").replace("Missiles / Wards", "Wards")
            renderer.draw_text(card_x + 5, card_y + 55, tags_clean, tag_color)

            # 4. Biome Lore Description (4 lines, complete, 25 chars per line)
            desc_lines = renderer.wrap_text(biome.localized_description, max_chars_per_line=25)
            for li, line in enumerate(desc_lines[:4]):
                renderer.draw_text(card_x + 5, card_y + 64 + li * 7, line, COLOR_WHITE)

            # Divider 1
            pyxel.line(card_x + 4, card_y + 94, card_x + card_w - 5, card_y + 94, COLOR_NAVY)

            # 5. Threats List (Full names, complete)
            renderer.draw_text(card_x + 5, card_y + 97, t("biome_threats"), COLOR_ORANGE)
            from src.entities.enemy import ENEMY_CATALOG

            threat_names = []
            for e_id in biome.basic_enemies[:3]:
                if e_id in ENEMY_CATALOG:
                    threat_names.append(ENEMY_CATALOG[e_id].localized_name)
                else:
                    threat_names.append(e_id.replace('_', ' ').title())

            for ti, tname in enumerate(threat_names[:3]):
                ty = card_y + 105 + ti * 8
                self._draw_threat_icon(card_x + 5, ty, tname)
                renderer.draw_text(card_x + 13, ty, tname, COLOR_WHITE)

            # Divider 2
            pyxel.line(card_x + 4, card_y + 130, card_x + card_w - 5, card_y + 130, COLOR_NAVY)

            # 6. Bosses List (Full names, complete)
            renderer.draw_text(card_x + 5, card_y + 133, t("biome_bosses"), COLOR_PEACH)
            boss_names = []
            for b_id in biome.bosses[:2]:
                if b_id in ENEMY_CATALOG:
                    boss_names.append(ENEMY_CATALOG[b_id].localized_name)
                else:
                    boss_names.append(b_id.replace('_', ' ').title())

            for bi, bname in enumerate(boss_names[:2]):
                by_pos = card_y + 141 + bi * 8
                self._draw_boss_icon(card_x + 5, by_pos, bname)
                renderer.draw_text(card_x + 13, by_pos, bname, COLOR_WHITE)

            # 7. Choose Route Button
            btn_w = 100
            btn_h = 15
            btn_x = card_x + (card_w - btn_w) // 2
            btn_y = card_y + card_h - 19

            btn_label = "[ CHOOSE ROUTE ]" if i18n.locale == "en" else "[ ELEGIR RUTA ]"

            if is_sel:
                pyxel.tri(btn_x - 6, btn_y + 3, btn_x - 6, btn_y + 11, btn_x - 2, btn_y + 7, COLOR_YELLOW)
                pyxel.rect(btn_x, btn_y, btn_w, btn_h, COLOR_BLACK)
                pyxel.rectb(btn_x, btn_y, btn_w, btn_h, COLOR_YELLOW)
                renderer.draw_text(btn_x + (btn_w - len(btn_label) * 4) // 2, btn_y + 4, btn_label, COLOR_YELLOW)
            else:
                pyxel.rect(btn_x, btn_y, btn_w, btn_h, COLOR_BLACK)
                pyxel.rectb(btn_x, btn_y, btn_w, btn_h, COLOR_LIGHT_BLUE)
                renderer.draw_text(btn_x + (btn_w - len(btn_label) * 4) // 2, btn_y + 4, btn_label, COLOR_WHITE)

        # =====================================================================
        # 4. BOTTOM EXPEDITION FOOTER PROMPT (y=240)
        # =====================================================================
        prompt_txt = "Choose a route to continue your journey." if i18n.locale == "en" else "Elige una ruta para continuar tu viaje."
        tw = len(prompt_txt) * 4
        prompt_x = max(10, (SCREEN_WIDTH - tw) // 2)
        renderer.draw_text(prompt_x, 240, prompt_txt, COLOR_WHITE)

        # Outer Gothic Room Double Border
        pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_DARK_BLUE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_NAVY)

        # Decorative Corner Crosses
        for corner_x, corner_y in [
            (box_x + 1, box_y + 1),
            (box_x + box_w - 2, box_y + 1),
            (box_x + 1, box_y + box_h - 2),
            (box_x + box_w - 2, box_y + box_h - 2),
        ]:
            pyxel.pset(corner_x, corner_y, COLOR_LIGHT_BLUE)
            pyxel.pset(corner_x - 1, corner_y, COLOR_DARK_BLUE)
            pyxel.pset(corner_x + 1, corner_y, COLOR_DARK_BLUE)
            pyxel.pset(corner_x, corner_y - 1, COLOR_DARK_BLUE)
            pyxel.pset(corner_x, corner_y + 1, COLOR_DARK_BLUE)

class MapView(View):
    """Visualizes the Spire node tree with atmospheric dungeon scenery, dotted trails, and custom icons."""

    def _get_node_pos(self, node, total_floors: int) -> tuple[int, int]:
        v_span = 156
        y_pos = 214 - int((node.floor / max(1, total_floors - 1)) * v_span)

        if node.floor == total_floors - 1:
            return SCREEN_WIDTH // 2, y_pos

        lane_w = (SCREEN_WIDTH - 84) // 3
        base_x = 42 + node.lane * lane_w
        offset_x = int(math.sin(node.floor * 1.7 + node.lane * 2.3) * 5)
        return base_x + offset_x, y_pos

    def update(self, game_state: GameState) -> None:
        available = game_state.map_graph.available_nodes
        floors = game_state.map_graph.floors
        total_floors = len(floors)

        for node in available:
            nx, ny = self._get_node_pos(node, total_floors)
            if Renderer.is_clicked(nx - 8, ny - 8, 16, 26):
                pyxel.play(0, 3)
                game_state.select_map_node(node.id)
                return

        for idx, node in enumerate(available):
            key = getattr(pyxel, f"KEY_{idx + 1}", None)
            if key and pyxel.btnp(key):
                pyxel.play(0, 3)
                game_state.select_map_node(node.id)
                break

    def _draw_node_icon(self, nx: int, ny: int, node_type: NodeType) -> None:
        if node_type == NodeType.COMBAT:
            pyxel.line(nx - 3, ny - 3, nx + 3, ny + 3, COLOR_PINK)
            pyxel.line(nx + 3, ny - 3, nx - 3, ny + 3, COLOR_PINK)
            pyxel.pset(nx, ny, COLOR_WHITE)
            pyxel.pset(nx - 3, ny - 2, COLOR_RED)
            pyxel.pset(nx + 3, ny + 2, COLOR_RED)
            pyxel.pset(nx - 3, ny + 2, COLOR_RED)
            pyxel.pset(nx + 3, ny - 2, COLOR_RED)

        elif node_type == NodeType.ELITE:
            pyxel.rect(nx - 2, ny - 1, 5, 4, COLOR_PURPLE)
            pyxel.pset(nx - 2, ny - 3, COLOR_PURPLE)
            pyxel.pset(nx + 2, ny - 3, COLOR_PURPLE)
            pyxel.pset(nx - 1, ny - 2, COLOR_PINK)
            pyxel.pset(nx + 1, ny - 2, COLOR_PINK)
            pyxel.pset(nx - 1, ny, COLOR_WHITE)
            pyxel.pset(nx + 1, ny, COLOR_WHITE)
            pyxel.pset(nx, ny + 2, COLOR_BLACK)

        elif node_type == NodeType.REST:
            pyxel.pset(nx, ny - 3, COLOR_YELLOW)
            pyxel.pset(nx - 1, ny - 2, COLOR_YELLOW)
            pyxel.pset(nx, ny - 2, COLOR_WHITE)
            pyxel.pset(nx + 1, ny - 2, COLOR_YELLOW)
            pyxel.pset(nx - 2, ny - 1, COLOR_ORANGE)
            pyxel.pset(nx - 1, ny - 1, COLOR_YELLOW)
            pyxel.pset(nx, ny - 1, COLOR_WHITE)
            pyxel.pset(nx + 1, ny - 1, COLOR_YELLOW)
            pyxel.pset(nx + 2, ny - 1, COLOR_ORANGE)
            pyxel.rect(nx - 2, ny, 5, 2, COLOR_RED)
            pyxel.pset(nx - 1, ny, COLOR_ORANGE)
            pyxel.pset(nx, ny, COLOR_YELLOW)
            pyxel.pset(nx + 1, ny, COLOR_ORANGE)
            pyxel.line(nx - 2, ny + 2, nx + 2, ny + 2, COLOR_BROWN)

        elif node_type == NodeType.TREASURE:
            pyxel.rect(nx - 3, ny - 2, 7, 5, COLOR_YELLOW)
            pyxel.rectb(nx - 3, ny - 2, 7, 5, COLOR_BROWN)
            pyxel.line(nx - 3, ny, nx + 3, ny, COLOR_BROWN)
            pyxel.pset(nx, ny, COLOR_WHITE)

        elif node_type == NodeType.SHOP:
            pyxel.pset(nx, ny - 3, COLOR_YELLOW)
            pyxel.rect(nx - 2, ny - 2, 5, 5, COLOR_BROWN)
            pyxel.line(nx - 3, ny, nx + 3, ny + 2, COLOR_PEACH)
            pyxel.pset(nx - 1, ny - 1, COLOR_YELLOW)

        elif node_type == NodeType.EVENT:
            pyxel.line(nx - 1, ny - 3, nx + 1, ny - 3, COLOR_CYAN)
            pyxel.pset(nx + 2, ny - 2, COLOR_CYAN)
            pyxel.pset(nx + 1, ny - 1, COLOR_CYAN)
            pyxel.pset(nx, ny, COLOR_CYAN)
            pyxel.pset(nx, ny + 2, COLOR_CYAN)

        elif node_type == NodeType.BOSS:
            pyxel.rect(nx - 4, ny - 1, 9, 4, COLOR_YELLOW)
            pyxel.pset(nx - 4, ny - 3, COLOR_YELLOW)
            pyxel.pset(nx, ny - 4, COLOR_WHITE)
            pyxel.pset(nx + 4, ny - 3, COLOR_YELLOW)
            pyxel.pset(nx - 2, ny, COLOR_RED)
            pyxel.pset(nx + 2, ny, COLOR_RED)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        box_x, box_y, box_w, box_h = 4, 25, SCREEN_WIDTH - 8, SCREEN_HEIGHT - 28

        # Background scenery
        pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

        pyxel.rect(198, 48, 8, 38, COLOR_NAVY)
        pyxel.rect(214, 48, 8, 38, COLOR_NAVY)
        pyxel.rect(198, 44, 24, 6, COLOR_NAVY)
        pyxel.tri(198, 44, 210, 36, 222, 44, COLOR_NAVY)

        moon_x, moon_y = 208, 48
        pyxel.circ(moon_x, moon_y, 8, COLOR_PEACH)
        pyxel.circ(moon_x - 1, moon_y - 1, 7, COLOR_WHITE)
        pyxel.pset(moon_x + 2, moon_y - 2, COLOR_PEACH)
        pyxel.pset(moon_x - 1, moon_y + 3, COLOR_PEACH)

        for ly in range(40, 230, 16):
            w_left = int(math.sin(ly * 0.08) * 10) + 20
            pyxel.rect(box_x + 2, ly, w_left, 12, COLOR_NAVY)
            pyxel.pset(box_x + w_left + 1, ly + 2, COLOR_PURPLE)
            pyxel.pset(box_x + w_left + 3, ly + 5, COLOR_PINK)

        for ry in range(45, 230, 18):
            w_right = int(math.cos(ry * 0.09) * 8) + 18
            rx = box_x + box_w - 2 - w_right
            pyxel.rect(rx, ry, w_right, 14, COLOR_NAVY)
            pyxel.pset(rx - 2, ry + 4, COLOR_PURPLE)
            pyxel.pset(rx - 4, ry + 8, COLOR_PINK)

        fc = pyxel.frame_count
        motes = [(56, 70), (84, 110), (180, 85), (145, 140), (72, 175), (195, 185)]
        for idx, (mx, my) in enumerate(motes):
            if (fc + idx * 7) % 30 < 15:
                pyxel.pset(mx, my, COLOR_CYAN if idx % 2 == 0 else COLOR_YELLOW)

        pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_DARK_BLUE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_NAVY)

        for cx, cy in [
            (box_x + 1, box_y + 1),
            (box_x + box_w - 2, box_y + 1),
            (box_x + 1, box_y + box_h - 2),
            (box_x + box_w - 2, box_y + box_h - 2),
        ]:
            pyxel.pset(cx, cy, COLOR_LIGHT_BLUE)
            pyxel.pset(cx - 1, cy, COLOR_DARK_BLUE)
            pyxel.pset(cx + 1, cy, COLOR_DARK_BLUE)
            pyxel.pset(cx, cy - 1, COLOR_DARK_BLUE)
            pyxel.pset(cx, cy + 1, COLOR_DARK_BLUE)

        from src.data.biomes import get_biome
        biome = get_biome(game_state.current_biome)

        icon_box_x, icon_box_y = 10, 29
        pyxel.rect(icon_box_x, icon_box_y, 16, 16, COLOR_NAVY)
        pyxel.rectb(icon_box_x, icon_box_y, 16, 16, COLOR_LIGHT_BLUE)

        tx, ty = icon_box_x + 8, icon_box_y + 13
        pyxel.line(tx, ty, tx, ty - 5, COLOR_LIGHT_BLUE)
        pyxel.line(tx - 1, ty - 2, tx - 3, ty - 6, COLOR_LIGHT_BLUE)
        pyxel.line(tx + 1, ty - 2, tx + 3, ty - 6, COLOR_LIGHT_BLUE)
        pyxel.line(tx - 2, ty - 5, tx - 4, ty - 9, COLOR_CYAN)
        pyxel.line(tx, ty - 5, tx, ty - 9, COLOR_CYAN)
        pyxel.line(tx + 2, ty - 5, tx + 4, ty - 9, COLOR_CYAN)

        act_title = f"Act {game_state.act}: {biome.localized_name if biome else 'Aethelgard'}"
        renderer.draw_text(30, 31, act_title, COLOR_YELLOW)
        subtitle = "Elige un camino [1-4]" if i18n.locale == "es" else "Select a path [1-4]"
        renderer.draw_text(30, 40, subtitle, COLOR_WHITE)

        floors = game_state.map_graph.floors
        available_ids = {n.id for n in game_state.map_graph.available_nodes}
        current_id = game_state.map_graph.current_node_id
        total_floors = len(floors)

        for floor in floors:
            for node in floor:
                x1, y1 = self._get_node_pos(node, total_floors)
                for out_id in node.outgoing_ids:
                    out_node = game_state.map_graph.nodes_by_id.get(out_id)
                    if out_node:
                        x2, y2 = self._get_node_pos(out_node, total_floors)
                        is_active_path = (node.id == current_id and out_node.id in available_ids) or \
                                         (current_id is None and node.floor == 0 and out_node.id in available_ids)

                        dot_col = COLOR_YELLOW if is_active_path else COLOR_DARK_BLUE

                        dx = x2 - x1
                        dy = y2 - y1
                        dist = math.hypot(dx, dy)
                        if dist > 0:
                            step = 4.0
                            num_dots = int(dist / step)
                            for s in range(2, num_dots - 1):
                                px = int(x1 + (dx / dist) * (s * step))
                                py = int(y1 + (dy / dist) * (s * step))
                                pyxel.pset(px, py, dot_col)

        option_index = 1
        pulse = (pyxel.frame_count // 6) % 2

        for floor in floors:
            for node in floor:
                nx, ny = self._get_node_pos(node, total_floors)
                is_curr = node.id == current_id
                is_avail = node.id in available_ids

                bg_col = COLOR_NAVY if is_avail else COLOR_BLACK
                border_col = COLOR_YELLOW if is_avail else (COLOR_LIME if is_curr else COLOR_DARK_BLUE)

                pyxel.circ(nx, ny, 6, bg_col)
                pyxel.circb(nx, ny, 6, border_col)

                if is_avail:
                    pyxel.circb(nx, ny, 7, COLOR_YELLOW)
                    if pulse == 1:
                        pyxel.circb(nx, ny, 8, COLOR_ORANGE)

                self._draw_node_icon(nx, ny, node.node_type)

                if is_curr:
                    pyxel.circb(nx, ny, 7, COLOR_LIME)

                if is_avail:
                    badge_x = nx - 6
                    badge_y = ny + 8
                    pyxel.rect(badge_x, badge_y, 13, 9, COLOR_NAVY)
                    pyxel.rectb(badge_x, badge_y, 13, 9, COLOR_YELLOW)
                    num_str = str(option_index)
                    tw = renderer.get_text_width(num_str)
                    renderer.draw_text(badge_x + (13 - tw) // 2 + 1, badge_y + 1, num_str, COLOR_WHITE)
                    option_index += 1

        div_y = box_y + box_h - 16
        pyxel.line(box_x + 2, div_y, box_x + box_w - 3, div_y, COLOR_NAVY)

        is_es = (i18n.locale == "es")
        legend_items = [
            (NodeType.COMBAT, "Lucha" if is_es else "Combat"),
            (NodeType.EVENT, "Evento" if is_es else "Event"),
            (NodeType.TREASURE, "Tesoro" if is_es else "Chest"),
            (NodeType.REST, "Acampar" if is_es else "Rest"),
            (NodeType.ELITE, "Elite" if is_es else "Elite"),
            (NodeType.SHOP, "Tienda" if is_es else "Shop"),
        ]

        leg_x = box_x + 6
        spacing = (box_w - 12) // len(legend_items)
        leg_y = div_y + 7

        for n_type, label in legend_items:
            self._draw_node_icon(leg_x + 4, leg_y, n_type)
            renderer.draw_text(leg_x + 11, leg_y - 3, label, COLOR_WHITE)
            leg_x += spacing


class CombatView(View):
    """Renders retro dungeon combat arena, detailed stat cards, split command panel, and battle log."""

    def __init__(self) -> None:
        self.popups: list[CombatPopup] = []
        self.player_flash: int = 0
        self.enemy_flash: int = 0
        self.shake_frames: int = 0
        self.speed_index: int = 0

    def _detect_combat_deltas(self, game_state: GameState, old_p_hp: int, old_e_hp: int) -> None:
        if game_state.combat is None:
            return

        combat = game_state.combat
        new_p_hp = game_state.player.current_hp
        new_e_hp = combat.enemy.current_hp

        # Player damage / heal
        if new_p_hp < old_p_hp:
            dmg = old_p_hp - new_p_hp
            is_crit = any("CRIT" in log or "CRÍTICO" in log for log in combat.combat_logs[-2:])
            txt = f"-{dmg}!" if is_crit else f"-{dmg}"
            col = COLOR_RED if is_crit else COLOR_PEACH
            self.popups.append(CombatPopup(x=62, y=44, text=txt, color=col))
            self.player_flash = 3
            if is_crit:
                self.shake_frames = 5
        elif new_p_hp > old_p_hp:
            heal = new_p_hp - old_p_hp
            self.popups.append(CombatPopup(x=62, y=44, text=f"+{heal}", color=COLOR_LIME))

        # Enemy damage / heal
        if new_e_hp < old_e_hp:
            dmg = old_e_hp - new_e_hp
            is_crit = any("CRIT" in log or "CRÍTICO" in log for log in combat.combat_logs[-2:])
            txt = f"-{dmg}!" if is_crit else f"-{dmg}"
            col = COLOR_YELLOW if is_crit else COLOR_WHITE
            self.popups.append(CombatPopup(x=184, y=44, text=txt, color=col))
            self.enemy_flash = 3
            if is_crit:
                self.shake_frames = 6

    def update(self, game_state: GameState) -> None:
        if game_state.combat is None:
            self.popups.clear()
            return

        for p in self.popups:
            if p.lifetime % 2 == 0:
                p.y -= 1
            p.lifetime -= 1
        self.popups = [p for p in self.popups if p.lifetime > 0]

        # Speed toggle [Z] or click at bottom-right corner of dungeon arena (222, 79, 28, 11)
        if pyxel.btnp(pyxel.KEY_Z) or Renderer.is_clicked(222, 79, 28, 11):
            self.speed_index = (self.speed_index + 1) % len(SPEED_INTERVALS)
            pyxel.play(0, 3)
            return

        speed_frames = SPEED_INTERVALS[self.speed_index]

        # Advance combat (auto-tick, space, or tap on arena/log)
        if pyxel.btnp(pyxel.KEY_SPACE) or (pyxel.frame_count % speed_frames == 0) or Renderer.is_clicked(0, 24, SCREEN_WIDTH, 68) or Renderer.is_clicked(0, 202, SCREEN_WIDTH, 54):
            old_p_hp = game_state.player.current_hp
            old_e_hp = game_state.combat.enemy.current_hp
            game_state.update_combat()
            self._detect_combat_deltas(game_state, old_p_hp, old_e_hp)

        if game_state.combat is None:
            return

        # Belt hotkeys: [1, 2, 3] or click on command panel
        belt_y_positions = [162, 174, 186]
        for idx, key in enumerate((pyxel.KEY_1, pyxel.KEY_2, pyxel.KEY_3)):
            by = belt_y_positions[idx]
            if pyxel.btnp(key) or Renderer.is_clicked(6, by, 114, 11):
                old_p_hp = game_state.player.current_hp
                if game_state.player.inventory.use_belt_item(idx, game_state.player):
                    pyxel.play(1, 2)
                    game_state.combat.combat_logs.append(
                        t("combat_belt_use", player=game_state.player.name, slot=idx + 1)
                    )
                    self._detect_combat_deltas(game_state, old_p_hp, game_state.combat.enemy.current_hp)

        # Ability hotkeys: [4, 5] or click on right action panel
        for idx, key in enumerate((pyxel.KEY_4, pyxel.KEY_5)):
            ay = 164 + idx * 16
            if (pyxel.btnp(key) or Renderer.is_clicked(130, ay, 118, 14)) and idx < len(
                    game_state.player.abilities.active):
                if game_state.combat.ability_cooldown <= 0:
                    game_state.combat.queued_ability = game_state.player.abilities.active[idx]
                    game_state.combat.ability_cooldown = 3
                    game_state.combat.combat_logs.append(
                        t("combat_queued", ability=game_state.player.abilities.active[idx].name)
                    )
                else:
                    game_state.combat.combat_logs.append(
                        t("combat_cooldown", cooldown=game_state.combat.ability_cooldown)
                    )

    def _get_enemy_sprite(self, enemy: Enemy) -> tuple[int, int]:
        arch_id = getattr(enemy, "archetype_id", None)
        if arch_id and arch_id in ENEMY_SPRITE_COORDS:
            return ENEMY_SPRITE_COORDS[arch_id]

        name_lower = enemy.name.lower()
        for key, coords in ENEMY_SPRITE_COORDS.items():
            if key.replace("_", " ") in name_lower:
                return coords

        tier_val = enemy.tier.value if hasattr(enemy.tier, "value") else int(enemy.tier)
        if tier_val >= 4 or "lich" in name_lower or "dragon" in name_lower:
            return (48, 0)
        if "goblin" in name_lower or "scavenger" in name_lower or "cultist" in name_lower:
            return (32, 0)
        return (16, 0)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        # Camera screen shake
        if self.shake_frames > 0:
            sx = random.randint(-2, 2)
            sy = random.randint(-2, 2)
            pyxel.camera(sx, sy)
            self.shake_frames -= 1
        else:
            pyxel.camera(0, 0)

        renderer.draw_hud(game_state.player, game_state.floor)

        if game_state.combat is None:
            pyxel.camera(0, 0)
            return

        combat = game_state.combat
        fc = pyxel.frame_count

        # =====================================================================
        # 1. RETRO DUNGEON STAGE ARENA (y=24 to y=92)
        # =====================================================================
        arena_x, arena_y, arena_w, arena_h = 4, 24, SCREEN_WIDTH - 8, 68
        pyxel.rect(arena_x, arena_y, arena_w, arena_h, COLOR_BLACK)

        # Stone wall masonry & vaulted arch columns
        for col_x in [12, 44, 94, 150, 200, 232]:
            pyxel.rect(col_x, arena_y, 8, arena_h - 14, COLOR_NAVY)
            for by in range(arena_y + 4, arena_y + arena_h - 14, 8):
                pyxel.line(col_x, by, col_x + 7, by, COLOR_DARK_BLUE)
                pyxel.pset(col_x + ((by // 4) % 6), by + 3, COLOR_LIGHT_BLUE)

        # Central arched entryway
        pyxel.rect(114, arena_y + 12, 28, arena_h - 26, COLOR_DARK_BLUE)
        pyxel.tri(114, arena_y + 12, 128, arena_y + 2, 141, arena_y + 12, COLOR_DARK_BLUE)
        pyxel.rect(118, arena_y + 16, 20, arena_h - 30, COLOR_BLACK)
        pyxel.tri(118, arena_y + 16, 128, arena_y + 8, 137, arena_y + 16, COLOR_BLACK)

        # Left Torch Sconce & Flame
        ltx, lty = 22, 38
        pyxel.rect(ltx - 1, lty + 6, 4, 3, COLOR_BROWN)
        pyxel.pset(ltx, lty + 9, COLOR_DARK_BLUE)
        pyxel.rect(ltx - 1, lty + 2, 4, 4, COLOR_ORANGE)
        pyxel.pset(ltx, lty + (1 if fc % 4 < 2 else 0), COLOR_YELLOW)
        pyxel.pset(ltx + 1, lty + 2, COLOR_WHITE)
        if fc % 3 == 0:
            pyxel.pset(ltx + (fc % 3) - 1, lty - 2, COLOR_YELLOW)

        # Right Torch Sconce & Flame
        rtx, rty = 230, 38
        pyxel.rect(rtx - 1, rty + 6, 4, 3, COLOR_BROWN)
        pyxel.pset(rtx, rty + 9, COLOR_DARK_BLUE)
        pyxel.rect(rtx - 1, rty + 2, 4, 4, COLOR_ORANGE)
        pyxel.pset(rtx, rty + (0 if fc % 4 < 2 else 1), COLOR_YELLOW)
        pyxel.pset(rtx - 1, rty + 2, COLOR_WHITE)
        if fc % 3 == 1:
            pyxel.pset(rtx - (fc % 3) + 1, rty - 2, COLOR_YELLOW)

        # Cobblestone ground
        ground_y = arena_y + arena_h - 14
        pyxel.rect(arena_x, ground_y, arena_w, 14, COLOR_DARK_BLUE)
        for gx in range(arena_x + 2, arena_x + arena_w - 4, 12):
            pyxel.line(gx, ground_y + 3, gx + 6, ground_y + 3, COLOR_NAVY)
            pyxel.line(gx + 6, ground_y + 8, gx + 11, ground_y + 8, COLOR_NAVY)

        # Status Badges Behind Player (Left of Hero: x=14..48)
        if game_state.player.statuses:
            status_y = 52
            for s in game_state.player.statuses[:3]:
                tag = f"{s.badge} {s.duration}"
                tw = renderer.get_text_width(tag)
                pill_w = tw + 6
                pill_x = 14
                pyxel.rect(pill_x, status_y - 1, pill_w, 9, COLOR_BLACK)
                pyxel.rectb(pill_x, status_y - 1, pill_w, 9, s.color)
                renderer.draw_text(pill_x + 3, status_y, tag, s.color)
                status_y += 11

        # Status Badges Behind Enemy (Right of Enemy: x=204..238)
        if combat.enemy.statuses:
            status_y = 52
            for s in combat.enemy.statuses[:3]:
                tag = f"{s.badge} {s.duration}"
                tw = renderer.get_text_width(tag)
                pill_w = tw + 6
                pill_x = arena_x + arena_w - pill_w - 6
                pyxel.rect(pill_x, status_y - 1, pill_w, 9, COLOR_BLACK)
                pyxel.rectb(pill_x, status_y - 1, pill_w, 9, s.color)
                renderer.draw_text(pill_x + 3, status_y, tag, s.color)
                status_y += 11

        # Combatant Ground Shadows
        pyxel.elli(56, 75, 20, 5, COLOR_NAVY)
        pyxel.elli(176, 75, 22, 5, COLOR_NAVY)

        # Animated Hero Character on Left
        sprite_map = {
            "warrior": (0, 0),
            "rogue": (0, 32),
            "mage": (16, 32),
        }
        pu, pv = sprite_map.get(game_state.player.class_id, (0, 0))
        hero_x, hero_y = 58, 62

        if self.player_flash > 0:
            self.player_flash -= 1
            for c in range(16):
                pyxel.pal(c, COLOR_WHITE)
            pyxel.blt(hero_x, hero_y, 0, pu, pv, 16, 16, 0)
            pyxel.pal()
        else:
            pyxel.blt(hero_x, hero_y, 0, pu, pv, 16, 16, 0)

        # Drawn hero blade
        pyxel.line(hero_x + 14, hero_y + 6, hero_x + 21, hero_y - 1, COLOR_CYAN)
        pyxel.line(hero_x + 15, hero_y + 6, hero_x + 22, hero_y - 1, COLOR_WHITE)

        # Animated Enemy Sprite on Right
        eu, ev = self._get_enemy_sprite(combat.enemy)
        enemy_x, enemy_y = 178, 62

        if self.enemy_flash > 0:
            self.enemy_flash -= 1
            for c in range(16):
                pyxel.pal(c, COLOR_WHITE)
            pyxel.blt(enemy_x, enemy_y, 0, eu, ev, 16, 16, 0)
            pyxel.pal()
        else:
            pyxel.blt(enemy_x, enemy_y, 0, eu, ev, 16, 16, 0)

        # Ambient floating magic/spore motes around enemy
        spore_coords = [(172, 56), (180, 50), (192, 52), (198, 58), (175, 66), (196, 68)]
        for s_idx, (sx, sy) in enumerate(spore_coords):
            sy_float = sy + int(math.sin((fc + s_idx * 5) * 0.2) * 2)
            if (fc + s_idx * 4) % 20 < 12:
                pyxel.pset(sx, sy_float, COLOR_CYAN if s_idx % 2 == 0 else COLOR_LIME)

        # Floating combat damage popups
        for pop in self.popups:
            renderer.draw_text(pop.x, pop.y, pop.text, pop.color)

        # Speed Button in the bottom-right corner of the dungeon arena
        renderer.draw_button(222, 79, 28, 11, f"[{SPEED_LABELS[self.speed_index]}]", bg_col=COLOR_BLACK, border_col=COLOR_YELLOW, text_col=COLOR_YELLOW)

        # Arena Outer Border
        pyxel.rectb(arena_x, arena_y, arena_w, arena_h, COLOR_DARK_BLUE)

        # =====================================================================
        # 2. STAT & PORTRAIT CARDS (y=94 to y=140)
        # =====================================================================
        card_w, card_h = 122, 46

        # --- PLAYER CARD (Left) ---
        pc_x, pc_y = 4, 94
        renderer.draw_box(pc_x, pc_y, card_w, card_h, bg_col=COLOR_DARK_BLUE, border_col=COLOR_LIGHT_BLUE)

        # Portrait Frame & Hero Sprite
        pyxel.rect(pc_x + 3, pc_y + 3, 20, 20, COLOR_NAVY)
        pyxel.rectb(pc_x + 3, pc_y + 3, 20, 20, COLOR_LIGHT_BLUE)
        pyxel.blt(pc_x + 5, pc_y + 5, 0, pu, pv, 16, 16, 0)

        # Player Name & HP Bar
        p_name = game_state.player.name[:14]
        renderer.draw_text(pc_x + 27, pc_y + 4, p_name, COLOR_YELLOW)
        renderer.draw_bar(pc_x + 27, pc_y + 13, 90, 5, game_state.player.current_hp, game_state.player.max_hp, fill_col=COLOR_GREEN, bg_col=COLOR_RED)

        # Numeric Stats
        p_stats = game_state.player.effective_stats
        renderer.draw_text(pc_x + 27, pc_y + 20, f"HP:  {game_state.player.current_hp}/{game_state.player.max_hp}", COLOR_WHITE)
        renderer.draw_text(pc_x + 27, pc_y + 28, f"ATK: {p_stats.attack:<3} DEF: {p_stats.defense}", COLOR_WHITE)
        crit_pct = int(p_stats.crit_chance * 100)
        renderer.draw_text(pc_x + 27, pc_y + 36, f"SPD: {p_stats.speed:<3} CRIT: {crit_pct}%", COLOR_WHITE)

        # --- ENEMY CARD (Right) ---
        ec_x, ec_y = 130, 94
        border_col = COLOR_RED if combat.enemy.tier.value >= 3 else COLOR_LIGHT_BLUE
        renderer.draw_box(ec_x, ec_y, card_w, card_h, bg_col=COLOR_DARK_BLUE, border_col=border_col)

        # Portrait Frame & Enemy Sprite
        pyxel.rect(ec_x + 3, ec_y + 3, 20, 20, COLOR_NAVY)
        pyxel.rectb(ec_x + 3, ec_y + 3, 20, 20, border_col)
        pyxel.blt(ec_x + 5, ec_y + 5, 0, eu, ev, 16, 16, 0)

        # Enemy Name & HP Bar
        e_name = combat.enemy.display_name if len(combat.enemy.display_name) <= 14 else combat.enemy.display_name[:13] + "."
        renderer.draw_text(ec_x + 27, ec_y + 4, e_name, COLOR_YELLOW)
        renderer.draw_bar(ec_x + 27, ec_y + 13, 90, 5, combat.enemy.current_hp, combat.enemy.max_hp, fill_col=COLOR_GREEN, bg_col=COLOR_RED)

        # Numeric Stats
        e_stats = combat.enemy.effective_stats
        renderer.draw_text(ec_x + 27, ec_y + 20, f"HP:  {combat.enemy.current_hp}/{combat.enemy.max_hp}", COLOR_WHITE)
        renderer.draw_text(ec_x + 27, ec_y + 28, f"ATK: {e_stats.attack:<3} DEF: {e_stats.defense}", COLOR_WHITE)
        e_crit = int(e_stats.crit_chance * 100)
        renderer.draw_text(ec_x + 27, ec_y + 36, f"SPD: {e_stats.speed:<3} CRIT: {e_crit}%", COLOR_WHITE)

        # =====================================================================
        # 3. ACTION TICK GAUGES (y=142 to y=156)
        # =====================================================================
        renderer.draw_text(4, 142, t("tick_gauges"), COLOR_YELLOW)

        # Player meter aligned with player card (x=4, w=122); Enemy meter aligned with enemy card (x=130, w=122)
        renderer.draw_bar(4, 150, 122, 5, combat.player_gauge, ACTION_THRESHOLD, fill_col=COLOR_LIGHT_BLUE, bg_col=COLOR_NAVY)
        renderer.draw_bar(130, 150, 122, 5, combat.enemy_gauge, ACTION_THRESHOLD, fill_col=COLOR_ORANGE, bg_col=COLOR_NAVY)

        # =====================================================================
        # 4. SPLIT ACTION COMMAND PANEL (y=158 to y=198)
        # =====================================================================
        cmd_x, cmd_y, cmd_w, cmd_h = 4, 158, SCREEN_WIDTH - 8, 42
        renderer.draw_box(cmd_x, cmd_y, cmd_w, cmd_h, bg_col=COLOR_NAVY, border_col=COLOR_LIGHT_BLUE)

        # Vertical Column Divider
        div_x = cmd_x + 120
        pyxel.line(div_x, cmd_y + 2, div_x, cmd_y + cmd_h - 3, COLOR_LIGHT_BLUE)

        # --- LEFT COLUMN: Belt Quick-Items ---
        inv = game_state.player.inventory
        for b_idx in range(MAX_BELT_SLOTS):
            b_item = inv.belt[b_idx]
            sy = cmd_y + 4 + b_idx * 12

            if b_idx == 0:
                pyxel.tri(cmd_x + 3, sy + 3, cmd_x + 3, sy + 7, cmd_x + 6, sy + 5, COLOR_YELLOW)

            if b_item:
                pyxel.rectb(cmd_x + 8, sy - 1, 108, 10, COLOR_LIGHT_BLUE if b_idx == 0 else COLOR_NAVY)
                renderer.draw_text(cmd_x + 11, sy, f"{b_idx+1}. {b_item.localized_name[:10]}", COLOR_WHITE)
                renderer.draw_text(cmd_x + 78, sy, f"[+{b_item.heal_amount} HP]", COLOR_LIME)
            else:
                renderer.draw_text(cmd_x + 11, sy, f"{b_idx+1}. {t('empty_slot_short')}", COLOR_GRAY)

        # --- RIGHT COLUMN: Active Skills ---
        skills = game_state.player.abilities.active
        for a_idx in range(2):
            sy = cmd_y + 7 + a_idx * 16
            if a_idx < len(skills):
                ab = skills[a_idx]
                is_queued = (combat.queued_ability == ab)

                if a_idx == 0:
                    pyxel.line(div_x + 4, sy + 1, div_x + 8, sy + 5, COLOR_WHITE)
                    pyxel.line(div_x + 8, sy + 1, div_x + 4, sy + 5, COLOR_WHITE)
                else:
                    pyxel.rect(div_x + 4, sy + 1, 5, 4, COLOR_WHITE)
                    pyxel.pset(div_x + 5, sy + 2, COLOR_BLACK)
                    pyxel.pset(div_x + 7, sy + 2, COLOR_BLACK)

                ab_name = f"{a_idx+4}. {ab.localized_name[:12]}"
                renderer.draw_text(div_x + 12, sy, ab_name, COLOR_YELLOW if is_queued else COLOR_WHITE)

                tag = "WAIT" if is_queued else "CAST"
                tag_col = COLOR_YELLOW if is_queued else COLOR_LIGHT_BLUE
                renderer.draw_text(cmd_x + cmd_w - 28, sy, tag, tag_col)
            else:
                renderer.draw_text(div_x + 12, sy, f"{a_idx+4}. (Empty)", COLOR_GRAY)

        # =====================================================================
        # 5. GOTHIC COMBAT ACTIVITY LOG (y=202 to y=254)
        # =====================================================================
        log_x, log_y, log_w, log_h = 4, 202, SCREEN_WIDTH - 8, 52
        renderer.draw_box(log_x, log_y, log_w, log_h, bg_col=COLOR_BLACK, border_col=COLOR_DARK_BLUE)
        pyxel.rectb(log_x + 1, log_y + 1, log_w - 2, log_h - 2, COLOR_NAVY)

        for cx, cy in [
            (log_x + 2, log_y + 2),
            (log_x + log_w - 3, log_y + 2),
            (log_x + 2, log_y + log_h - 3),
            (log_x + log_w - 3, log_y + log_h - 3),
        ]:
            pyxel.pset(cx, cy, COLOR_LIGHT_BLUE)

        renderer.draw_text(log_x + 8, log_y + 3, t("combat_log_header"), COLOR_YELLOW)

        recent_logs = combat.combat_logs if combat.combat_logs else [t("combat_awaiting")]
        wrapped_logs = []
        for line in recent_logs:
            wrapped_logs.extend(renderer.wrap_text(line, max_chars_per_line=39))

        display_entries = wrapped_logs[-4:] if wrapped_logs else []
        line_y = log_y + 13
        for disp in display_entries:
            if "CRIT" in disp or "CRÍTICO" in disp:
                renderer.draw_text(log_x + 8, line_y, disp, COLOR_YELLOW)
            elif "dmg" in disp or "daño" in disp:
                renderer.draw_text(log_x + 8, line_y, disp, COLOR_WHITE)
            elif "defeated" in disp or "derrotado" in disp:
                renderer.draw_text(log_x + 8, line_y, disp, COLOR_LIME)
            else:
                renderer.draw_text(log_x + 8, line_y, disp, COLOR_GRAY)
            line_y += 9

        if len(wrapped_logs) > 4:
            ind_x, ind_y = log_x + log_w - 8, log_y + log_h - 7
            pyxel.tri(ind_x - 2, ind_y, ind_x + 2, ind_y, ind_x, ind_y + 3, COLOR_YELLOW)

        pyxel.camera(0, 0)

class InventoryView(View):
    """Renders retro mannequin equipment layout, item inspector panel, 3-slot belt, and 10-slot pouch."""

    def __init__(self) -> None:
        self.active_pane: str = "POUCH"  # "POUCH", "EQUIPMENT", or "BELT"
        self.pouch_cursor: int = 0
        self.equip_cursor: int = 0
        self.belt_cursor: int = 0
        self.feedback_message: str = ""
        self.feedback_success: bool = False

    def _get_item_icon(self, item) -> tuple[int, int]:
        """Resolve 8x8 Bank 0 tile coordinates for any inventory item."""
        iid = item.id.lower()
        if "potion" in iid:
            return (64, 0)
        elif "flask" in iid:
            return (64, 8)
        elif "elixir" in iid:
            return (72, 8)
        elif any(k in iid for k in ("sword", "broadsword", "claymore", "cleaver", "worldbreaker")):
            return (72, 0)
        elif any(k in iid for k in ("shield", "buckler", "bastion")):
            return (80, 0)
        elif any(k in iid for k in ("helmet", "cowl", "sallet", "cap", "coif", "visage", "diadem")):
            return (80, 8)
        elif any(k in iid for k in ("chestplate", "vest", "tunic", "robe", "cuirass", "harness", "carapace")):
            return (88, 8)
        elif any(k in iid for k in ("gloves", "mitts", "handwraps")):
            return (96, 8)
        elif any(k in iid for k in ("pants", "breeches", "greaves", "boots", "treads", "sabatons")):
            return (104, 8)
        elif any(k in iid for k in ("mantle", "capelet", "cloak")):
            return (0, 16)
        elif any(k in iid for k in ("pauldrons", "epaulets")):
            return (8, 16)
        elif any(k in iid for k in ("belt", "girdle", "sash")):
            return (16, 16)
        elif any(k in iid for k in ("dagger", "dirk", "stiletto", "sai", "fang")):
            return (32, 16)
        elif any(k in iid for k in ("wand",)):
            return (40, 16)
        elif any(k in iid for k in ("grimoire", "skull", "scroll")):
            return (48, 16)
        elif any(k in iid for k in ("staff", "spire")):
            return (56, 16)
        return (96, 0)

    def _get_slot_default_icon(self, slot: EquipSlot) -> tuple[int, int]:
        """Default faint icon for an empty equipment slot."""
        if slot == EquipSlot.HEAD:
            return (80, 8)
        elif slot == EquipSlot.SHOULDERS:
            return (8, 16)
        elif slot == EquipSlot.CHEST:
            return (88, 8)
        elif slot == EquipSlot.WAIST:
            return (16, 16)
        elif slot == EquipSlot.HANDS:
            return (96, 8)
        elif slot == EquipSlot.LEGS:
            return (104, 8)
        elif slot == EquipSlot.MAIN_HAND:
            return (72, 0)
        elif slot == EquipSlot.OFF_HAND:
            return (80, 0)
        return (80, 0)

    def _get_selected_item(self, game_state: GameState):
        """Retrieve currently inspected item and its context category."""
        inv = game_state.player.inventory
        equip_order = [
            EquipSlot.HEAD, EquipSlot.SHOULDERS, EquipSlot.CHEST, EquipSlot.HANDS,
            EquipSlot.MAIN_HAND, EquipSlot.OFF_HAND, EquipSlot.WAIST, EquipSlot.LEGS
        ]
        if self.active_pane == "EQUIPMENT":
            slot = equip_order[self.equip_cursor]
            return inv.equipment.get(slot), t(f"slot_{slot.name.lower()}")
        elif self.active_pane == "BELT":
            item = inv.belt[self.belt_cursor]
            return item, "Belt Slot" if i18n.locale == "en" else "Ranura Cinto"
        else:  # "POUCH"
            if self.pouch_cursor < len(inv.pouch):
                item = inv.pouch[self.pouch_cursor]
                return item, "Pouch Item" if i18n.locale == "en" else "Objeto Bolsa"
            return None, "Empty Pouch Slot" if i18n.locale == "en" else "Ranura Vacía"

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.KEY_I) or Renderer.is_clicked(210, 230, 42, 18):
            game_state.toggle_inventory()
            return

        inv = game_state.player.inventory
        from src.systems.inventory import ConsumableItem, EquipmentItem, EquipSlot

        equip_order = [
            EquipSlot.HEAD, EquipSlot.SHOULDERS, EquipSlot.CHEST, EquipSlot.HANDS,
            EquipSlot.MAIN_HAND, EquipSlot.OFF_HAND, EquipSlot.WAIST, EquipSlot.LEGS
        ]

        # 1. Direct Touch/Click Detection
        # Equipment Slots (matched to draw: eq_x=4, eq_y=26, sy=43 + col_idx * 24)
        for i, slot in enumerate(equip_order):
            is_right = (i >= 4)
            col_idx = i - 4 if is_right else i
            sx = 82 if is_right else 10
            sy = 43 + col_idx * 24
            if Renderer.is_clicked(sx - 1, sy - 1, 52, 18):
                self.active_pane = "EQUIPMENT"
                self.equip_cursor = i
                self.feedback_message = ""
                pyxel.play(0, 3)
                return

        # Belt Slots (matched to draw: belt_x=4, belt_y=143 -> bx = 10 + b_idx * 33, by = 159, bw = 30, bh = 60)
        for b_idx in range(MAX_BELT_SLOTS):
            bx = 10 + b_idx * 33
            by = 159
            if Renderer.is_clicked(bx, by, 30, 60):
                self.active_pane = "BELT"
                self.belt_cursor = b_idx
                self.feedback_message = ""
                pyxel.play(0, 3)
                return

        # Pouch Slots (matched to draw: po_x=116, po_y=143 -> slot_x = 124 + col * 24, slot_y = 161 + row * 26)
        for p_idx in range(MAX_POUCH_SLOTS):
            col = p_idx % 5
            row = p_idx // 5
            slot_x = 124 + col * 24
            slot_y = 161 + row * 26
            if Renderer.is_clicked(slot_x, slot_y, 20, 20):
                self.active_pane = "POUCH"
                self.pouch_cursor = p_idx
                self.feedback_message = ""
                pyxel.play(0, 3)
                return

        # 2. Cycle Active Panes with [TAB]
        if pyxel.btnp(pyxel.KEY_TAB):
            order = ["POUCH", "EQUIPMENT", "BELT"]
            curr_idx = order.index(self.active_pane) if self.active_pane in order else 0
            self.active_pane = order[(curr_idx + 1) % len(order)]
            self.feedback_message = ""
            pyxel.play(0, 3)

        # 3. Directional Keyboard Navigation
        up = pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W)
        down = pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btnp(pyxel.KEY_S)
        left = pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A)
        right = pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D)

        if self.active_pane == "POUCH":
            if left:
                self.pouch_cursor = (self.pouch_cursor - 1) % MAX_POUCH_SLOTS
            elif right:
                self.pouch_cursor = (self.pouch_cursor + 1) % MAX_POUCH_SLOTS
            elif up:
                self.pouch_cursor = (self.pouch_cursor - 5) % MAX_POUCH_SLOTS
            elif down:
                self.pouch_cursor = (self.pouch_cursor + 5) % MAX_POUCH_SLOTS

        elif self.active_pane == "EQUIPMENT":
            if up:
                col_offset = 4 if self.equip_cursor >= 4 else 0
                row = (self.equip_cursor - col_offset - 1) % 4
                self.equip_cursor = col_offset + row
            elif down:
                col_offset = 4 if self.equip_cursor >= 4 else 0
                row = (self.equip_cursor - col_offset + 1) % 4
                self.equip_cursor = col_offset + row
            elif left or right:
                self.equip_cursor = (self.equip_cursor + 4) % 8

        elif self.active_pane == "BELT":
            if left:
                self.belt_cursor = (self.belt_cursor - 1) % MAX_BELT_SLOTS
            elif right:
                self.belt_cursor = (self.belt_cursor + 1) % MAX_BELT_SLOTS

        # 4. Action Handlers (Equip / Use / Unequip / Drop)
        equip_action = pyxel.btnp(pyxel.KEY_E) or Renderer.is_clicked(4, 230, 90, 18)
        drop_action = pyxel.btnp(pyxel.KEY_D) or Renderer.is_clicked(162, 230, 44, 18)

        if equip_action:
            if self.active_pane == "POUCH":
                if self.pouch_cursor < len(inv.pouch):
                    item = inv.pouch[self.pouch_cursor]
                    if isinstance(item, EquipmentItem):
                        success, msg = inv.equip_from_pouch(self.pouch_cursor, game_state.player)
                        self.feedback_message = msg
                        self.feedback_success = success
                        if success:
                            pyxel.play(0, 3)
                    elif isinstance(item, ConsumableItem):
                        target_belt = -1
                        for b in range(MAX_BELT_SLOTS):
                            if inv.belt[b] is None:
                                target_belt = b
                                break
                        if target_belt == -1:
                            target_belt = 0
                        success, msg = inv.assign_pouch_to_belt(self.pouch_cursor, target_belt)
                        self.feedback_message = msg
                        self.feedback_success = success
                        if success:
                            pyxel.play(0, 3)
            elif self.active_pane == "EQUIPMENT":
                slot = equip_order[self.equip_cursor]
                if inv.equipment[slot] is not None:
                    success, msg = inv.unequip_to_pouch(slot)
                    self.feedback_message = msg
                    self.feedback_success = success
                    if success:
                        pyxel.play(0, 3)
            elif self.active_pane == "BELT":
                if inv.use_belt_item(self.belt_cursor, game_state.player):
                    pyxel.play(1, 2)
                    self.feedback_message = "Item used!" if i18n.locale == "en" else "¡Objeto usado!"
                    self.feedback_success = True

        if drop_action:
            if self.active_pane == "POUCH":
                if self.pouch_cursor < len(inv.pouch):
                    success, msg = inv.drop_from_pouch(self.pouch_cursor)
                    self.feedback_message = msg
                    self.feedback_success = success
                    if success:
                        pyxel.play(0, 3)
            elif self.active_pane == "BELT":
                if inv.belt[self.belt_cursor] is not None:
                    dropped_name = inv.belt[self.belt_cursor].localized_name
                    inv.belt[self.belt_cursor] = None
                    self.feedback_message = f"Discarded {dropped_name}." if i18n.locale == "en" else f"Descartaste {dropped_name}."
                    self.feedback_success = True
                    pyxel.play(0, 3)

        # Belt quick assign buttons [B1], [B2], [B3]
        for idx, key in enumerate((pyxel.KEY_1, pyxel.KEY_2, pyxel.KEY_3)):
            bx = 98 + idx * 21
            if pyxel.btnp(key) or Renderer.is_clicked(bx, 230, 18, 18):
                if self.active_pane == "POUCH" and self.pouch_cursor < len(inv.pouch):
                    success, msg = inv.assign_pouch_to_belt(self.pouch_cursor, idx)
                    self.feedback_message = msg
                    self.feedback_success = success
                    if success:
                        pyxel.play(0, 3)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        inv = game_state.player.inventory
        from src.systems.inventory import ConsumableItem, EquipmentItem, EquipSlot
        from src.data.items import StatPotion

        fc = pyxel.frame_count
        pulse = (fc // 6) % 2

        equip_order = [
            EquipSlot.HEAD, EquipSlot.SHOULDERS, EquipSlot.CHEST, EquipSlot.HANDS,
            EquipSlot.MAIN_HAND, EquipSlot.OFF_HAND, EquipSlot.WAIST, EquipSlot.LEGS
        ]
        slot_labels = {
            EquipSlot.HEAD: "Head",
            EquipSlot.SHOULDERS: "Shld",
            EquipSlot.CHEST: "Chest",
            EquipSlot.HANDS: "Hands",
            EquipSlot.MAIN_HAND: "Main",
            EquipSlot.OFF_HAND: "Shield",
            EquipSlot.WAIST: "Waist",
            EquipSlot.LEGS: "Legs",
        }

        # =====================================================================
        # 1. UPPER LEFT: MANNEQUIN EQUIPMENT ALCOVE (x=4, y=26, w=138, h=115)
        # =====================================================================
        eq_x, eq_y, eq_w, eq_h = 4, 26, 138, 115
        renderer.draw_box(eq_x, eq_y, eq_w, eq_h, bg_col=COLOR_BLACK, border_col=COLOR_DARK_BLUE)
        pyxel.rectb(eq_x + 1, eq_y + 1, eq_w - 2, eq_h - 2, COLOR_NAVY)

        # Helmet Header Glyph & Title
        pyxel.blt(eq_x + 6, eq_y + 4, 0, 80, 8, 8, 8, 0)
        renderer.draw_text(eq_x + 18, eq_y + 5, "Equipment" if i18n.locale == "en" else "Equipamiento", COLOR_YELLOW)

        # Stone archway behind Hero Mannequin
        arch_x, arch_y = eq_x + 48, eq_y + 24
        pyxel.rect(arch_x, arch_y + 10, 38, 52, COLOR_NAVY)
        pyxel.tri(arch_x, arch_y + 10, arch_x + 19, arch_y, arch_x + 37, arch_y + 10, COLOR_NAVY)
        pyxel.rect(arch_x + 4, arch_y + 14, 30, 48, COLOR_BLACK)
        pyxel.tri(arch_x + 4, arch_y + 14, arch_x + 19, arch_y + 4, arch_x + 33, arch_y + 14, COLOR_BLACK)

        # Hanging small crimson banner in background
        pyxel.rect(arch_x + 13, arch_y + 14, 12, 18, COLOR_RED)
        pyxel.tri(arch_x + 13, arch_y + 32, arch_x + 19, arch_y + 36, arch_x + 24, arch_y + 32, COLOR_RED)
        pyxel.pset(arch_x + 18, arch_y + 20, COLOR_YELLOW)

        # Pedestal & Shadow
        shadow_x, shadow_y = arch_x + 3, arch_y + 54
        pyxel.elli(shadow_x, shadow_y, 32, 7, COLOR_NAVY)

        # Hero Sprite standing
        sprite_coords = {"warrior": (0, 0), "rogue": (0, 32), "mage": (16, 32)}
        pu, pv = sprite_coords.get(game_state.player.class_id, (0, 0))
        hx, hy = arch_x + 11, arch_y + 38
        pyxel.blt(hx, hy, 0, pu, pv, 16, 16, 0)

        # Drawn hero blade
        pyxel.line(hx + 14, hy + 6, hx + 21, hy - 1, COLOR_CYAN)
        pyxel.line(hx + 15, hy + 6, hx + 22, hy - 1, COLOR_WHITE)

        # Flanking 8 Equipment Slots
        for i, slot in enumerate(equip_order):
            is_right = (i >= 4)
            col_idx = i - 4 if is_right else i
            sx = eq_x + 78 if is_right else eq_x + 6
            sy = eq_y + 17 + col_idx * 24

            is_sel = (self.active_pane == "EQUIPMENT" and self.equip_cursor == i)
            equipped_item = inv.equipment.get(slot)

            # 16x16 Slot Icon Frame
            box_col = COLOR_NAVY if not is_sel else COLOR_DARK_BLUE
            border_col = COLOR_YELLOW if is_sel else (COLOR_LIGHT_BLUE if equipped_item else COLOR_NAVY)
            pyxel.rect(sx, sy, 16, 16, box_col)
            pyxel.rectb(sx, sy, 16, 16, border_col)

            if is_sel and pulse == 0:
                pyxel.rectb(sx - 1, sy - 1, 18, 18, COLOR_YELLOW)

            if equipped_item:
                iu, iv = self._get_item_icon(equipped_item)
                pyxel.blt(sx + 4, sy + 4, 0, iu, iv, 8, 8, 0)
            else:
                # Dashed empty box with faint silhouette icon
                du, dv = self._get_slot_default_icon(slot)
                pyxel.blt(sx + 4, sy + 4, 0, du, dv, 8, 8, 0)
                for py in range(sy + 2, sy + 14, 3):
                    pyxel.pset(sx + 2, py, COLOR_NAVY)
                    pyxel.pset(sx + 13, py, COLOR_NAVY)

            # Slot Text Label (Header & Item Name)
            tx = sx + 19
            s_name = slot_labels[slot]
            renderer.draw_text(tx, sy + 1, s_name, COLOR_YELLOW if is_sel else COLOR_WHITE)
            if equipped_item:
                renderer.draw_text(tx, sy + 8, equipped_item.localized_name[:7], COLOR_LIME)
            else:
                renderer.draw_text(tx, sy + 8, "(Empty)", COLOR_GRAY)

        # =====================================================================
        # 2. UPPER RIGHT: ITEM INSPECTOR DETAIL PANEL (x=144, y=26, w=108, h=115)
        # =====================================================================
        ins_x, ins_y, ins_w, ins_h = 144, 26, 108, 115
        renderer.draw_box(ins_x, ins_y, ins_w, ins_h, bg_col=COLOR_DARK_BLUE, border_col=COLOR_LIGHT_BLUE)
        pyxel.rectb(ins_x + 1, ins_y + 1, ins_w - 2, ins_h - 2, COLOR_NAVY)

        curr_item, curr_type = self._get_selected_item(game_state)

        # Large 22x22 Icon Showcase Frame
        fx, fy = ins_x + 6, ins_y + 6
        pyxel.rect(fx, fy, 22, 22, COLOR_NAVY)
        pyxel.rectb(fx, fy, 22, 22, COLOR_LIGHT_BLUE)

        if curr_item:
            iu, iv = self._get_item_icon(curr_item)
            pyxel.blt(fx + 7, fy + 7, 0, iu, iv, 8, 8, 0)
            renderer.draw_text(ins_x + 32, ins_y + 7, curr_item.localized_name[:12], COLOR_YELLOW)
            renderer.draw_text(ins_x + 32, ins_y + 16, curr_type[:12], COLOR_GRAY)
        else:
            pyxel.line(fx + 4, fy + 4, fx + 17, fy + 17, COLOR_NAVY)
            pyxel.line(fx + 17, fy + 4, fx + 4, fy + 17, COLOR_NAVY)
            renderer.draw_text(ins_x + 32, ins_y + 7, "Empty Slot" if i18n.locale == "en" else "Ranura Vacía", COLOR_GRAY)
            renderer.draw_text(ins_x + 32, ins_y + 16, curr_type[:12], COLOR_DARK_BLUE)

        # Stat Divider
        pyxel.line(ins_x + 6, ins_y + 32, ins_x + ins_w - 7, ins_y + 32, COLOR_LIGHT_BLUE)

        stat_y = ins_y + 36
        if isinstance(curr_item, EquipmentItem):
            stats = curr_item.stats_bonus
            if stats.attack > 0:
                renderer.draw_text(ins_x + 8, stat_y, f"ATK : +{stats.attack}", COLOR_WHITE)
                stat_y += 8
            if stats.defense > 0:
                renderer.draw_text(ins_x + 8, stat_y, f"DEF : +{stats.defense}", COLOR_WHITE)
                stat_y += 8
            if stats.speed != 0:
                renderer.draw_text(ins_x + 8, stat_y, f"SPD : {stats.speed:+d}", COLOR_WHITE)
                stat_y += 8
            if stats.crit_chance > 0:
                crit_pct = int(stats.crit_chance * 100)
                renderer.draw_text(ins_x + 8, stat_y, f"CRIT: +{crit_pct}%", COLOR_WHITE)
                stat_y += 8
            if stats.max_hp > 0:
                renderer.draw_text(ins_x + 8, stat_y, f"HP  : +{stats.max_hp}", COLOR_WHITE)
                stat_y += 8
        elif isinstance(curr_item, ConsumableItem):
            if curr_item.heal_amount > 0:
                renderer.draw_text(ins_x + 8, stat_y, f"HEAL: +{curr_item.heal_amount} HP", COLOR_LIME)
                stat_y += 8
            if isinstance(curr_item, StatPotion):
                b = curr_item.stat_bonus
                if b.attack > 0:
                    renderer.draw_text(ins_x + 8, stat_y, f"ATK : +{b.attack} (Perm)", COLOR_LIME)
                    stat_y += 8
                if b.defense > 0:
                    renderer.draw_text(ins_x + 8, stat_y, f"DEF : +{b.defense} (Perm)", COLOR_LIME)
                    stat_y += 8
                if b.speed > 0:
                    renderer.draw_text(ins_x + 8, stat_y, f"SPD : +{b.speed} (Perm)", COLOR_LIME)
                    stat_y += 8
                if b.max_hp > 0:
                    renderer.draw_text(ins_x + 8, stat_y, f"HP  : +{b.max_hp} (Perm)", COLOR_LIME)
                    stat_y += 8

        desc_line_y = max(stat_y + 2, ins_y + 70)
        pyxel.line(ins_x + 6, desc_line_y, ins_x + ins_w - 7, desc_line_y, COLOR_NAVY)

        desc_y = desc_line_y + 4
        if curr_item:
            lines = renderer.wrap_text(curr_item.localized_description, max_chars_per_line=16)
            for d_line in lines[:4]:
                renderer.draw_text(ins_x + 8, desc_y, d_line, COLOR_WHITE)
                desc_y += 8
        else:
            renderer.draw_text(ins_x + 8, desc_y, "Select an item to view details." if i18n.locale == "en" else "Selecciona un objeto para ver detalles.", COLOR_GRAY)

        # =====================================================================
        # 3. LOWER LEFT: 3-SLOT BELT PANEL (x=4, y=143, w=110, h=83)
        # =====================================================================
        belt_x, belt_y, belt_w, belt_h = 4, 143, 110, 83
        renderer.draw_box(belt_x, belt_y, belt_w, belt_h, bg_col=COLOR_BLACK, border_col=COLOR_DARK_BLUE)
        pyxel.rectb(belt_x + 1, belt_y + 1, belt_w - 2, belt_h - 2, COLOR_NAVY)

        # Flask Header Glyph & Title
        pyxel.blt(belt_x + 6, belt_y + 4, 0, 64, 0, 8, 8, 0)
        renderer.draw_text(belt_x + 17, belt_y + 5, t("belt_header").replace("-", "").strip(), COLOR_YELLOW)
        belt_count = sum(1 for b in inv.belt if b is not None)
        renderer.draw_text(belt_x + belt_w - 24, belt_y + 5, f"{belt_count}/3", COLOR_WHITE)

        for b_idx in range(MAX_BELT_SLOTS):
            bx = belt_x + 6 + b_idx * 33
            by = belt_y + 16
            bw, bh = 30, 60

            is_sel = (self.active_pane == "BELT" and self.belt_cursor == b_idx)
            b_item = inv.belt[b_idx]

            card_border = COLOR_YELLOW if is_sel else (COLOR_LIGHT_BLUE if b_item else COLOR_DARK_BLUE)
            pyxel.rect(bx, by, bw, bh, COLOR_DARK_BLUE if is_sel else COLOR_NAVY)
            pyxel.rectb(bx, by, bw, bh, card_border)

            if is_sel and pulse == 0:
                pyxel.rectb(bx - 1, by - 1, bw + 2, bh + 2, COLOR_YELLOW)

            renderer.draw_text(bx + 4, by + 3, f"[{b_idx+1}]", COLOR_YELLOW if is_sel else COLOR_WHITE)

            ix = bx + 6
            iy = by + 12
            pyxel.rect(ix, iy, 18, 18, COLOR_BLACK)
            pyxel.rectb(ix, iy, 18, 18, COLOR_LIGHT_BLUE if b_item else COLOR_DARK_BLUE)

            if b_item:
                iu, iv = self._get_item_icon(b_item)
                pyxel.blt(ix + 5, iy + 5, 0, iu, iv, 8, 8, 0)
                renderer.draw_text(bx + 2, by + 34, b_item.localized_name[:5], COLOR_WHITE)
                renderer.draw_text(bx + 2, by + 44, f"+{b_item.heal_amount}HP", COLOR_LIME)
            else:
                for dy in range(iy + 3, iy + 15, 3):
                    pyxel.pset(ix + 3, dy, COLOR_NAVY)
                    pyxel.pset(ix + 14, dy, COLOR_NAVY)
                renderer.draw_text(bx + 2, by + 38, "[Empty]", COLOR_GRAY)

        # =====================================================================
        # 4. LOWER RIGHT: 10-SLOT POUCH GRID (x=116, y=143, w=136, h=83)
        # =====================================================================
        po_x, po_y, po_w, po_h = 116, 143, 136, 83
        renderer.draw_box(po_x, po_y, po_w, po_h, bg_col=COLOR_BLACK, border_col=COLOR_DARK_BLUE)
        pyxel.rectb(po_x + 1, po_y + 1, po_w - 2, po_h - 2, COLOR_NAVY)

        pyxel.blt(po_x + 6, po_y + 4, 0, 104, 0, 8, 8, 0)
        pouch_title = f"Pouch ({len(inv.pouch)}/10)" if i18n.locale == "en" else f"Bolsa ({len(inv.pouch)}/10)"
        renderer.draw_text(po_x + 18, po_y + 5, pouch_title, COLOR_YELLOW)

        for p_idx in range(MAX_POUCH_SLOTS):
            col = p_idx % 5
            row = p_idx // 5
            slot_x = po_x + 8 + col * 24
            slot_y = po_y + 18 + row * 26

            is_sel = (self.active_pane == "POUCH" and self.pouch_cursor == p_idx)
            has_item = (p_idx < len(inv.pouch))

            slot_border = COLOR_YELLOW if is_sel else (COLOR_LIGHT_BLUE if has_item else COLOR_NAVY)
            pyxel.rect(slot_x, slot_y, 20, 20, COLOR_NAVY if has_item else COLOR_BLACK)
            pyxel.rectb(slot_x, slot_y, 20, 20, slot_border)

            if is_sel and pulse == 0:
                pyxel.rectb(slot_x - 1, slot_y - 1, 22, 22, COLOR_YELLOW)

            if has_item:
                p_item = inv.pouch[p_idx]
                iu, iv = self._get_item_icon(p_item)
                pyxel.blt(slot_x + 6, slot_y + 6, 0, iu, iv, 8, 8, 0)
            else:
                for dy in range(slot_y + 3, slot_y + 17, 3):
                    pyxel.pset(slot_x + 3, dy, COLOR_NAVY)
                    pyxel.pset(slot_x + 16, dy, COLOR_NAVY)

        # =====================================================================
        # 5. BOTTOM ACTION CONTROLS BAR (y=228 to y=248)
        # =====================================================================
        if self.feedback_message:
            msg_col = COLOR_LIME if self.feedback_success else COLOR_RED
            renderer.draw_text(10, 222, self.feedback_message, msg_col)

        e_label = "⚔ [ EQUIP / USE ]" if i18n.locale == "en" else "⚔ [ EQUIP / USAR ]"
        renderer.draw_button(4, 230, 90, 18, e_label, bg_col=COLOR_BLACK, border_col=COLOR_YELLOW, text_col=COLOR_YELLOW)

        renderer.draw_button(98, 230, 18, 18, "B1", bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE, text_col=COLOR_WHITE)
        renderer.draw_button(119, 230, 18, 18, "B2", bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE, text_col=COLOR_WHITE)
        renderer.draw_button(140, 230, 18, 18, "B3", bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE, text_col=COLOR_WHITE)

        d_label = "↓ [ DROP ]" if i18n.locale == "en" else "↓ [ TIRAR ]"
        renderer.draw_button(162, 230, 44, 18, d_label, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE, text_col=COLOR_PEACH)

        c_label = "✕ [ CLOSE ]" if i18n.locale == "en" else "✕ [ CERRAR ]"
        renderer.draw_button(210, 230, 42, 18, c_label, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE, text_col=COLOR_WHITE)


class EventsView(View):
    """Renders non-combat room encounters featuring gothic modal framing, treasure scenes, and centered event text."""

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or Renderer.is_clicked(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT):
            pyxel.play(0, 3)
            game_state.switch_mode(GameMode.MAP)

    def _draw_event_scene(self, box_x: int, box_y: int, box_w: int, text: str) -> None:
        """Render bespoke scene art: glowing ornate chest or holy sanctuary shrine."""
        fc = pyxel.frame_count
        cy = box_y + 60
        is_shrine = any(k in text.lower() for k in ("shrine", "sanctuary", "santuario", "altar", "pray", "rezar"))

        # Cobblestone ground at bottom of art frame
        ground_y = cy + 18
        pyxel.rect(box_x + 4, ground_y, box_w - 8, 22, COLOR_DARK_BLUE)
        for gx in range(box_x + 8, box_x + box_w - 12, 12):
            pyxel.line(gx, ground_y + 4, gx + 6, ground_y + 4, COLOR_NAVY)
            pyxel.line(gx + 6, ground_y + 11, gx + 11, ground_y + 11, COLOR_NAVY)

        # Ruined stone columns in background
        col_x_list = [box_x + 16, box_x + 36, box_x + box_w - 48, box_x + box_w - 28]
        for col_x in col_x_list:
            pyxel.rect(col_x, cy - 26, 12, 44, COLOR_NAVY)
            for my in range(cy - 22, cy + 18, 7):
                pyxel.line(col_x, my, col_x + 11, my, COLOR_DARK_BLUE)
                pyxel.pset(col_x + ((my // 3) % 8), my + 2, COLOR_LIGHT_BLUE)

        if is_shrine:
            # --- SANCTUARY / SHRINE ENCOUNTER ---
            sx = SCREEN_WIDTH // 2
            # Stone Altar Base
            pyxel.rect(sx - 24, cy + 4, 48, 16, COLOR_NAVY)
            pyxel.rectb(sx - 24, cy + 4, 48, 16, COLOR_LIGHT_BLUE)
            # Glowing Runestone Monolith
            pyxel.rect(sx - 14, cy - 24, 28, 30, COLOR_DARK_BLUE)
            pyxel.rectb(sx - 14, cy - 24, 28, 30, COLOR_CYAN)
            # Carved Holy Cross / Rune
            pyxel.line(sx, cy - 18, sx, cy - 2, COLOR_WHITE)
            pyxel.line(sx - 7, cy - 10, sx + 7, cy - 10, COLOR_WHITE)
            # Altar candles
            for cx in [sx - 20, sx + 20]:
                pyxel.rect(cx, cy - 1, 3, 5, COLOR_WHITE)
                pyxel.pset(cx + 1, cy - 3, COLOR_YELLOW if fc % 4 < 2 else COLOR_ORANGE)
            # Radiant healing aura
            if fc % 6 < 3:
                pyxel.circb(sx, cy - 10, 18, COLOR_CYAN)
        else:
            # --- ORNATE TREASURE CHEST ENCOUNTER ---
            cx = SCREEN_WIDTH // 2 - 24

            # Shadow beneath chest
            pyxel.elli(cx - 12, cy + 16, 72, 8, COLOR_NAVY)

            # Open Chest Lid (angled back)
            pyxel.rect(cx + 2, cy - 8, 44, 13, COLOR_NAVY)
            pyxel.rectb(cx + 2, cy - 8, 44, 13, COLOR_YELLOW)
            pyxel.line(cx + 12, cy - 8, cx + 12, cy + 4, COLOR_YELLOW)
            pyxel.line(cx + 34, cy - 8, cx + 34, cy + 4, COLOR_YELLOW)

            # Chest Base
            pyxel.rect(cx, cy + 6, 48, 16, COLOR_NAVY)
            pyxel.rectb(cx, cy + 6, 48, 16, COLOR_YELLOW)
            pyxel.line(cx, cy + 14, cx + 47, cy + 14, COLOR_DARK_BLUE)
            pyxel.line(cx + 10, cy + 6, cx + 10, cy + 21, COLOR_YELLOW)
            pyxel.line(cx + 37, cy + 6, cx + 37, cy + 21, COLOR_YELLOW)

            # Golden lock & keyhole
            pyxel.rect(cx + 21, cy + 8, 6, 8, COLOR_YELLOW)
            pyxel.pset(cx + 23, cy + 11, COLOR_BLACK)
            pyxel.pset(cx + 24, cy + 11, COLOR_BLACK)
            pyxel.pset(cx + 23, cy + 12, COLOR_BLACK)

            # Overflowing gold pile inside chest
            pyxel.rect(cx + 4, cy + 2, 40, 5, COLOR_YELLOW)
            pyxel.pset(cx + 8, cy + 3, COLOR_ORANGE)
            pyxel.pset(cx + 16, cy + 4, COLOR_ORANGE)
            pyxel.pset(cx + 28, cy + 3, COLOR_ORANGE)

            # Center Ruby Gem
            pyxel.rect(cx + 20, cy + 1, 5, 5, COLOR_RED)
            pyxel.pset(cx + 21, cy + 2, COLOR_WHITE)
            pyxel.pset(cx + 22, cy + 3, COLOR_PINK)

            # Steel sword blade embedded in gold
            pyxel.line(cx + 34, cy + 5, cx + 42, cy - 5, COLOR_WHITE)
            pyxel.line(cx + 35, cy + 4, cx + 43, cy - 4, COLOR_CYAN)
            pyxel.line(cx + 39, cy - 6, cx + 44, cy - 1, COLOR_YELLOW)

            # Piles of gold coins on cobblestone floor
            pyxel.rect(cx - 16, cy + 16, 14, 6, COLOR_YELLOW)
            pyxel.rect(cx - 8, cy + 14, 10, 5, COLOR_YELLOW)
            pyxel.rect(cx + 46, cy + 15, 16, 6, COLOR_YELLOW)
            pyxel.rect(cx + 42, cy + 18, 10, 4, COLOR_YELLOW)
            pyxel.rect(cx + 10, cy + 20, 8, 3, COLOR_YELLOW)
            pyxel.rect(cx + 26, cy + 21, 10, 3, COLOR_YELLOW)
            pyxel.pset(cx - 12, cy + 18, COLOR_ORANGE)
            pyxel.pset(cx - 5, cy + 16, COLOR_ORANGE)
            pyxel.pset(cx + 50, cy + 17, COLOR_ORANGE)
            pyxel.pset(cx + 56, cy + 19, COLOR_ORANGE)

            # Animated golden sparkle stars
            sparkle_coords = [
                (cx - 6, cy - 4), (cx - 14, cy + 8),
                (cx + 14, cy - 12), (cx + 56, cy - 5), (cx + 48, cy + 10)
            ]
            for si, (sx, sy) in enumerate(sparkle_coords):
                if (fc + si * 5) % 18 < 10:
                    pyxel.pset(sx, sy, COLOR_WHITE)
                    pyxel.pset(sx - 1, sy, COLOR_YELLOW)
                    pyxel.pset(sx + 1, sy, COLOR_YELLOW)
                    pyxel.pset(sx, sy - 1, COLOR_YELLOW)
                    pyxel.pset(sx, sy + 1, COLOR_YELLOW)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        box_x, box_y, box_w, box_h = 18, 42, SCREEN_WIDTH - 36, 198

        # =====================================================================
        # 1. OUTER MODAL FRAME & GOTHIC CORNER ACCENTS
        # =====================================================================
        pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)
        pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_LIGHT_BLUE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_NAVY)

        # Ornate Corner Crosses
        for cx, cy in [
            (box_x + 1, box_y + 1),
            (box_x + box_w - 2, box_y + 1),
            (box_x + 1, box_y + box_h - 2),
            (box_x + box_w - 2, box_y + box_h - 2),
        ]:
            pyxel.pset(cx, cy, COLOR_LIGHT_BLUE)
            pyxel.pset(cx - 1, cy, COLOR_DARK_BLUE)
            pyxel.pset(cx + 1, cy, COLOR_DARK_BLUE)
            pyxel.pset(cx, cy - 1, COLOR_DARK_BLUE)
            pyxel.pset(cx, cy + 1, COLOR_DARK_BLUE)

        # =====================================================================
        # 2. HEADER BANNER PLAQUE (-- Room Encounter --)
        # =====================================================================
        pw, ph = 184, 18
        px = (SCREEN_WIDTH - pw) // 2
        py = box_y + 8

        renderer.draw_box(px, py, pw, ph, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE)
        pyxel.rectb(px + 1, py + 1, pw - 2, ph - 2, COLOR_NAVY)

        # Corner ticks on Plaque
        pyxel.line(px + 3, py + 3, px + 6, py + 3, COLOR_LIGHT_BLUE)
        pyxel.line(px + 3, py + 3, px + 3, py + 6, COLOR_LIGHT_BLUE)
        pyxel.line(px + pw - 4, py + 3, px + pw - 7, py + 3, COLOR_LIGHT_BLUE)
        pyxel.line(px + pw - 4, py + 3, px + pw - 4, py + 6, COLOR_LIGHT_BLUE)

        # Star emblems on left & right
        for star_x in [px + 10, px + pw - 12]:
            pyxel.pset(star_x, py + 9, COLOR_WHITE)
            pyxel.pset(star_x - 1, py + 9, COLOR_CYAN)
            pyxel.pset(star_x + 1, py + 9, COLOR_CYAN)
            pyxel.pset(star_x, py + 8, COLOR_CYAN)
            pyxel.pset(star_x, py + 10, COLOR_CYAN)

        header_title = t("room_encounter_header")
        renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(header_title) // 2, py + 6, header_title, COLOR_YELLOW)

        # =====================================================================
        # 3. BESPOKE SCENE ILLUSTRATION
        # =====================================================================
        event_raw_text = game_state.current_event_text or ""
        self._draw_event_scene(box_x, box_y, box_w, event_raw_text)

        # =====================================================================
        # 4. CENTERED NARRATIVE & REWARD TEXT
        # =====================================================================
        lines = renderer.wrap_text(event_raw_text, max_chars_per_line=34)
        if not lines:
            lines = [t("room_encounter_header")]

        txt_start_y = box_y + 112
        for li, line in enumerate(lines[:3]):
            tw = renderer.get_text_width(line)
            tx = SCREEN_WIDTH // 2 - tw // 2
            # Highlight rewards line
            is_reward = any(k in line.lower() for k in ("gold", "oro", "heal", "cura", "obtained", "obtenido", "gained"))
            renderer.draw_text(tx, txt_start_y + li * 12, line, COLOR_YELLOW if is_reward else COLOR_WHITE)

        # =====================================================================
        # 5. ORNATE [CONTINUE] BUTTON WITH CORNER BRACKETS
        # =====================================================================
        btn_w, btn_h = 92, 18
        btn_x = (SCREEN_WIDTH - btn_w) // 2
        btn_y = box_y + box_h - 30

        pyxel.rect(btn_x, btn_y, btn_w, btn_h, COLOR_BLACK)
        pyxel.rectb(btn_x, btn_y, btn_w, btn_h, COLOR_LIGHT_BLUE)

        # Decorative Corner Ticks protruding from button
        pyxel.line(btn_x - 2, btn_y - 2, btn_x + 3, btn_y - 2, COLOR_LIGHT_BLUE)
        pyxel.line(btn_x - 2, btn_y - 2, btn_x - 2, btn_y + 3, COLOR_LIGHT_BLUE)

        pyxel.line(btn_x + btn_w + 1, btn_y - 2, btn_x + btn_w - 4, btn_y - 2, COLOR_LIGHT_BLUE)
        pyxel.line(btn_x + btn_w + 1, btn_y - 2, btn_x + btn_w + 1, btn_y + 3, COLOR_LIGHT_BLUE)

        pyxel.line(btn_x - 2, btn_y + btn_h + 1, btn_x + 3, btn_y + btn_h + 1, COLOR_LIGHT_BLUE)
        pyxel.line(btn_x - 2, btn_y + btn_h + 1, btn_x - 2, btn_y + btn_h - 4, COLOR_LIGHT_BLUE)

        pyxel.line(btn_x + btn_w + 1, btn_y + btn_h + 1, btn_x + btn_w - 4, btn_y + btn_h + 1, COLOR_LIGHT_BLUE)
        pyxel.line(btn_x + btn_w + 1, btn_y + btn_h + 1, btn_x + btn_w + 1, btn_y + btn_h - 4, COLOR_LIGHT_BLUE)

        btn_label = "[CONTINUE]" if i18n.locale == "en" else "[CONTINUAR]"
        renderer.draw_text(btn_x + (btn_w - renderer.get_text_width(btn_label)) // 2, btn_y + 6, btn_label, COLOR_WHITE)

class EndGameView(View):
    """Renders atmospheric Game Over or Victory screens with gothic catacomb art, fallen heroes, and ornate frames."""

    def __init__(self, is_victory: bool) -> None:
        self.is_victory: bool = is_victory

    def update(self, game_state: GameState) -> None:
        # Restart on Enter, Space, or clicking the Restart button
        btn_w, btn_h = 104, 18
        btn_x = (SCREEN_WIDTH - btn_w) // 2
        btn_y = 196
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE) or Renderer.is_clicked(btn_x, btn_y, btn_w, btn_h):
            pyxel.play(0, 3)
            game_state.__init__()

    def _draw_bold_letter(self, x: int, y: int, char: str, col: int) -> int:
        """Render chunky 7x10 retro title characters for the death headline."""
        FONT = {
            'Y': ["#.....#", "#.....#", ".#...#.", "..#.#..", "...#...", "...#...", "...#...", "...#...", "...#..."],
            'O': [".#####.", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", ".#####."],
            'U': ["#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", ".#####."],
            'D': ["######.", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "######."],
            'I': ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
            'E': ["######", "#.....", "#.....", "#####.", "#.....", "#.....", "#.....", "#.....", "######"],
        }
        bitmap = FONT.get(char)
        if not bitmap:
            return 6

        w = len(bitmap[0])
        # Drop shadow
        for r, row in enumerate(bitmap):
            for c, bit in enumerate(row):
                if bit == '#':
                    pyxel.pset(x + c + 1, y + r + 1, COLOR_BLACK)
                    pyxel.pset(x + c, y + r, col)
        return w

    def _draw_death_scene(self, box_x: int, box_y: int, box_w: int, box_h: int) -> None:
        """Draw the catacomb chamber, fallen hero, braziers, and skeletal remains."""
        fc = pyxel.frame_count

        # Stone arch and background masonry
        for my in range(box_y + 16, box_y + 148, 8):
            pyxel.line(box_x + 8, my, box_x + box_w - 9, my, COLOR_NAVY)
            pyxel.pset(box_x + 24 + ((my * 3) % 40), my + 4, COLOR_DARK_BLUE)
            pyxel.pset(box_x + box_w - 44 - ((my * 5) % 40), my + 4, COLOR_DARK_BLUE)

        # Distant central arch
        arch_x = SCREEN_WIDTH // 2
        pyxel.rect(arch_x - 48, box_y + 14, 96, 120, COLOR_NAVY)
        pyxel.tri(arch_x - 48, box_y + 14, arch_x, box_y + 2, arch_x + 47, box_y + 14, COLOR_NAVY)
        pyxel.rect(arch_x - 44, box_y + 18, 88, 116, COLOR_BLACK)
        pyxel.tri(arch_x - 44, box_y + 18, arch_x, box_y + 6, arch_x + 43, box_y + 18, COLOR_BLACK)

        # Hanging crimson banners on left and right
        for bx in [box_x + 16, box_x + box_w - 32]:
            pyxel.rect(bx, box_y + 16, 16, 38, COLOR_RED)
            pyxel.tri(bx, box_y + 54, bx + 8, box_y + 64, bx + 15, box_y + 54, COLOR_RED)
            pyxel.rectb(bx, box_y + 16, 16, 38, COLOR_BLACK)
            pyxel.line(bx + 7, box_y + 24, bx + 7, box_y + 44, COLOR_BLACK)
            pyxel.line(bx + 8, box_y + 24, bx + 8, box_y + 44, COLOR_BLACK)
            pyxel.line(bx + 3, box_y + 30, bx + 12, box_y + 30, COLOR_BLACK)

        # Cobblestone ground
        ground_y = box_y + 144
        pyxel.rect(box_x + 4, ground_y, box_w - 8, box_h - 148, COLOR_DARK_BLUE)
        for gy in range(ground_y + 2, box_y + box_h - 6, 7):
            pyxel.line(box_x + 6, gy, box_x + box_w - 7, gy, COLOR_NAVY)
            for gx in range(box_x + 12 + ((gy // 7) % 2) * 10, box_x + box_w - 12, 18):
                pyxel.line(gx, gy, gx, gy + 6, COLOR_BLACK)

        # Flanking stone braziers on pedestals
        for tx in [box_x + 24, box_x + box_w - 32]:
            pyxel.rect(tx - 2, ground_y - 28, 9, 28, COLOR_NAVY)
            pyxel.rectb(tx - 3, ground_y - 32, 11, 5, COLOR_LIGHT_BLUE)
            pyxel.tri(tx - 2, ground_y - 32, tx + 2, ground_y - 44, tx + 6, ground_y - 32, COLOR_RED)
            pyxel.tri(tx - 1, ground_y - 32, tx + 2, ground_y - 40, tx + 5, ground_y - 32, COLOR_ORANGE)
            pyxel.pset(tx + 2, ground_y - 36, COLOR_YELLOW if fc % 4 < 2 else COLOR_WHITE)
            if fc % 3 == 0:
                pyxel.pset(tx + (fc % 3), ground_y - 46, COLOR_YELLOW)

        # Left: Fallen column & skull
        pyxel.rect(box_x + 42, ground_y - 20, 16, 22, COLOR_NAVY)
        pyxel.line(box_x + 45, ground_y - 20, box_x + 45, ground_y + 1, COLOR_DARK_BLUE)
        pyxel.line(box_x + 50, ground_y - 20, box_x + 50, ground_y + 1, COLOR_DARK_BLUE)
        pyxel.line(box_x + 54, ground_y - 20, box_x + 54, ground_y + 1, COLOR_DARK_BLUE)
        sk1_x, sk1_y = box_x + 38, ground_y + 2
        pyxel.circ(sk1_x, sk1_y, 6, COLOR_LIGHT_BLUE)
        pyxel.rect(sk1_x - 3, sk1_y + 3, 7, 4, COLOR_LIGHT_BLUE)
        pyxel.pset(sk1_x - 2, sk1_y, COLOR_BLACK)
        pyxel.pset(sk1_x + 2, sk1_y, COLOR_BLACK)
        pyxel.pset(sk1_x, sk1_y + 2, COLOR_BLACK)

        # Right: Embedded blade & skull with bone
        sw_x, sw_y = box_x + box_w - 52, ground_y - 18
        pyxel.line(sw_x, sw_y, sw_x + 5, sw_y + 24, COLOR_LIGHT_BLUE)
        pyxel.line(sw_x - 3, sw_y + 4, sw_x + 4, sw_y + 2, COLOR_WHITE)
        pyxel.rect(sw_x - 4, sw_y + 18, 12, 6, COLOR_NAVY)
        sk2_x, sk2_y = box_x + box_w - 38, ground_y + 2
        pyxel.circ(sk2_x, sk2_y, 6, COLOR_LIGHT_BLUE)
        pyxel.rect(sk2_x - 3, sk2_y + 3, 7, 4, COLOR_LIGHT_BLUE)
        pyxel.pset(sk2_x - 2, sk2_y, COLOR_BLACK)
        pyxel.pset(sk2_x + 2, sk2_y, COLOR_BLACK)
        pyxel.line(sk2_x - 10, sk2_y + 9, sk2_x - 2, sk2_y + 9, COLOR_LIGHT_BLUE)
        pyxel.pset(sk2_x - 11, sk2_y + 8, COLOR_LIGHT_BLUE)
        pyxel.pset(sk2_x - 11, sk2_y + 10, COLOR_LIGHT_BLUE)
        pyxel.pset(sk2_x - 1, sk2_y + 8, COLOR_LIGHT_BLUE)
        pyxel.pset(sk2_x - 1, sk2_y + 10, COLOR_LIGHT_BLUE)

        # Fallen Hero Body
        hx = SCREEN_WIDTH // 2 - 4
        hy = ground_y - 4

        # Blood pool
        pyxel.elli(hx - 24, hy + 4, 52, 9, COLOR_RED)
        pyxel.elli(hx - 16, hy + 6, 36, 6, COLOR_PURPLE)
        pyxel.pset(hx - 26, hy + 6, COLOR_RED)
        pyxel.pset(hx + 28, hy + 7, COLOR_RED)
        pyxel.pset(hx + 18, hy + 11, COLOR_RED)

        # Body
        pyxel.circ(hx + 4, hy - 1, 7, COLOR_NAVY)
        pyxel.circb(hx + 4, hy - 1, 7, COLOR_RED)
        pyxel.pset(hx + 2, hy + 2, COLOR_PEACH)
        pyxel.pset(hx + 3, hy + 2, COLOR_PEACH)
        pyxel.rect(hx - 12, hy - 2, 12, 8, COLOR_DARK_BLUE)
        pyxel.line(hx - 12, hy + 2, hx, hy + 2, COLOR_NAVY)
        pyxel.pset(hx - 16, hy + 3, COLOR_PEACH)
        pyxel.pset(hx - 15, hy + 4, COLOR_PEACH)
        pyxel.rect(hx - 20, hy + 1, 7, 4, COLOR_BROWN)

        # Dropped dagger
        pyxel.line(hx + 14, hy + 8, hx + 26, hy + 11, COLOR_WHITE)
        pyxel.line(hx + 14, hy + 9, hx + 25, hy + 12, COLOR_CYAN)
        pyxel.line(hx + 12, hy + 7, hx + 14, hy + 11, COLOR_YELLOW)
        pyxel.pset(hx + 10, hy + 7, COLOR_BROWN)

        # Blood motes
        motes = [
            (hx - 14, hy - 16), (hx + 2, hy - 24),
            (hx + 18, hy - 14), (hx - 4, hy - 32)
        ]
        for mi, (mx, my) in enumerate(motes):
            float_y = my - ((fc + mi * 7) % 24)
            if float_y > box_y + 30:
                pyxel.pset(mx, float_y, COLOR_RED if mi % 2 == 0 else COLOR_PINK)

    def _draw_death_header(self, box_x: int, box_y: int, box_w: int, renderer: Renderer) -> None:
        """Draw the grim skull crest, title banner, and epitaph text."""
        cx = SCREEN_WIDTH // 2

        # Grim Skull Emblem
        sk_y = box_y + 12
        pyxel.circ(cx, sk_y + 6, 7, COLOR_RED)
        pyxel.rect(cx - 4, sk_y + 9, 9, 5, COLOR_RED)
        pyxel.pset(cx - 3, sk_y + 6, COLOR_BLACK)
        pyxel.pset(cx + 3, sk_y + 6, COLOR_BLACK)
        pyxel.pset(cx, sk_y + 8, COLOR_BLACK)
        pyxel.line(cx - 2, sk_y + 12, cx - 2, sk_y + 13, COLOR_BLACK)
        pyxel.line(cx, sk_y + 12, cx, sk_y + 13, COLOR_BLACK)
        pyxel.line(cx + 2, sk_y + 12, cx + 2, sk_y + 13, COLOR_BLACK)

        # Banner bars
        pyxel.line(cx - 40, sk_y + 8, cx - 12, sk_y + 8, COLOR_RED)
        pyxel.line(cx - 40, sk_y + 11, cx - 12, sk_y + 11, COLOR_RED)
        pyxel.line(cx + 12, sk_y + 8, cx + 40, sk_y + 8, COLOR_RED)
        pyxel.line(cx + 12, sk_y + 11, cx + 40, sk_y + 11, COLOR_RED)
        pyxel.pset(cx - 42, sk_y + 9, COLOR_RED)
        pyxel.pset(cx + 42, sk_y + 9, COLOR_RED)

        # Chunky "YOU DIED" Title
        title_y = box_y + 32
        text_w = 78
        start_x = cx - text_w // 2

        curr_x = start_x
        for char in "YOU DIED":
            if char == ' ':
                curr_x += 6
            else:
                w = self._draw_bold_letter(curr_x, title_y, char, COLOR_RED)
                curr_x += w + 2

        # Diamond Separator Line
        div_y = title_y + 16
        pyxel.line(cx - 52, div_y, cx + 52, div_y, COLOR_RED)
        pyxel.pset(cx, div_y - 2, COLOR_RED)
        pyxel.line(cx - 2, div_y, cx + 2, div_y, COLOR_RED)
        pyxel.pset(cx, div_y + 2, COLOR_RED)
        pyxel.pset(cx, div_y, COLOR_WHITE)

        # Epitaph Text
        if i18n.locale == "es":
            line1 = "Tus huesos se unen a la"
            line2 = "mazmorra eterna..."
        else:
            line1 = "Your bones join the"
            line2 = "endless dungeon..."

        renderer.draw_text(cx - renderer.get_text_width(line1) // 2, div_y + 8, line1, COLOR_WHITE)
        renderer.draw_text(cx - renderer.get_text_width(line2) // 2, div_y + 18, line2, COLOR_WHITE)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        box_x, box_y, box_w, box_h = 10, 28, SCREEN_WIDTH - 20, 220
        fc = pyxel.frame_count

        if not self.is_victory:
            # =================================================================
            # GAME OVER / DEATH SCREEN
            # =================================================================
            pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

            # Scene Backdrop & Fallen Champion
            self._draw_death_scene(box_x, box_y, box_w, box_h)

            # Header, Skull, Big Title & Epitaph
            self._draw_death_header(box_x, box_y, box_w, renderer)

            # Outer Red Border with Corner Ornaments
            pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_RED)
            pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_RED)

            for cx, cy in [
                (box_x + 3, box_y + 3),
                (box_x + box_w - 4, box_y + 3),
                (box_x + 3, box_y + box_h - 4),
                (box_x + box_w - 4, box_y + box_h - 4),
            ]:
                pyxel.pset(cx, cy, COLOR_RED)
                pyxel.pset(cx - 1, cy, COLOR_RED)
                pyxel.pset(cx + 1, cy, COLOR_RED)
                pyxel.pset(cx, cy - 1, COLOR_RED)
                pyxel.pset(cx, cy + 1, COLOR_RED)

            # Restart Button with Corner Bracket Ticks
            btn_w, btn_h = 104, 18
            btn_x = (SCREEN_WIDTH - btn_w) // 2
            btn_y = 196

            pyxel.rect(btn_x, btn_y, btn_w, btn_h, COLOR_BLACK)
            pyxel.rectb(btn_x, btn_y, btn_w, btn_h, COLOR_RED)

            pyxel.line(btn_x - 2, btn_y - 2, btn_x + 3, btn_y - 2, COLOR_RED)
            pyxel.line(btn_x - 2, btn_y - 2, btn_x - 2, btn_y + 3, COLOR_RED)
            pyxel.line(btn_x + btn_w + 1, btn_y - 2, btn_x + btn_w - 4, btn_y - 2, COLOR_RED)
            pyxel.line(btn_x + btn_w + 1, btn_y - 2, btn_x + btn_w + 1, btn_y + 3, COLOR_RED)
            pyxel.line(btn_x - 2, btn_y + btn_h + 1, btn_x + 3, btn_y + btn_h + 1, COLOR_RED)
            pyxel.line(btn_x - 2, btn_y + btn_h + 1, btn_x - 2, btn_y + btn_h - 4, COLOR_RED)
            pyxel.line(btn_x + btn_w + 1, btn_y + btn_h + 1, btn_x + btn_w - 4, btn_y + btn_h + 1, COLOR_RED)
            pyxel.line(btn_x + btn_w + 1, btn_y + btn_h + 1, btn_x + btn_w + 1, btn_y + btn_h - 4, COLOR_RED)

            btn_label = "[ RESTART ]" if i18n.locale == "en" else "[ REINICIAR ]"
            renderer.draw_text(btn_x + (btn_w - renderer.get_text_width(btn_label)) // 2, btn_y + 6, btn_label, COLOR_WHITE)

        else:
            # =================================================================
            # TRIUMPHANT VICTORY SCREEN
            # =================================================================
            pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

            # Golden Spire Cathedral backdrop
            cx = SCREEN_WIDTH // 2
            for my in range(box_y + 16, box_y + 148, 8):
                pyxel.line(box_x + 8, my, box_x + box_w - 9, my, COLOR_NAVY)

            # Golden Crown of Aethelgard at top
            crown_y = box_y + 16
            pyxel.rect(cx - 10, crown_y + 4, 20, 8, COLOR_YELLOW)
            pyxel.tri(cx - 10, crown_y + 4, cx - 10, crown_y - 4, cx - 4, crown_y + 4, COLOR_YELLOW)
            pyxel.tri(cx - 4, crown_y + 4, cx, crown_y - 6, cx + 4, crown_y + 4, COLOR_YELLOW)
            pyxel.tri(cx + 4, crown_y + 4, cx + 10, crown_y - 4, cx + 10, crown_y + 4, COLOR_YELLOW)
            pyxel.pset(cx, crown_y - 2, COLOR_WHITE)
            pyxel.pset(cx - 5, crown_y + 8, COLOR_RED)
            pyxel.pset(cx + 5, crown_y + 8, COLOR_CYAN)

            # Radiating gold sunburst laurels
            if (fc // 6) % 2 == 0:
                pyxel.circb(cx, crown_y + 6, 24, COLOR_YELLOW)

            # Victory Title & Subtitle
            vic_title = t("victory_achieved")
            renderer.draw_text(cx - renderer.get_text_width(vic_title) // 2, box_y + 48, vic_title, COLOR_YELLOW)

            v_lines = renderer.wrap_text(t("victory_desc"), max_chars_per_line=34)
            for li, line in enumerate(v_lines):
                renderer.draw_text(cx - renderer.get_text_width(line) // 2, box_y + 68 + li * 12, line, COLOR_WHITE)

            # Hero standing victorious on pedestal
            sprite_coords = {"warrior": (0, 0), "rogue": (0, 32), "mage": (16, 32)}
            pu, pv = sprite_coords.get(game_state.player.class_id, (0, 0))
            pyxel.elli(cx - 12, box_y + 160, 24, 6, COLOR_NAVY)
            pyxel.blt(cx - 8, box_y + 144, 0, pu, pv, 16, 16, 0)
            pyxel.line(cx + 6, box_y + 150, cx + 14, box_y + 142, COLOR_CYAN)
            pyxel.line(cx + 7, box_y + 150, cx + 15, box_y + 142, COLOR_WHITE)

            # Double Gold Frame
            pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_YELLOW)
            pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_ORANGE)

            # Restart / Play Again Button
            btn_w, btn_h = 104, 18
            btn_x = (SCREEN_WIDTH - btn_w) // 2
            btn_y = 196
            renderer.draw_button(btn_x, btn_y, btn_w, btn_h, t("btn_restart"), bg_col=COLOR_BLACK, border_col=COLOR_YELLOW, text_col=COLOR_YELLOW)

class ClassSelectView(View):
    """Interactive class selection screen featuring panoramic backdrop, hero cards, and stat alcove."""

    def __init__(self) -> None:
        self.classes: list[str] = ["warrior", "rogue", "mage"]
        self.selected_index: int = 0
        self.route_mode: str = "FATE"

    def update(self, game_state: GameState) -> None:
        from src.config import SND_CLICK, SND_VICTORY

        # Toggle route mode
        if pyxel.btnp(pyxel.KEY_B) or pyxel.btnp(pyxel.KEY_T) or Renderer.is_clicked(70, 230, 96, 18):
            self.route_mode = "PATHFINDER" if self.route_mode == "FATE" else "FATE"
            pyxel.play(0, SND_CLICK)

        card_w, card_h = 78, 80
        x_offsets = [6, 89, 172]
        card_y = 28

        for i, card_x in enumerate(x_offsets):
            if Renderer.is_clicked(card_x, card_y, card_w, card_h):
                if self.selected_index == i:
                    pyxel.play(0, SND_VICTORY)
                    game_state.start_new_game(self.classes[self.selected_index], route_mode=self.route_mode)
                    return
                else:
                    self.selected_index = i
                    pyxel.play(0, SND_CLICK)

        if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
            self.selected_index = (self.selected_index - 1) % len(self.classes)
            pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
            self.selected_index = (self.selected_index + 1) % len(self.classes)
            pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_1):
            self.selected_index = 0
            pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_2):
            self.selected_index = 1
            pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_3):
            self.selected_index = 2
            pyxel.play(0, SND_CLICK)
        elif pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE) or Renderer.is_clicked(172, 230, 78, 18):
            pyxel.play(0, SND_VICTORY)
            game_state.start_new_game(self.classes[self.selected_index], route_mode=self.route_mode)
        elif pyxel.btnp(pyxel.KEY_ESCAPE) or Renderer.is_clicked(6, 230, 58, 18):
            game_state.switch_mode(GameMode.WELCOME)

    def _draw_stat_icon(self, x: int, y: int, stat_type: str) -> None:
        """Draw small 5x5 stat glyphs matching the reference HUD."""
        if stat_type == "hp":
            # Green Heart
            pyxel.pset(x + 1, y, COLOR_LIME)
            pyxel.pset(x + 3, y, COLOR_LIME)
            pyxel.rect(x, y + 1, 5, 2, COLOR_LIME)
            pyxel.pset(x + 1, y + 3, COLOR_LIME)
            pyxel.pset(x + 2, y + 3, COLOR_LIME)
            pyxel.pset(x + 3, y + 3, COLOR_LIME)
            pyxel.pset(x + 2, y + 4, COLOR_LIME)
        elif stat_type == "atk":
            # Red Crossed Blades
            pyxel.line(x, y, x + 4, y + 4, COLOR_RED)
            pyxel.line(x + 4, y, x, y + 4, COLOR_RED)
            pyxel.pset(x + 2, y + 2, COLOR_WHITE)
        elif stat_type == "def":
            # Blue Shield
            pyxel.rect(x + 1, y, 3, 3, COLOR_CYAN)
            pyxel.pset(x, y + 1, COLOR_CYAN)
            pyxel.pset(x + 4, y + 1, COLOR_CYAN)
            pyxel.pset(x + 2, y + 4, COLOR_CYAN)
            pyxel.line(x + 1, y + 3, x + 3, y + 3, COLOR_CYAN)
        elif stat_type == "spd":
            # Yellow Speed Boot
            pyxel.rect(x + 1, y, 2, 4, COLOR_YELLOW)
            pyxel.rect(x + 1, y + 3, 4, 2, COLOR_YELLOW)
            pyxel.pset(x + 4, y + 4, COLOR_WHITE)
        elif stat_type == "crit":
            # Orange Star
            pyxel.pset(x + 2, y, COLOR_ORANGE)
            pyxel.line(x, y + 2, x + 4, y + 2, COLOR_ORANGE)
            pyxel.pset(x + 2, y + 4, COLOR_ORANGE)
            pyxel.pset(x + 2, y + 2, COLOR_YELLOW)

    def _draw_skill_glyph(self, x: int, y: int, skill_id: str) -> None:
        """Render distinct skill art inside the skill thumbnail box."""
        fc = pyxel.frame_count
        if "cross_cut" in skill_id:
            # Dual cyan sword slashes
            pyxel.line(x + 2, y + 2, x + 9, y + 9, COLOR_CYAN)
            pyxel.line(x + 3, y + 2, x + 10, y + 9, COLOR_WHITE)
            pyxel.line(x + 8, y + 2, x + 1, y + 9, COLOR_CYAN)
            pyxel.line(x + 9, y + 2, x + 2, y + 9, COLOR_WHITE)
        elif "shadow" in skill_id:
            # Shadow crescent with twin blade glints
            pyxel.circ(x + 6, y + 6, 4, COLOR_PURPLE)
            pyxel.circ(x + 8, y + 5, 3, COLOR_NAVY)
            pyxel.line(x + 2, y + 8, x + 9, y + 2, COLOR_WHITE)
        elif "arcane" in skill_id:
            # Pulsing arcane energy orb
            pyxel.circ(x + 6, y + 6, 3, COLOR_CYAN)
            pyxel.pset(x + 6, y + 6, COLOR_WHITE)
            if (fc // 6) % 2 == 0:
                pyxel.pset(x + 2, y + 2, COLOR_LIGHT_BLUE)
                pyxel.pset(x + 9, y + 9, COLOR_LIGHT_BLUE)
        else:
            # Default star burst
            pyxel.circ(x + 6, y + 6, 3, COLOR_YELLOW)
            pyxel.pset(x + 6, y + 6, COLOR_WHITE)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        fc = pyxel.frame_count

        # =====================================================================
        # 1. TOP PANORAMIC BACKDROP & TITLE
        # =====================================================================
        # Sky & Mountain Silhouette
        pyxel.rect(0, 0, SCREEN_WIDTH, 26, COLOR_NAVY)
        for my in range(14, 26):
            step = (my - 14) / 12.0
            for mx in range(SCREEN_WIDTH):
                if (mx + my) % 2 == 0 or (mx * 3 + my * 5) % 7 > int(step * 7):
                    pyxel.pset(mx, my, COLOR_DARK_BLUE)

        # Distant Spire Towers & Citadel Peaks
        pyxel.tri(188, 14, 194, 2, 200, 14, COLOR_BLACK)
        pyxel.tri(204, 14, 212, 0, 220, 14, COLOR_BLACK)
        pyxel.tri(222, 14, 230, 4, 238, 14, COLOR_BLACK)

        # Pale Moon at top right
        pyxel.circ(180, 8, 5, COLOR_PEACH)
        pyxel.circ(179, 7, 4, COLOR_WHITE)
        pyxel.pset(181, 6, COLOR_PEACH)

        # Ambient Pine Tree Silhouettes
        for tx in range(24, SCREEN_WIDTH - 24, 14):
            th = 6 + (tx % 5)
            pyxel.tri(tx, 18, tx + 4, 18 - th, tx + 8, 18, COLOR_BLACK)

        # Hanging Crimson Banners on Far Left & Right
        for bx in [8, SCREEN_WIDTH - 18]:
            pyxel.rect(bx, 0, 10, 22, COLOR_RED)
            pyxel.tri(bx, 22, bx + 5, 26, bx + 9, 22, COLOR_RED)
            pyxel.rectb(bx, 0, 10, 22, COLOR_ORANGE)
            pyxel.pset(bx + 4, 8, COLOR_YELLOW)
            pyxel.pset(bx + 5, 8, COLOR_YELLOW)
            pyxel.pset(bx + 4, 9, COLOR_YELLOW)
            pyxel.pset(bx + 5, 9, COLOR_YELLOW)

        # Flanking Wall Sconces with Animated Fire
        for tx, ty in [(3, 14), (SCREEN_WIDTH - 7, 14)]:
            pyxel.rect(tx, ty + 4, 4, 3, COLOR_BROWN)
            pyxel.rect(tx, ty, 4, 4, COLOR_ORANGE)
            pyxel.pset(tx + (1 if fc % 4 < 2 else 2), ty, COLOR_YELLOW)
            pyxel.pset(tx + 1, ty + 1, COLOR_WHITE)

        # Central Golden Title Frame
        title_text = t("choose_hero")
        tt_w = renderer.get_text_width(title_text)
        tb_w = tt_w + 24
        tb_x = SCREEN_WIDTH // 2 - tb_w // 2
        renderer.draw_box(tb_x, 3, tb_w, 18, bg_col=COLOR_BLACK, border_col=COLOR_YELLOW)
        pyxel.rectb(tb_x + 1, 4, tb_w - 2, 16, COLOR_ORANGE)
        renderer.draw_text(SCREEN_WIDTH // 2 - tt_w // 2, 8, title_text, COLOR_YELLOW)

        # =====================================================================
        # 2. THREE HERO SELECTION CARDS (y=28 to y=108)
        # =====================================================================
        card_w, card_h = 78, 80
        x_offsets = [6, 89, 172]
        card_y = 28

        from src.data.classes import CLASS_REGISTRY

        # Class weapon badge icons in Bank 0
        weapon_badges = {
            "warrior": (72, 0),   # Sword
            "rogue": (32, 16),    # Dagger
            "mage": (56, 16),     # Staff with orb
        }
        sprite_coords = {
            "warrior": (0, 0),
            "rogue": (0, 32),
            "mage": (16, 32),
        }

        pulse = (fc // 6) % 2

        for i, cls_id in enumerate(self.classes):
            card_x = x_offsets[i]
            is_selected = (i == self.selected_index)
            border_col = COLOR_YELLOW if is_selected else COLOR_LIGHT_BLUE
            fill_col = COLOR_DARK_BLUE if is_selected else COLOR_BLACK

            renderer.draw_box(card_x, card_y, card_w, card_h, bg_col=fill_col, border_col=border_col)

            # Selected Gold Studs & Double Border
            if is_selected:
                pyxel.rectb(card_x + 1, card_y + 1, card_w - 2, card_h - 2, COLOR_YELLOW if pulse == 0 else COLOR_ORANGE)
                # Corner accents
                pyxel.pset(card_x + 2, card_y + 2, COLOR_WHITE)
                pyxel.pset(card_x + card_w - 3, card_y + 2, COLOR_WHITE)
                pyxel.pset(card_x + 2, card_y + card_h - 3, COLOR_WHITE)
                pyxel.pset(card_x + card_w - 3, card_y + card_h - 3, COLOR_WHITE)

            # Top-Left Icon Badge Box (14x14)
            badge_x, badge_y = card_x + 4, card_y + 4
            pyxel.rect(badge_x, badge_y, 14, 14, COLOR_NAVY)
            pyxel.rectb(badge_x, badge_y, 14, 14, COLOR_LIGHT_BLUE if not is_selected else COLOR_YELLOW)
            wu, wv = weapon_badges.get(cls_id, (72, 0))
            pyxel.blt(badge_x + 3, badge_y + 3, 0, wu, wv, 8, 8, 0)

            # Class Name & Archetype
            cls_def = CLASS_REGISTRY[cls_id]
            renderer.draw_text(card_x + 22, card_y + 5, cls_def.localized_name, COLOR_YELLOW if is_selected else COLOR_WHITE)
            archetype = t(f"arch_{cls_id}")
            renderer.draw_text(card_x + 22, card_y + 13, archetype, COLOR_GRAY)

            # Stone Floor & Champion Cast Shadow
            floor_y = card_y + card_h - 14
            pyxel.line(card_x + 6, floor_y + 6, card_x + card_w - 7, floor_y + 6, COLOR_NAVY)
            pyxel.elli(card_x + card_w // 2 - 12, floor_y + 2, 24, 6, COLOR_NAVY)

            # Hero Sprite
            pu, pv = sprite_coords.get(cls_id, (0, 0))
            sprite_x = card_x + (card_w - 16) // 2
            sprite_y = card_y + 40
            pyxel.blt(sprite_x, sprite_y, 0, pu, pv, 16, 16, 0)

            # Drawn weapons/effects
            if cls_id == "warrior":
                pyxel.line(sprite_x + 14, sprite_y + 6, sprite_x + 21, sprite_y - 1, COLOR_CYAN)
                pyxel.line(sprite_x + 15, sprite_y + 6, sprite_x + 22, sprite_y - 1, COLOR_WHITE)
            elif cls_id == "rogue":
                pyxel.line(sprite_x - 3, sprite_y + 11, sprite_x + 1, sprite_y + 7, COLOR_WHITE)
                pyxel.line(sprite_x + 15, sprite_y + 7, sprite_x + 19, sprite_y + 11, COLOR_WHITE)
            elif cls_id == "mage":
                pyxel.line(sprite_x + 13, sprite_y + 14, sprite_x + 19, sprite_y + 2, COLOR_BROWN)
                pyxel.circ(sprite_x + 19, sprite_y + 2, 2, COLOR_CYAN)
                pyxel.pset(sprite_x + 19, sprite_y + 2, COLOR_WHITE)
                if (fc // 6) % 2 == 0:
                    pyxel.pset(sprite_x + 23, sprite_y + 5, COLOR_CYAN)
                    pyxel.pset(sprite_x - 4, sprite_y + 10, COLOR_CYAN)

        # =====================================================================
        # 3. DUAL-CHAMBER DETAIL PANEL (y=112 to y=222)
        # =====================================================================
        panel_x, panel_y, panel_w, panel_h = 6, 112, SCREEN_WIDTH - 12, 110
        renderer.draw_box(panel_x, panel_y, panel_w, panel_h, bg_col=COLOR_DARK_BLUE, border_col=COLOR_LIGHT_BLUE)
        pyxel.rectb(panel_x + 1, panel_y + 1, panel_w - 2, panel_h - 2, COLOR_NAVY)

        sel_cls_id = self.classes[self.selected_index]
        sel_cls_def = CLASS_REGISTRY[sel_cls_id]

        # --- LEFT ALCOVE: Stone Chamber with Hero Standing ---
        alcove_w = 58
        pyxel.rect(panel_x + 2, panel_y + 2, alcove_w, panel_h - 4, COLOR_NAVY)
        # Masonry stone lines
        for ay in range(panel_y + 6, panel_y + panel_h - 10, 8):
            pyxel.line(panel_x + 2, ay, panel_x + 1 + alcove_w, ay, COLOR_DARK_BLUE)
            offset = 4 if (ay // 8) % 2 == 0 else alcove_w // 2
            pyxel.pset(panel_x + 2 + offset, ay + 4, COLOR_GRAY)

        # Hanging Crimson Wall Banner in Alcove
        hbx, hby = panel_x + 6, panel_y + 6
        pyxel.rect(hbx, hby, 12, 24, COLOR_RED)
        pyxel.tri(hbx, hby + 24, hbx + 6, hby + 30, hbx + 11, hby + 24, COLOR_RED)
        pyxel.rectb(hbx, hby, 12, 24, COLOR_ORANGE)
        pyxel.pset(hbx + 5, hby + 10, COLOR_YELLOW)
        pyxel.pset(hbx + 6, hby + 10, COLOR_YELLOW)

        # Stone Pedestal & Shadow
        ped_x = panel_x + 14
        ped_y = panel_y + panel_h - 22
        pyxel.elli(ped_x, ped_y + 10, 32, 8, COLOR_BLACK)

        # Selected Hero Sprite in Alcove
        pu, pv = sprite_coords.get(sel_cls_id, (0, 0))
        hx = ped_x + 8
        hy = ped_y - 4
        pyxel.blt(hx, hy, 0, pu, pv, 16, 16, 0)

        if sel_cls_id == "warrior":
            pyxel.line(hx + 14, hy + 6, hx + 21, hy - 1, COLOR_CYAN)
            pyxel.line(hx + 15, hy + 6, hx + 22, hy - 1, COLOR_WHITE)
        elif sel_cls_id == "rogue":
            pyxel.line(hx - 3, hy + 11, hx + 1, hy + 7, COLOR_WHITE)
            pyxel.line(hx + 15, hy + 7, hx + 19, hy + 11, COLOR_WHITE)
        elif sel_cls_id == "mage":
            pyxel.line(hx + 13, hy + 14, hx + 19, hy + 2, COLOR_BROWN)
            pyxel.circ(hx + 19, hy + 2, 2, COLOR_CYAN)
            pyxel.pset(hx + 19, hy + 2, COLOR_WHITE)

        # Vertical Divider Line
        div_x = panel_x + alcove_w + 3
        pyxel.line(div_x, panel_y + 4, div_x, panel_y + panel_h - 5, COLOR_LIGHT_BLUE)

        # --- RIGHT DETAILS: Name, Description, Stats & Skills ---
        content_x = div_x + 6

        # Class Name & Description
        renderer.draw_text(content_x, panel_y + 6, sel_cls_def.localized_name, COLOR_YELLOW)
        for i, line in enumerate(renderer.wrap_text(sel_cls_def.localized_description, max_chars_per_line=36)):
            renderer.draw_text(content_x, panel_y + 16 + (i * 9), line, COLOR_WHITE)

        # --- ATTRIBUTES (Left sub-column) ---
        stat_x = content_x
        stats = sel_cls_def.base_stats
        growth = sel_cls_def.growth_per_level

        # HP
        self._draw_stat_icon(stat_x, panel_y + 36, "hp")
        renderer.draw_text(stat_x + 8, panel_y + 36, f"HP:  {stats.max_hp} (+{growth.max_hp}/lvl)", COLOR_WHITE)

        # ATK
        self._draw_stat_icon(stat_x, panel_y + 46, "atk")
        renderer.draw_text(stat_x + 8, panel_y + 46, f"ATK: {stats.attack} (+{growth.attack})", COLOR_WHITE)

        # DEF
        self._draw_stat_icon(stat_x, panel_y + 56, "def")
        renderer.draw_text(stat_x + 8, panel_y + 56, f"DEF: {stats.defense} (+{growth.defense})", COLOR_WHITE)

        # SPD
        self._draw_stat_icon(stat_x, panel_y + 66, "spd")
        renderer.draw_text(stat_x + 8, panel_y + 66, f"SPD: {stats.speed} (+{growth.speed})", COLOR_WHITE)

        # CRIT
        self._draw_stat_icon(stat_x, panel_y + 76, "crit")
        crit_pct = int(stats.crit_chance * 100)
        renderer.draw_text(stat_x + 8, panel_y + 76, f"CRIT: {crit_pct}%", COLOR_WHITE)

        # Vertical Sub-divider
        sub_div_x = stat_x + 94
        pyxel.line(sub_div_x, panel_y + 34, sub_div_x, panel_y + 86, COLOR_NAVY)

        # --- STARTING SKILL (Right sub-column) ---
        skill_x = sub_div_x + 6
        from src.systems.abilities import get_ability_by_id
        starting_skill_id = sel_cls_def.starting_abilities[0] if sel_cls_def.starting_abilities else "None"
        skill = get_ability_by_id(starting_skill_id)

        if skill:
            renderer.draw_text(skill_x, panel_y + 36, f"Skill: {skill.localized_name}", COLOR_CYAN)

            # Skill Thumbnail Frame (14x14)
            sbox_x, sbox_y = skill_x, panel_y + 47
            pyxel.rect(sbox_x, sbox_y, 14, 14, COLOR_NAVY)
            pyxel.rectb(sbox_x, sbox_y, 14, 14, COLOR_LIGHT_BLUE)
            self._draw_skill_glyph(sbox_x + 1, sbox_y + 1, skill.id)

            # Skill Description
            s_lines = renderer.wrap_text(skill.localized_description, max_chars_per_line=13)
            for si, sline in enumerate(s_lines[:3]):
                renderer.draw_text(sbox_x + 18, sbox_y + (si * 9), sline, COLOR_WHITE)

        # Best For / Promotions Footer Line
        promos_str = ", ".join(t(f"class_{p}_name") for p in sel_cls_def.promotions)
        promo_label = f"Promociones: {promos_str}" if i18n.locale == "es" else f"Best for: {promos_str}"
        renderer.draw_text(content_x, panel_y + panel_h - 13, promo_label, COLOR_PEACH)

        # =====================================================================
        # 4. BOTTOM ACTION CONTROL BAR (y=228 to y=248)
        # =====================================================================
        # Back Button with Left Arrow
        renderer.draw_button(6, 228, 58, 18, "◄ [ BACK ]" if i18n.locale == "en" else "◄ [ VOLVER ]", bg_col=COLOR_BLACK, border_col=COLOR_GRAY, text_col=COLOR_WHITE)

        # Central Route Selection Toggle
        mode_label = t("route_fate") if self.route_mode == "FATE" else t("route_pathfinder")
        renderer.draw_button(70, 228, 96, 18, mode_label, bg_col=COLOR_BLACK, border_col=COLOR_DARK_BLUE, text_col=COLOR_YELLOW if self.route_mode == "PATHFINDER" else COLOR_WHITE)

        # Begin Journey Button with Golden Border and Play Triangle
        b_label = "► [ BEGIN ]" if i18n.locale == "en" else "► [ INICIAR ]"
        renderer.draw_button(172, 228, 78, 18, b_label, bg_col=COLOR_BLACK, border_col=COLOR_YELLOW, text_col=COLOR_YELLOW)


class WelcomeView(View):
    """Renders the high-atmosphere gothic fantasy title screen."""

    def update(self, game_state: GameState) -> None:
        from src.config import SND_CLICK
        if Renderer.is_clicked(6, 6, 44, 14) or pyxel.btnp(pyxel.KEY_L):
            i18n.toggle_language()
            pyxel.play(0, 3)
        elif pyxel.btnp(pyxel.KEY_1) or Renderer.is_clicked(36, 158, 184, 16):
            pyxel.play(0, SND_CLICK)
            game_state.switch_mode(GameMode.CLASS_SELECT)
        elif pyxel.btnp(pyxel.KEY_2) or Renderer.is_clicked(36, 178, 184, 16):
            pass
        elif pyxel.btnp(pyxel.KEY_3) or Renderer.is_clicked(36, 198, 184, 16):
            pyxel.play(0, 3)
            game_state.switch_mode(GameMode.CREDITS)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        w = SCREEN_WIDTH
        fc = pyxel.frame_count

        pyxel.rect(0, 0, w, 52, COLOR_NAVY)
        for y in range(52, 72):
            step = (y - 52) / 20.0
            for x in range(w):
                if (x + y) % 2 == 0 or (x * 3 + y * 7) % 5 > int(step * 5):
                    pyxel.pset(x, y, COLOR_NAVY)
                else:
                    pyxel.pset(x, y, COLOR_BLACK)

        pyxel.circ(38, 44, 8, COLOR_WHITE)
        pyxel.circ(41, 43, 7, COLOR_NAVY)

        stars = [(18, 38), (60, 46), (82, 36), (110, 42), (180, 40), (210, 48), (145, 50)]
        for idx, (sx, sy) in enumerate(stars):
            col = COLOR_WHITE if (fc + idx * 7) % 24 < 12 else COLOR_YELLOW
            pyxel.pset(sx, sy, col)

        pyxel.rect(48, 86, 160, 40, COLOR_NAVY)
        for wx in range(48, 208, 8):
            pyxel.rect(wx, 82, 4, 4, COLOR_NAVY)

        citadel_towers = [
            (62, 126, 18, 48, True, 18),
            (84, 126, 22, 60, True, 22),
            (110, 126, 36, 72, True, 26),
            (150, 126, 20, 56, True, 20),
            (174, 126, 18, 44, True, 16),
        ]
        for tx, ty, tw, th, has_spire, sh in citadel_towers:
            wall_top = ty - th
            pyxel.rect(tx, wall_top, tw, th, COLOR_DARK_BLUE)
            for my in range(wall_top + 4, ty, 6):
                pyxel.line(tx, my, tx + tw - 1, my, COLOR_NAVY)
                offset = 3 if (my // 6) % 2 == 0 else tw // 2
                pyxel.pset(tx + offset, my + 3, COLOR_GRAY)
            for cx in range(tx, tx + tw, 4):
                pyxel.rect(cx, wall_top - 3, 2, 3, COLOR_DARK_BLUE)
            if has_spire:
                spire_top = wall_top - sh - 3
                pyxel.tri(tx - 1, wall_top - 3, tx + tw // 2, spire_top, tx + tw + 1, wall_top - 3, COLOR_DARK_BLUE)
                pyxel.line(tx + tw // 2, spire_top - 3, tx + tw // 2, spire_top, COLOR_YELLOW)

        gw_x, gw_y = 124, 76
        pyxel.rect(gw_x, gw_y + 4, 8, 12, COLOR_YELLOW if (fc // 15) % 2 == 0 else COLOR_ORANGE)
        pyxel.tri(gw_x, gw_y + 4, gw_x + 4, gw_y, gw_x + 7, gw_y + 4, COLOR_YELLOW)
        pyxel.line(gw_x + 3, gw_y + 1, gw_x + 3, gw_y + 15, COLOR_DARK_BLUE)
        pyxel.line(gw_x + 4, gw_y + 1, gw_x + 4, gw_y + 15, COLOR_DARK_BLUE)
        pyxel.line(gw_x, gw_y + 8, gw_x + 7, gw_y + 8, COLOR_DARK_BLUE)

        pyxel.rect(70, 92, 2, 6, COLOR_ORANGE if (fc // 10) % 3 != 0 else COLOR_YELLOW)
        pyxel.rect(94, 82, 2, 7, COLOR_YELLOW if (fc // 10) % 2 == 0 else COLOR_ORANGE)
        pyxel.rect(159, 86, 2, 6, COLOR_ORANGE if (fc // 12) % 2 == 0 else COLOR_YELLOW)

        pyxel.rect(0, 52, 24, 74, COLOR_DARK_BLUE)
        for py in range(52, 126, 6):
            pyxel.line(0, py, 23, py, COLOR_NAVY)
            stagger = 4 if (py // 6) % 2 == 0 else 14
            pyxel.pset(stagger, py + 3, COLOR_GRAY)
        pyxel.line(24, 52, 24, 126, COLOR_BLACK)
        pyxel.rect(18, 92, 3, 2, COLOR_BROWN)
        pyxel.pset(19, 90, COLOR_ORANGE if (fc % 4 < 2) else COLOR_YELLOW)
        pyxel.blt(0, 22, 1, 168, 0, 24, 32, 0)

        pyxel.rect(w - 24, 52, 24, 74, COLOR_DARK_BLUE)
        for py in range(52, 126, 6):
            pyxel.line(w - 24, py, w, py, COLOR_NAVY)
            stagger = 4 if (py // 6) % 2 == 0 else 14
            pyxel.pset(w - 24 + stagger, py + 3, COLOR_GRAY)
        pyxel.line(w - 25, 52, w - 25, 126, COLOR_BLACK)
        pyxel.rect(w - 21, 92, 3, 2, COLOR_BROWN)
        pyxel.pset(w - 20, 90, COLOR_YELLOW if (fc % 4 < 2) else COLOR_ORANGE)
        pyxel.blt(w - 24, 22, 1, 168, 0, -24, 32, 0)

        pyxel.rect(16, 126, w - 32, 20, COLOR_BROWN)
        pyxel.line(16, 126, w - 16, 126, COLOR_PEACH)
        for rx in range(18, w - 18, 8):
            pyxel.pset(rx, 127, COLOR_BROWN)
            if rx % 16 == 0:
                pyxel.line(rx, 128, rx + 2, 134, COLOR_BLACK)

        fire_x, fire_y = 114, 118
        pyxel.rect(fire_x - 3, fire_y + 7, 14, 2, COLOR_GRAY)
        pyxel.rect(fire_x - 1, fire_y + 8, 10, 1, COLOR_DARK_BLUE)
        for ox in range(-12, 13):
            dist = abs(ox)
            if dist < 6:
                pyxel.pset(fire_x + 4 + ox, 126, COLOR_YELLOW)
            elif dist < 11:
                pyxel.pset(fire_x + 4 + ox, 126, COLOR_ORANGE if (fc + ox) % 2 == 0 else COLOR_PEACH)

        pyxel.blt(fire_x, fire_y, 0, 88, 0, 8, 8, 0)
        for i in range(3):
            px = fire_x + 3 + ((fc * 2 + i * 5) % 5) - 2
            py = fire_y - ((fc + i * 7) % 10)
            pyxel.pset(px, py, COLOR_YELLOW if i % 2 == 0 else COLOR_ORANGE)

        pyxel.blt(76, 110, 0, 0, 0, 16, 16, 0)
        pyxel.line(90, 116, 100, 106, COLOR_CYAN)
        pyxel.line(91, 116, 101, 106, COLOR_WHITE)
        pyxel.blt(148, 98, 1, 144, 0, 24, 28, 0)

        pyxel.blt(56, 8, 1, 0, 0, 144, 32, 0)

        box_x, box_y, box_w, box_h = 36, 148, 184, 78
        renderer.draw_box(box_x, box_y, box_w, box_h, bg_col=COLOR_NAVY, border_col=COLOR_WHITE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_YELLOW)

        pyxel.blt(box_x - 3, box_y - 3, 1, 192, 0, 8, 8, 0)
        pyxel.blt(box_x + box_w - 5, box_y - 3, 1, 192, 0, 8, 8, 0)
        pyxel.blt(box_x - 3, box_y + box_h - 5, 1, 192, 0, 8, 8, 0)
        pyxel.blt(box_x + box_w - 5, box_y + box_h - 5, 1, 192, 0, 8, 8, 0)

        cursor_pulse = (fc // 6 % 2) * 2
        pyxel.blt(48 + cursor_pulse, 162, 1, 200, 0, 8, 8, 0)

        renderer.draw_button(46, 158, 164, 16, t("menu_new_game"), bg_col=COLOR_NAVY)
        renderer.draw_button(46, 178, 164, 16, t("menu_load_game"), bg_col=COLOR_NAVY, text_col=COLOR_GRAY)
        renderer.draw_button(46, 198, 164, 16, t("menu_credits"), bg_col=COLOR_NAVY, text_col=COLOR_WHITE)

        if (fc // 15) % 2 == 0:
            prompt = t("menu_prompt")
            renderer.draw_text(w // 2 - len(prompt) * 2, 236, prompt, COLOR_LIME)

        renderer.draw_button(
            6, 6, 44, 14,
            f"[{i18n.locale.upper()}]",
            bg_col=COLOR_NAVY,
            border_col=COLOR_WHITE,
            text_col=COLOR_YELLOW,
        )


class CreditsView(View):
    """Renders the game's credits screen."""

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_ESCAPE) or Renderer.is_clicked(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT):
            game_state.switch_mode(GameMode.WELCOME)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT

        renderer.draw_box(20, 60, w - 40, 120, bg_col=COLOR_NAVY, border_col=COLOR_YELLOW)
        renderer.draw_text(w // 2 - 20, 80, t("credits_title"), COLOR_YELLOW)
        renderer.draw_text(35, 110, t("credits_dev"), COLOR_WHITE)
        renderer.draw_text(35, 130, t("credits_ai"), COLOR_WHITE)

        renderer.draw_button(w // 2 - 50, 155, 100, 16, t("btn_back"), bg_col=COLOR_NAVY, text_col=COLOR_LIME)


class AbilityChoiceView(View):
    """Renders the ability selection screen featuring gothic chamber scenery, custom ability icons, and gold card frames."""

    def __init__(self) -> None:
        self.choices: list[Ability] = []
        self.pending_rarity: str = ""
        self.replace_mode = False
        self.selected_ability: Ability | None = None

    def _init_choices(self, game_state: GameState) -> None:
        if not game_state.player.pending_ability_choices:
            return

        self.pending_rarity = game_state.player.pending_ability_choices[0]
        rarity_enum = AbilityRarity.STANDARD if self.pending_rarity == "STANDARD" else AbilityRarity.EPIC
        known = [a.id for a in game_state.player.abilities.active + game_state.player.abilities.passive]
        self.choices = get_random_abilities(
            rarity_enum,
            known,
            player_class=game_state.player.class_id,
            count=2,
        )

    def update(self, game_state: GameState) -> None:
        if not self.choices and game_state.player.pending_ability_choices:
            self._init_choices(game_state)

        card_w, card_h = 216, 48
        card_x = 20
        card1_y = 90
        card2_y = 146
        skip_x, skip_y, skip_w, skip_h = SCREEN_WIDTH - 76, 226, 66, 18

        if self.replace_mode and self.selected_ability:
            if pyxel.btnp(pyxel.KEY_1) or pyxel.btnp(pyxel.KEY_KP_1) or Renderer.is_clicked(card_x, card1_y, card_w, card_h):
                game_state.player.abilities.replace_ability(self.selected_ability, 0)
                self._finish_choice(game_state)
            elif pyxel.btnp(pyxel.KEY_2) or pyxel.btnp(pyxel.KEY_KP_2) or Renderer.is_clicked(card_x, card2_y, card_w, card_h):
                game_state.player.abilities.replace_ability(self.selected_ability, 1)
                self._finish_choice(game_state)
            elif pyxel.btnp(pyxel.KEY_ESCAPE) or Renderer.is_clicked(skip_x, skip_y, skip_w, skip_h):
                self.replace_mode = False
                self.selected_ability = None
            return

        if pyxel.btnp(pyxel.KEY_ESCAPE) or Renderer.is_clicked(skip_x, skip_y, skip_w, skip_h):
            self._finish_choice(game_state)
            return

        if (pyxel.btnp(pyxel.KEY_1) or pyxel.btnp(pyxel.KEY_KP_1) or Renderer.is_clicked(card_x, card1_y, card_w, card_h)) and len(self.choices) > 0:
            self._handle_selection(game_state, self.choices[0])
        elif (pyxel.btnp(pyxel.KEY_2) or pyxel.btnp(pyxel.KEY_KP_2) or Renderer.is_clicked(card_x, card2_y, card_w, card_h)) and len(self.choices) > 1:
            self._handle_selection(game_state, self.choices[1])

    def _handle_selection(self, game_state: GameState, chosen: Ability) -> None:
        added = game_state.player.abilities.add_ability(chosen)
        if added:
            self._finish_choice(game_state)
        else:
            self.replace_mode = True
            self.selected_ability = chosen

    def _finish_choice(self, game_state: GameState) -> None:
        game_state.player.pending_ability_choices.pop(0)
        self.choices = []
        self.replace_mode = False
        self.selected_ability = None

        if game_state.player.pending_ability_choices:
            self._init_choices(game_state)
        else:
            current_node = game_state.map_graph.current_node
            if current_node and current_node.node_type == NodeType.BOSS:
                if game_state.act < 3:
                    game_state.act += 1
                    game_state.floor = 1
                    if game_state.biome_route_mode == "PATHFINDER":
                        game_state.switch_mode(GameMode.BIOME_SELECT)
                    else:
                        game_state.advance_act()
                else:
                    game_state.switch_mode(GameMode.VICTORY)
            else:
                game_state.switch_mode(GameMode.MAP)

    def _draw_ability_icon(self, x: int, y: int, ability_id: str) -> None:
        """Render distinct thematic pixel art inside the ability card thumbnail frame."""
        fc = pyxel.frame_count
        cx, cy = x + 16, y + 16
        aid = ability_id.lower()

        if "flurry" in aid or "fan" in aid:
            # Throwing blade with cyan speed slashes and particle sparkles
            pyxel.line(cx - 6, cy + 8, cx + 7, cy - 5, COLOR_WHITE)
            pyxel.line(cx - 5, cy + 9, cx + 8, cy - 4, COLOR_LIGHT_BLUE)
            pyxel.pset(cx + 8, cy - 5, COLOR_WHITE)
            # 3 Motion swoosh trails
            pyxel.line(cx - 10, cy - 3, cx - 2, cy - 3, COLOR_CYAN)
            pyxel.line(cx - 11, cy + 2, cx - 4, cy + 2, COLOR_CYAN)
            pyxel.line(cx - 7, cy + 7, cx + 1, cy + 7, COLOR_CYAN)
            if (fc // 6) % 2 == 0:
                pyxel.pset(cx + 10, cy - 8, COLOR_CYAN)
                pyxel.pset(cx + 4, cy + 8, COLOR_WHITE)

        elif "poison" in aid:
            # Stylized skull with glowing cyan/green eyes and bubbling poison motes
            pyxel.rect(cx - 6, cy - 6, 12, 10, COLOR_WHITE)
            pyxel.rect(cx - 4, cy + 4, 8, 4, COLOR_WHITE)
            # Eyes and nose cavity
            pyxel.rect(cx - 4, cy - 2, 3, 4, COLOR_LIME)
            pyxel.rect(cx + 2, cy - 2, 3, 4, COLOR_LIME)
            pyxel.pset(cx - 3, cy - 1, COLOR_BLACK)
            pyxel.pset(cx + 3, cy - 1, COLOR_BLACK)
            pyxel.pset(cx, cy + 2, COLOR_BLACK)
            # Teeth vertical lines
            pyxel.line(cx - 2, cy + 5, cx - 2, cy + 7, COLOR_BLACK)
            pyxel.line(cx, cy + 5, cx, cy + 7, COLOR_BLACK)
            pyxel.line(cx + 2, cy + 5, cx + 2, cy + 7, COLOR_BLACK)
            # Bubbling poison spores
            motes = [(cx - 9, cy - 7), (cx + 8, cy - 8), (cx - 10, cy + 3), (cx + 9, cy + 4)]
            for mi, (mx, my) in enumerate(motes):
                if (fc + mi * 5) % 16 < 10:
                    pyxel.pset(mx, my, COLOR_LIME if mi % 2 == 0 else COLOR_CYAN)

        elif any(k in aid for k in ("cross_cut", "cleave", "blade_storm")):
            # Dual crossed blades with brilliant white impact slashes
            pyxel.line(cx - 8, cy - 8, cx + 8, cy + 8, COLOR_WHITE)
            pyxel.line(cx + 8, cy - 8, cx - 8, cy + 8, COLOR_WHITE)
            pyxel.line(cx - 7, cy - 8, cx + 8, cy + 7, COLOR_CYAN)
            pyxel.line(cx + 7, cy - 8, cx - 8, cy + 7, COLOR_CYAN)
            pyxel.pset(cx, cy, COLOR_WHITE)
            pyxel.circb(cx, cy, 6, COLOR_LIGHT_BLUE)

        elif any(k in aid for k in ("shadow", "assassinate", "smoke")):
            # Dark violet dagger surrounded by swirling shadow vapor
            pyxel.circ(cx, cy, 7, COLOR_NAVY)
            pyxel.circb(cx, cy, 7, COLOR_PURPLE)
            pyxel.line(cx - 5, cy + 7, cx + 7, cy - 5, COLOR_WHITE)
            pyxel.pset(cx + 8, cy - 6, COLOR_PINK)
            if fc % 4 < 2:
                pyxel.pset(cx - 8, cy - 4, COLOR_PURPLE)
                pyxel.pset(cx + 8, cy + 5, COLOR_PURPLE)

        elif any(k in aid for k in ("fireball", "pyromania", "meteor")):
            # Blazing fireball with swirling flame trails
            pyxel.circ(cx, cy, 6, COLOR_RED)
            pyxel.circ(cx, cy, 4, COLOR_ORANGE)
            pyxel.circ(cx, cy, 2, COLOR_YELLOW)
            pyxel.pset(cx, cy, COLOR_WHITE)
            pyxel.pset(cx - 7, cy - 4, COLOR_YELLOW)
            pyxel.pset(cx + 7, cy + 4, COLOR_ORANGE)

        elif "frost" in aid:
            # Crystalline cyan snowflake with radiating arms
            pyxel.line(cx - 7, cy, cx + 7, cy, COLOR_CYAN)
            pyxel.line(cx, cy - 7, cx, cy + 7, COLOR_CYAN)
            pyxel.line(cx - 5, cy - 5, cx + 5, cy + 5, COLOR_LIGHT_BLUE)
            pyxel.line(cx + 5, cy - 5, cx - 5, cy + 5, COLOR_LIGHT_BLUE)
            pyxel.pset(cx, cy, COLOR_WHITE)

        elif "lightning" in aid:
            # Yellow zig-zag electric arc
            pyxel.line(cx + 2, cy - 8, cx - 3, cy, COLOR_YELLOW)
            pyxel.line(cx - 3, cy, cx + 4, cy, COLOR_YELLOW)
            pyxel.line(cx + 4, cy, cx - 2, cy + 8, COLOR_YELLOW)
            pyxel.line(cx + 3, cy - 7, cx - 2, cy + 1, COLOR_WHITE)
            pyxel.pset(cx + 6, cy - 2, COLOR_CYAN)
            pyxel.pset(cx - 6, cy + 3, COLOR_CYAN)

        elif any(k in aid for k in ("shield", "iron_skin", "barrier", "ward", "colossus", "undying")):
            # Steel kite shield with kinetic deflection barrier
            pyxel.rect(cx - 5, cy - 6, 11, 7, COLOR_CYAN)
            pyxel.tri(cx - 5, cy + 1, cx, cy + 8, cx + 5, cy + 1, COLOR_CYAN)
            pyxel.rect(cx - 3, cy - 4, 7, 5, COLOR_LIGHT_BLUE)
            pyxel.pset(cx, cy - 1, COLOR_WHITE)
            pyxel.line(cx - 8, cy - 2, cx - 8, cy + 3, COLOR_WHITE)
            pyxel.line(cx + 8, cy - 2, cx + 8, cy + 3, COLOR_WHITE)

        elif any(k in aid for k in ("time", "stop", "dilation")):
            # Mystic hourglass with glowing sand
            pyxel.line(cx - 5, cy - 7, cx + 5, cy - 7, COLOR_YELLOW)
            pyxel.line(cx - 5, cy + 7, cx + 5, cy + 7, COLOR_YELLOW)
            pyxel.tri(cx - 4, cy - 6, cx + 4, cy - 6, cx, cy - 1, COLOR_CYAN)
            pyxel.tri(cx - 4, cy + 6, cx + 4, cy + 6, cx, cy + 1, COLOR_CYAN)
            pyxel.pset(cx, cy, COLOR_WHITE)

        else:
            # Radiant magic gem / star burst
            pyxel.circ(cx, cy, 5, COLOR_NAVY)
            pyxel.circb(cx, cy, 5, COLOR_CYAN)
            pyxel.pset(cx, cy, COLOR_WHITE)
            pyxel.pset(cx - 3, cy, COLOR_LIGHT_BLUE)
            pyxel.pset(cx + 3, cy, COLOR_LIGHT_BLUE)
            pyxel.pset(cx, cy - 3, COLOR_LIGHT_BLUE)
            pyxel.pset(cx, cy + 3, COLOR_LIGHT_BLUE)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        box_x, box_y, box_w, box_h = 4, 25, SCREEN_WIDTH - 8, SCREEN_HEIGHT - 28
        fc = pyxel.frame_count

        # =====================================================================
        # 1. GOTHIC CHAMBER BACKDROP & TORCHES
        # =====================================================================
        pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

        # Masonry stone wall columns
        for px in [14, 46, SCREEN_WIDTH - 54, SCREEN_WIDTH - 22]:
            pyxel.rect(px, box_y + 2, 8, box_h - 14, COLOR_NAVY)
            for my in range(box_y + 6, box_y + box_h - 14, 8):
                pyxel.line(px, my, px + 7, my, COLOR_DARK_BLUE)
                pyxel.pset(px + ((my // 4) % 6), my + 3, COLOR_LIGHT_BLUE)

        # Central vaulted archway
        pyxel.rect(74, box_y + 8, 108, 48, COLOR_DARK_BLUE)
        pyxel.tri(74, box_y + 8, 128, box_y + 2, 181, box_y + 8, COLOR_DARK_BLUE)
        pyxel.rect(78, box_y + 12, 100, 44, COLOR_BLACK)
        pyxel.tri(78, box_y + 12, 128, box_y + 6, 177, box_y + 12, COLOR_BLACK)

        # Cobblestone ground at bottom
        ground_y = box_y + box_h - 14
        pyxel.rect(box_x + 2, ground_y, box_w - 4, 12, COLOR_DARK_BLUE)
        for gx in range(box_x + 6, box_x + box_w - 8, 12):
            pyxel.line(gx, ground_y + 3, gx + 6, ground_y + 3, COLOR_NAVY)
            pyxel.line(gx + 6, ground_y + 8, gx + 11, ground_y + 8, COLOR_NAVY)

        # Four Animated Wall Torches (2 Left, 2 Right)
        torch_positions = [
            (12, 48),                      # Upper Left
            (12, 172),                     # Lower Left
            (SCREEN_WIDTH - 16, 48),       # Upper Right
            (SCREEN_WIDTH - 16, 172),      # Lower Right
        ]
        for t_idx, (tx, ty) in enumerate(torch_positions):
            pyxel.rect(tx - 1, ty + 6, 4, 3, COLOR_BROWN)
            pyxel.rect(tx - 1, ty + 2, 4, 4, COLOR_ORANGE)
            pyxel.pset(tx + (1 if (fc + t_idx) % 4 < 2 else 0), ty, COLOR_YELLOW)
            pyxel.pset(tx + 1, ty + 1, COLOR_WHITE)
            if (fc + t_idx * 3) % 3 == 0:
                pyxel.pset(tx + ((fc // 2) % 3) - 1, ty - 2, COLOR_YELLOW)

        # Hanging Crimson Banners on Left & Right
        for bx in [26, SCREEN_WIDTH - 36]:
            pyxel.rect(bx, box_y + 4, 10, 20, COLOR_RED)
            pyxel.tri(bx, box_y + 24, bx + 5, box_y + 28, bx + 9, box_y + 24, COLOR_RED)
            pyxel.rectb(bx, box_y + 4, 10, 20, COLOR_ORANGE)
            pyxel.pset(bx + 4, box_y + 11, COLOR_YELLOW)
            pyxel.pset(bx + 5, box_y + 11, COLOR_YELLOW)

        # Outer Gothic Room Double Border
        pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_DARK_BLUE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_NAVY)

        # Decorative Corner Crosses
        for corner_x, corner_y in [
            (box_x + 1, box_y + 1),
            (box_x + box_w - 2, box_y + 1),
            (box_x + 1, box_y + box_h - 2),
            (box_x + box_w - 2, box_y + box_h - 2),
        ]:
            pyxel.pset(corner_x, corner_y, COLOR_LIGHT_BLUE)
            pyxel.pset(corner_x - 1, corner_y, COLOR_DARK_BLUE)
            pyxel.pset(corner_x + 1, corner_y, COLOR_DARK_BLUE)
            pyxel.pset(corner_x, corner_y - 1, COLOR_DARK_BLUE)
            pyxel.pset(corner_x, corner_y + 1, COLOR_DARK_BLUE)

        # =====================================================================
        # 2. HEADER BANNER PLAQUE (LEVEL UP! / ABILITY CHOICE)
        # =====================================================================
        bw, bh = 154, 26
        bx = SCREEN_WIDTH // 2 - bw // 2
        by = box_y + 4

        renderer.draw_box(bx, by, bw, bh, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE)
        pyxel.rectb(bx + 1, by + 1, bw - 2, bh - 2, COLOR_NAVY)

        # Corner Brackets on Plaque
        pyxel.line(bx + 3, by + 3, bx + 7, by + 3, COLOR_LIGHT_BLUE)
        pyxel.line(bx + 3, by + 3, bx + 3, by + 7, COLOR_LIGHT_BLUE)
        pyxel.line(bx + bw - 4, by + 3, bx + bw - 8, by + 3, COLOR_LIGHT_BLUE)
        pyxel.line(bx + bw - 4, by + 3, bx + bw - 4, by + 7, COLOR_LIGHT_BLUE)

        # Star Sparkles flanking the title
        sparkles = [
            (bx + 10, by + 8), (bx + 18, by + 14),
            (bx + bw - 12, by + 8), (bx + bw - 20, by + 14)
        ]
        for sx, sy in sparkles:
            pyxel.pset(sx, sy, COLOR_WHITE)
            pyxel.pset(sx - 1, sy, COLOR_YELLOW)
            pyxel.pset(sx + 1, sy, COLOR_YELLOW)
            pyxel.pset(sx, sy - 1, COLOR_YELLOW)
            pyxel.pset(sx, sy + 1, COLOR_YELLOW)

        if self.replace_mode and self.selected_ability:
            v_title = "REPLACE ABILITY" if i18n.locale == "en" else "REEMPLAZAR"
            sub_title = f"New: {self.selected_ability.localized_name}" if i18n.locale == "en" else f"Nueva: {self.selected_ability.localized_name}"
            renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(v_title) // 2, by + 5, v_title, COLOR_YELLOW)
            renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(sub_title) // 2, by + 15, sub_title, COLOR_LIME)
        else:
            v_title = "LEVEL UP!" if i18n.locale == "en" else "¡SUBIDA DE NIVEL!"
            rarity_label = "STANDARD ABILITY CHOICE" if self.pending_rarity == "STANDARD" else "EPIC ABILITY CHOICE"
            if i18n.locale == "es":
                rarity_label = "ELECCIÓN ESTÁNDAR" if self.pending_rarity == "STANDARD" else "ELECCIÓN ÉPICA"

            renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(v_title) // 2, by + 5, v_title, COLOR_YELLOW)
            renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(rarity_label) // 2, by + 15, rarity_label, COLOR_WHITE)

        # =====================================================================
        # 3. ABILITY SELECTION CARDS
        # =====================================================================
        card_w, card_h = 216, 48
        card_x = 20
        card1_y = 90
        card2_y = 146

        # Determine cards to display based on mode
        if self.replace_mode and self.selected_ability:
            target_list = game_state.player.abilities.active if self.selected_ability.ability_type == AbilityType.ACTIVE else game_state.player.abilities.passive
            cards_to_draw = target_list[:2]
        else:
            cards_to_draw = self.choices[:2]

        pulse = (fc // 6) % 2

        for i, ab in enumerate(cards_to_draw):
            cy = card1_y if i == 0 else card2_y
            is_active_card = (i == 0)

            # Card Box Border (Gold double border with corner studs on Card 1, Cyan on Card 2)
            border_col = COLOR_YELLOW if is_active_card else COLOR_LIGHT_BLUE
            fill_col = COLOR_DARK_BLUE if is_active_card else COLOR_BLACK
            renderer.draw_box(card_x, cy, card_w, card_h, bg_col=fill_col, border_col=border_col)

            if is_active_card:
                pyxel.rectb(card_x + 1, cy + 1, card_w - 2, card_h - 2, COLOR_YELLOW if pulse == 0 else COLOR_ORANGE)
                # Corner Studs
                pyxel.pset(card_x + 2, cy + 2, COLOR_WHITE)
                pyxel.pset(card_x + card_w - 3, cy + 2, COLOR_WHITE)
                pyxel.pset(card_x + 2, cy + card_h - 3, COLOR_WHITE)
                pyxel.pset(card_x + card_w - 3, cy + card_h - 3, COLOR_WHITE)
                # Active Selection Pointer Indicator (▶)
                pyxel.tri(card_x - 7, cy + 20, card_x - 7, cy + 28, card_x - 3, cy + 24, COLOR_YELLOW)

            # Left 32x32 Thumbnail Frame
            icon_x = card_x + 6
            icon_y = cy + 5
            pyxel.rect(icon_x, icon_y, 32, 38, COLOR_NAVY)
            pyxel.rectb(icon_x, icon_y, 32, 38, COLOR_LIGHT_BLUE if not is_active_card else COLOR_YELLOW)
            self._draw_ability_icon(icon_x, icon_y, ab.id)

            # Ability Name & Active/Passive Tag
            text_x = icon_x + 38
            slot_num = i + 1
            name_text = f"[{slot_num}] {ab.localized_name}"
            renderer.draw_text(text_x, cy + 7, name_text, COLOR_YELLOW if is_active_card else COLOR_WHITE)

            type_badge = f"({ab.localized_type.upper()})"
            type_x = text_x + renderer.get_text_width(name_text) + 6
            type_col = COLOR_CYAN if ab.ability_type == AbilityType.ACTIVE else COLOR_LIME
            renderer.draw_text(type_x, cy + 7, type_badge, type_col)

            # Formatted Ability Description
            desc_lines = renderer.wrap_text(ab.localized_description, max_chars_per_line=27)
            for l_idx, line in enumerate(desc_lines[:3]):
                renderer.draw_text(text_x, cy + 19 + l_idx * 9, line, COLOR_WHITE)

        # =====================================================================
        # 4. BOTTOM ACTION CONTROL BAR
        # =====================================================================
        if self.replace_mode:
            instr_text = t("replace_ability_instruction")
            skip_label = t("btn_cancel")
        else:
            instr_text = t("select_ability_instruction")
            skip_label = t("btn_skip")

        renderer.draw_text(16, 234, instr_text, COLOR_WHITE)
        renderer.draw_button(SCREEN_WIDTH - 76, 226, 66, 18, skip_label, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE, text_col=COLOR_PEACH)

class ShopView(View):
    """Interactive Merchant Shop View featuring cozy shopkeeper stall, dual-tab catalog, and inspector panel."""

    def __init__(self) -> None:
        self.active_tab: str = "BUY"
        self.buy_cursor: int = 0
        self.sell_cursor: int = 0
        self.feedback_msg: str = ""
        self.feedback_success: bool = False

    def _get_item_icon(self, item) -> tuple[int, int]:
        """Resolve 8x8 Bank 0 tile coordinates for any shop item."""
        iid = item.id.lower()
        if "potion" in iid:
            return (64, 0)
        elif "flask" in iid:
            return (64, 8)
        elif "elixir" in iid:
            return (72, 8)
        elif any(k in iid for k in ("sword", "broadsword", "claymore", "cleaver", "worldbreaker")):
            return (72, 0)
        elif any(k in iid for k in ("shield", "buckler", "bastion")):
            return (80, 0)
        elif any(k in iid for k in ("helmet", "cowl", "sallet", "cap", "coif", "visage", "diadem")):
            return (80, 8)
        elif any(k in iid for k in ("chestplate", "vest", "tunic", "robe", "cuirass", "harness", "carapace")):
            return (88, 8)
        elif any(k in iid for k in ("gloves", "mitts", "handwraps")):
            return (96, 8)
        elif any(k in iid for k in ("pants", "breeches", "greaves", "boots", "treads", "sabatons")):
            return (104, 8)
        elif any(k in iid for k in ("mantle", "capelet", "cloak")):
            return (0, 16)
        elif any(k in iid for k in ("pauldrons", "epaulets")):
            return (8, 16)
        elif any(k in iid for k in ("belt", "girdle", "sash")):
            return (16, 16)
        elif any(k in iid for k in ("dagger", "dirk", "stiletto", "sai", "fang")):
            return (32, 16)
        elif any(k in iid for k in ("wand",)):
            return (40, 16)
        elif any(k in iid for k in ("grimoire", "skull", "scroll", "notice")):
            return (48, 16)
        elif any(k in iid for k in ("staff", "spire")):
            return (56, 16)
        return (96, 0)

    def _get_inspected_item(self, game_state: GameState):
        """Retrieve the item currently highlighted by the active cursor."""
        if self.active_tab == "BUY":
            stock = game_state.merchant_stock
            if stock and 0 <= self.buy_cursor < len(stock):
                item, price = stock[self.buy_cursor]
                return item, price, True
        else:
            pouch = game_state.player.inventory.pouch
            if pouch and 0 <= self.sell_cursor < len(pouch):
                item = pouch[self.sell_cursor]
                sell_val = max(5, item.gold_value // 2)
                return item, sell_val, False
        return None, 0, False

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.KEY_SPACE) or Renderer.is_clicked(176, 227, 72, 18):
            game_state.switch_mode(GameMode.MAP)
            return

        # Tab Switching: [TAB] key or direct clicks
        if pyxel.btnp(pyxel.KEY_TAB) or Renderer.is_clicked(7, 89, 28, 13):
            self.active_tab = "SELL" if self.active_tab == "BUY" else "BUY"
            self.feedback_msg = ""
            pyxel.play(0, 3)
            return
        elif Renderer.is_clicked(38, 89, 36, 13):
            self.active_tab = "BUY"
            self.feedback_msg = ""
            pyxel.play(0, 3)
            return
        elif Renderer.is_clicked(76, 89, 36, 13):
            self.active_tab = "SELL"
            self.feedback_msg = ""
            pyxel.play(0, 3)
            return

        up = pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W)
        down = pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btnp(pyxel.KEY_S)

        # ---------------------------------------------------------------------
        # BUY TAB LOGIC
        # ---------------------------------------------------------------------
        if self.active_tab == "BUY":
            stock = game_state.merchant_stock
            scroll_offset = max(0, min(self.buy_cursor - 2, max(0, len(stock) - 5)))
            visible_count = min(5, len(stock) - scroll_offset)

            buy_triggered = pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_B) or Renderer.is_clicked(7, 227, 72, 18)

            # Click selection on catalog items
            for vi in range(visible_count):
                real_idx = scroll_offset + vi
                ry = 106 + vi * 23
                if Renderer.is_clicked(9, ry, 133, 21):
                    if self.buy_cursor == real_idx:
                        buy_triggered = True
                    else:
                        self.buy_cursor = real_idx
                        self.feedback_msg = ""
                        buy_triggered = False
                    break

            if up:
                self.buy_cursor = max(0, self.buy_cursor - 1)
            elif down:
                self.buy_cursor = min(max(0, len(stock) - 1), self.buy_cursor + 1)

            if len(stock) > 0 and buy_triggered:
                if 0 <= self.buy_cursor < len(stock):
                    item, price = stock[self.buy_cursor]
                    if game_state.player.gold < price:
                        self.feedback_msg = t("shop_no_gold")
                        self.feedback_success = False
                    elif len(game_state.player.inventory.pouch) >= MAX_POUCH_SLOTS:
                        self.feedback_msg = t("msg_pouch_full")
                        self.feedback_success = False
                    else:
                        game_state.player.gold -= price
                        game_state.player.inventory.add_to_pouch(item)
                        stock.pop(self.buy_cursor)
                        pyxel.play(0, 3)
                        self.feedback_msg = t("shop_purchased", item=item.localized_name)
                        self.feedback_success = True
                        if self.buy_cursor >= len(stock):
                            self.buy_cursor = max(0, len(stock) - 1)

        # ---------------------------------------------------------------------
        # SELL TAB LOGIC
        # ---------------------------------------------------------------------
        elif self.active_tab == "SELL":
            pouch = game_state.player.inventory.pouch
            scroll_offset = max(0, min(self.sell_cursor - 2, max(0, len(pouch) - 5)))
            visible_count = min(5, len(pouch) - scroll_offset)

            sell_triggered = pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_S) or Renderer.is_clicked(7, 227, 72, 18)

            for vi in range(visible_count):
                real_idx = scroll_offset + vi
                ry = 106 + vi * 23
                if Renderer.is_clicked(9, ry, 133, 21):
                    if self.sell_cursor == real_idx:
                        sell_triggered = True
                    else:
                        self.sell_cursor = real_idx
                        self.feedback_msg = ""
                        sell_triggered = False
                    break

            if up:
                self.sell_cursor = max(0, self.sell_cursor - 1)
            elif down:
                self.sell_cursor = min(max(0, len(pouch) - 1), self.sell_cursor + 1)

            if len(pouch) > 0 and sell_triggered:
                if 0 <= self.sell_cursor < len(pouch):
                    item = pouch[self.sell_cursor]
                    sell_value = max(5, item.gold_value // 2)
                    popped = game_state.player.inventory.remove_from_pouch(self.sell_cursor)
                    if popped:
                        game_state.player.gold += sell_value
                        pyxel.play(0, 3)
                        self.feedback_msg = t("shop_sold", item=popped.localized_name, val=sell_value)
                        self.feedback_success = True
                        if self.sell_cursor >= len(game_state.player.inventory.pouch):
                            self.sell_cursor = max(0, len(game_state.player.inventory.pouch) - 1)

    def _draw_merchant_scene(self, vx: int, vy: int, vw: int, vh: int) -> None:
        """Render the atmospheric shopkeeper alcove with wall shelves, lantern, counter, and merchant."""
        fc = pyxel.frame_count

        # Wall masonry background
        pyxel.rect(vx, vy, vw, vh, COLOR_DARK_BLUE)
        for my in range(vy + 4, vy + 38, 8):
            pyxel.line(vx, my, vx + vw - 1, my, COLOR_NAVY)

        # Hanging wall shelves with potion bottles & scrolls
        pyxel.rect(vx + 34, vy + 6, 78, 2, COLOR_BROWN)
        pyxel.rect(vx + 38, vy + 20, 74, 2, COLOR_BROWN)

        # Top shelf wares (Flasks & Potions)
        shelf1_items = [
            (vx + 38, COLOR_RED), (vx + 48, COLOR_CYAN), (vx + 58, COLOR_PURPLE),
            (vx + 74, COLOR_LIME), (vx + 84, COLOR_YELLOW), (vx + 98, COLOR_WHITE)
        ]
        for sx, col in shelf1_items:
            pyxel.rect(sx, vy + 2, 4, 4, col)
            pyxel.pset(sx + 1, vy + 1, COLOR_BROWN)
            pyxel.pset(sx + 1, vy + 2, COLOR_WHITE)

        # Hanging Wall Lantern on Left
        lx, ly = vx + 10, vy + 8
        pyxel.line(lx + 3, vy + 1, lx + 3, ly, COLOR_BROWN)
        pyxel.rect(lx, ly, 7, 10, COLOR_BROWN)
        pyxel.rect(lx + 1, ly + 2, 5, 6, COLOR_ORANGE)
        pyxel.pset(lx + 2, ly + 4, COLOR_YELLOW if fc % 4 < 2 else COLOR_WHITE)
        pyxel.pset(lx + 4, ly + 5, COLOR_YELLOW)
        pyxel.rect(lx - 2, ly + 11, 11, 12, COLOR_BROWN)  # Wooden barrel below lantern

        # Wooden Shop Counter (y=38 to y=56)
        pyxel.rect(vx + 2, vy + 38, vw - 4, vh - 38, COLOR_BROWN)
        pyxel.line(vx + 2, vy + 38, vx + vw - 3, vy + 38, COLOR_PEACH)
        for bx in range(vx + 16, vx + vw - 10, 20):
            pyxel.line(bx, vy + 39, bx, vy + vh - 1, COLOR_BLACK)

        # Counter Wares (Candle, small chest, coin stacks)
        # Candle on left
        pyxel.rect(vx + 22, vy + 34, 3, 4, COLOR_WHITE)
        pyxel.pset(vx + 23, vy + 32, COLOR_YELLOW if fc % 4 < 2 else COLOR_ORANGE)
        # Small Chest on right
        pyxel.rect(vx + vw - 24, vy + 32, 12, 7, COLOR_BROWN)
        pyxel.rectb(vx + vw - 24, vy + 32, 12, 7, COLOR_ORANGE)
        pyxel.pset(vx + vw - 19, vy + 35, COLOR_YELLOW)
        # Gold Coin Stack
        pyxel.rect(vx + vw - 36, vy + 34, 8, 4, COLOR_YELLOW)
        pyxel.pset(vx + vw - 33, vy + 35, COLOR_ORANGE)

        # Hooded Merchant Sprite at Counter
        mx, my = vx + 52, vy + 24
        # Red/purple hood cloak drapery
        pyxel.tri(mx - 4, my + 14, mx + 8, my - 2, mx + 20, my + 14, COLOR_RED)
        pyxel.rectb(mx - 4, my + 14, 25, 4, COLOR_PURPLE)
        # Merchant Sprite from Bank 0: (32, 32)
        pyxel.blt(mx, my, 0, 32, 32, 16, 16, 0)
        # Glowing mysterious eyes under hood
        pyxel.pset(mx + 5, my + 6, COLOR_YELLOW)
        pyxel.pset(mx + 9, my + 6, COLOR_YELLOW)

        # Outer border around merchant stall window
        pyxel.rectb(vx, vy, vw, vh, COLOR_DARK_BLUE)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        box_x, box_y, box_w, box_h = 4, 25, SCREEN_WIDTH - 8, SCREEN_HEIGHT - 28
        fc = pyxel.frame_count
        pulse = (fc // 6) % 2

        # Outer background
        pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

        # =====================================================================
        # 1. TOP HEADER: COZY STALL & MERCHANT DIALOGUE (y=28..86)
        # =====================================================================
        # Left: Merchant Stall Window (117x58)
        self._draw_merchant_scene(7, 28, 117, 58)

        # Right: Wandering Merchant Dialogue Plaque (121x58)
        dia_x, dia_y, dia_w, dia_h = 127, 28, 121, 58
        renderer.draw_box(dia_x, dia_y, dia_w, dia_h, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE)
        pyxel.rectb(dia_x + 1, dia_y + 1, dia_w - 2, dia_h - 2, COLOR_NAVY)

        # Corner accents on dialogue box
        for cx, cy in [(dia_x + 2, dia_y + 2), (dia_x + dia_w - 3, dia_y + 2), (dia_x + 2, dia_y + dia_h - 3), (dia_x + dia_w - 3, dia_y + dia_h - 3)]:
            pyxel.pset(cx, cy, COLOR_LIGHT_BLUE)

        m_name = t("wandering_merchant")
        renderer.draw_text(dia_x + 6, dia_y + 6, m_name, COLOR_YELLOW)

        quote_text = t("merchant_quote")
        quote_lines = renderer.wrap_text(quote_text, max_chars_per_line=19)
        for qi, qline in enumerate(quote_lines[:4]):
            renderer.draw_text(dia_x + 6, dia_y + 18 + qi * 9, qline, COLOR_WHITE)

        # =====================================================================
        # 2. TAB SELECTION BAR (y=89..102)
        # =====================================================================
        # Shortcut badge: [TAB]
        pyxel.rect(7, 89, 28, 13, COLOR_NAVY)
        pyxel.rectb(7, 89, 28, 13, COLOR_GRAY)
        renderer.draw_text(10, 93, "[TAB]", COLOR_WHITE)

        # Buy Tab
        is_buy = (self.active_tab == "BUY")
        b_col = COLOR_YELLOW if is_buy else COLOR_WHITE
        b_bg = COLOR_DARK_BLUE if is_buy else COLOR_BLACK
        b_border = COLOR_YELLOW if is_buy else COLOR_LIGHT_BLUE
        pyxel.rect(38, 89, 36, 13, b_bg)
        pyxel.rectb(38, 89, 36, 13, b_border)
        renderer.draw_text(48, 93, t("btn_buy"), b_col)

        # Sell Tab
        is_sell = (self.active_tab == "SELL")
        s_col = COLOR_YELLOW if is_sell else COLOR_WHITE
        s_bg = COLOR_DARK_BLUE if is_sell else COLOR_BLACK
        s_border = COLOR_YELLOW if is_sell else COLOR_LIGHT_BLUE
        pyxel.rect(76, 89, 36, 13, s_bg)
        pyxel.rectb(76, 89, 36, 13, s_border)
        renderer.draw_text(86, 93, t("btn_sell"), s_col)

        # =====================================================================
        # 3. MAIN BODY COLUMNS (y=104..223, h=119)
        # =====================================================================
        # --- LEFT COLUMN: ITEM CATALOG (137x119) ---
        col_x, col_y, col_w, col_h = 7, 104, 137, 119
        renderer.draw_box(col_x, col_y, col_w, col_h, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE)
        pyxel.rectb(col_x + 1, col_y + 1, col_w - 2, col_h - 2, COLOR_NAVY)

        from src.systems.inventory import ConsumableItem, EquipmentItem
        from src.data.items import StatPotion

        if self.active_tab == "BUY":
            stock = game_state.merchant_stock
            curr_cursor = self.buy_cursor
            scroll_offset = max(0, min(curr_cursor - 2, max(0, len(stock) - 5)))
            visible_items = stock[scroll_offset:scroll_offset + 5]

            if not stock:
                renderer.draw_text(col_x + 10, col_y + 12, t("merchant_out_of_stock"), COLOR_GRAY)
            else:
                for vi, (item, price) in enumerate(visible_items):
                    real_idx = scroll_offset + vi
                    is_active = (real_idx == curr_cursor)
                    ry = col_y + 2 + vi * 23
                    rw = col_w - 4

                    # Card frame
                    card_bg = COLOR_DARK_BLUE if is_active else COLOR_BLACK
                    card_border = COLOR_YELLOW if is_active else COLOR_NAVY
                    pyxel.rect(col_x + 2, ry, rw, 22, card_bg)
                    pyxel.rectb(col_x + 2, ry, rw, 22, card_border)

                    if is_active:
                        if pulse == 0:
                            pyxel.rectb(col_x + 3, ry + 1, rw - 2, 20, COLOR_YELLOW)
                        # Pointer arrow
                        pyxel.tri(col_x + 3, ry + 7, col_x + 3, ry + 15, col_x + 7, ry + 11, COLOR_YELLOW)

                    # 16x16 Item Icon frame
                    ix = col_x + 9
                    iy = ry + 3
                    pyxel.rect(ix, iy, 16, 16, COLOR_NAVY)
                    pyxel.rectb(ix, iy, 16, 16, COLOR_LIGHT_BLUE if not is_active else COLOR_YELLOW)
                    iu, iv = self._get_item_icon(item)
                    pyxel.blt(ix + 4, iy + 4, 0, iu, iv, 8, 8, 0)

                    # Item Title & Subtitle
                    tx = col_x + 28
                    renderer.draw_text(tx, ry + 4, item.localized_name[:11], COLOR_YELLOW if is_active else COLOR_WHITE)

                    if isinstance(item, EquipmentItem):
                        slot_str = t(f"slot_{item.slot.name.lower()}")
                        renderer.draw_text(tx, ry + 12, f"[{slot_str[:10]}]", COLOR_GRAY)
                    elif isinstance(item, ConsumableItem):
                        renderer.draw_text(tx, ry + 12, f"Heals {item.heal_amount}" if i18n.locale == "en" else f"Cura {item.heal_amount}", COLOR_LIME)

                    # Gold Coin & Price
                    pyxel.blt(col_x + rw - 35, ry + 7, 0, 40, 24, 8, 8, 0)
                    renderer.draw_text(col_x + rw - 25, ry + 8, f"{price}G", COLOR_YELLOW)

        else:  # "SELL"
            pouch = game_state.player.inventory.pouch
            curr_cursor = self.sell_cursor
            scroll_offset = max(0, min(curr_cursor - 2, max(0, len(pouch) - 5)))
            visible_items = pouch[scroll_offset:scroll_offset + 5]

            if not pouch:
                renderer.draw_text(col_x + 10, col_y + 12, t("merchant_empty_pouch"), COLOR_GRAY)
            else:
                for vi, item in enumerate(visible_items):
                    real_idx = scroll_offset + vi
                    is_active = (real_idx == curr_cursor)
                    ry = col_y + 2 + vi * 23
                    rw = col_w - 4
                    sell_price = max(5, item.gold_value // 2)

                    card_bg = COLOR_DARK_BLUE if is_active else COLOR_BLACK
                    card_border = COLOR_YELLOW if is_active else COLOR_NAVY
                    pyxel.rect(col_x + 2, ry, rw, 22, card_bg)
                    pyxel.rectb(col_x + 2, ry, rw, 22, card_border)

                    if is_active:
                        if pulse == 0:
                            pyxel.rectb(col_x + 3, ry + 1, rw - 2, 20, COLOR_YELLOW)
                        pyxel.tri(col_x + 3, ry + 7, col_x + 3, ry + 15, col_x + 7, ry + 11, COLOR_YELLOW)

                    ix = col_x + 9
                    iy = ry + 3
                    pyxel.rect(ix, iy, 16, 16, COLOR_NAVY)
                    pyxel.rectb(ix, iy, 16, 16, COLOR_LIGHT_BLUE if not is_active else COLOR_YELLOW)
                    iu, iv = self._get_item_icon(item)
                    pyxel.blt(ix + 4, iy + 4, 0, iu, iv, 8, 8, 0)

                    tx = col_x + 28
                    renderer.draw_text(tx, ry + 4, item.localized_name[:11], COLOR_YELLOW if is_active else COLOR_WHITE)

                    if isinstance(item, EquipmentItem):
                        slot_str = t(f"slot_{item.slot.name.lower()}")
                        renderer.draw_text(tx, ry + 12, f"[{slot_str[:10]}]", COLOR_GRAY)
                    elif isinstance(item, ConsumableItem):
                        renderer.draw_text(tx, ry + 12, f"Heals {item.heal_amount}" if i18n.locale == "en" else f"Cura {item.heal_amount}", COLOR_LIME)

                    pyxel.blt(col_x + rw - 35, ry + 7, 0, 40, 24, 8, 8, 0)
                    renderer.draw_text(col_x + rw - 25, ry + 8, f"{sell_price}G", COLOR_YELLOW)

        # --- RIGHT COLUMN: ITEM INSPECTOR (101x119) ---
        ins_x, ins_y, ins_w, ins_h = 147, 104, 101, 119
        renderer.draw_box(ins_x, ins_y, ins_w, ins_h, bg_col=COLOR_DARK_BLUE, border_col=COLOR_LIGHT_BLUE)
        pyxel.rectb(ins_x + 1, ins_y + 1, ins_w - 2, ins_h - 2, COLOR_NAVY)

        inspected_item, item_cost, is_buying = self._get_inspected_item(game_state)

        # 22x22 Icon Showcase
        fx, fy = ins_x + 5, ins_y + 5
        pyxel.rect(fx, fy, 22, 22, COLOR_NAVY)
        pyxel.rectb(fx, fy, 22, 22, COLOR_LIGHT_BLUE)

        if inspected_item:
            iu, iv = self._get_item_icon(inspected_item)
            pyxel.blt(fx + 7, fy + 7, 0, iu, iv, 8, 8, 0)

            renderer.draw_text(ins_x + 31, ins_y + 6, inspected_item.localized_name[:11], COLOR_YELLOW)
            type_label = t(f"slot_{inspected_item.slot.name.lower()}") if isinstance(inspected_item, EquipmentItem) else ("Consumable" if i18n.locale == "en" else "Consumible")
            renderer.draw_text(ins_x + 31, ins_y + 15, type_label[:11], COLOR_GRAY)
        else:
            pyxel.line(fx + 4, fy + 4, fx + 17, fy + 17, COLOR_NAVY)
            pyxel.line(fx + 17, fy + 4, fx + 4, fy + 17, COLOR_NAVY)
            renderer.draw_text(ins_x + 31, ins_y + 6, "No Item" if i18n.locale == "en" else "Sin Objeto", COLOR_GRAY)

        # Divider line
        pyxel.line(ins_x + 5, ins_y + 31, ins_x + ins_w - 6, ins_y + 31, COLOR_LIGHT_BLUE)

        # Lore description
        desc_y = ins_y + 35
        if inspected_item:
            d_lines = renderer.wrap_text(inspected_item.localized_description, max_chars_per_line=15)
            for dl in d_lines[:3]:
                renderer.draw_text(ins_x + 6, desc_y, dl, COLOR_WHITE)
                desc_y += 8
        else:
            renderer.draw_text(ins_x + 6, desc_y, "Select an item." if i18n.locale == "en" else "Elige un objeto.", COLOR_GRAY)
            desc_y += 16

        # Sub-divider
        pyxel.line(ins_x + 5, max(desc_y + 2, ins_y + 64), ins_x + ins_w - 6, max(desc_y + 2, ins_y + 64), COLOR_NAVY)

        # Stats / Effects
        stat_y = max(desc_y + 5, ins_y + 68)
        if isinstance(inspected_item, EquipmentItem):
            st = inspected_item.stats_bonus
            if st.attack > 0:
                renderer.draw_text(ins_x + 6, stat_y, f"ATK: +{st.attack}", COLOR_WHITE); stat_y += 8
            if st.defense > 0:
                renderer.draw_text(ins_x + 6, stat_y, f"DEF: +{st.defense}", COLOR_WHITE); stat_y += 8
            if st.speed != 0:
                renderer.draw_text(ins_x + 6, stat_y, f"SPD: {st.speed:+d}", COLOR_WHITE); stat_y += 8
            if st.max_hp > 0:
                renderer.draw_text(ins_x + 6, stat_y, f"HP : +{st.max_hp}", COLOR_WHITE); stat_y += 8
        elif isinstance(inspected_item, ConsumableItem):
            if inspected_item.heal_amount > 0:
                renderer.draw_text(ins_x + 6, stat_y, f"Heals {inspected_item.heal_amount} HP", COLOR_LIME); stat_y += 8
            if isinstance(inspected_item, StatPotion):
                b = inspected_item.stat_bonus
                if b.attack > 0: renderer.draw_text(ins_x + 6, stat_y, f"+{b.attack} ATK (Perm)", COLOR_LIME); stat_y += 8
                elif b.defense > 0: renderer.draw_text(ins_x + 6, stat_y, f"+{b.defense} DEF (Perm)", COLOR_LIME); stat_y += 8
                elif b.speed > 0: renderer.draw_text(ins_x + 6, stat_y, f"+{b.speed} SPD (Perm)", COLOR_LIME); stat_y += 8
                elif b.max_hp > 0: renderer.draw_text(ins_x + 6, stat_y, f"+{b.max_hp} HP (Perm)", COLOR_LIME); stat_y += 8

        # Bottom Price line
        if inspected_item:
            pyxel.blt(ins_x + 6, ins_y + ins_h - 14, 0, 40, 24, 8, 8, 0)
            price_tag = f"Price: {item_cost}G" if is_buying else f"Value: {item_cost}G"
            if i18n.locale == "es":
                price_tag = f"Precio: {item_cost}G" if is_buying else f"Valor: {item_cost}G"
            renderer.draw_text(ins_x + 16, ins_y + ins_h - 13, price_tag, COLOR_YELLOW)

        # =====================================================================
        # 4. BOTTOM ACTION CONTROL BAR (y=226..246)
        # =====================================================================
        # Toast message
        if self.feedback_msg:
            msg_col = COLOR_LIME if self.feedback_success else COLOR_RED
            renderer.draw_text(10, 224, self.feedback_msg, msg_col)

        # Buy / Sell Button
        action_btn_w = 72
        action_btn_x = 7
        action_btn_y = 227
        action_label = "[ BUY ]" if is_buy else "[ SELL ]"
        if i18n.locale == "es":
            action_label = "[ COMPRAR ]" if is_buy else "[ VENDER ]"

        renderer.draw_box(action_btn_x, action_btn_y, action_btn_w, 18, bg_col=COLOR_BLACK, border_col=COLOR_YELLOW)
        pyxel.blt(action_btn_x + 4, action_btn_y + 5, 0, 104, 0, 8, 8, 0)  # Shop sack icon
        renderer.draw_text(action_btn_x + 14, action_btn_y + 6, action_label, COLOR_YELLOW)

        # Switch Mode Indicator
        switch_prompt = "[TAB] Switch to Sell" if is_buy else "[TAB] Switch to Buy"
        if i18n.locale == "es":
            switch_prompt = "[TAB] Ver Vender" if is_buy else "[TAB] Ver Comprar"
        renderer.draw_text(85, 233, switch_prompt, COLOR_GRAY)

        # Leave Shop Button
        leave_btn_w = 72
        leave_btn_x = 176
        leave_btn_y = 227
        leave_label = "[ LEAVE ]" if i18n.locale == "en" else "[ SALIR ]"

        renderer.draw_box(leave_btn_x, leave_btn_y, leave_btn_w, 18, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE)
        # Door icon
        pyxel.rect(leave_btn_x + 5, leave_btn_y + 4, 6, 10, COLOR_LIGHT_BLUE)
        pyxel.rect(leave_btn_x + 6, leave_btn_y + 5, 4, 8, COLOR_NAVY)
        pyxel.pset(leave_btn_x + 8, leave_btn_y + 9, COLOR_YELLOW)
        renderer.draw_text(leave_btn_x + 14, leave_btn_y + 6, leave_label, COLOR_WHITE)

        # Outer Gothic Room Double Border
        pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_DARK_BLUE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_NAVY)

        # Decorative Corner Crosses
        for corner_x, corner_y in [
            (box_x + 1, box_y + 1),
            (box_x + box_w - 2, box_y + 1),
            (box_x + 1, box_y + box_h - 2),
            (box_x + box_w - 2, box_y + box_h - 2),
        ]:
            pyxel.pset(corner_x, corner_y, COLOR_LIGHT_BLUE)
            pyxel.pset(corner_x - 1, corner_y, COLOR_DARK_BLUE)
            pyxel.pset(corner_x + 1, corner_y, COLOR_DARK_BLUE)
            pyxel.pset(corner_x, corner_y - 1, COLOR_DARK_BLUE)
            pyxel.pset(corner_x, corner_y + 1, COLOR_DARK_BLUE)

class LootView(View):
    """Renders the post-combat loot screen featuring gothic chest scenery, reward tallies, and item cards."""

    def update(self, game_state: GameState) -> None:
        total_items = len(game_state.pending_loot)

        # Dynamic row clicks based on item count
        row_spacing = 26 if total_items > 2 else 28
        start_y = 120 if total_items > 2 else 122

        for i in range(min(3, total_items)):
            card_y = start_y + i * row_spacing
            if Renderer.is_clicked(8, card_y, SCREEN_WIDTH - 16, 24):
                self._take_loot(game_state, i)
                return

        if (pyxel.btnp(pyxel.KEY_1) or pyxel.btnp(pyxel.KEY_KP_1)) and total_items > 0:
            self._take_loot(game_state, 0)
        elif (pyxel.btnp(pyxel.KEY_2) or pyxel.btnp(pyxel.KEY_KP_2)) and total_items > 1:
            self._take_loot(game_state, 1)
        elif (pyxel.btnp(pyxel.KEY_3) or pyxel.btnp(pyxel.KEY_KP_3)) and total_items > 2:
            self._take_loot(game_state, 2)
        elif pyxel.btnp(pyxel.KEY_SPACE) or Renderer.is_clicked(110, 228, 66, 18):
            for i in range(len(game_state.pending_loot) - 1, -1, -1):
                self._take_loot(game_state, i, play_sound=False)
            pyxel.play(0, 3)
        elif pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_C) or Renderer.is_clicked(180, 228, 68, 18):
            self._exit_loot(game_state)

    def _take_loot(self, game_state: GameState, index: int, play_sound: bool = True) -> None:
        if index >= len(game_state.pending_loot):
            return
        item = game_state.pending_loot[index]
        if game_state.player.inventory.add_to_pouch(item):
            game_state.pending_loot.pop(index)
            if play_sound:
                pyxel.play(0, 3)

    def _exit_loot(self, game_state: GameState) -> None:
        if game_state.player.pending_ability_choices:
            game_state.switch_mode(GameMode.ABILITY_CHOICE)
            return

        current_node = game_state.map_graph.current_node
        if current_node and current_node.node_type == NodeType.BOSS:
            if game_state.act < 3:
                game_state.act += 1
                game_state.floor = 1
                if game_state.biome_route_mode == "PATHFINDER":
                    game_state.switch_mode(GameMode.BIOME_SELECT)
                else:
                    game_state.advance_act()
            else:
                game_state.switch_mode(GameMode.VICTORY)
        else:
            game_state.switch_mode(GameMode.MAP)

    def _get_item_icon(self, item) -> tuple[int, int]:
        """Resolve 8x8 Bank 0 tile coordinates for any inventory item."""
        iid = item.id.lower()
        if "potion" in iid:
            return (64, 0)
        elif "flask" in iid:
            return (64, 8)
        elif "elixir" in iid:
            return (72, 8)
        elif any(k in iid for k in ("sword", "broadsword", "claymore", "cleaver", "worldbreaker")):
            return (72, 0)
        elif any(k in iid for k in ("shield", "buckler", "bastion")):
            return (80, 0)
        elif any(k in iid for k in ("helmet", "cowl", "sallet", "cap", "coif")):
            return (80, 8)
        elif any(k in iid for k in ("chestplate", "vest", "tunic", "robe", "cuirass", "harness", "carapace")):
            return (88, 8)
        elif any(k in iid for k in ("gloves", "mitts", "handwraps")):
            return (96, 8)
        elif any(k in iid for k in ("pants", "breeches", "greaves", "boots", "treads")):
            return (104, 8)
        elif any(k in iid for k in ("mantle", "capelet", "cloak")):
            return (0, 16)
        elif any(k in iid for k in ("pauldrons", "epaulets")):
            return (8, 16)
        elif any(k in iid for k in ("belt", "girdle", "sash")):
            return (16, 16)
        elif any(k in iid for k in ("dagger", "dirk", "stiletto", "sai", "fang")):
            return (32, 16)
        elif any(k in iid for k in ("wand",)):
            return (40, 16)
        elif any(k in iid for k in ("grimoire", "skull", "scroll")):
            return (48, 16)
        elif any(k in iid for k in ("staff", "spire")):
            return (56, 16)
        return (96, 0)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        box_x, box_y, box_w, box_h = 4, 25, SCREEN_WIDTH - 8, SCREEN_HEIGHT - 28
        fc = pyxel.frame_count

        # =====================================================================
        # 1. DUNGEON TREASURE ALCOVE BACKDROP
        # =====================================================================
        pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

        # Stone arch pillars in the background
        for px in [14, 46, SCREEN_WIDTH - 54, SCREEN_WIDTH - 22]:
            pyxel.rect(px, box_y + 2, 8, 56, COLOR_NAVY)
            for my in range(box_y + 6, box_y + 56, 8):
                pyxel.line(px, my, px + 7, my, COLOR_DARK_BLUE)
                pyxel.pset(px + ((my // 4) % 6), my + 3, COLOR_LIGHT_BLUE)

        # Vaulted central arch
        pyxel.rect(74, box_y + 8, 108, 48, COLOR_DARK_BLUE)
        pyxel.tri(74, box_y + 8, 128, box_y + 2, 181, box_y + 8, COLOR_DARK_BLUE)
        pyxel.rect(78, box_y + 12, 100, 44, COLOR_BLACK)
        pyxel.tri(78, box_y + 12, 128, box_y + 6, 177, box_y + 12, COLOR_BLACK)

        # Left Torch Sconce
        ltx, lty = 12, 38
        pyxel.rect(ltx - 1, lty + 6, 4, 3, COLOR_BROWN)
        pyxel.rect(ltx - 1, lty + 2, 4, 4, COLOR_ORANGE)
        pyxel.pset(ltx, lty + (1 if fc % 4 < 2 else 0), COLOR_YELLOW)
        pyxel.pset(ltx + 1, lty + 2, COLOR_WHITE)

        # Right Torch Sconce
        rtx, rty = SCREEN_WIDTH - 16, 38
        pyxel.rect(rtx - 1, rty + 6, 4, 3, COLOR_BROWN)
        pyxel.rect(rtx - 1, rty + 2, 4, 4, COLOR_ORANGE)
        pyxel.pset(rtx, rty + (0 if fc % 4 < 2 else 1), COLOR_YELLOW)
        pyxel.pset(rtx - 1, rty + 2, COLOR_WHITE)

        # Hanging Crimson Banners
        for bx in [28, SCREEN_WIDTH - 38]:
            pyxel.rect(bx, box_y + 4, 10, 20, COLOR_RED)
            pyxel.tri(bx, box_y + 24, bx + 5, box_y + 28, bx + 9, box_y + 24, COLOR_RED)
            pyxel.rectb(bx, box_y + 4, 10, 20, COLOR_ORANGE)
            pyxel.pset(bx + 4, box_y + 11, COLOR_YELLOW)
            pyxel.pset(bx + 5, box_y + 11, COLOR_YELLOW)

        # =====================================================================
        # 2. OPEN ORNATE TREASURE CHEST WITH GOLD & SPARKLES
        # =====================================================================
        cx, cy = 108, 60

        # Shadow beneath chest and gold piles
        pyxel.elli(cx - 16, cy + 18, 72, 8, COLOR_NAVY)

        # Open Lid (angled upward)
        pyxel.rect(cx - 2, cy - 8, 44, 12, COLOR_BROWN)
        pyxel.rectb(cx - 2, cy - 8, 44, 12, COLOR_ORANGE)
        pyxel.line(cx + 8, cy - 8, cx + 8, cy + 3, COLOR_YELLOW)
        pyxel.line(cx + 31, cy - 8, cx + 31, cy + 3, COLOR_YELLOW)
        pyxel.rect(cx + 2, cy - 5, 36, 7, COLOR_NAVY)

        # Chest Base Body
        pyxel.rect(cx, cy + 4, 40, 16, COLOR_BROWN)
        pyxel.rectb(cx, cy + 4, 40, 16, COLOR_ORANGE)
        pyxel.line(cx + 8, cy + 4, cx + 8, cy + 19, COLOR_YELLOW)
        pyxel.line(cx + 31, cy + 4, cx + 31, cy + 19, COLOR_YELLOW)

        # Golden Keyhole Lock
        pyxel.rect(cx + 18, cy + 8, 4, 5, COLOR_YELLOW)
        pyxel.pset(cx + 19, cy + 10, COLOR_BLACK)

        # Glowing Gold & Gems overflowing
        pyxel.rect(cx + 4, cy + 1, 32, 5, COLOR_YELLOW)
        pyxel.pset(cx + 8, cy + 2, COLOR_WHITE)
        pyxel.pset(cx + 14, cy + 3, COLOR_RED)    # Ruby
        pyxel.pset(cx + 21, cy + 2, COLOR_CYAN)   # Sapphire
        pyxel.pset(cx + 27, cy + 3, COLOR_LIME)   # Emerald

        # Embedded sword blade in gold pile
        pyxel.line(cx + 28, cy - 2, cx + 34, cy - 9, COLOR_WHITE)
        pyxel.line(cx + 29, cy - 3, cx + 35, cy - 8, COLOR_CYAN)
        pyxel.line(cx + 33, cy - 10, cx + 36, cy - 7, COLOR_YELLOW)

        # Overflowing gold coin piles on floor
        for coin_x, coin_y in [
            (cx - 14, cy + 14), (cx - 9, cy + 16), (cx - 4, cy + 15),
            (cx + 42, cy + 15), (cx + 48, cy + 17), (cx + 54, cy + 14),
            (cx - 8, cy + 12), (cx + 44, cy + 12), (cx + 16, cy + 19)
        ]:
            pyxel.rect(coin_x, coin_y, 4, 3, COLOR_YELLOW)
            pyxel.pset(coin_x + 1, coin_y + 1, COLOR_ORANGE)

        # Animated treasure sparkles
        sparkle_coords = [(cx - 8, cy - 4), (cx + 14, cy - 10), (cx + 48, cy - 2), (cx + 2, cy + 8), (cx + 50, cy + 10)]
        for s_idx, (sx, sy) in enumerate(sparkle_coords):
            if (fc + s_idx * 6) % 18 < 9:
                pyxel.pset(sx, sy, COLOR_WHITE)
                pyxel.pset(sx - 1, sy, COLOR_YELLOW)
                pyxel.pset(sx + 1, sy, COLOR_YELLOW)
                pyxel.pset(sx, sy - 1, COLOR_YELLOW)
                pyxel.pset(sx, sy + 1, COLOR_YELLOW)

        # =====================================================================
        # 3. HEADER BANNER PLAQUE (VICTORY! / Spoils of Battle)
        # =====================================================================
        bw, bh = 138, 22
        bx = SCREEN_WIDTH // 2 - bw // 2
        by = box_y + 3

        renderer.draw_box(bx, by, bw, bh, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE)
        pyxel.rectb(bx + 1, by + 1, bw - 2, bh - 2, COLOR_NAVY)

        # Diamond Star Accents on Plaque
        for star_x in [bx + 10, bx + bw - 12]:
            pyxel.pset(star_x, by + 10, COLOR_WHITE)
            pyxel.pset(star_x - 1, by + 10, COLOR_PEACH)
            pyxel.pset(star_x + 1, by + 10, COLOR_PEACH)
            pyxel.pset(star_x, by + 9, COLOR_PEACH)
            pyxel.pset(star_x, by + 11, COLOR_PEACH)

        v_title = "VICTORY!" if i18n.locale == "en" else "¡VICTORIA!"
        v_sub = "Spoils of Battle" if i18n.locale == "en" else "Botín de batalla"
        renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(v_title) // 2, by + 4, v_title, COLOR_YELLOW)
        renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(v_sub) // 2, by + 12, v_sub, COLOR_WHITE)

        # =====================================================================
        # 4. REWARDS SUMMARY STATUS PANEL (EXP, Gold, Pouch)
        # =====================================================================
        sum_x, sum_y, sum_w, sum_h = 8, 86, SCREEN_WIDTH - 16, 28
        renderer.draw_box(sum_x, sum_y, sum_w, sum_h, bg_col=COLOR_NAVY, border_col=COLOR_LIGHT_BLUE)

        col_w = sum_w // 3
        c1_x = sum_x + 6
        c2_x = sum_x + col_w + 6
        c3_x = sum_x + col_w * 2 + 6

        # Vertical Column Dividers
        pyxel.line(sum_x + col_w, sum_y + 3, sum_x + col_w, sum_y + sum_h - 4, COLOR_LIGHT_BLUE)
        pyxel.line(sum_x + col_w * 2, sum_y + 3, sum_x + col_w * 2, sum_y + sum_h - 4, COLOR_LIGHT_BLUE)

        # Column 1: EXP Gained
        pyxel.pset(c1_x + 2, sum_y + 4, COLOR_ORANGE)
        pyxel.line(c1_x, sum_y + 6, c1_x + 4, sum_y + 6, COLOR_ORANGE)
        pyxel.pset(c1_x + 2, sum_y + 8, COLOR_ORANGE)
        pyxel.pset(c1_x + 2, sum_y + 6, COLOR_YELLOW)
        renderer.draw_text(c1_x + 8, sum_y + 4, "EXP Gained:" if i18n.locale == "en" else "EXP Ganada:", COLOR_WHITE)
        renderer.draw_text(c1_x + 8, sum_y + 13, str(game_state.last_exp_earned), COLOR_WHITE)
        # Mini EXP progress bar
        renderer.draw_bar(c1_x + 8, sum_y + 21, 60, 3, game_state.player.experience, max(1, game_state.player.exp_to_next_level), fill_col=COLOR_CYAN, bg_col=COLOR_BLACK)

        # Column 2: Gold
        pyxel.blt(c2_x, sum_y + 5, 0, 40, 24, 8, 8, 0)
        renderer.draw_text(c2_x + 10, sum_y + 5, "Gold:" if i18n.locale == "en" else "Oro:", COLOR_WHITE)
        renderer.draw_text(c2_x + 10, sum_y + 15, str(game_state.last_gold_earned), COLOR_YELLOW)

        # Column 3: Pouch Space
        pyxel.blt(c3_x, sum_y + 5, 0, 104, 0, 8, 8, 0)
        pouch_len = len(game_state.player.inventory.pouch)
        from src.systems.inventory import MAX_POUCH_SLOTS
        is_full = (pouch_len >= MAX_POUCH_SLOTS)
        pouch_color = COLOR_RED if is_full else COLOR_LIME
        renderer.draw_text(c3_x + 10, sum_y + 5, "Pouch Space:" if i18n.locale == "en" else "Bolsa:", COLOR_WHITE)
        renderer.draw_text(c3_x + 10, sum_y + 15, f"{pouch_len}/{MAX_POUCH_SLOTS}", pouch_color)

        # =====================================================================
        # 5. PENDING LOOT ITEM CARDS
        # =====================================================================
        total_loot = len(game_state.pending_loot)
        start_loot_y = 120 if total_loot > 2 else 122
        card_spacing = 26 if total_loot > 2 else 28

        for i, item in enumerate(game_state.pending_loot[:3]):
            iy = start_loot_y + i * card_spacing
            card_box_w = SCREEN_WIDTH - 16
            is_active = (i == 0)

            renderer.draw_box(8, iy, card_box_w, 24, bg_col=COLOR_DARK_BLUE, border_col=COLOR_YELLOW if is_active else COLOR_LIGHT_BLUE)
            if is_active:
                pyxel.rectb(9, iy + 1, card_box_w - 2, 22, COLOR_NAVY)
                # Active selection arrow
                pyxel.tri(10, iy + 7, 10, iy + 15, 14, iy + 11, COLOR_YELLOW)

            # Icon Box (16x16)
            icon_x = 17
            pyxel.rect(icon_x, iy + 4, 16, 16, COLOR_NAVY)
            pyxel.rectb(icon_x, iy + 4, 16, 16, COLOR_LIGHT_BLUE if not is_active else COLOR_YELLOW)
            iu, iv = self._get_item_icon(item)
            pyxel.blt(icon_x + 4, iy + 8, 0, iu, iv, 8, 8, 0)

            # Main Item Details
            content_x = icon_x + 22
            renderer.draw_text(content_x, iy + 5, f"[{i+1}] {item.localized_name}", COLOR_WHITE if not is_active else COLOR_YELLOW)

            from src.systems.inventory import ConsumableItem, EquipmentItem
            from src.data.items import StatPotion

            if isinstance(item, EquipmentItem):
                renderer.draw_text(content_x, iy + 14, t(f"slot_{item.slot.name.lower()}"), COLOR_GRAY)

                # Vertical Divider inside card
                vdiv_x = 158
                pyxel.line(vdiv_x, iy + 3, vdiv_x, iy + 20, COLOR_NAVY)

                # Stat bonuses
                stat_parts = []
                if item.stats_bonus.attack > 0:
                    stat_parts.append(f"ATK +{item.stats_bonus.attack}")
                if item.stats_bonus.defense > 0:
                    stat_parts.append(f"DEF +{item.stats_bonus.defense}")
                if item.stats_bonus.speed > 0:
                    stat_parts.append(f"SPD +{item.stats_bonus.speed}")
                if item.stats_bonus.max_hp > 0:
                    stat_parts.append(f"HP +{item.stats_bonus.max_hp}")

                if len(stat_parts) >= 2:
                    renderer.draw_text(vdiv_x + 8, iy + 5, stat_parts[0], COLOR_WHITE)
                    renderer.draw_text(vdiv_x + 8, iy + 14, stat_parts[1], COLOR_WHITE)
                elif len(stat_parts) == 1:
                    renderer.draw_text(vdiv_x + 8, iy + 9, stat_parts[0], COLOR_WHITE)

            elif isinstance(item, ConsumableItem):
                type_label = t("spoils_perm_elixir") if isinstance(item, StatPotion) else t("spoils_consumable")
                renderer.draw_text(content_x, iy + 14, type_label, COLOR_GRAY)

                vdiv_x = 158
                pyxel.line(vdiv_x, iy + 3, vdiv_x, iy + 20, COLOR_NAVY)

                if isinstance(item, StatPotion):
                    b_str = ""
                    if item.stat_bonus.attack > 0:
                        b_str = f"ATK +{item.stat_bonus.attack}"
                    elif item.stat_bonus.defense > 0:
                        b_str = f"DEF +{item.stat_bonus.defense}"
                    elif item.stat_bonus.speed > 0:
                        b_str = f"SPD +{item.stat_bonus.speed}"
                    elif item.stat_bonus.max_hp > 0:
                        b_str = f"HP +{item.stat_bonus.max_hp}"
                    renderer.draw_text(vdiv_x + 8, iy + 9, b_str, COLOR_LIME)
                else:
                    renderer.draw_text(vdiv_x + 8, iy + 9, f"Heals {item.heal_amount} HP" if i18n.locale == "en" else f"Cura {item.heal_amount} PV", COLOR_LIME)

        if not game_state.pending_loot:
            renderer.draw_text(SCREEN_WIDTH // 2 - 40, start_loot_y + 12, t("spoils_no_items"), COLOR_GRAY)

        # =====================================================================
        # 6. BOTTOM ACTION BUTTON BAR
        # =====================================================================
        prompt_txt = "[1-3] Take Item" if i18n.locale == "en" else "[1-3] Tomar Objeto"
        renderer.draw_text(12, 234, prompt_txt, COLOR_WHITE)

        take_all_label = "[ TAKE ALL ]" if i18n.locale == "en" else "[ TOMAR TODO ]"
        cont_label = "[ CONTINUE ]" if i18n.locale == "en" else "[ CONTINUAR ]"

        renderer.draw_button(110, 228, 66, 18, take_all_label, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE, text_col=COLOR_YELLOW)
        renderer.draw_button(180, 228, 68, 18, cont_label, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE, text_col=COLOR_WHITE)

        # Outer Gothic Room Border
        pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_DARK_BLUE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_NAVY)

        # Decorative Corner Crosses
        for corner_x, corner_y in [
            (box_x + 1, box_y + 1),
            (box_x + box_w - 2, box_y + 1),
            (box_x + 1, box_y + box_h - 2),
            (box_x + box_w - 2, box_y + box_h - 2),
        ]:
            pyxel.pset(corner_x, corner_y, COLOR_LIGHT_BLUE)
            pyxel.pset(corner_x - 1, corner_y, COLOR_DARK_BLUE)
            pyxel.pset(corner_x + 1, corner_y, COLOR_DARK_BLUE)
            pyxel.pset(corner_x, corner_y - 1, COLOR_DARK_BLUE)
            pyxel.pset(corner_x, corner_y + 1, COLOR_DARK_BLUE)


class ViewManager:
    """Manages view selection and delegates update/render calls."""

    def __init__(self) -> None:
        self.views: dict[GameMode, View] = {
            GameMode.WELCOME: WelcomeView(),
            GameMode.CLASS_SELECT: ClassSelectView(),
            GameMode.CREDITS: CreditsView(),
            GameMode.BIOME_SELECT: BiomeSelectView(),
            GameMode.MAP: MapView(),
            GameMode.COMBAT: CombatView(),
            GameMode.INVENTORY: InventoryView(),
            GameMode.EVENTS: EventsView(),
            GameMode.GAME_OVER: EndGameView(is_victory=False),
            GameMode.VICTORY: EndGameView(is_victory=True),
            GameMode.ABILITY_CHOICE: AbilityChoiceView(),
            GameMode.LOOT: LootView(),
            GameMode.SHOP: ShopView(),
        }

    def update(self, game_state: GameState) -> None:
        if game_state.current_mode in (GameMode.MAP, GameMode.COMBAT, GameMode.EVENTS, GameMode.INVENTORY, GameMode.LOOT, GameMode.SHOP):
            inv_clicked = Renderer.is_clicked(222, 3, 30, 16)
            if pyxel.btnp(pyxel.KEY_I) or inv_clicked or (game_state.current_mode == GameMode.INVENTORY and pyxel.btnp(pyxel.KEY_ESCAPE)):
                game_state.toggle_inventory()
                return

        view = self.views.get(game_state.current_mode)
        if view:
            view.update(game_state)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        view = self.views.get(game_state.current_mode)
        if view:
            view.draw(game_state, renderer)