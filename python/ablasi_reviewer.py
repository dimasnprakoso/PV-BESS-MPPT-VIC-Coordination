# -*- coding: utf-8 -*-
"""
Ablation of the coordination law (revision R1, Reviewer 2 comment 2), on the averaged model fullmodel.py.

A1 Which element of the law produces the benefit?
   - adaptive     : proposed scheme (knee gains), reference
   - smooth025    : fixed-gain VIC + NON-adaptive tanh droop rated 0.25 pu (= proposed beta_max);
                    tests whether the battery saving comes only from the lower cap
   - noalpha      : proposed gate + knee VIC with a fixed weight w = 1 (no alpha)
   - novic        : proposed gate only, without the VIC term (w = 0)
   - smoothstatic : evaluation baseline (rating 0.4 pu), for comparison
   Relay variants (does the limit cycle persist?):
   - static_m015  : static relay with a 0.15-pu quantum (close to the deficit)
   - static_hyst  : static 0.4-pu relay with genuine hysteresis
                    (on at Dw < -0.02, off when Dw > -0.01)
A5 Sensitivity of the relay f_osc and P_p2p to tau_inv and tau_pll (nominal S5).

All controllers in a scenario use the SAME xi draws (common random numbers, seed 11),
so the paired Wilcoxon signed-rank test is valid.
"""
import csv
import os
import time

import numpy as np
from scipy.stats import wilcoxon

import fullmodel as fm

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
N_R = 100
_orig_simulate = fm.simulate


def lc_detect(p2p, fosc, th=0.01):
    """Aturan deteksi naskah: P_p2p > th, f_osc > 1 Hz, bukan harmonik riak P&O (12,5 Hz)."""
    po = (np.abs(fosc / 12.5 - np.round(fosc / 12.5)) * 12.5 < 0.5) & (fosc >= 12.0)
    return (p2p > th) & (fosc > 1.0) & ~po


def run_variant(scn, name, xi):
    """Jalankan satu varian dengan menambal fungsi simulate secara terkendali."""
    knee = dict(fm.KNEE)
    m_relay, hyst = fm.M_RELAY, fm.HYST
    if name in ("adaptive", "smoothstatic", "static"):
        return _orig_simulate(scn, name, xi)[0]
    if name == "smooth025":
        fm.M_RELAY = knee["beta_max"]
        try:
            return _orig_simulate(scn, "smoothstatic", xi)[0]
        finally:
            fm.M_RELAY = m_relay
    if name == "static_m015":
        fm.M_RELAY = 0.15
        try:
            return _orig_simulate(scn, "static", xi)[0]
        finally:
            fm.M_RELAY = m_relay
    if name in ("noalpha", "novic"):
        # alpha dipaksa konstan lewat ka = kaw = 0 (w = 1 - 1/1 = 0) -> novic;
        # untuk noalpha bobot w = 1 dicapai dengan ka sangat besar.
        if name == "novic":
            fm.KNEE.update(ka=0.0, kaw=0.0)
        else:
            fm.KNEE.update(ka=1e12, kaw=1e12)
        try:
            return _orig_simulate(scn, "adaptive", xi)[0]
        finally:
            fm.KNEE.clear(); fm.KNEE.update(knee)
    if name == "static_hyst":
        return simulate_hyst(scn, xi)
    raise ValueError(name)


