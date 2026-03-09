/**
 * @file transposition_table.cpp
 * @author Marc
 * @brief Zobrist Hashing and Transposition Table cache implementation.
 * 
 * @copyright Copyright (c) 2026
 * 
 * This project is licensed under the MIT License.
 */
#include "transposition_table.h"
#include <cstring>
#include <random>

namespace {
    // Random keys for each (col, row, player) combination
    // player 0 = current, 1 = opponent
    uint64_t zobristKeys[7][6][2];
    
    // Fast lookup: keys indexed by bit position [bitIndex][player]
    // Bit index = col * 7 + row, covers bits 0-48 (49 total, but only 42 valid)
    uint64_t zobristKeysByBit[49][2];
    
    bool zobristInitialized = false;
}

namespace Zobrist {

void initialize() {
    if (zobristInitialized) return;
    
    // Use a fixed seed for reproducibility (important for debugging)
    std::mt19937_64 rng(0xC04EC7A4); 
    
    for (int col = 0; col < 7; col++) {
        for (int row = 0; row < 6; row++) {
            // player 0 = first mover, player 1 = second mover
            for (int player = 0; player < 2; player++) {
                uint64_t key = rng();
                zobristKeys[col][row][player] = key;
                int bitIndex = col * 7 + row;
                zobristKeysByBit[bitIndex][player] = key;
            }
        }
    }
    
    zobristInitialized = true;
}

// O(1) key update for incremental hashing
uint64_t getMoveKey(uint64_t moveBit, bool isFirstMover) {
    unsigned long bitIndex = ctzll_port(moveBit);
    return zobristKeysByBit[bitIndex][isFirstMover ? 0 : 1];
}

uint64_t getMoveKeyByIndex(int bitIndex, bool isFirstMover) {
    return zobristKeysByBit[bitIndex][isFirstMover ? 0 : 1];
}

uint64_t computeKey(uint64_t pos, uint64_t mask) {
    // Initialize Zobrist if needed
    if (!zobristInitialized) initialize();
    
    uint64_t key = 0;
    
    // Determine if current player (pos holder) is first mover or second mover
    int totalPieces = popcnt64_port(mask);
    bool currentPlayerIsFirstMover = (totalPieces % 2 == 0);
    
    // Iterate through all 42 positions
    for (int col = 0; col < 7; col++) {
        for (int row = 0; row < 6; row++) {
            int bitIndex = col * 7 + row;
            uint64_t bitMask = 1ULL << bitIndex;
            
            if (mask & bitMask) {
                bool isInPos = (pos & bitMask) != 0;
                // Map current player to absolute identity
                bool isFirstMover;
                if (isInPos) {
                    isFirstMover = currentPlayerIsFirstMover;
                } else {
                    isFirstMover = !currentPlayerIsFirstMover;
                }
                key ^= zobristKeys[col][row][isFirstMover ? 0 : 1];
            }
        }
    }
    
    return key;
}

} 
// Global instance with default size
TranspositionTable g_tt(512);

TranspositionTable::TranspositionTable(size_t sizeMB) {
    // Calculate number of entries (must be power of 2 for fast modulo)
    size_t bytes = sizeMB * 1024 * 1024;
    numEntries = 1;
    while (numEntries * sizeof(TTEntry) * 2 <= bytes) {
        numEntries *= 2;
    }
    
    mask = numEntries - 1;
    
    // Allocate and clear
    table = new TTEntry[numEntries];
    clear();
    
    // Initialize Zobrist keys
    Zobrist::initialize();
}

TranspositionTable::~TranspositionTable() {
    delete[] table;
}

void TranspositionTable::clear() {
    std::memset(table, 0, numEntries * sizeof(TTEntry));
}

void TranspositionTable::store(uint64_t key, int score, int depth, TTFlag flag, int bestMove) {
    size_t index = key & mask;
    TTEntry& entry = table[index];
    
    // Extract upper 32 bits of key for storage
    uint32_t keyUpper = static_cast<uint32_t>(key >> 32);
    
    // Depth-preferred replacement: only replace if:
    // 1. Slot is empty (key == 0)
    // 2. Same position (update with potentially better info)
    // 3. New search is deeper or equal depth
    if (entry.key == 0 || entry.key == keyUpper || depth >= entry.getDepth()) {
        entry.key = keyUpper;
        entry.score = static_cast<int16_t>(score);
        entry.setDepthFlag(depth, flag);
        entry.bestMove = static_cast<int8_t>(bestMove);
    }
}

bool TranspositionTable::probe(uint64_t key, TTEntry& entry) const {
    size_t index = key & mask;
    const TTEntry& stored = table[index];
    
    // Extract upper 32 bits for comparison
    uint32_t keyUpper = static_cast<uint32_t>(key >> 32);
    
    // Check for key match (collision detection using upper 32 bits)
    if (stored.key == keyUpper) {
        entry = stored;
        return true;
    }
    
    return false;
}