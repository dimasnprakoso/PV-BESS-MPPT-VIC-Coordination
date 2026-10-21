# -*- coding: utf-8 -*-
"""
Model penuh AVERAGED dua-tahap PV-BESS grid-connected (Python) — Paper Studi 1.

Komponen:
  - PV array single-diode 5-parameter (skala 100 kW), Newton 3-iterasi utk I(V)
  - MPPT Perturb & Observe (langkah 0,5 V tiap 20 ms) pada tegangan array
  - BESS: SOC (efisiensi, batas), faktor ketersediaan Phi_SOC taper dekat batas
  - Inverter: lag orde-1 (tau_inv) + saturasi daya
  - PLL: filter frekuensi orde-1 (tau_pll)
  - Grid agregat: persamaan ayun 2H dDw/dt = P_inj - P_load - D*Dw  (pu, S_base)
  - VIC: P_vic = -(Kd*Dw_f + Kj*dDw_f/dt)
  - Koordinasi (5 kontroler):
      * adaptive     : alpha severity-aware + gating tanh ber-SOC (USULAN paper)
      * adaptgain    : VIC gain-adaptif (alternating inertia) + relay BESS
      * smoothstatic : VIC gain tetap + BESS droop tanh halus NON-adaptif
      * static       : VIC gain tetap + relay BESS histeresis (konvensional)
      * droop        : hanya suku Kd (tanpa inersia), tanpa BESS-freq support

Kampanye: skenario S1-S5 x 3 kontroler x N_R realisasi Monte Carlo
Keluaran : results/metrics_summary.csv, results/metrics_raw.csv,
           ../figures/fullpy_S2.pdf, fullpy_S3.pdf, fullpy_S5.pdf,
           ../figures/fullpy_sens.pdf, trajektori referensi utk cross-impl Julia.
"""
import os
import time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
# WAJIB. Bawaan matplotlib menanam fon sebagai Type 3, yang ditolak
# IEEE PDF eXpress dan disorot banyak sistem submisi jurnal. 42 memaksa
# TrueType. Jangan dihapus.
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
FIG = os.path.join(HERE, "..", "figures")
os.makedirs(RES, exist_ok=True)
os.makedirs(FIG, exist_ok=True)

rng = np.random.default_rng(7)

# ================================================================ parameter
S_BASE = 100e3          # basis daya [W]
F0     = 50.0

# PV single-diode (array 100 kW: ~250 string paralel modul 400 W)
NS, NP   = 2 * 72, 250          # sel seri (2 modul), string paralel  (agregat)
ISC_STC  = 10.36 * NP           # arus hubung singkat array [A]
VOC_CELL = 0.72                 # tegangan open-circuit per sel [V]
KI_T     = 0.0005               # koef. arus thd suhu [/K]
A_DIODE  = 1.1
Q, KB    = 1.602e-19, 1.381e-23
RS_ARR   = 0.35 / NP * NS / 144.0   # resistansi seri agregat sederhana [ohm]

TAU_INV, TAU_PLL = 0.05, 0.02
DT, T_END = 1e-4, 8.0
N_STEP = int(T_END / DT)
MPPT_DT = 0.02
MPPT_STEP = 1.0                 # langkah perturbasi [V]

# gain knee-point PRODUKSI (NSGA-II POP=60/GEN=80/N_MC=200, CVaR 0.95)
KNEE = dict(Kd=1.0045, Kj=0.0317, ka=47.483, kaw=1.0, kb=45.797, beta_max=0.2497)
VIC_FIX = dict(Kd=0.50, Kj=0.10)      # VIC konvensional gain tetap
DROOP  = dict(Kd=0.50)
M_RELAY, HYST = 0.40, 0.02            # relay BESS statis [pu], histeresis [Hz-eq pu]

E_RATED = 50e3 * 3600.0               # [J]
ETA_C = ETA_D = 0.95
SOC_MIN, SOC_MAX = 0.20, 0.90
SOC_TAPER = 0.05                      # lebar taper Phi_SOC dekat batas

