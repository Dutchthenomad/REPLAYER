#!/usr/bin/env python3
"""
CDP Browser Manager - Phase 9.2 (Bulletproof Connection)

Manages browser lifecycle using Chrome DevTools Protocol (CDP) connection.
This approach solves the MV3 extension issues with Playwright's bundled Chromium.

Key Benefits:
- Uses YOUR system Chrome (not Playwright's Chromium)
- Extensions work natively (no service worker issues)
- Profile persists reliably across sessions
- Wallet stays connected

CRITICAL: Reliable Connection Sequence
1. Connect to Chrome via CDP
2. Navigate to rugs.fun
3. Wait for extensions to initialize
4. RELOAD the page (extensions don't inject into pre-loaded pages!)
5. Wait for page + extensions to fully load
6. VERIFY window.phantom/solflare exists
7. Ready for automation

Usage:
    manager = CDPBrowserManager()
    await manager.connect()  # Launches Chrome if needed, connects via CDP
    await manager.ensure_wallet_ready()  # CRITICAL: Ensures extensions are injected
    # ... use manager.page for automation ...
    await manager.disconnect()
"""

import asyncio
import subprocess
import socket
import logging
from pathlib import Path
from typing import Optional
from enum import Enum

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import config

logger = logging.getLogger(__name__)


class CDPStatus(Enum):
    """CDP Browser Manager status states"""
    DISCONNECTED = "disconnected"
    LAUNCHING_CHROME = "launching_chrome"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    NAVIGATING = "navigating"
    READY = "ready"
    ERROR = "error"


