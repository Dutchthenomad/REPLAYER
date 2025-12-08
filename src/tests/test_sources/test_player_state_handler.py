"""
Tests for player_state_handler.py - Phase 10.4C

TDD: Tests written FIRST before implementation.

Tests cover:
- PlayerStateHandler: player identity, server state, events
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock

# This import will FAIL until we create the module (TDD RED phase)
from sources.player_state_handler import PlayerStateHandler


class TestPlayerStateHandler:
    """Tests for PlayerStateHandler"""

    def test_initialization(self):
        """Test default initialization"""
        handler = PlayerStateHandler()
        assert handler.player_id is None
        assert handler.player_username is None
        assert handler.last_server_state is None

    def test_handle_username_status(self):
        """Test usernameStatus event sets player identity"""
        handler = PlayerStateHandler()

        handler.handle_username_status({
            'id': 'did:privy:cm3xxx',
            'username': 'Dutch'
        })

        assert handler.player_id == 'did:privy:cm3xxx'
        assert handler.player_username == 'Dutch'

    def test_handle_username_status_emits_event(self):
        """Test usernameStatus emits player_identified event"""
        handler = PlayerStateHandler()
        received = []

        def callback(data):
            received.append(data)

        handler.on('player_identified', callback)
        handler.handle_username_status({
            'id': 'did:privy:test',
            'username': 'TestUser'
        })

        assert len(received) == 1
        assert received[0]['player_id'] == 'did:privy:test'
        assert received[0]['username'] == 'TestUser'

    def test_handle_player_update(self):
        """Test playerUpdate event stores server state"""
        handler = PlayerStateHandler()

        handler.handle_player_update({
            'cash': 1.5,
            'positionQty': 0.001,
            'avgCost': 1.234,
            'cumulativePnL': 0.05,
            'totalInvested': 0.1
        })

        assert handler.last_server_state is not None
        assert handler.last_server_state['cash'] == Decimal('1.5')
        assert handler.last_server_state['position_qty'] == Decimal('0.001')
        assert handler.last_server_state['avg_cost'] == Decimal('1.234')
        assert handler.last_server_state['cumulative_pnl'] == Decimal('0.05')
        assert handler.last_server_state['total_invested'] == Decimal('0.1')

    def test_handle_player_update_emits_event(self):
        """Test playerUpdate emits server_state_update event"""
        handler = PlayerStateHandler()
        received = []

        def callback(data):
            received.append(data)

        handler.on('server_state_update', callback)
        handler.handle_player_update({
            'cash': 1.0,
            'positionQty': 0,
            'avgCost': 0,
            'cumulativePnL': 0,
            'totalInvested': 0
        })

        assert len(received) == 1
        assert received[0]['cash'] == Decimal('1.0')

    def test_handle_game_state_player_update(self):
        """Test gameStatePlayerUpdate emits personal_leaderboard event"""
        handler = PlayerStateHandler()
        received = []

        def callback(data):
            received.append(data)

        handler.on('personal_leaderboard', callback)
        handler.handle_game_state_player_update({
            'rank': 5,
            'username': 'Dutch',
            'pnl': '0.05'
        })

        assert len(received) == 1
        assert received[0]['rank'] == 5

    def test_event_handler_registration(self):
        """Test event handler can be registered"""
        handler = PlayerStateHandler()
        callback = MagicMock()

        handler.on('test_event', callback)

        # Handler should be registered
        assert 'test_event' in handler._event_handlers
        assert callback in handler._event_handlers['test_event']

    def test_multiple_event_handlers(self):
        """Test multiple handlers for same event"""
        handler = PlayerStateHandler()
        received1 = []
        received2 = []

        handler.on('player_identified', lambda d: received1.append(d))
        handler.on('player_identified', lambda d: received2.append(d))

        handler.handle_username_status({
            'id': 'test',
            'username': 'Test'
        })

        assert len(received1) == 1
        assert len(received2) == 1

    def test_handler_error_isolation(self):
        """Test handler errors don't affect other handlers"""
        handler = PlayerStateHandler()
        received = []

        def bad_handler(data):
            raise Exception("Handler error")

        def good_handler(data):
            received.append(data)

        handler.on('player_identified', bad_handler)
        handler.on('player_identified', good_handler)

        # Should not raise, should call good_handler
        handler.handle_username_status({
            'id': 'test',
            'username': 'Test'
        })

        assert len(received) == 1

    def test_handle_player_update_default_values(self):
        """Test playerUpdate handles missing fields"""
        handler = PlayerStateHandler()

        handler.handle_player_update({})

        assert handler.last_server_state['cash'] == Decimal('0')
        assert handler.last_server_state['position_qty'] == Decimal('0')

    def test_get_player_info(self):
        """Test getting player info"""
        handler = PlayerStateHandler()
        handler.handle_username_status({
            'id': 'did:privy:cm3xxx',
            'username': 'Dutch'
        })

        info = handler.get_player_info()

        assert info['player_id'] == 'did:privy:cm3xxx'
        assert info['username'] == 'Dutch'

    def test_get_player_info_unidentified(self):
        """Test getting player info before identification"""
        handler = PlayerStateHandler()

        info = handler.get_player_info()

        assert info['player_id'] is None
        assert info['username'] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
