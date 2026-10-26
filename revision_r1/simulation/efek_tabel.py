# -*- coding: utf-8 -*-
"""
Revision R1, Reviewer 2 comment 6: report effect sizes instead of p-values.
Source: python/results/metrics_raw.csv (manuscript evaluation, 100 realisations per cell; each
controller draws its own realisations -> UNPAIRED comparison).
Output: efek_tabel3_4.csv in the results folder -- proposed minus baseline: median difference,
95 % percentile bootstrap CI (10 000 resamples), Cliff's delta, Mann-Whitney p.
"""
import csv
import os
from collections import defaultdict

import numpy as np

from statistik_r1 import bandingkan

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "python", "results", "metrics_raw.csv")
OUT = os.path.join(HERE, "..", "results", "efek_tabel3_4.csv")

data = defaultdict(lambda: defaultdict(list))
with open(SRC) as f:
    for r in csv.DictReader(f):
        for k in ("nadir_Hz", "maxRoCoF_Hzps", "Pp2p_pu", "eMPP_pu_s", "eBESS_pu_s"):
            data[(r["scenario"], r["controller"])][k].append(float(r[k]))

with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["scenario", "baseline", "metric", "median_proposed", "median_baseline",
                "median_diff", "ci95_lo", "ci95_hi", "cliffs_delta", "p_mannwhitney"])
    for scn in ("S1", "S2", "S3", "S4", "S5"):
        a = data[(scn, "adaptive")]
        for base in ("adaptgain", "smoothstatic", "static", "droop"):
            b = data[(scn, base)]
            for k in ("nadir_Hz", "maxRoCoF_Hzps", "Pp2p_pu", "eMPP_pu_s", "eBESS_pu_s"):
                if base == "droop" and k == "eBESS_pu_s":
                    continue
                r = bandingkan(np.array(a[k]), np.array(b[k]), paired=False)
                w.writerow([scn, base, k, np.median(a[k]), np.median(b[k]), r["med_diff"],
                            r["ci_lo"], r["ci_hi"], r["cliff"], r["p"]])
                print(f"{scn} {base:12s} {k:13s} dmed={r['med_diff']:+.4f} "
                      f"[{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] delta={r['cliff']:+.2f}")
print("->", OUT)
