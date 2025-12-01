"""
Browser Actions Mixin

Provides browser action methods for executing trades.
Extracted from browser_executor.py during Phase 1 refactoring.

Classes:
    BrowserActionsMixin: Mixin providing click_buy, click_sell, click_sidebet methods
"""

import asyncio
import logging
import random
from decimal import Decimal
from typing import Optional

from bot.browser_selectors import (
    BUY_BUTTON_SELECTORS,
    SELL_BUTTON_SELECTORS,
    SIDEBET_BUTTON_SELECTORS,
    BET_AMOUNT_INPUT_SELECTORS,
    INCREMENT_SELECTOR_MAP,
    PERCENTAGE_TEXT_MAP,
)

logger = logging.getLogger(__name__)


class BrowserActionsMixin:
    """
    Mixin class providing browser action methods.

    Requires the host class to have:
    - self.page property (Playwright page object)
    - self.is_ready() method
    - self.action_timeout attribute
    - self.validation_delay attribute

    Usage:
        class BrowserExecutor(BrowserActionsMixin):
            ...
    """

    # ========================================================================
    # PUBLIC ACTION METHODS
    # ========================================================================

    async def click_buy(self, amount: Optional[Decimal] = None) -> bool:
        """
        Click BUY button in browser

        Phase A.3 UPDATE: Now uses incremental button clicking instead
        of direct text entry for human-like behavior.

        Args:
            amount: Optional bet amount to set before clicking

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_ready():
                logger.error("Browser not ready for BUY action")
                return False

            page = self.page  # Use property (CDP or legacy)

            # Set bet amount if provided (Phase A.3: use incremental clicking)
            if amount is not None:
                if not await self._build_amount_incrementally_in_browser(amount):
                    logger.error("Failed to build bet amount incrementally")
                    return False

            # Find and click BUY button
            for selector in BUY_BUTTON_SELECTORS:
                try:
                    button = await page.wait_for_selector(
                        selector,
                        timeout=self.action_timeout * 1000,
                        state='visible'
                    )
                    if button:
                        await button.click()
                        logger.info(f"Clicked BUY button ({amount if amount else 'default'} SOL)")

                        # Wait for action to process
                        await asyncio.sleep(self.validation_delay)
                        return True

                except Exception:
                    continue

            logger.error("Could not find BUY button with any selector")
            return False

        except Exception as e:
            logger.error(f"Error clicking BUY: {e}", exc_info=True)
            return False

    async def click_sell(self, percentage: Optional[float] = None) -> bool:
        """
        Click SELL button in browser

        Args:
            percentage: Optional sell percentage (0.1, 0.25, 0.5, 1.0)

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_ready():
                logger.error("Browser not ready for SELL action")
                return False

            page = self.page  # Use property (CDP or legacy)

            # Set sell percentage if provided
            if percentage is not None:
                if not await self._set_sell_percentage_in_browser(percentage):
                    logger.error("Failed to set sell percentage")
                    return False

            # Find and click SELL button
            for selector in SELL_BUTTON_SELECTORS:
                try:
                    button = await page.wait_for_selector(
                        selector,
                        timeout=self.action_timeout * 1000,
                        state='visible'
                    )
                    if button:
                        await button.click()
                        pct_str = f"{percentage*100:.0f}%" if percentage else "default"
                        logger.info(f"Clicked SELL button ({pct_str})")

                        # Wait for action to process
                        await asyncio.sleep(self.validation_delay)
                        return True

                except Exception:
                    continue

            logger.error("Could not find SELL button with any selector")
            return False

        except Exception as e:
            logger.error(f"Error clicking SELL: {e}", exc_info=True)
            return False

    async def click_sidebet(self, amount: Optional[Decimal] = None) -> bool:
        """
        Click SIDEBET button in browser

        Phase A.3 UPDATE: Now uses incremental button clicking instead
        of direct text entry for human-like behavior.

        Args:
            amount: Optional bet amount to set before clicking

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_ready():
                logger.error("Browser not ready for SIDEBET action")
                return False

            page = self.page  # Use property (CDP or legacy)

            # Set bet amount if provided (Phase A.3: use incremental clicking)
            if amount is not None:
                if not await self._build_amount_incrementally_in_browser(amount):
                    logger.error("Failed to build bet amount incrementally")
                    return False

            # Find and click SIDEBET button
            for selector in SIDEBET_BUTTON_SELECTORS:
                try:
                    button = await page.wait_for_selector(
                        selector,
                        timeout=self.action_timeout * 1000,
                        state='visible'
                    )
                    if button:
                        await button.click()
                        logger.info(f"Clicked SIDEBET button ({amount if amount else 'default'} SOL)")

                        # Wait for action to process
                        await asyncio.sleep(self.validation_delay)
                        return True

                except Exception:
                    continue

            logger.error("Could not find SIDEBET button with any selector")
            return False

        except Exception as e:
            logger.error(f"Error clicking SIDEBET: {e}", exc_info=True)
            return False

    # ========================================================================
    # INTERNAL HELPER METHODS
    # ========================================================================

    async def _set_bet_amount_in_browser(self, amount: Decimal) -> bool:
        """
        Set bet amount in browser input field (direct entry)

        Note: Prefer _build_amount_incrementally_in_browser for human-like behavior.

        Args:
            amount: Bet amount in SOL

        Returns:
            True if successful, False otherwise
        """
        try:
            page = self.page  # Use property (CDP or legacy)

            # Find bet amount input
            for selector in BET_AMOUNT_INPUT_SELECTORS:
                try:
                    input_field = await page.wait_for_selector(
                        selector,
                        timeout=self.action_timeout * 1000,
                        state='visible'
                    )
                    if input_field:
                        # Clear and set value
                        await input_field.fill(str(amount))
                        logger.debug(f"Set bet amount to {amount} SOL")
                        return True

                except Exception:
                    continue

            logger.error("Could not find bet amount input with any selector")
            return False

        except Exception as e:
            logger.error(f"Error setting bet amount: {e}", exc_info=True)
            return False

    async def _set_sell_percentage_in_browser(self, percentage: float) -> bool:
        """
        Set sell percentage in browser (click percentage button)

        Args:
            percentage: Sell percentage (0.1, 0.25, 0.5, 1.0)

        Returns:
            True if successful, False otherwise
        """
        try:
            page = self.page  # Use property (CDP or legacy)

            text = PERCENTAGE_TEXT_MAP.get(percentage)
            if not text:
                logger.error(f"Invalid percentage: {percentage}")
                return False

            # Find and click percentage button
            selectors = [
                f'button:has-text("{text}")',
                f'[data-percentage="{text}"]',
                f'button[class*="pct-{text}"]',
            ]

            for selector in selectors:
                try:
                    button = await page.wait_for_selector(
                        selector,
                        timeout=self.action_timeout * 1000,
                        state='visible'
                    )
                    if button:
                        await button.click()
                        logger.debug(f"Set sell percentage to {text}")
                        return True

                except Exception:
                    continue

            logger.warning(f"Could not find {text} percentage button - may need to update selectors")
            # Return True anyway (percentage buttons might not exist yet in UI)
            return True

        except Exception as e:
            logger.error(f"Error setting sell percentage: {e}", exc_info=True)
            return False

    async def _click_increment_button_in_browser(self, button_type: str, times: int = 1) -> bool:
        """
        Click an increment button multiple times in browser

        Phase A.3: Enables bot to build amounts incrementally by clicking
        browser buttons instead of directly setting text, matching human behavior.

        Args:
            button_type: '+0.001', '+0.01', '+0.1', '+1', '1/2', 'X2', 'MAX', 'X'
            times: Number of times to click (default 1)

        Returns:
            True if successful, False otherwise

        Example:
            _click_increment_button_in_browser('+0.001', 3)  # 0.0 -> 0.003
        """
        if not self.is_ready():
            logger.error("Browser not ready for button clicking")
            return False

        try:
            page = self.page  # Use property (CDP or legacy)

            selectors = INCREMENT_SELECTOR_MAP.get(button_type)
            if not selectors:
                logger.error(f"Unknown button type: {button_type}")
                return False

            # Find button using selectors
            button = None
            for selector in selectors:
                try:
                    button = await page.wait_for_selector(
                        selector,
                        timeout=self.action_timeout * 1000,
                        state='visible'
                    )
                    if button:
                        break
                except Exception:
                    continue

            if not button:
                logger.error(f"Could not find {button_type} button with any selector")
                return False

            # Click button {times} times with human delays (10-50ms)
            for i in range(times):
                await button.click()

                # Human delay between clicks (10-50ms)
                if i < times - 1:
                    delay = random.uniform(0.010, 0.050)  # 10-50ms
                    await asyncio.sleep(delay)

            logger.debug(f"Browser: Clicked {button_type} button {times}x")
            return True

        except Exception as e:
            logger.error(f"Failed to click {button_type} button in browser: {e}")
            return False

    async def _build_amount_incrementally_in_browser(self, target_amount: Decimal) -> bool:
        """
        Build to target amount by clicking increment buttons in browser

        Phase A.3: Matches human behavior of clicking buttons to reach
        desired amount, rather than directly typing. Creates realistic
        timing patterns for live trading.

        Strategy:
        1. Click 'X' to clear to 0.0
        2. Calculate optimal button sequence (largest first)
        3. Click buttons to reach target

        Examples:
            0.003 -> X, +0.001 (3x)
            0.015 -> X, +0.01 (1x), +0.001 (5x)
            1.234 -> X, +1 (1x), +0.1 (2x), +0.01 (3x), +0.001 (4x)

        Args:
            target_amount: Decimal target amount

        Returns:
            True if successful
        """
        try:
            # Clear to 0.0 first
            if not await self._click_increment_button_in_browser('X'):
                logger.error("Failed to clear bet amount in browser")
                return False

            # Human delay after clear
            await asyncio.sleep(random.uniform(0.010, 0.050))

            # Calculate button sequence (greedy algorithm, largest first)
            remaining = float(target_amount)
            sequence = []

            increments = [
                (1.0, '+1'),
                (0.1, '+0.1'),
                (0.01, '+0.01'),
                (0.001, '+0.001'),
            ]

            for increment_value, button_type in increments:
                count = int(remaining / increment_value)
                if count > 0:
                    sequence.append((button_type, count))
                    remaining -= count * increment_value
                    remaining = round(remaining, 3)  # Avoid floating point errors

            # Execute sequence
            for button_type, count in sequence:
                if not await self._click_increment_button_in_browser(button_type, count):
                    logger.error(f"Failed to click {button_type} {count} times in browser")
                    return False

                # Human delay between different button types
                await asyncio.sleep(random.uniform(0.010, 0.050))

            logger.info(f"Browser: Built amount {target_amount} incrementally: {sequence}")
            return True

        except Exception as e:
            logger.error(f"Failed to build amount incrementally in browser: {e}")
            return False
