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
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from src.core.game_state import GameMode
from src.core.i18n import i18n, t
from src.systems.inventory import MAX_POUCH_SLOTS
from src.ui.renderer import Renderer
from src.ui.views.base import View

if TYPE_CHECKING:
    from src.core.game_state import GameState


# =============================================================================
# BIOME ENEMY SPRITE COORDINATE MAP (Bank 0)
# =============================================================================
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

            buy_triggered = pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_B) or Renderer.is_clicked(7, 227, 72,
                                                                                                           18)

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

            sell_triggered = pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_S) or Renderer.is_clicked(7, 227, 72,
                                                                                                            18)

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
        for cx, cy in [(dia_x + 2, dia_y + 2), (dia_x + dia_w - 3, dia_y + 2), (dia_x + 2, dia_y + dia_h - 3),
                       (dia_x + dia_w - 3, dia_y + dia_h - 3)]:
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
                        renderer.draw_text(tx, ry + 12,
                                           f"Heals {item.heal_amount}" if i18n.locale == "en" else f"Cura {item.heal_amount}",
                                           COLOR_LIME)

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
                        renderer.draw_text(tx, ry + 12,
                                           f"Heals {item.heal_amount}" if i18n.locale == "en" else f"Cura {item.heal_amount}",
                                           COLOR_LIME)

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
            type_label = t(f"slot_{inspected_item.slot.name.lower()}") if isinstance(inspected_item,
                                                                                     EquipmentItem) else (
                "Consumable" if i18n.locale == "en" else "Consumible")
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
            renderer.draw_text(ins_x + 6, desc_y, "Select an item." if i18n.locale == "en" else "Elige un objeto.",
                               COLOR_GRAY)
            desc_y += 16

        # Sub-divider
        pyxel.line(ins_x + 5, max(desc_y + 2, ins_y + 64), ins_x + ins_w - 6, max(desc_y + 2, ins_y + 64), COLOR_NAVY)

        # Stats / Effects
        stat_y = max(desc_y + 5, ins_y + 68)
        if isinstance(inspected_item, EquipmentItem):
            st = inspected_item.stats_bonus
            if st.attack > 0:
                renderer.draw_text(ins_x + 6, stat_y, f"ATK: +{st.attack}", COLOR_WHITE);
                stat_y += 8
            if st.defense > 0:
                renderer.draw_text(ins_x + 6, stat_y, f"DEF: +{st.defense}", COLOR_WHITE);
                stat_y += 8
            if st.speed != 0:
                renderer.draw_text(ins_x + 6, stat_y, f"SPD: {st.speed:+d}", COLOR_WHITE);
                stat_y += 8
            if st.max_hp > 0:
                renderer.draw_text(ins_x + 6, stat_y, f"HP : +{st.max_hp}", COLOR_WHITE);
                stat_y += 8
        elif isinstance(inspected_item, ConsumableItem):
            if inspected_item.heal_amount > 0:
                renderer.draw_text(ins_x + 6, stat_y, f"Heals {inspected_item.heal_amount} HP", COLOR_LIME);
                stat_y += 8
            if isinstance(inspected_item, StatPotion):
                b = inspected_item.stat_bonus
                if b.attack > 0:
                    renderer.draw_text(ins_x + 6, stat_y, f"+{b.attack} ATK (Perm)", COLOR_LIME); stat_y += 8
                elif b.defense > 0:
                    renderer.draw_text(ins_x + 6, stat_y, f"+{b.defense} DEF (Perm)", COLOR_LIME); stat_y += 8
                elif b.speed > 0:
                    renderer.draw_text(ins_x + 6, stat_y, f"+{b.speed} SPD (Perm)", COLOR_LIME); stat_y += 8
                elif b.max_hp > 0:
                    renderer.draw_text(ins_x + 6, stat_y, f"+{b.max_hp} HP (Perm)", COLOR_LIME); stat_y += 8

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
