# -*- coding: utf-8 -*-
"""
Argumen absensi limit-cycle untuk gate BESS halus (skema usulan) via
circle criterion + non-interseksi describing function.

Gate halus (kanal dispatch usulan): u = beta_max * Phi_SOC * tanh(k_beta * x),
x = -Dwf. Nonlinieritas memoryless GANJIL dengan kemiringan maksimum di titik
asal: 0 <= f(x)/x <= k, k = beta_max*k_beta (Phi_SOC <= 1 hanya menyusutkan
sektor). Circle criterion (sektor [0,k], L stabil): stabil absolut bila lokus
Nyquist L(jw) berada di kanan garis Re = -1/k.

Bagian linear identik df_prediction.py: G = Ginv*Gsw*Gpll.
Dua kasus batas bobot VIC adaptif (1-alpha) in [0,1):
  L0 = G                                  ((1-alpha) -> 0, tanpa umpan-balik VIC)
  L1 = G / (1 + G*(Kd + Kj s))            ((1-alpha) -> 1, gain knee penuh)
Relay dead-band baseline: kemiringan inkremental TAK terbatas di |x|=h ->
tidak termuat dalam sektor hingga mana pun -> circle criterion tak dapat
menjamin; DF-nya memang memprediksi persilangan (lihat df_prediction.py).
"""
import numpy as np

tau_inv, tau_pll = 0.05, 0.02
H, D = 2.0, 1.0
Kd_knee, Kj_knee = 1.0045, 0.0317      # gain VIC knee (produksi)
beta_max, k_beta = 0.2497, 45.797      # gate knee

k_sector = beta_max * k_beta
print(f"sektor gate halus: [0, k], k = beta_max*k_beta = {k_sector:.3f}")
print(f"garis kritis circle criterion: Re = -1/k = {-1.0/k_sector:.5f}")

w = np.logspace(-2, 4, 800000)
jw = 1j * w
G = 1.0/(tau_inv*jw + 1.0) * 1.0/(2*H*jw + D) * 1.0/(tau_pll*jw + 1.0)

for nama, L in [("L0 (tanpa VIC, (1-a)->0)", G),
                ("L1 (VIC knee, (1-a)->1)", G/(1.0 + G*(Kd_knee + Kj_knee*jw)))]:
    reL = L.real
    i = int(np.argmin(reL))
    margin = reL[i] / (-1.0/k_sector)
    print(f"\n{nama}:")
    print(f"  min Re L(jw) = {reL[i]:.5f} pada f = {w[i]/2/np.pi:.2f} Hz "
          f"(batas -1/k = {-1.0/k_sector:.5f}; rasio {margin:.3f} dari batas)")
    # non-interseksi DF: N(A) <= k, siklus butuh N(A)=1/|L(jw180)|
    ph = np.unwrap(np.angle(L))
    idx = np.where(np.diff(np.sign(ph + np.pi)))[0]
    if len(idx):
        ii = idx[0]
        w180 = np.interp(-np.pi, [ph[ii+1], ph[ii]], [w[ii+1], w[ii]])
        mag = np.abs(np.interp(w180, w, np.abs(L)))
        print(f"  persilangan -180 deg: f = {w180/2/np.pi:.2f} Hz, |L| = {mag:.5f}"
              f" -> DF butuh N = {1.0/mag:.1f}, padahal max N gate = k = {k_sector:.1f}"
              f" ({'TIDAK ADA interseksi -> tak ada siklus' if k_sector < 1.0/mag else 'interseksi!'})")
    else:
        print("  tidak ada persilangan -180 deg")
