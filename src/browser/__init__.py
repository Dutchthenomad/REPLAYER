"""
Browser Automation Module - Phase 2 Consolidation

Unified module for all browser automation functionality.
Consolidates code from bot/browser_* and browser_automation/

Structure:
- executor.py - Main browser executor for trading actions
- bridge.py - UI <-> Browser bridge
- manager.py - CDP browser connection manager
- automation.py - Wallet automation helpers
- profiles.py - Browser profile management
- dom/ - DOM interaction utilities
  - selectors.py - Element selectors
  - timing.py - Timing and delays
- cdp/ - Chrome DevTools Protocol
  - launcher.py - Chrome launcher

Main exports for common use:
"""

from browser.executor import BrowserExecutor
from browser.bridge import BrowserBridge, get_browser_bridge, BridgeStatus
from browser.manager import CDPBrowserManager, CDPStatus

__all__ = [
    'BrowserExecutor',
    'BrowserBridge',
    'get_browser_bridge',
    'BridgeStatus',
    'CDPBrowserManager',
    'CDPStatus',
]
