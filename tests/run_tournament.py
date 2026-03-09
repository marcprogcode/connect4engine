"""
Connect 4 Tournament Runner

Runs engine-vs-engine matches using an opening book.
Each opening is played twice (swapping colors) to eliminate first-move advantage.

Usage:
    python run_tournament.py --engine1 <path> --engine2 <path>
    python run_tournament.py --engine1 ../bin/v1.exe --engine2 ../bin/v2.exe --games 20

Output:
    Match results, win rates, and optionally Elo difference estimation.
"""

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Optional
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent))
from engine_wrapper import EngineWrapper


class GameResult(Enum):
    """Result of a game from Player 1's perspective."""
    WIN = 1.0
    DRAW = 0.5
    LOSS = 0.0


@dataclass
class MatchResult:
    """Result of a single match (one opening, both colors)."""
    opening: str
    game1_result: GameResult  # Engine1 as Player 1
    game2_result: GameResult  # Engine2 as Player 1


@dataclass
class TournamentStats:
    """Overall tournament statistics."""
    engine1_name: str
    engine2_name: str
    engine1_wins: int = 0
    engine2_wins: int = 0
    draws: int = 0
    total_games: int = 0
    match_results: List[MatchResult] = field(default_factory=list)
    
    @property
    def engine1_score(self) -> float:
        return self.engine1_wins + 0.5 * self.draws
    
    @property
    def engine2_score(self) -> float:
        return self.engine2_wins + 0.5 * self.draws
    
    @property
    def engine1_winrate(self) -> float:
        if self.total_games == 0:
            return 0.0
        return self.engine1_score / self.total_games


class Connect4Game:
    """Simulates a Connect 4 game between two engines."""
    
    ROWS = 6
    COLS = 7
    
    def __init__(self):
        self.board = [[' ' for _ in range(self.COLS)] for _ in range(self.ROWS)]
        self.move_history = ""
        self.current_player = 'X'  # X always goes first
    
    def make_move(self, col: int) -> bool:
        """
        Make a move in the specified column (1-7).
        
        Returns True if move was successful, False otherwise.
        """
        if col < 1 or col > 7:
            return False
        
        col_idx = col - 1
        
        # Find the lowest empty row in this column
        for row in range(self.ROWS - 1, -1, -1):
            if self.board[row][col_idx] == ' ':
                self.board[row][col_idx] = self.current_player
                self.move_history += str(col)
                self.current_player = 'O' if self.current_player == 'X' else 'X'
                return True
        
        return False  # Column is full
    
    def is_column_full(self, col: int) -> bool:
        """Check if a column is full."""
        return self.board[0][col - 1] != ' '
    
    def check_winner(self) -> Optional[str]:
        """
        Check if there's a winner.
        
        Returns 'X', 'O', or None.
        """
        # Check horizontal
        for row in range(self.ROWS):
            for col in range(self.COLS - 3):
                if (self.board[row][col] != ' ' and
                    self.board[row][col] == self.board[row][col+1] ==
                    self.board[row][col+2] == self.board[row][col+3]):
                    return self.board[row][col]
        
        # Check vertical
        for row in range(self.ROWS - 3):
            for col in range(self.COLS):
                if (self.board[row][col] != ' ' and
                    self.board[row][col] == self.board[row+1][col] ==
                    self.board[row+2][col] == self.board[row+3][col]):
                    return self.board[row][col]
        
        # Check diagonal (down-right)
        for row in range(self.ROWS - 3):
            for col in range(self.COLS - 3):
                if (self.board[row][col] != ' ' and
                    self.board[row][col] == self.board[row+1][col+1] ==
                    self.board[row+2][col+2] == self.board[row+3][col+3]):
                    return self.board[row][col]
        
        # Check diagonal (up-right)
        for row in range(3, self.ROWS):
            for col in range(self.COLS - 3):
                if (self.board[row][col] != ' ' and
                    self.board[row][col] == self.board[row-1][col+1] ==
                    self.board[row-2][col+2] == self.board[row-3][col+3]):
                    return self.board[row][col]
        
        return None
    
    def is_draw(self) -> bool:
        """Check if the game is a draw (board full, no winner)."""
        return all(self.board[0][col] != ' ' for col in range(self.COLS))
    
    def is_game_over(self) -> Tuple[bool, Optional[str]]:
        """
        Check if game is over.
        
        Returns (is_over, winner) where winner is 'X', 'O', or None for draw.
        """
        winner = self.check_winner()
        if winner:
            return True, winner
        if self.is_draw():
            return True, None
        return False, None