# ================================================================ PV & MPPT
def pv_current(V, G, Tc):
    """Arus array (vektor) via Newton 3 iterasi pada model single-diode."""
    Vt = A_DIODE * KB * (273.15 + Tc) / Q * NS
    Iph = ISC_STC * (G / 1000.0) * (1.0 + KI_T * (Tc - 25.0))
    Io = ISC_STC * np.exp(-VOC_CELL * NS / Vt)
    I = np.maximum(Iph - Io * (np.exp(V / Vt) - 1.0), 0.0)
    for _ in range(3):
        f = Iph - Io * (np.exp((V + I * RS_ARR) / Vt) - 1.0) - I
        df = -Io * np.exp((V + I * RS_ARR) / Vt) * RS_ARR / Vt - 1.0
        I = np.maximum(I - f / df, 0.0)
    return I


# Kalibrasi-mandiri: skala array agar P_MPP(STC) = 0,95 pu dari S_BASE
_Vscan = np.linspace(0.55 * VOC_CELL * NS, 0.95 * VOC_CELL * NS, 200)
_Pscan = _Vscan * pv_current(_Vscan, 1000.0, 25.0)
PV_SCALE = 0.95 * S_BASE / float(np.max(_Pscan))


# ================================================================ kampanye
def g_profile(name, t, jit):
    """Iradiansi (skalar waktu, vektor realisasi via jitter)."""
    if name == "S2":  # cloud passing 1000 -> 300 -> 1000 (ramp 0,5 s)
        if t < 2.0: g = 1000.0
        elif t < 2.5: g = 1000.0 - 1400.0 * (t - 2.0)
        elif t < 5.0: g = 300.0
        elif t < 5.5: g = 300.0 + 1400.0 * (t - 5.0)
        else: g = 1000.0
    else:
        g = 1000.0
    return g * jit


