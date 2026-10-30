import json
import pytest

from src.core.game_state import GameMode, GameState
from src.core.save_manager import (
    FileStorageBackend,
    LocalStorageBackend,
    SaveManager,
    deserialize_inventory,
    deserialize_map_graph,
    deserialize_player,
    deserialize_stats,
    restore_game_state,
    serialize_inventory,
    serialize_map_graph,
    serialize_player,
    serialize_stats,
)
from src.data.items import get_item
from src.entities.actor import Stats
from src.entities.item import EquipSlot
from src.entities.player import Player
from src.systems.inventory import Inventory
from src.systems.map_gen import generate_spire_map


class MockWindow:
    """Mock JS window object with localStorage for testing LocalStorageBackend."""

    def __init__(self) -> None:
        self.storage: dict[str, str] = {}
        self.localStorage = self

    def getItem(self, key: str) -> str | None:
        return self.storage.get(key)

    def setItem(self, key: str, value: str) -> None:
        self.storage[key] = str(value)

    def removeItem(self, key: str) -> None:
        self.storage.pop(key, None)


def test_stats_serialization_roundtrip():
    original = Stats(max_hp=120, attack=25, defense=14, speed=11, crit_chance=0.15)
    data = serialize_stats(original)
    restored = deserialize_stats(data)

    assert restored.max_hp == original.max_hp
    assert restored.attack == original.attack
    assert restored.defense == original.defense
    assert restored.speed == original.speed
    assert abs(restored.crit_chance - original.crit_chance) < 1e-4


def test_inventory_serialization_roundtrip():
    inv = Inventory()
    weapon = get_item("iron_broadsword")
    shield = get_item("iron_tower_shield")
    potion = get_item("health_potion")

    assert weapon is not None
    assert shield is not None
    assert potion is not None

    inv.equip(weapon)
    inv.equip(shield)
    inv.add_to_pouch(potion)
    inv.belt[0] = potion

    data = serialize_inventory(inv)
    restored = deserialize_inventory(data)

    assert restored.equipment[EquipSlot.MAIN_HAND] is not None
    assert restored.equipment[EquipSlot.MAIN_HAND].id == "iron_broadsword"
    assert restored.equipment[EquipSlot.OFF_HAND] is not None
    assert restored.equipment[EquipSlot.OFF_HAND].id == "iron_tower_shield"
    assert len(restored.pouch) == 1
    assert restored.pouch[0].id == "health_potion"
    assert restored.belt[0] is not None
    assert restored.belt[0].id == "health_potion"
    assert restored.belt[1] is None


def test_player_serialization_roundtrip():
    player = Player(name="Sir Testalot", class_id="warrior")
    player.level = 5
    player.experience = 120
    player.gold = 350
    player.stat_points = 4
    player.current_hp = 42

    data = serialize_player(player)
    restored = deserialize_player(data)

    assert restored.name == "Sir Testalot"
    assert restored.class_id == "warrior"
    assert restored.level == 5
    assert restored.experience == 120
    assert restored.gold == 350
    assert restored.stat_points == 4
    assert restored.current_hp == 42
    assert len(restored.abilities.active) > 0


def test_map_graph_serialization_roundtrip():
    graph = generate_spire_map(num_floors=6, width_lanes=3, seed=42)
    # Select first floor node
    first_node = graph.available_nodes[0]
    graph.select_node(first_node.id)

    data = serialize_map_graph(graph)
    restored = deserialize_map_graph(data)

    assert len(restored.floors) == len(graph.floors)
    assert restored.current_node_id == first_node.id
    assert restored.current_node.id == first_node.id
    assert restored.current_node.visited is True
    # The next floor outgoing nodes should be available
    assert len(restored.available_nodes) == len(graph.available_nodes)
    for orig_node, rest_node in zip(graph.available_nodes, restored.available_nodes):
        assert orig_node.id == rest_node.id
        assert rest_node.available is True


def test_local_storage_backend():
    mock_window = MockWindow()
    backend = LocalStorageBackend(mock_window)

    assert not backend.exists("test_key")
    assert backend.get("test_key") is None

    backend.set("test_key", "sample_payload")
    assert backend.exists("test_key")
    assert backend.get("test_key") == "sample_payload"

    backend.remove("test_key")
    assert not backend.exists("test_key")
    assert backend.get("test_key") is None


