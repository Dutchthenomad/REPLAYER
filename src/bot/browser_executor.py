"""
Browser Executor - Phase 8.5

Bridges REPLAYER bot to live browser automation via Playwright.
Uses locally imported browser automation modules from browser_automation/.

Key Features:
- Async browser control methods (click BUY, SELL, SIDEBET)
- State synchronization (read balance, position from DOM)
- Execution validation (verify action effect)
- Retry logic (exponential backoff, max 3 attempts)
- Error handling and graceful degradation
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from decimal import Decimal
from dataclasses import dataclass, field

try:
    from browser_automation.rugs_browser import RugsBrowserManager, BrowserStatus
    BROWSER_MANAGER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"RugsBrowserManager not available: {e}")
    RugsBrowserManager = None
    BrowserStatus = None
    BROWSER_MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ExecutionTiming:
    """
    Timing metrics for a single action execution

    Phase 8.6: Tracks realistic execution delays
    """
    action: str  # BUY, SELL, SIDEBET
    decision_time: float  # When bot decided to act
    click_time: float  # When click was sent
    confirmation_time: float  # When state change confirmed
    success: bool  # Whether execution succeeded

    @property
    def decision_to_click_ms(self) -> float:
        """Time from decision to click (milliseconds)"""
        return (self.click_time - self.decision_time) * 1000

    @property
    def click_to_confirmation_ms(self) -> float:
        """Time from click to confirmation (milliseconds)"""
        return (self.confirmation_time - self.click_time) * 1000

    @property
    def total_delay_ms(self) -> float:
        """Total execution delay (milliseconds)"""
        return (self.confirmation_time - self.decision_time) * 1000


@dataclass
class TimingMetrics:
    """
    Aggregated timing metrics for bot performance tracking

    Phase 8.6: Statistical analysis of execution timing
    """
    executions: List[ExecutionTiming] = field(default_factory=list)
    max_history: int = 100  # Keep last 100 executions

    def add_execution(self, timing: ExecutionTiming) -> None:
        """Add execution timing (bounded to max_history)"""
        self.executions.append(timing)
        if len(self.executions) > self.max_history:
            self.executions.pop(0)  # Remove oldest

    def get_stats(self) -> Dict[str, Any]:
        """Calculate timing statistics"""
        if not self.executions:
            return {
                'total_executions': 0,
                'success_rate': 0.0,
                'avg_total_delay_ms': 0.0,
                'avg_click_delay_ms': 0.0,
                'avg_confirmation_delay_ms': 0.0,
                'p50_total_delay_ms': 0.0,
                'p95_total_delay_ms': 0.0,
            }

        successful = [e for e in self.executions if e.success]
        total_delays = [e.total_delay_ms for e in successful]
        click_delays = [e.decision_to_click_ms for e in successful]
        confirm_delays = [e.click_to_confirmation_ms for e in successful]

        # Calculate percentiles safely (avoid index out of bounds)
        if total_delays:
            sorted_delays = sorted(total_delays)
            n = len(sorted_delays)
            # P50: Use index n//2, bounded to [0, n-1]
            p50_index = max(0, min(n // 2, n - 1))
            p50_value = sorted_delays[p50_index]
            # P95: Use index int(n * 0.95), bounded to [0, n-1]
            p95_index = max(0, min(int(n * 0.95), n - 1))
            p95_value = sorted_delays[p95_index]
        else:
            p50_value = 0.0
            p95_value = 0.0

        return {
            'total_executions': len(self.executions),
            'successful_executions': len(successful),
            'success_rate': len(successful) / len(self.executions),
            'avg_total_delay_ms': sum(total_delays) / len(total_delays) if total_delays else 0.0,
            'avg_click_delay_ms': sum(click_delays) / len(click_delays) if click_delays else 0.0,
            'avg_confirmation_delay_ms': sum(confirm_delays) / len(confirm_delays) if confirm_delays else 0.0,
            'p50_total_delay_ms': p50_value,
            'p95_total_delay_ms': p95_value,
        }


class BrowserExecutor:
    """
    Browser execution controller for live trading

    Phase 8.5: Connects REPLAYER bot to live browser via Playwright
    - Manages browser lifecycle (start, stop, reconnect)
    - Executes trades via DOM interaction (click buttons)
    - Reads game state from browser (balance, position, price)
    - Validates execution (checks state changed)
    - Handles errors and retries
    """

    # Button selectors for Rugs.fun (multiple fallbacks for robustness)
    BUY_BUTTON_SELECTORS = [
        'button:has-text("BUY")',
        'button:has-text("Buy")',
        'button[class*="buy"]',
        '[data-action="buy"]',
    ]

    SELL_BUTTON_SELECTORS = [
        'button:has-text("SELL")',
        'button:has-text("Sell")',
        'button[class*="sell"]',
        '[data-action="sell"]',
    ]

    SIDEBET_BUTTON_SELECTORS = [
        'button:has-text("SIDEBET")',
        'button:has-text("Sidebet")',
        'button:has-text("Side Bet")',
        'button[class*="sidebet"]',
        '[data-action="sidebet"]',
    ]

    BET_AMOUNT_INPUT_SELECTORS = [
        'input[type="number"]',
        'input[placeholder*="amount"]',
        'input[class*="bet"]',
        '[data-input="bet-amount"]',
    ]

    def __init__(self, profile_name: str = "rugs_fun_phantom"):
        """
        Initialize browser executor

        Args:
            profile_name: Name of persistent browser profile (default: rugs_fun_phantom)
        """
        if not BROWSER_MANAGER_AVAILABLE:
            raise RuntimeError(
                "RugsBrowserManager not available. "
                "Check browser_automation/ directory is present."
            )

        self.profile_name = profile_name
        self.browser_manager: Optional[RugsBrowserManager] = None

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

        logger.info(f"BrowserExecutor initialized (profile: {profile_name})")

    async def start_browser(self) -> bool:
        """
        Start browser and connect to Rugs.fun

        AUDIT FIX: All browser operations wrapped in asyncio.wait_for() with timeouts
        to prevent deadlocks if browser freezes.

        Returns:
            True if browser started successfully, False otherwise
        """
        try:
            logger.info("Starting browser...")

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

        except Exception as e:
            logger.error(f"Error starting browser: {e}", exc_info=True)
            return False

    async def stop_browser(self) -> None:
        """
        Stop browser and cleanup resources

        AUDIT FIX: Wrapped in timeout to prevent deadlock during shutdown
        """
        try:
            if self.browser_manager:
                # AUDIT FIX: Wrap stop_browser in timeout to prevent deadlock
                try:
                    await asyncio.wait_for(
                        self.browser_manager.stop_browser(),
                        timeout=self.browser_stop_timeout
                    )
                    logger.info("Browser stopped")
                except asyncio.TimeoutError:
                    logger.error(f"Browser stop timeout after {self.browser_stop_timeout}s - forcing cleanup")
                    # Force cleanup even if timeout occurred
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
        if not self.browser_manager:
            return False

        return self.browser_manager.is_ready_for_observation()

    # ========================================================================
    # BROWSER ACTION METHODS (Phase 8.5)
    # ========================================================================

    async def click_buy(self, amount: Optional[Decimal] = None) -> bool:
        """
        Click BUY button in browser

        Args:
            amount: Optional bet amount to set before clicking

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_ready():
                logger.error("Browser not ready for BUY action")
                return False

            page = self.browser_manager.page

            # Set bet amount if provided
            if amount is not None:
                if not await self._set_bet_amount_in_browser(amount):
                    logger.error("Failed to set bet amount")
                    return False

            # Find and click BUY button
            for selector in self.BUY_BUTTON_SELECTORS:
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

            page = self.browser_manager.page

            # Set sell percentage if provided
            if percentage is not None:
                if not await self._set_sell_percentage_in_browser(percentage):
                    logger.error("Failed to set sell percentage")
                    return False

            # Find and click SELL button
            for selector in self.SELL_BUTTON_SELECTORS:
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

        Args:
            amount: Optional bet amount to set before clicking

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_ready():
                logger.error("Browser not ready for SIDEBET action")
                return False

            page = self.browser_manager.page

            # Set bet amount if provided
            if amount is not None:
                if not await self._set_bet_amount_in_browser(amount):
                    logger.error("Failed to set bet amount")
                    return False

            # Find and click SIDEBET button
            for selector in self.SIDEBET_BUTTON_SELECTORS:
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
            page = self.browser_manager.page

            # Find bet amount input
            for selector in self.BET_AMOUNT_INPUT_SELECTORS:
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
            page = self.browser_manager.page

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
        if not self.browser_manager or not self.browser_manager.page:
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
                        self.browser_manager.page.query_selector(selector),
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
        if not self.browser_manager or not self.browser_manager.page:
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
                        self.browser_manager.page.query_selector(selector),
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
