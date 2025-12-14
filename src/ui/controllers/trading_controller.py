"""
TradingController - Manages trade execution and bet amount management

Extracted from MainWindow to follow Single Responsibility Principle.
Handles:
- Trade execution (buy/sell/sidebet)
- Bet amount management (increment, clear, half, double, max)
- Sell percentage management (10%, 25%, 50%, 100%)
- UI updates for trade state

Phase 10.6: Records ALL button presses to RecordingController with
dual-state validation (local vs server).
"""

import tkinter as tk
from decimal import Decimal
from typing import Callable, Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from ui.controllers.recording_controller import RecordingController

logger = logging.getLogger(__name__)


class TradingController:
    """
    Manages trade execution and bet amount management.

    Extracted from MainWindow (Phase 3.3) to reduce God Object anti-pattern.
    """

    def __init__(
        self,
        parent_window,  # Reference to MainWindow for state access
        trade_manager,
        state,
        config,
        browser_bridge,
        # UI widgets
        bet_entry: tk.Entry,
        percentage_buttons: dict,
        # UI dispatcher
        ui_dispatcher,
        # Notifications
        toast,
        # Callbacks
        log_callback: Callable[[str], None],
        # Phase 10.6: Recording controller (replaces demo_recorder)
        recording_controller: Optional["RecordingController"] = None,
        # Legacy: Keep demo_recorder for backwards compatibility during migration
        demo_recorder=None
    ):
        """
        Initialize TradingController with dependencies.

        Args:
            parent_window: MainWindow instance (for state access)
            trade_manager: TradeManager instance
            state: GameState instance
            config: Config object
            browser_bridge: BrowserBridge instance (for browser sync)
            bet_entry: Bet amount entry widget
            percentage_buttons: Dict mapping percentages to button info
            ui_dispatcher: TkDispatcher for thread-safe UI updates
            toast: Toast notification widget
            log_callback: Logging function
            recording_controller: RecordingController for Phase 10.6 recording
            demo_recorder: DEPRECATED - Legacy DemoRecorderSink (Phase 10.1-10.3)
        """
        self.parent = parent_window
        self.trade_manager = trade_manager
        self.state = state
        self.config = config
        self.browser_bridge = browser_bridge

        # UI widgets
        self.bet_entry = bet_entry
        self.percentage_buttons = percentage_buttons

        # UI dispatcher
        self.ui_dispatcher = ui_dispatcher

        # Notifications
        self.toast = toast

        # Callbacks
        self.log = log_callback

        # Phase 10.6: Recording controller (primary)
        self.recording_controller = recording_controller

        # Legacy: Demo recorder (deprecated, kept for backwards compatibility)
        self.demo_recorder = demo_recorder

        logger.info("TradingController initialized")

    # ========================================================================
    # RECORDING (Phase 10.6 - Unified with Validation)
    # ========================================================================

    def _record_button_press(self, button: str, amount: Decimal = None):
        """
        Record a button press with dual-state validation.

        Phase 10.6: Records ALL button presses to RecordingController
        with local state snapshot for zero-tolerance validation against
        server state.

        Phase 11: Now includes server state for dual-state validation.

        Args:
            button: Button text (e.g., 'BUY', '+0.01', '25%')
            amount: Trade amount (for BUY/SELL/SIDEBET actions)
        """
        try:
            # Get current bet amount from entry
            try:
                bet_amount = Decimal(self.bet_entry.get())
            except Exception:
                bet_amount = Decimal('0')

            # Phase 10.6: Use new RecordingController
            if self.recording_controller:
                # Capture local state snapshot for validation
                local_state = self.state.capture_local_snapshot(bet_amount)

                # Phase 11: Get server state for dual-state validation
                server_state = None
                if hasattr(self.parent, 'get_latest_server_state'):
                    server_state = self.parent.get_latest_server_state()

                # Record to new unified system with server state
                self.recording_controller.on_button_press(
                    button=button,
                    local_state=local_state,
                    amount=amount,
                    server_state=server_state
                )
                logger.debug(f"Recorded button press (Phase 10.6): {button}")

            # Legacy: Also record to old system during migration
            elif self.demo_recorder and self.demo_recorder.is_game_active():
                state_before = self.state.capture_demo_snapshot(bet_amount)
                self.demo_recorder.record_button_press(
                    button=button,
                    state_before=state_before,
                    amount=amount
                )
                logger.debug(f"Recorded button press (legacy): {button}")

        except Exception as e:
            logger.error(f"Failed to record button press: {e}")

    # ========================================================================
    # TRADE EXECUTION
    # ========================================================================

    def execute_buy(self):
        """Execute buy action using TradeManager (Phase 9.3: syncs to browser)"""
        # Phase 9.3: ALWAYS click BUY in browser first - browser is source of truth
        # This happens regardless of REPLAYER's internal state/validation
        self.browser_bridge.on_buy_clicked()

        amount = self.get_bet_amount()
        if amount is None:
            return  # Validation failed (toast already shown), but browser click already sent

        # Phase 10: Record the action
        self._record_button_press('BUY', amount)

        result = self.trade_manager.execute_buy(amount)

        if result['success']:
            self.log(f"BUY executed at {result['price']:.4f}x")
            self.toast.show(f"Bought {amount} SOL at {result['price']:.4f}x", "success")
        else:
            self.log(f"BUY failed: {result['reason']}")
            self.toast.show(f"Buy failed: {result['reason']}", "error")

    def execute_sell(self):
        """Execute sell action using TradeManager (Phase 8.2: supports partial sells, Phase 9.3: syncs to browser)"""
        # Phase 9.3: Also click SELL in browser if connected
        self.browser_bridge.on_sell_clicked()

        # Phase 10: Record the action
        self._record_button_press('SELL')

        result = self.trade_manager.execute_sell()

        if result['success']:
            pnl = result.get('pnl_sol', 0)
            pnl_pct = result.get('pnl_percent', 0)
            msg_type = "success" if pnl >= 0 else "error"

            # Phase 8.2: Show partial sell information
            if result.get('partial', False):
                percentage = result.get('percentage', 1.0)
                remaining = result.get('remaining_amount', 0)
                self.log(f"PARTIAL SELL ({percentage*100:.0f}%) - P&L: {pnl:+.4f} SOL, Remaining: {remaining:.4f} SOL")
                self.toast.show(f"Sold {percentage*100:.0f}%! P&L: {pnl:+.4f} SOL ({pnl_pct:+.1f}%)", msg_type)
            else:
                self.log(f"SELL executed - P&L: {pnl:+.4f} SOL")
                self.toast.show(f"Sold! P&L: {pnl:+.4f} SOL ({pnl_pct:+.1f}%)", msg_type)
        else:
            self.log(f"SELL failed: {result['reason']}")
            self.toast.show(f"Sell failed: {result['reason']}", "error")

    def execute_sidebet(self):
        """Execute sidebet using TradeManager (Phase 9.3: syncs to browser)"""
        # Phase 9.3: ALWAYS click SIDEBET in browser first - browser is source of truth
        self.browser_bridge.on_sidebet_clicked()

        amount = self.get_bet_amount()
        if amount is None:
            return  # Validation failed (toast already shown), but browser click already sent

        # Phase 10: Record the action
        self._record_button_press('SIDEBET', amount)

        result = self.trade_manager.execute_sidebet(amount)

        if result['success']:
            potential_win = result.get('potential_win', 0)
            self.log(f"SIDEBET placed ({amount} SOL)")
            self.toast.show(f"Side bet placed! {amount} SOL (potential: {potential_win:.4f} SOL)", "warning")
        else:
            self.log(f"SIDEBET failed: {result['reason']}")
            self.toast.show(f"Side bet failed: {result['reason']}", "error")

    # ========================================================================
    # PERCENTAGE SELECTOR (Phase 8.2)
    # ========================================================================

    def set_sell_percentage(self, percentage: float):
        """
        Set the sell percentage (user clicked a percentage button)

        Phase 8.2: Radio-button style selector for partial sells
        Phase 9.3: Syncs to browser

        Args:
            percentage: 0.1 (10%), 0.25 (25%), 0.5 (50%), or 1.0 (100%)
        """
        # Phase 9.3: Also click percentage button in browser if connected
        self.browser_bridge.on_percentage_clicked(percentage)

        # Phase 10: Record the action
        button_text = f"{int(percentage * 100)}%"
        self._record_button_press(button_text)

        # Update GameState with new percentage
        success = self.state.set_sell_percentage(Decimal(str(percentage)))

        if success:
            self.parent.current_sell_percentage = percentage
            # Highlight the selected button
            self.ui_dispatcher.submit(lambda: self.highlight_percentage_button(percentage))
            self.log(f"Sell percentage set to {percentage*100:.0f}%")
        else:
            self.toast.show(f"Invalid percentage: {percentage*100:.0f}%", "error")

    def highlight_percentage_button(self, selected_percentage: float):
        """
        Highlight the selected percentage button (radio-button style)

        Phase 8.2: Only one button is highlighted at a time

        Args:
            selected_percentage: The percentage value that should be highlighted
        """
        for pct, btn_info in self.percentage_buttons.items():
            button = btn_info['button']
            if pct == selected_percentage:
                # Highlight selected button
                button.config(
                    bg=btn_info['selected_color'],
                    relief=tk.SUNKEN,
                    bd=3
                )
            else:
                # Reset unselected buttons
                button.config(
                    bg=btn_info['default_color'],
                    relief=tk.RAISED,
                    bd=2
                )

    # ========================================================================
    # BET AMOUNT MANAGEMENT
    # ========================================================================

    def set_bet_amount(self, amount: Decimal):
        """Set bet amount from quick buttons or manual input"""
        self.bet_entry.delete(0, tk.END)
        self.bet_entry.insert(0, str(amount))
        logger.debug(f"Bet amount set to {amount}")

    def increment_bet_amount(self, amount: Decimal):
        """Increment bet amount by specified amount (Phase 9.3: syncs to browser)"""
        # Phase 9.3: ALWAYS click increment button in browser FIRST
        # Map Decimal amount to button text: 0.001 -> '+0.001', 0.01 -> '+0.01', etc.
        button_text = f"+{amount}"
        self.browser_bridge.on_increment_clicked(button_text)

        # Phase 10: Record the action
        self._record_button_press(button_text)

        # Then update local UI
        try:
            current_amount = Decimal(self.bet_entry.get())
        except Exception:
            current_amount = Decimal('0')

        new_amount = current_amount + amount
        self.bet_entry.delete(0, tk.END)
        self.bet_entry.insert(0, str(new_amount))
        logger.debug(f"Bet amount incremented by {amount} to {new_amount}")

    def clear_bet_amount(self):
        """Clear bet amount to zero (Phase 9.3: syncs to browser)"""
        # Phase 9.3: ALWAYS click X (clear) button in browser FIRST
        self.browser_bridge.on_clear_clicked()

        # Phase 10: Record the action
        self._record_button_press('X')

        # Then update local UI
        self.bet_entry.delete(0, tk.END)
        self.bet_entry.insert(0, "0")
        logger.debug("Bet amount cleared to 0")

    def half_bet_amount(self):
        """Halve bet amount (1/2 button) - Phase 9.3: syncs to browser"""
        # Phase 9.3: ALWAYS click 1/2 button in browser FIRST
        self.browser_bridge.on_increment_clicked('1/2')

        # Phase 10: Record the action
        self._record_button_press('1/2')

        # Then update local UI
        try:
            current = Decimal(self.bet_entry.get())
            new_amount = current / 2
            self.bet_entry.delete(0, tk.END)
            self.bet_entry.insert(0, str(new_amount))
            logger.debug(f"Bet amount halved to {new_amount}")
        except Exception:
            pass

    def double_bet_amount(self):
        """Double bet amount (X2 button) - Phase 9.3: syncs to browser"""
        # Phase 9.3: ALWAYS click X2 button in browser FIRST
        self.browser_bridge.on_increment_clicked('X2')

        # Phase 10: Record the action
        self._record_button_press('X2')

        # Then update local UI
        try:
            current = Decimal(self.bet_entry.get())
            new_amount = current * 2
            self.bet_entry.delete(0, tk.END)
            self.bet_entry.insert(0, str(new_amount))
            logger.debug(f"Bet amount doubled to {new_amount}")
        except Exception:
            pass

    def max_bet_amount(self):
        """Set bet to max (MAX button) - Phase 9.3: syncs to browser"""
        # Phase 9.3: ALWAYS click MAX button in browser FIRST
        self.browser_bridge.on_increment_clicked('MAX')

        # Phase 10: Record the action
        self._record_button_press('MAX')

        # Then update local UI
        balance = self.state.get('balance')
        if balance:
            self.bet_entry.delete(0, tk.END)
            self.bet_entry.insert(0, str(balance))
            logger.debug(f"Bet amount set to MAX: {balance}")

    def get_bet_amount(self) -> Optional[Decimal]:
        """
        Get and validate bet amount from entry

        Returns:
            Decimal amount if valid, None otherwise
        """
        try:
            bet_amount = Decimal(self.bet_entry.get())

            min_bet = self.config.FINANCIAL['min_bet']
            max_bet = self.config.FINANCIAL['max_bet']

            if bet_amount < min_bet:
                self.toast.show(f"Bet must be at least {min_bet} SOL", "error")
                return None

            if bet_amount > max_bet:
                self.toast.show(f"Bet cannot exceed {max_bet} SOL", "error")
                return None

            balance = self.state.get('balance')
            if bet_amount > balance:
                self.toast.show(f"Insufficient balance! Have {balance:.4f} SOL", "error")
                return None

            return bet_amount

        except Exception as e:
            self.toast.show("Invalid bet amount", "error")
            logger.error(f"Invalid bet amount: {e}")
            return None
