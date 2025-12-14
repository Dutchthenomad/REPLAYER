"""
Automation helpers for Rugs.fun gameplay.

Functions for automating wallet connection, game interaction, and other
browser automation tasks specific to Rugs.fun.
"""

import asyncio
from typing import Optional

# AUDIT FIX: Import TimeoutError for specific exception handling
try:
    from playwright.async_api import TimeoutError as PlaywrightTimeout
except ImportError:
    PlaywrightTimeout = Exception  # Fallback if playwright not installed


async def connect_phantom_wallet(page, timeout: int = 30) -> bool:
    """
    Automatically connect Phantom wallet to Rugs.fun.

    This function:
    1. Checks if wallet is already connected (persistent profile)
    2. If not connected, finds and clicks the "Connect" button
    3. Waits for Phantom popup
    4. Approves connection in Phantom
    5. Verifies connection success

    Args:
        page: Playwright page object
        timeout: Maximum time to wait (seconds)

    Returns:
        True if connection succeeded, False otherwise
    """
    try:
        print("🔌 Checking wallet connection status...")

        # Wait for page to be ready
        await asyncio.sleep(2)

        # CRITICAL FIX: Check if wallet is ALREADY connected (persistent profile)
        already_connected = await page.evaluate("""() => {
            const bodyText = document.body.innerText;
            // Look for indicators of successful connection
            const hasAddress = bodyText.match(/[A-Za-z0-9]{32,}/);  // Solana address pattern
            const hasDisconnect = bodyText.toLowerCase().includes('disconnect');
            const hasBalance = bodyText.includes('SOL') || bodyText.includes('$SOL');
            const hasConnectButton = bodyText.toLowerCase().includes('connect wallet');

            // If we see disconnect/address/balance AND no connect button, wallet is connected
            return (hasAddress || hasDisconnect || hasBalance) && !hasConnectButton;
        }""")

        if already_connected:
            print("   ✅ Wallet already connected! (Persistent profile working)")
            return True

        print("   Wallet not connected yet - attempting to connect...")

        # Step 1: Find and click Connect button
        # Try multiple selectors in case UI changes
        connect_selectors = [
            'button:has-text("Connect")',
            'button:has-text("connect")',
            '[class*="connect"]',
            'button[class*="Connect"]',
        ]

        connect_button = None
        for selector in connect_selectors:
            try:
                connect_button = await page.wait_for_selector(
                    selector,
                    timeout=5000,
                    state='visible'
                )
                if connect_button:
                    print(f"   ✓ Found Connect button with selector: {selector}")
                    break
            except PlaywrightTimeout:
                # AUDIT FIX: Catch specific playwright timeout exception
                continue

        if not connect_button:
            print("   ✗ Could not find Connect button")
            return False

        # Click the Connect button
        await connect_button.click()
        print("   ✓ Clicked Connect button")
        await asyncio.sleep(1)

        # Step 2: Select Phantom from wallet options
        # Look for Phantom wallet option in modal
        phantom_selectors = [
            'button:has-text("Phantom")',
            'div:has-text("Phantom")',
            '[class*="phantom"]',
            'img[alt*="Phantom"]',
        ]

        phantom_option = None
        for selector in phantom_selectors:
            try:
                phantom_option = await page.wait_for_selector(
                    selector,
                    timeout=3000,
                    state='visible'
                )
                if phantom_option:
                    print(f"   ✓ Found Phantom option with selector: {selector}")
                    break
            except PlaywrightTimeout:
                # AUDIT FIX: Catch specific playwright timeout exception
                continue

        if phantom_option:
            await phantom_option.click()
            print("   ✓ Selected Phantom wallet")
            await asyncio.sleep(2)

        # Step 3: Handle Phantom popup (new window/popup)
        # Phantom opens a popup window for connection approval
        print("   ⏳ Waiting for Phantom popup...")

        # Wait for popup to appear
        try:
            async with page.context.expect_page(timeout=10000) as popup_info:
                popup = await popup_info.value
                print("   ✓ Phantom popup detected")

                # Wait for popup to load
                await popup.wait_for_load_state('domcontentloaded')
                await asyncio.sleep(1)

                # Look for "Connect" or "Approve" button in Phantom popup
                approval_selectors = [
                    'button:has-text("Connect")',
                    'button:has-text("Approve")',
                    'button:has-text("approve")',
                    'button[class*="primary"]',
                ]

                approved = False
                for selector in approval_selectors:
                    try:
                        approve_button = await popup.wait_for_selector(
                            selector,
                            timeout=3000,
                            state='visible'
                        )
                        if approve_button:
                            await approve_button.click()
                            print(f"   ✓ Clicked approval button in Phantom popup")
                            approved = True
                            break
                    except PlaywrightTimeout:
                        # AUDIT FIX: Catch specific playwright timeout exception
                        continue

                if not approved:
                    print("   ⚠️  Could not find approval button in Phantom popup")
                    print("      (May already be approved or different UI)")

                # Wait for popup to close
                await asyncio.sleep(2)

        except asyncio.TimeoutError:
            print("   ⚠️  Phantom popup did not appear")
            print("      (Wallet may already be connected)")

        # Step 4: Verify connection success
        await asyncio.sleep(2)

        # Check if wallet is connected by looking for wallet address or disconnect button
        connected = await page.evaluate("""() => {
            const bodyText = document.body.innerText;
            // Look for indicators of successful connection
            const hasAddress = bodyText.match(/[A-Za-z0-9]{32,}/);  // Solana address pattern
            const hasDisconnect = bodyText.toLowerCase().includes('disconnect');
            const hasBalance = bodyText.includes('SOL') || bodyText.includes('$SOL');

            return hasAddress || hasDisconnect || hasBalance;
        }""")

        if connected:
            print("   ✅ Wallet connected successfully!")
            return True
        else:
            print("   ⚠️  Wallet connection unclear - please verify manually")
            return False

    except Exception as e:
        print(f"   ✗ Error during wallet connection: {e}")
        return False


async def wait_for_game_ready(page, timeout: int = 10) -> bool:
    """
    Wait for Rugs.fun game to be ready to play.

    Checks for:
    - Page loaded
    - Game canvas/UI visible
    - No loading screens

    Args:
        page: Playwright page object
        timeout: Maximum time to wait (seconds)

    Returns:
        True if game is ready, False otherwise
    """
    try:
        # Wait for game elements to be visible
        # Rugs.fun typically shows a game timer or multiplier display
        await asyncio.sleep(3)

        # Check for game UI elements
        game_ready = await page.evaluate("""() => {
            const bodyText = document.body.innerText;
            // Look for game-specific elements
            const hasTimer = bodyText.match(/\\d+:\\d+/);  // Timer pattern
            const hasMultiplier = bodyText.includes('x') || bodyText.includes('X');
            const hasGameUI = document.querySelector('canvas') !== null;

            return hasTimer || hasMultiplier || hasGameUI;
        }""")

        return game_ready

    except Exception as e:
        print(f"Error checking game ready state: {e}")
        return False
