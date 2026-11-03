"""Pygame-CE Loot & Spoils Reward View.

Faithfully implements the 16-bit Super Nintendo JRPG loot / spoils design:
- Reusable Top Status Bar (TopHUDComponent)
- Biome map background dimmed over the entire viewport
- Centered ornate treasure alcove with fitted combat arena background
- Golden treasure chest overflowing with coins, jewels, and sword
- Victory & Spoils of Battle header banner plaque
- Rewards status panel with EXP Gained (progress bar), Gold, and Pouch Space
- Item cards with tier color bands, icons (SNES potions & Pyxel equipment fallback),
  stats granted, and live stat comparisons vs currently equipped gear
- Bottom action controls: Take Item hotkeys [1-3], [ SPACE ] TAKE ALL, [ C ] CONTINUE
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame

from src.core.commands import TakeLootCommand, TakeAllLootCommand
from src.core.game_state import GameMode
from src.core.i18n import t, i18n
from src.core.theme import ThemeToken
from src.entities.item import EquipmentItem, ConsumableItem
from src.data.items import StatPotion
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.components.top_hud import TopHUDComponent
from src.frontends.pygame_ce.views.base import PygameView
from src.systems.inventory import MAX_POUCH_SLOTS
from src.systems.loot_service import LootService

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


def get_fitted_surface(src_surf: pygame.Surface, target_w: int, target_h: int) -> pygame.Surface:
    """Scale uniformly (preserving aspect ratio, zero distortion) and crop center to fit target dimensions."""
    sw, sh = src_surf.get_size()
    scale = max(target_w / sw, target_h / sh)
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    scaled = pygame.transform.smoothscale(src_surf, (nw, nh))
    ox = (nw - target_w) // 2
    oy = (nh - target_h) // 2
    return scaled.subsurface((ox, oy, target_w, target_h))


def draw_hanging_banner(surface: pygame.Surface, x: int, y: int, w: int = 24, h: int = 56) -> None:
    """Draw classic Super Nintendo gothic hanging crimson banner with golden cross."""
    banner_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    # Crimson red base
    pygame.draw.rect(banner_surf, (155, 22, 44), (0, 0, w, h - 8))
    # Triangular point at bottom
    pygame.draw.polygon(banner_surf, (155, 22, 44), [(0, h - 8), (w // 2, h), (w, h - 8)])
    # Gold border
    pygame.draw.lines(
        banner_surf,
        (220, 180, 50),
        False,
        [(0, 0), (0, h - 8), (w // 2, h - 1), (w - 1, h - 8), (w - 1, 0)],
        width=1,
    )
    # Gold cross insignia in center
    cx, cy = w // 2, (h - 8) // 2
    pygame.draw.rect(banner_surf, (255, 230, 80), (cx - 2, cy - 8, 4, 16))
    pygame.draw.rect(banner_surf, (255, 230, 80), (cx - 6, cy - 4, 12, 4))
    surface.blit(banner_surf, (x, y))


class PygameLootView(PygameView):
    """Authentic 16-bit SNES post-combat loot & spoils reward view."""

    TIER_COLORS = {
        1: (180, 185, 195),  # Common (Silver/Gray)
        2: (80, 220, 100),   # Uncommon (Lime Green)
        3: (40, 170, 255),   # Rare (Sapphire Cyan)
        4: (190, 80, 240),   # Epic (Mystic Purple)
        5: (255, 190, 40),   # Legendary (Radiant Gold)
    }

    def __init__(self) -> None:
        self.top_hud = TopHUDComponent()
        self._hovered_btn: str | None = None
        self._selected_card_idx: int = 0

        # Action button rects
        self.take_all_btn_rect = pygame.Rect(380, 474, 180, 36)
        self.cont_btn_rect = pygame.Rect(580, 474, 180, 36)
        card_w = 720
        card_h = 56
        card_spacing = 6
        start_y = 286
        self.card_rects: list[pygame.Rect] = [
            pygame.Rect(120, start_y + i * (card_h + card_spacing), card_w, card_h)
            for i in range(3)
        ]
        self.no_loot_rect = pygame.Rect(120, start_y + 10, card_w, 70)

    def _get_item_icon(self, item) -> pygame.Surface | None:
        """Resolve authentic icon for item: SNES potions or Pyxel retro equipment."""
        if isinstance(item, ConsumableItem):
            if isinstance(item, StatPotion) or getattr(item, "stat_bonus", None):
                # Stat potion -> item_potion_mana
                return assets.get_item_icon("potion_mana", size=(28, 28))
            else:
                # HP potion -> item_potion_health
                return assets.get_item_icon("potion_health", size=(28, 28))

        # Equipment / other items -> Pyxel Bank 0 coordinate
        iid = item.id.lower()
        if any(k in iid for k in ("sword", "broadsword", "claymore", "cleaver", "worldbreaker", "blade")):
            coord = (72, 0)
        elif any(k in iid for k in ("shield", "buckler", "bastion")):
            coord = (80, 0)
        elif any(k in iid for k in ("helmet", "cowl", "sallet", "cap", "coif", "helm")):
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

    def _exit_loot(self, session: GameSession) -> None:
        """Advance past the rewards screen into promotion, draft, or map."""
        try:
            from src.core.events import AudioCue, event_bus
            event_bus.emit_audio(AudioCue.CLICK)
        except Exception:
            pass

        next_mode = LootService.resolve_exit_mode(session.player)
        if next_mode == GameMode.PROMOTION:
            if session.state.begin_promotion(GameMode.LOOT):
                return
        elif next_mode == GameMode.ABILITY_CHOICE:
            session.state.switch_mode(GameMode.ABILITY_CHOICE)
            return

        session.state.continue_after_rewards()

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Process keyboard shortcuts and mouse/touch interaction for loot collection."""
        # Top HUD handles inventory/char buttons unless key is 'C' (reserved for Loot Continue)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
            pass
        elif self.top_hud.handle_event(event, session):
            return

        pending = session.state.pending_loot

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_1, pygame.K_KP1) and len(pending) > 0:
                session.dispatch(TakeLootCommand(loot_index=0))
                if not session.state.pending_loot:
                    self._exit_loot(session)
            elif event.key in (pygame.K_2, pygame.K_KP2) and len(pending) > 1:
                session.dispatch(TakeLootCommand(loot_index=1))
                if not session.state.pending_loot:
                    self._exit_loot(session)
            elif event.key in (pygame.K_3, pygame.K_KP3) and len(pending) > 2:
                session.dispatch(TakeLootCommand(loot_index=2))
                if not session.state.pending_loot:
                    self._exit_loot(session)
            elif event.key == pygame.K_SPACE:
                if pending:
                    session.dispatch(TakeAllLootCommand())
                    if not session.state.pending_loot:
                        self._exit_loot(session)
                else:
                    self._exit_loot(session)
            elif event.key in (pygame.K_RETURN, pygame.K_c):
                self._exit_loot(session)

        elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1) or \
             (event.type == pygame.MOUSEBUTTONUP and event.button == 1):
            pos = event.pos

            # If all loot has been claimed, tapping anywhere on the stage advances
            if not pending:
                if pos[1] >= 56:
                    self._exit_loot(session)
                    return

            # Check item card clicks (generous hit target for mobile touch)
            for idx, rect in enumerate(self.card_rects):
                if rect.inflate(16, 12).collidepoint(pos) and idx < len(pending):
                    session.dispatch(TakeLootCommand(loot_index=idx))
                    if not session.state.pending_loot:
                        self._exit_loot(session)
                    return

            # Check Take All button
            if self.take_all_btn_rect.inflate(20, 20).collidepoint(pos):
                if pending:
                    session.dispatch(TakeAllLootCommand())
                    if not session.state.pending_loot:
                        self._exit_loot(session)
                else:
                    self._exit_loot(session)
                return

            # Check Continue button (generous bounds + full bottom-right action area)
            if self.cont_btn_rect.inflate(30, 24).collidepoint(pos) or (pos[0] >= 550 and pos[1] >= 450):
                self._exit_loot(session)
                return

    def update(self, dt: float, session: GameSession) -> None:
        """Update TopHUD and check hover highlights."""
        pos = pygame.mouse.get_pos()
        self.top_hud.update(pos)

        if self.take_all_btn_rect.inflate(10, 10).collidepoint(pos):
            self._hovered_btn = "take_all"
        elif self.cont_btn_rect.inflate(10, 10).collidepoint(pos):
            self._hovered_btn = "continue"
        else:
            self._hovered_btn = None

        # Check card hover
        self._selected_card_idx = 0
        for idx, rect in enumerate(self.card_rects):
            if rect.collidepoint(pos):
                self._selected_card_idx = idx
                break

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render complete 16-bit SNES spoils of battle reward screen."""
        w, h = surface.get_width(), surface.get_height()
        biome = getattr(session.state, "current_biome", "arboretum")
        pending = session.state.pending_loot
        player = session.player

        # =========================================================================
        # 1. BIOME MAP BACKGROUND (DIMMED)
        # =========================================================================
        bg_surf = assets.background_surfaces.get(biome.lower())
        if bg_surf:
            scaled_bg = pygame.transform.smoothscale(bg_surf, (w, h))
            surface.blit(scaled_bg, (0, 0))
        else:
            surface.fill((12, 10, 16))

        # Dim biome map background slightly so gold frames and chest pop cleanly
        dim_overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        dim_overlay.fill((0, 0, 0, 135))
        surface.blit(dim_overlay, (0, 0))

        # Main outer ornate gold frame (y = 56 to y = 530)
        outer_rect = pygame.Rect(8, 56, w - 16, h - 64)
        outer_frame = assets.get_9slice_frame(
            "frame_gold_ornate_hollow",
            outer_rect.width,
            outer_rect.height,
            margin=54,
            draw_center=False,
            edge_margin=24,
        )
        if outer_frame:
            surface.blit(outer_frame, outer_rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), outer_rect, width=3, border_radius=6)

        # Top HUD Status Bar
        self.top_hud.draw(surface, renderer, session)

        # =========================================================================
        # 2. REWARDS WINDOW / CHEST VIEWPORT (Fitted Combat Arena Background)
        # =========================================================================
        chest_rect = pygame.Rect(120, 68, 720, 154)

        # Draw fitted combat arena vista (aspect-ratio preserving crop, zero distortion)
        arena_src = assets.get_combat_arena_bg(biome)
        if arena_src:
            fitted_arena = get_fitted_surface(arena_src, chest_rect.width, chest_rect.height)
            surface.blit(fitted_arena, chest_rect.topleft)
        else:
            pygame.draw.rect(surface, (18, 15, 25), chest_rect)

        # Hanging crimson banners with golden crosses
        draw_hanging_banner(surface, chest_rect.x + 36, chest_rect.y + 4, w=22, h=52)
        draw_hanging_banner(surface, chest_rect.right - 58, chest_rect.y + 4, w=22, h=52)

        # Open Golden Treasure Chest with Gold & Sparkles
        chest_surf = assets.get_ui_component("chest_spoils")
        if chest_surf:
            cw, ch = chest_surf.get_size()
            cx = chest_rect.centerx - cw // 2
            cy = chest_rect.bottom - ch - 4
            surface.blit(chest_surf, (cx, cy))

        # Header Banner Plaque: "VICTORY! / Spoils of Battle"
        plaque_rect = pygame.Rect(chest_rect.centerx - 170, chest_rect.y + 12, 340, 46)
        plaque_bg = pygame.Surface((plaque_rect.width, plaque_rect.height), pygame.SRCALPHA)
        plaque_bg.fill((16, 14, 24, 240))
        surface.blit(plaque_bg, plaque_rect.topleft)

        plaque_frame = assets.get_9slice_frame("frame_button_gold", plaque_rect.width, plaque_rect.height, margin=20)
        if plaque_frame:
            surface.blit(plaque_frame, plaque_rect.topleft)

        v_title = "+  VICTORY!  +" if i18n.locale == "en" else "+  ¡VICTORIA!  +"
        v_sub = "Spoils of Battle" if i18n.locale == "en" else "Botín de batalla"
        renderer.draw_text(
            surface,
            v_title,
            plaque_rect.centerx,
            plaque_rect.y + 7,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=16,
            bold=True,
            align="center",
            font_variant="alagard",
        )
        renderer.draw_text(
            surface,
            v_sub,
            plaque_rect.centerx,
            plaque_rect.y + 26,
            token=ThemeToken.TEXT_NORMAL,
            size=12,
            align="center",
            font_variant="alagard",
        )

        # Frame around chest viewport
        chest_frame = assets.get_9slice_frame(
            "frame_gold_ornate_hollow",
            chest_rect.width,
            chest_rect.height,
            margin=40,
            draw_center=False,
            edge_margin=20,
        )
        if chest_frame:
            surface.blit(chest_frame, chest_rect.topleft)

        # =========================================================================
        # 3. REWARDS SUMMARY STATUS PANEL (EXP, Gold, Pouch Space)
        # =========================================================================
        sum_rect = pygame.Rect(120, 228, 720, 52)
        s_bg = pygame.Surface((sum_rect.width, sum_rect.height), pygame.SRCALPHA)
        s_bg.fill((18, 16, 28, 240))
        surface.blit(s_bg, sum_rect.topleft)

        s_frame = assets.get_9slice_frame("frame_gold_clean", sum_rect.width, sum_rect.height, margin=23)
        if s_frame:
            surface.blit(s_frame, sum_rect.topleft)

        col_w = sum_rect.width // 3
        # Vertical Dividers
        pygame.draw.line(surface, (70, 75, 105), (sum_rect.x + col_w, sum_rect.y + 8), (sum_rect.x + col_w, sum_rect.bottom - 8))
        pygame.draw.line(surface, (70, 75, 105), (sum_rect.x + col_w * 2, sum_rect.y + 8), (sum_rect.x + col_w * 2, sum_rect.bottom - 8))

        # Column 1: EXP Gained & Progress Bar
        c1_x = sum_rect.x + 16
        # 4-point sparkle icon
        pygame.draw.polygon(
            surface,
            (255, 230, 40),
            [(c1_x + 6, sum_rect.y + 10), (c1_x + 10, sum_rect.y + 14), (c1_x + 6, sum_rect.y + 18), (c1_x + 2, sum_rect.y + 14)],
        )
        pygame.draw.line(surface, (255, 255, 255), (c1_x + 6, sum_rect.y + 12), (c1_x + 6, sum_rect.y + 16))
        pygame.draw.line(surface, (255, 255, 255), (c1_x + 4, sum_rect.y + 14), (c1_x + 8, sum_rect.y + 14))

        exp_earned = getattr(session.state, "last_exp_earned", 0)
        renderer.draw_text(surface, "EXP Gained:", c1_x + 16, sum_rect.y + 8, token=ThemeToken.TEXT_NORMAL, size=12, bold=True, font_variant="alagard")
        renderer.draw_text(surface, str(exp_earned), c1_x + 16, sum_rect.y + 24, token=ThemeToken.TEXT_HIGHLIGHT, size=14, bold=True, font_variant="alagard")
        # Mini EXP bar
        bar_x = c1_x + 60
        bar_w = col_w - 85
        pygame.draw.rect(surface, (20, 22, 34), (bar_x, sum_rect.y + 29, bar_w, 6), border_radius=2)
        exp_ratio = min(1.0, max(0.0, player.experience / max(1, player.exp_to_next_level)))
        if exp_ratio > 0:
            pygame.draw.rect(surface, (41, 173, 255), (bar_x, sum_rect.y + 29, max(2, int(bar_w * exp_ratio)), 6), border_radius=2)
        pygame.draw.rect(surface, (120, 130, 160), (bar_x, sum_rect.y + 29, bar_w, 6), width=1, border_radius=2)

        # Column 2: Gold Earned
        c2_x = sum_rect.x + col_w + 20
        gold_icon = assets.get_pyxel_icon(40, 24, size=(20, 20))
        if gold_icon:
            surface.blit(gold_icon, (c2_x, sum_rect.y + 16))
        gold_earned = getattr(session.state, "last_gold_earned", 0)
        renderer.draw_text(surface, "Gold:", c2_x + 26, sum_rect.y + 8, token=ThemeToken.TEXT_NORMAL, size=12, bold=True, font_variant="alagard")
        renderer.draw_text(surface, f"+{gold_earned}", c2_x + 26, sum_rect.y + 24, token=ThemeToken.TEXT_HIGHLIGHT, size=15, bold=True, font_variant="alagard")

        # Column 3: Pouch Space
        c3_x = sum_rect.x + col_w * 2 + 20
        pouch_icon = assets.get_pyxel_icon(104, 0, size=(20, 20))
        if pouch_icon:
            surface.blit(pouch_icon, (c3_x, sum_rect.y + 16))
        pouch_len = len(player.inventory.pouch)
        is_full = pouch_len >= MAX_POUCH_SLOTS
        renderer.draw_text(surface, "Pouch Space:", c3_x + 26, sum_rect.y + 8, token=ThemeToken.TEXT_NORMAL, size=12, bold=True, font_variant="alagard")
        renderer.draw_text(surface, f"{pouch_len}/{MAX_POUCH_SLOTS}", c3_x + 26, sum_rect.y + 24, token=ThemeToken.TEXT_ALERT if is_full else ThemeToken.TEXT_SUCCESS, size=15, bold=True, font_variant="alagard")

        # =========================================================================
        # 4. PENDING LOOT ITEM CARDS
        # =========================================================================
        card_w = 720
        total_items = len(pending)
        card_h = 52 if total_items > 2 else 56
        card_spacing = 6
        start_y = 286

        self.card_rects = []
        if not pending:
            self.no_loot_rect = pygame.Rect(120, start_y + 10, card_w, 70)
            nl_bg = pygame.Surface((self.no_loot_rect.width, self.no_loot_rect.height), pygame.SRCALPHA)
            nl_bg.fill((18, 16, 28, 210))
            surface.blit(nl_bg, self.no_loot_rect.topleft)
            nl_frame = assets.get_9slice_frame("frame_gold_clean", self.no_loot_rect.width, self.no_loot_rect.height, margin=23)
            if nl_frame:
                surface.blit(nl_frame, self.no_loot_rect.topleft)
            renderer.draw_text(
                surface,
                "All spoils have been claimed. Press [SPACE] or Click Continue to advance.",
                self.no_loot_rect.centerx,
                self.no_loot_rect.centery - 8,
                token=ThemeToken.TEXT_SUCCESS,
                size=14,
                bold=True,
                align="center",
                font_variant="alagard",
            )
        else:
            for idx, item in enumerate(pending[:3]):
                card_y = start_y + idx * (card_h + card_spacing)
                card_rect = pygame.Rect(120, card_y, card_w, card_h)
                self.card_rects.append(card_rect)
                is_active = (idx == self._selected_card_idx)

                # Card background & frame
                c_bg = pygame.Surface((card_rect.width, card_rect.height), pygame.SRCALPHA)
                c_bg.fill((20, 18, 30, 245) if not is_active else (28, 26, 44, 250))
                surface.blit(c_bg, card_rect.topleft)

                c_frame = assets.get_9slice_frame("frame_gold_clean", card_rect.width, card_rect.height, margin=23)
                if c_frame:
                    surface.blit(c_frame, card_rect.topleft)

                # Active selection triangle arrow
                if is_active:
                    arrow_x = card_rect.x + 6
                    arrow_y = card_rect.centery
                    pygame.draw.polygon(
                        surface,
                        (255, 220, 40),
                        [(arrow_x, arrow_y - 6), (arrow_x + 7, arrow_y), (arrow_x, arrow_y + 6)],
                    )

                # Color band showing item tier
                tier = getattr(item, "tier", 1)
                tcolor = self.TIER_COLORS.get(tier, (180, 185, 195))
                pygame.draw.rect(surface, tcolor, (card_rect.x + 18, card_rect.y + 7, 5, card_rect.height - 14), border_radius=2)

                # Square Item Icon Frame (36x36)
                ib_rect = pygame.Rect(card_rect.x + 28, card_rect.y + 8, 36, 36)
                pygame.draw.rect(surface, (14, 12, 20), ib_rect)
                ib_frame = assets.get_9slice_frame("frame_button_gold", 36, 36, margin=10)
                if ib_frame:
                    surface.blit(ib_frame, ib_rect.topleft)

                # Item Icon (potions or Pyxel fallback equipment)
                icon_surf = self._get_item_icon(item)
                if icon_surf:
                    surface.blit(
                        icon_surf,
                        (ib_rect.centerx - icon_surf.get_width() // 2, ib_rect.centery - icon_surf.get_height() // 2),
                    )

                # Item Name & Subtitle
                name_x = card_rect.x + 74
                name_token = ThemeToken.TEXT_HIGHLIGHT if is_active else ThemeToken.TEXT_NORMAL
                
                # Check for localized name fallback
                loc_name = getattr(item, "localized_name", item.name)
                display_name = item.name if (loc_name.startswith("item_") and item.name) else loc_name

                renderer.draw_text(
                    surface,
                    f"[{idx + 1}] {display_name}",
                    name_x,
                    card_rect.y + 7,
                    token=name_token,
                    size=14,
                    bold=True,
                    font_variant="alagard",
                )

                # Subtitle (Slot name or Consumable type)
                if isinstance(item, EquipmentItem):
                    sub_str = t(f"slot_{item.slot.name.lower()}")
                elif isinstance(item, StatPotion):
                    sub_str = t("spoils_perm_elixir")
                else:
                    sub_str = t("spoils_consumable")
                renderer.draw_text(
                    surface,
                    sub_str,
                    name_x,
                    card_rect.y + 26,
                    token=ThemeToken.TEXT_MUTED,
                    size=11,
                    font_variant="alagard",
                )

                # Vertical Divider inside card
                vdiv_x = card_rect.x + 435
                pygame.draw.line(surface, (70, 75, 105), (vdiv_x, card_rect.y + 8), (vdiv_x, card_rect.bottom - 8))

                # Right Column: Stats & live comparison vs equipped gear
                stat_x = vdiv_x + 16
                if isinstance(item, EquipmentItem):
                    stats = item.stats_bonus
                    parts = []
                    if stats.attack != 0:
                        parts.append(f"ATK +{stats.attack}" if stats.attack > 0 else f"ATK {stats.attack}")
                    if stats.defense != 0:
                        parts.append(f"DEF +{stats.defense}" if stats.defense > 0 else f"DEF {stats.defense}")
                    if stats.speed != 0:
                        parts.append(f"SPD +{stats.speed}" if stats.speed > 0 else f"SPD {stats.speed}")
                    if stats.max_hp != 0:
                        parts.append(f"HP +{stats.max_hp}" if stats.max_hp > 0 else f"HP {stats.max_hp}")
                    if stats.crit_chance > 0:
                        parts.append(f"CRIT +{int(stats.crit_chance * 100)}%")

                    stat_str = "     ".join(parts) if parts else "No stat bonuses"
                    renderer.draw_text(
                        surface,
                        stat_str,
                        stat_x,
                        card_rect.y + 7,
                        token=ThemeToken.TEXT_NORMAL,
                        size=13,
                        bold=True,
                        font_variant="alagard",
                    )

                    # Stat comparison vs currently equipped gear in this slot
                    curr_item = player.inventory.equipment.get(item.slot)
                    if curr_item:
                        cstats = curr_item.stats_bonus
                        diff_parts = []
                        diff_atk = stats.attack - cstats.attack
                        diff_def = stats.defense - cstats.defense
                        diff_spd = stats.speed - cstats.speed
                        diff_hp = stats.max_hp - cstats.max_hp

                        if diff_atk != 0:
                            diff_parts.append(f"{'+' if diff_atk > 0 else ''}{diff_atk} ATK")
                        if diff_def != 0:
                            diff_parts.append(f"{'+' if diff_def > 0 else ''}{diff_def} DEF")
                        if diff_spd != 0:
                            diff_parts.append(f"{'+' if diff_spd > 0 else ''}{diff_spd} SPD")
                        if diff_hp != 0:
                            diff_parts.append(f"{'+' if diff_hp > 0 else ''}{diff_hp} HP")

                        if diff_parts:
                            comp_txt = f"(vs equipped: {', '.join(diff_parts)})"
                            has_positive = any("+" in p for p in diff_parts)
                            token = ThemeToken.TEXT_SUCCESS if has_positive else ThemeToken.TEXT_ALERT
                        else:
                            comp_txt = "(vs equipped: identical stats)"
                            token = ThemeToken.TEXT_MUTED
                    else:
                        comp_txt = "(vs equipped: empty slot)"
                        token = ThemeToken.ACCENT_PRIMARY

                    renderer.draw_text(
                        surface,
                        comp_txt,
                        stat_x,
                        card_rect.y + 26,
                        token=token,
                        size=11,
                        bold=False,
                        font_variant="alagard",
                    )

                elif isinstance(item, ConsumableItem):
                    if isinstance(item, StatPotion):
                        b_str = ""
                        if item.stat_bonus.attack > 0:
                            b_str = f"Permanent ATK +{item.stat_bonus.attack}"
                        elif item.stat_bonus.defense > 0:
                            b_str = f"Permanent DEF +{item.stat_bonus.defense}"
                        elif item.stat_bonus.speed > 0:
                            b_str = f"Permanent SPD +{item.stat_bonus.speed}"
                        elif item.stat_bonus.max_hp > 0:
                            b_str = f"Permanent HP +{item.stat_bonus.max_hp}"
                        renderer.draw_text(
                            surface,
                            b_str,
                            stat_x,
                            card_rect.y + 16,
                            token=ThemeToken.TEXT_SUCCESS,
                            size=13,
                            bold=True,
                            font_variant="alagard",
                        )
                    else:
                        heal_txt = f"Heals {item.heal_amount} HP" if i18n.locale == "en" else f"Cura {item.heal_amount} PV"
                        renderer.draw_text(
                            surface,
                            heal_txt,
                            stat_x,
                            card_rect.y + 16,
                            token=ThemeToken.TEXT_SUCCESS,
                            size=13,
                            bold=True,
                            font_variant="alagard",
                        )

        # =========================================================================
        # 5. BOTTOM ACTION CONTROLS & BUTTONS
        # =========================================================================
        prompt_txt = f"[1-{len(pending)}] Take Item" if pending else "[C] Continue"
        renderer.draw_text(
            surface,
            prompt_txt,
            124,
            484,
            token=ThemeToken.TEXT_NORMAL,
            size=13,
            bold=True,
            font_variant="alagard",
        )

        # TAKE ALL Button
        ta_rect = self.take_all_btn_rect
        ta_frame = assets.get_9slice_frame("frame_button_gold", ta_rect.width, ta_rect.height, margin=20)
        ta_bg = pygame.Surface((ta_rect.width, ta_rect.height), pygame.SRCALPHA)
        ta_bg.fill((16, 14, 24, 240) if self._hovered_btn != "take_all" else (35, 30, 50, 250))
        surface.blit(ta_bg, ta_rect.topleft)
        if ta_frame:
            surface.blit(ta_frame, ta_rect.topleft)
        renderer.draw_text(
            surface,
            "[ SPACE ] TAKE ALL",
            ta_rect.centerx,
            ta_rect.y + 9,
            token=ThemeToken.TEXT_HIGHLIGHT if pending else ThemeToken.TEXT_MUTED,
            size=13,
            bold=True,
            align="center",
            font_variant="alagard",
        )

        # CONTINUE Button
        co_rect = self.cont_btn_rect
        co_frame = assets.get_9slice_frame("frame_button_gold", co_rect.width, co_rect.height, margin=20)
        co_bg = pygame.Surface((co_rect.width, co_rect.height), pygame.SRCALPHA)
        co_bg.fill((16, 14, 24, 240) if self._hovered_btn != "continue" else (35, 30, 50, 250))
        surface.blit(co_bg, co_rect.topleft)
        if co_frame:
            surface.blit(co_frame, co_rect.topleft)
        renderer.draw_text(
            surface,
            "[ C ] CONTINUE",
            co_rect.centerx,
            co_rect.y + 9,
            token=ThemeToken.TEXT_NORMAL,
            size=13,
            bold=True,
            align="center",
            font_variant="alagard",
        )
