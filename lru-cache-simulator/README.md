# LRU-Based Multi-Level Cache Simulator

**Tech: Data Structures & Algorithms (C++17)**

A from-scratch simulation of a two-level CPU-style cache hierarchy,
combining three core DSA structures into one working system.

---

## Data Structures Used

| Structure | Role | Complexity |
|---|---|---|
| Doubly Linked List | Track recency order — MRU at front, LRU at tail | O(1) move & evict |
| HashMap (`unordered_map`) | Key → node pointer for instant lookup | O(1) get/put |
| Min-Heap (`priority_queue`) | Surface soonest-expiring TTL entry | O(log n) expiry |

---

## Architecture

```
PUT always writes to L1
                          ┌──────────────────┐
  ┌──────────────────┐    │   L2 Cache       │
  │   L1 Cache       │───▶│  (larger, warm)  │───▶ permanently gone
  │  (small, hot)    │    │                  │
  └──────────────────┘    └──────────────────┘
        │ overflow              ▲
        └── demote LRU ─────────┘

GET flow:
  L1 hit  → return immediately
  L1 miss → check L2 → promote to L1 (demote displaced L1 entry back to L2)
  L2 miss → cold miss, return null
```

---

## File Layout

```
lru-cache-simulator/
├── src/
│   ├── lru_cache.h      ← Core LRU (DLL + HashMap + Min-Heap TTL)
│   ├── cache_system.h   ← MultiLevelCache (L1/L2 promotion & demotion)
│   └── benchmark.h      ← Access patterns + stats printer
├── main.cpp             ← CLI menu
└── README.md
```

---

## Build & Run

```bash
g++ -std=c++17 -O2 main.cpp -o cache_sim
./cache_sim
```

No external libraries — standard C++17 only.

---

## CLI Menu

```
1. Run Benchmark         — Sequential / Random / Hotspot patterns
2. Custom Benchmark      — choose L1/L2 sizes, ops, key-space
3. Interactive Mode      — manual put/get with optional TTL
4. TTL Expiry Demo       — watch an entry expire in real time
5. Exit
```

### Access Patterns

| Pattern | Description | Expected Hit Rate |
|---|---|---|
| Sequential | Keys 0,1,2,...N in strict order | Lowest — cache thrashes |
| Random | Uniform random from key space | Medium |
| Hotspot | 80% of ops hit top 20% of keys | Highest — mirrors real workloads |

### Interactive Mode Example

```
cache> put username alice 5000
✓ Stored  [username] = "alice"   (expires in 5000 ms)

cache> get username
✓ HIT   [username] = "alice"

cache> stats
  Hit Rate: [###########################--------] 77.3%
```

---

## Key Concepts

**Why Doubly Linked List + HashMap?**
The hashmap gives O(1) lookup, but lookup alone isn't enough — we also need
to reorder entries on every access (move to MRU position) and evict from the
tail. A doubly linked list makes both operations O(1) with pointer rewiring.
A singly linked list or array would require O(n) traversal.

**Why a Min-Heap for TTL?**
We need to find the soonest-to-expire entry without scanning all entries.
A min-heap (min priority queue keyed on expiry time) keeps the earliest
expiry at the top — O(log n) insert, O(1) peek, O(log n) remove.
Stale heap entries (keys that were updated or already removed) are skipped
lazily when they surface at the top.

**Why L1/L2?**
An entry evicted from L1 due to LRU overflow isn't immediately lost — it is
demoted to L2. On the next access it gets promoted back to L1. This mirrors
real CPU cache behaviour and dramatically improves hit rate compared to a
single-level cache.
