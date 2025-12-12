"""
Sources module for REPLAYER - Live feed integrations

Phase 10.4A: Modular refactor - extracted classes to separate modules
for maintainability (<400 lines per file).
"""

from sources.websocket_feed import WebSocketFeed
from sources.game_state_machine import GameSignal, GameStateMachine

# Phase 10.4A: Extracted modules
from sources.feed_monitors import (
    LatencySpikeDetector,
    ConnectionHealth,
    ConnectionHealthMonitor
)
from sources.feed_rate_limiter import (
    TokenBucketRateLimiter,
    PriorityRateLimiter
)
from sources.feed_degradation import (
    OperatingMode,
    GracefulDegradationManager
)
# Phase 10.4D: Price history handler
from sources.price_history_handler import PriceHistoryHandler
# Phase 10.5C: Data integrity monitor
from sources.data_integrity_monitor import (
    DataIntegrityMonitor,
    ThresholdType,
    IntegrityIssue
)

__all__ = [
    'WebSocketFeed',
    'GameSignal',
    'GameStateMachine',
    # Phase 10.4A: Extracted monitors
    'LatencySpikeDetector',
    'ConnectionHealth',
    'ConnectionHealthMonitor',
    # Phase 10.4A: Extracted rate limiters
    'TokenBucketRateLimiter',
    'PriorityRateLimiter',
    # Phase 10.4A: Extracted degradation
    'OperatingMode',
    'GracefulDegradationManager',
    # Phase 10.4D: Price history handler
    'PriceHistoryHandler',
    # Phase 10.5C: Data integrity monitor
    'DataIntegrityMonitor',
    'ThresholdType',
    'IntegrityIssue',
]
