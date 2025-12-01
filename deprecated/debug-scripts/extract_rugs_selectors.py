#!/usr/bin/env python3
"""
Empirical Button Selector Extraction for Rugs.fun

CRITICAL: This script uses actual browser automation to identify
resilient selectors empirically, not from documentation.

Strategy:
1. Launch Rugs.fun in browser
2. Wait for page to load completely
3. Extract ALL button selectors using multiple strategies:
   - Text-based (button:has-text("BUY"))
   - data-testid attributes (if available)
   - CSS class-based selectors
   - Relative XPaths (NOT absolute)
4. Test each selector's stability
5. Generate priority-ordered selector arrays

Usage:
    cd /home/nomad/Desktop/REPLAYER
    python3 extract_rugs_selectors.py
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import Playwright
try:
    from playwright.async_api import async_playwright, Page, Locator
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.error("Playwright not available. Install with: pip install playwright && playwright install chromium")
    PLAYWRIGHT_AVAILABLE = False


class SelectorExtractor:
    """
    Extracts resilient selectors from live Rugs.fun website

    Selector Priority Order (most to least resilient):
    1. Text-based: button:has-text("BUY")
    2. data-testid: [data-testid="buy-button"]
    3. CSS class: .bet-controls .primary-action
    4. Relative XPath: //button[contains(text(), "BUY")]
    5. Absolute XPath: LAST RESORT ONLY
    """

    RUGS_URL = "https://rugs.fun"

    def __init__(self):
        self.page: Optional[Page] = None
        self.selectors: Dict[str, List[str]] = {}

    async def launch_browser(self):
        """Launch browser and navigate to Rugs.fun"""
        logger.info("Launching browser...")

        self.playwright = await async_playwright().start()

        # Use persistent context if available (for wallet connection)
        profile_dir = Path.home() / ".config" / "replayer" / "browser_profiles" / "rugs_fun_phantom"

        if profile_dir.exists():
            logger.info(f"Using persistent profile: {profile_dir}")
            self.context = await self.playwright.chromium.launch_persistent_context(
                str(profile_dir),
                headless=False,  # IMPORTANT: Run visible so we can see what's happening
                args=['--disable-blink-features=AutomationControlled']
            )
            self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        else:
            logger.info("Using non-persistent browser")
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

        # Navigate to Rugs.fun
        logger.info(f"Navigating to {self.RUGS_URL}...")
        await self.page.goto(self.RUGS_URL)

        # Wait for page to load
        await self.page.wait_for_load_state('networkidle', timeout=30000)
        logger.info("Page loaded successfully")

        # Wait a bit more for dynamic content
        await asyncio.sleep(2)

    async def extract_button_selectors(self, button_name: str, expected_texts: List[str]) -> List[str]:
        """
        Extract selectors for a specific button using multiple strategies

        Args:
            button_name: Human-readable name (e.g., "BUY", "INCREMENT_001")
            expected_texts: List of text strings to search for (e.g., ["BUY", "Buy"])

        Returns:
            List of selectors ordered by resilience (best first)
        """
        selectors = []

        logger.info(f"Extracting selectors for: {button_name}")

        # Strategy 1: Text-based locators (MOST RESILIENT)
        for text in expected_texts:
            # Try exact match
            exact_selector = f'button:has-text("{text}")'
            try:
                count = await self.page.locator(exact_selector).count()
                if count > 0:
                    selectors.append(exact_selector)
                    logger.info(f"  ✅ Text-based (exact): {exact_selector} ({count} matches)")
                    break  # Found it, no need to try other text variants
            except Exception as e:
                logger.debug(f"  ❌ Text-based (exact) failed: {e}")

            # Try case-insensitive
            ci_selector = f'button:has-text("{text}"):not([disabled])'
            try:
                count = await self.page.locator(ci_selector).count()
                if count > 0:
                    selectors.append(ci_selector)
                    logger.info(f"  ✅ Text-based (enabled): {ci_selector} ({count} matches)")
                    break
            except Exception as e:
                logger.debug(f"  ❌ Text-based (enabled) failed: {e}")

        # Strategy 2: data-testid (if available)
        testid_selector = f'[data-testid="{button_name.lower().replace("_", "-")}"]'
        try:
            count = await self.page.locator(testid_selector).count()
            if count > 0:
                selectors.append(testid_selector)
                logger.info(f"  ✅ data-testid: {testid_selector} ({count} matches)")
        except Exception as e:
            logger.debug(f"  ❌ data-testid failed: {e}")

        # Strategy 3: Get actual element and analyze its attributes
        if selectors:
            # Use first working selector to find element
            try:
                element = self.page.locator(selectors[0]).first

                # Get element properties
                classes = await element.get_attribute('class')
                id_attr = await element.get_attribute('id')
                aria_label = await element.get_attribute('aria-label')

                # Try CSS class-based selector
                if classes:
                    class_list = classes.split()
                    if class_list:
                        class_selector = f'button.{".".join(class_list)}'
                        try:
                            count = await self.page.locator(class_selector).count()
                            if count > 0 and count < 5:  # Reasonably specific
                                selectors.append(class_selector)
                                logger.info(f"  ✅ CSS class: {class_selector} ({count} matches)")
                        except Exception as e:
                            logger.debug(f"  ❌ CSS class failed: {e}")

                # Try ID-based selector
                if id_attr:
                    id_selector = f'#{id_attr}'
                    selectors.append(id_selector)
                    logger.info(f"  ✅ ID: {id_selector}")

                # Try aria-label
                if aria_label:
                    aria_selector = f'[aria-label="{aria_label}"]'
                    selectors.append(aria_selector)
                    logger.info(f"  ✅ aria-label: {aria_selector}")

            except Exception as e:
                logger.warning(f"  ⚠️ Could not analyze element: {e}")

        # Strategy 4: Relative XPath (LESS RESILIENT - use as fallback only)
        for text in expected_texts:
            relative_xpath = f'//button[contains(text(), "{text}")]'
            try:
                count = await self.page.locator(f'xpath={relative_xpath}').count()
                if count > 0:
                    selectors.append(f'xpath={relative_xpath}')
                    logger.info(f"  ⚠️ Relative XPath: {relative_xpath} ({count} matches)")
                    break
            except Exception as e:
                logger.debug(f"  ❌ Relative XPath failed: {e}")

        if not selectors:
            logger.error(f"  ❌ NO SELECTORS FOUND for {button_name}")

        return selectors

    async def extract_all_buttons(self):
        """Extract selectors for all Rugs.fun buttons"""

        # Define all buttons we need to find
        button_definitions = {
            # Increment buttons
            'CLEAR_BET': ['X', '×', 'Clear'],
            'INCREMENT_0001': ['+0.001', '0.001'],
            'INCREMENT_001': ['+0.01', '0.01'],
            'INCREMENT_01': ['+0.1', '0.1'],
            'INCREMENT_1': ['+1', '1'],
            'HALF': ['1/2', 'Half', '½'],
            'DOUBLE': ['X2', 'x2', 'Double', '2x'],
            'MAX': ['MAX', 'Max'],

            # Action buttons
            'BUY': ['BUY', 'Buy', 'LONG'],
            'SELL': ['SELL', 'Sell'],
            'SHORT': ['SHORT', 'Short'],  # May not exist in UI yet

            # Partial sell buttons
            'SELL_10': ['10%', '10'],
            'SELL_25': ['25%', '25'],
            'SELL_50': ['50%', '50'],
            'SELL_100': ['100%', '100'],

            # Sidebet buttons (two-step process)
            'SIDEBET_UNHIDE': ['OPEN', 'Open', 'Show'],
            'SIDEBET_ACTIVATE': ['ACTIVATE', 'Activate', 'Place Bet'],
        }

        logger.info("="*60)
        logger.info("EXTRACTING ALL BUTTON SELECTORS")
        logger.info("="*60)

        for button_name, expected_texts in button_definitions.items():
            selectors = await self.extract_button_selectors(button_name, expected_texts)
            self.selectors[button_name] = selectors
            print()  # Blank line between buttons

        logger.info("="*60)
        logger.info("EXTRACTION COMPLETE")
        logger.info("="*60)

    def generate_python_code(self) -> str:
        """Generate Python code with selector arrays"""

        code = '"""\nButton Selectors - Empirically Verified\n\n'
        code += 'Generated by: extract_rugs_selectors.py\n'
        code += 'Strategy: Text-based (primary) → data-testid → CSS class → XPath (fallback)\n'
        code += '"""\n\n'

        for button_name, selectors in self.selectors.items():
            if not selectors:
                code += f'# WARNING: No selectors found for {button_name}\n'
                code += f'{button_name}_SELECTORS = []\n\n'
            else:
                code += f'# {button_name} - {len(selectors)} selector(s)\n'
                code += f'{button_name}_SELECTORS = [\n'
                for selector in selectors:
                    code += f'    \'{selector}\',\n'
                code += ']\n\n'

        return code

    async def save_results(self):
        """Save extracted selectors to file"""

        output_file = Path(__file__).parent / 'extracted_selectors.py'

        code = self.generate_python_code()

        with open(output_file, 'w') as f:
            f.write(code)

        logger.info(f"✅ Selectors saved to: {output_file}")

        # Also save as JSON for reference
        json_file = Path(__file__).parent / 'extracted_selectors.json'
        with open(json_file, 'w') as f:
            json.dump(self.selectors, f, indent=2)

        logger.info(f"✅ JSON saved to: {json_file}")

    async def close(self):
        """Close browser"""
        if hasattr(self, 'context'):
            await self.context.close()
        if hasattr(self, 'browser'):
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()


async def main():
    """Main extraction flow"""

    if not PLAYWRIGHT_AVAILABLE:
        logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return

    logger.info("🌐 Rugs.fun Selector Extractor - Empirical Verification")
    logger.info("This will launch a browser and extract button selectors\n")
    logger.info("Starting in 2 seconds...")

    extractor = SelectorExtractor()

    try:
        await extractor.launch_browser()

        logger.info("\n⏳ Waiting 5 seconds for you to interact with page if needed...")
        logger.info("   (Connect wallet, start game, etc.)")
        await asyncio.sleep(5)

        await extractor.extract_all_buttons()

        await extractor.save_results()

        logger.info("\n✅ SELECTOR EXTRACTION COMPLETE!")
        logger.info("\nNext steps:")
        logger.info("1. Review extracted_selectors.py")
        logger.info("2. Update browser_executor.py with verified selectors")
        logger.info("3. Test button clicks in live browser")

        logger.info("\nClosing browser in 3 seconds...")
        await asyncio.sleep(3)

    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}", exc_info=True)

    finally:
        await extractor.close()


if __name__ == '__main__':
    asyncio.run(main())
