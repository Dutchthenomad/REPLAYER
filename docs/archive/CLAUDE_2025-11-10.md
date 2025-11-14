# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**REPLAYER** is a modular replay viewer and empirical analysis system for Rugs.fun trading game recordings. It serves dual purposes:

1. **Interactive Replay Viewer**: Professional Tkinter UI for viewing recorded games with bot automation
2. **Empirical Analysis Engine**: Statistical analysis of 900+ game recordings to extract trading patterns for RL bot training

This is part of a larger quantitative trading ecosystem including:
- **CV-BOILER-PLATE-FORK** (`~/Desktop/CV-BOILER-PLATE-FORK/`): YOLOv8 computer vision system for live gameplay detection
- **rugs-rl-bot** (`~/Desktop/rugs-rl-bot/`): Reinforcement learning trading bot (consumes REPLAYER analysis outputs)

**Key Architecture**: Event-driven modular design with centralized state management, transforming 2400+ line monolith into ~13,365 lines of clean, maintainable components across 141 tests.

## Quick Start Commands

### Running the Replay Viewer
```bash
# Launch GUI replay viewer (uses rugs-rl-bot venv for ML dependencies)
./run.sh

# Or directly with system Python:
cd src && python3 main.py
```

### Empirical Analysis (RL Bot Training Data)
```bash
# Comprehensive trading pattern analysis (entry zones, volatility, survival curves, profit distributions)
python3 analyze_trading_patterns.py
# Output: trading_pattern_analysis.json (~12KB, 140K+ samples)

# Position duration and temporal risk analysis
python3 analyze_position_duration.py
# Output: position_duration_analysis.json (~24KB, survival curves, hold times, rug timing)

# Game duration analysis
python3 analyze_game_durations.py

# View results
cat trading_pattern_analysis.json | jq .
cat position_duration_analysis.json | jq .
```

### Testing
```bash
# Run all tests (141 tests total)
cd src
python3 -m pytest tests/ -v

# Run specific test suite
python3 -m pytest tests/test_core/test_game_state.py -v
python3 -m pytest tests/test_bot/ -v

# Run with coverage
python3 -m pytest tests/ --cov=. --cov-report=html

# Run with detailed errors
python3 -m pytest tests/ -vv --tb=long

# Run specific test
python3 -m pytest tests/test_core/test_game_state.py::test_gamestate_creation -v
```

## Architecture Overview

### Modular Structure
```
REPLAYER/
├── run.sh                        # Launch script (uses rugs-rl-bot venv)
├── requirements.txt              # Python dependencies
├── analyze_trading_patterns.py  # Empirical analysis Phase 1-4 (870 lines)
├── analyze_position_duration.py # Duration analysis Phase 5 (600 lines)
├── analyze_game_durations.py    # Game lifespan analysis
│
├── src/                          # Production code (~8,000 lines)
│   ├── main.py                   # Application entry point
│   ├── config.py                 # Centralized configuration
│   │
│   ├── models/                   # Data models
│   │   ├── game_tick.py          # GameTick data model
│   │   ├── position.py           # Position tracking
│   │   ├── side_bet.py           # Side bet mechanics
│   │   └── enums.py              # Game phase enums
│   │
│   ├── core/                     # Core business logic
│   │   ├── game_state.py         # Centralized state management (~600 lines)
│   │   ├── replay_engine.py      # Playback control
│   │   ├── trade_manager.py      # Trade execution logic
│   │   └── validators.py         # Input validation
│   │
│   ├── bot/                      # Bot automation system
│   │   ├── interface.py          # BotInterface abstract base
│   │   ├── controller.py         # BotController (strategy selection)
│   │   ├── async_executor.py     # Async bot execution
│   │   └── strategies/           # Trading strategies
│   │       ├── base.py           # TradingStrategy base class
│   │       ├── conservative.py   # Conservative strategy
│   │       ├── aggressive.py     # Aggressive strategy
│   │       └── sidebet.py        # Sidebet-focused strategy
│   │
│   ├── ml/                       # ML Integration (symlinks to rugs-rl-bot)
│   │   ├── predictor.py          # SidebetPredictor (rug probability)
│   │   ├── feature_extractor.py  # Feature engineering
│   │   ├── data_processor.py     # Data processing
│   │   └── model.py              # ML model wrapper
│   │
│   ├── services/                 # Shared services
│   │   ├── event_bus.py          # Event-driven pub/sub system
│   │   └── logger.py             # Logging configuration
│   │
│   ├── ui/                       # User interface
│   │   ├── main_window.py        # Main application window
│   │   ├── layout_manager.py     # Panel positioning
│   │   ├── panels.py             # UI panels (Status, Chart, Trading, Bot)
│   │   └── widgets/              # Reusable UI components
│   │       ├── chart.py          # Price chart widget
│   │       └── toast_notification.py
│   │
│   ├── utils/                    # Utilities
│   │
│   └── tests/                    # Test suite (141 tests, ~3,500 lines)
│       ├── conftest.py           # Shared pytest fixtures
│       ├── test_models/          # Data model tests (12 tests)
│       ├── test_core/            # Core logic tests (63 tests)
│       ├── test_bot/             # Bot system tests (54 tests)
│       └── test_services/        # Service tests (12 tests)
│
├── docs/                         # Documentation
│   ├── game_mechanics/           # Game rules knowledge base
│   │   ├── GAME_MECHANICS.md     # Comprehensive game rules
│   │   └── side_bet_mechanics_v2.md
│   └── archive/                  # Historical reference
│
└── /home/nomad/rugs_recordings/  # Game recordings (929 JSONL files, ~100MB)
```

