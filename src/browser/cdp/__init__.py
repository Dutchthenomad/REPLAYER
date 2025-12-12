"""
Chrome DevTools Protocol (CDP) Module

CDP-specific browser connection and control.
"""

from browser.cdp.launcher import RugsBrowserManager, BrowserStatus

__all__ = [
    'RugsBrowserManager',
    'BrowserStatus',
]
