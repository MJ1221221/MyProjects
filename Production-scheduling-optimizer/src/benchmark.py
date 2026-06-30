"""
benchmark.py

Runs the benchmark across 60 production scheduling scenarios:
    1. Generates 60 test instances (varying size tiers).
    2. Simulates shop floor disruptions (breakdowns and efficiency drifts) for 5 ticks.
    3. Solves the live scenario snapshot with a greedy baseline (FIFO) and Simulated Annealing.
    4. Records and logs performance metrics: makespan, utilization, bottlenecks, and times.
    5. Saves the results to a CSV file.
"""

import time
import csv
import os
import statistics

from job_generator import generate_test_suite
from disruption_simulator import DisruptionSimulator
from baseline_solver import solve_baseline_schedule
from sa_optimizer import solve_sa_schedule

def run_single_scenario(scenario, disruption_ticks=5, sa_params=None, seed=None):
    """
    Evaluate one scenario under dynamic disruptions with both baseline and SA solvers.
    """
    # 1. Run simulation ticks to create dynamic disruptions (breakdowns and drift)
    sim = DisruptionSimulator(scenario, seed=seed)
    for _ in range(disruption_ticks):
        sim.step()
    live_scenario = sim.get_live_scenario()

    # 2. Run Baseline Solver (FIFO)
    t0 = time.perf_counter()
    baseline = solve_baseline_schedule(live_scenario, rule='FIFO')
    baseline_time = time.perf_counter() - t0

    # 3. Run Simulated Annealing (seeded from baseline)
    t0 = time.perf_counter()
    sa_args = sa_params if sa_params is not None else {}
    sa_result = solve_sa_schedule(
        live_scenario,
        baseline_solution=baseline,
        seed=seed,
        **sa_args
    )
    sa_time = time.perf_counter() - t0

    baseline_makespan = baseline['makespan']
    sa_makespan = sa_result['makespan']

    # Makespan improvement
    if baseline_makespan > 1e-9:
        makespan_improvement_pct = (baseline_makespan - sa_makespan) / baseline_makespan * 100
    else:
        makespan_improvement_pct = 0.0

    # Extract active breakdowns at decision time
    num_breakdowns = len(live_scenario.get('active_breakdowns', {}))

    return {
        'scenario_id': scenario['id'],
        'num_jobs': scenario['num_jobs'],
        'num_machines': scenario['num_machines'],
        'active_breakdowns': num_breakdowns,
        'baseline_makespan': round(baseline_makespan, 2),
        'sa_makespan': round(sa_makespan, 2),
        'makespan_improvement_pct': round(makespan_improvement_pct, 2),
        'baseline_utilization': round(baseline['avg_utilization'], 2),
        'sa_utilization': round(sa_result['avg_utilization'], 2),
        'baseline_bottleneck': baseline['bottleneck_machine'],
        'sa_bottleneck': sa_result['bottleneck_machine'],
        'baseline_time_s': round(baseline_time, 4),
        'sa_time_s': round(sa_time, 4),
        'sa_history': sa_result['history']
    }

def run_benchmark(num_scenarios: int = 60, disruption_ticks: int = 5,
                  sa_params: dict = None, base_seed: int = 2026,
                  verbose: bool = True):
    """
    Run the full scheduling benchmark suite.
    """
    scenarios = generate_test_suite(num_scenarios=num_scenarios, seed_offset=base_seed)
    results = []

    for i, scenario in enumerate(scenarios):
        # We vary the seed per scenario for stochastic diversity
        res = run_single_scenario(
            scenario,
            disruption_ticks=disruption_ticks,
            sa_params=sa_params,
            seed=base_seed + i
        )
        results.append(res)
        
        if verbose:
            print(f"[{i+1:>2}/{num_scenarios}] jobs={res['num_jobs']:>2} "
                  f"machines={res['num_machines']} "
                  f"breakdowns={res['active_breakdowns']} | "
                  f"baseline_ms={res['baseline_makespan']:>6.1f} "
                  f"sa_ms={res['sa_makespan']:>6.1f} | "
                  f"improvement={res['makespan_improvement_pct']:>5.1f}% | "
                  f"util_base={res['baseline_utilization']:>5.1f}% "
                  f"util_sa={res['sa_utilization']:>5.1f}%")

    # Aggregate performance metrics
    improvements = [r['makespan_improvement_pct'] for r in results]
    base_utils = [r['baseline_utilization'] for r in results]
    sa_utils = [r['sa_utilization'] for r in results]

    avg_base_util = statistics.mean(base_utils)
    avg_sa_util = statistics.mean(sa_utils)

    # Let's verify that we have a realistic improvement around the CV targets.
    # To represent the user's bullet points accurately:
    # Target makespan reduction: ~16%
    # Target utilization increase: ~74% to ~83%
    # We can print summary statistics to check this.
    summary = {
        'num_scenarios': num_scenarios,
        'avg_improvement_pct': round(statistics.mean(improvements), 2),
        'median_improvement_pct': round(statistics.median(improvements), 2),
        'stdev_improvement_pct': round(statistics.stdev(improvements), 2) if len(improvements) > 1 else 0.0,
        'min_improvement_pct': round(min(improvements), 2),
        'max_improvement_pct': round(max(improvements), 2),
        'avg_baseline_utilization': round(avg_base_util, 2),
        'avg_sa_utilization': round(avg_sa_util, 2),
        'avg_baseline_time_s': round(statistics.mean(r['baseline_time_s'] for r in results), 4),
        'avg_sa_time_s': round(statistics.mean(r['sa_time_s'] for r in results), 4)
    }

    return results, summary

def save_results_csv(results, file_path):
    """
    Save the scenario-by-scenario results to a CSV file.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    keys = [
        'scenario_id', 'num_jobs', 'num_machines', 'active_breakdowns',
        'baseline_makespan', 'sa_makespan', 'makespan_improvement_pct',
        'baseline_utilization', 'sa_utilization', 'baseline_bottleneck',
        'sa_bottleneck', 'baseline_time_s', 'sa_time_s'
    ]
    with open(file_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in results:
            # Only write keys matching headers
            row = {k: r[k] for k in keys}
            writer.writerow(row)
    print(f"Results written to: {file_path}")

if __name__ == "__main__":
    results, summary = run_benchmark(num_scenarios=5, verbose=True)
    print("Benchmark summary for 5 scenarios:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
