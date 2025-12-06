"""
TDD Tests for TradingController Demo Recording (Phase 10)

Tests that TradingController integrates with DemoRecorderSink
to record all button presses for imitation learning.

RED PHASE: These tests will fail until implementation is added.
"""

import pytest
import sys
import importlib.util
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal
from pathlib import Path
import tempfile

# Import TradingController directly to avoid ui/__init__.py cascade
# which triggers sources/__init__.py and requires socketio
_src_dir = Path(__file__).parent.parent.parent
spec = importlib.util.spec_from_file_location(
    "trading_controller",
    _src_dir / "ui" / "controllers" / "trading_controller.py"
)
_tc_module = importlib.util.module_from_spec(spec)
sys.modules["trading_controller"] = _tc_module
spec.loader.exec_module(_tc_module)
TradingController = _tc_module.TradingController

from core.demo_recorder import DemoRecorderSink
from models.demo_action import StateSnapshot as DemoStateSnapshot, ActionCategory


@pytest.fixture
def temp_demo_dir():
    """Create temp directory for demo recordings"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def demo_recorder(temp_demo_dir):
    """Create demo recorder with active session and game"""
    recorder = DemoRecorderSink(temp_demo_dir)
    recorder.start_session()
    recorder.start_game("test-game-123")
    yield recorder
    recorder.close()


@pytest.fixture
def mock_state():
    """Create mock GameState with capture_demo_snapshot support"""
    state = Mock()
    state.get.return_value = Decimal('0.100')  # Default balance
    state.set_sell_percentage.return_value = True
    state.capture_demo_snapshot.return_value = DemoStateSnapshot(
        balance=Decimal('0.100'),
        position=None,
        sidebet=None,
        bet_amount=Decimal('0.01'),
        sell_percentage=Decimal('1.0'),
        current_tick=42,
        current_price=Decimal('1.5'),
        phase='ACTIVE_GAMEPLAY'
    )
    return state


@pytest.fixture
def mock_trade_manager():
    """Create mock TradeManager"""
    tm = Mock()
    tm.execute_buy.return_value = {'success': True, 'price': Decimal('1.5')}
    tm.execute_sell.return_value = {'success': True, 'pnl_sol': Decimal('0.01'), 'pnl_percent': Decimal('10')}
    tm.execute_sidebet.return_value = {'success': True, 'potential_win': Decimal('0.05')}
    return tm


@pytest.fixture
def mock_browser_bridge():
    """Create mock BrowserBridge"""
    bridge = Mock()
    bridge.on_buy_clicked = Mock()
    bridge.on_sell_clicked = Mock()
    bridge.on_sidebet_clicked = Mock()
    bridge.on_percentage_clicked = Mock()
    bridge.on_increment_clicked = Mock()
    bridge.on_clear_clicked = Mock()
    return bridge


@pytest.fixture
def mock_bet_entry():
    """Create mock bet entry widget"""
    entry = Mock()
    entry.get.return_value = "0.01"
    entry.delete = Mock()
    entry.insert = Mock()
    return entry


@pytest.fixture
def mock_ui_dispatcher():
    """Create mock UI dispatcher"""
    dispatcher = Mock()
    dispatcher.submit = Mock(side_effect=lambda f: f())  # Execute immediately
    return dispatcher


@pytest.fixture
def mock_toast():
    """Create mock toast notification"""
    return Mock()


@pytest.fixture
def mock_config():
    """Create mock config"""
    config = Mock()
    config.FINANCIAL = {'min_bet': Decimal('0.001'), 'max_bet': Decimal('10.0')}
    return config


@pytest.fixture
def trading_controller_with_recorder(
    mock_state,
    mock_trade_manager,
    mock_browser_bridge,
    mock_bet_entry,
    mock_ui_dispatcher,
    mock_toast,
    mock_config,
    demo_recorder
):
    """Create TradingController with demo recorder attached"""
    parent = Mock()
    parent.current_sell_percentage = 1.0

    controller = TradingController(
        parent_window=parent,
        trade_manager=mock_trade_manager,
        state=mock_state,
        config=mock_config,
        browser_bridge=mock_browser_bridge,
        bet_entry=mock_bet_entry,
        percentage_buttons={},
        ui_dispatcher=mock_ui_dispatcher,
        toast=mock_toast,
        log_callback=Mock()
    )

    # Attach demo recorder
    controller.demo_recorder = demo_recorder

    return controller


class TestTradingControllerDemoRecorderSetup:
    """Tests for demo recorder integration setup"""

    def test_trading_controller_accepts_demo_recorder(
        self,
        mock_state,
        mock_trade_manager,
        mock_browser_bridge,
        mock_bet_entry,
        mock_ui_dispatcher,
        mock_toast,
        mock_config,
        demo_recorder
    ):
        """Test TradingController can accept optional demo_recorder parameter"""
        controller = TradingController(
            parent_window=Mock(),
            trade_manager=mock_trade_manager,
            state=mock_state,
            config=mock_config,
            browser_bridge=mock_browser_bridge,
            bet_entry=mock_bet_entry,
            percentage_buttons={},
            ui_dispatcher=mock_ui_dispatcher,
            toast=mock_toast,
            log_callback=Mock(),
            demo_recorder=demo_recorder  # New parameter
        )

        assert controller.demo_recorder is demo_recorder

    def test_demo_recorder_defaults_to_none(
        self,
        mock_state,
        mock_trade_manager,
        mock_browser_bridge,
        mock_bet_entry,
        mock_ui_dispatcher,
        mock_toast,
        mock_config
    ):
        """Test demo_recorder defaults to None when not provided"""
        controller = TradingController(
            parent_window=Mock(),
            trade_manager=mock_trade_manager,
            state=mock_state,
            config=mock_config,
            browser_bridge=mock_browser_bridge,
            bet_entry=mock_bet_entry,
            percentage_buttons={},
            ui_dispatcher=mock_ui_dispatcher,
            toast=mock_toast,
            log_callback=Mock()
        )

        assert controller.demo_recorder is None


class TestTradeButtonsRecording:
    """Tests for trade button (BUY/SELL/SIDEBET) recording"""

    def test_execute_buy_records_action(self, trading_controller_with_recorder, demo_recorder):
        """Test BUY button records action with state snapshot"""
        controller = trading_controller_with_recorder

        controller.execute_buy()

        # Verify action was recorded
        assert demo_recorder.action_count >= 1

    def test_execute_buy_records_correct_button_text(self, trading_controller_with_recorder, demo_recorder, temp_demo_dir):
        """Test BUY button records 'BUY' as button text"""
        controller = trading_controller_with_recorder

        controller.execute_buy()
        demo_recorder.end_game()  # Flush to file

        # Read the JSONL file to verify button text
        game_file = list(temp_demo_dir.glob("**/game_*.jsonl"))[0]
        import json
        with open(game_file) as f:
            lines = f.readlines()
            # Skip header, find action
            for line in lines:
                data = json.loads(line)
                if data.get('type') == 'action':
                    assert data['button'] == 'BUY'
                    assert data['category'] == 'TRADE_BUY'
                    break

    def test_execute_sell_records_action(self, trading_controller_with_recorder, demo_recorder):
        """Test SELL button records action"""
        controller = trading_controller_with_recorder

        controller.execute_sell()

        assert demo_recorder.action_count >= 1

    def test_execute_sidebet_records_action(self, trading_controller_with_recorder, demo_recorder):
        """Test SIDEBET button records action"""
        controller = trading_controller_with_recorder

        controller.execute_sidebet()

        assert demo_recorder.action_count >= 1


class TestPercentageButtonsRecording:
    """Tests for percentage button (10%, 25%, 50%, 100%) recording"""

    @pytest.mark.parametrize("percentage,button_text", [
        (0.10, '10%'),
        (0.25, '25%'),
        (0.50, '50%'),
        (1.00, '100%'),
    ])
    def test_set_sell_percentage_records_action(
        self,
        trading_controller_with_recorder,
        demo_recorder,
        percentage,
        button_text
    ):
        """Test percentage buttons record correct button text"""
        controller = trading_controller_with_recorder

        controller.set_sell_percentage(percentage)

        assert demo_recorder.action_count >= 1


class TestBetIncrementButtonsRecording:
    """Tests for bet increment buttons recording"""

    @pytest.mark.parametrize("amount,button_text", [
        (Decimal('0.001'), '+0.001'),
        (Decimal('0.01'), '+0.01'),
        (Decimal('0.1'), '+0.1'),
        (Decimal('1'), '+1'),
    ])
    def test_increment_bet_amount_records_action(
        self,
        trading_controller_with_recorder,
        demo_recorder,
        amount,
        button_text
    ):
        """Test increment buttons record correct button text"""
        controller = trading_controller_with_recorder

        controller.increment_bet_amount(amount)

        assert demo_recorder.action_count >= 1

    def test_clear_bet_amount_records_action(self, trading_controller_with_recorder, demo_recorder):
        """Test X (clear) button records action"""
        controller = trading_controller_with_recorder

        controller.clear_bet_amount()

        assert demo_recorder.action_count >= 1

    def test_half_bet_amount_records_action(self, trading_controller_with_recorder, demo_recorder):
        """Test 1/2 button records action"""
        controller = trading_controller_with_recorder

        controller.half_bet_amount()

        assert demo_recorder.action_count >= 1

    def test_double_bet_amount_records_action(self, trading_controller_with_recorder, demo_recorder):
        """Test X2 button records action"""
        controller = trading_controller_with_recorder

        controller.double_bet_amount()

        assert demo_recorder.action_count >= 1

    def test_max_bet_amount_records_action(self, trading_controller_with_recorder, demo_recorder):
        """Test MAX button records action"""
        controller = trading_controller_with_recorder

        controller.max_bet_amount()

        assert demo_recorder.action_count >= 1


class TestStateSnapshotCapture:
    """Tests for state snapshot capture during recording"""

    def test_buy_captures_state_before(self, trading_controller_with_recorder, mock_state):
        """Test BUY captures state snapshot before action"""
        controller = trading_controller_with_recorder

        controller.execute_buy()

        # Verify capture_demo_snapshot was called with bet_amount
        mock_state.capture_demo_snapshot.assert_called()

    def test_increment_captures_state_before(self, trading_controller_with_recorder, mock_state):
        """Test increment button captures state snapshot"""
        controller = trading_controller_with_recorder

        controller.increment_bet_amount(Decimal('0.01'))

        mock_state.capture_demo_snapshot.assert_called()


class TestNoRecordingWhenRecorderNotActive:
    """Tests for graceful handling when recorder is None or inactive"""

    def test_execute_buy_works_without_recorder(
        self,
        mock_state,
        mock_trade_manager,
        mock_browser_bridge,
        mock_bet_entry,
        mock_ui_dispatcher,
        mock_toast,
        mock_config
    ):
        """Test BUY works normally when no demo_recorder is set"""
        controller = TradingController(
            parent_window=Mock(),
            trade_manager=mock_trade_manager,
            state=mock_state,
            config=mock_config,
            browser_bridge=mock_browser_bridge,
            bet_entry=mock_bet_entry,
            percentage_buttons={},
            ui_dispatcher=mock_ui_dispatcher,
            toast=mock_toast,
            log_callback=Mock()
        )

        # Should not raise exception
        controller.execute_buy()

        # Trade should still execute
        mock_trade_manager.execute_buy.assert_called()

    def test_increment_works_without_recorder(
        self,
        mock_state,
        mock_trade_manager,
        mock_browser_bridge,
        mock_bet_entry,
        mock_ui_dispatcher,
        mock_toast,
        mock_config
    ):
        """Test increment works normally when no demo_recorder is set"""
        controller = TradingController(
            parent_window=Mock(),
            trade_manager=mock_trade_manager,
            state=mock_state,
            config=mock_config,
            browser_bridge=mock_browser_bridge,
            bet_entry=mock_bet_entry,
            percentage_buttons={},
            ui_dispatcher=mock_ui_dispatcher,
            toast=mock_toast,
            log_callback=Mock()
        )

        # Should not raise exception
        controller.increment_bet_amount(Decimal('0.01'))

        # UI update should still happen
        mock_bet_entry.delete.assert_called()
        mock_bet_entry.insert.assert_called()
