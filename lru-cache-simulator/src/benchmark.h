/*
 * benchmark.h
 *
 * Benchmarking harness for the multi-level cache.
 *
 * Three access patterns:
 *
 *   SEQUENTIAL  – keys 0,1,2,...,N-1,0,1,... in strict order.
 *                 Worst case for LRU: early keys are already evicted
 *                 by the time we loop back. Lowest hit rate.
 *
 *   RANDOM      – keys chosen uniformly at random from [0, num_unique_keys).
 *                 Moderate hit rate.
 *
 *   HOTSPOT     – 80% of accesses hit the top 20% of keys (Zipfian model).
 *                 Mirrors real workloads (hot DB rows, popular pages).
 *                 Highest hit rate.
 *
 * Workflow:
 *   1. Warm the cache (insert all keys once) so we don't measure cold-start.
 *   2. Reset stats.
 *   3. Execute the access sequence (mix of GETs and PUTs per write_ratio).
 *   4. Return a BenchmarkResult.
 */

#pragma once

#include "cache_system.h"
#include <vector>
#include <random>
#include <chrono>
#include <string>
#include <iostream>
#include <iomanip>
#include <algorithm>

enum class AccessPattern { SEQUENTIAL, RANDOM, HOTSPOT };

static const char* pattern_name(AccessPattern p) {
    switch (p) {
        case AccessPattern::SEQUENTIAL: return "Sequential";
        case AccessPattern::RANDOM:     return "Random";
        case AccessPattern::HOTSPOT:    return "Hotspot (80/20 Zipfian)";
    }
    return "Unknown";
}

// ─────────────────────────────────────────────────────────────────────────────
//  BenchmarkConfig
// ─────────────────────────────────────────────────────────────────────────────
struct BenchmarkConfig {
    int           num_operations  = 1000;
    int           num_unique_keys = 200;
    int           l1_capacity     = 20;
    int           l2_capacity     = 80;
    double        write_ratio     = 0.30;   // fraction of ops that are PUT
    long long     ttl_ms          = 0;      // 0 = never expires
    AccessPattern pattern         = AccessPattern::RANDOM;
    int           seed            = 42;
};

// ─────────────────────────────────────────────────────────────────────────────
//  BenchmarkResult
// ─────────────────────────────────────────────────────────────────────────────
struct BenchmarkResult {
    std::string pattern_name;
    int         total_ops;
    int         reads;
    int         writes;
    int         l1_hits;
    int         l2_hits;
    int         misses;
    double      hit_rate_pct;       // (l1_hits + l2_hits) / reads * 100
    double      l1_hit_rate_pct;    // l1_hits / reads * 100
    int         l1_evictions;       // L1 overflows → demoted to L2
    int         l2_evictions;       // L2 overflows → permanently lost
    long long   duration_us;        // wall-clock time in microseconds
};

// ─────────────────────────────────────────────────────────────────────────────
//  BenchmarkRunner
// ─────────────────────────────────────────────────────────────────────────────
class BenchmarkRunner {
public:

