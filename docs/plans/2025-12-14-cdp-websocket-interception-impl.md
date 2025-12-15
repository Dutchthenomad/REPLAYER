# CDP WebSocket Interception Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Intercept WebSocket frames from Chrome via CDP to capture ALL rugs.fun events (including authenticated events) and unify them into a single event stream.

**Architecture:** Use CDP Network domain to tap into browser's authenticated WebSocket connection. EventSourceManager orchestrates switching between CDP (primary) and fallback WebSocketFeed (public-only). All events flow through UnifiedEventBus for RAG cataloging and UI updates.

**Tech Stack:** Python 3.11, python-socketio, Chrome DevTools Protocol, tkinter, JSONL

**GitHub Issue:** #13

---

## Task 1: Socket.IO Frame Parser (Core Utility)

**Files:**
- Create: `src/sources/socketio_parser.py`
- Test: `src/tests/test_sources/test_socketio_parser.py`

**Step 1: Write the failing test**

```python
# src/tests/test_sources/test_socketio_parser.py
"""Tests for Socket.IO frame parsing."""
import pytest
from sources.socketio_parser import parse_socketio_frame, SocketIOFrame


class TestParseSocketIOFrame:
    """Test Socket.IO frame parsing."""

    def test_parse_event_frame(self):
        """Parse standard event frame."""
        raw = '42["gameStateUpdate",{"gameId":"123","price":1.5}]'
        frame = parse_socketio_frame(raw)

        assert frame.type == "event"
        assert frame.event_name == "gameStateUpdate"
        assert frame.data == {"gameId": "123", "price": 1.5}

    def test_parse_connect_frame(self):
        """Parse connection frame."""
        raw = '0{"sid":"abc123"}'
        frame = parse_socketio_frame(raw)

        assert frame.type == "connect"
        assert frame.data == {"sid": "abc123"}

    def test_parse_ping_frame(self):
        """Parse ping frame."""
        raw = '2'
        frame = parse_socketio_frame(raw)

        assert frame.type == "ping"
        assert frame.data is None

    def test_parse_pong_frame(self):
        """Parse pong frame."""
        raw = '3'
        frame = parse_socketio_frame(raw)

        assert frame.type == "pong"
        assert frame.data is None

    def test_parse_event_with_array_data(self):
        """Parse event with array payload."""
        raw = '42["standard/newTrade",{"type":"buy","amount":0.01}]'
        frame = parse_socketio_frame(raw)

        assert frame.event_name == "standard/newTrade"
        assert frame.data["type"] == "buy"

    def test_parse_auth_event(self):
        """Parse authenticated event."""
        raw = '42["usernameStatus",{"id":"did:privy:abc","username":"Dutch"}]'
        frame = parse_socketio_frame(raw)

        assert frame.event_name == "usernameStatus"
        assert frame.data["username"] == "Dutch"

    def test_invalid_frame_returns_none(self):
        """Invalid frame returns None."""
        frame = parse_socketio_frame("invalid")
        assert frame is None

    def test_empty_frame_returns_none(self):
        """Empty frame returns None."""
        frame = parse_socketio_frame("")
        assert frame is None
```

**Step 2: Run test to verify it fails**

Run: `cd src && python3 -m pytest tests/test_sources/test_socketio_parser.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'sources.socketio_parser'"

**Step 3: Write minimal implementation**

```python
# src/sources/socketio_parser.py
"""Socket.IO frame parser for CDP WebSocket interception."""
import json
import re
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class SocketIOFrame:
    """Parsed Socket.IO frame."""
    type: str           # "connect", "disconnect", "event", "ping", "pong", "error"
    event_name: Optional[str] = None
    data: Optional[Any] = None
    raw: str = ""


# Socket.IO Engine.IO packet types
PACKET_TYPES = {
    '0': 'connect',
    '1': 'disconnect',
    '2': 'ping',
    '3': 'pong',
    '4': 'message',
    '5': 'upgrade',
    '6': 'noop',
}

# Socket.IO packet types (after Engine.IO '4' message)
SOCKETIO_TYPES = {
    '0': 'connect',
    '1': 'disconnect',
    '2': 'event',
    '3': 'ack',
    '4': 'error',
    '5': 'binary_event',
    '6': 'binary_ack',
}


def parse_socketio_frame(raw: str) -> Optional[SocketIOFrame]:
    """
    Parse a Socket.IO frame from raw WebSocket data.

    Socket.IO uses Engine.IO as transport layer:
    - Engine.IO packet: <packet_type><data>
    - For message (type 4): 4<socketio_type>[<data>]

    Common patterns:
    - "0{...}" - Engine.IO connect
    - "2" - Engine.IO ping
    - "3" - Engine.IO pong
    - "42[...]" - Engine.IO message (4) + Socket.IO event (2)

    Args:
        raw: Raw WebSocket frame data

    Returns:
        Parsed SocketIOFrame or None if invalid
    """
    if not raw or not isinstance(raw, str):
        return None

    raw = raw.strip()
    if not raw:
        return None

    # Get Engine.IO packet type
    engine_type = raw[0]

    if engine_type not in PACKET_TYPES:
        return None

    packet_type = PACKET_TYPES[engine_type]

    # Handle simple packets (ping/pong)
    if packet_type in ('ping', 'pong', 'noop', 'upgrade'):
        return SocketIOFrame(type=packet_type, raw=raw)

    # Handle connect packet
    if packet_type == 'connect':
        data = None
        if len(raw) > 1:
            try:
                data = json.loads(raw[1:])
            except json.JSONDecodeError:
                pass
        return SocketIOFrame(type='connect', data=data, raw=raw)

    # Handle disconnect
    if packet_type == 'disconnect':
        return SocketIOFrame(type='disconnect', raw=raw)

    # Handle message packet (contains Socket.IO data)
    if packet_type == 'message':
        return _parse_socketio_message(raw[1:], raw)

    return None


def _parse_socketio_message(data: str, raw: str) -> Optional[SocketIOFrame]:
    """Parse Socket.IO message payload."""
    if not data:
        return None

    # Get Socket.IO packet type
    sio_type = data[0]

    if sio_type not in SOCKETIO_TYPES:
        return None

    sio_packet_type = SOCKETIO_TYPES[sio_type]

    # Handle event (type 2)
    if sio_packet_type == 'event':
        return _parse_event(data[1:], raw)

    # Handle other types
    return SocketIOFrame(type=sio_packet_type, raw=raw)


