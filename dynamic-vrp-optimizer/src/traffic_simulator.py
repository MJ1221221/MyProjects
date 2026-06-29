"""
traffic_simulator.py

This module makes the network 'dynamic'. A plain VRP solver runs once on
fixed edge weights; we instead simulate traffic conditions that change
over time, so any solver must adapt rather than relying on a single static
shortest-path computation.

Two effects are modeled:
    1. Congestion multipliers: random per-edge slowdowns that vary over
       time (representing rush-hour traffic, accidents, etc.)
    2. Road closures: a small probability that an edge becomes temporarily
       unusable (representing accidents, construction, flooding, etc.)

The simulator exposes a `get_current_weight(u, v)` style snapshot so the
solvers can query "what does this edge cost RIGHT NOW" without needing to
know how the dynamics are generated internally.
"""

import random
import copy


class TrafficSimulator:
    """
    Wraps a base graph and produces time-varying edge weights.

    Usage:
        sim = TrafficSimulator(G, seed=42)
        sim.step()                      # advance simulated time by one tick
        live_graph = sim.get_live_graph()   # graph with CURRENT weights
    """

    def __init__(self, G, seed: int = None,
                 congestion_std: float = 0.25,
                 closure_prob: float = 0.02,
                 closure_duration_range=(2, 5)):
        """
        Args:
            G: base networkx.Graph with 'weight' = free-flow travel time.
            seed: RNG seed for reproducibility.
            congestion_std: standard deviation of the lognormal congestion
                             multiplier applied to each edge each tick.
                             Higher = more volatile traffic.
            closure_prob: probability per tick that a *new* closure starts
                          on any given edge.
            closure_duration_range: (min, max) ticks a closure lasts.
        """
        self.base_graph = G
        self.rng = random.Random(seed)
        self.congestion_std = congestion_std
        self.closure_prob = closure_prob
        self.closure_duration_range = closure_duration_range

        self.time = 0
        # active_closures: {(u, v): ticks_remaining}
        self.active_closures = {}
        # current multiplier per edge, persisted so changes are gradual
        # rather than fully re-randomized every tick (more realistic)
        self.multipliers = {edge: 1.0 for edge in G.edges()}

    def step(self):
        """Advance the simulated clock by one tick, updating traffic state."""
        self.time += 1

        # Update congestion multipliers with a mean-reverting random walk,
        # so congestion drifts smoothly instead of jumping randomly each
        # tick (closer to how real traffic builds and clears)
        for edge in self.multipliers:
            current = self.multipliers[edge]
            shock = self.rng.gauss(0, self.congestion_std)
            # pull back toward 1.0 (free-flow) while applying the shock
            new_value = 0.8 * current + 0.2 * 1.0 + shock
            self.multipliers[edge] = max(0.6, min(new_value, 4.0))

        # Decrement existing closures, removing expired ones
        expired = []
        for edge, ticks_left in self.active_closures.items():
            self.active_closures[edge] = ticks_left - 1
            if self.active_closures[edge] <= 0:
                expired.append(edge)
        for edge in expired:
            del self.active_closures[edge]

        # Possibly start new closures
        for edge in self.base_graph.edges():
            if edge in self.active_closures:
                continue
            if self.rng.random() < self.closure_prob:
                duration = self.rng.randint(*self.closure_duration_range)
                self.active_closures[edge] = duration

    def get_live_weight(self, u, v):
        """
        Return the current travel time for edge (u, v), or None if the
        edge is closed right now.
        """
        edge = (u, v) if (u, v) in self.multipliers else (v, u)
        if edge in self.active_closures:
            return None  # closed
        base_weight = self.base_graph[u][v]['weight']
        return base_weight * self.multipliers.get(edge, 1.0)

    def get_live_graph(self):
        """
        Return a snapshot networkx.Graph reflecting current traffic
        conditions: closed edges are removed, open edges get their
        congestion-adjusted weight.
        """
        live = copy.deepcopy(self.base_graph)
        edges_to_remove = []

        for u, v in live.edges():
            live_weight = self.get_live_weight(u, v)
            if live_weight is None:
                edges_to_remove.append((u, v))
            else:
                live[u][v]['weight'] = live_weight

        live.remove_edges_from(edges_to_remove)
        return live

    def reset(self):
        """Reset simulator to its initial (free-flow) state."""
        self.time = 0
        self.active_closures = {}
        self.multipliers = {edge: 1.0 for edge in self.base_graph.edges()}


if __name__ == "__main__":
    # Quick smoke test
    from network_generator import generate_network

    G, depot, customers = generate_network(num_nodes=20, num_customers=6, seed=42)
    sim = TrafficSimulator(G, seed=1)

    for t in range(5):
        sim.step()
        live = sim.get_live_graph()
        print(f"Tick {t+1}: {live.number_of_edges()} edges open "
              f"(of {G.number_of_edges()} total), "
              f"{len(sim.active_closures)} closures active")
