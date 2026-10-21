function y = boost_mppt(Vpv, IL, Vdc, t)
% Boost sinkron PV: MPPT P&O (langkah 2 V tiap 40 ms) -> loop tegangan PV -> loop arus induktor.
% Ts 2e-4, disampel di lembah pembawa segitiga 5 kHz. Keluaran y = [d; en; Vref].
persistent Vref dir Pacc nacc Pprev k xv xi
if isempty(Vref)
    Vref = 0.85*7*51.7; dir = -1; Pacc = 0; nacc = 0; Pprev = 0; k = 0; xv = 0; xi = 0;
end
Ts = 2e-4; T_EN = 0.05; STEP = 2.0; N_MPPT = 200;    % 200 x 2e-4 = 40 ms
VMIN = 0.60*7*51.7; VMAX = 0.95*7*51.7;
en = double(t >= T_EN);
if en > 0
    Pacc = Pacc + Vpv*IL; nacc = nacc + 1; k = k + 1;
    if k >= N_MPPT
        P = Pacc / nacc;
        if P < Pprev, dir = -dir; end
        Pprev = P; Vref = min(max(Vref + dir*STEP, VMIN), VMAX);
        Pacc = 0; nacc = 0; k = 0;
    end
end
% loop tegangan PV: Vpv di atas acuan -> tarik arus lebih besar
ev = Vpv - Vref;
xv = min(max(xv + en*200*Ts*ev, -400), 400);
Iref = min(max(1.0*ev + xv, 0), 400);
% loop arus induktor (sama dengan loop BESS): V_L = Vpv - (1-d) Vdc
e = Iref - IL;
xi = min(max(xi + en*720*Ts*e, -300), 300);
u = 3.8*e + xi;
if en == 0, xv = 0; xi = 0; end
d = 1 - (Vpv - u) / max(Vdc, 1);
d = min(max(d, 0.02), 0.98);
y = [d; en; Vref];
end
