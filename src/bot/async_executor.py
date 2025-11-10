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
    """

    def __init__(self, bot_controller):
        """
        Initialize async bot executor

        Args:
            bot_controller: BotController instance to execute
        """
        self.bot_controller = bot_controller
        self.enabled = False

        # Queue for bot execution requests (max 10 pending ticks)
        # If bot can't keep up, older ticks are dropped
        self.execution_queue = queue.Queue(maxsize=10)
        self.result_queue = queue.Queue()

        # Worker thread
        self.worker_thread = None
        self.stop_event = threading.Event()

        # Statistics
        self.executions = 0
        self.failures = 0
        self.queue_drops = 0

        logger.info("AsyncBotExecutor initialized")

    def start(self):
        """Start the bot executor worker thread"""
        if self.worker_thread and self.worker_thread.is_alive():
            logger.warning("Bot executor already running")
            return

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
        """Stop the bot executor worker thread"""
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

        # Wait for worker to stop
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
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
            self.queue_drops += 1
            logger.debug(f"Bot execution queue full, dropped tick {tick.tick}")
            return False

    def _worker_loop(self):
        """Worker thread that processes bot execution requests"""
        logger.info("Bot executor worker started")

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

                    self.executions += 1

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
                    self.failures += 1
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
