"""Deterministic invariants for procedural spire generation."""

import pytest

from src.systems.map_gen import NodeType, generate_spire_map


@pytest.mark.parametrize("seed", range(100))
def test_generated_spire_has_a_playable_route_to_its_boss(seed):
    """Following available nodes from any seed must always reach the final boss."""
    graph = generate_spire_map(num_floors=12, width_lanes=4, seed=seed)

    assert len(graph.floors) == 12
    assert all(floor for floor in graph.floors)
    assert graph.floors[-1][0].node_type is NodeType.BOSS
    assert len(graph.floors[-1]) == 1

    for floor_index, floor in enumerate(graph.floors[:-1]):
        for node in floor:
            assert node.outgoing_ids, f"seed={seed}, floor={floor_index}, node={node.id}"
            for target_id in node.outgoing_ids:
                target = graph.nodes_by_id[target_id]
                assert target.floor == floor_index + 1
                assert node.id in target.incoming_ids

    while graph.available_nodes:
        assert graph.select_node(graph.available_nodes[0].id)

    assert graph.current_node is graph.floors[-1][0]


@pytest.mark.parametrize("seed", [0, 1, 42, 99])
def test_same_seed_generates_the_same_spire(seed):
    """Seeded map generation is stable for reproducible runs and bug reports."""
    first = generate_spire_map(num_floors=12, width_lanes=4, seed=seed)
    second = generate_spire_map(num_floors=12, width_lanes=4, seed=seed)

    def snapshot(graph):
        return [
            [
                (node.id, node.lane, node.node_type, tuple(node.outgoing_ids))
                for node in floor
            ]
            for floor in graph.floors
        ]

    assert snapshot(first) == snapshot(second)