### Key Design Patterns

**1. Event-Driven Architecture**
- Components communicate via `EventBus` (pub/sub pattern)
- Loose coupling between UI, bot system, and state management
- Event types defined in `services.event_bus.Events` enum

**2. Centralized State Management**
- `GameState` class is single source of truth
- Observer pattern for reactive updates (`subscribe()`, `_emit()`)
- Thread-safe operations with `threading.RLock()`

**3. Strategy Pattern (Bot System)**
- `TradingStrategy` abstract base class
- Strategy selection via `create_strategy()` factory
- Strategies return `TradeSignal` with action, confidence, reasoning

**4. Data Model Separation**
- `GameTick`: Single tick of game data (price, phase, tick number)
- `Position`: Open/closed trade position
- `SideBet`: Insurance bet against rug events

## Core Components

### GameState (core/game_state.py)
Centralized state management with thread-safe operations and observer pattern.

**Key Methods**:
- `get(key, default)` - Thread-safe state getter
- `update(**kwargs)` - Update multiple state values
- `open_position(position_data)` - Open new position
- `close_position(exit_price, exit_time, exit_tick)` - Close position, calculate P&L
- `place_sidebet(amount, tick, price)` - Place sidebet
- `resolve_sidebet(won, tick)` - Resolve sidebet (5x payout if won)
- `subscribe(event, callback)` - Subscribe to state changes
- `get_snapshot()` - Get immutable state snapshot
- `calculate_metrics()` - Calculate win rate, PnL, max drawdown

**State Events** (emit via observer pattern):
- `BALANCE_CHANGED`, `POSITION_OPENED`, `POSITION_CLOSED`
- `SIDEBET_PLACED`, `SIDEBET_RESOLVED`
- `TICK_UPDATED`, `GAME_STARTED`, `GAME_ENDED`, `RUG_EVENT`

### EventBus (services/event_bus.py)
Thread-safe pub/sub event system for component communication.

**Key Methods**:
- `subscribe(event, handler)` - Subscribe to event
- `unsubscribe(event, handler)` - Unsubscribe
- `publish(event, data)` - Publish event to all subscribers

**Event Types** (services.Events enum):
- `GAME_START`, `GAME_END`, `GAME_TICK`, `GAME_RUG`
- `TRADE_BUY`, `TRADE_SELL`, `TRADE_EXECUTED`, `TRADE_FAILED`
- `SIDEBET_PLACED`, `SIDEBET_WON`, `SIDEBET_LOST`
- `BOT_ENABLED`, `BOT_DISABLED`, `BOT_ERROR`
- `UI_ERROR`, `UI_UPDATE`

### Bot System (bot/)
Pluggable strategy system for automated trading.

