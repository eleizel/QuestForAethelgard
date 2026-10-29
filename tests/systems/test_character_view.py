from __future__ import annotations

import textwrap

from src.core.game_state import GameMode, GameState
from src.systems.abilities import Ability, AbilityRarity, AbilityType
from src.ui.views.character import CharacterView


def test_character_and_inventory_overlays_return_to_their_previous_views():
    state = GameState()
    state.current_mode = GameMode.MAP

    state.toggle_character()
    assert state.current_mode == GameMode.CHARACTER

    state.toggle_inventory()
    assert state.current_mode == GameMode.INVENTORY

    state.toggle_inventory()
    assert state.current_mode == GameMode.CHARACTER

    state.toggle_character()
    assert state.current_mode == GameMode.MAP


def test_character_view_renders_stats_and_current_abilities():
    player_state = GameState()
    passive = Ability(
        id="test_sheet_passive",
        name="Test Passive",
        description="A sample passive ability.",
        ability_type=AbilityType.PASSIVE,
        rarity=AbilityRarity.STANDARD,
    )
    signature = Ability(
        id="test_sheet_signature",
        name="Test Signature",
        description="A permanent class feature.",
        ability_type=AbilityType.PASSIVE,
        rarity=AbilityRarity.EPIC,
    )
    player_state.player.abilities.passive.append(passive)
    player_state.player.signature_passive = signature

    class RecordingRenderer:
        def __init__(self):
            self.text = []

        def draw_hud(self, *_args):
            pass

        def draw_box(self, *_args, **_kwargs):
            pass

        def draw_bar(self, *_args, **_kwargs):
            pass

        def draw_text(self, _x, _y, value, _color):
            self.text.append(value)

        @staticmethod
        def wrap_text(value, max_chars_per_line):
            return textwrap.wrap(value, width=max_chars_per_line)

    renderer = RecordingRenderer()
    CharacterView().draw(player_state, renderer)
    rendered = "\n".join(renderer.text)

    assert "ATK:" in rendered
    assert "DEF:" in rendered
    assert "SPD:" in rendered
    assert "Test Passive" in rendered
    assert "Test Signature" in rendered
    assert player_state.player.abilities.active[0].localized_name in rendered
