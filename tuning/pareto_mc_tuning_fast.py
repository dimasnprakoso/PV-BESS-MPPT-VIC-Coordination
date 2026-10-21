# -*- coding: utf-8 -*-
"""
Penalaan robust Monte Carlo-Pareto SKALA PRODUKSI (vektorisasi numpy).
Identik secara matematis dengan pareto_mc_tuning.py, tetapi loop Monte Carlo
dievaluasi serentak (vektor atas N_MC sampel) sehingga POP=60/GEN=80/N_MC=200
selesai dalam belasan menit.

Keluaran: pareto_front_prod.csv + ringkasan knee point di stdout.
"""
import time
import numpy as np

rng = np.random.default_rng(42)

# ---------------------------------------------------------------- PENGATURAN
POP, GEN, N_MC, GAMMA = 60, 80, 200, 0.95

LB = np.array([0.05, 0.02,  5.0,  1.0,  5.0, 0.10])
UB = np.array([2.00, 0.50, 60.0, 20.0, 60.0, 0.60])
DIM = len(LB)
NAMES = ["Kd", "Kj", "ka", "kaw", "kb", "beta_max"]

tau_inv, tau_pll = 0.05, 0.02
T, dt = 6.0, 1e-3
NSTEP = int(T / dt)
t_evt = 0.5
i0, i1 = int(3.5 / dt), int(6.0 / dt)


def sample_xi(n):
    return (rng.uniform(1.5, 4.0, n),      # H
            rng.uniform(0.05, 0.15, n),    # DPL
            rng.uniform(0.8, 1.5, n),      # Dsys
            rng.uniform(0.5, 1.0, n))      # Phi_soc


def simulate_batch(theta, xi):
    """Model tereduksi ADAPTIF, vektor atas N_MC sampel xi sekaligus."""
    Kd, Kj, ka, kaw, kb, beta_max = theta
    H, DPL, Dsys, Phi = xi
    n = H.size
    Df = np.zeros(n); Pinj = np.zeros(n); ffil = np.zeros(n)
    e_mpp = np.zeros(n); e_bat = np.zeros(n); maxDf = np.zeros(n)
    seg_min = np.full(n, np.inf); seg_max = np.full(n, -np.inf)
    for k in range(NSTEP):
        rocof = (Df - ffil) / tau_pll
        Pvic = -(Kd * ffil + Kj * rocof)
        alpha = 1.0 / (1.0 + ka * np.abs(ffil) + kaw * np.abs(rocof))
        w = 1.0 - alpha
        Pbat = beta_max * Phi * np.tanh(kb * (-ffil))
        Pref = w * Pvic + Pbat

        dist = DPL if (k * dt) >= t_evt else 0.0
        Df = Df + dt * (Pinj - Dsys * Df - dist) / (2.0 * H)
        Pinj = Pinj + dt * (Pref - Pinj) / tau_inv
        ffil = ffil + dt * (Df - ffil) / tau_pll

        e_mpp += dt * np.abs(w * Pvic)
        e_bat += dt * np.abs(Pbat)
        np.maximum(maxDf, np.abs(Df), out=maxDf)
        if k >= i0:
            np.minimum(seg_min, Pinj, out=seg_min)
            np.maximum(seg_max, Pinj, out=seg_max)
    p2p = seg_max - seg_min
    return np.stack([maxDf, e_mpp, e_bat, p2p], axis=1)   # (n, 4)


def cvar_cols(phis, gamma):
    n = phis.shape[0]
    k = max(1, int(np.ceil((1.0 - gamma) * n)))
    s = np.sort(phis, axis=0)
    return s[-k:].mean(axis=0)


def robust_objectives(theta):
    return cvar_cols(simulate_batch(theta, sample_xi(N_MC)), GAMMA)


# --------------------------------------------------------- NSGA-II (identik)
def dominates(a, b):
    return np.all(a <= b) and np.any(a < b)


def fast_nondominated_sort(F):
    n = len(F); S = [[] for _ in range(n)]
    ndom = np.zeros(n, dtype=int); fronts = [[]]
    for p in range(n):
        for q in range(n):
            if p == q: continue
            if dominates(F[p], F[q]): S[p].append(q)
            elif dominates(F[q], F[p]): ndom[p] += 1
        if ndom[p] == 0: fronts[0].append(p)
    i = 0
    while fronts[i]:
        nxt = []
        for p in fronts[i]:
            for q in S[p]:
                ndom[q] -= 1
                if ndom[q] == 0: nxt.append(q)
        i += 1; fronts.append(nxt)
    return fronts[:-1]


