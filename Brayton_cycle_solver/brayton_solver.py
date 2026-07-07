"""
Computational Performance Simulator for a Regenerative Brayton Power Cycle
=============================================================================
Modules:
1. Cycle thermodynamic model (air-standard, cold-air assumption) - Thermodynamics/Energy Systems
2. Parametric sweep over pressure ratio & turbine inlet temp - Coding/Energy Systems
3. Regenerator effectiveness study - Energy Systems
4. Statistical sensitivity analysis on efficiency - Statistics
"""

import numpy as np
from scipy.optimize import minimize_scalar
from scipy import stats
import matplotlib.pyplot as plt

# =====================================================================
# AIR-STANDARD ASSUMPTIONS (cold-air standard, constant properties)
# =====================================================================
gamma = 1.4
cp = 1005.0          # J/(kg.K)
R_air = 287.0        # J/(kg.K)

# =====================================================================
# DESIGN INPUTS - representative small industrial regenerative gas turbine
# =====================================================================
T1 = 300.0           # compressor inlet temp, K (~27C ambient)
P1 = 101325.0        # compressor inlet pressure, Pa (1 atm)
T4 = 1400.0          # turbine inlet temp (TIT), K -- representative modern industrial GT
eta_c = 0.85         # compressor isentropic efficiency
eta_t = 0.88         # turbine isentropic efficiency
epsilon_regen = 0.75 # regenerator effectiveness
LHV_fuel = 43.0e6    # lower heating value of natural-gas-like fuel, J/kg

def cycle_state(rp, T1=T1, T4=T4, eta_c=eta_c, eta_t=eta_t, epsilon=epsilon_regen):
    """
    Computes the regenerative Brayton cycle state points and performance
    metrics for a given pressure ratio rp = P2/P1.
    Returns dict with T2, T3, T5, T6, w_c, w_t, w_net, q_in, eta_thermal, bwr
    """
    exp = (gamma-1)/gamma

    # 1->2: Compressor (isentropic then corrected by efficiency)
    T2s = T1 * rp**exp
    T2  = T1 + (T2s - T1)/eta_c

    # 4->5: Turbine (isentropic then corrected by efficiency)
    T5s = T4 / rp**exp
    T5  = T4 - eta_t*(T4 - T5s)

    # Regenerator: preheats compressed air (2->3) using turbine exhaust (5->6)
    # energy balance for equal mass flow & cp on both sides:
    T3 = T2 + epsilon*(T5 - T2)
    T6 = T5 - epsilon*(T5 - T2)

    w_c = cp*(T2 - T1)          # specific compressor work, J/kg
    w_t = cp*(T4 - T5)          # specific turbine work, J/kg
    w_net = w_t - w_c
    q_in = cp*(T4 - T3)         # heat added in combustor (after regeneration)

    eta_thermal = w_net/q_in if q_in > 0 else np.nan
    bwr = w_c/w_t               # back-work ratio

    return dict(rp=rp, T2=T2, T3=T3, T5=T5, T6=T6,
                w_c=w_c, w_t=w_t, w_net=w_net, q_in=q_in,
                eta=eta_thermal, bwr=bwr)

