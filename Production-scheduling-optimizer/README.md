# Production Scheduling Optimization for Smart Manufacturing

A dynamic, flexible job shop scheduling optimization framework that models a
manufacturing shop floor with **sequence-dependent setup times** and **unexpected machine breakdowns**, 
and solves the scheduling problem using **Simulated Annealing (SA)**, benchmarked 
against a classical greedy priority dispatch baseline across 60 diverse scenarios.

## Problem Statement

Given:
- A set of jobs, each containing a sequence of operations that must be processed in order,
- A set of workstations/machines, where each operation can be processed on a subset of compatible machines with varying base processing times,
- Sequence-dependent setup times (overhead when transitioning between different product families/job types on any machine),
- Dynamic shop-floor disruptions (machine breakdown downtime and efficiency fluctuations),

Find a machine allocation and operation sequence that minimizes the **Makespan** (total time to complete all jobs) 
and maximizes **Machine Utilization**, satisfying all precedence and non-preemption constraints.

This is a variant of the **Flexible Job Shop Scheduling Problem (FJSP)** — known to be NP-hard — under dynamic constraints.

## Approach

1. **Job Generation** (`job_generator.py`): generates synthetic factory scheduling environments with varying job counts (5 to 15), machine counts (3 to 8), compatible routing constraints, and sequence-dependent setup matrices.

2. **Disruption Simulation** (`disruption_simulator.py`): simulates live shop floor dynamics — random machine breakdowns (downtime repair intervals) and machine efficiency fluctuations (mean-reverting random walks representing tool wear or thermal effects) — so the schedule solved is a live dynamic snapshot, not a static deterministic layout.

3. **Baseline Solver** (`baseline_solver.py`): a classical greedy dispatching approach — FIFO (First-In, First-Out) or SPT (Shortest Processing Time) sequencing coupled with a greedy machine assignment (allocating operations to the machine that can finish them the earliest). This models standard heuristic shop-floor scheduling rules.

4. **Simulated Annealing Optimizer** (`sa_optimizer.py`): starts from the baseline schedule and optimizes both operation sequence (using swap, relocate, and reversal moves on a job-repetition permutation representation) and machine assignments, accepting worse moves probabilistically via `exp(-Δmakespan / temperature)` to escape local minima.

5. **Benchmark** (`benchmark.py`): runs both solvers across 60 simulated scenarios (varying sizes and breakdown profiles) under live disruption conditions, reporting makespan reduction, machine utilization, throughput, and bottleneck statistics.

6. **Visualization** (`visualize.py`): generates Gantt charts of workstation timelines, SA convergence curves, and makespan improvement histograms.

## Why Simulated Annealing

The FJSP is NP-hard, making exact mathematical programming (like MILP) scale poorly to real factory sizes. Greedy priority dispatch rules (like FIFO or SPT) make early scheduling decisions that lead to massive idle-time gaps, tool setup overheads, and machine imbalances later. 

Simulated Annealing resolves this by treating the schedule as a joint optimization state. It starts from a reasonable greedy baseline and uses 4 neighborhood operators (sequence swap, sequence relocate, sequence reversal, and machine re-allocation) to search the state space. By accepting worse solutions at high temperatures, it bypasses local minima and converges to high-quality schedules.

## Results

Running the full 60-scenario benchmark (`python main.py`):

| Metric | Value |
|---|---|
| Average Makespan Reduction | ~16% |
| Average Baseline Machine Utilization | ~74% |
| Average Optimized Machine Utilization | ~83% |
| Scenarios Evaluated | 60 |
| Baseline Solve Time | <0.001s |
| SA Solve Time | ~0.15s |

*(Note: Exact results depend on random seed initialization.)*

## Project Structure

```
Production-scheduling-optimizer/
├── src/
│   ├── job_generator.py         # synthetic FJSP instance generation
│   ├── disruption_simulator.py   # dynamic breakdowns & efficiency drift simulator
│   ├── baseline_solver.py       # dispatch rules (FIFO/SPT) + greedy machine assignment
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

## Talking Points for Interviews (ME Core / Industrial Engg)

- **Why is this project relevant to mechanical/production engineering?**
  Operations Research and scheduling are foundational to production planning, assembly line balancing, and factory layout optimization. Managing tool setups and machine downtimes represents the core operational challenge in physical manufacturing.
  
- **What is the significance of the "Job-Shop Priority Permutation" representation?**
  We represent the operation sequence as a permutation of job IDs with repetition. If Job 1 has 3 operations, it appears exactly 3 times in the list. This ensures that any permutation of the sequence is *always* feasible, completely eliminating precedence violation errors during neighbor moves and making SA highly efficient.
  
- **How are sequence-dependent setup times handled?**
  Transitioning between job types (families) on any workstation incurs a setup time (e.g. tool change, re-clamping). The scheduling engine looks up the setup matrix `setup[type_from][type_to]` and inserts this setup block before starting the operation, ensuring that the schedule accurately reflects physical manufacturing setup losses.
  
- **How are dynamic disruptions modeled?**
  Rather than assuming a static workshop, we simulate machine breakdowns (downtimes) and efficiency drift (representing tool wear or thermal sluggishness). The baseline and SA algorithms operate on a live snapshot, and breakdowns are scheduled as blocked downtime intervals, forcing the solver to route operations around unavailable periods.
