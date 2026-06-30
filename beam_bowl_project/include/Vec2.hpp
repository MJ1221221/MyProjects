// Vec2.hpp
// Minimal 2D vector utility used throughout the beam-in-bowl project.
#pragma once
#include <cmath>

struct Vec2 {
    double x = 0.0, z = 0.0;

    Vec2() = default;
    Vec2(double x_, double z_) : x(x_), z(z_) {}

    Vec2 operator+(const Vec2& o) const { return {x + o.x, z + o.z}; }
    Vec2 operator-(const Vec2& o) const { return {x - o.x, z - o.z}; }
    Vec2 operator*(double s) const { return {x * s, z * s}; }

    double norm() const { return std::sqrt(x * x + z * z); }
};
