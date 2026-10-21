%% bangun_testbed.m -- testbed tingkat-switching BARU untuk revisi R1 (komentar R2-3)
% Menggantikan matlab/PVonGrid_patched.slx yang cacat neraca daya (see README).
%
% Rangkaian daya (Specialized Power Systems, diskret 2 us):
%   PV array (modul 350 W parameter model lama, 7 seri x 40 paralel = 98 kW STC) + C_pv 2 mF
%     -> boost sinkron (setengah jembatan MOSFET, L 2 mH) -> DC-link 800 V (2 x 20 mF, titik tengah ditanahkan)
%   Baterai Li-ion 400 V 150 Ah (60 kWh) -> L 1 mH -> setengah jembatan MOSFET -> DC-link
%   VSI 2-level (Universal Bridge IGBT/dioda, PWM 5 kHz) -> L 1,5 mH -> PCC -> jaringan
%   Jaringan: tiga Controlled Voltage Source (400 V, Yg) + RL (0,05 ohm, 0,5 mH); frekuensi dari
%   emulator persamaan ayun (S_g 100 kW, H 2 s, D 1, dP_L 0,1 pu pada t = 2 s).
% Kendali (MATLAB Function): PLL SRF + dq (1e-4), VSI dq + pengatur Vdc (1e-4), boost MPPT P&O
% (2e-4), loop arus BESS (2e-4), koordinasi (1e-4; MODE_R1), emulator (1e-5).
here = fileparts(mfilename('fullpath'));
mdl = 'Testbed_R1';
if bdIsLoaded(mdl), close_system(mdl, 0); end
if exist(fullfile(here, [mdl '.slx']), 'file'), delete(fullfile(here, [mdl '.slx'])); end
new_system(mdl); load_system('simulink'); load_system('powerlib');
lama = fullfile(here, '..', '..', '..', '..', 'matlab', 'PVonGrid_patched.slx');
load_system(lama); L0 = 'PVonGrid_patched';

set_param(mdl, 'Solver', 'ode1', 'FixedStep', '2e-6', 'StopTime', 'TSTOP_R1', ...
    'SaveOutput', 'off', 'SaveTime', 'off', 'SignalLogging', 'off', 'ReturnWorkspaceOutputs', 'on');
add_block('spspowerguiLib/powergui', [mdl '/powergui'], 'Position', [20 20 80 60]);
set_param([mdl '/powergui'], 'SimulationMode', 'Discrete', 'SampleTime', '2e-6');

