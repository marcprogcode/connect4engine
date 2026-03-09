/**
 * @file tauler.cpp
 * @author Marc
 * @brief Board representation and game logic for Connect 4.
 * 
 * @copyright Copyright (c) 2026
 * 
 * This project is licensed under the MIT License.
 */
#include "tauler.h"
#include <iostream>
#include <iomanip>
#include <cstdint>

using namespace std;
// This is kept  for backwards compatibility
// as this project was initially for a university class
// but I found it interesting, so I decided to dive deeper
// and use it as a learning oportunity

void vbr::inicialitzarTauler(char tauler[][COLUMNES], int nfil, int ncol) {
    for (int i = 0; i < nfil; i++) {
        for (int j = 0; j < ncol; j++) {
            tauler[i][j] = ' ';
        }
    }
}

void vbr::mostrarTauler(char tauler[][COLUMNES], int nfil, int ncol) {
    cout << endl;
    for (int i = 0; i < nfil; i++) {
        cout << "|";
        for (int j = 0; j < ncol; j++) {
            cout << " " << tauler[i][j] << " |";
        }
        cout << endl;
    }
    cout << "|";
    for (int j = 0; j < ncol; j++) cout << "---|";
    cout << endl;

    cout << " ";
    for (int j = 1; j <= ncol; j++) {
        cout << " " << j << "  ";
    }
    cout << endl << endl;
}

int vbr::columnaPlena(char tauler[][COLUMNES], int nfil, int ncol, int col) {
    (void)nfil;
    if (col < 1 || col > ncol) {
        return -1;
    }
    if (tauler[0][col - 1] != ' ') {
        return 1;
    }
    return 0;
}

bool vbr::taulerPle(char tauler[][COLUMNES], int nfil, int ncol) {
    for (int j = 1; j <= ncol; j++) {
        if (vbr::columnaPlena(tauler, nfil, ncol, j) == 0) {
            return false;
        }
    }
    return true;
}

void vbr::copiarTauler(char origen[][COLUMNES], char desti[][COLUMNES], int nfil, int ncol) {
    for (int i = 0; i < nfil; i++) {
        for (int j = 0; j < ncol; j++) {
            desti[i][j] = origen[i][j];
        }
    }
}

int vbr::ferMoviment(char tauler[][COLUMNES], int nfil, int ncol, int col, char jugador) {
    if (col < 1 || col > ncol) return -1;
    if (vbr::columnaPlena(tauler, nfil, ncol, col) == 1) return 0;

    for (int i = nfil - 1; i >= 0; i--) {
        if (tauler[i][col - 1] == ' ') {
            tauler[i][col - 1] = jugador;
            return 1;
        }
    }
    return 0;
}

int vbr::haGuanyat(char tauler[][COLUMNES], int nfil, int ncol, char jugador) {
    for (int i = 0; i < nfil; i++) {
        for (int j = 0; j < ncol - 3; j++) {
            if (tauler[i][j] == jugador && tauler[i][j + 1] == jugador &&
                tauler[i][j + 2] == jugador && tauler[i][j + 3] == jugador) return 1;
        }
    }

    for (int i = 0; i < nfil - 3; i++) {
        for (int j = 0; j < ncol; j++) {
            if (tauler[i][j] == jugador && tauler[i + 1][j] == jugador &&
                tauler[i + 2][j] == jugador && tauler[i + 3][j] == jugador) return 1;
        }
    }

    for (int i = 0; i < nfil - 3; i++) {
        for (int j = 0; j < ncol - 3; j++) {
            if (tauler[i][j] == jugador && tauler[i + 1][j + 1] == jugador &&
                tauler[i + 2][j + 2] == jugador && tauler[i + 3][j + 3] == jugador) return 1;
        }
    }

    for (int i = 3; i < nfil; i++) {
        for (int j = 0; j < ncol - 3; j++) {
            if (tauler[i][j] == jugador && tauler[i - 1][j + 1] == jugador &&
                tauler[i - 2][j + 2] == jugador && tauler[i - 3][j + 3] == jugador) return 1;
        }
    }
    return 0;
}

int vbr::entre(int min, int max) {
    int valor;
    do {
        cout << "Enter a value between " << min << " and " << max << ": ";
        cin >> valor;
        if (valor < min || valor > max) {
            cout << "Error: the input value is not within the requested range" << endl;
        }
    } while (valor < min || valor > max);
    return valor;
}

int vbr::demanarColumna(char tauler[][COLUMNES], int nfil, int ncol, char jugador) {
    int col = 0;
    bool valida = false;
    cout << "Player turn " << jugador << endl;

    while (!valida) {
        col = vbr::entre(1, ncol);
        if (vbr::columnaPlena(tauler, nfil, ncol, col) == 1) {
            cout << "Error: column " << col << " is full." << endl;
        }
        else {
            valida = true;
        }
    }
    return col;
}

