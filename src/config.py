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

RESOURCE_PATH: Final[str] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                         "assets/game.pyxres")

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

# Sound Channels & Allocation
SND_CH_MUS_LEAD: Final[int] = 0
SND_CH_MUS_BASS: Final[int] = 1
SND_CH_MUS_PERC: Final[int] = 2
SND_CH_SFX: Final[int] = 3
SND_CH_UI: Final[int] = 3

# Sound Effect IDs
SND_HIT: Final[int] = 0
SND_CRIT: Final[int] = 1
SND_HEAL: Final[int] = 2
SND_CLICK: Final[int] = 3
SND_VICTORY: Final[int] = 4
SND_DEFEAT: Final[int] = 5
SND_CHEST: Final[int] = 6
SND_DOOR: Final[int] = 7

# Music Track IDs
MUS_TITLE: Final[int] = 0
MUS_COMBAT: Final[int] = 1
MUS_BOSS: Final[int] = 2
MUS_MAP_ARBORETUM: Final[int] = 3
MUS_MAP_CATHEDRAL: Final[int] = 4
MUS_MAP_OSSUARY: Final[int] = 5
MUS_MAP_FOUNDRY: Final[int] = 6
MUS_MAP_OBSERVATORY: Final[int] = 7
MUS_MAP_SANCTUM: Final[int] = 8

# System Limits & Combat
ACTION_THRESHOLD: Final[int] = 100
TARGET_COMBAT_SPEED: Final[float] = 12.5
ABILITY_COOLDOWN_TICKS: Final[int] = 3
MAX_POUCH_SLOTS: Final[int] = 10
MAX_BELT_SLOTS: Final[int] = 3
MAX_ACTIVE_ABILITIES: Final[int] = 2
MAX_PASSIVE_ABILITIES: Final[int] = 2