def _parse_event(data: str, raw: str) -> Optional[SocketIOFrame]:
    """Parse Socket.IO event from JSON array."""
    if not data:
        return None

    try:
        # Event format: ["eventName", data]
        parsed = json.loads(data)

        if isinstance(parsed, list) and len(parsed) >= 1:
            event_name = parsed[0]
            event_data = parsed[1] if len(parsed) > 1 else None

            return SocketIOFrame(
                type='event',
                event_name=event_name,
                data=event_data,
                raw=raw
            )
    except json.JSONDecodeError:
        pass

    return None
```

**Step 4: Run test to verify it passes**

Run: `cd src && python3 -m pytest tests/test_sources/test_socketio_parser.py -v`
Expected: PASS (8 tests)

**Step 5: Commit**

```bash
git add src/sources/socketio_parser.py src/tests/test_sources/test_socketio_parser.py
git commit -m "feat(parser): add Socket.IO frame parser for CDP interception

Parses Engine.IO + Socket.IO protocol frames from raw WebSocket data.
Supports connect, ping/pong, and event packets.

Part of #13"
```

---

## Task 2: CDPWebSocketInterceptor (Core Component)

**Files:**
- Create: `src/sources/cdp_websocket_interceptor.py`
- Test: `src/tests/test_sources/test_cdp_websocket_interceptor.py`
- Reference: `src/browser_automation/cdp_browser_manager.py`

**Step 1: Write the failing test**

```python
# src/tests/test_sources/test_cdp_websocket_interceptor.py
"""Tests for CDP WebSocket Interceptor."""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from sources.cdp_websocket_interceptor import CDPWebSocketInterceptor


class TestCDPWebSocketInterceptor:
    """Test CDP WebSocket interception."""

    def test_init_default_state(self):
        """Interceptor initializes in disconnected state."""
        interceptor = CDPWebSocketInterceptor()

        assert interceptor.is_connected is False
        assert interceptor.rugs_websocket_id is None
        assert interceptor.on_event is None

    def test_set_event_callback(self):
        """Can set event callback."""
        interceptor = CDPWebSocketInterceptor()
        callback = Mock()

        interceptor.on_event = callback

        assert interceptor.on_event is callback

    def test_is_rugs_url(self):
        """Correctly identifies rugs.fun WebSocket URLs."""
        interceptor = CDPWebSocketInterceptor()

        assert interceptor._is_rugs_websocket("wss://backend.rugs.fun/socket.io/")
        assert interceptor._is_rugs_websocket("wss://backend.rugs.fun/socket.io/?EIO=4")
        assert not interceptor._is_rugs_websocket("wss://other.com/socket")
        assert not interceptor._is_rugs_websocket("https://rugs.fun")

    def test_handle_websocket_created(self):
        """Captures WebSocket ID when rugs.fun connection created."""
        interceptor = CDPWebSocketInterceptor()

        interceptor._handle_websocket_created({
            'requestId': 'ws-123',
            'url': 'wss://backend.rugs.fun/socket.io/?EIO=4&transport=websocket'
        })

        assert interceptor.rugs_websocket_id == 'ws-123'

    def test_handle_websocket_created_ignores_other(self):
        """Ignores non-rugs WebSocket connections."""
        interceptor = CDPWebSocketInterceptor()

        interceptor._handle_websocket_created({
            'requestId': 'ws-456',
            'url': 'wss://other.com/socket'
        })

        assert interceptor.rugs_websocket_id is None

    def test_handle_frame_received_emits_event(self):
        """Emits parsed event when frame received."""
        interceptor = CDPWebSocketInterceptor()
        interceptor.rugs_websocket_id = 'ws-123'
        callback = Mock()
        interceptor.on_event = callback

        interceptor._handle_frame_received({
            'requestId': 'ws-123',
            'timestamp': 1234567890.123,
            'response': {
                'payloadData': '42["gameStateUpdate",{"price":1.5}]'
            }
        })

        callback.assert_called_once()
        event = callback.call_args[0][0]
        assert event['event'] == 'gameStateUpdate'
        assert event['data']['price'] == 1.5
        assert event['direction'] == 'received'

    def test_handle_frame_received_ignores_other_websocket(self):
        """Ignores frames from other WebSocket connections."""
        interceptor = CDPWebSocketInterceptor()
        interceptor.rugs_websocket_id = 'ws-123'
        callback = Mock()
        interceptor.on_event = callback

        interceptor._handle_frame_received({
            'requestId': 'ws-OTHER',
            'response': {'payloadData': '42["event",{}]'}
        })

        callback.assert_not_called()

    def test_handle_frame_sent_emits_event(self):
        """Emits parsed event when frame sent."""
        interceptor = CDPWebSocketInterceptor()
        interceptor.rugs_websocket_id = 'ws-123'
        callback = Mock()
        interceptor.on_event = callback

        interceptor._handle_frame_sent({
            'requestId': 'ws-123',
            'timestamp': 1234567890.123,
            'response': {
                'payloadData': '42["buyOrder",{"amount":0.01}]'
            }
        })

        callback.assert_called_once()
        event = callback.call_args[0][0]
        assert event['event'] == 'buyOrder'
        assert event['direction'] == 'sent'

    def test_handle_websocket_closed(self):
        """Clears WebSocket ID when connection closed."""
        interceptor = CDPWebSocketInterceptor()
        interceptor.rugs_websocket_id = 'ws-123'

        interceptor._handle_websocket_closed({
            'requestId': 'ws-123'
        })

        assert interceptor.rugs_websocket_id is None
