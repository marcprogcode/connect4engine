/**
 * @file unit_tests.cpp
 * @author Marc
 * @brief Unit tests for Connect 4 core bitboard logic.
 * 
 * @copyright Copyright (c) 2026
 * 
 * This project is licensed under the MIT License.
 */
#include <iostream>
#include <cassert>
#include "../connect4engine/tauler.h"

void test_initialization() {
    uint64_t pos, mask;
    bbr::inizalizeBoard(pos, mask);
    assert(pos == 0 && "pos should be 0");
    assert(mask == 0 && "mask should be 0");
    
    char board[6][7];
    vbr::inicialitzarTauler(board, 6, 7);
    assert(board[0][0] == ' ' && "char board should be empty");
    
    std::cout << "[OK] test_initialization\n";
}

void test_make_move() {
    uint64_t pos, mask;
    bbr::inizalizeBoard(pos, mask);
    
    // Play move in column 3
    bbr::makeMove(pos, mask, 3);
    assert(mask != 0 && "mask should not be empty after a move");
    
    std::cout << "[OK] test_make_move\n";
}

void test_win_detection() {
    uint64_t pos = 0, mask = 0;
    
    // Create a horizontal win record at the bottom row (row 5)
    // Bit mapping: (col * 7) + (5 - row)
    // So for row 5 (bottom), bit is col * 7
    pos |= (1ULL << 0);
    pos |= (1ULL << 7);
    pos |= (1ULL << 14);
    pos |= (1ULL << 21);
    
    assert(bbr::hasWon(pos) == true && "Horizontal win not detected");
    
    std::cout << "[OK] test_win_detection\n";
}

int main() {
    std::cout << "Running Native C++ Unit Tests...\n";
    test_initialization();
    test_make_move();
    test_win_detection();
    std::cout << "All C++ Unit Tests Passed Successfully!\n";
    return 0;
}
