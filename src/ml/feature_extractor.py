"""
Feature extraction for sidebet prediction

Extracts 14 strategic features organized in 4 groups:
1. Statistical Position (3 features)
2. Volatility Evolution (4 features)
3. Spike Pattern (3 features)
4. Strategic Context (4 features)
"""

import numpy as np
from collections import deque
from typing import List, Dict, Optional


class FeatureExtractor:
    """Extract 14-dimensional feature vector for sidebet prediction"""

    def __init__(self):
        # State tracking
        self.spike_history = []
        self.volatility_history = deque(maxlen=20)
        self.last_bet_tick = 0

        # Configuration
        self.baseline_window = 40
        self.current_window = 10
        self.spike_threshold = 2.0

    def reset_for_new_game(self):
        """Reset state for new game"""
        self.spike_history = []
        self.volatility_history = deque(maxlen=20)
        self.last_bet_tick = 0

    def extract_features(
        self,
        tick_num: int,
        prices: List[float],
        stats: Dict[str, float]
    ) -> np.ndarray:
        """
        Extract 14-dimensional feature vector

        Args:
            tick_num: Current tick number
            prices: Price history up to and including current tick
            stats: Rolling statistics dict with keys: mean, median, std, q1, q3

        Returns:
            np.ndarray of shape (14,) with normalized features
        """
        # Group 1: Statistical Position (3 features)
        tick_percentile = self.calculate_tick_percentile(tick_num, stats)
        z_score = self.calculate_z_score(tick_num, stats)
        iqr_position = self.calculate_iqr_position(tick_num, stats)

        # Group 2: Volatility Evolution (4 features)
        volatility_features = self.calculate_volatility_features(prices)

        # Group 3: Spike Pattern (3 features)
        spike_features = self.calculate_spike_features(
            tick_num,
            volatility_features['ratio']
        )

        # Group 4: Strategic Context (4 features)
        theta_factor = self.calculate_theta_factor(tick_num, stats)
        sequence_feasibility = self.calculate_sequence_feasibility(
            tick_num,
            stats['mean'] + stats['std']  # Expected game length
        )
        cooldown_status = self.calculate_cooldown_status(tick_num)
        pattern_signal = 0.0  # Placeholder for future pattern detection

        # Assemble feature vector
        features = np.array([
            # Statistical Position
            tick_percentile,
            np.clip(z_score, -3, 3),
            iqr_position,

            # Volatility Evolution
            np.clip(volatility_features['ratio'], 0, 10),
            np.clip(volatility_features['momentum'], -1, 1),
            volatility_features['intensity'],
            np.clip(volatility_features['acceleration'], -1, 1),

            # Spike Pattern
            spike_features['frequency'],
            np.clip(spike_features['spacing'], 0, 2),
            spike_features['death_spike_score'],

            # Strategic Context
            theta_factor,
            sequence_feasibility,
            cooldown_status,
            pattern_signal
        ], dtype=np.float32)

        return features

    # =========================================================================
    # Group 1: Statistical Position
    # =========================================================================

    def calculate_tick_percentile(self, tick_num: int, stats: Dict) -> float:
        """Where are we in typical game distribution?"""
        return min(2.0, tick_num / max(stats['median'], 1))

    def calculate_z_score(self, tick_num: int, stats: Dict) -> float:
        """How many standard deviations from mean?"""
        return (tick_num - stats['mean']) / max(stats['std'], 1)

    def calculate_iqr_position(self, tick_num: int, stats: Dict) -> float:
        """Position within interquartile range"""
        if tick_num < stats['q1']:
            return -1.0
        elif tick_num > stats['q3']:
            return 1.0
        else:
            # Linear interpolation between Q1 and Q3
            denominator = stats['q3'] - stats['q1']
            if denominator == 0:
                return 0.0
            return 2 * (tick_num - stats['q1']) / denominator - 1

    # =========================================================================
    # Group 2: Volatility Evolution
    # =========================================================================

    def calculate_volatility_features(self, prices: List[float]) -> Dict:
        """Calculate volatility-based features"""

        # Baseline volatility (first 40 ticks)
        baseline_prices = prices[:self.baseline_window]
        baseline_vol = self.calculate_volatility(baseline_prices)

        # Current volatility (last 10 ticks)
        current_prices = prices[-self.current_window:]
        current_vol = self.calculate_volatility(current_prices)

        # Ratio (handle zero volatility edge case)
        if baseline_vol > 0:
            ratio = current_vol / baseline_vol
        else:
            # Both baseline and current are zero (constant prices)
            ratio = 1.0  # No change from baseline

        self.volatility_history.append(ratio)

        # Momentum (rate of change)
        if len(self.volatility_history) >= 2:
            momentum = self.volatility_history[-1] - self.volatility_history[-2]
        else:
            momentum = 0.0

        # Intensity (relative to max seen)
        if self.volatility_history and max(self.volatility_history) > 0:
            intensity = ratio / max(self.volatility_history)
        else:
            intensity = 0.0

        # Acceleration (second derivative)
        if len(self.volatility_history) >= 3:
            acceleration = (
                self.volatility_history[-1] -
                2 * self.volatility_history[-2] +
                self.volatility_history[-3]
            )
        else:
            acceleration = 0.0

        return {
            'ratio': ratio,
            'momentum': momentum,
            'intensity': intensity,
            'acceleration': acceleration
        }

    def calculate_volatility(self, prices: List[float]) -> float:
        """Calculate volatility as mean absolute percentage change"""
        if len(prices) < 2:
            return 0.0

        changes = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                change = abs(prices[i] - prices[i-1]) / prices[i-1]
                changes.append(change)

        return np.mean(changes) if changes else 0.0

    # =========================================================================
    # Group 3: Spike Pattern
    # =========================================================================

    def calculate_spike_features(self, tick_num: int, current_ratio: float) -> Dict:
        """Calculate spike pattern features"""

        # Track spikes (ratio >= 2.0x)
        if current_ratio >= self.spike_threshold:
            # Only add if not already added (avoid duplicates in same window)
            if not self.spike_history or self.spike_history[-1]['tick'] < tick_num - 5:
                self.spike_history.append({
                    'tick': tick_num,
                    'ratio': current_ratio
                })

        # Frequency
        spike_frequency = len(self.spike_history) / max(tick_num, 1)
        spike_frequency = min(1.0, spike_frequency * 100)  # Normalize

        # Spacing
        if len(self.spike_history) >= 2:
            spacings = [
                self.spike_history[i]['tick'] - self.spike_history[i-1]['tick']
                for i in range(1, len(self.spike_history))
            ]
            avg_spacing = np.mean(spacings)
            expected_spacing = tick_num / max(len(self.spike_history), 1)
            spike_spacing = avg_spacing / max(expected_spacing, 1)
        else:
            spike_spacing = 1.0

        # Death spike score (KEY FEATURE)
        death_spike_score = self.calculate_death_spike_score(
            self.spike_history,
            current_ratio
        )

        return {
            'frequency': spike_frequency,
            'spacing': spike_spacing,
            'death_spike_score': death_spike_score
        }

    def calculate_death_spike_score(
        self,
        spike_history: List[Dict],
        current_ratio: float
    ) -> float:
        """
        ⭐ KEY FEATURE: Distinguish death spike from normal spike

        Captures three critical factors:
        1. Sequence position (4th spike is typical death spike)
        2. Magnitude escalation (30% jump from last spike)
        3. Absolute magnitude (5x+ is strong independent signal)

        Based on findings:
        - 67.4% of rugs have multiple spikes
        - Average 4.04 spikes per game
        - Need to identify THE death spike, not just any spike
        """
        score = 0.0

        # Factor 1: Sequence position (4th spike typical)
        # Weight: 0.3 (30% of score)
        spike_position_score = min(1.0, len(spike_history) / 4.0)
        score += spike_position_score * 0.3

        # Factor 2: Magnitude escalation (30% jump from last spike)
        # Weight: 0.3 (30% of score)
        if len(spike_history) >= 2:
            if current_ratio > spike_history[-1]['ratio'] * 1.3:
                score += 0.3

        # Factor 3: Absolute magnitude (5x+ is strong signal)
        # Weight: 0.4 (40% of score)
        # Scales from 0 at 2x to 1 at 5x
        magnitude_score = min(1.0, max(0, (current_ratio - 2.0) / 3.0))
        score += magnitude_score * 0.4

        return min(1.0, score)

    # =========================================================================
    # Group 4: Strategic Context
    # =========================================================================

    def calculate_theta_factor(self, tick_num: int, stats: Dict) -> float:
        """
        Bayesian probability acceleration factor

        Accelerates risk assessment based on statistical position:
        - Q1: 0.5 (slow acceleration)
        - Median: 1.0 (normal)
        - Mean: 1.5 (accelerating)
        - Q3: 2.5 (rapid)
        - >Q3: 4.0 (extreme)
        """
        if tick_num < stats['q1']:
            return 0.5
        elif tick_num < stats['median']:
            return 1.0
        elif tick_num < stats['mean']:
            return 1.5
        elif tick_num < stats['q3']:
            return 2.5
        else:  # Beyond Q3
            return 4.0

    def calculate_sequence_feasibility(
        self,
        current_tick: int,
        expected_total: float
    ) -> float:
        """
        Can we complete a 4-attempt martingale sequence?

        Each attempt needs:
        - 40 tick window
        - 5 tick cooldown
        = 45 ticks per attempt

        Returns:
        - 0: Can't complete 1 attempt
        - 1.0: Exactly 4 attempts possible
        - >1.0: Plenty of time
        """
        expected_remaining = max(0, expected_total - current_tick)
        windows_possible = expected_remaining / 45
        return min(2.0, windows_possible / 4.0)

    def calculate_cooldown_status(self, tick_num: int) -> float:
        """
        When can we bet next?

        Returns:
        - 0.0: In cooldown (can't bet)
        - 1.0: Ready to bet
        """
        ticks_until_can_bet = max(0, self.last_bet_tick + 5 - tick_num)
        return 1.0 - (ticks_until_can_bet / 5.0)

    def record_bet_placed(self, tick_num: int):
        """Record that a bet was placed (updates cooldown)"""
        self.last_bet_tick = tick_num


# Feature names for interpretation
FEATURE_NAMES = [
    'tick_percentile',
    'z_score',
    'iqr_position',
    'volatility_ratio',
    'volatility_momentum',
    'spike_intensity',
    'volatility_acceleration',
    'spike_frequency',
    'spike_spacing',
    'death_spike_score',      # ⭐ KEY FEATURE
    'theta_factor',
    'sequence_feasibility',
    'cooldown_status',
    'pattern_signal'
]
