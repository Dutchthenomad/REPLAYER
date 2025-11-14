"""
Feature extractor regression tests
"""

from ml.feature_extractor import FeatureExtractor


def test_calculate_iqr_position_handles_zero_range():
    extractor = FeatureExtractor()
    stats = {
        'q1': 100,
        'q3': 100,
        'median': 100,
        'mean': 100,
        'std': 1
    }

    value = extractor.calculate_iqr_position(100, stats)
    assert value == 0.0
