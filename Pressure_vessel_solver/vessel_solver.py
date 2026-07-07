"""
Computational Design Solver for a Cylindrical Pressure Vessel Under Thermal Loading
=====================================================================================
Modules:
1. Thermodynamic sizing (energy balance) - Engineering Thermodynamics / Energy Systems
2. Transient heating response (ODE, lumped capacitance) - MTL Diff. Equations
3. Structural design (thin-wall pressure vessel stress) - Solid Mechanics
4. Statistical sensitivity analysis - MTL Statistics
"""

import numpy as np
from scipy.integrate import solve_ivp
from scipy import stats
import matplotlib.pyplot as plt

# =====================================================================
# DESIGN INPUTS (a realistic industrial thermal-storage vessel scenario)
# =====================================================================
# Fluid: water-based thermal storage tank (e.g. small industrial hot-water
# thermal energy storage vessel, heated by an electric/process heat source)

rho_f   = 1000.0      # fluid density, kg/m^3 (water)
cp_f    = 4186.0       # specific heat, J/(kg.K)

# Vessel geometry
r_i     = 0.30         # internal radius, m (600 mm ID tank)
L       = 1.2          # cylindrical length, m
V       = np.pi * r_i**2 * L   # internal volume, m^3
m_f     = rho_f * V             # fluid mass, kg

# Thermal operating conditions
T_amb   = 25.0          # ambient temp, C
T_i     = 25.0          # initial fluid temp, C
T_target = 90.0         # target/operating temp, C  (process hot-water requirement)
Q_in    = 6000.0        # heater input power, W  (6 kW industrial immersion heater)
U       = 25.0          # overall heat loss coefficient, W/(m^2.K) (lightly-lagged tank, natural convection + conduction through light insulation)
A_surf  = 2*np.pi*r_i*L + 2*np.pi*r_i**2   # external surface area, m^2 (cylinder + 2 end caps)

# Pressure / structural design conditions
P_design = 6.0e5        # internal design pressure, Pa (6 bar gauge, incl. safety margin over operating)
material = "SA-516 Gr.70 (carbon steel plate, common pressure-vessel steel)"
sigma_allow = 138e6      # allowable stress, Pa (typical ASME allowable for SA-516-70 at design temp)
FOS_target = 3.5         # target overall factor of safety on burst

print("="*70)
print("MODULE 1: THERMODYNAMIC SIZING (Energy Balance)")
print("="*70)
print(f"Internal radius        : {r_i*1000:.0f} mm")
print(f"Length                 : {L*1000:.0f} mm")
print(f"Internal volume        : {V*1000:.2f} L")
print(f"Fluid mass              : {m_f:.2f} kg")

# Energy required to raise fluid from T_i to T_target (ignoring losses, ideal case)
E_ideal = m_f * cp_f * (T_target - T_i)   # Joules
t_ideal = E_ideal / Q_in                    # seconds, if no losses
print(f"\nIdeal energy required to heat fluid {T_i:.0f}C -> {T_target:.0f}C : {E_ideal/1e6:.3f} MJ")
print(f"Ideal heating time (no losses, Q_in={Q_in:.0f} W)        : {t_ideal/60:.2f} min")

print("\n" + "="*70)
print("MODULE 2: TRANSIENT HEATING RESPONSE (Lumped Capacitance ODE)")
print("="*70)

# Lumped capacitance energy balance:
# m*cp * dT/dt = Q_in - U*A_surf*(T - T_amb)
def dTdt(t, T, Q, U, A, Tamb, m, cp):
    return (Q - U*A*(T[0] - Tamb)) / (m*cp)

t_span = (0, 24*3600)  # simulate up to 24 hours (>= 3 time-constants, enough to settle)
t_eval = np.linspace(*t_span, 6000)

sol = solve_ivp(dTdt, t_span, [T_i], t_eval=t_eval, args=(Q_in, U, A_surf, T_amb, m_f, cp_f), rtol=1e-8, atol=1e-8)

T_curve = sol.y[0]
t_curve = sol.t

# Steady-state temperature (as t -> infinity, dT/dt = 0)
T_ss = T_amb + Q_in/(U*A_surf)
print(f"External surface area           : {A_surf:.3f} m^2")
print(f"Steady-state (max achievable) temp: {T_ss:.2f} C")

# Time to reach target temperature (90C) if achievable
if T_ss > T_target:
    mask = T_curve >= T_target
    if np.any(mask):
        idx = np.argmax(mask)
        t_reach = t_curve[idx]
        print(f"Time to reach target {T_target:.0f}C          : {t_reach/60:.2f} min ({t_reach/3600:.3f} hr)")
    else:
        t_reach = None
        print(f"Target {T_target:.0f}C NOT reached within simulated window ({t_span[1]/3600:.1f} hr) -- extend t_span.")
