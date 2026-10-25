import timeit
import random
from src.systems.map_gen import generate_spire_map

def run_benchmark():
    map_graph = generate_spire_map(num_floors=50, width_lanes=10, seed=42)

    # Run the get_available_nodes multiple times to simulate many frame updates
    def test_func():
        for _ in range(100000):
            _ = map_graph.available_nodes

    # Test initial state
    t1 = timeit.timeit(test_func, number=10)

    # Select a node to change state
    avail = map_graph.available_nodes
    if avail:
        map_graph.select_node(avail[0].id)

    t2 = timeit.timeit(test_func, number=10)

    print(f"Time before selection: {t1:.4f}s")
    print(f"Time after selection: {t2:.4f}s")

if __name__ == '__main__':
    run_benchmark()
