"""
Tests for EventBus
"""

import pytest
from services import event_bus, Events
from services.event_bus import EventBus


class TestEventBusSubscription:
    """Tests for event subscription"""

    def test_subscribe_to_event(self):
        """Test subscribing to an event"""
        received_events = []

        def handler(data):
            received_events.append(data)

        event_bus.subscribe(Events.TRADE_BUY, handler)

        # Event should be in subscribers
        assert Events.TRADE_BUY in event_bus._subscribers
        assert handler in event_bus._subscribers[Events.TRADE_BUY]

    def test_unsubscribe_from_event(self):
        """Test unsubscribing from an event"""
        received_events = []

        def handler(data):
            received_events.append(data)

        event_bus.subscribe(Events.TRADE_BUY, handler)
        event_bus.unsubscribe(Events.TRADE_BUY, handler)

        # Handler should be removed
        if Events.TRADE_BUY in event_bus._subscribers:
            assert handler not in event_bus._subscribers[Events.TRADE_BUY]

    def test_multiple_handlers_same_event(self):
        """Test multiple handlers for same event"""
        received_1 = []
        received_2 = []

        def handler1(data):
            received_1.append(data)

        def handler2(data):
            received_2.append(data)

        event_bus.subscribe(Events.TRADE_BUY, handler1)
        event_bus.subscribe(Events.TRADE_BUY, handler2)

        event_bus.publish(Events.TRADE_BUY, {'test': 'data'})

        assert len(received_1) == 1
        assert len(received_2) == 1


class TestEventBusPublishing:
    """Tests for event publishing"""

    def test_publish_event(self):
        """Test publishing an event"""
        received_events = []

        def handler(data):
            received_events.append(data)

        event_bus.subscribe(Events.TRADE_BUY, handler)
        event_bus.publish(Events.TRADE_BUY, {'test': 'data'})

        assert len(received_events) == 1
        assert received_events[0]['test'] == 'data'

    def test_publish_event_with_no_subscribers(self):
        """Test publishing event with no subscribers doesn't error"""
        # Should not raise exception
        event_bus.publish(Events.TRADE_SELL, {'test': 'data'})

    def test_publish_multiple_events(self):
        """Test publishing multiple events"""
        received_events = []

        def handler(data):
            received_events.append(data)

        event_bus.subscribe(Events.TRADE_BUY, handler)

        event_bus.publish(Events.TRADE_BUY, {'event': 1})
        event_bus.publish(Events.TRADE_BUY, {'event': 2})
        event_bus.publish(Events.TRADE_BUY, {'event': 3})

        assert len(received_events) == 3
        assert received_events[0]['event'] == 1
        assert received_events[1]['event'] == 2
        assert received_events[2]['event'] == 3

    def test_publish_different_events(self):
        """Test publishing different event types"""
        buy_events = []
        sell_events = []

        def buy_handler(data):
            buy_events.append(data)

        def sell_handler(data):
            sell_events.append(data)

        event_bus.subscribe(Events.TRADE_BUY, buy_handler)
        event_bus.subscribe(Events.TRADE_SELL, sell_handler)

        event_bus.publish(Events.TRADE_BUY, {'type': 'buy'})
        event_bus.publish(Events.TRADE_SELL, {'type': 'sell'})

        assert len(buy_events) == 1
        assert len(sell_events) == 1
        assert buy_events[0]['type'] == 'buy'
        assert sell_events[0]['type'] == 'sell'


class TestEventBusStatistics:
    """Tests for event bus statistics"""

    def test_get_stats(self):
        """Test getting event bus statistics"""
        stats = event_bus.get_stats()

        assert isinstance(stats, dict)
        assert 'events_published' in stats

    def test_stats_increment_on_publish(self):
        """Test statistics increment when events published"""
        initial_stats = event_bus.get_stats()
        initial_count = initial_stats.get('events_published', 0)

        event_bus.publish(Events.TRADE_BUY, {'test': 'data'})

        new_stats = event_bus.get_stats()
        new_count = new_stats.get('events_published', 0)

        assert new_count > initial_count


class TestEventBusEventTypes:
    """Tests for event types"""

    def test_event_types_exist(self):
        """Test all expected event types exist"""
        assert hasattr(Events, 'TRADE_BUY')
        assert hasattr(Events, 'TRADE_SELL')
        assert hasattr(Events, 'TRADE_SIDEBET')
        assert hasattr(Events, 'FILE_LOADED')
        assert hasattr(Events, 'GAME_TICK')

    def test_subscribe_to_all_event_types(self):
        """Test subscribing to all event types"""
        def handler(data):
            pass

        # Should not raise exceptions
        event_bus.subscribe(Events.TRADE_BUY, handler)
        event_bus.subscribe(Events.TRADE_SELL, handler)
        event_bus.subscribe(Events.TRADE_SIDEBET, handler)
        event_bus.subscribe(Events.FILE_LOADED, handler)
        event_bus.subscribe(Events.GAME_TICK, handler)


class TestEventBusErrorHandling:
    """Tests for error handling"""

    def test_handler_exception_doesnt_break_other_handlers(self):
        """Test exception in one handler doesn't affect others"""
        received = []

        def bad_handler(data):
            raise Exception("Handler error")

        def good_handler(data):
            received.append(data)

        event_bus.subscribe(Events.TRADE_BUY, bad_handler)
        event_bus.subscribe(Events.TRADE_BUY, good_handler)

        # Should not raise, and good handler should still receive event
        event_bus.publish(Events.TRADE_BUY, {'test': 'data'})

        # Good handler should have received the event
        assert len(received) == 1


class TestEventBusShutdown:
    """Tests for graceful shutdown logic"""

    def test_stop_handles_full_queue(self):
        """Stopping should succeed even when queue is full"""
        local_bus = EventBus(max_queue_size=1)
        local_bus._processing = True
        local_bus._thread = None
        local_bus._queue.put_nowait((Events.GAME_TICK, {}))

        local_bus.stop()

        assert local_bus._processing is False
