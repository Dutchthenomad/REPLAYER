# Rugs Replay Viewer - Project Context

**Project Name**: Rugs.fun Replay Viewer (Modular Edition)
**Location**: `/home/nomad/Desktop/REPLAYER/rugs_replay_viewer/`
**Status**: ✅ **Phase 2B Complete** - Foundation Working, Issues Identified
**Version**: 1.0.0
**Last Updated**: 2025-11-03
**Created**: 2025-11-03 (5-hour sprint from monolithic refactor)

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Current Status](#current-status)
3. [What Was Accomplished](#what-was-accomplished)
4. [Architecture](#architecture)
5. [Known Issues](#known-issues)
6. [File Structure](#file-structure)
7. [Quick Start](#quick-start)
8. [Next Steps](#next-steps)
9. [Knowledge Base](#knowledge-base)
10. [Development Guidelines](#development-guidelines)

---

## 📖 Project Overview

### Purpose
A modular replay viewer for Rugs.fun game recordings that allows:
- Loading and visualizing game recordings (JSONL format)
- Running automated trading bots with different strategies
- Real-time playback with bot decision visualization
- Testing and evaluating bot performance

### Origin Story
This project was created through a **complete refactor** of a crashing 2400-line monolithic script. The original `game_ui_replay_viewer.py` would crash immediately when the bot was enabled due to thread safety issues, tight coupling, and poor architecture.

**Timeline**:
- **Problem Identified**: Monolithic script crashes on bot enable
- **Decision**: Skip incremental fixes, do complete modular refactor
- **Execution**: 5-hour sprint (Phases 1, 2A, 2B)
- **Result**: 31 modules, zero crashes, 100% test success

### Key Achievements
✅ Went from **crashing monolith** → **stable modular system** in 5 hours
✅ **Zero crashes** during 50-tick automated test with bot active
✅ **100% success rate** on all integration tests
✅ **Event-driven architecture** for clean UI updates
✅ **Thread-safe** state management
✅ **Strategy pattern** for pluggable bot behaviors

---

## 🎯 Current Status

### What's Working ✅

**Core Infrastructure** (Phase 1):
- GameState with thread-safe state management (RLock)
- TradeManager for buy/sell/sidebet execution
- Validators for all game rules
- Event bus with 26 event types
- Decimal precision for financial calculations
- Bounded collections (no memory leaks)

**Bot System** (Phase 2A):
- BotInterface (observation + action API)
- BotController (decision cycle: observe → decide → act)
- 3 strategies (conservative, aggressive, sidebet)
- Performance tracking (actions taken, success rate)
- CLI testing tool (tested with 719-tick real game)

**GUI Integration** (Phase 2B):
- MainWindow with Tkinter
- Game loading from JSONL files
- Playback controls (play/pause)
- Bot controls (enable/disable, strategy selection)
- Real-time displays (price, balance, P&L, position, bot decisions)
- Event-driven updates (zero polling)

**Testing**:
- 50/50 core integration tests passing
- All bot system tests passing
- Automated GUI test: 6/6 checks passing
- CLI test with real game: 100% success

### Known Issues ⚠️

**User Quote**: *"its got a number of issues that need to be addressed but this is a great foundation"*

Issues identified but not yet catalogued. See [Known Issues](#known-issues) section for tracking.

**Status**: Foundation is solid, issues are likely:
- UI/UX improvements needed
- Missing features
- Bot strategy refinements
- Performance optimizations
- Error handling edge cases

---

## 🏗️ What Was Accomplished

### Phase 1: Core Infrastructure (2 hours)

**Objective**: Build foundation without GUI

**Deliverables**:
1. **Data Models** (`models/`, 4 files, ~350 lines)
   - `enums.py` - Phase, PositionStatus, SideBetStatus
   - `game_tick.py` - GameTick with validation
   - `position.py` - Position with P&L calculations
   - `side_bet.py` - SideBet dataclass

2. **Services** (`services/`, 3 files, ~280 lines)
   - `logger.py` - Centralized logging
   - `event_bus.py` - Pub/sub event system (26 event types)

3. **Core Business Logic** (`core/`, 4 files, ~750 lines)
   - `validators.py` - Input validation, game rules
   - `game_state.py` - Centralized state management (thread-safe)
   - `trade_manager.py` - Trade execution logic

4. **Configuration** (`config.py`, ~180 lines)
   - All constants in one place
   - Financial limits, UI settings, game rules

5. **Testing** (`tests/test_core_integration.py`, ~280 lines)
   - 50 integration test checks
   - **Result**: 50/50 passing ✅

**Key Patterns Used**:
- Observer pattern (event bus)
- Thread safety (RLock)
- Decimal precision (financial calculations)
- Bounded collections (deques with maxlen)
- Weak references (event bus, prevent memory leaks)

---

### Phase 2A: Bot System (1.5 hours)

**Objective**: Extract bot logic from monolith, make testable

**Deliverables**:
1. **BotInterface** (`bot/interface.py`, 200 lines)
   - `bot_get_observation()` - Extract game state for bot
   - `bot_get_info()` - Get valid actions and constraints
   - `bot_execute_action()` - Execute BUY/SELL/SIDE/WAIT

2. **BotController** (`bot/controller.py`, 140 lines)
   - Decision cycle: observe → decide → execute
   - Strategy management (swap strategies dynamically)
   - Performance tracking (success rate, action counts)

3. **Strategies** (`bot/strategies/`, 3 files, 310 lines)
   - `base.py` - Abstract TradingStrategy class
   - `conservative.py` - Buy low (<1.5x), sell +20% or -15%, sidebet late
   - `aggressive.py` - Buy <3.0x, sell +50% or -30%, frequent sidebets
   - `sidebet.py` - Focus on testing sidebet mechanics

4. **Testing** (`tests/test_bot_system.py`, ~270 lines)
   - BotInterface tests
   - Strategy tests (all 3 strategies)
   - BotController tests
   - **Result**: All passing ✅

5. **CLI Tool** (`main_cli.py`, ~180 lines)
   - Headless testing without GUI
   - Load real game, run bot through entire playback
   - **Result**: 719 ticks, 50 decisions, 100% success ✅

**Key Patterns Used**:
- Strategy pattern (pluggable bot behaviors)
- Dependency injection (BotInterface receives state/manager)
- Clean API design (observation, info, action separation)

---

### Phase 2B: GUI Integration (1.5 hours)

**Objective**: Build minimal GUI that can load games and show bot playing

**Deliverables**:
1. **MainWindow** (`ui/main_window.py`, 450 lines)
   - Game loading (file dialog → JSONL parsing → state loading)
   - Playback controls (play/pause button, speed control)
   - Bot controls (enable/disable, strategy dropdown)
   - Real-time displays:
     - Price (current multiplier)
     - Tick (current / total)
     - Phase (COOLDOWN, PRESALE, ACTIVE, RUGGED)
     - Balance (current SOL)
     - P&L (session profit/loss)
     - Position (with unrealized P&L)
     - Bot decision (action + reasoning)
   - Event subscriptions (real-time updates via event bus)

2. **Main Entry Point** (`main.py`, ~40 lines)
   - Setup logging
   - Create Tkinter root
   - Initialize MainWindow
   - Start event loop

3. **Launch Script** (`RUN_GUI.sh`)
   - Quick launcher: `./RUN_GUI.sh`

4. **Automated Test** (`test_gui_automated.py`, 180 lines)
   - Test core GUI functionality without display
   - Load game, enable bot, simulate playback
   - **Result**: 6/6 checks passing ✅
     - Game loading: PASS
     - Bot initialization: PASS
     - Playback execution: PASS
     - Bot decision making: PASS
     - No crashes: PASS
     - Event system: PASS

**Key Patterns Used**:
- Event-driven UI (subscribe to events, update on publish)
- Playback thread (separate from main UI thread)
- Thread-safe state access (RLock prevents races)
- Clean separation (UI subscribes to business logic events)

---

## 🏛️ Architecture

### Design Principles

1. **Separation of Concerns**
   - Models: Data structures only
   - Services: Infrastructure (logging, events)
   - Core: Business logic (state, trades, validation)
   - Bot: Automation (strategies, decision-making)
   - UI: Display only (no business logic)

2. **Event-Driven**
   - Components publish events
   - Other components subscribe
   - Zero polling, instant updates
   - Weak references prevent memory leaks

3. **Thread Safety**
   - GameState uses RLock for all mutations
   - Event marshaling to main thread
   - No shared mutable state without protection

4. **Strategy Pattern**
   - BotController accepts any TradingStrategy
   - Easy to add new strategies
   - Swap strategies without restart

5. **Testability**
   - Small focused modules (<500 lines)
   - Dependency injection
   - Business logic separate from UI
   - 100% of core/bot logic tested

### Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                         MainWindow (UI)                      │
│  - Subscribes to events                                      │
│  - Updates displays                                          │
│  - Handles user input                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Uses
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                  BotController (Bot)                         │
│  - Manages strategy                                          │
│  - Executes decision cycle                                   │
│  - Tracks performance                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Uses
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                  BotInterface (Bot)                          │
│  - bot_get_observation()                                     │
│  - bot_get_info()                                            │
│  - bot_execute_action()                                      │
└─────────┬────────────────────┬───────────────────────────────┘
          │                    │
          │ Uses               │ Uses
          ↓                    ↓
┌──────────────────┐  ┌──────────────────────────────────────┐
│   GameState      │  │      TradeManager                     │
│   (Core)         │  │      (Core)                           │
│                  │  │                                        │
│ - Current tick   │  │ - execute_buy()                       │
│ - Balance        │  │ - execute_sell()                      │
│ - Positions      │  │ - execute_sidebet()                   │
│ - Side bets      │  │ - Uses validators                     │
│ - Thread-safe    │  │ - Publishes events                    │
│ - Publishes      │  │                                        │
│   events         │  │                                        │
└──────────────────┘  └──────────────────────────────────────┘
          │                    │
          └────────┬───────────┘
                   │
                   │ Publishes
                   ↓
          ┌────────────────────┐
          │     EventBus       │
          │    (Services)      │
          │                    │
          │ - 26 event types   │
          │ - Weak references  │
          │ - Pub/sub pattern  │
          └────────────────────┘
```

### Event Flow Example

```
User clicks "Play" button
  ↓
MainWindow._playback_loop() starts (separate thread)
  ↓
Loop: For each tick
  ↓
  ├─→ state.set_tick_index(i)
  │     ↓
  │     └─→ event_bus.publish(Events.STATE_TICK_CHANGED, {...})
  │           ↓
  │           └─→ MainWindow._on_tick_changed() [subscribed]
  │                 ↓
  │                 └─→ root.after(0, update_display)  [main thread]
  │
  └─→ bot_controller.execute_step()
        ↓
        ├─→ bot.bot_get_observation()
        │
        ├─→ bot.bot_get_info()
        │
        ├─→ strategy.decide(observation, info)
        │
        └─→ bot.bot_execute_action(action_type, amount)
              ↓
              └─→ manager.execute_buy(amount)
                    ↓
                    ├─→ state.update_balance(new_balance, reason)
                    │     ↓
                    │     └─→ event_bus.publish(Events.STATE_BALANCE_CHANGED, {...})
                    │           ↓
                    │           └─→ MainWindow._on_balance_changed() [subscribed]
                    │                 ↓
                    │                 └─→ Update balance label [main thread]
                    │
                    └─→ state.open_position(position)
                          ↓
                          └─→ event_bus.publish(Events.STATE_POSITION_OPENED, {...})
                                ↓
                                └─→ MainWindow._on_position_opened() [subscribed]
                                      ↓
                                      └─→ Update position display [main thread]
```

**Key Point**: No polling! All updates are event-driven.

---

## ⚠️ Known Issues

**Status**: Issues identified by user but not yet catalogued

**User Quote**: *"its got a number of issues that need to be addressed but this is a great foundation"*

### Issue Tracking Process

When issues are identified:
1. Document in `KNOWN_ISSUES.md`
2. Categorize (bug, feature request, enhancement, etc.)
3. Prioritize (critical, high, medium, low)
4. Assign to roadmap phase
5. Create test cases when fixing

### Likely Issue Categories

Based on typical replay viewer needs:

**UI/UX Issues** (probable):
- Chart visualization missing
- Better controls needed
- Visual feedback improvements
- Keyboard shortcuts
- Speed control UI

**Feature Gaps** (probable):
- Full chart with price history
- Position history display
- Session statistics panel
- Export/save functionality
- Multiple game loading

**Bot Strategy** (probable):
- Strategies too simple
- Need refinement based on game mechanics
- Missing pattern recognition
- Side bet timing needs work

**Performance** (possible):
- Playback speed optimization
- Memory usage with long games
- Large file loading

**Error Handling** (possible):
- Edge case crashes
- Invalid file handling
- Corrupted data recovery

**See**: `/home/nomad/Desktop/REPLAYER/DOCS/KNOWN_ISSUES.md` (to be created)

---

## 📁 File Structure

```
rugs_replay_viewer/
├── models/                          # Data structures
│   ├── __init__.py
│   ├── enums.py                     # Phase, PositionStatus, SideBetStatus
│   ├── game_tick.py                 # GameTick with validation
│   ├── position.py                  # Position with P&L calculations
│   └── side_bet.py                  # SideBet dataclass
│
├── services/                        # Infrastructure
│   ├── __init__.py
│   ├── logger.py                    # Centralized logging
│   └── event_bus.py                 # Pub/sub event system (26 events)
│
├── core/                            # Business logic
│   ├── __init__.py
│   ├── validators.py                # Input validation, game rules
│   ├── game_state.py                # Centralized state management
│   └── trade_manager.py             # Trade execution logic
│
├── bot/                             # Bot system
│   ├── __init__.py
│   ├── interface.py                 # BotInterface (observation + action API)
│   ├── controller.py                # BotController (decision cycle)
│   └── strategies/
│       ├── __init__.py
│       ├── base.py                  # Abstract TradingStrategy
│       ├── conservative.py          # Conservative strategy
│       ├── aggressive.py            # Aggressive strategy
│       └── sidebet.py               # Sidebet-focused strategy
│
├── ui/                              # User interface
│   ├── __init__.py
│   └── main_window.py               # Main GUI window
│
├── tests/                           # Integration tests
│   ├── test_core_integration.py     # Core tests (50 checks)
│   └── test_bot_system.py           # Bot tests
│
├── config.py                        # Configuration constants
├── main.py                          # GUI entry point
├── main_cli.py                      # CLI test tool
├── test_gui_automated.py            # Automated GUI test
├── RUN_GUI.sh                       # Launch script
│
├── CHECKPOINT_1C_PROGRESS.md        # Refactor progress notes
├── PHASE_1_COMPLETE.md              # Phase 1 summary
├── PHASE_2_COMPLETE.md              # Phase 2 summary
└── GUI_TEST_VERIFICATION.md         # Test verification report
```

**Total**: 31 files, ~3,200 lines of code

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Tkinter (usually included with Python)
- Game recordings in JSONL format at `~/rugs_recordings/`

### Installation
```bash
cd /home/nomad/Desktop/REPLAYER/rugs_replay_viewer

# Install dependencies (if any)
# pip install -r requirements.txt  # (not needed yet, pure stdlib)

# Make launch script executable
chmod +x RUN_GUI.sh
```

### Running the GUI
```bash
# Option 1: Use launch script
./RUN_GUI.sh

# Option 2: Direct Python
python3 main.py
```

### Using the GUI

1. **Load a Game**
   - Click "📁 Load Game"
   - Navigate to `~/rugs_recordings/`
   - Select any `game_*.jsonl` file
   - Game loads, shows tick count

2. **Select Strategy**
   - Choose from dropdown: conservative/aggressive/sidebet
   - Conservative recommended for first test

3. **Enable Bot**
   - Click "🤖 Enable Bot"
   - Button turns green
   - Shows "Bot Active (strategy_name)"

4. **Play**
   - Click "▶ Play"
   - Game starts playing (10 ticks/second default)
   - Price updates in real-time
   - Balance updates in real-time
   - Bot makes decisions (shown in Bot Decision panel)
   - See bot reasoning for each action

5. **Change Strategy Mid-Game** (if desired)
   - Click "🤖 Disable Bot"
   - Change strategy dropdown
   - Click "🤖 Enable Bot" again
   - Bot uses new strategy

### Testing Without GUI

**CLI Test** (headless, full game playback):
```bash
python3 main_cli.py
```

**Automated GUI Test** (core functionality):
```bash
python3 test_gui_automated.py
```

**Integration Tests**:
```bash
# Core tests
python3 tests/test_core_integration.py

# Bot tests
python3 tests/test_bot_system.py
```

---

## 🎯 Next Steps

### Immediate Priorities (Phase 3)

**User Feedback Needed**:
1. ❓ What specific issues did you encounter?
2. ❓ Which features are most important to add?
3. ❓ What improvements to existing features?
4. ❓ Performance concerns?

**Likely Next Work**:
1. **Issue Cataloguing** (1-2 hours)
   - Document all identified issues
   - Prioritize by severity/importance
   - Create test cases for each

2. **Critical Fixes** (varies by issue)
   - Fix any crashes or major bugs
   - Address user pain points
   - Improve error handling

3. **Feature Additions** (based on priorities)
   - Chart visualization (candlestick or line chart)
   - Session statistics panel
   - Position history display
   - Speed control UI
   - Export functionality

4. **Bot Improvements** (optional)
   - Refine strategies based on game mechanics
   - Add pattern recognition
   - Improve side bet timing
   - Risk management enhancements

### Future Roadmap (Phase 4+)

**Advanced Features**:
- Save/load sessions
- Multi-game comparison
- Strategy backtesting framework
- Performance analytics dashboard
- Keyboard shortcuts
- Configuration UI

**Bot Evolution**:
- ML-based strategies
- Pattern learning from recordings
- Adaptive strategies
- Multi-strategy ensembles

**Architecture**:
- Plugin system for custom strategies
- API for external tools
- Web-based UI alternative
- Real-time game integration (live play)

---

## 📚 Knowledge Base

### Related Documentation

**In DOCS folder** (`/home/nomad/Desktop/REPLAYER/DOCS/`):
- `GAME_MECHANICS.md` - Comprehensive game rules, Socket.IO architecture
- `RUGS_GAME_MECHANICS_KNOWLEDGE_BASE.md` - RAG-style cumulative knowledge
- `side_bet_mechanics_v2.md` - Side bet mechanics deep dive
- `SIDEbET kNOWhOW.txt` - Side bet probability analysis

**In Project**:
- `PHASE_1_COMPLETE.md` - Phase 1 summary (core infrastructure)
- `PHASE_2_COMPLETE.md` - Phase 2 summary (bot + GUI)
- `GUI_TEST_VERIFICATION.md` - Test verification report
- `CHECKPOINT_1C_PROGRESS.md` - Refactor progress notes

### Key Concepts

**Game Mechanics**:
- Presale phase (tick -1, guaranteed entry)
- Active phase (ticks 0→N, dynamic pricing)
- Rug event (instant liquidation of all positions)
- Side bets (5:1 payout, 40-tick window)
- Multiple positions allowed per game

**Critical Rules**:
- Positions held during rug = 100% loss
- Only defense = active side bet
- Presale positions locked until active phase
- One side bet active at a time
- 5-tick cooldown between side bets

**Bot Decision Framework**:
- Entry zones (presale, low price)
- Exit zones (profit target, stop loss)
- Risk zones (high multiplier, high volatility)
- Side bet timing (probability curves)

### Data Format

**Game Recording** (JSONL):
```json
{"type": "tick", "game_id": "...", "tick": 0, "timestamp": "...", "price": 1.0, "phase": "ACTIVE", "active": true, "rugged": false, "cooldown_timer": 0, "trade_count": 0}
```

**Fields**:
- `type`: "tick" (other types may exist)
- `game_id`: Unique game identifier
- `tick`: Tick number (-1 for presale, 0+ for active)
- `timestamp`: ISO format timestamp
- `price`: Multiplier (Decimal)
- `phase`: "COOLDOWN", "PRESALE", "ACTIVE", "RUGGED"
- `active`: Boolean (game is active)
- `rugged`: Boolean (game has rugged)
- `cooldown_timer`: Seconds remaining in cooldown
- `trade_count`: Number of trades in game

---

## 🛠️ Development Guidelines

### Code Style

**General**:
- Follow PEP 8
- Type hints encouraged
- Docstrings for all public functions
- Inline comments for complex logic

**Patterns**:
- Event-driven communication (publish/subscribe)
- Dependency injection
- Strategy pattern for bot behaviors
- Immutable dataclasses where possible
- Thread safety (RLock for shared state)

### Adding a New Bot Strategy

1. Create new file in `bot/strategies/`
2. Inherit from `TradingStrategy` base class
3. Implement `decide(observation, info)` method
4. Add to `__init__.py` and `get_strategy()` function
5. Write tests in `tests/test_bot_system.py`

**Example**:
```python
# bot/strategies/my_strategy.py
from .base import TradingStrategy
from decimal import Decimal
from typing import Dict, Tuple, Optional

class MyStrategy(TradingStrategy):
    """My custom trading strategy"""

    def decide(self, observation: Dict, info: Dict) -> Tuple[str, Optional[Decimal], str]:
        # Extract data
        price = Decimal(str(observation['current_state']['price']))
        balance = Decimal(str(observation['wallet']['balance']))

        # Your logic here
        if price < 2.0 and info['can_buy']:
            return ("BUY", Decimal('0.005'), "Entry at low price")

        return ("WAIT", None, "Waiting for setup")
```

### Adding UI Features

1. Add UI elements in `ui/main_window.py`
2. Subscribe to relevant events in `_setup_event_subscriptions()`
3. Create update handlers (e.g., `_on_new_event()`)
4. Use `root.after(0, update_fn)` for thread-safe updates
5. Update layout as needed

### Testing Guidelines

**Before Committing**:
1. Run all integration tests
2. Run automated GUI test
3. Manually test GUI with real game
4. Check for memory leaks (long playback)
5. Verify thread safety (no crashes)

**Test Coverage**:
- Unit tests for pure functions
- Integration tests for component interactions
- Automated GUI test for core functionality
- Manual GUI test for user experience

---

## 📞 Support & Troubleshooting

### Common Issues

**GUI doesn't start**:
```bash
# Check Tkinter availability
python3 -c "import tkinter; print('Tkinter available')"

# Check error output
python3 main.py 2>&1 | head -50
```

**Bot doesn't work**:
1. Check console output for errors
2. Try different strategy
3. Check game file is valid JSONL
4. Verify game has enough ticks

**Display doesn't update**:
1. Check event bus subscriptions
2. Verify thread is running
3. Check for exceptions in console
4. Try reloading game

### Debug Mode

Enable debug logging:
```python
# Edit main.py
setup_logging(level=logging.DEBUG)  # Change from INFO
```

### Getting Help

1. Check documentation in `/home/nomad/Desktop/REPLAYER/DOCS/`
2. Review test files for usage examples
3. Check event bus subscriptions in `ui/main_window.py`
4. Review state management in `core/game_state.py`

---

## 📝 Version History

### v1.0.0 (2025-11-03)

**Initial Release** - Complete modular refactor

**Changes**:
- ✅ Extracted all components from 2400-line monolith
- ✅ Created 31 focused modules (<500 lines each)
- ✅ Implemented event-driven architecture
- ✅ Added thread-safe state management
- ✅ Built bot system with 3 strategies
- ✅ Created GUI with real-time updates
- ✅ Achieved 100% test success rate
- ✅ Zero crashes during testing

**Metrics**:
- Files: 31
- Lines of code: ~3,200
- Test success: 100% (50/50 core, all bot tests)
- Automated GUI test: 6/6 passing
- Time to build: 5 hours

**Known Issues**: Identified by user, pending cataloguing

---

## 🎯 Project Goals

### Immediate Goals
1. ✅ Create stable, modular architecture
2. ✅ Enable bot testing without crashes
3. ✅ Real-time visualization of bot decisions
4. ⏳ Address identified issues
5. ⏳ Add missing features

### Long-Term Goals
1. Professional-grade replay analysis tool
2. Bot strategy development platform
3. Performance evaluation framework
4. Integration with live trading (future)
5. Educational tool for bot development

---

## 🤝 Contributing

### Code Organization
- Keep modules focused (<500 lines)
- Use event bus for cross-component communication
- Maintain thread safety (use RLock)
- Write tests for all new code
- Document public APIs

### Pull Request Process
1. Write tests first (TDD)
2. Implement feature
3. Run all tests
4. Update documentation
5. Test GUI manually
6. Create PR with description

---

**Last Updated**: 2025-11-03
**Status**: Foundation complete, issues identified, ready for Phase 3
**Next Session**: Catalogue and prioritize identified issues

---

*This is the primary context document for the Rugs Replay Viewer project. Update after significant changes.*
