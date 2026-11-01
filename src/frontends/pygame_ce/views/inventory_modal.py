"""Pygame-CE Inventory & Equipment Modal Overlay View."""

from __future__ import annotations

from typing import TYPE_CHECKING
import pygame

from src.core.game_state import GameMode
from src.core.theme import ThemeToken
from src.entities.item import EquipSlot, EquipmentItem, ConsumableItem
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


class PygameInventoryModalView(PygameView):
    """Full inventory management modal displaying equipped gear, 10-slot pouch, and 3-slot belt."""

    EQUIP_SLOT_ORDER = [
        EquipSlot.HEAD, EquipSlot.CHEST, EquipSlot.SHOULDERS, EquipSlot.HANDS,
        EquipSlot.WAIST, EquipSlot.LEGS, EquipSlot.MAIN_HAND, EquipSlot.OFF_HAND,
    ]

    def __init__(self) -> None:
        pass

    def _activate_pouch_item(self, idx: int, player, inv) -> None:
        if idx >= len(inv.pouch):
            return
        item = inv.pouch[idx]
        if isinstance(item, EquipmentItem):
            inv.equip_from_pouch(idx, player)
        elif isinstance(item, ConsumableItem):
            empty_belt = next((b for b in range(len(inv.belt)) if inv.belt[b] is None), None)
            if empty_belt is not None:
                inv.assign_pouch_to_belt(idx, empty_belt)
            else:
                inv.use_from_pouch(idx, player)

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        player = session.player
        inv = player.inventory

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_i, pygame.K_ESCAPE):
                session.toggle_inventory()
                return
            elif pygame.K_1 <= event.key <= pygame.K_9:
                p_idx = event.key - pygame.K_1
                self._activate_pouch_item(p_idx, player, inv)
                return
            elif event.key == pygame.K_0:
                self._activate_pouch_item(9, player, inv)
                return

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            close_btn = pygame.Rect(850, 45, 36, 36)
            if close_btn.collidepoint(pos):
                session.toggle_inventory()
                return

            for idx in range(len(inv.pouch)):
                item_rect = pygame.Rect(520, 130 + idx * 30, 340, 26)
                if item_rect.collidepoint(pos):
                    self._activate_pouch_item(idx, player, inv)
                    return

            for idx, slot in enumerate(self.EQUIP_SLOT_ORDER):
                slot_rect = pygame.Rect(100, 130 + idx * 38, 380, 32)
                if slot_rect.collidepoint(pos) and inv.equipment.get(slot) is not None:
                    inv.unequip_to_pouch(slot)
                    return

            belt_y = 445
            for b_idx in range(3):
                b_rect = pygame.Rect(240 + b_idx * 160, belt_y, 140, 28)
                if b_rect.collidepoint(pos):
                    if b_idx < len(inv.belt) and inv.belt[b_idx] is not None:
                        if len(inv.pouch) < 10:
                            inv.pouch.append(inv.belt[b_idx])
                            inv.belt[b_idx] = None
                    return

    def update(self, dt: float, session: GameSession) -> None:
        pass

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        w, h = surface.get_width(), surface.get_height()

        backdrop = pygame.Surface((w, h), pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, 180))
        surface.blit(backdrop, (0, 0))

        modal_rect = pygame.Rect(60, 30, 840, 480)
        renderer.draw_panel(surface, modal_rect, bg_token=ThemeToken.PANEL_BG, border_token=ThemeToken.ACCENT_PRIMARY, border_width=2, border_radius=10)

        renderer.draw_text(surface, "HERO INVENTORY & EQUIPMENT", modal_rect.x + 30, modal_rect.y + 20, token=ThemeToken.TEXT_HIGHLIGHT, size=20, bold=True)

        close_btn = pygame.Rect(modal_rect.right - 50, modal_rect.y + 15, 36, 36)
        renderer.draw_button(surface, close_btn, "X", accent_token=ThemeToken.BORDER_MUTED, font_size=14)

        player = session.player
        inv = player.inventory

        # Left Column: Equipped Items (8 slots)
        renderer.draw_text(surface, "EQUIPPED GEAR", 100, 95, token=ThemeToken.TEXT_HIGHLIGHT, size=15, bold=True)
        for idx, slot in enumerate(self.EQUIP_SLOT_ORDER):
            y = 130 + idx * 38
            slot_rect = pygame.Rect(100, y, 380, 32)
            renderer.draw_panel(surface, slot_rect, border_token=ThemeToken.BORDER_MUTED)

            slot_label = slot.name.replace("_", " ").capitalize()
            equipped_item = inv.equipment.get(slot)

            renderer.draw_text(surface, f"{slot_label}:", slot_rect.x + 12, slot_rect.y + 7, token=ThemeToken.TEXT_MUTED, size=12, bold=True)
            if equipped_item:
                renderer.draw_text(surface, equipped_item.name, slot_rect.x + 110, slot_rect.y + 7, token=ThemeToken.TEXT_NORMAL, size=13, bold=True)
                stats = getattr(equipped_item, "stats_bonus", getattr(equipped_item, "stats", None))
                if stats:
                    stats_str = f"+{stats.attack}A +{stats.defense}D"
                    renderer.draw_text(surface, stats_str, slot_rect.right - 12, slot_rect.y + 7, token=ThemeToken.ACCENT_PRIMARY, size=12, align="right")
            else:
                renderer.draw_text(surface, "(Empty)", slot_rect.x + 110, slot_rect.y + 7, token=ThemeToken.BORDER_MUTED, size=12)

        # Right Column: Pouch Inventory (10 slots)
        renderer.draw_text(surface, f"POUCH ({len(inv.pouch)}/10) - Click to Equip", 520, 95, token=ThemeToken.TEXT_HIGHLIGHT, size=15, bold=True)
        for idx in range(10):
            y = 130 + idx * 30
            pouch_rect = pygame.Rect(520, y, 340, 26)
            renderer.draw_panel(surface, pouch_rect, border_token=ThemeToken.BORDER_MUTED)

            if idx < len(inv.pouch):
                item = inv.pouch[idx]
                renderer.draw_text(surface, f"[{idx+1}] {item.name}", pouch_rect.x + 10, pouch_rect.y + 4, token=ThemeToken.TEXT_NORMAL, size=12, bold=True)
                tier_str = f"T{getattr(item, 'tier', 1)}"
                renderer.draw_text(surface, tier_str, pouch_rect.right - 10, pouch_rect.y + 4, token=ThemeToken.TEXT_MUTED, size=11, align="right")
            else:
                renderer.draw_text(surface, f"[{idx+1}] ---", pouch_rect.x + 10, pouch_rect.y + 4, token=ThemeToken.BORDER_MUTED, size=11)

        # Belt quick bar at bottom
        belt_y = 445
        renderer.draw_text(surface, "BELT QUICK SLOTS:", 100, belt_y + 4, token=ThemeToken.TEXT_MUTED, size=12, bold=True)
        for b_idx in range(3):
            b_rect = pygame.Rect(240 + b_idx * 160, belt_y, 140, 28)
            renderer.draw_panel(surface, b_rect, border_token=ThemeToken.ACCENT_SECONDARY)
            if b_idx < len(inv.belt) and inv.belt[b_idx] is not None:
                p_name = inv.belt[b_idx].name
                renderer.draw_text(surface, f"[{b_idx+1}] {p_name}", b_rect.centerx, b_rect.centery - 6, token=ThemeToken.TEXT_HIGHLIGHT, size=11, bold=True, align="center")
            else:
                renderer.draw_text(surface, f"[{b_idx+1}] Empty Potion", b_rect.centerx, b_rect.centery - 6, token=ThemeToken.TEXT_MUTED, size=11, align="center")
