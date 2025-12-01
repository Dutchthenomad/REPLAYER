"""
SidebetPredictor - Real-time Rug Probability Prediction Wrapper

Wraps the trained sidebet model v3 to provide tick-by-tick rug probability
predictions with actionable signals for the RL trading bot.

Features:
- Real-time rug probability predictions
- Confidence scoring based on feature quality
- Signal strength classification (low/medium/high/critical)
- Recommended actions (hold/reduce/exit/emergency)
- Timing estimates (ticks until predicted rug)

Usage:
    predictor = SidebetPredictor(model_path='./models/sidebet_model_gb_20251107_195802.pkl')

    # For each tick in the game
    prediction = predictor.predict_rug_probability(
        tick_num=current_tick,
        prices=price_history
    )

    if prediction['signal_strength'] == 'critical':
        # EMERGENCY EXIT
        close_all_positions()
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from .model import SidebetModel
from .feature_extractor import FeatureExtractor, FEATURE_NAMES


class SidebetPredictor:
    """
    Real-time sidebet prediction wrapper

    Wraps the trained v3 model and feature extractor to provide
    tick-by-tick rug probability predictions with actionable signals.
    """

    def __init__(
        self,
        model_path: str,
        game_stats: Optional[Dict[str, float]] = None
    ):
        """
        Initialize predictor

        Args:
            model_path: Path to trained sidebet model (.pkl file)
            game_stats: Rolling game statistics (mean, median, std, q1, q3)
                       If None, will use default Rugs.fun statistics
        """
        self.model = SidebetModel()
        self.model.load(model_path)

        self.feature_extractor = FeatureExtractor()

        # Default Rugs.fun game statistics (from historical data)
        # These are used if no custom stats are provided
        self.default_stats = {
            'mean': 329.0,     # Mean game duration (ticks)
            'median': 281.0,   # Median game duration
            'std': 180.0,      # Standard deviation
            'q1': 186.0,       # First quartile
            'q3': 424.0        # Third quartile
        }

        self.game_stats = game_stats or self.default_stats

        # Feature importance weights from v3 training
        # Used for confidence calculation
        self.feature_weights = {
            'z_score': 0.6364,          # Dominant feature
            'spike_spacing': 0.1343,
            'spike_frequency': 0.0840,
            'sequence_feasibility': 0.0409,
            'tick_percentile': 0.0390,
        }

        print(f"SidebetPredictor initialized")
        print(f"  Model: {Path(model_path).name}")
        print(f"  Optimal threshold: {self.model.optimal_threshold:.3f}")
        print(f"  Game stats: mean={self.game_stats['mean']:.0f}, median={self.game_stats['median']:.0f}")

    def reset_for_new_game(self):
        """Reset state for a new game"""
        self.feature_extractor.reset_for_new_game()

    def update_game_stats(self, stats: Dict[str, float]):
        """
        Update rolling game statistics

        Args:
            stats: Dictionary with keys: mean, median, std, q1, q3
        """
        self.game_stats = stats

    def predict_rug_probability(
        self,
        tick_num: int,
        prices: List[float]
    ) -> Dict[str, any]:
        """
        Predict rug probability for current tick

        Args:
            tick_num: Current tick number (0-indexed)
            prices: Price history up to and including current tick

        Returns:
            Dictionary with prediction details:
            {
                'probability': float,           # 0.0-1.0 rug probability
                'confidence': float,            # 0.0-1.0 prediction confidence
                'ticks_to_rug_estimate': int,   # Estimated ticks until rug
                'signal_strength': str,         # 'low'|'medium'|'high'|'critical'
                'recommended_action': str,      # 'hold'|'reduce'|'exit'|'emergency'
                'features': np.ndarray,         # Raw feature vector (14 dims)
                'feature_dict': dict            # Named features for debugging
            }
        """
        # Extract features
        features = self.feature_extractor.extract_features(
            tick_num=tick_num,
            prices=prices,
            stats=self.game_stats
        )

        # Get model prediction
        prediction, probability = self.model.predict(features)

        # Calculate confidence based on feature quality
        confidence = self._calculate_confidence(features)

        # Classify signal strength based on probability thresholds
        if probability >= 0.50:
            signal_strength = 'critical'
            recommended_action = 'emergency'
        elif probability >= 0.40:
            signal_strength = 'high'
            recommended_action = 'exit'
        elif probability >= 0.30:
            signal_strength = 'medium'
            recommended_action = 'reduce'
        else:
            signal_strength = 'low'
            recommended_action = 'hold'

        # Estimate timing (ticks until rug)
        ticks_to_rug_estimate = self._estimate_timing(probability, tick_num)

        # Create feature dictionary for debugging
        feature_dict = dict(zip(FEATURE_NAMES, features))

        return {
            'probability': float(probability),
            'confidence': float(confidence),
            'ticks_to_rug_estimate': int(ticks_to_rug_estimate),
            'signal_strength': signal_strength,
            'recommended_action': recommended_action,
            'features': features,
            'feature_dict': feature_dict
        }

    def _calculate_confidence(self, features: np.ndarray) -> float:
        """
        Calculate prediction confidence based on feature quality

        Confidence is based on:
        1. Strength of dominant features (z_score, spike_spacing)
        2. Game progression (early game = low confidence)
        3. Feature consistency (multiple signals agreeing)

        Args:
            features: 14-dimensional feature vector

        Returns:
            Confidence score in [0, 1]
        """
        # Extract key features by index
        # See FEATURE_NAMES for mapping
        tick_percentile = features[0]
        z_score = features[1]
        volatility_ratio = features[3]
        spike_frequency = features[7]
        spike_spacing = features[8]
        death_spike_score = features[9]

        confidence = 0.0

        # Component 1: z_score strength (dominant feature, 63.64% importance)
        # High z_score (game lasting abnormally long) = high confidence
        z_score_component = min(1.0, abs(z_score) / 3.0) * self.feature_weights['z_score']
        confidence += z_score_component

        # Component 2: Spike pattern signals (13.43% + 8.40% importance)
        spike_component = (
            spike_spacing * self.feature_weights['spike_spacing'] +
            spike_frequency * self.feature_weights['spike_frequency']
        )
        confidence += spike_component

        # Component 3: Game progression (early game = low confidence)
        # Only confident after reaching at least 50% of median duration
        progression_component = min(1.0, tick_percentile) * self.feature_weights['tick_percentile']
        confidence += progression_component

        # Component 4: Death spike signal (emergency boost)
        # If death spike is detected, add emergency confidence boost
        if death_spike_score > 0.7:
            confidence += 0.1  # Emergency boost

        # Normalize to [0, 1]
        # Maximum theoretical confidence from weighted sum
        max_confidence = sum([
            self.feature_weights['z_score'],
            self.feature_weights['spike_spacing'],
            self.feature_weights['spike_frequency'],
            self.feature_weights['tick_percentile']
        ]) + 0.1  # Plus emergency boost

        confidence = min(1.0, confidence / max_confidence)

        return confidence

    def _estimate_timing(self, probability: float, current_tick: int) -> int:
        """
        Estimate ticks until rug based on probability and current position

        Based on the 80-tick label window from training:
        - High probability (>0.50) = very soon (10-20 ticks)
        - Medium probability (0.30-0.50) = moderate (20-40 ticks)
        - Low probability (<0.30) = distant (40-80 ticks)

        Args:
            probability: Predicted rug probability
            current_tick: Current tick number

        Returns:
            Estimated ticks until rug
        """
        if probability >= 0.50:
            # Critical - rug is imminent
            return 10
        elif probability >= 0.40:
            # High risk - exit soon
            return 20
        elif probability >= 0.30:
            # Medium risk - monitor closely
            return 40
        else:
            # Low risk - still within 80-tick window
            return 80

    def get_model_info(self) -> Dict[str, any]:
        """
        Get model metadata

        Returns:
            Dictionary with model information
        """
        return {
            'model_type': 'GradientBoostingClassifier',
            'optimal_threshold': self.model.optimal_threshold,
            'is_trained': self.model.is_trained,
            'feature_count': 14,
            'feature_names': FEATURE_NAMES,
            'game_stats': self.game_stats,
            'feature_weights': self.feature_weights
        }

    def get_prediction_summary(self, prediction: Dict) -> str:
        """
        Get human-readable prediction summary

        Args:
            prediction: Prediction dictionary from predict_rug_probability()

        Returns:
            Formatted string summary
        """
        prob = prediction['probability']
        conf = prediction['confidence']
        strength = prediction['signal_strength']
        action = prediction['recommended_action']
        ticks = prediction['ticks_to_rug_estimate']

        # Signal emoji
        emoji_map = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🟠',
            'critical': '🔴'
        }
        emoji = emoji_map.get(strength, '⚪')

        summary = (
            f"{emoji} Rug Probability: {prob:.1%} (confidence: {conf:.1%})\n"
            f"   Signal: {strength.upper()} | Action: {action.upper()}\n"
            f"   Estimate: ~{ticks} ticks until rug"
        )

        # Add key feature insights
        features = prediction['feature_dict']
        z_score = features['z_score']
        tick_pct = features['tick_percentile']
        death_spike = features['death_spike_score']

        summary += (
            f"\n   Key Features: z_score={z_score:.2f}, "
            f"tick_pct={tick_pct:.2f}, death_spike={death_spike:.2f}"
        )

        return summary


# Convenience function for quick testing
def test_predictor(model_path: str, prices: List[float]):
    """
    Quick test function for the predictor

    Args:
        model_path: Path to trained model
        prices: Price history to test
    """
    predictor = SidebetPredictor(model_path)

    print("\n" + "="*70)
    print("SIDEBET PREDICTOR TEST")
    print("="*70)

    # Test predictions at different ticks
    test_ticks = [50, 100, 200, 300]

    for tick in test_ticks:
        if tick < len(prices):
            prediction = predictor.predict_rug_probability(
                tick_num=tick,
                prices=prices[:tick+1]
            )

            print(f"\nTick {tick}:")
            print(predictor.get_prediction_summary(prediction))

    print("\n" + "="*70)


if __name__ == "__main__":
    # Example usage
    print("SidebetPredictor module")
    print("Import and use with: from rugs_bot.sidebet.predictor import SidebetPredictor")
