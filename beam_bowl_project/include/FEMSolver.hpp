// FEMSolver.hpp
// Method 2 ("FEM model"): the beam is treated as a chain of constant-
// curvature beam finite elements. The same total potential energy
// functional (bending + gravity + bowl contact penalty) is minimized,
// but here with full Newton-Raphson iteration using a numerically
// assembled Hessian ("tangent stiffness matrix"), which is the standard
// nonlinear FEM equilibrium iteration. Used to independently verify the
// LumpedSolver (projected gradient descent) result.
#pragma once
#include "BeamConfig.hpp"
#include "LumpedSolver.hpp" // reuse EquilibriumResult
#include <vector>

class FEMSolver {
public:
    explicit FEMSolver(const BeamConfig& cfg);
    EquilibriumResult solve(int maxIters = 60, double tol = 1e-4);

private:
    BeamConfig cfg_;
    Bowl       bowl_;
    double     segLen_;
    double     k_;
    double     segMass_;
    mutable double loadFactor_ = 1.0;

    std::vector<Vec2> jointsFromAngles(const std::vector<double>& theta) const;
    double energy(const std::vector<double>& theta) const;
    std::vector<double> gradient(const std::vector<double>& theta) const;
    // Dense numerical Hessian (N x N, row-major).
    std::vector<double> hessian(const std::vector<double>& theta) const;

    // Solves H * dx = -g via Gaussian elimination with partial pivoting.
    std::vector<double> solveLinear(std::vector<double> H, std::vector<double> rhs, int n) const;
};
