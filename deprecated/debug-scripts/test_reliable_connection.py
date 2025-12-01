#!/usr/bin/env python3
"""
Reliable Connection Test - Phase 9.2

Tests the bulletproof connection sequence multiple times to verify reliability.

Usage:
    cd /home/nomad/Desktop/REPLAYER
    /home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3 scripts/test_reliable_connection.py

What this tests:
1. Full connection sequence (CDP + navigate + wallet check)
2. Wallet extension injection verification
3. Page reload for extension injection (if needed)
4. Disconnect and reconnect reliability
"""

import asyncio
import sys
import time
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from browser_automation.cdp_browser_manager import CDPBrowserManager, CDPStatus

# Terminal colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'


async def test_single_connection(test_num: int, manager: CDPBrowserManager) -> dict:
    """
    Test a single connection sequence.

    Returns:
        dict with test results
    """
    result = {
        'test_num': test_num,
        'cdp_connected': False,
        'navigation_ok': False,
        'wallet_injected': False,
        'wallet_details': {},
        'duration_ms': 0,
        'error': None,
    }

    start_time = time.time()

    try:
        # Step 1: CDP Connection
        print(f"  [1] Connecting via CDP...", end=" ", flush=True)
        if await manager.connect():
            print(f"{Colors.GREEN}OK{Colors.ENDC}")
            result['cdp_connected'] = True
        else:
            print(f"{Colors.RED}FAILED{Colors.ENDC}")
            result['error'] = "CDP connection failed"
            return result

        # Step 2: Navigate to game
        print(f"  [2] Navigating to rugs.fun...", end=" ", flush=True)
        if await manager.navigate_to_game():
            print(f"{Colors.GREEN}OK{Colors.ENDC}")
            result['navigation_ok'] = True
        else:
            print(f"{Colors.YELLOW}UNCLEAR{Colors.ENDC}")
            result['navigation_ok'] = True  # May still work

        # Step 3: Ensure wallet ready (with auto-reload)
        print(f"  [3] Checking wallet injection (will reload if needed)...", end=" ", flush=True)
        if await manager.ensure_wallet_ready(max_retries=3):
            print(f"{Colors.GREEN}OK{Colors.ENDC}")
            result['wallet_injected'] = True
        else:
            print(f"{Colors.RED}FAILED{Colors.ENDC}")
            result['error'] = "Wallet injection failed after 3 retries"

        # Step 4: Get wallet details
        wallet_status = await manager.check_wallet_injected()
        result['wallet_details'] = wallet_status

        # Step 5: Check if wallet is connected to site
        print(f"  [4] Checking wallet site connection...", end=" ", flush=True)
        is_connected = await manager.is_wallet_connected()
        if is_connected:
            print(f"{Colors.GREEN}CONNECTED{Colors.ENDC}")
        else:
            print(f"{Colors.YELLOW}NOT CONNECTED (click Connect button){Colors.ENDC}")

    except Exception as e:
        print(f"{Colors.RED}ERROR: {e}{Colors.ENDC}")
        result['error'] = str(e)

    result['duration_ms'] = int((time.time() - start_time) * 1000)
    return result


async def run_reliability_test(num_tests: int = 5):
    """
    Run multiple connection tests to verify reliability.
    """
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}  BULLETPROOF CONNECTION RELIABILITY TEST{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.ENDC}")
    print()
    print(f"Running {num_tests} connection tests...")
    print()

    results = []
    manager = CDPBrowserManager()

    for i in range(num_tests):
        print(f"{Colors.BOLD}Test {i + 1}/{num_tests}{Colors.ENDC}")

        # Run test
        result = await test_single_connection(i + 1, manager)
        results.append(result)

        # Print result
        if result['wallet_injected']:
            print(f"  {Colors.GREEN}✓ PASSED{Colors.ENDC} ({result['duration_ms']}ms)")
        else:
            print(f"  {Colors.RED}✗ FAILED{Colors.ENDC}: {result.get('error', 'Unknown')}")

        # Disconnect between tests
        print(f"  [5] Disconnecting...", end=" ", flush=True)
        await manager.disconnect()
        print(f"{Colors.GREEN}OK{Colors.ENDC}")
        print()

        # Small delay between tests
        if i < num_tests - 1:
            await asyncio.sleep(1)

    # Summary
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}  TEST SUMMARY{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.ENDC}")
    print()

    passed = sum(1 for r in results if r['wallet_injected'])
    failed = num_tests - passed

    print(f"  Total tests:  {num_tests}")
    print(f"  {Colors.GREEN}Passed:{Colors.ENDC}       {passed}")
    print(f"  {Colors.RED}Failed:{Colors.ENDC}       {failed}")
    print(f"  Success rate: {passed/num_tests*100:.0f}%")
    print()

    # Timing stats
    durations = [r['duration_ms'] for r in results if r['wallet_injected']]
    if durations:
        print(f"  Avg time:     {sum(durations)/len(durations):.0f}ms")
        print(f"  Min time:     {min(durations)}ms")
        print(f"  Max time:     {max(durations)}ms")
    print()

    # Final verdict
    if passed == num_tests:
        print(f"  {Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED - CONNECTION IS RELIABLE!{Colors.ENDC}")
    elif passed > 0:
        print(f"  {Colors.YELLOW}{Colors.BOLD}⚠ PARTIAL SUCCESS - {failed} failures{Colors.ENDC}")
    else:
        print(f"  {Colors.RED}{Colors.BOLD}✗ ALL TESTS FAILED - CONNECTION NOT WORKING{Colors.ENDC}")
    print()

    return passed == num_tests


async def test_full_connect_sequence():
    """
    Test the all-in-one full_connect_sequence method.
    """
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}  TESTING full_connect_sequence() METHOD{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.ENDC}")
    print()

    manager = CDPBrowserManager()

    print("Calling full_connect_sequence()...")
    start = time.time()
    success = await manager.full_connect_sequence()
    duration = int((time.time() - start) * 1000)

    if success:
        print(f"{Colors.GREEN}✓ SUCCESS{Colors.ENDC} ({duration}ms)")

        # Take screenshot as proof
        screenshot = await manager.get_screenshot()
        if screenshot:
            with open('/tmp/reliable_connection_proof.png', 'wb') as f:
                f.write(screenshot)
            print(f"Screenshot saved: /tmp/reliable_connection_proof.png")

        # Show wallet status
        wallet = await manager.check_wallet_injected()
        print(f"Wallet status: {wallet}")

    else:
        print(f"{Colors.RED}✗ FAILED{Colors.ENDC}")

    await manager.disconnect()
    return success


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test reliable browser connection")
    parser.add_argument("--tests", type=int, default=5, help="Number of tests to run")
    parser.add_argument("--quick", action="store_true", help="Run just the full_connect_sequence test")
    args = parser.parse_args()

    if args.quick:
        success = asyncio.run(test_full_connect_sequence())
    else:
        success = asyncio.run(run_reliability_test(args.tests))

    sys.exit(0 if success else 1)