class CDPBrowserManager:
    """
    Manages browser via CDP connection to running Chrome instance.

    This is the bulletproof approach for wallet automation:
    1. Launch Chrome with --remote-debugging-port (or connect to existing)
    2. Connect Playwright via CDP to control the browser
    3. Extensions and profile persist because it's your actual Chrome

    Features:
    - Auto-detect if Chrome is already running on debug port
    - Launch Chrome with correct flags if not running
    - Graceful reconnection on disconnect
    - Profile persistence across sessions
    """

    CDP_PORT = 9222
    PROFILE_DIR = Path.home() / ".gamebot" / "chrome_profiles" / "rugs_bot"
    TARGET_URL = "https://rugs.fun"

    # Chrome binary locations (Linux)
    CHROME_BINARIES = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
    ]

    def __init__(self, cdp_port: int = None, profile_name: str = None):
        """
        Initialize CDP Browser Manager.

        Args:
            cdp_port: Port for Chrome DevTools Protocol (default: from config or 9222)
            profile_name: Name of Chrome profile directory (default: from config or "rugs_bot")
        """
        self.cdp_port = cdp_port or config.BROWSER.get('cdp_port', 9222)
        profile_name = profile_name or config.BROWSER.get('profile_name', "rugs_bot")
        self.profile_path = Path.home() / ".gamebot" / "chrome_profiles" / profile_name

        # Playwright components
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Status tracking
        self.status = CDPStatus.DISCONNECTED
        self._chrome_process: Optional[subprocess.Popen] = None

        # Ensure profile directory exists
        self.profile_path.mkdir(parents=True, exist_ok=True)

    def _find_chrome_binary(self) -> Optional[str]:
        """
        Find Chrome binary on the system.

        Returns:
            Path to Chrome binary, or None if not found
        """
        # Check configured binary first
        config_binary = config.BROWSER.get('chrome_binary')
        if config_binary and Path(config_binary).exists():
            logger.info(f"Using configured Chrome binary: {config_binary}")
            return config_binary

        for binary in self.CHROME_BINARIES:
            if Path(binary).exists():
                logger.info(f"Found Chrome binary: {binary}")
                return binary
        return None

    def _is_port_in_use(self, port: int) -> bool:
        """
        Check if a port is in use.

        Args:
            port: Port number to check

        Returns:
            True if port is in use, False otherwise
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect(('localhost', port))
                return True
            except (ConnectionRefusedError, OSError):
                return False

    async def _is_chrome_running(self) -> bool:
        """
        Check if Chrome is running with debug port.

        Returns:
            True if Chrome is responding on CDP port
        """
        return self._is_port_in_use(self.cdp_port)

    def _check_existing_chrome(self) -> bool:
        """
        Check if Chrome is already running (may conflict with our launch).

        Returns:
            True if existing Chrome process found
        """
        try:
            result = subprocess.run(
                ["pgrep", "-f", "chrome|chromium"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                logger.warning(f"Found {len(pids)} existing Chrome process(es): {pids[:5]}")
                return True
            return False
        except Exception:
            return False

    async def _launch_chrome(self) -> bool:
        """
        Launch Chrome with remote debugging enabled.

        Returns:
            True if Chrome launched successfully
        """
        chrome_binary = self._find_chrome_binary()
        if not chrome_binary:
            logger.error("Chrome binary not found. Please install Google Chrome.")
            return False

        # AUDIT FIX: Check for existing Chrome that might conflict
        if self._check_existing_chrome():
            logger.warning("Existing Chrome detected. This may cause CDP connection issues.")
            logger.info("TIP: Close all Chrome windows or kill Chrome processes first.")

        self.status = CDPStatus.LAUNCHING_CHROME
        logger.info(f"Launching Chrome with debug port {self.cdp_port}...")

        # Chrome launch arguments
        args = [
            chrome_binary,
            f"--remote-debugging-port={self.cdp_port}",
            f"--user-data-dir={self.profile_path}",
            "--start-maximized",
            "--new-window",
            "--no-first-run",
            "--no-default-browser-check",
            self.TARGET_URL,  # Open rugs.fun directly
        ]

        try:
            # AUDIT FIX: Capture stderr for debugging
            self._chrome_process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,  # Capture errors for debugging
                start_new_session=True,  # Detach from parent process
            )

            # Wait for Chrome to start accepting connections
            for i in range(30):  # Wait up to 15 seconds
                await asyncio.sleep(0.5)
                if await self._is_chrome_running():
                    logger.info("Chrome is ready for CDP connection")
                    return True

                # Check if process died
                if self._chrome_process.poll() is not None:
                    stderr = self._chrome_process.stderr.read().decode() if self._chrome_process.stderr else ""
                    logger.error(f"Chrome process exited unexpectedly. Exit code: {self._chrome_process.returncode}")
                    if stderr:
                        logger.error(f"Chrome stderr: {stderr[:500]}")
                    return False

                if i > 0 and i % 10 == 0:
                    logger.info(f"Still waiting for Chrome to start ({i * 0.5:.1f}s elapsed)...")

            logger.error("Chrome failed to start accepting CDP connections after 15 seconds")
            logger.error("TIP: Try closing all Chrome windows and running again, or use a different profile")
            return False

        except Exception as e:
            logger.error(f"Failed to launch Chrome: {e}")
            return False

    async def connect(self) -> bool:
        """
        Connect to Chrome via CDP.

        Will launch Chrome if not already running on debug port.

        Returns:
            True if connection successful
        """
        try:
            # Check if Chrome is already running
            if not await self._is_chrome_running():
                logger.info("Chrome not running, launching...")
                if not await self._launch_chrome():
                    self.status = CDPStatus.ERROR
                    return False

            self.status = CDPStatus.CONNECTING
            logger.info(f"Connecting to Chrome via CDP on port {self.cdp_port}...")

            # Start Playwright
            self.playwright = await async_playwright().start()

            # Connect via CDP
            self.browser = await self.playwright.chromium.connect_over_cdp(
                f"http://localhost:{self.cdp_port}"
            )

            # Get existing context and page
            if self.browser.contexts:
                self.context = self.browser.contexts[0]
                if self.context.pages:
                    # Use existing page (prefer one with rugs.fun)
                    for p in self.context.pages:
                        if "rugs.fun" in p.url:
                            self.page = p
                            break
                    if not self.page:
                        self.page = self.context.pages[0]
                else:
                    self.page = await self.context.new_page()
            else:
                # Create new context if none exists
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()

            self.status = CDPStatus.CONNECTED
            logger.info(f"CDP connection established. Current URL: {self.page.url}")
            return True

        except Exception as e:
            logger.error(f"CDP connection failed: {e}")
            self.status = CDPStatus.ERROR
            return False

    async def navigate_to_game(self) -> bool:
        """
        Navigate to rugs.fun if not already there.

        Returns:
            True if navigation successful
        """
        if not self.page:
            logger.error("No page available - connect first")
            return False

        try:
            self.status = CDPStatus.NAVIGATING

            # Check if already on rugs.fun
            if "rugs.fun" in self.page.url:
                logger.info("Already on rugs.fun")
                self.status = CDPStatus.READY
                return True

            logger.info("Navigating to rugs.fun...")
            await self.page.goto(self.TARGET_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)  # Wait for page to settle

            self.status = CDPStatus.READY
            logger.info("Navigation complete")
            return True

        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            self.status = CDPStatus.ERROR
            return False

    async def disconnect(self) -> None:
        """
        Disconnect from Chrome (does NOT close Chrome).

        Chrome continues running so wallet/profile persist.
        """
        try:
            # Just disconnect Playwright, don't close browser
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            self.browser = None
            self.context = None
            self.page = None
            self.status = CDPStatus.DISCONNECTED

            logger.info("CDP connection closed (Chrome still running)")

        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            self.status = CDPStatus.ERROR

    async def close_chrome(self) -> None:
        """
        Fully close Chrome (when you want to end the session).
        """
        await self.disconnect()

        if self._chrome_process:
            try:
                self._chrome_process.terminate()
                self._chrome_process.wait(timeout=5)
            except Exception:
                self._chrome_process.kill()
            self._chrome_process = None
            logger.info("Chrome process terminated")

    async def get_screenshot(self) -> Optional[bytes]:
        """
        Capture screenshot of current page.

        Returns:
            Screenshot as PNG bytes, or None if error
        """
        if not self.page:
            return None

        try:
            return await self.page.screenshot(type="png")
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None

    def is_connected(self) -> bool:
        """Check if connected to Chrome"""
        return self.status in [CDPStatus.CONNECTED, CDPStatus.NAVIGATING, CDPStatus.READY]

    def is_ready(self) -> bool:
        """Check if ready for automation"""
        return self.status == CDPStatus.READY

    # ========================================================================
    # PHASE 9.2: BULLETPROOF WALLET CONNECTION
    # ========================================================================

    async def check_wallet_injected(self) -> dict:
        """
        Check if wallet extensions have injected their objects into the page.

        Returns:
            dict with wallet availability status
        """
        if not self.page:
            return {'phantom': False, 'solflare': False, 'solana': False, 'error': 'No page'}

        try:
            result = await self.page.evaluate("""() => {
                return {
                    phantom: typeof window.phantom !== 'undefined',
                    solflare: typeof window.solflare !== 'undefined',
                    solana: typeof window.solana !== 'undefined',
                    phantomSolana: typeof window.phantom?.solana !== 'undefined',
                };
            }""")
            return result
        except Exception as e:
            logger.error(f"Failed to check wallet injection: {e}")
            return {'phantom': False, 'solflare': False, 'solana': False, 'error': str(e)}

    async def ensure_wallet_ready(self, max_retries: int = 3) -> bool:
        """
        BULLETPROOF method to ensure wallet extensions are properly injected.

        This is the CRITICAL method that makes connections reliable.

        The problem: Extensions don't inject into pages loaded BEFORE the
        extension service worker is ready. Solution: RELOAD the page.

        Sequence:
        1. Navigate to rugs.fun (if not there)
        2. Wait for initial page load
        3. Check if wallets are injected
        4. If not, RELOAD and wait
        5. Verify wallets are now available
        6. Retry up to max_retries times

        Args:
            max_retries: Maximum reload attempts (default: 3)

        Returns:
            True if wallet extensions are ready, False otherwise
        """
        if not self.page:
            logger.error("No page available - connect first")
            return False

        for attempt in range(max_retries):
            logger.info(f"Wallet ready check attempt {attempt + 1}/{max_retries}")

            # Step 1: Make sure we're on rugs.fun
            if "rugs.fun" not in self.page.url:
                logger.info("Navigating to rugs.fun...")
                await self.page.goto(self.TARGET_URL, wait_until="domcontentloaded", timeout=30000)

            # Step 2: Wait for page to settle
            await asyncio.sleep(2)

            # Step 3: Check wallet injection
            wallet_status = await self.check_wallet_injected()
            logger.info(f"Wallet status: {wallet_status}")

            if wallet_status.get('phantom') or wallet_status.get('solflare'):
                logger.info("✓ Wallet extensions detected!")
                self.status = CDPStatus.READY
                return True

            # Step 4: Wallets not injected - RELOAD the page
            logger.warning(f"Wallets not injected (attempt {attempt + 1}), reloading page...")
            await self.page.reload(wait_until="domcontentloaded", timeout=30000)

            # Step 5: Wait longer for extensions to inject after reload
            await asyncio.sleep(3)

            # Step 6: Check again
            wallet_status = await self.check_wallet_injected()
            logger.info(f"Wallet status after reload: {wallet_status}")

            if wallet_status.get('phantom') or wallet_status.get('solflare'):
                logger.info("✓ Wallet extensions detected after reload!")
                self.status = CDPStatus.READY
                return True

        logger.error(f"Failed to detect wallet extensions after {max_retries} attempts")
        return False

    async def is_wallet_connected(self) -> bool:
        """
        Check if wallet is actually connected to rugs.fun (not just extension present).

        Returns:
            True if wallet is connected to the site
        """
        if not self.page:
            return False

        try:
            # Check for indicators that wallet is connected:
            # 1. Balance display visible
            # 2. "Connect" button NOT visible or has different text
            result = await self.page.evaluate(r"""() => {
                // Look for balance display (indicates connected)
                const balanceRegex = /[0-9]+\.[0-9]+\s*SOL/i;
                const bodyText = document.body.innerText;
                const hasBalance = balanceRegex.test(bodyText);

                // Look for "Connect" button (indicates NOT connected)
                const buttons = Array.from(document.querySelectorAll('button'));
                const connectButton = buttons.find(b => b.textContent.trim() === 'Connect');
                const hasConnectButton = connectButton && connectButton.offsetParent !== null;

                return {
                    hasBalance: hasBalance,
                    hasConnectButton: hasConnectButton,
                    isConnected: hasBalance || !hasConnectButton
                };
            }""")

            logger.info(f"Wallet connection status: {result}")
            return result.get('isConnected', False)

        except Exception as e:
            logger.error(f"Failed to check wallet connection: {e}")
            return False

    async def full_connect_sequence(self) -> bool:
        """
        Complete bulletproof connection sequence.

        This is the ONE method you should call for reliable connections.

        Sequence:
        1. Connect to Chrome via CDP
        2. Navigate to rugs.fun
        3. Ensure wallet extensions are injected (with reload if needed)
        4. Return ready status

        Returns:
            True if fully connected and ready for automation
        """
        # Step 1: CDP Connection
        if not await self.connect():
            logger.error("Failed to connect via CDP")
            return False

        # Step 2: Navigate to game
        if not await self.navigate_to_game():
            logger.error("Failed to navigate to rugs.fun")
            return False

        # Step 3: Ensure wallet extensions are ready
        if not await self.ensure_wallet_ready():
            logger.error("Wallet extensions not available")
            return False

        logger.info("✓ Full connection sequence complete - ready for automation!")
        return True

    # ========================================================================
    # PRODUCTION FIX: ASYNC CONTEXT MANAGER SUPPORT
    # ========================================================================

    async def __aenter__(self):
        """
        Async context manager entry.

        Ensures proper resource acquisition with guaranteed cleanup.

        Usage:
            async with CDPBrowserManager() as manager:
                await manager.page.click('button')
                # ... automation code ...
            # Automatically disconnects when exiting context

        Returns:
            self: The connected CDPBrowserManager instance

        Raises:
            RuntimeError: If connection fails
        """
        success = await self.connect()
        if not success:
            raise RuntimeError(f"Failed to connect to CDP on port {self.cdp_port}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit.

        Ensures browser connection is properly cleaned up even if exceptions occur.

        Args:
            exc_type: Exception type (if any)
            exc_val: Exception value (if any)
            exc_tb: Exception traceback (if any)

        Returns:
            False: Don't suppress exceptions (let them propagate)
        """
        try:
            await self.disconnect()
        except Exception as e:
            logger.error(f"Error during CDP cleanup: {e}")
            # Don't re-raise - we're already in exception handling context
        return False  # Don't suppress exceptions


# Quick test function
async def _test_cdp_manager():
    """Test CDP connection"""
    manager = CDPBrowserManager()

    print("Connecting to Chrome via CDP...")
    if await manager.connect():
        print(f"Connected! Status: {manager.status}")
        print(f"Current URL: {manager.page.url if manager.page else 'N/A'}")

        await manager.navigate_to_game()
        print(f"After navigation: {manager.page.url if manager.page else 'N/A'}")

        input("Press Enter to disconnect...")
        await manager.disconnect()
        print("Disconnected (Chrome still running)")
    else:
        print("Connection failed!")


if __name__ == "__main__":
    asyncio.run(_test_cdp_manager())
