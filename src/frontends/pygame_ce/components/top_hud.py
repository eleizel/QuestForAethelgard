"""Reusable Top Status Bar HUD component for Pygame-CE.

Provides consistent 16-bit SNES gold header bar across Map View, Combat View, and other game screens.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import pygame

from src.core.events import AudioCue, event_bus
from src.core.game_state import GameMode
from src.core.i18n import i18n
from src.core.theme import ThemeToken
from src.frontends.pygame_ce.asset_manager import assets

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


class TopHUDComponent:
    """Renders and handles events for the top character status and navigation bar."""

    def __init__(self) -> None:
        self.hud_rect = pygame.Rect(8, 6, 944, 46)
        self.save_btn_rect = pygame.Rect(608, 12, 98, 32)
        self.char_btn_rect = pygame.Rect(716, 12, 98, 32)
        self.inv_btn_rect = pygame.Rect(824, 12, 98, 32)
        self._hovered_btn: str | None = None

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> bool:
        """Handle hotkeys and mouse clicks on HUD action buttons. Returns True if handled."""
        # Save & Quit option on Exploration Map
        if session.current_mode == GameMode.MAP:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                session.save_game()
                event_bus.emit_audio(AudioCue.CLICK)
                session.switch_mode(GameMode.WELCOME)
                return True
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.save_btn_rect.collidepoint(event.pos):
                    session.save_game()
                    event_bus.emit_audio(AudioCue.CLICK)
                    session.switch_mode(GameMode.WELCOME)
                    return True

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_i:
                session.toggle_inventory()
                return True
            elif event.key == pygame.K_c:
                session.toggle_character()
                return True

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.inv_btn_rect.collidepoint(event.pos):
                session.toggle_inventory()
                return True
            elif self.char_btn_rect.collidepoint(event.pos):
                session.toggle_character()
                return True

        return False

    def update(self, mouse_pos: tuple[int, int]) -> None:
        """Update hover state for HUD buttons."""
        if self.inv_btn_rect.collidepoint(mouse_pos):
            self._hovered_btn = "inv"
        elif self.char_btn_rect.collidepoint(mouse_pos):
            self._hovered_btn = "char"
        elif self.save_btn_rect.collidepoint(mouse_pos):
            self._hovered_btn = "save"
        else:
            self._hovered_btn = None

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render the 16-bit status bar with player avatar, name, level, EXP bar, gold, and buttons."""
        player = session.player
        surface_w = surface.get_width()
        self.hud_rect.width = surface_w - 16

        # Dark background inside bar
        hud_bg = pygame.Surface((self.hud_rect.width, self.hud_rect.height), pygame.SRCALPHA)
        hud_bg.fill((18, 15, 24, 240))
        surface.blit(hud_bg, self.hud_rect.topleft)

        # 9-slice gold frame (margin=23 to keep native crisp corner)
        hud_frame = assets.get_9slice_frame("frame_gold_clean", self.hud_rect.width, self.hud_rect.height, margin=23)
        if hud_frame:
            surface.blit(hud_frame, self.hud_rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), self.hud_rect, width=2, border_radius=4)

        # 1. Character Headshot Bust
        bust_rect = pygame.Rect(self.hud_rect.x + 24, self.hud_rect.y + 5, 36, 36)
        bust_surf = assets.get_bust_portrait(player.class_id, size=(36, 36))
        if bust_surf:
            surface.blit(bust_surf, bust_rect.topleft)

        # 2. Name, Class, Level
        info_x = bust_rect.right + 10
        name_part = f"{player.name}"
        class_part = f" ({player.class_id.capitalize()})"
        lvl_part = f" Lv.{player.level}"

        r_name = renderer.draw_text(
            surface, name_part, info_x, self.hud_rect.y + 8,
            token=ThemeToken.TEXT_HIGHLIGHT, size=14, bold=True, font_variant="alagard"
        )
        r_class = renderer.draw_text(
            surface, class_part, r_name.right, self.hud_rect.y + 8,
            token=ThemeToken.TEXT_NORMAL, size=14, bold=True, font_variant="alagard"
        )
        renderer.draw_text(
            surface, lvl_part, r_class.right, self.hud_rect.y + 8,
            token=ThemeToken.TEXT_HIGHLIGHT, size=14, bold=True, font_variant="alagard"
        )

        # 3. EXP Text & Bar
        exp_next = max(1, getattr(player, "exp_to_next_level", 100))
        exp_curr = getattr(player, "experience", 0)
        exp_str = f"EXP: {exp_curr}/{exp_next}"
        r_exp = renderer.draw_text(
            surface, exp_str, info_x, self.hud_rect.y + 26,
            token=ThemeToken.TEXT_MUTED, size=11, bold=False, font_variant="alagard"
        )

        exp_bar_x = r_exp.right + 8
        exp_bar_rect = pygame.Rect(exp_bar_x, self.hud_rect.y + 28, 100, 10)
        pygame.draw.rect(surface, (30, 32, 45), exp_bar_rect, border_radius=2)
        exp_ratio = min(1.0, max(0.0, exp_curr / exp_next))
        if exp_ratio > 0:
            fill_w = max(2, int(exp_bar_rect.width * exp_ratio))
            pygame.draw.rect(surface, (41, 173, 255), (exp_bar_rect.x, exp_bar_rect.y, fill_w, exp_bar_rect.height), border_radius=2)
        pygame.draw.rect(surface, (150, 155, 175), exp_bar_rect, width=1, border_radius=2)

        # Vertical Divider
        div1_x = exp_bar_rect.right + 16
        renderer.draw_text(surface, "|", div1_x, self.hud_rect.y + 16, token=ThemeToken.BORDER_MUTED, size=14, font_variant="alagard")

        # 4. Gold
        gold_x = div1_x + 14
        renderer.draw_text(
            surface,
            f"Gold: {player.gold}",
            gold_x,
            self.hud_rect.y + 16,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=14,
            bold=True,
            font_variant="alagard",
        )

        # Vertical Divider
        div2_x = gold_x + 95
        renderer.draw_text(surface, "|", div2_x, self.hud_rect.y + 16, token=ThemeToken.BORDER_MUTED, size=14, font_variant="alagard")

        # 5. Floor
        floor_x = div2_x + 14
        floor_val = getattr(session.state, "floor", 1)
        renderer.draw_text(
            surface,
            f"Floor {floor_val}",
            floor_x,
            self.hud_rect.y + 16,
            token=ThemeToken.TEXT_NORMAL,
            size=14,
            bold=True,
            font_variant="alagard",
        )

        # 6. Action Buttons ([Q] SAVE, [C] CHAR, [I] INV)
        # SAVE & QUIT button (only visible on Map)
        if session.current_mode == GameMode.MAP:
            s_hover = (self._hovered_btn == "save")
            s_frame = assets.get_9slice_frame("frame_button_gold", self.save_btn_rect.width, self.save_btn_rect.height, margin=14)
            if s_frame:
                surface.blit(s_frame, self.save_btn_rect.topleft)
            else:
                pygame.draw.rect(surface, (218, 165, 32), self.save_btn_rect, width=2, border_radius=4)
            if s_hover:
                pygame.draw.rect(surface, (255, 255, 255), self.save_btn_rect, width=1, border_radius=4)
            save_text = "[Q] SAVE" if getattr(i18n, "locale", "en") == "en" else "[Q] GUARDAR"
            renderer.draw_text(
                surface,
                save_text,
                self.save_btn_rect.centerx,
                self.save_btn_rect.centery - 6,
                token=ThemeToken.TEXT_HIGHLIGHT if s_hover else ThemeToken.TEXT_NORMAL,
                size=12,
                bold=True,
                align="center",
                font_variant="alagard",
            )

        # CHAR button
        c_hover = (self._hovered_btn == "char")
        c_frame = assets.get_9slice_frame("frame_button_gold", self.char_btn_rect.width, self.char_btn_rect.height, margin=14)
        if c_frame:
            surface.blit(c_frame, self.char_btn_rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), self.char_btn_rect, width=2, border_radius=4)
        if c_hover:
            pygame.draw.rect(surface, (255, 255, 255), self.char_btn_rect, width=1, border_radius=4)
        renderer.draw_text(
            surface,
            "[C] CHAR",
            self.char_btn_rect.centerx,
            self.char_btn_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if c_hover else ThemeToken.TEXT_NORMAL,
            size=12,
            bold=True,
            align="center",
            font_variant="alagard",
        )

        # INV button
        i_hover = (self._hovered_btn == "inv")
        i_frame = assets.get_9slice_frame("frame_button_gold", self.inv_btn_rect.width, self.inv_btn_rect.height, margin=14)
        if i_frame:
            surface.blit(i_frame, self.inv_btn_rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), self.inv_btn_rect, width=2, border_radius=4)
        if i_hover:
            pygame.draw.rect(surface, (255, 255, 255), self.inv_btn_rect, width=1, border_radius=4)
        renderer.draw_text(
            surface,
            "[I] INV",
            self.inv_btn_rect.centerx,
            self.inv_btn_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if i_hover else ThemeToken.TEXT_NORMAL,
            size=12,
            bold=True,
            align="center",
            font_variant="alagard",
        )
