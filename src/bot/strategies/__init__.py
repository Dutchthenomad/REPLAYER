"""
Trading strategies for bot automation
"""

from .base import TradingStrategy
from .conservative import ConservativeStrategy
from .aggressive import AggressiveStrategy
from .sidebet import SidebetStrategy
from .foundational import FoundationalStrategy

# Strategy registry
STRATEGIES = {
    'conservative': ConservativeStrategy,
    'aggressive': AggressiveStrategy,
    'sidebet': SidebetStrategy,
    'foundational': FoundationalStrategy,  # Phase B: Evidence-based strategy
}


def get_strategy(name: str) -> TradingStrategy:
    """
    Get strategy instance by name

    Args:
        name: Strategy name (conservative, aggressive, sidebet)

    Returns:
        Strategy instance

    Raises:
        ValueError: If strategy name is invalid
    """
    name = name.lower()
    if name not in STRATEGIES:
        valid_strategies = ', '.join(STRATEGIES.keys())
        raise ValueError(
            f"Invalid strategy '{name}'. "
            f"Valid strategies: {valid_strategies}"
        )

    return STRATEGIES[name]()


def list_strategies() -> list:
    """List available strategy names"""
    return list(STRATEGIES.keys())


__all__ = [
    'TradingStrategy',
    'ConservativeStrategy',
    'AggressiveStrategy',
    'SidebetStrategy',
    'FoundationalStrategy',  # Phase B
    'get_strategy',
    'list_strategies',
]
