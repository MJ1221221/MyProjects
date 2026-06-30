% plot_results.m
% Reads ../results/results.csv (produced by the C++ batch driver) and
% plots: (1) tip-deflection deviation between the coarse and fine mesh
% per configuration, and (2) tip deflection vs. beam length for the
% length sweep (C01-C08), to visualize the onset of wall contact /
% multistability discussed in docs/RESULTS.md.

T = readtable(fullfile('..', 'results', 'results.csv'));

figure('Name', 'Coarse vs Fine Mesh Deviation');
bar(categorical(T.id), T.tipDefl_deviation_pct);
yline(5, 'r--', '5% target');
xlabel('Configuration ID');
ylabel('Tip deflection deviation (%)');
title('Coarse mesh vs fine mesh tip-deflection deviation');
grid on;

% Length sweep is configurations C01-C08
lengthSweepMask = startsWith(T.id, 'C0') & (str2double(extractAfter(T.id,'C')) <= 8);
Tl = T(lengthSweepMask, :);
Tl = sortrows(Tl, 'L');

figure('Name', 'Tip Deflection vs Beam Length');
plot(Tl.L, Tl.lumped_tipDefl, '-o', 'DisplayName', 'Coarse mesh');
hold on;
plot(Tl.L, Tl.fem_tipDefl, '-s', 'DisplayName', 'Fine mesh');
xlabel('Beam length L (m)');
ylabel('Tip deflection (m)');
title('Tip deflection vs beam length (bowl radius R = 0.12 m)');
legend('Location', 'best');
grid on;

disp('Plots generated. Close figures to exit.');
