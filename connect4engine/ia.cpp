#include "ia.h"
#include <cstdlib>
#include <iostream>

using namespace std;

// Constant for infinity
const int INF = 1000000000;

int eval(char tauler[][COLUMNES], int nfil, int ncol, char ia, char huma) {
    // Evaluation matrix generated based on how many 4-in-a-row combinations are possible from each position
    static const int scoreMap[6][7] = {
        {3, 4,  5,  7,  5, 4, 3},
        {4, 6,  8,  9,  8, 6, 4},
        {5, 8, 11, 13, 11, 8, 5},
        {5, 8, 11, 13, 11, 8, 5},
        {4, 6,  8,  9,  8, 6, 4},
        {3, 4,  5,  7,  5, 4, 3}
    };

    int score = 0;

    for (int r = 0; r < nfil; r++) {
        for (int c = 0; c < ncol; c++) {

            // Get the piece at the position
            char cell = tauler[r][c];

            if (cell != ' ') {
                int value = scoreMap[r][c];
                // Assign value to the cell based on who holds the piece at the position
                if (cell == ia) {
                    score += value;
                }
                else if (cell == huma) {
                    score -= value;
                }
            }
        }
    }

    return score;
}

int negamax(char tauler[][COLUMNES], int nfil, int ncol, int depth, bool tornIA, char ia, char huma, int alpha, int beta) {
    // Check that the game hasn't ended
    // If the previous player made the winning move, the current player loses
    char rival = tornIA ? huma : ia;
    if (haGuanyat(tauler, nfil, ncol, rival)) {
        return -1000000 - depth;
    }

    // Check for a draw
    bool ple = true;
    for (int c = 1; c <= ncol && ple; c++) {
        if (columnaPlena(tauler, nfil, ncol, c) == 0) {
            ple = false;
        }
    }

    // Neutral situation (we use the heuristic)
    if (depth == 0 || ple) {
        if (ple) return 0;
        // Calculate the position evaluation (Positive is an advantage for the AI)
        int globalScore = eval(tauler, nfil, ncol, ia, huma);

        // The negamax algorithm requires inverting the evaluation based on the player's turn
        return tornIA ? globalScore : -globalScore;
    }

    // Recursion with alpha-beta pruning
    // Declare the most efficient search order to save operations
    // Central columns have better chances of being a better move
    static const int columnOrder[7] = { 4, 3, 5, 2, 6, 1, 7 };
    for (int i = 0; i < 7; i++) {
        int c = columnOrder[i];
        if (columnaPlena(tauler, nfil, ncol, c) == 0) {
            // Make a copy of the matrix to make moves non-permanently
            char copia[FILES][COLUMNES];
            copiarTauler(tauler, copia, nfil, ncol);

            char actual = tornIA ? ia : huma;
            ferMoviment(copia, nfil, ncol, c, actual);

            int score = -negamax(copia, nfil, ncol, depth - 1, !tornIA, ia, huma, -beta, -alpha);
            // If the score is too good, the opponent will avoid this branch, so we eliminate it
            if (score >= beta) {
                return beta;
            }
            // If the move improves the best score, update alpha.
            if (score > alpha) {
                alpha = score;
            }
        }
    }
    // Return the best score
    return alpha;
}


int triarColumnaIA(char tauler[][COLUMNES], int nfil, int ncol, char ia, char huma) {
    int bestMove = 1;
    int bestScore = -INF;
    int maxDepth = 9;

    int alpha = -INF;
    int beta = INF;

    static const int columnOrder[7] = { 4, 3, 5, 2, 6, 1, 7 };
    for (int i = 0; i < 7; i++) {
        int c = columnOrder[i];

        if (columnaPlena(tauler, nfil, ncol, c) == 0) {
            char copia[FILES][COLUMNES];
            copiarTauler(tauler, copia, nfil, ncol);

            ferMoviment(copia, nfil, ncol, c, ia);

            int score = -negamax(copia, nfil, ncol, maxDepth, false, ia, huma, -beta, -alpha);

            if (score > bestScore) {
                bestScore = score;
                bestMove = c;
            }

            if (bestScore > alpha) {
                alpha = bestScore;
            }
        }
    }
    return bestMove;
}