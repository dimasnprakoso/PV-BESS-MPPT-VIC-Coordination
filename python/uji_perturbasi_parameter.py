# -*- coding: utf-8 -*-
"""Uji perturbasi: apakah setiap parameter BENAR-BENAR memengaruhi hasil?

Terpakai di kode belum tentu berpengaruh -- sebuah konstanta bisa berada di
cabang yang tak pernah diambil, atau efeknya ternetralkan. Uji ini mengubah
nilai satu parameter, menjalankan ulang potongan kampanye, dan mengukur
apakah metriknya bergerak.

Modul disalin dan disunting sumbernya lalu diimpor segar, bukan ditambal
setelah impor, supaya besaran turunan seperti PV_SCALE ikut dihitung ulang.
"""
import importlib.util
import io
import os
import re
import sys

import numpy as np

SRC = r'e:\AntiGravity\Proposal_Disertasi Dimas\paper_studi1\python\fullmodel.py'
TMP = os.path.join(__import__('tempfile').gettempdir(), '_fm_uji.py')
asli = io.open(SRC, encoding='utf-8').read()

# (nama, pola baris asli, pengganti, keterangan)
UJI = [
    ('MPPT_STEP', r'MPPT_STEP = 1\.0', 'MPPT_STEP = 3.0', 'langkah P&O 1,0 -> 3,0 V'),
    ('KI_T',      r'KI_T     = 0\.0005', 'KI_T     = 0.0050', 'koef. suhu x10'),
    ('A_DIODE',   r'A_DIODE  = 1\.1', 'A_DIODE  = 1.4', 'idealitas 1,1 -> 1,4'),
    ('TAU_INV',   r'TAU_INV, TAU_PLL = 0\.05, 0\.02',
                  'TAU_INV, TAU_PLL = 0.10, 0.02', 'lag inverter 50 -> 100 ms'),
    ('TAU_PLL',   r'TAU_INV, TAU_PLL = 0\.05, 0\.02',
                  'TAU_INV, TAU_PLL = 0.05, 0.04', 'filter PLL 20 -> 40 ms'),
    ('SOC_TAPER', r'SOC_TAPER = 0\.05', 'SOC_TAPER = 0.20', 'taper SOC 0,05 -> 0,20'),
    ('ETA',       r'ETA_C = ETA_D = 0\.95', 'ETA_C = ETA_D = 0.70', 'efisiensi 0,95 -> 0,70'),
    ('E_RATED',   r'E_RATED = 50e3 \* 3600\.0', 'E_RATED = 5e3 * 3600.0',
                  'energi BESS 50 -> 5 kWh'),
    ('H_range',   r'H = rng\.uniform\(1\.5, 4\.0, n\)',
                  'H = rng.uniform(3.0, 4.0, n)', 'sebaran H dipersempit'),
    ('SOC0_range', r'SOC0=rng\.uniform\(0\.30, 0\.80, n\)',
                   'SOC0=rng.uniform(0.21, 0.24, n)', 'SOC awal dekat batas bawah'),
    ('Gjit_range', r'Gjit=rng\.uniform\(0\.95, 1\.05, n\)',
                   'Gjit=rng.uniform(0.70, 0.75, n)', 'jitter iradiansi digeser'),
    ('M_RELAY',   r'M_RELAY, HYST = 0\.40, 0\.02',
                  'M_RELAY, HYST = 0.10, 0.02', 'rating relay 0,40 -> 0,10'),
    ('HYST',      r'M_RELAY, HYST = 0\.40, 0\.02',
                  'M_RELAY, HYST = 0.40, 0.10', 'histeresis 0,02 -> 0,10'),
]

N = 12
SCN = 'S3'


def jalankan(sumber, ctrl):
    io.open(TMP, 'w', encoding='utf-8').write(sumber)
    spec = importlib.util.spec_from_file_location('_fm_uji', TMP)
    m = importlib.util.module_from_spec(spec)
    sys.modules['_fm_uji'] = m
    cwd = os.getcwd()
    os.chdir(os.path.dirname(SRC))
    try:
        spec.loader.exec_module(m)
        xi = m.draw_xi(N, SCN)
        met, _ = m.simulate(SCN, ctrl, xi)
        return (float(np.mean(met['nadir_Hz'])),
                float(np.mean(met['Pp2p_pu'])),
                float(np.mean(met['eBESS_pu_s'])))
    finally:
        os.chdir(cwd)


print('  Basis: %s, kontroler adaptive kecuali disebut lain, n=%d' % (SCN, N))
b_ad = jalankan(asli, 'adaptive')
b_st = jalankan(asli, 'static')
print('  acuan adaptive: nadir=%.4f Pp2p=%.6f eBESS=%.4f' % b_ad)
print('  acuan static  : nadir=%.4f Pp2p=%.6f eBESS=%.4f' % b_st)
print()
print('  %-11s %-30s %-9s %s' % ('PARAM', 'PERUBAHAN', 'PENGARUH', 'delta terbesar'))
print('  ' + '-' * 74)

for nama, pola, ganti, ket in UJI:
    baru = re.sub(pola, ganti, asli)
    if baru == asli:
        print('  %-11s %-30s POLA TIDAK COCOK' % (nama, ket))
        continue
    ctrl = 'static' if nama in ('M_RELAY', 'HYST') else 'adaptive'
    acuan = b_st if ctrl == 'static' else b_ad
    try:
        hasil = jalankan(baru, ctrl)
    except Exception as e:
        print('  %-11s %-30s GAGAL: %s' % (nama, ket, e))
        continue
    d = [abs(h - a) / (abs(a) + 1e-12) for h, a in zip(hasil, acuan)]
    maks = max(d)
    tanda = 'YA' if maks > 1e-9 else '** TIDAK **'
    print('  %-11s %-30s %-9s %.3e' % (nama, ket, tanda, maks))

if os.path.exists(TMP):
    os.remove(TMP)
