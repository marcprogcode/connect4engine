/**
 * @file connect4engine.cpp
 * @author Marc
 * @brief Main entry point for the Connect 4 TUI.
 * 
 * @copyright Copyright (c) 2026
 * 
 * This project is licensed under the MIT License.
 */
#include <iostream>
#include <cstdlib>
#include <ctime>
#include <cstdint>
#include "tauler.h"
#include "ia.h"

using namespace std;

int main() {
    char tauler[FILES][COLUMNES];
    bool finalPartida = false;
    char guanyador = ' ';

    srand(static_cast<unsigned int>(time(NULL)));

    vbr::inicialitzarTauler(tauler, FILES, COLUMNES);

    cout << "=== CONNECT 4 GAME ===" << endl;
    vbr::mostrarTauler(tauler, FILES, COLUMNES);

    while (!finalPartida) {
        vbr::jugarTorn(tauler, FILES, COLUMNES, JUGADOR);

        if (vbr::haGuanyat(tauler, FILES, COLUMNES, JUGADOR)) {
            finalPartida = true;
            guanyador = JUGADOR;
        }
        else if (vbr::taulerPle(tauler, FILES, COLUMNES)) {
            finalPartida = true;
        }
        else {
            cout << "AI Turn (" << IA << ")..." << endl;
            uint64_t pos, mask;
            bbr::boardToBit(tauler, pos, mask);
            // boardToBit puts X's stones in pos, but AI is O.
            // negamax expects pos = current player's stones, so flip to O's perspective.
            int colIA = triarColumnaIA(mask ^ pos, mask, 42, 4000);
            vbr::ferMoviment(tauler, FILES, COLUMNES, colIA + 1, IA);
            vbr::mostrarTauler(tauler, FILES, COLUMNES);

            if (vbr::haGuanyat(tauler, FILES, COLUMNES, IA)) {
                finalPartida = true;
                guanyador = IA;
            }
            else if (vbr::taulerPle(tauler, FILES, COLUMNES)) {
                finalPartida = true;
            }
        }
    }

    if (guanyador == JUGADOR) {
        cout << "Player " << JUGADOR << " wins!" << endl;
    }
    else if (guanyador == IA) {
        cout << "Player " << IA << " wins!" << endl;
    }
    else {
        cout << "Draw" << endl;
    }

    return 0;
}
