#!/usr/bin/env python3
"""
Position Duration and Tick-Based Survival Analysis

Analyzes:
1. Average trade position duration (hold time from entry to exit)
2. Survival curves by absolute tick number (P(game survives past tick N))
3. Optimal hold times by entry zone
4. Rug timing distribution

For Bayesian model parameter estimation.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class GameTick:
    """Single tick of game data"""
    tick: int
    price: float
    phase: str
    active: bool
    rugged: bool
    trade_count: int
    timestamp: str


@dataclass
class GameData:
    """Complete game recording"""
    game_id: str
    ticks: List[GameTick]
    total_ticks: int
    peak_price: float
    final_price: float
    price_range: Tuple[float, float]
    tick_range: Tuple[int, int]
    rug_tick: int


class PositionDurationAnalyzer:
    """Analyzes position hold durations and survival curves"""

    def __init__(self, recordings_dir: str = "/home/nomad/rugs_recordings"):
        self.recordings_dir = Path(recordings_dir)
        self.games: List[GameData] = []

        # Entry zones for position simulation
        self.entry_zones = [
            (1.0, 10.0),
            (10.0, 50.0),
            (50.0, 200.0),
            (200.0, 1000.0),
            (1000.0, float('inf'))
        ]

        # Profit targets for exit simulation
        self.profit_targets = [0.10, 0.25, 0.50, 1.0]

    def load_all_games(self):
        """Load all game recordings"""
        print("=" * 80)
        print("LOADING GAME RECORDINGS")
        print("=" * 80)
        print()

        game_files = sorted(self.recordings_dir.glob("game_*.jsonl"))

        if not game_files:
            print(f"❌ No game files found in {self.recordings_dir}")
            return

        print(f"📁 Found {len(game_files)} game files")
        print(f"📊 Loading game data...")
        print()

        for i, game_file in enumerate(game_files, 1):
            if i % 100 == 0:
                print(f"   Loading game {i}/{len(game_files)}...")

            try:
                game_data = self._load_game(game_file)
                if game_data:
                    self.games.append(game_data)
            except Exception as e:
                pass  # Skip corrupted files silently

        print(f"✅ Loaded {len(self.games)} games successfully")
        print()

    def _load_game(self, game_file: Path) -> Optional[GameData]:
        """Load a single game JSONL file"""
        ticks = []
        game_id = None
        game_summary = None
        rug_tick = None

        with open(game_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue

                event = json.loads(line)

                if event['type'] == 'game_start':
                    game_id = event['game_id']

                elif event['type'] == 'tick':
                    tick = GameTick(
                        tick=event['tick'],
                        price=event['price'],
                        phase=event['phase'],
                        active=event['active'],
                        rugged=event['rugged'],
                        trade_count=event['trade_count'],
                        timestamp=event['timestamp']
                    )
                    ticks.append(tick)

                    # Record rug tick
                    if event['rugged'] and rug_tick is None:
                        rug_tick = event['tick']

                elif event['type'] == 'game_end':
                    game_summary = event

        if not ticks or not game_summary:
            return None

        # If rug tick not found, use last tick
        if rug_tick is None:
            rug_tick = ticks[-1].tick

        return GameData(
            game_id=game_id,
            ticks=ticks,
            total_ticks=game_summary['total_ticks'],
            peak_price=game_summary['peak_price'],
            final_price=game_summary['final_price'],
            price_range=tuple(game_summary['price_range']),
            tick_range=tuple(game_summary['tick_range']),
            rug_tick=rug_tick
        )

    def analyze_survival_by_tick(self) -> Dict:
        """
        Analysis 1: Survival Curve by Absolute Tick Number

        Calculate P(game survives past tick N) for all N
        """
        print("=" * 80)
        print("ANALYSIS 1: SURVIVAL CURVE BY ABSOLUTE TICK")
        print("=" * 80)
        print()

        # Collect all rug ticks
        rug_ticks = [game.rug_tick for game in self.games]

        # Statistics
        mean_rug_tick = np.mean(rug_ticks)
        median_rug_tick = np.median(rug_ticks)
        std_rug_tick = np.std(rug_ticks)
        min_rug_tick = min(rug_ticks)
        max_rug_tick = max(rug_ticks)

        print("Rug Timing Statistics:")
        print("-" * 80)
        print(f"Mean rug tick:   {mean_rug_tick:.1f}")
        print(f"Median rug tick: {median_rug_tick:.1f}")
        print(f"Std dev:         {std_rug_tick:.1f}")
        print(f"Min rug tick:    {min_rug_tick}")
        print(f"Max rug tick:    {max_rug_tick}")
        print()

        # Build survival curve
        # For each tick N, calculate % of games that survived past tick N
        tick_checkpoints = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500,
                           600, 700, 800, 900, 1000, 1500, 2000]

        survival_curve = {}
        for checkpoint in tick_checkpoints:
            survived = sum(1 for rt in rug_ticks if rt > checkpoint)
            survival_prob = survived / len(rug_ticks) * 100
            survival_curve[checkpoint] = survival_prob

        print("Survival Probability by Tick:")
        print("-" * 80)
        print(f"{'Tick':<10} {'Survived':<12} {'Rugged':<12} {'P(Survive)':<12}")
        print("-" * 80)

        for checkpoint in tick_checkpoints:
            survived = sum(1 for rt in rug_ticks if rt > checkpoint)
            rugged = len(rug_ticks) - survived
            survival_prob = survival_curve[checkpoint]

            print(f"{checkpoint:<10} {survived:<12} {rugged:<12} {survival_prob:<12.2f}%")

        print()

        # Percentiles
        percentiles = [10, 25, 50, 75, 90, 95, 99]
        print("Rug Tick Percentiles:")
        print("-" * 80)
        for p in percentiles:
            tick = np.percentile(rug_ticks, p)
            print(f"P{p:02d}: {tick:>7.1f} ticks ({p}% of games rug by this tick)")

        print()

        # Hazard rate (rug probability density)
        print("Rug Probability Density (Hazard Rate):")
        print("-" * 80)

        tick_bins = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, float('inf')]
        bin_labels = []
        for i in range(len(tick_bins) - 1):
            if tick_bins[i+1] == float('inf'):
                bin_labels.append(f"{tick_bins[i]}+")
            else:
                bin_labels.append(f"{tick_bins[i]}-{tick_bins[i+1]}")

        for i in range(len(tick_bins) - 1):
            low, high = tick_bins[i], tick_bins[i+1]
            count = sum(1 for rt in rug_ticks if low <= rt < high)
            pct = count / len(rug_ticks) * 100
            print(f"{bin_labels[i]:<12} {count:>5} games ({pct:>5.1f}%)")

        print()
        print("Key Insights:")
        print("-" * 80)

        # Find tick where 50% have rugged
        median_tick = median_rug_tick
        print(f"⏰ 50% of games rug by tick {median_tick:.0f}")

        # Find tick where 90% have rugged
        p90_tick = np.percentile(rug_ticks, 90)
        print(f"⏰ 90% of games rug by tick {p90_tick:.0f}")

        # Safe window
        p25_tick = np.percentile(rug_ticks, 25)
        print(f"✅ First 25% of games rug by tick {p25_tick:.0f} (relatively safe before this)")

        print()

        return {
            'mean_rug_tick': mean_rug_tick,
            'median_rug_tick': median_rug_tick,
            'std_rug_tick': std_rug_tick,
            'survival_curve': survival_curve,
            'percentiles': {p: np.percentile(rug_ticks, p) for p in percentiles},
            'rug_ticks': rug_ticks
        }

    def analyze_position_duration(self) -> Dict:
        """
        Analysis 2: Average Position Hold Duration

        Simulate entering at various multipliers and calculate:
        - Average hold time to reach profit target
        - Average hold time to rug (if target not reached)
        - Optimal hold time by entry zone
        """
        print("=" * 80)
        print("ANALYSIS 2: POSITION HOLD DURATION")
        print("=" * 80)
        print()

        entry_multipliers = [1, 5, 10, 25, 50, 100, 250, 500]
        profit_targets = [0.10, 0.25, 0.50, 1.0]

        results = defaultdict(lambda: defaultdict(list))

        # Simulate positions for each entry point
        for entry_mult in entry_multipliers:
            for game in self.games:
                for i, tick in enumerate(game.ticks):
                    if tick.rugged:
                        break

                    # Check if this is near our entry multiplier
                    if abs(tick.price - entry_mult) / entry_mult < 0.05:  # Within 5%
                        entry_price = tick.price
                        entry_tick = tick.tick

                        # Simulate position from this entry
                        for target in profit_targets:
                            target_price = entry_price * (1 + target)

                            # Find when we reach target or rug
                            reached_target = False
                            exit_tick = None
                            hold_duration = None

                            for j in range(i + 1, len(game.ticks)):
                                future_tick = game.ticks[j]

                                if future_tick.price >= target_price:
                                    # Target reached!
                                    reached_target = True
                                    exit_tick = future_tick.tick
                                    hold_duration = exit_tick - entry_tick
                                    break

                                if future_tick.rugged:
                                    # Rugged before target
                                    exit_tick = future_tick.tick
                                    hold_duration = exit_tick - entry_tick
                                    break

                            if hold_duration is not None:
                                results[entry_mult][target].append({
                                    'hold_duration': hold_duration,
                                    'reached_target': reached_target,
                                    'entry_tick': entry_tick,
                                    'exit_tick': exit_tick
                                })

        # Aggregate results
        print("Position Hold Duration by Entry Point and Target:")
        print("-" * 80)
        print(f"{'Entry':<8} {'Target':<8} {'N':<7} {'Success%':<10} {'Avg Hold':<12} {'Med Hold':<12} {'Avg (Win)':<12} {'Avg (Loss)':<12}")
        print("-" * 80)

        summary = {}
        for entry_mult in sorted(results.keys()):
            entry_summary = {}

            for target in sorted(results[entry_mult].keys()):
                positions = results[entry_mult][target]

                if len(positions) < 10:
                    continue

                wins = [p for p in positions if p['reached_target']]
                losses = [p for p in positions if not p['reached_target']]

                success_rate = len(wins) / len(positions) * 100

                all_durations = [p['hold_duration'] for p in positions]
                avg_hold = np.mean(all_durations)
                med_hold = np.median(all_durations)

                avg_win_hold = np.mean([p['hold_duration'] for p in wins]) if wins else 0
                avg_loss_hold = np.mean([p['hold_duration'] for p in losses]) if losses else 0

                print(f"{entry_mult:<8.0f} {int(target*100):>3}%    {len(positions):<7} "
                      f"{success_rate:<10.1f} {avg_hold:<12.1f} {med_hold:<12.1f} "
                      f"{avg_win_hold:<12.1f} {avg_loss_hold:<12.1f}")

                entry_summary[f"{int(target*100)}%"] = {
                    'n': len(positions),
                    'success_rate': success_rate,
                    'avg_hold': avg_hold,
                    'median_hold': med_hold,
                    'avg_win_hold': avg_win_hold,
                    'avg_loss_hold': avg_loss_hold,
                    'total_wins': len(wins),
                    'total_losses': len(losses)
                }

            summary[entry_mult] = entry_summary

        print()
        print("Key Insights:")
        print("-" * 80)

        # Find optimal hold times
        for entry_mult in [1, 25, 50, 100]:
            if entry_mult in summary and '50%' in summary[entry_mult]:
                stats = summary[entry_mult]['50%']
                print(f"💡 Entry at {entry_mult}x, 50% target:")
                print(f"   Success: {stats['success_rate']:.1f}%")
                print(f"   Avg hold: {stats['avg_hold']:.1f} ticks")
                print(f"   Win hold: {stats['avg_win_hold']:.1f} ticks")
                print(f"   Loss hold: {stats['avg_loss_hold']:.1f} ticks")

        print()

        return summary

    def analyze_hold_time_vs_success(self) -> Dict:
        """
        Analysis 3: Hold Time vs Success Rate

        For different hold durations, what's the success rate?
        """
        print("=" * 80)
        print("ANALYSIS 3: HOLD TIME VS SUCCESS RATE")
        print("=" * 80)
        print()

        # Simulate positions with fixed hold times
        hold_durations = [10, 20, 50, 100, 150, 200, 300]
        entry_zones = [(1, 10), (10, 50), (50, 200), (200, 1000)]

        results = defaultdict(lambda: defaultdict(list))

        for zone_low, zone_high in entry_zones:
            zone_key = f"{zone_low}-{zone_high}x"

            for game in self.games:
                for i, tick in enumerate(game.ticks):
                    if tick.rugged:
                        break

                    # Check if in this zone
                    if zone_low <= tick.price < zone_high:
                        entry_price = tick.price
                        entry_tick = tick.tick

                        # Test each hold duration
                        for hold_dur in hold_durations:
                            exit_idx = i + hold_dur

                            # Check if we can hold this long
                            if exit_idx >= len(game.ticks):
                                continue

                            exit_tick_obj = game.ticks[exit_idx]

                            if exit_tick_obj.rugged:
                                # Rugged during hold
                                success = False
                                pnl = -1.0  # Total loss
                            else:
                                # Exited successfully
                                exit_price = exit_tick_obj.price
                                pnl = (exit_price - entry_price) / entry_price
                                success = pnl > 0  # Any profit

                            results[zone_key][hold_dur].append({
                                'success': success,
                                'pnl': pnl
                            })

        # Aggregate
        print("Success Rate by Hold Duration and Zone:")
        print("-" * 80)
        print(f"{'Zone':<15} {'Hold':<8} {'N':<7} {'Success%':<12} {'Avg PnL%':<12} {'Med PnL%':<12}")
        print("-" * 80)

        summary = {}
        for zone in sorted(results.keys()):
            zone_summary = {}

            for hold_dur in sorted(results[zone].keys()):
                positions = results[zone][hold_dur]

                if len(positions) < 50:
                    continue

                success_count = sum(1 for p in positions if p['success'])
                success_rate = success_count / len(positions) * 100

                pnls = [p['pnl'] * 100 for p in positions]  # Convert to %
                avg_pnl = np.mean(pnls)
                med_pnl = np.median(pnls)

                print(f"{zone:<15} {hold_dur:<8} {len(positions):<7} "
                      f"{success_rate:<12.1f} {avg_pnl:<12.1f} {med_pnl:<12.1f}")

                zone_summary[hold_dur] = {
                    'n': len(positions),
                    'success_rate': success_rate,
                    'avg_pnl': avg_pnl,
                    'median_pnl': med_pnl
                }

            summary[zone] = zone_summary

        print()
        print("Key Insights:")
        print("-" * 80)

        # Find optimal hold time per zone
        for zone in sorted(summary.keys()):
            if not summary[zone]:
                continue

            # Find hold duration with best avg PnL
            best_hold = max(summary[zone].items(),
                          key=lambda x: x[1]['avg_pnl'])

            print(f"💡 {zone}: Optimal hold ~{best_hold[0]} ticks "
                  f"({best_hold[1]['success_rate']:.1f}% success, "
                  f"{best_hold[1]['avg_pnl']:.1f}% avg PnL)")

        print()

        return summary

    def generate_bayesian_params(self,
                                survival_results: Dict,
                                duration_results: Dict,
                                hold_vs_success: Dict) -> Dict:
        """
        Generate Bayesian model parameters from all analyses
        """
        print("=" * 80)
        print("BAYESIAN MODEL PARAMETERS")
        print("=" * 80)
        print()

        params = {
            'temporal_risk': {},
            'optimal_hold_times': {},
            'exit_urgency': {}
        }

        # 1. Temporal risk curve (P(rug at tick N))
        survival_curve = survival_results['survival_curve']

        print("Temporal Risk Model:")
        print("-" * 80)
        print("P(rug before tick N):")
        for tick, surv_prob in sorted(survival_curve.items()):
            rug_prob = 100 - surv_prob
            params['temporal_risk'][tick] = rug_prob / 100
            print(f"  Tick {tick:>4}: {rug_prob:>5.1f}% (cumulative rug probability)")

        print()

        # 2. Optimal hold times by entry
        print("Optimal Hold Times:")
        print("-" * 80)

        for entry_mult, targets in duration_results.items():
            if '50%' in targets:  # Use 50% target as reference
                stats = targets['50%']
                optimal_hold = stats['avg_win_hold']

                params['optimal_hold_times'][entry_mult] = {
                    'target_50pct': optimal_hold,
                    'median': stats['median_hold'],
                    'success_rate': stats['success_rate']
                }

                print(f"  Entry {entry_mult:>4}x: {optimal_hold:>6.1f} ticks "
                      f"(50% target, {stats['success_rate']:.1f}% success)")

        print()

        # 3. Exit urgency by hold duration
        print("Exit Urgency Model:")
        print("-" * 80)
        print("As hold time increases, when should we exit?")

        # Use median rug tick as reference
        median_rug = survival_results['median_rug_tick']
        p75_rug = survival_results['percentiles'][75]
        p90_rug = survival_results['percentiles'][90]

        params['exit_urgency'] = {
            'safe_window': median_rug * 0.5,  # First 50% of median
            'caution_window': median_rug * 0.75,  # 50-75% of median
            'danger_window': median_rug,  # 75-100% of median
            'critical_window': p75_rug  # Past 75th percentile
        }

        print(f"  Safe:     < {params['exit_urgency']['safe_window']:.0f} ticks "
              f"(low time-based risk)")
        print(f"  Caution:  < {params['exit_urgency']['caution_window']:.0f} ticks "
              f"(moderate time-based risk)")
        print(f"  Danger:   < {params['exit_urgency']['danger_window']:.0f} ticks "
              f"(high time-based risk)")
        print(f"  Critical: > {params['exit_urgency']['critical_window']:.0f} ticks "
              f"(extreme time-based risk)")

        print()

        return params

    def run_full_analysis(self) -> Dict:
        """Run all position duration analyses"""
        print()
        print("=" * 80)
        print("POSITION DURATION & SURVIVAL ANALYSIS")
        print("=" * 80)
        print()

        # Load data
        self.load_all_games()

        if not self.games:
            print("❌ No games loaded. Exiting.")
            return {}

        # Run analyses
        survival_results = self.analyze_survival_by_tick()
        duration_results = self.analyze_position_duration()
        hold_vs_success = self.analyze_hold_time_vs_success()

        # Generate Bayesian parameters
        bayesian_params = self.generate_bayesian_params(
            survival_results,
            duration_results,
            hold_vs_success
        )

        print("=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)
        print()
        print(f"✅ Analyzed {len(self.games)} games")
        print(f"✅ Built tick-based survival curve")
        print(f"✅ Calculated position hold durations")
        print(f"✅ Mapped hold time vs success rates")
        print(f"✅ Generated Bayesian temporal parameters")
        print()

        return {
            'survival_by_tick': survival_results,
            'position_duration': duration_results,
            'hold_vs_success': hold_vs_success,
            'bayesian_parameters': bayesian_params
        }


def main():
    """Main entry point"""
    analyzer = PositionDurationAnalyzer()
    results = analyzer.run_full_analysis()

    # Save results
    output_file = Path("/home/nomad/Desktop/REPLAYER/position_duration_analysis.json")

    # Convert numpy types to native Python types for JSON serialization
    def convert_types(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_types(item) for item in obj]
        return obj

    results_serializable = convert_types(results)

    with open(output_file, 'w') as f:
        json.dump(results_serializable, f, indent=2)

    print(f"📄 Results saved to: {output_file}")
    print()


if __name__ == "__main__":
    main()
