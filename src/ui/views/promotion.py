from __future__ import annotations

from typing import TYPE_CHECKING

import pyxel

from src.config import COLOR_BLACK, COLOR_CYAN, COLOR_DARK_BLUE, COLOR_GRAY, COLOR_LIGHT_BLUE, COLOR_WHITE, COLOR_YELLOW
from src.core.game_state import GameMode
from src.core.i18n import i18n
from src.ui.renderer import Renderer
from src.ui.views.base import View

if TYPE_CHECKING:
    from src.core.game_state import GameState


class PromotionView(View):
    """Choose one of the player's two level-10 advanced classes."""

    def _recommended_class(self, game_state: GameState) -> str:
        promotions = game_state.player.available_promotions()
        if not promotions:
            return ""
        scores = {class_id: 0 for class_id in promotions}
        for ability in (*game_state.player.abilities.active, *game_state.player.abilities.passive):
            for class_id in promotions:
                scores[class_id] += ability.affinities.count(class_id)
        return next((class_id for class_id in promotions if scores[class_id] == max(scores.values())), promotions[0])

    def update(self, game_state: GameState) -> None:
        promotions = game_state.player.available_promotions()
        for index, class_id in enumerate(promotions[:2]):
            y = 94 + index * 64
            clicked = Renderer.is_clicked(28, y, 200, 54)
            pressed = (index == 0 and (pyxel.btnp(pyxel.KEY_1) or pyxel.btnp(pyxel.KEY_KP_1))) or (
                index == 1 and (pyxel.btnp(pyxel.KEY_2) or pyxel.btnp(pyxel.KEY_KP_2)))
            if (clicked or pressed) and game_state.player.promote(class_id):
                game_state.promotion_return_mode = game_state.promotion_return_mode or GameMode.MAP
                game_state.switch_mode(GameMode.ABILITY_CHOICE)
                return

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pyxel.cls(COLOR_BLACK)
        title = "CHOOSE YOUR PROMOTION" if i18n.locale == "en" else "ELIGE TU PROMOCION"
        renderer.draw_text(128 - renderer.get_text_width(title) // 2, 36, title, COLOR_YELLOW)
        recommended = self._recommended_class(game_state)
        from src.data.classes import CLASS_REGISTRY
        from src.tools.generate_assets import CLASS_SPRITE_COORDS
        for index, class_id in enumerate(game_state.player.available_promotions()[:2]):
            y = 94 + index * 64
            renderer.draw_box(28, y, 200, 54, bg_col=COLOR_DARK_BLUE, border_col=COLOR_YELLOW if class_id == recommended else COLOR_LIGHT_BLUE)
            label = CLASS_REGISTRY[class_id].localized_name
            renderer.draw_text(40, y + 8, f"[{index + 1}] {label}", COLOR_YELLOW if class_id == recommended else COLOR_WHITE)
            if class_id == recommended:
                tag = "RECOMMENDED" if i18n.locale == "en" else "RECOMENDADA"
                renderer.draw_text(40, y + 22, tag, COLOR_CYAN)
            signature_name = CLASS_REGISTRY[class_id].signature_passive.replace("_", " ").title()
            renderer.draw_text(40, y + 37, f"Signature: {signature_name}"[:28], COLOR_GRAY)
            sprite_u, sprite_v = CLASS_SPRITE_COORDS[class_id]
            pyxel.blt(194, y + 19, 0, sprite_u, sprite_v, 16, 16, 0)
        hint = "Choose with 1 or 2" if i18n.locale == "en" else "Elige con 1 o 2"
        renderer.draw_text(128 - renderer.get_text_width(hint) // 2, 232, hint, COLOR_WHITE)
