"""Pygame-CE 16-bit SNES Merchant & Barter Shop View.

Authentic Super Nintendo Golden Age RPG design:
- Biome/Apothecary room background with ambient vignette
- Reusable TopHUDComponent displaying champion stats, EXP, gold, and floor
- Dual-tab catalog: [ 1 ] BUY WARES vs [ 2 ] SELL GOODS with dynamic counts
- 16-bit item icons (SNES potions, Pyxel Bank 0 weapons/armors/trinkets)
- Full Item Inspector Panel displaying lore, stats, and real-time comparison deltas vs equipped gear
- Bottom action controls with live transaction feedback toast and audio cues
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame

from src.config import MAX_POUCH_SLOTS
from src.core.events import AudioCue, event_bus
from src.core.game_state import GameMode
from src.core.i18n import i18n, t
from src.core.theme import ThemeToken
from src.data.items import StatPotion
from src.entities.item import ConsumableItem, EquipmentItem
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.components.top_hud import TopHUDComponent
from src.frontends.pygame_ce.views.base import PygameView
from src.systems.shop_service import ShopService

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


TIER_COLORS: dict[int, tuple[int, int, int]] = {
    1: (220, 225, 235),  # Tier 1 Common
    2: (64, 215, 120),   # Tier 2 Uncommon
    3: (70, 160, 255),   # Tier 3 Rare
    4: (185, 95, 255),   # Tier 4 Epic
    5: (255, 185, 45),   # Tier 5 Legendary
}


class PygameShopView(PygameView):
    """Interactive merchant shop view featuring dual-tab catalog, inspector panel, and transaction feedback."""

    def __init__(self) -> None:
        self.top_hud = TopHUDComponent()
        self.active_tab: str = "BUY"  # "BUY" or "SELL"
        self.buy_cursor: int = 0
        self.sell_cursor: int = 0
        self.anim_timer: float = 0.0
        self.feedback_msg: str = ""
        self.feedback_success: bool = True
        self.feedback_timer: float = 0.0
        self._door_played: bool = False
        self._hovered_btn: str | None = None
        self._hovered_row: int | None = None

        # Display Rectangles (960x540 display)
        self.outer_rect = pygame.Rect(36, 52, 888, 476)
        self.header_rect = pygame.Rect(self.outer_rect.x + 16, 62, 530, 48)
        self.treasury_rect = pygame.Rect(self.outer_rect.x + 556, 62, 316, 48)

        # Tab Rectangles
        self.tab_buy_rect = pygame.Rect(self.outer_rect.x + 16, 116, 175, 34)
        self.tab_sell_rect = pygame.Rect(self.outer_rect.x + 198, 116, 175, 34)

        # Catalog and Inspector Rectangles
        self.catalog_rect = pygame.Rect(self.outer_rect.x + 16, 156, 498, 312)
        self.inspector_rect = pygame.Rect(self.outer_rect.x + 524, 156, 348, 312)

        # Bottom Action Control Bar
        self.action_btn_rect = pygame.Rect(self.outer_rect.x + 16, 476, 210, 42)
        self.leave_btn_rect = pygame.Rect(self.outer_rect.right - 186, 476, 170, 42)

    def _get_item_icon(self, item) -> pygame.Surface | None:
        """Resolve authentic icon for item: SNES potions or Pyxel retro equipment."""
        if isinstance(item, ConsumableItem):
            if isinstance(item, StatPotion) or getattr(item, "stat_bonus", None):
                return assets.get_item_icon("potion_mana", size=(28, 28))
            else:
                return assets.get_item_icon("potion_health", size=(28, 28))

        iid = item.id.lower()
        if any(k in iid for k in ("sword", "broadsword", "claymore", "cleaver", "worldbreaker", "blade")):
            coord = (72, 0)
        elif any(k in iid for k in ("shield", "buckler", "bastion")):
            coord = (80, 0)
        elif any(k in iid for k in ("helmet", "cowl", "sallet", "cap", "coif", "helm", "diadem", "visage")):
            coord = (80, 8)
        elif any(k in iid for k in ("chestplate", "vest", "tunic", "robe", "cuirass", "harness", "carapace", "armor")):
            coord = (88, 8)
        elif any(k in iid for k in ("gloves", "mitts", "handwraps", "gauntlets")):
            coord = (96, 8)
        elif any(k in iid for k in ("pants", "breeches", "greaves", "boots", "treads", "sabatons")):
            coord = (104, 8)
        elif any(k in iid for k in ("mantle", "capelet", "cloak")):
            coord = (0, 16)
        elif any(k in iid for k in ("pauldrons", "epaulets")):
            coord = (8, 16)
        elif any(k in iid for k in ("belt", "girdle", "sash")):
            coord = (16, 16)
        elif any(k in iid for k in ("dagger", "dirk", "stiletto", "sai", "fang")):
            coord = (32, 16)
        elif any(k in iid for k in ("wand",)):
            coord = (40, 16)
        elif any(k in iid for k in ("grimoire", "skull", "scroll")):
            coord = (48, 16)
        elif any(k in iid for k in ("staff", "spire")):
            coord = (56, 16)
        elif "ring" in iid:
            coord = (16, 16)
        elif "amulet" in iid or "talisman" in iid:
            coord = (24, 16)
        else:
            coord = (96, 0)

        return assets.get_pyxel_icon(coord[0], coord[1], size=(28, 28))

    def _get_inspected_item(self, session: GameSession):
        """Retrieve the item currently highlighted by the active cursor."""
        if self.active_tab == "BUY":
            stock = session.state.merchant_stock
            if stock and 0 <= self.buy_cursor < len(stock):
                entry = stock[self.buy_cursor]
                if isinstance(entry, tuple):
                    item, price = entry
                else:
                    item = entry
                    price = getattr(item, "cost", getattr(item, "gold_value", 10))
                return item, price, True
        else:
            pouch = session.player.inventory.pouch
            if pouch and 0 <= self.sell_cursor < len(pouch):
                item = pouch[self.sell_cursor]
                sell_val = ShopService.calculate_sell_price(item)
                return item, sell_val, False
        return None, 0, False

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Handle keyboard shortcuts and mouse clicks."""
        if self.top_hud.handle_event(event, session):
            return

        stock = session.state.merchant_stock
        pouch = session.player.inventory.pouch

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_q):
                self._exit_shop(session)
            elif event.key in (pygame.K_TAB,):
                self.active_tab = "SELL" if self.active_tab == "BUY" else "BUY"
                self.feedback_msg = ""
                event_bus.emit_audio(AudioCue.CLICK)
            elif event.key in (pygame.K_1, pygame.K_KP1):
                self.active_tab = "BUY"
                self.feedback_msg = ""
                event_bus.emit_audio(AudioCue.CLICK)
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self.active_tab = "SELL"
                self.feedback_msg = ""
                event_bus.emit_audio(AudioCue.CLICK)
            elif event.key in (pygame.K_UP, pygame.K_w):
                if self.active_tab == "BUY" and stock:
                    self.buy_cursor = max(0, self.buy_cursor - 1)
                elif self.active_tab == "SELL" and pouch:
                    self.sell_cursor = max(0, self.sell_cursor - 1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                if self.active_tab == "BUY" and stock:
                    self.buy_cursor = min(len(stock) - 1, self.buy_cursor + 1)
                elif self.active_tab == "SELL" and pouch:
                    self.sell_cursor = min(len(pouch) - 1, self.sell_cursor + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_b):
                if self.active_tab == "BUY":
                    self._execute_buy(session)
                else:
                    self._execute_sell(session)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # Tab clicks
            if self.tab_buy_rect.collidepoint(pos):
                self.active_tab = "BUY"
                self.feedback_msg = ""
                event_bus.emit_audio(AudioCue.CLICK)
                return
            elif self.tab_sell_rect.collidepoint(pos):
                self.active_tab = "SELL"
                self.feedback_msg = ""
                event_bus.emit_audio(AudioCue.CLICK)
                return

            # Action button
            if self.action_btn_rect.collidepoint(pos):
                if self.active_tab == "BUY":
                    self._execute_buy(session)
                else:
                    self._execute_sell(session)
                return

            # Leave button
            if self.leave_btn_rect.collidepoint(pos):
                self._exit_shop(session)
                return

            # Catalog row clicks
            items = stock if self.active_tab == "BUY" else pouch
            curr_cursor = self.buy_cursor if self.active_tab == "BUY" else self.sell_cursor
            scroll_offset = max(0, min(curr_cursor - 2, max(0, len(items) - 5)))
            visible_count = min(5, len(items) - scroll_offset)

            for vi in range(visible_count):
                real_idx = scroll_offset + vi
                row_y = self.catalog_rect.y + 12 + vi * 58
                row_rect = pygame.Rect(self.catalog_rect.x + 12, row_y, self.catalog_rect.width - 24, 52)
                if row_rect.collidepoint(pos):
                    if (self.active_tab == "BUY" and self.buy_cursor == real_idx) or (
                        self.active_tab == "SELL" and self.sell_cursor == real_idx
                    ):
                        # Double click triggers purchase/sale
                        if self.active_tab == "BUY":
                            self._execute_buy(session)
                        else:
                            self._execute_sell(session)
                    else:
                        if self.active_tab == "BUY":
                            self.buy_cursor = real_idx
                        else:
                            self.sell_cursor = real_idx
                        self.feedback_msg = ""
                        event_bus.emit_audio(AudioCue.CLICK)
                    return

    def _execute_buy(self, session: GameSession) -> None:
        """Attempt to buy the currently selected merchant item."""
        stock = session.state.merchant_stock
        if not stock or self.buy_cursor >= len(stock):
            return
        res = ShopService.buy_item(session.player, stock, self.buy_cursor)
        self.feedback_msg = res.message
        self.feedback_success = res.success
        self.feedback_timer = 4.0
        if res.success and self.buy_cursor >= len(stock):
            self.buy_cursor = max(0, len(stock) - 1)

    def _execute_sell(self, session: GameSession) -> None:
        """Attempt to sell the currently selected pouch item."""
        pouch = session.player.inventory.pouch
        if not pouch or self.sell_cursor >= len(pouch):
            return
        res = ShopService.sell_item(session.player, self.sell_cursor)
        self.feedback_msg = res.message
        self.feedback_success = res.success
        self.feedback_timer = 4.0
        if res.success and self.sell_cursor >= len(pouch):
            self.sell_cursor = max(0, len(pouch) - 1)

    def _exit_shop(self, session: GameSession) -> None:
        """Play click sound and return to map navigation."""
        event_bus.emit_audio(AudioCue.CLICK)
        session.switch_mode(GameMode.MAP)

    def update(self, dt: float, session: GameSession) -> None:
        """Update animation timer and hover coordinates."""
        self.anim_timer += dt
        if self.feedback_timer > 0:
            self.feedback_timer -= dt
            if self.feedback_timer <= 0:
                self.feedback_msg = ""

        pos = pygame.mouse.get_pos()
        self._hovered_btn = None
        if self.action_btn_rect.collidepoint(pos):
            self._hovered_btn = "action"
        elif self.leave_btn_rect.collidepoint(pos):
            self._hovered_btn = "leave"
        elif self.tab_buy_rect.collidepoint(pos):
            self._hovered_btn = "tab_buy"
        elif self.tab_sell_rect.collidepoint(pos):
            self._hovered_btn = "tab_sell"

        # Catalog row hover
        self._hovered_row = None
        stock = session.state.merchant_stock
        pouch = session.player.inventory.pouch
        items = stock if self.active_tab == "BUY" else pouch
        curr_cursor = self.buy_cursor if self.active_tab == "BUY" else self.sell_cursor
        scroll_offset = max(0, min(curr_cursor - 2, max(0, len(items) - 5)))
        visible_count = min(5, len(items) - scroll_offset)

        for vi in range(visible_count):
            row_y = self.catalog_rect.y + 12 + vi * 58
            row_rect = pygame.Rect(self.catalog_rect.x + 12, row_y, self.catalog_rect.width - 24, 52)
            if row_rect.collidepoint(pos):
                self._hovered_row = scroll_offset + vi
                break

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render 16-bit SNES Merchant Shop View with dual tabs, catalog, and inspector."""
        # 1. Background (shop apothecary room)
        assets.draw_background(surface, "shop", vignette_alpha=120)

        # 2. Top HUD Bar
        self.top_hud.draw(surface, renderer, session)

        # 3. Outer Ornate Golden Frame
        bg_surf = pygame.Surface((self.outer_rect.width - 12, self.outer_rect.height - 12), pygame.SRCALPHA)
        bg_surf.fill((14, 16, 26, 235))
        surface.blit(bg_surf, (self.outer_rect.x + 6, self.outer_rect.y + 6))

        assets.draw_frame(surface, "frame_gold_ornate_hollow", self.outer_rect, margin=54)

        # 4. Header Plaque & Treasury Status
        self._draw_header(surface, renderer, session)

        # 5. Dual Tabs Bar
        self._draw_tabs(surface, renderer, session)

        # 6. Main Catalog List (Left)
        self._draw_catalog(surface, renderer, session)

        # 7. Item Inspector Panel (Right)
        self._draw_inspector(surface, renderer, session)

        # 8. Bottom Action Control Bar
        self._draw_bottom_bar(surface, renderer, session)

    def _draw_header(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render merchant title dialogue plaque and treasury pouch status."""
        # Merchant title box
        assets.draw_frame(surface, "frame_button_gold", self.header_rect, margin=16)
        m_title = "WANDERING APOTHECARY & TRADER" if i18n.locale == "en" else "MERCADER Y BOTICARIO AMBULANTE"
        renderer.draw_text(
            surface,
            m_title,
            self.header_rect.x + 18,
            self.header_rect.y + 8,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=15,
            bold=True,
        )

        quote = t("merchant_quote") if i18n.locale == "es" else "Care to inspect my rare wares, traveler?"
        renderer.draw_text(
            surface,
            f'"{quote}"',
            self.header_rect.x + 18,
            self.header_rect.y + 27,
            token=ThemeToken.TEXT_MUTED,
            size=12,
            bold=False,
        )

        # Treasury status box
        assets.draw_frame(surface, "frame_button_gold", self.treasury_rect, margin=16)
        gold_icon = assets.get_ui_component("icon_gold")
        if gold_icon:
            scaled_gold = pygame.transform.scale(gold_icon, (20, 20))
            surface.blit(scaled_gold, (self.treasury_rect.x + 16, self.treasury_rect.centery - 10))

        renderer.draw_text(
            surface,
            f"{session.player.gold} Gold",
            self.treasury_rect.x + 42,
            self.treasury_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=14,
            bold=True,
        )

        pouch_icon = assets.get_ui_component("icon_pouch")
        if pouch_icon:
            scaled_pouch = pygame.transform.scale(pouch_icon, (18, 18))
            surface.blit(scaled_pouch, (self.treasury_rect.x + 170, self.treasury_rect.centery - 9))

        pouch_len = len(session.player.inventory.pouch)
        renderer.draw_text(
            surface,
            f"Pouch: {pouch_len}/{MAX_POUCH_SLOTS}",
            self.treasury_rect.x + 196,
            self.treasury_rect.centery - 6,
            token=ThemeToken.TEXT_NORMAL if pouch_len < MAX_POUCH_SLOTS else ThemeToken.TEXT_ALERT,
            size=14,
            bold=True,
        )

    def _draw_tabs(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render dual [ BUY ] and [ SELL ] tabs with item counters."""
        is_buy = (self.active_tab == "BUY")
        stock_cnt = len(session.state.merchant_stock)
        pouch_cnt = len(session.player.inventory.pouch)

        # Buy Tab
        bg_buy = pygame.Surface(self.tab_buy_rect.size, pygame.SRCALPHA)
        bg_buy.fill((28, 36, 56, 240) if is_buy else (16, 20, 30, 200))
        surface.blit(bg_buy, self.tab_buy_rect.topleft)

        frame_name = "frame_button_gold" if is_buy else "frame_gold_clean"
        assets.draw_frame(surface, frame_name, self.tab_buy_rect, margin=14)

        buy_label = f"[ 1 ] BUY WARES ({stock_cnt})" if i18n.locale == "en" else f"[ 1 ] COMPRAR ({stock_cnt})"
        renderer.draw_text(
            surface,
            buy_label,
            self.tab_buy_rect.centerx,
            self.tab_buy_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if is_buy else ThemeToken.TEXT_MUTED,
            size=13,
            bold=is_buy,
            align="center",
        )

        # Sell Tab
        is_sell = (self.active_tab == "SELL")
        bg_sell = pygame.Surface(self.tab_sell_rect.size, pygame.SRCALPHA)
        bg_sell.fill((28, 36, 56, 240) if is_sell else (16, 20, 30, 200))
        surface.blit(bg_sell, self.tab_sell_rect.topleft)

        frame_name_s = "frame_button_gold" if is_sell else "frame_gold_clean"
        assets.draw_frame(surface, frame_name_s, self.tab_sell_rect, margin=14)

        sell_label = f"[ 2 ] SELL GOODS ({pouch_cnt})" if i18n.locale == "en" else f"[ 2 ] VENDER ({pouch_cnt})"
        renderer.draw_text(
            surface,
            sell_label,
            self.tab_sell_rect.centerx,
            self.tab_sell_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if is_sell else ThemeToken.TEXT_MUTED,
            size=13,
            bold=is_sell,
            align="center",
        )

        # Tab shortcut hint
        renderer.draw_text(
            surface,
            "[ TAB ] Switch Mode",
            self.outer_rect.x + 390,
            self.tab_buy_rect.centery - 6,
            token=ThemeToken.TEXT_MUTED,
            size=12,
            bold=False,
        )

    def _draw_catalog(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render catalog items list with scrolling, icons, names, and prices."""
        # Catalog panel background
        bg_surf = pygame.Surface((self.catalog_rect.width - 8, self.catalog_rect.height - 8), pygame.SRCALPHA)
        bg_surf.fill((12, 14, 22, 220))
        surface.blit(bg_surf, (self.catalog_rect.x + 4, self.catalog_rect.y + 4))

        assets.draw_frame(surface, "frame_gold_clean", self.catalog_rect, margin=18, draw_center=False)

        items = session.state.merchant_stock if self.active_tab == "BUY" else session.player.inventory.pouch
        curr_cursor = self.buy_cursor if self.active_tab == "BUY" else self.sell_cursor

        if not items:
            empty_msg = t("merchant_out_of_stock") if self.active_tab == "BUY" else t("merchant_empty_pouch")
            renderer.draw_text(
                surface,
                empty_msg or "No items available.",
                self.catalog_rect.centerx,
                self.catalog_rect.centery - 8,
                token=ThemeToken.TEXT_MUTED,
                size=14,
                bold=True,
                align="center",
            )
            return

        scroll_offset = max(0, min(curr_cursor - 2, max(0, len(items) - 5)))
        visible_items = items[scroll_offset : scroll_offset + 5]

        for vi, entry in enumerate(visible_items):
            real_idx = scroll_offset + vi
            is_active = (real_idx == curr_cursor)
            is_hover = (real_idx == self._hovered_row)

            if self.active_tab == "BUY":
                if isinstance(entry, tuple):
                    item, price = entry
                else:
                    item = entry
                    price = getattr(item, "cost", getattr(item, "gold_value", 10))
            else:
                item = entry
                price = ShopService.calculate_sell_price(item)

            row_y = self.catalog_rect.y + 12 + vi * 58
            row_rect = pygame.Rect(self.catalog_rect.x + 12, row_y, self.catalog_rect.width - 24, 52)

            # Row background
            row_surf = pygame.Surface(row_rect.size, pygame.SRCALPHA)
            if is_active:
                row_surf.fill((28, 38, 62, 240))
            elif is_hover:
                row_surf.fill((20, 26, 42, 220))
            else:
                row_surf.fill((16, 20, 32, 200))
            surface.blit(row_surf, row_rect.topleft)

            # Border
            frame_name = "frame_button_gold" if is_active else "frame_gold_clean"
            assets.draw_frame(surface, frame_name, row_rect, margin=14)

            # Cursor arrow
            if is_active:
                arrow_color = (255, 215, 0)
                pulse = int(math.sin(self.anim_timer * 6) * 3)
                ax = row_rect.x + 8 + pulse
                ay = row_rect.centery
                pygame.draw.polygon(surface, arrow_color, [(ax, ay - 6), (ax, ay + 6), (ax + 7, ay)])

            # Item Icon Box
            icon_box = pygame.Rect(row_rect.x + 22, row_rect.centery - 18, 36, 36)
            pygame.draw.rect(surface, (8, 10, 16), icon_box)
            pygame.draw.rect(surface, (70, 85, 115), icon_box, width=1)

            icon_surf = self._get_item_icon(item)
            if icon_surf:
                surface.blit(icon_surf, (icon_box.centerx - 14, icon_box.centery - 14))

            # Item Name & Subtitle
            tier = getattr(item, "tier", 1)
            rarity_col = TIER_COLORS.get(tier, (220, 225, 235))

            renderer.draw_text(
                surface,
                item.localized_name,
                row_rect.x + 68,
                row_rect.y + 8,
                color=rarity_col,
                size=14,
                bold=True,
            )

            # Subtitle (Slot or Consumable effect)
            if isinstance(item, EquipmentItem):
                sub_txt = f"[{item.slot.name.capitalize()}]"
            elif isinstance(item, ConsumableItem):
                sub_txt = f"Heals {item.heal_amount} HP" if getattr(item, "heal_amount", 0) > 0 else "Consumable"
            else:
                sub_txt = "Item"

            renderer.draw_text(
                surface,
                sub_txt,
                row_rect.x + 68,
                row_rect.y + 28,
                token=ThemeToken.TEXT_MUTED,
                size=12,
            )

            # Price Tag (Right side)
            gold_icon = assets.get_ui_component("icon_gold")
            gx = row_rect.right - 95
            if gold_icon:
                scaled_g = pygame.transform.scale(gold_icon, (16, 16))
                surface.blit(scaled_g, (gx, row_rect.centery - 8))

            can_afford = (session.player.gold >= price) if self.active_tab == "BUY" else True
            price_txt = f"{price}G"
            renderer.draw_text(
                surface,
                price_txt,
                gx + 22,
                row_rect.centery - 7,
                token=ThemeToken.TEXT_HIGHLIGHT if can_afford else ThemeToken.TEXT_ALERT,
                size=14,
                bold=True,
            )

    def _draw_inspector(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render detailed item inspection panel with stats comparison deltas."""
        # Panel backdrop
        bg_surf = pygame.Surface((self.inspector_rect.width - 8, self.inspector_rect.height - 8), pygame.SRCALPHA)
        bg_surf.fill((14, 18, 28, 230))
        surface.blit(bg_surf, (self.inspector_rect.x + 4, self.inspector_rect.y + 4))

        assets.draw_frame(surface, "frame_gold_clean", self.inspector_rect, margin=18, draw_center=False)

        item, price, is_buying = self._get_inspected_item(session)
        if not item:
            renderer.draw_text(
                surface,
                "Select an item to inspect.",
                self.inspector_rect.centerx,
                self.inspector_rect.centery - 8,
                token=ThemeToken.TEXT_MUTED,
                size=13,
                bold=True,
                align="center",
            )
            return

        # 1. Header Showcase: 44x44 Icon + Title
        icon_box = pygame.Rect(self.inspector_rect.x + 16, self.inspector_rect.y + 16, 44, 44)
        pygame.draw.rect(surface, (8, 10, 16), icon_box)
        pygame.draw.rect(surface, (90, 110, 145), icon_box, width=1)

        icon_surf = self._get_item_icon(item)
        if icon_surf:
            scaled_ic = pygame.transform.scale(icon_surf, (34, 34))
            surface.blit(scaled_ic, (icon_box.centerx - 17, icon_box.centery - 17))

        tier = getattr(item, "tier", 1)
        rarity_col = TIER_COLORS.get(tier, (220, 225, 235))

        renderer.draw_text(
            surface,
            item.localized_name,
            self.inspector_rect.x + 70,
            self.inspector_rect.y + 16,
            color=rarity_col,
            size=15,
            bold=True,
        )

        tier_names = {1: "Common", 2: "Uncommon", 3: "Rare", 4: "Epic", 5: "Legendary"}
        t_name = tier_names.get(tier, "Common")
        category_txt = f"Tier {tier} {t_name} Equipment" if isinstance(item, EquipmentItem) else "Consumable Potion"
        renderer.draw_text(
            surface,
            category_txt,
            self.inspector_rect.x + 70,
            self.inspector_rect.y + 36,
            token=ThemeToken.TEXT_MUTED,
            size=12,
        )

        # Divider line
        div_y = self.inspector_rect.y + 68
        pygame.draw.line(surface, (60, 70, 95), (self.inspector_rect.x + 16, div_y), (self.inspector_rect.right - 16, div_y), width=1)

        # 2. Lore Description
        desc_lines = []
        raw_desc = item.localized_description or "An ancient relic of forgotten origin."
        words = raw_desc.split(" ")
        curr = ""
        for w in words:
            if len(curr) + len(w) < 32:
                curr += w + " "
            else:
                desc_lines.append(curr.strip())
                curr = w + " "
        if curr:
            desc_lines.append(curr.strip())

        for idx, line in enumerate(desc_lines[:3]):
            renderer.draw_text(
                surface,
                line,
                self.inspector_rect.x + 16,
                div_y + 8 + idx * 16,
                token=ThemeToken.TEXT_NORMAL,
                size=12,
            )

        # Divider line
        div_y2 = div_y + 64
        pygame.draw.line(surface, (60, 70, 95), (self.inspector_rect.x + 16, div_y2), (self.inspector_rect.right - 16, div_y2), width=1)

        # 3. Attributes & Comparison Deltas
        stat_y = div_y2 + 8
        if isinstance(item, EquipmentItem):
            equipped = session.player.inventory.equipment.get(item.slot)
            eq_stats = equipped.stats_bonus if equipped else None

            st = item.stats_bonus
            stat_entries = [
                ("ATK", st.attack, eq_stats.attack if eq_stats else 0),
                ("DEF", st.defense, eq_stats.defense if eq_stats else 0),
                ("SPD", st.speed, eq_stats.speed if eq_stats else 0),
                ("HP", st.max_hp, eq_stats.max_hp if eq_stats else 0),
            ]

            renderer.draw_text(
                surface,
                f"SLOT: {item.slot.name.upper()}",
                self.inspector_rect.x + 16,
                stat_y,
                token=ThemeToken.TEXT_HIGHLIGHT,
                size=12,
                bold=True,
            )
            stat_y += 18

            for label, val, eq_val in stat_entries:
                if val != 0 or eq_val != 0:
                    diff = val - eq_val
                    diff_sign = f"+{diff}" if diff > 0 else str(diff)
                    diff_col = (64, 220, 120) if diff > 0 else ((240, 70, 80) if diff < 0 else (160, 170, 185))

                    val_str = f"+{val}" if val > 0 else str(val)
                    base_str = f"{label}: {val_str}"

                    renderer.draw_text(
                        surface,
                        base_str,
                        self.inspector_rect.x + 16,
                        stat_y,
                        token=ThemeToken.TEXT_NORMAL,
                        size=13,
                        bold=True,
                    )

                    diff_tag = f"(Diff: {diff_sign})"
                    renderer.draw_text(
                        surface,
                        diff_tag,
                        self.inspector_rect.x + 140,
                        stat_y,
                        color=diff_col,
                        size=13,
                        bold=True,
                    )
                    stat_y += 18

        elif isinstance(item, ConsumableItem):
            if getattr(item, "heal_amount", 0) > 0:
                renderer.draw_text(
                    surface,
                    f"Heals: {item.heal_amount} HP",
                    self.inspector_rect.x + 16,
                    stat_y,
                    color=(64, 220, 120),
                    size=13,
                    bold=True,
                )
                stat_y += 20

            if isinstance(item, StatPotion) or getattr(item, "stat_bonus", None):
                b = item.stat_bonus
                for sname, sval in [("ATK", b.attack), ("DEF", b.defense), ("SPD", b.speed), ("HP", b.max_hp)]:
                    if sval > 0:
                        renderer.draw_text(
                            surface,
                            f"+{sval} {sname} (Permanent)",
                            self.inspector_rect.x + 16,
                            stat_y,
                            color=(255, 215, 0),
                            size=13,
                            bold=True,
                        )
                        stat_y += 20

        # 4. Bottom Price Line
        price_rect = pygame.Rect(self.inspector_rect.x + 14, self.inspector_rect.bottom - 44, self.inspector_rect.width - 28, 32)
        assets.draw_frame(surface, "frame_button_gold", price_rect, margin=14)

        tag = "Price" if is_buying else "Sell Value"
        renderer.draw_text(
            surface,
            f"{tag}: {price} Gold",
            price_rect.centerx,
            price_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=14,
            bold=True,
            align="center",
        )

    def _draw_bottom_bar(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render live feedback notification and action buttons."""
        # Feedback Toast
        if self.feedback_msg:
            msg_col = (64, 220, 120) if self.feedback_success else (240, 70, 80)
            renderer.draw_text(
                surface,
                self.feedback_msg,
                self.outer_rect.x + 246,
                self.action_btn_rect.centery - 7,
                color=msg_col,
                size=14,
                bold=True,
            )

        # Action Button (Buy / Sell)
        is_buy = (self.active_tab == "BUY")
        is_hover_act = (self._hovered_btn == "action")

        bg_act = pygame.Surface(self.action_btn_rect.size, pygame.SRCALPHA)
        bg_act.fill((28, 38, 62, 240) if is_hover_act else (16, 22, 36, 220))
        surface.blit(bg_act, self.action_btn_rect.topleft)

        assets.draw_frame(surface, "frame_button_gold", self.action_btn_rect, margin=16)

        act_label = "[ ENTER / B ] BUY ITEM" if is_buy else "[ ENTER / S ] SELL ITEM"
        renderer.draw_text(
            surface,
            act_label,
            self.action_btn_rect.centerx,
            self.action_btn_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if is_hover_act else ThemeToken.TEXT_NORMAL,
            size=13,
            bold=True,
            align="center",
        )

        # Leave Button
        is_hover_leave = (self._hovered_btn == "leave")
        bg_leave = pygame.Surface(self.leave_btn_rect.size, pygame.SRCALPHA)
        bg_leave.fill((28, 38, 62, 240) if is_hover_leave else (16, 22, 36, 220))
        surface.blit(bg_leave, self.leave_btn_rect.topleft)

        assets.draw_frame(surface, "frame_button_gold", self.leave_btn_rect, margin=16)

        leave_label = "[ ESC ] LEAVE SHOP"
        renderer.draw_text(
            surface,
            leave_label,
            self.leave_btn_rect.centerx,
            self.leave_btn_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if is_hover_leave else ThemeToken.TEXT_NORMAL,
            size=13,
            bold=True,
            align="center",
        )