def simulate(scn, ctrl, xi, save_traj=False):
    """Satu batch realisasi (vektor). xi: dict array (H, DPL, SOC0, Gjit, Tc)."""
    H, DPL, SOC0, Gjit, Tc = (xi[k] for k in ("H", "DPL", "SOC0", "Gjit", "Tc"))
    n = H.size
    Dw = np.zeros(n); Pinj = np.zeros(n); Dwf = np.zeros(n)
    soc = SOC0.copy()
    relay = np.ones(n)
    Vpv = np.full(n, 0.80 * VOC_CELL * NS)   # mulai dekat MPP
    dV = np.full(n, MPPT_STEP)
    Ppv_prev = np.zeros(n)
    t_evt = 2.0
    k_sched = int(1.5 / DT)          # titik "jadwal": MPPT dianggap settle
    Psched = np.zeros(n)
    mppt_every = int(MPPT_DT / DT)

    maxDw = np.zeros(n); minDw = np.zeros(n); maxroc = np.zeros(n)
    e_mpp = np.zeros(n); e_bat = np.zeros(n)
    i0 = int(0.75 * N_STEP)                  # jendela tunak 6-8 s
    seg_min = np.full(n, np.inf); seg_max = np.full(n, -np.inf)
    seg = np.empty((N_STEP - i0, n)) if True else None
    traj = np.empty((N_STEP, 2)) if save_traj else None   # (Pinj, Dw) realisasi-0
    ts_idx = np.zeros(n)

    for k in range(N_STEP):
        t = k * DT
        # ---------- PV + MPPT (kuasi-statis)
        if k % mppt_every == 0:
            G = g_profile(scn, t, Gjit)
            Ipv = pv_current(Vpv, G, Tc)
            Ppv = Vpv * Ipv * PV_SCALE
            better = Ppv >= Ppv_prev
            dV = np.where(better, dV, -dV)
            Vpv = np.clip(Vpv + dV, 0.55 * VOC_CELL * NS, 0.95 * VOC_CELL * NS)
            Ppv_prev = Ppv
        Pmppt = Ppv / S_BASE                                  # [pu]

        # ---------- PLL + VIC
        rocof = (Dw - Dwf) / TAU_PLL
        np.maximum(maxroc, np.abs(rocof), out=maxroc)

        # ---------- Phi_SOC (taper dua sisi)
        phi_d = np.clip((soc - SOC_MIN) / SOC_TAPER, 0.0, 1.0)   # discharge avail
        phi_c = np.clip((SOC_MAX - soc) / SOC_TAPER, 0.0, 1.0)   # charge avail

        if ctrl == "adaptive":
            Pvic = -(KNEE["Kd"] * Dwf + KNEE["Kj"] * rocof)
            alpha = 1.0 / (1.0 + KNEE["ka"] * np.abs(Dwf) + KNEE["kaw"] * np.abs(rocof))
            w = 1.0 - alpha
            raw = KNEE["beta_max"] * np.tanh(KNEE["kb"] * (-Dwf))
            Pbat = np.where(raw >= 0, raw * phi_d, raw * phi_c)
            Pref = Pmppt + w * Pvic + Pbat
            e_mpp += DT * np.abs(w * Pvic + Pbat)
        elif ctrl == "static":
            # relay 3-keadaan dengan dead-band (bang-bang rule-based klasik):
            # discharge penuh bila f rendah, charge penuh bila f tinggi, diam
            # di dalam dead-band — sumber chattering/limit-cycle.
            Pvic = -(VIC_FIX["Kd"] * Dwf + VIC_FIX["Kj"] * rocof)
            state = np.where(Dwf < -HYST, 1.0, np.where(Dwf > HYST, -1.0, 0.0))
            Pbat = M_RELAY * state * np.where(state > 0, phi_d, phi_c)
            Pref = Pmppt + Pvic + Pbat
            e_mpp += DT * np.abs(Pvic + Pbat)
        elif ctrl == "adaptgain":
            # baseline SOTA: VIC gain-adaptif (representatif alternating-inertia
            # Alipoor 2015 / adaptive inertia-damping Tian 2023): inersia diperbesar
            # saat menjauh dari nominal (Dwf*rocof>0), diperkecil saat kembali;
            # redaman naik dgn |Dwf|. Koordinasi tetap statis (jumlah + relay BESS)
            # -> mengisolasi adaptasi-GAIN vs adaptasi-KOORDINASI (usulan).
            accel = (Dwf * rocof) > 0
            Kj_eff = np.where(accel, 3.0 * VIC_FIX["Kj"], 0.5 * VIC_FIX["Kj"])
            Kd_eff = VIC_FIX["Kd"] * (1.0 + 2.0 * np.minimum(np.abs(Dwf) / 0.01, 1.0))
            Pvic = -(Kd_eff * Dwf + Kj_eff * rocof)
            state = np.where(Dwf < -HYST, 1.0, np.where(Dwf > HYST, -1.0, 0.0))
            Pbat = M_RELAY * state * np.where(state > 0, phi_d, phi_c)
            Pref = Pmppt + Pvic + Pbat
            e_mpp += DT * np.abs(Pvic + Pbat)
        elif ctrl == "smoothstatic":
            # baseline halus NON-adaptif: VIC gain tetap + BESS droop tanh
            # saturasi (rating M_RELAY, slope gate knee, taper SOC sama) —
            # mengisolasi KEHALUSAN dispatch dari ADAPTIVITAS koordinasi.
            Pvic = -(VIC_FIX["Kd"] * Dwf + VIC_FIX["Kj"] * rocof)
            raw = M_RELAY * np.tanh(KNEE["kb"] * (-Dwf))
            Pbat = np.where(raw >= 0, raw * phi_d, raw * phi_c)
            Pref = Pmppt + Pvic + Pbat
            e_mpp += DT * np.abs(Pvic + Pbat)
        else:  # droop
            Pvic = -(DROOP["Kd"] * Dwf)
            Pbat = np.zeros(n)
            Pref = Pmppt + Pvic
            e_mpp += DT * np.abs(Pvic)
        e_bat += DT * np.abs(Pbat)

        # ---------- SOC
        Pb_W = Pbat * S_BASE
        dis = Pb_W > 0
        soc = soc - DT * np.where(dis, Pb_W / ETA_D, Pb_W * ETA_C) / E_RATED
        soc = np.clip(soc, 0.0, 1.0)

        # ---------- inverter + grid (frame deviasi terhadap jadwal)
        # P_sched = keluaran MPP saat sistem sudah settle (t_sched); sebelum itu
        # jaringan dianggap seimbang (inisialisasi MPPT).
        if k == k_sched:
            Psched = Pinj.copy()
        dist = DPL if (scn != "S1" and scn != "S2" and t >= t_evt) else np.zeros(n)
        Pinj += DT * (np.clip(Pref, -1.2, 1.2) - Pinj) / TAU_INV
        if k >= k_sched:
            Dw += DT * ((Pinj - Psched) - dist - 1.0 * Dw) / (2.0 * H)
        Dwf += DT * (Dw - Dwf) / TAU_PLL

        np.minimum(minDw, Dw, out=minDw)
        np.maximum(maxDw, np.abs(Dw), out=maxDw)
        out_band = np.abs(Dw) > 0.4e-2
        ts_idx = np.where(out_band, k, ts_idx)
        if k >= i0:
            np.minimum(seg_min, Pinj, out=seg_min)
            np.maximum(seg_max, Pinj, out=seg_max)
            seg[k - i0] = Pinj
        if save_traj:
            traj[k, 0] = Pinj[0]; traj[k, 1] = Dw[0]

    # ---------- metrik
    p2p = seg_max - seg_min
    segz = seg - seg.mean(axis=0)
    w_h = np.hanning(segz.shape[0])[:, None]
    amp = 2.0 / segz.shape[0] * np.abs(np.fft.rfft(segz * w_h, axis=0))
    fr = np.fft.rfftfreq(segz.shape[0], DT)
    fosc = fr[np.argmax(amp[1:], axis=0) + 1]
    m = dict(
        nadir_Hz=F0 - F0 * maxDw,
        maxRoCoF_Hzps=F0 * maxroc,
        ts_s=ts_idx * DT,
        Pp2p_pu=p2p, fosc_Hz=fosc,
        eMPP_pu_s=e_mpp, eBESS_pu_s=e_bat,
    )
    return m, traj


