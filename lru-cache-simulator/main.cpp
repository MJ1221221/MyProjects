/*
 * main.cpp
 *
 * Entry point — interactive CLI for the LRU Multi-Level Cache Simulator.
 *
 * Menu:
 *   1. Benchmark        – runs all 3 access patterns, prints stats
 *   2. Custom Benchmark – you pick L1/L2 sizes, ops, key-space, pattern
 *   3. Interactive Mode – type put/get commands manually
 *   4. TTL Expiry Demo  – watch an entry expire after its TTL elapses
 *   5. Exit
 *
 * Compile (requires GCC 7+ or Clang 5+ with C++17):
 *   g++ -std=c++17 -O2 main.cpp -o cache_sim
 *
 * Run:
 *   ./cache_sim        (Linux / macOS)
 *   cache_sim.exe      (Windows)
 */

#include <iostream>
#include <sstream>
#include <string>
#include <limits>
#include <thread>
#include <chrono>
#include <algorithm>

#include "src/lru_cache.h"
#include "src/cache_system.h"
#include "src/benchmark.h"

static void flush_cin() {
    std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
}

static void print_banner() {
    std::cout
        << "\n"
        << "╔══════════════════════════════════════════════════════════════╗\n"
        << "║         LRU-BASED MULTI-LEVEL CACHE SIMULATOR                ║\n"
        << "║                                                              ║\n"
        << "║  Data structures inside:                                     ║\n"
        << "║    Doubly Linked List  →  O(1) move-to-front & eviction      ║\n"
        << "║    HashMap             →  O(1) key lookup                    ║\n"
        << "║    Min-Heap            →  O(log n) TTL expiry                ║\n"
        << "║    L1 / L2 hierarchy   →  promotion & demotion               ║\n"
        << "╚══════════════════════════════════════════════════════════════╝\n\n";
}

