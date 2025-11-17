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

    def __init__(self, main_window):
        """
        Initialize UI controller

        Args:
            main_window: MainWindow instance with UI widgets
        """
        self.main_window = main_window
        self.root = main_window.root

        # Human delay range (as specified by user for 250ms game ticks)
        self.min_delay = 0.010  # 10ms
        self.max_delay = 0.050  # 50ms

        logger.info("BotUIController initialized (UI-layer execution mode)")

    def _schedule_ui_action(self, action):
        """
        AUDIT FIX: Thread-safe UI action scheduling

        Checks if we're on the main thread and uses appropriate method:
        - Main thread: Use root.after(0, ...)
        - Worker thread: Use ui_dispatcher.submit(...)

        Args:
            action: Callable to execute on UI thread
        """
        if threading.current_thread() == threading.main_thread():
            # Already on main thread, use root.after
            self.root.after(0, action)
        else:
            # Worker thread, use thread-safe dispatcher
            self.main_window.ui_dispatcher.submit(action)

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

        Args:
            amount: Amount in SOL

        Returns:
            True if successful
        """
        if not self.set_bet_amount(amount):
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

        Args:
            amount: Amount in SOL

        Returns:
            True if successful
        """
        if not self.set_bet_amount(amount):
            return False

        return self.click_sidebet()
