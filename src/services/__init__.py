"""Services module - Event bus, logger, and file handling"""

from .event_bus import event_bus, Events
from .logger import setup_logging, get_logger
# Phase 10.4E: State verifier
from .state_verifier import StateVerifier, BALANCE_TOLERANCE, POSITION_TOLERANCE
# Phase 10.4F: Recorders
from .recorders import GameStateRecorder, PlayerSessionRecorder
# Phase 10.5B: Recording state machine
from .recording_state_machine import RecordingState, RecordingStateMachine
# Phase 10.5D: Unified recorder
from .unified_recorder import UnifiedRecorder

__all__ = [
    'event_bus',
    'Events',
    'setup_logging',
    'get_logger',
    # Phase 10.4E: State verifier
    'StateVerifier',
    'BALANCE_TOLERANCE',
    'POSITION_TOLERANCE',
    # Phase 10.4F: Recorders
    'GameStateRecorder',
    'PlayerSessionRecorder',
    # Phase 10.5B: Recording state machine
    'RecordingState',
    'RecordingStateMachine',
    # Phase 10.5D: Unified recorder
    'UnifiedRecorder',
]
