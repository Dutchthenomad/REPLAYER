"""
Browser Bridge - Phase 9.3 PRODUCTION FIX

Bridges REPLAYER UI button clicks to the live browser game.

CRITICAL FIXES (Audit 2025-11-30):
1. Multi-strategy selector system (text -> contains -> CSS -> role-based)
2. Proper visibility detection for position:fixed elements
3. Timeout handling to prevent deadlocks
4. Pre-click state verification
5. Retry with exponential backoff
6. Comprehensive logging for debugging

When enabled, every button click in REPLAYER simultaneously executes
in the live browser, enabling real trading with the same interface.

Usage:
    bridge = BrowserBridge()
    await bridge.connect()  # Connect to browser
    bridge.on_buy_clicked()  # Async-queues browser click
"""

import asyncio
import logging
import threading
import time
from typing import Optional, Callable, Dict, Any, List
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass

from sources.cdp_websocket_interceptor import CDPWebSocketInterceptor
from services.event_source_manager import EventSourceManager, EventSource
from services.rag_ingester import RAGIngester
from services.event_bus import Events, event_bus

logger = logging.getLogger(__name__)


class BridgeStatus(Enum):
    """Browser bridge connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"  # Added for reconnection logic


@dataclass
class ClickResult:
    """Result of a button click attempt"""
    success: bool
    method: str = ""  # Which selector strategy worked
    button_text: str = ""  # Actual button text found
    error: str = ""
    attempt: int = 0


class SelectorStrategy:
    """
    Multi-strategy selector system for robust button finding.

    Priority order:
    1. Starts-with text match (handles "BUY" -> "BUY+0.030 SOL")
    2. Contains text match (backup)
    3. CSS selector (structural fallback)
    4. Role + text match (ARIA fallback)
    5. Class name pattern match
    """

    # Primary selectors - starts-with matching for dynamic text
    # These handle cases where button text is "BUY+0.030 SOL" but we search for "BUY"
    # UPDATED 2025-12-01: Added new rugs.fun UI text patterns
    BUTTON_TEXT_PATTERNS = {
        'BUY': ['BUY', 'Buy', 'buy'],
        'SELL': ['SELL', 'Sell', 'sell'],
        'SIDEBET': ['SIDEBET', 'SIDE', 'Side', 'sidebet', 'side', 'SIDE BET', 'Side Bet'],
        'X': ['×', '✕', 'X', 'x', '✖'],  # Clear button variants
        '+0.001': ['+0.001', '+ 0.001'],
        '+0.01': ['+0.01', '+ 0.01'],
        '+0.1': ['+0.1', '+ 0.1'],
        '+1': ['+1', '+ 1'],
        '1/2': ['1/2', '½', '0.5x', 'Half'],
        'X2': ['X2', 'x2', '2x', '2X', 'Double'],
        'MAX': ['MAX', 'Max', 'max', 'ALL'],
        '10%': ['10%', '10 %'],
        '25%': ['25%', '25 %'],
        '50%': ['50%', '50 %'],
        '100%': ['100%', '100 %', 'ALL'],
    }

    # CSS Selectors - structural fallback when text matching fails
    # These are more brittle but work when text matching completely fails
    # UPDATED 2025-12-01: New rugs.fun UI specific selectors
    BUTTON_CSS_SELECTORS = {
        'BUY': [
            # Primary: New rugs.fun specific class (div container)
            'div[class*="_buttonSection_"]:nth-child(1)',
            '[class*="_buttonsRow_"] > div:first-child',
            'div[class*="_buttonSection_"]:nth-child(1) button',
            '[class*="_buttonsRow_"] > div:first-child button',
            # Button container with buy-related classes
            'button[class*="buy" i]',
            'button[class*="Buy" i]',
            # Trade controls area - buy is typically first button
            '[class*="tradeControls"] button:first-of-type',
            '[class*="buttonsRow"] button:first-child',
            # MUI specific patterns
            '.MuiButton-root[class*="buy" i]',
            # Data attribute fallback
            '[data-action="buy"]',
            '[data-testid="buy-button"]',
        ],
        'SELL': [
            # Primary: New rugs.fun specific class (div container)
            'div[class*="_buttonSection_"]:nth-child(2)',
            '[class*="_buttonsRow_"] > div:nth-child(2)',
            'div[class*="_buttonSection_"]:nth-child(2) button',
            '[class*="_buttonsRow_"] > div:nth-child(2) button',
            # Legacy selectors
            'button[class*="sell" i]',
            'button[class*="Sell" i]',
            # Sell is typically second button in trade controls
            '[class*="tradeControls"] button:nth-of-type(2)',
            '[class*="buttonsRow"] button:nth-child(2)',
            '.MuiButton-root[class*="sell" i]',
            '[data-action="sell"]',
            '[data-testid="sell-button"]',
        ],
        'SIDEBET': [
            # Primary: New rugs.fun specific class
            '.bet-button',
            '[class*="bet-button"]',
            'div.bet-button',
            '[class*="sidebet-banner"] [class*="bet-button"]',
            '[class*="sidebet-container"] [class*="bet-button"]',
            # Legacy selectors
            'button[class*="side" i]',
            'button[class*="Side" i]',
            'button[class*="sidebet" i]',
            # Sidebet is typically third button
            '[class*="tradeControls"] button:nth-of-type(3)',
            '[class*="buttonsRow"] button:nth-child(3)',
            '[data-action="sidebet"]',
            '[data-action="side"]',
            '[data-testid="sidebet-button"]',
        ],
        'X': [
            # Primary: New rugs.fun specific class (escaped underscore for CSS)
            'button[class*="_clearButton_"]',
            '[class*="_clearButton_"]',
            '[class*="_inputActions_"] button',
            '[class*="_amountInputContainer_"] [class*="_clearButton_"]',
            # Legacy selectors
            'button[class*="clear" i]',
            'button[class*="clearButton" i]',
            'input[type="number"] ~ button',
            '[class*="inputGroup"] button:last-child',
        ],
        '10%': [
            'button[class*="_percentageBtn_"]:nth-child(1)',
            '[class*="_sellControlButtonsContainer_"] button:nth-child(1)',
        ],
        '25%': [
            'button[class*="_percentageBtn_"]:nth-child(2)',
            '[class*="_sellControlButtonsContainer_"] button:nth-child(2)',
        ],
        '50%': [
            'button[class*="_percentageBtn_"]:nth-child(3)',
            '[class*="_sellControlButtonsContainer_"] button:nth-child(3)',
        ],
        '100%': [
            'button[class*="_percentageBtn_"]:nth-child(4)',
            '[class*="_sellControlButtonsContainer_"] button:nth-child(4)',
        ],
    }

    # Class name patterns for fallback matching
    # UPDATED 2025-12-01: Added new rugs.fun class patterns
    CLASS_PATTERNS = {
        'BUY': ['buy', 'purchase', 'long', 'bid', 'buttonSection'],
        'SELL': ['sell', 'exit', 'short', 'ask', 'buttonSection'],
        'SIDEBET': ['side', 'sidebet', 'hedge', 'insurance', 'bet-button'],
        'X': ['clear', 'clearButton'],
        '10%': ['percentageBtn'],
        '25%': ['percentageBtn'],
        '50%': ['percentageBtn'],
        '100%': ['percentageBtn'],
    }

    @classmethod
    def get_text_patterns(cls, button: str) -> List[str]:
        """Get text patterns for a button"""
        return cls.BUTTON_TEXT_PATTERNS.get(button, [button])

    @classmethod
    def get_css_selectors(cls, button: str) -> List[str]:
        """Get CSS selectors for a button"""
        return cls.BUTTON_CSS_SELECTORS.get(button, [])

    @classmethod
    def get_class_patterns(cls, button: str) -> List[str]:
        """Get class name patterns for a button"""
        return cls.CLASS_PATTERNS.get(button, [button.lower()])


class BrowserBridge:
    """
    Bridges REPLAYER UI to live browser via CDP.

    Architecture:
    - UI thread (Tkinter) calls bridge methods synchronously
    - Bridge queues async operations for the browser
    - Background async loop processes the queue
    - Browser clicks happen in parallel with UI updates
    """

    # Timeouts (in seconds)
    CLICK_TIMEOUT = 10.0
    CONNECT_TIMEOUT = 30.0
    ACTION_TIMEOUT = 5.0

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 0.5  # Exponential backoff base

    def __init__(self):
        """Initialize browser bridge"""
        self.status = BridgeStatus.DISCONNECTED
        self.cdp_manager = None

        # Async infrastructure
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._action_queue: asyncio.Queue = None
        self._running = False
        self._loop_ready = threading.Event()  # FIX: Signal when loop is ready

        # Callback for status changes
        self.on_status_change: Optional[Callable[[BridgeStatus], None]] = None

        # Click statistics for debugging
        self._click_stats: Dict[str, Dict[str, int]] = {}

        # CDP WebSocket interception components (Task 8)
        self._cdp_interceptor = CDPWebSocketInterceptor()
        self._event_source_manager = EventSourceManager()
        self._rag_ingester = RAGIngester()

        # Wire up event flow from CDP interceptor
        def on_cdp_event(event):
            # Publish to EventBus for all subscribers
            event_bus.publish(Events.WS_RAW_EVENT, {'data': event})
            # Catalog for RAG
            self._rag_ingester.catalog(event)

        self._cdp_interceptor.on_event = on_cdp_event

        logger.info("BrowserBridge initialized (PRODUCTION FIX)")

    def _set_status(self, status: BridgeStatus):
        """Update status and notify callback"""
        old_status = self.status
        self.status = status

        if old_status != status:
            logger.info(f"Bridge status: {old_status.value} -> {status.value}")

        if self.on_status_change:
            try:
                self.on_status_change(status)
            except Exception as e:
                logger.error(f"Status callback error: {e}")

    def start_async_loop(self):
        """Start the background async loop for browser operations"""
        if self._running:
            return

        self._running = True
        self._loop_ready.clear()  # Reset the ready signal
        self._thread = threading.Thread(
            target=self._run_async_loop,
            daemon=True,
            name="BrowserBridge-AsyncLoop"
        )
        self._thread.start()

        # FIX: Wait for the loop to be ready before returning
        # This prevents race condition where connect() tries to queue actions
        # before the event loop and queue are created
        if not self._loop_ready.wait(timeout=5.0):
            logger.error("Async loop failed to start within 5 seconds")
            self._running = False
            return

        logger.info("Browser bridge async loop started")

    def _run_async_loop(self):
        """Background thread running the async event loop"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._action_queue = asyncio.Queue()

        # FIX: Signal that the loop is ready for use
        self._loop_ready.set()

        try:
            self._loop.run_until_complete(self._process_actions())
        except Exception as e:
            logger.error(f"Async loop error: {e}", exc_info=True)
        finally:
            self._loop.close()
            self._running = False
            self._loop_ready.clear()  # Clear ready state on shutdown

    async def _process_actions(self):
        """Process queued browser actions"""
        while self._running:
            try:
                # Wait for action with timeout
                try:
                    action = await asyncio.wait_for(
                        self._action_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Execute the action with timeout protection
                action_type = action.get('type')

                try:
                    if action_type == 'connect':
                        await asyncio.wait_for(
                            self._do_connect(),
                            timeout=self.CONNECT_TIMEOUT
                        )
                    elif action_type == 'disconnect':
                        await asyncio.wait_for(
                            self._do_disconnect(),
                            timeout=10.0
                        )
                    elif action_type == 'click':
                        await asyncio.wait_for(
                            self._do_click_with_retry(action.get('button')),
                            timeout=self.CLICK_TIMEOUT
                        )
                    elif action_type == 'stop':
                        break
                except asyncio.TimeoutError:
                    logger.error(f"Action '{action_type}' timed out")

            except Exception as e:
                logger.error(f"Action processing error: {e}", exc_info=True)

    def _queue_action(self, action: dict):
        """Queue an action for the async loop"""
        if not self._running or not self._loop:
            logger.warning("Bridge not running, cannot queue action")
            return

        # Thread-safe queue put
        asyncio.run_coroutine_threadsafe(
            self._action_queue.put(action),
            self._loop
        )

    # ========================================================================
    # PUBLIC SYNC API (called from UI thread)
    # ========================================================================

    def connect(self):
        """Connect to browser (non-blocking)."""
        if not self._running:
            self.start_async_loop()

        self._set_status(BridgeStatus.CONNECTING)
        self._queue_action({'type': 'connect'})

    def connect_async(self):
        """Backwards-compatible alias for connect()."""
        self.connect()

    def disconnect(self):
        """Disconnect from browser (non-blocking)."""
        self._queue_action({'type': 'disconnect'})

    def stop(self):
        """Stop the bridge completely"""
        self._running = False
        if self._loop:
            self._queue_action({'type': 'stop'})

    def is_connected(self) -> bool:
        """Check if browser is connected"""
        return self.status == BridgeStatus.CONNECTED

    # ========================================================================
    # BUTTON CLICK METHODS (called from UI thread)
    # ========================================================================

    def on_increment_clicked(self, button_type: str):
        """Called when increment button clicked in UI."""
        if not self.is_connected():
            return
        self._queue_action({'type': 'click', 'button': button_type})
        logger.debug(f"Bridge: Queued {button_type} click")

    def on_clear_clicked(self):
        """Called when clear (X) button clicked in UI"""
        self.on_increment_clicked('X')

    def on_buy_clicked(self):
        """Called when BUY button clicked in UI"""
        if not self.is_connected():
            return
        self._queue_action({'type': 'click', 'button': 'BUY'})
        logger.debug("Bridge: Queued BUY click")

    def on_sell_clicked(self):
        """Called when SELL button clicked in UI"""
        if not self.is_connected():
            return
        self._queue_action({'type': 'click', 'button': 'SELL'})
        logger.debug("Bridge: Queued SELL click")

    def on_sidebet_clicked(self):
        """Called when SIDEBET button clicked in UI"""
        if not self.is_connected():
            return
        self._queue_action({'type': 'click', 'button': 'SIDEBET'})
        logger.debug("Bridge: Queued SIDEBET click")

    def on_percentage_clicked(self, percentage: float):
        """Called when percentage button clicked in UI."""
        if not self.is_connected():
            return
        pct_text = {0.1: '10%', 0.25: '25%', 0.5: '50%', 1.0: '100%'}
        button = pct_text.get(percentage)
        if button:
            self._queue_action({'type': 'click', 'button': button})
            logger.debug(f"Bridge: Queued {button} click")

    # ========================================================================
    # ASYNC IMPLEMENTATIONS
    # ========================================================================

    async def _do_connect(self):
        """Actually connect to browser (async)"""
        try:
            import sys
            from pathlib import Path
            # Add parent directory for browser_automation imports
            parent_dir = str(Path(__file__).parent.parent.parent)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            from browser.manager import CDPBrowserManager

            self.cdp_manager = CDPBrowserManager()
            success = await self.cdp_manager.full_connect_sequence()

            if success:
                self._set_status(BridgeStatus.CONNECTED)
                logger.info("Browser bridge connected!")

                # Task 8: Start CDP WebSocket interception
                await self._start_cdp_interception()
            else:
                self._set_status(BridgeStatus.ERROR)
                logger.error("Browser bridge connection failed")

        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            self._set_status(BridgeStatus.ERROR)

    async def _do_disconnect(self):
        """Actually disconnect from browser (async)"""
        try:
            # Task 8: Stop CDP WebSocket interception
            await self._stop_cdp_interception()

            if self.cdp_manager:
                await self.cdp_manager.disconnect()
                self.cdp_manager = None

            self._set_status(BridgeStatus.DISCONNECTED)
            logger.info("Browser bridge disconnected")

        except Exception as e:
            logger.error(f"Disconnect error: {e}", exc_info=True)
            self._set_status(BridgeStatus.ERROR)

    # ========================================================================
    # CDP WEBSOCKET INTERCEPTION (Task 8)
    # ========================================================================

    async def _start_cdp_interception(self):
        """
        Start CDP WebSocket interception.

        Creates a CDP session and wires it to the interceptor.
        """
        try:
            if not self.cdp_manager or not self.cdp_manager.context:
                logger.warning("Cannot start CDP interception - no CDP manager or context")
                return

            # Create a CDP session from the browser context
            cdp_session = await self.cdp_manager.context.new_cdp_session(
                self.cdp_manager.page
            )

            # Connect the interceptor
            if self._cdp_interceptor.connect(cdp_session):
                self._event_source_manager.set_cdp_available(True)
                self._event_source_manager.switch_to_best_source()
                self._rag_ingester.start_session()
                logger.info("CDP WebSocket interception started")
            else:
                logger.error("Failed to connect CDP interceptor")

        except Exception as e:
            logger.error(f"Failed to start CDP interception: {e}", exc_info=True)

    async def _stop_cdp_interception(self):
        """
        Stop CDP WebSocket interception.

        Disconnects the interceptor and updates event source manager.
        """
        try:
            self._cdp_interceptor.disconnect()
            self._event_source_manager.set_cdp_available(False)
            self._event_source_manager.switch_to_best_source()
            self._rag_ingester.stop_session()
            logger.info("CDP WebSocket interception stopped")

        except Exception as e:
            logger.error(f"Failed to stop CDP interception: {e}", exc_info=True)

    # ========================================================================
    # BUTTON CLICK IMPLEMENTATIONS
    # ========================================================================

    async def _do_click_with_retry(self, button: str) -> ClickResult:
        """
        Click button with retry logic and exponential backoff.

        PRODUCTION FIX: Implements multi-strategy selector with retries.
        """
        last_result = ClickResult(success=False, error="No attempts made")

        for attempt in range(1, self.MAX_RETRIES + 1):
            result = await self._do_click(button)
            result.attempt = attempt

            if result.success:
                self._record_click_stat(button, 'success', result.method)
                return result

            last_result = result

            if attempt < self.MAX_RETRIES:
                delay = self.RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    f"Click attempt {attempt} failed for '{button}': {result.error}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)

        self._record_click_stat(button, 'failure', last_result.error)
        logger.error(f"All {self.MAX_RETRIES} click attempts failed for '{button}'")
        return last_result

    async def _do_click(self, button: str) -> ClickResult:
        """
        Actually click a button in the browser (async).

        PRODUCTION FIX 2025-12-01: Reordered strategies to prevent X->X2 mismatch
        1. CSS structural selectors FIRST (most reliable with new rugs.fun classes)
        2. Exact text match (prevents X matching X2)
        3. Starts-with text match (handles dynamic text like "BUY+0.030 SOL")
        4. Class pattern matching (last resort)
        """
        if not self.cdp_manager or not self.cdp_manager.page:
            return ClickResult(success=False, error="Browser not connected")

        try:
            page = self.cdp_manager.page

            # Strategy 1: CSS selector FIRST (most reliable - uses specific class names)
            # This prevents issues like 'X' matching 'X2' in text-based matching
            result = await self._try_css_selector_click(page, button)
            if result.success:
                return result

            # Strategy 2: Text-based matching (exact first, then starts-with)
            result = await self._try_text_based_click(page, button)
            if result.success:
                return result

            # Strategy 3: Class pattern matching
            result = await self._try_class_pattern_click(page, button)
            if result.success:
                return result

            # All strategies failed - collect debug info
            available = await self._get_available_buttons(page)
            logger.warning(
                f"All click strategies failed for '{button}'. "
                f"Available buttons: {available[:10]}"
            )

            return ClickResult(
                success=False,
                error=f"Button not found with any strategy. Available: {available[:5]}"
            )

        except Exception as e:
            logger.error(f"Click error for {button}: {e}", exc_info=True)
            return ClickResult(success=False, error=str(e))

    async def _try_text_based_click(self, page, button: str) -> ClickResult:
        """
        Try to click button using text-based matching.

        PRODUCTION FIX 2025-12-01: Added exact match FIRST to prevent X->X2 mismatch.
        Order: exact match -> starts-with -> contains
        """
        patterns = SelectorStrategy.get_text_patterns(button)

        # JavaScript to find button by text patterns
        # FIXED: Try EXACT match first to prevent 'X' matching 'X2'
        js_code = """
        (patterns) => {
            const allButtons = Array.from(document.querySelectorAll('button'));
            // Also check divs that act as buttons (rugs.fun uses div containers)
            const allClickables = [
                ...allButtons,
                ...Array.from(document.querySelectorAll('div[class*="button"], div[class*="Button"]'))
            ];

            // Improved visibility check (handles position:fixed)
            const isVisible = (el) => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none' &&
                       style.visibility !== 'hidden' &&
                       style.opacity !== '0' &&
                       rect.width > 0 &&
                       rect.height > 0 &&
                       rect.top < window.innerHeight &&
                       rect.bottom > 0;
            };

            // Check if button is enabled (not disabled)
            const isEnabled = (el) => {
                return !el.disabled &&
                       !el.classList.contains('disabled') &&
                       el.getAttribute('aria-disabled') !== 'true';
            };

            const visibleButtons = allClickables.filter(b => isVisible(b) && isEnabled(b));

            for (const pattern of patterns) {
                // Strategy 1: EXACT MATCH FIRST (prevents 'X' matching 'X2')
                let target = visibleButtons.find(b => {
                    const text = b.textContent.trim();
                    return text === pattern || text.toUpperCase() === pattern.toUpperCase();
                });

                if (target) {
                    target.click();
                    return { success: true, text: target.textContent.trim(), method: 'exact' };
                }
            }

            // Strategy 2: Starts-with (only if no exact match found)
            for (const pattern of patterns) {
                let target = visibleButtons.find(b => {
                    const text = b.textContent.trim();
                    // Skip if this would be a partial match that could cause issues
                    // e.g., 'X' should not match 'X2'
                    if (pattern.length === 1 && text.length > 1) {
                        return false;  // Single char pattern shouldn't match longer text via starts-with
                    }
                    return text.startsWith(pattern) || text.toUpperCase().startsWith(pattern.toUpperCase());
                });

                if (target) {
                    target.click();
                    return { success: true, text: target.textContent.trim(), method: 'starts-with' };
                }
            }

            // Strategy 3: Contains (most flexible, last resort)
            for (const pattern of patterns) {
                let target = visibleButtons.find(b => {
                    const text = b.textContent.trim().toUpperCase();
                    return text.includes(pattern.toUpperCase());
                });

                if (target) {
                    target.click();
                    return { success: true, text: target.textContent.trim(), method: 'contains' };
                }
            }

            return { success: false };
        }
        """

        try:
            result = await page.evaluate(js_code, patterns)

            if result.get('success'):
                logger.debug(
                    f"Text-based click succeeded for '{button}': "
                    f"found '{result.get('text')}' via {result.get('method')}"
                )
                return ClickResult(
                    success=True,
                    method=f"text-{result.get('method')}",
                    button_text=result.get('text', '')
                )

            return ClickResult(success=False, error="No text match found")

        except Exception as e:
            return ClickResult(success=False, error=f"Text match error: {e}")

    async def _try_css_selector_click(self, page, button: str) -> ClickResult:
        """Try to click button using CSS selectors."""
        selectors = SelectorStrategy.get_css_selectors(button)

        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    # Verify element is visible and enabled
                    is_valid = await page.evaluate("""
                        (el) => {
                            const style = window.getComputedStyle(el);
                            const rect = el.getBoundingClientRect();
                            return !el.disabled &&
                                   style.display !== 'none' &&
                                   style.visibility !== 'hidden' &&
                                   rect.width > 0 && rect.height > 0;
                        }
                    """, element)

                    if is_valid:
                        await element.click()
                        text = await element.text_content()
                        logger.debug(f"CSS selector click succeeded: '{selector}' -> '{text}'")
                        return ClickResult(
                            success=True,
                            method=f"css:{selector[:30]}",
                            button_text=text or ""
                        )
            except Exception:
                continue

        return ClickResult(success=False, error="No CSS selector matched")

    async def _try_class_pattern_click(self, page, button: str) -> ClickResult:
        """Try to click button by class name patterns."""
        patterns = SelectorStrategy.get_class_patterns(button)

        js_code = """
        (patterns) => {
            const buttons = Array.from(document.querySelectorAll('button'));

            for (const pattern of patterns) {
                const target = buttons.find(b => {
                    const classes = b.className.toLowerCase();
                    return classes.includes(pattern) &&
                           !b.disabled &&
                           b.offsetParent !== null;
                });

                if (target) {
                    target.click();
                    return { success: true, text: target.textContent.trim(), class: target.className };
                }
            }
            return { success: false };
        }
        """

        try:
            result = await page.evaluate(js_code, patterns)
            if result.get('success'):
                logger.debug(f"Class pattern click succeeded: {result.get('class')}")
                return ClickResult(
                    success=True,
                    method="class-pattern",
                    button_text=result.get('text', '')
                )
            return ClickResult(success=False, error="No class pattern matched")
        except Exception as e:
            return ClickResult(success=False, error=f"Class pattern error: {e}")

    async def _get_available_buttons(self, page) -> List[str]:
        """Get list of available button texts for debugging."""
        try:
            return await page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('button'))
                        .filter(b => b.offsetParent !== null)
                        .map(b => b.textContent.trim().substring(0, 40))
                        .filter(t => t.length > 0);
                }
            """)
        except Exception:
            return []

    def _record_click_stat(self, button: str, outcome: str, detail: str):
        """Record click statistics for monitoring."""
        if button not in self._click_stats:
            self._click_stats[button] = {'success': 0, 'failure': 0, 'methods': {}}

        self._click_stats[button][outcome] = self._click_stats[button].get(outcome, 0) + 1

        if outcome == 'success':
            methods = self._click_stats[button]['methods']
            methods[detail] = methods.get(detail, 0) + 1

    def get_click_stats(self) -> Dict[str, Any]:
        """Get click statistics for debugging."""
        return self._click_stats.copy()


# Singleton instance for global access
# PRODUCTION FIX: Thread-safe singleton with proper locking
_bridge_instance: Optional[BrowserBridge] = None
_bridge_lock = threading.Lock()


def get_browser_bridge() -> BrowserBridge:
    """Get or create the singleton browser bridge instance (thread-safe)"""
    global _bridge_instance
    if _bridge_instance is None:
        with _bridge_lock:
            # Double-check locking pattern
            if _bridge_instance is None:
                _bridge_instance = BrowserBridge()
    return _bridge_instance


def reset_browser_bridge():
    """Reset the singleton instance (for testing)"""
    global _bridge_instance
    with _bridge_lock:
        if _bridge_instance is not None:
            _bridge_instance.stop()
            _bridge_instance = None
