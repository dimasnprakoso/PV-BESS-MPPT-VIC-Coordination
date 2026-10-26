# -*- coding: utf-8 -*-
"""
Revision R1, Reviewer 1 comment 6: re-render the averaged-model result figures from the ORIGINAL
data and scripts at print size (160 mm width), text >= 9 pt at print size, as PDF + SVG (vector,
editable) and 600-dpi PNG. No raster upscaling and no AI tools.
  gbr3_pareto       <- copy of python/plot_pareto.py (output redirected, size adjusted)    [Figure 3]
  gbr4_lc_S5        <- python/results/traj_S5_{static,adaptive}.csv (output of fullmodel.py) [Figure 4]
  gbr6_dekomposisi  <- copy of python/s3_decomposition.py                                 [Figure 5]
  gbr7_sensitivitas <- sapuan_H.csv in the results folder (sapuan_H.py, model fullmodel.py)  [Figure 6]
"""
import os
import re
import runpy
import sys
import tempfile

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)).replace(chr(92), "/")
PY = os.path.abspath(os.path.join(HERE, "..", "..", "python"))
sys.path.insert(0, PY)
RES = os.path.join(PY, "results")
LEBAR = 160 / 25.4
RC = {"pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none", "font.family": "serif",
      "font.serif": ["Times New Roman", "DejaVu Serif"], "font.size": 10, "axes.titlesize": 10.5,
      "axes.labelsize": 10, "xtick.labelsize": 9.5, "ytick.labelsize": 9.5, "legend.fontsize": 9,
      "lines.linewidth": 1.4, "axes.grid": True, "grid.alpha": 0.3}


def simpan(fig, nama):
    for ext, kw in (("pdf", {}), ("svg", {}), ("png", {"dpi": 600})):
        fig.savefig(os.path.join(HERE, f"{nama}.{ext}"), **kw)
    plt.close(fig)
    print("->", nama)


def jalankan_salinan(skrip, nama_baru, ganti):
    """Salin skrip asli, alihkan keluaran ke folder ini dan sesuaikan ukuran, lalu jalankan."""
    src = open(os.path.join(PY, skrip), encoding="utf-8").read()
    for a, b in ganti:
        src2 = re.sub(a, b, src)
        if src2 == src:
            raise RuntimeError(f"pola tidak ditemukan di {skrip}: {a}")
        src = src2
    tmp = os.path.join(PY, f"_tmp_{nama_baru}.py")   # di folder python agar impor relatif tetap jalan
    open(tmp, "w", encoding="utf-8").write(src)
    try:
        runpy.run_path(tmp, run_name="__main__")
    finally:
        os.remove(tmp)


# ---------------------------------------------------------------- Gambar 3: Pareto
plt.rcParams.update(RC)
jalankan_salinan("plot_pareto.py", "gbr3", [
    (r'"font\.size": 16', '"font.size": 10'),
    (r"figsize=\(7\.0, 2\.7\)", f"figsize=({LEBAR:.3f}, 2.6)"),
    (r'fontsize=16', 'fontsize=10.5'),
    (r'fig\.savefig\(os\.path\.join\(FIG, "pareto_front\.pdf"\)\)',
     f'[fig.savefig(os.path.join(r"{HERE}", "gbr3_pareto." + e), **k) for e, k in (("pdf", {{}}), ("svg", {{}}), ("png", {{"dpi": 600}}))]'),
    (r'fig\.savefig\(os\.path\.join\(FIG, "pareto_front\.png"\), dpi=150\)', 'pass'),
])

# ---------------------------------------------------------------- Gambar 6: dekomposisi
plt.rcParams.update(RC)
jalankan_salinan("s3_decomposition.py", "gbr6", [
    (r'"font\.size": 16', '"font.size": 10'),
    (r"figsize=\(7\.4, 4\.6\)", f"figsize=({LEBAR:.3f}, 4.6)"),
    (r'fontsize=16', 'fontsize=10.5'),
    (r'fontsize=9\.5', 'fontsize=9'),
    (r'MPPT--VIC', 'MPPT–VIC'),
    (r'fontsize=10([,)])', r'fontsize=9\1'),
    (r'fig\.savefig\(os\.path\.join\(FIG, "fullpy_decomp\.pdf"\)\)',
     f'[fig.savefig(os.path.join(r"{HERE}", "gbr6_dekomposisi." + e), **k) for e, k in (("pdf", {{}}), ("svg", {{}}), ("png", {{"dpi": 600}}))]'),
    (r'fig\.savefig\(os\.path\.join\(FIG, "fullpy_decomp\.png"\), dpi=150\)', 'pass'),
])

# ---------------------------------------------------------------- Gambar 4: siklus batas S5
plt.rcParams.update(RC)
DT = 1e-4 * 10
tr = {c: np.loadtxt(os.path.join(RES, f"traj_S5_{c}.csv"), delimiter=",", skiprows=1)
      for c in ("static", "adaptive")}
t = np.arange(tr["static"].shape[0]) * DT
fig, ax = plt.subplots(1, 2, figsize=(LEBAR, 2.6))
for c, warna, lab in (("static", "tab:red", "conventional static"), ("adaptive", "tab:blue", "proposed")):
    ax[0].plot(t, tr[c][:, 0], color=warna, label=lab)
    ax[1].plot(t, 50 + 50 * tr[c][:, 1], color=warna)
ax[0].set_xlabel("Time (s)"); ax[0].set_ylabel(r"$P_{out}$ (pu)"); ax[0].set_title("(a)", loc="left")
ax[0].legend(loc="lower right")
ax[1].set_xlabel("Time (s)"); ax[1].set_ylabel("Frequency (Hz)"); ax[1].set_title("(b)", loc="left")
fig.tight_layout(); simpan(fig, "gbr4_lc_S5")

# ---------------------------------------------------------------- Gambar 7: sensitivitas H
plt.rcParams.update(RC)
d = np.genfromtxt(os.path.join(HERE, "..", "results", "sapuan_H.csv"), delimiter=",", names=True)
fig, ax = plt.subplots(1, 2, figsize=(LEBAR, 2.6))
ax[0].plot(d["H"], d["static_nadir_Hz"], "r-o", ms=4.5, label="conventional static")
ax[0].plot(d["H"], d["adaptive_nadir_Hz"], "b-s", ms=4.5, label="proposed")
ax[0].set_xlabel(r"$H_{sys}$ (s)"); ax[0].set_ylabel("Nadir (Hz)"); ax[0].set_title("(a)", loc="left")
ax[0].legend(loc="center right")
ax[1].semilogy(d["H"], np.maximum(d["static_Pp2p_pu"], 1e-8), "r-o", ms=4.5)
ax[1].semilogy(d["H"], np.maximum(d["adaptive_Pp2p_pu"], 1e-8), "b-s", ms=4.5)
ax[1].set_xlabel(r"$H_{sys}$ (s)"); ax[1].set_ylabel(r"$P_{p2p}$ (pu)"); ax[1].set_title("(b)", loc="left")
fig.tight_layout(); simpan(fig, "gbr7_sensitivitas")
