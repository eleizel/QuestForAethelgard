"""Unit tests for Phase 5: Memento & Repository Pattern for persistence."""

import json

import pytest
from src.core.game_state import GameState, GameMode
from src.core.persistence import (
    SAVE_STORAGE_KEY,
    MemoryStorageBackend,
    RunMemento,
    RunRepository,
    migrate_save_payload,
)
from src.core.save_manager import create_run_memento, restore_from_memento
from src.entities.player import Player


def test_memory_storage_backend():
    """MemoryStorageBackend provides fast in-memory key-value persistence without touching disk."""
    storage = MemoryStorageBackend()
    assert storage.exists("test_key") is False
    assert storage.get("test_key") is None

    assert storage.set("test_key", "sample_payload") is True
    assert storage.exists("test_key") is True
    assert storage.get("test_key") == "sample_payload"

    assert storage.remove("test_key") is True
    assert storage.exists("test_key") is False
    assert storage.get("test_key") is None


def test_run_memento_immutability_and_roundtrip():
    """RunMemento accurately snapshots game session primitives and survives roundtrip conversion."""
    memento = RunMemento(
        save_version=1,
        floor=5,
        act=2,
        biome_route_mode="PATHFINDER",
        current_biome="crypt",
        current_mode_name="MAP",
        previous_mode_name="LOOT",
        player_data={"name": "Aethelgard", "level": 10, "class_id": "paladin"},
        map_data={"current_node_id": 42},
        run_seed=1234,
    )

    data = memento.to_dict()
    assert data["floor"] == 5
    assert data["act"] == 2
    assert data["player"]["class_id"] == "paladin"
    assert data["run_seed"] == 1234

    restored = RunMemento.from_dict(data)
    assert restored.floor == memento.floor
    assert restored.act == memento.act
    assert restored.current_biome == memento.current_biome
    assert restored.player_data == memento.player_data
    assert restored.run_seed == 1234


def test_run_repository_lifecycle():
    """RunRepository stores, loads, and deletes RunMemento instances using pluggable backends."""
    storage = MemoryStorageBackend()
    repo = RunRepository(storage=storage)

    assert repo.exists() is False
    assert repo.load() is None

    memento = RunMemento(
        save_version=1,
        floor=3,
        act=1,
        biome_route_mode="FATE",
        current_biome="arboretum",
        current_mode_name="MAP",
        previous_mode_name="COMBAT",
        player_data={"name": "TestHero", "level": 3, "class_id": "warrior"},
        map_data=None,
    )

    saved = repo.save(memento)
    assert saved is True
    assert repo.exists() is True

    loaded = repo.load()
    assert loaded is not None
    assert loaded.floor == 3
    assert loaded.player_data["name"] == "TestHero"

    deleted = repo.delete()
    assert deleted is True
    assert repo.exists() is False
    assert repo.load() is None


@pytest.mark.parametrize(
    "payload",
    [
        {"save_version": 2, "player": {}},
        {"save_version": 1, "player": []},
        {"save_version": 1, "player": {}, "floor": 0},
        {"save_version": 1, "player": {}, "map_graph": []},
    ],
)
def test_repository_rejects_invalid_or_newer_save_payloads(payload):
    """Invalid data and unsupported future schemas never reach restoration."""
    storage = MemoryStorageBackend()
    storage.set(SAVE_STORAGE_KEY, json.dumps(payload))

    assert RunRepository(storage).load() is None


def test_unversioned_save_payload_migrates_to_current_schema():
    """Pre-versioned payloads retain the compatibility behavior of version 1."""
    payload = migrate_save_payload({"player": {"name": "Aethelgard"}})

    assert payload["save_version"] == 1
    assert payload["floor"] == 1
    assert payload["act"] == 1


def test_create_memento_and_restore_gamestate():
    """GameState can create a RunMemento and be cleanly restored from one."""
    state = GameState()
    state.start_new_game(class_id="rogue")
    state.floor = 4
    state.act = 1
    state.player.gold = 120

    memento = create_run_memento(state)
    assert memento.floor == 4
    assert memento.player_data["class_id"] == "rogue"
    assert memento.player_data["gold"] == 120

    # Mutate live state
    state.floor = 99
    state.player.gold = 0

    # Restore from memento
    success = restore_from_memento(state, memento)
    assert success is True
    assert state.floor == 4
    assert state.player.gold == 120
    assert state.player.class_id == "rogue"
