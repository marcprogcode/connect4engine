/**
 * @file search_controller.h
 * @author Marc
 * @brief Search controller for tracking time and iterative deepening limits.
 * 
 * @copyright Copyright (c) 2026
 * 
 * This project is licensed under the MIT License.
 */
#pragma once
#include <chrono>

/**
 * @brief SearchController manages time control for iterative deepening search. 
 * 
 * Tracks elapsed time and stores the best move from completed iterations.
 * Supports mid-search abort for precise time control.
 */
class SearchController {
public:
    /**
     * @brief Start time tracking for a new search
     * @param limitMs Time limit in milliseconds (0 = no time limit)
     */
    void startSearch(int limitMs) {
        this->timeLimitMs = limitMs;
        startTime = std::chrono::steady_clock::now();
        bestMove = 4;  // Default to center column
        bestScore = 0;
        lastCompletedDepth = 0;
        aborted = false;
        checkCounter = 0;
    }

    /**
     * @brief Check if we should stop searching (called between depth iterations)
     * @return true if time limit exceeded
     */
    bool shouldStop() const {
        if (timeLimitMs <= 0) return false;  // No time limit
        return getElapsedMs() >= timeLimitMs;
    }

    /**
     * @brief Check time during search (called frequently from negamax)
     * Only actually checks time every N calls to minimize overhead
     * Sets aborted flag if time is up
     * @return true if search should abort
     */
    bool checkTime() {
        if (timeLimitMs <= 0) return false;  // No time limit
        
        // Only check every 2048 calls to minimize overhead
        // Instead of a mod operator, we use a (2^N)-1 and operation
        // this way, it can be done in a single instruction and not perform division
        if (++checkCounter & 2047) return aborted;
        
        if (getElapsedMs() >= timeLimitMs) {
            aborted = true;
        }
        return aborted;
    }

    /**
     * @brief Check if search was aborted mid-iteration
     * @return true if search was aborted, false otherwise
     */
    bool wasAborted() const { return aborted; }

    /**
     * @brief Get elapsed time since startSearch() was called
     * @return Elapsed time in milliseconds
     */
    int getElapsedMs() const {
        auto now = std::chrono::steady_clock::now();
        return static_cast<int>(
            std::chrono::duration_cast<std::chrono::milliseconds>(now - startTime).count()
        );
    }

    /**
     * @brief Store best move from a completed depth iteration
     * @param move The best move found
     * @param score The score of the best move
     * @param depth The depth of the best move
     */
    void setBestMove(int move, int score, int depth) {
        bestMove = move;
        bestScore = score;
        lastCompletedDepth = depth;
    }

    int getBestMove() const { return bestMove; }
    int getBestScore() const { return bestScore; }
    int getLastCompletedDepth() const { return lastCompletedDepth; }

private:
    std::chrono::steady_clock::time_point startTime;
    int timeLimitMs = 0;
    int bestMove = 4;
    int bestScore = 0;
    int lastCompletedDepth = 0;
    bool aborted = false;
    mutable int checkCounter = 0;
};

// Global pointer for mid-search time checking
extern SearchController* g_searchController;
