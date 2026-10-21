# fullmodel.jl — Model penuh AVERAGED PV-BESS grid-connected (Julia)
# Port SATU-BANDING-SATU dari ../python/fullmodel.py (dinamika, konstanta, urutan
# update identik) untuk verifikasi cross-implementation pada MODEL PENUH:
#   epsilon = ||x_py - x_jl||_2 / ||x_py||_2   (target < 1%)
# Menjalankan skenario nominal S3 & S5 (adaptive + static), menulis trayektori
# terdesimasi 10x ke results/traj_<scn>_<ctrl>_julia.csv.
# Jalankan:  julia fullmodel.jl

const S_BASE = 100e3
const F0     = 50.0

const NS, NP   = 2 * 72, 250
const ISC_STC  = 10.36 * NP
const VOC_CELL = 0.72
const KI_T     = 0.0005
const A_DIODE  = 1.1
const Q_E, KB_B = 1.602e-19, 1.381e-23
const RS_ARR   = 0.35 / NP * NS / 144.0

const TAU_INV, TAU_PLL = 0.05, 0.02
const DT, T_END = 1e-4, 8.0
const N_STEP = Int(round(T_END / DT))
const MPPT_DT = 0.02
const MPPT_STEP = 1.0

# knee point PRODUKSI (samakan dengan Python)
const Kd_A, Kj_A, ka_A, kaw_A, kb_A, bmax_A = 1.0045, 0.0317, 47.483, 1.0, 45.797, 0.2497
const Kd_S, Kj_S = 0.50, 0.10          # VIC statis
const M_RELAY, HYST = 0.40, 0.02

const E_RATED = 50e3 * 3600.0
const ETA_C = 0.95; const ETA_D = 0.95
const SOC_MIN, SOC_MAX, SOC_TAPER = 0.20, 0.90, 0.05

function pv_current(V, G, Tc)
    Vt  = A_DIODE * KB_B * (273.15 + Tc) / Q_E * NS
    Iph = ISC_STC * (G / 1000.0) * (1.0 + KI_T * (Tc - 25.0))
    Io  = ISC_STC * exp(-VOC_CELL * NS / Vt)
    I = max(Iph - Io * (exp(V / Vt) - 1.0), 0.0)
    for _ in 1:3
        f  = Iph - Io * (exp((V + I * RS_ARR) / Vt) - 1.0) - I
        df = -Io * exp((V + I * RS_ARR) / Vt) * RS_ARR / Vt - 1.0
        I = max(I - f / df, 0.0)
    end
    return I
end

# Kalibrasi-mandiri identik Python: P_MPP(STC) = 0,95 pu
const PV_SCALE = let
    Vs = range(0.55 * VOC_CELL * NS, 0.95 * VOC_CELL * NS, length=200)
    Pmax = maximum(v * pv_current(v, 1000.0, 25.0) for v in Vs)
    0.95 * S_BASE / Pmax
end

# profil iradiansi (S3/S5: konstan 1000)
g_profile(t) = 1000.0

