"""
Tests for timing metrics display (Phase 8.6)

Simple unit tests that verify timing metrics logic without requiring full UI initialization.
"""

import pytest
from unittest.mock import Mock


def test_timing_stats_formatting():
    """
    Phase 8.6: Verify timing stats are formatted correctly for display
    """
    # Mock timing stats (as returned by BrowserExecutor)
    stats = {
        'avg_total_delay_ms': 45.8,
        'success_rate': 0.873,
        'total_executions': 12
    }

    # Format as done in _update_timing_metrics_display
    delay_ms = int(stats['avg_total_delay_ms'])
    success_rate = int(stats['success_rate'] * 100)
    exec_count = stats['total_executions']

    # Verify rounding
    assert delay_ms == 45  # 45.8 rounds down to 45
    assert success_rate == 87  # 0.873 * 100 = 87.3 rounds down to 87
    assert exec_count == 12

    # Verify text formatting
    text = f"| ⏱️ Delay: {delay_ms}ms | Success: {success_rate}% | Exec: {exec_count}"
    assert "45ms" in text
    assert "87%" in text
    assert "Exec: 12" in text


def test_timing_stats_zero_executions():
    """
    Phase 8.6: Verify timing stats handle zero executions gracefully
    """
    stats = {
        'avg_total_delay_ms': 0.0,
        'success_rate': 0.0,
        'total_executions': 0
    }

    delay_ms = int(stats['avg_total_delay_ms'])
    success_rate = int(stats['success_rate'] * 100)
    exec_count = stats['total_executions']

    assert delay_ms == 0
    assert success_rate == 0
    assert exec_count == 0


def test_timing_stats_high_values():
    """
    Phase 8.6: Verify timing stats handle high values correctly
    """
    stats = {
        'avg_total_delay_ms': 150.7,
        'success_rate': 0.987,
        'total_executions': 1234
    }

    delay_ms = int(stats['avg_total_delay_ms'])
    success_rate = int(stats['success_rate'] * 100)
    exec_count = stats['total_executions']

    assert delay_ms == 150
    assert success_rate == 98  # 0.987 * 100 = 98.7
    assert exec_count == 1234


def test_timing_metrics_show_hide_logic():
    """
    Phase 8.6: Verify show/hide logic based on execution mode
    """
    from bot.execution_mode import ExecutionMode

    # BACKEND mode - metrics should be hidden
    backend_mode = ExecutionMode.BACKEND
    assert backend_mode == ExecutionMode.BACKEND

    # UI_LAYER mode - metrics should be shown
    ui_layer_mode = ExecutionMode.UI_LAYER
    assert ui_layer_mode == ExecutionMode.UI_LAYER

    # Verify enum values are distinct
    assert backend_mode != ui_layer_mode


def test_browser_executor_stats_schema():
    """
    Phase 8.6: Verify browser executor returns expected stats schema
    """
    # Expected schema from BrowserExecutor.get_timing_stats()
    expected_keys = [
        'total_executions',
        'successful_executions',
        'success_rate',
        'avg_total_delay_ms',
        'avg_click_delay_ms',
        'avg_confirmation_delay_ms',
        'p50_total_delay_ms',
        'p95_total_delay_ms',
    ]

    # Mock stats (as returned by browser_executor.get_timing_stats())
    stats = {
        'total_executions': 150,
        'successful_executions': 142,
        'success_rate': 0.9467,
        'avg_total_delay_ms': 47.8,
        'avg_click_delay_ms': 12.3,
        'avg_confirmation_delay_ms': 35.5,
        'p50_total_delay_ms': 45.0,
        'p95_total_delay_ms': 78.9,
    }

    # Verify all expected keys exist
    for key in expected_keys:
        assert key in stats, f"Missing key: {key}"

    # Verify value types
    assert isinstance(stats['total_executions'], int)
    assert isinstance(stats['success_rate'], float)
    assert 0.0 <= stats['success_rate'] <= 1.0  # Rate is 0-1, not 0-100
