# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Project**: REPLAYER - Dual-Mode Replay/Live Trading Platform for Rugs.fun
**Location**: `/home/nomad/Desktop/REPLAYER/`
**Status**: Production Ready (Phase 8.6 Complete, 275/275 tests passing)
**Current Branch**: `main`

---

## Quick Start Commands

### Running the Application
```bash
./run.sh  # Uses rugs-rl-bot venv for ML dependencies
# OR
cd src && python3 main.py
```

### Testing
```bash
cd src
python3 -m pytest tests/ -v                    # All tests (275 total)
python3 -m pytest tests/test_core/ -v          # Core logic tests
python3 -m pytest tests/test_bot/ -v           # Bot system tests
python3 -m pytest tests/ --cov=. --cov-report=html  # With coverage
```

### Analysis Scripts (for RL training data)
```bash
# Run from repository root
python3 analyze_trading_patterns.py      # Entry zones, volatility, survival curves
python3 analyze_position_duration.py     # Temporal risk, optimal hold times
python3 analyze_game_durations.py        # Game lifespan analysis
```

### Code Quality
```bash
cd src
black .                           # Format code
flake8                           # Lint
mypy core/ bot/ services/        # Type checking
./verify_tests.sh                # Pre-commit verification
```

---

## Essential Architecture Concepts

### 1. Event-Driven Design with Thread Safety

**Core Pattern**: Components communicate via `EventBus` pub/sub, with strict thread safety:

```python
# Publishing events
from services.event_bus import Events
event_bus.publish(Events.GAME_TICK, {'tick': 100, 'price': Decimal('1.5')})

# Subscribing to events
event_bus.subscribe(Events.POSITION_OPENED, self._handle_position_opened)

# CRITICAL: UI updates from background threads MUST use TkDispatcher
from ui.tk_dispatcher import TkDispatcher
self.ui_dispatcher.submit(lambda: self.label.config(text="Updated"))
```

**Key Files**:
- `src/services/event_bus.py` - Pub/sub system with queue-based async processing
- `src/ui/tk_dispatcher.py` - Marshals background thread → main thread UI updates
- `src/core/game_state.py` - Centralized state with `threading.RLock()`

**Thread Safety Rules**:
1. ALL UI updates from worker threads MUST go through `TkDispatcher.submit()`
2. `GameState` releases lock before executing callbacks (prevents deadlock)
3. Use `RLock` for re-entrant locking (same thread can acquire multiple times)
4. Extract data in worker thread, pass extracted values to UI thread

### 2. Centralized State Management

**Pattern**: `GameState` is single source of truth with observer pattern:

```python
# Get state
balance = state.get('balance')

# Update state (triggers events automatically)
state.update(current_price=Decimal('1.5'), current_tick=100)

# Subscribe to state changes
state.subscribe(StateEvents.BALANCE_CHANGED, callback)

# Open/close positions (P&L calculated automatically)
state.open_position({'entry_price': Decimal('1.5'), 'amount': Decimal('0.001')})
state.close_position(exit_price=Decimal('2.0'), exit_tick=150)

# Partial closes (Phase 8.1)
state.partial_close_position(percentage=25, exit_price=Decimal('1.8'))
```

**Key Points**:
- Thread-safe with `RLock`
- Immutable snapshots via `get_snapshot()`
- Automatic event emission on state changes
- Tracks full transaction history

### 3. Dual-Mode Bot Execution (Phase 8)

**Pattern**: Bot can execute trades in two modes:

```python
from bot.execution_mode import ExecutionMode

# BACKEND mode - Direct calls (0ms delay, fast training)
bot = BotController(
    bot_interface=interface,
    strategy_name='conservative',
    execution_mode=ExecutionMode.BACKEND
)

# UI_LAYER mode - Simulated clicks (realistic timing, live prep)
bot = BotController(
    bot_interface=interface,
    strategy_name='conservative',
    execution_mode=ExecutionMode.UI_LAYER,
    ui_controller=ui_controller  # Required for UI_LAYER
)
```