**BotController** (bot/controller.py):
- `set_strategy(name)` - Switch trading strategy
- `enable()` / `disable()` - Start/stop bot
- `process_tick(state_dict, tick_data)` - Process game tick, execute strategy

**Trading Strategies** (bot/strategies/):
- `conservative.py` - Low-risk, profit-taking focused
- `aggressive.py` - High-risk, momentum-based
- `sidebet.py` - Sidebet-focused (5x payout on rug)

**Creating New Strategies**:
```python
# bot/strategies/custom.py
from bot.strategies.base import TradingStrategy, TradeSignal

class CustomStrategy(TradingStrategy):
    def analyze(self, state: Dict, history: List) -> TradeSignal:
        # Your logic here
        return TradeSignal(
            action='BUY',
            confidence=0.8,
            reasoning='Custom logic triggered',
            metadata={'entry_price': state['current_price']}
        )
```

### ML Integration (ml/)
Integration with rugs-rl-bot's ML predictor for rug probability prediction.

**SidebetPredictor** (symlinked from rugs-rl-bot):
- Real-time rug probability predictions
- 14-dimensional feature vector (z-score, volatility, sweet spot timing)
- 5 prediction outputs per tick: `probability`, `confidence`, `ticks_to_rug_norm`, `is_critical`, `should_exit`
- Gradient Boosting Classifier (v3): 38.1% win rate, 754% ROI

**Note**: The `ml/` directory contains symlinks to `/home/nomad/Desktop/rugs-rl-bot/rugs_bot/sidebet/`. This allows REPLAYER to use the trained ML models without duplicating code.

### Configuration (config.py)
Centralized configuration with environment variable support.

**Key Sections**:
- `FINANCIAL` - Initial balance, bet limits, commission rates
- `GAME_RULES` - Sidebet multiplier (5x), cooldown (5 ticks), duration (40 ticks)
- `PLAYBACK` - Replay speed, auto-play settings
- `UI` - Window dimensions, theme, layout
- `PATHS` - Recordings directory (`/home/nomad/rugs_recordings/`)
- `BOT` - Bot decision delay, risk per trade, confidence threshold

## Game Mechanics (Critical Knowledge)

### Rugs.fun Trading Rules
- **Price Format**: Multiplier (e.g., `1.5x`, `2.0x`)
- **Typical Range**: 1x to 5x (most games rug before 10x)
- **100% Rug Rate**: All games eventually rug - exit timing is everything
- **P&L Calculation**: `pnl = bet_amount * (current_price / entry_price - 1)`

### Sidebet Mechanics
- **Payout**: 5x multiplier (400% profit) if rug occurs
- **Duration**: 40 ticks (10 seconds at 4 ticks/second)
- **Cooldown**: 5 ticks between bets
- **Example**: Bet 0.001 SOL → Win 0.005 SOL if rug occurs within 40 ticks
- **Constraint**: Only one active sidebet at a time

### Game Phases
1. **COOLDOWN**: Countdown between games
2. **PRESALE**: Pre-game betting phase
3. **ACTIVE**: Trading active, price rising
4. **RUGGED**: Game ended, all positions liquidated

## Empirical Analysis System

### Purpose
Analyze 900+ game recordings to generate empirical data for RL bot reward function design:
- Entry opportunity windows (profit potential at different multipliers)
- Volatility patterns (actual price swings)
- Survival curves (conditional rug probability over time)
- Optimal hold times by entry zone

### Key Findings (From Analysis Scripts)
**Sweet Spot**: 25-50x entry (75% success, 186-427% median returns)

**Median Game Lifespan**: 138 ticks (50% of games rug by this point)

**Temporal Risk**:
- 23.4% rug by tick 50
- 38.6% rug by tick 100
- 50% rug by tick 138 (median)
- 79.3% rug by tick 300

**Optimal Hold Times**:
- 1-10x entry → 65 ticks (61% success)
- 25-50x entry → 60 ticks (75% success) ⭐
- 50-100x entry → 48 ticks (75% success) ⭐
- 100x+ entry → 71 ticks (36% success)

**Stop Loss Reality**: 30-50% stop losses recommended (not 10%)
- Average drawdowns: 8-25%
- Recovery rate: 85-91%

