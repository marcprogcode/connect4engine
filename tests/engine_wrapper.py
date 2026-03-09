"""
Connect 4 Engine Wrapper

Provides a Python interface to communicate with the Connect 4 engine
via subprocess STDIN/STDOUT using the UCI-like protocol.

Expected engine commands:
    position [moves]          - Set board position (e.g., "position 4453")
    go wtime [ms] btime [ms]  - Start thinking with time control
    go depth [d]              - Search to specific depth  
    quit                      - Exit the engine

Expected engine responses:
    info depth [d] score [cp] nodes [n] time [ms]  - Search info
    bestmove [col]                                 - Best move (1-7)
"""

import subprocess
import time
from typing import Optional
from dataclasses import dataclass


@dataclass
class SearchInfo:
    """Search statistics from the engine."""
    depth: int = 0
    score: int = 0
    nodes: int = 0
    time_ms: int = 0
    bestmove: Optional[int] = None


class EngineWrapper:
    """
    Wrapper class to communicate with the Connect 4 engine via subprocess.
    
    Usage:
        engine = EngineWrapper("./bin/engine.exe")
        engine.set_position("4453")  # Play moves: col4, col4, col5, col3
        result = engine.go(time_ms=1000)
        print(f"Best move: column {result.bestmove}")
        engine.close()
    """
    
    def __init__(self, executable_path: str):
        """
        Initialize the engine wrapper.
        
        Args:
            executable_path: Path to the engine executable
        """
        self.executable_path = executable_path
        self.process: Optional[subprocess.Popen] = None
        self._start_engine()
    
    def _start_engine(self) -> None:
        """Start the engine subprocess."""
        try:
            self.process = subprocess.Popen(
                self.executable_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
        except FileNotFoundError:
            raise FileNotFoundError(f"Engine not found at: {self.executable_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to start engine: {e}")
    
    def send_command(self, cmd: str) -> None:
        """
        Send a command to the engine.
        
        Args:
            cmd: Command string to send
        """
        if self.process is None or self.process.poll() is not None:
            raise RuntimeError("Engine process is not running")
        
        self.process.stdin.write(f"{cmd}\n")
        self.process.stdin.flush()
    
    def read_line(self, timeout: float = 5.0) -> Optional[str]:
        """
        Read a line from the engine output.
        
        Args:
            timeout: Maximum time to wait for response (seconds)
            
        Returns:
            Response line or None if timeout
        """
        if self.process is None:
            return None
        
        import select
        import sys
        
        if sys.platform == 'win32':
            try:
                line = self.process.stdout.readline()
                return line.strip() if line else None
            except Exception:
                return None
        else:
            ready, _, _ = select.select([self.process.stdout], [], [], timeout)
            if ready:
                line = self.process.stdout.readline()
                return line.strip() if line else None
            return None
    
    def set_position(self, moves: str = "") -> None:
        """
        Set the board position.
        
        Args:
            moves: Sequence of column numbers (1-7), e.g., "4453"
                   Empty string for starting position.
        """
        if moves:
            self.send_command(f"position {moves}")
        else:
            self.send_command("position")
    
    def go(self, time_ms: int = 1000, depth: Optional[int] = None, use_movetime: bool = False) -> SearchInfo:
        """
        Start the engine search.
        
        Args:
            time_ms: Think time in milliseconds
            depth: Search depth (if specified with time_ms, uses whichever finishes first)
            use_movetime: If True, use 'movetime' command (exact time per move)
                          If False, use 'wtime/btime' (clock time - engine applies
                          time management and may use only a fraction of specified time,
                          typically ~3% for this engine)
            
        Returns:
            SearchInfo with search results including bestmove
        
        Note:
            For benchmarks and tests where you want the engine to think for the
            full specified time, use use_movetime=True. For game simulations
            where the engine should manage its own time budget, use wtime/btime.
        """
        # Build go command based on parameters
        if depth is not None and time_ms > 0 and not use_movetime:
            # Combined: depth limit AND time limit (whichever first)
            self.send_command(f"go depth {depth} wtime {time_ms} btime {time_ms}")
        elif depth is not None and time_ms <= 0:
            # Depth only
            self.send_command(f"go depth {depth}")
        elif use_movetime:
            # Explicit movetime (cleaner for fixed time per move)
            if depth is not None:
                self.send_command(f"go depth {depth} movetime {time_ms}")
            else:
                self.send_command(f"go movetime {time_ms}")
        else:
            # Time only (wtime/btime format)
            self.send_command(f"go wtime {time_ms} btime {time_ms}")
        
        info = SearchInfo()
        
        # Read until we get bestmove
        while True:
            line = self.read_line(timeout=30.0)  # Allow up to 30s for deep searches
            if line is None:
                break
            
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        info.bestmove = int(parts[1])
                    except ValueError:
                        pass
                break
            
            elif line.startswith("info"):
                # Parse info line: info depth X score Y nodes Z time T
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "depth" and i + 1 < len(parts):
                        try:
                            info.depth = int(parts[i + 1])
                        except ValueError:
                            pass
                    elif part == "score" and i + 1 < len(parts):
                        try:
                            info.score = int(parts[i + 1])
                        except ValueError:
                            pass
                    elif part == "nodes" and i + 1 < len(parts):
                        try:
                            info.nodes = int(parts[i + 1])
                        except ValueError:
                            pass
                    elif part == "time" and i + 1 < len(parts):
                        try:
                            info.time_ms = int(parts[i + 1])
                        except ValueError:
                            pass
        
        
        return info
        """Check if the engine process is still running."""
        return self.process is not None and self.process.poll() is None
    
    def close(self) -> None:
        """Close the engine subprocess."""
        if self.process is not None:
            try:
                self.send_command("quit")
                self.process.wait(timeout=2.0)
            except Exception:
                pass
            finally:
                if self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                self.process = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def test_engine_wrapper():
    """Simple test to verify the wrapper works."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python engine_wrapper.py <engine_path>")
        print("Example: python engine_wrapper.py ../bin/connect4_uci.exe")
        return
    
    engine_path = sys.argv[1]
    
    print(f"Testing engine: {engine_path}")
    
    try:
        with EngineWrapper(engine_path) as engine:
            print("✓ Engine started successfully")
            
            # Test position setting
            engine.set_position("44")
            print("✓ Position set: 44")
            
            # Test search
            result = engine.go(time_ms=1000)
            print(f"✓ Search complete: bestmove={result.bestmove}, depth={result.depth}")
            
            print("\nAll tests passed!")
            
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    test_engine_wrapper()
