// main.cpp
// Batch driver: reads config/configs.csv (20+ beam-in-bowl configurations),
// solves equilibrium with both the lumped-link projected-gradient model
// and the FEM-style Newton-Raphson model, and writes a comparison table to
// results/results.csv plus per-configuration equilibrium shapes under
// results/shapes/.
#include "BeamConfig.hpp"
#include "LumpedSolver.hpp"
#include "FEMSolver.hpp"

#include <fstream>
#include <sstream>
#include <iostream>
#include <vector>
#include <cstdlib>
#include <iomanip>



static std::vector<BeamConfig> readConfigs(const std::string& path) {
    std::vector<BeamConfig> configs;
    std::ifstream f(path);
    if (!f) throw std::runtime_error("Cannot open config file: " + path);

    std::string line;
    std::getline(f, line); // header
    while (std::getline(f, line)) {
        if (line.empty()) continue;
        std::stringstream ss(line);
        std::string tok;
        BeamConfig c;
        std::getline(ss, c.id, ',');
        std::getline(ss, tok, ','); c.L  = std::stod(tok);
        std::getline(ss, tok, ','); c.EI = std::stod(tok);
        std::getline(ss, tok, ','); c.w  = std::stod(tok);
        std::getline(ss, tok, ','); c.R  = std::stod(tok);
        std::getline(ss, tok, ','); c.N  = std::stoi(tok);
        configs.push_back(c);
    }
    return configs;
}

static void writeShape(const std::string& path, const EquilibriumResult& r) {
    std::ofstream f(path);
    f << "x,z\n";
    for (auto& p : r.joints) f << p.x << "," << p.z << "\n";
}

int main(int argc, char** argv) {
    std::string configPath = (argc > 1) ? argv[1] : "config/configs.csv";
    std::string outDir     = (argc > 2) ? argv[2] : "results";

    system(("mkdir \"" + outDir + "\" 2>nul").c_str());
    system(("mkdir \"" + outDir + "/shapes\" 2>nul").c_str());  

    auto configs = readConfigs(configPath);
    std::ofstream out(outDir + "/results.csv");
    out << "id,L,EI,w,R,N,"
        << "lumped_tipDefl,lumped_energy,lumped_maxPen,lumped_iters,lumped_converged,"
        << "fem_tipDefl,fem_energy,fem_maxPen,fem_iters,fem_converged,"
        << "tipDefl_deviation_pct,energy_deviation_pct\n";
    out << std::setprecision(8);

    for (auto& c : configs) {
        std::cout << "Solving configuration " << c.id << " ..." << std::endl;

        LumpedSolver lumped(c);
        EquilibriumResult rl = lumped.solve();

        FEMSolver fem(c);
        EquilibriumResult rf = fem.solve();

        double tipDev = (rl.tipDeflection > 1e-9)
            ? std::fabs(rl.tipDeflection - rf.tipDeflection) / rl.tipDeflection * 100.0
            : std::fabs(rl.tipDeflection - rf.tipDeflection) * 100.0;
        double eDev = (std::fabs(rl.totalEnergy) > 1e-9)
            ? std::fabs(rl.totalEnergy - rf.totalEnergy) / std::fabs(rl.totalEnergy) * 100.0
            : std::fabs(rl.totalEnergy - rf.totalEnergy) * 100.0;

        out << c.id << "," << c.L << "," << c.EI << "," << c.w << "," << c.R << "," << c.N << ","
            << rl.tipDeflection << "," << rl.totalEnergy << "," << rl.maxPenetration << "," << rl.iterations << "," << rl.converged << ","
            << rf.tipDeflection << "," << rf.totalEnergy << "," << rf.maxPenetration << "," << rf.iterations << "," << rf.converged << ","
            << tipDev << "," << eDev << "\n";

        writeShape(outDir + "/shapes/" + c.id + "_lumped.csv", rl);
        writeShape(outDir + "/shapes/" + c.id + "_fem.csv", rf);
    }

    std::cout << "Done. Results written to " << outDir << "/results.csv" << std::endl;
    return 0;
}
