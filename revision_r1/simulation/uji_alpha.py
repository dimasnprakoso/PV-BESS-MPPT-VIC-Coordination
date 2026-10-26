# -*- coding: utf-8 -*-
"""
Revision R1, Reviewer 2 comment 2: what does adaptivity (the severity weight alpha) add?

The ablation in python/ablasi_reviewer.py tests a single load step on S3-S5, where alpha gives no
benefit. Here alpha is tested in the conditions it is meant for, i.e. damping the VIC response to
small deviations:
  T1 ambient       : OU load fluctuations only (sigma 0.01 pu, tau 1 s), H 1.5-4 s, 40 s
  T2 ambient-lowH  : as T1 with low inertia, H 0.5-1 s
  T3 ambient+event : noise + load step at t = 20 s, 30-s run
  T4 repeated      : noise + three on/off events (2-8, 14-20, 26-32 s), 36 s
Variants: adaptive (proposed), noalpha (w = 1), smooth025, smoothstatic, static.
Common random numbers: the xi draws (seed 31) and the noise (seed 7) are the same for all variants.
"""
import csv
import os
import time

import numpy as np

import model_r1 as M
import fullmodel as fm
from statistik_r1 import bandingkan

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
os.makedirs(OUT, exist_ok=True)
N_R = 100
SIG = 0.01
VARIAN = ["adaptive", "noalpha", "smooth025", "smoothstatic", "static"]
UJI = {
    "T1_ambient": dict(scn="S3", events=(), T_end=40.0),
    "T2_ambient_lowH": dict(scn="S4", events=(), T_end=40.0),
    "T3_ambient_event": dict(scn="S3", events=((20.0, None, 1.0),), T_end=30.0),
    "T4_berulang": dict(scn="S3", events=((2.0, 8.0, 1.0), (14.0, 20.0, 1.0), (26.0, 32.0, 1.0)),
                        T_end=36.0),
}
KEYS = ("nadir_Hz", "fstd_Hz", "maxRoCoF_Hzps", "Pp2p_pu", "fosc_Hz", "eMPP_pu_s", "eBESS_pu_s")

if __name__ == "__main__":
    t0 = time.time()
    fm.rng = np.random.default_rng(31)
    rows, hasil = [], {}
    for uji, cfg in UJI.items():
        xi = fm.draw_xi(N_R, cfg["scn"])
        for v in VARIAN:
            m, _ = M.simulate(M.ctrl_cfg(v), xi, events=cfg["events"], T_end=cfg["T_end"],
                              noise_sigma=SIG, noise_seed=7)
            hasil[(uji, v)] = m
            lc = int(M.lc_detect(m["Pp2p_pu"], m["fosc_Hz"]).sum())
            for j in range(N_R):
                rows.append([uji, v, j] + [float(m[k][j]) for k in KEYS])
            print(f"{uji:17s} {v:12s} nadir={m['nadir_Hz'].mean():.3f} fstd={1e3*m['fstd_Hz'].mean():.1f}mHz "
                  f"RoCoF={m['maxRoCoF_Hzps'].mean():.3f} eBESS={m['eBESS_pu_s'].mean():.3f} "
                  f"eMPP={m['eMPP_pu_s'].mean():.3f} LC={lc}/100  [{time.time()-t0:.0f}s]", flush=True)
    with open(os.path.join(OUT, "uji_alpha_raw.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["uji", "varian", "real"] + list(KEYS))
        w.writerows(rows)

    print("\n=== noalpha / smooth025 dibanding usulan (varian - usulan): median [CI95], Cliff d ===")
    with open(os.path.join(OUT, "uji_alpha_efek.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["uji", "varian", "metrik", "mean_usulan", "mean_varian", "med_diff", "ci_lo", "ci_hi",
                    "cliff", "p_wilcoxon"])
        for uji in UJI:
            a = hasil[(uji, "adaptive")]
            for v in ("noalpha", "smooth025", "smoothstatic"):
                b = hasil[(uji, v)]
                for k in ("nadir_Hz", "fstd_Hz", "eBESS_pu_s", "eMPP_pu_s"):
                    r = bandingkan(b[k], a[k])
                    w.writerow([uji, v, k, a[k].mean(), b[k].mean(), r["med_diff"], r["ci_lo"], r["ci_hi"],
                                r["cliff"], r["p"]])
                    sc = 1e3 if k == "fstd_Hz" else 1.0
                    print(f"{uji:17s} {v:12s} {k:10s} {sc*r['med_diff']:+.4f} [{sc*r['ci_lo']:+.4f},"
                          f"{sc*r['ci_hi']:+.4f}] d={r['cliff']:+.2f}")
    print(f"\nselesai {time.time()-t0:.0f} s")
