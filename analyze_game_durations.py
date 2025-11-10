#!/usr/bin/env python3
"""
Analyze game durations from recorded games
Calculates mean, median, mode, and range of tick counts
"""

import json
from pathlib import Path
from collections import Counter
import statistics

def count_game_ticks(game_file: Path) -> int:
    """Count number of ticks in a game JSONL file"""
    tick_count = 0
    with open(game_file, 'r') as f:
        for line in f:
            if line.strip():
                tick_count += 1
    return tick_count

def analyze_durations(recordings_dir: str = "/home/nomad/rugs_recordings"):
    """Analyze all game durations and compute statistics"""
    recordings_path = Path(recordings_dir)

    if not recordings_path.exists():
        print(f"❌ Directory not found: {recordings_dir}")
        return

    # Get all game files
    game_files = sorted(recordings_path.glob("game_*.jsonl"))

    if not game_files:
        print(f"❌ No game files found in {recordings_dir}")
        return

    print(f"📊 Analyzing {len(game_files)} game recordings...")
    print()

    # Count ticks for each game
    durations = []
    for game_file in game_files:
        tick_count = count_game_ticks(game_file)
        durations.append(tick_count)

    # Calculate statistics
    mean_duration = statistics.mean(durations)
    median_duration = statistics.median(durations)
    mode_result = Counter(durations).most_common(1)
    mode_duration = mode_result[0][0] if mode_result else None
    mode_count = mode_result[0][1] if mode_result else 0
    min_duration = min(durations)
    max_duration = max(durations)
    duration_range = max_duration - min_duration
    stdev_duration = statistics.stdev(durations)

    # Calculate quartiles
    durations_sorted = sorted(durations)
    q1 = durations_sorted[len(durations_sorted) // 4]
    q3 = durations_sorted[3 * len(durations_sorted) // 4]

    # Print results
    print("=" * 60)
    print("GAME DURATION STATISTICS")
    print("=" * 60)
    print()
    print(f"📈 Dataset Size")
    print(f"   Total Games: {len(game_files)}")
    print()
    print(f"📊 Central Tendency")
    print(f"   Mean:   {mean_duration:.2f} ticks")
    print(f"   Median: {median_duration:.1f} ticks")
    print(f"   Mode:   {mode_duration} ticks (appears {mode_count} times)")
    print()
    print(f"📏 Spread")
    print(f"   Range:  {duration_range} ticks")
    print(f"   Min:    {min_duration} ticks")
    print(f"   Max:    {max_duration} ticks")
    print(f"   StdDev: {stdev_duration:.2f} ticks")
    print()
    print(f"📦 Quartiles")
    print(f"   Q1 (25th percentile): {q1} ticks")
    print(f"   Q2 (50th percentile): {median_duration:.1f} ticks")
    print(f"   Q3 (75th percentile): {q3} ticks")
    print(f"   IQR (Q3-Q1):          {q3-q1} ticks")
    print()
    print("=" * 60)
    print()

    # Distribution analysis
    print("📊 DISTRIBUTION BREAKDOWN")
    print("=" * 60)
    print()

    # Categorize by duration
    ultra_short = sum(1 for d in durations if d < 12)  # Pattern from research
    short = sum(1 for d in durations if 12 <= d < 30)
    medium = sum(1 for d in durations if 30 <= d < 60)
    long_games = sum(1 for d in durations if 60 <= d < 100)
    very_long = sum(1 for d in durations if d >= 100)

    print(f"Ultra-Short (< 12 ticks):   {ultra_short:3d} games ({ultra_short/len(durations)*100:5.1f}%)")
    print(f"Short (12-29 ticks):        {short:3d} games ({short/len(durations)*100:5.1f}%)")
    print(f"Medium (30-59 ticks):       {medium:3d} games ({medium/len(durations)*100:5.1f}%)")
    print(f"Long (60-99 ticks):         {long_games:3d} games ({long_games/len(durations)*100:5.1f}%)")
    print(f"Very Long (≥ 100 ticks):    {very_long:3d} games ({very_long/len(durations)*100:5.1f}%)")
    print()
    print("=" * 60)
    print()

    # Top 10 most common durations
    print("🔢 TOP 10 MOST COMMON DURATIONS")
    print("=" * 60)
    print()
    duration_freq = Counter(durations).most_common(10)
    for i, (duration, count) in enumerate(duration_freq, 1):
        print(f"{i:2d}. {duration:3d} ticks - {count:3d} games ({count/len(durations)*100:5.1f}%)")
    print()
    print("=" * 60)

    # Additional insights
    print()
    print("💡 INSIGHTS")
    print("=" * 60)
    print()

    # Check for pattern alignments
    post_max_threshold = 60  # Approximate from research
    post_max_games = sum(1 for d in durations if d >= post_max_threshold)
    print(f"Games ≥ {post_max_threshold} ticks (potential Post-Max-Payout): {post_max_games} ({post_max_games/len(durations)*100:.1f}%)")
    print(f"Ultra-Short games (< 12 ticks pattern): {ultra_short} ({ultra_short/len(durations)*100:.1f}%)")

    # Coefficient of variation (relative variability)
    cv = (stdev_duration / mean_duration) * 100
    print(f"Coefficient of Variation: {cv:.1f}% (variability relative to mean)")

    if cv > 100:
        print("   → High variability - game durations are very inconsistent")
    elif cv > 50:
        print("   → Moderate variability - game durations vary considerably")
    else:
        print("   → Low variability - game durations are relatively consistent")

    print()
    print("=" * 60)

    return {
        'count': len(game_files),
        'mean': mean_duration,
        'median': median_duration,
        'mode': mode_duration,
        'min': min_duration,
        'max': max_duration,
        'range': duration_range,
        'stdev': stdev_duration,
        'q1': q1,
        'q3': q3,
        'durations': durations
    }

if __name__ == "__main__":
    analyze_durations()
