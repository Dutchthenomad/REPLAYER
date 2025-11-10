#!/usr/bin/env python3
"""
Analyze volatility spike timing and false positive rates

Key Questions:
1. How many ticks between spike detection (ratio ≥ 2.0x) and rug event?
2. Do volatility spikes occur during normal gameplay (false positives)?
3. What's the volatility trajectory throughout the game?
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Dict, Tuple
import statistics


class SpikeTimingAnalyzer:
    """Analyze when volatility spikes occur and reaction time available"""

    def __init__(self, baseline_window: int = 40, rolling_window: int = 10, spike_threshold: float = 2.0):
        self.baseline_window = baseline_window
        self.rolling_window = rolling_window
        self.spike_threshold = spike_threshold

    def load_game(self, game_file: Path) -> List[Dict]:
        """Load game ticks from JSONL file"""
        ticks = []
        with open(game_file, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if data.get('type') == 'tick':
                            ticks.append(data)
                    except:
                        continue
        return ticks

    def calc_volatility(self, prices: List[float]) -> float:
        """Calculate volatility as mean of absolute percentage changes"""
        if len(prices) < 2:
            return 0.0

        changes = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                change = abs(prices[i] - prices[i-1]) / prices[i-1]
                changes.append(change)

        return np.mean(changes) if changes else 0.0

    def analyze_game_trajectory(self, game_file: Path) -> Dict:
        """
        Analyze volatility trajectory throughout entire game

        Returns detailed spike timing and false positive info
        """
        ticks = self.load_game(game_file)

        # Find active start
        active_start = 0
        for i, tick in enumerate(ticks):
            if tick.get('active', False):
                active_start = i
                break

        active_ticks = ticks[active_start:]

        if len(active_ticks) < self.baseline_window + self.rolling_window:
            return None

        prices = [tick.get('price', 1.0) for tick in active_ticks]

        # Calculate baseline (first 40 ticks)
        baseline_prices = prices[:self.baseline_window]
        baseline_vol = self.calc_volatility(baseline_prices)

        if baseline_vol < 0.0001:
            return None

        # Calculate rolling volatility ratio at each tick
        volatility_ratios = []
        spike_events = []  # (tick_idx, ratio) when spike first detected

        for i in range(self.baseline_window, len(prices)):
            # Get last N ticks for rolling window
            window_start = max(0, i - self.rolling_window + 1)
            window_prices = prices[window_start:i+1]

            current_vol = self.calc_volatility(window_prices)
            ratio = current_vol / baseline_vol
            volatility_ratios.append((i, ratio))

            # Check if this is a new spike (not already in spike state)
            if ratio >= self.spike_threshold:
                if not spike_events or spike_events[-1][0] < i - self.rolling_window:
                    spike_events.append((i, ratio))

        # Check if game rugged
        last_tick = ticks[-1]
        rugged = last_tick.get('rugged', False)

        # Find rug tick (first tick where rugged=True)
        rug_tick = None
        if rugged:
            for i, tick in enumerate(active_ticks):
                if tick.get('rugged', False):
                    rug_tick = i
                    break

        # Calculate reaction time (ticks between first spike and rug)
        first_spike_tick = spike_events[0][0] if spike_events else None
        reaction_time = None
        if rugged and first_spike_tick is not None and rug_tick is not None:
            reaction_time = rug_tick - first_spike_tick

        return {
            'game_file': game_file.name,
            'rugged': rugged,
            'total_active_ticks': len(active_ticks),
            'baseline_vol': baseline_vol,
            'rug_tick': rug_tick,
            'spike_events': spike_events,
            'first_spike_tick': first_spike_tick,
            'reaction_time': reaction_time,
            'volatility_trajectory': volatility_ratios,
            'max_ratio': max([r for _, r in volatility_ratios]) if volatility_ratios else 0
        }

    def analyze_all_games(self, recordings_dir: str = "/home/nomad/rugs_recordings_normalized/games") -> List[Dict]:
        """Analyze all games"""
        recordings_path = Path(recordings_dir)
        game_files = sorted(recordings_path.glob("game_*.jsonl"))

        results = []
        for i, game_file in enumerate(game_files):
            if i % 100 == 0:
                print(f"Processing game {i+1}/{len(game_files)}...")
            result = self.analyze_game_trajectory(game_file)
            if result:
                results.append(result)

        return results


def print_statistics(results: List[Dict]):
    """Print comprehensive spike timing statistics"""

    rugged_games = [r for r in results if r['rugged']]
    safe_games = [r for r in results if not r['rugged']]

    print("=" * 80)
    print("VOLATILITY SPIKE TIMING & FALSE POSITIVE ANALYSIS")
    print("=" * 80)
    print()
    print(f"📊 Dataset Summary")
    print(f"   Total games: {len(results)}")
    print(f"   Rugged games: {len(rugged_games)}")
    print(f"   Safe games: {len(safe_games)}")
    print()
    print("=" * 80)
    print()

    # === PART 1: REACTION TIME ANALYSIS ===
    print("⏱️  REACTION TIME ANALYSIS (Rugged Games)")
    print("=" * 80)
    print()

    # Games where spike was detected before rug
    games_with_warning = [r for r in rugged_games if r['reaction_time'] is not None and r['reaction_time'] > 0]
    games_no_warning = [r for r in rugged_games if r['reaction_time'] is not None and r['reaction_time'] <= 0]
    games_no_spike = [r for r in rugged_games if not r['spike_events']]

    print(f"Detection Summary:")
    print(f"   Spike detected BEFORE rug: {len(games_with_warning)} games ({len(games_with_warning)/len(rugged_games)*100:.1f}%)")
    print(f"   Spike detected AT/AFTER rug: {len(games_no_warning)} games ({len(games_no_warning)/len(rugged_games)*100:.1f}%)")
    print(f"   No spike detected: {len(games_no_spike)} games ({len(games_no_spike)/len(rugged_games)*100:.1f}%)")
    print()

    if games_with_warning:
        reaction_times = [r['reaction_time'] for r in games_with_warning]

        mean_reaction = statistics.mean(reaction_times)
        median_reaction = statistics.median(reaction_times)
        min_reaction = min(reaction_times)
        max_reaction = max(reaction_times)

        print(f"Reaction Time Available (Spike → Rug):")
        print(f"   Mean:   {mean_reaction:.1f} ticks")
        print(f"   Median: {median_reaction:.1f} ticks")
        print(f"   Min:    {min_reaction} ticks")
        print(f"   Max:    {max_reaction} ticks")
        print()

        # Distribution
        instant = sum(1 for t in reaction_times if t <= 1)
        very_short = sum(1 for t in reaction_times if 2 <= t <= 5)
        short = sum(1 for t in reaction_times if 6 <= t <= 10)
        moderate = sum(1 for t in reaction_times if 11 <= t <= 20)
        long_time = sum(1 for t in reaction_times if t > 20)

        print(f"Reaction Time Distribution:")
        print(f"   ≤ 1 tick (instant):      {instant:3d} games ({instant/len(reaction_times)*100:5.1f}%) ⚠️  Too fast!")
        print(f"   2-5 ticks (very short):  {very_short:3d} games ({very_short/len(reaction_times)*100:5.1f}%) ⚠️  Difficult")
        print(f"   6-10 ticks (short):      {short:3d} games ({short/len(reaction_times)*100:5.1f}%) ⚠️  Challenging")
        print(f"   11-20 ticks (moderate):  {moderate:3d} games ({moderate/len(reaction_times)*100:5.1f}%) ✅ Actionable")
        print(f"   > 20 ticks (long):       {long_time:3d} games ({long_time/len(reaction_times)*100:5.1f}%) ✅ Plenty of time")
        print()

        actionable_pct = (moderate + long_time) / len(reaction_times) * 100
        print(f"💡 Actionable Warning Rate: {actionable_pct:.1f}% (≥11 ticks to react)")
        print()

    print("=" * 80)
    print()

    # === PART 2: FALSE POSITIVE ANALYSIS ===
    print("🚨 FALSE POSITIVE ANALYSIS (Safe Games)")
    print("=" * 80)
    print()

    if safe_games:
        # Count safe games that had spike events
        safe_with_spikes = [r for r in safe_games if r['spike_events']]
        safe_no_spikes = [r for r in safe_games if not r['spike_events']]

        print(f"Safe Game Spike Events:")
        print(f"   Games with spikes (≥2.0x): {len(safe_with_spikes)} ({len(safe_with_spikes)/len(safe_games)*100:.1f}%)")
        print(f"   Games without spikes: {len(safe_no_spikes)} ({len(safe_no_spikes)/len(safe_games)*100:.1f}%)")
        print()

        if safe_with_spikes:
            # Count total spike events in safe games
            total_spikes = sum(len(r['spike_events']) for r in safe_with_spikes)
            avg_spikes = total_spikes / len(safe_with_spikes)

            print(f"False Positive Details:")
            print(f"   Total spike events in safe games: {total_spikes}")
            print(f"   Average spikes per affected game: {avg_spikes:.1f}")
            print()

            # Show examples
            print(f"Examples of False Positives:")
            for i, game in enumerate(safe_with_spikes[:5], 1):
                num_spikes = len(game['spike_events'])
                max_ratio = max([ratio for _, ratio in game['spike_events']])
                print(f"   {i}. {game['game_file']}: {num_spikes} spikes, max {max_ratio:.2f}x")
            print()

        # Calculate false positive rate
        print(f"📊 False Positive Rate:")
        print(f"   {len(safe_with_spikes)/len(safe_games)*100:.1f}% of safe games trigger spike alert")
        print(f"   → Bot would exit {len(safe_with_spikes)} safe games unnecessarily")
        print()

    print("=" * 80)
    print()

    # === PART 3: SPIKE FREQUENCY IN RUGGED GAMES ===
    print("📈 SPIKE FREQUENCY IN RUGGED GAMES")
    print("=" * 80)
    print()

    rugged_with_multiple = [r for r in rugged_games if len(r['spike_events']) > 1]

    if rugged_games:
        spike_counts = [len(r['spike_events']) for r in rugged_games]
        mean_spikes = statistics.mean(spike_counts)

        print(f"Multiple Spikes Before Rug:")
        print(f"   Games with 1 spike: {sum(1 for c in spike_counts if c == 1)} ({sum(1 for c in spike_counts if c == 1)/len(spike_counts)*100:.1f}%)")
        print(f"   Games with 2+ spikes: {len(rugged_with_multiple)} ({len(rugged_with_multiple)/len(rugged_games)*100:.1f}%)")
        print(f"   Average spikes per game: {mean_spikes:.2f}")
        print()

        print(f"💡 Interpretation:")
        if len(rugged_with_multiple) / len(rugged_games) > 0.3:
            print(f"   ⚠️  Many games have multiple spikes before rug")
            print(f"   → Bot may exit early on first spike, missing potential profit")
            print(f"   → Need strategy to distinguish 'false alarm' from 'final spike'")
        else:
            print(f"   ✅ Most games have single spike before rug")
            print(f"   → Exit on first spike is appropriate strategy")
        print()

    print("=" * 80)
    print()

    # === PART 4: KEY INSIGHTS ===
    print("💡 KEY INSIGHTS & RECOMMENDATIONS")
    print("=" * 80)
    print()

    if games_with_warning:
        print(f"1. Reaction Time:")
        print(f"   - Mean: {mean_reaction:.1f} ticks between spike detection and rug")
        print(f"   - {actionable_pct:.1f}% of games give ≥11 ticks to react (actionable)")
        print(f"   - {(instant+very_short)/len(reaction_times)*100:.1f}% give ≤5 ticks (too fast to react)")
        print()

    if safe_games:
        fp_rate = len(safe_with_spikes)/len(safe_games)*100
        print(f"2. False Positives:")
        print(f"   - {fp_rate:.1f}% of safe games trigger spike alert")
        if fp_rate < 10:
            print(f"   - ✅ Low false positive rate - acceptable")
        elif fp_rate < 30:
            print(f"   - ⚠️  Moderate false positives - may exit safe games early")
        else:
            print(f"   - ❌ High false positives - bot will exit too often")
        print()

    print(f"3. Strategy Recommendations:")
    print()

    if games_with_warning and mean_reaction >= 10:
        print(f"   ✅ IMMEDIATE EXIT at 2.0x spike")
        print(f"      - {len(games_with_warning)/len(rugged_games)*100:.1f}% of rugs have warning spike")
        print(f"      - Average {mean_reaction:.1f} ticks to react (sufficient)")
    else:
        print(f"   ⚠️  GRADUATED EXIT strategy")
        print(f"      - 2.0x spike: Reduce position 50%")
        print(f"      - 3.0x spike: Exit 100%")
        print(f"      - Many spikes happen too close to rug")
    print()

    if safe_games and len(safe_with_spikes)/len(safe_games) > 0.2:
        print(f"   ⚠️  HIGH FALSE POSITIVES - Use confirmation:")
        print(f"      - Require 2 consecutive ticks above threshold")
        print(f"      - Or combine with other signals (patterns)")
    else:
        print(f"   ✅ LOW FALSE POSITIVES - Exit immediately on spike")
    print()

    if len(rugged_with_multiple) / len(rugged_games) > 0.3:
        print(f"   ⚠️  MULTIPLE SPIKES COMMON:")
        print(f"      - Consider trailing stop instead of immediate exit")
        print(f"      - Exit when ratio increases 2→3x or 3→4x")
    print()

    print("=" * 80)


def main():
    print("Analyzing volatility spike timing and false positives...")
    print("This may take a few minutes...")
    print()

    analyzer = SpikeTimingAnalyzer(baseline_window=40, rolling_window=10, spike_threshold=2.0)
    results = analyzer.analyze_all_games()

    print_statistics(results)


if __name__ == "__main__":
    main()
