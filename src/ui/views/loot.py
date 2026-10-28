"""View switching architecture including CombatView, MapView, and InventoryView."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyxel

from src.config import (
    COLOR_BLACK,
    COLOR_BROWN,
    COLOR_CYAN,
    COLOR_DARK_BLUE,
    COLOR_GRAY,
    COLOR_LIGHT_BLUE,
    COLOR_LIME,
    COLOR_NAVY,
    COLOR_ORANGE,
    COLOR_PEACH,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    SCREEN_HEIGHT,
    SCREEN_WIDTH, SND_CLICK, SND_CHEST,
)
from src.core.audio import audio
from src.core.game_state import GameMode
from src.core.i18n import i18n, t
from src.systems.map_gen import NodeType
from src.ui.renderer import Renderer
from src.ui.views.base import View

if TYPE_CHECKING:
    from src.core.game_state import GameState


# =============================================================================
# BIOME ENEMY SPRITE COORDINATE MAP (Bank 0)
# =============================================================================
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
            audio.play_sfx(SND_CHEST)
        elif pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_C) or Renderer.is_clicked(180, 228, 68, 18):
            audio.play_sfx(SND_CLICK)
            self._exit_loot(game_state)

    def _take_loot(self, game_state: GameState, index: int, play_sound: bool = True) -> None:
        if index >= len(game_state.pending_loot):
            return
        item = game_state.pending_loot[index]
        if game_state.player.inventory.add_to_pouch(item):
            game_state.pending_loot.pop(index)
            if play_sound:
                audio.play_sfx(SND_CHEST)

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
        pyxel.pset(cx + 14, cy + 3, COLOR_RED)  # Ruby
        pyxel.pset(cx + 21, cy + 2, COLOR_CYAN)  # Sapphire
        pyxel.pset(cx + 27, cy + 3, COLOR_LIME)  # Emerald

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
        renderer.draw_bar(c1_x + 8, sum_y + 21, 60, 3, game_state.player.experience,
                          max(1, game_state.player.exp_to_next_level), fill_col=COLOR_CYAN, bg_col=COLOR_BLACK)

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

            renderer.draw_box(8, iy, card_box_w, 24, bg_col=COLOR_DARK_BLUE,
                              border_col=COLOR_YELLOW if is_active else COLOR_LIGHT_BLUE)
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
            renderer.draw_text(content_x, iy + 5, f"[{i + 1}] {item.localized_name}",
                               COLOR_WHITE if not is_active else COLOR_YELLOW)

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
                    renderer.draw_text(vdiv_x + 8, iy + 9,
                                       f"Heals {item.heal_amount} HP" if i18n.locale == "en" else f"Cura {item.heal_amount} PV",
                                       COLOR_LIME)

        if not game_state.pending_loot:
            renderer.draw_text(SCREEN_WIDTH // 2 - 40, start_loot_y + 12, t("spoils_no_items"), COLOR_GRAY)

        # =====================================================================
        # 6. BOTTOM ACTION BUTTON BAR
        # =====================================================================
        prompt_txt = "[1-3] Take Item" if i18n.locale == "en" else "[1-3] Tomar Objeto"
        renderer.draw_text(12, 234, prompt_txt, COLOR_WHITE)

        take_all_label = "[ TAKE ALL ]" if i18n.locale == "en" else "[ TOMAR TODO ]"
        cont_label = "[ CONTINUE ]" if i18n.locale == "en" else "[ CONTINUAR ]"

        renderer.draw_button(110, 228, 66, 18, take_all_label, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE,
                             text_col=COLOR_YELLOW)
        renderer.draw_button(180, 228, 68, 18, cont_label, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE,
                             text_col=COLOR_WHITE)

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
