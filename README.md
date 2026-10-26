# Adaptive MPPT–VIC coordination for grid-connected PV–BESS systems

Code and data accompanying the paper

> D. N. Prakoso, A. Soeprijanto, D. F. U. Putra, A. W. Wardhana, B. Winarno,
> N. A. Prabatama, *Adaptive Coordination of MPPT and Virtual Inertia Control
> in Grid-Connected PV-BESS Systems with Limit-Cycle Detection*, submitted to
> *Emerging Science Journal* (revision R1).

The repository reproduces the numbers, tables and figures of the paper: the
averaged PV–BESS model (Python, with a Julia port for cross-implementation
verification), the robust Monte Carlo–CVaR / NSGA-II tuning, the scenario
campaign S1–S5 with five controllers and 100 realisations, the describing
function and circle-criterion analysis, the robustness tests added in
revision R1, and the switching-level Simulink testbed.

Source comments are partly in Indonesian; function names, variables and all
outputs follow the notation of the paper.

## Contents

| Path | Content | Paper |
|---|---|---|
| `python/fullmodel.py` | Averaged model (single-diode PV, P&O MPPT, battery SOC, inverter lag, PLL, VIC, aggregate swing equation), controllers `adaptive` (proposed), `adaptgain`, `smoothstatic`, `static` (relay), `droop`; campaign S1–S5 × 5 controllers × 100 realisations (seed 7) | Tables 3–4, Fig. 4 |
| `python/stats_tests.py`, `python/make_tables.py` | Rank-sum tests and table rows from the campaign | Tables 3–4 |
| `python/s3_decomposition.py` | Power decomposition of the nominal S3 event | Fig. 5 |
| `python/df_prediction.py`, `python/circle_criterion.py` | Describing-function prediction of the relay limit cycle; circle-criterion absence certificate for the smooth gate | Sec. 4-3, 4-7 |
| `python/ablasi_reviewer.py` | Ablation of the coordination law (smooth-0.25, no α, no VIC) | Table 7, Sec. 4-9 |
| `python/adaptive_beta04.py`, `python/uji_s6_charging.py`, `python/uji_perturbasi_parameter.py` | Proposed scheme at β_max = 0.4, load-rejection test S6 (charging branch), parameter-perturbation check | Sec. 4-9, 4-11 |
| `python/plot_pareto.py` | Pareto front and knee point | Fig. 3 |
| `python/results/` | Raw and summary campaign results, nominal S3/S5 trajectories | |
| `julia/fullmodel.jl`, `julia/compare_crossimpl.py` | Line-by-line Julia port and Python–Julia trajectory comparison | Sec. 4-2 |
| `tuning/pareto_mc_tuning_fast.py` | Robust tuning: Monte Carlo sampling, CVaR (γ = 0.95), NSGA-II (60 × 80, N_MC = 200, seed 42) | Fig. 3 |
| `tuning/pareto_front_prod.csv` | Production Pareto front (knee: index 27) | |
| `revision_r1/simulation/model_r1.py` | Extension of the averaged model (imports `python/fullmodel.py`): OU load noise, event sequences, relay and Nordic FFR triggers, SOC taper, governor (1/R, T_g) | |
| `revision_r1/simulation/uji_governor.py`, `gambar_peta_lc.py` | Existence of the limit cycle over primary-reserve gain and load step, condition hΣ < ΔP_L < hΣ + M | Fig. 7, Sec. 4-7 |
| `revision_r1/simulation/uji_ffr.py` | Relay baselines with realistic trigger (49.7 Hz, latched FFR) | Table 6, Sec. 4-8 |
| `revision_r1/simulation/uji_fcr.py` | Scenarios S3–S4 repeated with primary reserve (aggregate first-order governor, 5 % and 20 % droop, common random numbers) | Sec. 4-8 |
| `revision_r1/simulation/uji_alpha.py` | Severity weight α under ambient noise, low inertia and repeated events | Table 7, Sec. 4-9 |
| `revision_r1/simulation/uji_soc.py` | Battery state of charge near its limits | Sec. 4-10 |
| `revision_r1/simulation/efek_tabel.py`, `statistik_r1.py` | Effect sizes: median difference, 95 % bootstrap CI, Cliff's δ | Table 5 |
| `revision_r1/simulation/sapuan_H.py` | Inertia sweep, nominal S3 | Fig. 6, Sec. 4-6 |
| `revision_r1/simulation/simulink/testbed/` | Switching-level testbed (Simulink, Specialized Power Systems, discrete 2 µs): `Testbed_R1.slx`, its build script `bangun_testbed.m`, controllers `ctrl_*.m`, run script `jalankan_testbed.m`, results `hasil_S5_mode{0..3}.mat`, analysis `analisis_testbed.py` | Table 8, Fig. 8, Sec. 4-12 |
| `revision_r1/results/` | Raw results, logs and effect-size tables of the R1 tests | |
| `revision_r1/figures/` | Figures as printed (PDF, SVG, PNG 600 dpi), `render_ulang.py` (Figs. 3–6), `buat_flowchart_iso.py` (Fig. 1), `fig1_arch.tex` and `buat_gbr2_pptx.py` (Fig. 2, TikZ and PowerPoint); Figs. 7–8 come from `simulation/gambar_peta_lc.py` and `simulation/simulink/testbed/analisis_testbed.py`. **These are the figures of the paper** | Figs. 1–8 |
| `matlab/PVonGrid_patched.slx` | Earlier switching model, kept **only** as the block source (PV array, MOSFETs) for `bangun_testbed.m`; its results are not used in the paper because its DC-side power balance is not conserved | |
| `figures/` | Output folder for the diagnostic plots written by `python/fullmodel.py`, `plot_pareto.py` and `s3_decomposition.py` when they are run (empty in the repository). These plots are not the figures of the paper | |

## Reproduce

Python 3.11 or newer:

```sh
pip install -r requirements.txt
```

Averaged model and campaign (from `python/`):

```sh
python fullmodel.py           # campaign, results/metrics_*.csv and trajectories
python stats_tests.py
python make_tables.py
python s3_decomposition.py
python df_prediction.py
python circle_criterion.py
python ablasi_reviewer.py
python plot_pareto.py
```

Robust tuning (from `tuning/`): `python pareto_mc_tuning_fast.py`.

Cross-implementation (from `julia/`, Julia 1.10 or newer, after `fullmodel.py`):

```sh
julia fullmodel.jl
python compare_crossimpl.py
```

Revision R1 tests (from `revision_r1/simulation/`):

```sh
python efek_tabel.py
python uji_ffr.py
python uji_alpha.py
python uji_soc.py
python uji_governor.py
python uji_fcr.py
python gambar_peta_lc.py
python sapuan_H.py
python ../figures/render_ulang.py
```

Switching-level testbed (MATLAB R2025a, Simulink, Simscape Electrical –
Specialized Power Systems). From `revision_r1/simulation/simulink/testbed/`:

```matlab
bangun_testbed                                   % rebuilds Testbed_R1.slx
MODE = 1; TSTOP = 8; TAG = 'S5_mode1'; jalankan_testbed
```

`MODE`: 0 no support, 1 proposed, 2 static relay, 3 FFR relay at 49.7 Hz. One
8-s run takes about four minutes. Then `python analisis_testbed.py`.

All random seeds are fixed, so the results are regenerated exactly.

## Licence

Code: MIT (see `LICENSE`). Data, results and figures: CC BY 4.0.
