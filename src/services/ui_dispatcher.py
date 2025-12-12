"""
Thread-safe dispatcher for scheduling work on the Tk main thread.

AUDIT FIX: Added queue overflow protection, proper drain on stop,
and queue health monitoring.
"""

import queue
import logging
from typing import Callable, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class TkDispatcher:
    """
    Queues work items to be executed via Tk's event loop.

    AUDIT FIXES:
    - Queue size limit with overflow handling
    - Drain pending tasks during stop()
    - Queue health monitoring
    - Error isolation for individual tasks
    """

    # AUDIT FIX: Bounded queue to prevent memory exhaustion
    MAX_QUEUE_SIZE = 1000
    QUEUE_WARNING_THRESHOLD = 0.8  # Warn at 80% capacity

    def __init__(self, root, poll_interval: int = 16):
        """
        Args:
            root: Tk root object providing .after()
            poll_interval: milliseconds between queue drains
        """
        self._root = root
        self._poll_interval = poll_interval
        # AUDIT FIX: Use bounded queue
        self._queue: queue.Queue[Tuple[Callable, tuple, dict]] = queue.Queue(
            maxsize=self.MAX_QUEUE_SIZE
        )
        self._running = True
        self._dropped_count = 0
        self._total_processed = 0
        self._root.after(self._poll_interval, self._drain)

    def submit(self, fn: Callable, *args: Any, **kwargs: Any) -> bool:
        """
        Add a callable to be executed on the Tk thread.

        AUDIT FIX: Returns bool indicating success, gracefully handles overflow.

        Returns:
            bool: True if queued successfully, False if queue full or stopped
        """
        if not self._running:
            return False

        try:
            self._queue.put_nowait((fn, args, kwargs))

            # AUDIT FIX: Warn if queue is getting full
            qsize = self._queue.qsize()
            if qsize > self.MAX_QUEUE_SIZE * self.QUEUE_WARNING_THRESHOLD:
                logger.warning(
                    f"TkDispatcher queue at {qsize}/{self.MAX_QUEUE_SIZE} "
                    f"({qsize/self.MAX_QUEUE_SIZE*100:.0f}% capacity)"
                )
            return True

        except queue.Full:
            self._dropped_count += 1
            logger.warning(
                f"TkDispatcher queue full, dropped task "
                f"(total dropped: {self._dropped_count})"
            )
            return False

    def stop(self):
        """
        Stop scheduling new drain cycles.

        AUDIT FIX: Drains remaining tasks before stopping.
        """
        self._running = False

        # AUDIT FIX: Drain any remaining tasks
        remaining = 0
        while True:
            try:
                fn, args, kwargs = self._queue.get_nowait()
                remaining += 1
                try:
                    # Execute remaining tasks if root still exists
                    if self._root.winfo_exists():
                        fn(*args, **kwargs)
                except Exception as e:
                    logger.debug(f"Error executing task during shutdown: {e}")
                finally:
                    self._queue.task_done()
            except queue.Empty:
                break

        if remaining > 0:
            logger.debug(f"TkDispatcher drained {remaining} pending tasks on stop")

    def _drain(self):
        """
        Execute queued tasks; scheduled on the Tk thread.

        AUDIT FIX: Added error isolation and processing count.
        """
        processed = 0
        max_per_cycle = 50  # AUDIT FIX: Limit tasks per cycle to maintain UI responsiveness

        while processed < max_per_cycle:
            try:
                fn, args, kwargs = self._queue.get_nowait()
            except queue.Empty:
                break

            try:
                fn(*args, **kwargs)
                processed += 1
                self._total_processed += 1
            except Exception as e:
                # AUDIT FIX: Isolate errors - don't let one bad task crash the dispatcher
                logger.error(f"TkDispatcher task error: {e}", exc_info=True)
            finally:
                self._queue.task_done()

        if self._running:
            try:
                self._root.after(self._poll_interval, self._drain)
            except Exception:
                # Root may be destroyed during shutdown
                self._running = False

    def get_stats(self) -> dict:
        """
        Get dispatcher health statistics.

        AUDIT FIX: Added for monitoring queue health.

        Returns:
            dict: Statistics including queue size, dropped count, processed count
        """
        return {
            'queue_size': self._queue.qsize(),
            'max_queue_size': self.MAX_QUEUE_SIZE,
            'queue_utilization': self._queue.qsize() / self.MAX_QUEUE_SIZE,
            'dropped_count': self._dropped_count,
            'total_processed': self._total_processed,
            'running': self._running
        }
