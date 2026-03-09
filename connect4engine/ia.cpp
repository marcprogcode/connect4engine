/**
 * @file ia.cpp
 * @author Marc
 * @brief Intelligence/AI core routines using Negamax with Alpha-Beta pruning.
 * 
 * @copyright Copyright (c) 2026
 * 
 * This project is licensed under the MIT License.
 */
#include "ia.h"
#include "search_controller.h"
#include "transposition_table.h"
#include <cstdlib>
#include <iostream>
#include <cstdint>

#if defined(__x86_64__) || defined(_M_X64) || defined(__i386__) || defined(_M_IX86)
#include <mmintrin.h>
#include <xmmintrin.h>
#endif

using namespace std;

// Constant for infinity
constexpr int INF = 1000000000;

long long nodeCount = 0;
int lastSearchDepth = 0;

// Global search controller for mid-search time checking
SearchController* g_searchController = nullptr;

// Weights for each position in the board
// These were calculated based on how many 
// connect 4 patterns passed through the cell
static const int WEIGHTS[64] = {
    //(Bottom to Top) + 0 padding
    3, 4, 5, 5, 4, 3, 0,
    4, 6, 8, 8, 6, 4, 0,
    5, 8, 11, 11, 8, 5, 0,
    7, 9, 13, 13, 9, 7, 0,
    5, 8, 11, 11, 8, 5, 0,
    4, 6, 8, 8, 6, 4, 0,
    3, 4, 5, 5, 4, 3, 0,
    // Padding for remaining 64-bit space
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
};

// Mirror bit index lookup table
// Bottom to top, left to right
static const int MIRROR_IDX[64] = {
    42, 43, 44, 45, 46, 47, 0,
    35, 36, 37, 38, 39, 40, 0,
    28, 29, 30, 31, 32, 33, 0,
    21, 22, 23, 24, 25, 26, 0,
    14, 15, 16, 17, 18, 19, 0,
    7, 8, 9, 10, 11, 12, 0,
    0, 1, 2, 3, 4, 5, 0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
};

// Check if a player has won
inline bool checkWin(uint64_t pos) {
    uint64_t connected_pairs;
    // Horizontal
    connected_pairs = pos & (pos >> 7);
    if (connected_pairs & (connected_pairs >> 14)) return true;
    // Diagonal 
    connected_pairs = pos & (pos >> 8);
    if (connected_pairs & (connected_pairs >> 16)) return true;
    // Diagonal 
    connected_pairs = pos & (pos >> 6);
    if (connected_pairs & (connected_pairs >> 12)) return true;
    // Vertical
    connected_pairs = pos & (pos >> 1);
    if (connected_pairs & (connected_pairs >> 2)) return true;
    return false;
}

// Calculate the score of a position
int calculateScore(uint64_t playerStones) {
    int score = 0;
    // We loop through all the player's stones
    // and add up their value
    while (playerStones) {
        // Find index of the least significant bit (Trailing Zeros)
        unsigned long idx = ctzll_port(playerStones);

        // Add weight
        score += WEIGHTS[idx];

        // Remove that bit
        playerStones &= playerStones - 1;
    }
    return score;
}

// Evaluate the position
int eval(uint64_t playerStones, uint64_t mask) {
    // "playerStones" contains the current player's stones
    int score = calculateScore(playerStones);
    // "mask ^ playerStones" gives us the Opponent's stones
    int oppScore = calculateScore(mask ^ playerStones);

    return score - oppScore;
}

// Generate ordered moves: TT move first, then center-first order
// Returns number of valid moves
int generateOrderedMoves(uint64_t mask, int ttMove, int moves[7]) {
    static const int columnOrder[7] = { 3, 2, 4, 1, 5, 0, 6 };
    int count = 0;
    
    // First, add TT move if valid and column not full
    if (ttMove >= 0 && ttMove < 7 && !bbr::fullColumn(mask, ttMove)) {
        moves[count++] = ttMove;
    }
    
    // Then add remaining moves in center-first order
    // This way we maximize the score of the first nodes
    // we search, as usually the center nodes are best
    // and the other nodes will get pruned earlier
    for (int c : columnOrder) {
        if (c != ttMove && !bbr::fullColumn(mask, c)) {
            moves[count++] = c;
        }
    }
    
    return count;
}

