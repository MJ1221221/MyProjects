"""
baseline_solver.py

Baseline heuristic solver for the Flexible Job Shop Scheduling Problem (FJSP).
This solver uses priority dispatching rules (FIFO or Shortest Processing Time)
and greedily assigns operations to the machine that can finish them the earliest.
"""

def find_earliest_start(machine_schedule, job_ready_time, duration, job_type, setup_matrix):
    """
    Find the earliest valid start time t >= job_ready_time for an operation
    of job_type with duration, on a machine with machine_schedule.
    
    machine_schedule: list of (start, end, job_id, job_type) sorted by start
    """
    # Candidate start times to test:
    # 1. Right when the job is ready
    candidates = [job_ready_time]
    
    # 2. Right after any existing block ends (including setup)
    for _, end_b, _, j_type in machine_schedule:
        setup = 0.0 if j_type == 'Breakdown' else setup_matrix[j_type][job_type]
        candidates.append(end_b + setup)
        
    candidates = sorted(list(set(c for c in candidates if c >= job_ready_time)))
    
    for t in candidates:
        # Check if the interval [t, t + duration] is valid
        valid = True
        for start_b, end_b, _, j_type in machine_schedule:
            # Overlap check
            if not (t + duration <= start_b or t >= end_b):
                valid = False
                break
            
            # Predecessor setup check: if this block ends at or before t
            if end_b <= t:
                # Is it the immediate predecessor?
                other_between = any(end_o <= t and start_o >= end_b 
                                    for start_o, end_o, _, _ in machine_schedule 
                                    if (start_o, end_o) != (start_b, end_b))
                if not other_between:
                    setup = 0.0 if j_type == 'Breakdown' else setup_matrix[j_type][job_type]
                    if t < end_b + setup:
                        valid = False
                        break
                        
            # Successor setup check: if this block starts at or after t + duration
            if start_b >= t + duration:
                # Is it the immediate successor?
                other_between = any(start_o >= t + duration and end_o <= start_b 
                                    for start_o, end_o, _, _ in machine_schedule 
                                    if (start_o, end_o) != (start_b, end_b))
                if not other_between:
                    setup = 0.0 if j_type == 'Breakdown' else setup_matrix[job_type][j_type]
                    if t + duration + setup > start_b:
                        valid = False
                        break
        if valid:
            return t
            
    # Fallback to appending at the end of the last scheduled item
    if machine_schedule:
        last_block = machine_schedule[-1]
        last_end = last_block[1]
        last_type = last_block[3]
        setup = 0.0 if last_type == 'Breakdown' else setup_matrix[last_type][job_type]
        return max(job_ready_time, last_end + setup)
    return job_ready_time

def evaluate_schedule(ops_sequence, machine_assignments, scenario):
    """
    Simulate the scheduling of operations based on a priority sequence
    and machine assignments, returning full schedule details.

    Args:
        ops_sequence: list of job_ids representing the order/priority of scheduling.
                      For FJSP, job_id appears in the list as many times as it has operations.
                      E.g., [0, 1, 0, 1] means Job 0 Op 0, Job 1 Op 0, Job 0 Op 1, Job 1 Op 1.
        machine_assignments: dict mapping (job_id, op_idx) -> machine_id.
        scenario: dict containing jobs, setup_matrix, machines, and active_breakdowns.

    Returns:
        schedule: dict with 'makespan', 'machine_schedules', 'job_completion_times', etc.
    """
    machines = scenario['machines']
    setup_matrix = scenario['setup_matrix']
    jobs = scenario['jobs']
    
    # Initialize machine schedules with any active breakdowns as dummy blocks
    machine_schedules = {m: [] for m in machines}
    if 'active_breakdowns' in scenario:
        for m, duration in scenario['active_breakdowns'].items():
            # Breakdown starts at time 0 and lasts duration
            machine_schedules[m].append((0.0, float(duration), -1, 'Breakdown'))
            
    # Track completion time of each job's last scheduled operation
    job_last_completion = {j_id: 0.0 for j_id in jobs}
    # Track which operation index is next for each job
    job_next_op_idx = {j_id: 0 for j_id in jobs}
    
    # To keep track of scheduled operations for details
    scheduled_ops = {}
    
    for job_id in ops_sequence:
        op_idx = job_next_op_idx[job_id]
        job = jobs[job_id]
        
        # If we've already scheduled all ops for this job, skip (safety check)
        if op_idx >= len(job['operations']):
            continue
            
        op = job['operations'][op_idx]
        machine = machine_assignments[(job_id, op_idx)]
        
        # Get base duration
        base_dur = op['eligible_machines'].get(machine, float('inf'))
        if base_dur == float('inf'):
            # If assigned to incompatible machine, apply heavy penalty
            base_dur = 1e4
            
        # Find earliest start time on assigned machine
        ready_time = job_last_completion[job_id]
        start_time = find_earliest_start(
            machine_schedules[machine], 
            ready_time, 
            base_dur, 
            job['job_type'], 
            setup_matrix
        )
        
        end_time = start_time + base_dur
        
        # Record block in machine schedule
        machine_schedules[machine].append((start_time, end_time, job_id, job['job_type']))
        # Sort schedule by start time
        machine_schedules[machine].sort(key=lambda x: x[0])
        
        # Update job trackers
        job_last_completion[job_id] = end_time
        job_next_op_idx[job_id] += 1
        
        scheduled_ops[(job_id, op_idx)] = {
            'machine': machine,
            'start': start_time,
            'end': end_time,
            'duration': base_dur
        }
        
    # Calculate makespan
    makespan = max(job_last_completion.values()) if job_last_completion else 0.0
    
    # Calculate utilization
    machine_utilization = {}
    for m in machines:
        productive_time = 0.0
        for start, end, j_id, j_type in machine_schedules[m]:
            if j_id != -1:  # Not breakdown
                # Subtract setup if we want pure processing time, 
                # here we just count job duration (which includes no setup in itself, setup is just gap)
                productive_time += (end - start)
        machine_utilization[m] = round((productive_time / makespan * 100), 2) if makespan > 0 else 0.0
        
    avg_utilization = sum(machine_utilization.values()) / len(machines) if machines else 0.0
    bottleneck_machine = max(machine_utilization, key=machine_utilization.get) if machines else -1
    
    return {
        'makespan': round(makespan, 2),
        'machine_schedules': machine_schedules,
        'job_completion_times': job_last_completion,
        'machine_utilization': machine_utilization,
        'avg_utilization': round(avg_utilization, 2),
        'bottleneck_machine': bottleneck_machine,
        'scheduled_ops': scheduled_ops,
        'ops_sequence': list(ops_sequence),
        'machine_assignments': dict(machine_assignments)
    }

