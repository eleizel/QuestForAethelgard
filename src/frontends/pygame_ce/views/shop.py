"""Pygame-CE Merchant & Barter Shop View."""

from __future__ import annotations

from typing import TYPE_CHECKING
import pygame

from src.core.commands import BuyItemCommand, SellItemCommand
from src.core.game_state import GameMode
from src.core.theme import ThemeToken
from src.entities.item import EquipmentItem
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


class PygameShopView(PygameView):
    """Interactive shop view allowing players to buy merchant wares and sell pouch equipment."""

    def __init__(self) -> None:
        self.selected_merchant_idx: int = 0
        self.selected_pouch_idx: int = 0
        self.active_column: str = "buy"
        self._hovered_btn: str | None = None

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        stock = session.state.merchant_stock
        pouch = session.player.inventory.pouch

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_q):
                session.switch_mode(GameMode.MAP)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.active_column = "buy"
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.active_column = "sell"
            elif event.key in (pygame.K_UP, pygame.K_w):
                if self.active_column == "buy" and stock:
                    self.selected_merchant_idx = (self.selected_merchant_idx - 1) % len(stock)
                elif self.active_column == "sell" and pouch:
                    self.selected_pouch_idx = (self.selected_pouch_idx - 1) % len(pouch)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                if self.active_column == "buy" and stock:
                    self.selected_merchant_idx = (self.selected_merchant_idx + 1) % len(stock)
                elif self.active_column == "sell" and pouch:
                    self.selected_pouch_idx = (self.selected_pouch_idx + 1) % len(pouch)
            elif event.key == pygame.K_RETURN:
                if self.active_column == "buy" and stock and self.selected_merchant_idx < len(stock):
                    session.dispatch(BuyItemCommand(stock_index=self.selected_merchant_idx))
                elif self.active_column == "sell" and pouch and self.selected_pouch_idx < len(pouch):
                    session.dispatch(SellItemCommand(pouch_index=self.selected_pouch_idx))

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for idx in range(len(stock)):
                buy_row = pygame.Rect(70, 150 + idx * 56, 380, 48)
                if buy_row.collidepoint(pos):
                    session.dispatch(BuyItemCommand(stock_index=idx))
                    return

            for idx in range(len(pouch)):
                sell_row = pygame.Rect(510, 150 + idx * 56, 380, 48)
                if sell_row.collidepoint(pos):
                    session.dispatch(SellItemCommand(pouch_index=idx))
                    return

            leave_rect = pygame.Rect(380, 470, 200, 42)
            if leave_rect.collidepoint(pos):
                session.switch_mode(GameMode.MAP)
                return

    def update(self, dt: float, session: GameSession) -> None:
        pos = pygame.mouse.get_pos()
        leave_rect = pygame.Rect(380, 470, 200, 42)
        self._hovered_btn = "leave" if leave_rect.collidepoint(pos) else None

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        assets.draw_background(surface, "shop", vignette_alpha=120)
        w = surface.get_width()

        renderer.draw_text(surface, "THE WANDERING MERCHANT", w // 2, 30, token=ThemeToken.TEXT_HIGHLIGHT, size=28, bold=True, align="center")

        player = session.player
        gold_text = f"YOUR PURSE: {player.gold} GOLD"
        renderer.draw_text(surface, gold_text, w // 2, 65, token=ThemeToken.TEXT_HIGHLIGHT, size=16, bold=True, align="center")

        stock = session.state.merchant_stock
        pouch = player.inventory.pouch

        buy_panel = pygame.Rect(50, 100, 420, 350)
        renderer.draw_panel(surface, buy_panel, border_token=ThemeToken.ACCENT_PRIMARY if self.active_column == "buy" else ThemeToken.BORDER)
        renderer.draw_text(surface, "WARES FOR SALE", buy_panel.x + 20, buy_panel.y + 14, token=ThemeToken.TEXT_HIGHLIGHT, size=15, bold=True)

        if not stock:
            renderer.draw_text(surface, "Stock sold out!", buy_panel.centerx, buy_panel.centery, token=ThemeToken.TEXT_MUTED, size=14, align="center")
        else:
            for idx, entry in enumerate(stock[:5]):
                if isinstance(entry, tuple):
                    item, cost = entry
                else:
                    item = entry
                    cost = getattr(item, "cost", getattr(item, "gold_value", getattr(item, "value", 10)))

                row_rect = pygame.Rect(buy_panel.x + 15, buy_panel.y + 44 + idx * 56, 390, 48)
                is_sel = (self.active_column == "buy" and self.selected_merchant_idx == idx)
                renderer.draw_panel(surface, row_rect, border_token=ThemeToken.ACCENT_PRIMARY if is_sel else ThemeToken.BORDER_MUTED)

                can_afford = player.gold >= cost
                renderer.draw_text(surface, f"{item.name}", row_rect.x + 12, row_rect.y + 8, token=ThemeToken.TEXT_NORMAL, size=14, bold=True)
                renderer.draw_text(surface, f"Price: {cost}G", row_rect.x + 12, row_rect.y + 26, token=ThemeToken.TEXT_HIGHLIGHT if can_afford else ThemeToken.TEXT_ALERT, size=12, bold=True)

                buy_btn = pygame.Rect(row_rect.right - 90, row_rect.y + 8, 80, 32)
                renderer.draw_button(surface, buy_btn, "BUY", accent_token=ThemeToken.TEXT_SUCCESS if can_afford else ThemeToken.BORDER_MUTED, font_size=11)

        sell_panel = pygame.Rect(490, 100, 420, 350)
        renderer.draw_panel(surface, sell_panel, border_token=ThemeToken.ACCENT_PRIMARY if self.active_column == "sell" else ThemeToken.BORDER)
        renderer.draw_text(surface, f"YOUR INVENTORY ({len(pouch)}/10)", sell_panel.x + 20, sell_panel.y + 14, token=ThemeToken.TEXT_HIGHLIGHT, size=15, bold=True)

        if not pouch:
            renderer.draw_text(surface, "Inventory pouch is empty", sell_panel.centerx, sell_panel.centery, token=ThemeToken.TEXT_MUTED, size=14, align="center")
        else:
            for idx, item in enumerate(pouch[:5]):
                row_rect = pygame.Rect(sell_panel.x + 15, sell_panel.y + 44 + idx * 56, 390, 48)
                is_sel = (self.active_column == "sell" and self.selected_pouch_idx == idx)
                renderer.draw_panel(surface, row_rect, border_token=ThemeToken.ACCENT_PRIMARY if is_sel else ThemeToken.BORDER_MUTED)

                val = getattr(item, "gold_value", getattr(item, "value", 10))
                sell_val = max(5, val // 2)
                renderer.draw_text(surface, f"{item.name}", row_rect.x + 12, row_rect.y + 8, token=ThemeToken.TEXT_NORMAL, size=14, bold=True)
                renderer.draw_text(surface, f"Sell value: +{sell_val}G", row_rect.x + 12, row_rect.y + 26, token=ThemeToken.TEXT_SUCCESS, size=12, bold=True)

                sell_btn = pygame.Rect(row_rect.right - 90, row_rect.y + 8, 80, 32)
                renderer.draw_button(surface, sell_btn, "SELL", accent_token=ThemeToken.ACCENT_SECONDARY, font_size=11)

        leave_rect = pygame.Rect(380, 470, 200, 42)
        renderer.draw_button(surface, leave_rect, "LEAVE SHOP [ESC]", is_hovered=(self._hovered_btn == "leave"), accent_token=ThemeToken.BORDER, font_size=13)