    static BenchmarkResult run(const BenchmarkConfig& cfg) {
        MultiLevelCache cache(cfg.l1_capacity, cfg.l2_capacity);
        std::mt19937 rng(cfg.seed);
        std::uniform_real_distribution<double> coin(0.0, 1.0);

        // ── Warm start: pre-populate all keys ────────────────────────
        for (int i = 0; i < cfg.num_unique_keys; i++)
            cache.put("key_" + std::to_string(i), "val_" + std::to_string(i));
        cache.reset_stats();   // only measure the workload below

        // ── Build access sequence ─────────────────────────────────────
        std::vector<std::string> seq;
        seq.reserve(cfg.num_operations);

        std::vector<bool> is_write(cfg.num_operations);
        for (int i = 0; i < cfg.num_operations; i++)
            is_write[i] = coin(rng) < cfg.write_ratio;

        switch (cfg.pattern) {
            case AccessPattern::SEQUENTIAL:
                for (int i = 0; i < cfg.num_operations; i++)
                    seq.push_back("key_" + std::to_string(i % cfg.num_unique_keys));
                break;

            case AccessPattern::RANDOM: {
                std::uniform_int_distribution<int> d(0, cfg.num_unique_keys - 1);
                for (int i = 0; i < cfg.num_operations; i++)
                    seq.push_back("key_" + std::to_string(d(rng)));
                break;
            }

            case AccessPattern::HOTSPOT: {
                // Top 20% of keys get 80% of traffic
                int hot = std::max(1, cfg.num_unique_keys / 5);
                std::uniform_int_distribution<int> hot_d(0, hot - 1);
                std::uniform_int_distribution<int> cold_d(hot, cfg.num_unique_keys - 1);
                for (int i = 0; i < cfg.num_operations; i++) {
                    if (coin(rng) < 0.80)
                        seq.push_back("key_" + std::to_string(hot_d(rng)));
                    else
                        seq.push_back("key_" + std::to_string(cold_d(rng)));
                }
                break;
            }
        }

        // ── Execute workload ──────────────────────────────────────────
        int reads = 0, writes = 0;
        auto t0 = std::chrono::high_resolution_clock::now();

        for (int i = 0; i < cfg.num_operations; i++) {
            const std::string& k = seq[i];
            if (is_write[i]) {
                cache.put(k, "v_" + std::to_string(i), cfg.ttl_ms);
                writes++;
            } else {
                cache.get(k);
                reads++;
            }
        }

        auto t1      = std::chrono::high_resolution_clock::now();
        long long us = std::chrono::duration_cast<std::chrono::microseconds>(t1 - t0).count();

        // ── Collect stats ─────────────────────────────────────────────
        const auto& s1 = cache.l1().stats();
        const auto& s2 = cache.l2().stats();
        int l1h  = cache.l1_hits();
        int l2h  = cache.l2_hits();
        int miss = cache.total_misses();

        BenchmarkResult r;
        r.pattern_name    = ::pattern_name(cfg.pattern);
        r.total_ops       = cfg.num_operations;
        r.reads           = reads;
        r.writes          = writes;
        r.l1_hits         = l1h;
        r.l2_hits         = l2h;
        r.misses          = miss;
        r.hit_rate_pct    = reads > 0 ? 100.0 * (l1h + l2h) / reads : 0.0;
        r.l1_hit_rate_pct = reads > 0 ? 100.0 * l1h / reads : 0.0;
        r.l1_evictions    = s1.evictions;
        r.l2_evictions    = s2.evictions;
        r.duration_us     = us;
        return r;
    }

    static void print_result(const BenchmarkResult& r) {
        const int W = 35;
        int filled  = static_cast<int>(W * r.hit_rate_pct / 100.0 + 0.5);

        std::cout
            << "  Pattern      : " << r.pattern_name << "\n"
            << "  Operations   : " << r.total_ops
            << " (" << r.reads << " reads, " << r.writes << " writes)\n"
            << "  L1 Hits      : " << r.l1_hits << "\n"
            << "  L2 Hits      : " << r.l2_hits << "\n"
            << "  Misses       : " << r.misses << "\n"
            << "  L1 Evictions : " << r.l1_evictions << "  (demoted -> L2)\n"
            << "  L2 Evictions : " << r.l2_evictions << "  (permanently lost)\n"
            << "  Duration     : " << r.duration_us << " us\n"
            << "  Hit Rate     : [";
        for (int i = 0; i < W; i++) std::cout << (i < filled ? '#' : '-');
        std::cout << "] "
            << std::fixed << std::setprecision(1) << r.hit_rate_pct << "%"
            << "  (L1 alone: " << r.l1_hit_rate_pct << "%)\n";
    }

    // Run all three patterns back-to-back with the same settings
    static void run_all(int l1_cap = 20, int l2_cap = 80,
                        int ops = 1000, int keys = 200) {
        std::cout
            << "\n╔══════════════════════════════════════════════════════════╗\n"
            << "║         LRU MULTI-LEVEL CACHE -- BENCHMARK SUITE         ║\n"
            << "╠══════════════════════════════════════════════════════════╣\n"
            << "║  L1 capacity = " << std::setw(4) << l1_cap
            << "   L2 capacity = " << std::setw(4) << l2_cap
            << "                  ║\n"
            << "║  Operations  = " << std::setw(4) << ops
            << "   Key space   = " << std::setw(4) << keys
            << "                  ║\n"
            << "╚══════════════════════════════════════════════════════════╝\n";

        for (auto pat : { AccessPattern::SEQUENTIAL,
                          AccessPattern::RANDOM,
                          AccessPattern::HOTSPOT }) {
            BenchmarkConfig cfg;
            cfg.l1_capacity     = l1_cap;
            cfg.l2_capacity     = l2_cap;
            cfg.num_operations  = ops;
            cfg.num_unique_keys = keys;
            cfg.pattern         = pat;

            auto r = run(cfg);
            std::cout << "\n-- " << r.pattern_name << " --\n";
            print_result(r);
        }
        std::cout << "\n";
    }
};
