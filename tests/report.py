import os
import sys
import glob
import subprocess
import re
import time
import argparse
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# Configuration
TESTS_DIR = Path(__file__).parent
ENGINES_DIR = TESTS_DIR.parent / "engines"
IMAGES_DIR = ENGINES_DIR / "images"
REPORT_FILE = ENGINES_DIR / "engines.md"
LOGS_DIR = ENGINES_DIR / "logs"

# Time control configuration
# v7+ engines use wtime/btime with internal time management (~3% of clock time)
# v1-v6 engines use movetime (exact time per move)
# To make comparisons fair, we give older engines the effective time that newer engines use
BASE_TIME_MS = 250                    # Base time budget for v7+ engines (wtime/btime)
TIME_MANAGEMENT_PERCENT = 3           # v7+ uses ~3% of clock time per move
EFFECTIVE_TIME_MS = int(BASE_TIME_MS * TIME_MANAGEMENT_PERCENT / 100)  # 7.5ms for older engines
MIN_WTIME_VERSION = 7                 # First version with wtime/btime support
MIN_TIME_VERSION = 6                  # First version with any time-based search
SPEED_TEST_DEPTH = 13                 # Consistent depth for speed test

# Ensure directories exist
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Generate log filename
LOG_FILENAME = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
LOG_FILE_PATH = LOGS_DIR / LOG_FILENAME

# Unique separator for new entries
LOG_SEPARATOR = "|||REPORT_LOG_ENTRY_SEPARATOR|||"

# Style configuration for matplotlib
plt.style.use('seaborn-v0_8-darkgrid')
COLORS = ['#3498db', '#2ecc71', '#e74c3c', '#9b59b6', '#f39c12', '#1abc9c', '#e67e22', '#34495e']

# TODO: Fix perft comparison
@dataclass
class PerftDetail:
    """Per-depth perft result."""
    depth: int
    expected: int
    actual: int
    passed: bool
    time_ms: float

@dataclass
class SpeedDetail:
    """Per-position speed result."""
    position: str
    nodes: int
    time_ms: float
    nps: float

@dataclass
class TimingStats:
    """Timing statistics."""
    avg_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0

@dataclass
class BenchmarkResult:
    """Benchmark result with detailed metrics."""
    name: str
    nps: int = 0
    solver_accuracy: float = 0.0
    perft_passed: bool = False
    perft_details: List[PerftDetail] = field(default_factory=list)
    solver_timing: TimingStats = field(default_factory=TimingStats)
    solver_failures: int = 0
    solver_total: int = 0
    speed_details: List[SpeedDetail] = field(default_factory=list)
    total_nodes: int = 0
    solver_avg_depth: float = 0.0

@dataclass
class TournamentResult:
    """Tournament result."""
    p1: str
    p2: str
    winrate: float = 0.0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    total_games: int = 0
    elo_diff: Optional[float] = None

def log_test_output(title, output):
    """Append test output to log file."""
    with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
        f.write(f"\n{LOG_SEPARATOR}\n")
        f.write(f"TITLE: {title}\n")
        f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n")
        f.write(f"{'-'*60}\n")
        f.write(output)
        f.write("\n")

def get_sorted_engines():
    """Find and sort engine executables by version number prefix."""
    files = list(ENGINES_DIR.glob("*.exe"))
    engines = []
    for f in files:
        match = re.match(r"(\d+)_", f.name)
        if match:
            version = int(match.group(1))
            engines.append((version, f))
    engines.sort(key=lambda x: x[0])
    return [e[1] for e in engines]

def get_engine_version(engine_path):
    """Extract major version from filename."""
    match = re.search(r"^(\d+)_", engine_path.name)
    if match:
        return int(match.group(1))
    return 0

