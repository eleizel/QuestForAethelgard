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


class SaveValidationError(ValueError):
    """Raised when a save payload cannot safely be restored."""


def migrate_save_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and migrate a decoded save payload to the current schema.

    Version 1 is the first explicit schema. Older unversioned saves are treated
    as version 1 for backward compatibility. Future versions are rejected
    rather than guessed at, which prevents corrupting a newer player's run.
    """
    if not isinstance(data, dict):
        raise SaveValidationError("save payload must be an object")

    migrated = dict(data)
    raw_version = migrated.get("save_version", CURRENT_SAVE_VERSION)
    try:
        version = int(raw_version)
    except (TypeError, ValueError) as exc:
        raise SaveValidationError("save version must be an integer") from exc

    if version < 1:
        raise SaveValidationError(f"unsupported save version: {version}")
    if version > CURRENT_SAVE_VERSION:
        raise SaveValidationError(
            f"save version {version} is newer than supported version {CURRENT_SAVE_VERSION}"
        )

    # Add migrations here when CURRENT_SAVE_VERSION increases. A migration must
    # transform exactly one version and then increment `version`.
    while version < CURRENT_SAVE_VERSION:
        raise SaveValidationError(f"missing migration from save version {version}")

    player = migrated.get("player")
    if not isinstance(player, dict):
        raise SaveValidationError("save payload requires a player object")
    map_data = migrated.get("map_graph")
    if map_data is not None and not isinstance(map_data, dict):
        raise SaveValidationError("map_graph must be an object or null")

    for field_name, default in (("floor", 1), ("act", 1)):
        try:
            value = int(migrated.get(field_name, default))
        except (TypeError, ValueError) as exc:
            raise SaveValidationError(f"{field_name} must be an integer") from exc
        if value < 1:
            raise SaveValidationError(f"{field_name} must be positive")
        migrated[field_name] = value

    for field_name, default in (
        ("biome_route_mode", "FATE"),
        ("current_biome", "arboretum"),
        ("current_mode", "MAP"),
        ("previous_mode", "MAP"),
    ):
        value = migrated.get(field_name, default)
        if not isinstance(value, str):
            raise SaveValidationError(f"{field_name} must be a string")
        migrated[field_name] = value

    run_seed = migrated.get("run_seed")
    if run_seed is not None:
        try:
            migrated["run_seed"] = int(run_seed)
        except (TypeError, ValueError) as exc:
            raise SaveValidationError("run_seed must be an integer or null") from exc

    migrated["save_version"] = CURRENT_SAVE_VERSION
    return migrated


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
    run_seed: int | None = None

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
            "run_seed": self.run_seed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunMemento:
        """Reconstruct a RunMemento from a parsed dictionary."""
        data = migrate_save_payload(data)
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
            run_seed=data.get("run_seed"),
        )


class RunRepository:
    """Repository managing memento serialization and storage operations."""

    def __init__(self, storage: StorageBackend) -> None:
        self.storage = storage
        self.last_load_error: str | None = None

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
        self.last_load_error = None
        raw = self.storage.get(SAVE_STORAGE_KEY)
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return RunMemento.from_dict(data)
        except (json.JSONDecodeError, SaveValidationError, TypeError, ValueError) as e:
            self.last_load_error = str(e)
            preserve_invalid = getattr(self.storage, "preserve_invalid", None)
            if callable(preserve_invalid):
                preserve_invalid(SAVE_STORAGE_KEY, raw)
            return None

    def delete(self) -> bool:
        """Remove saved memento from storage."""
        return self.storage.remove(SAVE_STORAGE_KEY)

    def exists(self) -> bool:
        """Check if a saved memento exists in storage."""
        return self.storage.exists(SAVE_STORAGE_KEY)
