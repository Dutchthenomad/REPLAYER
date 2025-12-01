"""
Browser Bridge - Phase 9.3

Bridges REPLAYER UI button clicks to the live browser game.

When enabled, every button click in REPLAYER simultaneously executes
in the live browser, enabling real trading with the same interface.

Key Features:
- Async-safe bridging (UI is Tkinter, browser is async)
- One-way sync: UI -> Browser (browser is the "slave")
- Non-blocking: UI never waits for browser response
- Graceful degradation: If browser action fails, UI action still works

Usage:
    bridge = BrowserBridge()
    await bridge.connect()  # Connect to browser

    # When UI button clicked:
    bridge.on_increment_clicked('+0.001')  # Async-queues browser click
    bridge.on_buy_clicked()
    bridge.on_sell_clicked()
"""

import asyncio
import json
import logging
import threading
import time
from typing import Optional, Callable
from decimal import Decimal
from enum import Enum

logger = logging.getLogger(__name__)


class BridgeStatus(Enum):
    """Browser bridge connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"  # Reserved for future use / compatibility


class BrowserBridge:
    """
    Bridges REPLAYER UI to live browser via CDP.

    Architecture:
    - UI thread (Tkinter) calls bridge methods synchronously
    - Bridge queues async operations for the browser
    - Background async loop processes the queue
    - Browser clicks happen in parallel with UI updates

    This ensures:
    1. UI never blocks waiting for browser
    2. Browser actions execute as fast as possible
    3. Failures don't break the UI
    """

    # Button text mappings for browser clicks (via JavaScript)
    BUTTON_SELECTORS = {
        # Increment buttons
        'X': 'button:has-text("X"):near(input[type="number"])',
        '+0.001': 'button:has-text("+0.001")',
        '+0.01': 'button:has-text("+0.01")',
        '+0.1': 'button:has-text("+0.1")',
        '+1': 'button:has-text("+1")',
        '1/2': 'button:has-text("1/2")',
        'X2': 'button:has-text("X2")',
        'MAX': 'button:has-text("MAX")',
        # Action buttons
        'BUY': 'button:has-text("BUY")',
        'SELL': 'button:has-text("SELL")',
        'SIDEBET': 'button:has-text("SIDEBET")',
        # Percentage buttons
        '10%': 'button:has-text("10%")',
        '25%': 'button:has-text("25%")',
        '50%': 'button:has-text("50%")',
        '100%': 'button:has-text("100%")',
    }

    # CSS Selector fallback (used if text-based selection fails)
    # Updated: 2025-11-24 - Using CSS selectors instead of XPath (more reliable)
    BUTTON_CSS_SELECTORS = {
        'BUY': '#root > div > div.soapy-container.layout-horizontal.MuiBox-root.css-0 > div.soapy-container.MuiBox-root.css-0 > div > div._tradeControlsContainer_17syu_29 > div > div > div._buttonsRow_73g5s_247 > div:nth-child(1) > button',
        # Generic fallbacks for SELL / SIDEBET when text search fails
        'SELL': '#root > div > div.soapy-container.layout-horizontal.MuiBox-root.css-0 > div.soapy-container.MuiBox-root.css-0 > div > div._tradeControlsContainer_17syu_29 > div > div > div._buttonsRow_73g5s_247 > div:nth-child(2) > button, button[data-action=\"sell\"], button[class*=\"sell\"]',
        'SIDEBET': '#root > div > div.soapy-container.layout-horizontal.MuiBox-root.css-0 > div.soapy-container.MuiBox-root.css-0 > div > div._tradeControlsContainer_17syu_29 > div > div > div._buttonsRow_73g5s_247 > div:nth-child(3) > button, button[data-action=\"sidebet\"], button[class*=\"sidebet\"], button[class*=\"side-bet\"]',
        # Note: Increment and percentage buttons generally work with text matching
    }

    def __init__(self):
        """Initialize browser bridge"""
        self.status = BridgeStatus.DISCONNECTED
        self.cdp_manager = None

        # Async infrastructure
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._action_queue: asyncio.Queue = None
        self._running = False

        # Callback for status changes
        self.on_status_change: Optional[Callable[[BridgeStatus], None]] = None

        logger.info("BrowserBridge initialized")

    def _set_status(self, status: BridgeStatus):
        """Update status and notify callback"""
        self.status = status
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
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()
        logger.info("Browser bridge async loop started")

    def _run_async_loop(self):
        """Background thread running the async event loop"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._action_queue = asyncio.Queue()

        try:
            self._loop.run_until_complete(self._process_actions())
        except Exception as e:
            logger.error(f"Async loop error: {e}")
        finally:
            self._loop.close()
            self._running = False

    async def _process_actions(self):
        """Process queued browser actions"""
        while self._running:
            try:
                # Wait for action with timeout (allows checking _running flag)
                try:
                    action = await asyncio.wait_for(
                        self._action_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Execute the action
                action_type = action.get('type')

                if action_type == 'connect':
                    await self._do_connect()
                elif action_type == 'disconnect':
                    await self._do_disconnect()
                elif action_type == 'click':
                    await self._do_click(action.get('button'))
                elif action_type == 'stop':
                    break

            except Exception as e:
                logger.error(f"Action processing error: {e}")

    def _queue_action(self, action: dict):
        """Queue an action for the async loop"""
        if not self._running:
            logger.warning("Bridge not running, cannot queue action")
            return

        # Wait briefly for loop to initialize after start_async_loop
        if not self._loop:
            for _ in range(10):  # up to ~0.5s
                time.sleep(0.05)
                if self._loop:
                    break
        if not self._loop or not self._action_queue:
            logger.warning("Bridge loop not ready, dropping action: %s", action.get('type'))
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
        """
        Connect to browser (non-blocking).

        Call this from UI thread - actual connection happens async.
        """
        if not self._running:
            self.start_async_loop()

        self._set_status(BridgeStatus.CONNECTING)
        self._queue_action({'type': 'connect'})

    def connect_async(self):
        """
        Backwards-compatible alias for connect().

        Some callers still expect connect_async; this simply delegates to
        the non-blocking connect() to avoid runtime AttributeError.
        """
        self.connect()

    def disconnect(self):
        """
        Disconnect from browser (non-blocking).
        """
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
        """
        Called when increment button clicked in UI.

        Args:
            button_type: '+0.001', '+0.01', '+0.1', '+1', '1/2', 'X2', 'MAX', 'X'
        """
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
        """
        Called when percentage button clicked in UI.

        Args:
            percentage: 0.1, 0.25, 0.5, or 1.0
        """
        if not self.is_connected():
            return

        pct_text = {0.1: '10%', 0.25: '25%', 0.5: '50%', 1.0: '100%'}
        button = pct_text.get(percentage)
        if button:
            self._queue_action({'type': 'click', 'button': button})
            logger.debug(f"Bridge: Queued {button} click")

    # ========================================================================
    # ASYNC IMPLEMENTATIONS (run in background thread)
    # ========================================================================

    async def _do_connect(self):
        """Actually connect to browser (async)"""
        try:
            # Import here to avoid circular imports
            from browser_automation.cdp_browser_manager import CDPBrowserManager

            self.cdp_manager = CDPBrowserManager()

            # Use the bulletproof connection sequence
            success = await self.cdp_manager.full_connect_sequence()

            if success:
                self._set_status(BridgeStatus.CONNECTED)
                logger.info("Browser bridge connected!")
            else:
                self._set_status(BridgeStatus.ERROR)
                logger.error("Browser bridge connection failed")

        except Exception as e:
            logger.error(f"Connection error: {e}")
            self._set_status(BridgeStatus.ERROR)

    async def _do_disconnect(self):
        """Actually disconnect from browser (async)"""
        try:
            if self.cdp_manager:
                await self.cdp_manager.disconnect()
                self.cdp_manager = None

            self._set_status(BridgeStatus.DISCONNECTED)
            logger.info("Browser bridge disconnected")

        except Exception as e:
            logger.error(f"Disconnect error: {e}")
            self._set_status(BridgeStatus.ERROR)

    async def _do_click(self, button: str):
        """
        Actually click a button in the browser (async).

        Uses JavaScript click to bypass visibility checks.
        Strategy:
        1. Text-based (exact match > starts with > contains)
        2. CSS selector fallback (if text-based fails and selector exists)

        AUDIT FIX: Improved visibility check to handle position:fixed elements
        Updated 2025-11-24: Changed from XPath to CSS selectors (more reliable)
        """
        if not self.cdp_manager or not self.cdp_manager.page:
            logger.warning(f"Cannot click {button}: browser not connected")
            return

        try:
            page = self.cdp_manager.page

            # Use JavaScript to find and click the button
            # Priority: normalized text -> data-action/aria -> class hints -> CSS fallback
            clicked = await page.evaluate(f"""(selectorQuery) => {{
                const allButtons = Array.from(document.querySelectorAll(selectorQuery));

                const normalize = (txt = '') => txt.replace(/\\s+/g, '').toUpperCase();

                // AUDIT FIX: Improved visibility check (handles position:fixed)
                const isVisible = (el) => {{
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.display !== 'none' &&
                           style.visibility !== 'hidden' &&
                           rect.width > 0 &&
                           rect.height > 0 &&
                           style.pointerEvents !== 'none';
                }};

                const buttons = allButtons.filter(isVisible);
                const searchText = {json.dumps(button)};
                const normalizedTarget = normalize(searchText);

                // 1) Exact / startswith / contains on normalized text (handles "SIDE BET" vs "SIDEBET")
                let target = buttons.find(b => normalize(b.textContent || '') === normalizedTarget);
                if (!target) {{
                    target = buttons.find(b => normalize(b.textContent || '').startsWith(normalizedTarget));
                }}
                if (!target && searchText.length > 1) {{
                    target = buttons.find(b => normalize(b.textContent || '').includes(normalizedTarget));
                }}

                // 2) data-action / aria-label / data-testid fallbacks
                if (!target) {{
                    target = buttons.find(b => normalize(b.getAttribute('data-action') || '') === normalizedTarget);
                }}
                if (!target) {{
                    target = buttons.find(b => normalize(b.getAttribute('aria-label') || '') === normalizedTarget);
                }}
                if (!target) {{
                    target = buttons.find(b => normalize(b.getAttribute('data-testid') || '') === normalizedTarget);
                }}
                if (!target) {{
                    target = buttons.find(b => normalize(b.getAttribute('data-qa') || '') === normalizedTarget);
                }}

                // 3) Class name hint (e.g., btn-sell, btn-sidebet)
                if (!target) {{
                    target = buttons.find(b => {{
                        const classes = (b.className || '').split(/\\s+/).map(normalize);
                        return classes.some(c => c === normalizedTarget || c.includes(normalizedTarget));
                    }});
                }}

                if (target) {{
                    target.click();
                    return {{ success: true, text: (target.textContent || '').trim(), method: 'text' }};
                }}
                return {{ success: false, availableButtons: buttons.slice(0, 15).map(b => (b.textContent || '').trim().substring(0, 30)) }};
            }}""", "button, [role=\"button\"], [data-action], [data-testid], [data-qa], [class*=\"button\" i], [class*=\"Button\" i]")

            if clicked.get('success'):
                logger.debug(f"Browser: Clicked '{button}' (found: '{clicked.get('text')}')")
                return

            # Text-based selection failed - try CSS selector fallback
            if button in self.BUTTON_CSS_SELECTORS:
                selector = self.BUTTON_CSS_SELECTORS[button]
                logger.info(f"Browser: Text search failed for '{button}', trying CSS selector")

                css_clicked = await page.evaluate(f"""() => {{
                    const selector = {json.dumps(selector)};
                    const element = document.querySelector(selector);

                    if (element) {{
                        element.click();
                        return {{ success: true, tag: element.tagName, text: element.textContent?.trim().substring(0, 30) }};
                    }}
                    return {{ success: false }};
                }}""")

                if css_clicked.get('success'):
                    logger.info(f"Browser: CSS selector click succeeded for '{button}': {css_clicked.get('tag')} - {css_clicked.get('text')}")
                    return
                else:
                    logger.warning(f"Browser: CSS selector click failed for '{button}': element not found")

            # Both methods failed
            available = clicked.get('availableButtons', [])
            logger.warning(f"Browser: Button '{button}' not found via text or CSS selector. Available buttons: {available[:5]}")

        except Exception as e:
            logger.error(f"Click error for {button}: {e}")


# Singleton instance for global access
# PHASE 2 FIX: Corrected thread-safe singleton pattern
_bridge_instance: Optional[BrowserBridge] = None
_bridge_lock = threading.Lock()


def get_browser_bridge() -> BrowserBridge:
    """
    Get or create the singleton browser bridge instance (thread-safe).

    PHASE 2 FIX: Always acquire lock before checking instance.
    The previous double-check pattern had a race window where the first
    check outside the lock could see a partially constructed object.
    """
    global _bridge_instance
    with _bridge_lock:
        if _bridge_instance is None:
            _bridge_instance = BrowserBridge()
        return _bridge_instance