def parse_benchmark_output(engine_name: str, output: str) -> BenchmarkResult:
    """Parse output from run_benchmark.py with detail extraction."""
    result = BenchmarkResult(name=engine_name)
    
    # NPS
    nps_match = re.search(r"NPS:\s+([\d,]+)", output)
    if nps_match:
        result.nps = int(nps_match.group(1).replace(",", ""))
    
    # Solver Accuracy
    solver_match = re.search(r"SOLVER SUMMARY: (\d+)/(\d+) correct \(([\d.]+)%\)", output)
    if solver_match:
        passed = int(solver_match.group(1))
        total = int(solver_match.group(2))
        result.solver_accuracy = float(solver_match.group(3))
        result.solver_total = total
        result.solver_failures = total - passed
    
    # Solver Timing
    timing_match = re.search(r"Timing: avg=(\d+)ms, min=(\d+)ms, max=(\d+)ms", output)
    if timing_match:
        result.solver_timing = TimingStats(
            avg_ms=float(timing_match.group(1)),
            min_ms=float(timing_match.group(2)),
            max_ms=float(timing_match.group(3))
        )
    
    # Perft Details
    result.perft_passed = "PERFT SUMMARY:" in output and "FAIL" not in output.split("PERFT SUMMARY:")[1].split("\n")[0] if "PERFT SUMMARY:" in output else False
    
    # Parse per-depth perft results
    perft_pattern = r"Testing depth (\d+)\.\.\.\s*(✓ PASS|✗ FAIL)\s*Expected:\s*([\d,]+)\s*Actual:\s*([\d,]+)\s*Time:\s*([\d.]+)ms"
    for match in re.finditer(perft_pattern, output):
        detail = PerftDetail(
            depth=int(match.group(1)),
            passed="PASS" in match.group(2),
            expected=int(match.group(3).replace(",", "")),
            actual=int(match.group(4).replace(",", "")),
            time_ms=float(match.group(5))
        )
        result.perft_details.append(detail)
    
    # Speed Details
    speed_pattern = r"Position: (.+?)\s*Nodes:\s*([\d,]+)\s*Time:\s*([\d.]+)ms\s*NPS:\s*([\d,]+)"
    total_nodes = 0
    for match in re.finditer(speed_pattern, output):
        pos = match.group(1).strip()
        nodes = int(match.group(2).replace(",", ""))
        total_nodes += nodes
        detail = SpeedDetail(
            position=pos,
            nodes=nodes,
            time_ms=float(match.group(3)),
            nps=float(match.group(4).replace(",", ""))
        )
        result.speed_details.append(detail)
    result.total_nodes = total_nodes
    
    # Solver Depths
    depth_pattern = r"depth=(\d+),"
    depths = [int(m.group(1)) for m in re.finditer(depth_pattern, output)]
    if depths:
        result.solver_avg_depth = sum(depths) / len(depths)
    
    return result

def parse_tournament_output(engine1_name: str, engine2_name: str, output: str) -> TournamentResult:
    """Parse output from run_tournament.py with detail extraction."""
    result = TournamentResult(p1=engine1_name, p2=engine2_name)
    
    # Win Rate
    winrate_match = re.search(rf"{re.escape(engine1_name)} win rate: ([\d.]+)%", output)
    if winrate_match:
        result.winrate = float(winrate_match.group(1))
    
    # Wins/Losses/Draws
    wins_match = re.search(rf"{re.escape(engine1_name)}: (\d+) wins", output)
    if wins_match:
        result.wins = int(wins_match.group(1))
    
    losses_match = re.search(rf"{re.escape(engine2_name)}: (\d+) wins", output)
    if losses_match:
        result.losses = int(losses_match.group(1))
    
    draws_match = re.search(r"Draws: (\d+)", output)
    if draws_match:
        result.draws = int(draws_match.group(1))
    
    total_match = re.search(r"Total games: (\d+)", output)
    if total_match:
        result.total_games = int(total_match.group(1))
    
    # Elo Difference
    elo_match = re.search(r"Estimated Elo difference: ([+-]?\d+)", output)
    if elo_match:
        result.elo_diff = float(elo_match.group(1))
    
    return result

