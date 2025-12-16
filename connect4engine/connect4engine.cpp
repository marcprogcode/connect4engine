#include <iostream>
#include <cstdlib>
#include <ctime>
#include "tauler.h"
#include "ia.h"

using namespace std;

int main() {
    char tauler[FILES][COLUMNES];
    bool finalPartida = false;
    char guanyador = ' ';

    srand(time(NULL));

    inicialitzarTauler(tauler, FILES, COLUMNES);

    cout << "=== JOC 4 EN LINIA ===" << endl;
    mostrarTauler(tauler, FILES, COLUMNES);

    while (!finalPartida) {
        jugarTorn(tauler, FILES, COLUMNES, JUGADOR);

        if (haGuanyat(tauler, FILES, COLUMNES, JUGADOR)) {
            finalPartida = true;
            guanyador = JUGADOR;
        }
        else if (taulerPle(tauler, FILES, COLUMNES)) {
            finalPartida = true;
        }
        else {
            cout << "Torn de la Maquina (" << IA << ")..." << endl;
            int colIA = triarColumnaIA(tauler, FILES, COLUMNES, IA, JUGADOR);
            ferMoviment(tauler, FILES, COLUMNES, colIA, IA);
            mostrarTauler(tauler, FILES, COLUMNES);

            if (haGuanyat(tauler, FILES, COLUMNES, IA)) {
                finalPartida = true;
                guanyador = IA;
            }
            else if (taulerPle(tauler, FILES, COLUMNES)) {
                finalPartida = true;
            }
        }
    }

    if (guanyador == JUGADOR) {
        cout << "Victoria jugador " << JUGADOR << endl;
    }
    else if (guanyador == IA) {
        cout << "Victoria jugador " << IA << endl;
    }
    else {
        cout << "Taules" << endl;
    }

    return 0;
}
