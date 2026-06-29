"""
baseline_solver.py

Classical / greedy baseline for the Multi-Vehicle Routing Problem (VRP).
This is the "before" we compare Simulated Annealing against.

Approach:
    1. Precompute shortest-path travel time between every pair of relevant
       nodes (depot + customers) using Dijkstra. This gives us a fully
       connected "cost matrix" even though the underlying road network is
       sparse.
    2. Assign customers to vehicles using a simple greedy clustering: each
       vehicle is assigned the next-nearest unassigned customer to its
       current "load center", round-robin across vehicles. This balances
       work across the fleet without solving the much harder partitioning
       problem optimally.
    3. Within each vehicle's customer set, build a route using the
       Nearest-Neighbor heuristic (classic greedy TSP construction):
       always travel to the closest unvisited customer next, then return
       to depot.

This is intentionally simple and greedy -- the entire point of the project
is to show Simulated Annealing improving on it.
"""

import networkx as nx


def compute_cost_matrix(G, nodes):
    """
    Compute all-pairs shortest path travel time between the given nodes
    using Dijkstra, returning a dict-of-dicts cost matrix.

    Args:
        G: networkx.Graph with 'weight' edge attribute.
        nodes: list of node ids we need pairwise distances between
               (typically depot + all customers).

    Returns:
        cost[u][v] = shortest travel time from u to v.
        Unreachable pairs are set to float('inf').
    """
    cost = {u: {} for u in nodes}
    for u in nodes:
        try:
            lengths = nx.single_source_dijkstra_path_length(G, u, weight='weight')
        except nx.NetworkXError:
            lengths = {}
        for v in nodes:
            cost[u][v] = lengths.get(v, float('inf'))
    return cost


def nearest_neighbor_route(depot, customer_subset, cost_matrix):
    """
    Build a single vehicle's route using the Nearest-Neighbor heuristic:
    starting at the depot, repeatedly go to the closest unvisited
    customer, then return to depot at the end.

    Args:
        depot: depot node id.
        customer_subset: list of customer node ids assigned to this vehicle.
        cost_matrix: dict-of-dicts from compute_cost_matrix.

    Returns:
        route: list of node ids, e.g. [depot, c3, c1, c2, depot]
        total_cost: total travel time for this route.
    """
    if not customer_subset:
        return [depot, depot], 0.0

    unvisited = set(customer_subset)
    route = [depot]
    current = depot
    total_cost = 0.0

    while unvisited:
        next_stop = min(unvisited, key=lambda c: cost_matrix[current][c])
        step_cost = cost_matrix[current][next_stop]
        if step_cost == float('inf'):
            # Unreachable customer (can happen if traffic closures cut
            # off a region) -- skip it rather than crash the route.
            unvisited.remove(next_stop)
            continue
        total_cost += step_cost
        route.append(next_stop)
        current = next_stop
        unvisited.remove(next_stop)

    total_cost += cost_matrix[current][depot]
    route.append(depot)
    return route, total_cost


def solve_baseline_vrp(G, depot, customers, num_vehicles):
    """
    Solve the multi-vehicle VRP with the greedy baseline:
    round-robin assignment + nearest-neighbor routing per vehicle.

    Args:
        G: networkx.Graph (live or static -- caller decides).
        depot: depot node id.
        customers: list of customer node ids to visit.
        num_vehicles: number of vehicles available.

    Returns:
        solution: dict with:
            'routes': list of routes, one per vehicle (list of node ids)
            'route_costs': list of per-vehicle travel time
            'total_cost': sum of all route costs
    """
    relevant_nodes = [depot] + list(customers)
    cost_matrix = compute_cost_matrix(G, relevant_nodes)

    # Round-robin assignment: sort customers by distance from depot so
    # closer customers get assigned first (slightly better than pure
    # random round-robin, still a greedy/naive baseline)
    sorted_customers = sorted(customers, key=lambda c: cost_matrix[depot][c])
    vehicle_assignments = [[] for _ in range(num_vehicles)]
    for i, customer in enumerate(sorted_customers):
        vehicle_assignments[i % num_vehicles].append(customer)

    routes = []
    route_costs = []
    for assignment in vehicle_assignments:
        route, cost = nearest_neighbor_route(depot, assignment, cost_matrix)
        routes.append(route)
        route_costs.append(cost)

    return {
        'routes': routes,
        'route_costs': route_costs,
        'total_cost': sum(route_costs),
        'cost_matrix': cost_matrix,
    }


if __name__ == "__main__":
    from network_generator import generate_network

    G, depot, customers = generate_network(num_nodes=20, num_customers=8, seed=42)
    solution = solve_baseline_vrp(G, depot, customers, num_vehicles=3)

    print(f"Depot: {depot}, Customers: {customers}")
    for i, (route, cost) in enumerate(zip(solution['routes'], solution['route_costs'])):
        print(f"Vehicle {i+1}: route={route}, cost={cost:.2f}")
    print(f"Total cost: {solution['total_cost']:.2f}")
