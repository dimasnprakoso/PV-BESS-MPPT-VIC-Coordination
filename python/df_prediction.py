# -*- coding: utf-8 -*-
"""
Prediksi analitik limit-cycle koordinasi STATIS via describing function (DF).

Nonlinieritas: relay 3-keadaan dgn dead-band pada Dwf (input x, output u=Pbat):
    u = +M (x<-h), 0 (|x|<=h), -M (x>h)   ->  N(A) = (4M/(pi A))*sqrt(1-(h/A)^2), fase 0
Bagian linear (u -> x): loop swing + lag inverter + filter PLL, dengan VIC statis
(Kd + Kj s) sebagai umpan-balik linear internal:
    G(s)   = Ginv*Gsw*Gpll,  Ginv=1/(tau_inv s+1), Gsw=1/(2H s+D), Gpll=1/(tau_pll s+1)
    L(s)   = G / (1 + G*(Kd + Kj s))
Harmonic balance: N(A) L(jw) = -1  ->  arg L(jw*) = -180 deg,  N(A*) = 1/|L(jw*)|.
Bandingkan f* dan amplitudo Dwf* terhadap simulasi S5 statis nominal.
"""
import numpy as np

# parameter nominal (identik fullmodel/kampanye)
tau_inv, tau_pll = 0.05, 0.02
H, D = 2.0, 1.0
Kd, Kj = 0.50, 0.10          # VIC statis
M, h = 0.40, 0.02            # relay & dead-band

def L(jw):
    G = 1.0/(tau_inv*jw + 1.0) * 1.0/(2*H*jw + D) * 1.0/(tau_pll*jw + 1.0)
    return G / (1.0 + G*(Kd + Kj*jw))

# cari omega dgn fase -180 derajat
w = np.logspace(-1, 3, 400000)
ph = np.angle(L(1j*w))
ph_unwrap = np.unwrap(ph)
idx = np.where(np.diff(np.sign(ph_unwrap + np.pi)))[0]
if len(idx) == 0:
    print("tidak ada persilangan -180 (tidak ada prediksi limit-cycle)")
else:
    i = idx[0]
    w_star = np.interp(-np.pi, [ph_unwrap[i+1], ph_unwrap[i]], [w[i+1], w[i]])
    f_star = w_star/(2*np.pi)
    mag = abs(L(1j*w_star))
    # N(A) = 1/|L| -> selesaikan A: (4M/(pi A))*sqrt(1-(h/A)^2) = 1/mag
    # substitusi y=h/A: (4M/(pi h)) * y * sqrt(1-y^2) = 1/mag
    c = np.pi*h/(4*M*mag)          # y*sqrt(1-y^2) = c ; pilih akar A terbesar (siklus stabil)
    if c > 0.5:
        print(f"f*={f_star:.2f} Hz tapi c={c:.3f}>0.5 -> tak ada solusi A (tak ada siklus)")
    else:
        y2 = (1 - np.sqrt(1-4*c*c))/2     # akar y^2 kecil -> A besar (stabil)
        A = h/np.sqrt(y2)
        print(f"PREDIKSI DF: f_osc = {f_star:.2f} Hz | amplitudo Dwf A = {A:.5f} pu "
              f"(p2p {2*A:.5f} pu = {2*A*50:.3f} Hz)")
        print(f"|L(jw*)| = {mag:.4f}, N(A)= {1/mag:.4f}")

# ---- ukur dari simulasi S5 statis nominal (trajektori tersimpan)
import os
d = np.loadtxt(os.path.join(os.path.dirname(__file__), "results", "traj_S5_static.csv"),
               delimiter=",", skiprows=1)   # kolom: Pinj, Dw (decim 10 -> dt=1e-3)
Dw = d[:, 1]; dt = 1e-3
i0 = int(6.0/dt)
p2p_dw = Dw[i0:].max() - Dw[i0:].min()
seg = Dw[i0:] - Dw[i0:].mean()
n = len(seg)
amp = 2/n*np.abs(np.fft.rfft(seg*np.hanning(n)))
fr = np.fft.rfftfreq(n, dt)
fosc = fr[np.argmax(amp[1:])+1]
print(f"SIMULASI    : f_osc = {fosc:.2f} Hz | Dwf p2p = {p2p_dw:.5f} pu = {p2p_dw*50:.3f} Hz")
