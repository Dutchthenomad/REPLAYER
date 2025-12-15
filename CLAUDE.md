# REPLAYER - Production Documentation
**Version**: 0.11.0 | **Date**: December 14, 2025 | **Status**: Phase 11 In Progress (CDP WebSocket Interception)

---

## Development Workflow: Superpowers Methodology

**This project uses Superpowers as the PRIMARY development methodology.**

### Quick Reference
- Global commands: `~/.claude/WORKFLOW_QUICKREF.md`
- Project templates: `.claude/templates/`

### The 5 Iron Laws

| Principle | Command | Rule |
|-----------|---------|------|
| TDD | `/tdd` | NO code without failing test first |
| Verification | `/verify` | Fresh test run before claiming complete |
| Debugging | `/debug` | 4-phase root cause analysis |
| Planning | `/plan` | Zero-context executable plans |
| Isolation | `/worktree` | Isolated workspace per feature |

### Project Test Command
```bash
cd /home/nomad/Desktop/REPLAYER/src && ../.venv/bin/python -m pytest tests/ -v --tb=short
```

### Supporting Documentation
- `architect.yaml` - Design patterns reference
- `RULES.yaml` - Code standards reference
- `docs/WEBSOCKET_EVENTS_SPEC.md` - WebSocket protocol specification

---

## Production State

### What's Working (Phase 11 In Progress)
- CDP Browser Connection to system Chrome
- Phantom wallet persistence via Chrome profile
- Button selectors (BUY, SELL, percentages, sidebets)
- Multi-strategy selector system (text -> class -> structural -> ARIA)
- Incremental button clicking (human-like behavior)
- Raw WebSocket Capture Tool (Developer Tools menu)
- Hardcoded credentials workaround for auth-gated events
- **CDP WebSocket Interception** - Captures authenticated events from browser
- **EventSourceManager** - Auto-switches between CDP and fallback sources
- **RAGIngester** - Catalogs events for rugs-expert agent
- **DebugTerminal** - Real-time event viewer (separate window)
- 796 tests passing
- Modern UI with theme-aware charts

### What's Next (Phase 12)
- RL model integration for live trading
- Browser automation for real trades
- Portfolio management dashboard
- Player profile UI integration (balance, PnL, positions)

### Phase 10: Human Demo Recording System (Complete)
**Goal**: Record human gameplay to train RL bot with realistic behavior patterns.

| Sub-Phase | Status | Description |
|-----------|--------|-------------|
| 10.1 | Complete | DemoRecorderSink, demo_action models (32 tests) |
| 10.2 | Complete | TradingController integration (22 tests) |
| 10.3 | Complete | MainWindow menu integration |
| 10.4 | Complete | WebSocket foundation layer (game transition events) |
| 10.5 | Complete | Unified recording configuration system |
| 10.6 | Complete | Unified recording integration with dual-state validation |
| 10.7 | Complete | Raw Capture Tool + Hardcoded credentials workaround |

**Key Achievements**:
- Game-aware recording with automatic GAME_START/GAME_END detection
- LiveFeedController tracks game transitions and publishes events
- RecordingController integrates with EventBus for game lifecycle
- Verified recording captures complete price histories (500+ ticks per game)
- **Phase 10.6**: TradingController fully integrated with RecordingController
- **Phase 10.6**: Dual-state validation (local vs server) for drift detection
- **Phase 10.6**: Auto-start/stop recording on WebSocket connect/disconnect
- **Phase 10.7**: Raw WebSocket Capture Tool for protocol debugging
- **Phase 10.7**: Hardcoded credentials workaround (server only sends auth events to authenticated clients)

**References**:
- `docs/plans/2025-12-07-unified-recording-config-design.md` - Phase 10.5 design
- `docs/plans/2025-12-07-phase-10.6-unified-recording-integration.md` - Phase 10.6 design
- `docs/plans/2025-12-10-websocket-raw-capture-tool-design.md` - Phase 10.7 design

---

## Architecture (Distilled)

