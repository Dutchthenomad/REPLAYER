"""
Thread-safe dispatcher for scheduling work on the Tk main thread.
"""

import queue
from typing import Callable, Any, Tuple


class TkDispatcher:
    """Queues work items to be executed via Tk's event loop."""

    def __init__(self, root, poll_interval: int = 16):
        """
        Args:
            root: Tk root object providing .after()
            poll_interval: milliseconds between queue drains
        """
        self._root = root
        self._poll_interval = poll_interval
        self._queue: queue.Queue[Tuple[Callable, tuple, dict]] = queue.Queue()
        self._running = True
        self._root.after(self._poll_interval, self._drain)

    def submit(self, fn: Callable, *args: Any, **kwargs: Any):
        """Add a callable to be executed on the Tk thread."""
        if not self._running:
            raise RuntimeError("Dispatcher stopped")
        self._queue.put((fn, args, kwargs))

    def stop(self):
        """Stop scheduling new drain cycles."""
        self._running = False

    def _drain(self):
        """Execute queued tasks; scheduled on the Tk thread."""
        while True:
            try:
                fn, args, kwargs = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                fn(*args, **kwargs)
            finally:
                self._queue.task_done()

        if self._running:
            self._root.after(self._poll_interval, self._drain)
