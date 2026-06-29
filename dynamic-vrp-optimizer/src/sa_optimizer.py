"""
sa_optimizer.py

Simulated Annealing (SA) optimizer for the Multi-Vehicle Routing Problem.

WHY SIMULATED ANNEALING:
The multi-vehicle VRP is NP-hard -- there's no known polynomial-time exact
algorithm. The baseline (nearest-neighbor + round-robin) is fast but greedy:
it commits to decisions early and never revisits them, so it gets stuck in
locally bad solutions. SA fixes this by:
    - Starting from a candidate solution (we seed it with the baseline).
    - Repeatedly proposing small random changes ("neighbors") to the
      current solution.
    - Accepting improvements always, and accepting WORSE solutions with a
      probability that decreases over time (the "temperature" schedule).
      This lets SA escape local minima early on (high temperature = more
      willing to accept a worse move) while converging to a strong
      solution as temperature drops (low temperature = behaves greedily).

SOLUTION REPRESENTATION:
A solution is a list of routes, one per vehicle, where each route is a
list of customer node ids (depot is implicit at the start/end and not
stored in this internal representation -- it's added back when computing
cost or exporting the route).

NEIGHBOR MOVES (the "small random changes"):
    1. Intra-route swap: swap two customers within the same vehicle's route.
    2. Inter-route swap: swap one customer from vehicle A with one from
       vehicle B.
    3. Relocate: move one customer from one vehicle's route to another
       vehicle's route (at a random position).
    4. Intra-route reversal: reverse a sub-segment of one route (a classic
       2-opt style move that fixes "crossed path" inefficiencies).
"""

import math
import random
import copy


class VRPState:
    """
    Lightweight container for a candidate multi-vehicle solution.
    routes: list of lists, routes[i] = ordered list of customer ids
            assigned to vehicle i (depot excluded -- added back at eval time).
    """

    def __init__(self, routes):
        self.routes = routes

    def copy(self):
        return VRPState([list(r) for r in self.routes])


def evaluate_solution(state: VRPState, depot, cost_matrix):
    """
    Compute total travel cost of a candidate solution: for each vehicle,
    depot -> route stops in order -> back to depot, summed across vehicles.

    Unreachable legs (cost == inf, e.g. due to a traffic closure cutting
    off a node) are penalized heavily rather than crashing, so SA can
    still compare solutions and steer away from infeasible ones.
    """
    INF_PENALTY = 1e6
    total = 0.0
    for route in state.routes:
        if not route:
            continue
        current = depot
        for stop in route:
            leg_cost = cost_matrix[current][stop]
            total += leg_cost if leg_cost != float('inf') else INF_PENALTY
            current = stop
        leg_cost = cost_matrix[current][depot]
        total += leg_cost if leg_cost != float('inf') else INF_PENALTY
    return total


def _random_neighbor(state: VRPState):
    """
    Produce a neighboring solution by applying one random move.
    Returns a NEW VRPState (the input state is left untouched).
    """
    new_state = state.copy()
    num_vehicles = len(new_state.routes)
    move = random.choice(['intra_swap', 'inter_swap', 'relocate', 'reverse_segment'])

    non_empty = [i for i in range(num_vehicles) if len(new_state.routes[i]) > 0]
    if not non_empty:
        return new_state  # nothing to move

    if move == 'intra_swap':
        v = random.choice(non_empty)
        route = new_state.routes[v]
        if len(route) >= 2:
            i, j = random.sample(range(len(route)), 2)
            route[i], route[j] = route[j], route[i]

    elif move == 'inter_swap':
        candidates = [i for i in non_empty]
        if len(candidates) >= 2:
            v1, v2 = random.sample(candidates, 2)
            r1, r2 = new_state.routes[v1], new_state.routes[v2]
            if r1 and r2:
                i, j = random.randrange(len(r1)), random.randrange(len(r2))
                r1[i], r2[j] = r2[j], r1[i]

    elif move == 'relocate':
        v1 = random.choice(non_empty)
        v2 = random.randrange(num_vehicles)
        r1 = new_state.routes[v1]
        if r1:
            i = random.randrange(len(r1))
            customer = r1.pop(i)
            r2 = new_state.routes[v2]
            insert_pos = random.randint(0, len(r2))
            r2.insert(insert_pos, customer)

    elif move == 'reverse_segment':
        v = random.choice(non_empty)
        route = new_state.routes[v]
        if len(route) >= 2:
            i, j = sorted(random.sample(range(len(route)), 2))
            route[i:j + 1] = reversed(route[i:j + 1])

    return new_state


