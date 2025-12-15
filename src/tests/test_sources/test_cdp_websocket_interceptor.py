"""Tests for CDP WebSocket Interceptor."""
import asyncio
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
        assert "timestamp" in event

    def test_handle_frame_received_maps_monotonic_timestamp_to_wall_clock(self):
        """
        CDP `timestamp` values are monotonic, not epoch.

        For monotonic timestamps, interceptor should map them to a reasonable
        wall-clock epoch using a captured base offset.
        """
        interceptor = CDPWebSocketInterceptor()
        interceptor.rugs_websocket_id = "ws-123"
        callback = Mock()
        interceptor.on_event = callback

        with patch("sources.cdp_websocket_interceptor.time.time", return_value=1700000000.0):
            interceptor._handle_frame_received(
                {
                    "requestId": "ws-123",
                    "timestamp": 100.0,
                    "response": {"payloadData": '42["gameStateUpdate",{"price":1.5}]'},
                }
            )
            interceptor._handle_frame_received(
                {
                    "requestId": "ws-123",
                    "timestamp": 101.5,
                    "response": {"payloadData": '42["gameStateUpdate",{"price":1.6}]'},
                }
            )

        assert callback.call_count == 2
        first = callback.call_args_list[0][0][0]
        second = callback.call_args_list[1][0][0]

        assert first["timestamp"].startswith("2023") or first["timestamp"].startswith("2024")
        assert second["timestamp"].startswith("2023") or second["timestamp"].startswith("2024")
        assert first["timestamp"] != second["timestamp"]

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

    def test_disconnect_clears_state(self):
        """Disconnect clears all state and disables Network domain."""
        interceptor = CDPWebSocketInterceptor()
        interceptor.is_connected = True
        interceptor.rugs_websocket_id = 'ws-123'
        mock_client = Mock()
        mock_client.send = AsyncMock()
        interceptor._cdp_client = mock_client

        asyncio.run(interceptor.disconnect())

        assert interceptor.is_connected is False
        assert interceptor.rugs_websocket_id is None
        assert interceptor._cdp_client is None
        mock_client.send.assert_called_with('Network.disable')

    def test_disconnect_handles_missing_client(self):
        """Disconnect handles case where client is None."""
        interceptor = CDPWebSocketInterceptor()
        interceptor.is_connected = True
        interceptor._cdp_client = None

        # Should not raise exception
        asyncio.run(interceptor.disconnect())

        assert interceptor.is_connected is False

    def test_disconnect_handles_network_disable_error(self):
        """Disconnect continues even if Network.disable fails."""
        interceptor = CDPWebSocketInterceptor()
        interceptor.is_connected = True
        mock_client = Mock()
        mock_client.send = AsyncMock(side_effect=Exception("CDP error"))
        interceptor._cdp_client = mock_client

        # Should not raise exception
        asyncio.run(interceptor.disconnect())

        assert interceptor.is_connected is False
        assert interceptor._cdp_client is None
