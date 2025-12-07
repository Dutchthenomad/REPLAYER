# Phase 10.4: WebSocket Verification Layer
**Date**: December 6, 2025 | **Status**: Planning

---

## Objective

Extend `websocket_feed.py` to capture player-specific server state for:
1. **State verification** - Compare local calculations to server truth
2. **Latency tracking** - Measure request-to-confirmation timing
3. **Auto-start recording** - Trigger demo recording on game transitions

**Scope**: Player-specific data only. Excludes rugpool, battle, chat, other players.

---

## Current State

### Captured (9 fields in `_extract_signal`)
```python
gameId, active, rugged, tickCount, price,
cooldownTimer, allowPreRoundBuys, tradeCount, gameHistory
```

### Infrastructure Ready
- Event handler system (`on()`, `remove_handler()`)
- Latency tracking (`LatencySpikeDetector`)
- Health monitoring (`ConnectionHealthMonitor`)
- Graceful degradation (`GracefulDegradationManager`)

---

## Phase 10.4 Changes

### 10.4A: Player Identity Capture

**File**: `src/sources/websocket_feed.py`

Add event handler for `usernameStatus`:

```python
# In _setup_event_listeners():
@self.sio.on('usernameStatus')
def on_username_status(data):
    try:
        self.player_id = data.get('id')  # "did:privy:cm3xxxx"
        self.player_username = data.get('username')
        self.logger.info(f'👤 Player identified: {self.player_username} ({self.player_id})')
        self._emit_event('player_identified', {
            'id': self.player_id,
            'username': self.player_username
        })
    except Exception as e:
        self.logger.error(f"Error in usernameStatus handler: {e}")
        self.metrics['errors'] += 1
```

**Add instance variables**:
```python
# In __init__():
self.player_id: Optional[str] = None
self.player_username: Optional[str] = None
```

---

### 10.4B: Server State Sync

**File**: `src/sources/websocket_feed.py`

Add event handlers for personal state:

```python
@self.sio.on('playerUpdate')
def on_player_update(data):
    try:
        server_state = {
            'cash': Decimal(str(data.get('cash', 0))),
            'position_qty': Decimal(str(data.get('positionQty', 0))),
            'avg_cost': Decimal(str(data.get('avgCost', 0))),
            'cumulative_pnl': Decimal(str(data.get('cumulativePnL', 0))),
            'total_invested': Decimal(str(data.get('totalInvested', 0))),
            'timestamp': time.time()
        }
        self.last_server_state = server_state
        self._emit_event('server_state_update', server_state)
    except Exception as e:
        self.logger.error(f"Error in playerUpdate handler: {e}")
        self.metrics['errors'] += 1

@self.sio.on('gameStatePlayerUpdate')
def on_game_state_player_update(data):
    try:
        # Personal leaderboard entry - same structure as playerUpdate
        self._emit_event('personal_leaderboard', data)
    except Exception as e:
        self.logger.error(f"Error in gameStatePlayerUpdate handler: {e}")
        self.metrics['errors'] += 1
```

**Add instance variable**:
```python
self.last_server_state: Optional[Dict[str, Any]] = None
```

---

### 10.4C: Verification Layer

**New File**: `src/services/state_verifier.py`

