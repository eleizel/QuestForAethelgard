"""Semantic theme token abstraction for multi-frontend rendering.

Decouples visual color concepts (e.g. text highlights, health bars, warnings)
from platform-specific color formats (Pyxel 16-color indices vs. Pygame 24-bit RGB tuples).
"""

from __future__ import annotations

from enum import Enum, auto
from typing import NamedTuple


class RGB(NamedTuple):
    r: int
    g: int
    b: int


class ThemeToken(Enum):
    """Semantic color roles used throughout the game presentation."""
    BG = auto()
    PANEL_BG = auto()
    BORDER = auto()
    BORDER_MUTED = auto()
    TEXT_NORMAL = auto()
    TEXT_MUTED = auto()
    TEXT_HIGHLIGHT = auto()
    TEXT_ALERT = auto()
    TEXT_SUCCESS = auto()
    HP_FILL = auto()
    SHIELD_FILL = auto()
    ACCENT_PRIMARY = auto()
    ACCENT_SECONDARY = auto()


# Standard Pyxel 16-Color Palette (RGB definitions)
PYXEL_DEFAULT_PALETTE: list[RGB] = [
    RGB(0, 0, 0),        # 0: Black
    RGB(43, 51, 95),     # 1: Navy
    RGB(126, 37, 83),    # 2: Purple
    RGB(0, 135, 81),     # 3: Green
    RGB(171, 82, 54),    # 4: Brown
    RGB(95, 87, 79),     # 5: Dark Blue / Gray
    RGB(194, 195, 199),  # 6: Light Blue / Gray
    RGB(255, 255, 255),  # 7: White
    RGB(255, 0, 77),     # 8: Red
    RGB(255, 163, 0),    # 9: Orange
    RGB(255, 236, 39),   # 10: Yellow
    RGB(0, 228, 54),     # 11: Lime
    RGB(41, 173, 255),   # 12: Cyan
    RGB(131, 118, 156),  # 13: Gray / Indigo
    RGB(255, 119, 168),  # 14: Pink
    RGB(255, 204, 170),  # 15: Peach
]

# Pyxel Palette Index Mapping (ThemeToken -> int index 0..15)
PYXEL_THEME_MAP: dict[ThemeToken, int] = {
    ThemeToken.BG: 0,
    ThemeToken.PANEL_BG: 0,
    ThemeToken.BORDER: 1,
    ThemeToken.BORDER_MUTED: 5,
    ThemeToken.TEXT_NORMAL: 7,
    ThemeToken.TEXT_MUTED: 13,
    ThemeToken.TEXT_HIGHLIGHT: 10,
    ThemeToken.TEXT_ALERT: 8,
    ThemeToken.TEXT_SUCCESS: 11,
    ThemeToken.HP_FILL: 8,
    ThemeToken.SHIELD_FILL: 12,
    ThemeToken.ACCENT_PRIMARY: 10,
    ThemeToken.ACCENT_SECONDARY: 12,
}

# High-fidelity RGB Mapping for Pygame-CE / modern frontends
PYGAME_THEME_MAP: dict[ThemeToken, RGB] = {
    token: PYXEL_DEFAULT_PALETTE[idx] for token, idx in PYXEL_THEME_MAP.items()
}


def resolve_pyxel_color(token: ThemeToken) -> int:
    """Return Pyxel 0-15 color index for semantic token."""
    return PYXEL_THEME_MAP.get(token, 7)


def resolve_rgb_color(token: ThemeToken) -> tuple[int, int, int]:
    """Return RGB tuple for semantic token."""
    rgb = PYGAME_THEME_MAP.get(token, PYXEL_DEFAULT_PALETTE[7])
    return (rgb.r, rgb.g, rgb.b)
