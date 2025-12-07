# REPLAYER - Production Documentation
**Version**: 0.10.3 | **Date**: December 6, 2025 | **Status**: Phase 10.3 Complete

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
cd src && python3 -m pytest tests/ -v --tb=short
```

### Supporting Documentation
- `architect.yaml` - Design patterns reference
- `RULES.yaml` - Code standards reference
- `docs/WEBSOCKET_EVENTS_SPEC.md` - WebSocket protocol specification

---

## Production State

### What's Working (Phase 9 Complete)
- CDP Browser Connection to system Chrome
- Phantom wallet persistence via Chrome profile
- Button selectors (BUY, SELL, percentages, sidebets)
- Multi-strategy selector system (text -> class -> structural -> ARIA)
- Incremental button clicking (human-like behavior)
- 275 tests passing
- Modern UI with theme-aware charts

### What's Next (Phase 10.4)
- Server state verification layer (player-specific)
- Auto-start recording on game transitions
- Latency tracking for realistic bot timing

### Phase 10: Human Demo Recording System (In Progress)
**Goal**: Record human gameplay to train RL bot with realistic behavior patterns.

| Sub-Phase | Status | Description |
|-----------|--------|-------------|
| 10.1 | Complete | DemoRecorderSink, demo_action models (32 tests) |
| 10.2 | Complete | TradingController integration (22 tests) |
| 10.3 | Complete | MainWindow menu integration |
| 10.4 | **Next** | WebSocket verification layer |
| 10.5 | Planned | Auto-start on game transitions |
| 10.6 | Planned | Latency tracking for timing realism |

**Scope Focus**: Player-specific data only (not rugpool, battle, chat).

**References**:
- `docs/WEBSOCKET_EVENTS_SPEC.md` - Full protocol documentation
- `docs/PHASE_10_4_PLAN.md` - Implementation plan with code examples

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
├── ml/             # ML symlinks to rugs-rl-bot
└── tests/          # 275 tests
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
| 10.4 | **Active** | WebSocket verification layer |

---

## WebSocket Integration (Phase 10.4+)

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

**Full Protocol Reference**: `docs/WEBSOCKET_EVENTS_SPEC.md`

---

*Phase 10.3 Complete | Phase 10.4 Active | December 6, 2025*