**Key Files**:
- `src/bot/controller.py` - Strategy selection and execution routing
- `src/bot/ui_controller.py` - UI-layer execution (clicks buttons, reads labels)
- `src/bot/browser_executor.py` - Live browser control via Playwright
- `src/bot/execution_mode.py` - BACKEND vs UI_LAYER enum

**Why Two Modes?**
- BACKEND: Fast iteration for training RL models
- UI_LAYER: Learn realistic timing delays (button click → confirmation)
- Same bot code works in both modes, only execution path differs

**Incremental Button Clicking (Phase A.2-A.3)**:

Both UI_LAYER and live browser execution use **incremental button clicking** to match human behavior:

```python
# Example: To place 0.003 SOL position
# Bot clicks: X (clear) → +0.001 (3x) → BUY
# Not: Direct text entry "0.003"

# BotUIController (UI_LAYER mode):
ui_controller.build_amount_incrementally(Decimal('0.003'))
# → Clicks X button once
# → Clicks +0.001 button 3 times with 10-50ms delays
# → Returns when bet entry shows "0.003"

# BrowserExecutor (live browser):
await browser_executor._build_amount_incrementally_in_browser(Decimal('0.003'))
# → Same button sequence but in actual browser DOM
```

**Button Click Strategy**:
- Algorithm: Greedy (largest denominations first)
- Buttons: `X` (clear), `+0.001`, `+0.01`, `+0.1`, `+1`, `1/2`, `X2`, `MAX`
- Timing: 10-50ms delays between clicks (mimics human)
- Examples:
  - `0.003` → X, +0.001 (3x)
  - `0.015` → X, +0.01 (1x), +0.001 (5x)
  - `1.234` → X, +1 (1x), +0.1 (2x), +0.01 (3x), +0.001 (4x)

**Why Incremental Clicking?**
1. **Realism**: Matches human gameplay patterns exactly
2. **Timing Training**: RL bot learns realistic execution delays
3. **Live Compatibility**: Same code works in REPLAYER and live browser
4. **Transparency**: Easy to observe bot behavior in UI

**Partial Sell Flow**:
```python
# To sell 50% of position:
# Bot clicks: 50% button → SELL button

ui_controller.click_sell(percentage=0.5)
# → Clicks "50%" percentage button
# → Waits 10-50ms (human delay)
# → Clicks SELL button
```

**Key Difference from Direct Entry**:
```python
# OLD (Phase 8.0-8.2): Direct text entry
bet_entry.delete(0, tk.END)
bet_entry.insert(0, "0.003")

# NEW (Phase A.2+): Incremental clicking
build_amount_incrementally(Decimal('0.003'))
# → Visible button clicks with human timing
```

### 4. Strategy Pattern for Trading

**Pattern**: Pluggable trading strategies via ABC:

```python
from bot.strategies.base import TradingStrategy

class CustomStrategy(TradingStrategy):
    def decide(self, observation, info):
        # Your logic here
        return ("BUY", Decimal('0.001'), "Reason for buying")
        # Returns: (action_type, amount, reasoning)
        # action_type: "BUY", "SELL", "SIDE", "WAIT"
```

**Built-in Strategies**:
- `conservative.py` - Low-risk, 1-10x entries, 25% profit target
- `aggressive.py` - High-risk, 10-100x entries, 100% profit target
- `sidebet.py` - Sidebet-focused, 5x payout optimization

**Strategy Registration**: Add to `src/bot/strategies/__init__.py`:
```python
STRATEGIES = {
    'conservative': ConservativeStrategy,
    'aggressive': AggressiveStrategy,
    'custom': CustomStrategy,
}
```

### 5. Configuration Management

**Pattern**: Centralized config with validation:

```python
from config import Config

# Access settings
initial_balance = Config.FINANCIAL['initial_balance']
sidebet_multiplier = Config.GAME_RULES['sidebet_multiplier']

# Environment variables
recordings_dir = Config.get_env('RUGS_RECORDINGS_DIR', '/home/nomad/rugs_recordings')
```

