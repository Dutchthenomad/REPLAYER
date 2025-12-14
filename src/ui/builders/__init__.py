"""
UI Builders Package

Contains builder classes for UI construction, extracted from MainWindow.
Each builder handles construction of a specific UI section.

Pattern:
    builder = SomeBuilder(parent, **dependencies)
    widgets = builder.build()  # Returns dict of widget references
"""

from .menu_bar_builder import MenuBarBuilder
from .status_bar_builder import StatusBarBuilder
from .chart_builder import ChartBuilder
from .playback_builder import PlaybackBuilder
from .betting_builder import BettingBuilder
from .action_builder import ActionBuilder

__all__ = [
    'MenuBarBuilder',
    'StatusBarBuilder',
    'ChartBuilder',
    'PlaybackBuilder',
    'BettingBuilder',
    'ActionBuilder',
]
