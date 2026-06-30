function plot_shape(configId, bowlRadius)
% plot_shape(configId, bowlRadius)
% Plots the equilibrium beam centerline (coarse and fine mesh) for a
% given configuration ID against the hemispherical bowl outline.
%
% Example:
%   plot_shape('C05', 0.12)

if nargin < 2
    bowlRadius = 0.12;
end

lumpedFile = fullfile('..', 'results', 'shapes', [configId '_lumped.csv']);
femFile    = fullfile('..', 'results', 'shapes', [configId '_fem.csv']);

Tl = readtable(lumpedFile);
Tf = readtable(femFile);

theta = linspace(pi, 2*pi, 200); % lower half of the bowl rim, z <= 0
bowlX = bowlRadius * cos(theta);
bowlZ = bowlRadius * sin(theta);

figure('Name', ['Equilibrium shape: ' configId]);
plot(bowlX, bowlZ, 'k-', 'LineWidth', 1.5, 'DisplayName', 'Bowl wall');
hold on;
plot(Tl.x, Tl.z, '-o', 'DisplayName', 'Coarse mesh (numerical model)');
plot(Tf.x, Tf.z, '-s', 'DisplayName', 'Fine mesh (FEM model)');
axis equal;
xlabel('x (m)');
ylabel('z (m)');
title(['Beam equilibrium shape in bowl: ' configId]);
legend('Location', 'best');
grid on;

end
