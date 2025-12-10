# REPLAYER

**Watch. Learn. Trade.**

A desktop application that records and replays Rugs.fun gameplay, letting you study winning strategies and train AI bots to trade automatically.

![REPLAYER UI](replayer_ui_screenshot.png)

---

## What is This?

REPLAYER is a professional toolkit for the Rugs.fun crypto game. It does three things:

1. **Records Games** - Captures every price tick, every button press, every decision you make
2. **Replays Games** - Watch recorded games at any speed, study what worked and what didn't
3. **Trains Bots** - Use your recorded gameplay to teach AI bots how to trade like you

Think of it as a "player piano" for trading - record a human expert playing, then let the machine learn to play the same way.

---

## Why Use It?

### For Traders
- **Learn from yourself** - Review your best (and worst) trades
- **Study the game** - 1,500+ recorded games to analyze
- **Practice risk-free** - Replay mode costs nothing

### For Bot Builders
- **Human-quality data** - Record real gameplay, not simulated trades
- **Dual-state validation** - Every action verified against server state
- **Production ready** - Same code runs in replay and live modes

### For Researchers
- **Empirical analysis** - 899 games analyzed with temporal risk models
- **ML integration** - SidebetPredictor achieves 38% win rate (vs 17% random)
- **Complete price histories** - 500+ ticks per game with zero gaps

---

## Quick Start

```bash
# Clone and run
cd REPLAYER
./run.sh
```

That's it. The app opens with a game loaded and ready to play.

### Basic Controls

| Action | How |
|--------|-----|
| Load a game | File → Open Recording |
| Play/Pause | Spacebar or Play button |
| Speed up | Arrow keys or slider |
| Connect live | Live Feed → Connect |

---

## Key Features

### Dual-Mode Operation

Switch seamlessly between **Replay Mode** (study past games) and **Live Mode** (real-time trading):

| Mode | Purpose | Data Source |
|------|---------|-------------|
| Replay | Training & analysis | Recorded JSONL files |
| Live | Real trading | WebSocket feed |

The code is identical - only the tick source changes.

### Smart Recording (Phase 10)

The recording system captures everything needed to train high-quality bots:

- **Every button press** - BUY, SELL, percentage buttons, bet increments
- **State snapshots** - What you saw when you made each decision
- **Server validation** - Cross-check REPLAYER calculations vs server truth
- **Automatic sessions** - Recording starts when you connect, stops when you disconnect

### Bot Automation

Three built-in strategies, or build your own:

| Strategy | Risk | Best For |
|----------|------|----------|
| Conservative | Low | Capital preservation |
| Aggressive | High | Maximum returns |
| Sidebet | Moderate | 5x payout hunting |

Bots can run in **Backend Mode** (instant execution for training) or **UI Mode** (realistic timing for live prep).

### Browser Integration

Connect REPLAYER to your Chrome browser with Phantom wallet for live trading:

- CDP connection to existing Chrome session
- Wallet persistence across sessions
- Human-like button clicking patterns
- Execution timing metrics

---

## The Data

### What We Know (from 899 games)

| Metric | Value | Insight |
|--------|-------|---------|
| Rug Rate | 100% | Every game eventually rugs |
| Sweet Spot | 25-50x | 75% success rate, 200%+ returns |
| Median Lifespan | 138 ticks | Half of games dead by here |
| Optimal Hold | 48-60 ticks | For sweet spot entries |

### Recording Format

Games are saved as JSONL files with complete metadata:

```
rugs_recordings/
├── games/           # Price histories (500+ ticks each)
├── demonstrations/  # Human gameplay with actions
└── sessions/        # Multi-game recording sessions
```

Every file includes server seeds for verification.

---

## Architecture Highlights

For the technically curious, here's what's under the hood:

| Component | What It Does |
|-----------|-------------|
| EventBus | Pub/sub messaging (20+ event types) |
| GameState | Thread-safe state with RLock |
| TkDispatcher | Background → UI thread marshaling |
| UnifiedRecorder | Dual-layer recording (game + player) |
| BrowserExecutor | CDP browser automation |

**Test Coverage**: 275+ tests, all passing

**Lines of Code**: ~15,000 (production) + ~5,000 (tests)

---

## Project Structure

```
REPLAYER/
├── run.sh              # Launch script
├── src/
│   ├── main.py         # Entry point
│   ├── core/           # Game state, replay engine, trade manager
│   ├── bot/            # Strategies, controllers, browser automation
│   ├── ui/             # Tkinter interface, panels, widgets
│   ├── models/         # Data models (GameTick, Position, etc.)
│   ├── services/       # EventBus, recording, logging
│   └── tests/          # Test suite (275 tests)
├── browser_automation/ # Chrome CDP integration
├── docs/               # Design documents, specs
└── rugs_recordings/    # Recorded game data (symlink)
```

---

## Development Status

### Current: Phase 10.6 Complete

| Phase | Status | Description |
|-------|--------|-------------|
| 6 | Complete | WebSocket live feed |
| 7 | Complete | Menu UI, recording fixes |
| 8 | Complete | Browser automation, partial sells |
| 9 | Complete | CDP browser connection |
| 10 | Complete | Human demo recording system |

### What's Next: Phase 11

- RL model integration for autonomous trading
- Live trading validation
- Portfolio management dashboard

---

## Running Tests

```bash
cd src

# All tests
python3 -m pytest tests/ -v

# Quick check
python3 -m pytest tests/ -q

# With coverage
python3 -m pytest tests/ --cov=.
```

---

## Technical Notes

### Thread Safety

REPLAYER is heavily multi-threaded (WebSocket feed, browser automation, UI updates). Key patterns:

- `GameState` uses `RLock` - releases lock before callbacks
- `TkDispatcher` - all UI updates marshal to main thread
- `EventBus` - queue-based async processing

### Recording Validation

Phase 10.6 adds dual-state validation:

```
Local State (REPLAYER)  ←→  Server State (WebSocket)
         ↓                           ↓
    Compare with zero tolerance
         ↓
    Flag any drift for investigation
```

This ensures REPLAYER calculations match the real game exactly.

---

## License

MIT License - See LICENSE file

---

## Acknowledgments

Built for serious traders who want to understand the game deeply before risking real capital. The Rugs.fun community's empirical analysis made the statistical insights possible.

---

**Version**: 0.10.6 | **Phase**: 10.6 Complete | **Tests**: 275+ passing
