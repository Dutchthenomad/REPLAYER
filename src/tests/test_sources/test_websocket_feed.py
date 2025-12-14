"""
Tests for WebSocketFeed - Live game feed integration

Tests cover:
- GameSignal dataclass creation
- GameStateMachine phase detection (6 phases)
- State transition validation
- Tick regression detection
- Signal extraction (9 fields)
- Event handler registration
- Signal to GameTick conversion
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime

from sources import WebSocketFeed, GameSignal, GameStateMachine


class TestGameSignal:
    """Tests for GameSignal dataclass"""

    def test_game_signal_creation(self):
        """Test GameSignal can be created with all required fields"""
        signal = GameSignal(
            gameId="test-game-123",
            active=True,
            rugged=False,
            tickCount=42,
            price=1.5,
            cooldownTimer=0,
            allowPreRoundBuys=False,
            tradeCount=10,
            gameHistory=None
        )

        assert signal.gameId == "test-game-123"
        assert signal.active is True
        assert signal.rugged is False
        assert signal.tickCount == 42
        assert signal.price == 1.5
        assert signal.cooldownTimer == 0
        assert signal.allowPreRoundBuys is False
        assert signal.tradeCount == 10
        assert signal.gameHistory is None

    def test_game_signal_metadata_defaults(self):
        """Test GameSignal metadata fields have defaults"""
        signal = GameSignal(
            gameId="test", active=True, rugged=False, tickCount=0,
            price=1.0, cooldownTimer=0, allowPreRoundBuys=False,
            tradeCount=0, gameHistory=None
        )

        assert signal.phase == "UNKNOWN"
        assert signal.isValid is True
        assert isinstance(signal.timestamp, int)
        assert signal.latency >= 0


class TestGameStateMachine:
    """Tests for GameStateMachine phase detection and validation"""

    def test_active_gameplay_detection(self):
        """Test ACTIVE_GAMEPLAY phase detected correctly"""
        machine = GameStateMachine()

        result = machine.process({
            'active': True,
            'rugged': False,
            'tickCount': 50,
            'gameId': 'game-123',
            'cooldownTimer': 0,
            'allowPreRoundBuys': False,
            'tradeCount': 10
        })

        assert result['phase'] == 'ACTIVE_GAMEPLAY'
        assert result['isValid'] is True

    def test_game_activation_detection(self):
        """Test GAME_ACTIVATION phase (tick 0)"""
        machine = GameStateMachine()

        result = machine.process({
            'active': True,
            'rugged': False,
            'tickCount': 0,
            'gameId': 'game-123',
            'cooldownTimer': 0,
            'allowPreRoundBuys': False,
            'tradeCount': 0
        })

        assert result['phase'] == 'GAME_ACTIVATION'
        assert result['isValid'] is True

    def test_presale_detection(self):
        """Test PRESALE phase (cooldown 10-0 seconds)"""
        machine = GameStateMachine()

        result = machine.process({
            'active': False,
            'rugged': False,
            'tickCount': 0,
            'gameId': 'game-123',
            'cooldownTimer': 5000,  # 5 seconds (within 10-0 range)
            'allowPreRoundBuys': True,
            'tradeCount': 0
        })

        assert result['phase'] == 'PRESALE'
        assert result['isValid'] is True

    def test_cooldown_detection(self):
        """Test COOLDOWN phase (cooldown > 10 seconds)"""
        machine = GameStateMachine()

        result = machine.process({
            'active': False,
            'rugged': True,
            'tickCount': 0,
            'gameId': 'game-123',
            'cooldownTimer': 12000,  # 12 seconds (> 10s)
            'allowPreRoundBuys': False,
            'tradeCount': 0
        })

        assert result['phase'] == 'COOLDOWN'
        assert result['isValid'] is True

    def test_rug_event_1_detection(self):
        """Test RUG_EVENT_1 phase (seed reveal)"""
        machine = GameStateMachine()

        result = machine.process({
            'active': True,
            'rugged': True,
            'tickCount': 100,
            'gameId': 'game-123',
            'cooldownTimer': 0,
            'allowPreRoundBuys': False,
            'tradeCount': 50,
            'gameHistory': [{'id': 'game-123', 'peakMultiplier': 2.5}]
        })

        assert result['phase'] == 'RUG_EVENT_1'
        assert result['isValid'] is True

    def test_rug_event_2_detection(self):
        """Test RUG_EVENT_2 phase (new game setup)"""
        machine = GameStateMachine()

        # First transition to RUG_EVENT_1
        machine.process({
            'active': True,
            'rugged': True,
            'gameId': 'game-123',
            'gameHistory': [{}]
        })

        # Then transition to RUG_EVENT_2
        result = machine.process({
            'active': False,
            'rugged': True,
            'tickCount': 100,
            'gameId': 'game-123',
            'cooldownTimer': 0,
            'allowPreRoundBuys': False,
            'tradeCount': 50,
            'gameHistory': [{'id': 'game-123'}]
        })

        assert result['phase'] == 'RUG_EVENT_2'
        assert result['isValid'] is True

    def test_unknown_phase_detection(self):
        """Test UNKNOWN phase for ambiguous states"""
        machine = GameStateMachine()

        result = machine.process({
            'active': False,
            'rugged': False,
            'tickCount': 0,
            'gameId': 'game-123',
            'cooldownTimer': 0,
            'allowPreRoundBuys': False,
            'tradeCount': 0
        })

        assert result['phase'] == 'UNKNOWN'
        assert result['isValid'] is True

    def test_legal_state_transitions(self):
        """Test legal state transitions are validated correctly"""
        machine = GameStateMachine()

        # GAME_ACTIVATION → ACTIVE_GAMEPLAY (legal)
        result1 = machine.process({
            'active': True,
            'tickCount': 0,
            'rugged': False,
            'gameId': 'game-1'
        })
        assert result1['phase'] == 'GAME_ACTIVATION'

        result2 = machine.process({
            'active': True,
            'tickCount': 1,
            'rugged': False,
            'gameId': 'game-1'
        })
        assert result2['phase'] == 'ACTIVE_GAMEPLAY'
        assert result2['isValid'] is True

    def test_tick_regression_detection(self):
        """Test tick regression is detected and flagged"""
        machine = GameStateMachine()

        # First tick
        machine.process({
            'active': True,
            'tickCount': 50,
            'rugged': False,
            'gameId': 'game-1'
        })

        # Regressed tick (should be invalid)
        result = machine.process({
            'active': True,
            'tickCount': 40,  # Regression from 50 → 40
            'rugged': False,
            'gameId': 'game-1'
        })

        assert result['isValid'] is False

    def test_transition_history_tracking(self):
        """Test transition history is tracked correctly"""
        machine = GameStateMachine()

        machine.process({'active': True, 'tickCount': 0, 'rugged': False, 'gameId': 'g1'})
        machine.process({'active': True, 'tickCount': 1, 'rugged': False, 'gameId': 'g1'})

        assert len(machine.transition_history) > 0
        assert machine.transition_history[-1]['from'] == 'GAME_ACTIVATION'
        assert machine.transition_history[-1]['to'] == 'ACTIVE_GAMEPLAY'

    def test_transition_history_bounded(self):
        """Test transition history is limited to 20 entries"""
        machine = GameStateMachine()

        # Create 25 transitions
        for i in range(25):
            machine.process({
                'active': True if i % 2 == 0 else False,
                'tickCount': 0,
                'rugged': False,
                'gameId': f'game-{i}'
            })

        assert len(machine.transition_history) <= 20


class TestWebSocketFeed:
    """Tests for WebSocketFeed class"""

    @pytest.fixture
    def mock_socketio(self):
        """Mock Socket.IO client"""
        with patch('sources.websocket_feed.socketio.Client') as mock:
            client_instance = MagicMock()
            client_instance.sid = 'test-socket-id'
            mock.return_value = client_instance
            yield client_instance

    def test_websocket_feed_initialization(self, mock_socketio):
        """Test WebSocketFeed initializes correctly"""
        feed = WebSocketFeed(log_level='WARN')

        assert feed.server_url == 'https://backend.rugs.fun?frontend-version=1.0'
        assert feed.is_connected is False
        assert feed.last_signal is None
        assert isinstance(feed.state_machine, GameStateMachine)

    def test_signal_extraction(self, mock_socketio):
        """Test _extract_signal extracts only 9 fields"""
        feed = WebSocketFeed(log_level='ERROR')

        raw_data = {
            'gameId': 'test-123',
            'active': True,
            'rugged': False,
            'tickCount': 42,
            'price': 1.5,
            'cooldownTimer': 0,
            'allowPreRoundBuys': False,
            'tradeCount': 10,
            'gameHistory': None,
            # Noise fields (should be ignored)
            'leaderboard': [],
            'connectedPlayers': 100,
            'candles': [],
            'provablyFair': {}
        }

        signal = feed._extract_signal(raw_data)

        assert len(signal) == 9
        assert signal['gameId'] == 'test-123'
        assert signal['active'] is True
        assert signal['rugged'] is False
        assert signal['tickCount'] == 42
        assert signal['price'] == 1.5
        assert signal['cooldownTimer'] == 0
        assert signal['allowPreRoundBuys'] is False
        assert signal['tradeCount'] == 10
        assert signal['gameHistory'] is None

        # Noise fields should NOT be present
        assert 'leaderboard' not in signal
        assert 'connectedPlayers' not in signal
        assert 'candles' not in signal

    def test_event_handler_registration(self, mock_socketio):
        """Test event handlers can be registered"""
        feed = WebSocketFeed(log_level='ERROR')

        callback_called = []

        @feed.on('signal')
        def handler(signal):
            callback_called.append(signal)

        assert 'signal' in feed.event_handlers
        assert len(feed.event_handlers['signal']) == 1

    def test_event_emission(self, mock_socketio):
        """Test events are emitted to registered handlers"""
        feed = WebSocketFeed(log_level='ERROR')

        received_data = []

        @feed.on('test_event')
        def handler(data):
            received_data.append(data)

        feed._emit_event('test_event', {'value': 42})

        assert len(received_data) == 1
        assert received_data[0]['value'] == 42

    def test_signal_to_game_tick_conversion(self, mock_socketio):
        """Test GameSignal converts to GameTick correctly"""
        feed = WebSocketFeed(log_level='ERROR')

        signal = GameSignal(
            gameId="test-game",
            active=True,
            rugged=False,
            tickCount=42,
            price=1.5,
            cooldownTimer=0,
            allowPreRoundBuys=False,
            tradeCount=10,
            gameHistory=None,
            phase="ACTIVE_GAMEPLAY",
            timestamp=1700000000000  # Example timestamp
        )

        tick = feed.signal_to_game_tick(signal)

        assert tick.game_id == "test-game"
        assert tick.tick == 42
        assert tick.price == Decimal("1.5")
        assert tick.phase == "ACTIVE_GAMEPLAY"
        assert tick.active is True
        assert tick.rugged is False
        assert tick.cooldown_timer == 0
        assert tick.trade_count == 10

    def test_metrics_tracking(self, mock_socketio):
        """Test metrics are tracked correctly"""
        feed = WebSocketFeed(log_level='ERROR')

        assert feed.metrics['total_signals'] == 0
        assert feed.metrics['total_ticks'] == 0
        assert feed.metrics['total_games'] == 0
        assert feed.metrics['noise_filtered'] == 0

    def test_get_metrics_summary(self, mock_socketio):
        """Test get_metrics returns correct summary"""
        feed = WebSocketFeed(log_level='ERROR')

        metrics = feed.get_metrics()

        assert 'uptime' in metrics
        assert 'totalSignals' in metrics
        assert 'totalTicks' in metrics
        assert 'totalGames' in metrics
        assert 'noiseFiltered' in metrics
        assert 'currentPhase' in metrics
        assert 'avgLatency' in metrics

    def test_get_last_signal(self, mock_socketio):
        """Test get_last_signal returns None initially"""
        feed = WebSocketFeed(log_level='ERROR')

        assert feed.get_last_signal() is None

    def test_player_identity_event_emission(self, mock_socketio):
        """Test player_identity event is emitted correctly"""
        feed = WebSocketFeed(log_level='ERROR')

        received_events = []

        @feed.on('player_identity')
        def handler(data):
            received_events.append(data)

        # Simulate emitting player_identity
        feed._emit_event('player_identity', {
            'player_id': 'did:privy:test123',
            'username': 'TestPlayer'
        })

        assert len(received_events) == 1
        assert received_events[0]['player_id'] == 'did:privy:test123'
        assert received_events[0]['username'] == 'TestPlayer'

    def test_player_update_event_emission(self, mock_socketio):
        """Test player_update event is emitted correctly"""
        feed = WebSocketFeed(log_level='ERROR')

        received_events = []

        @feed.on('player_update')
        def handler(data):
            received_events.append(data)

        # Simulate emitting player_update
        update_data = {
            'cash': 5.0,
            'positionQty': 1.0,
            'avgCost': 1.5,
            'cumulativePnL': 0.5,
            'totalInvested': 1.5
        }
        feed._emit_event('player_update', update_data)

        assert len(received_events) == 1
        assert received_events[0]['cash'] == 5.0
        assert received_events[0]['positionQty'] == 1.0

    def test_player_leaderboard_event_emission(self, mock_socketio):
        """Test player_leaderboard event is emitted correctly"""
        feed = WebSocketFeed(log_level='ERROR')

        received_events = []

        @feed.on('player_leaderboard')
        def handler(data):
            received_events.append(data)

        # Simulate emitting player_leaderboard
        leaderboard_data = {
            'rank': 1164,
            'total': 2595,
            'player_entry': {
                'playerId': 'did:privy:test123',
                'username': 'TestPlayer',
                'pnl': -0.015559657
            }
        }
        feed._emit_event('player_leaderboard', leaderboard_data)

        assert len(received_events) == 1
        assert received_events[0]['rank'] == 1164
        assert received_events[0]['total'] == 2595
        assert received_events[0]['player_entry']['username'] == 'TestPlayer'

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
