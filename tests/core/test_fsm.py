"""Unit tests for GameStateMachine and ModeState protocol implementations."""

import pytest
from src.core.game_state import GameMode, GameState
from src.core.fsm import GameStateMachine, ModeState, MapState, CombatState, WelcomeState


def test_fsm_initial_state():
    """FSM initializes with provided start mode."""
    fsm = GameStateMachine(initial_mode=GameMode.WELCOME)
    assert fsm.current_mode == GameMode.WELCOME
    assert fsm.previous_mode == GameMode.WELCOME
    assert isinstance(fsm.current_state, WelcomeState)


def test_fsm_transitions():
    """FSM updates current and previous mode on transition."""
    state = GameState()
    fsm = GameStateMachine(initial_mode=GameMode.WELCOME)

    success = fsm.transition_to(state, GameMode.CLASS_SELECT)
    assert success is True
    assert fsm.current_mode == GameMode.CLASS_SELECT
    assert fsm.previous_mode == GameMode.WELCOME

    fsm.transition_to(state, GameMode.MAP)
    assert fsm.current_mode == GameMode.MAP
    assert fsm.previous_mode == GameMode.CLASS_SELECT


def test_overlay_access_rules():
    """can_open_overlay is permitted on exploration/menu states and blocked on narrative/title states."""
    state = GameState()
    fsm = GameStateMachine(initial_mode=GameMode.WELCOME)

    # Welcome screen cannot open overlay
    assert fsm.can_open_overlay(state) is False

    # Map screen can open overlay
    fsm.transition_to(state, GameMode.MAP)
    assert fsm.can_open_overlay(state) is True

    # Shop & Loot can open overlay
    fsm.transition_to(state, GameMode.SHOP)
    assert fsm.can_open_overlay(state) is True
    fsm.transition_to(state, GameMode.LOOT)
    assert fsm.can_open_overlay(state) is True

    # Ability Choice cannot open overlay
    fsm.transition_to(state, GameMode.ABILITY_CHOICE)
    assert fsm.can_open_overlay(state) is False


def test_combat_qte_blocks_overlay():
    """During Combat, overlays are allowed during normal ticks but blocked during an active QTE."""
    state = GameState()
    state.switch_mode(GameMode.COMBAT)

    # Mock combat with no QTE
    class MockCombatNoQTE:
        def is_qte_active(self):
            return False

    state.combat = MockCombatNoQTE()
    assert state.can_open_overlay() is True

    # Mock combat with active QTE
    class MockCombatWithQTE:
        def is_qte_active(self):
            return True

    state.combat = MockCombatWithQTE()
    assert state.can_open_overlay() is False


def test_gamestate_delegation_sync():
    """GameState and FSM remain strictly synchronized during switches."""
    state = GameState()
    assert state.current_mode == GameMode.WELCOME

    state.switch_mode(GameMode.MAP)
    assert state.current_mode == GameMode.MAP
    assert state.fsm.current_mode == GameMode.MAP
    assert state.previous_mode == GameMode.WELCOME

    state.switch_mode(GameMode.INVENTORY)
    assert state.current_mode == GameMode.INVENTORY
    assert state.fsm.current_mode == GameMode.INVENTORY
    assert state.previous_mode == GameMode.MAP


@pytest.mark.parametrize("terminal_mode", [GameMode.GAME_OVER, GameMode.VICTORY])
def test_terminal_states_reject_gameplay_reentry(terminal_mode):
    """Terminal screens can only lead back through the title/credits flow."""
    state = GameState()
    state.switch_mode(terminal_mode)

    assert state.switch_mode(GameMode.COMBAT) is False
    assert state.current_mode == terminal_mode
    assert state.switch_mode(GameMode.WELCOME) is True
    assert state.current_mode == GameMode.WELCOME


def test_modal_stack_nested_overlays():
    """Deeply nested modal overlays retain their precise return context."""
    state = GameState()
    state.switch_mode(GameMode.MAP)

    assert state.current_mode == GameMode.MAP
    assert len(state.modal_stack) == 0

    # Open Inventory overlay
    state.push_modal(GameMode.INVENTORY)
    assert state.current_mode == GameMode.INVENTORY
    assert state.modal_stack == [GameMode.MAP]

    # Nest Character sheet on top of Inventory
    state.push_modal(GameMode.CHARACTER)
    assert state.current_mode == GameMode.CHARACTER
    assert state.modal_stack == [GameMode.MAP, GameMode.INVENTORY]

    # Pop Character sheet -> restores Inventory
    assert state.pop_modal() is True
    assert state.current_mode == GameMode.INVENTORY
    assert state.modal_stack == [GameMode.MAP]

    # Pop Inventory -> restores Map
    assert state.pop_modal() is True
    assert state.current_mode == GameMode.MAP
    assert state.modal_stack == []
