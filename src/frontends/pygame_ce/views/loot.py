"""Pygame-CE Loot & Spoils Reward View."""

from __future__ import annotations

from typing import TYPE_CHECKING
import pygame

from src.core.commands import TakeLootCommand, TakeAllLootCommand
from src.core.game_state import GameMode
from src.core.i18n import t
from src.core.theme import ThemeToken
from src.entities.item import EquipmentItem
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


class PygameLootView(PygameView):
    """Loot view displaying dropped equipment, stat comparison, and Take/Take All actions."""

    TIER_COLORS = {
        1: (180, 185, 195),
        2: (80, 200, 120),
        3: (60, 150, 240),
        4: (180, 80, 220),
        5: (255, 180, 40),
    }

    def __init__(self) -> None:
        self._hovered_btn: str | None = None

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        pending = session.state.pending_loot

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_c):
                if not pending:
                    session.state.continue_after_rewards()
                else:
                    session.dispatch(TakeAllLootCommand())
                    if not session.state.pending_loot:
                        session.state.continue_after_rewards()
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                idx = event.key - pygame.K_1
                if 0 <= idx < len(pending):
                    session.dispatch(TakeLootCommand(loot_index=idx))
                    if not session.state.pending_loot:
                        session.state.continue_after_rewards()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for idx in range(len(pending)):
                take_btn = pygame.Rect(720, 160 + idx * 75, 120, 36)
                if take_btn.collidepoint(pos):
                    session.dispatch(TakeLootCommand(loot_index=idx))
                    if not session.state.pending_loot:
                        session.state.continue_after_rewards()
                    return

            take_all_btn = pygame.Rect(280, 450, 180, 42)
            if take_all_btn.collidepoint(pos) and pending:
                session.dispatch(TakeAllLootCommand())
                if not session.state.pending_loot:
                    session.state.continue_after_rewards()
                return

            cont_btn = pygame.Rect(500, 450, 180, 42)
            if cont_btn.collidepoint(pos):
                session.state.continue_after_rewards()
                return

    def update(self, dt: float, session: GameSession) -> None:
        pos = pygame.mouse.get_pos()
        take_all_btn = pygame.Rect(280, 450, 180, 42)
        cont_btn = pygame.Rect(500, 450, 180, 42)

        if take_all_btn.collidepoint(pos):
            self._hovered_btn = "take_all"
        elif cont_btn.collidepoint(pos):
            self._hovered_btn = "continue"
        else:
            self._hovered_btn = None

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        biome = getattr(session.state, "current_biome", "cathedral")
        assets.draw_background(surface, biome, vignette_alpha=145)

        w = surface.get_width()

        renderer.draw_text(surface, "VICTORY SPOILS", w // 2, 40, token=ThemeToken.TEXT_HIGHLIGHT, size=28, bold=True, align="center")
        renderer.draw_text(surface, "Claim equipment and relics from the fallen before proceeding deeper into the dungeon", w // 2, 75, token=ThemeToken.TEXT_MUTED, size=13, align="center")

        pending = session.state.pending_loot
        player = session.player

        panel_rect = pygame.Rect(100, 115, 760, 310)
        renderer.draw_panel(surface, panel_rect, border_token=ThemeToken.BORDER)

        if not pending:
            renderer.draw_text(surface, "All spoils have been claimed. Press [SPACE] or Click Continue to advance.", panel_rect.centerx, panel_rect.centery - 10, token=ThemeToken.TEXT_SUCCESS, size=16, bold=True, align="center")
        else:
            for idx, item in enumerate(pending[:4]):
                item_y = 135 + idx * 72
                item_rect = pygame.Rect(120, item_y, 720, 62)
                is_equip = isinstance(item, EquipmentItem)
                tier = getattr(item, "tier", 1)
                tcolor = self.TIER_COLORS.get(tier, (200, 200, 200))

                renderer.draw_panel(surface, item_rect, border_token=ThemeToken.BORDER_MUTED)
                pygame.draw.rect(surface, tcolor, pygame.Rect(item_rect.x, item_rect.y, 6, item_rect.height), border_top_left_radius=6, border_bottom_left_radius=6)

                slot_name = item.slot.name if is_equip else "Item"
                renderer.draw_text(surface, f"[{idx+1}] {item.name}", item_rect.x + 20, item_rect.y + 12, token=ThemeToken.TEXT_NORMAL, size=16, bold=True)
                renderer.draw_text(surface, f"Tier {tier} {slot_name.capitalize()}", item_rect.x + 20, item_rect.y + 36, token=ThemeToken.TEXT_MUTED, size=12)

                if is_equip:
                    stats = getattr(item, "stats_bonus", getattr(item, "stats", None))
                    if stats:
                        curr_equipped = player.inventory.equipment.get(item.slot)
                        stat_str = f"ATK: +{stats.attack}  DEF: +{stats.defense}  HP: +{stats.max_hp}"
                        if curr_equipped:
                            cstats = getattr(curr_equipped, "stats_bonus", getattr(curr_equipped, "stats", None))
                            if cstats:
                                diff_atk = stats.attack - cstats.attack
                                diff_def = stats.defense - cstats.defense
                                comp_str = f"({'+' if diff_atk >= 0 else ''}{diff_atk} ATK, {'+' if diff_def >= 0 else ''}{diff_def} DEF vs equipped)"
                                renderer.draw_text(surface, comp_str, item_rect.x + 280, item_rect.y + 36, token=ThemeToken.ACCENT_PRIMARY if diff_atk >= 0 else ThemeToken.TEXT_ALERT, size=11, bold=True)

                        renderer.draw_text(surface, stat_str, item_rect.x + 280, item_rect.y + 14, token=ThemeToken.TEXT_HIGHLIGHT, size=12, bold=True)

                take_btn = pygame.Rect(item_rect.right - 130, item_rect.y + 13, 115, 36)
                renderer.draw_button(surface, take_btn, f"TAKE [{idx+1}]", accent_token=ThemeToken.TEXT_SUCCESS, font_size=12)

        take_all_btn = pygame.Rect(280, 450, 180, 42)
        renderer.draw_button(surface, take_all_btn, "TAKE ALL [SPACE]", is_hovered=(self._hovered_btn == "take_all"), accent_token=ThemeToken.TEXT_SUCCESS if pending else ThemeToken.BORDER_MUTED, font_size=13)

        cont_btn = pygame.Rect(500, 450, 180, 42)
        renderer.draw_button(surface, cont_btn, "CONTINUE [C]", is_hovered=(self._hovered_btn == "continue"), accent_token=ThemeToken.ACCENT_SECONDARY, font_size=13)
