"""
Enumerations for game states and statuses
"""

from enum import Enum


class Phase(str, Enum):
    """Game phase states"""
    UNKNOWN = "UNKNOWN"
    PRESALE = "PRESALE"
    ACTIVE = "ACTIVE"
    COOLDOWN = "COOLDOWN"
    RUG_EVENT = "RUG_EVENT"
    RUG_EVENT_1 = "RUG_EVENT_1"

    @classmethod
    def is_tradeable(cls, phase: str) -> bool:
        """Check if trading is allowed in this phase.

        Tradeable phases:
        - PRESALE: Pre-round buy window (one BUY + one SIDEBET allowed)
        - ACTIVE: Normal active gameplay
        """
        return phase not in [cls.UNKNOWN, cls.COOLDOWN, cls.RUG_EVENT, cls.RUG_EVENT_1]


class PositionStatus(str, Enum):
    """Position lifecycle status"""
    ACTIVE = "active"
    CLOSED = "closed"


class SideBetStatus(str, Enum):
    """Side bet lifecycle status"""
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
