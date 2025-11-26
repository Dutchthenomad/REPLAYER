#!/usr/bin/env python3
"""
Chrome Profile Setup Script - Phase 9.2

Interactive setup script for first-time Chrome profile configuration.
Creates a dedicated Chrome profile with Phantom wallet for REPLAYER automation.

Usage:
    cd /home/nomad/Desktop/REPLAYER
    python3 scripts/setup_chrome_profile.py

What this does:
1. Launches Chrome with a dedicated profile directory
2. Guides user to install Phantom wallet extension
3. Guides user to connect wallet to rugs.fun
4. Verifies setup is complete
5. Profile persists for all future automation sessions

After setup:
- Wallet stays connected across sessions
- No need to re-authenticate
- REPLAYER can connect instantly via CDP
"""

import asyncio
import subprocess
import sys
import time
import socket
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Terminal colors for pretty output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a header line"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{text}{Colors.ENDC}")


def print_step(step_num: int, text: str):
    """Print a step indicator"""
    print(f"\n{Colors.BOLD}[{step_num}]{Colors.ENDC} {text}")


def print_success(text: str):
    """Print success message"""
    print(f"    {Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message"""
    print(f"    {Colors.YELLOW}⚠ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message"""
    print(f"    {Colors.RED}✗ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message"""
    print(f"    {Colors.BLUE}→ {text}{Colors.ENDC}")


def print_checklist_item(text: str, checked: bool = False):
    """Print a checklist item"""
    marker = f"{Colors.GREEN}✓{Colors.ENDC}" if checked else "[ ]"
    print(f"       {marker} {text}")


# Configuration
CDP_PORT = 9222
PROFILE_DIR = Path.home() / ".gamebot" / "chrome_profiles" / "rugs_bot"
TARGET_URL = "https://rugs.fun"
PHANTOM_STORE_URL = "https://chrome.google.com/webstore/detail/phantom/bfnaelmomeimhlpmgjnjophhpkkoljpa"

# Chrome binary locations (Linux)
CHROME_BINARIES = [
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/snap/bin/chromium",
]


def find_chrome_binary() -> str | None:
    """Find Chrome binary on the system"""
    for binary in CHROME_BINARIES:
        if Path(binary).exists():
            return binary
    return None


def is_port_in_use(port: int) -> bool:
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect(('localhost', port))
            return True
        except (ConnectionRefusedError, OSError):
            return False


def launch_chrome_for_setup() -> subprocess.Popen | None:
    """
    Launch Chrome with the dedicated profile for setup.

    Opens directly to rugs.fun so user can connect wallet.
    """
    chrome_binary = find_chrome_binary()
    if not chrome_binary:
        return None

    # Ensure profile directory exists
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    # Chrome launch arguments
    args = [
        chrome_binary,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--start-maximized",
        "--new-window",
        "--no-first-run",
        "--no-default-browser-check",
        TARGET_URL,  # Open rugs.fun directly
    ]

    try:
        process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return process
    except Exception as e:
        print_error(f"Failed to launch Chrome: {e}")
        return None


async def verify_phantom_installed() -> bool:
    """
    Try to verify if Phantom is installed by checking the page.

    This is a best-effort check - may not always work.
    """
    try:
        from browser_automation.cdp_browser_manager import CDPBrowserManager

        manager = CDPBrowserManager()
        if not await manager.connect():
            return False

        # Try to check for Phantom
        if manager.page:
            # Check if window.phantom exists
            try:
                result = await manager.page.evaluate("typeof window.phantom !== 'undefined'")
                await manager.disconnect()
                return result
            except Exception:
                await manager.disconnect()
                return False

        await manager.disconnect()
        return False

    except Exception:
        return False


async def verify_wallet_connected() -> bool:
    """
    Try to verify if wallet is connected on rugs.fun.

    Checks for balance display or connected wallet indicator.
    """
    try:
        from browser_automation.cdp_browser_manager import CDPBrowserManager

        manager = CDPBrowserManager()
        if not await manager.connect():
            return False

        if manager.page:
            try:
                # Navigate to rugs.fun if not there
                if "rugs.fun" not in manager.page.url:
                    await manager.page.goto(TARGET_URL, wait_until="domcontentloaded")
                    await asyncio.sleep(2)

                # Check for indicators that wallet is connected
                # Look for balance display, connected status, or absence of "Connect" button

                # Method 1: Check for balance element
                balance_check = await manager.page.query_selector('text=/\\d+\\.\\d+\\s*SOL/i')
                if balance_check:
                    await manager.disconnect()
                    return True

                # Method 2: Check for "Connect" button (if visible, NOT connected)
                connect_button = await manager.page.query_selector('button:has-text("Connect")')
                if connect_button:
                    is_visible = await connect_button.is_visible()
                    await manager.disconnect()
                    return not is_visible  # Connected if button NOT visible

                await manager.disconnect()
                return False

            except Exception:
                await manager.disconnect()
                return False

        await manager.disconnect()
        return False

    except Exception:
        return False


def print_setup_instructions():
    """Print the setup checklist for the user"""
    print(f"""
    {Colors.BOLD}Please complete these steps in the Chrome window:{Colors.ENDC}

    {Colors.YELLOW}STEP A: Install Phantom Wallet{Colors.ENDC}
       [ ] Open a new tab
       [ ] Go to: {PHANTOM_STORE_URL}
       [ ] Click "Add to Chrome"
       [ ] Complete Phantom setup (create or import wallet)

    {Colors.YELLOW}STEP B: Connect to Rugs.fun{Colors.ENDC}
       [ ] Go back to the rugs.fun tab
       [ ] Click the "Connect" button
       [ ] Select Phantom wallet
       [ ] Approve the connection in Phantom popup
       [ ] Verify you can see your SOL balance

    {Colors.CYAN}TIP: The profile is saved at:{Colors.ENDC}
       {PROFILE_DIR}

    {Colors.CYAN}TIP: After setup, your wallet stays connected forever!{Colors.ENDC}
    """)


def run_setup():
    """Main setup workflow"""
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}  CHROME PROFILE SETUP FOR REPLAYER - Phase 9.2{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.ENDC}")

    # Step 1: Check for Chrome
    print_step(1, "Checking for Chrome installation...")
    chrome_path = find_chrome_binary()
    if chrome_path:
        print_success(f"Found Chrome: {chrome_path}")
    else:
        print_error("Chrome not found!")
        print_info("Install with: sudo apt install google-chrome-stable")
        print_info("Or: sudo snap install chromium")
        return False

    # Step 2: Check if Chrome already running on debug port
    print_step(2, "Checking for existing Chrome on debug port...")
    if is_port_in_use(CDP_PORT):
        print_warning(f"Chrome already running on port {CDP_PORT}")
        print_info("Close existing Chrome instance or use it for setup")
        response = input(f"\n    Continue with existing Chrome? [Y/n]: ").strip().lower()
        if response == 'n':
            print_info("Please close Chrome and run this script again")
            return False
        print_success("Using existing Chrome instance")
    else:
        # Step 3: Launch Chrome
        print_step(3, "Launching Chrome with dedicated profile...")
        print_info(f"Profile: {PROFILE_DIR}")

        process = launch_chrome_for_setup()
        if not process:
            print_error("Failed to launch Chrome")
            return False

        # Wait for Chrome to start
        print_info("Waiting for Chrome to start...")
        for i in range(30):
            time.sleep(0.5)
            if is_port_in_use(CDP_PORT):
                break

        if is_port_in_use(CDP_PORT):
            print_success("Chrome launched successfully!")
        else:
            print_error("Chrome failed to start on debug port")
            return False

    # Step 4: Show setup instructions
    print_step(4, "Setup Instructions")
    print_setup_instructions()

    # Step 5: Wait for user to complete setup
    print_step(5, "Waiting for setup completion...")
    print()
    input(f"    {Colors.BOLD}Press ENTER when you've completed the steps above...{Colors.ENDC}")

    # Step 6: Verify setup
    print_step(6, "Verifying setup...")

    # Check Phantom
    print_info("Checking for Phantom wallet...")
    phantom_ok = asyncio.run(verify_phantom_installed())
    if phantom_ok:
        print_success("Phantom wallet detected!")
    else:
        print_warning("Could not verify Phantom (may still work)")

    # Check wallet connection
    print_info("Checking wallet connection...")
    wallet_ok = asyncio.run(verify_wallet_connected())
    if wallet_ok:
        print_success("Wallet appears connected!")
    else:
        print_warning("Could not verify wallet connection (may still work)")

    # Final status
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.ENDC}")

    if phantom_ok and wallet_ok:
        print(f"{Colors.GREEN}{Colors.BOLD}  ✓ SETUP COMPLETE!{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}  ⚠ SETUP MAY BE COMPLETE{Colors.ENDC}")
        print(f"    {Colors.YELLOW}Verification was inconclusive, but setup may still work.{Colors.ENDC}")

    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.ENDC}")
    print()
    print(f"    {Colors.BOLD}Profile saved at:{Colors.ENDC}")
    print(f"    {PROFILE_DIR}")
    print()
    print(f"    {Colors.BOLD}Next steps:{Colors.ENDC}")
    print(f"    1. Run REPLAYER: ./run.sh")
    print(f"    2. Use Browser → Connect to Chrome")
    print(f"    3. Your wallet will be ready for trading!")
    print()
    print(f"    {Colors.CYAN}TIP: Chrome can stay open, or you can close it.{Colors.ENDC}")
    print(f"    {Colors.CYAN}     The profile persists either way!{Colors.ENDC}")
    print()

    return True


if __name__ == "__main__":
    try:
        success = run_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Setup cancelled by user{Colors.ENDC}")
        sys.exit(1)