def run_benchmark(engine_path) -> Optional[BenchmarkResult]:
    """Run benchmark script and parse output.
    
    Time control strategy:
    - v7+: Uses wtime/btime
    - v6:  Uses movetime with effective time
    - v1-v5: Uses depth-only search
    """
    print(f"Benchmarking {engine_path.name}...")
    
    version = get_engine_version(engine_path)
    
    cmd = [
        sys.executable, 
        str(TESTS_DIR / "run_benchmark.py"),
        "--engine", str(engine_path),
        "--test", "all",
        "--positions", "100"
    ]
    
    if version >= MIN_WTIME_VERSION:
        # v7+: Use wtime/btime
        cmd.extend(["--time", str(BASE_TIME_MS), "--no-movetime", "--speed-depth", str(SPEED_TEST_DEPTH)])
        print(f"  -> Using wtime/btime {BASE_TIME_MS}ms")
    elif version >= MIN_TIME_VERSION:
        # v6: Has time-based search but no wtime support, use movetime
        cmd.extend(["--time", str(EFFECTIVE_TIME_MS), "--speed-depth", str(SPEED_TEST_DEPTH)])
        print(f"  -> Using movetime {EFFECTIVE_TIME_MS}ms (matching v7+ effective time)")
    else:
        # v1-v5: Depth-only search
        cmd.extend(["--depth", "7", "--speed-depth", str(SPEED_TEST_DEPTH)])
        print(f"  -> Using depth 7 (no time control)")
    
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    start_time = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', env=env)
        elapsed = time.time() - start_time
        output = result.stdout
        log_test_output(f"BENCHMARK: {engine_path.name}", output)
        print(f"  ✓ Completed in {elapsed:.1f}s")
        return parse_benchmark_output(engine_path.stem, output)
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"  ✗ Error after {elapsed:.1f}s: {e}")
        return None

def run_tournament(engine1, engine2) -> Optional[TournamentResult]:
    """Run head-to-head tournament.
    
    Time control strategy (same as benchmarks for fairness):
    - v7+: Uses wtime/btime
    - v6:  Uses movetime with effective time
    - v1-v5: Uses depth-only
    """
    print(f"Tournament: {engine1.name} vs {engine2.name}...")
    
    v1 = get_engine_version(engine1)
    v2 = get_engine_version(engine2)
    
    cmd = [
        sys.executable,
        str(TESTS_DIR / "run_tournament.py"),
        "--engine1", str(engine1),
        "--engine2", str(engine2),
        "--openings", "100", 
    ]
    
    # Configure engine 1
    if v1 >= MIN_WTIME_VERSION:
        cmd.extend(["--time1", str(BASE_TIME_MS)])
    elif v1 >= MIN_TIME_VERSION:
        cmd.extend(["--time1", str(EFFECTIVE_TIME_MS), "--movetime1"])
    else:
        cmd.extend(["--depth1", "7"])
        
    # Configure engine 2
    if v2 >= MIN_WTIME_VERSION:
        cmd.extend(["--time2", str(BASE_TIME_MS)])
    elif v2 >= MIN_TIME_VERSION:
        cmd.extend(["--time2", str(EFFECTIVE_TIME_MS), "--movetime2"])
    else:
        cmd.extend(["--depth2", "7"])
    
    start_time = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        elapsed = time.time() - start_time
        output = result.stdout
        log_test_output(f"TOURNAMENT: {engine1.name} vs {engine2.name}", output)
        print(f"  ✓ Completed in {elapsed:.1f}s")
        return parse_tournament_output(engine1.stem, engine2.stem, output)
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"  ✗ Error after {elapsed:.1f}s: {e}")
        return None

