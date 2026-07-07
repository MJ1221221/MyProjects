# Dynamic Workstation Scheduling & Sequencing System for Smart Manufacturing

A dynamic, flexible shop-floor routing and sequencing engine that models a
manufacturing shop floor with **sequence-dependent changeover times** and **unexpected workstation downtime**, 
and optimizes the scheduling sequence using **Simulated Annealing (SA)**, benchmarked 
against a greedy priority dispatch routing baseline across 60 diverse production runs.

## Problem Statement

Given:
- A set of jobs/production orders, each containing a sequence of operations that must be processed in order,
- A set of workstations/machines, where each operation can be processed on a subset of compatible workstations with varying base processing times,
- Sequence-dependent changeover times (overhead when transitioning between different product families on any workstation),
- Dynamic shop-floor disruptions (unexpected workstation downtime breakdowns and efficiency fluctuations),

Find a workstation allocation and operation sequence that minimizes the **Production Lead Time (Makespan)** 
and maximizes **Workstation Utilization**, satisfying all precedence and non-preemption constraints.

This is a variant of the **Flexible Job Shop Scheduling Problem (FJSP)** — known to be combinatorial and NP-hard — under dynamic shop-floor constraints.

## Approach

1. **Production Scenario Generation** (`job_generator.py`): generates synthetic factory routing environments with varying job counts (5 to 15), workstation counts (3 to 8), compatible routing constraints, and sequence-dependent changeover matrices.

2. **Downtime & Disruption Simulation** (`disruption_simulator.py`): simulates live shop floor dynamics — random workstation downtime and workstation efficiency fluctuations (mean-reverting random walks representing tool wear or thermal drift) — so the schedule solved is a live dynamic snapshot, not a static layout.

3. **Greedy Baseline Solver** (`baseline_solver.py`): a shop-floor routing approach — FIFO (First-In, First-Out) or SPT (Shortest Processing Time) sequencing coupled with a greedy workstation assignment (allocating operations to the workstation that can complete them the earliest). This models standard heuristic shop-floor routing rules.

4. **Simulated Annealing Optimizer** (`sa_optimizer.py`): starts from the baseline schedule and optimizes both operation sequence (using swap, relocate, and reversal moves on a job-repetition permutation representation) and workstation assignments, accepting worse moves probabilistically via `exp(-Δlead_time / temperature)` to escape local minima.

5. **Benchmark Engine** (`benchmark.py`): runs both solvers across 60 simulated production runs (varying sizes and downtime profiles) under live disruption conditions, reporting production lead time reduction, workstation utilization, throughput, and bottleneck statistics.

6. **Visualization** (`visualize.py`): generates Gantt charts of workstation timelines, SA lead-time convergence curves, and production lead-time reduction histograms.

## Why Simulated Annealing for Workstation Scheduling

The FJSP is NP-hard, making exact mathematical programming (like MILP) scale poorly to real factory sizes. Greedy sequencing rules (like FIFO or SPT) make early routing decisions that lead to massive idle-time gaps, tool changeover overheads, and workstation load imbalances later. 

Simulated Annealing resolves this by treating the schedule as a joint optimization state. It starts from a reasonable greedy baseline and uses 4 neighborhood operators (sequence swap, sequence relocate, sequence reversal, and workstation re-allocation) to search the state space. By accepting worse solutions at high temperatures, it bypasses local minima and converges to high-quality production schedules.

## Results

Running the full 60-scenario benchmark (`python main.py`):

| Metric | Value |
|---|---|
| Average Production Lead Time Reduction | ~16% |
| Average Baseline Workstation Utilization | ~74% |
| Average Optimized Workstation Utilization | ~83% |
| Scenarios Evaluated | 60 |
| Baseline Solve Time | <0.001s |
| SA Solve Time | ~0.15s |

*(Note: Exact results depend on random seed initialization.)*

## Project Structure

```
Production-scheduling-optimizer/
├── src/
│   ├── job_generator.py         # synthetic routing instance generation
│   ├── disruption_simulator.py   # dynamic breakdowns & efficiency drift simulator
│   ├── baseline_solver.py       # dispatch rules (FIFO/SPT) + greedy workstation assignment
│   ├── sa_optimizer.py          # Simulated Annealing scheduler (sequence + allocation)
│   ├── benchmark.py             # runs benchmark across 60 scenarios
│   └── visualize.py             # Gantt charts and matplotlib plotting utilities
├── tests/
│   └── test_solvers.py          # correctness tests for scheduling constraints
├── results/                     # output CSV + Gantt charts (gitignored)
├── main.py                      # CLI entry point to run the pipeline
├── requirements.txt             # project dependencies
└── README.md                    # project documentation
```

## Running the Code

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the benchmark (60 scenarios) and generate visualization plots:
```bash
python main.py
```

Run a smaller benchmark (e.g., 10 scenarios) for quick verification:
```bash
python main.py --scenarios 10
```

Run the sanity test suite:
```bash
python tests/test_solvers.py
```

## Talking Points for Interviews (ME Core / Industrial Engg / Production Engg)

- **Why is this project relevant to production and manufacturing engineering?**
  Operations scheduling and sequence-dependent setups are foundational to production planning, assembly line balancing, and factory layout optimization. Managing workstation changeovers and unexpected downtimes represents the core operational challenge in physical manufacturing.
  
- **What is the significance of the "Job-Shop Priority Permutation" representation?**
  We represent the operation sequence as a permutation of job IDs with repetition. If Job 1 has 3 operations, it appears exactly 3 times in the list. This ensures that any permutation of the sequence is *always* feasible, completely eliminating precedence violation errors during neighbor moves and making SA highly efficient.
  
- **How are sequence-dependent changeover times handled?**
  Transitioning between product families (types) on any workstation incurs a changeover time (e.g. tool change, purging, re-clamping). The scheduling engine looks up the changeover matrix `changeover_matrix[type_from][type_to]` and inserts this changeover block before starting the operation, ensuring that the schedule accurately reflects physical manufacturing setup losses.
  
- **How are dynamic disruptions modeled?**
  Rather than assuming a static workshop, we simulate workstation breakdowns (downtimes) and efficiency drift (representing tool wear or thermal sluggishness). The baseline and SA algorithms operate on a live snapshot, and breakdowns are scheduled as blocked downtime intervals, forcing the solver to route operations around unavailable periods.
