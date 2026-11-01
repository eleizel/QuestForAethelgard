"""Memento and Repository patterns for decoupled run persistence.

Separates snapshot data models (RunMemento) and persistence mechanisms (RunRepository)
from live domain entities, enabling pluggable backends (File, Memory, Web LocalStorage).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol


SAVE_STORAGE_KEY = "quest_for_aethelgard_save"
CURRENT_SAVE_VERSION = 1


class StorageBackend(Protocol):
    """Protocol defining primitive key-value persistence operations."""

    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str) -> bool: ...
    def remove(self, key: str) -> bool: ...
    def exists(self, key: str) -> bool: ...


class MemoryStorageBackend:
    """In-memory key-value storage for testing, bots, and headless simulations."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str) -> bool:
        self._data[key] = value
        return True

    def remove(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        return key in self._data and bool(self._data[key])

    def clear(self) -> None:
        self._data.clear()


@dataclass(frozen=True)
class RunMemento:
    """Immutable snapshot of a complete game run state (Memento Pattern).

    Contains exclusively serializable primitive dictionaries and scalar values,
    completely independent of live entity objects, display contexts, or audio systems.
    """

    save_version: int
    floor: int
    act: int
    biome_route_mode: str
    current_biome: str
    current_mode_name: str
    previous_mode_name: str
    player_data: dict[str, Any]
    map_data: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        """Convert memento to a plain JSON-serializable dictionary."""
        return {
            "save_version": self.save_version,
            "floor": self.floor,
            "act": self.act,
            "biome_route_mode": self.biome_route_mode,
            "current_biome": self.current_biome,
            "current_mode": self.current_mode_name,
            "previous_mode": self.previous_mode_name,
            "player": self.player_data,
            "map_graph": self.map_data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunMemento:
        """Reconstruct a RunMemento from a parsed dictionary."""
        return cls(
            save_version=int(data.get("save_version", CURRENT_SAVE_VERSION)),
            floor=int(data.get("floor", 1)),
            act=int(data.get("act", 1)),
            biome_route_mode=str(data.get("biome_route_mode", "FATE")),
            current_biome=str(data.get("current_biome", "arboretum")),
            current_mode_name=str(data.get("current_mode", "MAP")),
            previous_mode_name=str(data.get("previous_mode", "MAP")),
            player_data=dict(data.get("player", {})),
            map_data=data.get("map_graph"),
        )


class RunRepository:
    """Repository managing memento serialization and storage operations."""

    def __init__(self, storage: StorageBackend) -> None:
        self.storage = storage

    def save(self, memento: RunMemento) -> bool:
        """Persist a RunMemento to storage."""
        try:
            payload = memento.to_dict()
            json_str = json.dumps(payload, separators=(",", ":"))
            return self.storage.set(SAVE_STORAGE_KEY, json_str)
        except Exception as e:
            print(f"RunRepository.save error: {e}")
            return False

    def load(self) -> RunMemento | None:
        """Retrieve and parse a saved RunMemento, or None if absent/invalid."""
        raw = self.storage.get(SAVE_STORAGE_KEY)
        if not raw:
            return None
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "player" in data:
                return RunMemento.from_dict(data)
            return None
        except Exception as e:
            print(f"RunRepository.load error: {e}")
            return None

    def delete(self) -> bool:
        """Remove saved memento from storage."""
        return self.storage.remove(SAVE_STORAGE_KEY)

    def exists(self) -> bool:
        """Check if a saved memento exists in storage."""
        return self.storage.exists(SAVE_STORAGE_KEY)