if __name__ == "__main__":
    print("="*72)
    print("MODULE 1: CYCLE THERMODYNAMIC MODEL - BASELINE DESIGN POINT")
    print("="*72)
    baseline = cycle_state(rp=8.0)
    for k, v in baseline.items():
        print(f"  {k:8s}: {v:.4f}")

    print("\n" + "="*72)
    print("MODULE 2: PARAMETRIC SWEEP - PRESSURE RATIO & TURBINE INLET TEMP")
    print("="*72)

    rp_range = np.linspace(2, 25, 200)
    TIT_values = [1200, 1300, 1400, 1500]  # K, representing different turbine material/cooling limits

    sweep_results = {}
    for TIT in TIT_values:
        etas, w_nets, bwrs = [], [], []
        for rp in rp_range:
            s = cycle_state(rp, T4=TIT)
            etas.append(s['eta'])
            w_nets.append(s['w_net'])
            bwrs.append(s['bwr'])
        sweep_results[TIT] = dict(eta=np.array(etas), w_net=np.array(w_nets), bwr=np.array(bwrs))

    # Find optimum rp for max efficiency and max specific work, for the design TIT=1400K
    def neg_eta(rp): return -cycle_state(rp, T4=T4)['eta']
    def neg_wnet(rp): return -cycle_state(rp, T4=T4)['w_net']

    res_eta = minimize_scalar(neg_eta, bounds=(2, 30), method='bounded')
    res_wnet = minimize_scalar(neg_wnet, bounds=(2, 30), method='bounded')

    rp_opt_eta = res_eta.x
    eta_max = -res_eta.fun
    rp_opt_wnet = res_wnet.x
    wnet_max = -res_wnet.fun

    print(f"Design TIT = {T4:.0f} K")
    print(f"Optimum pressure ratio for MAX EFFICIENCY : rp = {rp_opt_eta:.2f}  -> eta = {eta_max*100:.2f}%")
    print(f"Optimum pressure ratio for MAX SPECIFIC WORK: rp = {rp_opt_wnet:.2f}  -> w_net = {wnet_max/1000:.2f} kJ/kg")

    # Baseline (rp=8) vs optimum-efficiency comparison
    s_base = cycle_state(8.0)
    s_opt  = cycle_state(rp_opt_eta)
    print(f"\nComparison: baseline rp=8 -> eta={s_base['eta']*100:.2f}%, w_net={s_base['w_net']/1000:.2f} kJ/kg")
    print(f"            optimum rp={rp_opt_eta:.1f} -> eta={s_opt['eta']*100:.2f}%, w_net={s_opt['w_net']/1000:.2f} kJ/kg")
    eta_gain = (s_opt['eta']-s_base['eta'])/s_base['eta']*100
    print(f"Efficiency gain moving to optimum rp: {eta_gain:.2f}%")

    print("\n" + "="*72)
    print("MODULE 3: REGENERATOR EFFECTIVENESS STUDY")
    print("="*72)

    epsilon_range = np.linspace(0.0, 0.95, 20)
    rp_fixed = 6.0   # regeneration benefit is strongest at lower pressure ratios
    eta_vs_epsilon = [cycle_state(rp_fixed, epsilon=eps)['eta'] for eps in epsilon_range]

    eta_no_regen = cycle_state(rp_fixed, epsilon=0.0)['eta']
    eta_with_regen = cycle_state(rp_fixed, epsilon=epsilon_regen)['eta']
    improvement = (eta_with_regen - eta_no_regen)/eta_no_regen*100

    print(f"At rp = {rp_fixed}:")
    print(f"  No regeneration (epsilon=0)      : eta = {eta_no_regen*100:.2f}%")
    print(f"  With regeneration (epsilon={epsilon_regen}) : eta = {eta_with_regen*100:.2f}%")
    print(f"  Relative efficiency improvement    : {improvement:.2f}%")

    # Specific fuel consumption (SFC) at design point
    s_design = cycle_state(8.0)
    sfc = 3600 / (s_design['eta'] * LHV_fuel / 1e6 * 1000/3600)   # kg fuel per kWh, standard GT metric form
    # simpler direct form: fuel mass per unit net work
    mdot_fuel_per_kg_air = s_design['q_in']/LHV_fuel
    sfc_kg_per_kWh = mdot_fuel_per_kg_air / (s_design['w_net']/3.6e6)  # kg fuel / kWh net work
    print(f"\nAt design point (rp=8, TIT=1400K, regen=0.75):")
    print(f"  Specific fuel consumption : {sfc_kg_per_kWh:.4f} kg-fuel/kWh")

    print("\n" + "="*72)
    print("MODULE 4: STATISTICAL SENSITIVITY ANALYSIS")
    print("="*72)

    np.random.seed(42)
    n_samples = 500

    # Realistic operating/manufacturing variability ranges
    eta_c_samples = np.random.uniform(0.82, 0.88, n_samples)   # compressor efficiency tolerance
    eta_t_samples = np.random.uniform(0.85, 0.91, n_samples)   # turbine efficiency tolerance
    TIT_samples   = np.random.uniform(1350, 1450, n_samples)    # TIT control band, K
    rp_samples    = np.random.uniform(7.5, 8.5, n_samples)       # compressor pressure ratio control band

    eta_results = np.array([
        cycle_state(rp_samples[i], T4=TIT_samples[i],
                    eta_c=eta_c_samples[i], eta_t=eta_t_samples[i])['eta']
        for i in range(n_samples)
    ])

    mean_eta = np.mean(eta_results)
    std_eta = np.std(eta_results, ddof=1)
    t_crit = stats.t.ppf(0.975, df=n_samples-1)
    margin = t_crit*std_eta/np.sqrt(n_samples)
    ci_low, ci_high = mean_eta-margin, mean_eta+margin

    print(f"Sample size: {n_samples}")
    print(f"Mean thermal efficiency        : {mean_eta*100:.3f}%")
    print(f"Std. dev.                       : {std_eta*100:.3f}%")
    print(f"95% CI on mean efficiency        : [{ci_low*100:.3f}%, {ci_high*100:.3f}%]")
    print(f"Min/Max efficiency in sweep       : {eta_results.min()*100:.2f}% / {eta_results.max()*100:.2f}%")

    # Multi-variable regression: which parameter matters most?
    from numpy.polynomial import polynomial as P
    for name, sample in [('eta_c', eta_c_samples), ('eta_t', eta_t_samples),
                          ('TIT', TIT_samples), ('rp', rp_samples)]:
        slope, intercept, r_value, p_value, std_err = stats.linregress(sample, eta_results)
        print(f"  Sensitivity to {name:6s}: slope={slope:.6f}, R^2={r_value**2:.4f}, p={p_value:.2e}")

    # =================================================================
    # PLOTS
    # =================================================================
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    # Plot 1: Efficiency vs pressure ratio for various TIT
    ax = axes[0,0]
    colors = plt.cm.plasma(np.linspace(0.15, 0.85, len(TIT_values)))
    for TIT, c in zip(TIT_values, colors):
        ax.plot(rp_range, sweep_results[TIT]['eta']*100, color=c, lw=2, label=f'TIT={TIT}K')
    ax.axvline(rp_opt_eta, color='gray', ls='--', alpha=0.6, label=f'Optimum rp={rp_opt_eta:.1f} (TIT=1400K)')
    ax.set_xlabel('Pressure ratio (rp)'); ax.set_ylabel('Thermal efficiency (%)')
    ax.set_title('Cycle Efficiency vs Pressure Ratio')
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # Plot 2: Specific work vs pressure ratio
    ax = axes[0,1]
    for TIT, c in zip(TIT_values, colors):
        ax.plot(rp_range, sweep_results[TIT]['w_net']/1000, color=c, lw=2, label=f'TIT={TIT}K')
    ax.axvline(rp_opt_wnet, color='gray', ls='--', alpha=0.6, label=f'Optimum rp={rp_opt_wnet:.1f} (max w_net)')
    ax.set_xlabel('Pressure ratio (rp)'); ax.set_ylabel('Specific net work (kJ/kg)')
    ax.set_title('Specific Work Output vs Pressure Ratio')
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # Plot 3: Regenerator effectiveness impact
    ax = axes[1,0]
    ax.plot(epsilon_range, np.array(eta_vs_epsilon)*100, color='#16a085', lw=2, marker='o', ms=3)
    ax.axvline(epsilon_regen, color='red', ls='--', label=f'Design point eps={epsilon_regen}')
    ax.set_xlabel('Regenerator effectiveness (epsilon)'); ax.set_ylabel('Thermal efficiency (%)')
    ax.set_title(f'Effect of Regeneration on Efficiency (rp={rp_fixed})')
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # Plot 4: Sensitivity analysis - efficiency distribution
    ax = axes[1,1]
    ax.hist(eta_results*100, bins=30, color='#e67e22', alpha=0.75, edgecolor='white')
    ax.axvline(mean_eta*100, color='black', lw=2, label=f'Mean={mean_eta*100:.2f}%')
    ax.axvline(ci_low*100, color='red', ls='--', label=f'95% CI [{ci_low*100:.2f},{ci_high*100:.2f}]')
    ax.axvline(ci_high*100, color='red', ls='--')
    ax.set_xlabel('Thermal efficiency (%)'); ax.set_ylabel('Frequency')
    ax.set_title('Efficiency Distribution Under Component Tolerances')
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig('/home/claude/brayton_project/brayton_analysis.png', dpi=150)
    print("\nPlots saved.")
