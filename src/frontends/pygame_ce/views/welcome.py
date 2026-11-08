"""Pygame-CE Welcome / Title Screen View matching 16-bit SNES Golden Age concept art."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame

from src.core.events import AudioCue, event_bus
from src.core.game_state import GameMode
from src.core.i18n import i18n, t
from src.core.theme import ThemeToken
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.music_engine import AudioSettingsManager, DynamicMusicEngine
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


class PygameWelcomeView(PygameView):
    """Gothic title screen matching 16-bit SNES concept art with golden frame, title logo, and sword cursor."""

    MENU_ITEMS = [
        ("new", "NEW GAME", "NUEVA PARTIDA"),
        ("load", "LOAD GAME", "CARGAR"),
        ("option", "OPTION", "OPCIONES"),
        ("credits", "CREDITS", "CRÉDITOS"),
    ]

    MUTE_BUTTON_RECT = pygame.Rect(960 - 140, 16, 124, 36)

    def __init__(
        self,
        music_engine: DynamicMusicEngine | None = None,
        settings_manager: AudioSettingsManager | None = None,
    ) -> None:
        self.selected_index: int = 0
        self.pulse_timer: float = 0.0
        self.music_engine: DynamicMusicEngine | None = music_engine
        self.settings_manager: AudioSettingsManager = (
            settings_manager
            if settings_manager is not None
            else (
                music_engine.settings_manager
                if music_engine is not None and getattr(music_engine, "settings_manager", None) is not None
                else AudioSettingsManager()
            )
        )
        self.mute_rect: pygame.Rect = self.MUTE_BUTTON_RECT.copy()
        self.mute_hovered: bool = False

    @property
    def mute_button_rect(self) -> pygame.Rect:
        """Alias property for mute_rect."""
        return self.mute_rect

    @property
    def is_mute_hovered(self) -> bool:
        """Alias property for mute_hovered."""
        return self.mute_hovered

    @is_mute_hovered.setter
    def is_mute_hovered(self, val: bool) -> None:
        self.mute_hovered = bool(val)

    @property
    def mute_button_text(self) -> str:
        """Alias property returning current dynamic label."""
        return self.get_mute_button_label()

    def set_music_engine(self, music_engine: DynamicMusicEngine) -> None:
        """Inject or update active DynamicMusicEngine reference."""
        self.music_engine = music_engine
        if getattr(music_engine, "settings_manager", None) is not None:
            self.settings_manager = music_engine.settings_manager

    def get_mute_button_rect(self) -> pygame.Rect:
        """Return bounding box for mute button in 960x540 canvas coordinate space."""
        return self.mute_rect.copy()

    def is_muted(self) -> bool:
        """Return True if background music is currently muted."""
        if self.music_engine is not None:
            return self.music_engine.is_muted()
        return self.settings_manager.is_music_muted()

    def set_muted(self, muted: bool) -> None:
        """Explicitly set mute state on DynamicMusicEngine and/or AudioSettingsManager."""
        if self.music_engine is not None:
            self.music_engine.set_muted(muted)
        else:
            self.settings_manager.set_music_muted(muted)

    def toggle_mute(self) -> bool:
        """Toggle mute state, emit audio click cue, persist, and return new mute state."""
        event_bus.emit_audio(AudioCue.CLICK)
        if self.music_engine is not None:
            return self.music_engine.toggle_mute()
        return self.settings_manager.toggle_music_muted()

    def get_mute_button_label(self) -> str:
        """Return dynamic visual button text reflecting mute status."""
        return "[♫ UNMUTE]" if self.is_muted() else "[♫ MUTE]"

    def _get_item_rects(self, frame_rect: pygame.Rect) -> list[pygame.Rect]:
        rects = []
        for idx in range(len(self.MENU_ITEMS)):
            ry = frame_rect.y + 40 + idx * 48
            rects.append(pygame.Rect(frame_rect.x + 30, ry, frame_rect.width - 60, 40))
        return rects

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Handle keyboard arrows, hotkeys, and mouse interaction."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_m:
                self.toggle_mute()
                return
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selected_index = (self.selected_index - 1) % len(self.MENU_ITEMS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_index = (self.selected_index + 1) % len(self.MENU_ITEMS)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_option(self.selected_index, session)
            elif event.key in (pygame.K_1, pygame.K_n):
                self._activate_option(0, session)
            elif event.key in (pygame.K_2, pygame.K_c):
                self._activate_option(1, session)
            elif event.key in (pygame.K_3, pygame.K_o, pygame.K_l):
                self._activate_option(2, session)
            elif event.key in (pygame.K_4, pygame.K_r):
                self._activate_option(3, session)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mute_rect = self.get_mute_button_rect()
            if mute_rect.collidepoint(event.pos):
                self.toggle_mute()
                return

            frame_rect = pygame.Rect((960 - 360) // 2, 172, 360, 260)
            rects = self._get_item_rects(frame_rect)
            for idx, r in enumerate(rects):
                if r.collidepoint(event.pos):
                    self.selected_index = idx
                    self._activate_option(idx, session)
                    return

        elif event.type == pygame.MOUSEMOTION:
            self.mute_hovered = self.get_mute_button_rect().collidepoint(event.pos)

    def _activate_option(self, index: int, session: GameSession) -> None:
        key = self.MENU_ITEMS[index][0]
        event_bus.emit_audio(AudioCue.CLICK)
        if key == "new":
            session.switch_mode(GameMode.CLASS_SELECT)
        elif key == "load":
            if session.has_saved_game():
                if session.load_game():
                    event_bus.emit_audio(AudioCue.CLICK)
        elif key == "option":
            i18n.toggle_language()
        elif key == "credits":
            session.switch_mode(GameMode.CREDITS)

    def update(self, dt: float, session: GameSession) -> None:
        """Update breathing pulse timer and track mouse hover."""
        self.pulse_timer += dt
        pos = pygame.mouse.get_pos()
        self.mute_hovered = self.get_mute_button_rect().collidepoint(pos)

        frame_rect = pygame.Rect((960 - 360) // 2, 172, 360, 260)
        rects = self._get_item_rects(frame_rect)
        for idx, r in enumerate(rects):
            if r.collidepoint(pos):
                self.selected_index = idx
                break

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render 16-bit SNES background, embossed title logo, ornate frame, sword cursor, and footer."""
        # 1. Base 16-bit SNES Background
        assets.draw_background(surface, "welcome", vignette_alpha=35)

        w, h = surface.get_width(), surface.get_height()

        # 2. Golden Metallic Title Logo
        logo = assets.get_ui_component("title_logo")
        if logo:
            logo_w = 640
            ratio = logo_w / logo.get_width()
            scaled_logo = pygame.transform.smoothscale(logo, (logo_w, int(logo.get_height() * ratio)))
            surface.blit(scaled_logo, ((w - logo_w) // 2, 40))
        else:
            renderer.draw_text(surface, "QUEST FOR AETHELGARD", w // 2, 60, token=ThemeToken.TEXT_HIGHLIGHT, size=36, bold=True, align="center")

        # 3. Gothic Subtitle
        renderer.draw_text(
            surface,
            "A GOTHIC ROGUELIKE DUNGEON CRAWLER",
            w // 2,
            135,
            token=ThemeToken.TEXT_MUTED,
            size=15,
            bold=True,
            align="center",
        )

        # 4. Interactive Mute/Unmute Button (Top-Right)
        mute_rect = self.get_mute_button_rect()
        btn_frame = assets.get_9slice_frame("frame_button_gold", mute_rect.width, mute_rect.height, margin=14)
        if btn_frame:
            surface.blit(btn_frame, mute_rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), mute_rect, width=2, border_radius=4)

        if self.mute_hovered:
            pygame.draw.rect(surface, (255, 236, 39), mute_rect, width=2, border_radius=4)

        mute_label = self.get_mute_button_label()
        mute_font = renderer.get_font(size=14, bold=True, variant="alagard")
        shadow_surf = mute_font.render(mute_label, True, (10, 12, 18))
        surface.blit(
            shadow_surf,
            (mute_rect.centerx - shadow_surf.get_width() // 2 + 1, mute_rect.centery - 7),
        )

        mute_token = (
            ThemeToken.TEXT_HIGHLIGHT
            if self.mute_hovered
            else (ThemeToken.TEXT_ALERT if self.is_muted() else ThemeToken.TEXT_NORMAL)
        )
        renderer.draw_text(
            surface,
            mute_label,
            mute_rect.centerx,
            mute_rect.centery - 8,
            token=mute_token,
            size=14,
            bold=True,
            align="center",
            font_variant="alagard",
        )

        # 5. Ornate 16-Bit Golden Frame
        frame = assets.get_ui_component("frame_gold_ornate")
        frame_rect = pygame.Rect((w - 360) // 2, 172, 360, 260)
        if frame:
            scaled_frame = pygame.transform.smoothscale(frame, (frame_rect.width, frame_rect.height))
            surface.blit(scaled_frame, frame_rect)
        else:
            renderer.draw_panel(surface, frame_rect, bg_token=ThemeToken.PANEL_BG, border_token=ThemeToken.ACCENT_PRIMARY)

        # 5. Menu Options & Sword Cursor
        is_es = (getattr(i18n, "locale", "en") == "es")
        sword = assets.get_ui_component("sword_cursor")
        scaled_sword = pygame.transform.smoothscale(sword, (28, 28)) if sword else None
        sword_pulse = int(math.sin(self.pulse_timer * 6.0) * 3)

        rects = self._get_item_rects(frame_rect)
        has_save = session.has_saved_game()

        for idx, (key, label_en, label_es) in enumerate(self.MENU_ITEMS):
            r = rects[idx]
            is_sel = (idx == self.selected_index)

            label = label_es if is_es else label_en
            if key == "load" and not has_save:
                label = f"{label} (---)"

            if not has_save and key == "load":
                text_tok = ThemeToken.BORDER_MUTED
            elif is_sel:
                text_tok = ThemeToken.TEXT_HIGHLIGHT
            else:
                text_tok = ThemeToken.TEXT_NORMAL

            # Sword Cursor
            if is_sel and scaled_sword:
                surface.blit(scaled_sword, (frame_rect.centerx - 100 + sword_pulse, r.centery - 14))

            # Shadow + Text
            font = renderer.get_font(size=18, bold=True)
            shadow_surf = font.render(label, True, (10, 12, 18))
            surface.blit(shadow_surf, (r.centerx - shadow_surf.get_width() // 2 + 10 + 1, r.centery - shadow_surf.get_height() // 2 + 1))

            renderer.draw_text(
                surface,
                label,
                r.centerx + 10,
                r.centery - 9,
                token=text_tok,
                size=18,
                bold=True,
                align="center",
            )

        # 6. Footer (exactly as concept art)
        footer_y = 488
        renderer.draw_text(
            surface,
            "DEVELOPED BY: SERGIO ESPERALTA GATA",
            w // 2,
            footer_y,
            token=ThemeToken.TEXT_NORMAL,
            size=14,
            bold=True,
            align="center",
        )