```

**Step 2: Run test to verify it fails**

Run: `cd src && python3 -m pytest tests/test_sources/test_cdp_websocket_interceptor.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/sources/cdp_websocket_interceptor.py
"""
CDP WebSocket Interceptor

Intercepts WebSocket frames from Chrome via CDP Network domain.
Captures ALL events the browser receives, including authenticated events.
"""
import logging
import threading
from datetime import datetime
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

        # Build event dict
        event = {
            'event': frame.event_name,
            'data': frame.data,
            'timestamp': datetime.fromtimestamp(timestamp).isoformat() if timestamp else datetime.now().isoformat(),
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

    def connect(self, cdp_client) -> bool:
        """
        Connect to CDP and start intercepting.

        Args:
            cdp_client: CDP client with execute() method

        Returns:
            True if connected successfully
        """
        try:
            self._cdp_client = cdp_client

            # Enable Network domain
            cdp_client.execute('Network.enable')

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

    def disconnect(self):
        """Stop intercepting and disconnect."""
        self.is_connected = False
        self.rugs_websocket_id = None
        self._cdp_client = None
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
```

**Step 4: Run test to verify it passes**

Run: `cd src && python3 -m pytest tests/test_sources/test_cdp_websocket_interceptor.py -v`
Expected: PASS (10 tests)

**Step 5: Commit**

```bash
git add src/sources/cdp_websocket_interceptor.py src/tests/test_sources/test_cdp_websocket_interceptor.py
git commit -m "feat(cdp): add CDPWebSocketInterceptor for frame capture

Intercepts WebSocket frames from Chrome via CDP Network domain.
Captures rugs.fun authenticated events (usernameStatus, playerUpdate).

Part of #13"
```

---

## Task 3: Event Bus Extensions

**Files:**
- Modify: `src/services/event_bus.py`
- Test: `src/tests/test_services/test_event_bus.py` (add tests)

**Step 1: Write the failing test**

```python
# Add to src/tests/test_services/test_event_bus.py

class TestWebSocketEvents:
    """Test WebSocket event types."""

    def test_ws_raw_event_exists(self):
        """WS_RAW_EVENT constant exists."""
        from services.event_bus import Events
        assert hasattr(Events, 'WS_RAW_EVENT')
        assert Events.WS_RAW_EVENT == "ws.raw_event"

    def test_ws_auth_event_exists(self):
        """WS_AUTH_EVENT constant exists."""
        from services.event_bus import Events
        assert hasattr(Events, 'WS_AUTH_EVENT')
        assert Events.WS_AUTH_EVENT == "ws.auth_event"

    def test_ws_source_changed_exists(self):
        """WS_SOURCE_CHANGED constant exists."""
        from services.event_bus import Events
        assert hasattr(Events, 'WS_SOURCE_CHANGED')
        assert Events.WS_SOURCE_CHANGED == "ws.source_changed"
```

**Step 2: Run test to verify it fails**

Run: `cd src && python3 -m pytest tests/test_services/test_event_bus.py::TestWebSocketEvents -v`
Expected: FAIL with "AttributeError: type object 'Events' has no attribute 'WS_RAW_EVENT'"

**Step 3: Add event types to Events class**

```python
# In src/services/event_bus.py, add to Events class:

    # WebSocket interception events (Phase 11)
    WS_RAW_EVENT = "ws.raw_event"           # Every frame, unfiltered
    WS_AUTH_EVENT = "ws.auth_event"         # Auth-only events
    WS_SOURCE_CHANGED = "ws.source_changed"  # Source switching ("cdp" or "fallback")
```

**Step 4: Run test to verify it passes**

Run: `cd src && python3 -m pytest tests/test_services/test_event_bus.py::TestWebSocketEvents -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/services/event_bus.py src/tests/test_services/test_event_bus.py
git commit -m "feat(events): add WebSocket interception event types

Adds WS_RAW_EVENT, WS_AUTH_EVENT, WS_SOURCE_CHANGED for CDP interception.

Part of #13"
```

---

## Task 4: RAGIngester (Event Cataloging)

**Files:**
- Create: `src/services/rag_ingester.py`
- Test: `src/tests/test_services/test_rag_ingester.py`

**Step 1: Write the failing test**

```python
# src/tests/test_services/test_rag_ingester.py
"""Tests for RAG event ingestion."""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from services.rag_ingester import RAGIngester


class TestRAGIngester:
    """Test RAG event cataloging."""

    def test_init_creates_capture_dir(self, tmp_path):
        """Ingester creates capture directory if missing."""
        capture_dir = tmp_path / "captures"
        ingester = RAGIngester(capture_dir=capture_dir)

        assert capture_dir.exists()

    def test_start_session_creates_file(self, tmp_path):
        """Starting session creates JSONL file."""
        ingester = RAGIngester(capture_dir=tmp_path)

        filepath = ingester.start_session()

        assert filepath is not None
        assert filepath.exists()
        assert filepath.suffix == '.jsonl'

    def test_catalog_writes_event(self, tmp_path):
        """Cataloging event writes to file."""
        ingester = RAGIngester(capture_dir=tmp_path)
        ingester.start_session()

        event = {
            'event': 'gameStateUpdate',
            'data': {'price': 1.5},
            'timestamp': '2025-12-14T12:00:00',
            'direction': 'received'
        }
        ingester.catalog(event)

        # Read back
        with open(ingester.current_session) as f:
            line = f.readline()
            record = json.loads(line)

        assert record['event'] == 'gameStateUpdate'
        assert record['data']['price'] == 1.5
        assert record['source'] == 'cdp_intercept'

    def test_catalog_tracks_event_counts(self, tmp_path):
        """Cataloging tracks event type counts."""
        ingester = RAGIngester(capture_dir=tmp_path)
        ingester.start_session()

        ingester.catalog({'event': 'gameStateUpdate', 'data': {}})
        ingester.catalog({'event': 'gameStateUpdate', 'data': {}})
        ingester.catalog({'event': 'usernameStatus', 'data': {}})

        assert ingester.event_counts['gameStateUpdate'] == 2
        assert ingester.event_counts['usernameStatus'] == 1

    def test_catalog_detects_novel_events(self, tmp_path):
        """Cataloging detects undocumented events."""
        ingester = RAGIngester(capture_dir=tmp_path)
        ingester.start_session()

        ingester.catalog({'event': 'unknownNewEvent', 'data': {}})

        assert 'unknownNewEvent' in ingester.novel_events

    def test_catalog_known_event_not_novel(self, tmp_path):
        """Known events not flagged as novel."""
        ingester = RAGIngester(capture_dir=tmp_path)
        ingester.start_session()

        ingester.catalog({'event': 'gameStateUpdate', 'data': {}})

        assert 'gameStateUpdate' not in ingester.novel_events

    def test_stop_session_returns_summary(self, tmp_path):
        """Stopping session returns summary."""
        ingester = RAGIngester(capture_dir=tmp_path)
        ingester.start_session()
        ingester.catalog({'event': 'gameStateUpdate', 'data': {}})

        summary = ingester.stop_session()

        assert summary['total_events'] == 1
        assert 'gameStateUpdate' in summary['event_counts']
        assert summary['capture_file'] is not None

    def test_stop_session_closes_file(self, tmp_path):
        """Stopping session closes file handle."""
        ingester = RAGIngester(capture_dir=tmp_path)
        ingester.start_session()

        ingester.stop_session()

        assert ingester.current_session is None
        assert ingester._file_handle is None
```

**Step 2: Run test to verify it fails**

Run: `cd src && python3 -m pytest tests/test_services/test_rag_ingester.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/services/rag_ingester.py
"""
RAG Ingester - Event Cataloging for rugs-expert Agent

Catalogs WebSocket events to JSONL format for RAG pipeline indexing.
Compatible with claude-flow/rag-pipeline/ingestion/event_chunker.py
"""
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)

