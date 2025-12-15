"""Services package.

Keep this module lightweight: importing `services` should not trigger heavy
imports (e.g., recorders that pull in live-feed dependencies). This improves
test startup, avoids optional-dependency explosions, and prevents import-order
side effects.
"""

from __future__ import annotations

from typing import Any
import importlib

from .event_bus import event_bus, Events
from .logger import setup_logging, get_logger

__all__ = ["event_bus", "Events", "setup_logging", "get_logger"]


_LAZY_EXPORTS = {
    # Phase 10.4E: State verifier
    "StateVerifier": ("services.state_verifier", "StateVerifier"),
    "BALANCE_TOLERANCE": ("services.state_verifier", "BALANCE_TOLERANCE"),
    "POSITION_TOLERANCE": ("services.state_verifier", "POSITION_TOLERANCE"),
    # Phase 10.4F: Recorders
    "GameStateRecorder": ("services.recorders", "GameStateRecorder"),
    "PlayerSessionRecorder": ("services.recorders", "PlayerSessionRecorder"),
    # Phase 10.5B: Recording state machine
    "RecordingState": ("services.recording_state_machine", "RecordingState"),
    "RecordingStateMachine": ("services.recording_state_machine", "RecordingStateMachine"),
    # Phase 10.5D: Unified recorder
    "UnifiedRecorder": ("services.unified_recorder", "UnifiedRecorder"),
}


def __getattr__(name: str):
    if name in _LAZY_EXPORTS:
        module_name, attr = _LAZY_EXPORTS[name]
        module = importlib.import_module(module_name)
        value = getattr(module, attr)
        globals()[name] = value
        if name not in __all__:
            __all__.append(name)
        return value
    raise AttributeError(f"module 'services' has no attribute {name!r}")