**Bot Configuration**: Persisted to `bot_config.json`:
```json
{
  "execution_mode": "ui_layer",
  "strategy": "conservative",
  "bot_enabled": false
}
```

---

## Game Mechanics (Critical Knowledge)

### Rugs.fun Trading Rules
- **Price Format**: Multiplier (1x, 2x, 5x, etc.)
- **100% Rug Rate**: All games eventually rug - exit timing is EVERYTHING
- **P&L Formula**: `pnl = bet_amount * (current_price / entry_price - 1)`
- **Sweet Spot**: 25-50x entry zone (75% success, 186-427% median returns)

### Sidebet Mechanics
- **Payout**: 5x multiplier (bet 0.001 SOL → win 0.005 SOL if rug)
- **Duration**: 40 ticks (~10 seconds at 4 ticks/sec)
- **Cooldown**: 5 ticks between bets
- **Constraint**: Only one active sidebet at a time

### Empirical Findings (from 899 games analyzed)
- **Median Game Lifespan**: 138 ticks (50% rug by this point)
- **Temporal Risk**: 23.4% rug by tick 50, 79.3% by tick 300
- **Optimal Hold Times**: 48-60 ticks for sweet spot entries (25-50x)
- **Stop Losses**: 30-50% recommended (not 10%, avg drawdown is 8-25%)

---

## Development Workflow

### Adding a New Feature

1. **Update State** (if needed):
```python
# src/core/game_state.py
def update_feature(self, value):
    with self._lock:
        self._state['feature'] = value
        self._emit(StateEvents.FEATURE_CHANGED, value)
```

2. **Add Event Handler** (thread-safe):
```python
# src/ui/main_window.py
def _handle_feature_changed(self, data):
    # Extract data in worker thread
    feature_value = data.get('value')
    # Marshal to UI thread
    self.ui_dispatcher.submit(lambda: self.update_ui(feature_value))
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

### Testing Philosophy

**Test Structure**: Mirror code structure under `src/tests/`:
- `src/core/game_state.py` → `tests/test_core/test_game_state.py`
- `src/bot/controller.py` → `tests/test_bot/test_controller.py`

**Pytest Markers** (from `pytest.ini`):
```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Exclude slow tests
```

**Critical Tests**:
- Thread safety (race conditions, deadlocks)
- Decimal precision (no float for money)
- Event ordering (pub/sub correctness)
- State observability (RL training requirements)

---

## Common Pitfalls & Gotchas

### 1. ML Symlinks Dependency
- `src/ml/` directory uses symlinks to `/home/nomad/Desktop/rugs-rl-bot/rugs_bot/sidebet/`
- If rugs-rl-bot is moved/deleted, ML features gracefully degrade
- Check for broken symlinks with: `find src/ml -xtype l`

### 2. Decimal Precision
- NEVER use `float` for financial calculations
- Always use `Decimal` from `decimal` module
- Validate with `Decimal.is_finite()` to catch NaN/Infinity

### 3. Thread Safety Violations
```python
# ❌ WRONG - Causes UI freeze/crash
widget.config(text="...")  # Called from worker thread