# Known event types (documented in EVENTS_INDEX.md)
KNOWN_EVENTS = {
    'gameStateUpdate',
    'standard/newTrade',
    'newChatMessage',
    'goldenHourUpdate',
    'goldenHourDrawing',
    'battleEventUpdate',
    'usernameStatus',
    'playerUpdate',
    'connect',
    'disconnect',
}


class RAGIngester:
    """
    Catalogs WebSocket events for RAG pipeline.

    Writes events to JSONL format compatible with claude-flow's
    event_chunker.py for automatic indexing by rugs-expert agent.
    """

    DEFAULT_CAPTURE_DIR = Path('/home/nomad/rugs_recordings/raw_captures')

    def __init__(self, capture_dir: Optional[Path] = None):
        """
        Initialize RAG ingester.

        Args:
            capture_dir: Directory for capture files
        """
        self.capture_dir = capture_dir or self.DEFAULT_CAPTURE_DIR
        self.capture_dir.mkdir(parents=True, exist_ok=True)

        # Session state
        self.current_session: Optional[Path] = None
        self._file_handle = None
        self._lock = threading.Lock()

        # Statistics
        self.sequence_number: int = 0
        self.event_counts: Dict[str, int] = {}
        self.novel_events: Set[str] = set()
        self.start_time: Optional[datetime] = None

        logger.info(f"RAGIngester initialized: {self.capture_dir}")

    def start_session(self) -> Optional[Path]:
        """
        Start a new capture session.

        Returns:
            Path to capture file
        """
        with self._lock:
            if self._file_handle:
                logger.warning("Session already active")
                return self.current_session

            # Generate filename
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            self.current_session = self.capture_dir / f'{timestamp}_cdp.jsonl'

            # Reset state
            self.sequence_number = 0
            self.event_counts = {}
            self.novel_events = set()
            self.start_time = datetime.now()

            # Open file
            self._file_handle = open(self.current_session, 'w', encoding='utf-8')

            logger.info(f"RAG capture session started: {self.current_session}")
            return self.current_session

    def catalog(self, event: Dict[str, Any]):
        """
        Catalog an event for RAG indexing.

        Args:
            event: Event dict with 'event', 'data', 'timestamp', 'direction'
        """
        if not self._file_handle:
            return

        with self._lock:
            self.sequence_number += 1
            event_type = event.get('event', 'unknown')

            # Track counts
            self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1

            # Check for novel events
            if event_type not in KNOWN_EVENTS:
                if event_type not in self.novel_events:
                    self.novel_events.add(event_type)
                    logger.info(f"🆕 Novel event type discovered: {event_type}")

            # Build record (compatible with event_chunker.py)
            record = {
                'seq': self.sequence_number,
                'ts': event.get('timestamp', datetime.now().isoformat()),
                'event': event_type,
                'data': event.get('data'),
                'source': 'cdp_intercept',
                'direction': event.get('direction', 'received')
            }

            try:
                json_line = json.dumps(record, default=str)
                self._file_handle.write(json_line + '\n')
                self._file_handle.flush()
            except Exception as e:
                logger.error(f"Failed to write event: {e}")

    def stop_session(self) -> Optional[Dict[str, Any]]:
        """
        Stop the capture session.

        Returns:
            Summary dict with statistics
        """
        with self._lock:
            if not self._file_handle:
                return None

            # Calculate duration
            duration = None
            if self.start_time:
                duration = (datetime.now() - self.start_time).total_seconds()

            # Build summary
            summary = {
                'capture_file': str(self.current_session),
                'total_events': self.sequence_number,
                'event_counts': dict(self.event_counts),
                'novel_events': list(self.novel_events),
                'duration_seconds': duration
            }

            # Close file
            try:
                self._file_handle.close()
            except Exception:
                pass

            self._file_handle = None
            self.current_session = None

            logger.info(f"RAG capture complete: {summary['total_events']} events")
            if self.novel_events:
                logger.info(f"Novel events discovered: {self.novel_events}")

            return summary

    def get_status(self) -> Dict[str, Any]:
        """Get current session status."""
        with self._lock:
            return {
                'is_active': self._file_handle is not None,
                'capture_file': str(self.current_session) if self.current_session else None,
                'event_count': self.sequence_number,
                'event_types': len(self.event_counts),
                'novel_events': list(self.novel_events)
            }
```

**Step 4: Run test to verify it passes**

Run: `cd src && python3 -m pytest tests/test_services/test_rag_ingester.py -v`
Expected: PASS (8 tests)

**Step 5: Commit**

```bash
git add src/services/rag_ingester.py src/tests/test_services/test_rag_ingester.py
git commit -m "feat(rag): add RAGIngester for event cataloging

Catalogs WebSocket events to JSONL for rugs-expert RAG agent.
Detects novel/undocumented event types automatically.

