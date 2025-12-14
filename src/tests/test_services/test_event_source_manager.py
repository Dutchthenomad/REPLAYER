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
