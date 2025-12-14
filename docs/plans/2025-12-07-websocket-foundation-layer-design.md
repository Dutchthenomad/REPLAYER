# WebSocket Foundation Layer Design
**Phase 10.4 Revised** | **Date**: December 7, 2025 | **Status**: Complete

---

## 1. Overview

### Purpose
Build the data foundation for RL/ML training by capturing complete, accurate game and player state from the WebSocket feed.

### Primary Driver
**Training Data Quality** - The foundation layer upon which all advanced ML/RL models will be built. Garbage in = garbage out. This must be rock solid.

### Vision
- Record human gameplay with complete context (prices + actions)
- Enable "player piano" bot mode - visually play through UI with animated buttons
- Provide data for mathematically/statistically optimal gameplay development
- Support future advanced features (PRNG analysis, Bayesian probabilities, treasury algorithm reverse engineering)

---

## 2. Data Architecture

### Two Distinct Layers

#### Game State Layer (the "board")
- Tick-by-tick price data
- Pure market data, no player-specific info
- One file per game
- Used for: chart animation, ML training context

#### Player State Layer (the "moves")
- Actions (BUY, SELL, SIDEBET)
- Balance, position, PnL at each action
- Links to game state via `game_id + tick`
- Used for: action replay, bot ghost mode, ML training labels

### Data Flow
```
WebSocket Events                    Storage
─────────────────                   ───────
gameStateUpdate.price      ───────► Game State File (prices array)
gameStateUpdate.partialPrices ────► Gap filling in prices array
usernameStatus             ───────► Player identity (session metadata)
playerUpdate               ───────► Server state verification
User actions (BUY/SELL)    ───────► Player State File (actions array)
```

---

## 3. File Structure

### Directory Layout
```
recordings/
├── 2025-12-07/
│   ├── games/
│   │   ├── 20251207T143022_e9ac71e7.game.json
│   │   └── 20251207T143245_f8bd92a3.game.json
│   ├── sessions/
│   │   └── 20251207T143000_dutch_session.json
│   └── index.json  ← sortable metadata for all games
```

### Game State File Format
**Filename**: `{ISO_timestamp}_{game_id_short}.game.json`

```json
{
  "meta": {
    "game_id": "20251207-e9ac71e78ebe4f83",
    "start_time": "2025-12-07T14:30:22.456Z",
    "end_time": "2025-12-07T14:32:45.789Z",
    "duration_ticks": 143,
    "peak_multiplier": "45.23",
    "server_seed_hash": "abc123...",
    "server_seed": "xyz789..."
  },
  "prices": ["1.0", "1.01", "0.99", "1.03", ...]
}
```

### Player State File Format
**Filename**: `{ISO_timestamp}_{username}_session.json`

```json
{
  "meta": {
    "player_id": "did:privy:cm3xxx",
    "username": "Dutch",
    "session_start": "2025-12-07T14:30:00.000Z",
    "session_end": "2025-12-07T15:45:00.000Z"
  },
  "actions": [
    {
      "game_id": "20251207-e9ac71e78ebe4f83",
      "tick": 12,
      "timestamp": "2025-12-07T14:30:34.567Z",
      "action": "BUY",
      "amount": "0.001",
      "price": "1.234",
      "balance_after": "0.999",
      "position_qty_after": "0.001",
      "entry_price": "1.234",
      "pnl": null
    }
  ]
}
```

### Index File Format
**Filename**: `index.json`

```json
{
  "date": "2025-12-07",
  "games": [
    {
      "file": "20251207T143022_e9ac71e7.game.json",
      "game_id": "20251207-e9ac71e78ebe4f83",
      "start_time": "2025-12-07T14:30:22.456Z",
      "duration_ticks": 143,
      "peak_multiplier": "45.23"
    }
  ],
  "sessions": [
    {
      "file": "20251207T143000_dutch_session.json",
      "player_id": "did:privy:cm3xxx",
      "username": "Dutch",
      "games_played": 2,
      "total_actions": 15
    }
  ]
}
```

