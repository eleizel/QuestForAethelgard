"""Save and Load system for Quest for Aethelgard.

Provides:
- Unified Storage Adapter: Browser/Android PWA (window.localStorage) and Desktop (local JSON file)
- Robust serialization and deserialization for Player, Inventory, MapGraph, and GameState
- Versioned save schema with corruption resilience
- Save metadata helpers for UI badges and menu display
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Protocol

from src.core.game_state import GameMode, GameState
from src.entities.actor import Stats
from src.entities.item import EquipSlot, EquipmentItem
from src.entities.player import Player
from src.systems.inventory import Inventory, MAX_BELT_SLOTS
from src.systems.map_gen import MapGraph, MapNode, NodeType

SAVE_STORAGE_KEY = "quest_for_aethelgard_save"
CURRENT_SAVE_VERSION = 1


class StorageBackend(Protocol):
    """Protocol defining persistence storage operations."""

    def get(self, key: str) -> str | None:
        """Retrieve raw string data for key, or None if absent."""
        ...

    def set(self, key: str, value: str) -> bool:
        """Store raw string data for key. Returns True on success."""
        ...

    def remove(self, key: str) -> bool:
        """Remove key from storage. Returns True if removed."""
        ...

    def exists(self, key: str) -> bool:
        """Check if key exists and contains non-empty data."""
        ...


class LocalStorageBackend:
    """Browser / Android PWA storage utilizing JavaScript window.localStorage."""

    def __init__(self, window: Any) -> None:
        self.window = window

    def get(self, key: str) -> str | None:
        try:
            val = self.window.localStorage.getItem(key)
            if val is None or val == "" or str(val) in ("null", "undefined"):
                return None
            return str(val)
        except Exception as e:
            print(f"LocalStorage read error for {key}: {e}")
            return None

    def set(self, key: str, value: str) -> bool:
        try:
            self.window.localStorage.setItem(key, value)
            return True
        except Exception as e:
            print(f"LocalStorage write error for {key}: {e}")
            return False

    def remove(self, key: str) -> bool:
        try:
            self.window.localStorage.removeItem(key)
            return True
        except Exception as e:
            print(f"LocalStorage remove error for {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        try:
            val = self.window.localStorage.getItem(key)
            return val is not None and str(val) not in ("null", "undefined", "")
        except Exception:
            return False


class FileStorageBackend:
    """Desktop Python fallback storage utilizing atomic JSON files on disk."""

    def __init__(self, save_dir: str = "saves") -> None:
        self.save_dir = save_dir

    def _get_path(self, key: str) -> str:
        return os.path.join(self.save_dir, f"{key}.json")

    def get(self, key: str) -> str | None:
        path = self._get_path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"FileStorage read error for {path}: {e}")
            return None

    def set(self, key: str, value: str) -> bool:
        try:
            os.makedirs(self.save_dir, exist_ok=True)
            path = self._get_path(key)
            temp_path = f"{path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(value)
            os.replace(temp_path, path)
            return True
        except Exception as e:
            print(f"FileStorage write error for {path}: {e}")
            return False

    def remove(self, key: str) -> bool:
        path = self._get_path(key)
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except Exception as e:
                print(f"FileStorage remove error for {path}: {e}")
                return False
        return False

    def exists(self, key: str) -> bool:
        return os.path.exists(self._get_path(key))


def detect_storage_backend() -> StorageBackend:
    """Select LocalStorageBackend if running in Pyxel WASM, else FileStorageBackend."""
    try:
        import js  # type: ignore
        if hasattr(js, "window") and hasattr(js.window, "localStorage"):
            return LocalStorageBackend(js.window)
    except (ImportError, AttributeError):
        pass
    return FileStorageBackend()


# =============================================================================
# SERIALIZATION HELPERS
# =============================================================================

def serialize_stats(stats: Stats) -> dict[str, Any]:
    return {
        "max_hp": stats.max_hp,
        "attack": stats.attack,
        "defense": stats.defense,
        "speed": stats.speed,
        "crit_chance": stats.crit_chance,
    }


def deserialize_stats(data: dict[str, Any]) -> Stats:
    return Stats(
        max_hp=int(data.get("max_hp", 0)),
        attack=int(data.get("attack", 0)),
        defense=int(data.get("defense", 0)),
        speed=int(data.get("speed", 0)),
        crit_chance=float(data.get("crit_chance", 0.05)),
    )


def serialize_inventory(inv: Inventory) -> dict[str, Any]:
    equip_data: dict[str, str] = {}
    for slot, item in inv.equipment.items():
        if item is not None:
            equip_data[slot.value] = item.id

    pouch_data = [item.id for item in inv.pouch if item is not None]
    belt_data = [item.id if item is not None else None for item in inv.belt]

    return {
        "equipment": equip_data,
        "pouch": pouch_data,
        "belt": belt_data,
    }


def deserialize_inventory(data: dict[str, Any]) -> Inventory:
    from src.data.items import get_item

    inv = Inventory()
    equipment_data = data.get("equipment", {})
    for slot_str, item_id in equipment_data.items():
        if item_id:
            item = get_item(item_id)
            if isinstance(item, EquipmentItem):
                try:
                    slot = EquipSlot(slot_str)
                    inv.equipment[slot] = item
                except ValueError:
                    pass

    for item_id in data.get("pouch", []):
        if item_id:
            item = get_item(item_id)
            if item:
                inv.add_to_pouch(item)

    raw_belt = data.get("belt", [None] * MAX_BELT_SLOTS)
    inv.belt = [get_item(item_id) if item_id else None for item_id in raw_belt]
    while len(inv.belt) < MAX_BELT_SLOTS:
        inv.belt.append(None)
    inv.belt = inv.belt[:MAX_BELT_SLOTS]

    inv._cached_stats = None
    return inv


def serialize_player(player: Player) -> dict[str, Any]:
    return {
        "name": player.name,
        "class_id": player.class_id,
        "level": player.level,
        "experience": player.experience,
        "exp_to_next_level": player.exp_to_next_level,
        "gold": player.gold,
        "stat_points": player.stat_points,
        "current_hp": player.current_hp,
        "exp_multiplier": player.exp_multiplier,
        "promotion_due": player.promotion_due,
        "pending_ability_choices": list(player.pending_ability_choices),
        "active_stances": list(player._active_stances),
        "signature_passive": player.signature_passive.id if player.signature_passive else None,
        "active_abilities": [a.id for a in player.abilities.active],
        "passive_abilities": [a.id for a in player.abilities.passive],
        "base_stats": serialize_stats(player.base_stats),
        "inventory": serialize_inventory(player.inventory),
    }


def deserialize_player(data: dict[str, Any]) -> Player:
    from src.data.abilities import get_ability_by_id

    player = Player(
        name=data.get("name", "Sir Aethelgard"),
        class_id=data.get("class_id", "warrior"),
    )
    player.level = int(data.get("level", 1))
    player.experience = int(data.get("experience", 0))
    player.exp_to_next_level = int(data.get("exp_to_next_level", 50))
    player.gold = int(data.get("gold", 0))
    player.stat_points = int(data.get("stat_points", 0))
    player.exp_multiplier = float(data.get("exp_multiplier", 1.0))
    player.promotion_due = bool(data.get("promotion_due", False))
    player.pending_ability_choices = list(data.get("pending_ability_choices", []))
    player._active_stances = set(data.get("active_stances", []))

    if "base_stats" in data:
        player.base_stats = deserialize_stats(data["base_stats"])

    sig_id = data.get("signature_passive")
    player.signature_passive = get_ability_by_id(sig_id) if sig_id else None

    # Restore equipped abilities
    player.abilities.active.clear()
    for ab_id in data.get("active_abilities", []):
        ab = get_ability_by_id(ab_id)
        if ab:
            player.abilities.active.append(ab)

    player.abilities.passive.clear()
    for ab_id in data.get("passive_abilities", []):
        ab = get_ability_by_id(ab_id)
        if ab:
            player.abilities.passive.append(ab)
    player.abilities._update_cached_flags()

    # Restore inventory gear and consumables
    if "inventory" in data:
        player.inventory = deserialize_inventory(data["inventory"])

    # Restore HP accurately now that equipment stats are computed
    saved_hp = data.get("current_hp")
    if saved_hp is not None:
        player.current_hp = max(1, min(player.max_hp, int(saved_hp)))

    return player


def serialize_map_node(node: MapNode) -> dict[str, Any]:
    return {
        "id": node.id,
        "floor": node.floor,
        "lane": node.lane,
        "node_type": node.node_type.name,
        "outgoing_ids": list(node.outgoing_ids),
        "incoming_ids": list(node.incoming_ids),
        "visited": node.visited,
        "available": node.available,
    }


def deserialize_map_node(data: dict[str, Any]) -> MapNode:
    return MapNode(
        id=int(data["id"]),
        floor=int(data["floor"]),
        lane=int(data["lane"]),
        node_type=NodeType[data["node_type"]],
        outgoing_ids=list(data.get("outgoing_ids", [])),
        incoming_ids=list(data.get("incoming_ids", [])),
        visited=bool(data.get("visited", False)),
        available=bool(data.get("available", False)),
    )


def serialize_map_graph(graph: MapGraph) -> dict[str, Any]:
    return {
        "floors": [[serialize_map_node(node) for node in floor] for floor in graph.floors],
        "current_node_id": graph.current_node_id,
    }


def deserialize_map_graph(data: dict[str, Any]) -> MapGraph:
    raw_floors = data.get("floors", [])
    floors = [[deserialize_map_node(n) for n in floor_data] for floor_data in raw_floors]
    graph = MapGraph(floors)

    # Re-apply explicit saved visited/available states to override MapGraph.__init__ defaults
    for f_idx, floor_data in enumerate(raw_floors):
        for n_idx, n_data in enumerate(floor_data):
            node = graph.floors[f_idx][n_idx]
            node.available = bool(n_data.get("available", False))
            node.visited = bool(n_data.get("visited", False))

    graph.current_node_id = data.get("current_node_id")
    graph._available_nodes = [node for floor in graph.floors for node in floor if node.available]
    return graph


def serialize_game_state(game_state: GameState) -> dict[str, Any]:
    # Saving always safely restores to MAP mode or current active progression view
    mode = game_state.current_mode
    if mode in (GameMode.WELCOME, GameMode.GAME_OVER, GameMode.VICTORY, GameMode.CLASS_SELECT):
        mode = GameMode.MAP

    return {
        "save_version": CURRENT_SAVE_VERSION,
        "floor": game_state.floor,
        "act": game_state.act,
        "biome_route_mode": game_state.biome_route_mode,
        "current_biome": game_state.current_biome,
        "current_mode": mode.name,
        "previous_mode": game_state.previous_mode.name,
        "player": serialize_player(game_state.player),
        "map_graph": serialize_map_graph(game_state.map_graph) if game_state.map_graph else None,
    }


def restore_game_state(game_state: GameState, data: dict[str, Any]) -> bool:
    try:
        game_state.floor = int(data.get("floor", 1))
        game_state.act = int(data.get("act", 1))
        game_state.biome_route_mode = str(data.get("biome_route_mode", "FATE"))
        game_state.current_biome = str(data.get("current_biome", "arboretum"))
        game_state.combat = None
        game_state.pending_loot = []
        game_state.merchant_stock = []
        game_state.overlay_return_modes.clear()
        game_state.promotion_return_mode = None

        if "player" in data:
            game_state.player = deserialize_player(data["player"])

        if data.get("map_graph"):
            game_state.map_graph = deserialize_map_graph(data["map_graph"])

        # Determine target mode to resume safely
        saved_mode_str = data.get("current_mode", "MAP")
        try:
            target_mode = GameMode[saved_mode_str]
            if target_mode in (GameMode.WELCOME, GameMode.GAME_OVER, GameMode.VICTORY, GameMode.CLASS_SELECT):
                target_mode = GameMode.MAP
        except KeyError:
            target_mode = GameMode.MAP

        game_state.switch_mode(target_mode)
        return True
    except Exception as e:
        print(f"Failed to restore game state: {e}")
        return False


# =============================================================================
# SAVE MANAGER SERVICE
# =============================================================================

class SaveManager:
    """Coordinates game state saving, loading, metadata extraction, and storage."""

    def __init__(self, storage: StorageBackend | None = None) -> None:
        self.storage: StorageBackend = storage if storage is not None else detect_storage_backend()

    def set_storage(self, storage: StorageBackend) -> None:
        """Allow switching the storage backend (e.g. for testing)."""
        self.storage = storage

    def has_save(self) -> bool:
        """Return True if an existing, valid save game is available."""
        return self.storage.exists(SAVE_STORAGE_KEY)

    def get_save_data(self) -> dict[str, Any] | None:
        """Retrieve and parse JSON save state dictionary, or None if invalid."""
        raw = self.storage.get(SAVE_STORAGE_KEY)
        if not raw:
            return None
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "player" in data:
                return data
            return None
        except Exception as e:
            print(f"Error parsing save JSON: {e}")
            return None

    def get_save_summary(self) -> dict[str, Any] | None:
        """Extract quick run overview for UI banners without reconstructing full entities."""
        data = self.get_save_data()
        if not data or "player" not in data:
            return None
        player_info = data["player"]
        return {
            "name": player_info.get("name", "Sir Aethelgard"),
            "class_id": player_info.get("class_id", "warrior"),
            "level": player_info.get("level", 1),
            "act": data.get("act", 1),
            "floor": data.get("floor", 1),
            "current_biome": data.get("current_biome", "arboretum"),
        }

    def save_game(self, game_state: GameState) -> bool:
        """Serialize and persist the given GameState."""
        try:
            payload = serialize_game_state(game_state)
            json_str = json.dumps(payload, separators=(",", ":"))
            return self.storage.set(SAVE_STORAGE_KEY, json_str)
        except Exception as e:
            print(f"Failed to save game: {e}")
            return False

    def load_game(self, game_state: GameState) -> bool:
        """Load saved data and restore it into the provided GameState container."""
        data = self.get_save_data()
        if not data:
            return False
        return restore_game_state(game_state, data)

    def delete_save(self) -> bool:
        """Delete active save game (e.g. on Game Over or Victory)."""
        return self.storage.remove(SAVE_STORAGE_KEY)


# Global singleton instance
save_manager = SaveManager()