```python
"""
State Verification Layer - Compares local state to server truth.

Phase 10.4: Detect drift between local calculations and server state.
"""
from decimal import Decimal
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Tolerance for Decimal comparison (dust threshold)
BALANCE_TOLERANCE = Decimal('0.000001')
POSITION_TOLERANCE = Decimal('0.000001')


class StateVerifier:
    """Compares local GameState to server playerUpdate data."""

    def __init__(self, game_state):
        self.game_state = game_state
        self.last_verification: Optional[Dict[str, Any]] = None
        self.drift_count = 0
        self.total_verifications = 0

    def verify(self, server_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare local state to server truth.

        Args:
            server_state: Dict from playerUpdate event

        Returns:
            Dict with verification results
        """
        self.total_verifications += 1

        local_balance = self.game_state.balance
        server_balance = server_state.get('cash', Decimal('0'))

        local_position = self.game_state.position
        server_position_qty = server_state.get('position_qty', Decimal('0'))
        server_avg_cost = server_state.get('avg_cost', Decimal('0'))

        # Compare balance
        balance_diff = abs(local_balance - server_balance)
        balance_ok = balance_diff <= BALANCE_TOLERANCE

        # Compare position
        local_position_qty = local_position.amount if local_position else Decimal('0')
        position_diff = abs(local_position_qty - server_position_qty)
        position_ok = position_diff <= POSITION_TOLERANCE

        # Compare entry price (if position exists)
        entry_ok = True
        entry_diff = Decimal('0')
        if local_position and server_position_qty > 0:
            local_entry = local_position.entry_price
            entry_diff = abs(local_entry - server_avg_cost)
            entry_ok = entry_diff <= POSITION_TOLERANCE

        # Overall result
        all_ok = balance_ok and position_ok and entry_ok

        if not all_ok:
            self.drift_count += 1
            logger.warning(
                f"State drift detected! "
                f"balance: {local_balance} vs {server_balance} (diff={balance_diff}), "
                f"position: {local_position_qty} vs {server_position_qty} (diff={position_diff})"
            )

        result = {
            'verified': all_ok,
            'balance': {
                'local': local_balance,
                'server': server_balance,
                'diff': balance_diff,
                'ok': balance_ok
            },
            'position': {
                'local_qty': local_position_qty,
                'server_qty': server_position_qty,
                'diff': position_diff,
                'ok': position_ok
            },
            'entry_price': {
                'local': local_position.entry_price if local_position else None,
                'server': server_avg_cost if server_position_qty > 0 else None,
                'diff': entry_diff,
                'ok': entry_ok
            },
            'drift_count': self.drift_count,
            'total_verifications': self.total_verifications
        }

        self.last_verification = result
        return result
```

---

### 10.4D: Integration with TradingController

**File**: `src/ui/controllers/trading_controller.py`

Wire verification to `server_state_update` events:

```python
# In __init__():
from services.state_verifier import StateVerifier
self.state_verifier = StateVerifier(self.game_state)

# Subscribe to server state updates
if self.websocket_feed:
    self.websocket_feed.on('server_state_update', self._on_server_state_update)

def _on_server_state_update(self, server_state: Dict[str, Any]):
    """Handle server state sync - verify local state matches server."""
    result = self.state_verifier.verify(server_state)
    if not result['verified']:
        self.event_bus.publish(Events.STATE_DRIFT_DETECTED, result)
```

---

### 10.4E: Auto-Start Recording (Game Transitions)

**File**: `src/sources/websocket_feed.py`

Emit game transition events for auto-start:

```python
# In _broadcast_signal():
# Detect game start
if validation['previousPhase'] == 'COOLDOWN' and validation['phase'] == 'ACTIVE_GAMEPLAY':
    self._emit_event('game_started', {
        'gameId': signal.gameId,
        'timestamp': signal.timestamp
    })

# Detect game end (rug or cooldown transition)
if signal.rugged or (validation['previousPhase'] == 'ACTIVE_GAMEPLAY' and
                      validation['phase'] in ['RUG_EVENT', 'RUG_EVENT_1', 'COOLDOWN']):
    self._emit_event('game_ended', {
        'gameId': signal.gameId,
        'rugged': signal.rugged,
        'timestamp': signal.timestamp
    })
```

**File**: `src/ui/main_window.py`

Auto-start demo recording on game transitions:

```python
# In _connect_websocket_handlers():
self.websocket_feed.on('game_started', self._on_game_started)
self.websocket_feed.on('game_ended', self._on_game_ended)

def _on_game_started(self, data):
    """Auto-start demo recording if enabled."""
    if self.auto_record_enabled and not self.demo_recording_active:
        self._start_demo_recording()

def _on_game_ended(self, data):
    """Auto-stop demo recording on game end."""
    if self.demo_recording_active:
        self._stop_demo_recording()
```

---

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `src/sources/websocket_feed.py` | Extend | Add 3 new event handlers, player identity tracking |
| `src/services/state_verifier.py` | **New** | State verification logic (~80 lines) |
| `src/ui/controllers/trading_controller.py` | Extend | Wire verification to server updates |
| `src/ui/main_window.py` | Extend | Auto-start recording on game transitions |
| `src/services/event_bus.py` | Extend | Add `STATE_DRIFT_DETECTED` event |

---

## Test Plan (TDD - Tests First)

### Test File: `tests/test_sources/test_websocket_verification.py`