### Analysis Output Files
- `trading_pattern_analysis.json` - 140K+ samples, entry zones, volatility, profit distributions
- `position_duration_analysis.json` - Survival curves, hold times, rug timing distribution

### Data Format (Game Recordings)
**Location**: `/home/nomad/rugs_recordings/`
**Format**: JSONL (one JSON object per line, one tick per line)
**Example Tick**:
```json
{
  "tick": 100,
  "price": 1.5,
  "phase": "ACTIVE",
  "active": true,
  "rugged": false,
  "trade_count": 42,
  "timestamp": "2025-11-08T12:34:56"
}
```

## Development Workflow

### Dependencies & Environment

**Python Version**: Python 3.12+

**Virtual Environment**: The project uses the rugs-rl-bot virtual environment for ML dependencies:
```bash
# Activate rugs-rl-bot venv
source ~/Desktop/rugs-rl-bot/.venv/bin/activate

# Install REPLAYER dependencies (optional, most are already in rugs-rl-bot venv)
pip install -r requirements.txt
```

**Note**: The `run.sh` script automatically uses the rugs-rl-bot venv if available, otherwise falls back to system Python.

### Adding a New UI Panel
```python
# ui/panels.py
class CustomPanel:
    def __init__(self, parent, state, event_bus):
        self.frame = tk.Frame(parent)
        self.state = state
        self.event_bus = event_bus
        self._setup_ui()

    def _setup_ui(self):
        # UI setup here
        pass
```

### Adding Event Handlers
```python
# Subscribe to events
event_bus.subscribe(Events.GAME_TICK, self.on_tick)

# Publish events
event_bus.publish(Events.TRADE_BUY, {'price': 1.5, 'amount': 0.001})
```

### Memory Management
- Use `collections.deque(maxlen=N)` for bounded collections
- Event bus uses weak references to prevent leaks
- Clean up resources in shutdown handlers

## Testing Strategy

**Test Coverage**: 141 tests across 8 test modules (~3,500 lines)
- **Data Models** (12 tests): Model creation, validation, serialization
- **Core Logic** (63 tests): GameState, TradeManager, ReplayEngine, validators
- **Bot System** (54 tests): Strategy behavior, signal generation, controller
- **Services** (12 tests): EventBus pub/sub, logging

**Test Structure**:
- `conftest.py` - Shared fixtures (mock GameState, EventBus, config)
- Use `@pytest.fixture` for reusable test components
- Mark slow tests with `@pytest.mark.slow`

**Running Specific Test Categories**:
```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Exclude slow tests
```

## Integration with Related Projects

### rugs-rl-bot (RL Trading Bot)
**Location**: `/home/nomad/Desktop/rugs-rl-bot/`
- Consumes REPLAYER empirical analysis outputs (JSON files)
- Uses analysis results to design RL reward functions
- Trained models can be integrated into REPLAYER for visual validation
- REPLAYER symlinks to rugs-rl-bot's sidebet predictor (`ml/` directory)

**Integration Points**:
- `trading_pattern_analysis.json` → Reward function parameters
- `position_duration_analysis.json` → Temporal risk models
- REPLAYER bot system → RL model deployment validation
- `ml/predictor.py` → Real-time rug probability predictions

**Commands (rugs-rl-bot)**:
```bash
# Run tests
cd ~/Desktop/rugs-rl-bot && .venv/bin/python -m pytest tests/ -v

# Train RL model
.venv/bin/python scripts/train_phase0_model.py --timesteps 250000

# Evaluate model
.venv/bin/python scripts/evaluate_phase0_model.py --model models/phase0_*/phase0_final.zip
```

### CV-BOILER-PLATE-FORK (Vision Training System)
**Location**: `/home/nomad/Desktop/CV-BOILER-PLATE-FORK/`
- YOLOv8 object detection for live gameplay
- Replaces OCR approach (0% accuracy → 62-94% accuracy)
- Session recorder generates training data for CV models

**Integration Points**:
- Game recordings used for CV training data annotation
- Live CV predictions can be replayed in REPLAYER for validation

**Commands (CV Boilerplate)**:
```bash
cd ~/Desktop/CV-BOILER-PLATE-FORK

# Run tests
.venv/bin/python3 -m pytest tests/ -v

# Train YOLO model
.venv/bin/python3 train_overnight.py
```

