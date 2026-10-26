# -*- coding: utf-8 -*-
"""
Metrics and figure of the switching-level testbed runs (revision R1, Reviewer 2 comment 3).
Reads hasil_S5_mode{0,1,2,3}.mat. Metrics as in the averaged model: nadir, max |RoCoF| (derivative of
f_grid, 20-ms filter), P_p2p and f_osc in the last 2-s steady-state window, battery throughput since the
event (pu*s on S_g), limit-cycle detection: P_p2p > 0.01 pu, f_osc > 2/T_w, not the P&O ripple.
Before P_p2p and f_osc, P is low-pass filtered (2nd-order Butterworth, 25 Hz, filtfilt, zero phase):
the switching model contains harmonic/switching ripple (~100-150 Hz) that is absent from the averaged
model and is not a limit cycle; the 0-25 Hz band holds all relevant electromechanical and control
dynamics. The unfiltered P_p2p is reported as well.
"""
from scipy.signal import butter, filtfilt
import os
import sys

import numpy as np
import scipy.io as sio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "..", "results")
GBR = os.path.join(HERE, "..", "..", "..", "figures")
os.makedirs(GBR, exist_ok=True)
S_G, T_EVT, WIN = 100e3, 2.0, 2.0
NAMA = {0: "no support", 1: "proposed (adaptive)", 2: "static relay (paper)", 3: "relay at 49.7 Hz"}
WARNA = {0: "0.45", 1: "tab:blue", 2: "tab:red", 3: "tab:orange"}


def muat(m):
    p = os.path.join(HERE, f"hasil_S5_mode{m}.mat")
    if not os.path.exists(p):
        return None
    S = sio.loadmat(p, squeeze_me=True)["S"]
    return {k: np.asarray(S[k].item(), float).ravel() for k in S.dtype.names}


def metrik(d):
    t, f, P, Pb = d["t"], d["fgrid"], d["Pg"] / S_G, d["Pbat"] / S_G
    dt = np.median(np.diff(t))
    a = dt / 0.02
    ff = np.copy(f)
    for i in range(1, ff.size):
        ff[i] = ff[i - 1] + a * (f[i] - ff[i - 1])
    roc = np.gradient(ff, dt)
    pasca = t >= T_EVT
    w = t >= t[-1] - WIN
    p2p_mentah = P[w].max() - P[w].min()
    bb, aa = butter(2, 25.0 / (0.5 / dt))
    P = filtfilt(bb, aa, P)
    seg = P[w] - P[w].mean()
    amp = np.abs(np.fft.rfft(seg * np.hanning(seg.size)))
    fr = np.fft.rfftfreq(seg.size, dt)
    fosc = fr[np.argmax(amp[1:]) + 1]
    p2p = P[w].max() - P[w].min()
    po = abs(fosc / 12.5 - round(fosc / 12.5)) * 12.5 < 0.5 and fosc >= 12.0
    return dict(nadir=f[pasca].min(), rocof=np.abs(roc[pasca]).max(), p2p=p2p, fosc=fosc,
                lc=bool(p2p > 0.01 and fosc > 2 / WIN and not po),
                ebess=np.sum(np.abs(Pb[pasca])) * dt, f_ss=f[w].mean(), p2p_mentah=p2p_mentah)


if __name__ == "__main__":
    D = {m: muat(m) for m in NAMA}
    baris = []
    for m, d in D.items():
        if d is None:
            print(f"mode {m}: belum ada"); continue
        r = metrik(d)
        baris.append((m, r))
        print(f"{NAMA[m]:22s} nadir={r['nadir']:.3f} Hz |RoCoF|={r['rocof']:.3f} Hz/s "
              f"P_p2p={r['p2p']:.4f} pu (mentah {r['p2p_mentah']:.3f}) f_osc={r['fosc']:.2f} Hz LC={r['lc']} "
              f"eBESS={r['ebess']:.3f} pu*s f_tunak={r['f_ss']:.3f} Hz")
    with open(os.path.join(OUT, "testbed_switching_metrik.csv"), "w") as fh:
        fh.write("mode,controller,nadir_Hz,maxRoCoF_Hzps,Pp2p_pu_lp25,Pp2p_pu_raw,fosc_Hz,LC,eBESS_pu_s,f_ss_Hz\n")
        for m, r in baris:
            fh.write(f"{m},{NAMA[m]},{r['nadir']:.4f},{r['rocof']:.4f},{r['p2p']:.5f},{r['p2p_mentah']:.5f},{r['fosc']:.2f},"
                     f"{r['lc']},{r['ebess']:.4f},{r['f_ss']:.4f}\n")
    # figur
    fig, ax = plt.subplots(3, 1, figsize=(7.0, 7.2), sharex=True)
    for m, d in D.items():
        if d is None:
            continue
        k = (d["t"] >= 1.5) & (d["t"] <= d["t"][-1] - 0.01)   # buang tepi rerata bergerak
        lw = 1.6 if m in (1, 2) else 1.2
        ax[0].plot(d["t"][k], d["fgrid"][k], color=WARNA[m], lw=lw, label=NAMA[m])
        rata = lambda x: np.convolve(x, np.ones(10) / 10, mode="same")   # rerata bergerak 10 ms
        ax[1].plot(d["t"][k], rata(d["Pg"])[k] / 1e3, color=WARNA[m], lw=lw)
        ax[2].plot(d["t"][k], rata(d["Pbat"])[k] / 1e3, color=WARNA[m], lw=lw)
    ax[0].set_ylabel("Grid frequency (Hz)"); ax[1].set_ylabel("Grid power (kW)\n10-ms average")
    ax[2].set_ylabel("Battery power (kW)\n10-ms average"); ax[2].set_xlabel("Time (s)")
    for a, lab in zip(ax, "abc"):
        a.grid(alpha=0.3); a.set_title(f"({lab})", fontsize=11, loc="left")
        a.tick_params(labelsize=10); a.yaxis.label.set_size(11)
    ax[2].xaxis.label.set_size(11)
    ax[0].legend(fontsize=9, loc="lower right", ncol=2)
    fig.tight_layout()
    for ext, kw in (("pdf", {}), ("png", {"dpi": 600}), ("svg", {})):
        fig.savefig(os.path.join(GBR, f"testbed_S5.{ext}"), **kw)
    print("figur ->", os.path.join(GBR, "testbed_S5.*"))
