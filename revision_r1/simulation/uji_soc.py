# -*- coding: utf-8 -*-
"""
Komentar R2-5: gerbang sadar-SOC tidak pernah teruji (Phi_SOC = 1 sepanjang kampanye).

U1 dekat batas bawah : SOC0 ~ U(0,20; 0,25) (di dalam pita taper), event turun-frekuensi S3, 20 s
U2 dekat batas atas  : SOC0 ~ U(0,85; 0,90), event NAIK-frekuensi (pelepasan beban, DPL < 0), 20 s
U3 pengurasan        : SOC0 = 0,205, event turun-frekuensi bertahan 120 s, H dan DPL acak
Varian:
  adaptive          : gerbang usulan dengan taper linear 5 %
  adaptive_hardcut  : gerbang usulan, taper diganti potong keras (lebar 1e-6)
  static            : relai naskah (taper sama)
Metrik tambahan: SOC minimum/maksimum, Phi minimum, P_p2p dan deteksi siklus batas di
jendela 2 s terakhir.
"""
import csv
import os
import time

import numpy as np

import model_r1 as M
import fullmodel as fm

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
N_R = 100
VARIAN = {"adaptive": ("adaptive", None), "adaptive_hardcut": ("adaptive", 1e-6),
          "static": ("static", None)}
KEYS = ("nadir_Hz", "maxRoCoF_Hzps", "Pp2p_pu", "fosc_Hz", "eBESS_pu_s", "soc_min", "soc_end", "phi_min")

if __name__ == "__main__":
    t0 = time.time()
    fm.rng = np.random.default_rng(51)
    uji = {}
    xi = fm.draw_xi(N_R, "S3"); xi["SOC0"] = fm.rng.uniform(0.20, 0.25, N_R)
    uji["U1_SOC_rendah"] = (xi, dict(T_end=20.0))
    xi = fm.draw_xi(N_R, "S6"); xi["SOC0"] = fm.rng.uniform(0.85, 0.90, N_R)
    uji["U2_SOC_tinggi"] = (xi, dict(T_end=20.0))
    xi = fm.draw_xi(N_R, "S3"); xi["SOC0"] = np.full(N_R, 0.205)
    uji["U3_pengurasan"] = (xi, dict(T_end=120.0))
    rows = []
    for nama, (xi, kw) in uji.items():
        for v, (c, tap) in VARIAN.items():
            m, _ = M.simulate(M.ctrl_cfg(c), xi, soc_taper=tap, **kw)
            m["soc_max"] = None
            lc = int(M.lc_detect(m["Pp2p_pu"], m["fosc_Hz"]).sum())
            for j in range(N_R):
                rows.append([nama, v, j] + [float(m[k][j]) for k in KEYS])
            # untuk U2 nadir_Hz = 50 - 50*max|Dw| -> dilaporkan sebagai puncak frekuensi
            print(f"{nama:15s} {v:16s} |dev|max={50-m['nadir_Hz'].mean():.3f}Hz "
                  f"Pp2p={m['Pp2p_pu'].mean():.4f} (maks {m['Pp2p_pu'].max():.4f}) LC={lc}/100 "
                  f"SOCmin={m['soc_min'].min():.4f} SOCend={m['soc_end'].mean():.4f} "
                  f"phi_min={m['phi_min'].mean():.3f} eBESS={m['eBESS_pu_s'].mean():.3f}  [{time.time()-t0:.0f}s]",
                  flush=True)
    with open(os.path.join(OUT, "uji_soc_raw.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["uji", "varian", "real"] + list(KEYS)); w.writerows(rows)
    print(f"\nselesai {time.time()-t0:.0f} s")
