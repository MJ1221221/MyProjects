# Equilibrium of a Large-Deflection Beam in a Hemispherical Bowl

**Self-Project, Nov '25 – Dec '25**

Investigation of the equilibrium configuration of a slender elastic beam,
deformed under its own self-weight alone, resting inside a rigid
hemispherical bowl. The project studies how geometric parameters (beam
length vs. bowl radius, bending stiffness, weight per unit length) govern
whether the beam settles into a smooth, single-contact equilibrium or
buckles into one of several locally stable large-deflection shapes once it
contacts the bowl wall.

> Note on implementation: the original project plan used MATLAB for the
> numerical/FEM models. Per request, the full solver stack here is
> implemented in **C++** (no external numerical libraries — everything,
> including the dense linear solve, is hand-written). A small set of
> MATLAB/Octave scripts is still included under `scripts/` purely for
> post-processing and plotting the C++ solver's CSV output, to keep with
> the spirit of the original bullet ("MATLAB-based ... models").

---

## What was built

1. **A nonlinear large-deflection beam model** (discrete elastica: rigid
   links + torsional springs, i.e. the standard way to approximate an
   Euler–Bernoulli beam under large rotations) under self-weight.
2. **Two independent equilibrium solvers**, both minimizing total potential
   energy (bending + gravitational + bowl-contact penalty) via damped
   Newton–Raphson with load-stepping (continuation) for robustness:
   - `LumpedSolver` — coarse mesh ("numerical model").
   - `FEMSolver` — mesh refined 2× ("finite element model"), used as an
     independent cross-check via h-refinement.
3. **A batch driver** that sweeps **25 configurations** (length, bending
   stiffness, weight density, bowl radius) and writes a comparison table.
4. **Geometric stability analysis**: because the beam can buckle against
   the rigid bowl wall in more than one way once contact occurs, the two
   independently-discretized solvers were used as a sensitivity probe for
   *how stable* a given equilibrium is to discretization — see
   `docs/RESULTS.md`.

## Repository layout

```
beam_bowl_project/
├── CMakeLists.txt          # build (also buildable directly with g++, see below)
├── include/                # headers
│   ├── Vec2.hpp
│   ├── BeamConfig.hpp      # beam + bowl parameters, contact geometry
│   ├── LumpedSolver.hpp    # coarse-mesh Newton-Raphson solver
│   └── FEMSolver.hpp       # fine-mesh Newton-Raphson solver (h-refinement check)
├── src/
│   ├── LumpedSolver.cpp
│   ├── FEMSolver.cpp
│   └── main.cpp            # batch driver / CSV I/O
├── config/
│   └── configs.csv         # 25 beam-in-bowl configurations
├── results/
│   ├── results.csv         # summary table (generated)
│   └── shapes/             # per-configuration equilibrium shapes (generated)
├── scripts/
│   ├── generate_configs.py # builds config/configs.csv parameter sweep
│   ├── plot_results.m      # MATLAB/Octave: deviation + parameter-sweep plots
│   └── plot_shape.m        # MATLAB/Octave: plot one equilibrium shape vs bowl
└── docs/
    ├── THEORY.md            # beam model, energy functional, solver derivation
    └── RESULTS.md            # findings across the 25 configurations
```

## Building and running

```bash
# Build (no external dependencies beyond a C++17 compiler)
g++ -std=c++17 -O2 -Iinclude src/main.cpp src/LumpedSolver.cpp src/FEMSolver.cpp -o build/beam_in_bowl

# or, if CMake is available:
cmake -S . -B build && cmake --build build

# Run the full sweep (reads config/configs.csv, writes results/)
./build/beam_in_bowl config/configs.csv results
```

Each run prints progress per configuration and writes:
- `results/results.csv` — one row per configuration with both solvers'
  tip deflection, total potential energy, max wall-contact penetration,
  iteration counts/convergence, and the percentage deviation between the
  coarse and fine mesh.
- `results/shapes/<id>_lumped.csv`, `results/shapes/<id>_fem.csv` — (x, z)
  coordinates of the beam centerline at equilibrium, for plotting against
  the bowl outline.

See `docs/THEORY.md` for the model derivation and `docs/RESULTS.md` for
the discussion of the 25-configuration sweep.
