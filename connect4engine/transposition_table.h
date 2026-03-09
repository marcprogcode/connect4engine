/**
 * @file transposition_table.h
 * @author Marc
 * @brief Zobrist Hashing and Transposition Table cache implementation.
 * 
 * @copyright Copyright (c) 2026
 * 
 * This project is licensed under the MIT License.
 */
#pragma once
#include <cstdint>
#include <cstddef>

#if defined(__x86_64__) || defined(_M_X64) || defined(__i386__) || defined(_M_IX86)
#include <xmmintrin.h>
#endif

#ifdef _MSC_VER
#include <intrin.h>
inline int ctzll_port(uint64_t x) {
    unsigned long idx;
    _BitScanForward64(&idx, x);
    return static_cast<int>(idx);
}
inline int popcnt64_port(uint64_t x) {
    return static_cast<int>(__popcnt64(x));
}
#else
inline int ctzll_port(uint64_t x) {
    return __builtin_ctzll(x);
}
inline int popcnt64_port(uint64_t x) {
    return __builtin_popcountll(x);
}
#endif

// Entry flags indicating the type of score stored
enum class TTFlag : uint8_t {
    EXACT = 0,       // Score is exact (alpha < score < beta)
    LOWER_BOUND = 1, // Score is >= beta (beta cutoff)
    UPPER_BOUND = 2  // Score is <= alpha (failed low)
};

// Compact transposition table entry (8 bytes - fits in single cache fetch)
// Uses key compression: index provides lower bits, we store upper 32 bits
#pragma pack(push, 1)

struct alignas(8) TTEntry {
    uint32_t key;      // Upper 32 bits of position hash (4 bytes)
    int16_t score;     // Evaluation score (2 bytes)
    uint8_t depthFlag; // Depth (6 bits) + Flag (2 bits) packed (1 byte)
    int8_t bestMove;   // Best move column 0-6, or -1 if none (1 byte)
    
    // Accessors for packed fields
    int getDepth() const { return depthFlag >> 2; }
    TTFlag getFlag() const { return static_cast<TTFlag>(depthFlag & 0x3); }
    void setDepthFlag(int depth, TTFlag flag) {
        depthFlag = static_cast<uint8_t>((depth << 2) | static_cast<uint8_t>(flag));
    }
};
#pragma pack(pop)
static_assert(sizeof(TTEntry) == 8, "TTEntry must be 8 bytes");

class TranspositionTable {
public:
    // Default size of 512MB
    TranspositionTable(size_t sizeMB = 512);
    ~TranspositionTable();

    // Disable copy
    TranspositionTable(const TranspositionTable&) = delete;
    TranspositionTable& operator=(const TranspositionTable&) = delete;

    // Store a position evaluation
    void store(uint64_t key, int score, int depth, TTFlag flag, int bestMove);

    // Probe for a position, returns true if found
    bool probe(uint64_t key, TTEntry& entry) const;

    // Clear all entries
    void clear();

    // Get table size info
    size_t getEntryCount() const { return numEntries; }
    size_t getSizeMB() const { return (numEntries * sizeof(TTEntry)) / (1024 * 1024); }
    void prefetch(uint64_t key) const { 
#if defined(__GNUC__) || defined(__clang__)
        __builtin_prefetch((const void*)&table[key & mask]);
#elif defined(_MSC_VER) && (defined(_M_X64) || defined(_M_IX86))
        _mm_prefetch((const char*)&table[key & mask], _MM_HINT_T0);
#endif
    }

private:
    TTEntry* table;
    size_t numEntries;
    // For fast modulo: index = hash & mask
    size_t mask;  
};

// Zobrist hashing for position keys
// Uses ABSOLUTE player identity (first mover = 0, second mover = 1) not relative identity
// This allows correct incremental updates when perspective swaps in negamax
namespace Zobrist {
    // Initialize the random keys (call once at startup)
    void initialize();

    // Compute full key from position
    uint64_t computeKey(uint64_t pos, uint64_t mask);
    
    // Fast incremental key update: get key for a move bit
    uint64_t getMoveKey(uint64_t moveBit, bool isFirstMover);
    
    // Faster version if we already know the bit index
    uint64_t getMoveKeyByIndex(int bitIndex, bool isFirstMover);
}

// Global transposition table instance
extern TranspositionTable g_tt;