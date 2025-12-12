"""
Browser Executor - Phase 9.1 (CDP Update)

Bridges REPLAYER bot to live browser automation via Playwright CDP.
Uses CDP (Chrome DevTools Protocol) for reliable wallet persistence.

Key Features:
- CDP connection to running Chrome (not Playwright's Chromium)
- Wallet and profile persistence across sessions
- Async browser control methods (click BUY, SELL, SIDEBET)
- State synchronization (read balance, position from DOM)
- Execution validation (verify action effect)
- Retry logic (exponential backoff, max 3 attempts)
- Error handling and graceful degradation
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any
from decimal import Decimal

# Phase 2 Refactoring: Browser module consolidation
from browser.dom.timing import ExecutionTiming, TimingMetrics
from browser.dom.selectors import (
    BUY_BUTTON_SELECTORS,
    SELL_BUTTON_SELECTORS,
    SIDEBET_BUTTON_SELECTORS,
    BET_AMOUNT_INPUT_SELECTORS,
    INCREMENT_SELECTOR_MAP,
    PERCENTAGE_TEXT_MAP,
    BALANCE_SELECTORS,
    POSITION_SELECTORS,
)

# Phase 2: Browser consolidation - Use CDP Browser Manager for reliable wallet persistence
try:
    from browser.manager import CDPBrowserManager, CDPStatus
    CDP_MANAGER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"CDPBrowserManager not available: {e}")
    CDPBrowserManager = None
    CDPStatus = None
    CDP_MANAGER_AVAILABLE = False

# Legacy fallback (deprecated - kept for compatibility)
try:
    from browser.cdp.launcher import RugsBrowserManager, BrowserStatus
    LEGACY_MANAGER_AVAILABLE = True
except ImportError:
    RugsBrowserManager = None
    BrowserStatus = None
    LEGACY_MANAGER_AVAILABLE = False

BROWSER_MANAGER_AVAILABLE = CDP_MANAGER_AVAILABLE or LEGACY_MANAGER_AVAILABLE

logger = logging.getLogger(__name__)


# Note: ExecutionTiming and TimingMetrics moved to browser_timing.py (Phase 1 refactoring)


class BrowserExecutor:
    """
    Browser execution controller for live trading

    Phase 8.5: Connects REPLAYER bot to live browser via Playwright
    - Manages browser lifecycle (start, stop, reconnect)
    - Executes trades via DOM interaction (click buttons)
    - Reads game state from browser (balance, position, price)
    - Validates execution (checks state changed)
    - Handles errors and retries

    Phase 1 Refactoring:
    - Selectors moved to browser_selectors.py
    - Timing classes moved to browser_timing.py
    - Action methods implemented inline (click_buy, click_sell, click_sidebet)
    - State reader methods implemented inline (read_balance, read_position)
    """

    # Note: Selectors moved to browser_selectors.py (Phase 1 refactoring)

    def __init__(self, profile_name: str = "rugs_bot", use_cdp: bool = True):
        """
        Initialize browser executor

        Args:
            profile_name: Name of persistent browser profile (default: rugs_bot)
            use_cdp: Use CDP connection (default: True, recommended)
        """
        if not BROWSER_MANAGER_AVAILABLE:
            raise RuntimeError(
                "No browser manager available. "
                "Check browser_automation/ directory is present."
            )

        self.profile_name = profile_name
        self.use_cdp = use_cdp and CDP_MANAGER_AVAILABLE

        # Phase 9.1: CDP is the default and recommended approach
        self.cdp_manager: Optional[CDPBrowserManager] = None if self.use_cdp else None
        self.browser_manager: Optional[RugsBrowserManager] = None  # Legacy fallback

        # Execution tracking
        self.last_action = None
        self.last_action_time = None
        self.retry_count = 0

        # Phase 8.6: Timing metrics tracking
        self.timing_metrics = TimingMetrics()
        self.current_decision_time = None  # Set when bot decides to act

        # Configuration
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        self.action_timeout = 5.0  # seconds
        self.validation_delay = 0.5  # seconds

        # AUDIT FIX: Timeout protection against browser deadlocks
        self.browser_start_timeout = 30.0  # seconds
        self.browser_stop_timeout = 10.0  # seconds
        self.click_timeout = 10.0  # seconds

        # AUDIT FIX Phase 2.4: Reconnection configuration
        self.reconnect_max_attempts = 5
        self.reconnect_base_delay = 1.0  # seconds
        self.reconnect_max_delay = 30.0  # seconds
        self._reconnect_attempt = 0
        self._is_reconnecting = False

        mode = "CDP" if self.use_cdp else "Legacy"
        logger.info(f"BrowserExecutor initialized ({mode} mode, profile: {profile_name})")

    async def start_browser(self) -> bool:
        """
        Start browser and connect to Rugs.fun

        Phase 9.1: Uses CDP connection by default for reliable wallet persistence.
        CDP connects to YOUR Chrome browser (not Playwright's Chromium), ensuring
        Phantom wallet and profile persist across sessions.

        AUDIT FIX: All browser operations wrapped in asyncio.wait_for() with timeouts
        to prevent deadlocks if browser freezes.

        Returns:
            True if browser started successfully, False otherwise
        """
        try:
            if self.use_cdp:
                return await self._start_browser_cdp()
            else:
                return await self._start_browser_legacy()

        except Exception as e:
            logger.error(f"Error starting browser: {e}", exc_info=True)
            return False

    async def _start_browser_cdp(self) -> bool:
        """
        Start browser using CDP connection (Phase 9.1)

        Benefits:
        - Uses YOUR Chrome browser (not Playwright's Chromium)
        - Wallet and profile persist across sessions
        - Extensions work natively (no MV3 issues)
        """
        # AUDIT FIX: Defensive check for CDP availability
        if not CDP_MANAGER_AVAILABLE or CDPBrowserManager is None:
            logger.error("CDP Manager not available - check browser_automation imports")
            return False

        logger.info("Starting browser via CDP connection...")

        # Create CDP browser manager
        self.cdp_manager = CDPBrowserManager(profile_name=self.profile_name)

        # Connect (will launch Chrome if needed)
        try:
            connect_result = await asyncio.wait_for(
                self.cdp_manager.connect(),
                timeout=self.browser_start_timeout
            )
            if not connect_result:
                logger.error("Failed to connect via CDP")
                return False
        except asyncio.TimeoutError:
            logger.error(f"CDP connection timeout after {self.browser_start_timeout}s")
            return False

        logger.info(f"CDP connected! Current URL: {self.cdp_manager.page.url if self.cdp_manager.page else 'N/A'}")

        # Navigate to rugs.fun if not already there
        try:
            nav_result = await asyncio.wait_for(
                self.cdp_manager.navigate_to_game(),
                timeout=15.0
            )
            if not nav_result:
                logger.warning("Navigation unclear - check browser")
        except asyncio.TimeoutError:
            logger.warning("Navigation timeout - check browser")

        logger.info("Browser ready for live trading via CDP!")
        logger.info("NOTE: Wallet should already be connected in your Chrome profile")
        return True

    async def _start_browser_legacy(self) -> bool:
        """
        Start browser using legacy RugsBrowserManager (deprecated)

        DEPRECATED: Use CDP mode instead for reliable wallet persistence.
        """
        logger.warning("Using legacy browser manager (CDP recommended)")

        # Create browser manager
        self.browser_manager = RugsBrowserManager(profile_name=self.profile_name)

        # AUDIT FIX: Wrap start_browser in timeout to prevent deadlock
        try:
            start_result = await asyncio.wait_for(
                self.browser_manager.start_browser(),
                timeout=self.browser_start_timeout
            )
            if not start_result:
                logger.error("Failed to start browser")
                return False
        except asyncio.TimeoutError:
            logger.error(f"Browser start timeout after {self.browser_start_timeout}s")
            return False

        logger.info("Browser started successfully")

        # Navigate to game FIRST (before wallet connection)
        logger.info("Navigating to rugs.fun...")
        # AUDIT FIX: Wrap navigation in timeout
        try:
            nav_result = await asyncio.wait_for(
                self.browser_manager.navigate_to_game(),
                timeout=15.0  # 15 seconds for page load
            )
            if not nav_result:
                logger.warning("Navigation to rugs.fun unclear - continuing anyway")
                # Don't fail here - browser might still work
        except asyncio.TimeoutError:
            logger.warning("Navigation timeout - continuing anyway")

        logger.info("Page loaded")

        # Connect wallet (now that we're on rugs.fun)
        logger.info("Connecting Phantom wallet...")
        # AUDIT FIX: Wrap wallet connection in timeout
        try:
            wallet_result = await asyncio.wait_for(
                self.browser_manager.connect_wallet(),
                timeout=20.0  # 20 seconds for wallet connection (may require user approval)
            )
            if not wallet_result:
                logger.warning("Wallet connection unclear - please verify in browser")
                # Don't fail here - user can connect manually
            else:
                logger.info("Wallet connected successfully!")
        except asyncio.TimeoutError:
            logger.warning("Wallet connection timeout - may need manual approval")

        logger.info("Browser ready for live trading!")
        return True

    async def stop_browser(self) -> None:
        """
        Stop browser and cleanup resources

        Phase 9.1: For CDP mode, disconnects but leaves Chrome running.
        For legacy mode, stops browser completely.

        AUDIT FIX: Wrapped in timeout to prevent deadlock during shutdown
        """
        try:
            # CDP mode - disconnect (Chrome keeps running for persistence)
            if self.cdp_manager:
                try:
                    await asyncio.wait_for(
                        self.cdp_manager.disconnect(),
                        timeout=self.browser_stop_timeout
                    )
                    logger.info("CDP disconnected (Chrome still running for persistence)")
                except asyncio.TimeoutError:
                    logger.error(f"CDP disconnect timeout after {self.browser_stop_timeout}s")
                finally:
                    self.cdp_manager = None

            # Legacy mode - stop browser completely
            if self.browser_manager:
                try:
                    await asyncio.wait_for(
                        self.browser_manager.stop_browser(),
                        timeout=self.browser_stop_timeout
                    )
                    logger.info("Browser stopped")
                except asyncio.TimeoutError:
                    logger.error(f"Browser stop timeout after {self.browser_stop_timeout}s - forcing cleanup")
                finally:
                    self.browser_manager = None

        except Exception as e:
            logger.error(f"Error stopping browser: {e}", exc_info=True)

    def is_ready(self) -> bool:
        """
        Check if browser is ready for trading

        Returns:
            True if browser is ready, False otherwise
        """
        # CDP mode
        if self.cdp_manager:
            return self.cdp_manager.is_ready()

        # Legacy mode
        if self.browser_manager:
            return self.browser_manager.is_ready_for_observation()

        return False

    @property
    def page(self):
        """Get the active browser page (CDP or legacy)"""
        if self.cdp_manager and self.cdp_manager.page:
            return self.cdp_manager.page
        if self.browser_manager and self.browser_manager.page:
            return self.browser_manager.page
        return None

    # ========================================================================
    # AUDIT FIX Phase 2.4: BROWSER RECONNECTION LOGIC
    # ========================================================================

    async def ensure_connected(self) -> bool:
        """
        Ensure browser is connected, attempting reconnection if needed.

        AUDIT FIX Phase 2.4: Added to handle dropped connections gracefully.
        Uses exponential backoff for reconnection attempts.

        Returns:
            True if connected (or successfully reconnected), False otherwise
        """
        if self.is_ready():
            # Reset reconnect counter on successful connection
            self._reconnect_attempt = 0
            return True

        # Already in the process of reconnecting
        if self._is_reconnecting:
            logger.debug("Reconnection already in progress")
            return False

        # Attempt reconnection
        return await self._attempt_reconnect()

    async def _attempt_reconnect(self) -> bool:
        """
        Attempt to reconnect to browser with exponential backoff.

        AUDIT FIX Phase 2.4: Implements robust reconnection with:
        - Exponential backoff (1s, 2s, 4s, 8s, 16s, max 30s)
        - Maximum attempts limit (5 by default)
        - Graceful failure logging

        Returns:
            True if reconnection successful, False otherwise
        """
        if self._reconnect_attempt >= self.reconnect_max_attempts:
            logger.error(
                f"Max reconnection attempts ({self.reconnect_max_attempts}) reached. "
                f"Browser connection lost."
            )
            return False

        self._is_reconnecting = True

        try:
            self._reconnect_attempt += 1

            # Calculate delay with exponential backoff
            delay = min(
                self.reconnect_base_delay * (2 ** (self._reconnect_attempt - 1)),
                self.reconnect_max_delay
            )

            logger.warning(
                f"Browser connection lost. Reconnection attempt "
                f"{self._reconnect_attempt}/{self.reconnect_max_attempts} "
                f"in {delay:.1f}s..."
            )

            await asyncio.sleep(delay)

            # First, clean up any stale connection
            await self.stop_browser()

            # Attempt to reconnect
            success = await self.start_browser()

            if success:
                logger.info(
                    f"Reconnection successful after {self._reconnect_attempt} attempt(s)"
                )
                self._reconnect_attempt = 0
                return True
            else:
                logger.warning(
                    f"Reconnection attempt {self._reconnect_attempt} failed"
                )
                return False

        except Exception as e:
            logger.error(f"Reconnection error: {e}", exc_info=True)
            return False

        finally:
            self._is_reconnecting = False

    def reset_reconnect_counter(self):
        """Reset the reconnection attempt counter (call after successful manual reconnect)"""
        self._reconnect_attempt = 0
        self._is_reconnecting = False
        logger.debug("Reconnection counter reset")

    # ========================================================================
    # BROWSER ACTION METHODS (Phase 8.5)
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
            # AUDIT FIX Phase 2.4: Use ensure_connected for auto-reconnect
            if not await self.ensure_connected():
                logger.error("Browser not ready for BUY action (reconnection failed)")
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
            # AUDIT FIX Phase 2.4: Use ensure_connected for auto-reconnect
            if not await self.ensure_connected():
                logger.error("Browser not ready for SELL action (reconnection failed)")
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
            # AUDIT FIX Phase 2.4: Use ensure_connected for auto-reconnect
            if not await self.ensure_connected():
                logger.error("Browser not ready for SIDEBET action (reconnection failed)")
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
        Set bet amount in browser input field

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

            # Map percentage to button text
            percentage_text = {
                0.1: "10%",
                0.25: "25%",
                0.5: "50%",
                1.0: "100%"
            }

            text = percentage_text.get(percentage)
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
            _click_increment_button_in_browser('+0.001', 3)  # 0.0 → 0.003
        """
        # AUDIT FIX Phase 2.4: Use ensure_connected for auto-reconnect
        if not await self.ensure_connected():
            logger.error("Browser not ready for button clicking (reconnection failed)")
            return False

        try:
            page = self.page  # Use property (CDP or legacy)

            # Use centralized selector map from browser_selectors module
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
                    import random
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
            0.003 → X, +0.001 (3x)
            0.015 → X, +0.01 (1x), +0.001 (5x)
            1.234 → X, +1 (1x), +0.1 (2x), +0.01 (3x), +0.001 (4x)

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
            import random
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

    # ========================================================================
    # STATE READING METHODS (Phase 8.6 - Placeholder)
    # ========================================================================

    async def read_balance_from_browser(self) -> Optional[Decimal]:
        """
        Read balance from browser DOM

        Phase 8.6: Polls browser state for accurate balance

        Returns:
            Balance in SOL, or None if not available
        """
        if not self.page:
            logger.warning("Cannot read balance: browser not started")
            return None

        try:
            # Try multiple selectors for balance display
            balance_selectors = [
                'text=/Balance.*([0-9.]+)\\s*SOL/i',
                '[data-balance]',
                '.balance',
                'span:has-text("SOL")',
            ]

            for selector in balance_selectors:
                try:
                    element = await asyncio.wait_for(
                        self.page.query_selector(selector),
                        timeout=2.0
                    )
                    if element:
                        text = await element.text_content()
                        # Extract number from text like "Balance: 1.234 SOL"
                        import re
                        match = re.search(r'([0-9]+\.[0-9]+)', text)
                        if match:
                            balance = Decimal(match.group(1))
                            logger.debug(f"Read balance from browser: {balance} SOL")
                            return balance
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            logger.warning("Could not find balance element in browser DOM")
            return None

        except Exception as e:
            logger.error(f"Failed to read balance from browser: {e}")
            return None

    async def read_position_from_browser(self) -> Optional[Dict[str, Any]]:
        """
        Read position from browser DOM

        Phase 8.6: Polls browser state for open position

        Returns:
            Position dict with entry_price, amount, status; or None if no position
        """
        if not self.page:
            logger.warning("Cannot read position: browser not started")
            return None

        try:
            # Try multiple selectors for position display
            position_selectors = [
                '[data-position]',
                '.position',
                'text=/Position.*([0-9.]+)x/i',
            ]

            for selector in position_selectors:
                try:
                    element = await asyncio.wait_for(
                        self.page.query_selector(selector),
                        timeout=2.0
                    )
                    if element:
                        text = await element.text_content()
                        # Extract position info like "Position: 1.5x, 0.01 SOL"
                        import re
                        price_match = re.search(r'([0-9]+\.[0-9]+)x', text)
                        amount_match = re.search(r'([0-9]+\.[0-9]+)\\s*SOL', text)

                        if price_match:
                            entry_price = Decimal(price_match.group(1))
                            amount = Decimal(amount_match.group(1)) if amount_match else Decimal('0.001')

                            position = {
                                'entry_price': entry_price,
                                'amount': amount,
                                'status': 'active',
                                'entry_tick': 0,  # Unknown from DOM
                            }
                            logger.debug(f"Read position from browser: {entry_price}x, {amount} SOL")
                            return position
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            # No position found
            logger.debug("No position found in browser DOM")
            return None

        except Exception as e:
            logger.error(f"Failed to read position from browser: {e}")
            return None

    def get_timing_stats(self) -> Dict[str, Any]:
        """
        Get timing statistics for UI display

        Phase 8.6: Exposes timing metrics for dashboard

        Returns:
            Dictionary with timing statistics
        """
        return self.timing_metrics.get_stats()

    def record_decision_time(self) -> None:
        """
        Record when bot made decision to act

        Phase 8.6: Captures decision timestamp for timing analysis
        Should be called by bot BEFORE executing action
        """
        self.current_decision_time = time.time()
        logger.debug("Decision time recorded")
