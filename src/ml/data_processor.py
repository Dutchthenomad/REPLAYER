"""
Data processing pipeline for sidebet training

Processes JSONL game recordings into ML-ready feature vectors with labels.
"""

import json
import numpy as np
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional
import statistics


class RollingStats:
    """Manages rolling game duration statistics"""

    def __init__(self, window_size: int = 10):
        self.game_lengths = deque(maxlen=window_size)
        self.default_stats = {
            'mean': 329.34,
            'median': 281.0,
            'std': 188.24,
            'q1': 201.0,
            'q3': 410.0
        }

    def add_game(self, length: int):
        """Add a game length to rolling window"""
        self.game_lengths.append(length)

    def get_stats(self) -> Dict[str, float]:
        """Get current statistics (rolling or default)"""
        if len(self.game_lengths) >= 5:
            # Have enough data for rolling stats
            lengths = list(self.game_lengths)
            return {
                'mean': statistics.mean(lengths),
                'median': statistics.median(lengths),
                'std': statistics.stdev(lengths) if len(lengths) > 1 else self.default_stats['std'],
                'q1': np.percentile(lengths, 25),
                'q3': np.percentile(lengths, 75)
            }
        else:
            # Use defaults
            return self.default_stats.copy()


class GameDataProcessor:
    """Process raw game JSONL files into ML-ready features"""

    def __init__(self):
        self.rolling_stats = RollingStats()
        self.games_processed = 0

    def process_game_file(self, filepath: str, feature_extractor) -> List[Dict]:
        """
        Convert JSONL game file to tick-by-tick feature vectors

        Args:
            filepath: Path to JSONL game file
            feature_extractor: FeatureExtractor instance

        Returns:
            List of dicts with keys:
            - features: np.ndarray(14,)
            - label: 0 or 1 (rug in next 40 ticks?)
            - tick: int
            - rug_tick: int
        """
        path = Path(filepath)

        if not path.exists():
            print(f"Warning: File not found: {filepath}")
            return []

        # Load events
        try:
            with open(filepath, 'r') as f:
                events = [json.loads(line) for line in f if line.strip()]
        except json.JSONDecodeError as e:
            print(f"Warning: JSON parse error in {filepath}: {e}")
            return []

        # Filter to active game ticks only (including PRESALE phase)
        ticks = []
        for event in events:
            if event.get('type') == 'tick':
                # Check if tick is active (not cooldown)
                # Include PRESALE phase as it's a tradeable phase
                phase = event.get('phase', 'ACTIVE')
                is_tradeable_phase = phase in ['ACTIVE', 'PRESALE'] or event.get('active', True)
                if is_tradeable_phase:
                    ticks.append(event)

        if len(ticks) < 50:
            # Need minimum 50 ticks for meaningful analysis
            return []

        # Extract price series
        prices = []
        for tick in ticks:
            price = tick.get('price', tick.get('multiplier', 1.0))
            prices.append(float(price))

        # Determine rug tick (search in TICKS array, not events!)
        rug_tick = len(ticks) - 1  # Default to last tick
        for i, tick in enumerate(ticks):
            if tick.get('rugged', False):
                rug_tick = i  # Index matches ticks array
                break

        # Generate features for each tick (start at 40 for baseline)
        features_list = []

        # Reset feature extractor state for new game
        feature_extractor.reset_for_new_game()

        for tick_num in range(40, len(ticks)):
            try:
                features = feature_extractor.extract_features(
                    tick_num=tick_num,
                    prices=prices[:tick_num+1],
                    stats=self.rolling_stats.get_stats()
                )

                # Label: Will rug occur in next 80 ticks? (EXPANDED from 40)
                # Rationale: 166-tick average spike-to-rug time means 40-tick
                # window only captures 17.5% of opportunities. 80 ticks = 33.8%
                ticks_to_rug = rug_tick - tick_num
                label = 1 if (0 < ticks_to_rug <= 80) else 0

                features_list.append({
                    'features': features,
                    'label': label,
                    'tick': tick_num,
                    'rug_tick': rug_tick,
                    'ticks_to_rug': ticks_to_rug
                })

            except Exception as e:
                print(f"Warning: Feature extraction failed at tick {tick_num} in {filepath}: {e}")
                continue

        # Update rolling statistics
        self.rolling_stats.add_game(len(ticks))
        self.games_processed += 1

        if self.games_processed % 100 == 0:
            print(f"Processed {self.games_processed} games...")

        return features_list

    def process_multiple_games(
        self,
        game_files: List[str],
        feature_extractor,
        min_tick: int = 100
    ) -> tuple[np.ndarray, np.ndarray, List[Dict]]:
        """
        Process multiple game files

        Args:
            game_files: List of paths to JSONL files
            feature_extractor: FeatureExtractor instance
            min_tick: Minimum tick to include (filter early game noise)

        Returns:
            (features, labels, metadata)
            - features: np.ndarray of shape (N, 14)
            - labels: np.ndarray of shape (N,)
            - metadata: List of dicts with tick info
        """
        all_features = []
        all_labels = []
        all_metadata = []

        print(f"Processing {len(game_files)} game files...")

        for game_file in game_files:
            game_data = self.process_game_file(game_file, feature_extractor)

            for sample in game_data:
                # Filter to avoid early game noise
                if sample['tick'] >= min_tick:
                    all_features.append(sample['features'])
                    all_labels.append(sample['label'])
                    all_metadata.append({
                        'tick': sample['tick'],
                        'rug_tick': sample['rug_tick'],
                        'ticks_to_rug': sample['ticks_to_rug'],
                        'game_file': game_file
                    })

        # Convert to numpy arrays
        X = np.array(all_features)
        y = np.array(all_labels)

        print(f"\nDataset Summary:")
        print(f"  Total samples: {len(X)}")
        print(f"  Positive samples: {y.sum()} ({y.mean():.1%})")
        print(f"  Negative samples: {(1-y).sum()} ({(1-y).mean():.1%})")
        print(f"  Feature shape: {X.shape}")

        return X, y, all_metadata

    def get_summary(self) -> Dict:
        """Get processing summary"""
        return {
            'games_processed': self.games_processed,
            'current_stats': self.rolling_stats.get_stats(),
            'using_rolling': len(self.rolling_stats.game_lengths) >= 5
        }
