#!/usr/bin/env python3
"""
Diagnostic script to identify why button forwarding isn't working

Run this after connecting browser and clicking BUY button.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("="*80)
print("🔍 REPLAYER Button Forwarding Diagnostic")
print("="*80)
print()

# Check 1: Can we import browser_executor?
print("✓ CHECK 1: Import BrowserExecutor")
try:
    from bot.browser_executor import BrowserExecutor
    print("   ✅ SUCCESS: BrowserExecutor imported")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    print("   FIX: Check browser_automation/ directory exists")
    sys.exit(1)

# Check 2: Can we import async_loop_manager?
print()
print("✓ CHECK 2: Import AsyncLoopManager")
try:
    from services.async_loop_manager import AsyncLoopManager
    print("   ✅ SUCCESS: AsyncLoopManager imported")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    sys.exit(1)

# Check 3: Can we create BrowserExecutor?
print()
print("✓ CHECK 3: Create BrowserExecutor")
try:
    executor = BrowserExecutor(profile_name="rugs_fun_phantom")
    print("   ✅ SUCCESS: BrowserExecutor created")
    print(f"   Profile: {executor.profile_name}")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Check 4: Can we create AsyncLoopManager?
print()
print("✓ CHECK 4: Create AsyncLoopManager")
try:
    async_mgr = AsyncLoopManager()
    async_mgr.start()
    print("   ✅ SUCCESS: AsyncLoopManager started")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Check 5: Test forwarding simulation
print()
print("✓ CHECK 5: Simulate Button Forwarding (DRY RUN)")
print("   Simulating: User clicks BUY in REPLAYER")

# Simulate the conditions that should trigger forwarding
browser_connected = True  # Assume connected
browser_executor = executor
async_manager = async_mgr

print(f"   browser_connected: {browser_connected}")
print(f"   browser_executor exists: {browser_executor is not None}")
print(f"   async_manager exists: {async_manager is not None}")

if browser_connected and browser_executor and async_manager:
    print("   ✅ ALL CONDITIONS MET - Forwarding would trigger!")
else:
    print("   ❌ CONDITIONS NOT MET - Forwarding would NOT trigger!")
    print(f"      Missing: ", end="")
    missing = []
    if not browser_connected:
        missing.append("browser_connected")
    if not browser_executor:
        missing.append("browser_executor")
    if not async_manager:
        missing.append("async_manager")
    print(", ".join(missing))

# Check 6: Test if browser_executor methods exist
print()
print("✓ CHECK 6: Verify browser_executor methods")
methods = ['click_buy', 'click_sell', 'click_sidebet', 'is_ready']
for method_name in methods:
    if hasattr(executor, method_name):
        print(f"   ✅ {method_name}() exists")
    else:
        print(f"   ❌ {method_name}() MISSING!")

# Check 7: Check selectors
print()
print("✓ CHECK 7: Verify selectors are defined")
selector_attrs = [
    'BUY_BUTTON_SELECTORS',
    'SELL_BUTTON_SELECTORS',
    'INCREMENT_001_SELECTORS',
    'CLEAR_BUTTON_SELECTORS'
]
for attr in selector_attrs:
    if hasattr(executor, attr):
        selectors = getattr(executor, attr)
        print(f"   ✅ {attr}: {len(selectors)} selectors")
        if selectors:
            print(f"      PRIMARY: {selectors[0]}")
    else:
        print(f"   ❌ {attr} MISSING!")

# Check 8: Check if browser_automation exists
print()
print("✓ CHECK 8: Verify browser_automation module")
try:
    from browser_automation.rugs_browser import RugsBrowserManager
    print("   ✅ RugsBrowserManager imported")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    print("   FIX: Check browser_automation/rugs_browser.py exists")

# Check 9: Test async execution (without browser)
print()
print("✓ CHECK 9: Test async execution path")
import asyncio
from decimal import Decimal

async def test_click():
    print("   → Testing click_buy() WITHOUT browser connected...")
    result = await executor.click_buy(Decimal('0.003'))
    return result

try:
    future = async_mgr.run_coroutine(test_click())
    result = future.result(timeout=5.0)
    if result:
        print("   ⚠️ UNEXPECTED: click_buy() returned True (browser not connected!)")
    else:
        print("   ✅ EXPECTED: click_buy() returned False (browser not connected)")
except Exception as e:
    print(f"   ✅ EXPECTED: Got exception (browser not connected): {type(e).__name__}")

print()
print("="*80)
print("📊 DIAGNOSTIC SUMMARY")
print("="*80)
print()
print("If all checks passed, the issue is likely:")
print("1. browser_connected flag not being set to True after connection")
print("2. Browser connection dialog not calling on_connected() callback")
print("3. async_manager not being passed to MainWindow")
print()
print("Next steps:")
print("1. Connect browser via Browser → Connect menu")
print("2. Add this debug line to execute_buy() in main_window.py:")
print("   logger.error(f'DEBUG: browser_connected={self.browser_connected}, executor={self.browser_executor is not None}, async={self.async_manager is not None}')")
print("3. Click BUY button and check logs")
print()
print("If you see 'browser_connected=False', the connection callback isn't firing.")
print("If you see 'executor=False', BrowserExecutor import failed.")
print("If you see 'async=False', async_manager wasn't passed to MainWindow.")
print()
print("="*80)

# Cleanup
async_mgr.stop()
