"""
Feed Monitors - Phase 10.4A Modular Refactor

Extracted from websocket_feed.py:
- LatencySpikeDetector: Detects latency spikes in WebSocket signal delivery
- ConnectionHealth: Connection health status enum
- ConnectionHealthMonitor: Monitors WebSocket connection health

These classes handle health monitoring and latency tracking for the
WebSocket feed without containing any Socket.IO-specific code.
"""

import time
import threading
from typing import Dict, Any, Optional
from collections import deque
import logging

logger = logging.getLogger(__name__)


class LatencySpikeDetector:
    """
    Detects latency spikes in WebSocket signal delivery.

    PHASE 3.5 AUDIT FIX: Alerts when latency exceeds threshold.

    Uses rolling statistics to detect anomalous latency values.

    NOTE: Thresholds significantly relaxed (2025-12-01) to prevent spam.
    Normal network jitter of 100-300ms is NOT a spike.
    Only truly severe latency (>10 seconds) should trigger alerts.
    """

    WARNING_THRESHOLD_MS = 2000.0   # 2 seconds - warning
    ERROR_THRESHOLD_MS = 5000.0     # 5 seconds - error
    CRITICAL_THRESHOLD_MS = 10000.0  # 10 seconds - critical

    def __init__(
        self,
        window_size: int = 100,
        spike_threshold_std: float = 10.0,
        absolute_threshold_ms: float = CRITICAL_THRESHOLD_MS
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

            # Calculate rolling statistics when enough samples
            mean = 0.0
            std = 0.0
            if len(self.latencies) >= 10:
                mean = sum(self.latencies) / len(self.latencies)
                variance = sum((x - mean) ** 2 for x in self.latencies) / len(self.latencies)
                std = variance ** 0.5 if variance > 0 else 0

            status = self.check_latency(latency_ms)
            is_spike = status != 'OK'
            spike_reason = None

            # Absolute threshold check
            if latency_ms >= self.absolute_threshold_ms:
                is_spike = True
                spike_reason = f"Absolute threshold exceeded: {latency_ms:.0f}ms"

            # Statistical spike check (requires variance)
            elif std > 0:
                z_score = (latency_ms - mean) / std
                if z_score > self.spike_threshold_std:
                    is_spike = True
                    spike_reason = f"Statistical spike: {z_score:.1f} std devs above mean ({mean:.0f}ms)"

            if is_spike:
                self.total_spikes += 1
                self.last_spike_time = time.time()
                self.last_spike_value = latency_ms
                spike_status = status if status != 'OK' else 'WARNING'
                return self._maybe_emit_status(latency_ms, spike_status, spike_reason, mean, std)

            return None

    def check_latency(self, latency_ms: float) -> str:
        """Tiered latency threshold evaluation"""
        if latency_ms >= self.absolute_threshold_ms:
            logger.critical(f"CRITICAL latency: {latency_ms}ms")
            return 'CRITICAL'
        if latency_ms >= self.ERROR_THRESHOLD_MS:
            logger.error(f"High latency: {latency_ms}ms")
            return 'ERROR'
        if latency_ms >= self.WARNING_THRESHOLD_MS:
            logger.warning(f"Elevated latency: {latency_ms}ms")
            return 'WARNING'
        return 'OK'

    def _maybe_emit_status(
        self,
        latency_ms: float,
        status: str,
        reason: Optional[str] = None,
        mean: float = 0.0,
        std: float = 0.0
    ) -> Optional[Dict[str, Any]]:
        """Rate-limit status emission"""
        if status == 'OK':
            return None
        now = time.time()
        if now - self._last_warning_time < self._warning_cooldown_sec:
            return None

        self._last_warning_time = now
        return {
            'latency_ms': latency_ms,
            'mean_ms': mean,
            'std_ms': std,
            'reason': reason or status,
            'spike_count': self.total_spikes,
            'timestamp': self.last_spike_time or now,
            'status': status,
        }

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
