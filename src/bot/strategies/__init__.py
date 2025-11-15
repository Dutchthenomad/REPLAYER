"""
Trading strategies for bot automation
"""

from .base import TradingStrategy
from .conservative import ConservativeStrategy
from .aggressive import AggressiveStrategy
from .sidebet import SidebetStrategy

# Strategy registry
STRATEGIES = {
    'conservative': ConservativeStrategy,
    'aggressive': AggressiveStrategy,
    'sidebet': SidebetStrategy,
}


def get_strategy(name: str) -> TradingStrategy:
    """
    Get strategy instance by name

    Args:
        name: Strategy name (conservative, aggressive, sidebet)

    Returns:
        Strategy instance or None if not found
    """
    name = name.lower()
    if name not in STRATEGIES:
        return None

    return STRATEGIES[name]()


def list_strategies() -> list:
    """List available strategy names"""
    return list(STRATEGIES.keys())


__all__ = [
    'TradingStrategy',
    'ConservativeStrategy',
    'AggressiveStrategy',
    'SidebetStrategy',
    'get_strategy',
    'list_strategies',
]
