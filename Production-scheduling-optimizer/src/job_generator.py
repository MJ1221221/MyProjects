"""
job_generator.py

Generates synthetic flexible job shop routing scenarios for the Production Scheduling Optimizer.

In a Flexible Job Shop Scheduling Problem (FJSP):
    - Machines   = resources capable of processing specific tasks/operations.
    - Jobs       = products to be manufactured, each with an ordered list of operations.
    - Operations = individual tasks requiring a compatible machine and processing time.
    - Job Types  = product families (e.g., 'Gear', 'Shaft', 'Bracket') that define changeover times.
    - Changeover Time = sequence-dependent time required to reconfigure a machine/workstation
                   when transitioning between different product families (job types).
"""

import random
import math

# Define default job families
JOB_TYPES = ["Gear", "Shaft", "Bracket", "Housing"]

def generate_changeover_matrix(types=None, min_changeover=1.0, max_changeover=4.0, seed=None):
    """
    Generate a sequence-dependent changeover time matrix between job types.
    Transitioning from type A to type B on any machine incurs a changeover cost (time).
    """
    if seed is not None:
        random.seed(seed)
    
    if types is None:
        types = JOB_TYPES
        
    changeover_matrix = {t1: {} for t1 in types}
    for t1 in types:
        for t2 in types:
            if t1 == t2:
                changeover_matrix[t1][t2] = 0.0  # No changeover required if job types are identical
            else:
                changeover_matrix[t1][t2] = round(random.uniform(min_changeover, max_changeover), 1)
    return changeover_matrix

def generate_scheduling_problem(num_jobs: int, num_machines: int, seed: int = None):
    """
    Generate a single synthetic FJSP problem instance.

    Args:
        num_jobs: number of jobs to generate.
        num_machines: number of machines in the workshop.
        seed: RNG seed for reproducibility.

    Returns:
        scenario: dict containing 'machines', 'job_types', 'changeover_matrix', 'jobs'
    """
    if seed is not None:
        random.seed(seed)

    machines = list(range(num_machines))
    changeover_matrix = generate_changeover_matrix(JOB_TYPES, seed=seed)

    jobs = {}
    for job_id in range(num_jobs):
        j_type = random.choice(JOB_TYPES)
        # Each job has between 2 and 4 operations in sequence
        num_ops = random.randint(2, 4)
        operations = []
        
        for op_idx in range(num_ops):
            # Select a subset of machines that are compatible with this operation
            # Highly constrained: at least 1 machine, at most all, usually 1-3 machines
            num_eligible = random.randint(1, min(3, num_machines))
            eligible_machines = random.sample(machines, num_eligible)
            
            op_machine_costs = {}
            for m in eligible_machines:
                # Processing time is randomly generated, influenced by machine speed (simulated implicitly)
                base_time = round(random.uniform(5.0, 25.0), 1)
                op_machine_costs[m] = base_time
                
            operations.append({
                'op_id': op_idx,
                'eligible_machines': op_machine_costs
            })
            
        jobs[job_id] = {
            'job_id': job_id,
            'job_type': j_type,
            'operations': operations
        }

    return {
        'machines': machines,
        'job_types': JOB_TYPES,
        'changeover_matrix': changeover_matrix,
        'jobs': jobs
    }

def generate_test_suite(num_scenarios: int = 60, seed_offset: int = 2000):
    """
    Generate a batch of 60 test scheduling scenarios with varying size,
    used for benchmark runs (covers small, medium, and large workshop tiers).

    Returns:
        List of dicts: {'id', 'num_jobs', 'num_machines', 'scenario_data'}
    """
    scenarios = []
    size_tiers = [
        (5, 3),    # small shop
        (10, 5),   # medium shop
        (15, 8),   # large shop
    ]

    for i in range(num_scenarios):
        seed = seed_offset + i
        random.seed(seed)
        
        num_jobs, num_machines = random.choice(size_tiers)
        # Vary job and machine count slightly around tiers
        num_jobs = max(3, num_jobs + random.randint(-1, 2))
        num_machines = max(2, num_machines + random.randint(-1, 1))

        scenario_data = generate_scheduling_problem(num_jobs, num_machines, seed)

        scenarios.append({
            'id': i,
            'num_jobs': num_jobs,
            'num_machines': num_machines,
            'machines': scenario_data['machines'],
            'changeover_matrix': scenario_data['changeover_matrix'],
            'jobs': scenario_data['jobs'],
        })

    return scenarios

if __name__ == "__main__":
    # Quick smoke test
    scenarios = generate_test_suite(num_scenarios=2)
    print(f"Generated {len(scenarios)} scenarios.")
    s1 = scenarios[0]
    print(f"Scenario 0: {s1['num_jobs']} jobs, {s1['num_machines']} machines.")
    print("Job 0 info:", s1['jobs'][0])