def simulated_annealing(initial_state: VRPState, depot, cost_matrix,
                         initial_temp: float = 100.0,
                         cooling_rate: float = 0.995,
                         min_temp: float = 0.01,
                         iterations_per_temp: int = 20,
                         max_iterations: int = 20000,
                         seed: int = None):
    """
    Run Simulated Annealing starting from `initial_state` (we seed this
    with the baseline solution so SA only has to IMPROVE on it, never
    starts from scratch).

    Args:
        initial_state: VRPState to start from.
        depot: depot node id.
        cost_matrix: dict-of-dicts shortest-path costs (from baseline_solver).
        initial_temp: starting temperature (higher = more exploration early on).
        cooling_rate: multiplicative cooling factor applied each outer loop
                      (temp *= cooling_rate). Closer to 1.0 = slower cooling.
        min_temp: stop once temperature drops below this.
        iterations_per_temp: number of neighbor proposals per temperature level.
        max_iterations: hard cap on total proposals, as a safety net.
        seed: RNG seed for reproducibility.

    Returns:
        best_state: VRPState with the lowest cost found.
        best_cost: cost of best_state.
        history: list of (iteration, current_cost, best_cost) for plotting
                 the convergence curve.
    """
    if seed is not None:
        random.seed(seed)

    current_state = initial_state.copy()
    current_cost = evaluate_solution(current_state, depot, cost_matrix)

    best_state = current_state.copy()
    best_cost = current_cost

    temp = initial_temp
    history = [(0, current_cost, best_cost)]
    iteration = 0

    while temp > min_temp and iteration < max_iterations:
        for _ in range(iterations_per_temp):
            iteration += 1
            candidate = _random_neighbor(current_state)
            candidate_cost = evaluate_solution(candidate, depot, cost_matrix)

            delta = candidate_cost - current_cost
            if delta < 0:
                # Improvement: always accept
                accept = True
            else:
                # Worse solution: accept with probability exp(-delta/temp).
                # This is the core SA mechanism that lets us escape local
                # minima -- early on (high temp) we tolerate big jumps in
                # cost, and as temp cools we become effectively greedy.
                accept_prob = math.exp(-delta / temp)
                accept = random.random() < accept_prob

            if accept:
                current_state = candidate
                current_cost = candidate_cost
                if current_cost < best_cost:
                    best_state = current_state.copy()
                    best_cost = current_cost

            if iteration >= max_iterations:
                break

        history.append((iteration, current_cost, best_cost))
        temp *= cooling_rate

    return best_state, best_cost, history


def solve_sa_vrp(G, depot, customers, num_vehicles, baseline_solution,
                  cost_matrix, sa_params=None, seed=None):
    """
    Convenience wrapper: take the baseline solution's routes as the SA
    starting point, run SA, and return a result dict in the same shape
    as solve_baseline_vrp's output (so benchmark.py can compare them
    directly).

    Args:
        G: networkx.Graph (unused directly here, kept for interface symmetry).
        depot: depot node id.
        customers: list of customer node ids.
        num_vehicles: number of vehicles.
        baseline_solution: output dict from solve_baseline_vrp (we reuse
                            its routes as our SA starting point and its
                            cost_matrix to avoid recomputing Dijkstra).
        cost_matrix: dict-of-dicts shortest path costs.
        sa_params: optional dict overriding simulated_annealing's defaults.
        seed: RNG seed.

    Returns:
        dict with 'routes', 'route_costs', 'total_cost', 'history'
        ('routes' includes the depot at start/end of each route, matching
        baseline_solver's output format).
    """
    sa_params = sa_params or {}

    # Convert baseline routes (which include depot at both ends) into the
    # internal VRPState representation (customers only, no depot)
    initial_routes = [
        [node for node in route if node != depot]
        for route in baseline_solution['routes']
    ]
    initial_state = VRPState(initial_routes)

    best_state, best_cost, history = simulated_annealing(
        initial_state, depot, cost_matrix, seed=seed, **sa_params
    )

    # Reconstruct full routes with depot at start/end, and per-vehicle costs,
    # so the output format matches solve_baseline_vrp exactly.
    full_routes = []
    route_costs = []
    for route in best_state.routes:
        full_route = [depot] + route + [depot]
        cost = 0.0
        current = depot
        for stop in route:
            leg = cost_matrix[current][stop]
            cost += leg if leg != float('inf') else 0.0
            current = stop
        cost += cost_matrix[current][depot] if cost_matrix[current][depot] != float('inf') else 0.0
        full_routes.append(full_route)
        route_costs.append(cost)

    return {
        'routes': full_routes,
        'route_costs': route_costs,
        'total_cost': best_cost,
        'history': history,
    }


if __name__ == "__main__":
    from network_generator import generate_network
    from baseline_solver import solve_baseline_vrp

    G, depot, customers = generate_network(num_nodes=20, num_customers=8, seed=42)
    baseline = solve_baseline_vrp(G, depot, customers, num_vehicles=3)
    print(f"Baseline total cost: {baseline['total_cost']:.2f}")

    sa_result = solve_sa_vrp(
        G, depot, customers, num_vehicles=3,
        baseline_solution=baseline,
        cost_matrix=baseline['cost_matrix'],
        seed=7
    )
    print(f"SA total cost:       {sa_result['total_cost']:.2f}")
    improvement = (baseline['total_cost'] - sa_result['total_cost']) / baseline['total_cost'] * 100
    print(f"Improvement: {improvement:.1f}%")
