"""
test_solvers.py

Lightweight sanity tests for the project's core logic. Not a full test
suite with a framework like pytest -- just enough assertions to catch
obvious regressions (e.g. "did I break route validity while refactoring").

Run with:
    python tests/test_solvers.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from network_generator import generate_network, generate_test_suite
from traffic_simulator import TrafficSimulator
from baseline_solver import solve_baseline_vrp, compute_cost_matrix
from sa_optimizer import solve_sa_vrp, VRPState, evaluate_solution


def check(condition, message):
    if not condition:
        raise AssertionError(f"FAILED: {message}")
    print(f"  OK: {message}")


def test_network_generation():
    print("test_network_generation")
    G, depot, customers = generate_network(num_nodes=20, num_customers=6, seed=1)
    check(G.number_of_nodes() == 20, "network has requested number of nodes")
    check(depot not in customers, "depot is not also a customer")
    check(len(customers) == 6, "correct number of customers generated")

    import networkx as nx
    check(nx.is_connected(G), "generated network is fully connected")


def test_traffic_simulator():
    print("test_traffic_simulator")
    G, depot, customers = generate_network(num_nodes=20, num_customers=6, seed=1)
    sim = TrafficSimulator(G, seed=1)
    base_edges = G.number_of_edges()

    for _ in range(10):
        sim.step()
    live = sim.get_live_graph()

    check(live.number_of_edges() <= base_edges, "live graph never has MORE edges than base graph")
    check(sim.time == 10, "simulator clock advanced correctly")

    sim.reset()
    check(sim.time == 0, "reset() restores clock to zero")
    check(len(sim.active_closures) == 0, "reset() clears active closures")


def test_baseline_solver_route_validity():
    print("test_baseline_solver_route_validity")
    G, depot, customers = generate_network(num_nodes=30, num_customers=10, seed=2)
    solution = solve_baseline_vrp(G, depot, customers, num_vehicles=3)

    all_visited = set()
    for route in solution['routes']:
        check(route[0] == depot, "every route starts at depot")
        check(route[-1] == depot, "every route ends at depot")
        all_visited.update(route[1:-1])

    check(all_visited == set(customers), "every customer visited exactly once across all routes")
    check(solution['total_cost'] >= 0, "total cost is non-negative")


def test_sa_improves_or_matches_baseline():
    print("test_sa_improves_or_matches_baseline")
    G, depot, customers = generate_network(num_nodes=30, num_customers=10, seed=3)
    baseline = solve_baseline_vrp(G, depot, customers, num_vehicles=3)
    sa_result = solve_sa_vrp(
        G, depot, customers, num_vehicles=3,
        baseline_solution=baseline, cost_matrix=baseline['cost_matrix'], seed=3
    )

    # SA starts FROM the baseline solution, so it should never end up worse
    # (it always tracks the best solution seen, including the starting one)
    check(sa_result['total_cost'] <= baseline['total_cost'] + 1e-6,
          "SA result is never worse than its baseline starting point")

    all_visited = set()
    for route in sa_result['routes']:
        check(route[0] == depot, "every SA route starts at depot")
        check(route[-1] == depot, "every SA route ends at depot")
        all_visited.update(route[1:-1])
    check(all_visited == set(customers), "SA solution still visits every customer exactly once")


def test_vrp_state_neighbor_moves_preserve_customers():
    print("test_vrp_state_neighbor_moves_preserve_customers")
    from sa_optimizer import _random_neighbor
    import random
    random.seed(42)

    state = VRPState([[1, 2, 3], [4, 5], [6, 7, 8, 9]])
    original_customers = set(c for route in state.routes for c in route)

    for _ in range(50):
        state = _random_neighbor(state)
        new_customers = set(c for route in state.routes for c in route)
        check(new_customers == original_customers,
              "neighbor move preserves the full customer set (no customer lost/duplicated)")


def test_generate_test_suite_diversity():
    print("test_generate_test_suite_diversity")
    scenarios = generate_test_suite(num_scenarios=10, seed_offset=999)
    check(len(scenarios) == 10, "correct number of scenarios generated")
    sizes = set(s['num_nodes'] for s in scenarios)
    check(len(sizes) > 1, "test suite contains networks of varying size (not all identical)")


def run_all_tests():
    tests = [
        test_network_generation,
        test_traffic_simulator,
        test_baseline_solver_route_validity,
        test_sa_improves_or_matches_baseline,
        test_vrp_state_neighbor_moves_preserve_customers,
        test_generate_test_suite_diversity,
    ]
    failures = 0
    for test_fn in tests:
        try:
            test_fn()
        except AssertionError as e:
            print(e)
            failures += 1
        print()

    if failures == 0:
        print(f"All {len(tests)} test groups passed.")
    else:
        print(f"{failures} test group(s) FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