---

## 4. Data Models (Python)

### Location: `src/models/recording_models.py`

```python
"""
Recording Data Models - Phase 10.4 Foundation Layer

Separate models for game state and player state recordings.
All monetary values stored as Decimal for precision.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import json


@dataclass
class GameStateMeta:
    """Metadata for a single game recording."""
    game_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ticks: int = 0
    peak_multiplier: Decimal = Decimal("1.0")
    server_seed_hash: Optional[str] = None
    server_seed: Optional[str] = None


@dataclass
class GameStateRecord:
    """Complete game state - prices tick by tick."""
    meta: GameStateMeta
    prices: List[Decimal] = field(default_factory=list)

    def add_price(self, tick: int, price: Decimal):
        """Add price at tick, extending array if needed."""
        while len(self.prices) <= tick:
            self.prices.append(None)
        self.prices[tick] = price

    def fill_gaps(self, partial_prices: dict):
        """Fill gaps using partialPrices data from WebSocket."""
        for tick_str, price in partial_prices.items():
            tick = int(tick_str)
            if tick < len(self.prices) and self.prices[tick] is None:
                self.prices[tick] = Decimal(str(price))

    def has_gaps(self) -> bool:
        """Check if any ticks are missing."""
        return None in self.prices

    def to_dict(self) -> dict:
        """Serialize for JSON storage."""
        return {
            "meta": {
                "game_id": self.meta.game_id,
                "start_time": self.meta.start_time.isoformat(),
                "end_time": self.meta.end_time.isoformat() if self.meta.end_time else None,
                "duration_ticks": self.meta.duration_ticks,
                "peak_multiplier": str(self.meta.peak_multiplier),
                "server_seed_hash": self.meta.server_seed_hash,
                "server_seed": self.meta.server_seed,
            },
            "prices": [str(p) if p is not None else None for p in self.prices]
        }


@dataclass
class PlayerAction:
    """Single player action with state snapshot."""
    game_id: str
    tick: int
    timestamp: datetime
    action: str  # BUY, SELL, SIDEBET_PLACE, SIDEBET_WIN, SIDEBET_LOSE
    amount: Decimal
    price: Decimal
    balance_after: Decimal
    position_qty_after: Decimal
    entry_price: Optional[Decimal] = None
    pnl: Optional[Decimal] = None

    def to_dict(self) -> dict:
        """Serialize for JSON storage."""
        return {
            "game_id": self.game_id,
            "tick": self.tick,
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "amount": str(self.amount),
            "price": str(self.price),
            "balance_after": str(self.balance_after),
            "position_qty_after": str(self.position_qty_after),
            "entry_price": str(self.entry_price) if self.entry_price else None,
            "pnl": str(self.pnl) if self.pnl else None,
        }


@dataclass
class PlayerSessionMeta:
    """Metadata for a player recording session."""
    player_id: str
    username: str
    session_start: datetime
    session_end: Optional[datetime] = None


@dataclass
class PlayerSession:
    """Complete player session - all actions across games."""
    meta: PlayerSessionMeta
    actions: List[PlayerAction] = field(default_factory=list)

    def add_action(self, action: PlayerAction):
        """Add action to session."""
        self.actions.append(action)

    def get_games_played(self) -> set:
        """Get unique game IDs in this session."""
        return set(a.game_id for a in self.actions)

    def to_dict(self) -> dict:
        """Serialize for JSON storage."""
        return {
            "meta": {
                "player_id": self.meta.player_id,
                "username": self.meta.username,
                "session_start": self.meta.session_start.isoformat(),
                "session_end": self.meta.session_end.isoformat() if self.meta.session_end else None,
            },
            "actions": [a.to_dict() for a in self.actions]
        }
```

---

## 5. WebSocket Data Sources

### Events to Capture

