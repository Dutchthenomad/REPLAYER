# REPLAYER - Development Context

**Project**: Dual-Mode Replay/Live Game Viewer & RL Training Environment
**Location**: `/home/nomad/Desktop/REPLAYER/`
**Status**: ✅ **Production Ready** - Phase 6 complete, Live Feed working, 237/237 tests passing
**Last Updated**: 2025-11-15
**Current Branch**: `feature/menu-bar` (Phase 7B in progress)

---

## Quick Start

### Running the Application
```bash
cd /home/nomad/Desktop/REPLAYER
./run.sh  # Uses rugs-rl-bot venv for ML dependencies
```

### Running Tests
```bash
cd src
python3 -m pytest tests/ -v
# Total: 237 tests - ALL PASSING ✅
```

### Running Analysis Scripts
```bash
# Empirical analysis for RL training data
python3 analyze_trading_patterns.py  # Entry zones, volatility, survival
python3 analyze_position_duration.py  # Temporal risk, hold times
python3 analyze_game_durations.py    # Game lifespan analysis
```

---

## Current State (2025-11-15)

### ✅ Production Ready

**Phase 6 Complete**: WebSocket Live Feed Integration working flawlessly
- **Status**: Fully functional dual-mode viewer (replay + live feed) ✅
- **Bot System**: 3 strategies working (conservative, aggressive, sidebet)
- **UI**: Thread-safe, real-time updates, live feed support, no freezes
- **Tests**: 237/237 tests passing ✅
- **Live Feed**: Continuous multi-game support, 4.01 signals/sec, 241ms latency

### Recent Completions (Session 2025-11-15)

**Phase 7A - RecorderSink Test Fixes** ✅
- Fixed `test_recorded_tick_format` - Save filepath before `stop_recording()`
- All 21 RecorderSink tests passing
- Documentation: `docs/PHASE_7A_COMPLETION.md`

**Phase 6 - WebSocket Live Feed Integration** ✅ (3 commits)
1. Initial integration - Socket.IO connection, thread-safe callbacks
2. Bug fix: `catch_all` handler signature error
3. Bug fix: Shutdown sequence cleanup
4. Bug fix: Multi-game loop support (continuous feed across games)
- Documentation: `docs/PHASE_6_COMPLETION.md`
- Test script: `test_live_feed_automation.py` (62 signals in 15s)

**Phase 5 - Recording Infrastructure + Audit Fixes** ✅
- RecorderSink auto-recording, JSONL metadata format
- Live ring buffer (5000-tick memory-bounded)
- 7 critical audit fixes applied
- Documentation: `docs/Codex/`

**Phase 4 - ReplaySource Abstraction** ✅
- Multi-source architecture (file replay + live feed)

### 🚧 Current Development (Phase 7B - Menu Bar)

**Branch**: `feature/menu-bar` (safely isolated from `main`)
**Status**: UI mockups complete, ready for implementation
**Goal**: Add menu bar to existing UI for recording controls and settings

**Branching Strategy**:
- **main branch**: Stable, production-ready code (Phase 6 complete)
- **feature/menu-bar**: Menu bar development (can be reverted if needed)
- Merge strategy: Test fully on feature branch before merging to main

**Mockup Files**:
- `ui_mockup.py` - Full menu system mockup (complex)
- `ui_mockup_simple.py` - Minimal menu bar only (approved design)

**Next Steps**:
1. Finalize menu structure with user
2. Implement menu bar in `src/ui/main_window.py`
3. Add recording toggle functionality
4. Test on feature branch
5. Merge to main if approved

---

## Meta Vision: RL Training Environment

**NOT IMPLEMENTED YET** - This is the long-term goal informing current design decisions.

### End Goal (Future)
- **Dual-mode**: Replay recorded games OR display live WebSocket feed
- **Perfect fidelity**: Replay and live use IDENTICAL code paths
- **Gymnasium-compatible**: Well-defined observation/action spaces for RL training
- **Deterministic**: Same replay → same results → reproducible training
- **Scalable**: Train bots at speed using 900+ recorded games

