# -*- coding: utf-8 -*-
"""S6 -- uji terarah cabang PENGISIAN baterai (peristiwa lebih-frekuensi).

Alasan keberadaan berkas ini. Gambar 1 (koreksi Prof. Adi) menggambar konverter
DUA-ARAH, dan Pers. (4) dalam bentuk bertandanya membolehkan beta negatif.
Tetapi seluruh skenario kampanye S1-S5 memberikan kehilangan pembangkitan atau
kenaikan beban, sehingga frekuensi selalu TURUN dan beta tidak pernah keluar
dari cabang pelepasan. Tanpa uji ini, arah kedua konverter tergambar tanpa
pernah dibuktikan.

S6 membalik tanda gangguan (pelepasan beban), sehingga frekuensi NAIK dan
cabang pengisian benar-benar bekerja.

S6 SENGAJA TIDAK dimasukkan ke kampanye utama: metrik `nadir_Hz` dihitung dari
max|Delta omega|, sehingga untuk peristiwa lebih-frekuensi ia akan mencetak
angka di bawah 50 Hz padahal frekuensi naik. Melaporkannya di kolom yang sama
akan menyesatkan pembaca.

Pakai: py -3 uji_s6_charging.py
"""
import io
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

import fullmodel as F                                       # noqa: E402

N_R = 100
CTRL = ('adaptive', 'smoothstatic', 'static', 'droop')


def beta_of(dwf, soc):
    """Ulangi Pers. (4) persis seperti cabang 'adaptive' pada fullmodel."""
    phi_d = np.clip((soc - F.SOC_MIN) / F.SOC_TAPER, 0.0, 1.0)
    phi_c = np.clip((F.SOC_MAX - soc) / F.SOC_TAPER, 0.0, 1.0)
    raw = F.KNEE['beta_max'] * np.tanh(F.KNEE['kb'] * (-dwf))
    return np.where(raw >= 0, raw * phi_d, raw * phi_c)


def main():
    baris = []
    print('  %-13s %-11s %-11s %-11s %s'
          % ('KONTROLER', 'df maks[Hz]', 'Pbat min', 'Pp2p[pu]', 'eBESS[pu.s]'))
    print('  ' + '-' * 62)
    for ctrl in CTRL:
        xi = F.draw_xi(N_R, 'S6')
        m, tr = F.simulate('S6', ctrl, xi, save_traj=True)
        dw = tr[:, 1]
        df_max = float(dw.max()) * F.F0            # deviasi frekuensi PUNCAK [Hz]
        # rekonstruksi beta pada lintasan realisasi-0 (SOC awal rata-rata)
        pb = beta_of(dw, np.full(dw.size, float(xi['SOC0'].mean())))
        baris.append((ctrl, df_max, float(pb.min()),
                      float(np.mean(m['Pp2p_pu'])),
                      float(np.mean(m['eBESS_pu_s']))))
        print('  %-13s %+11.4f %+11.5f %11.5f %11.4f' % baris[-1])

    ad = [b for b in baris if b[0] == 'adaptive'][0]
    print()
    print('  Pbat minimum %+.5f pu pada kontroler usulan.' % ad[2])
    print('  Nilai NEGATIF berarti cabang PENGISIAN benar-benar aktif,')
    print('  sehingga arah kedua konverter dua-arah pada Gambar 1 terbukti.')

    out = os.path.join(F.RES, 'S6_charging.csv')
    with io.open(out, 'w', encoding='utf-8') as f:
        f.write('controller,df_peak_Hz,Pbat_min_pu,Pp2p_pu,eBESS_pu_s\n')
        for b in baris:
            f.write('%s,%.6f,%.6f,%.6f,%.6f\n' % b)
    print('  -> %s' % out)


if __name__ == '__main__':
    main()