```python
"""Tests for WebSocket verification layer - Phase 10.4"""
import pytest
from unittest.mock import Mock, patch
from decimal import Decimal

class TestUsernameStatus:
    """10.4A: Player identity capture"""

    def test_username_status_captures_player_id(self, websocket_feed):
        """usernameStatus event stores player_id"""
        data = {'id': 'did:privy:cm3xxxx', 'username': 'TestUser'}
        websocket_feed._handle_username_status(data)
        assert websocket_feed.player_id == 'did:privy:cm3xxxx'

    def test_username_status_captures_username(self, websocket_feed):
        """usernameStatus event stores username"""
        data = {'id': 'did:privy:cm3xxxx', 'username': 'TestUser'}
        websocket_feed._handle_username_status(data)
        assert websocket_feed.player_username == 'TestUser'

    def test_username_status_emits_event(self, websocket_feed):
        """usernameStatus emits player_identified event"""
        handler = Mock()
        websocket_feed.on('player_identified', handler)
        data = {'id': 'did:privy:cm3xxxx', 'username': 'TestUser'}
        websocket_feed._handle_username_status(data)
        handler.assert_called_once()


class TestPlayerUpdate:
    """10.4B: Server state sync"""

    def test_player_update_parses_cash(self, websocket_feed):
        """playerUpdate extracts cash as Decimal"""
        data = {'cash': 3.967072345, 'positionQty': 0, 'avgCost': 0}
        websocket_feed._handle_player_update(data)
        assert websocket_feed.last_server_state['cash'] == Decimal('3.967072345')

    def test_player_update_parses_position(self, websocket_feed):
        """playerUpdate extracts position_qty as Decimal"""
        data = {'cash': 1.0, 'positionQty': 0.2222919, 'avgCost': 1.259}
        websocket_feed._handle_player_update(data)
        assert websocket_feed.last_server_state['position_qty'] == Decimal('0.2222919')

    def test_player_update_emits_event(self, websocket_feed):
        """playerUpdate emits server_state_update event"""
        handler = Mock()
        websocket_feed.on('server_state_update', handler)
        data = {'cash': 1.0, 'positionQty': 0, 'avgCost': 0}
        websocket_feed._handle_player_update(data)
        handler.assert_called_once()


class TestGameTransitions:
    """10.4E: Game transition events"""

    def test_game_started_on_cooldown_to_active(self, websocket_feed):
        """game_started emitted on COOLDOWN → ACTIVE_GAMEPLAY"""
        handler = Mock()
        websocket_feed.on('game_started', handler)
        # Simulate transition
        websocket_feed._emit_game_transition('COOLDOWN', 'ACTIVE_GAMEPLAY', 'game123')
        handler.assert_called_once()

    def test_game_ended_on_rug(self, websocket_feed):
        """game_ended emitted when rugged=True"""
        handler = Mock()
        websocket_feed.on('game_ended', handler)
        websocket_feed._emit_game_ended('game123', rugged=True)
        handler.assert_called_once()

    def test_game_ended_on_active_to_cooldown(self, websocket_feed):
        """game_ended emitted on ACTIVE_GAMEPLAY → COOLDOWN"""
        handler = Mock()
        websocket_feed.on('game_ended', handler)
        websocket_feed._emit_game_transition('ACTIVE_GAMEPLAY', 'COOLDOWN', 'game123')
        handler.assert_called_once()
```

### Test File: `tests/test_services/test_state_verifier.py`

