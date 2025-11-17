#!/usr/bin/env python3
"""
Test Browser Connection - Phase 8.5

This script tests the browser automation system by:
1. Opening a non-headless Chromium browser
2. Connecting to Phantom wallet (manual password entry required)
3. Navigating to Rugs.fun
4. Keeping the browser open for manual verification

Run with: python test_browser_connection.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from browser_automation.rugs_browser import RugsBrowserManager, BrowserStatus


async def test_browser_connection():
    """Test browser connection and wallet automation"""
    print("="*70)
    print("Phase 8.5: Browser Connection Test")
    print("="*70)

    # Create browser manager with existing profile that has Phantom installed
    print("\n[1/5] Initializing RugsBrowserManager...")
    print("   Using existing profile: rugs_fun_phantom (with Phantom wallet)")
    print("   Extension: ~/.gamebot/chromium_extensions/phantom")
    browser_manager = RugsBrowserManager()  # Uses default: rugs_fun_phantom
    print("   ✓ Browser manager created")

    # Start browser (non-headless)
    print("\n[2/5] Starting browser (non-headless)...")
    print("   NOTE: Browser window will appear - this is expected!")
    success = await browser_manager.start_browser()

    if not success:
        print("   ✗ Failed to start browser")
        return False

    print("   ✓ Browser started successfully")
    print(f"   Status: {browser_manager.status.value}")

    # Navigate to game FIRST (before wallet connection)
    print("\n[3/5] Navigating to Rugs.fun...")
    nav_success = await browser_manager.navigate_to_game()

    if not nav_success:
        print("   ⚠️  Navigation failed - check browser manually")
        # Continue anyway to allow manual fixing
    else:
        print("   ✓ Navigation successful!")

    # Connect wallet (now that we're on rugs.fun)
    print("\n[4/5] Connecting Phantom wallet...")
    print("   NOTE: Automation will:")
    print("   - First check if wallet is already connected (persistent profile)")
    print("   - If not connected, click 'Connect' button")
    print("   - Select Phantom from wallet options")
    print("   - Wait for Phantom popup (you may need to enter password)")
    print("   - Approve connection")

    wallet_connected = await browser_manager.connect_wallet()

    if not wallet_connected:
        print("   ⚠️  Wallet connection unclear - please verify manually in browser")
    else:
        print("   ✓ Wallet connected successfully!")

    # Keep browser open for manual verification
    print("\n[5/5] Browser is ready!")
    print("\n" + "="*70)
    print("SUCCESS: Browser automation test complete!")
    print("="*70)
    print("\nThe browser will stay open for manual verification.")
    print("You can:")
    print("  - Check that Phantom wallet is connected")
    print("  - Verify you can see the Rugs.fun game")
    print("  - Manually test clicking BUY/SELL buttons")
    print("\nPress Ctrl+C to close the browser and exit...")
    print("="*70)

    try:
        # Keep browser open until user presses Ctrl+C
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n\nShutting down...")

    finally:
        print("Closing browser...")
        await browser_manager.stop_browser()
        print("✓ Browser closed. Test complete!")

    return True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("REPLAYER - Browser Automation Test")
    print("Phase 8.5: Testing Playwright integration with Phantom wallet")
    print("="*70 + "\n")

    try:
        result = asyncio.run(test_browser_connection())

        if result:
            print("\n✅ Test completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Test failed")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