## Common Patterns

### State Updates
```python
# Get current state
balance = state.get('balance')

# Update state (triggers events)
state.update(
    current_price=Decimal('1.5'),
    current_tick=100,
    current_phase='ACTIVE'
)

# Subscribe to changes
state.subscribe(StateEvents.BALANCE_CHANGED, lambda event: print(event.data))
```

### Trade Execution
```python
# Open position
position = {
    'entry_price': Decimal('1.5'),
    'amount': Decimal('0.001'),
    'tick': 100
}
state.open_position(position)

# Close position (calculates P&L automatically)
result = state.close_position(
    exit_price=Decimal('2.0'),
    exit_tick=150
)
print(f"P&L: {result['pnl_sol']} SOL ({result['pnl_percent']}%)")
```

### Bot Strategy Execution
```python
# Enable bot with strategy
bot_controller.set_strategy('conservative')
bot_controller.enable()

# Process tick (bot auto-executes if signal generated)
state_dict = state.get_snapshot()
bot_controller.process_tick(state_dict, tick_data)
```

## Known Issues & Gotchas

1. **ML Symlinks**: The `ml/` directory uses symlinks to rugs-rl-bot. If rugs-rl-bot is moved/deleted, these will break.
2. **Virtual Environment**: Run script expects rugs-rl-bot venv at `~/Desktop/rugs-rl-bot/.venv/`
3. **Thread Safety**: Always use `with state._lock:` when accessing state directly (prefer public methods)
4. **Decimal Precision**: Use `Decimal` for all financial calculations to avoid floating point errors
5. **Event Ordering**: Events are processed asynchronously - don't assume ordering
6. **UI Updates**: Marshal UI updates to main thread using `root.after()`

## Performance Considerations

- **Lazy Loading**: Game files loaded on demand
- **Event Throttling**: Chart updates throttled to reduce CPU (configurable in config.py)
- **Memory Bounds**: Collections limited with `maxlen` to prevent unbounded growth
- **Analysis Scripts**: Process 900+ games in <30 seconds
- **Weak References**: EventBus uses weak references to prevent memory leaks

## Version Control & Development Workflow

### Git Workflow
```bash
# Check status
git status

# Stage changes
git add .

# Commit with descriptive message
git commit -m "Phase X: Description of changes"

# Push to GitHub
git push origin main
```

### Commit Guidelines
- Commit at the end of each major phase or milestone
- Use descriptive commit messages: "Phase X: [Feature/Fix] - Description"
- Include phase completion markers in commit messages
- Push to GitHub after each phase completion

### GitHub CLI Commands
```bash
# View repo info
gh repo view

# Create issues
gh issue create --title "Bug: Description" --body "Details"

# View pull requests
gh pr list

# View repository in browser
gh repo view --web
```

## Documentation Locations

- **CLAUDE.md** (this file): Primary development context for Claude Code
- **README.md**: High-level project overview and features
- **docs/game_mechanics/**: Game rules knowledge base
  - `GAME_MECHANICS.md` - Comprehensive game rules
  - `side_bet_mechanics_v2.md` - Sidebet mechanics details
- **docs/archive/**: Historical project documentation

## Related Commands

### Project Navigation
```bash
# Related projects
cd ~/Desktop/rugs-rl-bot                  # RL trading bot
cd ~/Desktop/CV-BOILER-PLATE-FORK         # CV training system
cd ~/Desktop/SOLANA\ EDU/2048-playwright-fork/2048-demo  # 2048 bot (reference)
```

### Data Management
```bash
# View recordings
ls -lh /home/nomad/rugs_recordings/ | head -20

# Count recordings
ls /home/nomad/rugs_recordings/*.jsonl | wc -l

# Sample recording
head -5 /home/nomad/rugs_recordings/game_*.jsonl | head -20

# Analyze recordings
python3 analyze_trading_patterns.py
python3 analyze_position_duration.py
python3 analyze_game_durations.py
```

### Code Quality
```bash
# Format code
black src/

# Lint code
flake8 src/
pylint src/

# Type checking
mypy src/
```