%% ---------------- rangkaian daya
% PV
add_block([L0 '/PV '], [mdl '/PV'], 'Position', [100 200 160 280]);
set_param([mdl '/PV'], 'Nser', '7', 'Npar', '40');
add_block('simulink/Sources/Constant', [mdl '/G'], 'Value', 'G_R1', 'Position', [30 200 60 220]);
add_block('simulink/Sources/Constant', [mdl '/Tc'], 'Value', '28', 'Position', [30 240 60 260]);
add_line(mdl, 'G/1', 'PV/1'); add_line(mdl, 'Tc/1', 'PV/2');
add_block('simulink/Sinks/Terminator', [mdl '/tPV'], 'Position', [180 300 190 310]); add_line(mdl, 'PV/1', 'tPV/1');
rlc(mdl, 'Cpv', 'RC', '1e-3', '0', '2e-3', [220 200 250 240], 'InitialVoltage', '350');
vmeas(mdl, 'mVpv', [260 280 290 310]);
rlc(mdl, 'Lpv', 'RL', '5e-3', '2e-3', '0', [300 160 340 180]);
imeas(mdl, 'mIpv', [360 160 390 180]);
add_block([L0 '/Battrai Energy Stroge System/Mosfet'], [mdl '/Qpv_lo'], 'Position', [420 220 460 260]);
add_block([L0 '/Battrai Energy Stroge System/Mosfet1'], [mdl '/Qpv_hi'], 'Position', [420 100 460 140]);
% DC-link: dua kapasitor seri, titik tengah ke tanah
rlc(mdl, 'Cdc1', 'RC', '1e-3', '0', '20e-3', [560 100 590 140], 'InitialVoltage', '400');
rlc(mdl, 'Cdc2', 'RC', '1e-3', '0', '20e-3', [560 220 590 260], 'InitialVoltage', '400');
add_block('spsGroundLib/Ground', [mdl '/Gdc'], 'Position', [620 170 640 190]);
vmeas(mdl, 'mVdc', [600 280 630 310]);
% BESS
add_block([L0 '/Battrai Energy Stroge System/Battery'], [mdl '/Bat'], 'Position', [100 420 160 480]);
set_param([mdl '/Bat'], 'SOC', 'SOC0_R1');
vmeas(mdl, 'mVb', [180 500 210 530]);
rlc(mdl, 'Lb', 'RL', '0.02', '1e-3', '0', [300 400 340 420]);
imeas(mdl, 'mIb', [360 400 390 420]);
add_block([L0 '/Battrai Energy Stroge System/Mosfet'], [mdl '/Qb_lo'], 'Position', [420 460 460 500]);
add_block([L0 '/Battrai Energy Stroge System/Mosfet1'], [mdl '/Qb_hi'], 'Position', [420 340 460 380]);
for q = {'Qpv_lo', 'Qpv_hi', 'Qb_lo', 'Qb_hi'}, set_param([mdl '/' q{1}], 'Ron', '1e-3'); end
% VSI
add_block([L0 '/Inverter/IGBT - Diode Bridge 6 Pulses'], [mdl '/VSI'], 'Position', [700 140 760 260]);
add_block([L0 '/VSI Current Control /PWM Generator (2-Level) '], [mdl '/PWMvsi'], 'Position', [700 330 760 370]);
set_param([mdl '/PWMvsi'], 'Fc', '5000', 'Ts', '2e-6', 'ModulatingSignals', 'off');
add_block('simulink/Sinks/Terminator', [mdl '/tCar'], 'Position', [780 360 790 370]); add_line(mdl, 'PWMvsi/2', 'tCar/1');
add_block('simulink/Math Operations/Product', [mdl '/gateVSI'], 'Position', [780 320 800 340]);
add_line(mdl, 'PWMvsi/1', 'gateVSI/1'); add_line(mdl, 'gateVSI/1', 'VSI/1');
add_block('spsThreePhaseSeriesRLCBranchLib/Three-Phase Series RLC Branch', [mdl '/Lf'], 'Position', [820 150 860 250]);
set_param([mdl '/Lf'], 'BranchType', 'RL', 'Resistance', '0.01', 'Inductance', '1.5e-3');
add_block('spsThreePhaseVIMeasurementLib/Three-Phase V-I Measurement', [mdl '/PCC'], 'Position', [900 150 940 250]);
set_param([mdl '/PCC'], 'VoltageMeasurement', 'phase-to-ground', 'CurrentMeasurement', 'yes');
% jaringan
for k = 1:3
    add_block('spsControlledVoltageSourceLib/Controlled Voltage Source', sprintf('%s/Vg%d', mdl, k), ...
        'Position', [1100 120+60*k 1140 150+60*k], 'Initialize', 'off');
    rlc(mdl, sprintf('Zg%d', k), 'RL', '0.05', '0.5e-3', '0', [1000 125+60*k 1040 145+60*k]);
    add_block('spsGroundLib/Ground', sprintf('%s/Gg%d', mdl, k), 'Position', [1180 130+60*k 1200 150+60*k]);
end
close_system(L0, 0);