Part of #13"
```

---

## Task 5: EventSourceManager (Source Switching)

**Files:**
- Create: `src/services/event_source_manager.py`
- Test: `src/tests/test_services/test_event_source_manager.py`

**Step 1: Write the failing test**

```python
# src/tests/test_services/test_event_source_manager.py
"""Tests for EventSourceManager."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from services.event_source_manager import EventSourceManager, EventSource


class TestEventSourceManager:
    """Test event source management."""

    def test_init_default_state(self):
        """Manager initializes with no active source."""
        manager = EventSourceManager()

        assert manager.active_source == EventSource.NONE
        assert manager.is_cdp_available is False

    def test_event_source_enum(self):
        """EventSource enum has correct values."""
        assert EventSource.NONE.value == "none"
        assert EventSource.CDP.value == "cdp"
        assert EventSource.FALLBACK.value == "fallback"

    def test_set_cdp_available(self):
        """Can mark CDP as available."""
        manager = EventSourceManager()

        manager.set_cdp_available(True)

        assert manager.is_cdp_available is True

    def test_switch_to_cdp_when_available(self):
        """Switches to CDP when available."""
        manager = EventSourceManager()
        manager.set_cdp_available(True)
        callback = Mock()
        manager.on_source_changed = callback

        manager.switch_to_best_source()

        assert manager.active_source == EventSource.CDP
        callback.assert_called_with(EventSource.CDP)

    def test_fallback_when_cdp_unavailable(self):
        """Falls back when CDP unavailable."""
        manager = EventSourceManager()
        manager.set_cdp_available(False)
        callback = Mock()
        manager.on_source_changed = callback

        manager.switch_to_best_source()

        assert manager.active_source == EventSource.FALLBACK
        callback.assert_called_with(EventSource.FALLBACK)

    def test_auto_switch_on_cdp_disconnect(self):
        """Auto-switches to fallback on CDP disconnect."""
        manager = EventSourceManager()
        manager.set_cdp_available(True)
        manager.switch_to_best_source()
        assert manager.active_source == EventSource.CDP

        callback = Mock()
        manager.on_source_changed = callback

        manager.set_cdp_available(False)
        manager.switch_to_best_source()

        assert manager.active_source == EventSource.FALLBACK

    def test_get_status(self):
        """Get status returns correct info."""
        manager = EventSourceManager()
        manager.set_cdp_available(True)
        manager.switch_to_best_source()

        status = manager.get_status()

        assert status['active_source'] == 'cdp'
        assert status['is_cdp_available'] is True
```

**Step 2: Run test to verify it fails**

Run: `cd src && python3 -m pytest tests/test_services/test_event_source_manager.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/services/event_source_manager.py
"""
Event Source Manager

Manages switching between CDP (authenticated) and fallback (public) event sources.
"""
import logging
import threading
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class EventSource(Enum):
    """Available event sources."""
    NONE = "none"
    CDP = "cdp"           # Authenticated via CDP interception
    FALLBACK = "fallback"  # Public WebSocketFeed


class EventSourceManager:
    """
    Manages event source selection and switching.

    Prefers CDP (authenticated) when available, falls back to
    WebSocketFeed (public only) when CDP is unavailable.
    """

    def __init__(self):
        """Initialize source manager."""
        self._lock = threading.Lock()

        # State
        self.active_source: EventSource = EventSource.NONE
        self.is_cdp_available: bool = False

        # Callbacks
        self.on_source_changed: Optional[Callable[[EventSource], None]] = None

        logger.info("EventSourceManager initialized")

    def set_cdp_available(self, available: bool):
        """
        Update CDP availability status.

        Args:
            available: Whether CDP interception is available
        """
        with self._lock:
            self.is_cdp_available = available

        logger.info(f"CDP availability: {available}")

    def switch_to_best_source(self):
        """
        Switch to the best available source.

        Prefers CDP when available, falls back otherwise.
        """
        with self._lock:
            new_source = EventSource.CDP if self.is_cdp_available else EventSource.FALLBACK

            if new_source != self.active_source:
                old_source = self.active_source
                self.active_source = new_source

                logger.info(f"Event source: {old_source.value} -> {new_source.value}")

                if self.on_source_changed:
                    try:
                        self.on_source_changed(new_source)
                    except Exception as e:
                        logger.error(f"Error in source changed callback: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        with self._lock:
            return {
                'active_source': self.active_source.value,
                'is_cdp_available': self.is_cdp_available
            }
```

**Step 4: Run test to verify it passes**

Run: `cd src && python3 -m pytest tests/test_services/test_event_source_manager.py -v`
Expected: PASS (7 tests)

**Step 5: Commit**

```bash
git add src/services/event_source_manager.py src/tests/test_services/test_event_source_manager.py
git commit -m "feat(sources): add EventSourceManager for source switching

Manages CDP vs fallback source selection with auto-switching.

Part of #13"
```

---

## Task 6: DebugTerminal UI (Separate Window)

**Files:**
- Create: `src/ui/debug_terminal.py`
- Test: `src/tests/test_ui/test_debug_terminal.py`

**Step 1: Write the failing test**

```python
# src/tests/test_ui/test_debug_terminal.py
"""Tests for Debug Terminal UI."""
import pytest
from unittest.mock import Mock, MagicMock, patch


class TestDebugTerminal:
    """Test Debug Terminal window."""

    @patch('ui.debug_terminal.tk.Toplevel')
    def test_creates_separate_window(self, mock_toplevel):
        """Debug terminal creates separate Toplevel window."""
        from ui.debug_terminal import DebugTerminal

        parent = Mock()
        terminal = DebugTerminal(parent)

        mock_toplevel.assert_called_once_with(parent)

    @patch('ui.debug_terminal.tk.Toplevel')
    def test_window_not_transient(self, mock_toplevel):
        """Window is independent (not transient)."""
        from ui.debug_terminal import DebugTerminal

        mock_window = MagicMock()
        mock_toplevel.return_value = mock_window

        terminal = DebugTerminal(Mock())

        # Should NOT be transient (tied to parent)
        mock_window.transient.assert_not_called()

    @patch('ui.debug_terminal.tk.Toplevel')
    def test_log_event_adds_to_display(self, mock_toplevel):
        """Logging event adds to text display."""
        from ui.debug_terminal import DebugTerminal

        mock_window = MagicMock()
        mock_toplevel.return_value = mock_window

        terminal = DebugTerminal(Mock())
        terminal._log_text = MagicMock()

        event = {
            'event': 'gameStateUpdate',
            'data': {'price': 1.5},
            'timestamp': '2025-12-14T12:00:00'
        }
        terminal.log_event(event)

        terminal._log_text.insert.assert_called()

    @patch('ui.debug_terminal.tk.Toplevel')
    def test_filter_by_event_type(self, mock_toplevel):
        """Can filter events by type."""
        from ui.debug_terminal import DebugTerminal

        terminal = DebugTerminal(Mock())
        terminal.set_filter('usernameStatus')

        assert terminal.current_filter == 'usernameStatus'

    @patch('ui.debug_terminal.tk.Toplevel')
    def test_auth_only_filter(self, mock_toplevel):
        """AUTH_ONLY filter shows only auth events."""
        from ui.debug_terminal import DebugTerminal

        terminal = DebugTerminal(Mock())
        terminal.set_filter('AUTH_ONLY')

        assert terminal._is_filtered({'event': 'gameStateUpdate'}) is True
        assert terminal._is_filtered({'event': 'usernameStatus'}) is False
        assert terminal._is_filtered({'event': 'playerUpdate'}) is False

    @patch('ui.debug_terminal.tk.Toplevel')
    def test_get_color_for_event(self, mock_toplevel):
        """Events have correct colors."""
        from ui.debug_terminal import DebugTerminal

        terminal = DebugTerminal(Mock())

        assert terminal._get_event_color('gameStateUpdate') == '#888888'  # Gray
        assert terminal._get_event_color('usernameStatus') == '#00ff88'   # Green
        assert terminal._get_event_color('playerUpdate') == '#00ffff'     # Cyan
        assert terminal._get_event_color('unknownEvent') == '#ff4444'     # Red (novel)
```

**Step 2: Run test to verify it fails**

Run: `cd src && python3 -m pytest tests/test_ui/test_debug_terminal.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/ui/debug_terminal.py
"""
Debug Terminal - Real-time WebSocket Event Viewer

