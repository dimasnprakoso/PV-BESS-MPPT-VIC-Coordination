# -*- coding: utf-8 -*-
"""
Simulator perluasan untuk revisi R1 ESJ (Okt 2026), di atas model rerata
python/fullmodel.py (parameter, PV, MPPT, BESS, inverter, PLL, ayun diimpor dari
sana, tidak disalin).

Perluasan dibanding fullmodel.simulate:
  - gangguan beban = jumlah event tangga (t_on, t_off, kelipatan DPL) + derau
    beban Ornstein-Uhlenbeck (fluktuasi ambient), benih derau dapat dipilih
    sehingga semua kontroler melihat derau yang SAMA (common random numbers);
  - lama simulasi bebas;
  - kontroler berparameter: adaptive (ka, kaw, beta_max, kb), smooth (rating M),
    relay (ambang h, kuantum M, histeresis opsional), droop;
  - E_RATED dapat diganti (uji gerbang SOC).

Dengan konfigurasi bawaan (satu tangga di t = 2 s, tanpa derau, T = 8 s) hasilnya
harus BIT-IDENTIK dengan fullmodel.simulate -- diuji oleh cek_identik() di bawah.
"""
import os
import sys

import numpy as np

PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "python")
sys.path.insert(0, os.path.abspath(PY))
import fullmodel as fm  # noqa: E402

DT = fm.DT


def ctrl_cfg(name):
    """Konfigurasi kontroler bernama (dipakai di naskah dan uji tambahan)."""
    K = fm.KNEE
    base = dict(
        adaptive=dict(type="adaptive", Kd=K["Kd"], Kj=K["Kj"], ka=K["ka"], kaw=K["kaw"],
                      beta_max=K["beta_max"], kb=K["kb"]),
        # bobot w = 1 tetap (alpha dibuang), selebihnya identik dengan usulan
        noalpha=dict(type="adaptive", Kd=K["Kd"], Kj=K["Kj"], ka=None, kaw=None,
                     beta_max=K["beta_max"], kb=K["kb"]),
        smoothstatic=dict(type="smooth", Kd=fm.VIC_FIX["Kd"], Kj=fm.VIC_FIX["Kj"],
                          M=fm.M_RELAY, kb=K["kb"]),
        smooth025=dict(type="smooth", Kd=fm.VIC_FIX["Kd"], Kj=fm.VIC_FIX["Kj"],
                       M=K["beta_max"], kb=K["kb"]),
        static=dict(type="relay", Kd=fm.VIC_FIX["Kd"], Kj=fm.VIC_FIX["Kj"],
                    M=fm.M_RELAY, h_on=fm.HYST, h_off=None),
        droop=dict(type="droop", Kd=fm.DROOP["Kd"]),
        # FFR Nordik: ambang 49,7 Hz, aktif penuh <= 1,3 s, durasi dukungan 5 s,
        # deaktivasi <= 20 %/s (parameter dapat diubah pemanggil)
        ffr=dict(type="ffr", Kd=fm.VIC_FIX["Kd"], Kj=fm.VIC_FIX["Kj"], M=fm.M_RELAY,
                 h_on=0.3 / fm.F0, t_full=1.3, t_hold=5.0, ramp_down=0.2, t_buffer=0.0),
    )
    return dict(base[name])


