function y = pll_dq(vabc, iabc)
% PLL kerangka-sinkron (SRF) + transformasi dq (Ts 1e-4). Arus positif = inverter -> jaringan.
% Keluaran y = [theta; f; vd; vq; id; iq; P; Q]
persistent th w xi
if isempty(th), th = 0; w = 2*pi*50; xi = 0; end
Ts = 1e-4; W0 = 2*pi*50; VPK = 400*sqrt(2/3);
Kp = 176; Ki = 15791;                      % omega_n = 2*pi*20, zeta = 0,7 (ternormalisasi)
va = 2/3*(vabc(1) - 0.5*vabc(2) - 0.5*vabc(3));
vb = 2/3*(sqrt(3)/2)*(vabc(2) - vabc(3));
ia = 2/3*(iabc(1) - 0.5*iabc(2) - 0.5*iabc(3));
ib = 2/3*(sqrt(3)/2)*(iabc(2) - iabc(3));
c = cos(th); s = sin(th);
vd =  c*va + s*vb;  vq = -s*va + c*vb;
id =  c*ia + s*ib;  iq = -s*ia + c*ib;
e = vq / VPK;
xi = xi + Ki*Ts*e;
w = W0 + Kp*e + xi;
th = th + w*Ts;
if th > 2*pi, th = th - 2*pi; end
P = 1.5*(vd*id + vq*iq);  Q = 1.5*(vq*id - vd*iq);
y = [th; w/(2*pi); vd; vq; id; iq; P; Q];
end