% sambungan fisik
P = @(b) get_param([mdl '/' b], 'PortHandles');
c = @(a, b) add_line(mdl, a, b, 'autorouting', 'on');
pv = P('PV'); cpv = P('Cpv'); mvpv = P('mVpv'); lpv = P('Lpv'); ipv = P('mIpv');
qpl = P('Qpv_lo'); qph = P('Qpv_hi'); c1 = P('Cdc1'); c2 = P('Cdc2'); gdc = P('Gdc'); mvdc = P('mVdc');
bat = P('Bat'); mvb = P('mVb'); lb = P('Lb'); ib = P('mIb'); qbl = P('Qb_lo'); qbh = P('Qb_hi');
vsi = P('VSI'); lf = P('Lf'); pcc = P('PCC');
% node PV+ / DC- bersama
c(pv.RConn(1), cpv.LConn(1)); c(pv.RConn(2), cpv.RConn(1));
c(mvpv.LConn(1), pv.RConn(1)); c(mvpv.LConn(2), pv.RConn(2));
c(pv.RConn(1), lpv.LConn(1)); c(lpv.RConn(1), ipv.LConn(1));
c(ipv.RConn(1), qpl.LConn(1)); c(ipv.RConn(1), qph.RConn(1));          % titik tengah boost
c(qph.LConn(1), c1.LConn(1));                                          % DC+
c(c1.RConn(1), c2.LConn(1)); c(c1.RConn(1), gdc.LConn(1));             % titik tengah DC ke tanah
c(c2.RConn(1), qpl.RConn(1)); c(c2.RConn(1), pv.RConn(2));             % DC-
c(mvdc.LConn(1), c1.LConn(1)); c(mvdc.LConn(2), c2.RConn(1));
% BESS
c(mvb.LConn(1), bat.LConn(1)); c(mvb.LConn(2), bat.LConn(2));
c(bat.LConn(1), lb.LConn(1)); c(lb.RConn(1), ib.LConn(1));
c(ib.RConn(1), qbl.LConn(1)); c(ib.RConn(1), qbh.RConn(1));
c(qbh.LConn(1), c1.LConn(1)); c(qbl.RConn(1), bat.LConn(2)); c(bat.LConn(2), c2.RConn(1));
% VSI
imeas(mdl, 'mIdc', [640 140 670 160]); idc = P('mIdc');
c(c1.LConn(1), idc.LConn(1)); c(idc.RConn(1), vsi.RConn(1)); c(vsi.RConn(2), c2.RConn(1));
for k = 1:3
    c(vsi.LConn(k), lf.LConn(k)); c(lf.RConn(k), pcc.LConn(k));
    zg = P(sprintf('Zg%d', k)); vg = P(sprintf('Vg%d', k)); gg = P(sprintf('Gg%d', k));
    c(pcc.RConn(k), zg.LConn(1)); c(zg.RConn(1), vg.RConn(1)); c(vg.LConn(1), gg.LConn(1));
end

%% ---------------- kendali
add_block('simulink/Sources/Clock', [mdl '/clk'], 'Position', [20 600 40 620]);
goto(mdl, 'clk/1', 't', [60 600]);
goto(mdl, 'mVpv/1', 'Vpv', [300 320]); goto(mdl, 'mIpv/1', 'Ipv', [400 190]);
goto(mdl, 'mVdc/1', 'Vdc', [640 320]); goto(mdl, 'mVb/1', 'Vb', [220 540]); goto(mdl, 'mIb/1', 'Ib', [400 430]);
% filter anti-aliasing orde-1 2 kHz (riak switching PCC ber-aliasing bila disampel sinkron PWM)
for k = 1:2
    nm = {'aaV', 'aaI'}; add_block('simulink/Discrete/Discrete Filter', [mdl '/' nm{k}], 'Numerator', '[0.024819]', ...
        'Denominator', '[1 -0.975181]', 'SampleTime', '2e-6', 'InputProcessing', 'Elements as channels (sample based)', ...
        'Position', [960 100+120*k 1000 130+120*k]);
    add_line(mdl, sprintf('PCC/%d', k), [nm{k} '/1']);
end
goto(mdl, 'aaV/1', 'vabc', [1020 220]); goto(mdl, 'aaI/1', 'iabc', [1020 340]);
add_block('simulink/Signal Routing/Bus Selector', [mdl '/selBat'], 'Position', [180 440 185 470]);
add_line(mdl, 'Bat/1', 'selBat/1');
nm = cellfun(@char, get_param([mdl '/selBat'], 'InputSignals'), 'UniformOutput', false);
set_param([mdl '/selBat'], 'OutputSignals', nm{find(contains(nm, 'SOC'), 1)});
goto(mdl, 'selBat/1', 'SOC', [200 440]);

