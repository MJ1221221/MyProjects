# Theory and Model Derivation

## 1. Physical setup

A slender elastic beam of natural length `L`, bending stiffness `EI`, and
self-weight per unit length `w`, is laid inside a rigid hemispherical bowl
of radius `R`. One end of the beam is pinned at the bowl rim
(`x = -R, z = 0`); the rest of the beam hangs/drapes under gravity and is
free to deform, subject only to:

- its own elastic bending resistance,
- gravity acting in `-z`,
- the rigid, frictionless constraint that no point of the beam may pass
  through the bowl wall (`x² + z² ≤ R²`, `z ≤ 0`) or above the open rim
  (`z ≤ 0`).

This is a classical **large-deflection (geometrically nonlinear) beam
problem with unilateral contact** — Euler–Bernoulli beam theory with small
strains but *large rotations*, which is why a linear beam-on-elastic-
foundation model is not adequate and a nonlinear formulation is required.

## 2. Discretization: the "discrete elastica"

The beam is discretized into `N` rigid links of equal length
`l = L / N`, connected end-to-end. The orientation of link `i` is the
angle `θᵢ` measured from the global x-axis. Joint positions follow by
forward kinematics:

```
p₀ = (-R, 0)
pᵢ₊₁ = pᵢ + l · (cos θᵢ, sin θᵢ)
```

Bending is represented by a torsional spring at each internal joint with
stiffness `k = EI / l` (this is the standard discrete approximation of
curvature energy `∫ (EI/2) κ² ds` for piecewise-linear centerlines, and
converges to the continuum Euler–Bernoulli energy as `N → ∞`):

```
U_bend = (k/2)(θ₀ - θ_ref)² + Σ_{i=1}^{N-1} (k/2)(θᵢ - θᵢ₋₁)²
```

`θ_ref = -π/4` is the natural (undeformed) orientation of the first
segment, representing the beam entering the bowl at a fixed initial
pinned angle.

## 3. Gravitational potential energy

Lumping each link's weight `m·g = w·l·g` at its outer joint:

```
U_grav = Σ_{i=1}^{N} (w · l · g) · z_i
```

## 4. Contact with the bowl wall

Rigid unilateral contact is enforced with a quadratic penalty (a standard
regularization used so that a smooth Newton method can be applied; the
penalty stiffness is chosen large enough that residual penetration is
negligible at equilibrium):

```
U_contact = Σ_i  (κ_p/2) · max(0, |pᵢ| - R)²  +  (κ_p/2) · max(0, zᵢ)²
```

The second term keeps the beam from rising above the open rim.

## 5. Equilibrium condition

Total potential energy:

```
Π(θ) = U_bend(θ) + U_grav(θ) + U_contact(θ)
```

Equilibrium configurations are stationary points of `Π`, i.e.
`∇Π(θ) = 0`, that are also local minima (stable equilibria). This is
solved numerically with **damped Newton–Raphson**:

```
θ_(n+1) = θ_n - α · H⁻¹ ∇Π(θ_n)
```

where `H` is the (numerically assembled) Hessian of `Π`, and `α` is
chosen by backtracking line search to guarantee energy descent at every
step (`Π(θ_(n+1)) < Π(θ_n)`).

### Load-stepping (continuation)

Because `U_contact` makes `Π` non-convex (a beam pressed against a rigid
wall can buckle into more than one locally stable shape), gravity is
introduced gradually via a load factor `λ ∈ [0, 1]`:

```
U_grav(θ; λ) = λ · Σ (w·l·g)·zᵢ
```

`λ` is stepped from 0 to 1 in increments, re-solving (warm-started from
the previous step) at each increment. This is the standard nonlinear-FEM
continuation technique for tracking a single equilibrium branch instead of
landing in an arbitrary local minimum on the first full-load solve.

## 6. Two independent discretizations (cross-validation)

- `LumpedSolver` uses `N` links as given in the configuration ("numerical
  model").
- `FEMSolver` independently re-discretizes the *same* beam with `2N`
  links ("finite element model"), and solves the identical energy
  functional and continuation schedule.

If both discretizations converge to the same physical equilibrium branch,
their predicted tip deflection and total potential energy should agree
to within mesh-discretization error, which shrinks with `N` — this is the
basis for the `<5%` deviation check reported in `docs/RESULTS.md`.

## 7. Why deviation is not uniformly small

Because `Π` is non-convex once the beam contacts the bowl wall, the two
meshes do **not** always converge to the same local minimum even when
following the same load-stepping schedule — small numerical differences
between a coarse and a 2× finer mesh can be enough to fall into different
buckled branches. This is a real mechanical effect (bifurcation /
multistability), not purely a numerical artifact, and is itself the
"geometric constraints affecting beam stability" referenced in the
project goals — see `docs/RESULTS.md` for the breakdown of which
configurations are sensitive to this and which are not.
