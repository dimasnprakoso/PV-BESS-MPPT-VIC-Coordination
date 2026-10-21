# -*- coding: utf-8 -*-
"""
Uji signifikansi kampanye (n=100): Mann-Whitney/Wilcoxon rank-sum dua-sisi,
proposed (adaptive) vs tiap baseline, per skenario, pada nadir, Pp2p,
eBESS, eMPP. Sumber: results/metrics_raw.csv.
"""
import csv
import os
from collections import defaultdict
from scipy.stats import mannwhitneyu

d = defaultdict(list)
with open(os.path.join(os.path.dirname(__file__), "results", "metrics_raw.csv")) as f:
    for r in csv.DictReader(f):
        d[(r["scenario"], r["controller"])].append(
            (float(r["nadir_Hz"]), float(r["Pp2p_pu"]),
             float(r["eBESS_pu_s"]), float(r["eMPP_pu_s"])))

MET = {"nadir": 0, "Pp2p": 1, "eBESS": 2, "eMPP": 3}
BASES = ["adaptgain", "smoothstatic", "static", "droop"]
for sc in ["S2", "S3", "S4", "S5"]:
    for base in BASES:
        for m, col in MET.items():
            if m in ("eBESS", "eMPP") and base == "droop":
                continue
            a = [x[col] for x in d[(sc, "adaptive")]]
            b = [x[col] for x in d[(sc, base)]]
            res = mannwhitneyu(a, b, alternative="two-sided", method="auto")
            n2 = len(a) * len(b)
            sep = "SEPARASI-PENUH" if res.statistic in (0, n2) else ""
            arah = "adaptive>" if res.statistic > n2 / 2 else "adaptive<"
            print(f"{sc} {m:6s} vs {base:12s}: U={res.statistic:6.0f} "
                  f"p={res.pvalue:.2e} {arah} {sep}")
