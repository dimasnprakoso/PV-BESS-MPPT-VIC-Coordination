function y = emulator(Pg, t)
% Emulator jaringan agregat (Ts 1e-5): tegangan tiga fasa dengan frekuensi dari persamaan ayun
%   2H dDw/dt = (P_eksp - P_jadwal)/S_g - dP_L(t) - D Dw     (pu pada S_g)
% P_eksp = P terukur di PCC dari pll_dq (positif = ekspor), difilter 20 ms.
% Ayun dibekukan sampai T_SCHED (inisialisasi MPPT); P_jadwal = P_eksp rerata 0,3 s terakhir.
% Keluaran y = [va; vb; vc; f_grid].
persistent th Dw Pf Pacc nacc Psch
if isempty(th), th = 0; Dw = 0; Pf = 0; Pacc = 0; nacc = 0; Psch = 0; end
Ts = 1e-5; S = 100e3; H = 2.0; D = 1.0; DPL = 0.10;
T_SCHED = 1.5; T_EVT = 2.0; VPK = 400 * sqrt(2/3);
Pf = Pf + Ts * (Pg - Pf) / 0.02;
if t >= T_SCHED - 0.3 && t < T_SCHED
    Pacc = Pacc + Pf; nacc = nacc + 1;
end
if t >= T_SCHED
    if nacc > 0 && Psch == 0, Psch = Pacc / nacc; end
    dist = 0;
    if t >= T_EVT, dist = DPL; end
    Dw = Dw + Ts * ((Pf - Psch) / S - dist - D * Dw) / (2 * H);
    Dw = min(max(Dw, -0.2), 0.2);
end
f = 50 * (1 + Dw);
th = th + Ts * 2 * pi * f;
if th > 2 * pi, th = th - 2 * pi; end
y = [VPK * sin(th); VPK * sin(th - 2*pi/3); VPK * sin(th + 2*pi/3); f];
end
