# -*- coding: utf-8 -*-
"""
Existence map of the relay limit cycle with primary reserve (revision R1, Reviewer 2 comment 1).
The main evaluation has no governor/FCR, so the battery is the only steady-state regulator; with a
5 % FCR droop the cycle of the nominal relay disappears. This test maps where the cycle occurs and
checks the analytical criterion

    |Dw_ss| = DPL / (D + Kd + 1/R)  >  h      (D = 1, Kd = 0.5, fixed-gain VIC)

i.e. the cycle exists when the steady-state deviation AFTER the primary response is still outside the
dead-band (condition (6) of the manuscript adds the upper bound h*Sigma + M).
Map: droop R x DPL, H fixed at 2 s, for the nominal relay (h 0.02) and the 49.7-Hz FFR relay
(h 0.006, M 0.15), and for the proposed scheme. First-order governor, T_g = 5 s.
"""
import csv
import os
import time

import numpy as np

import model_r1 as M
import fullmodel as fm

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
RS = [0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30, 0.50, None]
DPL = np.round(np.arange(0.02, 0.201, 0.01), 3)


def relay(h, m):
    c = M.ctrl_cfg("static"); c["h_on"] = h; c["M"] = m; return c


CTRL = {"static_h020_M040": relay(0.02, 0.40), "relay_h006_M015": relay(0.006, 0.15),
        "adaptive": M.ctrl_cfg("adaptive")}

if __name__ == "__main__":
    t0 = time.time()
    n = DPL.size
    xi = dict(H=np.full(n, 2.0), DPL=DPL.copy(), SOC0=np.full(n, 0.6), Gjit=np.ones(n),
              Tc=np.full(n, 28.0))
    rows = []
    for R in RS:
        for name, c in CTRL.items():
            m, _ = M.simulate(c, xi, T_end=40.0, win=10.0, gov_R=R, gov_T=5.0)
            lc = M.lc_detect(m["Pp2p_pu"], m["fosc_Hz"], T_w=10.0)
            ginv = 0.0 if R is None else 1.0 / R
            dw_ss = DPL / (1.0 + c.get("Kd", 0.0) + ginv)
            h = c.get("h_on", np.nan)
            pred = dw_ss > h if name != "adaptive" else np.zeros(n, bool)
            for j in range(n):
                rows.append([R if R else "none", name, DPL[j], float(dw_ss[j]), bool(pred[j]),
                             bool(lc[j]), float(m["Pp2p_pu"][j]), float(m["fosc_Hz"][j]),
                             float(m["nadir_Hz"][j])])
            cocok = int((pred == lc).sum())
            print(f"R={str(R):5s} {name:17s} LC di DPL={[float(d) for d in DPL[lc]][:3]}... "
                  f"({lc.sum()}/{n})  kriteria cocok {cocok}/{n}  [{time.time()-t0:.0f}s]", flush=True)
    with open(os.path.join(OUT, "uji_governor.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["gov_R", "controller", "DPL", "dw_ss_pred", "LC_pred", "LC_sim", "Pp2p_pu", "fosc_Hz",
                    "nadir_Hz"])
        w.writerows(rows)
    print(f"selesai {time.time()-t0:.0f} s")
