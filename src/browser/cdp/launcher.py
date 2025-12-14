#!/usr/bin/env python3
"""
Rugs Browser Manager

Manages browser lifecycle for Rugs.fun observation bot in TUI.
Combines persistent profile, wallet automation, and async integration.

Created for Checkpoint 3.5E.3
"""


from pathlib import Path
from enum import Enum
from typing import Optional
import asyncio


from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from browser.profiles import (
    PersistentProfileConfig,
    build_launch_options
)
from browser.automation import connect_phantom_wallet, wait_for_game_ready


class BrowserStatus(Enum):
    """Browser manager status states"""
    STOPPED = "stopped"
    LAUNCHING = "launching"
    RUNNING = "running"
    CONNECTING_WALLET = "connecting_wallet"
    WALLET_CONNECTED = "wallet_connected"
    GAME_READY = "game_ready"
    ERROR = "error"


class RugsBrowserManager:
    """
    Manages browser lifecycle for Rugs.fun observation.

    Features:
    - Persistent Chromium profile (wallet stays connected)
    - Auto-connects Phantom wallet on startup
    - Navigates to rugs.fun automatically
    - Async methods for TUI integration
    - Clean shutdown and error handling

    Usage:
        manager = RugsBrowserManager()
        await manager.start_browser()
        await manager.connect_wallet()
        await manager.navigate_to_game()
        # ... observe gameplay ...
        await manager.stop_browser()
    """

    def __init__(self, profile_name: str = "rugs_fun_phantom"):
        """
        Initialize browser manager.

        Args:
            profile_name: Name of persistent browser profile
        """
        self.profile_name = profile_name
        # Use the pre-configured .gamebot profile (shared with CV-BOILER-PLATE-FORK)
        self.profile_path = Path.home() / ".gamebot" / "chromium_profiles" / profile_name
        self.extension_path = Path.home() / ".gamebot" / "chromium_extensions" / "phantom"

        # Playwright components
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Status tracking
        self.status = BrowserStatus.STOPPED

        # Create persistent profile config (with Phantom extension if available)
        # Only load extension if it has a valid manifest.json file
        extension_dirs = []
        if self.extension_path.exists():
            manifest_path = self.extension_path / "manifest.json"
            if manifest_path.exists():
                extension_dirs.append(self.extension_path)
            else:
                print(f"   ⚠️  Phantom extension directory exists but manifest.json missing")
                print(f"      Extension will not be loaded - manual wallet connection required")

        self.profile_config = PersistentProfileConfig(
            user_data_dir=self.profile_path,
            extension_dirs=extension_dirs,
            headless=False,  # Visible browser for TUI
            block_ads=False,
            extra_args=[
                "--start-maximized",  # Force window to be visible and maximized
                "--new-window",       # Open in new window (not just new tab)
            ]
        )

    async def start_browser(self) -> bool:
        """
        Launch Chromium browser with persistent profile.

        Returns:
            True if browser launched successfully, False otherwise
        """
        try:
            self.status = BrowserStatus.LAUNCHING

            # Start Playwright
            self.playwright = await async_playwright().start()

            # Get launch options from profile config
            launch_options = build_launch_options(self.profile_config)

            # Remove user_data_dir from launch_options (we pass it separately)
            if 'user_data_dir' in launch_options:
                del launch_options['user_data_dir']

            # Launch browser with persistent profile
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_config.user_data_dir),
                **launch_options
            )

            # Create new page
            self.page = await self.context.new_page()

            self.status = BrowserStatus.RUNNING
            return True

        except Exception as e:
            self.status = BrowserStatus.ERROR
            print(f"Error starting browser: {e}")
            return False

    async def stop_browser(self) -> None:
        """
        Cleanly shut down browser.

        Closes all resources and resets status.
        """
        try:
            # Close page
            if self.page:
                await self.page.close()
                self.page = None

            # Close context
            if self.context:
                await self.context.close()
                self.context = None

            # Stop Playwright
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            # Browser is None when using persistent context
            self.browser = None

            self.status = BrowserStatus.STOPPED

        except Exception as e:
            print(f"Error stopping browser: {e}")
            self.status = BrowserStatus.ERROR

    async def navigate_to_game(self) -> bool:
        """
        Navigate to rugs.fun (must be called before connect_wallet).

        Returns:
            True if navigation successful, False otherwise
        """
        if self.status != BrowserStatus.RUNNING:
            print("Browser not running - cannot navigate")
            return False

        try:
            print("🌐 Navigating to https://rugs.fun...")

            # Navigate to rugs.fun
            await self.page.goto("https://rugs.fun", wait_until="domcontentloaded", timeout=30000)
            print("   ✓ Page loaded")

            # Wait for page to settle
            await asyncio.sleep(2)

            return True

        except Exception as e:
            print(f"   ✗ Error navigating to game: {e}")
            self.status = BrowserStatus.ERROR
            return False

    async def connect_wallet(self) -> bool:
        """
        Auto-connect Phantom wallet (must navigate to rugs.fun first).

        Uses existing automation from automation.py.

        Returns:
            True if wallet connected, False otherwise
        """
        if self.status != BrowserStatus.RUNNING:
            print("Browser not running - cannot connect wallet")
            return False

        try:
            self.status = BrowserStatus.CONNECTING_WALLET

            # Use existing wallet automation
            success = await connect_phantom_wallet(self.page)

            if success:
                self.status = BrowserStatus.WALLET_CONNECTED

                # Wait for game to be ready after wallet connection
                print("🎮 Waiting for game to be ready...")
                game_ready = await wait_for_game_ready(self.page, timeout=10)

                if game_ready:
                    self.status = BrowserStatus.GAME_READY
                    print("   ✓ Game ready!")

                return True
            else:
                # Even if wallet connection unclear, we might still be able to use the game
                print("   ⚠️  Proceeding anyway - check browser manually")
                return False

        except Exception as e:
            print(f"Error connecting wallet: {e}")
            self.status = BrowserStatus.ERROR
            return False

    async def get_screenshot(self) -> Optional[bytes]:
        """
        Capture screenshot of current page.

        Used by SessionRecorder for YOLO processing.

        Returns:
            Screenshot as PNG bytes, or None if error
        """
        if not self.page:
            return None

        try:
            screenshot_bytes = await self.page.screenshot(type="png")
            return screenshot_bytes

        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            return None

    def is_running(self) -> bool:
        """Check if browser is running"""
        return self.status in [
            BrowserStatus.RUNNING,
            BrowserStatus.CONNECTING_WALLET,
            BrowserStatus.WALLET_CONNECTED,
            BrowserStatus.GAME_READY
        ]

    def is_ready_for_observation(self) -> bool:
        """Check if browser is ready for observation (game loaded)"""
        return self.status == BrowserStatus.GAME_READY
