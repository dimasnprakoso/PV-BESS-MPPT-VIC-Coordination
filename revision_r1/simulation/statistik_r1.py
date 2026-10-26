# -*- coding: utf-8 -*-
"""Effect sizes for revision R1 (Reviewer 2 comment 6): median difference + bootstrap CI, Cliff's delta."""
import numpy as np
from scipy.stats import wilcoxon


def cliffs_delta(a, b):
    """delta = P(a > b) - P(a < b), semua pasangan (tak berpasangan)."""
    a = np.asarray(a)[:, None]; b = np.asarray(b)[None, :]
    return float((a > b).mean() - (a < b).mean())


def boot_ci(a, b, paired=True, n_boot=10000, seed=0, q=(2.5, 97.5)):
    """Selisih median (a - b) dan CI bootstrap persentil 95 %."""
    rng = np.random.default_rng(seed)
    a = np.asarray(a); b = np.asarray(b)
    if paired:
        d = a - b
        idx = rng.integers(0, d.size, (n_boot, d.size))
        bs = np.median(d[idx], axis=1)
        est = float(np.median(d))
    else:
        ia = rng.integers(0, a.size, (n_boot, a.size))
        ib = rng.integers(0, b.size, (n_boot, b.size))
        bs = np.median(a[ia], axis=1) - np.median(b[ib], axis=1)
        est = float(np.median(a) - np.median(b))
    lo, hi = np.percentile(bs, q)
    return est, float(lo), float(hi)


def bandingkan(a, b, paired=True):
    """Ringkasan perbandingan a (varian) terhadap b (acuan)."""
    est, lo, hi = boot_ci(a, b, paired=paired)
    d = np.asarray(a) - np.asarray(b)
    if paired:
        p = wilcoxon(a, b).pvalue if np.any(d != 0) else 1.0
    else:
        from scipy.stats import mannwhitneyu
        p = mannwhitneyu(a, b).pvalue
    return dict(med_diff=est, ci_lo=lo, ci_hi=hi, cliff=cliffs_delta(a, b), p=float(p))
