"""Spire-like reverse-tree node graph generator for dungeon exploration."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum


class NodeType(Enum):
    """Types of encounter nodes on the Spire map."""

    COMBAT = "Monster"
    ELITE = "Elite"
    REST = "Rest Site"
    SHOP = "Merchant"
    TREASURE = "Treasure"
    EVENT = "Unknown Event"
    BOSS = "Boss"


@dataclass
class MapNode:
    """A single decision node in the reverse-tree graph."""

    id: int
    floor: int
    lane: int  # Horizontal lane/column index
    node_type: NodeType
    outgoing_ids: list[int] = field(default_factory=list)
    incoming_ids: list[int] = field(default_factory=list)
    visited: bool = False
    available: bool = False


class MapGraph:
    """Directed acyclic graph representing floor-by-floor progression."""

    def __init__(self, floors: list[list[MapNode]]) -> None:
        self.floors: list[list[MapNode]] = floors
        self.nodes_by_id: dict[int, MapNode] = {}
        for floor_nodes in floors:
            for node in floor_nodes:
                self.nodes_by_id[node.id] = node

        self.current_node_id: int | None = None
        # Make starting floor nodes available
        if self.floors and self.floors[0]:
            for node in self.floors[0]:
                node.available = True

    @property
    def current_node(self) -> MapNode | None:
        """The currently occupied map node."""
        if self.current_node_id is not None:
            return self.nodes_by_id.get(self.current_node_id)
        return None

    def get_available_nodes(self) -> list[MapNode]:
        """Return nodes that can be chosen next."""
        if self.current_node_id is None:
            return [n for n in self.floors[0] if n.available]
        curr = self.nodes_by_id[self.current_node_id]
        return [self.nodes_by_id[nxt_id] for nxt_id in curr.outgoing_ids if self.nodes_by_id[nxt_id].available]

    def select_node(self, node_id: int) -> bool:
        """Move player to selected node if it is available."""
        target = self.nodes_by_id.get(node_id)
        if target is None or not target.available:
            return False

        # Mark all current floor nodes as unavailable
        current_floor_index = target.floor
        for node in self.floors[current_floor_index]:
            node.available = False

        target.visited = True
        self.current_node_id = target.id

        # Activate connected nodes on next floor
        for next_id in target.outgoing_ids:
            next_node = self.nodes_by_id.get(next_id)
            if next_node:
                next_node.available = True

        return True


def generate_spire_map(
    num_floors: int = 10,
    width_lanes: int = 4,
    seed: int | None = None,
) -> MapGraph:
    """Generate a convergent reverse-tree node graph resembling Slay the Spire."""
    rand = random.Random(seed)
    floors: list[list[MapNode]] = []
    node_counter = 0

    # 1. Generate nodes floor by floor
    for floor_idx in range(num_floors):
        floor_nodes: list[MapNode] = []

        # Final floor is always a single Boss node
        if floor_idx == num_floors - 1:
            boss_node = MapNode(
                id=node_counter,
                floor=floor_idx,
                lane=width_lanes // 2,
                node_type=NodeType.BOSS,
            )
            node_counter += 1
            floor_nodes.append(boss_node)
        elif floor_idx == 0:
            # First floor is starting combat encounters
            for lane in range(width_lanes):
                if rand.random() < 0.8:  # 80% chance for a lane to have a node
                    node = MapNode(
                        id=node_counter,
                        floor=floor_idx,
                        lane=lane,
                        node_type=NodeType.COMBAT,
                    )
                    node_counter += 1
                    floor_nodes.append(node)
            if not floor_nodes:  # Ensure at least one start node
                floor_nodes.append(
                    MapNode(id=node_counter, floor=floor_idx, lane=0, node_type=NodeType.COMBAT)
                )
                node_counter += 1
        elif floor_idx == num_floors // 2:
            # Mid-point treasure floor
            for lane in range(width_lanes):
                if rand.random() < 0.6:
                    node = MapNode(
                        id=node_counter,
                        floor=floor_idx,
                        lane=lane,
                        node_type=NodeType.TREASURE,
                    )
                    node_counter += 1
                    floor_nodes.append(node)
            if not floor_nodes:
                floor_nodes.append(
                    MapNode(id=node_counter, floor=floor_idx, lane=0, node_type=NodeType.TREASURE)
                )
                node_counter += 1
        else:
            # Intermediary floors with weighted node distribution
            weights = [
                (NodeType.COMBAT, 0.45),
                (NodeType.EVENT, 0.20),
                (NodeType.ELITE, 0.15),
                (NodeType.REST, 0.12),
                (NodeType.SHOP, 0.08),
            ]
            types, probs = zip(*weights)

            for lane in range(width_lanes):
                if rand.random() < 0.7:
                    chosen_type = rand.choices(types, weights=probs)[0]
                    node = MapNode(
                        id=node_counter,
                        floor=floor_idx,
                        lane=lane,
                        node_type=chosen_type,
                    )
                    node_counter += 1
                    floor_nodes.append(node)

            if not floor_nodes:
                floor_nodes.append(
                    MapNode(id=node_counter, floor=floor_idx, lane=0, node_type=NodeType.COMBAT)
                )
                node_counter += 1

        floors.append(floor_nodes)

    # 2. Connect floors with forward and reverse edges
    for floor_idx in range(num_floors - 1):
        current_floor = floors[floor_idx]
        next_floor = floors[floor_idx + 1]

        # Ensure every node on current floor connects to at least one next-floor node
        for curr_node in current_floor:
            # Find closest lanes in next floor
            candidates = sorted(next_floor, key=lambda n: abs(n.lane - curr_node.lane))
            # Connect to closest 1 or 2 candidates within reach (lane difference <= 1)
            connected = False
            for cand in candidates:
                if abs(cand.lane - curr_node.lane) <= 1 or len(next_floor) == 1:
                    curr_node.outgoing_ids.append(cand.id)
                    cand.incoming_ids.append(curr_node.id)
                    connected = True
                    if rand.random() < 0.3:  # Chance to connect multiple
                        continue
                    break
            if not connected:
                # Fallback: connect to absolute closest
                closest = candidates[0]
                curr_node.outgoing_ids.append(closest.id)
                closest.incoming_ids.append(curr_node.id)

        # Ensure every node on next floor has at least one incoming edge
        for next_node in next_floor:
            if not next_node.incoming_ids:
                closest_prev = min(current_floor, key=lambda n: abs(n.lane - next_node.lane))
                closest_prev.outgoing_ids.append(next_node.id)
                next_node.incoming_ids.append(closest_prev.id)

    return MapGraph(floors)
