"""Pygame-CE Character Sheet Modal Overlay View."""

from __future__ import annotations

from typing import TYPE_CHECKING
import pygame

from src.core.game_state import GameMode
from src.core.theme import ThemeToken
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


class PygameCharacterModalView(PygameView):
    """Detailed character sheet displaying effective stats, growth rates, and equipped passives."""

    def __init__(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_c, pygame.K_ESCAPE):
            session.toggle_character()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            close_btn = pygame.Rect(840, 45, 36, 36)
            if close_btn.collidepoint(event.pos):
                session.toggle_character()

    def update(self, dt: float, session: GameSession) -> None:
        pass

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        w, h = surface.get_width(), surface.get_height()

        # Dimmed backdrop
        backdrop = pygame.Surface((w, h), pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, 180))
        surface.blit(backdrop, (0, 0))

        # Main Modal Window
        modal_rect = pygame.Rect(60, 30, 840, 480)
        renderer.draw_panel(surface, modal_rect, bg_token=ThemeToken.PANEL_BG, border_token=ThemeToken.ACCENT_PRIMARY, border_width=2, border_radius=10)

        # Header & Close button
        renderer.draw_text(surface, "CHAMPION ATTRIBUTES & SPELLBOOK", modal_rect.x + 30, modal_rect.y + 20, token=ThemeToken.TEXT_HIGHLIGHT, size=20, bold=True)
        close_btn = pygame.Rect(modal_rect.right - 50, modal_rect.y + 15, 36, 36)
        renderer.draw_button(surface, close_btn, "X", accent_token=ThemeToken.BORDER_MUTED, font_size=14)

        player = session.player
        stats = player.effective_stats

        # Left Column: Hero Portrait and Lore
        portrait_rect = pygame.Rect(100, 80, 240, 390)
        renderer.draw_panel(surface, portrait_rect, border_token=ThemeToken.BORDER_MUTED)

        portrait = assets.get_class_portrait(player.class_id, scale=2)
        if portrait:
            surface.blit(portrait, (portrait_rect.centerx - 48, portrait_rect.y + 20))

        renderer.draw_text(surface, player.name.upper(), portrait_rect.centerx, portrait_rect.y + 160, token=ThemeToken.TEXT_HIGHLIGHT, size=16, bold=True, align="center")
        renderer.draw_text(surface, f"Level {player.level} {player.class_id.capitalize()}", portrait_rect.centerx, portrait_rect.y + 185, token=ThemeToken.TEXT_MUTED, size=13, align="center")

        exp_str = f"EXP: {player.experience} / {player.exp_to_next_level}"
        renderer.draw_text(surface, exp_str, portrait_rect.centerx, portrait_rect.y + 215, token=ThemeToken.ACCENT_SECONDARY, size=12, bold=True, align="center")

        # Right Column: Effective Stats Breakdown
        stat_panel = pygame.Rect(360, 80, 500, 180)
        renderer.draw_panel(surface, stat_panel, border_token=ThemeToken.BORDER_MUTED)
        renderer.draw_text(surface, "EFFECTIVE ATTRIBUTES", stat_panel.x + 20, stat_panel.y + 12, token=ThemeToken.TEXT_HIGHLIGHT, size=14, bold=True)

        stat_grid = [
            ("Max Health (HP)", f"{player.current_hp} / {stats.max_hp}"),
            ("Attack Power (ATK)", f"{stats.attack}"),
            ("Armor Defense (DEF)", f"{stats.defense}"),
            ("Action Speed (SPD)", f"{stats.speed}"),
            ("Critical Strike", f"{int(stats.crit_chance * 100)}%"),
            ("Evade Rating", f"{player.evade_charges} Charges"),
        ]

        for s_idx, (label, val) in enumerate(stat_grid):
            col = s_idx % 2
            row = s_idx // 2
            sx = stat_panel.x + 25 + col * 240
            sy = stat_panel.y + 44 + row * 40
            renderer.draw_text(surface, label, sx, sy, token=ThemeToken.TEXT_MUTED, size=12, bold=True)
            renderer.draw_text(surface, val, sx + 210, sy, token=ThemeToken.TEXT_NORMAL, size=13, bold=True, align="right")

        # Active Abilities & Passives Panel
        skill_panel = pygame.Rect(360, 280, 500, 190)
        renderer.draw_panel(surface, skill_panel, border_token=ThemeToken.BORDER_MUTED)
        renderer.draw_text(surface, "ACTIVE SKILLS & PASSIVES", skill_panel.x + 20, skill_panel.y + 12, token=ThemeToken.TEXT_HIGHLIGHT, size=14, bold=True)

        actives = getattr(player.abilities, "active", [])
        renderer.draw_text(surface, "Active Techniques:", skill_panel.x + 20, skill_panel.y + 40, token=ThemeToken.ACCENT_PRIMARY, size=12, bold=True)
        for a_idx, act in enumerate(actives[:2]):
            renderer.draw_text(surface, f"• {act.name} (CD: {act.cooldown} turns)", skill_panel.x + 35, skill_panel.y + 60 + a_idx * 20, token=ThemeToken.TEXT_NORMAL, size=12)

        passives = player.all_passives
        renderer.draw_text(surface, "Passive Masteries:", skill_panel.x + 20, skill_panel.y + 110, token=ThemeToken.ACCENT_SECONDARY, size=12, bold=True)
        for p_idx, pas in enumerate(passives[:3]):
            p_name = pas.name if hasattr(pas, "name") else str(pas)
            renderer.draw_text(surface, f"• {p_name}", skill_panel.x + 35, skill_panel.y + 130 + p_idx * 20, token=ThemeToken.TEXT_NORMAL, size=12)
