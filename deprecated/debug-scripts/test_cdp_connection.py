#!/usr/bin/env python3
"""
Test CDP Connection - Phase 9.1

Quick test to verify CDP connection workflow works correctly.

Usage:
    cd /home/nomad/Desktop/REPLAYER
    python3 scripts/test_cdp_connection.py

What this tests:
1. Chrome binary detection
2. CDP port availability check
3. Chrome launch with debugging port
4. CDP connection via Playwright
5. Page navigation to rugs.fun
"""

import asyncio
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from browser_automation.cdp_browser_manager import CDPBrowserManager, CDPStatus


async def test_cdp_connection():
    """Test the full CDP connection workflow"""
    print("=" * 60)
    print("CDP Connection Test - Phase 9.1")
    print("=" * 60)
    print()

    manager = CDPBrowserManager()

    # Test 1: Chrome binary detection
    print("[1] Chrome binary detection...")
    chrome_path = manager._find_chrome_binary()
    if chrome_path:
        print(f"    ✓ Found Chrome: {chrome_path}")
    else:
        print("    ✗ Chrome not found!")
        print("    Install with: sudo apt install google-chrome-stable")
        return False

    # Test 2: Check if Chrome already running
    print("\n[2] Checking for existing Chrome on port 9222...")
    already_running = await manager._is_chrome_running()
    if already_running:
        print("    ✓ Chrome already running on debug port")
    else:
        print("    → Chrome not running, will launch")

    # Test 3: Connect
    print("\n[3] Connecting via CDP...")
    try:
        success = await manager.connect()
        if success:
            print(f"    ✓ CDP connection established!")
            print(f"    Status: {manager.status.value}")
        else:
            print("    ✗ CDP connection failed")
            return False
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False

    # Test 4: Check page
    print("\n[4] Checking page...")
    if manager.page:
        print(f"    ✓ Page available")
        print(f"    URL: {manager.page.url}")
    else:
        print("    ✗ No page available")
        await manager.disconnect()
        return False

    # Test 5: Navigate to rugs.fun
    print("\n[5] Navigating to rugs.fun...")
    try:
        nav_success = await manager.navigate_to_game()
        if nav_success:
            print(f"    ✓ Navigation successful")
            print(f"    URL: {manager.page.url}")
        else:
            print("    ⚠ Navigation unclear")
    except Exception as e:
        print(f"    ⚠ Navigation issue: {e}")

    # Test 6: Screenshot
    print("\n[6] Taking screenshot...")
    try:
        screenshot = await manager.get_screenshot()
        if screenshot:
            print(f"    ✓ Screenshot captured ({len(screenshot)} bytes)")
        else:
            print("    ⚠ Screenshot failed")
    except Exception as e:
        print(f"    ⚠ Screenshot error: {e}")

    print("\n" + "=" * 60)
    print("CDP Connection Test Complete!")
    print("=" * 60)
    print()
    print("Press Enter to disconnect (Chrome will keep running)...")
    input()

    await manager.disconnect()
    print("Disconnected. Chrome should still be running.")
    print()
    print("To verify wallet persistence:")
    print("1. Check Chrome window - you should see rugs.fun")
    print("2. Phantom wallet should still be connected")
    print("3. Run this script again - should connect faster")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_cdp_connection())
    sys.exit(0 if success else 1)
