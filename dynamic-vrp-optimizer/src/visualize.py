"""
visualize.py

Plotting utilities for the project:
    1. plot_routes        -- draw a network with baseline vs SA routes overlaid,
                              so you can visually show "look, SA's routes are
                              tighter / less crossed-over than the baseline's."
    2. plot_convergence    -- SA cost-vs-iteration curve, the classic
                              "annealing converging" plot for a report/interview.
    3. plot_benchmark_summary -- distribution of improvement % across all
                              50 scenarios (histogram) -- shows the result
                              is consistent, not a one-off lucky run.

All plots are saved to the results/ directory as PNG files.
"""

import os
import matplotlib.pyplot as plt
import networkx as nx


def plot_routes(G, depot, routes, title, save_path, ax=None):
    """
    Draw the network graph with a set of vehicle routes overlaid in
    distinct colors, depot highlighted as a star.

    Args:
        G: networkx.Graph with 'pos' node attribute.
        depot: depot node id.
        routes: list of routes (each a list of node ids, depot included
                at start/end, as produced by baseline_solver / sa_optimizer).
        title: plot title.
        save_path: where to save the PNG (ignored if ax is provided, since
                   the caller is composing a multi-panel figure).
        ax: optional matplotlib Axes to draw into (for side-by-side comparisons).
    """
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(8, 8))

    pos = nx.get_node_attributes(G, 'pos')

    # Draw the full road network faintly in the background
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color='#dddddd', width=1)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color='#cccccc', node_size=40)

    # Overlay each vehicle's route in a distinct color
    colors = plt.get_cmap('tab10')
    for i, route in enumerate(routes):
        if len(route) < 2:
            continue
        route_edges = list(zip(route[:-1], route[1:]))
        color = colors(i % 10)
        nx.draw_networkx_edges(
            G, pos, edgelist=route_edges, ax=ax,
            edge_color=[color], width=2.5, alpha=0.85
        )
        customer_nodes = [n for n in route if n != depot]
        nx.draw_networkx_nodes(
            G, pos, nodelist=customer_nodes, ax=ax,
            node_color=[color], node_size=80, label=f'Vehicle {i+1}'
        )

    # Highlight the depot
    nx.draw_networkx_nodes(
        G, pos, nodelist=[depot], ax=ax,
        node_color='black', node_shape='*', node_size=300, label='Depot'
    )

    ax.set_title(title, fontsize=12)
    ax.legend(loc='upper right', fontsize=8)
    ax.axis('off')

    if standalone:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.tight_layout()
        plt.savefig(save_path, dpi=150)
        plt.close(fig)
        print(f"Saved: {save_path}")


def plot_routes_comparison(G, depot, baseline_routes, sa_routes, save_path):
    """
    Side-by-side comparison: baseline routing vs SA-optimized routing on
    the same network, so the visual difference in route quality is obvious.
    """
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    plot_routes(G, depot, baseline_routes, "Baseline (Nearest-Neighbor)", None, ax=axes[0])
    plot_routes(G, depot, sa_routes, "Simulated Annealing", None, ax=axes[1])
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {save_path}")


def plot_convergence(history, save_path, title="Simulated Annealing Convergence"):
    """
    Plot SA's current-solution-cost and best-solution-cost over iterations.

    Args:
        history: list of (iteration, current_cost, best_cost) tuples,
                 as returned by simulated_annealing().
        save_path: where to save the PNG.
    """
    iterations = [h[0] for h in history]
    current_costs = [h[1] for h in history]
    best_costs = [h[2] for h in history]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(iterations, current_costs, color='#a0a0d0', alpha=0.6,
            linewidth=1, label='Current solution cost')
    ax.plot(iterations, best_costs, color='#1f3a93', linewidth=2.2,
            label='Best solution found')
    ax.set_xlabel('Iteration')
    ax.set_ylabel('Total route cost')
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {save_path}")


def plot_benchmark_summary(results, save_path):
    """
    Histogram of per-scenario improvement percentages across the full
    benchmark, showing the distribution of gains (not just the average) --
    useful evidence that SA reliably beats the baseline rather than only
    winning on a few lucky scenarios.
    """
    improvements = [r['improvement_pct'] for r in results]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(improvements, bins=15, color='#2e7d32', alpha=0.8, edgecolor='white')
    mean_val = sum(improvements) / len(improvements)
    ax.axvline(mean_val, color='red', linestyle='--', linewidth=2,
               label=f'Mean = {mean_val:.1f}%')
    ax.set_xlabel('Improvement over baseline (%)')
    ax.set_ylabel('Number of scenarios')
    ax.set_title(f'SA Improvement Distribution Across {len(results)} Test Scenarios')
    ax.legend()
    ax.grid(alpha=0.3)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {save_path}")


if __name__ == "__main__":
    # Demo: generate one scenario, solve it both ways, and produce all
    # three plot types as a smoke test.
    from network_generator import generate_network
    from baseline_solver import solve_baseline_vrp
    from sa_optimizer import solve_sa_vrp

    G, depot, customers = generate_network(num_nodes=30, num_customers=8, seed=5)
    baseline = solve_baseline_vrp(G, depot, customers, num_vehicles=3)
    sa_result = solve_sa_vrp(
        G, depot, customers, num_vehicles=3,
        baseline_solution=baseline, cost_matrix=baseline['cost_matrix'], seed=5
    )

    out_dir = "/home/claude/dynamic-vrp-optimizer/results"
    plot_routes_comparison(G, depot, baseline['routes'], sa_result['routes'],
                            f"{out_dir}/demo_route_comparison.png")
    plot_convergence(sa_result['history'], f"{out_dir}/demo_convergence.png")
