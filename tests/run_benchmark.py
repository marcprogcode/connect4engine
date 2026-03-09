"""
Connect 4 Benchmark Runner

Runs objective tests on the Connect 4 engine:
1. Solver test - Checks if engine suggests the Best Move (compared to solved database)
2. Speed test - Measures nodes per second (NPS)

Usage:
    python run_benchmark.py --engine <path> --test <solver|speed|all>
"""

import argparse
import csv
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from engine_wrapper import EngineWrapper, SearchInfo


@dataclass
class SolverResult:
    """Result of a solver test for a single position."""
    position: str
    expected_moves: List[str] 
    engine_move: str         
    passed: bool
    time_ms: float
    depth: int = 0            


@dataclass
class SpeedResult:
    """Result of a speed benchmark."""
    position: str
    depth: int
    nodes: int
    time_ms: float
    nps: float 


class BenchmarkRunner:
    """Runs benchmarks on a Connect 4 engine."""
    
    def __init__(self, engine_path: str):
        self.engine_path = engine_path
        self.datasets_dir = Path(__file__).parent / "datasets"
        self.test_file_name = "solved.txt" 
        
    def load_test_positions(self) -> List[Tuple[str, List[str]]]:
        """
        Load test positions with expected BEST MOVES.
        Expected format: "sequence - move1 move2"
        Example: "3344 - 3 4"
        """
        positions = []
        positions_file = self.datasets_dir / self.test_file_name
        
        if not positions_file.exists():
            positions_file = self.datasets_dir / "test_positions.txt"

        if not positions_file.exists():
            print(f"Warning: Test positions file not found at: {positions_file}")
            return positions
        
        print(f"Loading positions from: {positions_file.name}")
        
        with open(positions_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Check for format "Sequence - Move(s)"
                if '-' in line:
                    parts = line.split('-')
                    sequence = parts[0].strip()
                    moves_str = parts[1].strip()
                    # Split moves by space (e.g., "3 4" -> ["3", "4"])
                    valid_moves = moves_str.split()
                    
                    # Clean up sequence (remove "1. " etc if present from file numbering)
                    if ". " in sequence:
                        sequence = sequence.split(". ")[1]

                    if sequence and valid_moves:
                        positions.append((sequence, valid_moves))
        
        return positions
    
    def run_solver_test(self, time_ms: int = 2000, max_positions: int = 100, depth: Optional[int] = None, use_movetime: bool = True) -> List[SolverResult]:
        """
        Run solver tests - Check if engine suggests the CORRECT MOVE.
        
        Args:
            time_ms: Time per position in milliseconds
            max_positions: Maximum number of positions to test
            depth: Search depth limit (None = no limit)
            use_movetime: If True, use 'movetime' for exact time control (recommended)
                         If False, use 'wtime/btime' (engine may use only ~3% of time)
        """
        print("\n" + "=" * 60)
        time_mode = "movetime" if use_movetime else "wtime/btime"
        print(f"SOLVER TEST - Best Move Matching (Depth {depth}, {time_mode})")
        print("=" * 60)
        
        positions = self.load_test_positions()
        results = []
        
        if not positions:
            print("No test positions found!")
            return results
        
        if len(positions) > max_positions:
            positions = positions[:max_positions]
            print(f"\nTesting {max_positions} of {len(positions)} positions")
        
        try:
            with EngineWrapper(self.engine_path) as engine:
                for i, (sequence, valid_moves) in enumerate(positions):
                    
                    # Display truncated sequence
                    pos_display = sequence if len(sequence) < 25 else sequence[:22] + "..."
                    
                    print(f"\n[{i+1}/{len(positions)}] Seq: {pos_display}")
                    print(f"  Allowed Moves: {', '.join(valid_moves)}")
                    
                    engine.set_position(sequence)
                    
                    start_time = time.time()
                    # We expect info to contain .bestmove
                    info = engine.go(time_ms=time_ms, depth=depth, use_movetime=use_movetime) 
                    elapsed_ms = (time.time() - start_time) * 1000
                    
                    # Ensure engine_move is a string for comparison
                    engine_move = str(info.bestmove)
                    
                    # CHECK: Is the engine's move in the list of valid moves?
                    passed = engine_move in valid_moves
                    status = "✓ MATCH" if passed else "✗ FAIL"
                    
                    print(f"  Engine Move:   {engine_move}  {status}  (depth={info.depth}, {elapsed_ms:.0f}ms)")
                    
                    # WARNING: Depth 42 means the engine fully solved the position
                    # If it still got the move wrong, that's a critical bug
                    if info.depth == 42 and not passed:
                        print(f"  ⚠️  WARNING: Engine reached depth 42 (fully solved) but chose wrong move!")
                    
                    results.append(SolverResult(
                        position=sequence,
                        expected_moves=valid_moves,
                        engine_move=engine_move,
                        passed=passed,
                        time_ms=elapsed_ms,
                        depth=info.depth
                    ))
                    
        except Exception as e:
            print(f"\nError during solver test: {e}")
            import traceback
            traceback.print_exc()
        
        # Summary
        if results:
            passed_count = sum(1 for r in results if r.passed)
            total = len(results)
            percentage = (passed_count / total) * 100 if total > 0 else 0
            
            # Timing statistics
            times = [r.time_ms for r in results]
            avg_time = sum(times) / len(times) if times else 0
            min_time = min(times) if times else 0
            max_time = max(times) if times else 0
            
            print(f"\n{'=' * 60}")
            print(f"SOLVER SUMMARY: {passed_count}/{total} correct ({percentage:.1f}%)")
            print(f"Timing: avg={avg_time:.0f}ms, min={min_time:.0f}ms, max={max_time:.0f}ms")
            print("=" * 60)
            
            # Check for critical depth-42 failures
            depth42_failures = [r for r in results if r.depth == 42 and not r.passed]
            if depth42_failures:
                print(f"\n{'!' * 60}")
                print(f"⚠️  CRITICAL: {len(depth42_failures)} position(s) FAILED at depth 42!")
                print("The engine fully solved these positions but chose the wrong move.")
                print("This indicates a bug in move selection or score evaluation.")
                print("!" * 60)
                for r in depth42_failures:
                    print(f"  Seq: {r.position[:20]}... | Engine: {r.engine_move} | Valid: {r.expected_moves}")
            
            # Print details of failures
            failures = [r for r in results if not r.passed]
            if failures:
                print("\nFailed Positions:")
                for r in failures[:10]: # Show first 10 failures
                    print(f"  Seq: {r.position[:15]}... | Engine: {r.engine_move} | Valid: {r.expected_moves}")
                if len(failures) > 10:
                    print(f"  ... and {len(failures)-10} more.")

        return results
    
    def run_speed_test(self, depth: int = 12) -> List[SpeedResult]:
        """Run speed benchmark - measure NPS at fixed depth."""
        print("\n" + "=" * 60)
        print(f"SPEED TEST - Nodes Per Second (Depth {depth})")
        print("=" * 60)
        
        test_positions = ["", "44", "443355", "4433552266"]
        results = []
        
        try:
            with EngineWrapper(self.engine_path) as engine:
                for pos in test_positions:
                    pos_display = pos if pos else "(empty)"
                    print(f"\nPosition: {pos_display}")
                    
                    engine.set_position(pos)
                    start_time = time.time()
                    info = engine.go(depth=depth, time_ms=0)
                    elapsed_ms = (time.time() - start_time) * 1000
                    
                    nps = (info.nodes / elapsed_ms * 1000) if elapsed_ms > 0 and info.nodes > 0 else 0
                    
                    print(f"  Nodes:    {info.nodes:,}")
                    print(f"  Time:     {elapsed_ms:.1f}ms")
                    print(f"  NPS:      {nps:,.0f}")
                    
                    results.append(SpeedResult(
                        position=pos,
                        depth=depth,
                        nodes=info.nodes,
                        time_ms=elapsed_ms,
                        nps=nps
                    ))
                    
        except Exception as e:
            print(f"\nError during speed test: {e}")
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Connect 4 Engine Benchmark Runner")
    parser.add_argument("--engine", required=True, help="Path to engine executable")
    parser.add_argument("--test", choices=["solver", "speed", "all"], 
                        default="all", help="Test type to run")
    parser.add_argument("--depth", type=int, default=None, 
                        help="Max depth for tests (default: 8 for speed, None for solver)")
    parser.add_argument("--time", type=int, default=2000,
                        help="Time per position in ms for solver test")
    parser.add_argument("--positions", type=int, default=100,
                        help="Max positions for solver test")
    parser.add_argument("--movetime", action="store_true", default=True,
                        help="Use 'movetime' for exact time control (default: True)")
    parser.add_argument("--no-movetime", dest="movetime", action="store_false",
                        help="Use 'wtime/btime' instead (engine uses time management, ~5%% of time)")
    parser.add_argument("--speed-depth", type=int, default=None,
                        help="Depth for speed test (default: 11, or --depth if specified)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.engine):
        print(f"Error: Engine not found at {args.engine}")
        sys.exit(1)
    
    runner = BenchmarkRunner(args.engine)
    
    print(f"\nConnect 4 Engine Benchmark")
    print(f"Engine: {args.engine}")
    
    print(f"Test:   {args.test}")
    
    if args.test in ["solver", "all"]:
        # For solver test: if --depth not specified, use time-only mode (no depth limit)
        # Use movetime by default for exact time control
        runner.run_solver_test(time_ms=args.time, max_positions=args.positions, depth=args.depth, use_movetime=args.movetime)
    
    if args.test in ["speed", "all"]:
        # Use --speed-depth if provided, else --depth if provided, else default 11
        speed_depth = args.speed_depth if args.speed_depth else (args.depth if args.depth else 11)
        runner.run_speed_test(depth=speed_depth)
    
    print("\nBenchmark complete!")


if __name__ == "__main__":
    main()