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
import time

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
    SELL_PERCENTAGE_CHANGED = "trade.sell_percentage_changed"  # Phase 8.1
    POSITION_REDUCED = "trade.position_reduced"  # Phase 8.1

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
    REPLAY_RESET = "replay.reset"
    REPLAY_SPEED_CHANGED = "replay.speed_changed"
    REPLAY_STARTED = "replay.started"  # Alias for REPLAY_START
    REPLAY_PAUSED = "replay.paused"    # Alias for REPLAY_PAUSE
    REPLAY_STOPPED = "replay.stopped"  # Alias for REPLAY_STOP

    # Phase 10.7: Player State Events (WebSocket server state)
    PLAYER_IDENTITY = "player.identity"  # Player ID and username from usernameStatus
    PLAYER_UPDATE = "player.update"      # Server state from playerUpdate

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

        # AUDIT FIX 2: Track original callbacks by id for proper unsubscribe
        self._callback_ids: Dict[Events, Dict[int, Any]] = {}

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
        """
        Stop event processing

        AUDIT FIX: Improved shutdown with retry loop to prevent hangs.
        Uses multiple attempts with queue draining to ensure sentinel delivery.
        """
        if not self._processing:
            return

        # Signal processing to stop (allows _process_events to exit on timeout)
        self._processing = False

        # AUDIT FIX: Retry loop with timeout for reliable sentinel insertion
        max_attempts = 10
        sentinel_sent = False

        for attempt in range(max_attempts):
            try:
                self._queue.put(None, timeout=0.2)  # Sentinel to wake thread
                sentinel_sent = True
                break
            except queue.Full:
                # Drain one item to make space, then retry
                try:
                    self._queue.get_nowait()
                    logger.debug(f"Drained queue item on shutdown attempt {attempt + 1}")
                except queue.Empty:
                    pass
                # Small delay before retry
                time.sleep(0.05)

        if not sentinel_sent:
            logger.warning("Failed to send shutdown sentinel after max attempts")

        # Wait for processing thread to finish
        if self._thread:
            self._thread.join(timeout=3.0)
            if self._thread.is_alive():
                logger.error("EventBus thread did not stop cleanly within timeout")

        logger.info("EventBus stopped")
    
    def subscribe(self, event: Events, callback: Callable, weak: bool = True):
        """
        Subscribe to an event

        AUDIT FIX: Added weak reference support to prevent memory leaks
        AUDIT FIX 2: Track callback IDs for proper unsubscribe

        Args:
            event: Event to subscribe to
            callback: Callback function
            weak: Use weak reference (default True)
        """
        with self._sub_lock:
            if event not in self._subscribers:
                self._subscribers[event] = []
            if event not in self._callback_ids:
                self._callback_ids[event] = {}

            # Use object id to track callback for unsubscribe
            cb_id = id(callback)

            # Skip if already subscribed (prevent duplicates)
            if cb_id in self._callback_ids[event]:
                logger.debug(f"Already subscribed to {event.value}, skipping duplicate")
                return

            # AUDIT FIX: Store as weak reference by default
            if weak:
                try:
                    ref = weakref.ref(callback)
                    self._subscribers[event].append((cb_id, ref))
                except TypeError:
                    # Callback not weak-referenceable (e.g., lambda), store directly
                    self._subscribers[event].append((cb_id, callback))
            else:
                # Store direct reference
                self._subscribers[event].append((cb_id, callback))

            # Track by ID for unsubscribe
            self._callback_ids[event][cb_id] = callback
            logger.debug(f"Subscribed to {event.value}")
    
    def unsubscribe(self, event: Events, callback: Callable):
        """
        Unsubscribe from an event

        AUDIT FIX 2: Use callback ID for proper matching (fixes broken unsubscribe)
        """
        with self._sub_lock:
            if event not in self._subscribers:
                logger.debug(f"No subscribers for {event.value}, nothing to unsubscribe")
                return

            cb_id = id(callback)

            # Remove from ID tracking
            if event in self._callback_ids:
                self._callback_ids[event].pop(cb_id, None)

            # Remove from subscriber list by ID
            self._subscribers[event] = [
                (cid, ref) for cid, ref in self._subscribers[event]
                if cid != cb_id
            ]
            logger.debug(f"Unsubscribed from {event.value}")
    
    def publish(self, event: Events, data: Any = None):
        """
        Publish an event

        AUDIT FIX: Track statistics and queue capacity monitoring
        """
        try:
            self._queue.put_nowait((event, data))
            self._stats['events_published'] += 1

            # AUDIT FIX: Warn at 80% capacity
            qsize = self._queue.qsize()
            max_size = self._queue.maxsize
            if max_size > 0 and qsize > max_size * 0.8:
                logger.warning(
                    f"EventBus queue at {qsize}/{max_size} "
                    f"({qsize/max_size*100:.0f}% capacity)"
                )
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
        AUDIT FIX 2: Updated to work with (cb_id, ref) tuple format
        """
        callbacks_to_call = []
        with self._sub_lock:
            if event in self._subscribers:
                alive_entries = []
                dead_entries = []
                for cb_id, ref in self._subscribers[event]:
                    callback = self._resolve_callback(ref)
                    if callback:
                        callbacks_to_call.append(callback)
                        alive_entries.append((cb_id, ref))
                    else:
                        dead_entries.append((cb_id, ref))
                self._subscribers[event] = alive_entries

        for callback in callbacks_to_call:
            try:
                callback({'name': event.value, 'data': data})
                self._stats['events_processed'] += 1
            except Exception as e:
                self._stats['errors'] += 1
                logger.error(f"Error in callback for {event.value}: {e}", exc_info=True)

    def _resolve_callback(self, ref):
        """Safely resolve weak or direct callback reference"""
        try:
            if isinstance(ref, weakref.ReferenceType):
                return ref()
            if callable(ref):
                return ref
        except Exception as e:
            logger.warning(f"Failed to resolve callback: {e}")
        return None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get event bus statistics

        AUDIT FIX: Include processing stats
        """
        with self._sub_lock:
            stats = {
                'subscriber_count': sum(len(entries) for entries in self._subscribers.values()),
                'event_types': len(self._subscribers),
                'queue_size': self._queue.qsize(),
                'processing': self._processing
            }
            # Add processing stats
            stats.update(self._stats)
            return stats

    def clear_all(self):
        """
        Clear all subscribers (for testing/cleanup).

        AUDIT FIX 2: Added for proper cleanup
        """
        with self._sub_lock:
            self._subscribers.clear()
            self._callback_ids.clear()
            logger.debug("All subscribers cleared")

# Global instance
event_bus = EventBus()
