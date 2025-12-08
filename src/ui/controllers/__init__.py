"""
UI Controllers Package

Contains controller classes extracted from MainWindow to follow Single Responsibility Principle.
Each controller handles a specific aspect of the application.
"""

from .bot_manager import BotManager
from .replay_controller import ReplayController
from .trading_controller import TradingController
from .live_feed_controller import LiveFeedController
from .browser_bridge_controller import BrowserBridgeController
# Phase 10.5H: Recording controller
from .recording_controller import RecordingController

__all__ = [
    'BotManager',
    'ReplayController',
    'TradingController',
    'LiveFeedController',
    'BrowserBridgeController',
    'RecordingController',
]