function simulate(ctrl::String; H=2.0, DPL=0.10, SOC0=0.60, Tc=28.0)
    Dw = 0.0; Pinj = 0.0; Dwf = 0.0
    soc = SOC0; relay = 1.0
    Vpv = 0.80 * VOC_CELL * NS
    dV = MPPT_STEP
    Ppv_prev = 0.0; Ppv = 0.0
    t_evt = 2.0
    k_sched = Int(round(1.5 / DT))
    Psched = 0.0
    mppt_every = Int(round(MPPT_DT / DT))

    traj = zeros(N_STEP, 2)
    for k in 0:(N_STEP - 1)
        t = k * DT
        if k % mppt_every == 0
            G = g_profile(t)
            Ipv = pv_current(Vpv, G, Tc)
            Ppv = Vpv * Ipv * PV_SCALE
            dV = (Ppv >= Ppv_prev) ? dV : -dV
            Vpv = clamp(Vpv + dV, 0.55 * VOC_CELL * NS, 0.95 * VOC_CELL * NS)
            Ppv_prev = Ppv
        end
        Pmppt = Ppv / S_BASE

        rocof = (Dw - Dwf) / TAU_PLL
        phi_d = clamp((soc - SOC_MIN) / SOC_TAPER, 0.0, 1.0)
        phi_c = clamp((SOC_MAX - soc) / SOC_TAPER, 0.0, 1.0)

        local Pref, Pbat
        if ctrl == "adaptive"
            Pvic  = -(Kd_A * Dwf + Kj_A * rocof)
            alpha = 1.0 / (1.0 + ka_A * abs(Dwf) + kaw_A * abs(rocof))
            w = 1.0 - alpha
            raw = bmax_A * tanh(kb_A * (-Dwf))
            Pbat = raw >= 0 ? raw * phi_d : raw * phi_c
            Pref = Pmppt + w * Pvic + Pbat
        elseif ctrl == "adaptgain"
            # VIC gain-adaptif (alternating inertia + adaptive damping),
            # koordinasi tetap statis (relay BESS) — identik Python
            accel = (Dwf * rocof) > 0
            Kj_eff = accel ? 3.0 * Kj_S : 0.5 * Kj_S
            Kd_eff = Kd_S * (1.0 + 2.0 * min(abs(Dwf) / 0.01, 1.0))
            Pvic = -(Kd_eff * Dwf + Kj_eff * rocof)
            state = Dwf < -HYST ? 1.0 : (Dwf > HYST ? -1.0 : 0.0)
            Pbat = M_RELAY * state * (state > 0 ? phi_d : phi_c)
            Pref = Pmppt + Pvic + Pbat
        elseif ctrl == "smoothstatic"
            # VIC gain tetap + BESS droop tanh halus non-adaptif — identik Python
            Pvic = -(Kd_S * Dwf + Kj_S * rocof)
            raw = M_RELAY * tanh(kb_A * (-Dwf))
            Pbat = raw >= 0 ? raw * phi_d : raw * phi_c
            Pref = Pmppt + Pvic + Pbat
        elseif ctrl == "droop"
            Pvic = -(Kd_S * Dwf)
            Pbat = 0.0
            Pref = Pmppt + Pvic
        else  # static: relay 3-keadaan dead-band (identik Python)
            Pvic = -(Kd_S * Dwf + Kj_S * rocof)
            state = Dwf < -HYST ? 1.0 : (Dwf > HYST ? -1.0 : 0.0)
            Pbat = M_RELAY * state * (state > 0 ? phi_d : phi_c)
            Pref = Pmppt + Pvic + Pbat
        end

        Pb_W = Pbat * S_BASE
        soc -= DT * (Pb_W > 0 ? Pb_W / ETA_D : Pb_W * ETA_C) / E_RATED
        soc = clamp(soc, 0.0, 1.0)

        if k == k_sched
            Psched = Pinj
        end
        dist = (t >= t_evt) ? DPL : 0.0
        Pinj += DT * (clamp(Pref, -1.2, 1.2) - Pinj) / TAU_INV
        if k >= k_sched
            Dw += DT * ((Pinj - Psched) - dist - 1.0 * Dw) / (2.0 * H)
        end
        Dwf += DT * (Dw - Dwf) / TAU_PLL

        traj[k + 1, 1] = Pinj
        traj[k + 1, 2] = Dw
    end
    return traj
end

resdir = joinpath(@__DIR__, "results")
isdir(resdir) || mkdir(resdir)
for scn in ("S3", "S5"), ctrl in ("adaptive", "adaptgain", "smoothstatic", "static", "droop")
    tr = simulate(ctrl)
    open(joinpath(resdir, "traj_$(scn)_$(ctrl)_julia.csv"), "w") do io
        println(io, "Pinj_pu,Dw_pu")
        for k in 1:10:N_STEP
            println(io, tr[k, 1], ",", tr[k, 2])
        end
    end
    # metrik ringkas jendela tunak (6-8 s)
    i0 = Int(round(0.75 * N_STEP))
    p2p = maximum(tr[i0:end, 1]) - minimum(tr[i0:end, 1])
    println("JULIA $scn $ctrl : P_p2p tunak = $p2p pu")
end
println("trayektori Julia ditulis ke results/")
