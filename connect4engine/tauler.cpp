#include "tauler.h"
#include <iostream>
#include <iomanip>

using namespace std;

void inicialitzarTauler(char tauler[][COLUMNES], int nfil, int ncol) {
    for (int i = 0; i < nfil; i++) {
        for (int j = 0; j < ncol; j++) {
            tauler[i][j] = ' ';
        }
    }
}

void mostrarTauler(char tauler[][COLUMNES], int nfil, int ncol) {
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

int columnaPlena(char tauler[][COLUMNES], int nfil, int ncol, int col) {
    if (col < 1 || col > ncol) {
        return -1;
    }
    if (tauler[0][col - 1] != ' ') {
        return 1;
    }
    return 0;
}

bool taulerPle(char tauler[][COLUMNES], int nfil, int ncol) {
    for (int j = 1; j <= ncol; j++) {
        if (columnaPlena(tauler, nfil, ncol, j) == 0) {
            return false;
        }
    }
    return true;
}

void copiarTauler(char origen[][COLUMNES], char desti[][COLUMNES], int nfil, int ncol) {
    for (int i = 0; i < nfil; i++) {
        for (int j = 0; j < ncol; j++) {
            desti[i][j] = origen[i][j];
        }
    }
}

int ferMoviment(char tauler[][COLUMNES], int nfil, int ncol, int col, char jugador) {
    if (col < 1 || col > ncol) return -1;
    if (columnaPlena(tauler, nfil, ncol, col) == 1) return 0;

    for (int i = nfil - 1; i >= 0; i--) {
        if (tauler[i][col - 1] == ' ') {
            tauler[i][col - 1] = jugador;
            return 1;
        }
    }
    return 0;
}

int haGuanyat(char tauler[][COLUMNES], int nfil, int ncol, char jugador) {
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

int entre(int min, int max) {
    int valor;
    do {
        cout << "Introdueix un valor entre " << min << " i " << max << ": ";
        cin >> valor;
        if (valor < min || valor > max) {
            cout << "Error: el valor introduit no esta dintre l'interval demanat" << endl;
        }
    } while (valor < min || valor > max);
    return valor;
}

int demanarColumna(char tauler[][COLUMNES], int nfil, int ncol, char jugador) {
    int col;
    bool valida = false;
    cout << "Torn jugador " << jugador << endl;

    while (!valida) {
        col = entre(1, ncol);
        if (columnaPlena(tauler, nfil, ncol, col) == 1) {
            cout << "Error: la coluna " << col << " esta plena." << endl;
        }
        else {
            valida = true;
        }
    }
    return col;
}

void jugarTorn(char tauler[][COLUMNES], int nfil, int ncol, char jugador) {
    int col = demanarColumna(tauler, nfil, ncol, jugador);
    int resultat = ferMoviment(tauler, nfil, ncol, col, jugador);

    if (resultat != 1) {
        cout << "S'ha produit un error inesperat en ferMoviment." << endl;
    }
    mostrarTauler(tauler, nfil, ncol);
}
