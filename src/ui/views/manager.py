from __future__ import annotations

from typing import TYPE_CHECKING

import pyxel

from src.core.game_state import GameMode
from src.ui.renderer import Renderer
from src.ui.views.ability_choice import AbilityChoiceView
from src.ui.views.base import View
from src.ui.views.biome_select import BiomeSelectView
from src.ui.views.class_select import ClassSelectView
from src.ui.views.character import CharacterView
from src.ui.views.combat import CombatView
from src.ui.views.credits import CreditsView
from src.ui.views.end_game import EndGameView
from src.ui.views.events import EventsView
from src.ui.views.inventory import InventoryView
from src.ui.views.loot import LootView
from src.ui.views.promotion import PromotionView
from src.ui.views.map import MapView
from src.ui.views.shop import ShopView
from src.ui.views.welcome import WelcomeView

if TYPE_CHECKING:
    from src.core.game_state import GameState


class ViewManager:
    """Manages view selection and delegates update/render calls."""

    def __init__(self) -> None:
        self.views: dict[GameMode, View] = {
            GameMode.WELCOME: WelcomeView(),
            GameMode.CLASS_SELECT: ClassSelectView(),
            GameMode.CREDITS: CreditsView(),
            GameMode.BIOME_SELECT: BiomeSelectView(),
            GameMode.MAP: MapView(),
            GameMode.COMBAT: CombatView(),
            GameMode.INVENTORY: InventoryView(),
            GameMode.CHARACTER: CharacterView(),
            GameMode.EVENTS: EventsView(),
            GameMode.GAME_OVER: EndGameView(is_victory=False),
            GameMode.VICTORY: EndGameView(is_victory=True),
            GameMode.ABILITY_CHOICE: AbilityChoiceView(),
            GameMode.LOOT: LootView(),
            GameMode.SHOP: ShopView(),
            GameMode.PROMOTION: PromotionView(),
        }

    def update(self, game_state: GameState) -> None:
        if game_state.current_mode not in (GameMode.LOOT, GameMode.GAME_OVER, GameMode.VICTORY,
                                           GameMode.WELCOME, GameMode.CLASS_SELECT) and game_state.player.promotion_due:
            game_state.begin_promotion(game_state.current_mode)

        overlay_modes = (
            GameMode.MAP, GameMode.COMBAT, GameMode.EVENTS, GameMode.INVENTORY,
            GameMode.CHARACTER, GameMode.LOOT, GameMode.SHOP,
        )
        qte_blocking = (
            game_state.current_mode == GameMode.COMBAT
            and game_state.combat is not None
            and game_state.combat.is_qte_active()
        )
        if game_state.current_mode in overlay_modes and not qte_blocking:
            inv_clicked = Renderer.is_clicked(222, 3, 30, 16)
            character_clicked = Renderer.is_clicked(188, 3, 30, 16)
            if game_state.current_mode == GameMode.CHARACTER and (
                    pyxel.btnp(pyxel.KEY_C) or character_clicked or pyxel.btnp(pyxel.KEY_ESCAPE)):
                game_state.toggle_character()
                return
            if game_state.current_mode == GameMode.INVENTORY and (
                    pyxel.btnp(pyxel.KEY_I) or inv_clicked or pyxel.btnp(pyxel.KEY_ESCAPE)):
                game_state.toggle_inventory()
                return
            if pyxel.btnp(pyxel.KEY_C) or character_clicked:
                game_state.toggle_character()
                return
            if pyxel.btnp(pyxel.KEY_I) or inv_clicked:
                game_state.toggle_inventory()
                return

        view = self.views.get(game_state.current_mode)
        if view:
            view.update(game_state)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        view = self.views.get(game_state.current_mode)
        if view:
            view.draw(game_state, renderer)
