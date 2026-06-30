// LumpedSolver.hpp
// Method 1 ("numerical model"): the beam is discretized into N rigid links
// of equal length connected by torsional springs (stiffness EI/l), under
// self-weight, resting inside a rigid hemispherical bowl. Equilibrium is
// found by minimizing total potential energy (bending + gravitational +
// contact penalty) with projected gradient descent + line search. This
// mirrors a classic "discrete elastica" large-deflection beam model.
#pragma once
#include "BeamConfig.hpp"
#include "Vec2.hpp"
#include <vector>

struct EquilibriumResult {
    std::vector<double> theta;     // segment orientation angles [rad]
    std::vector<Vec2>   joints;    // joint positions, joints.size() == N+1
    double totalEnergy   = 0.0;    // bending + gravitational PE at equilibrium [J]
    double tipDeflection = 0.0;    // |free end position - straight-line reference| [m]
    double maxPenetration= 0.0;    // worst residual contact violation [m]
    int    iterations    = 0;
    bool   converged      = false;
};

class LumpedSolver {
public:
    explicit LumpedSolver(const BeamConfig& cfg);

    // Runs the projected-gradient energy minimization and returns the
    // equilibrium configuration.
    EquilibriumResult solve(int maxIters = 60, double tol = 1e-4);

private:
    BeamConfig cfg_;
    Bowl       bowl_;
    double     segLen_;   // length of each rigid link
    double     k_;        // torsional spring stiffness per joint
    double     segMass_;  // weight (force) lumped at each joint
    mutable double loadFactor_ = 1.0; // continuation parameter, ramped 0->1

    // Forward-kinematics: angles -> joint positions.
    std::vector<Vec2> jointsFromAngles(const std::vector<double>& theta) const;

    // Total potential energy for a given angle set.
    double energy(const std::vector<double>& theta) const;

    // Numerical gradient of energy wrt each theta_i (central differences).
    std::vector<double> gradient(const std::vector<double>& theta) const;
};
