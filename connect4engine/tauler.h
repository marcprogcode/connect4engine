#pragma once
#define FILES 6
#define COLUMNES 7
#define JUGADOR 'X'
#define IA 'O'

void inicialitzarTauler(char tauler[][COLUMNES], int nfil, int ncol);
void mostrarTauler(char tauler[][COLUMNES], int nfil, int ncol);
int columnaPlena(char tauler[][COLUMNES], int nfil, int ncol, int col);
bool taulerPle(char tauler[][COLUMNES], int nfil, int ncol);
void copiarTauler(char origen[][COLUMNES], char desti[][COLUMNES], int nfil, int ncol);
int ferMoviment(char tauler[][COLUMNES], int nfil, int ncol, int col, char jugador);
int haGuanyat(char tauler[][COLUMNES], int nfil, int ncol, char jugador);
int entre(int min, int max);
int demanarColumna(char tauler[][COLUMNES], int nfil, int ncol, char jugador);
void jugarTorn(char tauler[][COLUMNES], int nfil, int ncol, char jugador);