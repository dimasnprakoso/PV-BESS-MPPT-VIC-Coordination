function Psup = koordinasi(f, soc, t, mode)
% Koordinasi dukungan frekuensi (Ts 1e-4), cermin python/fullmodel.py.
% mode 0 = tanpa dukungan, 1 = skema usulan (knee), 2 = relai statis naskah,
% 3 = relai FFR 49,7 Hz (h 0,006, M 0,15), 9 = uji: 20 kW konstan mulai 0,6 s. Keluaran: P_sup [W] (positif = ekspor).
persistent Dwf
if isempty(Dwf), Dwf = 0; end
Ts = 1e-4; tau = 0.02; S = 100e3; T_ON = 1.0;
Dw = (f - 50) / 50;
rocof = (Dw - Dwf) / tau;
Dwf = Dwf + Ts * (Dw - Dwf) / tau;
s = soc / 100;
phi_d = min(max((s - 0.20) / 0.05, 0), 1);
phi_c = min(max((0.90 - s) / 0.05, 0), 1);
P = 0;
if mode == 1
    Pvic = -(1.0045 * Dwf + 0.0317 * rocof);
    a = 1 / (1 + 47.483 * abs(Dwf) + 1.0 * abs(rocof));
    raw = 0.2497 * tanh(45.797 * (-Dwf));
    if raw >= 0, Pb = raw * phi_d; else, Pb = raw * phi_c; end
    P = (1 - a) * Pvic + Pb;
elseif mode == 2 || mode == 3
    if mode == 2, h = 0.02; M = 0.40; else, h = 0.006; M = 0.15; end
    Pvic = -(0.5 * Dwf + 0.1 * rocof);
    st = 0;
    if Dwf < -h, st = 1; elseif Dwf > h, st = -1; end
    if st > 0, Pb = M * phi_d; elseif st < 0, Pb = -M * phi_c; else, Pb = 0; end
    P = Pvic + Pb;
end
if t < T_ON, P = 0; end
if mode == 9 && t >= 0.6, P = 20e3 / S; end   % uji polaritas/aliran daya
Psup = P * S;
end