### Why This Matters NOW
Even though we're NOT implementing ML/training yet, infrastructure must support:
- **Determinism**: Same replay = same results
- **State Observability**: Complete state snapshots for reward calculation
- **Clean Action Space**: BUY/SELL/SIDEBET/WAIT
- **Event Traceability**: All reward-relevant events captured

**Bottom Line**: We're building the foundation for RL training without implementing RL training.

---

## Project Structure

```
/home/nomad/Desktop/REPLAYER/
├── run.sh                        # Launch script (uses rugs-rl-bot venv)
├── requirements.txt              # Python dependencies
├── AGENTS.md                     # Concise repository guidelines
├── README.md                     # User-facing overview
├── SESSION_PLANNING.md           # Detailed planning document
├── DEADLOCK_BUG_REPORT.md        # Technical bug analysis
├── BUG_FIXES_SUMMARY.md          # Bug fix summary
│
├── src/                          # Production code (~8,000 lines)
│   ├── main.py                   # Application entry point
│   ├── config.py                 # Centralized configuration
│   │
│   ├── models/                   # Data models
│   │   ├── game_tick.py          # GameTick data model (9 params)
│   │   ├── position.py           # Position tracking
│   │   ├── side_bet.py           # Sidebet mechanics (5x payout)
│   │   └── enums.py              # Game phase enums
│   │
│   ├── core/                     # Core business logic
│   │   ├── game_state.py         # ⭐ State management (640 lines)
│   │   ├── replay_engine.py      # Playback control (439 lines)
│   │   ├── trade_manager.py      # Trade execution (297 lines)
│   │   ├── game_queue.py         # Multi-game queue (133 lines)
│   │   └── validators.py         # Input validation (187 lines)
│   │
│   ├── bot/                      # Bot automation system
│   │   ├── interface.py          # BotInterface ABC (226 lines)
│   │   ├── controller.py         # BotController (152 lines)
│   │   ├── async_executor.py     # Async execution (214 lines)
│   │   └── strategies/           # Trading strategies
│   │       ├── base.py           # TradingStrategy ABC
│   │       ├── conservative.py   # Low-risk strategy (3,475 lines)
│   │       ├── aggressive.py     # High-risk strategy (2,914 lines)
│   │       └── sidebet.py        # Sidebet-focused (2,309 lines)
│   │
│   ├── ml/                       # ML Integration (symlinks to rugs-rl-bot)
│   │   ├── predictor.py          # Sidebet predictor (38.1% win, 754% ROI)
│   │   ├── feature_extractor.py  # Feature engineering (IQR fix applied)
│   │   └── ...
│   │
│   ├── services/                 # Shared services
│   │   ├── event_bus.py          # ⭐ Event pub/sub system
│   │   └── logger.py             # Logging configuration
│   │
│   ├── ui/                       # User interface
│   │   ├── main_window.py        # ⭐ Main window (926 lines)
│   │   ├── tk_dispatcher.py      # ⭐ Thread-safe UI updates (47 lines)
│   │   ├── panels.py             # UI panels (525 lines)
│   │   ├── layout_manager.py     # Panel positioning (256 lines)
│   │   └── widgets/              # Reusable components
│   │
│   └── tests/                    # Test suite (237 tests - ALL PASSING ✅)
│       ├── conftest.py           # Shared fixtures
│       ├── test_models/          # Data model tests (12 tests)
│       ├── test_core/            # Core logic tests (63 tests)
│       ├── test_bot/             # Bot system tests (54 tests)
│       ├── test_services/        # Service tests (12 tests)
│       ├── test_ml/              # ML integration (1 test)
│       ├── test_ui/              # UI tests (1 test)
│       ├── test_sources/         # WebSocket feed tests (21 tests)
│       └── test_validators/      # Validation tests (15 tests)
│
├── docs/                         # Documentation
│   ├── Codex/                    # Audit & planning docs
│   │   ├── codebase_audit.md     # Comprehensive audit (7 findings)
│   │   ├── changes_summary.md    # Audit fix details
│   │   ├── handoff.md            # Session handoff notes
│   │   └── live_feed_integration_plan.md  # Live feed roadmap
│   │
│   ├── game_mechanics/           # Game rules knowledge base
│   │   ├── GAME_MECHANICS.md     # Comprehensive rules
│   │   └── side_bet_mechanics_v2.md
│   │
│   └── archive/                  # Historical docs
│       ├── CLAUDE_2025-11-10.md  # OLD root CLAUDE.md
│       ├── CLAUDE_MODULAR_ERA.md # OLD docs/CLAUDE.md
│       └── [other archived docs]
│
├── external/                     # External integrations
│   └── continuous_game_recorder.py  # WebSocket reference (325 lines)
│
├── models/                       # ML models
│   └── sidebet_model_gb_*.pkl    # Trained sidebet predictor (239KB)
│
├── Analysis Scripts (Root)       # Empirical analysis for RL
│   ├── analyze_trading_patterns.py      # 689 lines
│   ├── analyze_position_duration.py     # 659 lines
│   ├── analyze_game_durations.py        # 161 lines
│   ├── analyze_volatility_spikes.py     # 329 lines
│   └── analyze_spike_timing.py          # 358 lines
│
└── Analysis Outputs              # Generated data
    ├── trading_pattern_analysis.json       # 12KB (140K+ samples)
    └── position_duration_analysis.json     # 24KB (survival curves)
```