| Event | Data | Purpose |
|-------|------|---------|
| `gameStateUpdate.price` | Current tick price | Primary price data |
| `gameStateUpdate.partialPrices` | Recent price window | Gap filling |
| `gameStateUpdate.tickCount` | Current tick | Array indexing |
| `gameStateUpdate.gameId` | Game identifier | File linking |
| `gameStateUpdate.rugged` | Game ended | Trigger save |
| `gameStateUpdate.gameHistory[0]` | Completed game metadata | seed, peak, etc. |
| `usernameStatus` | Player ID, username | Session identity |
| `playerUpdate` | cash, positionQty, avgCost | Server state verification |

### Price History Handling
- Build complete `prices[]` array in memory as ticks arrive
- Use `partialPrices` to backfill any gaps
- On game end, save clean array to file

---

## 6. Code Architecture

### Modular Refactor

**Current** (1212 lines, monolithic):
```
sources/websocket_feed.py (1212 lines)
```

**After** (modular, each <400 lines):
```
sources/
├── websocket_feed.py        (~400 lines) - Core feed, Socket.IO handlers
├── feed_monitors.py         (~300 lines) - LatencySpikeDetector, ConnectionHealthMonitor
├── feed_rate_limiter.py     (~100 lines) - TokenBucket, PriorityRateLimiter
├── feed_degradation.py      (~170 lines) - GracefulDegradationManager
├── player_state_handler.py  (~150 lines) - usernameStatus, playerUpdate handlers
├── price_history_handler.py (~120 lines) - partialPrices merging, gap detection
└── game_state_machine.py    (existing)   - Already extracted
```

### New Module: `player_state_handler.py`

```python
"""
Player State Handler - Phase 10.4

Handles player-specific WebSocket events:
- usernameStatus: Player identity on connect
- playerUpdate: Server state after trades
- gameStatePlayerUpdate: Personal leaderboard entry
"""
from decimal import Decimal
from typing import Optional, Dict, Any, Callable
import logging

logger = logging.getLogger(__name__)


class PlayerStateHandler:
    """Handles player-specific WebSocket events."""

    def __init__(self):
        self.player_id: Optional[str] = None
        self.player_username: Optional[str] = None
        self.last_server_state: Optional[Dict[str, Any]] = None
        self._event_handlers: Dict[str, list] = {}

    def on(self, event: str, handler: Callable):
        """Register event handler."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def _emit(self, event: str, data: Any):
        """Emit event to handlers."""
        for handler in self._event_handlers.get(event, []):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in {event} handler: {e}")

    def handle_username_status(self, data: dict):
        """Handle usernameStatus event - player identity."""
        self.player_id = data.get('id')
        self.player_username = data.get('username')
        logger.info(f"Player identified: {self.player_username} ({self.player_id})")
        self._emit('player_identified', {
            'player_id': self.player_id,
            'username': self.player_username
        })

    def handle_player_update(self, data: dict):
        """Handle playerUpdate event - server state sync."""
        self.last_server_state = {
            'cash': Decimal(str(data.get('cash', 0))),
            'position_qty': Decimal(str(data.get('positionQty', 0))),
            'avg_cost': Decimal(str(data.get('avgCost', 0))),
            'cumulative_pnl': Decimal(str(data.get('cumulativePnL', 0))),
            'total_invested': Decimal(str(data.get('totalInvested', 0))),
        }
        self._emit('server_state_update', self.last_server_state)

    def handle_game_state_player_update(self, data: dict):
        """Handle gameStatePlayerUpdate - personal leaderboard."""
        self._emit('personal_leaderboard', data)
```

### New Module: `price_history_handler.py`

