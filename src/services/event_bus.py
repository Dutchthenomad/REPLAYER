"""
Event Bus Service - Thread-safe with deadlock prevention
AUDIT FIX: Added weak references and lock-free callback execution
"""

from typing import Dict, List, Callable, Any, Optional
from enum import Enum
import threading
import queue
import logging
import weakref

logger = logging.getLogger(__name__)

class Events(Enum):
    """Event constants matching what's used in main.py"""
    # UI Events
    UI_READY = "ui.ready"
    UI_UPDATE = "ui.update"
    UI_ERROR = "ui.error"
    
    # Game Events
    GAME_START = "game.start"
    GAME_END = "game.end"
    GAME_TICK = "game.tick"
    GAME_RUG = "game.rug"
    RUG_DETECTED = "game.rug_detected"
    
    # Trading Events
    TRADE_BUY = "trade.buy"
    TRADE_SELL = "trade.sell"
    TRADE_SIDEBET = "trade.sidebet"
    TRADE_EXECUTED = "trade.executed"
    TRADE_FAILED = "trade.failed"
    
    # Bot Events
    BOT_ENABLED = "bot.enabled"
    BOT_DISABLED = "bot.disabled"
    BOT_DECISION = "bot.decision"
    BOT_ACTION = "bot.action"
    
    # File Events
    FILE_LOADED = "file.loaded"
    FILE_SAVED = "file.saved"
    FILE_ERROR = "file.error"
    
    # Replay Events
    REPLAY_START = "replay.start"
    REPLAY_PAUSE = "replay.pause"
    REPLAY_STOP = "replay.stop"
    REPLAY_SPEED_CHANGED = "replay.speed_changed"

class EventBus:
    """
    Thread-safe event bus with deadlock prevention

    AUDIT FIX: Key improvements:
    - No locks held during callback execution
    - Weak references for automatic cleanup
    - Error isolation
    - Larger queue (5000 vs 1000)
    """

    def __init__(self, max_queue_size: int = 5000):
        # AUDIT FIX: Use weak references to prevent memory leaks
        self._subscribers: Dict[Events, List[weakref.ref]] = {}

        # AUDIT FIX: Increased queue size from 1000 to 5000
        self._queue = queue.Queue(maxsize=max_queue_size)

        self._processing = False
        self._thread = None

        # AUDIT FIX: Lock only for subscription management, not event dispatch
        self._sub_lock = threading.RLock()

        # AUDIT FIX: Add statistics tracking
        self._stats = {
            'events_published': 0,
            'events_processed': 0,
            'events_dropped': 0,
            'errors': 0
        }

        logger.info(f"EventBus initialized with queue size {max_queue_size}")
        
    def start(self):
        """Start event processing thread"""
        if not self._processing:
            self._processing = True
            self._thread = threading.Thread(target=self._process_events, daemon=True)
            self._thread.start()
            logger.info("EventBus started")
    
    def stop(self):
        """Stop event processing"""
        if not self._processing:
            return

        try:
            self._queue.put(None, timeout=1)  # Sentinel to wake thread
        except queue.Full:
            # Drain one item to make space, then retry
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            self._queue.put(None)

        if self._thread:
            self._thread.join(timeout=2)

        self._processing = False
        logger.info("EventBus stopped")
    
    def subscribe(self, event: Events, callback: Callable, weak: bool = True):
        """
        Subscribe to an event

        AUDIT FIX: Added weak reference support to prevent memory leaks

        Args:
            event: Event to subscribe to
            callback: Callback function
            weak: Use weak reference (default True)
        """
        with self._sub_lock:
            if event not in self._subscribers:
                self._subscribers[event] = []

            # AUDIT FIX: Store as weak reference by default
            if weak:
                try:
                    ref = weakref.ref(callback)
                    self._subscribers[event].append(ref)
                except TypeError:
                    # Callback not weak-referenceable (e.g., lambda), store directly
                    self._subscribers[event].append(lambda: callback)
            else:
                # Store direct reference
                self._subscribers[event].append(lambda: callback)
            logger.debug(f"Subscribed to {event.value}")
    
    def unsubscribe(self, event: Events, callback: Callable):
        """
        Unsubscribe from an event

        AUDIT FIX: Handle weak references properly
        """
        with self._sub_lock:
            if event in self._subscribers:
                # AUDIT FIX: Filter out matching callbacks (handle weak refs)
                self._subscribers[event] = [
                    ref for ref in self._subscribers[event]
                    if callable(ref) and ref() != callback
                ]
                logger.debug(f"Unsubscribed from {event.value}")
    
    def publish(self, event: Events, data: Any = None):
        """
        Publish an event

        AUDIT FIX: Track statistics
        """
        try:
            self._queue.put_nowait((event, data))
            self._stats['events_published'] += 1
        except queue.Full:
            self._stats['events_dropped'] += 1
            logger.warning(f"Event queue full, dropping event: {event.value}")
    
    def _process_events(self):
        """Background thread to process events"""
        while self._processing:
            try:
                item = self._queue.get(timeout=0.1)
                if item is None:  # Sentinel
                    break
                    
                event, data = item
                self._dispatch(event, data)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)
    
    def _dispatch(self, event: Events, data: Any):
        """
        Dispatch event to subscribers

        AUDIT FIX: CRITICAL - DO NOT hold lock during callback execution!
        This prevents deadlocks when callbacks publish events.
        """
        # AUDIT FIX: Get callbacks THEN release lock before calling them
        callbacks_to_call = []
        with self._sub_lock:
            if event in self._subscribers:
                # Clean up dead weak references while we're here
                alive_callbacks = []
                for ref in self._subscribers[event]:
                    if callable(ref):
                        # It's a weakref
                        cb = ref()
                        if cb is not None:
                            callbacks_to_call.append(cb)
                            alive_callbacks.append(ref)
                    else:
                        # It's a direct reference (lambda wrapper)
                        callbacks_to_call.append(ref)
                        alive_callbacks.append(ref)

                # Update list with only alive callbacks
                self._subscribers[event] = alive_callbacks

        # AUDIT FIX: Call callbacks OUTSIDE the lock!
        for callback in callbacks_to_call:
            try:
                callback({'name': event.value, 'data': data})
                self._stats['events_processed'] += 1
            except Exception as e:
                self._stats['errors'] += 1
                logger.error(f"Error in callback for {event.value}: {e}", exc_info=True)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get event bus statistics

        AUDIT FIX: Include processing stats
        """
        with self._sub_lock:
            stats = {
                'subscriber_count': sum(len(callbacks) for callbacks in self._subscribers.values()),
                'event_types': len(self._subscribers),
                'queue_size': self._queue.qsize(),
                'processing': self._processing
            }
            # Add processing stats
            stats.update(self._stats)
            return stats

# Global instance
event_bus = EventBus()
