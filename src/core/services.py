"""Application services supplied explicitly to a game session.

The domain must not reach into module-level singletons for persistence, event
delivery, or randomness.  This module defines the narrow ports that a session
needs and the value object used by composition roots and tests.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from src.core.events import EventBus

if TYPE_CHECKING:
    from src.core.game_state import GameState


class RunPersistence(Protocol):
    """Port used by a running game to persist or delete its run."""

    def save_game(self, game_state: GameState) -> bool:
        """Persist a game state snapshot."""

    def delete_save(self) -> bool:
        """Delete the active run snapshot."""


@dataclass
class GameServices:
    """Session-scoped infrastructure dependencies.

    `rng` is intentionally session-owned so callers can provide a fixed seed
    for reproducible tests and bug reports.
    """

    persistence: RunPersistence
    event_bus: EventBus
    rng: random.Random = field(default_factory=random.Random)
    run_seed: int | None = None
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("quest_for_aethelgard"))