// Negamax recursive function to search and evaluate the positions
int negamax(uint64_t pos, uint64_t mask, uint64_t zobristKey, uint64_t mirrorZobristKey, int moveCount, int depth, int alpha, int beta, int currentScore, int oppScore) {
    nodeCount++;
    
    // Check time periodically - abort if time is up
    if (g_searchController && g_searchController->checkTime()) {
        return 0;  // Return immediately, result will be discarded
    }
    
    int maxPossible = 10000 + depth;
    int minPossible = -10000 - (depth - 1); // Worst case: we lose next turn

    if (alpha < minPossible) alpha = minPossible;
    if (beta > maxPossible) beta = maxPossible;
    if (alpha >= beta) return alpha;

    // Check that the game hasn't ended
    // If the previous player made the winning move, the current player loses
    if (bbr::hasWon(mask ^ pos)) {
        return -10000 - depth; // Prefer winning sooner, or losing later
    }

    // Check for a draw
    if (bbr::fullBoard(mask)) return 0;

    // If we reached the maximum depth, return the evaluation
    if (depth == 0) 
        return currentScore - oppScore;
    
    // Determine the canonical key (minimum of key and mirrorKey)
    uint64_t canonicalKey = zobristKey;
    bool isMirrored = false;
    if (mirrorZobristKey < zobristKey) {
        canonicalKey = mirrorZobristKey;
        isMirrored = true;
    }

    TTEntry ttEntry;
    int ttMove = -1;
    
    // TT probe using canonical key
    if (g_tt.probe(canonicalKey, ttEntry)) {
        ttMove = ttEntry.bestMove;  // Use for move ordering regardless of depth
        if (ttMove != -1 && isMirrored) {
            ttMove = 6 - ttMove; // Mirror the move back to our perspective
        }
        
        // If sufficient depth, we might be able to use the score directly
        if (ttEntry.getDepth() >= depth) {
            int ttScore = ttEntry.score;
            
            if (ttEntry.getFlag() == TTFlag::EXACT) {
                return ttScore;
            }
            if (ttEntry.getFlag() == TTFlag::LOWER_BOUND && ttScore >= beta) {
                return ttScore;  // Beta cutoff
            }
            if (ttEntry.getFlag() == TTFlag::UPPER_BOUND && ttScore <= alpha) {
                return ttScore;  // Alpha cutoff
            }
        }
    }

    // Store original alpha for TT flag determination
    int origAlpha = alpha;
    int bestMove = -1;

    // Immediate Win Check
    for (int c = 0; c < 7; c++) {
        if (!bbr::fullColumn(mask, c)) {
            uint64_t move = (mask + (1ULL << (c * 7))) & ~mask;
            if (checkWin(pos | move)) {
                // Return winning score (10000 + depth - 1)
                // We prefer winning with more remaining depth
                return 10000 + depth - 1;
            }
        }
    }

    // Forced Block Check
    int forcedMove = -1;
    uint64_t oppPos = mask ^ pos;
    for (int c = 0; c < 7; c++) {
        if (!bbr::fullColumn(mask, c)) {
            uint64_t move = (mask + (1ULL << (c * 7))) & ~mask;
            if (checkWin(oppPos | move)) {
                forcedMove = c;
                break; // Found immediate threat, must block
            }
        }
    }

    // Generate moves
    int moves[7];
    int numMoves;
    
    if (forcedMove != -1) {
        // If forced, only search the forced move
        moves[0] = forcedMove;
        numMoves = 1;
    } else {
        // Otherwise, generate all moves
        numMoves = generateOrderedMoves(mask, ttMove, moves);
    }
    
    // Current player is first mover if moveCount is even
    bool isFirstMover = (moveCount % 2 == 0);

    // Iterate through all possible moves
    for (int i = 0; i < numMoves; i++) {
        int c = moves[i];

        // Generates the legal move in column 'c' using a carry chain.
        // Adding the bottom bit (1 << c*7) flips the first empty '0' to '1'.
        // This addition also zeroes out the filled '1's below that empty cell.
        // The '& ~mask' isolates that single new bit, clearing all original pieces.
        uint64_t move = (mask + (1ULL << (c * 7))) & ~mask;

        // Find index of the least significant bit (Trailing Zeros)
        unsigned long idx = ctzll_port(move);

        // XOR the move to the bitmaps
        pos ^= move;
        mask ^= move;
        
        // Update Zobrist key incrementally using absolute player identity
        uint64_t newKey = zobristKey ^ Zobrist::getMoveKeyByIndex(idx, isFirstMover);
        
        // Update Mirror Zobrist Key using lookup table
        uint64_t newMirrorKey = mirrorZobristKey ^ Zobrist::getMoveKeyByIndex(MIRROR_IDX[idx], isFirstMover);


        // If there is a next move in the list, calculate its key and fetch it from RAM.
        if (i + 1 < numMoves) {
            int next_c = moves[i + 1];
            uint64_t nextMove = (mask + (1ULL << (next_c * 7))) & ~mask;
            uint64_t nextKey = zobristKey ^ Zobrist::getMoveKey(nextMove, isFirstMover);
            uint64_t nextCanonical = nextKey;
            // Ideally we would check min(nextKey, nextMirrorKey) but simplified for speed
            g_tt.prefetch(nextCanonical);
        }

        // Recursion passing moveCount+1 and inverting pos, alpha, beta and swapping them
        // We swap and invert alpha and beta because whats best for us is worst for opp
        int score = -negamax(mask ^ pos, mask, newKey, newMirrorKey, moveCount + 1, depth - 1, -beta, -alpha, oppScore, currentScore + WEIGHTS[idx]);

        // Undo the move by XOR again
        pos ^= move;
        mask ^= move;

        // Prune the search
        if (score >= beta) {
            // Store in TT before returning (lower bound)
            // If we are in mirrored state, we must mirror the move we store
            int storeMove = c;
            if (isMirrored) storeMove = 6 - c;
            
            g_tt.store(canonicalKey, score, depth, TTFlag::LOWER_BOUND, storeMove);
            return beta;
        }
        if (score > alpha) {
            alpha = score;
            bestMove = c;
        }
    }
    
    // Store in TT
    TTFlag flag = (alpha <= origAlpha) ? TTFlag::UPPER_BOUND : TTFlag::EXACT;
    
    int storeMove = bestMove;
    if (bestMove != -1 && isMirrored) {
        storeMove = 6 - bestMove;
    }
    g_tt.store(canonicalKey, alpha, depth, flag, storeMove);
    
    return alpha;
}

