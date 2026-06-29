"""
network_generator.py

Generates synthetic transportation networks for the Dynamic VRP project.

A network is represented as a NetworkX Graph where:
    - Nodes  = intersections / locations (with 2D coordinates for visualization)
    - Edges  = roads, weighted by base travel time (minutes)
    - One node is designated the 'depot' (vehicle start/end point)
    - A subset of nodes are designated 'customers' (must be visited)

We build networks with a grid backbone (so they look like real road networks)
plus random extra edges (shortcuts / diagonal roads), which avoids generating
a totally random graph that wouldn't resemble a real city layout.
"""

import random
import math
import networkx as nx


def generate_network(num_nodes: int, num_customers: int, seed: int = None,
                      grid_jitter: float = 0.4, extra_edge_prob: float = 0.15):
    """
    Generate a single synthetic transportation network.

    Args:
        num_nodes: total number of intersections/nodes in the network.
        num_customers: number of nodes (excluding depot) that must be visited.
        seed: RNG seed for reproducibility.
        grid_jitter: how much to randomly offset nodes from a perfect grid
                     (0 = perfect grid, higher = more irregular layout).
        extra_edge_prob: probability of adding a random "shortcut" edge
                         between two nearby non-adjacent grid nodes.

    Returns:
        G: networkx.Graph with node attribute 'pos' (x, y) and
           edge attribute 'weight' (base travel time in minutes).
        depot: node id of the depot (route start/end).
        customers: list of node ids that must be visited.
    """
    if seed is not None:
        random.seed(seed)

    G = nx.Graph()

    # Build a roughly square grid large enough to hold num_nodes
    side = math.ceil(math.sqrt(num_nodes))
    node_id = 0
    coords = {}

    for r in range(side):
        for c in range(side):
            if node_id >= num_nodes:
                break
            jitter_x = random.uniform(-grid_jitter, grid_jitter)
            jitter_y = random.uniform(-grid_jitter, grid_jitter)
            x, y = c + jitter_x, r + jitter_y
            coords[node_id] = (x, y)
            G.add_node(node_id, pos=(x, y))
            node_id += 1

    # Connect grid neighbors (right and down) to form the road backbone
    def node_at(rr, cc):
        idx = rr * side + cc
        return idx if idx < num_nodes else None

    for r in range(side):
        for c in range(side):
            n1 = node_at(r, c)
            if n1 is None:
                continue
            for (dr, dc) in [(0, 1), (1, 0)]:
                n2 = node_at(r + dr, c + dc)
                if n2 is not None:
                    w = _euclidean_weight(coords[n1], coords[n2])
                    G.add_edge(n1, n2, weight=w)

    # Ensure the graph is connected (in case grid construction left gaps
    # for the last partial row, which can happen when num_nodes isn't a
    # perfect square)
    if not nx.is_connected(G):
        components = list(nx.connected_components(G))
        for i in range(1, len(components)):
            n1 = random.choice(list(components[0]))
            n2 = random.choice(list(components[i]))
            w = _euclidean_weight(coords[n1], coords[n2])
            G.add_edge(n1, n2, weight=w)

    # Add random shortcut edges between nearby nodes that aren't already
    # connected, to mimic diagonal roads / highways cutting across the grid
    all_nodes = list(G.nodes())
    for n1 in all_nodes:
        for n2 in all_nodes:
            if n1 >= n2 or G.has_edge(n1, n2):
                continue
            dist = _euclidean_weight(coords[n1], coords[n2])
            if dist < 1.6 and random.random() < extra_edge_prob:
                G.add_edge(n1, n2, weight=dist)

    # Pick depot (closest to the centroid, like a central warehouse) and
    # customers (random sample of remaining nodes)
    centroid = (sum(x for x, y in coords.values()) / num_nodes,
                sum(y for x, y in coords.values()) / num_nodes)
    depot = min(all_nodes, key=lambda n: _euclidean_weight(coords[n], centroid))

    remaining = [n for n in all_nodes if n != depot]
    num_customers = min(num_customers, len(remaining))
    customers = random.sample(remaining, num_customers)

    return G, depot, customers


def _euclidean_weight(p1, p2):
    """Euclidean distance between two (x, y) points, used as edge weight."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def generate_test_suite(num_scenarios: int = 50, seed_offset: int = 1000):
    """
    Generate a batch of test network scenarios with varying size, used for
    the benchmark (this is where the "50 diverse test network scenarios"
    in the project description comes from).

    Network size and customer count are randomized per scenario, within
    realistic small/medium/large city tiers, so the benchmark covers a
    range of problem difficulties rather than one fixed size.

    Returns:
        List of dicts: {'id', 'num_nodes', 'num_customers', 'num_vehicles',
                         'graph', 'depot', 'customers'}
    """
    scenarios = []
    size_tiers = [
        (20, 6),    # small network, few customers
        (50, 12),   # medium network
        (100, 20),  # large network
    ]

    for i in range(num_scenarios):
        seed = seed_offset + i
        random.seed(seed)
        num_nodes, max_customers = random.choice(size_tiers)
        num_customers = random.randint(max(4, max_customers // 2), max_customers)
        num_vehicles = random.randint(2, 4)

        G, depot, customers = generate_network(
            num_nodes=num_nodes,
            num_customers=num_customers,
            seed=seed
        )

        scenarios.append({
            'id': i,
            'num_nodes': num_nodes,
            'num_customers': num_customers,
            'num_vehicles': num_vehicles,
            'graph': G,
            'depot': depot,
            'customers': customers,
        })

    return scenarios


if __name__ == "__main__":
    # Quick smoke test when running this file directly
    G, depot, customers = generate_network(num_nodes=20, num_customers=6, seed=42)
    print(f"Generated network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"Depot: {depot}")
    print(f"Customers: {customers}")
