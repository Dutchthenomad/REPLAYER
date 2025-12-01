"""
Browser State Reader Mixin

Provides methods to read game state from browser DOM.
Extracted from browser_executor.py during Phase 1 refactoring.

Classes:
    BrowserStateReaderMixin: Mixin providing read_balance_from_browser, read_position_from_browser
"""

import asyncio
import logging
import re
from decimal import Decimal
from typing import Optional, Dict, Any

from bot.browser_selectors import BALANCE_SELECTORS, POSITION_SELECTORS

logger = logging.getLogger(__name__)


class BrowserStateReaderMixin:
    """
    Mixin class providing browser state reading methods.

    Requires the host class to have:
    - self.page property (Playwright page object)

    Usage:
        class BrowserExecutor(BrowserStateReaderMixin):
            ...
    """

    async def read_balance_from_browser(self) -> Optional[Decimal]:
        """
        Read balance from browser DOM

        Phase 8.6: Polls browser state for accurate balance

        Returns:
            Balance in SOL, or None if not available
        """
        if not self.page:
            logger.warning("Cannot read balance: browser not started")
            return None

        try:
            for selector in BALANCE_SELECTORS:
                try:
                    element = await asyncio.wait_for(
                        self.page.query_selector(selector),
                        timeout=2.0
                    )
                    if element:
                        text = await element.text_content()
                        # Extract number from text like "Balance: 1.234 SOL"
                        match = re.search(r'([0-9]+\.[0-9]+)', text)
                        if match:
                            balance = Decimal(match.group(1))
                            logger.debug(f"Read balance from browser: {balance} SOL")
                            return balance
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            logger.warning("Could not find balance element in browser DOM")
            return None

        except Exception as e:
            logger.error(f"Failed to read balance from browser: {e}")
            return None

    async def read_position_from_browser(self) -> Optional[Dict[str, Any]]:
        """
        Read position from browser DOM

        Phase 8.6: Polls browser state for open position

        Returns:
            Position dict with entry_price, amount, status; or None if no position
        """
        if not self.page:
            logger.warning("Cannot read position: browser not started")
            return None

        try:
            for selector in POSITION_SELECTORS:
                try:
                    element = await asyncio.wait_for(
                        self.page.query_selector(selector),
                        timeout=2.0
                    )
                    if element:
                        text = await element.text_content()
                        # Extract position info like "Position: 1.5x, 0.01 SOL"
                        price_match = re.search(r'([0-9]+\.[0-9]+)x', text)
                        amount_match = re.search(r'([0-9]+\.[0-9]+)\s*SOL', text)

                        if price_match:
                            entry_price = Decimal(price_match.group(1))
                            amount = Decimal(amount_match.group(1)) if amount_match else Decimal('0.001')

                            position = {
                                'entry_price': entry_price,
                                'amount': amount,
                                'status': 'active',
                                'entry_tick': 0,  # Unknown from DOM
                            }
                            logger.debug(f"Read position from browser: {entry_price}x, {amount} SOL")
                            return position
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            # No position found
            logger.debug("No position found in browser DOM")
            return None

        except Exception as e:
            logger.error(f"Failed to read position from browser: {e}")
            return None

    async def read_current_price_from_browser(self) -> Optional[Decimal]:
        """
        Read current price multiplier from browser DOM

        Returns:
            Current price as Decimal, or None if not available
        """
        if not self.page:
            logger.warning("Cannot read price: browser not started")
            return None

        try:
            # Try common selectors for price display
            price_selectors = [
                'text=/([0-9]+\\.?[0-9]*)x/i',
                '[data-price]',
                '.price',
                '.multiplier',
            ]

            for selector in price_selectors:
                try:
                    element = await asyncio.wait_for(
                        self.page.query_selector(selector),
                        timeout=2.0
                    )
                    if element:
                        text = await element.text_content()
                        # Extract price like "1.5x" or "25.3x"
                        match = re.search(r'([0-9]+\.?[0-9]*)x?', text)
                        if match:
                            price = Decimal(match.group(1))
                            logger.debug(f"Read price from browser: {price}x")
                            return price
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            logger.debug("Could not find price element in browser DOM")
            return None

        except Exception as e:
            logger.error(f"Failed to read price from browser: {e}")
            return None

    async def is_game_active_in_browser(self) -> bool:
        """
        Check if a game is currently active in browser

        Returns:
            True if game is active, False otherwise
        """
        if not self.page:
            return False

        try:
            # Check for game active indicators
            active_selectors = [
                '[data-game-active="true"]',
                '.game-active',
                'button:has-text("BUY"):not([disabled])',
            ]

            for selector in active_selectors:
                try:
                    element = await asyncio.wait_for(
                        self.page.query_selector(selector),
                        timeout=1.0
                    )
                    if element:
                        return True
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.error(f"Failed to check game active state: {e}")
            return False

    async def is_rugged_in_browser(self) -> bool:
        """
        Check if the current game has rugged in browser

        Returns:
            True if rugged, False otherwise
        """
        if not self.page:
            return False

        try:
            # Check for rug indicators
            rug_selectors = [
                '[data-rugged="true"]',
                '.rugged',
                'text=/RUGGED/i',
                'text=/RUG/i',
            ]

            for selector in rug_selectors:
                try:
                    element = await asyncio.wait_for(
                        self.page.query_selector(selector),
                        timeout=1.0
                    )
                    if element:
                        return True
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.error(f"Failed to check rug state: {e}")
            return False
