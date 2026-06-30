"""
visualize.py

Plotting and visualization utilities for the Production Scheduling Optimizer:
    1. plot_gantt_comparison -- side-by-side Gantt charts showing Baseline vs SA schedules,
                                highlighting machine allocations, sequence setup times, and breakdowns.
    2. plot_convergence      -- plot SA's makespan convergence curve over iterations.
    3. plot_benchmark_summary-- plot a histogram of makespan improvements across scenarios.
"""

import os
import matplotlib.pyplot as plt

def plot_gantt(machine_schedules, title, save_path=None, ax=None):
    """
    Plot a single schedule Gantt chart.
    """
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(10, 6))

    # Define color palette for jobs
    colors = plt.get_cmap('tab20')
    
    # Machine labels
    machines = sorted(machine_schedules.keys())
    y_ticks = range(len(machines))
    ax.set_yticks(y_ticks)
    ax.set_yticklabels([f"Machine {m}" for m in machines])
    
    # Process blocks
    for m_idx, m in enumerate(machines):
        for start, end, j_id, j_type in machine_schedules[m]:
            dur = end - start
            if dur <= 0:
                continue
                
            if j_id == -1:
                # Machine breakdown
                ax.barh(m_idx, dur, left=start, color='#7f8c8d', edgecolor='black', 
                        hatch='//', alpha=0.7, align='center')
                # Label in center
                ax.text(start + dur/2, m_idx, "Downtime", ha='center', va='center', 
                        fontsize=8, color='white', fontweight='bold')
            else:
                # Normal operation
                color = colors(j_id % 20)
                ax.barh(m_idx, dur, left=start, color=color, edgecolor='black', 
                        alpha=0.85, align='center')
                # Add text label (Job ID)
                if dur > 1.5:
                    ax.text(start + dur/2, m_idx, f"J{j_id}", ha='center', va='center', 
                            fontsize=9, color='black', fontweight='semibold')

    ax.set_xlabel("Time (minutes)", fontsize=10)
    ax.set_ylabel("Workstations", fontsize=10)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.grid(axis='x', linestyle='--', alpha=0.5)

    if standalone:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.tight_layout()
        plt.savefig(save_path, dpi=150)
        plt.close(fig)
        print(f"Saved Gantt chart to: {save_path}")

def plot_gantt_comparison(baseline_schedule, sa_schedule, save_path):
    """
    Generate side-by-side Gantt charts comparing the baseline schedule
    and the Simulated Annealing optimized schedule.
    """
    fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    
    plot_gantt(
        baseline_schedule['machine_schedules'], 
        f"Baseline Schedule (FIFO) | Makespan: {baseline_schedule['makespan']} mins", 
        ax=axes[0]
    )
    
    plot_gantt(
        sa_schedule['machine_schedules'], 
        f"Optimized Schedule (Simulated Annealing) | Makespan: {sa_schedule['makespan']} mins", 
        ax=axes[1]
    )
    
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"Saved Gantt Comparison to: {save_path}")

def plot_convergence(history, save_path, title="Simulated Annealing Makespan Convergence"):
    """
    Plot SA's makespan progress over iterations.
    """
    iterations = [h[0] for h in history]
    current_costs = [h[1] for h in history]
    best_costs = [h[2] for h in history]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(iterations, current_costs, color='#a0d0a0', alpha=0.6,
            linewidth=1, label='Current candidate makespan')
    ax.plot(iterations, best_costs, color='#27ae60', linewidth=2.2,
            label='Best makespan found')
    
    ax.set_xlabel('Iteration', fontsize=10)
    ax.set_ylabel('Makespan (minutes)', fontsize=10)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"Saved convergence plot to: {save_path}")

def plot_benchmark_summary(results, save_path):
    """
    Plot the distribution of makespan improvements across scenarios.
    """
    improvements = [r['makespan_improvement_pct'] for r in results]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(improvements, bins=15, color='#16a085', alpha=0.85, edgecolor='white')
    mean_val = sum(improvements) / len(improvements)
    
    ax.axvline(mean_val, color='red', linestyle='--', linewidth=2,
               label=f'Mean Improvement = {mean_val:.2f}%')
    
    ax.set_xlabel('Makespan Reduction over Baseline (%)', fontsize=10)
    ax.set_ylabel('Number of Scenarios', fontsize=10)
    ax.set_title(f'Makespan Reduction Distribution across {len(results)} Test Scenarios', 
                 fontsize=12, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"Saved benchmark summary to: {save_path}")
