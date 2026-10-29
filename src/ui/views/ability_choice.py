"""View switching architecture including CombatView, MapView, and InventoryView."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyxel

from src.config import (
    COLOR_BLACK,
    COLOR_BROWN,
    COLOR_CYAN,
    COLOR_DARK_BLUE,
    COLOR_LIGHT_BLUE,
    COLOR_LIME,
    COLOR_NAVY,
    COLOR_ORANGE,
    COLOR_PEACH,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from src.core.game_state import GameMode
from src.core.i18n import i18n, t
from src.data.abilities import get_random_abilities
from src.systems.abilities import Ability, AbilityRarity, AbilityType
from src.systems.map_gen import NodeType
from src.tools.generate_assets import get_ability_icon
from src.ui.renderer import Renderer
from src.ui.views.base import View

if TYPE_CHECKING:
    from src.core.game_state import GameState


class AbilityChoiceView(View):
    """Renders the ability selection screen featuring gothic chamber scenery, custom ability icons, and gold card frames."""

    def __init__(self) -> None:
        self.choices: list[Ability] = []
        self.pending_rarity: str = ""
        self.replace_mode = False
        self.selected_ability: Ability | None = None

    def _init_choices(self, game_state: GameState) -> None:
        if not game_state.player.pending_ability_choices:
            return

        self.pending_rarity = game_state.player.pending_ability_choices[0]
        rarity_enum = AbilityRarity.STANDARD if self.pending_rarity in ("STANDARD", "PROMOTION") else AbilityRarity.EPIC
        known = [a.id for a in game_state.player.all_passives + game_state.player.abilities.active]
        self.choices = get_random_abilities(
            rarity_enum,
            known,
            player_class=game_state.player.class_id,
            count=2,
        )

    def update(self, game_state: GameState) -> None:
        if not self.choices and game_state.player.pending_ability_choices:
            self._init_choices(game_state)

        card_w, card_h = 216, 48
        card_x = 20
        card1_y = 90
        card2_y = 146
        skip_x, skip_y, skip_w, skip_h = SCREEN_WIDTH - 76, 226, 66, 18

        if self.replace_mode and self.selected_ability:
            if pyxel.btnp(pyxel.KEY_1) or pyxel.btnp(pyxel.KEY_KP_1) or Renderer.is_clicked(card_x, card1_y, card_w,
                                                                                            card_h):
                game_state.player.abilities.replace_ability(self.selected_ability, 0)
                self._finish_choice(game_state)
            elif pyxel.btnp(pyxel.KEY_2) or pyxel.btnp(pyxel.KEY_KP_2) or Renderer.is_clicked(card_x, card2_y, card_w,
                                                                                              card_h):
                game_state.player.abilities.replace_ability(self.selected_ability, 1)
                self._finish_choice(game_state)
            elif pyxel.btnp(pyxel.KEY_ESCAPE) or Renderer.is_clicked(skip_x, skip_y, skip_w, skip_h):
                self.replace_mode = False
                self.selected_ability = None
            return

        if pyxel.btnp(pyxel.KEY_ESCAPE) or Renderer.is_clicked(skip_x, skip_y, skip_w, skip_h):
            self._finish_choice(game_state)
            return

        if (pyxel.btnp(pyxel.KEY_1) or pyxel.btnp(pyxel.KEY_KP_1) or Renderer.is_clicked(card_x, card1_y, card_w,
                                                                                         card_h)) and len(
                self.choices) > 0:
            self._handle_selection(game_state, self.choices[0])
        elif (pyxel.btnp(pyxel.KEY_2) or pyxel.btnp(pyxel.KEY_KP_2) or Renderer.is_clicked(card_x, card2_y, card_w,
                                                                                           card_h)) and len(
                self.choices) > 1:
            self._handle_selection(game_state, self.choices[1])

    def _handle_selection(self, game_state: GameState, chosen: Ability) -> None:
        added = game_state.player.abilities.add_ability(chosen)
        if added:
            self._finish_choice(game_state)
        else:
            self.replace_mode = True
            self.selected_ability = chosen

    def _finish_choice(self, game_state: GameState) -> None:
        game_state.player.pending_ability_choices.pop(0)
        self.choices = []
        self.replace_mode = False
        self.selected_ability = None

        if game_state.player.pending_ability_choices:
            self._init_choices(game_state)
        elif game_state.promotion_return_mode is not None:
            return_mode = game_state.promotion_return_mode
            game_state.promotion_return_mode = None
            game_state.switch_mode(return_mode)
        else:
            current_node = game_state.map_graph.current_node
            if current_node and current_node.node_type == NodeType.BOSS:
                if game_state.act < 3:
                    game_state.act += 1
                    game_state.floor = 1
                    if game_state.biome_route_mode == "PATHFINDER":
                        game_state.switch_mode(GameMode.BIOME_SELECT)
                    else:
                        game_state.advance_act()
                else:
                    game_state.switch_mode(GameMode.VICTORY)
            else:
                game_state.switch_mode(GameMode.MAP)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        renderer.draw_hud(game_state.player, game_state.floor)

        box_x, box_y, box_w, box_h = 4, 25, SCREEN_WIDTH - 8, SCREEN_HEIGHT - 28
        fc = pyxel.frame_count

        # =====================================================================
        # 1. GOTHIC CHAMBER BACKDROP & TORCHES
        # =====================================================================
        pyxel.rect(box_x, box_y, box_w, box_h, COLOR_BLACK)

        # Masonry stone wall columns
        for px in [14, 46, SCREEN_WIDTH - 54, SCREEN_WIDTH - 22]:
            pyxel.rect(px, box_y + 2, 8, box_h - 14, COLOR_NAVY)
            for my in range(box_y + 6, box_y + box_h - 14, 8):
                pyxel.line(px, my, px + 7, my, COLOR_DARK_BLUE)
                pyxel.pset(px + ((my // 4) % 6), my + 3, COLOR_LIGHT_BLUE)

        # Central vaulted archway
        pyxel.rect(74, box_y + 8, 108, 48, COLOR_DARK_BLUE)
        pyxel.tri(74, box_y + 8, 128, box_y + 2, 181, box_y + 8, COLOR_DARK_BLUE)
        pyxel.rect(78, box_y + 12, 100, 44, COLOR_BLACK)
        pyxel.tri(78, box_y + 12, 128, box_y + 6, 177, box_y + 12, COLOR_BLACK)

        # Cobblestone ground at bottom
        ground_y = box_y + box_h - 14
        pyxel.rect(box_x + 2, ground_y, box_w - 4, 12, COLOR_DARK_BLUE)
        for gx in range(box_x + 6, box_x + box_w - 8, 12):
            pyxel.line(gx, ground_y + 3, gx + 6, ground_y + 3, COLOR_NAVY)
            pyxel.line(gx + 6, ground_y + 8, gx + 11, ground_y + 8, COLOR_NAVY)

        # Four Animated Wall Torches
        torch_positions = [
            (12, 48), (12, 172),
            (SCREEN_WIDTH - 16, 48), (SCREEN_WIDTH - 16, 172),
        ]
        for t_idx, (tx, ty) in enumerate(torch_positions):
            pyxel.rect(tx - 1, ty + 6, 4, 3, COLOR_BROWN)
            pyxel.rect(tx - 1, ty + 2, 4, 4, COLOR_ORANGE)
            pyxel.pset(tx + (1 if (fc + t_idx) % 4 < 2 else 0), ty, COLOR_YELLOW)
            pyxel.pset(tx + 1, ty + 1, COLOR_WHITE)
            if (fc + t_idx * 3) % 3 == 0:
                pyxel.pset(tx + ((fc // 2) % 3) - 1, ty - 2, COLOR_YELLOW)

        # Hanging Crimson Banners on Left & Right
        for bx in [26, SCREEN_WIDTH - 36]:
            pyxel.rect(bx, box_y + 4, 10, 20, COLOR_RED)
            pyxel.tri(bx, box_y + 24, bx + 5, box_y + 28, bx + 9, box_y + 24, COLOR_RED)
            pyxel.rectb(bx, box_y + 4, 10, 20, COLOR_ORANGE)
            pyxel.pset(bx + 4, box_y + 11, COLOR_YELLOW)
            pyxel.pset(bx + 5, box_y + 11, COLOR_YELLOW)

        # Outer Gothic Room Double Border
        pyxel.rectb(box_x, box_y, box_w, box_h, COLOR_DARK_BLUE)
        pyxel.rectb(box_x + 2, box_y + 2, box_w - 4, box_h - 4, COLOR_NAVY)

        for corner_x, corner_y in [
            (box_x + 1, box_y + 1),
            (box_x + box_w - 2, box_y + 1),
            (box_x + 1, box_y + box_h - 2),
            (box_x + box_w - 2, box_y + box_h - 2),
        ]:
            pyxel.pset(corner_x, corner_y, COLOR_LIGHT_BLUE)
            pyxel.pset(corner_x - 1, corner_y, COLOR_DARK_BLUE)
            pyxel.pset(corner_x + 1, corner_y, COLOR_DARK_BLUE)
            pyxel.pset(corner_x, corner_y - 1, COLOR_DARK_BLUE)
            pyxel.pset(corner_x, corner_y + 1, COLOR_DARK_BLUE)

        # =====================================================================
        # 2. HEADER BANNER PLAQUE (LEVEL UP! / ABILITY CHOICE)
        # =====================================================================
        bw, bh = 154, 26
        bx = SCREEN_WIDTH // 2 - bw // 2
        by = box_y + 4

        renderer.draw_box(bx, by, bw, bh, bg_col=COLOR_BLACK, border_col=COLOR_LIGHT_BLUE)
        pyxel.rectb(bx + 1, by + 1, bw - 2, bh - 2, COLOR_NAVY)

        # Corner Brackets
        pyxel.line(bx + 3, by + 3, bx + 7, by + 3, COLOR_LIGHT_BLUE)
        pyxel.line(bx + 3, by + 3, bx + 3, by + 7, COLOR_LIGHT_BLUE)
        pyxel.line(bx + bw - 4, by + 3, bx + bw - 8, by + 3, COLOR_LIGHT_BLUE)
        pyxel.line(bx + bw - 4, by + 3, bx + bw - 4, by + 7, COLOR_LIGHT_BLUE)

        # Star Sparkles
        for sx, sy in [(bx + 10, by + 8), (bx + 18, by + 14), (bx + bw - 12, by + 8), (bx + bw - 20, by + 14)]:
            pyxel.pset(sx, sy, COLOR_WHITE)
            pyxel.pset(sx - 1, sy, COLOR_YELLOW)
            pyxel.pset(sx + 1, sy, COLOR_YELLOW)
            pyxel.pset(sx, sy - 1, COLOR_YELLOW)
            pyxel.pset(sx, sy + 1, COLOR_YELLOW)

        if self.replace_mode and self.selected_ability:
            v_title = "REPLACE ABILITY" if i18n.locale == "en" else "REEMPLAZAR"
            sub_title = f"New: {self.selected_ability.localized_name}" if i18n.locale == "en" else f"Nueva: {self.selected_ability.localized_name}"
            renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(v_title) // 2, by + 5, v_title, COLOR_YELLOW)
            renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(sub_title) // 2, by + 15, sub_title,
                               COLOR_LIME)
        else:
            v_title = ("PROMOTION!" if self.pending_rarity == "PROMOTION" else "LEVEL UP!") if i18n.locale == "en" else ("¡PROMOCION!" if self.pending_rarity == "PROMOTION" else "¡SUBIDA DE NIVEL!")
            rarity_label = "PROMOTION ABILITY CHOICE" if self.pending_rarity == "PROMOTION" else ("STANDARD ABILITY CHOICE" if self.pending_rarity == "STANDARD" else "EPIC ABILITY CHOICE")
            if i18n.locale == "es":
                rarity_label = "HABILIDAD DE PROMOCION" if self.pending_rarity == "PROMOTION" else ("ELECCIÓN ESTÁNDAR" if self.pending_rarity == "STANDARD" else "ELECCIÓN ÉPICA")

            renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(v_title) // 2, by + 5, v_title, COLOR_YELLOW)
            renderer.draw_text(SCREEN_WIDTH // 2 - renderer.get_text_width(rarity_label) // 2, by + 15, rarity_label,
                               COLOR_WHITE)

        # =====================================================================
        # 3. ABILITY SELECTION CARDS
        # =====================================================================
        card_w, card_h = 216, 48
        card_x = 20
        card1_y = 90
        card2_y = 146

        if self.replace_mode and self.selected_ability:
            target_list = game_state.player.abilities.active if self.selected_ability.ability_type == AbilityType.ACTIVE else game_state.player.abilities.passive
            cards_to_draw = target_list[:2]
        else:
            cards_to_draw = self.choices[:2]

        pulse = (fc // 6) % 2

        for i, ab in enumerate(cards_to_draw):
            cy = card1_y if i == 0 else card2_y
            is_active_card = (i == 0)

            border_col = COLOR_YELLOW if is_active_card else COLOR_LIGHT_BLUE
            fill_col = COLOR_DARK_BLUE if is_active_card else COLOR_BLACK
            renderer.draw_box(card_x, cy, card_w, card_h, bg_col=fill_col, border_col=border_col)

            if is_active_card:
                pyxel.rectb(card_x + 1, cy + 1, card_w - 2, card_h - 2, COLOR_YELLOW if pulse == 0 else COLOR_ORANGE)
                pyxel.pset(card_x + 2, cy + 2, COLOR_WHITE)
                pyxel.pset(card_x + card_w - 3, cy + 2, COLOR_WHITE)
                pyxel.pset(card_x + 2, cy + card_h - 3, COLOR_WHITE)
                pyxel.pset(card_x + card_w - 3, cy + card_h - 3, COLOR_WHITE)
                pyxel.tri(card_x - 7, cy + 20, card_x - 7, cy + 28, card_x - 3, cy + 24, COLOR_YELLOW)

            # Left 32x38 Thumbnail Frame
            icon_x = card_x + 6
            icon_y = cy + 5
            pyxel.rect(icon_x, icon_y, 32, 38, COLOR_NAVY)
            pyxel.rectb(icon_x, icon_y, 32, 38, COLOR_LIGHT_BLUE if not is_active_card else COLOR_YELLOW)

            # Blit 16x16 icon from Bank 1 (centered inside the 32x38 frame)
            bank, u, v = get_ability_icon(ab.id)
            spr_x = icon_x + 8
            spr_y = icon_y + 11
            pyxel.blt(spr_x, spr_y, bank, u, v, 16, 16, 0)

            # Ability Name & Active/Passive Tag
            text_x = icon_x + 38
            slot_num = i + 1
            name_text = f"[{slot_num}] {ab.localized_name}"
            renderer.draw_text(text_x, cy + 7, name_text, COLOR_YELLOW if is_active_card else COLOR_WHITE)

            type_badge = f"({ab.localized_type.upper()})"
            type_x = text_x + renderer.get_text_width(name_text) + 6
            type_col = COLOR_CYAN if ab.ability_type == AbilityType.ACTIVE else COLOR_LIME
            renderer.draw_text(type_x, cy + 7, type_badge, type_col)

            # Formatted Ability Description
            desc_lines = renderer.wrap_text(ab.localized_description, max_chars_per_line=27)
            for l_idx, line in enumerate(desc_lines[:3]):
                renderer.draw_text(text_x, cy + 19 + l_idx * 9, line, COLOR_WHITE)

        # =====================================================================
        # 4. BOTTOM ACTION CONTROL BAR
        # =====================================================================
        if self.replace_mode:
            instr_text = t("replace_ability_instruction")
            skip_label = t("btn_cancel")
        else:
            instr_text = t("select_ability_instruction")
            skip_label = t("btn_skip")

        renderer.draw_text(16, 234, instr_text, COLOR_WHITE)
        renderer.draw_button(SCREEN_WIDTH - 76, 226, 66, 18, skip_label, bg_col=COLOR_BLACK,
                             border_col=COLOR_LIGHT_BLUE, text_col=COLOR_PEACH)
