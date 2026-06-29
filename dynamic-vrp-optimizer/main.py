"""
main.py

Single entry point to run the whole Dynamic VRP Optimization project:
    1. Run the 50-scenario benchmark (baseline vs Simulated Annealing).
    2. Save per-scenario results to results/benchmark_results.csv.
    3. Generate a demo route-comparison plot, an SA convergence plot, and
       a benchmark-wide improvement-distribution histogram.
    4. Print a final summary report to the console.

Usage:
    python main.py                      # run everything with defaults
    python main.py --scenarios 20       # run a smaller benchmark
    python main.py --no-plots           # skip plot generation (faster)
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from network_generator import generate_network
from baseline_solver import solve_baseline_vrp
from sa_optimizer import solve_sa_vrp
from benchmark import run_benchmark, save_results_csv
from visualize import plot_routes_comparison, plot_convergence, plot_benchmark_summary


RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def main():
    parser = argparse.ArgumentParser(
        description="Dynamic Network Optimization for Multi-Vehicle Routing (SA vs baseline)"
    )
    parser.add_argument("--scenarios", type=int, default=50,
                         help="Number of test network scenarios to benchmark (default: 50)")
    parser.add_argument("--traffic-ticks", type=int, default=5,
                         help="Simulated traffic ticks before solving each scenario (default: 5)")
    parser.add_argument("--no-plots", action="store_true",
                         help="Skip generating plots (just run the numeric benchmark)")
    parser.add_argument("--seed", type=int, default=2026,
                         help="Base random seed for reproducibility (default: 2026)")
    args = parser.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("=" * 60)
    print("DYNAMIC NETWORK OPTIMIZATION FOR SMART ROUTING")
    print(f"Running benchmark across {args.scenarios} scenarios...")
    print("=" * 60 + "\n")

    results, summary = run_benchmark(
        num_scenarios=args.scenarios,
        traffic_ticks=args.traffic_ticks,
        base_seed=args.seed,
        verbose=True,
    )

    csv_path = os.path.join(RESULTS_DIR, "benchmark_results.csv")
    save_results_csv(results, csv_path)

    if not args.no_plots:
        print("\nGenerating plots...")

        # 1. Route comparison on one illustrative demo network (separate
        #    from the benchmark scenarios, sized for a clean visual)
        G, depot, customers = generate_network(num_nodes=30, num_customers=8, seed=args.seed)
        baseline = solve_baseline_vrp(G, depot, customers, num_vehicles=3)
        sa_result = solve_sa_vrp(
            G, depot, customers, num_vehicles=3,
            baseline_solution=baseline, cost_matrix=baseline["cost_matrix"],
            seed=args.seed,
        )
        plot_routes_comparison(
            G, depot, baseline["routes"], sa_result["routes"],
            os.path.join(RESULTS_DIR, "route_comparison.png")
        )

        # 2. SA convergence curve from that same demo run
        plot_convergence(
            sa_result["history"],
            os.path.join(RESULTS_DIR, "sa_convergence.png")
        )

        # 3. Improvement distribution across the full benchmark
        plot_benchmark_summary(
            results,
            os.path.join(RESULTS_DIR, "improvement_distribution.png")
        )

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
    print(f"Average improvement over baseline : {summary['avg_improvement_pct']}%")
    print(f"Overall cost reduction            : {summary['overall_cost_reduction_pct']}%")
    print(f"Results CSV                       : {csv_path}")
    if not args.no_plots:
        print(f"Plots saved to                    : {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
