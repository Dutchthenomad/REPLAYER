"""Integration tests for CDP event flow."""
import pytest
import time
import threading
from unittest.mock import Mock, MagicMock, patch
from services.event_bus import Events, event_bus
from sources.cdp_websocket_interceptor import CDPWebSocketInterceptor
from services.event_source_manager import EventSourceManager, EventSource
from services.rag_ingester import RAGIngester


class TestCDPEventFlow:
    """Test end-to-end event flow."""

    def setup_method(self):
        """Clean up event bus subscriptions before each test."""
        # Store original subscribers to restore later
        self._original_subscribers = event_bus._subscribers.copy()
        self._original_callback_ids = event_bus._callback_ids.copy()

        # Ensure event bus is started
        if not event_bus._processing:
            event_bus.start()

    def teardown_method(self):
        """Restore event bus state after each test."""
        event_bus._subscribers = self._original_subscribers
        event_bus._callback_ids = self._original_callback_ids

    def test_cdp_event_reaches_event_bus(self):
        """CDP-intercepted events reach EventBus."""
        interceptor = CDPWebSocketInterceptor()
        received = []
        event_received = threading.Event()

        def on_event(event):
            event_bus.publish(Events.WS_RAW_EVENT, {'data': event})

        def subscriber(e):
            received.append(e)
            event_received.set()

        interceptor.on_event = on_event
        event_bus.subscribe(Events.WS_RAW_EVENT, subscriber, weak=False)

        # Simulate CDP frame
        interceptor.rugs_websocket_id = 'ws-123'
        interceptor._handle_frame_received({
            'requestId': 'ws-123',
            'timestamp': 1234567890.0,
            'response': {'payloadData': '42["usernameStatus",{"username":"Dutch"}]'}
        })

        # Wait for event to be processed (with timeout)
        assert event_received.wait(timeout=1.0), "Event was not received within timeout"

        assert len(received) == 1
        # EventBus wraps events as: {'name': event_name, 'data': payload}
        # Our payload is: {'data': {actual_event_data}}
        # So we need to unwrap twice
        assert 'data' in received[0]
        assert 'data' in received[0]['data']
        event_data = received[0]['data']['data']
        assert event_data['event'] == 'usernameStatus'

    def test_fallback_on_cdp_unavailable(self):
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
