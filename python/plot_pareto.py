# -*- coding: utf-8 -*-
"""
Figur pareto_front: front Pareto robust produksi (NSGA-II 60 solusi, CVaR
gamma=0.95). Sumber: ../tuning/pareto_front_prod.csv
(kolom: Kd,Kj,ka,kaw,kb,beta_max,F1_maxDf,F2_eMPP,F3_eBat,F4_p2p).
Knee = jarak-ternormalisasi minimum ke titik ideal (idx 27, parameter
produksi: Kd=1.0045, Kj=0.0317, ka=47.483, kaw=1.0, kb=45.797, bmax=0.2497).
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
# WAJIB. Bawaan matplotlib menanam fon sebagai Type 3, yang ditolak
# IEEE PDF eXpress dan disorot banyak sistem submisi jurnal. 42 memaksa
# TrueType. Jangan dihapus.
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "..", "figures")
F = np.loadtxt(os.path.join(HERE, "..", "tuning", "pareto_front_prod.csv"),
               delimiter=",", skiprows=1)
obj = F[:, 6:10]
z = (obj - obj.min(0)) / (obj.max(0) - obj.min(0) + 1e-12)
knee = int(np.argmin(np.linalg.norm(z, axis=1)))
print(f"knee idx {knee} | params {np.round(F[knee, :6], 4)} | F {np.round(F[knee, 6:], 4)}")

plt.rcParams.update({"legend.borderpad": 0.3, "legend.labelspacing": 0.25, "legend.handlelength": 1.3, "legend.handletextpad": 0.5, "legend.framealpha": 0.95, "font.size": 16, "font.family": "serif"})
fig, ax = plt.subplots(1, 2, figsize=(7.0, 2.7))

ax[0].scatter(obj[:, 0], obj[:, 2], s=22, c="tab:blue", alpha=0.75, label="Pareto set")
ax[0].scatter(obj[knee, 0], obj[knee, 2], marker="*", s=260, c="tab:red",
              edgecolors="k", linewidths=0.6, zorder=5, label="knee")
ax[0].set_xlabel(r"$F_1$: max $|\Delta f|$ (CVaR)")
ax[0].set_ylabel(r"$F_3$: BESS thr.")
ax[0].grid(alpha=0.3); ax[0].legend(fontsize=10, loc="upper right", markerscale=0.8)
ax[0].set_title("(a)", fontsize=16)

ax[1].scatter(obj[:, 1], obj[:, 3], s=22, c="tab:blue", alpha=0.75)
ax[1].scatter(obj[knee, 1], obj[knee, 3], marker="*", s=260, c="tab:red",
              edgecolors="k", linewidths=0.6, zorder=5)
ax[1].set_yscale("log")
ax[1].set_xlabel(r"$F_2$: MPP dev. (CVaR)")
ax[1].set_ylabel(r"$F_4$: $P_{p2p}$ (CVaR)")
ax[1].grid(alpha=0.3, which="both")
ax[1].set_title("(b)", fontsize=16)

fig.tight_layout()
fig.savefig(os.path.join(FIG, "pareto_front.pdf"))
fig.savefig(os.path.join(FIG, "pareto_front.png"), dpi=150)
print("figur: pareto_front.pdf/png")
