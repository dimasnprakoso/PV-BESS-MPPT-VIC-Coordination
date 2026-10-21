# -*- coding: utf-8 -*-
"""Cross-implementation MODEL PENUH: Python vs Julia.
Membandingkan trayektori (Pinj, Dw) nominal S3/S5 x 5 kontroler:
    epsilon = ||x_py - x_jl||_2 / ||x_py||_2   (target < 1%)
Jalankan SETELAH ../python/fullmodel.py dan fullmodel.jl.
"""
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(HERE, "..", "python", "results")
JL = os.path.join(HERE, "results")

worst = 0.0
print("=== cross-implementation MODEL PENUH: Python (A) vs Julia (B) ===")
for scn in ("S3", "S5"):
    for ctrl in ("adaptive", "adaptgain", "smoothstatic", "static", "droop"):
        a = np.genfromtxt(os.path.join(PY, f"traj_{scn}_{ctrl}.csv"),
                          delimiter=",", names=True)
        b = np.genfromtxt(os.path.join(JL, f"traj_{scn}_{ctrl}_julia.csv"),
                          delimiter=",", names=True)
        for var in ("Pinj_pu", "Dw_pu"):
            x, y = a[var], b[var]
            n = min(len(x), len(y)); x, y = x[:n], y[:n]
            den = np.linalg.norm(x)
            e = float(np.linalg.norm(x - y) / den) if den > 0 else 0.0
            worst = max(worst, e)
            print(f"  {scn} {ctrl:9s} {var:8s} : eps = {e:.3e} ({e*100:.4f} %)")
print(f"  WORST eps = {worst:.3e} ({worst*100:.4f} %) -> "
      f"{'LULUS (<1%)' if worst < 0.01 else 'PERIKSA'}")
