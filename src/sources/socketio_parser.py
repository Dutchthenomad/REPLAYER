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
