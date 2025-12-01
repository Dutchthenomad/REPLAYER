#!/usr/bin/env python3
"""
Playwright Debug Helper - Visual validation for browser automation

This script helps debug browser automation by:
- Taking screenshots at key moments
- Capturing console logs
- Recording video of bot actions
- Validating UI state changes

Usage:
    cd /home/nomad/Desktop/REPLAYER/src
    /home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3 playwright_debug_helper.py

This will launch a browser and monitor bot actions with visual validation.
"""

import sys
import os
from pathlib import Path
import asyncio
import logging
from datetime import datetime
import json

# Add parent directory to Python path to allow imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright, Page

# Setup logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
debug_dir = Path(f"playwright_debug_{timestamp}")
debug_dir.mkdir(exist_ok=True)
screenshot_dir = debug_dir / "screenshots"
screenshot_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(debug_dir / "playwright_debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Metrics
metrics = {
    'session_start': timestamp,
    'screenshots': [],
    'console_logs': [],
    'actions': [],
    'errors': []
}

screenshot_counter = 0


class PlaywrightDebugger:
    """Debug helper for Playwright browser automation"""

    def __init__(self):
        self.browser_manager = None
        self.page = None

    async def initialize(self):
        """Initialize browser and setup monitoring"""
        logger.info("Initializing browser...")

        # Create browser manager
        self.browser_manager = RugsBrowserManager(headless=False)

        # Start browser
        await self.browser_manager.start()
        self.page = self.browser_manager.page

        # Setup console log monitoring
        self.page.on("console", self._on_console_message)
        self.page.on("pageerror", self._on_page_error)

        logger.info("Browser initialized successfully")

    async def take_screenshot(self, reason: str):
        """Take screenshot of browser state"""
        global screenshot_counter
        screenshot_counter += 1

        filename = f"{screenshot_counter:03d}_{reason}.png"
        filepath = screenshot_dir / filename

        await self.page.screenshot(path=str(filepath), full_page=True)

        metrics['screenshots'].append({
            'number': screenshot_counter,
            'reason': reason,
            'filename': filename,
            'timestamp': datetime.now().isoformat()
        })

        logger.info(f"📸 Screenshot {screenshot_counter}: {reason}")

    def _on_console_message(self, msg):
        """Capture console logs from browser"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': msg.type,
            'text': msg.text,
            'location': msg.location
        }

        metrics['console_logs'].append(log_entry)

        # Log important messages
        if msg.type in ['error', 'warning']:
            logger.warning(f"Browser {msg.type}: {msg.text}")
        else:
            logger.debug(f"Browser console: {msg.text}")

    def _on_page_error(self, error):
        """Capture page errors"""
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'error': str(error)
        }

        metrics['errors'].append(error_entry)
        logger.error(f"Browser error: {error}")

    async def monitor_bot_action(self, action_name: str, action_func):
        """
        Monitor a bot action and capture screenshots before/after

        Args:
            action_name: Name of the action (e.g., "click_buy")
            action_func: Async function to execute
        """
        logger.info(f"▶️ Action: {action_name}")

        # Screenshot before
        await self.take_screenshot(f"before_{action_name}")

        # Execute action
        start_time = datetime.now()
        try:
            result = await action_func()

            # Screenshot after
            await asyncio.sleep(0.5)  # Let UI update
            await self.take_screenshot(f"after_{action_name}")

            # Record action
            metrics['actions'].append({
                'timestamp': start_time.isoformat(),
                'name': action_name,
                'duration_ms': (datetime.now() - start_time).total_seconds() * 1000,
                'success': True,
                'result': str(result) if result else None
            })

            logger.info(f"✅ Action completed: {action_name}")
            return result

        except Exception as e:
            # Screenshot on error
            await self.take_screenshot(f"error_{action_name}")

            # Record error
            metrics['actions'].append({
                'timestamp': start_time.isoformat(),
                'name': action_name,
                'duration_ms': (datetime.now() - start_time).total_seconds() * 1000,
                'success': False,
                'error': str(e)
            })

            logger.error(f"❌ Action failed: {action_name} - {e}")
            raise

    async def validate_ui_state(self, expected_state: dict):
        """
        Validate current UI state matches expectations

        Args:
            expected_state: Dict with expected values (balance, price, position, etc.)
        """
        logger.info("🔍 Validating UI state...")

        # Extract UI state using selectors
        actual_state = {}

        try:
            # Balance
            if 'balance' in expected_state:
                balance_text = await self.page.locator('[data-testid="balance"]').text_content()
                actual_state['balance'] = float(balance_text.strip())

            # Price
            if 'price' in expected_state:
                price_text = await self.page.locator('[data-testid="price"]').text_content()
                actual_state['price'] = float(price_text.replace('x', '').strip())

            # Compare
            for key, expected_value in expected_state.items():
                actual_value = actual_state.get(key)
                if actual_value is None:
                    logger.warning(f"⚠️ Could not read {key} from UI")
                elif abs(actual_value - expected_value) > 0.0001:
                    logger.error(f"❌ State mismatch - {key}: expected {expected_value}, got {actual_value}")
                    await self.take_screenshot(f"state_mismatch_{key}")
                else:
                    logger.info(f"✅ State match - {key}: {actual_value}")

        except Exception as e:
            logger.error(f"State validation error: {e}")
            await self.take_screenshot("state_validation_error")

    async def cleanup(self):
        """Cleanup browser and save metrics"""
        logger.info("Cleaning up...")

        if self.browser_manager:
            await self.browser_manager.cleanup()

        # Save metrics
        metrics_file = debug_dir / "metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)

        logger.info("=" * 80)
        logger.info("PLAYWRIGHT DEBUG SESSION COMPLETE")
        logger.info(f"Screenshots: {len(metrics['screenshots'])}")
        logger.info(f"Console logs: {len(metrics['console_logs'])}")
        logger.info(f"Actions: {len(metrics['actions'])}")
        logger.info(f"Errors: {len(metrics['errors'])}")
        logger.info(f"Output directory: {debug_dir}")
        logger.info("=" * 80)


async def demo_debug_session():
    """Demo debug session showing capabilities"""
    debugger = PlaywrightDebugger()

    try:
        await debugger.initialize()

        # Navigate to game
        logger.info("Navigating to Rugs.fun...")
        await debugger.monitor_bot_action(
            "navigate_to_game",
            lambda: debugger.page.goto("https://rugs.fun")
        )

        # Wait for game to load
        await asyncio.sleep(3)
        await debugger.take_screenshot("game_loaded")

        # Demo: Monitor a buy action (if bot were running)
        logger.info("Demo complete - browser will stay open for manual inspection")

        # Keep browser open for 30 seconds for manual inspection
        await asyncio.sleep(30)

    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)
    finally:
        await debugger.cleanup()


if __name__ == '__main__':
    # Run demo
    asyncio.run(demo_debug_session())
