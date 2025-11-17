#!/usr/bin/env python3
"""
Quick test to verify browser launches with fixed PLAYWRIGHT_BROWSERS_PATH
"""
import sys
from pathlib import Path
import asyncio

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_browser_launch():
    """Test browser launch with fixed path"""
    print("=" * 60)
    print("BROWSER LAUNCH TEST")
    print("=" * 60)

    print("\n[1/5] Importing RugsBrowserManager...")
    try:
        from browser_automation.rugs_browser import RugsBrowserManager
        print("   ✅ Import successful")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False

    print("\n[2/5] Creating browser manager...")
    try:
        manager = RugsBrowserManager(profile_name="rugs_fun_phantom")
        print(f"   ✅ Manager created")
        print(f"      Profile: {manager.profile_path}")
        print(f"      Extension: {manager.extension_path}")
    except Exception as e:
        print(f"   ❌ Manager creation failed: {e}")
        return False

    print("\n[3/5] Starting browser...")
    try:
        success = await manager.start_browser()
        if success:
            print("   ✅ Browser started successfully!")
        else:
            print("   ❌ Browser start returned False")
            return False
    except Exception as e:
        print(f"   ❌ Browser start failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n[4/5] Checking browser status...")
    if manager.is_running():
        print(f"   ✅ Browser is running (status: {manager.status})")
    else:
        print(f"   ❌ Browser not running (status: {manager.status})")
        return False

    print("\n[5/5] Stopping browser...")
    try:
        await manager.stop_browser()
        print("   ✅ Browser stopped cleanly")
    except Exception as e:
        print(f"   ⚠️  Browser stop error (non-critical): {e}")

    print("\n" + "=" * 60)
    print("✅ TEST PASSED - Browser connection working!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    result = asyncio.run(test_browser_launch())
    sys.exit(0 if result else 1)