def solve_baseline_schedule(scenario, rule='FIFO'):
    """
    Solve the FJSP using a baseline priority rule:
    1. Determine operation priority sequence based on rule (FIFO or SPT).
    2. Assign each operation greedily to the eligible machine that can finish it earliest.
    """
    jobs = scenario['jobs']
    machines = scenario['machines']
    
    # Step 1: Set up sequencing
    # We will build the ops sequence and machine assignments iteratively
    # list of ready operations: (job_id, op_idx)
    ready_ops = []
    for j_id in jobs:
        ready_ops.append((j_id, 0))
        
    ops_sequence = []
    machine_assignments = {}
    
    # Temporary trackers for greedy assignment during resolution
    job_last_completion = {j_id: 0.0 for j_id in jobs}
    machine_schedules = {m: [] for m in machines}
    if 'active_breakdowns' in scenario:
        for m, duration in scenario['active_breakdowns'].items():
            machine_schedules[m].append((0.0, float(duration), -1, 'Breakdown'))
            
    while ready_ops:
        # Sort/select ready ops according to rule
        if rule == 'FIFO':
            # FIFO: select by job_id (first job first)
            selected_op = ready_ops.pop(0)
        elif rule == 'SPT':
            # SPT: select op with shortest minimum processing time across eligible machines
            def get_min_processing_time(op_tuple):
                j_id, o_idx = op_tuple
                eligible = jobs[j_id]['operations'][o_idx]['eligible_machines']
                return min(eligible.values()) if eligible else float('inf')
            
            ready_ops.sort(key=get_min_processing_time)
            selected_op = ready_ops.pop(0)
        else:
            selected_op = ready_ops.pop(0)
            
        job_id, op_idx = selected_op
        job = jobs[job_id]
        op = job['operations'][op_idx]
        
        # Greedy machine assignment: find the machine that finishes this op earliest
        best_machine = None
        best_finish = float('inf')
        best_start = float('inf')
        
        for m in op['eligible_machines']:
            dur = op['eligible_machines'][m]
            if dur == float('inf'):
                continue
            ready_time = job_last_completion[job_id]
            
            start = find_earliest_start(
                machine_schedules[m], 
                ready_time, 
                dur, 
                job['job_type'], 
                scenario['setup_matrix']
            )
            finish = start + dur
            if finish < best_finish:
                best_finish = finish
                best_start = start
                best_machine = m
                
        # Fallback if all eligible machines are down
        if best_machine is None:
            best_machine = list(op['eligible_machines'].keys())[0]
            dur = 1e4
            best_start = job_last_completion[job_id]
            best_finish = best_start + dur
                
        # Record assignment
        machine_assignments[(job_id, op_idx)] = best_machine
        ops_sequence.append(job_id)
        
        # Update temp trackers for the next decisions
        machine_schedules[best_machine].append((best_start, best_finish, job_id, job['job_type']))
        machine_schedules[best_machine].sort(key=lambda x: x[0])
        job_last_completion[job_id] = best_finish
        
        # Add next operation of this job to ready list if it exists
        if op_idx + 1 < len(job['operations']):
            ready_ops.append((job_id, op_idx + 1))
            
    # Evaluate final schedule
    return evaluate_schedule(ops_sequence, machine_assignments, scenario)

if __name__ == "__main__":
    from job_generator import generate_scheduling_problem
    
    scenario = generate_scheduling_problem(num_jobs=3, num_machines=2, seed=42)
    res = solve_baseline_schedule(scenario, rule='FIFO')
    print("Baseline makespan (FIFO):", res['makespan'])
    print("Baseline utilization (FIFO):", res['avg_utilization'])
