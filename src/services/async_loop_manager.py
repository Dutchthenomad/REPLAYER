"""
Async Loop Manager - Critical Fix for asyncio/Tkinter Concurrency

PROBLEM:
Creating new event loops on-the-fly (asyncio.new_event_loop()) in threads causes:
1. Playwright object ownership issues (objects bound to original loop)
2. Deadlocks when trying to close browser from different loop
3. Resource leaks from temporary event loops

SOLUTION:
Single dedicated thread running loop.run_forever(), with:
- asyncio.run_coroutine_threadsafe() to dispatch tasks from Tkinter
- root.after() to dispatch results back to Tkinter UI thread
- Proper shutdown sequence

Usage:
    # In main.py initialization:
    async_manager = AsyncLoopManager()
    async_manager.start()

    # In main_window.py or browser_executor:
    future = async_manager.run_coroutine(some_async_function())
    result = future.result(timeout=10)  # Or use add_done_callback

    # In shutdown:
    async_manager.stop()
"""

import asyncio
import threading
import logging
from typing import Any, Callable, Coroutine, Optional
from concurrent.futures import Future

logger = logging.getLogger(__name__)


class AsyncLoopManager:
    """
    Manages a dedicated asyncio event loop in a separate thread

    Provides thread-safe methods to:
    - Run coroutines from the Tkinter main thread
    - Avoid creating temporary event loops
    - Prevent Playwright ownership issues
    - Ensure clean shutdown
    """

    def __init__(self):
        """Initialize manager (does not start loop yet)"""
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._started = False
        self._stopping = False

    def start(self) -> None:
        """
        Start dedicated async event loop in background thread

        Must be called before run_coroutine()
        """
        if self._started:
            logger.warning("AsyncLoopManager already started")
            return

        logger.info("Starting dedicated asyncio event loop thread")

        # Create loop in new thread
        def run_loop():
            # Create loop in this thread
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            logger.info("Asyncio event loop running")

            # Run until stop() is called
            try:
                self._loop.run_forever()
            finally:
                # Cleanup
                logger.info("Asyncio event loop stopped, cleaning up")
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()

                # Wait for cancellations to complete
                if pending:
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

                self._loop.close()
                logger.info("Asyncio event loop closed")

        self._thread = threading.Thread(target=run_loop, daemon=True, name="AsyncLoopThread")
        self._thread.start()
        self._started = True

        # Wait briefly for loop to initialize
        import time
        timeout = 2.0
        start = time.time()
        while self._loop is None and (time.time() - start) < timeout:
            time.sleep(0.01)

        if self._loop is None:
            raise RuntimeError("Failed to start asyncio event loop")

        logger.info("AsyncLoopManager started successfully")

    def run_coroutine(self, coro: Coroutine) -> Future:
        """
        Run coroutine in dedicated async thread, return Future

        Args:
            coro: Coroutine to execute

        Returns:
            concurrent.futures.Future that will contain result

        Usage:
            future = manager.run_coroutine(browser.stop_browser())
            # Option 1: Block until done
            result = future.result(timeout=10)

            # Option 2: Non-blocking callback (recommended for UI)
            def on_done(f):
                try:
                    result = f.result()
                    root.after(0, lambda: update_ui(result))
                except Exception as e:
                    root.after(0, lambda: show_error(e))
            future.add_done_callback(on_done)
        """
        if not self._started or self._loop is None:
            raise RuntimeError("AsyncLoopManager not started. Call start() first.")

        if self._stopping:
            raise RuntimeError("AsyncLoopManager is shutting down")

        # Submit to dedicated loop thread
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def stop(self, timeout: float = 5.0) -> None:
        """
        Stop async event loop and join thread

        Args:
            timeout: Max seconds to wait for shutdown
        """
        if not self._started:
            return

        self._stopping = True
        logger.info("Stopping AsyncLoopManager")

        if self._loop and self._loop.is_running():
            # Stop the loop
            self._loop.call_soon_threadsafe(self._loop.stop)

        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

            if self._thread.is_alive():
                logger.warning(f"Async loop thread did not stop within {timeout}s")
            else:
                logger.info("Async loop thread stopped successfully")

        self._started = False
        self._stopping = False
        self._loop = None
        self._thread = None

    def is_running(self) -> bool:
        """Check if loop is running"""
        return self._started and self._loop is not None and self._loop.is_running()

    def __del__(self):
        """Ensure cleanup on deletion"""
        if self._started:
            logger.warning("AsyncLoopManager deleted without calling stop()")
            self.stop(timeout=1.0)
