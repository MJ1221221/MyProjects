/*
 * cache_system.h
 *
 * MultiLevelCache — a two-tier L1/L2 cache hierarchy built on top of LRUCache.
 *
 * GET flow:
 *   ┌─────────────────────────────────────────────────────────┐
 *   │  L1 hit?  ──yes──▶  return value            (best case) │
 *   │     │                                                    │
 *   │    no                                                    │
 *   │     ▼                                                    │
 *   │  L2 hit?  ──yes──▶  promote to L1                       │
 *   │               └──▶  if L1 evicts X → demote X to L2     │
 *   │     │                                                    │
 *   │    no                                                    │
 *   │     ▼                                                    │
 *   │  cold miss → return nullopt                              │
 *   └─────────────────────────────────────────────────────────┘
 *
 * PUT flow:
 *   Always write to L1.
 *   If L1 overflows → evicted entry goes to L2 (demotion).
 *   If L2 overflows → that entry is truly gone (no L3).
 */

#pragma once

#include "lru_cache.h"
#include <iostream>
#include <iomanip>

class MultiLevelCache {
public:
    MultiLevelCache(int l1_cap, int l2_cap)
        : l1_(l1_cap, "L1"), l2_(l2_cap, "L2") {}

    // ─────────────────────────────────────────────────────────────────
    //  GET
    // ─────────────────────────────────────────────────────────────────
    std::optional<std::string> get(const std::string& key) {

        // Step 1: Try L1
        if (auto val = l1_.get(key); val.has_value()) {
            l1_hits_++;
            return val;
        }

        // Step 2: Try L2 (peek = no reordering inside L2)
        if (auto l2_val = l2_.peek(key); l2_val.has_value()) {
            l2_hits_++;

            // Pull out of L2 and promote to L1
            l2_.remove(key);
            auto evicted = l1_.put(key, *l2_val);

            // If L1 overflowed during promotion, demote the victim to L2
            if (evicted.has_value())
                l2_.put(evicted->first, evicted->second);

            return l2_val;
        }

        // Step 3: Cold miss
        total_misses_++;
        return std::nullopt;
    }

    // ─────────────────────────────────────────────────────────────────
    //  PUT
    // ─────────────────────────────────────────────────────────────────
    void put(const std::string& key, const std::string& value, long long ttl_ms = 0) {
        // Insert into L1; get back whatever was evicted (if anything)
        auto evicted = l1_.put(key, value, ttl_ms);

        // Demote the displaced L1 entry to L2 rather than losing it
        if (evicted.has_value())
            l2_.put(evicted->first, evicted->second);
    }

    // ─────────────────────────────────────────────────────────────────
    //  Stats
    // ─────────────────────────────────────────────────────────────────
    int l1_hits()      const { return l1_hits_; }
    int l2_hits()      const { return l2_hits_; }
    int total_misses() const { return total_misses_; }

    void reset_stats() {
        l1_.reset_stats();
        l2_.reset_stats();
        l1_hits_ = l2_hits_ = total_misses_ = 0;
    }

    void print_stats() const {
        const auto& s1 = l1_.stats();
        const auto& s2 = l2_.stats();
        int total_gets  = l1_hits_ + l2_hits_ + total_misses_;
        double hit_rate = total_gets > 0
            ? 100.0 * (l1_hits_ + l2_hits_) / total_gets : 0.0;

        const int W = 30;
        int filled  = static_cast<int>(W * hit_rate / 100.0 + 0.5);

        std::cout
            << "\n  ┌────────────────────────────────────────────────────┐\n"
            << "  │           CACHE PERFORMANCE REPORT                  │\n"
            << "  ├───────┬──────────┬────────┬───────┬─────────────────┤\n"
            << "  │ Level │ Capacity │  Size  │  Hits │ Evictions       │\n"
            << "  ├───────┼──────────┼────────┼───────┼─────────────────┤\n"
            << "  │  L1   │ " << std::setw(8) << l1_.capacity()
            << " │ " << std::setw(6) << l1_.size()
            << " │ " << std::setw(5) << l1_hits_
            << " │ " << std::setw(5) << s1.evictions << " (-> L2)      │\n"
            << "  │  L2   │ " << std::setw(8) << l2_.capacity()
            << " │ " << std::setw(6) << l2_.size()
            << " │ " << std::setw(5) << l2_hits_
            << " │ " << std::setw(5) << s2.evictions << " (gone)       │\n"
            << "  ├───────┴──────────┴────────┴───────┴─────────────────┤\n"
            << "  │ Total GETs:      " << std::setw(6) << total_gets    << "                    │\n"
            << "  │ Total Misses:    " << std::setw(6) << total_misses_ << "                    │\n"
            << "  │ TTL Expirations: " << std::setw(6) << (s1.ttl_expired + s2.ttl_expired)
            << "                    │\n"
            << "  │ Hit Rate:  [";
        for (int i = 0; i < W; i++) std::cout << (i < filled ? '#' : '-');
        std::cout
            << "] " << std::fixed << std::setprecision(1) << hit_rate << "%\n"
            << "  └────────────────────────────────────────────────────┘\n";
    }

    LRUCache& l1() { return l1_; }
    LRUCache& l2() { return l2_; }
    const LRUCache& l1() const { return l1_; }
    const LRUCache& l2() const { return l2_; }

private:
    LRUCache l1_;
    LRUCache l2_;
    int l1_hits_      = 0;
    int l2_hits_      = 0;
    int total_misses_ = 0;
};
