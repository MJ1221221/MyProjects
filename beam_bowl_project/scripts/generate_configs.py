import csv

rows = []
idx = 1

# Base bowl radius
R = 0.12  # m

# Sweep 1: beam length relative to bowl diameter (8 cases)
for L in [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45]:
    rows.append([f"C{idx:02d}", L, 0.05, 0.40, R, 40]); idx += 1

# Sweep 2: bending stiffness EI (6 cases) at fixed L
for EI in [0.005, 0.01, 0.02, 0.05, 0.10, 0.20]:
    rows.append([f"C{idx:02d}", 0.30, EI, 0.40, R, 40]); idx += 1

# Sweep 3: self-weight per length w (6 cases) at fixed L, EI
for w in [0.10, 0.20, 0.40, 0.60, 0.80, 1.00]:
    rows.append([f"C{idx:02d}", 0.30, 0.05, w, R, 40]); idx += 1

# Sweep 4: bowl radius R (5 cases) at fixed L, EI, w
for Rv in [0.08, 0.10, 0.12, 0.15, 0.18]:
    rows.append([f"C{idx:02d}", 0.30, 0.05, 0.40, Rv, 40]); idx += 1

with open("/home/claude/beam_bowl_project/config/configs.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "L_m", "EI_Nm2", "w_Npm", "R_m", "N_segments"])
    writer.writerows(rows)

print(f"Wrote {len(rows)} configurations")
