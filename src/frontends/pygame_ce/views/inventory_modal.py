"""Pygame-CE Hero Inventory & Equipment View.

Faithfully implements the 16-bit Super Nintendo JRPG inventory management view:
- Reusable Top Status Bar (TopHUDComponent)
- Biome map background dimmed over the screen
- Upper-Left: Mannequin Equipment Alcove with stone arch, pedestal, hero sprite,
  and 8 equipment slots flanking the hero mannequin
- Upper-Right: Item Inspector Detail Panel with large icon showcase, stats breakdown,
  live stat difference comparison vs equipped gear, and wrapped description
- Lower-Left: 3-Slot Belt Panel with vertical potion cards and effects
- Lower-Right: 10-Slot Pouch Grid with tier color bands, icons, and empty silhouettes
- Bottom Action Bar: [ EQUIP / USE ] (E), Quick Belt Assign [B1, B2, B3] (1-3),
  [ DROP ] (D), [ CLOSE ] (ESC/I), with dynamic feedback messages
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame

from src.core.game_state import GameMode
from src.core.i18n import t, i18n
from src.core.theme import ThemeToken
from src.entities.item import EquipSlot, EquipmentItem, ConsumableItem
from src.data.items import StatPotion
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.components.top_hud import TopHUDComponent
from src.frontends.pygame_ce.views.base import PygameView
from src.systems.inventory import MAX_BELT_SLOTS, MAX_POUCH_SLOTS

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


def get_item_display_name(item) -> str:
    """Resolve user-facing name with fallback when translation key is missing."""
    loc_name = getattr(item, "localized_name", getattr(item, "name", "Item"))
    if loc_name.startswith("item_") and getattr(item, "name", None):
        return item.name
    return loc_name


def get_item_display_desc(item) -> str:
    """Resolve user-facing description with fallback."""
    loc_desc = getattr(item, "localized_description", getattr(item, "description", ""))
    if loc_desc.startswith("item_") and getattr(item, "description", None):
        return item.description
    return loc_desc


class PygameInventoryModalView(PygameView):
    """Authentic 16-bit SNES hero inventory and equipment management view."""

    TIER_COLORS = {
        1: (180, 185, 195),  # Common (Silver/Gray)
        2: (80, 220, 100),   # Uncommon (Lime Green)
        3: (40, 170, 255),   # Rare (Sapphire Cyan)
        4: (190, 80, 240),   # Epic (Mystic Purple)
        5: (255, 190, 40),   # Legendary (Radiant Gold)
    }

    EQUIP_SLOT_ORDER = [
        EquipSlot.HEAD, EquipSlot.SHOULDERS, EquipSlot.CHEST, EquipSlot.HANDS,
        EquipSlot.MAIN_HAND, EquipSlot.OFF_HAND, EquipSlot.WAIST, EquipSlot.LEGS,
    ]

    SLOT_NAMES = {
        EquipSlot.HEAD: "Head",
        EquipSlot.SHOULDERS: "Shoulders",
        EquipSlot.CHEST: "Chest",
        EquipSlot.HANDS: "Hands",
        EquipSlot.MAIN_HAND: "Main Hand",
        EquipSlot.OFF_HAND: "Off Hand",
        EquipSlot.WAIST: "Waist",
        EquipSlot.LEGS: "Legs",
    }

    def __init__(self) -> None:
        self.top_hud = TopHUDComponent()
        self.active_pane: str = "POUCH"  # "POUCH", "EQUIPMENT", or "BELT"
        self.pouch_cursor: int = 0
        self.equip_cursor: int = 0
        self.belt_cursor: int = 0
        self.feedback_message: str = ""
        self.feedback_success: bool = False
        self._hovered_btn: str | None = None
        self._last_click_target: str | None = None
        self._last_click_time: float = 0.0

        # Clickable rects
        self.equip_rects: list[pygame.Rect] = []
        self.belt_rects: list[pygame.Rect] = []
        self.pouch_rects: list[pygame.Rect] = []

        # Action button rects
        self.equip_btn_rect = pygame.Rect(380, 480, 160, 34)
        self.b1_btn_rect = pygame.Rect(550, 480, 42, 34)
        self.b2_btn_rect = pygame.Rect(598, 480, 42, 34)
        self.b3_btn_rect = pygame.Rect(646, 480, 42, 34)
        self.drop_btn_rect = pygame.Rect(698, 480, 100, 34)
        self.close_btn_rect = pygame.Rect(808, 480, 110, 34)

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

    def _get_slot_default_icon(self, slot: EquipSlot) -> pygame.Surface | None:
        """Default faint silhouette icon for an empty equipment slot."""
        coords = {
            EquipSlot.HEAD: (80, 8),
            EquipSlot.SHOULDERS: (8, 16),
            EquipSlot.CHEST: (88, 8),
            EquipSlot.HANDS: (96, 8),
            EquipSlot.MAIN_HAND: (72, 0),
            EquipSlot.OFF_HAND: (80, 0),
            EquipSlot.WAIST: (16, 16),
            EquipSlot.LEGS: (104, 8),
        }
        coord = coords.get(slot, (96, 0))
        surf = assets.get_pyxel_icon(coord[0], coord[1], size=(28, 28))
        if surf:
            faint = surf.copy()
            faint.set_alpha(90)
            return faint
        return None

    def _get_selected_item(self, session: GameSession):
        """Retrieve currently inspected item and its context category."""
        inv = session.player.inventory
        if self.active_pane == "EQUIPMENT":
            slot = self.EQUIP_SLOT_ORDER[self.equip_cursor]
            return inv.equipment.get(slot), f"{self.SLOT_NAMES[slot]} Slot"
        elif self.active_pane == "BELT":
            item = inv.belt[self.belt_cursor]
            return item, f"Belt Slot {self.belt_cursor + 1}"
        else:  # "POUCH"
            if self.pouch_cursor < len(inv.pouch):
                item = inv.pouch[self.pouch_cursor]
                return item, "Pouch Item"
            return None, "Empty Pouch Slot"

    def _perform_equip_or_use(self, session: GameSession) -> None:
        """Execute equip, unequip, or consume depending on active pane."""
        player = session.player
        inv = player.inventory

        if self.active_pane == "POUCH":
            if self.pouch_cursor < len(inv.pouch):
                item = inv.pouch[self.pouch_cursor]
                if isinstance(item, EquipmentItem):
                    success, msg = inv.equip_from_pouch(self.pouch_cursor, player)
                    self.feedback_message = msg
                    self.feedback_success = success
                elif isinstance(item, ConsumableItem):
                    # Assign to next empty belt slot
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

        elif self.active_pane == "EQUIPMENT":
            slot = self.EQUIP_SLOT_ORDER[self.equip_cursor]
            if inv.equipment.get(slot) is not None:
                success, msg = inv.unequip_to_pouch(slot)
                self.feedback_message = msg
                self.feedback_success = success

        elif self.active_pane == "BELT":
            if inv.use_belt_item(self.belt_cursor, player):
                self.feedback_message = "Item used!" if i18n.locale == "en" else "¡Objeto usado!"
                self.feedback_success = True
            else:
                self.feedback_message = "Cannot use item."
                self.feedback_success = False

    def _perform_drop(self, session: GameSession) -> None:
        """Drop selected item from pouch or belt."""
        inv = session.player.inventory
        if self.active_pane == "POUCH":
            if self.pouch_cursor < len(inv.pouch):
                success, msg = inv.drop_from_pouch(self.pouch_cursor)
                self.feedback_message = msg
                self.feedback_success = success
        elif self.active_pane == "BELT":
            if inv.belt[self.belt_cursor] is not None:
                dropped_name = get_item_display_name(inv.belt[self.belt_cursor])
                inv.belt[self.belt_cursor] = None
                self.feedback_message = f"Discarded {dropped_name}."
                self.feedback_success = True

    def _assign_to_belt(self, session: GameSession, belt_idx: int) -> None:
        """Assign currently selected pouch item to specific belt slot."""
        inv = session.player.inventory
        if self.active_pane == "POUCH" and self.pouch_cursor < len(inv.pouch):
            success, msg = inv.assign_pouch_to_belt(self.pouch_cursor, belt_idx)
            self.feedback_message = msg
            self.feedback_success = success

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Process keyboard shortcuts and mouse clicks for inventory."""
        if self.top_hud.handle_event(event, session):
            return

        inv = session.player.inventory

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_i):
                session.toggle_inventory()
                return

            # Cycle active pane with TAB
            elif event.key == pygame.K_TAB:
                order = ["POUCH", "EQUIPMENT", "BELT"]
                curr_idx = order.index(self.active_pane) if self.active_pane in order else 0
                self.active_pane = order[(curr_idx + 1) % len(order)]
                self.feedback_message = ""
                return

            # Directional Cursor Navigation
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                if self.active_pane == "POUCH":
                    self.pouch_cursor = (self.pouch_cursor - 1) % MAX_POUCH_SLOTS
                elif self.active_pane == "EQUIPMENT":
                    self.equip_cursor = (self.equip_cursor + 4) % 8
                elif self.active_pane == "BELT":
                    self.belt_cursor = (self.belt_cursor - 1) % MAX_BELT_SLOTS
            elif event.key in (pygame.K_RIGHT, pygame.K_d_key if hasattr(pygame, "K_d_key") else pygame.K_d) and event.key != pygame.K_d:
                pass
            elif event.key in (pygame.K_RIGHT,):
                if self.active_pane == "POUCH":
                    self.pouch_cursor = (self.pouch_cursor + 1) % MAX_POUCH_SLOTS
                elif self.active_pane == "EQUIPMENT":
                    self.equip_cursor = (self.equip_cursor + 4) % 8
                elif self.active_pane == "BELT":
                    self.belt_cursor = (self.belt_cursor + 1) % MAX_BELT_SLOTS
            elif event.key in (pygame.K_UP, pygame.K_w):
                if self.active_pane == "POUCH":
                    self.pouch_cursor = (self.pouch_cursor - 5) % MAX_POUCH_SLOTS
                elif self.active_pane == "EQUIPMENT":
                    col = 4 if self.equip_cursor >= 4 else 0
                    row = (self.equip_cursor - col - 1) % 4
                    self.equip_cursor = col + row
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                if self.active_pane == "POUCH":
                    self.pouch_cursor = (self.pouch_cursor + 5) % MAX_POUCH_SLOTS
                elif self.active_pane == "EQUIPMENT":
                    col = 4 if self.equip_cursor >= 4 else 0
                    row = (self.equip_cursor - col + 1) % 4
                    self.equip_cursor = col + row

            # Action Keys
            elif event.key in (pygame.K_e, pygame.K_RETURN):
                self._perform_equip_or_use(session)
            elif event.key == pygame.K_d:
                self._perform_drop(session)
            elif event.key in (pygame.K_1, pygame.K_KP1):
                self._assign_to_belt(session, 0)
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self._assign_to_belt(session, 1)
            elif event.key in (pygame.K_3, pygame.K_KP3):
                self._assign_to_belt(session, 2)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            curr_time = pygame.time.get_ticks() / 1000.0

            # 1. Equipment slot clicks -> unequip to pouch
            for idx, rect in enumerate(self.equip_rects):
                if rect.collidepoint(pos):
                    self.active_pane = "EQUIPMENT"
                    self.equip_cursor = idx
                    self._perform_equip_or_use(session)
                    return

            # 2. Belt slot clicks -> use or inspect
            for idx, rect in enumerate(self.belt_rects):
                if rect.collidepoint(pos):
                    self.active_pane = "BELT"
                    self.belt_cursor = idx
                    self._perform_equip_or_use(session)
                    return

            # 3. Pouch slot clicks -> equip or assign to belt
            for idx, rect in enumerate(self.pouch_rects):
                if rect.collidepoint(pos):
                    self.active_pane = "POUCH"
                    self.pouch_cursor = idx
                    self._perform_equip_or_use(session)
                    return

            # 4. Action button clicks
            if self.equip_btn_rect.collidepoint(pos):
                self._perform_equip_or_use(session)
                return
            elif self.b1_btn_rect.collidepoint(pos):
                self._assign_to_belt(session, 0)
                return
            elif self.b2_btn_rect.collidepoint(pos):
                self._assign_to_belt(session, 1)
                return
            elif self.b3_btn_rect.collidepoint(pos):
                self._assign_to_belt(session, 2)
                return
            elif self.drop_btn_rect.collidepoint(pos):
                self._perform_drop(session)
                return
            elif self.close_btn_rect.inflate(14, 10).collidepoint(pos):
                session.toggle_inventory()
                return
            elif pos[1] >= 56 and not pygame.Rect(8, 56, 944, 476).collidepoint(pos):
                session.toggle_inventory()
                return

    def update(self, dt: float, session: GameSession) -> None:
        """Update top status bar and check hovered buttons and slots."""
        pos = pygame.mouse.get_pos()
        self.top_hud.update(pos)

        # Hover inspection: preview item under cursor
        for idx, rect in enumerate(self.pouch_rects):
            if rect.collidepoint(pos) and idx < len(session.player.inventory.pouch):
                self.active_pane = "POUCH"
                self.pouch_cursor = idx
                break

        for idx, rect in enumerate(self.equip_rects):
            if rect.collidepoint(pos):
                self.active_pane = "EQUIPMENT"
                self.equip_cursor = idx
                break

        for idx, rect in enumerate(self.belt_rects):
            if rect.collidepoint(pos):
                self.active_pane = "BELT"
                self.belt_cursor = idx
                break

        if self.equip_btn_rect.collidepoint(pos):
            self._hovered_btn = "equip"
        elif self.b1_btn_rect.collidepoint(pos):
            self._hovered_btn = "b1"
        elif self.b2_btn_rect.collidepoint(pos):
            self._hovered_btn = "b2"
        elif self.b3_btn_rect.collidepoint(pos):
            self._hovered_btn = "b3"
        elif self.drop_btn_rect.collidepoint(pos):
            self._hovered_btn = "drop"
        elif self.close_btn_rect.collidepoint(pos):
            self._hovered_btn = "close"
        else:
            self._hovered_btn = None

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render complete 16-bit SNES inventory, equipment alcove, belt, and inspector."""
        w, h = surface.get_width(), surface.get_height()
        player = session.player
        inv = player.inventory
        biome = getattr(session.state, "current_biome", "arboretum")

        # Semi-transparent dark gothic backdrop over underlying view
        backdrop = pygame.Surface((w, h), pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, 155))
        surface.blit(backdrop, (0, 0))

        # Main Outer Window Frame (y = 56 to y = 530)
        outer_rect = pygame.Rect(8, 56, w - 16, h - 64)
        outer_frame = assets.get_9slice_frame(
            "frame_gold_ornate_hollow",
            outer_rect.width,
            outer_rect.height,
            margin=54,
            draw_center=False,
            edge_margin=24,
        )
        # Deep dark navy-black gothic fill
        bg_panel = pygame.Surface((outer_rect.width, outer_rect.height), pygame.SRCALPHA)
        bg_panel.fill((14, 12, 20, 245))
        surface.blit(bg_panel, outer_rect.topleft)

        if outer_frame:
            surface.blit(outer_frame, outer_rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), outer_rect, width=3, border_radius=6)

        # Top Status Bar
        self.top_hud.draw(surface, renderer, session)

        # =========================================================================
        # 1. UPPER LEFT: MANNEQUIN EQUIPMENT ALCOVE (w = 480, h = 244)
        # =========================================================================
        eq_rect = pygame.Rect(24, 70, 480, 244)
        eq_bg = pygame.Surface((eq_rect.width, eq_rect.height), pygame.SRCALPHA)
        eq_bg.fill((18, 16, 26, 230))
        surface.blit(eq_bg, eq_rect.topleft)

        eq_frame = assets.get_9slice_frame("frame_gold_clean", eq_rect.width, eq_rect.height, margin=23)
        if eq_frame:
            surface.blit(eq_frame, eq_rect.topleft)

        # Header Title
        helm_icon = assets.get_pyxel_icon(80, 8, size=(20, 20))
        if helm_icon:
            surface.blit(helm_icon, (eq_rect.x + 16, eq_rect.y + 10))
        renderer.draw_text(
            surface,
            "Hero Equipment",
            eq_rect.x + 48,
            eq_rect.y + 12,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=14,
            bold=True,
            font_variant="alagard",
        )

        # Center Stone Archway & Pedestal
        arch_cx = eq_rect.x + eq_rect.width // 2
        arch_w, arch_h = 130, 180
        arch_rect = pygame.Rect(arch_cx - arch_w // 2, eq_rect.y + 40, arch_w, arch_h)

        # Stone arch backdrop
        pygame.draw.rect(surface, (25, 22, 36), arch_rect, border_top_left_radius=60, border_top_right_radius=60)
        pygame.draw.rect(surface, (45, 40, 65), arch_rect, width=2, border_top_left_radius=60, border_top_right_radius=60)
        # Inner dark niche
        inner_niche = arch_rect.inflate(-16, -16)
        pygame.draw.rect(surface, (12, 10, 18), inner_niche, border_top_left_radius=50, border_top_right_radius=50)

        # Stone pedestal & shadow beneath hero
        ground_y = arch_rect.bottom - 16
        pygame.draw.ellipse(surface, (0, 0, 0, 130), (arch_cx - 40, ground_y - 6, 80, 14))

        # Standing Hero Character Sprite
        hero_sprite = assets.get_class_sprite(player.class_id)
        if hero_sprite:
            hw, hh = hero_sprite.get_size()
            target_h = 92
            target_w = max(1, int(hw * (target_h / hh)))
            hero_scaled = pygame.transform.smoothscale(hero_sprite, (target_w, target_h))
            surface.blit(hero_scaled, (arch_cx - target_w // 2, ground_y - target_h + 4))

        # Flanking 8 Equipment Slots (4 left, 4 right)
        self.equip_rects = []
        for i, slot in enumerate(self.EQUIP_SLOT_ORDER):
            is_right = (i >= 4)
            col_idx = i - 4 if is_right else i
            sx = eq_rect.x + 14 if not is_right else eq_rect.right - 164
            sy = eq_rect.y + 42 + col_idx * 48
            slot_rect = pygame.Rect(sx, sy, 150, 42)
            self.equip_rects.append(slot_rect)

            is_sel = (self.active_pane == "EQUIPMENT" and self.equip_cursor == i)
            equipped_item = inv.equipment.get(slot)

            # Slot background
            s_color = (32, 28, 48) if is_sel else (18, 16, 26)
            pygame.draw.rect(surface, s_color, slot_rect, border_radius=4)
            border_color = (255, 220, 40) if is_sel else ((140, 145, 175) if equipped_item else (55, 50, 75))
            pygame.draw.rect(surface, border_color, slot_rect, width=1 if not is_sel else 2, border_radius=4)

            # 32x32 Square Icon Frame
            ib_rect = pygame.Rect(slot_rect.x + 5, slot_rect.y + 5, 32, 32)
            pygame.draw.rect(surface, (12, 10, 18), ib_rect, border_radius=2)
            ib_frame = assets.get_9slice_frame("frame_button_gold", 32, 32, margin=8)
            if ib_frame:
                surface.blit(ib_frame, ib_rect.topleft)

            if equipped_item:
                # Tier stripe on slot
                tier = getattr(equipped_item, "tier", 1)
                tcolor = self.TIER_COLORS.get(tier, (180, 185, 195))
                pygame.draw.rect(surface, tcolor, (slot_rect.x + 2, slot_rect.y + 6, 2, slot_rect.height - 12))

                item_icon = self._get_item_icon(equipped_item)
                if item_icon:
                    surface.blit(item_icon, (ib_rect.centerx - item_icon.get_width() // 2, ib_rect.centery - item_icon.get_height() // 2))
            else:
                # Default silhouette icon
                faint_icon = self._get_slot_default_icon(slot)
                if faint_icon:
                    surface.blit(faint_icon, (ib_rect.centerx - faint_icon.get_width() // 2, ib_rect.centery - faint_icon.get_height() // 2))

            # Slot text labels
            tx = slot_rect.x + 42
            slot_name = self.SLOT_NAMES[slot]
            name_color = ThemeToken.TEXT_HIGHLIGHT if is_sel else ThemeToken.TEXT_NORMAL
            renderer.draw_text(
                surface,
                slot_name,
                tx,
                slot_rect.y + 5,
                token=name_color,
                size=11,
                bold=True,
                font_variant="alagard",
            )
            if equipped_item:
                item_name = get_item_display_name(equipped_item)
                renderer.draw_text(
                    surface,
                    item_name[:12],
                    tx,
                    slot_rect.y + 22,
                    token=ThemeToken.TEXT_SUCCESS,
                    size=11,
                    bold=False,
                    font_variant="alagard",
                )
            else:
                renderer.draw_text(
                    surface,
                    "(Empty)",
                    tx,
                    slot_rect.y + 22,
                    token=ThemeToken.TEXT_MUTED,
                    size=10,
                    bold=False,
                    font_variant="alagard",
                )

        # =========================================================================
        # 2. UPPER RIGHT: ITEM INSPECTOR DETAIL PANEL (w = 420, h = 244)
        # =========================================================================
        ins_rect = pygame.Rect(516, 70, 420, 244)
        ins_bg = pygame.Surface((ins_rect.width, ins_rect.height), pygame.SRCALPHA)
        ins_bg.fill((18, 16, 26, 240))
        surface.blit(ins_bg, ins_rect.topleft)

        ins_frame = assets.get_9slice_frame("frame_gold_clean", ins_rect.width, ins_rect.height, margin=23)
        if ins_frame:
            surface.blit(ins_frame, ins_rect.topleft)

        curr_item, curr_type = self._get_selected_item(session)

        # Large 48x48 Icon Showcase Box
        fx, fy = ins_rect.x + 18, ins_rect.y + 16
        icon_showcase = pygame.Rect(fx, fy, 48, 48)
        pygame.draw.rect(surface, (12, 10, 18), icon_showcase, border_radius=4)
        ib_frame = assets.get_9slice_frame("frame_button_gold", 48, 48, margin=12)
        if ib_frame:
            surface.blit(ib_frame, icon_showcase.topleft)

        if curr_item:
            showcase_icon = self._get_item_icon(curr_item)
            if showcase_icon:
                scaled_icon = pygame.transform.scale(showcase_icon, (36, 36))
                surface.blit(scaled_icon, (icon_showcase.centerx - 18, icon_showcase.centery - 18))

            display_name = get_item_display_name(curr_item)
            renderer.draw_text(
                surface,
                display_name,
                ins_rect.x + 76,
                ins_rect.y + 16,
                token=ThemeToken.TEXT_HIGHLIGHT,
                size=16,
                bold=True,
                font_variant="alagard",
            )

            tier = getattr(curr_item, "tier", 1)
            tier_name = f"Tier {tier}  *  {curr_type}"
            renderer.draw_text(
                surface,
                tier_name,
                ins_rect.x + 76,
                ins_rect.y + 40,
                token=ThemeToken.TEXT_MUTED,
                size=12,
                font_variant="alagard",
            )
        else:
            renderer.draw_text(
                surface,
                "Empty Slot",
                ins_rect.x + 76,
                ins_rect.y + 16,
                token=ThemeToken.TEXT_MUTED,
                size=16,
                bold=True,
                font_variant="alagard",
            )
            renderer.draw_text(
                surface,
                curr_type,
                ins_rect.x + 76,
                ins_rect.y + 40,
                token=ThemeToken.TEXT_MUTED,
                size=12,
                font_variant="alagard",
            )

        # Stat Divider line
        div_y = ins_rect.y + 72
        pygame.draw.line(surface, (70, 75, 105), (ins_rect.x + 18, div_y), (ins_rect.right - 18, div_y))

        # Stats Breakdown
        stat_y = div_y + 10
        if isinstance(curr_item, EquipmentItem):
            stats = curr_item.stats_bonus
            parts = []
            if stats.attack != 0:
                parts.append(f"ATK : +{stats.attack}" if stats.attack > 0 else f"ATK : {stats.attack}")
            if stats.defense != 0:
                parts.append(f"DEF : +{stats.defense}" if stats.defense > 0 else f"DEF : {stats.defense}")
            if stats.speed != 0:
                parts.append(f"SPD : +{stats.speed}" if stats.speed > 0 else f"SPD : {stats.speed}")
            if stats.max_hp != 0:
                parts.append(f"HP  : +{stats.max_hp}" if stats.max_hp > 0 else f"HP  : {stats.max_hp}")
            if stats.crit_chance > 0:
                parts.append(f"CRIT: +{int(stats.crit_chance * 100)}%")

            for p_line in parts:
                renderer.draw_text(
                    surface,
                    p_line,
                    ins_rect.x + 20,
                    stat_y,
                    token=ThemeToken.TEXT_NORMAL,
                    size=12,
                    bold=True,
                    font_variant="alagard",
                )
                stat_y += 16

            # Comparison vs equipped if pouch item is selected
            if self.active_pane == "POUCH":
                equipped_gear = inv.equipment.get(curr_item.slot)
                if equipped_gear:
                    cstats = equipped_gear.stats_bonus
                    diffs = []
                    d_atk = stats.attack - cstats.attack
                    d_def = stats.defense - cstats.defense
                    d_spd = stats.speed - cstats.speed
                    d_hp = stats.max_hp - cstats.max_hp

                    if d_atk != 0:
                        diffs.append(f"{'+' if d_atk > 0 else ''}{d_atk} ATK")
                    if d_def != 0:
                        diffs.append(f"{'+' if d_def > 0 else ''}{d_def} DEF")
                    if d_spd != 0:
                        diffs.append(f"{'+' if d_spd > 0 else ''}{d_spd} SPD")
                    if d_hp != 0:
                        diffs.append(f"{'+' if d_hp > 0 else ''}{d_hp} HP")

                    if diffs:
                        comp_str = f"vs equipped: {', '.join(diffs)}"
                        token = ThemeToken.TEXT_SUCCESS if any("+" in d for d in diffs) else ThemeToken.TEXT_ALERT
                    else:
                        comp_str = "vs equipped: identical stats"
                        token = ThemeToken.TEXT_MUTED
                else:
                    comp_str = "vs equipped: empty slot"
                    token = ThemeToken.ACCENT_PRIMARY

                renderer.draw_text(
                    surface,
                    f"({comp_str})",
                    ins_rect.x + 20,
                    stat_y,
                    token=token,
                    size=11,
                    bold=False,
                    font_variant="alagard",
                )
                stat_y += 16

        elif isinstance(curr_item, ConsumableItem):
            if isinstance(curr_item, StatPotion):
                b = curr_item.stat_bonus
                if b.attack > 0:
                    renderer.draw_text(surface, f"Permanent ATK: +{b.attack}", ins_rect.x + 20, stat_y, token=ThemeToken.TEXT_SUCCESS, size=13, bold=True, font_variant="alagard")
                    stat_y += 18
                if b.defense > 0:
                    renderer.draw_text(surface, f"Permanent DEF: +{b.defense}", ins_rect.x + 20, stat_y, token=ThemeToken.TEXT_SUCCESS, size=13, bold=True, font_variant="alagard")
                    stat_y += 18
            else:
                renderer.draw_text(surface, f"HEAL: +{curr_item.heal_amount} HP", ins_rect.x + 20, stat_y, token=ThemeToken.TEXT_SUCCESS, size=13, bold=True, font_variant="alagard")
                stat_y += 18

        # Description Divider
        desc_div_y = max(stat_y + 4, ins_rect.y + 148)
        pygame.draw.line(surface, (50, 48, 70), (ins_rect.x + 18, desc_div_y), (ins_rect.right - 18, desc_div_y))

        # Description text
        desc_y = desc_div_y + 8
        if curr_item:
            desc_text = get_item_display_desc(curr_item)
            # Wrap text manually
            words = desc_text.split()
            lines = []
            cur_line = ""
            for word in words:
                test_line = f"{cur_line} {word}".strip()
                if len(test_line) > 42:
                    lines.append(cur_line)
                    cur_line = word
                else:
                    cur_line = test_line
            if cur_line:
                lines.append(cur_line)

            for d_line in lines[:4]:
                renderer.draw_text(surface, d_line, ins_rect.x + 20, desc_y, token=ThemeToken.TEXT_MUTED, size=11, font_variant="alagard")
                desc_y += 16
        else:
            renderer.draw_text(
                surface,
                "Select an item from your pouch, equipment, or belt to view details.",
                ins_rect.x + 20,
                desc_y,
                token=ThemeToken.TEXT_MUTED,
                size=11,
                font_variant="alagard",
            )

        # =========================================================================
        # 3. LOWER LEFT: 3-SLOT BELT PANEL (w = 340, h = 152)
        # =========================================================================
        belt_panel = pygame.Rect(24, 322, 340, 150)
        bp_bg = pygame.Surface((belt_panel.width, belt_panel.height), pygame.SRCALPHA)
        bp_bg.fill((18, 16, 26, 230))
        surface.blit(bp_bg, belt_panel.topleft)

        bp_frame = assets.get_9slice_frame("frame_gold_clean", belt_panel.width, belt_panel.height, margin=23)
        if bp_frame:
            surface.blit(bp_frame, belt_panel.topleft)

        # Header Title
        pot_icon = assets.get_item_icon("potion_health", size=(16, 16))
        if pot_icon:
            surface.blit(pot_icon, (belt_panel.x + 16, belt_panel.y + 10))
        belt_count = sum(1 for b in inv.belt if b is not None)
        renderer.draw_text(
            surface,
            f"Belt Slots ({belt_count}/3)",
            belt_panel.x + 38,
            belt_panel.y + 10,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=13,
            bold=True,
            font_variant="alagard",
        )

        self.belt_rects = []
        for b_idx in range(MAX_BELT_SLOTS):
            bx = belt_panel.x + 14 + b_idx * 105
            by = belt_panel.y + 36
            bw, bh = 98, 100
            b_card = pygame.Rect(bx, by, bw, bh)
            self.belt_rects.append(b_card)

            is_sel = (self.active_pane == "BELT" and self.belt_cursor == b_idx)
            b_item = inv.belt[b_idx]

            # Background & border
            b_color = (30, 26, 44) if is_sel else (18, 16, 26)
            pygame.draw.rect(surface, b_color, b_card, border_radius=4)
            b_border = (255, 220, 40) if is_sel else ((140, 145, 175) if b_item else (55, 50, 75))
            pygame.draw.rect(surface, b_border, b_card, width=1 if not is_sel else 2, border_radius=4)

            # Slot hotkey badge [1], [2], [3]
            renderer.draw_text(
                surface,
                f"[{b_idx + 1}]",
                b_card.centerx,
                b_card.y + 6,
                token=ThemeToken.TEXT_HIGHLIGHT if is_sel else ThemeToken.TEXT_MUTED,
                size=12,
                bold=True,
                align="center",
                font_variant="alagard",
            )

            # Square Icon Box
            bi_rect = pygame.Rect(b_card.centerx - 18, b_card.y + 24, 36, 36)
            pygame.draw.rect(surface, (12, 10, 18), bi_rect, border_radius=2)
            bi_frame = assets.get_9slice_frame("frame_button_gold", 36, 36, margin=8)
            if bi_frame:
                surface.blit(bi_frame, bi_rect.topleft)

            if b_item:
                b_icon = self._get_item_icon(b_item)
                if b_icon:
                    surface.blit(b_icon, (bi_rect.centerx - b_icon.get_width() // 2, bi_rect.centery - b_icon.get_height() // 2))

                b_name = get_item_display_name(b_item)
                renderer.draw_text(surface, b_name[:9], b_card.centerx, b_card.y + 66, token=ThemeToken.TEXT_NORMAL, size=11, bold=True, align="center", font_variant="alagard")
                effect_str = f"+{b_item.heal_amount}HP" if getattr(b_item, "heal_amount", 0) > 0 else "Buff"
                renderer.draw_text(surface, effect_str, b_card.centerx, b_card.y + 82, token=ThemeToken.TEXT_SUCCESS, size=11, align="center", font_variant="alagard")
            else:
                renderer.draw_text(surface, "[Empty]", b_card.centerx, b_card.y + 72, token=ThemeToken.TEXT_MUTED, size=11, align="center", font_variant="alagard")

        # =========================================================================
        # 4. LOWER RIGHT: 10-SLOT POUCH GRID (w = 560, h = 152)
        # =========================================================================
        pouch_panel = pygame.Rect(376, 322, 560, 150)
        po_bg = pygame.Surface((pouch_panel.width, pouch_panel.height), pygame.SRCALPHA)
        po_bg.fill((18, 16, 26, 230))
        surface.blit(po_bg, pouch_panel.topleft)

        po_frame = assets.get_9slice_frame("frame_gold_clean", pouch_panel.width, pouch_panel.height, margin=23)
        if po_frame:
            surface.blit(po_frame, pouch_panel.topleft)

        # Header Title
        pouch_icon = assets.get_pyxel_icon(104, 0, size=(16, 16))
        if pouch_icon:
            surface.blit(pouch_icon, (pouch_panel.x + 16, pouch_panel.y + 10))
        pouch_count = len(inv.pouch)
        renderer.draw_text(
            surface,
            f"Pouch Inventory ({pouch_count}/10)",
            pouch_panel.x + 38,
            pouch_panel.y + 10,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=13,
            bold=True,
            font_variant="alagard",
        )

        self.pouch_rects = []
        for p_idx in range(MAX_POUCH_SLOTS):
            col = p_idx % 5
            row = p_idx // 5
            px = pouch_panel.x + 20 + col * 105
            py = pouch_panel.y + 36 + row * 52
            pw, ph = 96, 46
            p_card = pygame.Rect(px, py, pw, ph)
            self.pouch_rects.append(p_card)

            is_sel = (self.active_pane == "POUCH" and self.pouch_cursor == p_idx)
            has_item = p_idx < len(inv.pouch)
            p_item = inv.pouch[p_idx] if has_item else None

            # Slot background & border
            p_color = (32, 28, 48) if is_sel else (18, 16, 26)
            pygame.draw.rect(surface, p_color, p_card, border_radius=4)
            p_border = (255, 220, 40) if is_sel else ((140, 145, 175) if has_item else (55, 50, 75))
            pygame.draw.rect(surface, p_border, p_card, width=1 if not is_sel else 2, border_radius=4)

            # Square Icon Box
            pi_rect = pygame.Rect(p_card.x + 5, p_card.y + 5, 36, 36)
            pygame.draw.rect(surface, (12, 10, 18), pi_rect, border_radius=2)
            pi_frame = assets.get_9slice_frame("frame_button_gold", 36, 36, margin=8)
            if pi_frame:
                surface.blit(pi_frame, pi_rect.topleft)

            if has_item and p_item:
                tier = getattr(p_item, "tier", 1)
                tcolor = self.TIER_COLORS.get(tier, (180, 185, 195))
                pygame.draw.rect(surface, tcolor, (p_card.x + 2, p_card.y + 6, 2, p_card.height - 12))

                p_icon = self._get_item_icon(p_item)
                if p_icon:
                    surface.blit(p_icon, (pi_rect.centerx - p_icon.get_width() // 2, pi_rect.centery - p_icon.get_height() // 2))

                p_name = get_item_display_name(p_item)
                renderer.draw_text(surface, p_name[:8], p_card.x + 46, p_card.y + 8, token=ThemeToken.TEXT_NORMAL, size=11, bold=True, font_variant="alagard")
                
                # Subtitle (Slot or consumable)
                sub_txt = t(f"slot_{p_item.slot.name.lower()}") if isinstance(p_item, EquipmentItem) else "Consumable"
                renderer.draw_text(surface, sub_txt[:9], p_card.x + 46, p_card.y + 24, token=ThemeToken.TEXT_MUTED, size=10, font_variant="alagard")
            else:
                renderer.draw_text(surface, f"[{p_idx + 1}]", p_card.x + 46, p_card.y + 16, token=ThemeToken.TEXT_MUTED, size=11, font_variant="alagard")

        # =========================================================================
        # 5. BOTTOM ACTION CONTROLS BAR (y = 478 to y = 520)
        # =========================================================================
        # Feedback message
        if self.feedback_message:
            f_color = ThemeToken.TEXT_SUCCESS if self.feedback_success else ThemeToken.TEXT_ALERT
            renderer.draw_text(
                surface,
                self.feedback_message,
                32,
                488,
                token=f_color,
                size=13,
                bold=True,
                font_variant="alagard",
            )

        # ⚔ [ EQUIP / USE ] Button
        eq_btn = self.equip_btn_rect
        eq_frame = assets.get_9slice_frame("frame_button_gold", eq_btn.width, eq_btn.height, margin=16)
        eq_bg = pygame.Surface((eq_btn.width, eq_btn.height), pygame.SRCALPHA)
        eq_bg.fill((16, 14, 24, 240) if self._hovered_btn != "equip" else (35, 30, 50, 250))
        surface.blit(eq_bg, eq_btn.topleft)
        if eq_frame:
            surface.blit(eq_frame, eq_btn.topleft)
        renderer.draw_text(
            surface,
            "[ EQUIP / USE ]",
            eq_btn.centerx,
            eq_btn.y + 8,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=12,
            bold=True,
            align="center",
            font_variant="alagard",
        )

        # Quick Belt Assign Buttons: B1, B2, B3
        for b_num, b_rect, b_id in [(1, self.b1_btn_rect, "b1"), (2, self.b2_btn_rect, "b2"), (3, self.b3_btn_rect, "b3")]:
            b_frame = assets.get_9slice_frame("frame_button_gold", b_rect.width, b_rect.height, margin=10)
            b_bg = pygame.Surface((b_rect.width, b_rect.height), pygame.SRCALPHA)
            b_bg.fill((16, 14, 24, 240) if self._hovered_btn != b_id else (35, 30, 50, 250))
            surface.blit(b_bg, b_rect.topleft)
            if b_frame:
                surface.blit(b_frame, b_rect.topleft)
            renderer.draw_text(
                surface,
                f"B{b_num}",
                b_rect.centerx,
                b_rect.y + 8,
                token=ThemeToken.TEXT_NORMAL,
                size=12,
                bold=True,
                align="center",
                font_variant="alagard",
            )

        # ↓ [ DROP ] Button
        dr_btn = self.drop_btn_rect
        dr_frame = assets.get_9slice_frame("frame_button_gold", dr_btn.width, dr_btn.height, margin=14)
        dr_bg = pygame.Surface((dr_btn.width, dr_btn.height), pygame.SRCALPHA)
        dr_bg.fill((16, 14, 24, 240) if self._hovered_btn != "drop" else (35, 30, 50, 250))
        surface.blit(dr_bg, dr_btn.topleft)
        if dr_frame:
            surface.blit(dr_frame, dr_btn.topleft)
        renderer.draw_text(
            surface,
            "[ DROP ]",
            dr_btn.centerx,
            dr_btn.y + 8,
            token=ThemeToken.TEXT_ALERT,
            size=12,
            bold=True,
            align="center",
            font_variant="alagard",
        )

        # ✕ [ CLOSE ] Button
        cl_btn = self.close_btn_rect
        cl_frame = assets.get_9slice_frame("frame_button_gold", cl_btn.width, cl_btn.height, margin=14)
        cl_bg = pygame.Surface((cl_btn.width, cl_btn.height), pygame.SRCALPHA)
        cl_bg.fill((16, 14, 24, 240) if self._hovered_btn != "close" else (35, 30, 50, 250))
        surface.blit(cl_bg, cl_btn.topleft)
        if cl_frame:
            surface.blit(cl_frame, cl_btn.topleft)
        renderer.draw_text(
            surface,
            "[ CLOSE ]",
            cl_btn.centerx,
            cl_btn.y + 8,
            token=ThemeToken.TEXT_NORMAL,
            size=12,
            bold=True,
            align="center",
            font_variant="alagard",
        )