def simulate_hyst(scn, xi):
    """Relai statis dengan histeresis sungguhan: aktif bila Dwf < -h_on, padam bila Dwf > -h_off."""
    h_on, h_off = 0.02, 0.01
    # implementasi: salin logika static, tetapi status relai diingat antarlangkah.
    H, DPL, SOC0, Gjit, Tc = (xi[k] for k in ("H", "DPL", "SOC0", "Gjit", "Tc"))
    n = H.size
    Dw = np.zeros(n); Pinj = np.zeros(n); Dwf = np.zeros(n)
    soc = SOC0.copy(); st = np.zeros(n)
    Vpv = np.full(n, 0.80 * fm.VOC_CELL * fm.NS); dV = np.full(n, fm.MPPT_STEP)
    Ppv_prev = np.zeros(n); Psched = np.zeros(n)
    k_sched = int(1.5 / fm.DT); every = int(fm.MPPT_DT / fm.DT)
    maxDw = np.zeros(n); maxroc = np.zeros(n); e_mpp = np.zeros(n); e_bat = np.zeros(n)
    i0 = int(0.75 * fm.N_STEP); seg = np.empty((fm.N_STEP - i0, n))
    for k in range(fm.N_STEP):
        t = k * fm.DT
        if k % every == 0:
            G = fm.g_profile(scn, t, Gjit)
            Ppv = Vpv * fm.pv_current(Vpv, G, Tc) * fm.PV_SCALE
            dV = np.where(Ppv >= Ppv_prev, dV, -dV)
            Vpv = np.clip(Vpv + dV, 0.55 * fm.VOC_CELL * fm.NS, 0.95 * fm.VOC_CELL * fm.NS)
            Ppv_prev = Ppv
        Pmppt = Ppv / fm.S_BASE
        rocof = (Dw - Dwf) / fm.TAU_PLL
        np.maximum(maxroc, np.abs(rocof), out=maxroc)
        phi_d = np.clip((soc - fm.SOC_MIN) / fm.SOC_TAPER, 0.0, 1.0)
        phi_c = np.clip((fm.SOC_MAX - soc) / fm.SOC_TAPER, 0.0, 1.0)
        Pvic = -(fm.VIC_FIX["Kd"] * Dwf + fm.VIC_FIX["Kj"] * rocof)
        # histeresis dua sisi
        st = np.where(Dwf < -h_on, 1.0, np.where(Dwf > h_on, -1.0, st))
        st = np.where((st > 0) & (Dwf > -h_off), 0.0, st)
        st = np.where((st < 0) & (Dwf < h_off), 0.0, st)
        Pbat = fm.M_RELAY * st * np.where(st > 0, phi_d, phi_c)
        Pref = Pmppt + Pvic + Pbat
        e_mpp += fm.DT * np.abs(Pvic + Pbat); e_bat += fm.DT * np.abs(Pbat)
        Pb_W = Pbat * fm.S_BASE
        soc = np.clip(soc - fm.DT * np.where(Pb_W > 0, Pb_W / fm.ETA_D, Pb_W * fm.ETA_C) / fm.E_RATED, 0, 1)
        if k == k_sched:
            Psched = Pinj.copy()
        dist = DPL if (scn not in ("S1", "S2") and t >= 2.0) else np.zeros(n)
        Pinj += fm.DT * (np.clip(Pref, -1.2, 1.2) - Pinj) / fm.TAU_INV
        if k >= k_sched:
            Dw += fm.DT * ((Pinj - Psched) - dist - 1.0 * Dw) / (2.0 * H)
        Dwf += fm.DT * (Dw - Dwf) / fm.TAU_PLL
        np.maximum(maxDw, np.abs(Dw), out=maxDw)
        if k >= i0:
            seg[k - i0] = Pinj
    p2p = seg.max(axis=0) - seg.min(axis=0)
    segz = seg - seg.mean(axis=0)
    amp = np.abs(np.fft.rfft(segz * np.hanning(segz.shape[0])[:, None], axis=0))
    fr = np.fft.rfftfreq(segz.shape[0], fm.DT)
    fosc = fr[np.argmax(amp[1:], axis=0) + 1]
    return dict(nadir_Hz=fm.F0 - fm.F0 * maxDw, maxRoCoF_Hzps=fm.F0 * maxroc,
                Pp2p_pu=p2p, fosc_Hz=fosc, eMPP_pu_s=e_mpp, eBESS_pu_s=e_bat)


