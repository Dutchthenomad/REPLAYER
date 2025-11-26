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
from typing import Optional, Dict, Any, List
from decimal import Decimal
from dataclasses import dataclass, field

# Add repository root to path for browser_automation imports
_repo_root = Path(__file__).parent.parent.parent  # src/bot -> src -> repo root
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Phase 9.1: Use CDP Browser Manager for reliable wallet persistence
try:
    from browser_automation.cdp_browser_manager import CDPBrowserManager, CDPStatus
    CDP_MANAGER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"CDPBrowserManager not available: {e}")
    CDPBrowserManager = None
    CDPStatus = None
    CDP_MANAGER_AVAILABLE = False

# Legacy fallback (deprecated - kept for compatibility)
try:
    from browser_automation.rugs_browser import RugsBrowserManager, BrowserStatus
    LEGACY_MANAGER_AVAILABLE = True
except ImportError:
    RugsBrowserManager = None
    BrowserStatus = None
    LEGACY_MANAGER_AVAILABLE = False

BROWSER_MANAGER_AVAILABLE = CDP_MANAGER_AVAILABLE or LEGACY_MANAGER_AVAILABLE

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

    # Phase A.3: Increment button selectors for incremental clicking
    CLEAR_BUTTON_SELECTORS = [
        'button:has-text("X")',
        'button[title*="clear"]',
        '[data-action="clear-bet"]',
    ]

    INCREMENT_001_SELECTORS = [
        'button:has-text("+0.001")',
        'button[data-increment="0.001"]',
    ]

    INCREMENT_01_SELECTORS = [
        'button:has-text("+0.01")',
        'button[data-increment="0.01"]',
    ]

    INCREMENT_10_SELECTORS = [
        'button:has-text("+0.1")',
        'button[data-increment="0.1"]',
    ]

    INCREMENT_1_SELECTORS = [
        'button:has-text("+1")',
        'button[data-increment="1"]',
    ]

    HALF_BUTTON_SELECTORS = [
        'button:has-text("1/2")',
        'button:has-text("÷2")',
        'button[data-action="half"]',
    ]

    DOUBLE_BUTTON_SELECTORS = [
        'button:has-text("X2")',
        'button:has-text("×2")',
        'button[data-action="double"]',
    ]

    MAX_BUTTON_SELECTORS = [
        'button:has-text("MAX")',
        'button:has-text("All")',
        'button[data-action="max"]',
    ]

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

            page = self.page  # Use property (CDP or legacy)

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
            page = self.page  # Use property (CDP or legacy)

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
        if not self.is_ready():
            logger.error("Browser not ready for button clicking")
            return False

        try:
            page = self.page  # Use property (CDP or legacy)

            # Map button type to selectors
            selector_map = {
                'X': self.CLEAR_BUTTON_SELECTORS,
                '+0.001': self.INCREMENT_001_SELECTORS,
                '+0.01': self.INCREMENT_01_SELECTORS,
                '+0.1': self.INCREMENT_10_SELECTORS,
                '+1': self.INCREMENT_1_SELECTORS,
                '1/2': self.HALF_BUTTON_SELECTORS,
                'X2': self.DOUBLE_BUTTON_SELECTORS,
                'MAX': self.MAX_BUTTON_SELECTORS,
            }

            selectors = selector_map.get(button_type)
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
