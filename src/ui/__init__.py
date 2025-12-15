"""UI package.

Keep this module lightweight: importing `ui` should not trigger heavy optional
dependencies (e.g., Playwright) via deep import chains.
"""

from __future__ import annotations

from typing import Any
import importlib

from .layout_manager import LayoutManager, Panel, PanelConfig, PanelPosition, ResizeMode
from .panels import StatusPanel, ChartPanel, TradingPanel, BotPanel, ControlsPanel

__all__ = [
    "LayoutManager",
    "Panel",
    "PanelConfig",
    "PanelPosition",
    "ResizeMode",
    "StatusPanel",
    "ChartPanel",
    "TradingPanel",
    "BotPanel",
    "ControlsPanel",
]


_LAZY_EXPORTS = {
    "MainWindow": ("ui.main_window", "MainWindow"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        module_name, attr = _LAZY_EXPORTS[name]
        module = importlib.import_module(module_name)
        value = getattr(module, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'ui' has no attribute {name!r}")