mf(mdl, 'PLL', 1e-4, 'ctrl_pll_dq.m', {'vabc', 'iabc'}, [1300 100]);
goto(mdl, 'PLL/1', 'dq', [1500 100]);
add_block('simulink/Signal Routing/Selector', [mdl '/selF'], 'InputPortWidth', '8', 'Indices', '2', 'Position', [1520 160 1540 180]);
add_block('simulink/Signal Routing/Selector', [mdl '/selP'], 'InputPortWidth', '8', 'Indices', '7', 'Position', [1520 200 1540 220]);
add_line(mdl, 'PLL/1', 'selF/1'); add_line(mdl, 'PLL/1', 'selP/1');
goto(mdl, 'selF/1', 'fpll', [1560 160]); goto(mdl, 'selP/1', 'Pg', [1560 200]);
% P_dc umpan maju = Vpv*Ipv + Vb*Ib
add_block('simulink/Math Operations/Product', [mdl '/pPV'], 'Position', [1300 300 1320 320]);
add_block('simulink/Math Operations/Product', [mdl '/pB'], 'Position', [1300 340 1320 360]);
add_block('simulink/Math Operations/Add', [mdl '/pDC'], 'Position', [1340 310 1360 350]);
from(mdl, 'Vpv', 'pPV/1', [1260 300]); from(mdl, 'Ipv', 'pPV/2', [1260 320]);
from(mdl, 'Vb', 'pB/1', [1260 340]); from(mdl, 'Ib', 'pB/2', [1260 360]);
add_line(mdl, 'pPV/1', 'pDC/1'); add_line(mdl, 'pB/1', 'pDC/2');
add_block('simulink/Discrete/Discrete Transfer Fcn', [mdl '/fDC'], 'Numerator', '[0.0198]', 'Denominator', '[1 -0.9802]', ...
    'SampleTime', '1e-4', 'Position', [1380 320 1420 340]);      % filter 5 ms
add_line(mdl, 'pDC/1', 'fDC/1'); goto(mdl, 'fDC/1', 'Pdc', [1440 320]);
goto(mdl, 'pPV/1', 'Ppv', [1340 280]); goto(mdl, 'pB/1', 'Pbat', [1340 370]);

mf(mdl, 'VSIctrl', 1e-4, 'ctrl_vsi.m', {'dq', 'Vdc', 'Pdc', 't'}, [1300 450]);
add_block('simulink/Signal Routing/Demux', [mdl '/dmxV'], 'Outputs', '[3 1]', 'Position', [1500 450 1505 500]);
add_line(mdl, 'VSIctrl/1', 'dmxV/1');
goto(mdl, 'dmxV/1', 'mabc', [1520 450]); goto(mdl, 'dmxV/2', 'enV', [1520 490]);
from(mdl, 'mabc', 'PWMvsi/1', [650 330]); from(mdl, 'enV', 'gateVSI/2', [740 300]);

mf(mdl, 'BoostCtrl', 2e-4, 'ctrl_boost_mppt.m', {'Vpv', 'Ipv', 'Vdc', 't'}, [1300 600]);
add_block('simulink/Signal Routing/Demux', [mdl '/dmxB'], 'Outputs', '3', 'Position', [1500 600 1505 660]);
add_line(mdl, 'BoostCtrl/1', 'dmxB/1');
goto(mdl, 'dmxB/3', 'Vref', [1520 650]);
pwm_leg(mdl, 'PVleg', 'dmxB/1', 'dmxB/2', 'Qpv_lo', 'Qpv_hi', [1550 600]);

mf(mdl, 'Koordinasi', 1e-4, 'ctrl_koordinasi.m', {'fpll', 'SOC', 't'}, [1300 750]);
add_block('simulink/Sources/Constant', [mdl '/mode'], 'Value', 'MODE_R1', 'Position', [1240 840 1270 860]);
add_line(mdl, 'mode/1', 'Koordinasi/4');
goto(mdl, 'Koordinasi/1', 'Psup', [1500 750]);
mf(mdl, 'BESSctrl', 2e-4, 'ctrl_bess.m', {'Psup', 'Vb', 'Ib', 'Vdc', 't'}, [1300 900]);
add_block('simulink/Signal Routing/Demux', [mdl '/dmxBs'], 'Outputs', '3', 'Position', [1500 900 1505 960]);
add_line(mdl, 'BESSctrl/1', 'dmxBs/1');
add_block('simulink/Sinks/Terminator', [mdl '/tXi'], 'Position', [1520 950 1530 960]); add_line(mdl, 'dmxBs/3', 'tXi/1');
pwm_leg(mdl, 'Bleg', 'dmxBs/1', 'dmxBs/2', 'Qb_lo', 'Qb_hi', [1550 900]);

