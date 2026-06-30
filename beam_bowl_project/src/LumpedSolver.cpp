// LumpedSolver.cpp
// Method 1 ("numerical model"): coarse-mesh discrete elastica solved with
// damped Newton-Raphson energy minimization (bending + gravity + bowl
// contact penalty). See FEMSolver.cpp for the fine-mesh counterpart used
// as an independent mesh-refinement cross-check.
#define _USE_MATH_DEFINES
#include "LumpedSolver.hpp"
#include <cmath>
#include <algorithm>
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static constexpr double GRAV = 9.81;

LumpedSolver::LumpedSolver(const BeamConfig& cfg)
    : cfg_(cfg), bowl_(cfg.R) {
    segLen_  = cfg_.L / cfg_.N;
    k_       = cfg_.EI / segLen_;
    segMass_ = cfg_.w * segLen_;
}

std::vector<Vec2> LumpedSolver::jointsFromAngles(const std::vector<double>& theta) const {
    std::vector<Vec2> joints(cfg_.N + 1);
    joints[0] = Vec2(-cfg_.R + 1e-6, 0.0);
    for (int i = 0; i < cfg_.N; ++i) {
        Vec2 dir(std::cos(theta[i]), std::sin(theta[i]));
        joints[i + 1] = joints[i] + dir * segLen_;
    }
    return joints;
}

double LumpedSolver::energy(const std::vector<double>& theta) const {
    auto joints = jointsFromAngles(theta);
    double E = 0.0;
    const double theta0Ref = -M_PI / 4.0;
    E += 0.5 * k_ * (theta[0] - theta0Ref) * (theta[0] - theta0Ref);
    for (int i = 1; i < cfg_.N; ++i) {
        double d = theta[i] - theta[i - 1];
        E += 0.5 * k_ * d * d;
    }
    for (int i = 1; i <= cfg_.N; ++i) {
        E += loadFactor_ * segMass_ * GRAV * joints[i].z;
    }
    for (int i = 1; i <= cfg_.N; ++i) {
        double pen = bowl_.penetration(joints[i]);
        if (pen > 0.0) E += 0.5 * cfg_.penalty * pen * pen;
        if (joints[i].z > 0.0) E += 0.5 * cfg_.penalty * joints[i].z * joints[i].z;
    }
    return E;
}

std::vector<double> LumpedSolver::gradient(const std::vector<double>& theta) const {
    std::vector<double> g(cfg_.N, 0.0);
    const double h = 1e-6;
    std::vector<double> t = theta;
    for (int i = 0; i < cfg_.N; ++i) {
        double orig = t[i];
        t[i] = orig + h; double Ep = energy(t);
        t[i] = orig - h; double Em = energy(t);
        t[i] = orig;
        g[i] = (Ep - Em) / (2.0 * h);
    }
    return g;
}

EquilibriumResult LumpedSolver::solve(int maxIters, double tol) {
    int n = cfg_.N;
    std::vector<double> theta(n, -M_PI / 4.0);

    auto hessian = [&](const std::vector<double>& th) {
        std::vector<double> H(n * n, 0.0);
        const double h = 1e-4;
        std::vector<double> t = th;
        for (int i = 0; i < n; ++i) {
            for (int j = i; j < n; ++j) {
                double oi = t[i], oj = t[j];
                t[i] = oi + h; t[j] = oj + h; double Epp = energy(t);
                t[i] = oi + h; t[j] = oj - h; double Epm = energy(t);
                t[i] = oi - h; t[j] = oj + h; double Emp = energy(t);
                t[i] = oi - h; t[j] = oj - h; double Emm = energy(t);
                t[i] = oi; t[j] = oj;
                double val = (Epp - Epm - Emp + Emm) / (4.0 * h * h);
                H[i * n + j] = val; H[j * n + i] = val;
            }
        }
        return H;
    };

    auto solveLinear = [&](std::vector<double> H, std::vector<double> rhs) {
        for (int i = 0; i < n; ++i) H[i * n + i] += 1e-8;
        for (int col = 0; col < n; ++col) {
            int piv = col; double best = std::fabs(H[col * n + col]);
            for (int row = col + 1; row < n; ++row) {
                double v = std::fabs(H[row * n + col]);
                if (v > best) { best = v; piv = row; }
            }
            if (piv != col) {
                for (int c = 0; c < n; ++c) std::swap(H[col * n + c], H[piv * n + c]);
                std::swap(rhs[col], rhs[piv]);
            }
            double diag = H[col * n + col];
            if (std::fabs(diag) < 1e-14) continue;
            for (int row = col + 1; row < n; ++row) {
                double factor = H[row * n + col] / diag;
                if (factor == 0.0) continue;
                for (int c = col; c < n; ++c) H[row * n + c] -= factor * H[col * n + c];
                rhs[row] -= factor * rhs[col];
            }
        }
        std::vector<double> x(n, 0.0);
        for (int row = n - 1; row >= 0; --row) {
            double sum = rhs[row];
            for (int c = row + 1; c < n; ++c) sum -= H[row * n + c] * x[c];
            double diag = H[row * n + row];
            x[row] = (std::fabs(diag) > 1e-14) ? sum / diag : 0.0;
        }
        return x;
    };

    int it = 0;
    bool converged = false;
    double E = energy(theta);

    auto newtonStep = [&](int iters, double thisTol) {
        for (it = 0; it < iters; ++it) {
            auto grad = gradient(theta);
            double gnorm = 0.0;
            for (double v : grad) gnorm += v * v;
            gnorm = std::sqrt(gnorm);
            if (gnorm < thisTol) { converged = true; return; }
            converged = false;

            auto H = hessian(theta);
            std::vector<double> rhs(n);
            for (int i = 0; i < n; ++i) rhs[i] = -grad[i];
            auto dx = solveLinear(H, rhs);

            double alpha = 1.0;
            std::vector<double> trial(n);
            double trialE = E;
            for (int ls = 0; ls < 30; ++ls) {
                for (int i = 0; i < n; ++i) trial[i] = theta[i] + alpha * dx[i];
                trialE = energy(trial);
                if (trialE < E) break;
                alpha *= 0.5;
            }
            theta = trial;
            E = trialE;
        }
    };

    // Continuation: ramp gravity from 0 to full load in steps, warm-starting
    // each step from the previous converged shape. This keeps the solver on
    // a single physical equilibrium branch instead of jumping between the
    // multiple local minima created by the rigid bowl-wall contact.
    const int loadSteps = 8;
    for (int s = 1; s <= loadSteps; ++s) {
        loadFactor_ = static_cast<double>(s) / loadSteps;
        E = energy(theta);
        newtonStep(20, 1e-4);
    }
    // Final polish at full load with tighter tolerance.
    loadFactor_ = 1.0;
    E = energy(theta);
    newtonStep(maxIters, tol);

    EquilibriumResult res;
    res.theta = theta;
    res.joints = jointsFromAngles(theta);
    res.totalEnergy = E;
    res.iterations = it;
    res.converged = converged;

    Vec2 straightTip = res.joints.front() + Vec2(cfg_.L, 0.0);
    res.tipDeflection = (res.joints.back() - straightTip).norm();

    double maxPen = 0.0;
    for (size_t i = 1; i < res.joints.size(); ++i) {
        maxPen = std::max(maxPen, bowl_.penetration(res.joints[i]));
    }
    res.maxPenetration = maxPen;

    return res;
}
