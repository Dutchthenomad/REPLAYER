# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Project**: REPLAYER - Dual-Mode Replay/Live Trading Platform for Rugs.fun
**Location**: `/home/nomad/Desktop/REPLAYER/`
**Status**: Phase 9.1 Complete (CDP Browser Connection)
**Current Branch**: `main`

---

## CRITICAL: Production Readiness Audit Complete (Nov 24, 2025)

**Audit Results**: MEDIUM-HIGH risk level. System requires critical fixes before production.
- See `COMPREHENSIVE_AUDIT_REPORT.md` for full audit findings
- See `PRODUCTION_READINESS_PLAN.md` for 4-week fix roadmap

**Next Priority**: Begin Phase 10 (Critical Fixes) immediately

---

## Phase 9.1 Complete: CDP Browser Connection

### What Was Implemented (Nov 22, 2025)

**Problem Solved**: Playwright's bundled Chromium has a known MV3 extension bug - Phantom extension appears in toolbar but `window.phantom` never gets injected.

**Solution Implemented**: CDP (Chrome DevTools Protocol) connection to YOUR system Chrome.

**Files Created/Modified**:
1. `browser_automation/cdp_browser_manager.py` - NEW (270 lines)
   - Chrome binary detection
   - CDP port availability checking
   - Chrome launch with debug port
   - CDP connection via `connect_over_cdp()`

2. `src/bot/browser_executor.py` - MODIFIED
   - Added CDP manager support (primary)
   - Legacy RugsBrowserManager kept as fallback
   - All action methods updated to use `page` property

3. `src/ui/browser_connection_dialog.py` - MODIFIED
   - Updated for CDP workflow
   - Simplified options (no wallet step - persisted in profile)

4. `scripts/test_cdp_connection.py` - NEW
   - Interactive test script for CDP workflow

### How to Test CDP Connection

```bash
cd /home/nomad/Desktop/REPLAYER
python3 scripts/test_cdp_connection.py
```

### How CDP Works

```python
# CDP connects to YOUR Chrome browser
from browser_automation.cdp_browser_manager import CDPBrowserManager

manager = CDPBrowserManager()
await manager.connect()  # Launches Chrome if needed
# Your Phantom wallet is now available!
await manager.navigate_to_game()
# ... do automation ...
await manager.disconnect()  # Chrome keeps running
```

### First-Time Setup

Before using CDP connection, set up your Chrome profile:
1. Run the test script: `python3 scripts/test_cdp_connection.py`
2. In the Chrome window that opens, install Phantom wallet
3. Connect Phantom to rugs.fun
4. Close and rerun - wallet should still be connected!

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

# Run with specific markers (from pytest.ini)
python3 -m pytest -m unit                      # Unit tests only
python3 -m pytest -m integration               # Integration tests only
python3 -m pytest -m "not slow"                # Exclude slow tests
python3 -m pytest -m ui                        # UI tests only
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

# Pre-commit review (automated code review)
cd /home/nomad/Desktop/REPLAYER
./scripts/pre_commit_review.sh   # Run aicode-review checks
```

### Debugging Commands
```bash
# Manual bot testing (watch UI behavior)
./run.sh  # Then enable bot in UI

# Automated debugging with screenshots
cd src
python3 debug_bot_session.py --duration 30     # Capture 30s of bot activity
python3 automated_bot_test.py --games 5        # Run validation test on 5 games
python3 playwright_debug_helper.py             # Visual browser automation debug

# Demo incremental clicking (educational)
python3 demo_incremental_clicking.py           # Show button clicking algorithm
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

### 6. Browser XPaths and Selectors
- Button selectors documented in `docs/XPATHS.txt`
- Used by BrowserExecutor for live browser automation
- Increment buttons: `+0.001`, `+0.01`, `+0.1`, `+1`, `1/2`, `X2`, `MAX`, `X` (clear)
- Action buttons: `BUY`, `SELL`, `SIDEBET`
- Partial sell: `10%`, `25%`, `50%`, `100%`
- If selectors change, update both XPATHS.txt and `browser_automation/rugs_browser.py`

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

### Environment Variables
- `RUGS_RECORDINGS_DIR` - Path to recordings directory (default: `/home/nomad/rugs_recordings`)
- `RUGS_CONFIG_DIR` - Config directory (default: `~/.config/replayer`)
- `LOG_LEVEL` - Logging level (default: `INFO`)
- Set in `src/config.py` with `Config.get_env()`

---

## File Organization

