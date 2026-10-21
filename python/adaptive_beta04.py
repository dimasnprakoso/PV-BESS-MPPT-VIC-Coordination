# -*- coding: utf-8 -*-
"""
Amunisi respons reviewer: kontroler ADAPTIF dgn beta_max = 0.4 (apple-to-apple
vs rating smooth-static 0.4), S2-S5 x 100 realisasi. Bandingkan nadir/eBESS
terhadap smooth-static dan adaptif-0.25 dari kampanye (metrics_raw.csv).
"""
import csv
import os
from collections import defaultdict

import numpy as np
from scipy.stats import mannwhitneyu

import fullmodel as fm

HERE = os.path.dirname(os.path.abspath(__file__))
fm.KNEE["beta_max"] = 0.40          # override cap gate (lainnya tetap knee)

print("adaptive beta_max=0.40 | n=100 | seed stream default (7)")
rows = []
res = {}
for scn in ["S2", "S3", "S4", "S5"]:
    xi = fm.draw_xi(100, scn)
    m, _ = fm.simulate(scn, "adaptive", xi)
    res[scn] = m
    for j in range(100):
        rows.append([scn, j, float(m["nadir_Hz"][j]), float(m["Pp2p_pu"][j]),
                     float(m["eBESS_pu_s"][j]), float(m["eMPP_pu_s"][j])])
    print(f"{scn}: nadir={np.mean(m['nadir_Hz']):.3f}+-{np.std(m['nadir_Hz']):.3f} "
          f"| Pp2p={np.mean(m['Pp2p_pu']):.4f} "
          f"| eBESS={np.mean(m['eBESS_pu_s']):.3f} | eMPP={np.mean(m['eMPP_pu_s']):.3f}")

with open(os.path.join(HERE, "results", "beta04_raw.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["scenario", "real", "nadir_Hz", "Pp2p_pu", "eBESS_pu_s", "eMPP_pu_s"])
    w.writerows(rows)

# ---- banding vs kampanye
camp = defaultdict(list)
with open(os.path.join(HERE, "results", "metrics_raw.csv")) as f:
    for r in csv.DictReader(f):
        camp[(r["scenario"], r["controller"])].append(
            (float(r["nadir_Hz"]), float(r["Pp2p_pu"]),
             float(r["eBESS_pu_s"]), float(r["eMPP_pu_s"])))

print("\n=== adaptif-0.40 vs smooth-static (rating sama 0.4) ===")
for scn in ["S2", "S3", "S4", "S5"]:
    a = res[scn]
    ss = camp[(scn, "smoothstatic")]
    for nama, key, col in [("nadir", "nadir_Hz", 0), ("eBESS", "eBESS_pu_s", 2),
                           ("eMPP", "eMPP_pu_s", 3)]:
        x = [float(v) for v in a[key]]
        y = [v[col] for v in ss]
        p = mannwhitneyu(x, y, alternative="two-sided", method="auto").pvalue
        print(f"{scn} {nama:6s}: b04={np.mean(x):.3f} vs ss={np.mean(y):.3f} "
              f"(selisih {np.mean(x)-np.mean(y):+.3f}) p={p:.2e}")
print("\n=== nadir adaptif-0.40 vs adaptif-0.25 (kampanye) ===")
for scn in ["S2", "S3", "S4", "S5"]:
    x = [float(v) for v in res[scn]["nadir_Hz"]]
    y = [v[0] for v in camp[(scn, "adaptive")]]
    print(f"{scn}: b04={np.mean(x):.3f} vs b025={np.mean(y):.3f} ({np.mean(x)-np.mean(y):+.3f} Hz)")
