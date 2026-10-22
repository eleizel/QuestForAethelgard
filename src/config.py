"""Global constants for Quest for Aethelgard.

Defines screen dimensions, target framerate, color palette indices, and layout configs.
"""

from typing import Final

# Window and Display
WINDOW_TITLE: Final[str] = "Quest for Aethelgard"
SCREEN_WIDTH: Final[int] = 256
SCREEN_HEIGHT: Final[int] = 256
FPS: Final[int] = 30
import os
RESOURCE_PATH: Final[str] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets/game.pyxres")

# Pyxel Palette Color Indices (0 to 15)
COLOR_BLACK: Final[int] = 0
COLOR_NAVY: Final[int] = 1
COLOR_PURPLE: Final[int] = 2
COLOR_GREEN: Final[int] = 3
COLOR_BROWN: Final[int] = 4
COLOR_DARK_BLUE: Final[int] = 5
COLOR_LIGHT_BLUE: Final[int] = 6
COLOR_WHITE: Final[int] = 7
COLOR_RED: Final[int] = 8
COLOR_ORANGE: Final[int] = 9
COLOR_YELLOW: Final[int] = 10
COLOR_LIME: Final[int] = 11
COLOR_CYAN: Final[int] = 12
COLOR_GRAY: Final[int] = 13
COLOR_PINK: Final[int] = 14
COLOR_PEACH: Final[int] = 15

# UI Colors
BG_COLOR: Final[int] = COLOR_BLACK
TEXT_COLOR_NORMAL: Final[int] = COLOR_WHITE
TEXT_COLOR_MUTED: Final[int] = COLOR_GRAY
TEXT_COLOR_HIGHLIGHT: Final[int] = COLOR_YELLOW
TEXT_COLOR_ALERT: Final[int] = COLOR_RED
TEXT_COLOR_SUCCESS: Final[int] = COLOR_LIME

# Panel Layout Dimensions
HUD_HEIGHT: Final[int] = 24
STATUS_PANEL_WIDTH: Final[int] = 80
LOG_PANEL_HEIGHT: Final[int] = 64
