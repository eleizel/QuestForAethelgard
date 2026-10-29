from __future__ import annotations

from typing import TYPE_CHECKING

import pyxel

from src.config import (
    COLOR_BLACK,
    COLOR_CYAN,
    COLOR_DARK_BLUE,
    COLOR_LIGHT_BLUE,
    COLOR_NAVY,
    COLOR_ORANGE,
    COLOR_PEACH,
    COLOR_WHITE,
    COLOR_YELLOW,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from src.core.game_state import GameMode
from src.core.i18n import i18n
from src.ui.renderer import Renderer
from src.ui.views.base import View

if TYPE_CHECKING:
    from src.core.game_state import GameState


class PromotionView(View):
    """Advanced-class selection presented as a pair of biome-style cards."""

    def __init__(self) -> None:
        self.selected_index: int | None = None

    def _select_or_promote(self, game_state: GameState, index: int, class_id: str) -> bool:
        if self.selected_index != index:
            self.selected_index = index
            return False
        if game_state.player.promote(class_id):
            game_state.switch_mode(GameMode.ABILITY_CHOICE)
            return True
        return False

    def _recommended_class(self, game_state: GameState) -> str:
        promotions = game_state.player.available_promotions()
        scores = {class_id: 0 for class_id in promotions}
        for ability in (*game_state.player.abilities.active, *game_state.player.abilities.passive):
            for class_id in promotions:
                scores[class_id] += ability.affinities.count(class_id)
        if not scores:
            return ""
        return max(promotions, key=lambda class_id: (scores[class_id], -promotions.index(class_id)))

    def update(self, game_state: GameState) -> None:
        promotions = game_state.player.available_promotions()
        if not promotions:
            return_mode = game_state.promotion_return_mode
            game_state.promotion_return_mode = None
            if return_mode == GameMode.LOOT or return_mode is None:
                game_state.continue_after_rewards()
            else:
                game_state.switch_mode(return_mode)
            return

        if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
            self.selected_index = 0 if self.selected_index != 0 else 1
        elif pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
            self.selected_index = 1 if len(promotions) > 1 and self.selected_index != 1 else 0

        for index, class_id in enumerate(promotions[:2]):
            card_x = 7 if index == 0 else 130
            clicked = Renderer.is_clicked(card_x, 50, 119, 184)
            pressed = (index == 0 and (pyxel.btnp(pyxel.KEY_1) or pyxel.btnp(pyxel.KEY_KP_1))) or (
                index == 1 and (pyxel.btnp(pyxel.KEY_2) or pyxel.btnp(pyxel.KEY_KP_2))
            )
            if (clicked or pressed) and self._select_or_promote(game_state, index, class_id):
                return

        if self.selected_index is not None and (pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE)):
            if self.selected_index < len(promotions):
                class_id = promotions[self.selected_index]
                self._select_or_promote(game_state, self.selected_index, class_id)

    def _draw_card(self, renderer: Renderer, class_id: str,
                   index: int, x: int, recommended: str) -> None:
        from src.data.abilities import get_ability_by_id
        from src.data.classes import CLASS_REGISTRY
        from src.tools.generate_assets import CLASS_SPRITE_COORDS, get_class_portrait

        y, width, height = 50, 119, 184
        is_recommended = class_id == recommended
        is_selected = index == self.selected_index
        border = COLOR_YELLOW if is_selected else (COLOR_PEACH if is_recommended else COLOR_LIGHT_BLUE)
        renderer.draw_box(x, y, width, height, bg_col=COLOR_DARK_BLUE if is_selected or is_recommended else COLOR_BLACK,
                          border_col=border)
        if is_selected:
            pyxel.rectb(x + 1, y + 1, width - 2, height - 2,
                        COLOR_YELLOW if pyxel.frame_count // 6 % 2 == 0 else COLOR_ORANGE)
        elif is_recommended:
            pyxel.rectb(x + 1, y + 1, width - 2, height - 2, COLOR_PEACH)
        for corner_x, corner_y in ((x + 2, y + 2), (x + width - 3, y + 2),
                                   (x + 2, y + height - 3), (x + width - 3, y + height - 3)):
            pyxel.pset(corner_x, corner_y, COLOR_WHITE if is_selected else COLOR_CYAN)

        # Portrait and battle sprite mirror the dual-art presentation on class selection.
        portrait_bank, portrait_u, portrait_v = get_class_portrait(class_id)
        frame_x, frame_y = x + 34, y + 4
        pyxel.rect(frame_x - 1, frame_y - 1, 50, 66, COLOR_NAVY)
        portrait_border = COLOR_YELLOW if is_selected else (COLOR_PEACH if is_recommended else COLOR_LIGHT_BLUE)
        pyxel.rectb(frame_x - 1, frame_y - 1, 50, 66, portrait_border)
        pyxel.blt(frame_x, frame_y, portrait_bank, portrait_u, portrait_v, 48, 64, 0)
        sprite_u, sprite_v = CLASS_SPRITE_COORDS[class_id]
        pyxel.blt(x + 8, y + 27, 0, sprite_u, sprite_v, 16, 16, 0)

        class_def = CLASS_REGISTRY[class_id]
        ability = get_ability_by_id(class_def.signature_passive) if class_def.signature_passive else None
        title = f"[{index + 1}] {class_def.localized_name}"
        renderer.draw_text(x + 4, y + 70, title[:27], COLOR_YELLOW if is_selected or is_recommended else COLOR_WHITE)
        if is_recommended:
            tag = "RECOMMENDED" if i18n.locale == "en" else "RECOMENDADA"
            renderer.draw_text(x + 4, y + 78, tag, COLOR_CYAN)

        description = renderer.wrap_text(class_def.localized_description, max_chars_per_line=27)
        for line_index, line in enumerate(description[:3]):
            renderer.draw_text(x + 4, y + 88 + line_index * 7, line, COLOR_WHITE)

        pyxel.line(x + 4, y + 110, x + width - 5, y + 110, COLOR_NAVY)
        growth = class_def.growth_per_level
        renderer.draw_text(x + 4, y + 113, "GROWTH / LEVEL" if i18n.locale == "en" else "CRECIMIENTO / NIVEL",
                           COLOR_PEACH)
        renderer.draw_text(x + 4, y + 122, f"HP +{growth.max_hp}  ATK +{growth.attack}", COLOR_WHITE)
        renderer.draw_text(x + 4, y + 130, f"DEF +{growth.defense}  SPD +{growth.speed}", COLOR_WHITE)
        renderer.draw_text(x + 4, y + 138, f"CRIT +{growth.crit_chance * 100:.1f}%", COLOR_WHITE)

        pyxel.line(x + 4, y + 148, x + width - 5, y + 148, COLOR_NAVY)
        renderer.draw_text(x + 4, y + 151, "SIGNATURE PASSIVE" if i18n.locale == "en" else "PASIVA EMBLEMATICA",
                           COLOR_PEACH)
        if ability:
            renderer.draw_text(x + 4, y + 160, ability.localized_name[:27], COLOR_CYAN)
            passive_lines = renderer.wrap_text(ability.localized_description, max_chars_per_line=27)
            for line_index, line in enumerate(passive_lines[:2]):
                renderer.draw_text(x + 4, y + 168 + line_index * 7, line, COLOR_WHITE)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)
        box_x, box_y = 4, 25
        box_w, box_h = SCREEN_WIDTH - 8, SCREEN_HEIGHT - 28
        pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

        # Gothic header and double frame echo the biome-route selection screen.
        pyxel.rect(16, 28, SCREEN_WIDTH - 32, 18, COLOR_NAVY)
        renderer.draw_box(28, 29, SCREEN_WIDTH - 56, 16, bg_col=COLOR_BLACK, border_col=COLOR_YELLOW)
        title = "CHOOSE YOUR PROMOTION" if i18n.locale == "en" else "ELIGE TU PROMOCION"
        renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(title) // 2, 34, title, COLOR_YELLOW)

        recommended = self._recommended_class(game_state)
        promotions = game_state.player.available_promotions()[:2]
        for index, (class_id, x) in enumerate(zip(promotions, (7, 130))):
            self._draw_card(renderer, class_id, index, x, recommended)

        hint = "Tap to select; tap again to confirm" if i18n.locale == "en" else "Toca para seleccionar y confirmar"
        renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(hint) // 2, 239, hint, COLOR_WHITE)
        pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_DARK_BLUE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_NAVY)
