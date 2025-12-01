"""
Browser Automation Package

Provides browser control for live trading via CDP (Chrome DevTools Protocol).
"""

# Lazy imports to avoid import errors when dependencies are missing
__all__ = [
    'CDPBrowserManager',
    'CDPStatus',
    'RugsBrowserManager',
    'BrowserStatus',
    'PersistentProfile',
]


def __getattr__(name):
    """Lazy import to avoid errors when playwright not installed."""
    if name in ('CDPBrowserManager', 'CDPStatus'):
        try:
            from .cdp_browser_manager import CDPBrowserManager, CDPStatus
            return CDPBrowserManager if name == 'CDPBrowserManager' else CDPStatus
        except ImportError as e:
            raise ImportError(f"CDPBrowserManager requires playwright: {e}")

    if name in ('RugsBrowserManager', 'BrowserStatus'):
        try:
            from .rugs_browser import RugsBrowserManager, BrowserStatus
            return RugsBrowserManager if name == 'RugsBrowserManager' else BrowserStatus
        except ImportError as e:
            raise ImportError(f"RugsBrowserManager requires playwright: {e}")

    if name == 'PersistentProfile':
        from .persistent_profile import PersistentProfile
        return PersistentProfile

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