def crowding_distance(F):
    n, m = F.shape; dist = np.zeros(n)
    for j in range(m):
        o = np.argsort(F[:, j])
        dist[o[0]] = dist[o[-1]] = np.inf
        fmin, fmax = F[o[0], j], F[o[-1], j]
        if fmax - fmin < 1e-12: continue
        for i in range(1, n - 1):
            dist[o[i]] += (F[o[i+1], j] - F[o[i-1], j]) / (fmax - fmin)
    return dist


def tournament(pop, rank, crowd):
    i, j = rng.integers(0, len(pop), 2)
    if rank[i] != rank[j]: return pop[i] if rank[i] < rank[j] else pop[j]
    return pop[i] if crowd[i] > crowd[j] else pop[j]


def sbx(p1, p2, eta=15.0):
    u = rng.random(DIM)
    b = np.where(u <= 0.5, (2*u)**(1/(eta+1)), (1/(2*(1-u)))**(1/(eta+1)))
    return (np.clip(0.5*((1+b)*p1+(1-b)*p2), LB, UB),
            np.clip(0.5*((1-b)*p1+(1+b)*p2), LB, UB))


def mut(x, eta=20.0):
    y = x.copy()
    for i in range(DIM):
        if rng.random() < 1.0/DIM:
            u = rng.random()
            d = (2*u)**(1/(eta+1))-1 if u < 0.5 else 1-(2*(1-u))**(1/(eta+1))
            y[i] = np.clip(x[i] + d*(UB[i]-LB[i]), LB[i], UB[i])
    return y


def knee(F):
    fmin, fmax = F.min(0), F.max(0)
    span = np.where(fmax-fmin < 1e-12, 1.0, fmax-fmin)
    return int(np.argmin(np.linalg.norm((F-fmin)/span, axis=1)))


if __name__ == "__main__":
    t0 = time.time()
    print(f"PRODUKSI NSGA-II vektorisasi | POP={POP} GEN={GEN} N_MC={N_MC} gamma={GAMMA}", flush=True)
    pop = LB + rng.random((POP, DIM)) * (UB - LB)
    F = np.array([robust_objectives(p) for p in pop])
    for g in range(GEN):
        fronts = fast_nondominated_sort(F)
        rank = np.empty(POP, int); crowd = np.empty(POP)
        for r, fr in enumerate(fronts):
            rank[fr] = r; crowd[fr] = crowding_distance(F[fr])
        ch = []
        while len(ch) < POP:
            c1, c2 = sbx(tournament(pop, rank, crowd), tournament(pop, rank, crowd))
            ch.append(mut(c1))
            if len(ch) < POP: ch.append(mut(c2))
        ch = np.array(ch)
        Fc = np.array([robust_objectives(c) for c in ch])
        ap, aF = np.vstack([pop, ch]), np.vstack([F, Fc])
        fronts = fast_nondominated_sort(aF)
        idx = []
        for fr in fronts:
            if len(idx) + len(fr) <= POP: idx.extend(fr)
            else:
                cd = crowding_distance(aF[fr])
                idx.extend([fr[i] for i in np.argsort(-cd)[:POP-len(idx)]]); break
        pop, F = ap[idx], aF[idx]
        if (g+1) % 5 == 0:
            b = F[fast_nondominated_sort(F)[0]]
            print(f"  gen {g+1:3d}/{GEN} | front={len(b):3d} | minF1={b[:,0].min():.4f} "
                  f"minF4={b[:,3].min():.3e} | {time.time()-t0:6.1f}s", flush=True)

    fr0 = fast_nondominated_sort(F)[0]
    Pf, Ff = pop[fr0], F[fr0]
    ki = knee(Ff)
    print(f"\nselesai {time.time()-t0:.1f}s | front akhir {len(Pf)} solusi")
    print("=== KNEE POINT (produksi) ===")
    for n_, v in zip(NAMES, Pf[ki]):
        print(f"  {n_:>9s} = {v:.4f}")
    print("  F =", np.array2string(Ff[ki], precision=4))
    np.savetxt("pareto_front_prod.csv", np.hstack([Pf, Ff]), delimiter=",",
               header=",".join(NAMES + ["F1_maxDf", "F2_eMPP", "F3_eBat", "F4_p2p"]),
               comments="")
    print("pareto_front_prod.csv ditulis")