def parse_log_file(log_path: str) -> Tuple[List[BenchmarkResult], List[TournamentResult]]:
    """Parse results directly from a log file."""
    print(f"Parsing log file: {log_path}")
    
    with open(log_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    benchmarks = {}
    tournaments = {}
    sections = []
    
    # Try splitting by new unique separator
    if LOG_SEPARATOR in content:
        print("Detected new log format.")
        raw_sections = [s for s in content.split(LOG_SEPARATOR) if s.strip()]
        for s in raw_sections:
            lines = s.strip().split('\n')
            if not lines: continue
            if lines[0].startswith("TITLE: "):
                title = lines[0][7:].strip()
                body_start = 0
                for i, line in enumerate(lines):
                    if line.startswith("---------"):
                        body_start = i + 1
                        break
                if body_start < len(lines):
                    body = '\n'.join(lines[body_start:])
                    sections.append((title, body))
    else:
        print("Detected legacy log format. Using regex parsing.")
        pattern = r"={60}\s*\n(.*?)\nTimestamp:.*?\n={60}\s*\n"
        matches = list(re.finditer(pattern, content))
        for i, match in enumerate(matches):
            title = match.group(1).strip()
            start_pos = match.end()
            if i + 1 < len(matches):
                end_pos = matches[i+1].start()
            else:
                end_pos = len(content)
            body = content[start_pos:end_pos].strip()
            sections.append((title, body))

    print(f"Found {len(sections)} log entries.")
    
    for title, body in sections:
        bench_match = re.search(r"BENCHMARK: (.+)", title)
        if bench_match:
            engine_filename = bench_match.group(1).strip()
            engine_name = Path(engine_filename).stem
            res = parse_benchmark_output(engine_name, body)
            benchmarks[engine_name] = res
            continue
            
        tourney_match = re.search(r"TOURNAMENT: (.+) vs (.+)", title)
        if tourney_match:
            engine1_name = Path(tourney_match.group(1).strip()).stem
            engine2_name = Path(tourney_match.group(2).strip()).stem
            res = parse_tournament_output(engine1_name, engine2_name, body)
            tournaments[(engine1_name, engine2_name)] = res
            continue
            
    benchmark_results = sorted(benchmarks.values(), key=lambda x: x.name)
    tournament_results = sorted(tournaments.values(), key=lambda x: (x.p1, x.p2))
    
    return benchmark_results, tournament_results

def generate_graphs(benchmark_results: List[BenchmarkResult], tournament_results: List[TournamentResult]):
    """Generate all visualizations."""
    
    names = [r.name for r in benchmark_results]
    short_names = [n.split('_')[0] if '_' in n else n for n in names]
    
    # NPS Comparison
    nps_values = [r.nps for r in benchmark_results]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(short_names, nps_values, color=COLORS[:len(names)], edgecolor='white', linewidth=1.2)
    ax.set_title('Engine Speed (Nodes Per Second)', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('Engine Version', fontsize=11)
    ax.set_ylabel('NPS', fontsize=11)
    ax.set_xticks(range(len(short_names)))
    ax.set_xticklabels(short_names, rotation=45, ha='right')
    
    # Add value labels
    for bar, val in zip(bars, nps_values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                   f'{val/1e6:.1f}M' if val >= 1e6 else f'{val/1e3:.0f}K',
                   ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(IMAGES_DIR / "nps_comparison.png", dpi=150, bbox_inches='tight')
    plt.close()
    
    # Solver Accuracy
    accuracies = [r.solver_accuracy for r in benchmark_results]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(short_names, accuracies, marker='o', markersize=10, linewidth=2.5, color='#27ae60')
    ax.fill_between(short_names, accuracies, alpha=0.3, color='#27ae60')
    ax.set_title('Solver Test Accuracy', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('Engine Version', fontsize=11)
    ax.set_ylabel('Accuracy (%)', fontsize=11)
    ax.set_ylim(0, 105)
    ax.axhline(y=100, color='#2ecc71', linestyle='--', alpha=0.5, linewidth=1)
    
    for i, (name, acc) in enumerate(zip(short_names, accuracies)):
        ax.annotate(f'{acc:.1f}%', (i, acc), textcoords="offset points", 
                   xytext=(0, 10), ha='center', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(IMAGES_DIR / "solver_accuracy.png", dpi=150, bbox_inches='tight')
    plt.close()

    # Win Rate Progression
    if tournament_results:
        labels = [f"v{r.p1.split('_')[0]} vs v{r.p2.split('_')[0]}" for r in tournament_results]
        rates = [r.winrate for r in tournament_results]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        colors_win = ['#27ae60' if r > 50 else '#e74c3c' if r < 50 else '#95a5a6' for r in rates]
        bars = ax.bar(labels, rates, color=colors_win, edgecolor='white', linewidth=1.2)
        ax.axhline(y=50, color='#7f8c8d', linestyle='--', alpha=0.7, linewidth=1.5)
        ax.set_title('Win Rate vs Previous Version', fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel('Matchup', fontsize=11)
        ax.set_ylabel('Win Rate (%)', fontsize=11)
        ax.set_ylim(0, 100)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        
        for bar, rate in zip(bars, rates):
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2,
                   f'{rate:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
                    
        plt.tight_layout()
        plt.savefig(IMAGES_DIR / "winrates.png", dpi=150, bbox_inches='tight')
        plt.close()

    # Total Nodes Comparison
    total_nodes = [r.total_nodes for r in benchmark_results]
    
    if any(n > 0 for n in total_nodes):
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.bar(short_names, total_nodes, color=COLORS[:len(names)], edgecolor='white', linewidth=1.2)
        ax.set_title('Total Nodes Searched (Speed Test)', fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel('Engine Version', fontsize=11)
        ax.set_ylabel('Nodes', fontsize=11)
        ax.set_xticks(range(len(short_names)))
        ax.set_xticklabels(short_names, rotation=45, ha='right')
        
        for bar, val in zip(bars, total_nodes):
            if val > 0:
                label = f'{val/1e9:.2f}B' if val >= 1e9 else f'{val/1e6:.1f}M' if val >= 1e6 else f'{val/1e3:.0f}K'
                ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                       label, ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(IMAGES_DIR / "nodes_comparison.png", dpi=150, bbox_inches='tight')
        plt.close()

    # Solver Timing Comparison
    avg_times = [r.solver_timing.avg_ms for r in benchmark_results]
    min_times = [r.solver_timing.min_ms for r in benchmark_results]
    max_times = [r.solver_timing.max_ms for r in benchmark_results]
    
    if any(t > 0 for t in avg_times):
        fig, ax = plt.subplots(figsize=(12, 6))
        x = np.arange(len(short_names))
        width = 0.25
        
        ax.bar(x - width, min_times, width, label='Min', color='#3498db', edgecolor='white')
        ax.bar(x, avg_times, width, label='Average', color='#2ecc71', edgecolor='white')
        ax.bar(x + width, max_times, width, label='Max', color='#e74c3c', edgecolor='white')
        
        ax.set_title('Solver Test Timing', fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel('Engine Version', fontsize=11)
        ax.set_ylabel('Time (ms)', fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels(short_names, rotation=45, ha='right')
        ax.legend()
        
        plt.tight_layout()
        plt.savefig(IMAGES_DIR / "solver_timing.png", dpi=150, bbox_inches='tight')
        plt.close()

    # Elo Progression
    if tournament_results and any(r.elo_diff is not None for r in tournament_results):
        cumulative_elo = [0]
        elo_labels = [short_names[0]]
        
        for r in tournament_results:
            elo_diff = r.elo_diff if r.elo_diff is not None else 0
            cumulative_elo.append(cumulative_elo[-1] + elo_diff)
            p1_short = r.p1.split('_')[0]
            elo_labels.append(p1_short)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(elo_labels, cumulative_elo, marker='o', markersize=10, linewidth=2.5, color='#9b59b6')
        ax.fill_between(elo_labels, cumulative_elo, alpha=0.3, color='#9b59b6')
        ax.axhline(y=0, color='#7f8c8d', linestyle='--', alpha=0.5)
        ax.set_title('Cumulative Elo Rating (vs Version 1)', fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel('Engine Version', fontsize=11)
        ax.set_ylabel('Elo Rating', fontsize=11)
        
        for i, (name, elo) in enumerate(zip(elo_labels, cumulative_elo)):
            ax.annotate(f'{elo:+.0f}', (i, elo), textcoords="offset points", 
                       xytext=(0, 10), ha='center', fontsize=9, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(IMAGES_DIR / "elo_progression.png", dpi=150, bbox_inches='tight')
        plt.close()

    # Combined Dashboard
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Top-left: NPS
    ax = axes[0, 0]
    ax.bar(short_names, nps_values, color=COLORS[:len(names)])
    ax.set_title('Speed (NPS)', fontweight='bold')
    ax.set_ylabel('NPS')
    ax.tick_params(axis='x', rotation=45)
    
    # Top-right: Accuracy
    ax = axes[0, 1]
    ax.plot(short_names, accuracies, marker='o', markersize=8, linewidth=2, color='#27ae60')
    ax.fill_between(short_names, accuracies, alpha=0.3, color='#27ae60')
    ax.set_title('Solver Accuracy', fontweight='bold')
    ax.set_ylabel('Accuracy (%)')
    ax.set_ylim(0, 105)
    ax.tick_params(axis='x', rotation=45)
    
    # Bottom-left: Nodes
    ax = axes[1, 0]
    ax.bar(short_names, total_nodes, color=COLORS[:len(names)])
    ax.set_title('Total Nodes', fontweight='bold')
    ax.set_ylabel('Nodes')
    ax.tick_params(axis='x', rotation=45)
    
    # Bottom-right: Win rates or Elo
    ax = axes[1, 1]
    if tournament_results:
        labels = [f"v{r.p1.split('_')[0]}" for r in tournament_results]
        rates = [r.winrate for r in tournament_results]
        colors_win = ['#27ae60' if r > 50 else '#e74c3c' for r in rates]
        ax.bar(labels, rates, color=colors_win)
        ax.axhline(y=50, color='gray', linestyle='--', alpha=0.7)
        ax.set_title('Win Rate vs Predecessor', fontweight='bold')
        ax.set_ylabel('Win Rate (%)')
        ax.set_ylim(0, 100)
    else:
        ax.text(0.5, 0.5, 'No tournament data', ha='center', va='center', transform=ax.transAxes)
        ax.set_title('Tournament Results', fontweight='bold')
    ax.tick_params(axis='x', rotation=45)
    
    plt.suptitle('Engine Evolution Dashboard', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(IMAGES_DIR / "dashboard.png", dpi=150, bbox_inches='tight')
    plt.close()

def write_report(benchmark_results: List[BenchmarkResult], tournament_results: List[TournamentResult]):
    """Write comprehensive markdown report."""
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("# Connect 4 Engine Evolution Report\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        
        # Executive Summary
        f.write("## Summary\n\n")
        
        if benchmark_results:
            best_nps = max(benchmark_results, key=lambda x: x.nps)
            best_acc = max(benchmark_results, key=lambda x: x.solver_accuracy)
            f.write(f"- **Fastest Engine**: {best_nps.name} ({best_nps.nps:,} NPS)\n")
            f.write(f"- **Most Accurate**: {best_acc.name} ({best_acc.solver_accuracy:.1f}%)\n")
            
            if tournament_results:
                total_elo = sum(r.elo_diff for r in tournament_results if r.elo_diff)
                f.write(f"- **Total Elo Gain**: {total_elo:+.0f} (v1 → latest)\n")
            f.write("\n")
        
        # Dashboard
        f.write("## Dashboard\n\n")
        f.write("![Dashboard](images/dashboard.png)\n\n")
        
        # Performance Summary Table
        f.write("## 1. Performance Summary\n\n")
        f.write("| Engine | NPS | Nodes | Solver Accuracy | Avg Depth | Avg Time | Perft |\n")
        f.write("| :--- | ---: | ---: | ---: | ---: | ---: | :---: |\n")
        for r in benchmark_results:
            perft_status = "✅" if r.perft_passed else "❌"
            nodes_str = f"{r.total_nodes:,}" if r.total_nodes > 0 else "N/A"
            depth_str = f"{r.solver_avg_depth:.1f}" if r.solver_avg_depth > 0 else "N/A"
            time_str = f"{r.solver_timing.avg_ms:.0f}ms" if r.solver_timing.avg_ms > 0 else "N/A"
            f.write(f"| {r.name} | {r.nps:,} | {nodes_str} | {r.solver_accuracy:.1f}% | {depth_str} | {time_str} | {perft_status} |\n")
        f.write("\n")
        
        # Visualizations
        f.write("## 2. Visualizations\n\n")
        
        f.write("### Speed Comparison\n")
        f.write("![NPS Comparison](images/nps_comparison.png)\n\n")
        
        f.write("### Nodes Searched\n")
        f.write("![Nodes Comparison](images/nodes_comparison.png)\n\n")
        
        f.write("### Accuracy Improvement\n")
        f.write("![Solver Accuracy](images/solver_accuracy.png)\n\n")
        
        f.write("### Solver Timing\n")
        f.write("![Solver Timing](images/solver_timing.png)\n\n")
        
        # Tournament Analysis
        f.write("## 3. Head-to-Head Progression\n\n")
        f.write("Each version was tested against its predecessor in 200-game matches (100 openings × 2 colors).\n\n")
        f.write("![Win Rates](images/winrates.png)\n\n")
        
        if tournament_results:
            f.write("### Match Results\n\n")
            f.write("| Matchup | Wins | Losses | Draws | Win Rate | Elo Δ |\n")
            f.write("| :--- | ---: | ---: | ---: | ---: | ---: |\n")
            for r in tournament_results:
                elo_str = f"{r.elo_diff:+.0f}" if r.elo_diff else "N/A"
                f.write(f"| **{r.p1}** vs {r.p2} | {r.wins} | {r.losses} | {r.draws} | {r.winrate:.1f}% | {elo_str} |\n")
            f.write("\n")
            
            # Elo progression graph
            if any(r.elo_diff is not None for r in tournament_results):
                f.write("### Elo Progression\n")
                f.write("![Elo Progression](images/elo_progression.png)\n\n")
        else:
            f.write("No tournament data available (need at least 2 engines).\n\n")
        
        # Detailed Solver Analysis
        f.write("## 4. Solver Analysis\n\n")
        f.write("### Timing Statistics\n\n")
        f.write("| Engine | Tested | Correct | Failed | Avg Depth | Min Time | Avg Time | Max Time |\n")
        f.write("| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n")
        for r in benchmark_results:
            correct = r.solver_total - r.solver_failures
            depth_str = f"{r.solver_avg_depth:.1f}" if r.solver_avg_depth > 0 else "N/A"
            f.write(f"| {r.name} | {r.solver_total} | {correct} | {r.solver_failures} | {depth_str} | ")
            f.write(f"{r.solver_timing.min_ms:.0f}ms | {r.solver_timing.avg_ms:.0f}ms | {r.solver_timing.max_ms:.0f}ms |\n")
        f.write("\n")
        
        # Speed Test Details
        f.write("## 5. Speed Test Details\n\n")
        
        # Get all unique positions
        all_positions = set()
        for r in benchmark_results:
            for detail in r.speed_details:
                all_positions.add(detail.position)
        
        if all_positions:
            positions = sorted(all_positions, key=lambda x: len(x))
            f.write("| Engine | " + " | ".join([p if p != "(empty)" else "Empty" for p in positions]) + " |\n")
            f.write("| :--- | " + " | ".join(["---:" for _ in positions]) + " |\n")
            
            for r in benchmark_results:
                pos_map = {d.position: d.nps for d in r.speed_details}
                row = [r.name]
                for pos in positions:
                    nps = pos_map.get(pos, 0)
                    row.append(f"{nps/1e6:.1f}M" if nps >= 1e6 else f"{nps/1e3:.0f}K" if nps > 0 else "N/A")
                f.write("| " + " | ".join(row) + " |\n")
            f.write("\n")
        
        # Footer
        f.write("---\n\n")
        f.write("*Generated by automated reporting script.*\n")

def main():
    parser = argparse.ArgumentParser(description="Generate engine report")
    parser.add_argument("--from-log", help="Generate report from existing log file instead of running tests")
    args = parser.parse_args()

    print("Starting Report Generation...")
    
    if args.from_log:
        if not os.path.exists(args.from_log):
            print(f"Error: Log file not found: {args.from_log}")
            return
        benchmark_results, tournament_results = parse_log_file(args.from_log)
    else:
        print(f"Logging to: {LOG_FILE_PATH}")
        engines = get_sorted_engines()
        if not engines:
            print("No engines found!")
            return
            
        print(f"Found {len(engines)} engines: {[e.name for e in engines]}")
        
        # 1. Benchmarks
        benchmark_results = []
        for engine in engines:
            res = run_benchmark(engine)
            if res:
                benchmark_results.append(res)
                
        # 2. Tournaments (Consecutive pairs)
        tournament_results = []
        for i in range(len(engines) - 1):
            res = run_tournament(engines[i+1], engines[i])
            if res:
                tournament_results.append(res)
            
    # 3. Generate Artifacts
    if benchmark_results:
        print("Generating graphs...")
        generate_graphs(benchmark_results, tournament_results)
        print("Writing report...")
        write_report(benchmark_results, tournament_results)
        print(f"\nReport generated at: {REPORT_FILE}")
    else:
        print("No results to report.")

if __name__ == "__main__":
    main()