def draw_xi(n, scn):
    H = rng.uniform(1.5, 4.0, n)
    if scn == "S4":
        H = rng.uniform(0.5, 1.0, n)      # inersia rendah
    DPL = rng.uniform(0.05, 0.15, n)
    if scn == "S6":
        # PELEPASAN BEBAN: gangguan bertanda NEGATIF sehingga frekuensi NAIK dan
        # cabang PENGISIAN pada Pers. (4) benar-benar diuji. Tanpa skenario ini
        # konverter dua-arah pada Gambar 1 tergambar tanpa pernah terbukti: pada
        # S1-S5 seluruh gangguan menurunkan frekuensi, sehingga beta selalu
        # berada di cabang pelepasan. Tanda dibalik dari undian yang sama supaya
        # jumlah tarikan RNG tidak berubah dan hasil S1-S5 tetap bit-identik.
        DPL = -DPL
    return dict(
        H=H,
        DPL=DPL,
        SOC0=rng.uniform(0.30, 0.80, n),
        Gjit=rng.uniform(0.95, 1.05, n),
        Tc=rng.uniform(22.0, 30.0, n),    # rentang suhu Madiun
    )


def xi_nominal(n=1):
    return dict(H=np.full(n, 2.0), DPL=np.full(n, 0.10), SOC0=np.full(n, 0.60),
                Gjit=np.ones(n), Tc=np.full(n, 28.0))