```python
"""
Price History Handler - Phase 10.4

Maintains tick-by-tick price history per game.
Uses partialPrices to fill gaps from missed ticks.
"""
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)


class PriceHistoryHandler:
    """Maintains complete price history per game."""

    def __init__(self):
        self.current_game_id: Optional[str] = None
        self.prices: List[Optional[Decimal]] = []
        self.peak_multiplier: Decimal = Decimal("1.0")
        self._event_handlers: Dict[str, list] = {}

    def on(self, event: str, handler: Callable):
        """Register event handler."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def _emit(self, event: str, data: Any):
        """Emit event to handlers."""
        for handler in self._event_handlers.get(event, []):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in {event} handler: {e}")

    def handle_tick(self, game_id: str, tick: int, price: Decimal):
        """Handle new price tick."""
        # New game started
        if game_id != self.current_game_id:
            if self.current_game_id:
                self._finalize_game()
            self._start_game(game_id)

        # Extend array if needed
        while len(self.prices) <= tick:
            self.prices.append(None)

        self.prices[tick] = price

        # Track peak
        if price > self.peak_multiplier:
            self.peak_multiplier = price

    def handle_partial_prices(self, partial_prices: dict):
        """Fill gaps using partialPrices from WebSocket."""
        values = partial_prices.get('values', {})
        for tick_str, price_val in values.items():
            tick = int(tick_str)
            if tick < len(self.prices) and self.prices[tick] is None:
                self.prices[tick] = Decimal(str(price_val))
                logger.debug(f"Filled gap at tick {tick}: {price_val}")

    def handle_game_end(self, game_id: str, game_history: list):
        """Handle game completion - extract seed data and finalize."""
        if game_id != self.current_game_id:
            return

        seed_data = None
        if game_history and len(game_history) > 0:
            completed = game_history[0]
            provably_fair = completed.get('provablyFair', {})
            seed_data = {
                'server_seed': provably_fair.get('serverSeed'),
                'server_seed_hash': provably_fair.get('serverSeedHash'),
                'peak_multiplier': Decimal(str(completed.get('peakMultiplier', self.peak_multiplier))),
            }

        self._finalize_game(seed_data)

    def _start_game(self, game_id: str):
        """Start tracking new game."""
        self.current_game_id = game_id
        self.prices = [Decimal("1.0")]  # Tick 0 always starts at 1.0
        self.peak_multiplier = Decimal("1.0")
        logger.info(f"Started tracking game: {game_id}")

    def _finalize_game(self, seed_data: Optional[dict] = None):
        """Finalize and emit completed game data."""
        gaps = self.prices.count(None)
        if gaps > 0:
            logger.warning(f"Game {self.current_game_id} has {gaps} missing ticks")

        self._emit('game_prices_complete', {
            'game_id': self.current_game_id,
            'prices': self.prices.copy(),
            'peak_multiplier': self.peak_multiplier,
            'duration_ticks': len(self.prices),
            'seed_data': seed_data,
            'has_gaps': gaps > 0
        })

    def get_prices(self) -> List[Optional[Decimal]]:
        """Get current price array."""
        return self.prices.copy()

    def has_gaps(self) -> bool:
        """Check for missing ticks."""
        return None in self.prices
```

### New Module: `state_verifier.py`

```python
"""
State Verifier - Phase 10.4

Compares local GameState to server playerUpdate data.
Logs drift when calculations don't match server truth.
"""
from decimal import Decimal
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

BALANCE_TOLERANCE = Decimal('0.000001')
POSITION_TOLERANCE = Decimal('0.000001')


class StateVerifier:
    """Compares local state to server truth."""

    def __init__(self, game_state):
        self.game_state = game_state
        self.drift_count = 0
        self.total_verifications = 0
        self.last_verification: Optional[Dict[str, Any]] = None

    def verify(self, server_state: Dict[str, Any]) -> Dict[str, Any]:
        """Compare local state to server state."""
        self.total_verifications += 1

        # Get local values
        local_balance = self.game_state.balance
        local_position = self.game_state.position
        local_position_qty = local_position.amount if local_position else Decimal('0')
        local_entry = local_position.entry_price if local_position else Decimal('0')

        # Get server values
        server_balance = server_state.get('cash', Decimal('0'))
        server_position_qty = server_state.get('position_qty', Decimal('0'))
        server_avg_cost = server_state.get('avg_cost', Decimal('0'))

        # Compare
        balance_diff = abs(local_balance - server_balance)
        position_diff = abs(local_position_qty - server_position_qty)
        entry_diff = abs(local_entry - server_avg_cost) if server_position_qty > 0 else Decimal('0')

        balance_ok = balance_diff <= BALANCE_TOLERANCE
        position_ok = position_diff <= POSITION_TOLERANCE
        entry_ok = entry_diff <= POSITION_TOLERANCE

        all_ok = balance_ok and position_ok and entry_ok

        if not all_ok:
            self.drift_count += 1
            logger.warning(
                f"State drift detected! "
                f"balance: {local_balance} vs {server_balance}, "
                f"position: {local_position_qty} vs {server_position_qty}"
            )

        result = {
            'verified': all_ok,
            'balance': {'local': local_balance, 'server': server_balance, 'ok': balance_ok},
            'position': {'local': local_position_qty, 'server': server_position_qty, 'ok': position_ok},
            'entry_price': {'local': local_entry, 'server': server_avg_cost, 'ok': entry_ok},
            'drift_count': self.drift_count,
            'total_verifications': self.total_verifications
        }

        self.last_verification = result
        return result
```

