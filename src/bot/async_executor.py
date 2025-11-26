"""
Asynchronous Bot Executor - Prevents Deadlock and UI Freezing

This module provides non-blocking bot execution to prevent the replay thread
from freezing when the bot is enabled.

Author: AI Assistant
Date: 2025-11-06
"""

import threading
import queue
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from models import GameTick

logger = logging.getLogger(__name__)


class AsyncBotExecutor:
    """
    Asynchronous bot executor that prevents deadlocks

    Executes bot decisions in a separate worker thread with queuing to prevent
    blocking the replay engine's tick update callback.

    Key Features:
    - Non-blocking execution: Tick updates return immediately
    - Queue-based: Prevents direct thread blocking
    - Graceful degradation: Drops ticks if bot can't keep up
    - Clean shutdown: Proper thread cleanup

    Thread Safety:
    - Uses queue.Queue for thread-safe communication
    - Worker thread is daemon for automatic cleanup
    - Stop event for graceful shutdown
    - AUDIT FIX: Added Condition for proper shutdown synchronization
    """

    def __init__(self, bot_controller):
        """
        Initialize async bot executor

        Args:
            bot_controller: BotController instance to execute
        """
        self.bot_controller = bot_controller

        # AUDIT FIX: Thread-safe state with lock
        self._state_lock = threading.Lock()
        self._enabled = False

        # Queue for bot execution requests (max 10 pending ticks)
        # If bot can't keep up, older ticks are dropped
        self.execution_queue = queue.Queue(maxsize=10)
        self.result_queue = queue.Queue()

        # Worker thread
        self.worker_thread = None
        self.stop_event = threading.Event()

        # AUDIT FIX: Condition for clean shutdown synchronization
        self._shutdown_condition = threading.Condition()
        self._worker_stopped = False

        # Statistics (protected by _state_lock)
        self._executions = 0
        self._failures = 0
        self._queue_drops = 0

        logger.info("AsyncBotExecutor initialized")

    @property
    def enabled(self) -> bool:
        """Thread-safe enabled state accessor."""
        with self._state_lock:
            return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        """Thread-safe enabled state setter."""
        with self._state_lock:
            self._enabled = value

    @property
    def executions(self) -> int:
        """Thread-safe executions counter."""
        with self._state_lock:
            return self._executions

    @property
    def failures(self) -> int:
        """Thread-safe failures counter."""
        with self._state_lock:
            return self._failures

    @property
    def queue_drops(self) -> int:
        """Thread-safe queue_drops counter."""
        with self._state_lock:
            return self._queue_drops

    def start(self):
        """Start the bot executor worker thread"""
        if self.worker_thread and self.worker_thread.is_alive():
            logger.warning("Bot executor already running")
            return

        # AUDIT FIX: Reset shutdown state under condition lock
        with self._shutdown_condition:
            self._worker_stopped = False

        self.stop_event.clear()
        self.enabled = True

        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            name="BotExecutor",
            daemon=True  # Daemon ensures clean exit
        )
        self.worker_thread.start()
        logger.info("Bot executor started")

    def stop(self):
        """
        Stop the bot executor worker thread

        AUDIT FIX: Uses Condition for proper synchronization to ensure
        the worker thread has fully stopped before returning.
        """
        self.enabled = False
        self.stop_event.set()

        # Clear the execution queue
        while not self.execution_queue.empty():
            try:
                self.execution_queue.get_nowait()
            except queue.Empty:
                break

        # Send stop signal (None) to worker
        try:
            self.execution_queue.put(None, timeout=0.1)
        except queue.Full:
            pass

        # AUDIT FIX: Wait for worker to signal completion via Condition
        with self._shutdown_condition:
            # Wait up to 3 seconds for worker to signal it has stopped
            if not self._worker_stopped:
                self._shutdown_condition.wait(timeout=3.0)

        # Also join the thread as backup
        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)
            if self.worker_thread.is_alive():
                logger.warning("Bot executor thread did not stop cleanly")

        logger.info(f"Bot executor stopped. Stats: {self.executions} executions, "
                   f"{self.failures} failures, {self.queue_drops} drops")

    def queue_execution(self, tick: GameTick) -> bool:
        """
        Queue a bot execution request (non-blocking)

        Args:
            tick: GameTick to process

        Returns:
            bool: True if queued successfully, False if queue full
        """
        if not self.enabled:
            return False

        try:
            # Try to add to queue (non-blocking)
            self.execution_queue.put_nowait(tick)
            return True
        except queue.Full:
            # Queue is full - drop this tick
            # AUDIT FIX: Thread-safe counter increment
            with self._state_lock:
                self._queue_drops += 1
            logger.debug(f"Bot execution queue full, dropped tick {tick.tick}")
            return False

    def _worker_loop(self):
        """
        Worker thread that processes bot execution requests

        AUDIT FIX: Signals completion via Condition for clean shutdown.
        """
        logger.info("Bot executor worker started")

        try:
            while not self.stop_event.is_set():
                try:
                    # Wait for execution request (with timeout for responsiveness)
                    tick = self.execution_queue.get(timeout=0.5)

                    if tick is None:  # Stop signal
                        break

                    # Execute bot decision
                    start_time = time.perf_counter()

                    try:
                        result = self.bot_controller.execute_step()
                        elapsed = time.perf_counter() - start_time

                        # AUDIT FIX: Thread-safe counter increment
                        with self._state_lock:
                            self._executions += 1

                        # Put result in result queue for UI updates
                        self.result_queue.put({
                            'tick': tick.tick,
                            'result': result,
                            'elapsed': elapsed,
                            'timestamp': datetime.now()
                        })

                        # Log non-WAIT actions
                        action = result.get('action', 'WAIT')
                        if action != 'WAIT':
                            logger.debug(f"Bot executed {action} at tick {tick.tick} "
                                       f"in {elapsed:.3f}s")

                    except Exception as e:
                        # AUDIT FIX: Thread-safe counter increment
                        with self._state_lock:
                            self._failures += 1
                        logger.error(f"Bot execution failed at tick {tick.tick}: {e}")

                        # Put error in result queue
                        self.result_queue.put({
                            'tick': tick.tick,
                            'error': str(e),
                            'timestamp': datetime.now()
                        })

                except queue.Empty:
                    # Timeout - continue loop to check stop event
                    continue
                except Exception as e:
                    logger.error(f"Bot worker error: {e}", exc_info=True)
        finally:
            # AUDIT FIX: Signal that worker has stopped via Condition
            with self._shutdown_condition:
                self._worker_stopped = True
                self._shutdown_condition.notify_all()

        logger.info("Bot executor worker stopped")

    def get_latest_result(self) -> Optional[Dict]:
        """
        Get latest bot execution result (non-blocking)

        Returns:
            dict: Latest result or None if no results pending
        """
        try:
            return self.result_queue.get_nowait()
        except queue.Empty:
            return None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get executor statistics

        Returns:
            dict: Statistics including executions, failures, drops, queue size
        """
        return {
            'enabled': self.enabled,
            'executions': self.executions,
            'failures': self.failures,
            'queue_drops': self.queue_drops,
            'queue_size': self.execution_queue.qsize()
        }