else:
    t_reach = None
    print(f"NOTE: Steady-state temp {T_ss:.2f}C is BELOW target {T_target:.0f}C -> heater cannot reach target with these losses.")

# Time to reach 95% of steady-state (standard settling metric)
T_95 = T_amb + 0.95*(T_ss - T_amb)
mask95 = T_curve >= T_95
if np.any(mask95):
    idx_95 = np.argmax(mask95)
    t_95 = t_curve[idx_95]
    print(f"Time to reach 95% of steady-state ({T_95:.2f}C) : {t_95/60:.2f} min ({t_95/3600:.3f} hr)")
else:
    t_95 = None
    print(f"95% settling NOT reached within simulated window -- extend t_span.")

# Analytical solution check (first-order linear ODE has closed form)
tau = m_f*cp_f/(U*A_surf)   # time constant
T_analytical = T_ss - (T_ss - T_i)*np.exp(-t_curve/tau)
max_err = np.max(np.abs(T_analytical - T_curve))
print(f"Time constant (tau)              : {tau/60:.2f} min")
print(f"Max deviation, numerical vs analytical closed-form: {max_err:.2e} C  (validates solver)")

print("\n" + "="*70)
print("MODULE 3: STRUCTURAL DESIGN (Thin-Wall Pressure Vessel Stress)")
print("="*70)

# Thin-wall cylinder assumption valid when r_i/t > 10
# Hoop (circumferential) stress:  sigma_h = P*r_i / t
# Longitudinal (axial) stress:    sigma_l = P*r_i / (2*t)
# Design thickness from allowable stress with FOS:
#   sigma_allow_design = sigma_allow / FOS
#   t_required = P_design * r_i * FOS / sigma_allow   (governed by hoop stress, the larger of the two)

sigma_design = sigma_allow / FOS_target
t_required = P_design * r_i / sigma_design    # from hoop stress eqn, solved for t
thinwall_check = r_i / t_required

print(f"Material                          : {material}")
print(f"ASME allowable stress (sigma_allow): {sigma_allow/1e6:.1f} MPa")
print(f"Target factor of safety            : {FOS_target}")
print(f"Design (working) stress limit      : {sigma_design/1e6:.2f} MPa")
print(f"Design pressure                    : {P_design/1e5:.1f} bar")
print(f"Required wall thickness (hoop-governed): {t_required*1000:.2f} mm")
print(f"Thin-wall validity check (r_i/t)   : {thinwall_check:.1f}  (>10 => thin-wall theory valid: {thinwall_check>10})")

# Round to a standard commercial plate thickness (next available up)
standard_plates_mm = [4, 5, 6, 8, 10, 12, 14, 16, 20, 25]
t_selected_mm = next(p for p in standard_plates_mm if p >= t_required*1000)
t_selected = t_selected_mm/1000

sigma_h_actual = P_design*r_i/t_selected
sigma_l_actual = P_design*r_i/(2*t_selected)
FOS_actual = sigma_allow/sigma_h_actual

print(f"\nSelected standard plate thickness   : {t_selected_mm} mm")
print(f"Resulting hoop stress               : {sigma_h_actual/1e6:.2f} MPa")
print(f"Resulting longitudinal stress        : {sigma_l_actual/1e6:.2f} MPa")
print(f"Resulting actual factor of safety     : {FOS_actual:.2f}")

print("\n" + "="*70)
print("MODULE 4: STATISTICAL SENSITIVITY ANALYSIS")
print("="*70)

# Parametric sweep: vary design pressure and thickness across realistic
# manufacturing/operating ranges, compute resulting FOS, then use linear
# regression (Intro to Statistics) to quantify sensitivity, plus a
# confidence interval on FOS at the selected design point using
# thickness-tolerance-driven variability (standard plate tolerance +/-0.3mm)

np.random.seed(42)
n_samples = 500

# Standard plate thickness tolerance (typical commercial rolling tolerance)
t_tol_mm = 0.3
t_samples_mm = np.random.uniform(t_selected_mm - t_tol_mm, t_selected_mm + t_tol_mm, n_samples)
t_samples = t_samples_mm/1000

# Operating pressure also has some variability (relief valve deadband, +/-0.2 bar)
P_tol = 0.2e5
P_samples = np.random.uniform(P_design - P_tol, P_design + P_tol, n_samples)

FOS_samples = sigma_allow / (P_samples * r_i / t_samples)

mean_FOS = np.mean(FOS_samples)
std_FOS = np.std(FOS_samples, ddof=1)
# 95% confidence interval on the mean FOS (t-distribution, since we're
# estimating population mean from a sample -- standard Stats-course approach)
conf = 0.95
t_crit = stats.t.ppf((1+conf)/2, df=n_samples-1)
margin = t_crit * std_FOS/np.sqrt(n_samples)
ci_low, ci_high = mean_FOS-margin, mean_FOS+margin