### New Recorders

#### `game_state_recorder.py`
```python
"""
Game State Recorder - Phase 10.4

Records game state files (prices + metadata).
One file per game in recordings/{date}/games/
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

from models.recording_models import GameStateRecord, GameStateMeta

logger = logging.getLogger(__name__)


class GameStateRecorder:
    """Records game state to JSON files."""

    def __init__(self, base_path: str = "recordings"):
        self.base_path = Path(base_path)
        self.current_game: Optional[GameStateRecord] = None
        self.game_start_time: Optional[datetime] = None

    def start_game(self, game_id: str):
        """Start recording a new game."""
        self.game_start_time = datetime.utcnow()
        self.current_game = GameStateRecord(
            meta=GameStateMeta(
                game_id=game_id,
                start_time=self.game_start_time
            )
        )
        logger.info(f"Started recording game: {game_id}")

    def record_prices(self, prices: list, peak: Decimal, seed_data: Optional[dict] = None):
        """Record completed price data."""
        if not self.current_game:
            return

        self.current_game.prices = prices
        self.current_game.meta.end_time = datetime.utcnow()
        self.current_game.meta.duration_ticks = len(prices)
        self.current_game.meta.peak_multiplier = peak

        if seed_data:
            self.current_game.meta.server_seed = seed_data.get('server_seed')
            self.current_game.meta.server_seed_hash = seed_data.get('server_seed_hash')

    def save(self) -> Optional[str]:
        """Save current game to file."""
        if not self.current_game:
            return None

        # Create directory structure
        date_str = self.game_start_time.strftime("%Y-%m-%d")
        games_dir = self.base_path / date_str / "games"
        games_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        time_str = self.game_start_time.strftime("%Y%m%dT%H%M%S")
        game_id_short = self.current_game.meta.game_id.split('-')[-1][:8]
        filename = f"{time_str}_{game_id_short}.game.json"
        filepath = games_dir / filename

        # Write file
        with open(filepath, 'w') as f:
            json.dump(self.current_game.to_dict(), f, indent=2)

        logger.info(f"Saved game state: {filepath}")

        # Update index
        self._update_index(date_str, filename)

        self.current_game = None
        return str(filepath)

    def _update_index(self, date_str: str, filename: str):
        """Update daily index file."""
        index_path = self.base_path / date_str / "index.json"

        if index_path.exists():
            with open(index_path, 'r') as f:
                index = json.load(f)
        else:
            index = {"date": date_str, "games": [], "sessions": []}

        # Add game entry
        index["games"].append({
            "file": filename,
            "game_id": self.current_game.meta.game_id,
            "start_time": self.current_game.meta.start_time.isoformat(),
            "duration_ticks": self.current_game.meta.duration_ticks,
            "peak_multiplier": str(self.current_game.meta.peak_multiplier)
        })

        with open(index_path, 'w') as f:
            json.dump(index, f, indent=2)
```

