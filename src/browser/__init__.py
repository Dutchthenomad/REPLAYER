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

from __future__ import annotations

from typing import Any
import importlib


_LAZY_EXPORTS = {
    "BrowserExecutor": ("browser.executor", "BrowserExecutor"),
    "BrowserBridge": ("browser.bridge", "BrowserBridge"),
    "get_browser_bridge": ("browser.bridge", "get_browser_bridge"),
    "BridgeStatus": ("browser.bridge", "BridgeStatus"),
    "CDPBrowserManager": ("browser.manager", "CDPBrowserManager"),
    "CDPStatus": ("browser.manager", "CDPStatus"),
}


__all__ = [
    # Intentionally omit lazy exports from `__all__` to keep lint/typecheck
    # tools happy; direct imports (`from browser import BrowserExecutor`) still
    # work via PEP 562 module `__getattr__`.
]


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        module_name, attr = _LAZY_EXPORTS[name]
        module = importlib.import_module(module_name)
        value = getattr(module, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'browser' has no attribute {name!r}")