void vbr::jugarTorn(char tauler[][COLUMNES], int nfil, int ncol, char jugador) {
    int col = vbr::demanarColumna(tauler, nfil, ncol, jugador);
    int resultat = vbr::ferMoviment(tauler, nfil, ncol, col, jugador);

    if (resultat != 1) {
        cout << "An unexpected error occurred in ferMoviment." << endl;
    }
    vbr::mostrarTauler(tauler, nfil, ncol);
}

// Here are the intermediate steps from the old char grid to the bitboards
// Needed to still pass the university's auto grading tests, and playing on a simple TUI
void bbr::inizalizeBoard(uint64_t &pos, uint64_t &mask) {
    pos = 0;
    mask = 0;
}

void bbr::bitToBoard(char board[6][7], uint64_t pos, uint64_t mask) {
    uint64_t bit_mask;

    for (int i = 0; i < 49; i++) {
        if ((i % 7) == 6) continue;
        bit_mask = 1ULL << i;
        if ((mask & bit_mask) != 0) board[5 - (i % 7)][i / 7] = ((pos & bit_mask) != 0) ? 'X' : 'O';
        else {
            board[5 - (i % 7)][i / 7] = ' ';
        }
    }
}
void bbr::boardToBit(char board[6][7], uint64_t& pos, uint64_t& mask) {
    // 1. Reset everything to 0
    pos = 0;
    mask = 0;

    // 2. Iterate through the board columns and rows
    for (int col = 0; col < 7; col++) {
        for (int row = 0; row < 6; row++) {
            char cell = board[row][col];

            // If empty, skip
            if (cell == ' ') continue;

            // Calculate the specific bit index
            // (5 - row) flips it so array index 5 (bottom) becomes bit offset 0
            int bit_index = (col * 7) + (5 - row);

            // Add to mask (Occupied slots)
            mask |= (1ULL << bit_index);

            // Add to pos (Current player slots)
            if (cell == 'X') {
                pos |= (1ULL << bit_index);
            }
        }
    }
}

bool bbr::fullColumn(uint64_t mask, int col) {
    return (mask & 1ULL << (col * 7 + 5)) != 0;
}

bool bbr::fullBoard(uint64_t mask) {
    constexpr uint64_t TOP_MASK = 0x810204081020ULL;
    return (mask & TOP_MASK) == TOP_MASK;
}

void bbr::makeMove(uint64_t &pos, uint64_t &mask, int col) {
    pos ^= ((mask + (1ULL << (col * 7))) & ~mask);
    mask ^= ((mask + (1ULL << (col * 7))) & ~mask);
}

bool bbr::hasWon(uint64_t pos) {
    uint64_t connected_pairs;

    // 1. Horizontal (Offset 7: Height of one column)
    connected_pairs = pos & (pos >> 7);
    if (connected_pairs & (connected_pairs >> 14)) return true;

    // 2. Diagonal / (Offset 8: Up 1 + Right 1)
    connected_pairs = pos & (pos >> 8);
    if (connected_pairs & (connected_pairs >> 16)) return true;

    // 3. Diagonal \ (Offset 6: Down 1 + Right 1)
    connected_pairs = pos & (pos >> 6);
    if (connected_pairs & (connected_pairs >> 12)) return true;

    // 4. Vertical (Offset 1: Up 1)
    connected_pairs = pos & (pos >> 1);
    if (connected_pairs & (connected_pairs >> 2)) return true;

    return false;
}

uint64_t bbr::mirror(uint64_t pos) {
    // 7 columns, 7 bits per column (6 rows + padding)
    // We need to swap col 0<->6, 1<->5, 2<->4
    
    // Define column masks
    constexpr uint64_t COL_0 = 0x7FULL;
    constexpr uint64_t COL_1 = 0x7FULL << 7;
    constexpr uint64_t COL_2 = 0x7FULL << 14;
    constexpr uint64_t COL_3 = 0x7FULL << 21;
    constexpr uint64_t COL_4 = 0x7FULL << 28;
    constexpr uint64_t COL_5 = 0x7FULL << 35;
    constexpr uint64_t COL_6 = 0x7FULL << 42;

    uint64_t newPos = 0;
    
    // Swap 0 and 6
    newPos |= (pos & COL_0) << 42;
    newPos |= (pos & COL_6) >> 42;
    
    // Swap 1 and 5
    newPos |= (pos & COL_1) << 28;
    newPos |= (pos & COL_5) >> 28;
    
    // Swap 2 and 4
    newPos |= (pos & COL_2) << 14;
    newPos |= (pos & COL_4) >> 14;
    
    // Keep 3
    newPos |= (pos & COL_3);
    
    return newPos;
}