#### `player_session_recorder.py`
```python
"""
Player Session Recorder - Phase 10.4

Records player actions to session files.
One file per session in recordings/{date}/sessions/
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

from models.recording_models import PlayerSession, PlayerSessionMeta, PlayerAction

logger = logging.getLogger(__name__)


class PlayerSessionRecorder:
    """Records player actions to JSON files."""

    def __init__(self, base_path: str = "recordings"):
        self.base_path = Path(base_path)
        self.session: Optional[PlayerSession] = None
        self.session_start: Optional[datetime] = None

    def start_session(self, player_id: str, username: str):
        """Start new recording session."""
        self.session_start = datetime.utcnow()
        self.session = PlayerSession(
            meta=PlayerSessionMeta(
                player_id=player_id,
                username=username,
                session_start=self.session_start
            )
        )
        logger.info(f"Started session for: {username}")

    def record_action(self, action: PlayerAction):
        """Record player action."""
        if not self.session:
            return
        self.session.add_action(action)

    def save(self) -> Optional[str]:
        """Save session to file."""
        if not self.session or not self.session.actions:
            return None

        self.session.meta.session_end = datetime.utcnow()

        # Create directory
        date_str = self.session_start.strftime("%Y-%m-%d")
        sessions_dir = self.base_path / date_str / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        time_str = self.session_start.strftime("%Y%m%dT%H%M%S")
        username = self.session.meta.username or "anonymous"
        filename = f"{time_str}_{username}_session.json"
        filepath = sessions_dir / filename

        # Write file
        with open(filepath, 'w') as f:
            json.dump(self.session.to_dict(), f, indent=2)

        logger.info(f"Saved session: {filepath}")

        # Update index
        self._update_index(date_str, filename)

        return str(filepath)

    def _update_index(self, date_str: str, filename: str):
        """Update daily index file."""
        index_path = self.base_path / date_str / "index.json"

        if index_path.exists():
            with open(index_path, 'r') as f:
                index = json.load(f)
        else:
            index = {"date": date_str, "games": [], "sessions": []}

        index["sessions"].append({
            "file": filename,
            "player_id": self.session.meta.player_id,
            "username": self.session.meta.username,
            "games_played": len(self.session.get_games_played()),
            "total_actions": len(self.session.actions)
        })

        with open(index_path, 'w') as f:
            json.dump(index, f, indent=2)
```

---

## 7. Integration Flow

### Event Wiring
```
WebSocketFeed
  │
  ├─ @sio.on('usernameStatus')
  │   └─► PlayerStateHandler.handle_username_status()
  │        └─► emit 'player_identified'
  │             └─► PlayerSessionRecorder.start_session()
  │
  ├─ @sio.on('playerUpdate')
  │   └─► PlayerStateHandler.handle_player_update()
  │        └─► emit 'server_state_update'
  │             └─► StateVerifier.verify()
  │
  ├─ @sio.on('gameStateUpdate')
  │   ├─► PriceHistoryHandler.handle_tick(game_id, tick, price)
  │   ├─► PriceHistoryHandler.handle_partial_prices(partialPrices)
  │   └─► (on rugged) PriceHistoryHandler.handle_game_end()
  │        └─► emit 'game_prices_complete'
  │             └─► GameStateRecorder.record_prices() + save()
  │
  └─ User actions (via TradingController)
      └─► PlayerSessionRecorder.record_action()
```

### TradingController Integration
```python
# In TradingController.__init__():
self.player_session_recorder = PlayerSessionRecorder()

# After player identified:
def _on_player_identified(self, data):
    self.player_session_recorder.start_session(
        data['player_id'],
        data['username']
    )

# After each trade:
def _record_action(self, action_type: str, amount: Decimal, price: Decimal):
    action = PlayerAction(
        game_id=self.game_state.current_game_id,
        tick=self.game_state.current_tick,
        timestamp=datetime.utcnow(),
        action=action_type,
        amount=amount,
        price=price,
        balance_after=self.game_state.balance,
        position_qty_after=self.game_state.position.amount if self.game_state.position else Decimal('0'),
        entry_price=self.game_state.position.entry_price if self.game_state.position else None,
    )
    self.player_session_recorder.record_action(action)
```

