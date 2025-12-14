"""
Feed Degradation - Phase 10.4A Modular Refactor

Extracted from websocket_feed.py:
- OperatingMode: Operating mode for graceful degradation
- GracefulDegradationManager: Manages graceful degradation based on system health

These classes handle graceful degradation logic for the WebSocket feed
without containing any Socket.IO-specific code.
"""

import time
import threading
from typing import Dict, Any, Optional, Callable
from collections import deque


class OperatingMode:
    """
    Operating mode for graceful degradation.

    PHASE 3.6 AUDIT FIX: Defines system operating states.
    """
    NORMAL = "NORMAL"              # Full functionality
    DEGRADED = "DEGRADED"          # Reduced functionality (high latency/errors)
    MINIMAL = "MINIMAL"            # Minimal functionality (severe issues)
    OFFLINE = "OFFLINE"            # No connection


class GracefulDegradationManager:
    """
    Manages graceful degradation based on system health.

    PHASE 3.6 AUDIT FIX: Reduces functionality when issues detected to maintain stability.

    Degradation levels:
    - NORMAL: Full processing, all features enabled
    - DEGRADED: Skip non-critical processing, log warnings
    - MINIMAL: Only essential processing, buffer aggressively
    - OFFLINE: No processing, queue for retry
    """

    def __init__(
        self,
        error_threshold: int = 10,
        spike_threshold: int = 5,
        recovery_window_sec: float = 60.0
    ):
        """
        Initialize degradation manager.

        Args:
            error_threshold: Errors in window before degradation
            spike_threshold: Latency spikes in window before degradation
            recovery_window_sec: Seconds without issues before recovery
        """
        self.error_threshold = error_threshold
        self.spike_threshold = spike_threshold
        self.recovery_window_sec = recovery_window_sec

        self.current_mode = OperatingMode.NORMAL
        self.mode_history: deque = deque(maxlen=20)

        # Tracking
        self.errors_in_window = 0
        self.spikes_in_window = 0
        self.last_issue_time: Optional[float] = None
        self.degradation_start_time: Optional[float] = None
        self._lock = threading.Lock()

        # Callbacks
        self.on_mode_change: Optional[Callable] = None

    def record_error(self):
        """Record an error occurrence"""
        with self._lock:
            self.errors_in_window += 1
            self.last_issue_time = time.time()
            self._evaluate_mode()

    def record_spike(self):
        """Record a latency spike"""
        with self._lock:
            self.spikes_in_window += 1
            self.last_issue_time = time.time()
            self._evaluate_mode()

    def record_disconnect(self):
        """Record a disconnect event"""
        with self._lock:
            self._set_mode(OperatingMode.OFFLINE)

    def record_reconnect(self):
        """Record a reconnect event"""
        with self._lock:
            # Start in DEGRADED after reconnect, will recover to NORMAL if stable
            if self.current_mode == OperatingMode.OFFLINE:
                self._set_mode(OperatingMode.DEGRADED)

    def check_recovery(self):
        """Check if system has recovered and can return to normal mode"""
        with self._lock:
            if self.current_mode == OperatingMode.NORMAL:
                return  # Already normal

            if self.current_mode == OperatingMode.OFFLINE:
                return  # Can't recover without reconnect

            if self.last_issue_time is None:
                return  # No issues recorded

            elapsed = time.time() - self.last_issue_time
            if elapsed >= self.recovery_window_sec:
                # No issues for recovery window - recover
                self.errors_in_window = 0
                self.spikes_in_window = 0
                self._set_mode(OperatingMode.NORMAL)

    def _evaluate_mode(self):
        """Evaluate current conditions and set appropriate mode"""
        if self.current_mode == OperatingMode.OFFLINE:
            return  # Stay offline until reconnect

        # Check for MINIMAL conditions (severe)
        if self.errors_in_window >= self.error_threshold * 2:
            self._set_mode(OperatingMode.MINIMAL)
            return

        # Check for DEGRADED conditions
        if (self.errors_in_window >= self.error_threshold or
            self.spikes_in_window >= self.spike_threshold):
            self._set_mode(OperatingMode.DEGRADED)
            return

    def _set_mode(self, new_mode: str):
        """Set operating mode with history tracking"""
        if new_mode == self.current_mode:
            return

        old_mode = self.current_mode
        self.current_mode = new_mode

        # Record in history
        self.mode_history.append({
            'from': old_mode,
            'to': new_mode,
            'timestamp': time.time(),
            'errors': self.errors_in_window,
            'spikes': self.spikes_in_window
        })

        # Track degradation start
        if new_mode != OperatingMode.NORMAL and old_mode == OperatingMode.NORMAL:
            self.degradation_start_time = time.time()
        elif new_mode == OperatingMode.NORMAL:
            self.degradation_start_time = None

        # Call callback if set
        if self.on_mode_change:
            try:
                self.on_mode_change(old_mode, new_mode)
            except Exception:
                pass  # Don't let callback errors affect degradation logic

    def should_skip_non_critical(self) -> bool:
        """Check if non-critical processing should be skipped"""
        return self.current_mode in [OperatingMode.DEGRADED, OperatingMode.MINIMAL]

    def should_buffer_aggressively(self) -> bool:
        """Check if aggressive buffering is needed"""
        return self.current_mode == OperatingMode.MINIMAL

    def get_status(self) -> Dict[str, Any]:
        """Get current degradation status"""
        with self._lock:
            degradation_duration = None
            if self.degradation_start_time:
                degradation_duration = time.time() - self.degradation_start_time

            return {
                'mode': self.current_mode,
                'errors_in_window': self.errors_in_window,
                'spikes_in_window': self.spikes_in_window,
                'last_issue_time': self.last_issue_time,
                'degradation_duration_sec': degradation_duration,
                'recent_transitions': list(self.mode_history)[-5:]
            }
