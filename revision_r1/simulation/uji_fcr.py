# -*- coding: utf-8 -*-
"""
Penguat R2-1: kampanye skenario DENGAN cadangan primer (FCR/governor orde-1).

Kampanye naskah tidak memiliki governor, sehingga baterai menjadi satu-satunya pengatur
tunak. Di sini setiap realisasi S3/S4 diulang dengan governor agregat orde-1
(T_g = 5 s) pada dua tingkat cadangan:
  R = 0,05  -> cadangan normal (droop 5 %)
  R = 0,20  -> cadangan lemah
Kontroler: usulan, smooth-static, relai naskah (1 Hz, M 0,4), relai 49,7 Hz (M 0,15 dan 0,4),
FFR Nordik berlatch 5 s (M 0,15; kini wajar karena ada FCR yang mengambil alih), droop.
Semua kontroler dan kedua tingkat R memakai realisasi yang SAMA (common random numbers),
sehingga perbandingan berpasangan. Durasi 40 s, jendela tunak 10 s terakhir.
"""
import csv
import os
import time

import numpy as np

import model_r1 as M
import fullmodel as fm
from statistik_r1 import bandingkan

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
N_R, T_END, WIN, T_GOV = 100, 40.0, 10.0, 5.0
H06 = 0.3 / fm.F0
RS = (0.05, 0.20)


def cfg(name):
    if name in ("adaptive", "static", "smoothstatic", "droop"):
        return M.ctrl_cfg(name)
    if name.startswith("relay006"):
        c = M.ctrl_cfg("static"); c["h_on"] = H06; c["M"] = float(name[-3:]) / 100; return c
    c = M.ctrl_cfg("ffr"); c["t_hold"] = 5.0; c["M"] = float(name[-3:]) / 100
    return c


VARIAN = ["adaptive", "smoothstatic", "static", "relay006_M015", "relay006_M040", "ffr5_M015", "droop"]
KEYS = ("nadir_Hz", "fstd_Hz", "maxRoCoF_Hzps", "Pp2p_pu", "fosc_Hz", "eMPP_pu_s", "eBESS_pu_s")

if __name__ == "__main__":
    t0 = time.time()
    fm.rng = np.random.default_rng(43)
    xis = {scn: fm.draw_xi(N_R, scn) for scn in ("S3", "S4")}
    rows, hasil = [], {}
    for R in RS:
        for scn in ("S3", "S4"):
            for v in VARIAN:
                xi = {k: np.array(x, copy=True) for k, x in xis[scn].items()}
                m, _ = M.simulate(cfg(v), xi, T_end=T_END, win=WIN, gov_R=R, gov_T=T_GOV)
                hasil[(R, scn, v)] = m
                lc = M.lc_detect(m["Pp2p_pu"], m["fosc_Hz"], T_w=WIN)
                for j in range(N_R):
                    rows.append([R, scn, v, j, int(lc[j])] + [float(m[k][j]) for k in KEYS])
                print(f"R={R:.2f} {scn} {v:14s} nadir={m['nadir_Hz'].mean():.3f}±{m['nadir_Hz'].std():.3f} "
                      f"Pp2p={m['Pp2p_pu'].mean():.4f} fosc~{np.median(m['fosc_Hz']):.2f}Hz "
                      f"eBESS={m['eBESS_pu_s'].mean():.3f} LC={int(lc.sum())}/{N_R}  [{time.time()-t0:.0f}s]",
                      flush=True)
    with open(os.path.join(OUT, "uji_fcr_raw.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["R", "scenario", "varian", "real", "lc"] + list(KEYS)); w.writerows(rows)

    print("\n=== usulan dibanding tiap baseline (usulan - baseline, berpasangan): median [CI95], Cliff d ===")
    with open(os.path.join(OUT, "uji_fcr_efek.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["R", "scenario", "baseline", "metrik", "mean_usulan", "mean_baseline", "med_diff",
                    "ci_lo", "ci_hi", "cliff", "p_wilcoxon"])
        for R in RS:
            for scn in ("S3", "S4"):
                a = hasil[(R, scn, "adaptive")]
                for v in VARIAN[1:]:
                    b = hasil[(R, scn, v)]
                    for k in ("nadir_Hz", "Pp2p_pu", "eBESS_pu_s"):
                        r = bandingkan(a[k], b[k])
                        w.writerow([R, scn, v, k, a[k].mean(), b[k].mean(), r["med_diff"], r["ci_lo"],
                                    r["ci_hi"], r["cliff"], r["p"]])
                        print(f"R={R:.2f} {scn} {v:14s} {k:10s} {r['med_diff']:+.4f} "
                              f"[{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] d={r['cliff']:+.2f}")
    print(f"\nselesai {time.time()-t0:.0f} s")
