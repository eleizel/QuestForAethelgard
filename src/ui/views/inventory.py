"""View switching architecture including CombatView, MapView, and InventoryView."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyxel

from src.config import (
    COLOR_BLACK,
    COLOR_CYAN,
    COLOR_DARK_BLUE,
    COLOR_GRAY,
    COLOR_LIGHT_BLUE,
    COLOR_LIME,
    COLOR_NAVY,
    COLOR_PEACH,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
)
from src.core.i18n import i18n, t
from src.systems.inventory import MAX_BELT_SLOTS, MAX_POUCH_SLOTS, EquipSlot
from src.ui.renderer import Renderer
from src.ui.views.base import View

if TYPE_CHECKING:
    from src.core.game_state import GameState


# =============================================================================
# BIOME ENEMY SPRITE COORDINATE MAP (Bank 0)
# =============================================================================
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
            renderer.draw_text(ins_x + 32, ins_y + 7, "Empty Slot" if i18n.locale == "en" else "Ranura Vacía",
                               COLOR_GRAY)
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
            renderer.draw_text(ins_x + 8, desc_y,
                               "Select an item to view details." if i18n.locale == "en" else "Selecciona un objeto para ver detalles.",
                               COLOR_GRAY)

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

            renderer.draw_text(bx + 4, by + 3, f"[{b_idx + 1}]", COLOR_YELLOW if is_sel else COLOR_WHITE)

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
        renderer.draw_button(4, 230, 90, 18, e_label, bg_col=COLOR_BLACK, border_col=COLOR_YELLOW,
                             text_col=COLOR_YELLOW)

        renderer.draw_button(98, 230, 18, 18, "B1", bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE,
                             text_col=COLOR_WHITE)
        renderer.draw_button(119, 230, 18, 18, "B2", bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE,
                             text_col=COLOR_WHITE)
        renderer.draw_button(140, 230, 18, 18, "B3", bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE,
                             text_col=COLOR_WHITE)

        d_label = "↓ [ DROP ]" if i18n.locale == "en" else "↓ [ TIRAR ]"
        renderer.draw_button(162, 230, 44, 18, d_label, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE,
                             text_col=COLOR_PEACH)

        c_label = "✕ [ CLOSE ]" if i18n.locale == "en" else "✕ [ CERRAR ]"
        renderer.draw_button(210, 230, 42, 18, c_label, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE,
                             text_col=COLOR_WHITE)
