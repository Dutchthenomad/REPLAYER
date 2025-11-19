"""
Unit tests for BotUIController incremental button clicking

Phase A.5: Comprehensive tests for incremental clicking logic
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch, call
import time

from bot.ui_controller import BotUIController


@pytest.fixture
def mock_main_window():
    """Create mock main_window with all required button references"""
    window = Mock()

    # Mock root.after to execute scheduled actions immediately
    def mock_after(delay, action):
        action()  # Execute immediately for testing
    window.root = Mock()
    window.root.after = Mock(side_effect=mock_after)

    # Mock ui_dispatcher.submit to execute immediately
    def mock_submit(action):
        action()  # Execute immediately for testing
    window.ui_dispatcher = Mock()
    window.ui_dispatcher.submit = Mock(side_effect=mock_submit)

    # Mock all increment buttons (Phase A.2 requirement)
    window.clear_button = Mock()
    window.increment_001_button = Mock()
    window.increment_01_button = Mock()
    window.increment_10_button = Mock()
    window.increment_1_button = Mock()
    window.half_button = Mock()
    window.double_button = Mock()
    window.max_button = Mock()

    # Mock action buttons
    window.buy_button = Mock()
    window.sell_button = Mock()
    window.sidebet_button = Mock()

    # Mock percentage buttons
    window.percentage_buttons = {
        0.1: {'button': Mock()},
        0.25: {'button': Mock()},
        0.5: {'button': Mock()},
        1.0: {'button': Mock()},
    }

    # Mock entry field
    window.bet_entry = Mock()
    window.bet_entry.get.return_value = "0.0"

    # Mock labels for reading state
    window.balance_label = Mock()
    window.balance_label.cget.return_value = "Balance: 0.100 SOL"

    window.position_label = Mock()
    window.position_label.cget.return_value = "Position: None"

    window.price_label = Mock()
    window.price_label.cget.return_value = "PRICE: 1.50x"

    return window


@pytest.fixture
def ui_controller(mock_main_window):
    """Create BotUIController with mocked main_window"""
    return BotUIController(mock_main_window)


class TestClickIncrementButton:
    """Test clicking individual increment buttons"""

    def test_click_001_button_once(self, ui_controller, mock_main_window):
        """Test clicking +0.001 button once"""
        result = ui_controller.click_increment_button('+0.001', 1)

        assert result is True
        assert mock_main_window.increment_001_button.invoke.call_count == 1

    def test_click_001_button_multiple(self, ui_controller, mock_main_window):
        """Test clicking +0.001 button 3 times"""
        result = ui_controller.click_increment_button('+0.001', 3)

        assert result is True
        assert mock_main_window.increment_001_button.invoke.call_count == 3

    def test_click_01_button(self, ui_controller, mock_main_window):
        """Test clicking +0.01 button"""
        result = ui_controller.click_increment_button('+0.01', 2)

        assert result is True
        assert mock_main_window.increment_01_button.invoke.call_count == 2

    def test_click_10_button(self, ui_controller, mock_main_window):
        """Test clicking +0.1 button"""
        result = ui_controller.click_increment_button('+0.1', 5)

        assert result is True
        assert mock_main_window.increment_10_button.invoke.call_count == 5

    def test_click_1_button(self, ui_controller, mock_main_window):
        """Test clicking +1 button"""
        result = ui_controller.click_increment_button('+1', 1)

        assert result is True
        assert mock_main_window.increment_1_button.invoke.call_count == 1

    def test_click_clear_button(self, ui_controller, mock_main_window):
        """Test clicking X (clear) button"""
        result = ui_controller.click_increment_button('X', 1)

        assert result is True
        assert mock_main_window.clear_button.invoke.call_count == 1

    def test_click_half_button(self, ui_controller, mock_main_window):
        """Test clicking 1/2 (half) button"""
        result = ui_controller.click_increment_button('1/2', 1)

        assert result is True
        assert mock_main_window.half_button.invoke.call_count == 1

    def test_click_double_button(self, ui_controller, mock_main_window):
        """Test clicking X2 (double) button"""
        result = ui_controller.click_increment_button('X2', 1)

        assert result is True
        assert mock_main_window.double_button.invoke.call_count == 1

    def test_click_max_button(self, ui_controller, mock_main_window):
        """Test clicking MAX button"""
        result = ui_controller.click_increment_button('MAX', 1)

        assert result is True
        assert mock_main_window.max_button.invoke.call_count == 1

    def test_click_invalid_button(self, ui_controller, mock_main_window):
        """Test clicking invalid button type returns False"""
        result = ui_controller.click_increment_button('INVALID', 1)

        assert result is False

    def test_click_timing_delays(self, ui_controller, mock_main_window):
        """Test that multiple clicks have delays between them"""
        start_time = time.time()

        # Click 5 times (should have 4 delays of 10-50ms each)
        ui_controller.click_increment_button('+0.001', 5)

        elapsed = time.time() - start_time

        # 4 delays × 10ms minimum = 40ms minimum
        # Allow some buffer for execution overhead
        assert elapsed >= 0.035, f"Expected delays, got {elapsed*1000:.1f}ms"


class TestBuildAmountIncrementally:
    """Test building amounts by clicking increment buttons"""

    def test_build_simple_amount_003(self, ui_controller, mock_main_window):
        """Test: 0.003 → X, +0.001, X2 (optimized)"""
        result = ui_controller.build_amount_incrementally(Decimal('0.003'))

        assert result is True

        # Verify button sequence (Phase A.6 smart algorithm: uses X2 optimization)
        # 0.003 = 0.0015 × 2 = (+0.001) × 2 (2 clicks vs 3 clicks)
        assert mock_main_window.clear_button.invoke.call_count == 1  # X once
        assert mock_main_window.increment_001_button.invoke.call_count == 1  # +0.001 once
        assert mock_main_window.double_button.invoke.call_count == 1  # X2 once

    def test_build_amount_015(self, ui_controller, mock_main_window):
        """Test: 0.015 → X, +0.01 (1x), +0.001 (5x)"""
        result = ui_controller.build_amount_incrementally(Decimal('0.015'))

        assert result is True

        # Verify button sequence
        assert mock_main_window.clear_button.invoke.call_count == 1
        assert mock_main_window.increment_01_button.invoke.call_count == 1  # +0.01 once
        assert mock_main_window.increment_001_button.invoke.call_count == 5  # +0.001 five times

    def test_build_complex_amount_1234(self, ui_controller, mock_main_window):
        """Test: 1.234 → X, +1 (1x), +0.1 (2x), +0.01 (3x), +0.001 (4x)"""
        result = ui_controller.build_amount_incrementally(Decimal('1.234'))

        assert result is True

        # Verify button sequence
        assert mock_main_window.clear_button.invoke.call_count == 1
        assert mock_main_window.increment_1_button.invoke.call_count == 1  # +1 once
        assert mock_main_window.increment_10_button.invoke.call_count == 2  # +0.1 twice
        assert mock_main_window.increment_01_button.invoke.call_count == 3  # +0.01 three times
        assert mock_main_window.increment_001_button.invoke.call_count == 4  # +0.001 four times

    def test_build_amount_050(self, ui_controller, mock_main_window):
        """Test: 0.050 → X, +0.1, 1/2 (optimized)"""
        result = ui_controller.build_amount_incrementally(Decimal('0.050'))

        assert result is True

        # Verify button sequence (Phase A.6 smart algorithm: uses 1/2 optimization)
        # 0.050 = 0.1 / 2 (2 clicks vs 5 clicks)
        assert mock_main_window.clear_button.invoke.call_count == 1
        assert mock_main_window.increment_10_button.invoke.call_count == 1  # +0.1 once
        assert mock_main_window.half_button.invoke.call_count == 1  # 1/2 once
        # Should NOT click +0.01 or +0.001 buttons
        assert mock_main_window.increment_01_button.invoke.call_count == 0
        assert mock_main_window.increment_001_button.invoke.call_count == 0

    def test_build_amount_100(self, ui_controller, mock_main_window):
        """Test: 1.0 → X, +1 (1x)"""
        result = ui_controller.build_amount_incrementally(Decimal('1.0'))

        assert result is True

        # Verify button sequence
        assert mock_main_window.clear_button.invoke.call_count == 1
        assert mock_main_window.increment_1_button.invoke.call_count == 1  # +1 once
        # Should NOT click smaller buttons
        assert mock_main_window.increment_10_button.invoke.call_count == 0
        assert mock_main_window.increment_01_button.invoke.call_count == 0
        assert mock_main_window.increment_001_button.invoke.call_count == 0

    def test_build_zero_amount(self, ui_controller, mock_main_window):
        """Test: 0.0 → X only (no increments needed)"""
        result = ui_controller.build_amount_incrementally(Decimal('0.0'))

        assert result is True

        # Verify only clear button clicked
        assert mock_main_window.clear_button.invoke.call_count == 1
        assert mock_main_window.increment_1_button.invoke.call_count == 0
        assert mock_main_window.increment_10_button.invoke.call_count == 0
        assert mock_main_window.increment_01_button.invoke.call_count == 0
        assert mock_main_window.increment_001_button.invoke.call_count == 0

    def test_build_timing_delays(self, ui_controller, mock_main_window):
        """Test that building has delays between button types"""
        start_time = time.time()

        # Build 0.015 (requires clear + 2 different button types)
        ui_controller.build_amount_incrementally(Decimal('0.015'))

        elapsed = time.time() - start_time

        # Delays: After clear, after +0.01, after +0.001 = 3 delays × 10ms = 30ms minimum
        # Plus 4 delays within +0.001 button clicks (5 times) = 4 × 10ms = 40ms minimum
        # Total minimum: 70ms
        assert elapsed >= 0.060, f"Expected delays, got {elapsed*1000:.1f}ms"

    def test_clear_failure_propagates(self, ui_controller, mock_main_window):
        """Test that failure to clear returns False immediately"""
        # Make clear button fail
        def fail_clear():
            raise Exception("Clear failed")

        mock_main_window.clear_button.invoke.side_effect = fail_clear

        result = ui_controller.build_amount_incrementally(Decimal('0.003'))

        assert result is False
        # Should not attempt increment buttons if clear failed
        assert mock_main_window.increment_001_button.invoke.call_count == 0


class TestCompositeActions:
    """Test composite actions using incremental clicking"""

    def test_execute_buy_with_amount(self, ui_controller, mock_main_window):
        """Test execute_buy_with_amount uses incremental clicking"""
        result = ui_controller.execute_buy_with_amount(Decimal('0.003'))

        assert result is True

        # Verify incremental clicking was used (Phase A.6 smart algorithm: uses X2)
        assert mock_main_window.clear_button.invoke.call_count == 1
        assert mock_main_window.increment_001_button.invoke.call_count == 1  # +0.001 once
        assert mock_main_window.double_button.invoke.call_count == 1  # X2 once

        # Verify BUY button clicked
        assert mock_main_window.buy_button.invoke.call_count == 1

    def test_execute_sidebet_with_amount(self, ui_controller, mock_main_window):
        """Test execute_sidebet_with_amount uses incremental clicking"""
        result = ui_controller.execute_sidebet_with_amount(Decimal('0.006'))

        assert result is True

        # Verify incremental clicking was used (Phase A.6 smart algorithm: uses X2)
        # 0.006 = 0.003 × 2 = (0.001 × 3) × 2 = (+0.001) × X2 (optimized)
        assert mock_main_window.clear_button.invoke.call_count == 1
        assert mock_main_window.increment_001_button.invoke.call_count == 3  # +0.001 three times
        assert mock_main_window.double_button.invoke.call_count == 1  # X2 once

        # Verify SIDEBET button clicked
        assert mock_main_window.sidebet_button.invoke.call_count == 1

    def test_execute_buy_fails_if_build_fails(self, ui_controller, mock_main_window):
        """Test that BUY is not clicked if amount building fails"""
        # Make clear fail
        def fail_clear():
            raise Exception("Clear failed")

        mock_main_window.clear_button.invoke.side_effect = fail_clear

        result = ui_controller.execute_buy_with_amount(Decimal('0.003'))

        assert result is False
        # BUY should not be clicked if amount building failed
        assert mock_main_window.buy_button.invoke.call_count == 0
