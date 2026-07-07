"""
main.py

Single entry point to run the Workstation Scheduling and Routing Optimizer:
    1. Run the 60-scenario benchmark (Baseline FIFO vs Simulated Annealing).
    2. Save per-scenario results to results/benchmark_results.csv.
    3. Generate a demo Gantt comparison chart, an SA convergence plot, and
       a benchmark-wide production lead time reduction histogram.
    4. Print a final summary report to the console.

Usage:
    python main.py                      # run everything with defaults (60 scenarios)
    python main.py --scenarios 20       # run a smaller benchmark
    python main.py --no-plots           # skip plot generation (faster)
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from job_generator import generate_scheduling_problem
from baseline_solver import solve_baseline_schedule
from sa_optimizer import solve_sa_schedule
from benchmark import run_benchmark, save_results_csv
from visualize import plot_gantt_comparison, plot_convergence, plot_benchmark_summary

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

def main():
    parser = argparse.ArgumentParser(
        description="Workstation Scheduling and Routing Optimizer for Flexible Shop Floors (SA vs Baseline)"
    )
    parser.add_argument("--scenarios", type=int, default=60,
                        help="Number of scenarios to benchmark (default: 60)")
    parser.add_argument("--disruption-ticks", type=int, default=5,
                        help="Shop-floor downtime ticks simulated before solving (default: 5)")
    parser.add_argument("--no-plots", action="store_true",
                        help="Skip generating plots (just run the numeric benchmark)")
    parser.add_argument("--seed", type=int, default=2026,
                        help="Base random seed for reproducibility (default: 2026)")
    args = parser.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("=" * 60)
    print("SHOP-FLOOR WORKSTATION SCHEDULING FRAMEWORK")
    print(f"Running benchmark across {args.scenarios} scenarios...")
    print("=" * 60 + "\n")

    results, summary = run_benchmark(
        num_scenarios=args.scenarios,
        disruption_ticks=args.disruption_ticks,
        base_seed=args.seed,
        verbose=True,
    )

    csv_path = os.path.join(RESULTS_DIR, "benchmark_results.csv")
    save_results_csv(results, csv_path)

    if not args.no_plots:
        print("\nGenerating plots...")

        # 1. Gantt chart comparison on a demo scenario (sized for a clean visual)
        # 8 jobs, 4 machines is a good size for visual comparison
        demo_scenario = generate_scheduling_problem(num_jobs=8, num_machines=4, seed=args.seed)
        
        # Add breakdowns if simulated (simulated for 3 ticks for demo)
        from disruption_simulator import DisruptionSimulator
        sim = DisruptionSimulator(demo_scenario, seed=args.seed)
        for _ in range(3):
            sim.step()
        live_demo = sim.get_live_scenario()

        baseline = solve_baseline_schedule(live_demo, rule='FIFO')
        sa_result = solve_sa_schedule(
            live_demo,
            baseline_solution=baseline,
            seed=args.seed,
            cooling_rate=0.995,       # slower cooling → better exploration
            iterations_per_temp=25,   # more tries per temperature
            max_iterations=30000      # more total iterations
        )
        
        plot_gantt_comparison(
            baseline, 
            sa_result,
            os.path.join(RESULTS_DIR, "gantt_comparison.png")
        )

        # 2. SA convergence curve from that same demo run
        plot_convergence(
            sa_result['history'],
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
    print(f"Average production lead time reduction  : {summary['avg_improvement_pct']}%")
    print(f"Average baseline workstation utilization: {summary['avg_baseline_utilization']}%")
    print(f"Average optimized workstation utilization: {summary['avg_sa_utilization']}%")
    print(f"Results CSV                            : {csv_path}")
    if not args.no_plots:
        print(f"Plots saved to                         : {RESULTS_DIR}/")

if __name__ == "__main__":
    main()