class TournamentRunner:
    """Runs a tournament between two engines."""
    

    def __init__(self, engine1_path: str, engine2_path: str,
                 depth1: int = 9, depth2: int = 9, 
                 time1: Optional[int] = None, time2: Optional[int] = None,
                 use_movetime: bool = False,
                 use_movetime1: Optional[bool] = None, use_movetime2: Optional[bool] = None):
        """
        Initialize the tournament runner.
        
        Args:
            engine1_path: Path to first engine executable
            engine2_path: Path to second engine executable
            depth1: Search depth for engine 1 (None = no depth limit)
            depth2: Search depth for engine 2 (None = no depth limit)
            time1: Time limit in ms for engine 1 (None = no time limit)
            time2: Time limit in ms for engine 2 (None = no time limit)
            use_movetime: Default movetime setting for both engines
            use_movetime1: Override movetime for engine 1 (None = use default)
            use_movetime2: Override movetime for engine 2 (None = use default)
        """
        self.engine1_path = engine1_path
        self.engine2_path = engine2_path
        self.depth1 = depth1
        self.depth2 = depth2
        self.time1 = time1
        self.time2 = time2
        # Per-engine movetime settings (fall back to global if not specified)
        self.use_movetime1 = use_movetime1 if use_movetime1 is not None else use_movetime
        self.use_movetime2 = use_movetime2 if use_movetime2 is not None else use_movetime
        self.openings_dir = Path(__file__).parent / "openings"
    
    def load_openings(self, max_openings: Optional[int] = None) -> List[str]:
        """Load opening positions from the opening book."""
        openings = []
        openings_file = self.openings_dir / "balanced_openings.txt"
        
        if not openings_file.exists():
            print(f"Warning: Openings file not found: {openings_file}")
            return [""]  # Use empty opening as fallback
        
        with open(openings_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Take only the moves part (before any comment)
                moves = line.split('#')[0].strip()
                if moves:
                    openings.append(moves)
        
        if max_openings and len(openings) > max_openings:
            openings = openings[:max_openings]
        
        return openings if openings else [""]
    
    def play_game(self, engine1: EngineWrapper, engine2: EngineWrapper,
                  opening: str, engine1_is_player1: bool) -> GameResult:
        """
        Play a single game.
        
        Args:
            engine1: First engine wrapper
            engine2: Second engine wrapper
            opening: Opening moves to apply before engines start
            engine1_is_player1: If True, engine1 plays as X (first player)
            
        Returns:
            GameResult from engine1's perspective
        """
        game = Connect4Game()
        
        # Apply opening moves
        for char in opening:
            if char.isdigit():
                col = int(char)
                if not game.make_move(col):
                    print(f"  Warning: Invalid opening move {col}")
                    break
        
        # Determine which engine plays which color
        if engine1_is_player1:
            player_x = engine1
            player_o = engine2
        else:
            player_x = engine2
            player_o = engine1
        
        # Play the game
        max_moves = 42  # Maximum possible moves in Connect 4
        move_count = len(opening)
        
        while move_count < max_moves:
            # Check if game is over
            game_over, winner = game.is_game_over()
            if game_over:
                break
            
            # Get current player's engine
            current_engine = player_x if game.current_player == 'X' else player_o
            
            # Set position and get move
            current_engine.set_position(game.move_history)
            
            # Determine search parameters for current engine
            if current_engine == engine1:
                depth = self.depth1 if self.depth1 else None
                time_ms = self.time1 if self.time1 else 0
                use_movetime = self.use_movetime1
            else:
                depth = self.depth2 if self.depth2 else None
                time_ms = self.time2 if self.time2 else 0
                use_movetime = self.use_movetime2
                
            info = current_engine.go(time_ms=time_ms, depth=depth, use_movetime=use_movetime)
            
            if info.bestmove is None:
                print(f"  Warning: Engine returned no move!")
                break
            
            # Make the move
            if not game.make_move(info.bestmove):
                print(f"  Warning: Engine made invalid move {info.bestmove}")
                break
            
            move_count += 1
        
        # Determine result from engine1's perspective
        game_over, winner = game.is_game_over()
        
        if winner is None:
            return GameResult.DRAW
        elif (winner == 'X' and engine1_is_player1) or (winner == 'O' and not engine1_is_player1):
            return GameResult.WIN
        else:
            return GameResult.LOSS
    
    def run_match(self, engine1: EngineWrapper, engine2: EngineWrapper,
                  opening: str) -> MatchResult:
        """
        Run a match (two games with swapped colors).
        
        Args:
            engine1: First engine wrapper
            engine2: Second engine wrapper
            opening: Opening moves
            
        Returns:
            MatchResult with both game results
        """
        # Game 1: Engine1 plays as Player 1 (X)
        result1 = self.play_game(engine1, engine2, opening, engine1_is_player1=True)
        
        # Game 2: Engine2 plays as Player 1 (X)
        result2_raw = self.play_game(engine1, engine2, opening, engine1_is_player1=False)
        
        return MatchResult(
            opening=opening,
            game1_result=result1,
            game2_result=result2_raw
        )
    
    def run_tournament(self, max_openings: Optional[int] = None) -> TournamentStats:
        """
        Run the full tournament.
        
        Args:
            max_openings: Maximum number of openings to use
            
        Returns:
            TournamentStats with all results
        """
        openings = self.load_openings(max_openings)
        
        engine1_name = Path(self.engine1_path).stem
        engine2_name = Path(self.engine2_path).stem
        
        stats = TournamentStats(
            engine1_name=engine1_name,
            engine2_name=engine2_name
        )
        
        print(f"\n{'=' * 60}")
        print(f"TOURNAMENT: {engine1_name} vs {engine2_name}")
        print(f"Openings: {len(openings)}")
        
        # Show per-engine settings
        e1_settings = []
        if self.depth1: e1_settings.append(f"depth={self.depth1}")
        if self.time1: e1_settings.append(f"time={self.time1}ms")
        if not e1_settings: e1_settings.append("default (depth 9)")
        e2_settings = []
        if self.depth2: e2_settings.append(f"depth={self.depth2}")
        if self.time2: e2_settings.append(f"time={self.time2}ms")
        if not e2_settings: e2_settings.append("default (depth 9)")
        
        print(f"{engine1_name}: {', '.join(e1_settings)}")
        print(f"{engine2_name}: {', '.join(e2_settings)}")
        print(f"{'=' * 60}")
        
        try:
            with EngineWrapper(self.engine1_path) as engine1, \
                 EngineWrapper(self.engine2_path) as engine2:
                
                for i, opening in enumerate(openings):
                    opening_display = opening if opening else "(empty)"
                    print(f"\nMatch {i+1}/{len(openings)}: Opening '{opening_display}'")
                    
                    match = self.run_match(engine1, engine2, opening)
                    stats.match_results.append(match)
                    
                    # Update stats based on game results
                    for game_result, is_game1 in [(match.game1_result, True), 
                                                   (match.game2_result, False)]:
                        stats.total_games += 1
                        
                        if game_result == GameResult.WIN:
                            stats.engine1_wins += 1
                            result_str = f"{engine1_name} wins"
                        elif game_result == GameResult.LOSS:
                            stats.engine2_wins += 1
                            result_str = f"{engine2_name} wins"
                        else:
                            stats.draws += 1
                            result_str = "Draw"
                        
                        game_label = "Game 1" if is_game1 else "Game 2"
                        player1 = engine1_name if is_game1 else engine2_name
                        print(f"  {game_label} ({player1} as X): {result_str}")
                    
        except Exception as e:
            print(f"\nError during tournament: {e}")
            import traceback
            traceback.print_exc()
        
        # Print final summary
        self._print_summary(stats)
        
        return stats
    
    def _print_summary(self, stats: TournamentStats):
        """Print tournament summary."""
        print(f"\n{'=' * 60}")
        print("TOURNAMENT RESULTS")
        print(f"{'=' * 60}")
        print(f"\n{stats.engine1_name}: {stats.engine1_wins} wins ({stats.engine1_score} points)")
        print(f"{stats.engine2_name}: {stats.engine2_wins} wins ({stats.engine2_score} points)")
        print(f"Draws: {stats.draws}")
        print(f"Total games: {stats.total_games}")
        
        if stats.total_games > 0:
            winrate1 = stats.engine1_winrate * 100
            winrate2 = (1 - stats.engine1_winrate) * 100
            print(f"\n{stats.engine1_name} win rate: {winrate1:.1f}%")
            print(f"{stats.engine2_name} win rate: {winrate2:.1f}%")
            
            # Simple Elo difference estimation (approximate)
            if 0 < stats.engine1_winrate < 1:
                import math
                elo_diff = -400 * math.log10(1 / stats.engine1_winrate - 1)
                print(f"\nEstimated Elo difference: {elo_diff:+.0f} (E1 - E2)")
        
        print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(description="Connect 4 Tournament Runner")
    parser.add_argument("--engine1", required=True, help="Path to first engine")
    parser.add_argument("--engine2", required=True, help="Path to second engine")
    parser.add_argument("--openings", type=int, default=None,
                        help="Number of openings to use (default: all)")
    parser.add_argument("--depth1", type=int, default=None,
                        help="Search depth for engine 1 (default: 9 if no time specified)")
    parser.add_argument("--depth2", type=int, default=None,
                        help="Search depth for engine 2 (default: 9 if no time specified)")
    parser.add_argument("--time", type=int, default=None,
                        help="Time limit in ms for BOTH engines (optional)")
    parser.add_argument("--time1", type=int, default=None,
                        help="Time limit in ms for engine 1 (overrides --time)")
    parser.add_argument("--time2", type=int, default=None,
                        help="Time limit in ms for engine 2 (overrides --time)")
    parser.add_argument("--movetime", action="store_true",
                        help="Use 'movetime' for BOTH engines instead of 'wtime/btime'")
    parser.add_argument("--movetime1", action="store_true", default=None,
                        help="Use 'movetime' for engine 1 (overrides --movetime)")
    parser.add_argument("--movetime2", action="store_true", default=None,
                        help="Use 'movetime' for engine 2 (overrides --movetime)")
    args = parser.parse_args()
    
    # Handle --time shorthand for both engines
    time1 = args.time1 if args.time1 is not None else args.time
    time2 = args.time2 if args.time2 is not None else args.time
    
    # If no depth specified and no time specified, default to depth 9
    depth1 = args.depth1
    depth2 = args.depth2
    if depth1 is None and time1 is None:
        depth1 = 9
    if depth2 is None and time2 is None:
        depth2 = 9
    
    # Verify engines exist
    for engine, name in [(args.engine1, "engine1"), (args.engine2, "engine2")]:
        if not os.path.exists(engine):
            print(f"Error: {name} not found at {engine}")
            sys.exit(1)
    
    runner = TournamentRunner(
        engine1_path=args.engine1,
        engine2_path=args.engine2,
        depth1=depth1,
        depth2=depth2,
        time1=time1,
        time2=time2,
        use_movetime=args.movetime,
        use_movetime1=args.movetime1,
        use_movetime2=args.movetime2
    )
    
    runner.run_tournament(max_openings=args.openings)


if __name__ == "__main__":
    main()