def test_file_storage_backend(tmp_path):
    backend = FileStorageBackend(save_dir=str(tmp_path))

    assert not backend.exists("test_file")
    assert backend.get("test_file") is None

    backend.set("test_file", '{"foo": "bar"}')
    assert backend.exists("test_file")
    assert backend.get("test_file") == '{"foo": "bar"}'

    backend.remove("test_file")
    assert not backend.exists("test_file")


def test_save_and_load_full_run(tmp_path):
    backend = FileStorageBackend(save_dir=str(tmp_path))
    sm = SaveManager(storage=backend)

    # Setup game state
    state = GameState()
    state.start_new_game(class_id="rogue", route_mode="FATE")
    state.player.gold = 77
    state.player.current_hp = 30
    first_node = state.map_graph.available_nodes[0]
    state.map_graph.select_node(first_node.id)

    # Save
    assert sm.save_game(state) is True
    assert sm.has_save() is True

    # Check summary
    summary = sm.get_save_summary()
    assert summary is not None
    assert summary["class_id"] == "rogue"
    assert summary["act"] == 1

    # Load into a fresh GameState
    new_state = GameState()
    assert sm.load_game(new_state) is True

    assert new_state.player.class_id == "rogue"
    assert new_state.player.gold == 77
    assert new_state.player.current_hp == 30
    assert new_state.map_graph is not None
    assert new_state.map_graph.current_node_id == first_node.id
    assert new_state.current_mode == GameMode.MAP

    # Delete save
    assert sm.delete_save() is True
    assert sm.has_save() is False
    assert sm.load_game(new_state) is False


def test_corrupted_save_handling(tmp_path):
    backend = FileStorageBackend(save_dir=str(tmp_path))
    sm = SaveManager(storage=backend)

    # Put corrupted garbage
    backend.set("quest_for_aethelgard_save", "{invalid_json: 42")
    assert sm.has_save() is True
    assert sm.get_save_data() is None
    assert sm.get_save_summary() is None

    dummy_state = GameState()
    assert sm.load_game(dummy_state) is False


def test_player_promoted_save_roundtrip():
    player = Player(name="Promoted Hero", class_id="warrior")
    player.level = 10
    assert player.promote("paladin") is True
    assert player.signature_passive is not None
    assert player.class_id == "paladin"

    data = serialize_player(player)
    restored = deserialize_player(data)

    assert restored.class_id == "paladin"
    assert restored.signature_passive is not None
    assert restored.signature_passive.id == player.signature_passive.id
    assert "EPIC" in restored.pending_ability_choices


def test_full_game_lifecycle_auto_save_and_death(tmp_path):
    from src.core.save_manager import save_manager
    backend = FileStorageBackend(save_dir=str(tmp_path))
    save_manager.set_storage(backend)

    # 1. Start a new game - auto-save triggers on map entry
    state = GameState()
    assert not save_manager.has_save()
    state.start_new_game(class_id="mage", route_mode="FATE")
    assert save_manager.has_save()

    # 2. Inspect summary
    summary = save_manager.get_save_summary()
    assert summary is not None
    assert summary["class_id"] == "mage"
    assert summary["act"] == 1
    assert summary["floor"] == 1

    # 3. Simulate progression & changes
    state.player.gold += 150
    state.player.gain_experience(80)
    save_manager.save_game(state)

    # 4. Load into a brand-new GameState
    fresh_state = GameState()
    assert save_manager.load_game(fresh_state) is True
    assert fresh_state.player.class_id == "mage"
    assert fresh_state.player.gold == state.player.gold
    assert fresh_state.player.experience == state.player.experience
    assert fresh_state.map_graph is not None
    assert fresh_state.current_mode == GameMode.MAP

    # 5. Simulate player defeat in combat
    from src.systems.combat import CombatResult, CombatSystem
    from src.entities.enemy import EnemyTier, generate_enemy

    enemy = generate_enemy(EnemyTier.COMMON, floor=1, biome_id="arboretum", player_speed=10)
    state.combat = CombatSystem(state.player, enemy)
    state.combat.result = CombatResult.PLAYER_DEFEAT
    state.combat.completion_delay_ticks = 0
    state.update_combat()

    # Save should be deleted on defeat (permadeath)
    assert not save_manager.has_save()


