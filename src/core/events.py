"""Domain events and EventBus for reactive decoupling.

Allows domain systems (Combat, Loot, Progression) to emit signals (e.g. AudioCue,
DamageDealt, StateChanged) without depending on hardware, audio drivers, or UI views.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, TypeVar, Type

T = TypeVar("T", bound="DomainEvent")


class AudioCue(Enum):
    """Platform-agnostic sound effect trigger."""
    HIT = auto()
    CRIT = auto()
    HEAL = auto()
    CLICK = auto()
    VICTORY = auto()
    DEFEAT = auto()
    CHEST = auto()
    DOOR = auto()


@dataclass(frozen=True)
class DomainEvent:
    """Base marker class for all domain events."""
    pass


@dataclass(frozen=True)
class AudioCueEvent(DomainEvent):
    """Audio cue requested by domain logic."""
    cue: AudioCue


class EventBus:
    """Drainable domain event queue with optional immediate subscriptions."""

    def __init__(self) -> None:
        self._queue: list[DomainEvent] = []
        self._subscribers: dict[type, list[Callable[[Any], None]]] = {}

    def emit(self, event: DomainEvent) -> None:
        """Enqueue an event and notify immediate subscribers."""
        self._queue.append(event)
        handlers = self._subscribers.get(type(event), [])
        for handler in handlers:
            handler(event)

    def emit_audio(self, cue: AudioCue) -> None:
        """Convenience helper to emit an AudioCueEvent."""
        self.emit(AudioCueEvent(cue=cue))

    def drain(self) -> list[DomainEvent]:
        """Drain and return all queued events since last drain."""
        events = list(self._queue)
        self._queue.clear()
        return events

    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        """Register a reactive listener for an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def clear(self) -> None:
        """Clear queued events without dispatching."""
        self._queue.clear()


# Default singleton instance for game sessions
event_bus = EventBus()