```python
"""Tests for StateVerifier - Phase 10.4C"""
import pytest
from decimal import Decimal
from unittest.mock import Mock
from services.state_verifier import StateVerifier

class TestStateVerifier:
    """10.4C: State verification logic"""

    @pytest.fixture
    def mock_game_state(self):
        state = Mock()
        state.balance = Decimal('1.0')
        state.position = None
        return state

    def test_verify_matching_balance(self, mock_game_state):
        """Verification passes when balance matches"""
        verifier = StateVerifier(mock_game_state)
        result = verifier.verify({'cash': Decimal('1.0'), 'position_qty': Decimal('0')})
        assert result['verified'] is True
        assert result['balance']['ok'] is True

    def test_verify_balance_drift(self, mock_game_state):
        """Verification detects balance drift"""
        verifier = StateVerifier(mock_game_state)
        result = verifier.verify({'cash': Decimal('2.0'), 'position_qty': Decimal('0')})
        assert result['verified'] is False
        assert result['balance']['ok'] is False
        assert result['balance']['diff'] == Decimal('1.0')

    def test_verify_position_drift(self, mock_game_state):
        """Verification detects position size drift"""
        mock_game_state.position = Mock()
        mock_game_state.position.amount = Decimal('0.5')
        mock_game_state.position.entry_price = Decimal('1.0')
        verifier = StateVerifier(mock_game_state)
        result = verifier.verify({
            'cash': Decimal('1.0'),
            'position_qty': Decimal('0.3'),
            'avg_cost': Decimal('1.0')
        })
        assert result['verified'] is False
        assert result['position']['ok'] is False

    def test_verify_within_tolerance(self, mock_game_state):
        """Verification passes within tolerance (dust)"""
        mock_game_state.balance = Decimal('1.0000001')
        verifier = StateVerifier(mock_game_state)
        result = verifier.verify({'cash': Decimal('1.0'), 'position_qty': Decimal('0')})
        assert result['verified'] is True  # Within 0.000001 tolerance

    def test_drift_count_increments(self, mock_game_state):
        """Drift count increments on each drift"""
        verifier = StateVerifier(mock_game_state)
        verifier.verify({'cash': Decimal('2.0'), 'position_qty': Decimal('0')})
        verifier.verify({'cash': Decimal('3.0'), 'position_qty': Decimal('0')})
        assert verifier.drift_count == 2
```

### Test File: `tests/test_ui/test_auto_recording.py`

```python
"""Tests for auto-recording on game transitions - Phase 10.4E"""
import pytest
from unittest.mock import Mock, patch

class TestAutoRecording:
    """10.4E: Auto-start/stop demo recording"""

    def test_auto_start_on_game_started(self, main_window):
        """Demo recording starts on game_started when enabled"""
        main_window.auto_record_enabled = True
        main_window.demo_recording_active = False
        main_window._on_game_started({'gameId': 'game123'})
        assert main_window.demo_recording_active is True

    def test_auto_stop_on_game_ended(self, main_window):
        """Demo recording stops on game_ended"""
        main_window.demo_recording_active = True
        main_window._on_game_ended({'gameId': 'game123', 'rugged': True})
        assert main_window.demo_recording_active is False

    def test_auto_record_disabled_by_default(self, main_window):
        """Auto-recording disabled by default"""
        assert main_window.auto_record_enabled is False

    def test_no_auto_start_when_disabled(self, main_window):
        """No auto-start when auto_record_enabled=False"""
        main_window.auto_record_enabled = False
        main_window.demo_recording_active = False
        main_window._on_game_started({'gameId': 'game123'})
        assert main_window.demo_recording_active is False

    def test_no_double_start(self, main_window):
        """No double-start if already recording"""
        main_window.auto_record_enabled = True
        main_window.demo_recording_active = True
        start_mock = Mock()
        main_window._start_demo_recording = start_mock
        main_window._on_game_started({'gameId': 'game123'})
        start_mock.assert_not_called()  # Already recording
```

### Integration Tests (Manual)
1. Connect to live feed, verify player identity logged in console
2. Make trade, verify `playerUpdate` received and logged
3. Enable auto-record, wait for game transition, verify recording starts
4. Wait for rug, verify recording stops automatically

---

## Non-Breaking Integration

**Additive only** - No changes to existing functionality:
- New event handlers alongside existing `gameStateUpdate`
- New `state_verifier.py` module, not modifying core
- New events in EventBus, not removing existing
- Auto-recording is opt-in via `auto_record_enabled` flag

**Fallback** - If player identity not received:
- `player_id` remains `None`
- Verification layer logs warning but doesn't crash
- Manual recording still works

---

## Success Criteria

1. Player identity captured on connection
2. Server state received after each trade
3. State verifier detects drift when local != server
4. Game start/end events emitted on transitions
5. Demo recording auto-starts/stops on game transitions
6. All existing 275+ tests still pass
7. No breaking changes to existing functionality

---

## Estimated Effort

| Task | Effort |
|------|--------|
| 10.4A: Player identity | 1 hour |
| 10.4B: Server state sync | 1 hour |
| 10.4C: Verification layer | 2 hours |
| 10.4D: Controller integration | 1 hour |
| 10.4E: Auto-start recording | 2 hours |
| Tests | 3 hours |
| **Total** | **~10 hours** |

---

*Phase 10.4 Planning Complete | Ready for Implementation*