Displays ALL WebSocket events in a separate, non-blocking window.
Supports filtering and color-coded event types.
"""
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)

# Auth-required events
AUTH_EVENTS = {'usernameStatus', 'playerUpdate', 'buyOrderResponse', 'sellOrderResponse'}

# Known events (non-novel)
KNOWN_EVENTS = {
    'gameStateUpdate', 'standard/newTrade', 'newChatMessage',
    'goldenHourUpdate', 'goldenHourDrawing', 'battleEventUpdate',
    'usernameStatus', 'playerUpdate', 'connect', 'disconnect'
}

# Event colors
EVENT_COLORS = {
    'gameStateUpdate': '#888888',      # Gray - high frequency
    'usernameStatus': '#00ff88',       # Green - auth identity
    'playerUpdate': '#00ffff',         # Cyan - auth balance
    'standard/newTrade': '#ffff00',    # Yellow - trades
    'newChatMessage': '#ffffff',       # White - chat
    'goldenHourUpdate': '#ff8800',     # Orange - lottery
    'goldenHourDrawing': '#ff8800',    # Orange - lottery
    'battleEventUpdate': '#ff00ff',    # Magenta - battle
    'connect': '#00ff00',              # Bright green
    'disconnect': '#ff0000',           # Red
}

DEFAULT_COLOR = '#ff4444'  # Red for novel/unknown events


class DebugTerminal:
    """
    Real-time WebSocket event viewer in separate window.

    Features:
    - Independent Toplevel window (non-blocking)
    - Event filtering by type
    - Color-coded display
    - Live statistics
    """

    def __init__(self, parent):
        """
        Initialize debug terminal.

        Args:
            parent: Parent tkinter widget
        """
        self.parent = parent
        self.current_filter: str = 'ALL'
        self.event_count: int = 0
        self.novel_events: Set[str] = set()

        # Create separate window
        self.window = tk.Toplevel(parent)
        self.window.title("WebSocket Debug Terminal")
        self.window.geometry("1000x600")

        # Don't tie to parent visibility
        # (NOT calling transient - window is independent)

        self._setup_ui()

        logger.info("DebugTerminal window created")

    def _setup_ui(self):
        """Setup UI components."""
        # Top frame - controls
        control_frame = ttk.Frame(self.window)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Filter dropdown
        ttk.Label(control_frame, text="Filter:").pack(side=tk.LEFT)
        self._filter_var = tk.StringVar(value='ALL')
        self._filter_combo = ttk.Combobox(
            control_frame,
            textvariable=self._filter_var,
            values=[
                'ALL',
                'AUTH_ONLY',
                'NOVEL_ONLY',
                '---',
                'gameStateUpdate',
                'usernameStatus',
                'playerUpdate',
                'standard/newTrade',
                'newChatMessage',
            ],
            width=20
        )
        self._filter_combo.pack(side=tk.LEFT, padx=5)
        self._filter_combo.bind('<<ComboboxSelected>>', self._on_filter_changed)

        # Clear button
        ttk.Button(control_frame, text="Clear", command=self._clear_log).pack(side=tk.LEFT, padx=5)

        # Stats label
        self._stats_label = ttk.Label(control_frame, text="Events: 0")
        self._stats_label.pack(side=tk.RIGHT, padx=5)

        # Log display
        self._log_text = ScrolledText(
            self.window,
            font=("JetBrains Mono", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#ffffff",
            wrap=tk.NONE
        )
        self._log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configure tags for colors
        for event_type, color in EVENT_COLORS.items():
            self._log_text.tag_configure(event_type, foreground=color)
        self._log_text.tag_configure('novel', foreground=DEFAULT_COLOR)
        self._log_text.tag_configure('timestamp', foreground='#666666')

    def _on_filter_changed(self, event=None):
        """Handle filter selection change."""
        self.current_filter = self._filter_var.get()
        logger.debug(f"Filter changed to: {self.current_filter}")

    def set_filter(self, filter_type: str):
        """Set event filter programmatically."""
        self.current_filter = filter_type
        self._filter_var.set(filter_type)

    def _is_filtered(self, event: Dict[str, Any]) -> bool:
        """Check if event should be filtered out."""
        event_type = event.get('event', '')

        if self.current_filter == 'ALL':
            return False

        if self.current_filter == 'AUTH_ONLY':
            return event_type not in AUTH_EVENTS

        if self.current_filter == 'NOVEL_ONLY':
            return event_type in KNOWN_EVENTS

        # Specific event type filter
        return event_type != self.current_filter

    def _get_event_color(self, event_type: str) -> str:
        """Get color for event type."""
        if event_type in EVENT_COLORS:
            return EVENT_COLORS[event_type]
        return DEFAULT_COLOR

    def log_event(self, event: Dict[str, Any]):
        """
        Log an event to the display.

        Args:
            event: Event dict with 'event', 'data', 'timestamp'
        """
        if self._is_filtered(event):
            return

        self.event_count += 1
        event_type = event.get('event', 'unknown')

        # Track novel events
        if event_type not in KNOWN_EVENTS:
            self.novel_events.add(event_type)

        # Format line
        timestamp = event.get('timestamp', datetime.now().isoformat())
        if 'T' in timestamp:
            timestamp = timestamp.split('T')[1][:12]  # HH:MM:SS.mmm

        data = event.get('data', {})
        data_preview = self._format_data_preview(event_type, data)

        direction = event.get('direction', 'received')
        direction_symbol = '◀' if direction == 'received' else '▶'

        line = f"[{timestamp}] {direction_symbol} {event_type:<20} {data_preview}\n"

        # Insert with color tag
        tag = event_type if event_type in EVENT_COLORS else 'novel'
        self._log_text.insert(tk.END, line, tag)
        self._log_text.see(tk.END)

        # Update stats
        self._stats_label.config(text=f"Events: {self.event_count}")

    def _format_data_preview(self, event_type: str, data: Any) -> str:
        """Format data preview based on event type."""
        if not isinstance(data, dict):
            return str(data)[:50]

        if event_type == 'gameStateUpdate':
            price = data.get('price', '?')
            tick = data.get('tickCount', '?')
            game_id = data.get('gameId', '?')[:8]
            return f"game={game_id} tick={tick} price={price}"

        if event_type == 'usernameStatus':
            username = data.get('username', '?')
            return f"username={username}"

        if event_type == 'playerUpdate':
            cash = data.get('cash', '?')
            pos = data.get('positionQty', '?')
            return f"cash={cash} pos={pos}"

        if event_type == 'standard/newTrade':
            trade_type = data.get('type', '?')
            username = data.get('username', '?')
            amount = data.get('amount', '?')
            return f"{trade_type} by {username} amt={amount}"

        # Generic preview
        keys = list(data.keys())[:3]
        return ', '.join(f"{k}={data[k]}" for k in keys)[:60]

    def _clear_log(self):
        """Clear the log display."""
        self._log_text.delete(1.0, tk.END)
        self.event_count = 0
        self._stats_label.config(text="Events: 0")

    def show(self):
        """Show the window."""
        self.window.deiconify()
        self.window.lift()

    def hide(self):
        """Hide the window."""
        self.window.withdraw()

    def destroy(self):
        """Destroy the window."""
        self.window.destroy()
```

**Step 4: Run test to verify it passes**

Run: `cd src && python3 -m pytest tests/test_ui/test_debug_terminal.py -v`
Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add src/ui/debug_terminal.py src/tests/test_ui/test_debug_terminal.py
git commit -m "feat(ui): add DebugTerminal for real-time event viewing

Separate window for viewing all WebSocket events with filtering.
Color-coded by event type, detects novel events.

Part of #13"
```

---

## Task 7: MainWindow Integration

**Files:**
- Modify: `src/ui/main_window.py`
- Test: Manual verification (UI integration)

**Step 1: Add menu item and status indicator**

Add to Developer Tools menu (around line 600):

```python
# In _setup_developer_menu():
self.developer_menu.add_separator()
self.developer_menu.add_command(
    label="Open Debug Terminal",
    command=self._open_debug_terminal
)
```

Add handler method:

```python
def _open_debug_terminal(self):
    """Open WebSocket debug terminal window."""
    from ui.debug_terminal import DebugTerminal

    if not hasattr(self, '_debug_terminal') or self._debug_terminal is None:
        self._debug_terminal = DebugTerminal(self.root)

        # Subscribe to raw WebSocket events
        from services.event_bus import Events, event_bus
        event_bus.subscribe(
            Events.WS_RAW_EVENT,
            lambda e: self.ui_dispatcher.submit(
                lambda: self._debug_terminal.log_event(e.get('data', {}))
            )
        )
    else:
        self._debug_terminal.show()
```

Add status bar indicator (in status bar section):

```python
# Event source indicator
self._source_label = ttk.Label(
    self._status_bar,
    text="🔴 No Source",
    font=("Helvetica", 9)
)
self._source_label.pack(side=tk.LEFT, padx=10)
```

Add source change handler:

```python
def _update_source_indicator(self, source):
    """Update event source indicator."""
    from services.event_source_manager import EventSource

    if source == EventSource.CDP:
        text = "🟢 CDP: Authenticated"
        color = '#00ff88'
    elif source == EventSource.FALLBACK:
        text = "🟡 Fallback: Public"
        color = '#ffcc00'
    else:
        text = "🔴 No Source"
        color = '#ff4444'

    def update():
        self._source_label.config(text=text, foreground=color)

    self.ui_dispatcher.submit(update)
```

**Step 2: Commit**

```bash
git add src/ui/main_window.py
git commit -m "feat(ui): integrate Debug Terminal and source indicator

Adds 'Open Debug Terminal' to Developer Tools menu.
Adds event source status indicator to status bar.

Part of #13"
```

---

## Task 8: Wire CDP Interceptor to Browser Bridge

**Files:**
- Modify: `src/bot/browser_bridge.py` (or wherever CDP connection lives)
- Reference: `src/browser_automation/cdp_browser_manager.py`

**Step 1: Initialize interceptor when browser connects**

In the browser bridge connection code, add:

```python
from sources.cdp_websocket_interceptor import CDPWebSocketInterceptor
from services.event_source_manager import EventSourceManager, EventSource
from services.rag_ingester import RAGIngester
from services.event_bus import Events, event_bus

# Initialize components
self._cdp_interceptor = CDPWebSocketInterceptor()
self._event_source_manager = EventSourceManager()
self._rag_ingester = RAGIngester()

# Wire up event flow
def on_cdp_event(event):
    # Publish to EventBus for all subscribers
    event_bus.publish(Events.WS_RAW_EVENT, {'data': event})

    # Catalog for RAG
    self._rag_ingester.catalog(event)

self._cdp_interceptor.on_event = on_cdp_event

# When CDP connects successfully
def on_cdp_connected(cdp_client):
    if self._cdp_interceptor.connect(cdp_client):
        self._event_source_manager.set_cdp_available(True)
        self._event_source_manager.switch_to_best_source()
        self._rag_ingester.start_session()

# When CDP disconnects
def on_cdp_disconnected():
    self._cdp_interceptor.disconnect()
    self._event_source_manager.set_cdp_available(False)
    self._event_source_manager.switch_to_best_source()
    self._rag_ingester.stop_session()
```

**Step 2: Commit**

```bash
git add src/bot/browser_bridge.py
git commit -m "feat(bridge): wire CDP interceptor to browser connection

Starts interception on CDP connect, stops on disconnect.
Events flow to EventBus and RAGIngester.

Part of #13"
```

---

## Task 9: End-to-End Integration Test

**Files:**
- Create: `src/tests/test_integration/test_cdp_event_flow.py`

**Step 1: Write integration test**

```python
# src/tests/test_integration/test_cdp_event_flow.py
"""Integration tests for CDP event flow."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from services.event_bus import Events, event_bus
from sources.cdp_websocket_interceptor import CDPWebSocketInterceptor
from services.event_source_manager import EventSourceManager, EventSource
from services.rag_ingester import RAGIngester


