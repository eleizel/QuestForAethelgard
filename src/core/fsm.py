"""Finite State Machine (FSM) and State Pattern for game flow and mode transitions.

Replaces monolithic conditional branching and mode flags with explicit ModeState classes
that enforce valid transitions, lifecycle callbacks (on_enter/on_exit), and overlay access rules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.game_state import GameMode, GameState


class ModeState:
    """Base class for all discrete operational states."""

    def __init__(self, mode: GameMode) -> None:
        self.mode = mode

    def can_open_overlay(self, context: GameState) -> bool:
        """Whether player can open modal overlays (Inventory, Character Sheet)."""
        return False

    def can_transition_to(self, target_mode: GameMode) -> bool:
        """Whether a direct transition from this state to target_mode is permitted."""
        return True

    def on_enter(self, context: GameState, previous_mode: GameMode) -> None:
        """Hook called immediately upon entering this state."""
        pass

    def on_exit(self, context: GameState, next_mode: GameMode) -> None:
        """Hook called immediately before exiting this state."""
        pass


class WelcomeState(ModeState):
    def can_open_overlay(self, context: GameState) -> bool:
        return False


class ClassSelectState(ModeState):
    def can_open_overlay(self, context: GameState) -> bool:
        return False


class CreditsState(ModeState):
    def can_open_overlay(self, context: GameState) -> bool:
        return False


class BiomeSelectState(ModeState):
    def can_open_overlay(self, context: GameState) -> bool:
        return False


class MapState(ModeState):
    def can_open_overlay(self, context: GameState) -> bool:
        return True


class CombatState(ModeState):
    def can_open_overlay(self, context: GameState) -> bool:
        # Overlays are strictly blocked if a timing-sensitive QTE is active
        if context.combat is not None and context.combat.is_qte_active():
            return False
        return True


class InventoryState(ModeState):
    def can_open_overlay(self, context: GameState) -> bool:
        return True


class CharacterState(ModeState):
    def can_open_overlay(self, context: GameState) -> bool:
        return True


class EventsState(ModeState):
    def can_open_overlay(self, context: GameState) -> bool:
        return True


class ShopState(ModeState):
    def can_open_overlay(self, context: GameState) -> bool:
        return True


class LootState(ModeState):
    def can_open_overlay(self, context: GameState) -> bool:
        return True


class AbilityChoiceState(ModeState):
    def can_open_overlay(self, context: GameState) -> bool:
        return False


class PromotionState(ModeState):
    def can_open_overlay(self, context: GameState) -> bool:
        return False


class GameOverState(ModeState):
    def can_open_overlay(self, context: GameState) -> bool:
        return False

    def can_transition_to(self, target_mode: GameMode) -> bool:
        """A defeated run can only return to title/credits or remain visible."""
        from src.core.game_state import GameMode

        return target_mode in {GameMode.GAME_OVER, GameMode.WELCOME, GameMode.CREDITS}


class VictoryState(ModeState):
    def can_open_overlay(self, context: GameState) -> bool:
        return False

    def can_transition_to(self, target_mode: GameMode) -> bool:
        """A completed run cannot re-enter gameplay without a fresh title flow."""
        from src.core.game_state import GameMode

        return target_mode in {GameMode.VICTORY, GameMode.WELCOME, GameMode.CREDITS}


class GameStateMachine:
    """Manages mode transitions, transition guards, and state lifecycle."""

    def __init__(self, initial_mode: GameMode) -> None:
        from src.core.game_state import GameMode

        self._states: dict[GameMode, ModeState] = {
            GameMode.WELCOME: WelcomeState(GameMode.WELCOME),
            GameMode.CLASS_SELECT: ClassSelectState(GameMode.CLASS_SELECT),
            GameMode.CREDITS: CreditsState(GameMode.CREDITS),
            GameMode.BIOME_SELECT: BiomeSelectState(GameMode.BIOME_SELECT),
            GameMode.MAP: MapState(GameMode.MAP),
            GameMode.COMBAT: CombatState(GameMode.COMBAT),
            GameMode.INVENTORY: InventoryState(GameMode.INVENTORY),
            GameMode.CHARACTER: CharacterState(GameMode.CHARACTER),
            GameMode.EVENTS: EventsState(GameMode.EVENTS),
            GameMode.SHOP: ShopState(GameMode.SHOP),
            GameMode.LOOT: LootState(GameMode.LOOT),
            GameMode.ABILITY_CHOICE: AbilityChoiceState(GameMode.ABILITY_CHOICE),
            GameMode.PROMOTION: PromotionState(GameMode.PROMOTION),
            GameMode.GAME_OVER: GameOverState(GameMode.GAME_OVER),
            GameMode.VICTORY: VictoryState(GameMode.VICTORY),
        }

        self.current_mode: GameMode = initial_mode
        self.previous_mode: GameMode = initial_mode

    @property
    def current_state(self) -> ModeState:
        """Retrieve the active ModeState handler."""
        return self._states[self.current_mode]

    def can_open_overlay(self, context: GameState) -> bool:
        """Check whether the active state permits opening modal overlays."""
        return self.current_state.can_open_overlay(context)

    def can_transition_to(self, target_mode: GameMode) -> bool:
        """Validate if the active state allows transition to target_mode."""
        return self.current_state.can_transition_to(target_mode)

    def transition_to(
        self,
        context: GameState,
        target_mode: GameMode,
        force: bool = False,
    ) -> bool:
        """Perform a state transition with lifecycle hooks."""
        if not force and not self.can_transition_to(target_mode):
            return False

        old_state = self.current_state
        prev_mode = self.current_mode

        old_state.on_exit(context, target_mode)

        self.previous_mode = prev_mode
        self.current_mode = target_mode

        new_state = self._states[target_mode]
        new_state.on_enter(context, prev_mode)

        return True
