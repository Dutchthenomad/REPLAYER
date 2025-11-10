# Rugs Replay Viewer - Modular Architecture

## 🚀 Overview

A professional, modular replay viewer for Rugs.fun trading game with bot automation capabilities. This refactored version transforms the monolithic 2400+ line script into a clean, maintainable, and extensible architecture.

## 📁 Project Structure

```
REPLAYER/
├── run.sh                 # Launch script
├── README.md              # This file
├── requirements.txt       # Python dependencies
│
├── src/                   # Production code
│   ├── main.py           # Entry point
│   ├── config.py         # Centralized configuration
│   ├── models/           # Data models (Position, GameTick, etc.)
│   ├── core/             # Core business logic
│   │   ├── game_state.py     # Centralized state management
│   │   ├── replay_engine.py  # Replay playback logic
│   │   └── trade_manager.py  # Trading logic
│   ├── bot/              # Bot automation
│   │   └── strategies/   # Trading strategies
│   ├── ui/               # User interface
│   │   └── widgets/      # Reusable UI components
│   ├── services/         # Shared services
│   │   ├── event_bus.py  # Event-driven communication
│   │   └── logger.py     # Logging configuration
│   └── tests/            # Test suite
│
└── docs/                  # Documentation
    ├── CLAUDE.md          # Developer guide
    ├── game_mechanics/    # Game knowledge base
    └── archive/           # Historical reference
```

## ✨ Key Improvements

### 1. **Separation of Concerns**
- Each module has a single, clear responsibility
- UI logic separated from business logic
- Data models isolated from processing logic

### 2. **Event-Driven Architecture**
- Components communicate via event bus
- Loose coupling between modules
- Easy to add new features without modifying existing code

### 3. **Centralized State Management**
- Single source of truth for game state
- Observer pattern for reactive updates
- Thread-safe operations

### 4. **Proper Error Handling**
- Comprehensive error recovery
- Graceful degradation
- Detailed logging at all levels

### 5. **Memory Management**
- Bounded collections (deque with maxlen)
- Weak references to prevent leaks
- Resource cleanup on shutdown

### 6. **Configuration Management**
- All constants in config module
- Environment variable support
- JSON config file support

## 🔧 Installation & Quick Start

```bash
# Navigate to the project
cd REPLAYER

# Install dependencies
pip install -r requirements.txt

# Run the application
./run.sh

# Or run directly:
cd src && python3 main.py
```

## 🎮 Usage

### Basic Usage
```python
from rugs_replay_viewer.main import Application

app = Application()
app.run()
```

### Using Individual Components

#### State Management
```python
from core.game_state import GameState
from decimal import Decimal

# Create state instance
state = GameState(initial_balance=Decimal('0.100'))

# Subscribe to events
state.subscribe(StateEvents.BALANCE_CHANGED, handle_balance_change)

# Update state
state.update(current_price=Decimal('1.5'), current_tick=100)

# Get snapshot
snapshot = state.get_snapshot()
```

#### Event Bus
```python
from services.event_bus import event_bus, Events

# Subscribe to events
event_bus.subscribe(Events.GAME_TICK, handle_tick)

# Publish events
event_bus.publish(Events.TRADE_BUY, {'price': 1.2, 'amount': 0.01})
```

#### Trading Strategies
```python
from bot.strategies.base import create_strategy

# Create strategy
strategy = create_strategy('conservative')

# Get trading signal
signal = strategy.analyze(state_dict, history)
if signal.should_execute:
    execute_trade(signal)
```

## 🔌 Extending the System

### Adding a New Strategy

1. Create new strategy class:
```python
# bot/strategies/custom.py
from bot.strategies.base import TradingStrategy

class CustomStrategy(TradingStrategy):
    def analyze(self, state, history):
        # Your logic here
        pass
```

2. Register in factory:
```python
# bot/strategies/base.py
strategies = {
    'custom': CustomStrategy,
    # ...
}
```

### Adding a New UI Widget

1. Create widget class:
```python
# ui/widgets/custom_widget.py
import tkinter as tk

class CustomWidget(tk.Frame):
    def __init__(self, parent, state, event_bus):
        super().__init__(parent)
        # Widget implementation
```

2. Add to main window:
```python
# ui/main_window.py
self.custom_widget = CustomWidget(self, self.state, self.event_bus)
```

### Adding a New Event Type

1. Define event:
```python
# services/event_bus.py
class Events:
    CUSTOM_EVENT = "custom.event"
```

2. Publish event:
```python
event_bus.publish(Events.CUSTOM_EVENT, data)
```

3. Subscribe to event:
```python
event_bus.subscribe(Events.CUSTOM_EVENT, handler)
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=rugs_replay_viewer

# Run specific test module
pytest tests/test_core/test_game_state.py
```

## 📊 Performance Optimizations

1. **Lazy Loading**: Game files loaded on demand
2. **Event Throttling**: Chart updates throttled to reduce CPU
3. **Memory Bounds**: Collections limited to prevent unbounded growth
4. **Thread Pooling**: Background processing for non-UI tasks

## 🔒 Thread Safety

- All state mutations use locks
- Event bus uses thread-safe queues
- UI updates marshaled to main thread

## 📝 Configuration

### Environment Variables
```bash
export RUGS_RECORDINGS_DIR=/path/to/recordings
export RUGS_CONFIG_DIR=/path/to/config
export LOG_LEVEL=DEBUG
```

### Config File (settings.json)
```json
{
  "financial": {
    "initial_balance": "0.100",
    "max_bet": "1.0"
  },
  "ui": {
    "theme": "dark",
    "window_width": 1200
  }
}
```

## 🤝 Contributing

1. Follow the modular architecture
2. Add tests for new features
3. Update documentation
4. Use type hints
5. Follow PEP 8

## 📈 Benefits of This Architecture

### For Development
- **Easier debugging**: Issues isolated to specific modules
- **Faster development**: Work on modules independently
- **Better testing**: Unit test individual components
- **Code reuse**: Components usable in other projects

### For Maintenance
- **Clear structure**: Easy to understand codebase
- **Version control**: Cleaner diffs and merges
- **Documentation**: Self-documenting architecture
- **Refactoring**: Change internals without breaking interfaces

### For Performance
- **Lazy loading**: Load only what's needed
- **Resource management**: Proper cleanup and bounds
- **Async processing**: Non-blocking operations
- **Optimized updates**: Event-driven selective updates

## 🎯 Next Steps

1. **Add more strategies**: Implement balanced, momentum, mean-reversion strategies
2. **Enhanced UI**: Add more visualization widgets (heatmaps, indicators)
3. **Backtesting engine**: Systematic strategy testing
4. **Machine Learning**: Add ML-based prediction strategies
5. **WebSocket support**: Real-time game connection
6. **Database integration**: Store results and analytics
7. **Web interface**: Flask/FastAPI REST API
8. **Docker support**: Containerized deployment

## 📜 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

Refactored from the original monolithic design to demonstrate professional software architecture principles.
