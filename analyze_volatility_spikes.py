#!/usr/bin/env python3
"""
Analyze volatility spikes before rug events across all recorded games

Validates the theory that massive volatility spikes (664.7% mean) occur
before rug events, as identified in the volatility tracker research.

Methodology:
1. Baseline volatility = mean abs % change over first 40 ticks
2. Current volatility = mean abs % change over last 10 ticks (before rug)
3. Volatility ratio = current / baseline
4. Expected: 94.7% of rugs show ratio > 2.0, mean ratio ~6.6x
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
import statistics
from typing import List, Dict, Tuple


class VolatilityAnalyzer:
    """Analyze volatility spikes in game recordings"""

    def __init__(self, baseline_window: int = 40, current_window: int = 10):
        self.baseline_window = baseline_window
        self.current_window = current_window

    def load_game(self, game_file: Path) -> List[Dict]:
        """Load game ticks from JSONL file"""
        ticks = []
        with open(game_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        data = json.loads(line)
                        # Only include tick events, skip game_start events
                        if data.get('type') == 'tick':
                            ticks.append(data)
                    except json.JSONDecodeError as e:
                        # Skip malformed JSON lines
                        print(f"Warning: Skipping malformed JSON in {game_file.name} line {line_num}: {e}")
                        continue
        return ticks

    def calc_volatility(self, prices: List[float]) -> float:
        """
        Calculate volatility as mean of absolute percentage changes

        Args:
            prices: List of price multipliers

        Returns:
            Volatility (mean abs % change)
        """
        if len(prices) < 2:
            return 0.0

        changes = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:  # Avoid division by zero
                change = abs(prices[i] - prices[i-1]) / prices[i-1]
                changes.append(change)

        return np.mean(changes) if changes else 0.0

    def analyze_game(self, game_file: Path) -> Dict:
        """
        Analyze a single game for volatility spike before rug

        Returns:
            Dict with analysis results or None if no rug
        """
        ticks = self.load_game(game_file)

        if len(ticks) < self.baseline_window + self.current_window:
            return None  # Game too short

        # Find where game becomes active (skip cooldown period)
        active_start = 0
        for i, tick in enumerate(ticks):
            if tick.get('active', False):
                active_start = i
                break

        # Get active ticks only
        active_ticks = ticks[active_start:]

        if len(active_ticks) < self.baseline_window + self.current_window:
            return None  # Not enough active ticks

        # Extract prices from active period
        prices = [tick.get('price', 1.0) for tick in active_ticks]

        # Check if game rugged (last tick has rugged=True)
        last_tick = ticks[-1]
        rugged = last_tick.get('rugged', False)

        # Calculate baseline volatility (first 40 active ticks)
        baseline_prices = prices[:self.baseline_window]
        baseline_vol = self.calc_volatility(baseline_prices)

        # Calculate current volatility (last 10 ticks before end)
        current_prices = prices[-self.current_window:]
        current_vol = self.calc_volatility(current_prices)

        # Calculate ratio
        if baseline_vol == 0.0 or baseline_vol < 0.0001:  # Avoid division by zero
            return None  # Skip games with no baseline volatility
        else:
            ratio = current_vol / baseline_vol

        # Calculate peak price in last 10 ticks
        peak_price = max(current_prices) if current_prices else 0.0

        return {
            'game_file': game_file.name,
            'total_ticks': len(ticks),
            'active_ticks': len(active_ticks),
            'rugged': rugged,
            'baseline_vol': baseline_vol,
            'current_vol': current_vol,
            'ratio': ratio,
            'peak_price': peak_price,
            'final_price': prices[-1] if prices else 0.0
        }

    def analyze_all_games(self, recordings_dir: str = "/home/nomad/rugs_recordings_normalized/games") -> List[Dict]:
        """Analyze all games in directory"""
        recordings_path = Path(recordings_dir)
        game_files = sorted(recordings_path.glob("game_*.jsonl"))

        results = []
        for game_file in game_files:
            result = self.analyze_game(game_file)
            if result:
                results.append(result)

        return results


def print_statistics(results: List[Dict]):
    """Print comprehensive volatility spike statistics"""

    # Separate rugged vs non-rugged games
    rugged_games = [r for r in results if r['rugged']]
    non_rugged_games = [r for r in results if not r['rugged']]

    print("=" * 70)
    print("VOLATILITY SPIKE ANALYSIS: ALL GAMES")
    print("=" * 70)
    print()
    print(f"📊 Dataset Summary")
    print(f"   Total games analyzed: {len(results)}")
    print(f"   Rugged games: {len(rugged_games)} ({len(rugged_games)/len(results)*100:.1f}%)")
    print(f"   Non-rugged games: {len(non_rugged_games)} ({len(non_rugged_games)/len(results)*100:.1f}%)")
    print()
    print("=" * 70)
    print()

    # Analyze rugged games
    if rugged_games:
        ratios = [r['ratio'] for r in rugged_games if r['ratio'] > 0]

        if ratios:
            mean_ratio = statistics.mean(ratios)
            median_ratio = statistics.median(ratios)
            max_ratio = max(ratios)
            min_ratio = min(ratios)
            stdev_ratio = statistics.stdev(ratios) if len(ratios) > 1 else 0

            # Count games with significant spikes
            spike_2x = sum(1 for r in ratios if r >= 2.0)
            spike_5x = sum(1 for r in ratios if r >= 5.0)
            spike_10x = sum(1 for r in ratios if r >= 10.0)

            print("🔴 RUGGED GAMES - VOLATILITY SPIKE STATISTICS")
            print("=" * 70)
            print()
            print(f"📈 Central Tendency (Volatility Ratio = Current / Baseline)")
            print(f"   Mean:   {mean_ratio:.2f}x baseline ({mean_ratio*100-100:.1f}% spike)")
            print(f"   Median: {median_ratio:.2f}x baseline ({median_ratio*100-100:.1f}% spike)")
            print()
            print(f"📏 Spread")
            print(f"   Min:    {min_ratio:.2f}x baseline")
            print(f"   Max:    {max_ratio:.2f}x baseline ({max_ratio*100-100:.0f}% spike)")
            print(f"   Range:  {max_ratio - min_ratio:.2f}x")
            print(f"   StdDev: {stdev_ratio:.2f}x")
            print()
            print(f"🎯 Spike Detection Thresholds")
            print(f"   Ratio ≥ 2.0x (>100% spike):  {spike_2x:3d} games ({spike_2x/len(ratios)*100:5.1f}%)")
            print(f"   Ratio ≥ 5.0x (~400% spike):  {spike_5x:3d} games ({spike_5x/len(ratios)*100:5.1f}%)")
            print(f"   Ratio ≥ 10.0x (~900% spike): {spike_10x:3d} games ({spike_10x/len(ratios)*100:5.1f}%)")
            print()

            # Compare to research findings
            print(f"📊 Research Validation")
            print(f"   Expected (from research):")
            print(f"      - 94.7% of games show >100% spike (ratio ≥ 2.0)")
            print(f"      - Mean spike: 664.7% (ratio ~7.6x)")
            print(f"      - Median spike: 551.6% (ratio ~6.5x)")
            print()
            print(f"   Actual (from recordings):")
            print(f"      - {spike_2x/len(ratios)*100:.1f}% of games show >100% spike")
            print(f"      - Mean spike: {mean_ratio*100-100:.1f}% (ratio {mean_ratio:.2f}x)")
            print(f"      - Median spike: {median_ratio*100-100:.1f}% (ratio {median_ratio:.2f}x)")
            print()

            # Validation result
            if spike_2x/len(ratios) >= 0.90 and 5.0 <= mean_ratio <= 9.0:
                print(f"   ✅ VALIDATED: Results match research findings!")
            elif spike_2x/len(ratios) >= 0.70:
                print(f"   ⚠️  PARTIAL: Spike detection rate lower than expected")
            else:
                print(f"   ❌ NOT VALIDATED: Results differ significantly from research")
            print()
            print("=" * 70)
            print()

            # Distribution breakdown
            print("📊 VOLATILITY RATIO DISTRIBUTION (Rugged Games)")
            print("=" * 70)
            print()
            no_spike = sum(1 for r in ratios if r < 1.5)
            low_spike = sum(1 for r in ratios if 1.5 <= r < 2.0)
            moderate = sum(1 for r in ratios if 2.0 <= r < 5.0)
            high = sum(1 for r in ratios if 5.0 <= r < 10.0)
            extreme = sum(1 for r in ratios if r >= 10.0)

            print(f"No Spike (< 1.5x):         {no_spike:3d} games ({no_spike/len(ratios)*100:5.1f}%)")
            print(f"Low Spike (1.5-2.0x):      {low_spike:3d} games ({low_spike/len(ratios)*100:5.1f}%)")
            print(f"Moderate Spike (2.0-5.0x): {moderate:3d} games ({moderate/len(ratios)*100:5.1f}%)")
            print(f"High Spike (5.0-10.0x):    {high:3d} games ({high/len(ratios)*100:5.1f}%)")
            print(f"Extreme Spike (≥ 10.0x):   {extreme:3d} games ({extreme/len(ratios)*100:5.1f}%)")
            print()
            print("=" * 70)
            print()

    # Analyze non-rugged games for comparison
    if non_rugged_games:
        ratios_safe = [r['ratio'] for r in non_rugged_games if r['ratio'] > 0]

        if ratios_safe:
            mean_safe = statistics.mean(ratios_safe)
            median_safe = statistics.median(ratios_safe)
            spike_2x_safe = sum(1 for r in ratios_safe if r >= 2.0)

            print("🟢 NON-RUGGED GAMES - VOLATILITY COMPARISON")
            print("=" * 70)
            print()
            print(f"📈 Volatility Ratios (for comparison)")
            print(f"   Mean:   {mean_safe:.2f}x baseline")
            print(f"   Median: {median_safe:.2f}x baseline")
            print(f"   Ratio ≥ 2.0x: {spike_2x_safe} games ({spike_2x_safe/len(ratios_safe)*100:.1f}%)")
            print()
            print(f"💡 Insight:")
            if ratios and mean_ratio > mean_safe * 2:
                print(f"   ✅ Rugged games have {mean_ratio/mean_safe:.1f}x higher volatility")
                print(f"      → Strong predictive signal!")
            else:
                print(f"   ⚠️  Rugged and safe games have similar volatility")
                print(f"      → Weaker predictive signal")
            print()
            print("=" * 70)
            print()

    # Extreme cases
    if rugged_games:
        ratios_with_names = [(r['ratio'], r['game_file']) for r in rugged_games if r['ratio'] > 0]
        ratios_with_names.sort(reverse=True)

        print("🔝 TOP 10 HIGHEST VOLATILITY SPIKES (Rugged Games)")
        print("=" * 70)
        print()
        for i, (ratio, name) in enumerate(ratios_with_names[:10], 1):
            print(f"{i:2d}. {ratio:6.2f}x baseline ({ratio*100-100:7.1f}% spike) - {name}")
        print()
        print("=" * 70)
        print()

    # Summary insights
    print("💡 KEY INSIGHTS")
    print("=" * 70)
    print()

    if rugged_games and ratios:
        print(f"1. Volatility Spike Prevalence:")
        print(f"   - {spike_2x/len(ratios)*100:.1f}% of rugged games show >2x volatility spike")
        print(f"   - This is {'CONSISTENT' if spike_2x/len(ratios) >= 0.90 else 'INCONSISTENT'} with 94.7% research finding")
        print()

        print(f"2. Spike Magnitude:")
        print(f"   - Mean spike: {mean_ratio:.2f}x baseline ({mean_ratio*100-100:.1f}%)")
        print(f"   - Research claimed: ~7.6x baseline (664.7%)")
        print(f"   - Difference: {abs(mean_ratio - 7.6):.1f}x")
        print()

        if non_rugged_games and ratios_safe:
            print(f"3. Predictive Power:")
            print(f"   - Rugged games: {mean_ratio:.2f}x average volatility ratio")
            print(f"   - Safe games: {mean_safe:.2f}x average volatility ratio")
            print(f"   - Separation: {mean_ratio/mean_safe:.1f}x difference")
            print()

        print(f"4. Trading Strategy Implications:")
        if spike_2x/len(ratios) >= 0.90:
            print(f"   ✅ Exit at 2.0x volatility ratio catches {spike_2x/len(ratios)*100:.1f}% of rugs")
            print(f"   ✅ Exit at 5.0x volatility ratio catches {spike_5x/len(ratios)*100:.1f}% of rugs")
        else:
            print(f"   ⚠️  Only {spike_2x/len(ratios)*100:.1f}% of rugs show 2x spike")
            print(f"   ⚠️  Volatility signal may be less reliable than expected")
        print()

    print("=" * 70)


def main():
    print("Analyzing volatility spikes in 857 recorded games...")
    print()

    analyzer = VolatilityAnalyzer(baseline_window=40, current_window=10)
    results = analyzer.analyze_all_games()

    print_statistics(results)


if __name__ == "__main__":
    main()
