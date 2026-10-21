function y = vsi(dq, Vdc, Pdc, t)
% Kendali arus dq VSI 2-level + pengatur tegangan DC (Ts 1e-4).
% dq = [theta; f; vd; vq; id; iq; P; Q] dari pll_dq. Pdc = P_PV + P_BESS terukur (umpan maju).
% Keluaran y = [ma; mb; mc; en]  (indeks modulasi, [-1, 1]).
persistent xd xq xv
if isempty(xd), xd = 0; xq = 0; xv = 0; end
Ts = 1e-4; L = 1.5e-3; VREF = 800; T_EN = 0.02; IMAX = 320;
th = dq(1); w = 2*pi*dq(2); vd = dq(3); vq = dq(4); id = dq(5); iq = dq(6);
en = double(t >= T_EN);
% pengatur tegangan DC: Vdc di atas acuan -> ekspor lebih banyak
ev = Vdc - VREF;
xv = min(max(xv + en*35*Ts*ev, -IMAX), IMAX);
id_ff = Pdc / (1.5*max(vd, 200));
id_ref = min(max(id_ff + 1.5*ev + xv, -IMAX), IMAX);
iq_ref = 0;                                          % faktor daya satu
% arus
Kp = 2.83; Ki = 300;
ed_ = id_ref - id; eq_ = iq_ref - iq;
xd = min(max(xd + en*Ki*Ts*ed_, -200), 200);
xq = min(max(xq + en*Ki*Ts*eq_, -200), 200);
ud = vd - w*L*iq + Kp*ed_ + xd;
uq = vq + w*L*id + Kp*eq_ + xq;
if en == 0, xd = 0; xq = 0; xv = 0; ud = vd; uq = vq; end
thm = th + 1.5*Ts*w;                                 % kompensasi tunda komputasi + PWM
c = cos(thm); s = sin(thm);
ua = c*ud - s*uq; ub = s*ud + c*uq;
uabc = [ua; -0.5*ua + sqrt(3)/2*ub; -0.5*ua - sqrt(3)/2*ub];
m = uabc / (max(Vdc, 100)/2);
m = min(max(m, -1), 1);
y = [m; en];
end
