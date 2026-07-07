/*
 * lru_cache.h
 *
 * Core LRU Cache — built from scratch using three data structures:
 *
 *   1. unordered_map<string, CacheNode*>
 *        → O(1) lookup by key
 *
 *   2. Doubly Linked List (DLL)
 *        [HEAD] <-> [MRU] <-> ... <-> [LRU] <-> [TAIL]
 *        → O(1) move-to-front on every access (marks as most recently used)
 *        → O(1) evict from tail  (removes least recently used)
 *
 *   3. Min-Heap keyed on expiry_ms
 *        → efficiently finds the soonest-to-expire entry
 *        → lazy deletion: stale heap entries are skipped when they surface
 *
 * put() returns the evicted {key, value} pair so MultiLevelCache can
 * demote it to L2 instead of permanently losing the entry.
 */

#pragma once

#include <string>
#include <unordered_map>
#include <queue>
#include <optional>
#include <utility>
#include <chrono>

// ─────────────────────────────────────────────────────────────────────────────
//  CacheNode  –  one node in the doubly linked list
// ─────────────────────────────────────────────────────────────────────────────
struct CacheNode {
    std::string key;
    std::string value;
    long long   expiry_ms;   // epoch-ms; 0 means no expiry (lives forever)
    CacheNode*  prev;
    CacheNode*  next;

    CacheNode(std::string k, std::string v, long long exp = 0)
        : key(std::move(k)), value(std::move(v)),
          expiry_ms(exp), prev(nullptr), next(nullptr) {}
};

// ─────────────────────────────────────────────────────────────────────────────
//  LRUCache
// ─────────────────────────────────────────────────────────────────────────────
class LRUCache {
public:

    struct Stats {
        int hits        = 0;
        int misses      = 0;
        int evictions   = 0;   // LRU evictions (capacity overflow)
        int ttl_expired = 0;   // entries removed because their TTL elapsed
    };

    explicit LRUCache(int capacity, std::string name = "Cache")
        : capacity_(capacity), name_(std::move(name))
    {
        // Two dummy sentinels so pointer logic never hits nullptr
        head_ = new CacheNode("__HEAD__", "");
        tail_ = new CacheNode("__TAIL__", "");
        head_->next = tail_;
        tail_->prev = head_;
    }

    ~LRUCache() {
        CacheNode* cur = head_;
        while (cur) {
            CacheNode* nxt = cur->next;
            delete cur;
            cur = nxt;
        }
    }

    LRUCache(const LRUCache&)            = delete;
    LRUCache& operator=(const LRUCache&) = delete;

    // ─────────────────────────────────────────────────────────────────
    //  GET
    //    O(1) lookup + O(1) move-to-front.
    //    Returns nullopt if key is absent or TTL has elapsed.
    // ─────────────────────────────────────────────────────────────────
    std::optional<std::string> get(const std::string& key) {
        purge_expired();

        auto it = map_.find(key);
        if (it == map_.end()) {
            stats_.misses++;
            return std::nullopt;
        }

        CacheNode* node = it->second;
        if (is_expired(node)) {
            remove_node(node);
            map_.erase(it);
            delete node;
            stats_.ttl_expired++;
            stats_.misses++;
            return std::nullopt;
        }

        move_to_front(node);
        stats_.hits++;
        return node->value;
    }

    // ─────────────────────────────────────────────────────────────────
    //  PUT
    //    Inserts or refreshes a key. ttl_ms=0 means never expires.
    //    Returns the LRU-evicted {key, value} if capacity overflowed,
    //    so the caller (MultiLevelCache) can demote it to L2.
    // ─────────────────────────────────────────────────────────────────
    std::optional<std::pair<std::string, std::string>>
    put(const std::string& key, const std::string& value, long long ttl_ms = 0) {
        purge_expired();

        long long expiry = ttl_ms > 0 ? now_ms() + ttl_ms : 0LL;

        if (auto it = map_.find(key); it != map_.end()) {
            // Key already present → update and refresh position
            CacheNode* node = it->second;
            node->value     = value;
            node->expiry_ms = expiry;
            move_to_front(node);
            if (ttl_ms > 0) ttl_heap_.emplace(expiry, key);
            return std::nullopt;
        }

        // Fresh insert at MRU end
        auto* node = new CacheNode(key, value, expiry);
        map_[key]  = node;
        insert_at_front(node);
        if (ttl_ms > 0) ttl_heap_.emplace(expiry, key);

        // Evict LRU if over capacity
        if (static_cast<int>(map_.size()) > capacity_) {
            CacheNode* lru  = tail_->prev;
            auto evicted    = std::make_pair(lru->key, lru->value);
            remove_node(lru);
            map_.erase(lru->key);
            delete lru;
            stats_.evictions++;
            return evicted;
        }

        return std::nullopt;
    }

    // ─────────────────────────────────────────────────────────────────
    //  PEEK  –  read without changing recency order.
    //  Used by MultiLevelCache to check L2 without disturbing its order.
    // ─────────────────────────────────────────────────────────────────
    std::optional<std::string> peek(const std::string& key) const {
        auto it = map_.find(key);
        if (it == map_.end())       return std::nullopt;
        if (is_expired(it->second)) return std::nullopt;
        return it->second->value;
    }

    // ─────────────────────────────────────────────────────────────────
    //  REMOVE  –  explicit delete (called during L2 → L1 promotion)
    // ─────────────────────────────────────────────────────────────────
    void remove(const std::string& key) {
        auto it = map_.find(key);
        if (it == map_.end()) return;
        remove_node(it->second);
        delete it->second;
        map_.erase(it);
    }

    int                size()      const { return static_cast<int>(map_.size()); }
    int                capacity()  const { return capacity_; }
    const std::string& name()      const { return name_; }
    const Stats&       stats()     const { return stats_; }
    void               reset_stats()     { stats_ = {}; }

    double hit_rate() const {
        int total = stats_.hits + stats_.misses;
        return total > 0 ? 100.0 * stats_.hits / total : 0.0;
    }

private:
    int         capacity_;
    std::string name_;
    Stats       stats_;
    CacheNode*  head_;
    CacheNode*  tail_;

    std::unordered_map<std::string, CacheNode*> map_;

    // Min-heap: {expiry_ms, key} — smallest expiry at top
    using TTLEntry = std::pair<long long, std::string>;
    std::priority_queue<TTLEntry,
                        std::vector<TTLEntry>,
                        std::greater<TTLEntry>> ttl_heap_;

    static long long now_ms() {
        return std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
    }

    bool is_expired(CacheNode* n) const {
        return n->expiry_ms > 0 && now_ms() > n->expiry_ms;
    }

    // Sweep the TTL heap top and remove genuinely expired nodes (lazy deletion)
    void purge_expired() {
        long long now = now_ms();
        while (!ttl_heap_.empty() && ttl_heap_.top().first <= now) {
            const std::string& k = ttl_heap_.top().second;
            if (auto it = map_.find(k); it != map_.end() && is_expired(it->second)) {
                remove_node(it->second);
                delete it->second;
                map_.erase(it);
                stats_.ttl_expired++;
            }
            ttl_heap_.pop();
        }
    }

    void remove_node(CacheNode* n) {
        n->prev->next = n->next;
        n->next->prev = n->prev;
    }

    void insert_at_front(CacheNode* n) {
        n->next           = head_->next;
        n->prev           = head_;
        head_->next->prev = n;
        head_->next       = n;
    }

    void move_to_front(CacheNode* n) {
        remove_node(n);
        insert_at_front(n);
    }
};
