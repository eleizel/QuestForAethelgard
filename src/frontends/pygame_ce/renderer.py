"""Pygame-CE presentation renderer utilizing ThemeToken mappings."""

from __future__ import annotations

from pathlib import Path
from typing import Literal
import pygame

from src.core.theme import ThemeToken, resolve_rgb_color

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FONTS_DIR = PROJECT_ROOT / "assets" / "fonts"
ALAGARD_FONT = FONTS_DIR / "alagard.ttf"
M5X7_FONT = FONTS_DIR / "m5x7.ttf"


class PygameRenderer:
    """Renders visual components using semantic theme tokens on Pygame surfaces."""

    def __init__(self) -> None:
        if not pygame.font.get_init():
            pygame.font.init()
        self._fonts: dict[tuple[int, bool, str], pygame.font.Font] = {}

    def get_font(
        self,
        size: int = 16,
        bold: bool = False,
        variant: Literal["alagard", "body", "default"] = "alagard",
    ) -> pygame.font.Font:
        """Retrieve a cached retro 16-bit font (Alagard for titles/accents, m5x7 for body text)."""
        key = (size, bold, variant)
        if key not in self._fonts:
            font_path = ALAGARD_FONT if variant in ("alagard", "default") else M5X7_FONT
            if not font_path.exists():
                font_path = ALAGARD_FONT if ALAGARD_FONT.exists() else M5X7_FONT

            if font_path.exists():
                try:
                    font = pygame.font.Font(str(font_path), size)
                except Exception:
                    font = pygame.font.Font(None, size)
            else:
                try:
                    font = pygame.font.SysFont("georgia,segoeui,arial", size=size, bold=bold)
                except Exception:
                    font = pygame.font.Font(None, size)
            self._fonts[key] = font
        return self._fonts[key]

    def color(self, token: ThemeToken) -> tuple[int, int, int]:
        """Resolve RGB color tuple from semantic theme token."""
        return resolve_rgb_color(token)

    def draw_text(
        self,
        surface: pygame.Surface,
        text: str,
        x: int,
        y: int,
        token: ThemeToken = ThemeToken.TEXT_NORMAL,
        size: int = 16,
        bold: bool = False,
        align: Literal["left", "center", "right"] = "left",
        font_variant: Literal["alagard", "body", "default"] = "alagard",
    ) -> pygame.Rect:
        """Render 16-bit pixel font text on surface with horizontal alignment."""
        font = self.get_font(size=size, bold=bold, variant=font_variant)
        rendered = font.render(text, True, self.color(token))
        rect = rendered.get_rect()

        if align == "center":
            rect.centerx = x
            rect.y = y
        elif align == "right":
            rect.right = x
            rect.y = y
        else:
            rect.x = x
            rect.y = y

        surface.blit(rendered, rect)
        return rect

    def draw_panel(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        bg_token: ThemeToken = ThemeToken.PANEL_BG,
        border_token: ThemeToken = ThemeToken.BORDER,
        border_width: int = 2,
        border_radius: int = 6,
    ) -> None:
        """Draw a styled UI panel with background and border."""
        # Draw background fill
        pygame.draw.rect(
            surface,
            self.color(bg_token),
            rect,
            border_radius=border_radius,
        )
        # Draw border
        if border_width > 0:
            pygame.draw.rect(
                surface,
                self.color(border_token),
                rect,
                width=border_width,
                border_radius=border_radius,
            )

    def draw_button(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        text: str,
        is_hovered: bool = False,
        is_selected: bool = False,
        accent_token: ThemeToken = ThemeToken.ACCENT_PRIMARY,
        font_size: int = 16,
    ) -> None:
        """Draw an interactive clickable button."""
        bg_token = ThemeToken.PANEL_BG
        border_token = accent_token if (is_hovered or is_selected) else ThemeToken.BORDER_MUTED
        text_token = ThemeToken.TEXT_HIGHLIGHT if (is_hovered or is_selected) else ThemeToken.TEXT_NORMAL

        self.draw_panel(
            surface,
            rect,
            bg_token=bg_token,
            border_token=border_token,
            border_width=2 if (is_hovered or is_selected) else 1,
            border_radius=6,
        )

        self.draw_text(
            surface,
            text,
            rect.centerx,
            rect.centery - (font_size // 2),
            token=text_token,
            size=font_size,
            bold=(is_hovered or is_selected),
            align="center",
        )

    def draw_progress_bar(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        current: int,
        maximum: int,
        fill_token: ThemeToken = ThemeToken.HP_FILL,
        bg_token: ThemeToken = ThemeToken.PANEL_BG,
        label: str | None = None,
    ) -> None:
        """Draw a horizontal stat progress bar with optional numerical text."""
        # Background bar
        pygame.draw.rect(surface, self.color(bg_token), rect, border_radius=4)

        # Fill bar
        if maximum > 0 and current > 0:
            pct = min(1.0, max(0.0, current / maximum))
            fill_rect = pygame.Rect(rect.x, rect.y, int(rect.width * pct), rect.height)
            pygame.draw.rect(surface, self.color(fill_token), fill_rect, border_radius=4)

        # Outline border
        pygame.draw.rect(surface, self.color(ThemeToken.BORDER), rect, width=1, border_radius=4)

        # Centered label
        text_str = label if label is not None else f"{current}/{maximum}"
        self.draw_text(
            surface,
            text_str,
            rect.centerx,
            rect.centery - 6,
            token=ThemeToken.TEXT_NORMAL,
            size=12,
            bold=True,
            align="center",
        )
