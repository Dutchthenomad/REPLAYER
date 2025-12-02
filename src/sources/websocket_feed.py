"""
Real-Time WebSocket Feed for Rugs.fun

Python port of the Socket.IO real-time collector.
Provides noise-free, tick-by-tick game state updates.

Usage:
    feed = WebSocketFeed()
    feed.connect()

    # Get latest signal
    signal = feed.get_last_signal()
    print(f"Price: {signal['price']:.4f}x")

    # Or use callbacks
    @feed.on('signal')
    def handle_signal(signal):
        print(f"Tick {signal['tickCount']}: {signal['price']:.4f}x")
"""

import socketio
import time
import threading
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import logging
from decimal import Decimal
from collections import deque  # AUDIT FIX: For efficient latency tracking

# REPLAYER imports
from models import GameTick


class LatencySpikeDetector:
    """
    Detects latency spikes in WebSocket signal delivery.

    PHASE 3.5 AUDIT FIX: Alerts when latency exceeds threshold.

    Uses rolling statistics to detect anomalous latency values.

    NOTE: Thresholds significantly relaxed (2025-12-01) to prevent spam.
    Normal network jitter of 100-300ms is NOT a spike.
    Only truly severe latency (>10 seconds) should trigger alerts.
    """

    def __init__(
        self,
        window_size: int = 100,
        spike_threshold_std: float = 10.0,  # Relaxed from 2.0 - only extreme outliers
        absolute_threshold_ms: float = 10000.0  # Relaxed from 2000ms to 10 seconds
    ):
        """
        Initialize spike detector.

        Args:
            window_size: Number of samples for rolling statistics
            spike_threshold_std: Standard deviations above mean to trigger spike
            absolute_threshold_ms: Absolute threshold (ms) that always triggers spike
        """
        self.window_size = window_size
        self.spike_threshold_std = spike_threshold_std
        self.absolute_threshold_ms = absolute_threshold_ms

        self.latencies: deque = deque(maxlen=window_size)
        self._lock = threading.Lock()

        # Statistics
        self.total_samples = 0
        self.total_spikes = 0
        self.last_spike_time: Optional[float] = None
        self.last_spike_value: Optional[float] = None

        # Rate limiting for warnings (prevent spam)
        self._last_warning_time: float = 0
        self._warning_cooldown_sec: float = 30.0  # Only warn once per 30 seconds

    def record(self, latency_ms: float) -> Optional[Dict[str, Any]]:
        """
        Record a latency sample and check for spike.

        Args:
            latency_ms: Latency in milliseconds

        Returns:
            Spike info dict if spike detected, None otherwise
        """
        with self._lock:
            self.latencies.append(latency_ms)
            self.total_samples += 1

            # Need minimum samples for statistics
            if len(self.latencies) < 10:
                return None

            # Calculate rolling statistics
            mean = sum(self.latencies) / len(self.latencies)
            variance = sum((x - mean) ** 2 for x in self.latencies) / len(self.latencies)
            std = variance ** 0.5 if variance > 0 else 0

            # Check for spike
            is_spike = False
            spike_reason = None

            # Check absolute threshold
            if latency_ms > self.absolute_threshold_ms:
                is_spike = True
                spike_reason = f"Absolute threshold exceeded: {latency_ms:.0f}ms > {self.absolute_threshold_ms:.0f}ms"

            # Check standard deviation threshold
            elif std > 0:
                z_score = (latency_ms - mean) / std
                if z_score > self.spike_threshold_std:
                    is_spike = True
                    spike_reason = f"Statistical spike: {z_score:.1f} std devs above mean ({mean:.0f}ms)"

            if is_spike:
                self.total_spikes += 1
                self.last_spike_time = time.time()
                self.last_spike_value = latency_ms

                # Rate limit: only return spike info if cooldown has passed
                # This prevents warning spam while still tracking statistics
                now = time.time()
                if now - self._last_warning_time >= self._warning_cooldown_sec:
                    self._last_warning_time = now
                    return {
                        'latency_ms': latency_ms,
                        'mean_ms': mean,
                        'std_ms': std,
                        'reason': spike_reason,
                        'spike_count': self.total_spikes,
                        'timestamp': self.last_spike_time
                    }
                # Spike detected but suppressed due to rate limiting
                return None

            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get spike detector statistics"""
        with self._lock:
            if self.latencies:
                mean = sum(self.latencies) / len(self.latencies)
                max_lat = max(self.latencies)
                min_lat = min(self.latencies)
            else:
                mean = max_lat = min_lat = 0

            return {
                'total_samples': self.total_samples,
                'total_spikes': self.total_spikes,
                'spike_rate': (self.total_spikes / self.total_samples * 100)
                    if self.total_samples > 0 else 0.0,
                'mean_latency_ms': mean,
                'max_latency_ms': max_lat,
                'min_latency_ms': min_lat,
                'last_spike_time': self.last_spike_time,
                'last_spike_value_ms': self.last_spike_value
            }


class ConnectionHealth:
    """
    Connection health status enum.

    PHASE 3.2 AUDIT FIX: Track connection quality.
    """
    HEALTHY = "HEALTHY"          # Connected, receiving signals
    DEGRADED = "DEGRADED"        # Connected but high latency/drops
    STALE = "STALE"              # Connected but no recent signals
    DISCONNECTED = "DISCONNECTED"  # Not connected
    UNKNOWN = "UNKNOWN"          # Initial state


class ConnectionHealthMonitor:
    """
    Monitors WebSocket connection health.

    PHASE 3.2 AUDIT FIX: Detects connection issues before they cause problems.

    Metrics tracked:
    - Time since last signal
    - Average latency
    - Error rate
    - Drop rate
    """

    def __init__(
        self,
        stale_threshold_sec: float = 10.0,
        latency_threshold_ms: float = 1000.0,
        error_rate_threshold: float = 5.0
    ):
        """
        Initialize health monitor.

        Args:
            stale_threshold_sec: Seconds without signal before STALE
            latency_threshold_ms: Avg latency (ms) threshold for DEGRADED
            error_rate_threshold: Error rate (%) threshold for DEGRADED
        """
        self.stale_threshold_sec = stale_threshold_sec
        self.latency_threshold_ms = latency_threshold_ms
        self.error_rate_threshold = error_rate_threshold

        self.last_signal_time: Optional[float] = None
        self.is_connected = False
        self._lock = threading.Lock()

    def record_signal(self):
        """Record that a signal was received"""
        with self._lock:
            self.last_signal_time = time.time()

    def set_connected(self, connected: bool):
        """Update connection state"""
        with self._lock:
            self.is_connected = connected
            if connected:
                self.last_signal_time = time.time()

    def get_signal_age(self) -> Optional[float]:
        """Get seconds since last signal, or None if never received"""
        with self._lock:
            if self.last_signal_time is None:
                return None
            return time.time() - self.last_signal_time

    def check_health(
        self,
        avg_latency_ms: float = 0.0,
        error_rate: float = 0.0,
        drop_rate: float = 0.0
    ) -> Dict[str, Any]:
        """
        Check connection health status.

        Args:
            avg_latency_ms: Average latency in milliseconds
            error_rate: Error rate percentage
            drop_rate: Drop rate percentage (from rate limiter)

        Returns:
            Dict with status, issues list, and metrics
        """
        with self._lock:
            issues = []
            status = ConnectionHealth.UNKNOWN

            # Check connection
            if not self.is_connected:
                return {
                    'status': ConnectionHealth.DISCONNECTED,
                    'issues': ['Not connected to server'],
                    'signal_age_sec': None,
                    'avg_latency_ms': avg_latency_ms,
                    'error_rate': error_rate,
                    'drop_rate': drop_rate
                }

            # Check signal freshness
            signal_age = None
            if self.last_signal_time:
                signal_age = time.time() - self.last_signal_time

                if signal_age > self.stale_threshold_sec:
                    issues.append(f'No signals for {signal_age:.1f}s')
                    status = ConnectionHealth.STALE

            # Check latency
            if avg_latency_ms > self.latency_threshold_ms:
                issues.append(f'High latency: {avg_latency_ms:.0f}ms')
                if status != ConnectionHealth.STALE:
                    status = ConnectionHealth.DEGRADED

            # Check error rate
            if error_rate > self.error_rate_threshold:
                issues.append(f'High error rate: {error_rate:.1f}%')
                if status != ConnectionHealth.STALE:
                    status = ConnectionHealth.DEGRADED

            # Check drop rate
            if drop_rate > 10.0:  # More than 10% drops
                issues.append(f'High drop rate: {drop_rate:.1f}%')
                if status != ConnectionHealth.STALE:
                    status = ConnectionHealth.DEGRADED

            # If no issues, we're healthy
            if not issues:
                status = ConnectionHealth.HEALTHY

            return {
                'status': status,
                'issues': issues,
                'signal_age_sec': signal_age,
                'avg_latency_ms': avg_latency_ms,
                'error_rate': error_rate,
                'drop_rate': drop_rate
            }


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


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for WebSocket flood protection.

    PHASE 3.1 AUDIT FIX: Prevents data floods from overwhelming the system.

    Args:
        rate: Maximum tokens per second (signals/sec)
        burst: Maximum burst capacity (default: 2x rate)
    """

    def __init__(self, rate: float = 20.0, burst: int = None):
        self.rate = rate
        self.burst = burst if burst is not None else int(rate * 2)
        self.tokens = float(self.burst)
        self.last_update = time.time()
        self._lock = threading.Lock()

        # Statistics
        self.total_requests = 0
        self.total_allowed = 0
        self.total_dropped = 0

    def acquire(self) -> bool:
        """
        Attempt to acquire a token.

        Returns:
            True if token acquired (request allowed), False if rate limited
        """
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now

            # Refill tokens based on elapsed time
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)

            self.total_requests += 1

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                self.total_allowed += 1
                return True
            else:
                self.total_dropped += 1
                return False

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        with self._lock:
            return {
                'rate': self.rate,
                'burst': self.burst,
                'tokens_available': self.tokens,
                'total_requests': self.total_requests,
                'total_allowed': self.total_allowed,
                'total_dropped': self.total_dropped,
                'drop_rate': (self.total_dropped / self.total_requests * 100)
                    if self.total_requests > 0 else 0.0
            }

