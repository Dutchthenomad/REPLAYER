"""
Backtest sidebet model with martingale sequencing

Simulates realistic betting with:
- 40-tick sidebet windows
- 5-tick cooldown between bets
- 4-attempt martingale sequences
- Bankroll management
"""

import numpy as np
from typing import List, Dict
from .data_processor import GameDataProcessor
from .feature_extractor import FeatureExtractor


class MartingaleSequence:
    """Manages martingale betting sequence"""

    def __init__(self, base_bet: float = 0.001):
        self.base_bet = base_bet
        self.attempts = [0.001, 0.002, 0.004, 0.008]  # 4 attempts
        self.total_risk = sum(self.attempts)  # 0.015 SOL
        self.max_attempts = 4

    def calculate_outcome(self, attempt_num: int, won: bool) -> float:
        """
        Calculate profit/loss for single bet

        Args:
            attempt_num: 0-3 (which attempt in sequence)
            won: Did we win?

        Returns:
            Net profit (+) or loss (-)
        """
        bet_size = self.attempts[attempt_num]

        if won:
            # 5:1 payout
            return (bet_size * 5) - bet_size  # Net profit
        else:
            return -bet_size


class SidebetBacktester:
    """Backtest sidebet model with realistic constraints"""

    def __init__(self, model, initial_bankroll: float = 0.1):
        self.model = model
        self.initial_bankroll = initial_bankroll
        self.bankroll = initial_bankroll
        self.martingale = MartingaleSequence()

        # Results tracking
        self.total_bets = 0
        self.winning_bets = 0
        self.sequences = []
        self.bankroll_history = [initial_bankroll]

    def backtest(self, game_files: List[str]) -> Dict:
        """
        Run backtest on list of games

        Args:
            game_files: List of paths to JSONL game files

        Returns:
            Dictionary with backtest results
        """
        print(f"\n{'='*60}")
        print(f"BACKTESTING ON {len(game_files)} GAMES")
        print(f"{'='*60}\n")

        processor = GameDataProcessor()
        feature_extractor = FeatureExtractor()

        for i, game_file in enumerate(game_files):
            if i % 50 == 0:
                print(f"Processing game {i+1}/{len(game_files)}...")

            self.backtest_game(game_file, processor, feature_extractor)

            # Check bankruptcy
            if self.bankroll < self.martingale.total_risk:
                print(f"\n⚠️  BANKRUPTCY at game {i+1}")
                print(f"   Bankroll: {self.bankroll:.4f} SOL")
                print(f"   Required: {self.martingale.total_risk:.4f} SOL")
                break

        # Calculate final metrics
        results = self.calculate_results()

        self.print_results(results)

        return results

    def backtest_game(
        self,
        game_file: str,
        processor: GameDataProcessor,
        feature_extractor: FeatureExtractor
    ):
        """Backtest single game"""

        # Process game
        game_data = processor.process_game_file(game_file, feature_extractor)

        if not game_data:
            return

        # Sequence state
        current_sequence = []
        sequence_attempts = 0
        last_bet_tick = 0

        for sample in game_data:
            # Skip early game
            if sample['tick'] < 100:
                continue

            # Check cooldown
            if sample['tick'] - last_bet_tick < 5:
                continue

            # Check if sequence complete
            if sequence_attempts >= 4:
                # Sequence failed (4 losses)
                sequence_attempts = 0
                current_sequence = []
                continue

            # Get prediction
            prediction, probability = self.model.predict(sample['features'])

            if prediction == 1:
                # Place bet
                self.total_bets += 1
                outcome = self.martingale.calculate_outcome(
                    sequence_attempts,
                    sample['label'] == 1
                )

                self.bankroll += outcome

                current_sequence.append({
                    'attempt': sequence_attempts,
                    'tick': sample['tick'],
                    'probability': probability,
                    'won': sample['label'] == 1,
                    'profit': outcome
                })

                if sample['label'] == 1:
                    # WIN - sequence complete
                    self.winning_bets += 1
                    self.sequences.append({
                        'attempts': sequence_attempts + 1,
                        'profit': sum(bet['profit'] for bet in current_sequence),
                        'ticks': [bet['tick'] for bet in current_sequence]
                    })
                    sequence_attempts = 0
                    current_sequence = []
                else:
                    # LOSS - continue sequence
                    sequence_attempts += 1

                last_bet_tick = sample['tick']

                # Skip ahead 45 ticks (40 window + 5 cooldown)
                # This prevents multiple bets in same window
                last_bet_tick = sample['tick'] + 45

        # Record bankroll after game
        self.bankroll_history.append(self.bankroll)

    def calculate_results(self) -> Dict:
        """Calculate final backtest metrics"""

        win_rate = self.winning_bets / max(self.total_bets, 1)
        roi = (self.bankroll - self.initial_bankroll) / self.initial_bankroll

        max_dd = self.calculate_max_drawdown()

        profitable_sequences = sum(1 for s in self.sequences if s['profit'] > 0)

        return {
            'total_bets': self.total_bets,
            'winning_bets': self.winning_bets,
            'win_rate': win_rate,
            'initial_bankroll': self.initial_bankroll,
            'final_bankroll': self.bankroll,
            'profit': self.bankroll - self.initial_bankroll,
            'roi': roi,
            'max_drawdown': max_dd,
            'total_sequences': len(self.sequences),
            'profitable_sequences': profitable_sequences,
            'avg_attempts': np.mean([s['attempts'] for s in self.sequences]) if self.sequences else 0,
            'avg_profit_per_sequence': np.mean([s['profit'] for s in self.sequences]) if self.sequences else 0,
            'bankrupt': self.bankroll < self.martingale.total_risk
        }

    def calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from peak"""
        peak = self.bankroll_history[0]
        max_dd = 0

        for value in self.bankroll_history:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, drawdown)

        return max_dd

    def print_results(self, results: Dict):
        """Print formatted results"""
        print(f"\n{'='*60}")
        print("BACKTEST RESULTS")
        print(f"{'='*60}")

        print(f"\nBetting Performance:")
        print(f"  Total bets: {results['total_bets']}")
        print(f"  Winning bets: {results['winning_bets']}")
        print(f"  Win rate: {results['win_rate']:.3%} {'✅' if results['win_rate'] >= 0.25 else '❌'}")

        print(f"\nBankroll:")
        print(f"  Initial: {results['initial_bankroll']:.4f} SOL")
        print(f"  Final: {results['final_bankroll']:.4f} SOL")
        print(f"  Profit: {results['profit']:+.4f} SOL {'✅' if results['profit'] > 0 else '❌'}")
        print(f"  ROI: {results['roi']:.3%} {'✅' if results['roi'] > 0.3 else '❌'}")
        print(f"  Max Drawdown: {results['max_drawdown']:.3%}")

        print(f"\nSequence Performance:")
        print(f"  Total sequences: {results['total_sequences']}")
        print(f"  Profitable sequences: {results['profitable_sequences']}")
        if results['total_sequences'] > 0:
            seq_success = results['profitable_sequences'] / results['total_sequences']
            print(f"  Sequence success rate: {seq_success:.3%} {'✅' if seq_success >= 0.8 else '❌'}")
        print(f"  Avg attempts: {results['avg_attempts']:.2f}")
        print(f"  Avg profit/sequence: {results['avg_profit_per_sequence']:+.4f} SOL")

        print(f"\nStatus: {'✅ PROFITABLE' if results['roi'] > 0 else '❌ UNPROFITABLE'}")
        if results['bankrupt']:
            print(f"⚠️  BANKRUPT")

        print(f"{'='*60}\n")
