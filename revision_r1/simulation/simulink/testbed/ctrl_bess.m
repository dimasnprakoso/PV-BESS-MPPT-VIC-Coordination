function y = looparus(Pref, Vb, Ib, Vdc, t)
% Loop arus konverter BESS dua arah (Ts 2e-4, disampel di lembah pembawa segitiga 5 kHz
% sehingga sampel = arus rata-rata; versi 2e-5 dengan pembawa gigi gergaji ber-aliasing). Ib positif = pelepasan (baterai -> DC-link);
% tanda dicek 20 Okt: duty 0,98 menghasilkan Ib = +2800 A (hubung singkat lewat Q_lo).
% Boost rata-rata: V_L = Vb - (1-d) Vdc  ->  d = 1 - (Vb - u)/Vdc, u = PI(Iref - Ib).
% Kedua gate dimatikan (en = 0) sampai T_EN agar DC-link selesai start-up.
persistent xi
if isempty(xi), xi = 0; end
Ts = 2e-4; Kp = 1.9; Ki = 360; IMAX = 120; T_EN = 0.05;
en = double(t >= T_EN);
Iref = Pref / max(Vb, 300);
Iref = min(max(Iref, -IMAX), IMAX);
e = Iref - Ib;
if en == 0, xi = 0; end
u = Kp * e + xi;
xi = min(max(xi + en * Ki * Ts * e, -300), 300);
d = 1 - (Vb - u) / max(Vdc, 1);
d = min(max(d, 0.02), 0.98);
y = [d; en; xi];
end
