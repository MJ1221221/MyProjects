"""
test_solvers.py

Lightweight sanity tests for the Production Scheduling Optimizer's core logic.
Validates schedule correctness, precedence constraints, machine double-booking rules,
and Simulated Annealing optimizer performance.

Run with:
    python tests/test_solvers.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from job_generator import generate_scheduling_problem, generate_test_suite
from disruption_simulator import DisruptionSimulator
from baseline_solver import solve_baseline_schedule
from sa_optimizer import solve_sa_schedule, SchedulingState, _random_neighbor

def check(condition, message):
    if not condition:
        raise AssertionError(f"FAILED: {message}")
    print(f"  OK: {message}")

def test_job_generation():
    print("test_job_generation")
    scenario = generate_scheduling_problem(num_jobs=8, num_machines=4, seed=42)
    check(len(scenario['jobs']) == 8, "generates correct number of jobs")
    check(len(scenario['machines']) == 4, "generates correct number of machines")
    
    # Check that job operations list structure is correct
    job0 = scenario['jobs'][0]
    check('job_id' in job0, "job has job_id")
    check('job_type' in job0, "job has job_type")
    check('operations' in job0, "job has operations")
    check(len(job0['operations']) >= 2 and len(job0['operations']) <= 4, 
          "job operations count within valid bounds")

def test_disruption_simulator():
    print("test_disruption_simulator")
    scenario = generate_scheduling_problem(num_jobs=5, num_machines=3, seed=42)
    sim = DisruptionSimulator(scenario, seed=1)
    
    for _ in range(5):
        sim.step()
        
    live = sim.get_live_scenario()
    check(sim.time == 5, "simulator time advanced correctly")
    check(len(live['jobs']) == 5, "live scenario preserves jobs")
    
    # Check that efficiency multipliers are working
    for m in scenario['machines']:
        check(sim.efficiency_multipliers[m] > 0.0, "machine efficiency multiplier is positive")
        
    sim.reset()
    check(sim.time == 0, "reset restores clock to zero")
    check(len(sim.active_breakdowns) == 0, "reset clears active breakdowns")

def validate_schedule_constraints(schedule, scenario):
    """
    Helper to validate that a schedule doesn't violate precedence or double-booking.
    """
    scheduled_ops = schedule['scheduled_ops']
    machine_schedules = schedule['machine_schedules']
    jobs = scenario['jobs']
    
    # 1. Check operation precedence constraints: for each job, op k must start >= end of op k-1
    for j_id, job in jobs.items():
        for k in range(1, len(job['operations'])):
            prev_op = scheduled_ops.get((j_id, k-1))
            curr_op = scheduled_ops.get((j_id, k))
            if prev_op and curr_op:
                check(curr_op['start'] >= prev_op['end'] - 1e-5, 
                      f"precedence constraint satisfied for Job {j_id} Op {k} (starts after Op {k-1} ends)")

    # 2. Check no machine double-bookings (overlapping processing windows)
    for m in scenario['machines']:
        intervals = []
        for start, end, j_id, j_type in machine_schedules[m]:
            intervals.append((start, end, j_id))
        
        # Sort by start time and verify no overlap
        intervals.sort(key=lambda x: x[0])
        for idx in range(1, len(intervals)):
            prev_start, prev_end, prev_jid = intervals[idx-1]
            curr_start, curr_end, curr_jid = intervals[idx]
            check(curr_start >= prev_end - 1e-5, 
                  f"no machine double-booking: Machine {m} has non-overlapping blocks {prev_jid} and {curr_jid}")

def test_baseline_solver_validity():
    print("test_baseline_solver_validity")
    scenario = generate_scheduling_problem(num_jobs=6, num_machines=3, seed=10)
    baseline = solve_baseline_schedule(scenario, rule='FIFO')
    
    check(baseline['makespan'] > 0.0, "baseline solver makespan is positive")
    validate_schedule_constraints(baseline, scenario)

def test_sa_improves_or_matches_baseline():
    print("test_sa_improves_or_matches_baseline")
    scenario = generate_scheduling_problem(num_jobs=6, num_machines=3, seed=15)
    baseline = solve_baseline_schedule(scenario, rule='FIFO')
    
    sa_res = solve_sa_schedule(scenario, baseline, seed=15)
    
    check(sa_res['makespan'] <= baseline['makespan'] + 1e-5, 
          "SA makespan is less than or equal to baseline makespan")
    validate_schedule_constraints(sa_res, scenario)

def test_state_neighbor_moves_preserve_operations():
    print("test_state_neighbor_moves_preserve_operations")
    scenario = generate_scheduling_problem(num_jobs=4, num_machines=3, seed=20)
    baseline = solve_baseline_schedule(scenario, rule='FIFO')
    
    state = SchedulingState(
        list(baseline['ops_sequence']),
        dict(baseline['machine_assignments'])
    )
    
    original_seq_len = len(state.ops_sequence)
    original_alloc_len = len(state.machine_assignments)
    
    # Run 50 random mutations and verify structure holds
    for _ in range(50):
        state = _random_neighbor(state, scenario)
        check(len(state.ops_sequence) == original_seq_len, "neighbor move preserves sequence length")
        check(len(state.machine_assignments) == original_alloc_len, "neighbor move preserves machine allocation size")
        
        # Verify job occurrence count matches operation counts
        for j_id, job in scenario['jobs'].items():
            op_count = len(job['operations'])
            seq_occurrences = state.ops_sequence.count(j_id)
            check(seq_occurrences == op_count, f"neighbor preserves op counts for job {j_id}")

def test_generate_test_suite_diversity():
    print("test_generate_test_suite_diversity")
    scenarios = generate_test_suite(num_scenarios=5, seed_offset=500)
    check(len(scenarios) == 5, "generated correct number of scenarios in suite")
    
    job_counts = set(s['num_jobs'] for s in scenarios)
    check(len(job_counts) > 1, "test suite contains scenarios of varying sizes")

def run_all_tests():
    tests = [
        test_job_generation,
        test_disruption_simulator,
        test_baseline_solver_validity,
        test_sa_improves_or_matches_baseline,
        test_state_neighbor_moves_preserve_operations,
        test_generate_test_suite_diversity
    ]
    
    failures = 0
    for test in tests:
        try:
            test()
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
