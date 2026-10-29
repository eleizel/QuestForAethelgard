from __future__ import annotations

from typing import TYPE_CHECKING

from src.config import (
    COLOR_BLACK,
    COLOR_CYAN,
    COLOR_DARK_BLUE,
    COLOR_LIGHT_BLUE,
    COLOR_NAVY,
    COLOR_PEACH,
    COLOR_WHITE,
    COLOR_YELLOW,
)
from src.core.i18n import t
from src.ui.views.base import View

if TYPE_CHECKING:
    from src.core.game_state import GameState
    from src.ui.renderer import Renderer
    from src.systems.abilities import Ability


class CharacterView(View):
    """Read-only character sheet with current stats and equipped abilities."""

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        player = game_state.player
        stats = player.effective_stats

        renderer.draw_hud(player, game_state.floor)
        renderer.draw_box(4, 27, 248, 67, bg_col=COLOR_BLACK, border_col=COLOR_DARK_BLUE)
        renderer.draw_text(11, 32, t("character_title"), COLOR_CYAN)
        renderer.draw_text(
            11, 40,
            f"{player.name} - {player.class_name} - Lv.{player.level}"[:39],
            COLOR_YELLOW,
        )
        renderer.draw_text(
            11, 49,
            t("stat_hp", current=player.current_hp, max=stats.max_hp),
            COLOR_WHITE,
        )
        renderer.draw_bar(
            11, 58, 232, 6, player.current_hp, stats.max_hp,
            fill_col=COLOR_LIGHT_BLUE, bg_col=COLOR_NAVY,
        )
        renderer.draw_text(11, 69, t("stat_atk", val=stats.attack), COLOR_WHITE)
        renderer.draw_text(133, 69, t("stat_def", val=stats.defense), COLOR_WHITE)
        renderer.draw_text(11, 81, t("stat_spd", val=stats.speed), COLOR_WHITE)
        renderer.draw_text(
            133, 81,
            t("stat_crit", val=int(stats.crit_chance * 100)),
            COLOR_WHITE,
        )

        self._draw_skill_panel(
            renderer, x=4, title=t("character_active"),
            abilities=player.abilities.active, signature=None,
        )
        self._draw_skill_panel(
            renderer, x=130, title=t("character_passive"),
            abilities=player.all_passives, signature=player.signature_passive,
        )
        renderer.draw_text(6, 243, t("character_back_hint"), COLOR_PEACH)

    def _draw_skill_panel(
        self,
        renderer: Renderer,
        x: int,
        title: str,
        abilities: list[Ability],
        signature: Ability | None,
    ) -> None:
        panel_y, panel_w, panel_h = 100, 122, 137
        renderer.draw_box(
            x, panel_y, panel_w, panel_h,
            bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE,
        )
        renderer.draw_text(x + 5, panel_y + 5, title, COLOR_CYAN)
        if not abilities:
            renderer.draw_text(
                x + 5, panel_y + 21, t("character_empty_skills"), COLOR_WHITE,
            )
            return

        row_height = max(25, (panel_h - 24) // len(abilities))
        for index, ability in enumerate(abilities):
            row_y = panel_y + 19 + index * row_height
            renderer.draw_text(
                x + 5, row_y, ability.localized_name[:13 if ability is signature else 18], COLOR_YELLOW,
            )
            if ability is signature:
                renderer.draw_text(
                    x + panel_w - 24, row_y, t("character_signature"), COLOR_PEACH,
                )
            description = renderer.wrap_text(
                ability.localized_description, max_chars_per_line=18,
            )
            for line_index, line in enumerate(description[:2]):
                renderer.draw_text(
                    x + 5, row_y + 8 + line_index * 7, line, COLOR_WHITE,
                )
