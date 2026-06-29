"""
benchmark.py

Runs the full experiment: generate N test network scenarios, solve each
one with both the greedy baseline and Simulated Annealing (under dynamic,
time-varying traffic conditions), and report aggregate improvement stats.

This is the script that produces the actual numbers behind claims like
"improved routing efficiency by X% and reduced transportation costs by Y%
across 50 diverse test network scenarios."

DYNAMIC EVALUATION:
Rather than solving once on a static graph, each scenario is evaluated
under a live traffic snapshot from TrafficSimulator after a few ticks.
This means the cost matrix used for both solvers reflects current
congestion/closures, not just free-flow distances -- which is what makes
this a "dynamic" network optimization problem rather than a static one.
"""

import time
import csv
import os
import statistics

from network_generator import generate_test_suite
from traffic_simulator import TrafficSimulator
from baseline_solver import solve_baseline_vrp
from sa_optimizer import solve_sa_vrp


def run_single_scenario(scenario, traffic_ticks=5, sa_params=None, seed=None):
    """
    Solve one scenario with both baseline and SA, under a simulated
    live-traffic snapshot.

    Args:
        scenario: dict from generate_test_suite (graph, depot, customers, etc).
        traffic_ticks: how many simulation steps to advance before solving,
                       so we're solving under realistic mid-simulation
                       traffic rather than the initial free-flow state.
        sa_params: optional override dict for simulated_annealing params.
        seed: RNG seed for this scenario's traffic + SA randomness.

    Returns:
        dict with scenario id, sizes, baseline/SA costs, improvement %,
        and timing info.
    """
    G = scenario['graph']
    depot = scenario['depot']
    customers = scenario['customers']
    num_vehicles = scenario['num_vehicles']

    # Advance traffic simulation to get a "live" snapshot of the network
    sim = TrafficSimulator(G, seed=seed)
    for _ in range(traffic_ticks):
        sim.step()
    live_graph = sim.get_live_graph()

    # --- Baseline ---
    t0 = time.perf_counter()
    baseline = solve_baseline_vrp(live_graph, depot, customers, num_vehicles)
    baseline_time = time.perf_counter() - t0

    # --- Simulated Annealing (seeded from baseline) ---
    t0 = time.perf_counter()
    sa_result = solve_sa_vrp(
        live_graph, depot, customers, num_vehicles,
        baseline_solution=baseline,
        cost_matrix=baseline['cost_matrix'],
        sa_params=sa_params,
        seed=seed,
    )
    sa_time = time.perf_counter() - t0

    baseline_cost = baseline['total_cost']
    sa_cost = sa_result['total_cost']

    # Guard against degenerate scenarios where baseline cost is ~0
    if baseline_cost > 1e-9:
        improvement_pct = (baseline_cost - sa_cost) / baseline_cost * 100
    else:
        improvement_pct = 0.0

    return {
        'scenario_id': scenario['id'],
        'num_nodes': scenario['num_nodes'],
        'num_customers': scenario['num_customers'],
        'num_vehicles': num_vehicles,
        'closed_edges': scenario['graph'].number_of_edges() - live_graph.number_of_edges(),
        'baseline_cost': round(baseline_cost, 3),
        'sa_cost': round(sa_cost, 3),
        'improvement_pct': round(improvement_pct, 2),
        'baseline_time_s': round(baseline_time, 4),
        'sa_time_s': round(sa_time, 4),
        'sa_history': sa_result['history'],  # kept for convergence plots
    }


def run_benchmark(num_scenarios: int = 50, traffic_ticks: int = 5,
                   sa_params: dict = None, base_seed: int = 2026,
                   verbose: bool = True):
    """
    Run the full benchmark across `num_scenarios` generated networks.

    Returns:
        results: list of per-scenario result dicts (see run_single_scenario).
        summary: dict of aggregate statistics across all scenarios.
    """
    scenarios = generate_test_suite(num_scenarios=num_scenarios, seed_offset=base_seed)
    results = []

    for i, scenario in enumerate(scenarios):
        result = run_single_scenario(
            scenario, traffic_ticks=traffic_ticks,
            sa_params=sa_params, seed=base_seed + i
        )
        results.append(result)
        if verbose:
            print(f"[{i+1:>2}/{num_scenarios}] nodes={result['num_nodes']:>3} "
                  f"customers={result['num_customers']:>2} "
                  f"vehicles={result['num_vehicles']} | "
                  f"baseline={result['baseline_cost']:>7.2f}  "
                  f"SA={result['sa_cost']:>7.2f}  "
                  f"improvement={result['improvement_pct']:>5.1f}%")

    improvements = [r['improvement_pct'] for r in results]
    baseline_costs = [r['baseline_cost'] for r in results]
    sa_costs = [r['sa_cost'] for r in results]

    total_baseline_cost = sum(baseline_costs)
    total_sa_cost = sum(sa_costs)
    overall_cost_reduction_pct = (
        (total_baseline_cost - total_sa_cost) / total_baseline_cost * 100
        if total_baseline_cost > 0 else 0.0
    )

    summary = {
        'num_scenarios': num_scenarios,
        'avg_improvement_pct': round(statistics.mean(improvements), 2),
        'median_improvement_pct': round(statistics.median(improvements), 2),
        'stdev_improvement_pct': round(statistics.stdev(improvements), 2) if len(improvements) > 1 else 0.0,
        'min_improvement_pct': round(min(improvements), 2),
        'max_improvement_pct': round(max(improvements), 2),
        'overall_cost_reduction_pct': round(overall_cost_reduction_pct, 2),
        'total_baseline_cost': round(total_baseline_cost, 2),
        'total_sa_cost': round(total_sa_cost, 2),
        'avg_baseline_time_s': round(statistics.mean(r['baseline_time_s'] for r in results), 4),
        'avg_sa_time_s': round(statistics.mean(r['sa_time_s'] for r in results), 4),
    }

    if verbose:
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)
        for k, v in summary.items():
            print(f"  {k:30s}: {v}")

    return results, summary


def save_results_csv(results, filepath):
    """Save per-scenario results to a CSV file (excludes SA history)."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    fieldnames = [k for k in results[0].keys() if k != 'sa_history']
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r[k] for k in fieldnames})
    print(f"\nSaved per-scenario results to: {filepath}")


if __name__ == "__main__":
    results, summary = run_benchmark(num_scenarios=50)
    save_results_csv(results, "/home/claude/dynamic-vrp-optimizer/results/benchmark_results.csv")