---

## 8. Implementation Plan

### Phase 10.4A: Modular Refactor (Day 1)
1. Extract `LatencySpikeDetector`, `ConnectionHealthMonitor` → `feed_monitors.py`
2. Extract `TokenBucketRateLimiter`, `PriorityRateLimiter` → `feed_rate_limiter.py`
3. Extract `GracefulDegradationManager` → `feed_degradation.py`
4. Update imports in `websocket_feed.py`
5. Verify all existing tests pass

### Phase 10.4B: Data Models (Day 1)
1. Create `models/recording_models.py` with all dataclasses
2. Write unit tests for serialization/deserialization
3. Test gap filling logic

### Phase 10.4C: Player State Handler (Day 2)
1. Create `sources/player_state_handler.py`
2. Wire into WebSocketFeed (`usernameStatus`, `playerUpdate`)
3. Write unit tests
4. Integration test with live feed

### Phase 10.4D: Price History Handler (Day 2)
1. Create `sources/price_history_handler.py`
2. Wire into WebSocketFeed tick processing
3. Write unit tests for gap filling
4. Integration test with live feed

### Phase 10.4E: State Verifier (Day 3)
1. Create `services/state_verifier.py`
2. Wire to `server_state_update` events
3. Write unit tests
4. Verify drift detection works

### Phase 10.4F: Recorders (Day 3-4)
1. Create `core/game_state_recorder.py`
2. Create `core/player_session_recorder.py`
3. Wire to events and TradingController
4. Write integration tests
5. Manual test: record real gameplay, verify files

### Phase 10.4G: Final Integration (Day 4)
1. End-to-end test with live WebSocket
2. Verify complete data flow
3. Update CLAUDE.md
4. Create PR

---

## 9. Test Strategy

### Unit Tests
- `test_recording_models.py` - Serialization, gap filling
- `test_player_state_handler.py` - Event handling
- `test_price_history_handler.py` - Tick processing, gap detection
- `test_state_verifier.py` - Drift detection
- `test_game_state_recorder.py` - File creation, index updates
- `test_player_session_recorder.py` - Action recording

### Integration Tests
- `test_websocket_foundation_integration.py` - Full flow with mock WebSocket
- Manual test with live feed (documented procedure)

---

## 10. Success Criteria

1. **Modular Code**: All source files under 400 lines
2. **Complete Price Data**: Gap-free `prices[]` array per game
3. **Player Identity**: Captured on WebSocket connect
4. **Server Verification**: Drift detection with logging
5. **Clean Files**: Separate game state and player state JSON
6. **Sortable Index**: Daily index with queryable metadata
7. **Test Coverage**: Unit tests for all new modules
8. **Backward Compatible**: All existing 275+ tests pass

---

## 11. Files Created/Modified

### New Files
| File | Lines | Purpose |
|------|-------|---------|
| `models/recording_models.py` | ~120 | Data models |
| `sources/player_state_handler.py` | ~80 | Player events |
| `sources/price_history_handler.py` | ~100 | Price tracking |
| `sources/feed_monitors.py` | ~280 | Extracted monitors |
| `sources/feed_rate_limiter.py` | ~80 | Extracted rate limiter |
| `sources/feed_degradation.py` | ~160 | Extracted degradation |
| `services/state_verifier.py` | ~80 | Drift detection |
| `core/game_state_recorder.py` | ~100 | Game file writer |
| `core/player_session_recorder.py` | ~100 | Session file writer |

### Modified Files
| File | Change |
|------|--------|
| `sources/websocket_feed.py` | Reduced to ~400 lines, wire new handlers |
| `ui/controllers/trading_controller.py` | Wire recorders |
| `services/event_bus.py` | Add new event types |

---

## 12. References

- GitHub Issue: #2
- WebSocket Protocol: `docs/WEBSOCKET_EVENTS_SPEC.md`
- Original Plan: `docs/PHASE_10_4_PLAN.md`

---

*Design Complete - Ready for Implementation*
