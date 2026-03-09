/**
 * @file ia.h
 * @author Marc
 * @brief Intelligence/AI core routines using Negamax with Alpha-Beta pruning.
 * 
 * @copyright Copyright (c) 2026
 * 
 * This project is licensed under the MIT License.
 */
#pragma once
#include "tauler.h"
#include <cstdint>


/**
 * @brief Chooses the best column for the AI to play.
 * 
 * @param pos Current player's position bitboard.
 * @param mask Combined occupancy bitboard.
 * @param maxDepth Maximum search depth.
 * @param timeMs Time limit in milliseconds. 0 disables time control.
 * @return Selected column index (0-based) for the best move.
 */
int triarColumnaIA(uint64_t pos, uint64_t mask, int maxDepth = 9, int timeMs = 0);

// Variables for performance metrics
extern long long nodeCount;
extern int lastSearchDepth;

/**
 * @brief Core Negamax recursive search with alpha-beta pruning.
 * 
 * @param pos Current player's bitboard.
 * @param mask Occupancy mask.
 * @param zobristKey Current position hash.
 * @param mirrorZobristKey Current mirrored position hash.
 * @param moveCount Number of moves played so far.
 * @param depth Remaining search depth.
 * @param alpha Alpha bound.
 * @param beta Beta bound.
 * @param currentScore Pre-evaluated positional score for the current player.
 * @param oppScore Pre-evaluated positional score for the opponent.
 * @return The minmax evaluation score for the current position.
 */
int negamax(uint64_t pos, uint64_t mask, uint64_t zobristKey, uint64_t mirrorZobristKey, int moveCount, int depth, int alpha, int beta, int currentScore, int oppScore);

/**
 * @brief Returns the static evaluation score of a board configuration.
 * @param pos Player position bitboard.
 * @param mask Occupancy mask bitboard.
 * @return The evaluation score.
 */
int eval(uint64_t pos, uint64_t mask);

/**
 * @brief Clears the global transposition table.
 */
void clearTranspositionTable();