# Phase 3 refactoring: GameSignal and GameStateMachine extracted to own module
from sources.game_state_machine import GameSignal, GameStateMachine


class WebSocketFeed:
    """Real-time WebSocket feed for Rugs.fun game state"""

    def __init__(self, log_level: str = 'INFO', rate_limit: float = 20.0):
        """
        Initialize WebSocket feed

        Args:
            log_level: Logging level (DEBUG, INFO, WARN, ERROR)
            rate_limit: Max signals per second (PHASE 3.1 AUDIT FIX)
        """
        self.server_url = 'https://backend.rugs.fun?frontend-version=1.0'

        # AUDIT FIX: Configure Socket.IO with heartbeat and reconnection
        self.sio = socketio.Client(
            logger=False,
            engineio_logger=False,
            reconnection=True,              # Enable automatic reconnection
            reconnection_attempts=10,       # Max 10 reconnection attempts
            reconnection_delay=1,           # Start with 1s delay
            reconnection_delay_max=10,      # Max 10s delay (exponential backoff)
        )
        self.state_machine = GameStateMachine()

        # PHASE 3.1 AUDIT FIX: Rate limiter to prevent data floods
        self.rate_limiter = TokenBucketRateLimiter(rate=rate_limit)

        # PHASE 3.2 AUDIT FIX: Connection health monitor
        self.health_monitor = ConnectionHealthMonitor()

        # PHASE 3.5 AUDIT FIX: Latency spike detector
        self.spike_detector = LatencySpikeDetector()

        # PHASE 3.6 AUDIT FIX: Graceful degradation manager
        self.degradation_manager = GracefulDegradationManager()
        self.degradation_manager.on_mode_change = self._on_mode_change

        # Metrics
        self.metrics = {
            'start_time': time.time(),
            'total_signals': 0,
            'total_ticks': 0,
            'total_games': 0,
            'noise_filtered': 0,
            'latencies': deque(maxlen=100),  # AUDIT FIX: O(1) operations, auto-evicts oldest
            'phase_transitions': 0,
            'anomalies': 0,
            'errors': 0,  # AUDIT FIX: Track callback errors
            'rate_limited': 0,  # PHASE 3.1: Track rate-limited signals
            'latency_spikes': 0  # PHASE 3.5: Track latency spikes
        }

        # State
        self.last_signal: Optional[GameSignal] = None
        self.last_tick_time = None
        self.is_connected = False
        self.event_handlers = {}

        # AUDIT FIX: Guard to prevent duplicate event listener registration
        self._listeners_setup = False

        # Setup logging
        self.logger = logging.getLogger('WebSocketFeed')
        self.logger.setLevel(getattr(logging, log_level.upper()))
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Setup Socket.IO event handlers
        self._setup_event_listeners()

    def _on_mode_change(self, old_mode: str, new_mode: str):
        """
        PHASE 3.6: Handle operating mode changes.

        Args:
            old_mode: Previous operating mode
            new_mode: New operating mode
        """
        self.logger.warning(f'🔄 Operating mode changed: {old_mode} → {new_mode}')
        self._emit_event('mode_change', {
            'old_mode': old_mode,
            'new_mode': new_mode,
            'status': self.degradation_manager.get_status()
        })

    def _setup_event_listeners(self):
        """
        Setup Socket.IO event listeners

        AUDIT FIX: Guard against duplicate event listener registration.
        If called multiple times (e.g., on reconnect), this prevents
        handler accumulation and memory leaks.
        """
        # AUDIT FIX: Prevent duplicate event listener registration
        if self._listeners_setup:
            self.logger.debug("Event listeners already set up, skipping duplicate registration")
            return

        self._listeners_setup = True

        @self.sio.event
        def connect():
            # AUDIT FIX: Error boundary for connection handler
            try:
                self.is_connected = True
                # PHASE 3.2: Update health monitor
                self.health_monitor.set_connected(True)
                self.logger.info('✅ Connected to Rugs.fun backend')
                self.logger.info(f'   Socket ID: {self.sio.sid}')
                self._emit_event('connected', {'socketId': self.sio.sid})
            except Exception as e:
                self.logger.error(f"Error in connect handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        @self.sio.event
        def disconnect(reason=None):
            # AUDIT FIX: Error boundary for disconnect handler
            # FIX 2025-12-01: Accept optional reason argument (newer Socket.IO versions pass it)
            try:
                self.is_connected = False
                # PHASE 3.2: Update health monitor
                self.health_monitor.set_connected(False)
                # PHASE 3.4: Initiate state machine recovery
                recovery_info = self.state_machine.recover_from_disconnect()
                # PHASE 3.6: Notify degradation manager
                self.degradation_manager.record_disconnect()
                # FIX: Reset latency baseline to prevent spike spam on reconnect
                self.last_tick_time = None
                self.spike_detector.latencies.clear()
                self.spike_detector.total_samples = 0
                reason_str = f' (reason: {reason})' if reason else ''
                self.logger.warning(f'❌ Disconnected from backend{reason_str}')
                self._emit_event('disconnected', {'recovery_info': recovery_info, 'reason': reason})
                # AUDIT FIX: Clear handlers on disconnect to prevent memory leaks
                # Note: Don't clear Socket.IO internal handlers, only our custom handlers
                # self.clear_handlers()  # Commented out - handlers are intentionally persistent
            except Exception as e:
                self.logger.error(f"Error in disconnect handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        @self.sio.event
        def connect_error(data):
            # AUDIT FIX: Error boundary for connect_error handler
            try:
                self.logger.error(f'🚨 Connection error: {data}')
                self._emit_event('error', {'message': str(data), 'type': 'connect_error'})
            except Exception as e:
                self.logger.error(f"Error in connect_error handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        # AUDIT FIX: Add reconnection event handlers
        @self.sio.event
        def reconnect():
            """Handle successful reconnection"""
            try:
                self.is_connected = True
                # PHASE 3.2: Update health monitor
                self.health_monitor.set_connected(True)
                # PHASE 3.4: Log state machine recovery status
                state_summary = self.state_machine.get_state_summary()
                # PHASE 3.6: Notify degradation manager
                self.degradation_manager.record_reconnect()
                # FIX: Reset latency baseline to prevent spike spam after reconnect
                self.last_tick_time = None
                self.spike_detector.latencies.clear()
                self.spike_detector.total_samples = 0
                self.logger.info('🔄 Reconnected to Rugs.fun backend')
                self.logger.info(f'   State machine: phase={state_summary["phase"]}, game={state_summary["game_id"]}')
                self._emit_event('reconnected', {
                    'socketId': self.sio.sid,
                    'state_summary': state_summary
                })
            except Exception as e:
                self.logger.error(f"Error in reconnect handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        @self.sio.event
        def reconnect_attempt(attempt_number):
            """Handle reconnection attempt"""
            try:
                self.logger.warning(f'⏳ Reconnection attempt #{attempt_number}...')
                self._emit_event('reconnect_attempt', {'attempt': attempt_number})
            except Exception as e:
                self.logger.error(f"Error in reconnect_attempt handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        @self.sio.event
        def reconnect_failed():
            """Handle reconnection failure (all attempts exhausted)"""
            try:
                self.logger.error('❌ Reconnection failed - all attempts exhausted')
                self._emit_event('reconnect_failed', {})
            except Exception as e:
                self.logger.error(f"Error in reconnect_failed handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        @self.sio.on('gameStateUpdate')
        def on_game_state_update(data):
            # AUDIT FIX: Critical error boundary - prevents connection death
            try:
                self._handle_game_state_update(data)
            except Exception as e:
                self.logger.error(f"Error handling game state update: {e}", exc_info=True)
                self.metrics['errors'] += 1

        # Catch-all for noise tracking
        @self.sio.on('*')
        def catch_all(event, *args):
            # AUDIT FIX: Error boundary for catch-all handler
            try:
                if event != 'gameStateUpdate':
                    self.metrics['noise_filtered'] += 1
                    self.logger.debug(f'❌ NOISE filtered: {event}')
            except Exception as e:
                self.logger.error(f"Error in catch_all handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

    def _handle_game_state_update(self, raw_data: Dict[str, Any]):
        """Handle gameStateUpdate event - PRIMARY SIGNAL SOURCE"""
        receive_time = time.time() * 1000  # milliseconds

        # PHASE 3.1 AUDIT FIX: Apply rate limiting
        if not self.rate_limiter.acquire():
            self.metrics['rate_limited'] += 1
            # Log every 100th rate-limited signal to avoid log spam
            if self.metrics['rate_limited'] % 100 == 1:
                self.logger.warning(
                    f"Rate limiting active: {self.metrics['rate_limited']} signals dropped "
                    f"(drop rate: {self.rate_limiter.get_stats()['drop_rate']:.1f}%)"
                )
            return  # Drop this signal

        # Calculate tick interval
        if self.last_tick_time:
            tick_interval = receive_time - self.last_tick_time

            # FIX: Reset baseline if gap exceeds threshold (5 seconds)
            # This prevents cumulative latency spam after processing pauses
            # (e.g., when browser connection blocks the handler thread)
            MAX_REASONABLE_GAP_MS = 5000.0  # 5 seconds
            if tick_interval > MAX_REASONABLE_GAP_MS:
                self.logger.info(
                    f"⏭️ Large gap detected ({tick_interval:.0f}ms), resetting latency baseline"
                )
                # Reset spike detector's baseline by clearing its history
                self.spike_detector.latencies.clear()
                self.spike_detector.total_samples = 0
                # Don't record this anomalous interval
                self.last_tick_time = receive_time
                # Continue processing the signal but skip latency recording
            else:
                # Normal case: record the tick interval
                # AUDIT FIX: deque auto-evicts oldest when maxlen exceeded (O(1) operation)
                self.metrics['latencies'].append(tick_interval)

                # PHASE 3.5: Check for latency spike
                spike_info = self.spike_detector.record(tick_interval)
                if spike_info:
                    self.metrics['latency_spikes'] += 1
                    self.logger.warning(f"⚠️ Latency spike detected: {spike_info['reason']}")
                    # PHASE 3.6: Notify degradation manager
                    self.degradation_manager.record_spike()
                    self._emit_event('latency_spike', spike_info)
        self.last_tick_time = receive_time

        # PHASE 3.2: Record signal reception for health monitoring
        self.health_monitor.record_signal()

        # PHASE 3.6: Check for recovery from degraded state
        self.degradation_manager.check_recovery()

        # Extract signal (9 fields only)
        signal_dict = self._extract_signal(raw_data)

        # Validate with state machine
        validation = self.state_machine.process(raw_data)

        # Add metadata
        signal_dict['phase'] = validation['phase']
        signal_dict['isValid'] = validation['isValid']
        signal_dict['timestamp'] = int(receive_time)
        signal_dict['latency'] = time.time() * 1000 - receive_time

        # Create signal object
        signal = GameSignal(**signal_dict)

        # Update metrics
        self.metrics['total_signals'] += 1
        self.metrics['total_ticks'] += 1

        if validation['phase'] != validation['previousPhase']:
            self.metrics['phase_transitions'] += 1
            self.logger.info(f"🔄 {validation['previousPhase']} → {validation['phase']}")

        if not validation['isValid']:
            self.metrics['anomalies'] += 1

        # Store last signal
        self.last_signal = signal

        # Broadcast signal
        self._broadcast_signal(signal, validation)

    def _extract_signal(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract ONLY the 9 signal fields from raw gameStateUpdate"""
        # AUDIT FIX: Convert price to Decimal for financial precision
        raw_price = raw_data.get('price', 1.0)
        price = Decimal(str(raw_price)) if raw_price is not None else Decimal('1.0')

        return {
            'gameId': raw_data.get('gameId', ''),
            'active': raw_data.get('active', False),
            'rugged': raw_data.get('rugged', False),
            'tickCount': raw_data.get('tickCount', 0),
            'price': price,  # AUDIT FIX: Now Decimal, not float
            'cooldownTimer': raw_data.get('cooldownTimer', 0),
            'allowPreRoundBuys': raw_data.get('allowPreRoundBuys', False),
            'tradeCount': raw_data.get('tradeCount', 0),
            'gameHistory': raw_data.get('gameHistory')
        }

    def _broadcast_signal(self, signal: GameSignal, validation: Dict[str, Any]):
        """Broadcast clean signal to consumers"""
        # Emit 'signal' event
        self._emit_event('signal', signal)

        # Emit phase-specific events
        self._emit_event(f'phase:{signal.phase}', signal)

        # Emit tick event during active gameplay
        if signal.phase == 'ACTIVE_GAMEPLAY':
            self._emit_event('tick', {
                'gameId': signal.gameId,
                'tickCount': signal.tickCount,
                'price': signal.price,
                'timestamp': signal.timestamp
            })

        # Detect game completion (AUDIT FIX: only emit on RUG_EVENT_1 to prevent duplicates)
        if signal.phase == 'RUG_EVENT_1':
            self._handle_game_complete(signal)

    def _handle_game_complete(self, signal: GameSignal):
        """Handle game completion"""
        self.metrics['total_games'] += 1

        # Extract seed data if available
        seed_data = None
        if signal.gameHistory and len(signal.gameHistory) > 0:
            completed_game = signal.gameHistory[0]
            provably_fair = completed_game.get('provablyFair', {})
            seed_data = {
                'gameId': completed_game.get('id'),
                'serverSeed': provably_fair.get('serverSeed'),
                'serverSeedHash': provably_fair.get('serverSeedHash'),
                'peakMultiplier': completed_game.get('peakMultiplier'),
                'finalTick': len(completed_game.get('prices', [])) or signal.tickCount
            }

        self.logger.info('💥 GAME COMPLETE')
        if seed_data:
            self.logger.info(f"   Game ID: {seed_data['gameId']}")
            self.logger.info(f"   Peak: {seed_data['peakMultiplier']:.2f}x")

        self._emit_event('gameComplete', {
            'signal': signal,
            'seedData': seed_data,
            'gameNumber': self.metrics['total_games']
        })

    def _emit_event(self, event_name: str, data: Any):
        """Emit event to registered handlers"""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    handler(data)
                except Exception as e:
                    self.logger.error(f"Error in event handler for '{event_name}': {e}")

    def on(self, event_name: str, handler: Callable = None):
        """
        Register event handler (decorator or function)

        Usage:
            @feed.on('signal')
            def handle_signal(signal):
                print(signal.price)

            # OR

            def handler(signal):
                print(signal.price)
            feed.on('signal', handler)
        """
        def decorator(func):
            if event_name not in self.event_handlers:
                self.event_handlers[event_name] = []
            self.event_handlers[event_name].append(func)
            return func

        if handler is None:
            return decorator
        else:
            return decorator(handler)

    def remove_handler(self, event_name: str, handler: Callable):
        """
        Remove a specific event handler (AUDIT FIX: Prevent memory leaks)

        Args:
            event_name: Event to remove handler from
            handler: Handler function to remove
        """
        if event_name in self.event_handlers:
            try:
                self.event_handlers[event_name].remove(handler)
                # Remove empty lists to free memory
                if not self.event_handlers[event_name]:
                    del self.event_handlers[event_name]
            except ValueError:
                # Handler not found, silently ignore
                pass

    def clear_handlers(self, event_name: str = None):
        """
        Clear event handlers (AUDIT FIX: Prevent memory leaks on reconnect)

        Args:
            event_name: Specific event to clear, or None to clear all
        """
        if event_name:
            if event_name in self.event_handlers:
                self.event_handlers[event_name] = []
                del self.event_handlers[event_name]
        else:
            # Clear all handlers
            self.event_handlers.clear()
            self.logger.debug("Cleared all event handlers")

    def connect(self):
        """Connect to Rugs.fun backend"""
        self.logger.info('🔌 Connecting to Rugs.fun backend...')
        self.logger.info(f'   Server: {self.server_url}')
        self.logger.info('   Mode: READ-ONLY (0% noise, 9 signal fields only)')

        try:
            self.sio.connect(
                self.server_url,
                transports=['websocket', 'polling'],
                wait_timeout=20
            )
        except Exception as e:
            self.logger.error(f'🚨 Connection failed: {e}')
            raise

    def disconnect(self):
        """Disconnect from backend"""
        self.logger.info('🔌 Disconnecting...')
        self.sio.disconnect()
        self.print_metrics()

    def get_last_signal(self) -> Optional[GameSignal]:
        """Get the last received signal"""
        return self.last_signal

    def signal_to_game_tick(self, signal: GameSignal) -> GameTick:
        """
        Convert GameSignal to REPLAYER GameTick model

        Args:
            signal: GameSignal from WebSocket feed

        Returns:
            GameTick compatible with REPLAYER models
        """
        return GameTick(
            game_id=signal.gameId,
            tick=signal.tickCount,
            timestamp=datetime.fromtimestamp(signal.timestamp / 1000).isoformat(),
            price=signal.price,  # AUDIT FIX: Already Decimal, no conversion needed
            phase=signal.phase,
            active=signal.active,
            rugged=signal.rugged,
            cooldown_timer=signal.cooldownTimer,
            trade_count=signal.tradeCount
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics summary"""
        uptime = time.time() - self.metrics['start_time']

        avg_latency = (
            sum(self.metrics['latencies']) / len(self.metrics['latencies'])
            if self.metrics['latencies'] else 0
        )

        # PHASE 3.1: Include rate limiter stats
        rate_stats = self.rate_limiter.get_stats()

        return {
            'uptime': f'{uptime:.1f}s',
            'totalSignals': self.metrics['total_signals'],
            'totalTicks': self.metrics['total_ticks'],
            'totalGames': self.metrics['total_games'],
            'noiseFiltered': self.metrics['noise_filtered'],
            'phaseTransitions': self.metrics['phase_transitions'],
            'anomalies': self.metrics['anomalies'],
            'avgLatency': f'{avg_latency:.2f}ms',
            'signalsPerSecond': f'{self.metrics["total_signals"] / uptime:.2f}' if uptime > 0 else '0',
            'currentPhase': self.state_machine.current_phase,
            'currentGameId': self.state_machine.current_game_id or 'N/A',
            'lastPrice': f'{self.last_signal.price:.4f}x' if self.last_signal else 'N/A',
            # PHASE 3.1: Rate limiting stats
            'rateLimited': self.metrics['rate_limited'],
            'rateLimitDropRate': f'{rate_stats["drop_rate"]:.1f}%',
            'errors': self.metrics['errors']
        }

    def get_health(self) -> Dict[str, Any]:
        """
        Get connection health status.

        PHASE 3.2 AUDIT FIX: Provides health check for monitoring.

        Returns:
            Dict with status, issues, and health metrics
        """
        # Calculate metrics for health check
        avg_latency = (
            sum(self.metrics['latencies']) / len(self.metrics['latencies'])
            if self.metrics['latencies'] else 0
        )

        total_signals = self.metrics['total_signals']
        error_rate = (
            (self.metrics['errors'] / total_signals * 100)
            if total_signals > 0 else 0.0
        )

        rate_stats = self.rate_limiter.get_stats()
        drop_rate = rate_stats['drop_rate']

        return self.health_monitor.check_health(
            avg_latency_ms=avg_latency,
            error_rate=error_rate,
            drop_rate=drop_rate
        )

    def is_healthy(self) -> bool:
        """
        Quick health check.

        PHASE 3.2 AUDIT FIX: Simple boolean for health checks.

        Returns:
            True if connection is healthy
        """
        health = self.get_health()
        return health['status'] == ConnectionHealth.HEALTHY

    def get_operating_mode(self) -> str:
        """
        Get current operating mode.

        PHASE 3.6 AUDIT FIX: Returns current degradation state.

        Returns:
            Operating mode string (NORMAL, DEGRADED, MINIMAL, OFFLINE)
        """
        return self.degradation_manager.current_mode

    def get_degradation_status(self) -> Dict[str, Any]:
        """
        Get full degradation status.

        PHASE 3.6 AUDIT FIX: Provides detailed degradation info.

        Returns:
            Dict with mode, error counts, and history
        """
        return self.degradation_manager.get_status()

    def print_metrics(self):
        """Print metrics summary"""
        metrics = self.get_metrics()

        print('')
        print('━' * 50)
        print('📊 WEBSOCKET FEED METRICS')
        print('━' * 50)
        print(f'   Uptime: {metrics["uptime"]}')
        print(f'   Total Signals: {metrics["totalSignals"]}')
        print(f'   Total Ticks: {metrics["totalTicks"]}')
        print(f'   Total Games: {metrics["totalGames"]}')
        print(f'   Noise Filtered: {metrics["noiseFiltered"]}')
        print('')
        print('   Performance:')
        print(f'     Avg Latency: {metrics["avgLatency"]}')
        print(f'     Signals/sec: {metrics["signalsPerSecond"]}')
        print('')
        print('   Validation:')
        print(f'     Phase Transitions: {metrics["phaseTransitions"]}')
        print(f'     Anomalies: {metrics["anomalies"]}')
        print('')
        print('   Current State:')
        print(f'     Phase: {metrics["currentPhase"]}')
        print(f'     Game: {metrics["currentGameId"]}')
        print(f'     Price: {metrics["lastPrice"]}')
        print('━' * 50)

    def wait(self):
        """Wait for Socket.IO events (blocking)"""
        try:
            self.sio.wait()
        except KeyboardInterrupt:
            self.logger.info('')
            self.logger.info('🛑 Shutting down gracefully...')
            self.disconnect()
