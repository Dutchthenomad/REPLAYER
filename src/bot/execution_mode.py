"""
Execution Mode Enum - Phase 8.3

Defines how the bot executes trades:
- BACKEND: Direct calls to TradeManager (fast, for training)
- UI_LAYER: Simulated UI clicks (realistic timing, for live preparation)
"""

from enum import Enum


class ExecutionMode(Enum):
    """
    Bot execution mode

    BACKEND: Bot calls TradeManager directly
        - Fastest execution (0ms delay)
        - Perfect for training RL models
        - No timing learning

    UI_LAYER: Bot interacts via UI layer
        - Realistic execution (10-50ms delays)
        - Learns actual timing between action and effect
        - Prepares bot for live browser automation (Phase 8.5)
    """
    BACKEND = "backend"
    UI_LAYER = "ui_layer"