### Core Patterns
1. **Event-Driven**: EventBus pub/sub for all component communication
2. **Thread-Safe**: TkDispatcher for UI updates from worker threads
3. **Centralized State**: GameState with RLock, observer pattern
4. **Dual-Mode Execution**: BACKEND (fast) vs UI_LAYER (realistic timing)
5. **Strategy Pattern**: Pluggable trading strategies via ABC

### Critical Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/core/game_state.py` | State management | 640 |
| `src/bot/browser_executor.py` | Browser automation | 517 |
| `src/ui/main_window.py` | Main UI | 1730 |
| `src/services/event_bus.py` | Pub/sub | ~200 |
| `src/debug/raw_capture_recorder.py` | Raw WebSocket capture | 280 |
| `src/sources/cdp_websocket_interceptor.py` | CDP frame interception | 205 |
| `src/sources/socketio_parser.py` | Socket.IO frame parsing | 151 |
| `src/services/event_source_manager.py` | Source auto-switching | 86 |
| `src/services/rag_ingester.py` | Event RAG cataloging | 181 |
| `src/ui/debug_terminal.py` | Real-time event viewer | 247 |

### Thread Safety Rules
1. UI updates from workers -> `TkDispatcher.submit()`
2. GameState releases lock before callbacks
3. Use `RLock` for re-entrant locking
4. Extract data in worker, pass to UI thread

### Key Patterns

**Event Publishing**:
```python
from services.event_bus import Events
event_bus.publish(Events.GAME_TICK, {'tick': 100, 'price': Decimal('1.5')})
```

**Thread-Safe UI Update**:
```python
# WRONG - causes freeze/crash
widget.config(text="...")  # From worker thread

# CORRECT
self.ui_dispatcher.submit(lambda: widget.config(text="..."))
```

**State Management**:
```python
state.update(current_price=Decimal('1.5'), current_tick=100)
state.open_position({'entry_price': Decimal('1.5'), 'amount': Decimal('0.001')})
```

---

## Commands

### Run & Test
```bash
./run.sh                                    # Launch app
cd src && python3 -m pytest tests/ -v       # All tests
cd src && python3 -m pytest tests/ --cov=.  # With coverage
```

### CDP Browser Setup
```bash
python3 scripts/test_cdp_connection.py      # Test connection
# First time: Install Phantom in Chrome, connect to rugs.fun
```

### Analysis Scripts
```bash
python3 analyze_trading_patterns.py         # Entry zones, volatility
python3 analyze_position_duration.py        # Temporal risk
python3 analyze_game_durations.py           # Game lifespan
```

---

## Game Mechanics (Reference)

| Rule | Value |
|------|-------|
| 100% Rug Rate | Exit timing is everything |
| Sweet Spot | 25-50x entry (75% success) |
| Median Game Life | 138 ticks |
| Sidebet Payout | 5x multiplier |
| Sidebet Duration | 40 ticks |

### Empirical Findings (899 games)
- Temporal Risk: 23.4% rug by tick 50, 79.3% by tick 300
- Optimal Hold Times: 48-60 ticks for sweet spot entries
- Stop Losses: 30-50% recommended (avg drawdown 8-25%)

---

## File Structure

```
src/
├── core/           # State, replay, trade management
│   ├── game_state.py       # Centralized state (640 lines)
│   ├── replay_engine.py    # Playback control
│   ├── trade_manager.py    # Trade execution
│   └── recorder_sink.py    # Auto-recording
├── bot/            # Controller, strategies, browser executor
│   ├── controller.py       # Bot orchestration
│   ├── browser_executor.py # Browser automation (517 lines)
│   ├── ui_controller.py    # UI-layer execution
│   └── strategies/         # Trading strategies
├── ui/             # Main window, panels, widgets
│   ├── main_window.py      # Main UI (1730 lines)
│   └── tk_dispatcher.py    # Thread-safe UI
├── services/       # EventBus, logger
├── models/         # GameTick, Position, SideBet
├── sources/        # WebSocket feed
├── debug/          # Raw capture, protocol debugging
├── ml/             # ML symlinks to rugs-rl-bot
└── tests/          # 737 tests
```