# ================================================================ main
if __name__ == "__main__":
    t0 = time.time()
    N_R = 100
    # S6 SENGAJA TIDAK dimasukkan kampanye utama: metrik nadir_Hz dihitung dari
    # max|Dw| sehingga untuk peristiwa LEBIH-frekuensi kolom itu akan mencetak
    # angka di bawah 50 Hz padahal frekuensi NAIK -- menyesatkan. S6 dijalankan
    # sebagai uji terarah oleh python/uji_s6_charging.py.
    scens = ["S1", "S2", "S3", "S4", "S5"]
    ctrls = ["adaptive", "adaptgain", "smoothstatic", "static", "droop"]
    rows = []
    raw_rows = []
    for scn in scens:
        for ctrl in ctrls:
            xi = draw_xi(N_R, scn)
            m, _ = simulate(scn, ctrl, xi)
            for j in range(N_R):
                raw_rows.append([scn, ctrl, j] + [float(m[k][j]) for k in
                    ("nadir_Hz", "maxRoCoF_Hzps", "ts_s", "Pp2p_pu", "fosc_Hz",
                     "eMPP_pu_s", "eBESS_pu_s")])
            rows.append([scn, ctrl] + sum(
                ([float(np.mean(m[k])), float(np.std(m[k]))] for k in
                 ("nadir_Hz", "maxRoCoF_Hzps", "ts_s", "Pp2p_pu", "fosc_Hz",
                  "eMPP_pu_s", "eBESS_pu_s")), []))
            print(f"{scn} {ctrl:9s} | nadir={np.mean(m['nadir_Hz']):7.3f} Hz "
                  f"| RoCoF={np.mean(m['maxRoCoF_Hzps']):6.3f} Hz/s "
                  f"| Pp2p={np.mean(m['Pp2p_pu']):.4f} pu "
                  f"| eBESS={np.mean(m['eBESS_pu_s']):.3f}", flush=True)

    hdr_stats = []
    for k in ("nadir_Hz", "maxRoCoF_Hzps", "ts_s", "Pp2p_pu", "fosc_Hz",
              "eMPP_pu_s", "eBESS_pu_s"):
        hdr_stats += [k + "_mean", k + "_std"]
    with open(os.path.join(RES, "metrics_summary.csv"), "w") as f:
        f.write("scenario,controller," + ",".join(hdr_stats) + "\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")
    with open(os.path.join(RES, "metrics_raw.csv"), "w") as f:
        f.write("scenario,controller,real,nadir_Hz,maxRoCoF_Hzps,ts_s,Pp2p_pu,"
                "fosc_Hz,eMPP_pu_s,eBESS_pu_s\n")
        for r in raw_rows:
            f.write(",".join(str(x) for x in r) + "\n")

    # ---------------- trajektori deterministik utk figur & cross-impl Julia
    for scn, fname in (("S3", "traj_S3"), ("S5", "traj_S5")):
        trs = {}
        for ctrl in ("adaptive", "adaptgain", "smoothstatic", "static", "droop"):
            _, tr = simulate(scn, ctrl, xi_nominal(), save_traj=True)
            trs[ctrl] = tr
            np.savetxt(os.path.join(RES, f"{fname}_{ctrl}.csv"),
                       tr[::10], delimiter=",", header="Pinj_pu,Dw_pu", comments="")
        t = np.arange(N_STEP) * DT
        fig, ax = plt.subplots(1, 2, figsize=(7.0, 2.7))
        plt.rcParams.update({"legend.borderpad": 0.3, "legend.labelspacing": 0.25, "legend.handlelength": 1.3, "legend.handletextpad": 0.5, "legend.framealpha": 0.95, "font.size": 16, "font.family": "serif"})
        ax[0].plot(t, trs["static"][:, 0], "r", lw=1.6, label="conventional (static)")
        ax[0].plot(t, trs["adaptive"][:, 0], "b", lw=1.6, label="proposed (adaptive)")
        ax[0].set_xlabel("Time (s)"); ax[0].set_ylabel(r"$P_{out}$ (pu)")
        ax[0].grid(alpha=0.3); ax[0].legend(fontsize=10, loc="lower right"); ax[0].set_title("(a)", fontsize=16)
        ax[1].plot(t, F0 + F0 * trs["static"][:, 1], "r", lw=1.6)
        ax[1].plot(t, F0 + F0 * trs["adaptive"][:, 1], "b", lw=1.6)
        ax[1].set_xlabel("Time (s)"); ax[1].set_ylabel("f (Hz)")
        ax[1].grid(alpha=0.3); ax[1].set_title("(b)", fontsize=16)
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, f"fullpy_{scn}.pdf"))
        fig.savefig(os.path.join(FIG, f"fullpy_{scn}.png"), dpi=150)
        plt.close(fig)

    # ---------------- figur S2 (cloud passing, adaptif)
    _, tr = simulate("S2", "adaptive", xi_nominal(), save_traj=True)
    t = np.arange(N_STEP) * DT
    g = np.array([g_profile("S2", tt, 1.0) for tt in t[::100]])
    fig, ax = plt.subplots(1, 2, figsize=(7.0, 2.7))
    ax[0].plot(t[::100], g, "k", lw=1.6)
    ax[0].set_xlabel("Time (s)"); ax[0].set_ylabel(r"G (W/m$^2$)")
    ax[0].grid(alpha=0.3); ax[0].set_title("(a) irradiance profile", fontsize=16)
    ax[1].plot(t, tr[:, 0], "b", lw=1.6)
    ax[1].set_xlabel("Time (s)"); ax[1].set_ylabel(r"$P_{out}$ (pu)")
    ax[1].grid(alpha=0.3); ax[1].set_title("(b) injected power (adaptive)", fontsize=16)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fullpy_S2.pdf"))
    fig.savefig(os.path.join(FIG, "fullpy_S2.png"), dpi=150)
    plt.close(fig)

    # ---------------- sensitivitas: sweep H & SOC0 (nadir & Pp2p, adaptif vs statis)
    Hs = np.linspace(0.5, 4.0, 8)
    nadA = []; nadS = []; p2pA = []; p2pS = []
    for h in Hs:
        xi = xi_nominal(); xi["H"][:] = h
        mA, _ = simulate("S3", "adaptive", xi)
        mS, _ = simulate("S3", "static", xi)
        nadA.append(float(mA["nadir_Hz"][0])); nadS.append(float(mS["nadir_Hz"][0]))
        p2pA.append(float(mA["Pp2p_pu"][0])); p2pS.append(float(mS["Pp2p_pu"][0]))
    fig, ax = plt.subplots(1, 2, figsize=(7.0, 2.7))
    ax[0].plot(Hs, nadS, "r-o", ms=5.5, lw=1.6, label="conventional")
    ax[0].plot(Hs, nadA, "b-s", ms=5.5, lw=1.6, label="proposed")
    ax[0].set_xlabel(r"$H_{sys}$ (s)"); ax[0].set_ylabel("nadir (Hz)")
    ax[0].grid(alpha=0.3); ax[0].legend(fontsize=10, loc="center right"); ax[0].set_title("(a)", fontsize=16)
    ax[1].semilogy(Hs, np.maximum(p2pS, 1e-8), "r-o", ms=5.5, lw=1.6)
    ax[1].semilogy(Hs, np.maximum(p2pA, 1e-8), "b-s", ms=5.5, lw=1.6)
    ax[1].set_xlabel(r"$H_{sys}$ (s)"); ax[1].set_ylabel(r"$P_{p2p}$ (pu)")
    ax[1].grid(alpha=0.3); ax[1].set_title("(b)", fontsize=16)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fullpy_sens.pdf"))
    fig.savefig(os.path.join(FIG, "fullpy_sens.png"), dpi=150)
    plt.close(fig)

    print(f"\nselesai {time.time()-t0:.1f} s | hasil di results/ + ../figures/")
