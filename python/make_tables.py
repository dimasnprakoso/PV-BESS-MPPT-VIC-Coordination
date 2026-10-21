# -*- coding: utf-8 -*-
"""Bangun baris LaTeX Tabel kampanye & biaya energi dari metrics_summary.csv."""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
rows = {}
with open(os.path.join(HERE, "results", "metrics_summary.csv")) as f:
    for r in csv.DictReader(f):
        rows[(r["scenario"], r["controller"])] = {k: float(v) for k, v in r.items()
                                                  if k not in ("scenario", "controller")}

NAMA = {"adaptive": "proposed", "adaptgain": "gain-adap.",
        "smoothstatic": "smooth-st.", "static": "static", "droop": "droop"}
ORD = ["adaptive", "adaptgain", "smoothstatic", "static", "droop"]


def pm(m, s, fmt):
    return f"${m:{fmt}}\\pm{s:{fmt}}$"


print("% ---- Tabel kampanye (nadir, RoCoF, Pp2p) ----")
for sc in ["S1", "S2", "S3", "S4", "S5"]:
    for i, c in enumerate(ORD):
        d = rows[(sc, c)]
        lead = sc if i == 0 else "  "
        print(f"{lead} & {NAMA[c]:10s} & {pm(d['nadir_Hz_mean'], d['nadir_Hz_std'], '.2f')} & "
              f"{pm(d['maxRoCoF_Hzps_mean'], d['maxRoCoF_Hzps_std'], '.2f')} & "
              f"{pm(d['Pp2p_pu_mean'], d['Pp2p_pu_std'], '.4f')} \\\\")
    if sc != "S5":
        print("\\midrule")

print()
print("% ---- Tabel biaya energi (eMPP, eBESS), S3-S5 ----")
for sc in ["S3", "S4", "S5"]:
    for i, c in enumerate(ORD):
        d = rows[(sc, c)]
        lead = sc if i == 0 else "  "
        print(f"{lead} & {NAMA[c]:10s} & {pm(d['eMPP_pu_s_mean'], d['eMPP_pu_s_std'], '.2f')} & "
              f"{pm(d['eBESS_pu_s_mean'], d['eBESS_pu_s_std'], '.2f')} \\\\")
    if sc != "S5":
        print("\\midrule")

print()
print("% ---- angka kunci utk teks ----")
a5, s5 = rows[("S5", "adaptive")], rows[("S5", "static")]
g5, m5 = rows[("S5", "adaptgain")], rows[("S5", "smoothstatic")]
print(f"S5 statik/adaptif Pp2p = {s5['Pp2p_pu_mean']/a5['Pp2p_pu_mean']:.0f}x")
print(f"S5 adaptgain/static Pp2p = {100*g5['Pp2p_pu_mean']/s5['Pp2p_pu_mean']:.0f}%")
for sc in ["S2", "S3", "S4", "S5"]:
    a, st, ss = rows[(sc, "adaptive")], rows[(sc, "static")], rows[(sc, "smoothstatic")]
    print(f"{sc}: eBESS adaptif vs static {100*(1-a['eBESS_pu_s_mean']/st['eBESS_pu_s_mean']):+.0f}% "
          f"| vs smooth-st {100*(1-a['eBESS_pu_s_mean']/ss['eBESS_pu_s_mean']):+.0f}% "
          f"| nadir adaptif-smoothst = {a['nadir_Hz_mean']-ss['nadir_Hz_mean']:+.2f} Hz")
print(f"S2 adaptive Pp2p = {rows[('S2','adaptive')]['Pp2p_pu_mean']:.3f} "
      f"+- {rows[('S2','adaptive')]['Pp2p_pu_std']:.3f} (CoV "
      f"{rows[('S2','adaptive')]['Pp2p_pu_std']/rows[('S2','adaptive')]['Pp2p_pu_mean']*100:.0f}%)")