def simulate(ctrl, xi, events=((2.0, None, 1.0),), T_end=8.0, noise_sigma=0.0,
             noise_tau=1.0, noise_seed=0, g_scn="S3", e_rated=None, win=2.0,
             save_traj=False, traj_every=10, soc_taper=None, gov_R=None, gov_T=5.0):
    """
    ctrl   : dict dari ctrl_cfg() (boleh dimodifikasi)
    xi     : dict H, DPL, SOC0, Gjit, Tc (vektor n realisasi)
    events : daftar (t_on, t_off|None, kelipatan DPL); gangguan = sum kelipatan*DPL
    noise_sigma : simpangan baku stasioner derau beban OU [pu]; 0 = tanpa derau
    g_scn  : profil iradiansi fullmodel.g_profile ("S2" = awan, lain = 1000 W/m2)
    win    : panjang jendela tunak di akhir simulasi untuk P_p2p dan f_osc [s]
    """
    H, DPL, SOC0, Gjit, Tc = (xi[k] for k in ("H", "DPL", "SOC0", "Gjit", "Tc"))
    n = H.size
    N = int(round(T_end / DT))
    E = fm.E_RATED if e_rated is None else e_rated
    tap = fm.SOC_TAPER if soc_taper is None else soc_taper  # ~0 = potong keras
    Dw = np.zeros(n); Pinj = np.zeros(n); Dwf = np.zeros(n)
    soc = SOC0.copy()
    st = np.zeros(n)  # status relai (histeresis)
    ffr_on = np.zeros(n, bool); ffr_lvl = np.zeros(n)
    ffr_start = np.full(n, -1.0); ffr_rearm = np.full(n, -1.0)
    Vpv = np.full(n, 0.80 * fm.VOC_CELL * fm.NS)
    dV = np.full(n, fm.MPPT_STEP)
    Ppv_prev = np.zeros(n)
    k_sched = int(1.5 / DT)
    Psched = np.zeros(n)
    mppt_every = int(fm.MPPT_DT / DT)

    # derau beban OU, diperbarui tiap 10 ms (zero-order hold)
    nrng = np.random.default_rng(noise_seed)
    n_every = int(0.01 / DT)
    a_ou = np.exp(-0.01 / noise_tau)
    b_ou = noise_sigma * np.sqrt(1.0 - a_ou ** 2)
    xn = noise_sigma * nrng.standard_normal(n) if noise_sigma > 0 else np.zeros(n)

    maxDw = np.zeros(n); maxroc = np.zeros(n)
    e_mpp = np.zeros(n); e_bat = np.zeros(n)
    i0 = N - int(round(win / DT))
    seg = np.empty((N - i0, n))
    # statistik frekuensi pasca-inisialisasi (t >= 3 s)
    k_stat = int(3.0 / DT)
    s1 = np.zeros(n); s2 = np.zeros(n); cnt = 0
    soc_min = soc.copy(); phi_min = np.ones(n)
    traj = [] if save_traj else None
    Pgov = np.zeros(n)  # governor/FCR agregat orde-1 (opsional, gov_R = droop pu)

    t_type = ctrl["type"]
    for k in range(N):
        t = k * DT
        if k % mppt_every == 0:
            G = fm.g_profile(g_scn, t, Gjit)
            Ipv = fm.pv_current(Vpv, G, Tc)
            Ppv = Vpv * Ipv * fm.PV_SCALE
            better = Ppv >= Ppv_prev
            dV = np.where(better, dV, -dV)
            Vpv = np.clip(Vpv + dV, 0.55 * fm.VOC_CELL * fm.NS, 0.95 * fm.VOC_CELL * fm.NS)
            Ppv_prev = Ppv
        Pmppt = Ppv / fm.S_BASE

        rocof = (Dw - Dwf) / fm.TAU_PLL
        np.maximum(maxroc, np.abs(rocof), out=maxroc)
        phi_d = np.clip((soc - fm.SOC_MIN) / tap, 0.0, 1.0)
        phi_c = np.clip((fm.SOC_MAX - soc) / tap, 0.0, 1.0)

        if t_type == "adaptive":
            Pvic = -(ctrl["Kd"] * Dwf + ctrl["Kj"] * rocof)
            if ctrl["ka"] is None:
                w = 1.0
            else:
                alpha = 1.0 / (1.0 + ctrl["ka"] * np.abs(Dwf) + ctrl["kaw"] * np.abs(rocof))
                w = 1.0 - alpha
            raw = ctrl["beta_max"] * np.tanh(ctrl["kb"] * (-Dwf))
            Pbat = np.where(raw >= 0, raw * phi_d, raw * phi_c)
            Pref = Pmppt + w * Pvic + Pbat
            e_mpp += DT * np.abs(w * Pvic + Pbat)
        elif t_type == "relay":
            Pvic = -(ctrl["Kd"] * Dwf + ctrl["Kj"] * rocof)
            h_on, h_off = ctrl["h_on"], ctrl["h_off"]
            if h_off is None:
                st = np.where(Dwf < -h_on, 1.0, np.where(Dwf > h_on, -1.0, 0.0))
            else:
                st = np.where(Dwf < -h_on, 1.0, np.where(Dwf > h_on, -1.0, st))
                st = np.where((st > 0) & (Dwf > -h_off), 0.0, st)
                st = np.where((st < 0) & (Dwf < h_off), 0.0, st)
            Pbat = ctrl["M"] * st * np.where(st > 0, phi_d, phi_c)
            Pref = Pmppt + Pvic + Pbat
            e_mpp += DT * np.abs(Pvic + Pbat)
        elif t_type == "ffr":
            # FFR terpicu gaya Nordik: aktif bila Dwf < -h, naik ke penuh dalam
            # t_full, ditahan t_hold sejak aktivasi, lalu turun dengan laju
            # ramp_down (fraksi M per detik); boleh aktif lagi t_buffer setelah nol.
            Pvic = -(ctrl["Kd"] * Dwf + ctrl["Kj"] * rocof)
            trig = (~ffr_on) & (ffr_lvl <= 0.0) & (t >= ffr_rearm) & (Dwf < -ctrl["h_on"])
            ffr_start = np.where(trig, t, ffr_start)
            ffr_on = ffr_on | trig
            stop = ffr_on & (t - ffr_start >= ctrl["t_hold"])
            ffr_on = ffr_on & ~stop
            prev = ffr_lvl
            ffr_lvl = np.where(ffr_on, np.minimum(ffr_lvl + DT / ctrl["t_full"], 1.0),
                               np.maximum(ffr_lvl - DT * ctrl["ramp_down"], 0.0))
            ffr_rearm = np.where((prev > 0.0) & (ffr_lvl <= 0.0), t + ctrl["t_buffer"], ffr_rearm)
            Pbat = ctrl["M"] * ffr_lvl * phi_d
            Pref = Pmppt + Pvic + Pbat
            e_mpp += DT * np.abs(Pvic + Pbat)
        elif t_type == "smooth":
            Pvic = -(ctrl["Kd"] * Dwf + ctrl["Kj"] * rocof)
            raw = ctrl["M"] * np.tanh(ctrl["kb"] * (-Dwf))
            Pbat = np.where(raw >= 0, raw * phi_d, raw * phi_c)
            Pref = Pmppt + Pvic + Pbat
            e_mpp += DT * np.abs(Pvic + Pbat)
        else:
            Pvic = -(ctrl["Kd"] * Dwf)
            Pbat = np.zeros(n)
            Pref = Pmppt + Pvic
            e_mpp += DT * np.abs(Pvic)
        e_bat += DT * np.abs(Pbat)

        Pb_W = Pbat * fm.S_BASE
        dis = Pb_W > 0
        soc = soc - DT * np.where(dis, Pb_W / fm.ETA_D, Pb_W * fm.ETA_C) / E
        soc = np.clip(soc, 0.0, 1.0)
        np.minimum(soc_min, soc, out=soc_min)
        np.minimum(phi_min, np.minimum(phi_d, phi_c), out=phi_min)

        if k == k_sched:
            Psched = Pinj.copy()
        dist = np.zeros(n)
        for (ton, toff, mult) in events:
            if t >= ton and (toff is None or t < toff):
                dist = dist + mult * DPL
        if noise_sigma > 0:
            if k % n_every == 0 and k > 0:
                xn = a_ou * xn + b_ou * nrng.standard_normal(n)
            if k >= k_sched:
                dist = dist + xn
        Pinj += DT * (np.clip(Pref, -1.2, 1.2) - Pinj) / fm.TAU_INV
        if k >= k_sched:
            if gov_R is not None:
                Pgov += DT * (-Dw / gov_R - Pgov) / gov_T
            Dw += DT * ((Pinj - Psched) + Pgov - dist - 1.0 * Dw) / (2.0 * H)
        Dwf += DT * (Dw - Dwf) / fm.TAU_PLL

        np.maximum(maxDw, np.abs(Dw), out=maxDw)
        if k >= k_stat:
            s1 += Dw; s2 += Dw * Dw; cnt += 1
        if k >= i0:
            seg[k - i0] = Pinj
        if save_traj and k % traj_every == 0:
            traj.append(np.stack([np.full(n, t), Pinj, Dw, Pbat, soc]))

    p2p = seg.max(axis=0) - seg.min(axis=0)
    segz = seg - seg.mean(axis=0)
    amp = np.abs(np.fft.rfft(segz * np.hanning(segz.shape[0])[:, None], axis=0))
    fr = np.fft.rfftfreq(segz.shape[0], DT)
    fosc = fr[np.argmax(amp[1:], axis=0) + 1]
    mean = s1 / max(cnt, 1)
    fstd = fm.F0 * np.sqrt(np.maximum(s2 / max(cnt, 1) - mean ** 2, 0.0))
    m = dict(nadir_Hz=fm.F0 - fm.F0 * maxDw, maxRoCoF_Hzps=fm.F0 * maxroc,
             Pp2p_pu=p2p, fosc_Hz=fosc, eMPP_pu_s=e_mpp, eBESS_pu_s=e_bat,
             fstd_Hz=fstd, soc_min=soc_min, phi_min=phi_min, soc_end=soc)
    if save_traj:
        traj = np.array(traj)  # (T, 5, n)
    return m, traj


