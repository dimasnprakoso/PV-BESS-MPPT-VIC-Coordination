# -*- coding: utf-8 -*-
"""Gambar baru: peta keberadaan siklus batas pada bidang (gain FCR 1/R, dP_L) dengan batas analitis
h*Sigma < dP_L < h*Sigma + M, Sigma = D + Kd + 1/R. Data: results/uji_governor.csv."""
import csv, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 11})
OUT = os.path.join("..", "figures")
rows = list(csv.DictReader(open(os.path.join("..", "results", "uji_governor.csv"))))
cfg = {"static_h020_M040": (0.02, 0.40, "(a) $h$ = 0.02 pu (49.0 Hz), $M$ = 0.4 pu"),
       "relay_h006_M015": (0.006, 0.15, "(b) $h$ = 0.006 pu (49.7 Hz), $M$ = 0.15 pu")}
g = lambda R: 0.0 if R == "none" else 1.0 / float(R)
fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.6), sharey=True)
for a, (name, (h, M, title)) in zip(ax, cfg.items()):
    pts = [r for r in rows if r["controller"] == name]
    x = np.array([g(r["gov_R"]) for r in pts]); y = np.array([float(r["DPL"]) for r in pts])
    lc = np.array([r["LC_sim"] == "True" for r in pts])
    a.scatter(x[lc], y[lc], marker="o", s=22, c="tab:red", label="limit cycle (simulated)", zorder=3)
    a.scatter(x[~lc], y[~lc], marker="o", s=22, facecolors="none", edgecolors="0.4", label="no limit cycle", zorder=3)
    gg = np.linspace(0, 36, 200); S = 1.0 + 0.5 + gg
    a.plot(gg, h * S, "k-", lw=1.4, label=r"$h\,\Sigma$ and $h\,\Sigma + M$")
    a.plot(gg, h * S + M, "k-", lw=1.4)
    a.fill_between(gg, h * S, np.minimum(h * S + M, 0.21), color="tab:red", alpha=0.08)
    a.set_xlim(-1, 35); a.set_ylim(0.01, 0.21)
    a.set_xlabel(r"primary-reserve gain $1/R$ (pu/pu)"); a.set_title(title, fontsize=10, loc="left")
    a.grid(alpha=0.3)
ax[0].set_ylabel(r"load step $\Delta P_L$ (pu)")
h_, l_ = ax[0].get_legend_handles_labels()
fig.legend(h_, l_, loc="lower center", ncol=3, fontsize=9, frameon=False)
fig.tight_layout(rect=(0, 0.08, 1, 1))
for ext, kw in (("pdf", {}), ("png", {"dpi": 600}), ("svg", {})):
    fig.savefig(os.path.join(OUT, f"peta_lc.{ext}"), **kw)
print("ok")