if __name__ == "__main__":
    t0 = time.time()
    fm.rng = np.random.default_rng(11)
    varian = ["adaptive", "smooth025", "noalpha", "novic", "smoothstatic",
              "static", "static_m015", "static_hyst"]
    hasil = {}
    rows = []
    for scn in ["S3", "S4", "S5"]:
        xi = fm.draw_xi(N_R, scn)
        for v in varian:
            m = run_variant(scn, v, xi)
            hasil[(scn, v)] = m
            det = int(lc_detect(m["Pp2p_pu"], m["fosc_Hz"]).sum())
            for j in range(N_R):
                rows.append([scn, v, j] + [float(m[k][j]) for k in
                            ("nadir_Hz", "maxRoCoF_Hzps", "Pp2p_pu", "fosc_Hz", "eMPP_pu_s", "eBESS_pu_s")])
            print(f"{scn} {v:12s} nadir={np.mean(m['nadir_Hz']):.3f}±{np.std(m['nadir_Hz']):.3f} "
                  f"RoCoF={np.mean(m['maxRoCoF_Hzps']):.3f} Pp2p={np.mean(m['Pp2p_pu']):.4f} "
                  f"fosc~{np.median(m['fosc_Hz']):.2f} eBESS={np.mean(m['eBESS_pu_s']):.3f} "
                  f"eMPP={np.mean(m['eMPP_pu_s']):.3f} LC={det}/100", flush=True)
    with open(os.path.join(RES, "ablasi_raw.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "variant", "real", "nadir_Hz", "maxRoCoF_Hzps", "Pp2p_pu",
                    "fosc_Hz", "eMPP_pu_s", "eBESS_pu_s"])
        w.writerows(rows)

    print("\n=== uji berpasangan (Wilcoxon signed-rank) terhadap skema usulan ===")
    for scn in ["S3", "S4", "S5"]:
        a = hasil[(scn, "adaptive")]
        for v in ("smooth025", "noalpha", "novic", "smoothstatic"):
            b = hasil[(scn, v)]
            for key in ("nadir_Hz", "eBESS_pu_s", "eMPP_pu_s", "maxRoCoF_Hzps"):
                d = b[key] - a[key]
                p = wilcoxon(b[key], a[key]).pvalue if np.any(d != 0) else 1.0
                rel = 100 * np.mean(d) / np.mean(a[key]) if key != "nadir_Hz" else np.nan
                print(f"{scn} {v:12s} {key:13s} usulan={np.mean(a[key]):.3f} varian={np.mean(b[key]):.3f} "
                      f"selisih={np.mean(d):+.3f}" + ("" if np.isnan(rel) else f" ({rel:+.1f}%)") + f" p={p:.1e}")

    print("\n=== A5: sensitivitas relai statis & usulan terhadap tau_inv, tau_pll (S5 nominal) ===")
    sens = []
    ti0, tp0 = fm.TAU_INV, fm.TAU_PLL
    for ti in (0.02, 0.035, 0.05, 0.075, 0.10):
        for tp in (0.01, 0.02, 0.04):
            fm.TAU_INV, fm.TAU_PLL = ti, tp
            ms = _orig_simulate("S5", "static", fm.xi_nominal())[0]
            ma = _orig_simulate("S5", "adaptive", fm.xi_nominal())[0]
            r = [ti, tp, float(ms["Pp2p_pu"][0]), float(ms["fosc_Hz"][0]), bool(lc_detect(ms["Pp2p_pu"], ms["fosc_Hz"])[0]),
                 float(ma["Pp2p_pu"][0]), float(ma["fosc_Hz"][0]), bool(lc_detect(ma["Pp2p_pu"], ma["fosc_Hz"])[0])]
            sens.append(r)
            print("tau_inv=%.3f tau_pll=%.3f | relai Pp2p=%.3f f=%.2f LC=%s | usulan Pp2p=%.4f f=%.2f LC=%s" % tuple(r), flush=True)
    fm.TAU_INV, fm.TAU_PLL = ti0, tp0
    with open(os.path.join(RES, "sens_tau.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tau_inv", "tau_pll", "static_Pp2p", "static_fosc", "static_LC",
                    "adaptive_Pp2p", "adaptive_fosc", "adaptive_LC"])
        w.writerows(sens)
    print(f"\nselesai {time.time() - t0:.0f} s")