# ✅ CORRECT - Marshals to main thread
self.ui_dispatcher.submit(lambda: widget.config(text="..."))
```

### 4. Lock Ordering
- `GameState._emit()` releases lock before calling callbacks
- Never call `state.update()` from inside a state callback (deadlock)
- Use `state.get_snapshot()` if you need consistent state view

### 5. Recordings Path
- Recordings live in `src/rugs_recordings/` (symlink to `/home/nomad/rugs_recordings/`)
- NOT in repository root (was moved in Phase 6)
- Check symlink: `ls -la src/rugs_recordings`

---

## Integration Points

### External Projects

**rugs-rl-bot** (`/home/nomad/Desktop/rugs-rl-bot/`):
- REPLAYER generates empirical analysis (JSON files)
- rugs-rl-bot uses analysis for RL reward design
- Shared ML predictor via symlinks

**CV-BOILER-PLATE-FORK** (`/home/nomad/Desktop/CV-BOILER-PLATE-FORK/`):
- YOLOv8 object detection for live gameplay
- WebSocket feed reference implementation
- Playwright browser automation shared

### Venv Sharing
- REPLAYER uses rugs-rl-bot's venv (via `run.sh`)
- Ensures ML dependency compatibility
- Fallback to system python3 if unavailable

---

## File Organization

### Core Modules
- `src/core/game_state.py` - State management (640 lines) ⭐
- `src/core/replay_engine.py` - Playback control
- `src/core/trade_manager.py` - Trade execution logic
- `src/core/validators.py` - Input validation (Decimal, NaN checks)

### Bot System
- `src/bot/controller.py` - Bot orchestration ⭐
- `src/bot/ui_controller.py` - UI-layer execution (Phase 8.3)
- `src/bot/browser_executor.py` - Live browser control (Phase 8.5)
- `src/bot/strategies/` - Trading strategy implementations

### UI Components
- `src/ui/main_window.py` - Main window (1730 lines) ⭐
- `src/ui/tk_dispatcher.py` - Thread-safe UI (47 lines) ⭐
- `src/ui/bot_config_panel.py` - Bot configuration dialog
- `src/ui/timing_overlay.py` - Draggable timing metrics widget (Phase 8.6)

### Services
- `src/services/event_bus.py` - Event pub/sub ⭐
- `src/services/logger.py` - Logging setup

### Tests
- `src/tests/conftest.py` - Shared fixtures
- `src/tests/test_core/` - Core logic (71 tests)
- `src/tests/test_bot/` - Bot system (54 tests)
- `src/tests/test_ui/` - UI components (6 tests)

### Documentation
- `CLAUDE.md` - This file (developer guide)
- `AGENTS.md` - Concise repository guidelines
- `README.md` - User-facing overview
- `docs/PHASE_8_COMPLETION_ROADMAP.md` - Current development status
- `docs/game_mechanics/` - Game rules knowledge base

---

## Current Development Status

**Phase 8: UI-First Bot System** - 90% Complete

✅ **Completed** (Phases 8.1-8.6):
- Partial sell infrastructure (10%, 25%, 50%, 100% buttons)
- BotUIController (UI-layer execution with human delays)
- Bot configuration panel with JSON persistence
- Browser automation via Playwright
- Timing metrics tracking with draggable overlay widget
- 12 critical bug fixes (thread safety, validation, config defaults)

⏳ **Remaining** (Phase 8.7, ~2-3 hours):
- Safety mechanisms (loss limits, emergency stop)
- Validation layer for browser actions
- Production readiness checklist

**Next Session**: Implement Phase 8.7 safety features

---

## Version Control

### Commit Pattern
```bash
git commit -m "Phase 8.X: [Feature/Fix] - Description

- Bullet point change 1
- Bullet point change 2

Files changed: X files (Y insertions, Z deletions)
Tests: A/B passing

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Git Workflow
```bash
git status                    # Check status
git add .                     # Stage all changes
git commit -m "..."           # Commit with pattern above
git push origin main          # Push to remote
```

---

## Key References

**For Detailed Context**: See `/home/nomad/CLAUDE.md` (parent project overview)

**For Quick Guidelines**: See `AGENTS.md` (concise repository rules)

**For Planning**: See `docs/PHASE_8_COMPLETION_ROADMAP.md` (current status)

**For Architecture Deep-Dive**: See `docs/Codex/codebase_audit.md` (audit findings)

**For Game Rules**: See `docs/game_mechanics/GAME_MECHANICS.md`

---

**Last Updated**: 2025-11-18
**Status**: Production Ready (275/275 tests passing)
**Next Milestone**: Phase 8.7 Production Readiness