### Browser Automation
```
browser_automation/
├── cdp_browser_manager.py  # CDP connection (270 lines)
├── rugs_browser.py         # Browser manager (268 lines)
└── persistent_profile.py   # Profile config
```

---

## Dual-Mode Execution

### BACKEND Mode (Training)
- Direct function calls
- 0ms delay
- Fast iteration for RL training

### UI_LAYER Mode (Live Prep)
- Simulated button clicks
- Human-like timing delays
- Validates UI integration

```python
from bot.execution_mode import ExecutionMode

bot = BotController(
    execution_mode=ExecutionMode.BACKEND  # or UI_LAYER
)
```

### Incremental Button Clicking
Bot builds amounts by clicking increment buttons (matches human behavior):
```
0.003 SOL -> X (clear), +0.001 (3x)
0.015 SOL -> X, +0.01, +0.001 (5x)
```

---

## Common Pitfalls

### 1. ML Symlinks
`src/ml/` symlinks to `/home/nomad/Desktop/rugs-rl-bot/rugs_bot/sidebet/`
Check: `find src/ml -xtype l`

### 2. Decimal Precision
NEVER use `float` for money. Always `Decimal`.

### 3. Thread Safety
UI updates from workers MUST use `TkDispatcher.submit()`.

### 4. Lock Ordering
`GameState._emit()` releases lock before callbacks. Never call `state.update()` from inside a callback.

### 5. Recordings Path
Symlink: `src/rugs_recordings` -> `/home/nomad/rugs_recordings/`

---

## Related Projects

| Project | Location | Purpose |
|---------|----------|---------|
| rugs-rl-bot | `/home/nomad/Desktop/rugs-rl-bot/` | RL training |
| CV-BOILER-PLATE-FORK | `/home/nomad/Desktop/CV-BOILER-PLATE-FORK/` | YOLO detection |
| Recordings | `/home/nomad/rugs_recordings/` | 929 games |

---

## Phase History

| Phase | Status | Description |
|-------|--------|-------------|
| 6 | Complete | WebSocket live feed integration |
| 7 | Complete | Menu bar UI, RecorderSink fixes |
| 8 | Complete | UI-first bot, partial sells, timing overlay |
| 9 | Complete | CDP browser connection, button selectors |
| 10.1-10.3 | Complete | Human demo recording (models, controller, menu) |
| 10.4 | Complete | WebSocket foundation layer (game transitions) |
| 10.5 | Complete | Unified recording configuration system |
| 10.6 | Complete | Unified recording integration with dual-state validation |
| 10.7 | Complete | Raw Capture Tool + Hardcoded credentials workaround |
| 11 | In Progress | CDP WebSocket Interception + RAG event cataloging |

---

## Phase 10.7: Raw Capture Tool & Auth Workaround

### Raw WebSocket Capture Tool

**Purpose**: Capture ALL raw Socket.IO events for protocol debugging and documentation.

**Location**: `Developer Tools` menu in main window

**Menu Structure**:
```
Developer Tools
├── Start Raw Capture (toggles to "⏺ Stop Raw Capture")
├── ─────────────────
├── Analyze Last Capture
├── Open Captures Folder
├── ─────────────────
└── Show Capture Status
```

**Output**: `/home/nomad/rugs_recordings/raw_captures/`

**Files Created**:
- `src/debug/__init__.py`
- `src/debug/raw_capture_recorder.py` (280 lines)
- `scripts/analyze_raw_capture.py` (CLI analysis tool)
- `src/tests/test_debug/test_raw_capture_recorder.py` (19 tests)

### Hardcoded Credentials Workaround

**Problem**: Server only sends `usernameStatus` and `playerUpdate` events to authenticated clients. Our WebSocket connection is read-only/unauthenticated.

**Solution**: Hardcode Dutch's credentials and extract state from `gameStatePlayerUpdate` events (which are broadcast to all clients).

