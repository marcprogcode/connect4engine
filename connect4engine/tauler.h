/**
 * @file tauler.h
 * @author Marc
 * @brief Board representation and game logic for Connect 4.
 * 
 * @copyright Copyright (c) 2026
 * 
 * This project is licensed under the MIT License.
 */
#pragma once
#define FILES 6
#define COLUMNES 7
#define JUGADOR 'X'
#define IA 'O'
#include <cstdint>
// Visual Board Representation: This code was built for
// the original university project that required this format
// with the board being a char matrix.
namespace vbr {
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
}
// While Visual Board Representation a good learning tool, it's 
// extremly slow for the use I am giving it in this project, 
// so it will be maintained for backwards compatibility but 
// new AI's past v6 will use new bit board representation.
namespace bbr {
	/**
	 * @brief Initialize the board state.
	 * @param pos Player position bitboard.
	 * @param mask Occupancy mask bitboard.
	 */
	void inizalizeBoard(uint64_t &pos, uint64_t &mask);

	/**
	 * @brief Convert bitboard representation back to visual character board.
	 * @param board The character board to convert to.
	 * @param pos Player position bitboard.
	 * @param mask Occupancy mask bitboard.
	 */
	void bitToBoard(char board[6][7], uint64_t pos, uint64_t mask);

	/**
	 * @brief Convert character board representation to bitboard.
	 * @param board The character board to convert from.
	 * @param pos Player position bitboard.
	 * @param mask Occupancy mask bitboard.
	 */
	void boardToBit(char board[6][7], uint64_t& pos, uint64_t& mask);

	/**
	 * @brief Check if a column is full.
	 * @param mask Occupancy mask bitboard.
	 * @param col The column index (0-indexed).
	 * @return true if the column is full, false otherwise.
	 */
	bool fullColumn(uint64_t mask, int col);

	/**
	 * @brief Check if the entire board is full.
	 * @param mask Occupancy mask bitboard.
	 * @return true if the board is full, false otherwise.
	 */
	bool fullBoard(uint64_t mask);

	/**
	 * @brief Apply a move to the bitboards for the given column.
	 * @param pos Player position bitboard.
	 * @param mask Occupancy mask bitboard.
	 * @param col The column index (0-indexed).
	 */
	void makeMove(uint64_t &pos, uint64_t &mask, int col);

	/**
	 * @brief Check if the current player's bitboard has a winning 4-in-a-row alignment.
	 * @param pos Player position bitboard.
	 * @return true if there is a win, false otherwise.
	 */
	bool hasWon(uint64_t pos);

	/**
	 * @brief Mirror the bitboard horizontally (useful for symmetric evaluation).
	 * @param pos Bitboard to mirror.
	 * @return The mirrored bitboard.
	 */
	uint64_t mirror(uint64_t pos);
}
