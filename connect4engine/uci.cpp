/**
 * @file uci.cpp
 * @author Marc
 * @brief Connect 4 UCI Wrapper
 *
 * A command-line interface that wraps the existing Connect 4 engine
 * to support UCI-like protocol for automated testing.
 *
 * IMPORTANT: This engine is built as a separate "uci" executable via CMake.
 * It links to the existing tauler.cpp and ia.cpp without modifying them.
 * Select the "uci" target in your IDE or CMake build system to compile and run it.
 *
 * Supported commands:
 *   position [moves]          - Set position (e.g., "position 4453")
 *   go wtime [ms] btime [ms]  - Think with time limit
 *   go depth [d]              - Search to fixed depth
 *   d                         - Display current board
 *   quit                      - Exit
 *
 * Output:
 *   bestmove [col]            - Best move (1-7)
 *   info depth [d] score [s] nodes [n] time [ms]
 * 
 * @copyright Copyright (c) 2026
 * 
 * This project is licensed under the MIT License.
 */

#include <iostream>
#include <sstream>
#include <string>
#include <chrono>
#include "../connect4engine/tauler.h"
#include "../connect4engine/ia.h"
#include "../connect4engine/transposition_table.h"
#include <vector>
#include <algorithm> 

using namespace std;

// GLOBAL STATE
uint64_t global_pos = 0;   // Current player's stones
uint64_t global_mask = 0;  // All stones
int moveCount = 0;

void resetBoard() {
    global_pos = 0;
    global_mask = 0;
    moveCount = 0;
}

// Check if string is a valid move sequence (digits 1-7)
bool isMoveString(const string& s) {
    if (s.empty()) return false;
    return s.find_first_not_of("1234567") == string::npos;
}

// Apply moves to the global bitboards
void applyMoves(const string& moves) {
    for (char c : moves) {
        if (c >= '1' && c <= '7') {
            int col = c - '1'; // Convert 1-7 to 0-6
            if (!bbr::fullColumn(global_mask, col)) {
                bbr::makeMove(global_pos, global_mask, col);
                // Switch turns
                global_pos = global_mask ^ global_pos;
                moveCount++;
            }
        }
    }
}


// Search Wrapper
void findBestMove(int depth, int timeMs) {
    // Reset stats
    nodeCount = 0;

    auto start = chrono::high_resolution_clock::now();

    // Call the AI (returns 0-6 index)
    // If timeMs is 0, logic in ia.cpp should treat it as "infinite time / depth only"
    int bestMoveIndex = triarColumnaIA(global_pos, global_mask, depth, timeMs);

    auto end = chrono::high_resolution_clock::now();
    auto duration = chrono::duration_cast<chrono::milliseconds>(end - start);
    long long timeTaken = duration.count();

    // Avoid divide by zero for NPS
    long long nps = (timeTaken > 0) ? (nodeCount * 1000 / timeTaken) : 0;

    // Output info line (Required by benchmark runner)
    // Score is placeholder "cp 0" unless we extract it from AI controller
    cout << "info depth " << lastSearchDepth
        << " score cp 0"
        << " nodes " << nodeCount
        << " time " << timeTaken
        << " nps " << nps
        << endl;

    // Output bestmove (Required 1-7 format)
    cout << "bestmove " << (bestMoveIndex + 1) << endl;
}

// Main Command Processor
void processCommand(const string& line) {
    istringstream iss(line);
    string cmd;
    iss >> cmd;

    if (cmd == "uci") {
        cout << "id name connect4engine" << endl;
        cout << "id author Marc" << endl;
        cout << "uciok" << endl;
    }
    else if (cmd == "isready") {
        cout << "readyok" << endl;
    }
    else if (cmd == "ucinewgame" || cmd == "new") {
        resetBoard();
        clearTranspositionTable();
    }
    else if (cmd == "position") {
        resetBoard();
        string token;
        while (iss >> token) {
            if (token == "startpos") continue;
            if (token == "moves") continue;

            if (isMoveString(token)) {
                applyMoves(token);
            }
        }
    }
    else if (cmd == "go") {
        string token;

        // Defaults
        int depth = 42;         // Infinite if not specified
        int timeLimit = 0;      // 0 = Infinite / Depth controlled

        // Input parsing
        int movetime = -1;      // Explicit per-move time
        int myTime = -1;        // Time left on clock
        int inc = 0;            // Increment

        while (iss >> token) {
            if (token == "depth") iss >> depth;
            else if (token == "movetime") iss >> movetime;
            else if (token == "wtime") {
                int t; iss >> t;
                if (moveCount % 2 == 0) myTime = t; // P1 (Even)
            }
            else if (token == "btime") {
                int t; iss >> t;
                if (moveCount % 2 == 1) myTime = t; // P2 (Odd)
            }
            else if (token == "winc") {
                int t; iss >> t;
                if (moveCount % 2 == 0) inc = t;
            }
            else if (token == "binc") {
                int t; iss >> t;
                if (moveCount % 2 == 1) inc = t;
            }
        }

        // Case 1: "movetime" (Exact time per move)
        if (movetime != -1) {
            timeLimit = movetime;
        }
        // Case 2: "wtime/btime" (Clock time)
        else if (myTime != -1) {
            // Strategy: Use 5% of remaining time + 50% of increment
            timeLimit = (myTime / 20) + (inc / 2);

            // Minimum safety buffer (don't think for < 50ms unless clock is dying)
            if (timeLimit < 50 && myTime > 100) timeLimit = 50;
        }
        // Case 3: Neither (Depth only) -> timeLimit remains 0

        findBestMove(depth, timeLimit);
    }
    else if (cmd == "quit" || cmd == "exit") {
        exit(0);
    }
}

int main() {
    // Fast IO
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    resetBoard();
    clearTranspositionTable();

    string line;
    while (getline(cin, line)) {
        if (line.empty()) continue;
        processCommand(line);
    }
    return 0;
}