// Main function that returns the best move
int triarColumnaIA(uint64_t pos, uint64_t mask, int maxDepth, int timeMs) {
    SearchController controller;
    controller.startSearch(timeMs);
    
    // Set global pointer for mid-search time checking (only active if timeMs > 0)
    if (timeMs > 0) {
        g_searchController = &controller;
    }
    
    nodeCount = 0;
        
    // Compute root Zobrist key ONCE at the start
    uint64_t rootKey = Zobrist::computeKey(pos, mask);
    // Compute root Mirror Zobrist key ONCE
    uint64_t mirrorPos = bbr::mirror(pos);
    uint64_t mirrorMask = bbr::mirror(mask);
    uint64_t rootMirrorKey = Zobrist::computeKey(mirrorPos, mirrorMask);
    
    // Compute root move count once (for determining first mover)
    int rootMoveCount = popcnt64_port(mask);
    
    // Iterative deepening 
    for (int depth = 1; depth <= maxDepth; depth++) {
        // Check if we should stop before starting a new iteration (time limit)
        if (timeMs > 0 && controller.shouldStop()) {
            break;
        }
        
        int bestMove = 3;
        int bestScore = -INF;
        int alpha = -INF;
        int beta = INF;
        
        // Get TT move for root move ordering (using canonical key)
        TTEntry rootEntry;
        int ttMove = -1;
        
        uint64_t canonicalRootKey = rootKey;
        bool isMirrored = false;
        if (rootMirrorKey < rootKey) {
            canonicalRootKey = rootMirrorKey;
            isMirrored = true;
        }
        
        if (g_tt.probe(canonicalRootKey, rootEntry)) {
            ttMove = rootEntry.bestMove;
            if (ttMove != -1 && isMirrored) {
                ttMove = 6 - ttMove;
            }
        }
        
        // Generate moves with TT move first for better ordering
        int moves[7];
        int numMoves = generateOrderedMoves(mask, ttMove, moves);
        
        // Root player is first mover if rootMoveCount is even
        bool isFirstMover = (rootMoveCount % 2 == 0);

        int rootCurrentScore = calculateScore(pos);
        int rootOppScore = calculateScore(mask ^ pos);

        for (int i = 0; i < numMoves; i++) {
            int c = moves[i];

            // Generates the legal move in column 'c' using a carry chain.
            // Adding the bottom bit (1 << c*7) flips the first empty '0' to '1'.
            // This addition also zeroes out the filled '1's below that empty cell.
            // The '& ~mask' isolates that single new bit, clearing all original pieces.
            uint64_t move = (mask + (1ULL << (c * 7))) & ~mask;

            // Find index of the least significant bit (Trailing Zeros)
            unsigned long idx = ctzll_port(move);

            // XOR the move to the bitmaps
            pos ^= move;
            mask ^= move;
            
            // Update key for this move using absolute player identity
            uint64_t childKey = rootKey ^ Zobrist::getMoveKeyByIndex(idx, isFirstMover);
            
            // Update Mirror Key using lookup
            uint64_t childMirrorKey = rootMirrorKey ^ Zobrist::getMoveKeyByIndex(MIRROR_IDX[idx], isFirstMover);


            // Recursion passing moveCount+1 and inverting pos, alpha, beta and swapping them
            // We swap and invert alpha and beta because whats best for us is worst for opp
            int score = -negamax(mask ^ pos, mask, childKey, childMirrorKey, rootMoveCount + 1, depth, -beta, -alpha, rootOppScore, rootCurrentScore + WEIGHTS[idx]);

            // Undo the move by XOR again
            pos ^= move;
            mask ^= move;

            // Check if we should stop before starting a new iteration (time limit)
            if (timeMs > 0 && controller.wasAborted()) break;

            if (score > bestScore) {
                bestScore = score;
                bestMove = c;
            }
            if (bestScore > alpha) alpha = bestScore;
        }
        
        // Only update best move if this depth completed fully (not aborted)
        if (timeMs <= 0 || !controller.wasAborted()) {
            controller.setBestMove(bestMove, bestScore, depth);
            
            // Store root position in TT
            int storeMove = bestMove;
            if (isMirrored) storeMove = 6 - bestMove;
            g_tt.store(canonicalRootKey, bestScore, depth, TTFlag::EXACT, storeMove);
        }
        
        // Check time after each completed depth
        if (timeMs > 0 && (controller.shouldStop() || controller.wasAborted())) {
            break;
        }
    }
    
    // Clear global pointer and save depth reached
    g_searchController = nullptr;
    lastSearchDepth = controller.getLastCompletedDepth();
    
    return controller.getBestMove();
}

void clearTranspositionTable() {
    g_tt.clear();
}