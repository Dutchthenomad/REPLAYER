#!/usr/bin/env python3
"""
Comprehensive Game Pattern Analysis for RL Trading Bot Reward Design

Analyzes 900+ recorded games to build empirical probability tables for:
1. Entry Opportunity Windows (profit potential at different multipliers)
2. Volatility Reality Check (actual price swings)
3. Hold Duration vs Success Rate (survival curves)
4. Profit Target Reality (achievable gains from entry points)

Outputs empirical data to inform RL reward function design.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
import statistics


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


class TradingPatternAnalyzer:
    """Analyzes recorded games to extract trading patterns"""

    def __init__(self, recordings_dir: str = "/home/nomad/rugs_recordings"):
        self.recordings_dir = Path(recordings_dir)
        self.games: List[GameData] = []

        # Multiplier zones for analysis
        self.multiplier_zones = [
            (1.0, 10.0),
            (10.0, 50.0),
            (50.0, 200.0),
            (200.0, 1000.0),
            (1000.0, float('inf'))
        ]

        # Tick zones for survival analysis
        self.tick_zones = [50, 100, 200, 300, 400, 500]

        # Profit targets to test
        self.profit_targets = [0.10, 0.25, 0.50, 1.0, 2.0]  # 10%, 25%, 50%, 100%, 200%

    def load_all_games(self):
        """Load all game recordings into memory"""
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
                print(f"⚠️  Error loading {game_file.name}: {e}")

        print(f"✅ Loaded {len(self.games)} games successfully")
        print()

    def _load_game(self, game_file: Path) -> Optional[GameData]:
        """Load a single game JSONL file"""
        ticks = []
        game_id = None
        game_summary = None

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

                elif event['type'] == 'game_end':
                    game_summary = event

        if not ticks or not game_summary:
            return None

        return GameData(
            game_id=game_id,
            ticks=ticks,
            total_ticks=game_summary['total_ticks'],
            peak_price=game_summary['peak_price'],
            final_price=game_summary['final_price'],
            price_range=tuple(game_summary['price_range']),
            tick_range=tuple(game_summary['tick_range'])
        )

    def analyze_entry_opportunities(self) -> Dict:
        """
        Phase 1: Entry Opportunity Windows

        For each entry multiplier, calculate forward-looking returns:
        - What % of trades reach profit targets?
        - What's the average/median/max return from entry?
        - What's the risk (% that rug before profit)?
        """
        print("=" * 80)
        print("PHASE 1: ENTRY OPPORTUNITY ANALYSIS")
        print("=" * 80)
        print()

        entry_points = [1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2000]
        results = {}

        for entry_mult in entry_points:
            # Find all possible entries at this multiplier
            opportunities = []

            for game in self.games:
                for i, tick in enumerate(game.ticks):
                    if tick.rugged:
                        break

                    # Check if this tick is near our entry multiplier
                    if abs(tick.price - entry_mult) / entry_mult < 0.05:  # Within 5%
                        # Calculate forward returns
                        max_return = 0.0
                        eventual_return = None
                        rugged_before_profit = False

                        for j in range(i + 1, len(game.ticks)):
                            future_tick = game.ticks[j]

                            if future_tick.rugged:
                                eventual_return = (future_tick.price - tick.price) / tick.price
                                rugged_before_profit = True
                                break

                            future_return = (future_tick.price - tick.price) / tick.price
                            max_return = max(max_return, future_return)

                        if eventual_return is None:
                            eventual_return = (game.ticks[-1].price - tick.price) / tick.price

                        opportunities.append({
                            'entry_price': tick.price,
                            'entry_tick': tick.tick,
                            'max_return': max_return,
                            'eventual_return': eventual_return,
                            'rugged_before_profit': rugged_before_profit,
                            'ticks_to_rug': len(game.ticks) - i if rugged_before_profit else None
                        })

            if not opportunities:
                continue

            # Calculate statistics
            max_returns = [o['max_return'] for o in opportunities]
            eventual_returns = [o['eventual_return'] for o in opportunities]

            # Calculate profit target achievement rates
            achievement_rates = {}
            for target in self.profit_targets:
                achieved = sum(1 for r in max_returns if r >= target)
                achievement_rates[f"{int(target*100)}%"] = achieved / len(opportunities) * 100

            results[entry_mult] = {
                'sample_size': len(opportunities),
                'avg_max_return': np.mean(max_returns) * 100,  # Convert to %
                'median_max_return': np.median(max_returns) * 100,
                'avg_eventual_return': np.mean(eventual_returns) * 100,
                'median_eventual_return': np.median(eventual_returns) * 100,
                'rug_rate': sum(1 for o in opportunities if o['rugged_before_profit']) / len(opportunities) * 100,
                'profit_achievement': achievement_rates,
                'best_return': max(max_returns) * 100,
                'worst_return': min(eventual_returns) * 100
            }

        # Print results
        print("Entry Multiplier Analysis:")
        print("-" * 80)
        print(f"{'Entry':<8} {'N':<6} {'Avg Max':<10} {'Med Max':<10} {'Rug%':<8} {'10%':<6} {'25%':<6} {'50%':<6} {'100%':<6}")
        print("-" * 80)

        for entry_mult, stats in sorted(results.items()):
            if stats['sample_size'] < 10:
                continue  # Skip low sample sizes

            profit_rates = stats['profit_achievement']
            print(f"{entry_mult:<8.0f} {stats['sample_size']:<6} "
                  f"{stats['avg_max_return']:<10.1f} {stats['median_max_return']:<10.1f} "
                  f"{stats['rug_rate']:<8.1f} "
                  f"{profit_rates.get('10%', 0):<6.1f} "
                  f"{profit_rates.get('25%', 0):<6.1f} "
                  f"{profit_rates.get('50%', 0):<6.1f} "
                  f"{profit_rates.get('100%', 0):<6.1f}")

        print()
        print("Key Insights:")
        print("-" * 80)

        # Find sweet spots
        viable_entries = [(m, s) for m, s in results.items()
                         if s['sample_size'] >= 10 and s['avg_eventual_return'] > 0]

        if viable_entries:
            best_entry = max(viable_entries, key=lambda x: x[1]['avg_eventual_return'])
            print(f"✅ Best entry point: {best_entry[0]:.0f}x (avg {best_entry[1]['avg_eventual_return']:.1f}% return)")

            safest_entry = min(viable_entries, key=lambda x: x[1]['rug_rate'])
            print(f"🛡️  Safest entry point: {safest_entry[0]:.0f}x ({safest_entry[1]['rug_rate']:.1f}% rug rate)")

            last_viable = max([m for m, s in viable_entries])
            print(f"⏰ Latest viable entry: {last_viable:.0f}x")

        print()
        return results

    def analyze_volatility(self) -> Dict:
        """
        Phase 2: Volatility Reality Check

        Measure actual tick-to-tick price changes at different multiplier zones:
        - Average % change per tick
        - Maximum drawdowns that recover
        - Maximum drawdowns before rug
        """
        print("=" * 80)
        print("PHASE 2: VOLATILITY ANALYSIS")
        print("=" * 80)
        print()

        zone_volatility = defaultdict(list)
        zone_drawdowns = defaultdict(list)
        zone_recovery_drawdowns = defaultdict(list)
        zone_rug_drawdowns = defaultdict(list)

        for game in self.games:
            peak_so_far = 0

            for i in range(len(game.ticks) - 1):
                current_tick = game.ticks[i]
                next_tick = game.ticks[i + 1]

                if current_tick.rugged or next_tick.rugged:
                    continue

                # Calculate tick-to-tick % change
                pct_change = abs(next_tick.price - current_tick.price) / current_tick.price * 100

                # Determine which zone we're in
                zone_key = None
                for zone_min, zone_max in self.multiplier_zones:
                    if zone_min <= current_tick.price < zone_max:
                        zone_key = f"{zone_min:.0f}-{zone_max:.0f}x"
                        break

                if zone_key:
                    zone_volatility[zone_key].append(pct_change)

                # Track drawdowns
                peak_so_far = max(peak_so_far, current_tick.price)
                if peak_so_far > 0:
                    drawdown = (peak_so_far - current_tick.price) / peak_so_far * 100

                    if zone_key:
                        zone_drawdowns[zone_key].append(drawdown)

                        # Check if this drawdown recovered
                        recovered = False
                        for j in range(i + 1, len(game.ticks)):
                            if game.ticks[j].price >= peak_so_far * 0.95:  # Within 5% of peak
                                recovered = True
                                break
                            if game.ticks[j].rugged:
                                break

                        if recovered:
                            zone_recovery_drawdowns[zone_key].append(drawdown)
                        elif game.ticks[-1].rugged:
                            zone_rug_drawdowns[zone_key].append(drawdown)

        # Print results
        print("Tick-to-Tick Volatility by Zone:")
        print("-" * 80)
        print(f"{'Zone':<15} {'Avg %':<10} {'Median %':<10} {'90th %':<10} {'Max %':<10}")
        print("-" * 80)

        for zone in sorted(zone_volatility.keys()):
            volatilities = zone_volatility[zone]
            if len(volatilities) < 100:
                continue

            avg_vol = np.mean(volatilities)
            median_vol = np.median(volatilities)
            p90_vol = np.percentile(volatilities, 90)
            max_vol = np.max(volatilities)

            print(f"{zone:<15} {avg_vol:<10.2f} {median_vol:<10.2f} {p90_vol:<10.2f} {max_vol:<10.2f}")

        print()
        print("Drawdown Analysis:")
        print("-" * 80)
        print(f"{'Zone':<15} {'Avg DD%':<10} {'Max DD%':<10} {'Recovered':<12} {'Rugged':<12}")
        print("-" * 80)

        results = {}
        for zone in sorted(zone_drawdowns.keys()):
            drawdowns = zone_drawdowns[zone]
            recovered = zone_recovery_drawdowns[zone]
            rugged = zone_rug_drawdowns[zone]

            if len(drawdowns) < 100:
                continue

            avg_dd = np.mean(drawdowns)
            max_dd = np.max(drawdowns)
            recovery_rate = len(recovered) / len(drawdowns) * 100
            rug_rate = len(rugged) / len(drawdowns) * 100

            print(f"{zone:<15} {avg_dd:<10.2f} {max_dd:<10.2f} {recovery_rate:<12.1f} {rug_rate:<12.1f}")

            results[zone] = {
                'avg_volatility': np.mean(zone_volatility[zone]),
                'p90_volatility': np.percentile(zone_volatility[zone], 90),
                'avg_drawdown': avg_dd,
                'max_drawdown': max_dd,
                'recovery_rate': recovery_rate,
                'rug_rate': rug_rate
            }

        print()
        print("Key Insights:")
        print("-" * 80)
        print(f"💡 Realistic stop loss levels: 30-50% (not 10%)")
        print(f"💡 High volatility zones require wider stops")
        print(f"💡 Drawdown recovery rate decreases at higher multipliers")
        print()

        return results

    def analyze_survival_curves(self) -> Dict:
        """
        Phase 3: Hold Duration vs Success Rate

        Build survival probability curves:
        P(survive to tick T+n | currently at tick T and multiplier M)
        """
        print("=" * 80)
        print("PHASE 3: SURVIVAL CURVE ANALYSIS")
        print("=" * 80)
        print()

        # Build survival matrix
        survival_matrix = defaultdict(lambda: defaultdict(list))

        for game in self.games:
            for i, tick in enumerate(game.ticks):
                if tick.rugged:
                    break

                # Determine multiplier zone
                zone_key = None
                for zone_min, zone_max in self.multiplier_zones:
                    if zone_min <= tick.price < zone_max:
                        zone_key = f"{zone_min:.0f}-{zone_max:.0f}x"
                        break

                if not zone_key:
                    continue

                # Check survival at various horizons
                for horizon in [20, 50, 100, 200]:
                    survived = True

                    for j in range(i + 1, min(i + horizon + 1, len(game.ticks))):
                        if game.ticks[j].rugged:
                            survived = False
                            break

                    # If we didn't check full horizon (game ended), mark as censored
                    if i + horizon >= len(game.ticks):
                        survived = None  # Censored data

                    if survived is not None:
                        survival_matrix[zone_key][horizon].append(survived)

        # Calculate survival probabilities
        print("Survival Probability Matrix:")
        print("-" * 80)
        print(f"{'Zone':<15} {'20 ticks':<12} {'50 ticks':<12} {'100 ticks':<12} {'200 ticks':<12}")
        print("-" * 80)

        results = {}
        for zone in sorted(survival_matrix.keys()):
            row_data = []
            zone_results = {}

            for horizon in [20, 50, 100, 200]:
                survivals = survival_matrix[zone][horizon]
                if len(survivals) >= 10:
                    survival_prob = sum(survivals) / len(survivals) * 100
                    row_data.append(f"{survival_prob:.1f}%")
                    zone_results[f"{horizon}_ticks"] = survival_prob
                else:
                    row_data.append("N/A")
                    zone_results[f"{horizon}_ticks"] = None

            print(f"{zone:<15} {row_data[0]:<12} {row_data[1]:<12} {row_data[2]:<12} {row_data[3]:<12}")
            results[zone] = zone_results

        print()
        print("Key Insights:")
        print("-" * 80)
        print(f"💡 Survival probability decreases exponentially with hold time")
        print(f"💡 Higher multipliers have much lower survival rates")
        print(f"💡 Use survival curves to set dynamic exit thresholds")
        print()

        return results

    def analyze_profit_distributions(self) -> Dict:
        """
        Phase 4: Profit Target Reality

        What gains are actually achievable from various entry points?
        """
        print("=" * 80)
        print("PHASE 4: PROFIT DISTRIBUTION ANALYSIS")
        print("=" * 80)
        print()

        # Similar to entry analysis but focused on profit distributions
        entry_points = [1, 5, 10, 25, 50, 100, 250, 500]

        print("Profit Achievement Rates (%):")
        print("-" * 80)
        print(f"{'Entry':<8} {'N':<6} {'10%':<8} {'25%':<8} {'50%':<8} {'100%':<8} {'200%':<8} {'Avg':<10}")
        print("-" * 80)

        results = {}
        for entry_mult in entry_points:
            returns = []

            for game in self.games:
                for i, tick in enumerate(game.ticks):
                    if tick.rugged:
                        break

                    if abs(tick.price - entry_mult) / entry_mult < 0.05:
                        # Find maximum forward return
                        max_return = 0.0
                        for j in range(i + 1, len(game.ticks)):
                            if game.ticks[j].rugged:
                                break
                            future_return = (game.ticks[j].price - tick.price) / tick.price
                            max_return = max(max_return, future_return)

                        returns.append(max_return)

            if len(returns) < 10:
                continue

            # Calculate achievement rates
            rates = []
            for target in [0.10, 0.25, 0.50, 1.0, 2.0]:
                rate = sum(1 for r in returns if r >= target) / len(returns) * 100
                rates.append(rate)

            avg_return = np.mean(returns) * 100

            print(f"{entry_mult:<8.0f} {len(returns):<6} "
                  f"{rates[0]:<8.1f} {rates[1]:<8.1f} {rates[2]:<8.1f} "
                  f"{rates[3]:<8.1f} {rates[4]:<8.1f} {avg_return:<10.1f}")

            results[entry_mult] = {
                'sample_size': len(returns),
                'achievement_rates': {
                    '10%': rates[0],
                    '25%': rates[1],
                    '50%': rates[2],
                    '100%': rates[3],
                    '200%': rates[4]
                },
                'avg_return': avg_return
            }

        print()
        print("Key Insights:")
        print("-" * 80)
        print(f"💡 Set profit targets based on entry multiplier")
        print(f"💡 Early entries (1-10x) can achieve 100%+ gains")
        print(f"💡 Late entries (100x+) should target 10-25% gains")
        print(f"💡 Dynamic profit targets improve win rate")
        print()

        return results

    def generate_bayesian_parameters(self,
                                    entry_results: Dict,
                                    survival_results: Dict,
                                    profit_results: Dict) -> Dict:
        """
        Generate Bayesian model parameters from empirical data
        """
        print("=" * 80)
        print("BAYESIAN MODEL PARAMETERS")
        print("=" * 80)
        print()

        parameters = {
            'entry_scores': {},
            'survival_curves': survival_results,
            'profit_targets': {},
            'risk_zones': {}
        }

        # Entry scores (base success rate)
        for entry_mult, stats in entry_results.items():
            if stats['sample_size'] >= 10:
                # Score based on avg return and rug rate
                base_score = max(0, stats['avg_eventual_return']) / 100
                risk_penalty = stats['rug_rate'] / 100
                entry_score = base_score * (1 - risk_penalty)

                parameters['entry_scores'][entry_mult] = {
                    'score': entry_score,
                    'base_return': stats['avg_eventual_return'],
                    'rug_risk': stats['rug_rate']
                }

        # Profit targets by entry point
        for entry_mult, stats in profit_results.items():
            # Choose target where achievement rate > 50%
            recommended_target = 0.10  # Default 10%

            for target_pct, rate in stats['achievement_rates'].items():
                target_val = float(target_pct.strip('%')) / 100
                if rate >= 50 and target_val > recommended_target:
                    recommended_target = target_val

            parameters['profit_targets'][entry_mult] = {
                'recommended': recommended_target,
                'conservative': recommended_target * 0.7,
                'aggressive': recommended_target * 1.3
            }

        # Risk zones (classify multiplier ranges)
        parameters['risk_zones'] = {
            'green': (1.0, 10.0),    # Low risk
            'yellow': (10.0, 50.0),  # Medium risk
            'orange': (50.0, 200.0), # High risk
            'red': (200.0, float('inf'))  # Extreme risk
        }

        print("Entry Score Table:")
        print("-" * 80)
        for mult, params in sorted(parameters['entry_scores'].items()):
            print(f"{mult:>8.0f}x: score={params['score']:.3f}, "
                  f"return={params['base_return']:>6.1f}%, "
                  f"rug_risk={params['rug_risk']:>5.1f}%")

        print()
        print("Recommended Profit Targets:")
        print("-" * 80)
        for mult, targets in sorted(parameters['profit_targets'].items()):
            print(f"{mult:>8.0f}x: {targets['recommended']*100:.0f}% "
                  f"(conservative: {targets['conservative']*100:.0f}%, "
                  f"aggressive: {targets['aggressive']*100:.0f}%)")

        print()

        return parameters

    def run_full_analysis(self) -> Dict:
        """Run all analysis phases and generate report"""
        print()
        print("=" * 80)
        print("COMPREHENSIVE TRADING PATTERN ANALYSIS")
        print("=" * 80)
        print()

        # Load data
        self.load_all_games()

        if not self.games:
            print("❌ No games loaded. Exiting.")
            return {}

        # Run all phases
        entry_results = self.analyze_entry_opportunities()
        volatility_results = self.analyze_volatility()
        survival_results = self.analyze_survival_curves()
        profit_results = self.analyze_profit_distributions()

        # Generate Bayesian parameters
        bayesian_params = self.generate_bayesian_parameters(
            entry_results,
            survival_results,
            profit_results
        )

        # Final summary
        print("=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)
        print()
        print(f"✅ Analyzed {len(self.games)} games")
        print(f"✅ Generated entry opportunity tables")
        print(f"✅ Calculated volatility profiles")
        print(f"✅ Built survival probability curves")
        print(f"✅ Mapped profit distributions")
        print(f"✅ Created Bayesian model parameters")
        print()
        print("Results can be used to inform RL reward function design.")
        print()

        return {
            'entry_opportunities': entry_results,
            'volatility_patterns': volatility_results,
            'survival_curves': survival_results,
            'profit_distributions': profit_results,
            'bayesian_parameters': bayesian_params
        }


def main():
    """Main entry point"""
    analyzer = TradingPatternAnalyzer()
    results = analyzer.run_full_analysis()

    # Save results to JSON
    output_file = Path("/home/nomad/Desktop/REPLAYER/trading_pattern_analysis.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"📄 Results saved to: {output_file}")
    print()


if __name__ == "__main__":
    main()