### Source Directory Structure (`src/`)
```
src/
├── main.py                  # Application entry point
├── config.py                # Centralized configuration
│
├── models/                  # Data models
│   ├── game_tick.py        # GameTick (9 parameters)
│   ├── position.py         # Position tracking with partial close
│   ├── side_bet.py         # Sidebet (5x payout)
│   └── enums.py            # Game phase enums
│
├── core/                    # Core business logic ⭐
│   ├── game_state.py       # State management (640 lines)
│   ├── replay_engine.py    # Playback control
│   ├── trade_manager.py    # Trade execution
│   ├── validators.py       # Input validation
│   ├── live_ring_buffer.py # Memory-bounded buffer
│   └── recorder_sink.py    # Auto-recording to JSONL
│
├── bot/                     # Bot automation system ⭐
│   ├── controller.py       # Bot orchestration
│   ├── ui_controller.py    # UI-layer execution (347 lines)
│   ├── browser_executor.py # Browser automation (517 lines)
│   ├── execution_mode.py   # BACKEND vs UI_LAYER
│   ├── async_executor.py   # Async execution (214 lines)
│   └── strategies/         # Trading strategies
│       ├── base.py         # TradingStrategy ABC
│       ├── conservative.py # Low-risk strategy
│       ├── aggressive.py   # High-risk strategy
│       └── foundational.py # Production strategy
│
├── ml/                      # ML integration (symlinks)
│   ├── predictor.py        # SidebetPredictor wrapper
│   └── feature_extractor.py # Feature engineering
│
├── sources/                 # Tick sources
│   └── websocket_feed.py   # Live WebSocket integration
│
├── ui/                      # User interface ⭐
│   ├── main_window.py      # Main window (1730 lines)
│   ├── tk_dispatcher.py    # Thread-safe UI (47 lines)
│   ├── panels.py           # UI panels
│   ├── bot_config_panel.py # Bot settings dialog
│   ├── timing_overlay.py   # Timing metrics widget
│   └── widgets/            # Reusable components
│       ├── chart.py        # Chart widget
│       └── toast.py        # Toast notifications
│
├── services/                # Shared services ⭐
│   ├── event_bus.py        # Event pub/sub system
│   └── logger.py           # Logging configuration
│
├── tests/                   # Test suite (275 tests)
│   ├── conftest.py         # Shared fixtures
│   ├── test_core/          # Core logic (63 tests)
│   ├── test_bot/           # Bot system (54 tests)
│   ├── test_ui/            # UI components (6 tests)
│   ├── test_models/        # Data models (12 tests)
│   ├── test_services/      # Services (12 tests)
│   ├── test_ml/            # ML integration (1 test)
│   └── test_sources/       # WebSocket (21 tests)
│
├── rugs_recordings/         # Symlink to /home/nomad/rugs_recordings
│
├── debug_bot_session.py     # Debug script with screenshots
├── automated_bot_test.py    # Automated validation
├── playwright_debug_helper.py # Browser debug
├── demo_incremental_clicking.py # Educational demo
└── verify_tests.sh          # Pre-commit test verification
```

### Repository Root Files
- `CLAUDE.md` - Developer guide (this file)
- `AGENTS.md` - Concise repository guidelines
- `README.md` - User-facing overview
- `run.sh` - Launch script
- `architect.yaml` - Design patterns config (aicode-architect)
- `RULES.yaml` - Coding standards (aicode-review)
- `toolkit.yaml` - Project metadata

### Documentation (`docs/`)
- `PHASE_8_COMPLETION_ROADMAP.md` - Current development status
- `DEBUGGING_GUIDE.md` - Debugging workflow and tools
- `QUICK_START_GUIDE.md` - User quick start
- `NEXT_SESSION_PLAN.md` - Next session planning
- `XPATHS.txt` - Browser element selectors
- `game_mechanics/` - Game rules knowledge base
- `archive/` - Historical reference docs

### Browser Automation (`browser_automation/`)
- `rugs_browser.py` - Browser manager (268 lines)
- `automation.py` - Wallet automation (226 lines)
- `persistent_profile.py` - Profile config (161 lines)

---

## Current Development Status

**PRIORITY: Phase 10-14 Production Readiness** (4-week plan)

See `PRODUCTION_READINESS_PLAN.md` for detailed implementation roadmap.

### Phase 10: CRITICAL FIXES (Days 1-5) - START IMMEDIATELY
- **10.1**: Fix browser automation path imports (Day 1)
- **10.2**: Implement memory management/archival (Days 2-3)
- **10.3**: Fix WebSocket Decimal conversion (Day 3)
- **10.4**: Fix EventBus shutdown race condition (Days 4-5)

### Phase 11: HIGH PRIORITY (Days 6-12)
- **11.1**: Browser reconnection logic (Days 6-7)
- **11.2**: Thread safety audit (Days 8-9)
- **11.3**: File handle management (Days 10-11)
- **11.4**: Remove backup files (Day 12)

### Phase 12: MEDIUM PRIORITY (Days 13-19)
- **12.1**: Async/Sync architecture (Days 13-14)
- **12.2**: Configuration centralization (Days 15-16)
- **12.3**: Input validation (Days 17-18)
- **12.4**: Async file I/O (Day 19)

