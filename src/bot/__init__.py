"""Bot module - Trading strategies and bot controller"""

from .interface import BotInterface
from .controller import BotController
from .strategies import (
    TradingStrategy,
    ConservativeStrategy,
    AggressiveStrategy,
    SidebetStrategy,
    get_strategy,
    list_strategies
)

__all__ = [
    'BotInterface',
    'BotController',
    'TradingStrategy',
    'ConservativeStrategy',
    'AggressiveStrategy',
    'SidebetStrategy',
    'get_strategy',
    'list_strategies',
]
