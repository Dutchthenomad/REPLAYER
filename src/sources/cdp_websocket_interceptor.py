"""
CDP WebSocket Interceptor

Intercepts WebSocket frames from Chrome via CDP Network domain.
Captures ALL events the browser receives, including authenticated events.
"""
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from sources.socketio_parser import parse_socketio_frame

logger = logging.getLogger(__name__)


class CDPWebSocketInterceptor:
    """
    Intercepts WebSocket frames from Chrome via CDP.

    Uses Network.webSocketFrameReceived to capture ALL events
    the browser receives, including authenticated events like
    usernameStatus and playerUpdate.
    """

    RUGS_BACKEND_HOST = 'backend.rugs.fun'

    def __init__(self):
        """Initialize interceptor."""
        self._lock = threading.Lock()

        # Connection state
        self.is_connected: bool = False
        self.rugs_websocket_id: Optional[str] = None

        # CDP client (set by connect())
        self._cdp_client = None

        # Event callback
        self.on_event: Optional[Callable[[Dict[str, Any]], None]] = None

        # CDP timestamps are monotonic (not UNIX epoch). Capture a base mapping
        # so we can emit reasonable wall-clock timestamps for downstream consumers.
        self._cdp_timestamp_base: Optional[float] = None
        self._wall_epoch_base: Optional[float] = None

        # Statistics
        self.events_received: int = 0
        self.events_sent: int = 0

        logger.info("CDPWebSocketInterceptor initialized")

    def _is_rugs_websocket(self, url: str) -> bool:
        """Check if URL is rugs.fun WebSocket."""
        return (
            self.RUGS_BACKEND_HOST in url and
            'socket.io' in url and
            url.startswith('wss://')
        )

    def _handle_websocket_created(self, params: Dict[str, Any]):
        """
        Handle Network.webSocketCreated event.

        Captures the request ID for rugs.fun WebSocket connections.
        """
        url = params.get('url', '')
        request_id = params.get('requestId')

        if self._is_rugs_websocket(url):
            with self._lock:
                self.rugs_websocket_id = request_id
            logger.info(f"Captured rugs.fun WebSocket: {request_id}")

    def _handle_frame_received(self, params: Dict[str, Any]):
        """
        Handle Network.webSocketFrameReceived event.

        Parses incoming frames and emits structured events.
        """
        request_id = params.get('requestId')

        with self._lock:
            if request_id != self.rugs_websocket_id:
                return

        response = params.get('response', {})
        payload = response.get('payloadData', '')
        timestamp = params.get('timestamp', 0)

        self._process_frame(payload, timestamp, 'received')

    def _handle_frame_sent(self, params: Dict[str, Any]):
        """
        Handle Network.webSocketFrameSent event.

        Parses outgoing frames and emits structured events.
        """
        request_id = params.get('requestId')

        with self._lock:
            if request_id != self.rugs_websocket_id:
                return

        response = params.get('response', {})
        payload = response.get('payloadData', '')
        timestamp = params.get('timestamp', 0)

        self._process_frame(payload, timestamp, 'sent')

    def _process_frame(self, payload: str, timestamp: float, direction: str):
        """Process a WebSocket frame and emit event."""
        frame = parse_socketio_frame(payload)

        if frame is None:
            return

        # Only emit actual events (not ping/pong)
        if frame.type != 'event' or not frame.event_name:
            return

        event_epoch = self._to_epoch_seconds(timestamp)

        # Build event dict
        event = {
            'event': frame.event_name,
            'data': frame.data,
            'timestamp': datetime.fromtimestamp(event_epoch, tz=timezone.utc).isoformat(),
            'direction': direction,
            'raw': frame.raw
        }

        # Update stats
        with self._lock:
            if direction == 'received':
                self.events_received += 1
            else:
                self.events_sent += 1

        # Emit to callback
        if self.on_event:
            try:
                self.on_event(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")

    def _to_epoch_seconds(self, cdp_timestamp: float) -> float:
        """
        Convert a CDP timestamp to UNIX epoch seconds.

        Chrome DevTools Protocol uses monotonic timestamps for many events.
        If the value doesn't look like epoch seconds, map it to wall-clock time
        using a captured base offset.
        """
        if not cdp_timestamp:
            return time.time()

        # If it looks like epoch seconds already, pass through.
        if cdp_timestamp >= 1_000_000_000:
            return float(cdp_timestamp)

        with self._lock:
            if self._cdp_timestamp_base is None or self._wall_epoch_base is None:
                self._cdp_timestamp_base = float(cdp_timestamp)
                self._wall_epoch_base = time.time()

            return self._wall_epoch_base + (float(cdp_timestamp) - self._cdp_timestamp_base)

    def _handle_websocket_closed(self, params: Dict[str, Any]):
        """
        Handle Network.webSocketClosed event.

        Clears the tracked WebSocket ID.
        """
        request_id = params.get('requestId')

        with self._lock:
            if request_id == self.rugs_websocket_id:
                self.rugs_websocket_id = None
                logger.info("Rugs.fun WebSocket closed")

    async def connect(self, cdp_client) -> bool:
        """
        Connect to CDP and start intercepting.

        Args:
            cdp_client: Playwright CDPSession with send() method

        Returns:
            True if connected successfully
        """
        try:
            self._cdp_client = cdp_client

            # Enable Network domain (Playwright uses async send())
            await cdp_client.send('Network.enable')

            # Subscribe to WebSocket events
            cdp_client.on('Network.webSocketCreated', self._handle_websocket_created)
            cdp_client.on('Network.webSocketFrameReceived', self._handle_frame_received)
            cdp_client.on('Network.webSocketFrameSent', self._handle_frame_sent)
            cdp_client.on('Network.webSocketClosed', self._handle_websocket_closed)

            self.is_connected = True
            logger.info("CDP WebSocket interception started")
            return True

        except Exception as e:
            logger.error(f"Failed to connect CDP interceptor: {e}")
            return False

    async def disconnect(self):
        """Stop intercepting and disconnect."""
        if self._cdp_client:
            try:
                # Disable Network domain to stop receiving events
                await self._cdp_client.send('Network.disable')
            except Exception as e:
                logger.warning(f"Error disabling Network domain: {e}")

        self.is_connected = False
        self.rugs_websocket_id = None
        self._cdp_client = None
        with self._lock:
            self._cdp_timestamp_base = None
            self._wall_epoch_base = None
        logger.info("CDP WebSocket interception stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get interception statistics."""
        with self._lock:
            return {
                'is_connected': self.is_connected,
                'has_rugs_websocket': self.rugs_websocket_id is not None,
                'events_received': self.events_received,
                'events_sent': self.events_sent
            }