mf(mdl, 'Emulator', 1e-5, 'ctrl_emulator.m', {'Pg', 't'}, [1300 1100]);
% putus loop aljabar P -> tegangan sumber
ph = get_param([mdl '/Emulator'], 'PortHandles'); delete_line(get_param(ph.Inport(1), 'Line'));
add_block('simulink/Discrete/Unit Delay', [mdl '/zP'], 'SampleTime', '1e-4', 'Position', [1240 1100 1260 1120]);
from(mdl, 'Pg', 'zP/1', [1200 1100]); add_line(mdl, 'zP/1', 'Emulator/1');
add_block('simulink/Signal Routing/Demux', [mdl '/dmxE'], 'Outputs', '4', 'Position', [1500 1100 1505 1180]);
add_line(mdl, 'Emulator/1', 'dmxE/1');
for k = 1:3, goto(mdl, sprintf('dmxE/%d', k), sprintf('vg%d', k), [1520 1090+20*k]); from(mdl, sprintf('vg%d', k), sprintf('Vg%d/1', k), [1060 120+60*k]); end
goto(mdl, 'dmxE/4', 'fgrid', [1520 1180]);

% pengukuran silang neraca daya: P_dc VSI = Vdc*Idc, P sesaat PCC = sum(v.*i), keduanya rerata 20 ms
add_block('simulink/Math Operations/Product', [mdl '/pIdc'], 'Position', [1300 1250 1320 1270]);
from(mdl, 'Vdc', 'pIdc/1', [1260 1250]); goto(mdl, 'mIdc/1', 'Idc', [700 170]); from(mdl, 'Idc', 'pIdc/2', [1260 1270]);
add_block('simulink/Math Operations/Dot Product', [mdl '/pInst'], 'Position', [1300 1300 1320 1320]);
from(mdl, 'vabc', 'pInst/1', [1260 1300]); from(mdl, 'iabc', 'pInst/2', [1260 1320]);
for nm = {'pIdc', 'pInst'}
    add_block('simulink/Discrete/Discrete Transfer Fcn', [mdl '/a_' nm{1}], 'Numerator', '[0.000999500]', ...
        'Denominator', '[1 -0.9990005]', 'SampleTime', '2e-5', 'Position', [1340 1250 1380 1270]);  % rerata ~20 ms
    add_line(mdl, [nm{1} '/1'], ['a_' nm{1} '/1']);
end
goto(mdl, 'a_pIdc/1', 'PdcVSI', [1400 1250]); goto(mdl, 'a_pInst/1', 'Pinst', [1400 1300]);

%% ---------------- pencatatan (1 kHz)
tags = {'t', 'fgrid', 'fpll', 'Pg', 'Psup', 'Pbat', 'Ppv', 'SOC', 'Vdc', 'Vpv', 'Vref', 'Ib', 'PdcVSI', 'Pinst'};
for i = 1:numel(tags)
    f = sprintf('%s/lf_%s', mdl, tags{i}); w = sprintf('%s/lw_%s', mdl, tags{i});
    add_block('simulink/Signal Routing/From', f, 'GotoTag', tags{i}, 'Position', [1800 100+40*i 1840 120+40*i]);
    add_block('simulink/Sinks/To Workspace', w, 'VariableName', ['L_' tags{i}], 'SaveFormat', 'Array', ...
        'SampleTime', '1e-3', 'Position', [1880 100+40*i 1960 120+40*i]);
    add_line(mdl, sprintf('lf_%s/1', tags{i}), sprintf('lw_%s/1', tags{i}));
end
save_system(mdl, fullfile(here, [mdl '.slx']));
close_system(mdl, 0);
fprintf('%s tersimpan\n', mdl);

%% ---------------- fungsi bantu
function rlc(mdl, nm, typ, R, L, C, pos, varargin)
    add_block('spsSeriesRLCBranchLib/Series RLC Branch', [mdl '/' nm], 'Position', pos);
    set_param([mdl '/' nm], 'BranchType', typ, 'Resistance', R, 'Inductance', L, 'Capacitance', C);
    if ~isempty(varargin), set_param([mdl '/' nm], 'Setx0', 'on', varargin{:}); end
end
function vmeas(mdl, nm, pos)
    add_block('spsVoltageMeasurementLib/Voltage Measurement', [mdl '/' nm], 'Position', pos);
end
function imeas(mdl, nm, pos)
    add_block('spsCurrentMeasurementLib/Current Measurement', [mdl '/' nm], 'Position', pos);