### Phase 13: PERFORMANCE (Days 20-23)
- **13.1**: WebSocket latency buffer (Day 20)
- **13.2**: Lock optimization (Days 21-22)
- **13.3**: Performance profiling (Day 23)

### Phase 14: SECURITY & TESTING (Days 24-28)
- **14.1**: Security hardening (Days 24-25)
- **14.2**: Comprehensive testing (Days 26-27)
- **14.3**: Documentation & deployment (Day 28)

---

## Previously Completed: Phase 9 CDP Browser Connection

### Problem Identified (Nov 22, 2025)
Playwright's `launch_persistent_context` with MV3 extensions (Phantom) is fundamentally broken:
- Extension loads (visible in toolbar)
- Service worker doesn't start
- `window.phantom` never injected
- rugs.fun shows "Install Phantom" dialog even though it's installed

### Solution: CDP Connection Architecture
See `docs/BROWSER_CONNECTION_PLAN.md` for full 6-phase plan.

**Phase 9.1**: CDP Infrastructure (2-3h) - **START HERE**
- Create `CDPBrowserManager` class
- Connect to running Chrome via `connect_over_cdp()`
- Profile at `~/.gamebot/chrome_profiles/rugs_bot`

**Phase 9.2**: Setup Script (1-2h)
- Interactive `scripts/setup_chrome_profile.py`
- User installs Phantom, connects wallet once
- Profile persists forever

**Phase 9.3**: UI Integration (2-3h)
- Update menu: Connect to Chrome, Launch Chrome, Setup Profile
- Replace RugsBrowserManager with CDPBrowserManager

**Phase 9.4**: Button Automation (2-3h)
- Verify XPath selectors work via CDP
- Test incremental clicking

**Phase 9.5**: Robustness (2-3h)
- Auto-reconnect, health checks, recovery

**Phase 9.6**: Documentation (1-2h)

**Total Estimate**: 10-16 hours

---

### Previous Phases (Complete)

**Phase 8: UI-First Bot System** - 95% Complete
- ✅ Partial sell infrastructure (10%, 25%, 50%, 100% buttons)
- ✅ BotUIController (UI-layer execution with human delays)
- ✅ Bot configuration panel with JSON persistence
- ✅ Timing metrics tracking with draggable overlay widget
- ✅ 12 critical bug fixes (thread safety, validation, config defaults)
- ⏸️ Phase 8.7 (safety mechanisms) - DEFERRED until browser works

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

**For Browser Connection Plan**: See `docs/BROWSER_CONNECTION_PLAN.md` (Phase 9 implementation details)

**For Detailed Context**: See `/home/nomad/CLAUDE.md` (parent project overview)

**For Quick Guidelines**: See `AGENTS.md` (concise repository rules)

**For Architecture Deep-Dive**: See `docs/Codex/codebase_audit.md` (audit findings)

**For Game Rules**: See `docs/game_mechanics/GAME_MECHANICS.md`

**For XPath Selectors**: See `docs/XPATHS.txt` (button selectors for automation)

---

**Last Updated**: 2025-11-22
**Status**: Phase 9 Active (Browser Connection Overhaul)
**Next Milestone**: CDP Browser Connection (Phase 9.1)

---

## Additional Resources

**For Browser Plan**: See `docs/BROWSER_CONNECTION_PLAN.md` (bulletproof browser connection)

**For Deep Debugging**: See `docs/DEBUGGING_GUIDE.md` (comprehensive debugging workflow)

**For Quick Reference**: See `AGENTS.md` (concise coding guidelines)

**For Users**: See `docs/QUICK_START_GUIDE.md` (user-facing documentation)

**For Architecture Review**: See `architect.yaml` and `RULES.yaml` (design patterns and coding standards)

---

## Session Notes (Nov 22, 2025)

### What Happened This Session
1. Attempted to fix browser connection issues with Playwright's `launch_persistent_context`
2. Discovered fundamental MV3 extension bug in Playwright's bundled Chromium
3. Researched alternatives: CDP, Selenium, Synpress
4. Created comprehensive plan: `docs/BROWSER_CONNECTION_PLAN.md`
5. **Decision**: Use CDP (Chrome DevTools Protocol) to connect to system Chrome

### Files Modified
- `browser_automation/rugs_browser.py` - Reverted to HEAD (temporary page reload added then removed)
- `docs/BROWSER_CONNECTION_PLAN.md` - NEW: Complete 6-phase implementation plan
- `CLAUDE.md` - Updated with Phase 9 priority

### Files to Create Next Session
- `browser_automation/cdp_browser_manager.py` - New CDP-based browser manager
- `scripts/setup_chrome_profile.py` - One-time profile setup script

### Key Insight
The problem was never the code - Playwright + MV3 extensions is fundamentally broken.
CDP connection to YOUR Chrome is the proven solution used by all wallet automation projects.
