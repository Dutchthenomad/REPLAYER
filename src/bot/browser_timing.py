"""
Browser Timing Metrics

Tracks execution timing for browser automation actions.
Extracted from browser_executor.py during Phase 1 refactoring.

Classes:
    ExecutionTiming: Timing metrics for a single action execution
    TimingMetrics: Aggregated timing metrics for bot performance tracking
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class ExecutionTiming:
    """
    Timing metrics for a single action execution

    Phase 8.6: Tracks realistic execution delays for BUY/SELL/SIDEBET actions.

    Attributes:
        action: Action type (BUY, SELL, SIDEBET)
        decision_time: Timestamp when bot decided to act
        click_time: Timestamp when click was sent to browser
        confirmation_time: Timestamp when state change was confirmed
        success: Whether the execution succeeded
    """
    action: str  # BUY, SELL, SIDEBET
    decision_time: float  # When bot decided to act
    click_time: float  # When click was sent
    confirmation_time: float  # When state change confirmed
    success: bool  # Whether execution succeeded

    @property
    def decision_to_click_ms(self) -> float:
        """Time from decision to click (milliseconds)"""
        return (self.click_time - self.decision_time) * 1000

    @property
    def click_to_confirmation_ms(self) -> float:
        """Time from click to confirmation (milliseconds)"""
        return (self.confirmation_time - self.click_time) * 1000

    @property
    def total_delay_ms(self) -> float:
        """Total execution delay (milliseconds)"""
        return (self.confirmation_time - self.decision_time) * 1000


@dataclass
class TimingMetrics:
    """
    Aggregated timing metrics for bot performance tracking

    Phase 8.6: Statistical analysis of execution timing.
    Maintains a bounded history of executions for memory efficiency.

    Attributes:
        executions: List of ExecutionTiming records
        max_history: Maximum number of executions to retain (default: 100)
    """
    executions: List[ExecutionTiming] = field(default_factory=list)
    max_history: int = 100  # Keep last 100 executions

    def add_execution(self, timing: ExecutionTiming) -> None:
        """
        Add execution timing record (bounded to max_history)

        Args:
            timing: ExecutionTiming record to add
        """
        self.executions.append(timing)
        if len(self.executions) > self.max_history:
            self.executions.pop(0)  # Remove oldest

    def get_stats(self) -> Dict[str, Any]:
        """
        Calculate timing statistics

        Returns:
            Dictionary containing:
            - total_executions: Total number of executions
            - successful_executions: Number of successful executions
            - success_rate: Ratio of successful to total executions
            - avg_total_delay_ms: Average total delay in milliseconds
            - avg_click_delay_ms: Average decision-to-click delay
            - avg_confirmation_delay_ms: Average click-to-confirmation delay
            - p50_total_delay_ms: Median total delay
            - p95_total_delay_ms: 95th percentile total delay
        """
        if not self.executions:
            return {
                'total_executions': 0,
                'success_rate': 0.0,
                'avg_total_delay_ms': 0.0,
                'avg_click_delay_ms': 0.0,
                'avg_confirmation_delay_ms': 0.0,
                'p50_total_delay_ms': 0.0,
                'p95_total_delay_ms': 0.0,
            }

        successful = [e for e in self.executions if e.success]
        total_delays = [e.total_delay_ms for e in successful]
        click_delays = [e.decision_to_click_ms for e in successful]
        confirm_delays = [e.click_to_confirmation_ms for e in successful]

        # Calculate percentiles safely (avoid index out of bounds)
        if total_delays:
            sorted_delays = sorted(total_delays)
            n = len(sorted_delays)
            # P50: Use index n//2, bounded to [0, n-1]
            p50_index = max(0, min(n // 2, n - 1))
            p50_value = sorted_delays[p50_index]
            # P95: Use index int(n * 0.95), bounded to [0, n-1]
            p95_index = max(0, min(int(n * 0.95), n - 1))
            p95_value = sorted_delays[p95_index]
        else:
            p50_value = 0.0
            p95_value = 0.0

        return {
            'total_executions': len(self.executions),
            'successful_executions': len(successful),
            'success_rate': len(successful) / len(self.executions),
            'avg_total_delay_ms': sum(total_delays) / len(total_delays) if total_delays else 0.0,
            'avg_click_delay_ms': sum(click_delays) / len(click_delays) if click_delays else 0.0,
            'avg_confirmation_delay_ms': sum(confirm_delays) / len(confirm_delays) if confirm_delays else 0.0,
            'p50_total_delay_ms': p50_value,
            'p95_total_delay_ms': p95_value,
        }

    def clear(self) -> None:
        """Clear all execution history"""
        self.executions.clear()

    def get_recent(self, n: int = 10) -> List[ExecutionTiming]:
        """
        Get the N most recent executions

        Args:
            n: Number of recent executions to return

        Returns:
            List of most recent ExecutionTiming records
        """
        return self.executions[-n:] if self.executions else []
