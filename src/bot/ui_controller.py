"""
Bot UI Controller - Phase 8.3

Enables bot to interact with UI layer instead of calling backend directly.

Key Concepts:
- Bot "clicks" buttons programmatically
- Simulates human delays (10-50ms)
- Reads state from UI labels
- Prepares bot for live browser automation (Phase 8.5)
"""

import time
import random
import logging
import threading
from decimal import Decimal
from typing import Optional
import tkinter as tk

logger = logging.getLogger(__name__)


class BotUIController:
    """
    UI-layer execution controller for bot

    Phase 8.3: Allows bot to interact via UI instead of backend

    The bot will:
    1. Set bet amount via entry field
    2. Click percentage buttons (10%, 25%, 50%, 100%)
    3. Click action buttons (BUY, SELL, SIDEBET)
    4. Read state from UI labels (balance, position)
    5. Experience realistic delays (10-50ms per action)

    This prepares the bot for Phase 8.5 where it will control
    a live browser via Playwright using identical timing.
    """

    def __init__(self, main_window, button_depress_duration_ms: int = 50, inter_click_pause_ms: int = 100,
                 clear_pause_ms: int = 50):
        """
        Initialize UI controller

        Args:
            main_window: MainWindow instance with UI widgets
            button_depress_duration_ms: Duration to show button as pressed (milliseconds)
            inter_click_pause_ms: Pause between button clicks (milliseconds)
            clear_pause_ms: Pause after clear button before building amount (milliseconds)
                           AUDIT FIX: Was hardcoded to 500ms, now configurable.
                           Production: 50ms, Demo mode: 500ms
        """
        self.main_window = main_window
        self.root = main_window.root

        # Phase A.7: Configurable timing (from bot_config.json)
        self.button_depress_duration_ms = button_depress_duration_ms  # Visual feedback duration
        self.inter_click_pause_ms = inter_click_pause_ms  # Pause between clicks
        # AUDIT FIX: Configurable clear pause (was hardcoded 500ms)
        self.clear_pause_ms = clear_pause_ms  # Pause after clear before building

        # Human delay range (as specified by user for 250ms game ticks)
        self.min_delay = 0.010  # 10ms
        self.max_delay = 0.050  # 50ms

        # Store button widget references (Phase A.2 - Incremental clicking)
        # AUDIT FIX: Access via property getters for existence checking
        self._main_window = main_window

        logger.info(f"BotUIController initialized (UI-layer execution mode, "
                   f"button_depress={button_depress_duration_ms}ms, "
                   f"inter_click_pause={inter_click_pause_ms}ms, "
                   f"clear_pause={clear_pause_ms}ms)")

    # AUDIT FIX: Safe widget access with existence checking
    def _widget_exists(self, widget) -> bool:
        """Check if widget still exists and is valid."""
        try:
            return widget is not None and widget.winfo_exists()
        except tk.TclError:
            return False

    def _get_button(self, attr_name):
        """Safely get button widget from main_window."""
        try:
            btn = getattr(self._main_window, attr_name, None)
            if self._widget_exists(btn):
                return btn
            return None
        except Exception:
            return None

    @property
    def clear_button(self):
        return self._get_button('clear_button')

    @property
    def increment_001_button(self):
        return self._get_button('increment_001_button')

    @property
    def increment_01_button(self):
        return self._get_button('increment_01_button')

    @property
    def increment_10_button(self):
        return self._get_button('increment_10_button')

    @property
    def increment_1_button(self):
        return self._get_button('increment_1_button')

    @property
    def half_button(self):
        return self._get_button('half_button')

    @property
    def double_button(self):
        return self._get_button('double_button')

    @property
    def max_button(self):
        return self._get_button('max_button')

    def _schedule_ui_action(self, action):
        """
        AUDIT FIX: Thread-safe UI action scheduling

        Checks if we're on the main thread and uses appropriate method:
        - Main thread: Use root.after(0, ...)
        - Worker thread: Use ui_dispatcher.submit(...)

        Args:
            action: Callable to execute on UI thread

        Returns:
            True if scheduled successfully, False if UI is destroyed
        """
        # AUDIT FIX: Check if root still exists before scheduling
        if not self._widget_exists(self.root):
            logger.debug("UI destroyed, skipping action")
            return False

        if threading.current_thread() == threading.main_thread():
            # Already on main thread, use root.after
            self.root.after(0, action)
        else:
            # Worker thread, use thread-safe dispatcher
            self.main_window.ui_dispatcher.submit(action)
        return True

    def _human_delay(self):
        """
        Simulate human delay between UI interactions

        Phase 8.3: 10-50ms delays (user specification)
        Game ticks at 250ms, so delays must be much shorter
        """
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)
        return delay

    # ========================================================================
    # UI INTERACTION METHODS (Phase 8.3)
    # ========================================================================

    def set_bet_amount(self, amount: Decimal) -> bool:
        """
        Set bet amount in entry field

        Args:
            amount: Amount to set in SOL

        Returns:
            True if successful
        """
        try:
            # Schedule UI update on main thread
            def _set_amount():
                self.main_window.bet_entry.delete(0, tk.END)
                self.main_window.bet_entry.insert(0, str(amount))

            self._schedule_ui_action(_set_amount)
            self._human_delay()

            logger.debug(f"UI: Set bet amount to {amount} SOL")
            return True

        except Exception as e:
            logger.error(f"Failed to set bet amount: {e}")
            return False

    def click_increment_button(self, button_type: str, times: int = 1) -> bool:
        """
        Click an increment button multiple times (human-like behavior)

        Phase A.2: Enables bot to build amounts incrementally by clicking
        buttons instead of directly setting text, matching human behavior.

        Args:
            button_type: '+0.001', '+0.01', '+0.1', '+1', '1/2', 'X2', 'MAX', 'X'
            times: Number of times to click (default 1)

        Returns:
            True if successful

        Example:
            click_increment_button('+0.001', 3)  # 0.0 → 0.003
        """
        button_map = {
            'X': self.clear_button,
            '+0.001': self.increment_001_button,
            '+0.01': self.increment_01_button,
            '+0.1': self.increment_10_button,
            '+1': self.increment_1_button,
            '1/2': self.half_button,
            'X2': self.double_button,
            'MAX': self.max_button,
        }

        button = button_map.get(button_type)
        if not button:
            logger.error(f"Unknown button type: {button_type}")
            return False

        try:
            # Click button {times} times with human delays
            for i in range(times):
                def _click_button_with_visual_feedback(btn=button):
                    """
                    Click button with visual depression effect

                    Phase A.7: Configurable visual feedback duration + color indication
                    """
                    # Save original button state
                    original_relief = btn.cget('relief')
                    try:
                        original_bg = btn.cget('background')
                    except tk.TclError:
                        # AUDIT FIX: Catch specific Tkinter exception
                        original_bg = None

                    # Press button down (sunken relief + color change)
                    btn.config(relief=tk.SUNKEN)
                    if original_bg:
                        btn.config(background='#90EE90')  # Light green when pressed

                    # Force UI update to show pressed state
                    btn.update_idletasks()

                    # Hold pressed state (configurable duration)
                    self.root.after(self.button_depress_duration_ms,
                                  lambda: self._release_button(btn, original_relief, original_bg))

                    # Execute the button's command
                    btn.invoke()

                self._schedule_ui_action(_click_button_with_visual_feedback)

                # Phase A.7: Configurable delay AFTER EVERY click
                # Wait for button depression animation + pause before next click
                # Typical: 60-100ms for realistic play, 500ms for slow demo
                time.sleep(self.inter_click_pause_ms / 1000.0)  # Convert ms to seconds

            logger.debug(f"UI: Clicked {button_type} button {times}x")
            return True

        except Exception as e:
            logger.error(f"Failed to click {button_type} button: {e}")
            return False

    def _release_button(self, button, original_relief, original_bg=None):
        """
        Release button back to normal state

        Phase A.7: Visual feedback helper (relief + color restoration)
        """
        try:
            button.config(relief=original_relief)
            if original_bg:
                button.config(background=original_bg)
        except Exception as e:
            # Button might have been destroyed
            logger.debug(f"Could not release button: {e}")

    def build_amount_incrementally(self, target_amount: Decimal) -> bool:
        """
        Build to target amount by clicking increment buttons

        Phase A.2: Matches human behavior of clicking buttons to reach
        desired amount, rather than directly typing. Creates realistic
        timing patterns for RL training.

        Phase A.6 UPDATE: Smart algorithm using 1/2 and X2 buttons for efficiency.

        Strategy:
        1. Click 'X' to clear to 0.0
        2. Calculate optimal button sequence using:
           - Standard increments (+1, +0.1, +0.01, +0.001)
           - 1/2 button (halve current amount)
           - X2 button (double current amount)
        3. Choose most efficient path (fewest total clicks)

        Optimized Examples:
            0.005 → X, +0.01, 1/2 (3 clicks vs 5 clicks)
            0.012 → X, +0.01, 1/2, +0.001, X2 (5 clicks vs 12 clicks)
            0.003 → X, +0.001 (3x) (4 clicks - no optimization needed)

        Args:
            target_amount: Decimal target amount

        Returns:
            True if successful
        """
        try:
            # Clear to 0.0 first
            if not self.click_increment_button('X'):
                logger.error("Failed to clear bet amount")
                return False

            # AUDIT FIX: Configurable pause after clear (production: 50ms, demo: 500ms)
            time.sleep(self.clear_pause_ms / 1000.0)

            # Calculate optimal button sequence using smart algorithm
            sequence = self._calculate_optimal_sequence(float(target_amount))

            # Execute sequence
            # NOTE: click_increment_button already handles 500ms pauses between each click,
            # so we don't need additional delays here
            for i, (button_type, count) in enumerate(sequence):
                if not self.click_increment_button(button_type, count):
                    logger.error(f"Failed to click {button_type} {count} times")
                    return False

            logger.info(f"UI: Built amount {target_amount} incrementally: {sequence}")
            return True

        except Exception as e:
            logger.error(f"Failed to build amount incrementally: {e}")
            return False

    def _calculate_optimal_sequence(self, target: float) -> list:
        """
        Calculate optimal button sequence using 1/2 and X2 buttons

        Phase A.6: Smart algorithm that considers:
        - Standard increments (greedy: largest first)
        - Halving (if target is half of a round number)
        - Doubling (if current value × 2 gets closer to target)

        Args:
            target: Target amount as float

        Returns:
            List of (button_type, count) tuples
        """
        # Try to find efficient patterns using 1/2 and X2

        # Check if target is half of a round increment
        # e.g., 0.005 = 0.01 / 2 (2 clicks vs 5 clicks)
        round_increments = [1.0, 0.1, 0.01, 0.001]
        for inc in round_increments:
            if abs(target - inc / 2) < 0.0001:  # Close enough to half
                # Build to inc, then halve
                base_sequence = self._greedy_sequence(inc)
                return base_sequence + [('1/2', 1)]

        # Check if target can be built efficiently with X2
        # e.g., 0.012 = (0.006) × 2 = (0.005 + 0.001) × 2
        half_target = target / 2
        if half_target >= 0.001:  # Only if half is reasonable
            # Calculate cost of building half_target, then doubling
            half_sequence = self._greedy_sequence(half_target)
            half_clicks = sum(count for _, count in half_sequence)
            double_clicks = half_clicks + 1  # +1 for X2

            # Calculate cost of direct greedy approach
            direct_sequence = self._greedy_sequence(target)
            direct_clicks = sum(count for _, count in direct_sequence)

            # Use doubling if it's more efficient
            if double_clicks < direct_clicks:
                return half_sequence + [('X2', 1)]

        # Fall back to greedy algorithm (no optimization found)
        return self._greedy_sequence(target)

    def _greedy_sequence(self, target: float) -> list:
        """
        Greedy algorithm: largest increments first

        AUDIT FIX: Uses Decimal internally to avoid floating point precision errors

        Args:
            target: Target amount as float

        Returns:
            List of (button_type, count) tuples
        """
        from decimal import Decimal, ROUND_DOWN

        # AUDIT FIX: Convert to Decimal for precise arithmetic
        remaining = Decimal(str(target))
        sequence = []

        increments = [
            (Decimal('1'), '+1'),
            (Decimal('0.1'), '+0.1'),
            (Decimal('0.01'), '+0.01'),
            (Decimal('0.001'), '+0.001'),
        ]

        for increment_value, button_type in increments:
            count = int(remaining / increment_value)
            if count > 0:
                sequence.append((button_type, count))
                remaining -= count * increment_value
                # Decimal handles precision correctly, no rounding needed

        return sequence

    def set_sell_percentage(self, percentage: float) -> bool:
        """
        Click a percentage button (10%, 25%, 50%, 100%)

        Args:
            percentage: Percentage as float (0.1, 0.25, 0.5, 1.0)

        Returns:
            True if successful
        """
        try:
            # Find and click the percentage button
            if percentage not in self.main_window.percentage_buttons:
                logger.error(f"Invalid percentage: {percentage}")
                return False

            btn_info = self.main_window.percentage_buttons[percentage]
            button = btn_info['button']

            # Schedule button click on main thread
            self._schedule_ui_action(button.invoke)
            self._human_delay()

            logger.debug(f"UI: Clicked {percentage*100:.0f}% button")
            return True

        except Exception as e:
            logger.error(f"Failed to click percentage button: {e}")
            return False

    def click_buy(self) -> bool:
        """
        Click BUY button

        Returns:
            True if successful
        """
        try:
            # Schedule button click on main thread
            self._schedule_ui_action(self.main_window.buy_button.invoke)
            self._human_delay()

            logger.debug("UI: Clicked BUY button")
            return True

        except Exception as e:
            logger.error(f"Failed to click BUY: {e}")
            return False

    def click_sell(self, percentage: Optional[float] = None) -> bool:
        """
        Click SELL button (optionally setting percentage first)

        Phase 8.3: Bot can set percentage then sell in one call

        Args:
            percentage: Optional percentage to set before selling
                       (0.1, 0.25, 0.5, 1.0)

        Returns:
            True if successful
        """
        try:
            # Set percentage first if provided
            if percentage is not None:
                if not self.set_sell_percentage(percentage):
                    return False

            # Click SELL button
            self._schedule_ui_action(self.main_window.sell_button.invoke)
            self._human_delay()

            logger.debug(f"UI: Clicked SELL button (percentage: {percentage or 'current'})")
            return True

        except Exception as e:
            logger.error(f"Failed to click SELL: {e}")
            return False

    def click_sidebet(self) -> bool:
        """
        Click SIDEBET button

        Returns:
            True if successful
        """
        try:
            # Schedule button click on main thread
            self._schedule_ui_action(self.main_window.sidebet_button.invoke)
            self._human_delay()

            logger.debug("UI: Clicked SIDEBET button")
            return True

        except Exception as e:
            logger.error(f"Failed to click SIDEBET: {e}")
            return False

    # ========================================================================
    # UI STATE READING METHODS (Phase 8.3)
    # ========================================================================

    def read_balance(self) -> Optional[Decimal]:
        """
        Read balance from UI label

        Returns:
            Balance in SOL, or None if failed to read
        """
        try:
            # Balance label format: "Balance: 0.0950 SOL"
            label_text = self.main_window.balance_label.cget("text")

            # Extract number
            parts = label_text.split()
            if len(parts) >= 2:
                balance_str = parts[1]  # "0.0950"
                balance = Decimal(balance_str)
                return balance
            else:
                logger.warning(f"Unexpected balance label format: {label_text}")
                return None

        except Exception as e:
            logger.error(f"Failed to read balance from UI: {e}")
            return None

    def read_position(self) -> Optional[dict]:
        """
        Read position from UI label

        Returns:
            Position dict with 'amount' and 'entry_price', or None if no position
        """
        try:
            # Position label format: "Position: 0.010 SOL @ 1.50x"
            # or "Position: None" if no active position
            label_text = self.main_window.position_label.cget("text")

            if "None" in label_text or label_text == "Position: ":
                return None

            # Extract amount and entry_price
            # Format: "Position: 0.010 SOL @ 1.50x"
            parts = label_text.split()
            if len(parts) >= 5:
                amount_str = parts[1]  # "0.010"
                price_str = parts[4].rstrip('x')  # "1.50"

                return {
                    'amount': Decimal(amount_str),
                    'entry_price': Decimal(price_str)
                }
            else:
                logger.warning(f"Unexpected position label format: {label_text}")
                return None

        except Exception as e:
            logger.error(f"Failed to read position from UI: {e}")
            return None

    def read_current_price(self) -> Optional[Decimal]:
        """
        Read current price from UI label

        Returns:
            Current price multiplier, or None if failed
        """
        try:
            # Price label format: "PRICE: 1.50x"
            label_text = self.main_window.price_label.cget("text")

            # Extract price
            parts = label_text.split()
            if len(parts) >= 2:
                price_str = parts[1].rstrip('x')  # "1.50"
                price = Decimal(price_str)
                return price
            else:
                logger.warning(f"Unexpected price label format: {label_text}")
                return None

        except Exception as e:
            logger.error(f"Failed to read price from UI: {e}")
            return None

    # ========================================================================
    # COMPOSITE ACTIONS (Phase 8.3)
    # ========================================================================

    def execute_buy_with_amount(self, amount: Decimal) -> bool:
        """
        Set bet amount and click BUY (composite action)

        Phase A.2 UPDATE: Now uses incremental button clicking instead
        of direct text entry for human-like behavior.

        Args:
            amount: Amount in SOL

        Returns:
            True if successful
        """
        # Use incremental clicking (Phase A.2)
        if not self.build_amount_incrementally(amount):
            return False

        return self.click_buy()

    def execute_partial_sell(self, percentage: float) -> bool:
        """
        Set sell percentage and click SELL (composite action)

        Args:
            percentage: Percentage to sell (0.1, 0.25, 0.5, 1.0)

        Returns:
            True if successful
        """
        return self.click_sell(percentage=percentage)

    def execute_sidebet_with_amount(self, amount: Decimal) -> bool:
        """
        Set bet amount and click SIDEBET (composite action)

        Phase A.2 UPDATE: Now uses incremental button clicking instead
        of direct text entry for human-like behavior.

        Args:
            amount: Amount in SOL

        Returns:
            True if successful
        """
        # Use incremental clicking (Phase A.2)
        if not self.build_amount_incrementally(amount):
            return False

        return self.click_sidebet()