**External Dependencies**:
- `/home/nomad/rugs_recordings/` - 929 game recordings (99MB, JSONL format)
- `/home/nomad/Desktop/rugs-rl-bot/` - ML predictor and RL bot project

---

## Architecture Overview

### Design Principles

1. **Event-Driven Architecture**
   - Components communicate via `EventBus` (pub/sub pattern)
   - 20+ event types (game, trading, bot, UI)
   - Weak references prevent memory leaks

2. **Centralized State Management**
   - `GameState` is single source of truth
   - Observer pattern for reactive updates
   - Thread-safe with `threading.RLock()`
   - Immutable snapshots via `get_snapshot()`

3. **Thread Safety**
   - `TkDispatcher` marshals UI updates to main thread
   - `AsyncBotExecutor` runs bot in worker thread
   - `GameState` uses `RLock` for re-entrant locking
   - Event callbacks released from lock before execution

4. **Strategy Pattern (Bot System)**
   - `TradingStrategy` ABC
   - Factory pattern for strategy creation
   - Pluggable strategies (conservative, aggressive, sidebet)

5. **Perfect Fidelity (Future Live Mode)**
   - Replay and live will use identical code paths
   - Only difference: tick SOURCE (file vs WebSocket)
   - Same GameState, TradeManager, UI for both modes

---

## Key Components

### GameState (`src/core/game_state.py` - 640 lines)

**Centralized state management** with thread-safe operations and observer pattern.

**Key Methods**:
- `get(key, default)` - Thread-safe state getter
- `update(**kwargs)` - Update multiple state values
- `open_position(position_data)` - Open new position
- `close_position(exit_price, exit_time, exit_tick)` - Close position, calculate P&L
- `place_sidebet(amount, tick, price)` - Place sidebet
- `resolve_sidebet(won, tick)` - Resolve sidebet (5x payout if won)
- `subscribe(event, callback)` - Subscribe to state changes
- `calculate_metrics()` - Win rate, P&L, max drawdown

**State Events** (Observer pattern):
- `BALANCE_CHANGED`, `POSITION_OPENED`, `POSITION_CLOSED`
- `SIDEBET_PLACED`, `SIDEBET_RESOLVED`
- `TICK_UPDATED`, `GAME_STARTED`, `GAME_ENDED`, `RUG_EVENT`

**Thread Safety** (Critical):
- Uses `threading.RLock()` for re-entrant locking
- `_emit()` releases lock before calling callbacks (prevents deadlock)
- Properties use lock for safe access

### EventBus (`src/services/event_bus.py`)

**Thread-safe pub/sub event system** for component communication.

**Key Methods**:
- `subscribe(event, handler)` - Subscribe to event
- `publish(event, data)` - Publish event to subscribers
- `unsubscribe(event, handler)` - Unsubscribe

