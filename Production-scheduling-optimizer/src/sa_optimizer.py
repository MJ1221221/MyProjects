"""
sa_optimizer.py

Simulated Annealing (SA) optimizer for the Flexible Job Shop Scheduling Problem (FJSP).
Solves the joint sequencing and machine allocation problem.
"""

import math
import random
import copy
from baseline_solver import evaluate_schedule

class SchedulingState:
    """
    Container for a candidate FJSP solution.
    - ops_sequence: list of job_ids representing operation priority.
    - machine_assignments: dict mapping (job_id, op_idx) -> machine_id.
    """
    def __init__(self, ops_sequence, machine_assignments):
        self.ops_sequence = ops_sequence
        self.machine_assignments = machine_assignments

    def copy(self):
        return SchedulingState(
            list(self.ops_sequence),
            dict(self.machine_assignments)
        )

def _random_neighbor(state: SchedulingState, scenario):
    """
    Produce a neighboring solution by applying a random move:
    1. Swap two operations in the sequence.
    2. Relocate an operation in the sequence.
    3. Reverse a subsequence of operations.
    4. Reallocate an operation to a different compatible machine.
    """
    new_state = state.copy()
    seq_len = len(new_state.ops_sequence)
    
    if seq_len < 2:
        return new_state

    # Pick move type
    move = random.choice(['swap', 'relocate', 'reverse', 'reallocate'])
    
    if move == 'swap':
        i, j = random.sample(range(seq_len), 2)
        new_state.ops_sequence[i], new_state.ops_sequence[j] = new_state.ops_sequence[j], new_state.ops_sequence[i]
        
    elif move == 'relocate':
        i = random.randrange(seq_len)
        job_id = new_state.ops_sequence.pop(i)
        j = random.randint(0, seq_len - 1)
        new_state.ops_sequence.insert(j, job_id)
        
    elif move == 'reverse':
        i, j = sorted(random.sample(range(seq_len), 2))
        new_state.ops_sequence[i:j+1] = reversed(new_state.ops_sequence[i:j+1])
        
    elif move == 'reallocate':
        # Find operations that have multiple eligible machines
        jobs = scenario['jobs']
        candidates = []
        for j_id, job in jobs.items():
            for op_idx, op in enumerate(job['operations']):
                if len(op['eligible_machines']) > 1:
                    candidates.append((j_id, op_idx))
                    
        if candidates:
            j_id, op_idx = random.choice(candidates)
            op = jobs[j_id]['operations'][op_idx]
            current_m = new_state.machine_assignments[(j_id, op_idx)]
            options = [m for m in op['eligible_machines'] if m != current_m]
            if options:
                new_state.machine_assignments[(j_id, op_idx)] = random.choice(options)
                
    return new_state

def solve_sa_schedule(scenario, baseline_solution,
                      initial_temp: float = 100.0,
                      cooling_rate: float = 0.992,
                      min_temp: float = 0.05,
                      iterations_per_temp: int = 15,
                      max_iterations: int = 15000,
                      seed: int = None):
    """
    Optimize schedule using Simulated Annealing.
    Seeded from baseline_solution.
    """
    if seed is not None:
        random.seed(seed)

    # Initialize state from baseline
    initial_state = SchedulingState(
        list(baseline_solution['ops_sequence']),
        dict(baseline_solution['machine_assignments'])
    )
    
    current_state = initial_state.copy()
    current_schedule = evaluate_schedule(
        current_state.ops_sequence, 
        current_state.machine_assignments, 
        scenario
    )
    current_cost = current_schedule['makespan']
    
    best_state = current_state.copy()
    best_schedule = current_schedule
    best_cost = current_cost
    
    temp = initial_temp
    history = [(0, current_cost, best_cost)]
    iteration = 0
    
    while temp > min_temp and iteration < max_iterations:
        for _ in range(iterations_per_temp):
            iteration += 1
            candidate = _random_neighbor(current_state, scenario)
            candidate_schedule = evaluate_schedule(
                candidate.ops_sequence, 
                candidate.machine_assignments, 
                scenario
            )
            candidate_cost = candidate_schedule['makespan']
            
            delta = candidate_cost - current_cost
            if delta < 0:
                accept = True
            else:
                # Accept worse move with probability
                # Clamp probability to prevent overflow
                try:
                    accept_prob = math.exp(-delta / temp)
                except OverflowError:
                    accept_prob = 0.0
                accept = random.random() < accept_prob
                
            if accept:
                current_state = candidate
                current_cost = candidate_cost
                current_schedule = candidate_schedule
                
                if current_cost < best_cost:
                    best_state = current_state.copy()
                    best_cost = current_cost
                    best_schedule = candidate_schedule
                    
            if iteration >= max_iterations:
                break
                
        history.append((iteration, current_cost, best_cost))
        temp *= cooling_rate
        
    return {
        'makespan': best_schedule['makespan'],
        'machine_schedules': best_schedule['machine_schedules'],
        'job_completion_times': best_schedule['job_completion_times'],
        'machine_utilization': best_schedule['machine_utilization'],
        'avg_utilization': best_schedule['avg_utilization'],
        'bottleneck_machine': best_schedule['bottleneck_machine'],
        'scheduled_ops': best_schedule['scheduled_ops'],
        'ops_sequence': best_state.ops_sequence,
        'machine_assignments': best_state.machine_assignments,
        'history': history
    }

if __name__ == "__main__":
    from job_generator import generate_scheduling_problem
    from baseline_solver import solve_baseline_schedule
    
    scenario = generate_scheduling_problem(num_jobs=4, num_machines=3, seed=42)
    baseline = solve_baseline_schedule(scenario, rule='FIFO')
    print("Baseline makespan:", baseline['makespan'])
    
    sa_res = solve_sa_schedule(scenario, baseline, seed=42)
    print("SA makespan:", sa_res['makespan'])
    print("SA avg utilization:", sa_res['avg_utilization'])