end
function goto(mdl, src, tag, xy)
    b = sprintf('%s/g_%s', mdl, tag);
    add_block('simulink/Signal Routing/Goto', b, 'GotoTag', tag, 'TagVisibility', 'global', ...
        'Position', [xy(1) xy(2) xy(1)+40 xy(2)+20]);
    add_line(mdl, src, sprintf('g_%s/1', tag));
end
function from(mdl, tag, dst, xy)
    persistent n
    if isempty(n), n = 0; end
    n = n + 1; b = sprintf('%s/f%d_%s', mdl, n, tag);
    add_block('simulink/Signal Routing/From', b, 'GotoTag', tag, 'Position', [xy(1) xy(2) xy(1)+40 xy(2)+20]);
    add_line(mdl, sprintf('f%d_%s/1', n, tag), dst);
end
function mf(mdl, nm, ts, file, ins, xy)
    p = [mdl '/' nm];
    add_block('simulink/User-Defined Functions/MATLAB Function', p, 'Position', [xy(1) xy(2) xy(1)+160 xy(2)+30*numel(ins)]);
    ch = sfroot().find('-isa', 'Stateflow.EMChart', 'Path', p);
    ch.Script = fileread(fullfile(evalin('base', 'here'), file));
    ch.ChartUpdate = 'DISCRETE'; ch.SampleTime = num2str(ts);
    for i = 1:numel(ins), from(mdl, ins{i}, sprintf('%s/%d', nm, i), [xy(1)-80 xy(2)+30*(i-1)]); end
end
function pwm_leg(mdl, nm, dsrc, esrc, qlo, qhi, xy)
    % pembawa segitiga 5 kHz (lembah di kelipatan 2e-4); Q_lo = d > pembawa, Q_hi = komplemen
    x = xy(1); y = xy(2);
    add_block('simulink/Sources/Repeating Sequence', [mdl '/' nm '_car'], 'rep_seq_t', '[0 1e-4 2e-4]', ...
        'rep_seq_y', '[0 1 0]', 'Position', [x y+40 x+30 y+60]);
    add_block('simulink/Logic and Bit Operations/Relational Operator', [mdl '/' nm '_cmp'], 'Operator', '>', 'Position', [x+60 y x+90 y+40]);
    add_block('simulink/Logic and Bit Operations/Compare To Constant', [mdl '/' nm '_en'], 'relop', '>', 'const', '0.5', 'Position', [x+60 y+70 x+90 y+90]);
    add_block('simulink/Logic and Bit Operations/Logical Operator', [mdl '/' nm '_not'], 'Operator', 'NOT', 'Position', [x+110 y+40 x+130 y+60]);
    add_block('simulink/Logic and Bit Operations/Logical Operator', [mdl '/' nm '_alo'], 'Operator', 'AND', 'Position', [x+150 y x+170 y+30]);
    add_block('simulink/Logic and Bit Operations/Logical Operator', [mdl '/' nm '_ahi'], 'Operator', 'AND', 'Position', [x+150 y+40 x+170 y+70]);
    add_block('simulink/Signal Attributes/Data Type Conversion', [mdl '/' nm '_dlo'], 'OutDataTypeStr', 'double', 'Position', [x+190 y x+220 y+20]);
    add_block('simulink/Signal Attributes/Data Type Conversion', [mdl '/' nm '_dhi'], 'OutDataTypeStr', 'double', 'Position', [x+190 y+40 x+220 y+60]);
    add_line(mdl, dsrc, [nm '_cmp/1']); add_line(mdl, [nm '_car/1'], [nm '_cmp/2']); add_line(mdl, esrc, [nm '_en/1']);
    add_line(mdl, [nm '_cmp/1'], [nm '_alo/1']); add_line(mdl, [nm '_en/1'], [nm '_alo/2']);
    add_line(mdl, [nm '_cmp/1'], [nm '_not/1']); add_line(mdl, [nm '_not/1'], [nm '_ahi/1']); add_line(mdl, [nm '_en/1'], [nm '_ahi/2']);
    add_line(mdl, [nm '_alo/1'], [nm '_dlo/1']); add_line(mdl, [nm '_ahi/1'], [nm '_dhi/1']);
    add_line(mdl, [nm '_dlo/1'], [qlo '/1']); add_line(mdl, [nm '_dhi/1'], [qhi '/1']);
end