class TestCDPEventFlow:
    """Test end-to-end event flow."""

    def test_cdp_event_reaches_event_bus(self):
        """CDP-intercepted events reach EventBus."""
        interceptor = CDPWebSocketInterceptor()
        received = []

        def on_event(event):
            event_bus.publish(Events.WS_RAW_EVENT, {'data': event})

        interceptor.on_event = on_event
        event_bus.subscribe(Events.WS_RAW_EVENT, lambda e: received.append(e))

        # Simulate CDP frame
        interceptor.rugs_websocket_id = 'ws-123'
        interceptor._handle_frame_received({
            'requestId': 'ws-123',
            'timestamp': 1234567890.0,
            'response': {'payloadData': '42["usernameStatus",{"username":"Dutch"}]'}
        })

        assert len(received) == 1
        assert received[0]['data']['event'] == 'usernameStatus'

    def test_fallback_on_cdp_unavailable(self, tmp_path):
        """Falls back to public feed when CDP unavailable."""
        manager = EventSourceManager()

        # CDP unavailable
        manager.set_cdp_available(False)
        manager.switch_to_best_source()

        assert manager.active_source == EventSource.FALLBACK

    def test_rag_captures_all_events(self, tmp_path):
        """RAG ingester captures all events."""
        ingester = RAGIngester(capture_dir=tmp_path)
        ingester.start_session()

        events = [
            {'event': 'gameStateUpdate', 'data': {'price': 1.5}},
            {'event': 'usernameStatus', 'data': {'username': 'Dutch'}},
            {'event': 'playerUpdate', 'data': {'cash': 5.0}},
        ]

        for event in events:
            ingester.catalog(event)

        summary = ingester.stop_session()

        assert summary['total_events'] == 3
        assert 'gameStateUpdate' in summary['event_counts']
        assert 'usernameStatus' in summary['event_counts']
