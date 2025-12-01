"""
Game State Machine and Signal

Provides game phase detection and state transition validation.
Extracted from websocket_feed.py during Phase 3 refactoring.

Classes:
    GameSignal: Clean game state signal dataclass (9 fields + metadata)
    GameStateMachine: Validates game state transitions and detects phases
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class GameSignal:
    """Clean game state signal (9 fields + metadata)"""
    # Core identifiers
    gameId: str

    # State flags
    active: bool
    rugged: bool

    # Game progress
    tickCount: int
    price: Decimal  # AUDIT FIX: Use Decimal for financial precision

    # Timing
    cooldownTimer: int

    # Trading
    allowPreRoundBuys: bool
    tradeCount: int

    # Post-game data
    gameHistory: Optional[List[Dict[str, Any]]]

    # Metadata (added by collector)
    phase: str = "UNKNOWN"
    isValid: bool = True
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    latency: float = 0.0


class GameStateMachine:
    """
    Validates game state transitions and detects phases.

    Responsibilities:
    - Detect current game phase from raw data
    - Validate state transitions are legal
    - Track transition history
    - Count anomalies

    Phases:
    - UNKNOWN: Initial/ambiguous state
    - PRESALE: 10-second window before game starts
    - GAME_ACTIVATION: Instant transition from presale
    - ACTIVE_GAMEPLAY: Main game phase
    - RUG_EVENT_1: Seed reveal (game rugged but still active)
    - RUG_EVENT_2: New game setup
    - COOLDOWN: 5-second settlement buffer

    Usage:
        machine = GameStateMachine()
        result = machine.process(raw_data)
        print(f"Phase: {result['phase']}, Valid: {result['isValid']}")
    """

    def __init__(self):
        """Initialize state machine."""
        self.current_phase = "UNKNOWN"
        self.current_game_id = None
        self.last_tick_count = -1
        self.transition_history = []
        self.anomaly_count = 0

    def detect_phase(self, data: Dict[str, Any]) -> str:
        """
        Detect game phase from raw data.

        Args:
            data: Raw gameStateUpdate data

        Returns:
            Phase string (PRESALE, ACTIVE_GAMEPLAY, RUG_EVENT_1, etc.)
        """
        # RUG EVENT - gameHistory ONLY appears during rug events
        if data.get('gameHistory'):
            if data.get('active') and data.get('rugged'):
                return 'RUG_EVENT_1'  # Seed reveal
            if not data.get('active') and data.get('rugged'):
                return 'RUG_EVENT_2'  # New game setup

        # PRESALE - 10-second window before game starts
        cooldown = data.get('cooldownTimer', 0)
        if (0 < cooldown <= 10000 and
            data.get('allowPreRoundBuys', False)):
            return 'PRESALE'

        # COOLDOWN - 5-second settlement buffer
        if (cooldown > 10000 and
            data.get('rugged', False) and
            not data.get('active', True)):
            return 'COOLDOWN'

        # ACTIVE GAMEPLAY - Main game phase
        if (data.get('active', False) and
            data.get('tickCount', 0) > 0 and
            not data.get('rugged', False)):
            return 'ACTIVE_GAMEPLAY'

        # GAME ACTIVATION - Instant transition from presale
        if (data.get('active', False) and
            data.get('tickCount', 0) == 0 and
            not data.get('rugged', False)):
            return 'GAME_ACTIVATION'

        # Log unknown states for debugging
        logging.debug(f"UNKNOWN state detected - active:{data.get('active')} rugged:{data.get('rugged')} tick:{data.get('tickCount')} cooldown:{cooldown}")

        # If we can't determine state but game is active, stay in current phase
        # This handles brief moments where data might be in transition
        if self.current_phase in ['ACTIVE_GAMEPLAY', 'GAME_ACTIVATION'] and data.get('active', False):
            return self.current_phase

        return 'UNKNOWN'

    def validate_transition(self, new_phase: str, data: Dict[str, Any]) -> bool:
        """
        Validate state transition is legal.

        Args:
            new_phase: Phase we're transitioning to
            data: Raw gameStateUpdate data

        Returns:
            True if transition is legal, False otherwise
        """
        # First state is always valid
        if self.current_phase == 'UNKNOWN':
            return True

        # Transitioning TO unknown is allowed (data ambiguity, not an error)
        # But log it for monitoring
        if new_phase == 'UNKNOWN':
            logging.debug(f"Transitioning from {self.current_phase} to UNKNOWN (data ambiguity)")
            return True

        # Legal transition map
        legal_transitions = {
            'GAME_ACTIVATION': ['ACTIVE_GAMEPLAY', 'RUG_EVENT_1'],
            'ACTIVE_GAMEPLAY': ['ACTIVE_GAMEPLAY', 'RUG_EVENT_1'],
            'RUG_EVENT_1': ['RUG_EVENT_2'],
            'RUG_EVENT_2': ['COOLDOWN'],
            'COOLDOWN': ['PRESALE'],
            'PRESALE': ['PRESALE', 'GAME_ACTIVATION', 'ACTIVE_GAMEPLAY'],  # FIX: Allow direct PRESALE → ACTIVE_GAMEPLAY
            'UNKNOWN': ['GAME_ACTIVATION', 'ACTIVE_GAMEPLAY', 'PRESALE', 'COOLDOWN']
        }

        allowed_next = legal_transitions.get(self.current_phase, [])
        is_legal = new_phase in allowed_next or new_phase == self.current_phase

        if not is_legal:
            logging.warning(f"Illegal transition: {self.current_phase} → {new_phase} (allowed: {allowed_next})")
            return False

        # Validate tick progression in active gameplay
        if new_phase == 'ACTIVE_GAMEPLAY' and self.current_phase == 'ACTIVE_GAMEPLAY':
            game_id = data.get('gameId')
            tick_count = data.get('tickCount', 0)

            if game_id == self.current_game_id:
                if tick_count <= self.last_tick_count:
                    logging.warning(f"Tick regression detected: {self.last_tick_count} → {tick_count}")
                    return False

        return True

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process game state update and return validation result.

        Args:
            data: Raw gameStateUpdate data

        Returns:
            Dict with 'phase', 'isValid', and 'previousPhase'
        """
        phase = self.detect_phase(data)
        is_valid = self.validate_transition(phase, data)

        if not is_valid:
            self.anomaly_count += 1
            logging.warning(f"Invalid state transition detected (anomaly #{self.anomaly_count})")

        # Track transition
        previous_phase = self.current_phase
        if phase != self.current_phase:
            self.transition_history.append({
                'from': self.current_phase,
                'to': phase,
                'gameId': data.get('gameId'),
                'tick': data.get('tickCount', 0),
                'timestamp': int(time.time() * 1000)
            })

            # Keep only last 20 transitions
            if len(self.transition_history) > 20:
                self.transition_history.pop(0)

        # Update state
        self.current_phase = phase
        self.current_game_id = data.get('gameId')
        self.last_tick_count = data.get('tickCount', 0)

        return {
            'phase': phase,
            'isValid': is_valid,
            'previousPhase': previous_phase
        }

    def reset(self):
        """Reset state machine to initial state."""
        self.current_phase = "UNKNOWN"
        self.current_game_id = None
        self.last_tick_count = -1
        self.transition_history = []
        self.anomaly_count = 0

    def recover_from_disconnect(self) -> Dict[str, Any]:
        """
        PHASE 3.4 AUDIT FIX: Recover state machine after a disconnect.

        This method handles the case where the WebSocket connection is lost
        and then re-established. It preserves game context while allowing
        the state machine to gracefully re-sync with incoming data.

        Returns:
            Dict with recovery info (previous state, game_id, etc.)
        """
        recovery_info = {
            'previous_phase': self.current_phase,
            'previous_game_id': self.current_game_id,
            'previous_tick': self.last_tick_count,
            'anomaly_count_before': self.anomaly_count,
            'recovered': True
        }

        # Record the disconnect in transition history
        self.transition_history.append({
            'from': self.current_phase,
            'to': 'DISCONNECT_RECOVERY',
            'gameId': self.current_game_id,
            'tick': self.last_tick_count,
            'timestamp': int(time.time() * 1000)
        })

        # Keep only last 20 transitions
        if len(self.transition_history) > 20:
            self.transition_history.pop(0)

        # Reset to UNKNOWN phase to allow re-detection
        # But preserve game_id so we can detect if game changed during disconnect
        self.current_phase = "UNKNOWN"
        # Don't reset game_id - we'll compare on first signal after reconnect
        # Don't reset tick count - we'll compare to detect gaps

        logging.info(
            f"State machine recovery initiated: "
            f"was in {recovery_info['previous_phase']} at tick {recovery_info['previous_tick']}"
        )

        return recovery_info

    def get_state_summary(self) -> Dict[str, Any]:
        """
        PHASE 3.4 AUDIT FIX: Get a summary of current state for debugging.

        Returns:
            Dict with current state info
        """
        return {
            'phase': self.current_phase,
            'game_id': self.current_game_id,
            'tick': self.last_tick_count,
            'anomaly_count': self.anomaly_count,
            'recent_transitions': self.transition_history[-5:] if self.transition_history else []
        }
