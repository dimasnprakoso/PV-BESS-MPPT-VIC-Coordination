# -*- coding: utf-8 -*-
"""Angka di balik Gambar 5 naskah (sapuan H_sys, S3 nominal) untuk interpretasi R1-7."""
import numpy as np, model_r1 as M, fullmodel as fm, csv, os
Hs = np.linspace(0.5, 4.0, 8)
xi = fm.xi_nominal(Hs.size); xi["H"] = Hs.copy()
rows = []
res = {c: M.simulate(M.ctrl_cfg(c), xi, g_scn="S3")[0] for c in ("adaptive", "static", "smoothstatic", "droop")}
for i, h in enumerate(Hs):
    r = [h] + [float(res[c][k][i]) for c in res for k in ("nadir_Hz", "Pp2p_pu", "maxRoCoF_Hzps")]
    rows.append(r)
    print("H=%.2f | " % h + " | ".join("%s nadir=%.3f p2p=%.4f roc=%.2f" % (c, res[c]["nadir_Hz"][i], res[c]["Pp2p_pu"][i], res[c]["maxRoCoF_Hzps"][i]) for c in res))
with open(os.path.join("..", "results", "sapuan_H.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["H"] + [f"{c}_{k}" for c in res for k in ("nadir_Hz", "Pp2p_pu", "maxRoCoF_Hzps")]); w.writerows(rows)
