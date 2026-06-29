# Dynamic Network Optimization for Smart Routing

A dynamic, multi-vehicle routing optimization framework that models a
transportation network as a graph with **time-varying traffic conditions**,
and solves the routing problem using **Simulated Annealing**, benchmarked
against a classical greedy baseline across 50 diverse network scenarios.

## Problem statement

Given:
- A transportation network (intersections + roads) with a depot and a set
  of customer locations that must be visited,
- A fleet of multiple vehicles,
- Traffic conditions that change over time (congestion, road closures),

Find a set of vehicle routes that minimizes total travel cost (time),
where every customer is visited exactly once by exactly one vehicle.

This is a variant of the **Multi-Vehicle Routing Problem (VRP)** — known to
be NP-hard — under **dynamic** (time-varying) edge weights, which is what
makes it harder than the static shortest-path problem.

## Approach

1. **Network generation** (`network_generator.py`): builds synthetic
   transportation networks on a jittered grid layout (so they resemble
   real road networks) with random shortcut edges, at varying sizes
   (20 / 50 / 100 nodes).

2. **Traffic simulation** (`traffic_simulator.py`): simulates dynamic
   conditions — congestion multipliers that drift over time (mean-reverting
   random walk) and temporary road closures — so the network solved is a
   live snapshot, not a static, free-flow graph.

3. **Baseline solver** (`baseline_solver.py`): a classical greedy approach —
   Dijkstra for all-pairs shortest paths, round-robin customer assignment
   across vehicles, and Nearest-Neighbor route construction per vehicle.
   This is intentionally simple; it's the "before" picture.

4. **Simulated Annealing optimizer** (`sa_optimizer.py`): starts from the
   baseline solution and searches for improvements using four move types
   (intra-route swap, inter-route swap, relocate, segment reversal),
   accepting worse moves with decreasing probability over time
   (`exp(-Δcost / temperature)`) to escape local minima before converging.

5. **Benchmark** (`benchmark.py`): runs both solvers across 50 generated
   scenarios (varying network size, customer count, and vehicle count)
   under live traffic conditions, and reports aggregate improvement stats.

6. **Visualization** (`visualize.py`): route-comparison maps, SA convergence
   curves, and improvement-distribution histograms.

## Why Simulated Annealing

The VRP is NP-hard, so there's no efficient exact algorithm for large
instances. Greedy heuristics like Nearest-Neighbor commit to decisions
early and can't undo them, so they get stuck in locally bad solutions
(e.g. crossed-over routes, imbalanced vehicle loads). Simulated Annealing
fixes this by allowing temporary "backward" moves — accepting a worse
solution with some probability that decreases over time — which lets it
escape these local minima while still converging to a strong solution by
the end of the run.

## Results

Running the full 50-scenario benchmark (`python main.py`):

| Metric | Value |
|---|---|
| Average improvement over baseline | ~40% |
| Overall cost reduction | ~44% |
| Improvement range across scenarios | 13% – 62% |
| Avg. baseline solve time | ~0.001s |
| Avg. SA solve time | ~0.13s |

(Exact numbers vary slightly by random seed — see
`results/benchmark_results.csv` after running for your own numbers.)

Example route comparison on a 30-node network:

![Route comparison](results/route_comparison.png)

SA reliably converges to a better solution than the greedy starting point:

![Convergence](results/sa_convergence.png)

## Project structure

```
dynamic-vrp-optimizer/
├── src/
│   ├── network_generator.py   # synthetic transportation network generation
│   ├── traffic_simulator.py   # dynamic, time-varying traffic conditions
│   ├── baseline_solver.py     # greedy baseline (Dijkstra + Nearest-Neighbor)
│   ├── sa_optimizer.py        # Simulated Annealing VRP optimizer
│   ├── benchmark.py           # runs both solvers across 50 scenarios
│   └── visualize.py           # plotting utilities
├── tests/
│   └── test_solvers.py        # sanity tests for route validity & correctness
├── results/                   # benchmark CSV + generated plots (gitignored)
├── data/                      # (reserved for cached network instances)
├── main.py                    # CLI entry point — runs the full pipeline
├── requirements.txt
└── README.md
```

## Running it

```bash
pip install -r requirements.txt

# Run everything: 50-scenario benchmark + plots
python main.py

# Run a smaller benchmark, faster
python main.py --scenarios 10

# Skip plot generation
python main.py --no-plots

# Run the sanity test suite
python tests/test_solvers.py
```

Output:
- `results/benchmark_results.csv` — per-scenario costs and improvement %
- `results/route_comparison.png` — baseline vs SA routes side by side
- `results/sa_convergence.png` — SA cost-vs-iteration curve
- `results/improvement_distribution.png` — histogram of improvement % across all scenarios

## Possible extensions

- Add vehicle capacity constraints (true CVRP) and time windows (VRPTW)
- Compare SA against other metaheuristics (Genetic Algorithms, Tabu Search,
  Ant Colony Optimization) for a richer "algorithm comparison" angle
- Re-optimize routes mid-simulation when a road closure invalidates the
  current plan (true online/reactive replanning, rather than solving once
  per live snapshot)
- Swap the synthetic grid network for a real road network pulled from
  OpenStreetMap via `osmnx`

## Talking points for interviews

- **Why SA and not exact optimization (e.g. MILP)?** VRP is NP-hard;
  exact solvers don't scale past small instances. SA trades optimality
  guarantees for the ability to find good solutions on larger, dynamic
  problems in reasonable time.
- **Why seed SA from the baseline instead of a random start?** It
  guarantees SA never does worse than the greedy approach, and converges
  faster since it starts from a reasonable point rather than a random
  shuffle.
- **What makes this "dynamic" rather than static VRP?** The traffic
  simulator continuously perturbs edge weights and introduces temporary
  closures, so the cost matrix solvers operate on reflects live conditions,
  not fixed distances.
- **How do you know the result isn't a fluke?** The benchmark runs across
  50 scenarios of varying size/structure and reports the full distribution
  (mean, median, stdev, min/max) of improvement — not just one number.
