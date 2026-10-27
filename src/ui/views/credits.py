"""View switching architecture including CombatView, MapView, and InventoryView."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyxel

from src.config import (
    COLOR_BLACK,
    COLOR_LIME,
    COLOR_NAVY,
    COLOR_WHITE,
    COLOR_YELLOW,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from src.core.game_state import GameMode
from src.core.i18n import t
from src.data.abilities import get_random_abilities
from src.ui.renderer import Renderer
from src.ui.views.base import View

if TYPE_CHECKING:
    from src.core.game_state import GameState


# =============================================================================
# BIOME ENEMY SPRITE COORDINATE MAP (Bank 0)
# =============================================================================
class CreditsView(View):
    """Renders the game's credits screen."""

    def update(self, game_state: GameState) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_ESCAPE) or Renderer.is_clicked(0, 0, SCREEN_WIDTH,
                                                                                               SCREEN_HEIGHT):
            game_state.switch_mode(GameMode.WELCOME)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT

        renderer.draw_box(20, 60, w - 40, 120, bg_col=COLOR_NAVY, border_col=COLOR_YELLOW)
        renderer.draw_text(w // 2 - 20, 80, t("credits_title"), COLOR_YELLOW)
        renderer.draw_text(35, 110, t("credits_dev"), COLOR_WHITE)
        renderer.draw_text(35, 130, t("credits_ai"), COLOR_WHITE)

        renderer.draw_button(w // 2 - 50, 155, 100, 16, t("btn_back"), bg_col=COLOR_NAVY, text_col=COLOR_LIME)
