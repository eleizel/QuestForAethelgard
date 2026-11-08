"""Application Facade unifying game state, command dispatching, events, and persistence.















Acts as the primary boundary layer between frontends (Pyxel, Pygame-CE, Monte Carlo)







and the pure Python domain core. Frontends interact through high-level session commands







and snapshot queries without directly manipulating entity internals.







"""

from __future__ import annotations


import random


import secrets


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.systems.abilities import Ability


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


from src.core.view_models import (
    AbilityDraftViewModel,
    AbilityOptionViewModel,
    CombatantViewModel,
    CombatViewModel,
    LootItemViewModel,
    LootViewModel,
    MapNodeViewModel,
    MapViewModel,
    ShopItemViewModel,
    ShopViewModel,
    StatusViewModel,
)


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
                event_bus=EventBus(),
                rng=random.Random(run_seed),
                run_seed=run_seed,
            )

        self.services = services

        self.save_manager = self.services.persistence

        self.bus: EventBus = self.services.event_bus

        self.logger = self.services.logger

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

    @property
    def modal_stack(self) -> list[GameMode]:
        """Active modal return stack."""

        return self.state.modal_stack

    def push_modal(self, modal_mode: GameMode) -> bool:
        """Push current mode to modal stack and enter modal view."""

        return self.state.push_modal(modal_mode)

    def pop_modal(self) -> bool:
        """Pop modal stack and return to previous context."""

        return self.state.pop_modal()

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
            return ShopService.sell_item(self.state.player, cmd.pouch_index, bus=self.bus)

        elif isinstance(cmd, TakeLootCommand):
            return LootService.take_item(
                self.state.player, self.state.pending_loot, cmd.loot_index, bus=self.bus
            )

        elif isinstance(cmd, TakeAllLootCommand):
            return LootService.take_all(self.state.player, self.state.pending_loot, bus=self.bus)

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
            return ProgressionService.promote_class(self.state.player, cmd.class_id, bus=self.bus)

        return CommandResult(
            success=False,
            error_code="UNKNOWN_COMMAND",
            message=f"Unhandled command: {type(cmd).__name__}",
        )

    def generate_ability_draft(self, count: int = 2) -> list[Ability]:
        """Generate randomized ability draft candidates using the session's deterministic RNG."""

        return DraftService.generate_draft(self.state.player, count=count, rng=self.services.rng)

    def get_combat_view_model(self) -> CombatViewModel | None:
        """Generate an immutable presentation snapshot of the active combat."""

        combat = self.state.combat

        if combat is None:
            return None

        def make_combatant(actor) -> CombatantViewModel:

            max_hp = max(1, actor.base_stats.max_hp)

            hp_pct = max(0.0, min(1.0, actor.current_hp / max_hp))

            statuses = [
                StatusViewModel(
                    id=s.id,
                    name=s.name,
                    duration=s.duration,
                    stacks=getattr(s, "stacks", 1),
                )
                for s in actor.statuses
            ]

            return CombatantViewModel(
                name=actor.name,
                current_hp=actor.current_hp,
                max_hp=max_hp,
                hp_percent=hp_pct,
                attack=actor.effective_stats.attack,
                defense=actor.effective_stats.defense,
                speed=actor.effective_stats.speed,
                is_alive=actor.is_alive,
                statuses=statuses,
            )

        return CombatViewModel(
            hero=make_combatant(combat.player),
            enemy=make_combatant(combat.enemy),
            turn_count=combat.current_tick,
            is_active=combat.is_active(),
            is_qte_active=combat.is_qte_active(),
            result=combat.result.name,
            logs=[str(log) for log in combat.combat_logs],
        )

    def get_shop_view_model(self) -> ShopViewModel:
        """Generate an immutable presentation snapshot of the merchant screen."""

        from src.config import MAX_POUCH_SLOTS

        stock_vms = [
            ShopItemViewModel(
                index=i,
                item_id=item.id,
                name=item.name,
                description=item.description,
                price=price,
                item_type=item.item_type.name,
                can_afford=self.state.player.gold >= price,
            )
            for i, (item, price) in enumerate(self.state.merchant_stock)
        ]

        pouch_used = len(self.state.player.inventory.pouch)

        return ShopViewModel(
            player_gold=self.state.player.gold,
            stock=stock_vms,
            pouch_used=pouch_used,
            pouch_max=MAX_POUCH_SLOTS,
            can_buy_any=any(vm.can_afford for vm in stock_vms) and pouch_used < MAX_POUCH_SLOTS,
        )

    def get_loot_view_model(self) -> LootViewModel:
        """Generate an immutable presentation snapshot of post-battle loot."""

        from src.config import MAX_POUCH_SLOTS

        items = [
            LootItemViewModel(
                index=i,
                item_id=item.id,
                name=item.name,
                description=item.description,
                gold_value=item.gold_value,
                item_type=item.item_type.name,
            )
            for i, item in enumerate(self.state.pending_loot)
        ]

        pouch_used = len(self.state.player.inventory.pouch)

        return LootViewModel(
            items=items,
            pouch_used=pouch_used,
            pouch_max=MAX_POUCH_SLOTS,
            has_loot=len(items) > 0,
            pouch_has_space=pouch_used < MAX_POUCH_SLOTS,
        )

    def get_map_view_model(self) -> MapViewModel | None:
        """Generate an immutable presentation snapshot of the spire map."""

        graph = self.state.map_graph

        if graph is None:
            return None

        available_nodes = [
            MapNodeViewModel(
                id=n.id,
                floor=n.floor,
                node_type=n.node_type.name,
                visited=n.visited,
                available=n.available,
                outgoing_ids=list(n.outgoing_ids),
            )
            for n in graph.available_nodes
        ]

        return MapViewModel(
            act=self.state.act,
            floor=self.state.floor,
            biome=self.state.current_biome,
            current_node_id=graph.current_node_id,
            available_nodes=available_nodes,
            total_floors=len(graph.floors),
        )

    def get_ability_draft_view_model(self) -> AbilityDraftViewModel:
        """Generate an immutable presentation snapshot of pending ability choices."""

        choices = self.generate_ability_draft()

        choice_vms = [
            AbilityOptionViewModel(
                id=ab.id,
                name=ab.name,
                description=ab.description,
                rarity=ab.rarity.name,
                affinities=list(ab.affinities),
                cooldown=ab.cooldown,
            )
            for ab in choices
        ]

        pending_count = len(self.state.player.pending_ability_choices)

        return AbilityDraftViewModel(
            pending_choices_count=pending_count,
            has_pending_draft=pending_count > 0,
            choices=choice_vms,
        )
