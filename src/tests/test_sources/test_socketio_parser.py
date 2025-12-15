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
