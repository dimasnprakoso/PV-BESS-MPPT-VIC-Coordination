%% jalankan_testbed.m -- satu run testbed. Variabel masukan (opsional, set sebelum run):
%   MODE (0 tanpa dukungan, 1 usulan, 2 relai statis, 3 relai FFR 49,7 Hz, 9 uji 20 kW)
%   TSTOP [s], SOC0 [%], G [W/m2], TAG (nama berkas hasil)
here = fileparts(mfilename('fullpath')); cd(here);
if ~exist('MODE', 'var'), MODE = 0; end
if ~exist('TSTOP', 'var'), TSTOP = 0.8; end
if ~exist('SOC0', 'var'), SOC0 = 60; end
if ~exist('G', 'var'), G = 1000; end
if ~exist('TAG', 'var'), TAG = sprintf('mode%d_%gs', MODE, TSTOP); end
mdl = 'Testbed_R1'; load_system(fullfile(here, [mdl '.slx']));
assignin('base', 'MODE_R1', MODE); assignin('base', 'TSTOP_R1', TSTOP);
assignin('base', 'SOC0_R1', SOC0); assignin('base', 'G_R1', G);
tic; out = sim(mdl); wall = toc;
fprintf('SIM OK %s: %.1f s simulasi dalam %.0f s\n', TAG, TSTOP, wall);
S = struct();
for v = {'t', 'fgrid', 'fpll', 'Pg', 'Psup', 'Pbat', 'Ppv', 'SOC', 'Vdc', 'Vpv', 'Vref', 'Ib', 'PdcVSI', 'Pinst'}
    S.(v{1}) = out.get(['L_' v{1}]);
end
save(fullfile(here, ['hasil_' TAG '.mat']), 'S', 'MODE', 'TSTOP', 'SOC0', 'G', 'wall');
t = S.t; tt = linspace(TSTOP/8, TSTOP, 8);
fprintf('%-6s', 't'); fprintf('%10.3f', tt); fprintf('\n');
for v = {'Vdc', 'Vpv', 'Vref', 'Ppv', 'PdcVSI', 'Pinst', 'Pg', 'Psup', 'Pbat', 'Ib', 'fpll', 'fgrid', 'SOC'}
    x = S.(v{1}); fprintf('%-6s', v{1});
    for k = 1:numel(tt), j = t > tt(k) - 0.02 & t <= tt(k); fprintf('%10.4g', mean(x(j))); end
    fprintf('\n');
end
close_system(mdl, 0);