**Event Types** (`services.Events` enum):
- Game: `GAME_START`, `GAME_END`, `GAME_TICK`, `GAME_RUG`
- Trading: `TRADE_BUY`, `TRADE_SELL`, `TRADE_EXECUTED`, `TRADE_FAILED`
- Bot: `BOT_ENABLED`, `BOT_DISABLED`, `BOT_DECISION`
- Sidebet: `SIDEBET_PLACED`, `SIDEBET_WON`, `SIDEBET_LOST`

**Architecture**:
- Queue-based async processing (5000 event capacity)
- Background thread with daemon mode
- Error isolation (one callback failure doesn't crash system)

### TkDispatcher (`src/ui/tk_dispatcher.py` - 47 lines) ⭐ NEW

**Thread-safe UI update marshaling** (critical for bot operation).

**Purpose**: Marshal UI updates from background threads to Tk main thread

**Implementation**:
- Queue-based work submission
- 16ms poll interval (60 FPS)
- Safe shutdown mechanism

**Critical**: Prevents `TclError` crashes from bot worker thread updating UI

**Usage**:
```python
# In UI event handlers called from worker thread
self.ui_dispatcher.submit(lambda: self.balance_label.config(text=f"Balance: {balance:.4f}"))
```

### Bot System (`src/bot/`)

**Pluggable strategy system** for automated trading.

**Components**:
- `BotController` - Strategy selection and execution
- `BotInterface` - Observation/action API
- `AsyncBotExecutor` - Async execution (prevents deadlock)
- `TradingStrategy` (ABC) - Base strategy class

**Strategies**:
- `conservative.py` - Low-risk, profit-taking focused
- `aggressive.py` - High-risk, momentum-based
- `sidebet.py` - Sidebet-focused (5x payout optimization)

**Current Behavior** (Sidebet Strategy):
- Rule-based (places sidebet every tick if no active sidebet)
- Does NOT use trained `SidebetPredictor` ML model yet
- Designed for testing sidebet mechanics
- **Future**: Integrate ML predictor for intelligent decisions

### ML Integration (`src/ml/` - Symlinks)

**Location**: Symlinks to `/home/nomad/Desktop/rugs-rl-bot/rugs_bot/sidebet/`

**SidebetPredictor**:
- Gradient Boosting Classifier (v3)
- 38.1% win rate (vs 16.7% random), 754% ROI
- 14-dimensional feature vector (z-score, volatility, timing)
- 5 outputs per tick: `probability`, `confidence`, `ticks_to_rug_norm`, `is_critical`, `should_exit`

**Note**: If rugs-rl-bot is moved/deleted, these symlinks break. ML features gracefully degrade.

---

## Game Mechanics (Critical Knowledge)

### Rugs.fun Trading Rules
- **Price Format**: Multiplier (e.g., 1.5x, 2.0x)
- **Typical Range**: 1x to 5x (most games rug before 10x)
- **100% Rug Rate**: All games eventually rug - exit timing is everything
- **P&L Calculation**: `pnl = bet_amount * (current_price / entry_price - 1)`

### Sidebet Mechanics
- **Payout**: 5x multiplier (400% profit) if rug occurs
- **Duration**: 40 ticks (10 seconds at 4 ticks/second)
- **Cooldown**: 5 ticks between bets
- **Example**: Bet 0.001 SOL → Win 0.005 SOL if rug within 40 ticks
- **Constraint**: Only one active sidebet at a time

### Empirical Findings (From Analysis Scripts)
- **Sweet Spot**: 25-50x entry (75% success, 186-427% median returns)
- **Median Game Lifespan**: 138 ticks (50% rug by this point)
- **Temporal Risk**: 23.4% rug by tick 50, 79.3% by tick 300
- **Optimal Hold Times**: 48-60 ticks for sweet spot entries

---

## Development Workflow

### Adding a New Feature

1. **Update State (if needed)**:
   ```python
   # src/core/game_state.py
   def update_feature(self, value):
       with self._lock:
           self._state['feature'] = value
           self._emit(StateEvents.FEATURE_CHANGED, value)
   ```

2. **Add Event Handler**:
   ```python
   # src/ui/main_window.py
   def _handle_feature_changed(self, data):
       # Marshal to UI thread
       self.ui_dispatcher.submit(
           lambda: self.update_ui(data)
       )
   ```

3. **Subscribe to Event**:
   ```python
   # src/ui/main_window.py __init__
   self.state.subscribe(StateEvents.FEATURE_CHANGED, self._handle_feature_changed)
   ```

4. **Write Tests**:
   ```python
   # src/tests/test_core/test_feature.py
   def test_feature_update(mock_state):
       mock_state.update_feature(123)
       assert mock_state.get('feature') == 123
   ```

### Thread Safety Guidelines

**CRITICAL RULES**:

1. **Always use `ui_dispatcher` for UI updates from background threads**
   ```python
   # ✅ CORRECT
   self.ui_dispatcher.submit(lambda: widget.config(text="..."))

   # ❌ WRONG - Causes UI freeze
   widget.config(text="...")
   ```

2. **Release lock before calling callbacks** (already done in `GameState._emit()`)
   ```python
   # ✅ CORRECT
   def _emit(self, event, data):
       with self._lock:
           callbacks = list(self._observers[event])
       for callback in callbacks:  # Outside lock!
           callback(data)

   # ❌ WRONG - Can deadlock
   def _emit(self, event, data):
       for callback in self._observers[event]:  # While holding lock!
           callback(data)
   ```

3. **Use RLock for re-entrant locking**
   - ✅ Already using `threading.RLock()` in GameState
   - Allows same thread to acquire lock multiple times

4. **Extract data before marshaling to UI thread**
   ```python
   # ✅ CORRECT
   def _handle_balance_changed(self, data):
       balance = data.get('new')  # Extract in worker thread
       self.ui_dispatcher.submit(lambda: update_ui(balance))  # Pass extracted data

   # ❌ WRONG - Accesses state in UI thread
   def _handle_balance_changed(self, data):
       self.ui_dispatcher.submit(lambda: update_ui(self.state.get('balance')))
   ```

---

## Next Phase: Live Feed Integration

**Status**: PLANNED (not implemented)
**Reference**: `docs/Codex/live_feed_integration_plan.md`

### Phase Breakdown

**Phase 4: ReplaySource Abstraction** (1-2 days)
- Abstract tick source (file vs live)
- Implement `FileDirectorySource`
- Add `push_tick()` method to `ReplayEngine`

**Phase 5: RecorderSink & LiveRingBuffer** (2-3 days)
- Port recorder logic from `continuous_game_recorder.py`
- Implement 10-game rolling context buffer
- Pre-populate from recent JSONL files

**Phase 6: LiveFeedSource** (3-4 days)
- Integrate `WebSocketFeed` from CV-BOILER-PLATE-FORK
- Implement real-time tick ingestion
- 4-minute keep-alive mechanism

**Phase 7: UI Mode Toggle** (1-2 days)
- Mode toggle (Recorded / Live)
- Connection status indicator
- Pause buffering for live mode

**Total Timeline**: ~1-2 weeks

**Key Design**: Perfect fidelity - replay and live use IDENTICAL code paths, only tick SOURCE differs.

---

## Testing Philosophy (RL-Aware)

### Current Testing (Implemented)

✅ **Unit Tests**: 148 tests (86 passing, 62 legacy need alignment)
✅ **Integration Tests**: Multi-component interaction
✅ **Fixtures**: Reusable test components (mock state, event bus)
✅ **Coverage**: Critical paths covered

### Future Testing (RL Readiness - Not Implemented)

**NOT implementing now, but infrastructure must support:**

1. **Determinism Tests**: Same replay → same results
2. **State Observability Tests**: All reward-relevant state observable
3. **Action Space Tests**: Action effects observable in state
4. **Reward Property Tests**: Mathematical properties hold (monotonicity, bounds)

---

## Integration with Related Projects

### rugs-rl-bot (RL Trading Bot)
**Location**: `/home/nomad/Desktop/rugs-rl-bot/`

**Integration Points**:
- Consumes REPLAYER empirical analysis outputs (JSON files)
- Uses analysis results to design RL reward functions
- REPLAYER symlinks to rugs-rl-bot's sidebet predictor (`ml/` directory)

**Commands**:
```bash
cd ~/Desktop/rugs-rl-bot
.venv/bin/python -m pytest tests/ -v           # Run tests
.venv/bin/python scripts/train_phase0_model.py  # Train RL model
```

### CV-BOILER-PLATE-FORK (Vision Training)
**Location**: `/home/nomad/Desktop/CV-BOILER-PLATE-FORK/`

**Integration Points**:
- YOLOv8 object detection for live gameplay
- Game recordings used for CV training data
- WebSocket feed reference (`WebSocketFeed` class)

**Commands**:
```bash
cd ~/Desktop/CV-BOILER-PLATE-FORK
.venv/bin/python3 -m pytest tests/ -v  # Run tests
.venv/bin/python3 train_overnight.py    # Train YOLO model
```

---

## Common Patterns

### State Updates
```python
# Get current state
balance = state.get('balance')

# Update state (triggers events)
state.update(current_price=Decimal('1.5'), current_tick=100)

# Subscribe to changes
state.subscribe(StateEvents.BALANCE_CHANGED, lambda data: print(data))
```

### Trade Execution
```python
# Open position
position = {'entry_price': Decimal('1.5'), 'amount': Decimal('0.001'), 'tick': 100}
state.open_position(position)

# Close position (calculates P&L automatically)
result = state.close_position(exit_price=Decimal('2.0'), exit_tick=150)
print(f"P&L: {result['pnl_sol']} SOL")
```

### Bot Strategy Execution
```python
# Enable bot
bot_controller.set_strategy('conservative')
bot_executor.start()

# Process tick (bot auto-executes)
bot_executor.queue_execution(tick)
```

---

## Known Issues & Gotchas

### Fixed Issues ✅
1. ✅ UI thread safety (TkDispatcher implemented)
2. ✅ Deadlock prevention (lock released before callbacks)
3. ✅ GameTick fallback parameters
4. ✅ Real-time balance updates

### Current Limitations
1. **ML Symlinks**: `ml/` directory uses symlinks to rugs-rl-bot (breaks if rugs-rl-bot moved)
2. **Legacy Tests**: 62 tests need API alignment (reference old methods)
3. **Sidebet Strategy**: Rule-based, not using ML predictor yet

### Future Enhancements
1. Integrate `SidebetPredictor` into sidebet strategy
2. Align legacy tests with current API
3. Live WebSocket feed integration (Phase 4-7)

---

## Version Control

### Commit Guidelines
- Commit at end of each phase/milestone
- Use descriptive messages: "Phase X: [Feature/Fix] - Description"
- Include metrics: "X lines changed, Y tests added"
- Add co-authorship footer

### Git Workflow
```bash
git status                     # Check status
git add .                      # Stage changes
git commit -m "Phase 3: ..."   # Commit
git push origin main           # Push to GitHub
```

---

## Quick Reference

### Key Files to Know
- `src/core/game_state.py` - State management (640 lines) ⭐
- `src/ui/main_window.py` - Main window (926 lines) ⭐
- `src/services/event_bus.py` - Event system ⭐
- `src/ui/tk_dispatcher.py` - Thread-safe UI (47 lines) ⭐
- `src/bot/controller.py` - Bot control (152 lines)
- `AGENTS.md` - Concise quick reference
- `SESSION_PLANNING.md` - Detailed planning (1587 lines)

### Key Directories
- `src/core/` - Core business logic
- `src/bot/` - Bot automation
- `src/ui/` - User interface
- `src/ml/` - ML integration (symlinks)
- `src/tests/` - Test suite
- `docs/Codex/` - Audit & planning docs

### External Dependencies
- `/home/nomad/rugs_recordings/` - 929 game recordings
- `/home/nomad/Desktop/rugs-rl-bot/` - ML predictor, RL bot

---

**Status**: Production ready, all audit fixes complete
**Next Phase**: Live feed integration (Phase 4-7, ~1-2 weeks)
**Last Updated**: 2025-11-14