```

**Step 2: Run test**

Run: `cd src && python3 -m pytest tests/test_integration/test_cdp_event_flow.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/tests/test_integration/test_cdp_event_flow.py
git commit -m "test(integration): add CDP event flow integration tests

Verifies end-to-end event flow from CDP to EventBus and RAG.

Part of #13"
```

---

## Task 10: Documentation Update

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add Phase 11 documentation**

Add to CLAUDE.md:

```markdown
## Phase 11: CDP WebSocket Interception (In Progress)

**Goal**: Capture ALL WebSocket events (including authenticated) via Chrome CDP.

**Components:**
- `CDPWebSocketInterceptor` - Intercepts browser WebSocket frames
- `EventSourceManager` - Switches between CDP and fallback sources
- `RAGIngester` - Catalogs events for rugs-expert agent
- `DebugTerminal` - Real-time event viewer (Developer Tools menu)

**Event Flow:**
```
Chrome (authenticated) → CDP Network.webSocketFrameReceived
    → CDPWebSocketInterceptor → EventBus (WS_RAW_EVENT)
        → GameState handlers
        → RAGIngester (JSONL capture)
        → DebugTerminal (real-time view)
```

**Status Indicators:**
- 🟢 CDP: Authenticated (full events)
- 🟡 Fallback: Public (limited events)
- 🔴 No Source (disconnected)
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add Phase 11 CDP WebSocket interception documentation

Documents new components, event flow, and status indicators.

Closes #13"
```

---

## Summary

| Task | Component | Tests | Status |
|------|-----------|-------|--------|
| 1 | Socket.IO Parser | 8 | Pending |
| 2 | CDPWebSocketInterceptor | 10 | Pending |
| 3 | EventBus Extensions | 3 | Pending |
| 4 | RAGIngester | 8 | Pending |
| 5 | EventSourceManager | 7 | Pending |
| 6 | DebugTerminal | 6 | Pending |
| 7 | MainWindow Integration | Manual | Pending |
| 8 | Browser Bridge Wiring | Manual | Pending |
| 9 | Integration Tests | 3 | Pending |
| 10 | Documentation | N/A | Pending |

**Total: 10 tasks, ~45 tests**

---

**Plan complete and saved to `docs/plans/2025-12-14-cdp-websocket-interception-impl.md`.**

**Two execution options:**

1. **Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

2. **Parallel Session (separate)** - Open new session in worktree with executing-plans, batch execution with checkpoints

**Which approach?**