print(f"Sweep sample size                  : {n_samples}")
print(f"Plate thickness range               : {t_selected_mm-t_tol_mm:.2f} - {t_selected_mm+t_tol_mm:.2f} mm")
print(f"Design pressure range                : {(P_design-P_tol)/1e5:.2f} - {(P_design+P_tol)/1e5:.2f} bar")
print(f"Mean FOS across sweep                : {mean_FOS:.3f}")
print(f"Std. dev. of FOS                     : {std_FOS:.3f}")
print(f"95% Confidence Interval on mean FOS   : [{ci_low:.3f}, {ci_high:.3f}]")
print(f"Minimum FOS observed in sweep (worst-case combination): {FOS_samples.min():.3f}")

# Linear regression: FOS vs thickness (holding pressure effect noted separately)
slope, intercept, r_value, p_value, std_err = stats.linregress(t_samples_mm, FOS_samples)
print(f"\nLinear regression: FOS vs thickness")
print(f"  slope     : {slope:.3f} FOS-units per mm")
print(f"  intercept : {intercept:.3f}")
print(f"  R^2       : {r_value**2:.4f}")

# =====================================================================
# PLOTS
# =====================================================================
fig, axes = plt.subplots(2, 2, figsize=(13, 9))

# Plot 1: Transient heating curve
ax = axes[0,0]
ax.plot(t_curve/3600, T_curve, color='#c0392b', lw=2, label='Numerical (solve_ivp)')
ax.plot(t_curve/3600, T_analytical, '--', color='#2c3e50', lw=1.2, label='Analytical closed-form')
ax.axhline(T_target, color='gray', ls=':', label=f'Target {T_target:.0f} C')
ax.axhline(T_ss, color='green', ls=':', label=f'Steady-state {T_ss:.1f} C')
if t_reach: ax.axvline(t_reach/3600, color='orange', ls='--', alpha=0.6)
ax.set_xlabel('Time (hr)'); ax.set_ylabel('Fluid Temperature (C)')
ax.set_title('Transient Heating Response (Lumped Capacitance)')
ax.legend(fontsize=8); ax.grid(alpha=0.3)

# Plot 2: Stress vs thickness
t_range_mm = np.linspace(3, 12, 100)
sigma_h_range = P_design*r_i/(t_range_mm/1000)/1e6
ax = axes[0,1]
ax.plot(t_range_mm, sigma_h_range, color='#2980b9', lw=2, label='Hoop stress')
ax.axhline(sigma_allow/1e6, color='red', ls='--', label=f'Allowable stress {sigma_allow/1e6:.0f} MPa')
ax.axvline(t_selected_mm, color='green', ls=':', label=f'Selected t = {t_selected_mm} mm')
ax.set_xlabel('Wall thickness (mm)'); ax.set_ylabel('Hoop stress (MPa)')
ax.set_title('Structural Design: Stress vs Wall Thickness')
ax.legend(fontsize=8); ax.grid(alpha=0.3)

# Plot 3: FOS sensitivity sweep scatter
ax = axes[1,0]
sc = ax.scatter(t_samples_mm, FOS_samples, c=P_samples/1e5, cmap='viridis', s=12, alpha=0.6)
ax.plot(t_range_mm, slope*t_range_mm+intercept, 'r-', lw=2, label='Linear fit')
ax.axhline(FOS_target, color='gray', ls='--', label=f'Target FOS {FOS_target}')
cbar = plt.colorbar(sc, ax=ax); cbar.set_label('Pressure (bar)')
ax.set_xlabel('Wall thickness (mm)'); ax.set_ylabel('Factor of Safety')
ax.set_title('Statistical Sensitivity: FOS vs Thickness & Pressure')
ax.legend(fontsize=8); ax.grid(alpha=0.3)

# Plot 4: FOS distribution histogram
ax = axes[1,1]
ax.hist(FOS_samples, bins=30, color='#8e44ad', alpha=0.7, edgecolor='white')
ax.axvline(mean_FOS, color='black', lw=2, label=f'Mean = {mean_FOS:.2f}')
ax.axvline(ci_low, color='red', ls='--', label=f'95% CI [{ci_low:.2f}, {ci_high:.2f}]')
ax.axvline(ci_high, color='red', ls='--')
ax.set_xlabel('Factor of Safety'); ax.set_ylabel('Frequency')
ax.set_title('FOS Distribution Under Manufacturing/Operating Tolerance')
ax.legend(fontsize=8); ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('/home/claude/vessel_project/vessel_analysis.png', dpi=150)
print("\nPlots saved.")