**In `src/sources/websocket_feed.py`**:
```python
HARDCODED_PLAYER_ID = "did:privy:cmaibr7rt0094jp0mc2mbpfu4"
HARDCODED_USERNAME = "Dutch"
```

**How it works**:
1. On WebSocket connect, auto-confirm identity using hardcoded credentials
2. Filter `gameStatePlayerUpdate` events for Dutch's player ID
3. Extract: PnL, pnlPercent, positionQty, avgCost, totalInvested, hasActiveTrades, sidebet
4. Update `_last_server_state` for Phase 11 reconciliation
5. Emit `player_state_update` event for UI/recording

**Events captured (from raw capture analysis)**:
| Event Type | Count | Percentage |
|------------|-------|------------|
| gameStateUpdate | 510 | 92.1% |
| standard/newTrade | 31 | 5.6% |
| newChatMessage | 11 | 2.0% |
| connect | 1 | 0.2% |
| battleEventUpdate | 1 | 0.2% |

**Key Finding**: No `usernameStatus` or `playerUpdate` events in unauthenticated capture.

---

## WebSocket Integration

### Player-Specific Events (In Scope)

| Event | Purpose | Key Fields |
|-------|---------|------------|
| `usernameStatus` | Player identity | `id`, `username` |
| `playerUpdate` | Server state sync | `cash`, `positionQty`, `avgCost` |
| `gameStatePlayerUpdate` | Personal leaderboard | Same as leaderboard entry |
| Trade responses | Confirmation + latency | `timestamp`, `success` |

### Verification Layer Design

```python
# Compare local state to server truth
local_balance = game_state.balance
server_balance = player_update['cash']
if abs(local_balance - server_balance) > Decimal('0.000001'):
    log.warning(f"Balance drift: local={local_balance}, server={server_balance}")
```

### Out of Scope (Phase 10)
- Rugpool metrics (side game)
- Battle mode events
- Chat messages
- Other players' leaderboard data

---

## Known Issues / Bugs to Fix

Phase 10.7 implementation needs live testing. Potential issues to investigate:
1. UI freeze when stopping raw capture (fixed with background thread, but verify)
2. Verify `gameStatePlayerUpdate` filtering works in live environment
3. Verify `player_state_update` event properly reaches recording system
4. Test identity confirmation terminal output displays correctly

---

## Phase 11: CDP WebSocket Interception (In Progress)

**Goal**: Capture ALL WebSocket events (including authenticated) via Chrome CDP to enable proper player state tracking.

### Problem Statement

Two separate WebSocket connections existed:
1. **WebSocketFeed** - Unauthenticated, only receives public events
2. **CDP Browser Bridge** - Authenticated via Phantom wallet, receives all events

The server only sends `usernameStatus` and `playerUpdate` events to authenticated clients. Without intercepting the browser's authenticated WebSocket, we cannot properly track player balance, positions, and PnL.

### Solution Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    CDP WEBSOCKET INTERCEPTION                           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐    ┌─────────────────────┐    ┌─────────────────────┐   │
│  │   Chrome    │───▶│ CDPWebSocketIntercep│───▶│ SocketIOParser      │   │
│  │  (rugs.fun) │    │     tor             │    │ (frame parsing)     │   │
│  └─────────────┘    └─────────────────────┘    └─────────────────────┘   │
│        │                     │                         │                 │
│        │              Network.webSocketFrameReceived   │                 │
│        │                     │                         │                 │
│        │                     ▼                         ▼                 │
│        │              ┌──────────────────────────────────────┐          │
│        │              │           EventBus                   │          │
│        │              │  WS_RAW_EVENT | WS_AUTH_EVENT        │          │
│        │              └──────────────────────────────────────┘          │
│        │                     │              │                           │
│        │                     ▼              ▼                           │
│        │              ┌─────────────┐ ┌─────────────┐                   │
│        │              │ RAGIngester │ │DebugTerminal│                   │
│        │              │ (catalog)   │ │ (display)   │                   │
│        │              └─────────────┘ └─────────────┘                   │
│        │                                                                │
│        ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    EventSourceManager                           │   │
│  │  CDP (authenticated) ←→ Fallback (public WebSocketFeed)         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| `SocketIOParser` | `src/sources/socketio_parser.py` | Parse Socket.IO/Engine.IO frames |
| `CDPWebSocketInterceptor` | `src/sources/cdp_websocket_interceptor.py` | Intercept browser WebSocket via CDP |
| `EventSourceManager` | `src/services/event_source_manager.py` | Auto-switch between CDP and fallback |
| `RAGIngester` | `src/services/rag_ingester.py` | Catalog events for rugs-expert agent |
| `DebugTerminal` | `src/ui/debug_terminal.py` | Real-time event viewer (separate window) |