def lc_detect(p2p, fosc, th=0.01, T_w=2.0):
    """Aturan deteksi naskah: P_p2p > th, f_osc > 2/T_w, bukan riak P&O (12,5 Hz dan kelipatannya)."""
    po = (np.abs(fosc / 12.5 - np.round(fosc / 12.5)) * 12.5 < 0.5) & (fosc >= 12.0)
    return (p2p > th) & (fosc > 2.0 / T_w) & ~po


def cek_identik():
    """Konfigurasi bawaan harus bit-identik dengan fullmodel.simulate."""
    fm.rng = np.random.default_rng(123)
    for scn in ("S3", "S5"):
        xi = fm.draw_xi(8, scn)
        for c in ("adaptive", "smoothstatic", "static", "droop"):
            a, _ = fm.simulate(scn, c, xi)
            b, _ = simulate(ctrl_cfg(c), xi, g_scn=scn)
            for key in ("nadir_Hz", "maxRoCoF_Hzps", "Pp2p_pu", "fosc_Hz", "eMPP_pu_s", "eBESS_pu_s"):
                if not np.array_equal(a[key], b[key]):
                    raise AssertionError(f"{scn} {c} {key} beda: {np.max(np.abs(a[key]-b[key]))}")
    print("cek_identik: OK (bit-identik dengan fullmodel.simulate)")


if __name__ == "__main__":
    cek_identik()
