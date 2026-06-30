// BeamConfig.hpp
// Defines the physical parameters of one beam-in-bowl configuration and
// the hemispherical bowl geometry/contact helper used by both solvers.
#pragma once
#include "Vec2.hpp"
#include <string>

struct BeamConfig {
    std::string id;        // configuration label, e.g. "C01"
    double L      = 0.30;  // beam natural (undeformed) length            [m]
    double EI     = 0.05;  // bending stiffness (Young's modulus * I)     [N*m^2]
    double w      = 0.40;  // self-weight per unit length                 [N/m]
    double R      = 0.12;  // hemispherical bowl radius                   [m]
    int    N      = 40;    // number of discretization segments
    double penalty= 5.0e3; // contact penalty stiffness for bowl wall
};

// Hemispherical bowl: rim at z = 0 (x-z plane, gravity acts along -z),
// bowl interior is the region x^2 + z^2 <= R^2 with z <= 0 (open side up).
struct Bowl {
    double R;
    explicit Bowl(double R_) : R(R_) {}

    // Signed penetration depth: positive when the point lies OUTSIDE the
    // bowl wall (i.e. has been pushed through the shell) or above the rim.
    double penetration(const Vec2& p) const {
        double r = p.norm();
        return r - R; // > 0 means outside the spherical shell radius R
    }

    // Project a point back onto/inside the bowl surface (used for the
    // projected-gradient contact handling in the lumped solver).
    Vec2 project(const Vec2& p) const {
        double r = p.norm();
        if (r <= R || r < 1e-12) return p;
        return p * (R / r);
    }
};