### EventBus Extensions

New event types added to `src/services/event_bus.py`:

```python
# WebSocket event types
WS_RAW_EVENT = "ws.raw_event"       # All raw WebSocket events
WS_AUTH_EVENT = "ws.auth_event"     # Auth-specific events (usernameStatus, playerUpdate)
WS_SOURCE_CHANGED = "ws.source_changed"  # Source switch notifications
```

### Debug Terminal

**Access**: `Developer Tools` → `Open Debug Terminal`

**Features**:
- Opens in **separate window** (tk.Toplevel)
- Color-coded event display by type
- Event filtering (all/auth/trades/game)
- Pause/resume, clear, export to JSON
- Ring buffer (1000 events max)

**Color Coding**:
| Event Type | Color |
|------------|-------|
| gameStateUpdate | Gray |
| usernameStatus | Green |
| playerUpdate | Cyan |
| standard/newTrade | Yellow |
| Novel/unknown | Red |

### RAG Integration

Events are automatically cataloged to `/home/nomad/rugs_recordings/rag_events/` in JSONL format:

```json
{"timestamp": "2025-12-14T10:30:45.123", "event_name": "playerUpdate", "data": {...}, "source": "cdp", "game_id": "..."}
```

**Novel Event Detection**: Unknown events are flagged and logged for documentation.

### Status Bar Indicator

The status bar shows current event source:
- 🟢 **CDP** - Connected to authenticated browser
- 🟡 **Fallback** - Using public WebSocketFeed
- 🔴 **No Source** - Neither connected

### Usage

1. **Start Chrome with CDP**:
   ```bash
   google-chrome --remote-debugging-port=9222
   ```

2. **Launch REPLAYER**:
   ```bash
   ./run.sh
   ```

3. **Connect to browser** via `Browser` menu

4. **Open Debug Terminal**: `Developer Tools` → `Open Debug Terminal`

5. **View status**: Check status bar for current source (CDP/Fallback)

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/sources/socketio_parser.py` | 151 | Socket.IO frame parsing |
| `src/sources/cdp_websocket_interceptor.py` | 205 | CDP interception |
| `src/services/event_source_manager.py` | 86 | Source switching |
| `src/services/rag_ingester.py` | 181 | Event cataloging |
| `src/ui/debug_terminal.py` | 247 | Debug UI |
| `src/tests/test_sources/test_socketio_parser.py` | 8 tests | Parser tests |
| `src/tests/test_sources/test_cdp_websocket_interceptor.py` | 12 tests | Interceptor tests |
| `src/tests/test_services/test_event_source_manager.py` | 7 tests | Manager tests |
| `src/tests/test_services/test_rag_ingester.py` | 8 tests | Ingester tests |
| `src/tests/test_ui/test_debug_terminal.py` | 6 tests | UI tests |
| `src/tests/test_integration/test_cdp_event_flow.py` | 3 tests | Integration tests |

### References

- Design document: `docs/plans/2025-12-14-cdp-websocket-interception-design.md`
- Implementation plan: `docs/plans/2025-12-14-cdp-websocket-interception-impl.md`
- GitHub Issue: #13

---

*Phase 11 In Progress | December 14, 2025*
