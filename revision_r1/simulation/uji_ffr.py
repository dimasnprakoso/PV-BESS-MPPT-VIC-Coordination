# -*- coding: utf-8 -*-
"""
Komentar R2-1: baseline relai dinilai tidak realistis (ambang 0,02 pu = 1 Hz, kuantum 0,4 pu).

Baseline diganti dengan pemicu realistis menurut spesifikasi FFR Nordik
(Svenska kraftnaet / Fingrid / Statnett / Energinet, "Technical requirements for FFR"):
ambang 49,7 Hz (h = 0,006 pu), aktif penuh <= 1,3 s, durasi dukungan 5 s (pendek)
atau 30 s (panjang), deaktivasi <= 20 %/s, boleh aktif ulang segera.
Varian:
  adaptive        : skema usulan (acuan)
  static          : relai naskah (h 0,02 pu, M 0,4 pu)
  relay006_M015   : relai tanpa memori, ambang 49,7 Hz, M 0,15 pu
  relay006_M040   : idem, M 0,4 pu
  ffr5_M010/M015/M040 : FFR Nordik dukungan pendek 5 s
  ffr30_M015      : FFR Nordik dukungan panjang 30 s
Durasi 40 s (event di 2 s), jendela tunak 10 s terakhir (resolusi 0,1 Hz,
ambang deteksi f_osc > 2/T_w = 0,2 Hz) agar perburuan lambat FFR ikut tertangkap.
"""
import csv
import os
import time

import numpy as np

import model_r1 as M
import fullmodel as fm
from statistik_r1 import bandingkan

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
N_R, T_END, WIN = 100, 40.0, 10.0
H06 = 0.3 / fm.F0


def cfg(name):
    if name in ("adaptive", "static"):
        return M.ctrl_cfg(name)
    if name.startswith("relay006"):
        c = M.ctrl_cfg("static"); c["h_on"] = H06; c["M"] = float(name[-3:]) / 100; return c
    c = M.ctrl_cfg("ffr")
    c["t_hold"] = 30.0 if name.startswith("ffr30") else 5.0
    c["M"] = float(name[-3:]) / 100
    return c


VARIAN = ["adaptive", "static", "relay006_M015", "relay006_M040",
          "ffr5_M010", "ffr5_M015", "ffr5_M040", "ffr30_M015"]
KEYS = ("nadir_Hz", "fstd_Hz", "maxRoCoF_Hzps", "Pp2p_pu", "fosc_Hz", "eMPP_pu_s", "eBESS_pu_s")

if __name__ == "__main__":
    t0 = time.time()
    fm.rng = np.random.default_rng(41)
    rows, hasil = [], {}
    for scn in ("S3", "S4"):
        xi = fm.draw_xi(N_R, scn)
        for v in VARIAN:
            m, _ = M.simulate(cfg(v), xi, T_end=T_END, win=WIN)
            hasil[(scn, v)] = m
            lc = int(M.lc_detect(m["Pp2p_pu"], m["fosc_Hz"], T_w=WIN).sum())
            for j in range(N_R):
                rows.append([scn, v, j] + [float(m[k][j]) for k in KEYS])
            print(f"{scn} {v:14s} nadir={m['nadir_Hz'].mean():.3f}±{m['nadir_Hz'].std():.3f} "
                  f"Pp2p={m['Pp2p_pu'].mean():.4f} fosc~{np.median(m['fosc_Hz']):.2f}Hz "
                  f"eBESS={m['eBESS_pu_s'].mean():.3f} LC={lc}/100  [{time.time()-t0:.0f}s]", flush=True)
    with open(os.path.join(OUT, "uji_ffr_raw.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["scenario", "varian", "real"] + list(KEYS)); w.writerows(rows)

    print("\n=== usulan dibanding tiap baseline (usulan - baseline): median [CI95], Cliff d ===")
    with open(os.path.join(OUT, "uji_ffr_efek.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "baseline", "metrik", "mean_usulan", "mean_baseline", "med_diff",
                    "ci_lo", "ci_hi", "cliff", "p_wilcoxon"])
        for scn in ("S3", "S4"):
            a = hasil[(scn, "adaptive")]
            for v in VARIAN[1:]:
                b = hasil[(scn, v)]
                for k in ("nadir_Hz", "Pp2p_pu", "eBESS_pu_s"):
                    r = bandingkan(a[k], b[k])
                    w.writerow([scn, v, k, a[k].mean(), b[k].mean(), r["med_diff"], r["ci_lo"],
                                r["ci_hi"], r["cliff"], r["p"]])
                    print(f"{scn} {v:14s} {k:10s} {r['med_diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] "
                          f"d={r['cliff']:+.2f}")
    print(f"\nselesai {time.time()-t0:.0f} s")
