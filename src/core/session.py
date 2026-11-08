"""Application Facade unifying game state, command dispatching, events, and persistence.

Acts as the primary boundary layer between frontends (Pyxel, Pygame-CE, Monte Carlo)
and the pure Python domain core. Frontends interact through high-level session commands
and snapshot queries without directly manipulating entity internals.
"""

from __future__ import annotations

import random
import secrets
from typing import TYPE_CHECKING
from src.core.commands import (
    Command,
    CommandResult,
    BuyItemCommand,
    SellItemCommand,
    TakeLootCommand,
    TakeAllLootCommand,
    ChooseAbilityCommand,
    SkipAbilityDraftCommand,
    PromoteClassCommand,
)
from src.core.events import DomainEvent, EventBus, event_bus
from src.core.game_state import GameState, GameMode
from src.core.save_manager import save_manager, SaveManager
from src.core.services import GameServices
from src.systems.combat import CombatResult, CombatSystem
from src.systems.shop_service import ShopService
from src.systems.loot_service import LootService
from src.systems.draft_service import DraftService
from src.systems.progression_service import ProgressionService

if TYPE_CHECKING:
    from src.entities.player import Player


class GameSession:
    """Facade providing a cohesive boundary for presentations and simulations."""

    def __init__(
        self,
        game_state: GameState | None = None,
        save_mgr: SaveManager | None = None,
        services: GameServices | None = None,
    ) -> None:
        if services is not None and save_mgr is not None:
            raise ValueError("Pass either services or save_mgr, not both")

        if services is None:
            run_seed = secrets.randbits(64)
            services = GameServices(
                persistence=save_mgr if save_mgr is not None else save_manager,
                event_bus=event_bus,
                rng=random.Random(run_seed),
                run_seed=run_seed,
            )
        self.services = services
        self.save_manager = self.services.persistence
        self.bus: EventBus = self.services.event_bus
        self.state: GameState = game_state if game_state is not None else GameState()
        self.state.configure_services(
            self.save_manager,
            self.services.rng,
            self.bus,
            self.services.run_seed,
        )

    @property
    def player(self) -> Player:
        """Active hero entity."""
        return self.state.player

    @property
    def current_mode(self) -> GameMode:
        """Active operational mode."""
        return self.state.current_mode

    @property
    def previous_mode(self) -> GameMode:
        """Previously active operational mode."""
        return self.state.previous_mode

    @property
    def combat(self) -> CombatSystem | None:
        """Active combat system instance if engaged in battle."""
        return self.state.combat

    def start_new_game(self, class_id: str = "warrior", route_mode: str = "FATE") -> None:
        """Initialize a new journey with chosen class and route rules."""
        self.state.start_new_game(class_id=class_id, route_mode=route_mode)

    def save_game(self) -> bool:
        """Persist current session state."""
        return self.save_manager.save_game(self.state)

    def load_game(self) -> bool:
        """Resume a saved session state."""
        return self.save_manager.load_game(self.state)

    def has_saved_game(self) -> bool:
        """Check if an active saved game is available."""
        return self.save_manager.has_save()

    def delete_save(self) -> bool:
        """Delete current saved state."""
        return self.save_manager.delete_save()

    def reset_to_title(self) -> None:
        """Return to title screen and reset session."""
        self.state.reset_to_title()

    def switch_mode(self, mode: GameMode) -> bool:
        """Transition to another operational mode."""
        return self.state.switch_mode(mode)

    def can_open_overlay(self) -> bool:
        """Check if modal overlays are allowed in the current state."""
        return self.state.can_open_overlay()

    def toggle_inventory(self) -> None:
        """Toggle inventory overlay."""
        self.state.toggle_inventory()

    def toggle_character(self) -> None:
        """Toggle character sheet overlay."""
        self.state.toggle_character()

    def select_map_node(self, node_id: int) -> bool:
        """Select a node on the exploration map and enter its encounter."""
        return self.state.select_map_node(node_id)

    def update_combat(self) -> None:
        """Advance combat simulation and handle post-battle transitions."""
        self.state.update_combat()

    def step_combat(self) -> CombatResult:
        """Advance combat simulation by one step."""
        if self.state.combat and self.state.combat.is_active():
            return self.state.combat.step()
        return CombatResult.IN_PROGRESS

    def drain_events(self) -> list[DomainEvent]:
        """Drain queued domain events."""
        return self.bus.drain()

    def dispatch(self, cmd: Command) -> CommandResult:
        """Execute player command via the appropriate domain service."""
        if isinstance(cmd, BuyItemCommand):
            return ShopService.buy_item(
                self.state.player, self.state.merchant_stock, cmd.stock_index, bus=self.bus
            )

        elif isinstance(cmd, SellItemCommand):
            return ShopService.sell_item(
                self.state.player, cmd.pouch_index, bus=self.bus
            )

        elif isinstance(cmd, TakeLootCommand):
            return LootService.take_item(
                self.state.player, self.state.pending_loot, cmd.loot_index, bus=self.bus
            )

        elif isinstance(cmd, TakeAllLootCommand):
            return LootService.take_all(
                self.state.player, self.state.pending_loot, bus=self.bus
            )

        elif isinstance(cmd, ChooseAbilityCommand):
            return DraftService.apply_selection(
                self.state.player,
                cmd.ability,
                replace_index=cmd.replace_index,
                bus=self.bus,
                consume_token=True,
            )

        elif isinstance(cmd, SkipAbilityDraftCommand):
            return DraftService.skip_draft(self.state.player, bus=self.bus)

        elif isinstance(cmd, PromoteClassCommand):
            return ProgressionService.promote_class(
                self.state.player, cmd.class_id, bus=self.bus
            )

        return CommandResult(
            success=False,
            error_code="UNKNOWN_COMMAND",
            message=f"Unhandled command: {type(cmd).__name__}",
        )
