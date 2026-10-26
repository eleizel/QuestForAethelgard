"""View switching architecture including CombatView, MapView, and InventoryView."""

from __future__ import annotations
from src.ui.views.base import View, CombatPopup, ENEMY_SPRITE_COORDS, SPEED_INTERVALS, SPEED_LABELS

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pyxel

from src.config import (
    COLOR_BLACK,
    COLOR_BROWN,
    COLOR_CYAN,
    COLOR_DARK_BLUE,
    COLOR_GRAY,
    COLOR_GREEN,
    COLOR_LIGHT_BLUE,
    COLOR_LIME,
    COLOR_NAVY,
    COLOR_ORANGE,
    COLOR_PEACH,
    COLOR_PINK,
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from src.core.game_state import GameMode
from src.core.i18n import i18n, t
from src.entities import Enemy
from src.systems.abilities import Ability, AbilityRarity, AbilityType, get_random_abilities
from src.systems.combat import ACTION_THRESHOLD
from src.systems.inventory import MAX_BELT_SLOTS, MAX_POUCH_SLOTS, EquipSlot
from src.systems.map_gen import NodeType
from src.ui import renderer
from src.ui.renderer import Renderer

if TYPE_CHECKING:
    from src.core.game_state import GameState

# =============================================================================
# BIOME ENEMY SPRITE COORDINATE MAP (Bank 0)
# =============================================================================
class CreditsView(View):
    """Renders the game's credits screen."""

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_ESCAPE) or Renderer.is_clicked(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT):
            game_state.switch_mode(GameMode.WELCOME)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT

        renderer.draw_box(20, 60, w - 40, 120, bg_col=COLOR_NAVY, border_col=COLOR_YELLOW)
        renderer.draw_text(w // 2 - 20, 80, t("credits_title"), COLOR_YELLOW)
        renderer.draw_text(35, 110, t("credits_dev"), COLOR_WHITE)
        renderer.draw_text(35, 130, t("credits_ai"), COLOR_WHITE)

        renderer.draw_button(w // 2 - 50, 155, 100, 16, t("btn_back"), bg_col=COLOR_NAVY, text_col=COLOR_LIME)