// ─────────────────────────────────────────────────────────────────────────────
//  Menu option 3 — Interactive mode
//  Commands:  put <key> <value> [ttl_ms]  |  get <key>  |  stats  |  quit
// ─────────────────────────────────────────────────────────────────────────────
static void interactive_mode() {
    std::cout << "\n  Enter L1 capacity (e.g. 5): ";
    int l1_cap = 5; std::cin >> l1_cap; flush_cin();

    std::cout << "  Enter L2 capacity (e.g. 20): ";
    int l2_cap = 20; std::cin >> l2_cap; flush_cin();

    l1_cap = std::max(1, l1_cap);
    l2_cap = std::max(1, l2_cap);

    MultiLevelCache cache(l1_cap, l2_cap);

    std::cout
        << "\n  Cache ready.  L1=" << l1_cap << "  L2=" << l2_cap << "\n"
        << "\n  Commands:\n"
        << "    put <key> <value> [ttl_ms]   ->  insert or update\n"
        << "    get <key>                    ->  look up a key\n"
        << "    stats                        ->  show hit/miss report\n"
        << "    quit                         ->  return to main menu\n\n";

    std::string line;
    while (true) {
        std::cout << "  cache> ";
        if (!std::getline(std::cin, line)) break;

        std::istringstream ss(line);
        std::string cmd;
        ss >> cmd;

        if (cmd == "put") {
            std::string key, val;
            long long ttl = 0;
            ss >> key >> val >> ttl;
            if (key.empty() || val.empty()) {
                std::cout << "  Usage: put <key> <value> [ttl_ms]\n";
                continue;
            }
            cache.put(key, val, ttl);
            std::cout << "  [OK] Stored  [" << key << "] = \"" << val << "\"";
            if (ttl > 0) std::cout << "   (expires in " << ttl << " ms)";
            std::cout << "\n";

        } else if (cmd == "get") {
            std::string key;
            ss >> key;
            if (key.empty()) { std::cout << "  Usage: get <key>\n"; continue; }
            auto v = cache.get(key);
            if (v.has_value())
                std::cout << "  [HIT]  [" << key << "] = \"" << *v << "\"\n";
            else
                std::cout << "  [MISS] [" << key << "] not found\n";

        } else if (cmd == "stats") {
            cache.print_stats();

        } else if (cmd == "quit" || cmd == "exit" || cmd == "q") {
            break;

        } else if (!cmd.empty()) {
            std::cout << "  Unknown command. Try: put / get / stats / quit\n";
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  Menu option 4 — TTL Expiry Demo
// ─────────────────────────────────────────────────────────────────────────────
static void ttl_demo() {
    std::cout
        << "\n  -- TTL Expiry Demo --\n"
        << "  Inserting two keys into a standalone L1 cache:\n"
        << "    \"session\"  with a 2000 ms TTL   (will expire)\n"
        << "    \"config\"   with no TTL           (permanent)\n\n";

    LRUCache cache(10, "TTL-Demo");
    cache.put("session", "user_abc_token_xyz", 2000);
    cache.put("config",  "theme=dark",         0);

    auto v = cache.get("session");
    std::cout << "  Immediate get (session): "
              << (v ? ("\"" + *v + "\"") : "MISS") << "  <- expected hit\n";
    v = cache.get("config");
    std::cout << "  Immediate get (config) : "
              << (v ? ("\"" + *v + "\"") : "MISS") << "  <- expected hit\n\n";

    std::cout << "  Sleeping 2.1 seconds...\n";
    std::this_thread::sleep_for(std::chrono::milliseconds(2100));

    v = cache.get("session");
    std::cout << "\n  After 2.1s (session)  : "
              << (v ? ("\"" + *v + "\"") : "EXPIRED -- MISS") << "  <- TTL evicted\n";
    v = cache.get("config");
    std::cout << "  After 2.1s (config)   : "
              << (v ? ("\"" + *v + "\"") : "MISS") << "  <- still alive\n";

    std::cout << "\n  TTL expirations logged: " << cache.stats().ttl_expired << "\n";
}

// ─────────────────────────────────────────────────────────────────────────────
//  main
// ─────────────────────────────────────────────────────────────────────────────
int main() {
    print_banner();

    while (true) {
        std::cout
            << "  MAIN MENU\n"
            << "  ──────────────────────────────────────────────────────\n"
            << "  1.  Run Benchmark        (Sequential / Random / Hotspot)\n"
            << "  2.  Custom Benchmark     (choose your own settings)\n"
            << "  3.  Interactive Mode     (manual put / get)\n"
            << "  4.  TTL Expiry Demo      (watch an entry expire)\n"
            << "  5.  Exit\n"
            << "  ──────────────────────────────────────────────────────\n"
            << "  Choice: ";

        int choice = 0;
        std::cin >> choice;
        flush_cin();
        std::cout << "\n";

        switch (choice) {

            case 1:
                BenchmarkRunner::run_all();
                break;

            case 2: {
                int l1, l2, ops, keys, pat;
                std::cout << "  L1 capacity   (e.g. 20)  : "; std::cin >> l1;
                std::cout << "  L2 capacity   (e.g. 80)  : "; std::cin >> l2;
                std::cout << "  Operations    (e.g. 1000): "; std::cin >> ops;
                std::cout << "  Unique keys   (e.g. 200) : "; std::cin >> keys;
                std::cout << "  Pattern  0=Sequential  1=Random  2=Hotspot : ";
                std::cin >> pat;
                flush_cin();

                BenchmarkConfig cfg;
                cfg.l1_capacity     = std::max(1, l1);
                cfg.l2_capacity     = std::max(1, l2);
                cfg.num_operations  = std::max(1, ops);
                cfg.num_unique_keys = std::max(1, keys);
                cfg.pattern         = static_cast<AccessPattern>(std::clamp(pat, 0, 2));

                auto r = BenchmarkRunner::run(cfg);
                std::cout << "\n-- Result --\n";
                BenchmarkRunner::print_result(r);
                std::cout << "\n";
                break;
            }

            case 3:
                interactive_mode();
                std::cout << "\n";
                break;

            case 4:
                ttl_demo();
                std::cout << "\n";
                break;

            case 5:
                std::cout << "  Goodbye!\n\n";
                return 0;

            default:
                std::cout << "  Invalid choice. Please enter 1-5.\n\n";
        }
    }
}
