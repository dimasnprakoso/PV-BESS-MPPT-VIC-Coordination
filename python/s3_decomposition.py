# -*- coding: utf-8 -*-
"""
Dekomposisi daya skenario S3 nominal (kontroler adaptif, model averaged):
  P_pv (MPPT), kontribusi VIC (1-alpha)*P_vic, kontribusi BESS beta*P_bat,
  P_inj total, plus frekuensi & RoCoF.
Loop dinamika identik fullmodel.simulate (nominal, n=1) tetapi menyimpan
seluruh komponen. Keluaran: ../figures/fullpy_decomp.pdf/png + metrik konsol.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
# WAJIB. Bawaan matplotlib menanam fon sebagai Type 3, yang ditolak
# IEEE PDF eXpress dan disorot banyak sistem submisi jurnal. 42 memaksa
# TrueType. Jangan dihapus.
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42

import fullmodel as fm

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "..", "figures")

# ---------------- loop nominal dgn perekaman komponen (skalar, n=1)
H, DPL, SOC0, Gjit, Tc = 2.0, 0.10, 0.60, 1.0, 28.0
DT, N = fm.DT, fm.N_STEP
K = fm.KNEE
Dw = Pinj = Dwf = 0.0
soc = SOC0
Vpv = 0.80 * fm.VOC_CELL * fm.NS
dV = fm.MPPT_STEP
Ppv_prev = Ppv = 0.0
k_sched = int(1.5 / DT); Psched = 0.0
mppt_every = int(fm.MPPT_DT / DT)

t = np.arange(N) * DT
TR = np.zeros((N, 8))   # Pmppt, wPvic, bPbat, Pinj, f, RoCoF, alpha, beta_eff
for k in range(N):
    if k % mppt_every == 0:
        Ipv = fm.pv_current(np.array([Vpv]), 1000.0 * Gjit, Tc)[0]
        Ppv_new = Vpv * Ipv * fm.PV_SCALE
        dV = dV if Ppv_new >= Ppv_prev else -dV
        Vpv = np.clip(Vpv + dV, 0.55 * fm.VOC_CELL * fm.NS, 0.95 * fm.VOC_CELL * fm.NS)
        Ppv_prev = Ppv_new; Ppv = Ppv_new
    Pmppt = Ppv / fm.S_BASE

    rocof = (Dw - Dwf) / fm.TAU_PLL
    phi_d = np.clip((soc - fm.SOC_MIN) / fm.SOC_TAPER, 0.0, 1.0)
    phi_c = np.clip((fm.SOC_MAX - soc) / fm.SOC_TAPER, 0.0, 1.0)
    Pvic = -(K["Kd"] * Dwf + K["Kj"] * rocof)
    alpha = 1.0 / (1.0 + K["ka"] * abs(Dwf) + K["kaw"] * abs(rocof))
    w = 1.0 - alpha
    raw = K["beta_max"] * np.tanh(K["kb"] * (-Dwf))
    Pbat = raw * phi_d if raw >= 0 else raw * phi_c
    Pref = Pmppt + w * Pvic + Pbat

    Pb_W = Pbat * fm.S_BASE
    soc -= DT * (Pb_W / fm.ETA_D if Pb_W > 0 else Pb_W * fm.ETA_C) / fm.E_RATED
    soc = min(max(soc, 0.0), 1.0)

    if k == k_sched: Psched = Pinj
    dist = DPL if (k * DT) >= 2.0 else 0.0
    Pinj += DT * (np.clip(Pref, -1.2, 1.2) - Pinj) / fm.TAU_INV
    if k >= k_sched:
        Dw += DT * ((Pinj - Psched) - dist - 1.0 * Dw) / (2.0 * H)
    Dwf += DT * (Dw - Dwf) / fm.TAU_PLL

    beta_eff = abs(raw) * (phi_d if raw >= 0 else phi_c)   # beta = bmax*Phi*tanh(kb|Dw|)
    TR[k] = (Pmppt, w * Pvic, Pbat, Pinj, fm.F0 * (1 + Dw), fm.F0 * rocof, alpha, beta_eff)

# ---------------- metrik ringkas (jendela pasca-event & tunak)
i_ev, i_ss = int(2.0 / DT), int(6.0 / DT)
print("S3 nominal adaptif — dekomposisi:")
print(f"  P_pv tunak      = {TR[i_ss:,0].mean():.4f} pu")
print(f"  (1-a)Pvic tunak = {TR[i_ss:,1].mean():.4f} pu | puncak = {TR[i_ev:,1].max():.4f}")
print(f"  bPbat tunak     = {TR[i_ss:,2].mean():.4f} pu | puncak = {TR[i_ev:,2].max():.4f}")
print(f"  P_inj tunak     = {TR[i_ss:,3].mean():.4f} pu")
print(f"  nadir           = {TR[:,4].min():.3f} Hz | max|RoCoF| = {np.abs(TR[:,5]).max():.3f} Hz/s")
i_min_a = int(np.argmin(TR[:, 6]))
i_half = i_ev + int(np.argmax(TR[i_ev:, 6] < 0.5)) if (TR[i_ev:, 6] < 0.5).any() else -1
print(f"  alpha: pra-event = {TR[:i_ev,6].min():.3f} (min) | min = {TR[i_min_a,6]:.3f} "
      f"@ t = {t[i_min_a]:.3f} s | <0.5 dicapai {1e3*(t[i_half]-2.0):.1f} ms pasca-event"
      if i_half > 0 else f"  alpha min = {TR[i_min_a,6]:.3f}")
print(f"  alpha tunak (6-8 s) = {TR[i_ss:,6].mean():.3f}")
print(f"  beta : puncak = {TR[i_ev:,7].max():.4f} @ t = {t[i_ev+int(np.argmax(TR[i_ev:,7]))]:.3f} s "
      f"| tunak = {TR[i_ss:,7].mean():.4f} (beta_max = {K['beta_max']:.4f})")

# ---------------- figur (2x2: panel alpha/beta melebar di baris bawah)
plt.rcParams.update({"legend.borderpad": 0.3, "legend.labelspacing": 0.25, "legend.handlelength": 1.3, "legend.handletextpad": 0.5, "legend.framealpha": 0.95, "font.size": 16, "font.family": "serif"})
fig = plt.figure(figsize=(7.4, 4.6), layout="constrained")
gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 0.85])
ax = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])]
axc = fig.add_subplot(gs[1, :])
ax[0].plot(t, TR[:, 3], "k",  lw=1.8, label=r"$P_{inj}$ (total)")
ax[0].plot(t, TR[:, 0], "g--", lw=1.6, label=r"$P_{mppt}$")
ax[0].plot(t, TR[:, 2], "b",  lw=1.6, label=r"$\beta P_{bat}$")
ax[0].plot(t, TR[:, 1], "r",  lw=1.6, label=r"$(1{-}\alpha)P_{vic}$")
ax[0].set_xlabel("Time (s)"); ax[0].set_ylabel("Power (pu)")
ax[0].set_xlim(1.5, 8); ax[0].grid(alpha=0.3)
ax[0].legend(fontsize=9.5, ncol=2, loc="center")
ax[0].set_title("(a) power decomposition", fontsize=16)

ax2 = ax[1].twinx()
l1, = ax[1].plot(t, TR[:, 4], "b", lw=1.8, label="frequency")
l2, = ax2.plot(t, TR[:, 5], "r", lw=1.3, alpha=0.8, label="RoCoF")
ax[1].set_xlabel("Time (s)"); ax[1].set_ylabel("f (Hz)", color="b")
ax2.set_ylabel("RoCoF (Hz/s)", color="r")
ax[1].set_xlim(1.5, 8); ax[1].grid(alpha=0.3)
ax[1].legend(handles=[l1, l2], fontsize=10, loc="center right")
ax[1].set_title("(b) frequency and RoCoF", fontsize=16)

axc2 = axc.twinx()
la, = axc.plot(t, TR[:, 6], "b", lw=1.8, label=r"$\alpha$ (MPPT--VIC weight)")
lb, = axc2.plot(t, TR[:, 7], "r", lw=1.8, label=r"$\beta$ (BESS gate)")
axc.axvline(2.0, color="k", ls=":", lw=1.4)
axc.set_xlabel("Time (s)"); axc.set_ylabel(r"$\alpha$", color="b")
axc2.set_ylabel(r"$\beta$", color="r")
axc.set_xlim(1.5, 8); axc.set_ylim(-0.02, 1.05)
axc2.set_ylim(-0.005, 0.28)
axc.grid(alpha=0.3)
axc.legend(handles=[la, lb], fontsize=10, loc="center right")
axc.set_title(r"(c) internal adaptive signals $\alpha(t)$, $\beta(t)$", fontsize=16)

fig.savefig(os.path.join(FIG, "fullpy_decomp.pdf"))
fig.savefig(os.path.join(FIG, "fullpy_decomp.png"), dpi=150)
print("figur: fullpy_decomp.pdf/png")
