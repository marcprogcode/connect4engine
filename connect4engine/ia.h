#pragma once
#include "tauler.h"

int triarColumnaIA(char tauler[][COLUMNES], int nfil, int ncol, char ia, char huma);

int negamax(char tauler[][COLUMNES], int nfil, int ncol, int depth, bool tornIA, char ia, char huma, int alpha, int beta);

int eval(char tauler[][COLUMNES], int nfil, int ncol, char ia, char huma);
