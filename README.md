# connect4engine
## Intro
This project implements a Connect 4 engine using a command-line interface. The two main objectives for the program were:
*   Beat the average human player consistently.
*   Run in real-time (under 5 seconds per move).

## How to Run
1.  Clone this repository.
2.  Open the project folder or solution file in **Visual Studio**.
3.  Build and Run the project (Standard "Start" or `F5`).

## Implementation
To accomplish the project goals, I built a CLI version of Connect 4 that allows a player to input moves, while the AI calculates a response. The AI logic is decoupled from the game board logic:
*   `tauler.cpp`: Handles the main board logic.
*   `ia.cpp`: Handles the AI decision-making.

The engine uses a **Negamax** algorithm (a variant of Minimax) to search the decision tree. To evaluate positions efficiently, I implemented simple heuristics:
1.  **Scoring:** The evaluation function assigns a score from -infinity to +infinity.
    *   **Win/Loss:** Set to +/- infinity.
    *   **Draw:** Set to 0.
    *   **Heuristic:** For non-terminal states, the engine calculates a score based on a precomputed matrix. This matrix weights positions based on how many distinct 4-in-a-row combinations are possible through that specific cell.
2.  **Alpha-Beta Pruning:** To drastically reduce the search space, the engine filters out branches that are proven to be worse than the current best option.

With this configuration, the engine consistently beats average players at **search depth 9**, taking significantly less than a second to calculate a move on modern hardware.

## Future Improvements
*   **Bitboards:** Replacing the current matrix representation with two bitboards (one for position, one for mask) would greatly increase search speed and reduce memory usage.
*   **Dynamic Depth:** Implementing iterative deepening or dynamic depth adjustment based on the number of remaining empty cells.
*   **Heuristic Tuning:** Balancing complexity vs. accuracy to squeeze out more performance.
*   **Monte-Carlo Tree Search (MCTS):** While potentially overkill for Connect 4, exploring MCTS would be a valuable educational exercise.