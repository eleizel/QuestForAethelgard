"""Command pattern definitions for player interactions and view mutations.

Encapsulates user intents (e.g. buying an item, taking loot, picking an ability)
into strongly typed command objects with standard CommandResult feedback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.events import DomainEvent
    from src.entities.item import Item
    from src.systems.abilities import Ability


@dataclass(frozen=True)
class Command:
    """Base marker class for player / UI commands."""
    pass


@dataclass(frozen=True)
class BuyItemCommand(Command):
    """Attempt to purchase an item from the merchant catalog."""
    stock_index: int


@dataclass(frozen=True)
class SellItemCommand(Command):
    """Attempt to sell an item from the player pouch to the merchant."""
    pouch_index: int


@dataclass(frozen=True)
class TakeLootCommand(Command):
    """Attempt to claim a single loot item into the pouch."""
    loot_index: int


@dataclass(frozen=True)
class TakeAllLootCommand(Command):
    """Attempt to claim all available loot items into the pouch."""
    pass


@dataclass(frozen=True)
class ChooseAbilityCommand(Command):
    """Select an ability from an active ability draft."""
    ability: Ability
    replace_index: int | None = None


@dataclass(frozen=True)
class SkipAbilityDraftCommand(Command):
    """Skip the current ability draft without choosing."""
    pass


@dataclass(frozen=True)
class PromoteClassCommand(Command):
    """Confirm promotion to a chosen advanced class."""
    class_id: str


@dataclass(frozen=True)
class CommandResult:
    """Standardized response from domain services."""
    success: bool
    message: str = ""
    error_code: str | None = None
    events: list[DomainEvent] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
