# REPLAYER - Session Planning Document
**Date**: 2025-11-14
**Session Goal**: Planning & Documentation Cleanup
**Status**: NO CODING - Consensus Building

---

## Executive Summary

**Current State**: All audit fixes complete (7 findings resolved), production-ready code pending commit

**Meta Goal**: Build a dual-mode replay/live system with **perfect fidelity** that will eventually become a gymnasium environment for RL bot training at scale

**Immediate Focus**:
1. Understand current state and what we're keeping
2. Plan live feed integration phases
3. Clean up documentation
4. Establish testing methodology for RL-compatible infrastructure

**NO ML/TRAINING WORK IN THIS PHASE** - We're building the infrastructure only

---

## 1. Meta Context: The End Vision

### What REPLAYER Will Become

**Primary Purpose**: Dual-mode game viewer with perfect fidelity
- **Replay Mode**: Play back recorded JSONL sessions frame-by-frame
- **Live Mode**: Display live WebSocket feed in real-time
- **Perfect Fidelity**: Replay and live use IDENTICAL code paths

**Secondary Purpose**: RL Training Environment (Future)
- **Gymnasium-compatible**: Well-defined observation/action spaces
- **Deterministic**: Same replay = same results = reproducible training
- **Scalable**: Can train bots at speed using recorded or live data
- **Observable**: Full state visibility for reward function design

### Why This Matters Now

Even though we're NOT implementing ML/training yet, we must design with this in mind:

1. **Code Paths Must Be Identical**
   - Replay and live can't diverge in behavior
   - Same GameState, same TradeManager, same event flow
   - Only difference: tick SOURCE (file vs WebSocket)

2. **Testing Must Consider RL Use Cases**
   - Not just "does it work" but "can it train agents"
   - Determinism is critical (same inputs → same outputs)
   - State observability must be complete
   - Reward-relevant events must be captured

3. **Architecture Must Support Future Gymnasium Wrapper**
   - Clean observation space (current state snapshot)
   - Clean action space (BUY/SELL/SIDEBET/WAIT)
   - Reset semantics (load game, reset state)
   - Step semantics (advance tick, return obs/reward/done)

**Bottom Line**: We're building the foundation for RL training without implementing RL training

---

## 2. Reference Implementation: continuous_game_recorder.py

### Location
`/home/nomad/Desktop/REPLAYER/external/continuous_game_recorder.py` (325 lines)

### What It Does
- Connects to Rugs.fun via `WebSocketFeed` from CV-BOILER-PLATE-FORK
- Records live games to JSONL files (one file per game)
- Implements keep-alive mechanism (4-minute ping to prevent timeout)
- Handles graceful shutdown with statistics

### Key Architecture Patterns

**WebSocket Connection**:
```python
from core.rugs.websocket_feed import WebSocketFeed

websocket = WebSocketFeed(log_level='WARN')

@websocket.on('connected')
def on_connected(info):
    # Connection established, start keep-alive

@websocket.on('signal')
def on_signal(signal):
    # Every tick of the game
    tick_data = {
        'game_id': signal.gameId,
        'tick': signal.tickCount,
        'price': signal.price,
        'phase': signal.phase,
        'active': signal.active,
        'rugged': signal.rugged,
        'cooldown_timer': signal.cooldownTimer,
        'trade_count': signal.tradeCount
    }

@websocket.on('gameComplete')
def on_game_complete(data):
    # Game ended, finalize recording

websocket.connect()
```

**Keep-Alive Mechanism**:
- Background thread pings every 4 minutes
- Prevents WebSocket timeout during long sessions
- Logs connection status via `get_metrics()`

**File Structure** (JSONL per game):
```json
{"type": "game_start", "timestamp": "...", "game_id": "..."}
{"type": "tick", "timestamp": "...", "tick": 1, "price": 1.0, ...}
{"type": "tick", "timestamp": "...", "tick": 2, "price": 1.1, ...}
...
{"type": "game_end", "timestamp": "...", "total_ticks": 150, ...}
```

### What We'll Reuse

✅ **WebSocketFeed class** - Port from CV-BOILER-PLATE-FORK to REPLAYER
✅ **Event handlers** - `connected`, `signal`, `gameComplete`
✅ **Keep-alive pattern** - 4-minute background ping
✅ **Data structure** - Tick format matches our GameTick model
✅ **Recording logic** - Adapt ContinuousRecorder for dual recording/display

---

## 3. Current State: What We're Keeping

### Production Code (src/) - **KEEP ALL AS-IS**

**Status**: ✅ All audit fixes applied, production-ready

```
src/
├── main.py                    # Entry point (with fixes)
├── config.py                  # Configuration
│
├── models/                    # Data models
│   ├── game_tick.py           # ✅ Compatible with WebSocket signal format
│   ├── position.py
│   ├── side_bet.py
│   └── enums.py
│
├── core/                      # Core logic (WITH AUDIT FIXES)
│   ├── game_state.py          # ✅ Fixed: reset, metrics, rug_detected
│   ├── replay_engine.py       # ✅ Fixed: lifecycle, game_id, GAME_START/END
│   ├── trade_manager.py       # ✅ Fixed: exit_tick tracking
│   ├── game_queue.py          # Multi-game queue
│   └── validators.py          # Input validation
│
├── bot/                       # Bot system
│   ├── interface.py           # Bot API
│   ├── controller.py          # Bot control
│   ├── async_executor.py      # Async execution
│   └── strategies/            # Trading strategies (3 strategies)
│
├── ml/                        # ML integration (symlinks to rugs-rl-bot)
│   ├── predictor.py           # Sidebet predictor (38.1% win rate, 754% ROI)
│   ├── feature_extractor.py   # ✅ Fixed: IQR division guard
│   └── ...
│
├── services/                  # Services (WITH AUDIT FIXES)
│   ├── event_bus.py           # ✅ Fixed: shutdown, RUG_DETECTED event
│   └── logger.py              # Logging
│
├── ui/                        # User interface (WITH AUDIT FIXES)
│   ├── main_window.py         # ✅ Fixed: TkDispatcher, multi-game auto-resume
│   ├── tk_dispatcher.py       # ✅ NEW: Thread-safe UI updates
│   ├── panels.py              # 5 specialized panels
│   ├── layout_manager.py      # Panel positioning
│   └── widgets/               # Reusable components
│
└── tests/                     # Test suite (148 tests, WITH ADDITIONS)
    ├── conftest.py            # Shared fixtures
    ├── test_core/             # ✅ Added: test_replay_engine.py
    ├── test_services/         # ✅ Updated: event_bus shutdown tests
    ├── test_ml/               # ✅ NEW: feature_extractor tests
    └── test_ui/               # ✅ NEW: tk_dispatcher tests
```

**Key Fixes from Audit** (All Complete):
1. ✅ UI thread safety (TkDispatcher)
2. ✅ Rug event handling (positions liquidated, sidebets resolved)
3. ✅ State reset hygiene (preserves flags, no bleed)
4. ✅ Exit tick tracking (parameter order fixed)
5. ✅ Event bus shutdown (handles full queues)
6. ✅ Metrics accuracy (realized P&L, not balance deltas)
7. ✅ Game ID propagation
8. ✅ Feature extractor IQR (guards zero division)

### Analysis Scripts (Root Level) - **KEEP**

**Production analysis tools** for RL training data generation:

✅ `analyze_trading_patterns.py` (689 lines) - Entry zones, volatility, survival curves
✅ `analyze_position_duration.py` (659 lines) - Temporal risk, hold times
✅ `analyze_game_durations.py` (161 lines) - Game lifespan analysis
✅ `analyze_volatility_spikes.py` (329 lines) - Volatility patterns
✅ `analyze_spike_timing.py` (358 lines) - Spike timing analysis

**Output Files** (Generated empirical data):
- `trading_pattern_analysis.json` (12KB, 140K+ samples)
- `position_duration_analysis.json` (24KB, survival curves)

**Purpose**: These feed empirical findings into RL reward function design

### Documentation - **NEEDS CLEANUP**

#### Keep (Active)

✅ `README.md` - Project overview
✅ `AGENTS.md` - **NEW** Repository guidelines (most current, concise)
✅ `run.sh` - Launch script
✅ `requirements.txt` - Dependencies
✅ `docs/Codex/` - **NEW** Audit documentation (all files)
✅ `docs/game_mechanics/` - Game rules knowledge base
✅ `docs/archive/` - Historical reference

#### Update/Archive (Outdated)

⚠️ **NEEDS UPDATE**:
- `CLAUDE.md` (root) - Outdated (claims Phase 5, 85%, wrong test count)
- `docs/CLAUDE.md` - Very outdated (references non-existent MODULAR path)

⚠️ **REVIEW FOR ARCHIVAL**:
- `CLEANUP_COMPLETE.md` - Phase cleanup notes
- `VOLATILITY_SPIKE_VALIDATION.md` - Analysis notes
- `SPIKE_TIMING_ANALYSIS.md` - Analysis notes
- `docs/LIVE_INTEGRATION_PLAN.md` - Duplicate of Codex version?

### Debug/Test Scripts - **REVIEW**

⚠️ **DECISION NEEDED**:
- `debug_volatility.py` - One-off debug script (delete or archive?)
- `test_multi_game.py` - Manual test script (keep for testing or archive?)
- `setup_playwright_mcp.sh` - MCP setup (still needed?)

### External Reference - **KEEP**

✅ `external/continuous_game_recorder.py` - **WebSocket reference implementation**

---

## 4. RL Testing Methodology (Meta Context)

### Why This Matters

Traditional testing (unit, integration) is insufficient for RL systems because:
- **Bugs don't crash** - They create subtle misaligned incentives
- **Reward hacking emerges** - After thousands of episodes, not in unit tests
- **Integration bugs** - Only visible in aggregate statistics
- **Degenerate strategies** - Agent learns exploits, not intended behavior

### Recommended Testing Stack (Future Implementation)

**NOT implementing now, but designing infrastructure to support:**

#### 1. Property-Based Testing
**Tool**: `hypothesis`
**Purpose**: Reward functions must satisfy mathematical properties

Example properties to test (FUTURE):
- **Monotonicity**: Higher rug probability → higher penalty
- **Bounds**: All rewards in defined range
- **Consistency**: Same state+action → same reward
- **Non-exploitability**: No action combo yields infinite reward

#### 2. Reward Decomposition Unit Tests
**Tool**: `pytest` with fixtures
**Purpose**: Test each reward component in isolation

Future tests:
- `test_rug_avoidance_reward()` - Verify sidebet signal integration
- `test_pnl_reward()` - Verify profit scaling
- `test_bankruptcy_penalty()` - Verify threshold triggering
- `test_total_reward_bounds()` - Verify no overflow

#### 3. Synthetic Episode Testing
**Tool**: Custom framework using `gymnasium`
**Purpose**: Hand-crafted edge case episodes

Future scenarios:
- "Agent holds through obvious rug signal" → massive penalty
- "Agent exits on false positive" → small penalty
- "Agent exits just before rug" → large reward
- "Agent bankrupts from greed" → terminal penalty

#### 4. Reward Distribution Analysis
**Tool**: `matplotlib`, `pandas`, `scipy.stats`
**Purpose**: Diagnostic checks (not pass/fail)

Future diagnostics:
- Histogram of rewards per episode
- Detect reward imbalance (99% from one component)
- Check for reward sparsity (too many zeros)
- Verify reward variance matches design intent

#### 5. Behavioral Integration Tests
**Tool**: Minimal training runs (100-500 episodes)
**Purpose**: Catch reward hacking early

Future red flags:
- Agent always exits immediately (overfit to early-exit bonus)
- Agent never exits (rug penalty too weak)
- Agent spams single action (reward exploitation)
- Reward magnitude diverges (numerical instability)

#### 6. Regression Testing
**Tool**: `pytest-benchmark` with stored baselines
**Purpose**: Lock in known-good behaviors

Future baselines:
- Known rug at tick 300 → agent should exit by tick 250
- Store expected reward trajectory
- Any reward function change must pass all baselines

### What We Need to Design NOW

To support RL testing later, we must ensure:

1. **Deterministic Replay**
   - Same JSONL file → same GameState evolution
   - No randomness in core logic
   - Reproducible bot decisions

2. **Complete State Observability**
   - `GameState.get_snapshot()` captures ALL relevant state
   - No hidden state that affects rewards
   - Full history available (closed positions, metrics)

3. **Clean Action Space**
   - Well-defined actions (BUY/SELL/SIDEBET/WAIT)
   - Actions validated and executed consistently
   - Action effects observable in state

4. **Event Traceability**
   - All reward-relevant events captured (GAME_RUG, POSITION_CLOSED, etc.)
   - EventBus provides audit trail
   - Can reconstruct reward calculation from event log

5. **Metrics Infrastructure**
   - Accurate P&L tracking (already fixed in audit)
   - Win/loss statistics (already implemented)
   - Drawdown, ROI (already implemented)

**Good News**: Most of this is already in place from the audit fixes!

---

## 5. Live Feed Integration Phases

### Design Principles

1. **Perfect Fidelity**: Replay and live must be indistinguishable
   - Same GameState updates
   - Same TradeManager execution
   - Same EventBus events
   - Only difference: tick SOURCE

2. **ReplaySource Abstraction**:
   - File-based source (JSONL playback)
   - Live-based source (WebSocket feed)
   - Future: Gymnasium wrapper uses same abstraction

3. **Dual Recording**:
   - Live games recorded to JSONL automatically
   - Same format as manual recordings
   - Can replay live sessions later for debugging/training

4. **Stateless Components**:
   - GameState is pure data
   - ReplayEngine just orchestrates tick flow
   - UI/Bot react to events, don't own state

### Phase Breakdown

---

#### Phase 3A: Commit Audit Fixes (IMMEDIATE - 10 min)

**Duration**: 10 minutes
**Prerequisites**: None (all fixes complete)
**Status**: NEXT - Ready to execute

**Tasks**:
1. ✅ Run full test suite to verify 148 tests pass
2. ✅ Stage modified files (8 files, 175 lines)
3. ✅ Stage new files (AGENTS.md, docs/Codex/, external/, new tests)
4. ✅ Commit with comprehensive message
5. ✅ Push to GitHub

**Deliverables**:
- Clean git history with all audit fixes
- Baseline for future work
- All findings documented and resolved

**Git Commit Message**:
```
Phase 3: Audit Fixes & Live Feed Prep - Thread Safety + Rug Handling

Critical Fixes (All Complete):
- Add TkDispatcher for thread-safe UI updates (prevents TclError crashes)
- Fix GameState reset hygiene (rug_detected flag, game_id preservation)
- Fix position exit_tick tracking (parameter order corrected)
- Harden EventBus shutdown for full queues
- Fix metrics to use realized P&L (not balance deltas)
- Guard feature extractor against zero IQR division
- Wire rug/sidebet checks to UI dispatcher (every tick)

New Components:
- src/ui/tk_dispatcher.py (47 lines) - Thread-safe UI marshaling
- docs/Codex/ - Comprehensive audit documentation
- AGENTS.md - Repository guidelines and quick reference
- external/continuous_game_recorder.py - WebSocket reference

Testing:
- Added 7 new test files (replay, dispatcher, event_bus, ML)
- Updated existing tests for new APIs
- Total test count: 148 tests (up from 141-142 documented)

Changes:
- 175+ lines modified across 8 files
- All critical/high/medium audit findings resolved
- Ready for live WebSocket integration (Phase 4+)

Documentation:
- docs/Codex/codebase_audit.md - Full audit findings
- docs/Codex/changes_summary.md - Detailed changes
- docs/Codex/handoff.md - Session handoff notes
- docs/Codex/live_feed_integration_plan.md - Roadmap

This commit establishes a clean baseline with all known bugs fixed
and infrastructure ready for dual-mode (replay + live) operation.

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

---

#### Phase 3B: Documentation Cleanup (NEXT - 30 min)

**Duration**: 30 minutes
**Prerequisites**: Phase 3A complete
**Status**: Planned

**Tasks**:
1. Archive outdated CLAUDE.md files to docs/archive/
2. Create new comprehensive CLAUDE.md reflecting current state
3. Update test count (148 tests, not 141-142)
4. Reference Codex documentation
5. Outline live feed integration and RL vision as meta context
6. Archive completed analysis notes
7. Review debug scripts for archival/deletion
8. Update AGENTS.md if needed

**Documentation Structure (Proposed)**:
```
/home/nomad/Desktop/REPLAYER/
├── CLAUDE.md                          # NEW - Comprehensive dev context
│   ├── 1. Project Overview
│   ├── 2. Meta Vision (RL Training Environment)
│   ├── 3. Current State (Audit Fixes Complete)
│   ├── 4. Architecture (Event-driven, modular)
│   ├── 5. Live Feed Integration Plan
│   ├── 6. Testing Philosophy (RL-aware)
│   ├── 7. Development Workflow
│   └── 8. References (Codex docs, game mechanics)
│
├── AGENTS.md                          # Concise quick reference
│   ├── Build/test commands
│   ├── Coding style
│   ├── Commit guidelines
│   └── Configuration notes
│
├── README.md                          # User-facing overview
│
├── docs/
│   ├── Codex/                         # Audit & planning
│   │   ├── codebase_audit.md
│   │   ├── changes_summary.md
│   │   ├── handoff.md
│   │   └── live_feed_integration_plan.md
│   │
│   ├── game_mechanics/                # Game rules
│   │   ├── GAME_MECHANICS.md
│   │   ├── side_bet_mechanics_v2.md
│   │   └── ...
│   │
│   └── archive/                       # Historical docs
│       ├── CLAUDE_2025-11-10.md       # OLD root CLAUDE.md
│       ├── CLAUDE_MODULAR_ERA.md      # OLD docs/CLAUDE.md
│       ├── CLEANUP_COMPLETE.md        # Archived
│       ├── VOLATILITY_SPIKE_VALIDATION.md
│       └── SPIKE_TIMING_ANALYSIS.md
```

**Git Commit Message**:
```
Phase 3B: Documentation Cleanup - Consolidate & Update

Archive Outdated Documentation:
- Move CLAUDE.md → docs/archive/CLAUDE_2025-11-10.md
- Move docs/CLAUDE.md → docs/archive/CLAUDE_MODULAR_ERA.md
- Archive completed analysis notes to docs/archive/

Create New CLAUDE.md:
- Reflect current state (all audit fixes complete)
- Correct test count (148 tests, not 141-142)
- Add meta vision (RL training environment)
- Reference Codex documentation
- Outline live feed integration plan
- Include RL testing methodology as design context

Cleanup:
- Archive debug_volatility.py to docs/archive/
- Archive test_multi_game.py to docs/archive/
- Remove duplicate LIVE_INTEGRATION_PLAN.md (use Codex version)

Documentation now accurately reflects production-ready state
with clear roadmap for live feed integration and RL training.

All historical context preserved in docs/archive/

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

---

#### Phase 4: ReplaySource Abstraction (1-2 days)

**Duration**: 1-2 days
**Prerequisites**: Phase 3A, 3B complete
**Status**: Planned

**Goal**: Abstract replay source to support file and live feed interchangeably

**Design Principle**: **Perfect Fidelity**
- File and live sources must produce identical tick streams
- GameState, TradeManager, UI react identically to both sources
- Only difference is WHERE ticks come from

**Components to Create**:

**1. ReplaySource Interface** (`src/core/replay_source.py`):
```python
from abc import ABC, abstractmethod
from typing import List, Optional, Iterator
from models.game_tick import GameTick

class ReplaySource(ABC):
    """Abstract interface for replay tick sources"""

    @abstractmethod
    def is_live(self) -> bool:
        """True if this is a live feed, False for recorded"""
        pass

    @abstractmethod
    def load_game(self, game_id: Optional[str] = None) -> Iterator[GameTick]:
        """
        Load a game and return tick iterator

        Args:
            game_id: Specific game ID (file source) or None (live, next game)

        Returns:
            Iterator yielding GameTick objects
        """
        pass

    @abstractmethod
    def get_available_games(self) -> List[str]:
        """Get list of available game IDs (file source only)"""
        pass

    @abstractmethod
    def start(self):
        """Start the source (connect WebSocket, etc.)"""
        pass

    @abstractmethod
    def stop(self):
        """Stop the source (disconnect, cleanup)"""
        pass
```

**2. FileDirectorySource** (`src/core/file_source.py`):
```python
class FileDirectorySource(ReplaySource):
    """
    Replay source that reads from JSONL files in a directory

    This is the existing behavior - just refactored into the abstraction
    """

    def __init__(self, recordings_dir: Path):
        self.recordings_dir = recordings_dir
        self.current_game = None

    def is_live(self) -> bool:
        return False

    def load_game(self, game_id: Optional[str] = None) -> Iterator[GameTick]:
        """Load game from JSONL file, yield ticks"""
        # Existing logic from ReplayEngine.load_file()
        pass

    def get_available_games(self) -> List[str]:
        """Scan directory for game files"""
        return [f.stem for f in self.recordings_dir.glob('game_*.jsonl')]

    def start(self):
        pass  # No connection needed

    def stop(self):
        pass  # No cleanup needed
```

**3. ReplayEngine Updates** (`src/core/replay_engine.py`):
```python
class ReplayEngine:
    def __init__(self, state, event_bus, config):
        self.state = state
        self.event_bus = event_bus
        self.config = config
        self.source: Optional[ReplaySource] = None

        # Existing playback state...

    def attach_source(self, source: ReplaySource):
        """Attach a replay source (file or live)"""
        if self.source:
            self.source.stop()
        self.source = source
        self.source.start()

    def push_tick(self, tick: GameTick):
        """
        Push a single tick from live source

        This bypasses the ticks list and directly updates state/UI.
        Used by LiveFeedSource to inject real-time ticks.
        """
        def apply_tick():
            self.state.update(
                current_tick=tick.tick,
                current_price=tick.price,
                current_phase=tick.phase,
                rugged=tick.rugged,
                game_active=tick.active,
                game_id=tick.game_id
            )
            self._maybe_handle_rug(tick)
            self.event_bus.publish(Events.GAME_TICK, tick.to_dict())

            if self.on_tick_callback:
                self.on_tick_callback(tick, tick.tick, None)

        # Thread-safe UI update
        if hasattr(self, 'ui_dispatcher'):
            self.ui_dispatcher.submit(apply_tick)
        else:
            apply_tick()

    def load_file(self, file_path: Path):
        """
        Load file using attached source

        Backward compatibility: If no source attached, create FileDirectorySource
        """
        if not self.source or not isinstance(self.source, FileDirectorySource):
            from .file_source import FileDirectorySource
            self.attach_source(FileDirectorySource(file_path.parent))

        # Use source.load_game() to get ticks
        # Existing logic but delegated to source
```

**Tasks**:
1. Create `ReplaySource` abstract base class
2. Implement `FileDirectorySource` (refactor existing logic)
3. Update `ReplayEngine` to use source abstraction
4. Add `push_tick()` method for live feed
5. Maintain backward compatibility (existing code still works)
6. Write tests:
   - Test `FileDirectorySource` loads games correctly
   - Test `push_tick()` updates state correctly
   - Test source switching works

**Deliverables**:
- `src/core/replay_source.py` - Abstract interface
- `src/core/file_source.py` - File-based implementation
- Updated `src/core/replay_engine.py` - Uses abstraction
- Tests for new abstraction
- Documentation update

**Why This Matters for RL**:
- Gymnasium wrapper will use same ReplaySource abstraction
- Can train on recorded games (FileDirectorySource)
- Can deploy to live games (LiveFeedSource) with same code
- Deterministic: Same file → same tick sequence → same rewards

**Git Commit Message**:
```
Phase 4: ReplaySource Abstraction - Foundation for Dual-Mode Operation

Add ReplaySource Interface:
- Abstract base class defining tick source contract
- Methods: is_live(), load_game(), start(), stop()
- Supports both file-based and live sources

Implement FileDirectorySource:
- Refactor existing JSONL playback logic into ReplaySource
- Maintains backward compatibility
- Scans directory for available games

Extend ReplayEngine:
- attach_source() to plug in different sources
- push_tick() for live feed injection (thread-safe)
- Refactor load_file() to use source abstraction
- Maintains existing API (no breaking changes)

Testing:
- Unit tests for FileDirectorySource
- Integration tests for source switching
- Test push_tick() state updates

Architecture:
- Perfect fidelity: File and live sources produce identical behavior
- Only difference is WHERE ticks come from (file vs WebSocket)
- Prepares for LiveFeedSource (Phase 6)
- Foundation for Gymnasium wrapper (future RL training)

This abstraction enables dual-mode operation (replay + live)
while maintaining identical code paths for both sources.

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

---

#### Phase 5: RecorderSink & LiveRingBuffer (2-3 days)

**Duration**: 2-3 days
**Prerequisites**: Phase 4 complete
**Status**: Planned

**Goal**: Implement recording and 10-game context buffering for live mode

**Design Principle**: **Dual Recording**
- Live games recorded to JSONL automatically
- Same format as manual recordings (continuous_game_recorder.py)
- Can replay live sessions later for debugging/training

**Components to Create**:

**1. RecorderSink** (`src/services/recorder.py`):
```python
class RecorderSink:
    """
    Records game ticks to JSONL files

    Adapted from continuous_game_recorder.py but runs inside REPLAYER
    to avoid dual processes.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.current_game_id = None
        self.current_file = None
        self.current_file_path = None
        self.current_ticks = []

    def start(self, game_id: str):
        """Start recording new game"""
        # Close previous file if exists
        if self.current_file:
            self.finish({})

        # Create new file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_file_path = self.output_dir / f"game_{timestamp}.jsonl"
        self.current_file = open(self.current_file_path, 'w')
        self.current_game_id = game_id
        self.current_ticks = []

        # Write game_start event
        event = {
            "type": "game_start",
            "timestamp": datetime.now().isoformat(),
            "game_id": game_id
        }
        self.current_file.write(json.dumps(event) + '\n')
        self.current_file.flush()

    def write_tick(self, tick: GameTick):
        """Write tick to current game file"""
        if self.current_file:
            event = {
                "type": "tick",
                "timestamp": datetime.now().isoformat(),
                **tick.to_dict()
            }
            self.current_file.write(json.dumps(event) + '\n')
            self.current_file.flush()
            self.current_ticks.append(tick)

    def finish(self, metadata: dict):
        """Finish current game file with metadata"""
        if self.current_file and self.current_ticks:
            # Calculate statistics
            prices = [t.price for t in self.current_ticks]
            ticks = [t.tick for t in self.current_ticks]

            game_end = {
                "type": "game_end",
                "timestamp": datetime.now().isoformat(),
                "game_id": self.current_game_id,
                "total_ticks": len(self.current_ticks),
                "tick_range": [min(ticks), max(ticks)],
                "price_range": [min(prices), max(prices)],
                "peak_price": max(prices),
                "final_price": prices[-1],
                **metadata
            }

            self.current_file.write(json.dumps(game_end) + '\n')
            self.current_file.close()

            self.current_file = None
            self.current_file_path = None
            self.current_game_id = None
            self.current_ticks = []
```

**2. LiveRingBuffer** (`src/services/live_ring_buffer.py`):
```python
from collections import deque

class LiveRingBuffer:
    """
    Maintains a rolling window of the last N completed games

    Purpose: Provide bot with context (last 10 games) for analysis
    Survives restarts by pre-populating from recent JSONL files
    """

    def __init__(self, capacity: int = 10, recordings_dir: Optional[Path] = None):
        self.capacity = capacity
        self.completed = deque(maxlen=capacity)
        self.current = None
        self.recordings_dir = recordings_dir

        # Pre-populate from recent files on startup
        if recordings_dir:
            self.pre_populate()

    def start_game(self, game_id: str):
        """Start tracking new game"""
        self.current = {
            'game_id': game_id,
            'ticks': [],
            'metadata': {},
            'start_time': datetime.now()
        }

    def ingest_tick(self, tick: GameTick):
        """Add tick to current game"""
        if not self.current or self.current['game_id'] != tick.game_id:
            self.start_game(tick.game_id)
        self.current['ticks'].append(tick)

    def complete_game(self, metadata: dict):
        """Mark current game as complete, move to buffer"""
        if self.current:
            self.current['metadata'] = metadata
            self.current['end_time'] = datetime.now()
            self.completed.append(self.current)
            self.current = None

    def get_last_games(self, count: int = 10) -> List[dict]:
        """Get last N completed games"""
        return list(self.completed)[-count:]

    def pre_populate(self):
        """Load recent games from JSONL files on startup"""
        if not self.recordings_dir or not self.recordings_dir.exists():
            return

        # Get most recent files (up to capacity)
        files = sorted(
            self.recordings_dir.glob('game_*.jsonl'),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )[:self.capacity]

        for file_path in reversed(files):  # Oldest first
            game_data = self._load_game_file(file_path)
            if game_data:
                self.completed.append(game_data)

    def _load_game_file(self, file_path: Path) -> Optional[dict]:
        """Load game from JSONL file"""
        # Parse file, extract game_id, ticks, metadata
        # Return dict compatible with buffer format
        pass
```

**Tasks**:
1. Port recorder logic from continuous_game_recorder.py
2. Create RecorderSink service
3. Implement LiveRingBuffer with pre-population
4. Wire to EventBus (auto-record on GAME_TICK, GAME_END)
5. Write tests:
   - Test RecorderSink creates proper JSONL files
   - Test LiveRingBuffer maintains window correctly
   - Test pre-population from existing files

**Deliverables**:
- `src/services/recorder.py` - RecorderSink service
- `src/services/live_ring_buffer.py` - LiveRingBuffer service
- Integration with EventBus
- Tests for both components
- Documentation update

**Why This Matters for RL**:
- Bot can access last 10 games for context-aware decisions
- All live games recorded for later analysis/training
- Can replay "interesting" live games to debug bot behavior
- Context survives restarts (pre-population)

**Git Commit Message**:
```
Phase 5: RecorderSink & LiveRingBuffer - Game Context & Persistence

Add RecorderSink Service:
- Adapted from continuous_game_recorder.py
- Records live games to JSONL (same format as manual recordings)
- start(), write_tick(), finish() lifecycle
- Automatic statistics calculation (peak price, total ticks, etc.)

Implement LiveRingBuffer:
- Maintains rolling window of last 10 completed games
- Pre-populates from recent JSONL files on startup
- Provides bot with game context for analysis
- Survives application restarts

Integration:
- Wire to EventBus (GAME_TICK, GAME_END events)
- Automatic recording of live games
- Context updated in real-time

Testing:
- RecorderSink creates valid JSONL files
- LiveRingBuffer maintains correct window size
- Pre-population loads recent games correctly

Use Cases:
- Bot accesses last 10 games for context-aware decisions
- All live sessions recorded for later replay/training
- Debug "interesting" live games by replaying them
- RL training can use live game history

This completes the persistence layer for dual-mode operation.
Live games now automatically recorded and buffered.

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

---

#### Phase 6: LiveFeedSource Implementation (3-4 days)

**Duration**: 3-4 days
**Prerequisites**: Phase 5 complete
**Status**: Planned

**Goal**: Implement WebSocket live feed source using continuous_game_recorder.py pattern

**Design Principle**: **Same Events, Different Source**
- WebSocketFeed events → GameTick objects → same pipeline
- Perfect fidelity: Live ticks indistinguishable from recorded ticks
- Dual recording: Live games saved to JSONL, buffered for context

**Components to Create**:

**1. WebSocketFeed Service** (`src/services/websocket_feed.py`):
```python
# Port from CV-BOILER-PLATE-FORK/core/rugs/websocket_feed.py

class WebSocketFeed:
    """
    WebSocket client for Rugs.fun live game feed

    Ported from CV-BOILER-PLATE-FORK with minimal changes.
    Handles connection, keep-alive, event dispatching.
    """

    def __init__(self, log_level='INFO'):
        self.log_level = log_level
        self.is_connected = False
        self.event_handlers = {}
        # ... WebSocket setup

    def on(self, event: str):
        """Decorator to register event handler"""
        def decorator(func):
            self.event_handlers[event] = func
            return func
        return decorator

    def connect(self):
        """Connect to Rugs.fun WebSocket"""
        # ... connection logic

    def disconnect(self):
        """Disconnect and cleanup"""
        # ... cleanup logic

    def get_metrics(self):
        """Get connection metrics (for keep-alive)"""
        # ... metrics logic
```

**2. LiveFeedSource** (`src/core/live_feed_source.py`):
```python
class LiveFeedSource(ReplaySource):
    """
    Replay source that ingests live WebSocket feed

    Wraps WebSocketFeed and implements ReplaySource interface.
    Forwards ticks to ReplayEngine.push_tick() in real-time.
    """

    def __init__(self, event_bus, recorder: RecorderSink,
                 ring_buffer: LiveRingBuffer, config):
        self.event_bus = event_bus
        self.recorder = recorder
        self.ring_buffer = ring_buffer
        self.config = config

        self.websocket = WebSocketFeed(log_level='WARN')
        self.current_game_id = None
        self.replay_engine = None  # Set by attach_source()

        # Keep-alive thread
        self.keep_alive_thread = None
        self.keep_alive_interval = 240  # 4 minutes

    def set_replay_engine(self, engine):
        """Called by ReplayEngine.attach_source()"""
        self.replay_engine = engine

    def is_live(self) -> bool:
        return True

    def load_game(self, game_id=None) -> Iterator[GameTick]:
        """Not used for live source (ticks pushed via events)"""
        raise NotImplementedError("Live source uses event-driven push")

    def get_available_games(self) -> List[str]:
        """Not applicable for live source"""
        return []

    def start(self):
        """Connect to WebSocket and start receiving ticks"""
        @self.websocket.on('connected')
        def on_connected(info):
            self.event_bus.publish(Events.UI_UPDATE, {
                'message': 'Live feed connected - Recording started!'
            })
            self._start_keep_alive()

        @self.websocket.on('signal')
        def on_signal(signal):
            # Convert WebSocket signal to GameTick
            tick = GameTick(
                game_id=signal.gameId,
                tick=signal.tickCount,
                timestamp=datetime.utcnow().isoformat(),
                price=Decimal(str(signal.price)),
                phase=signal.phase,
                active=signal.active,
                rugged=signal.rugged,
                cooldown_timer=signal.cooldownTimer,
                trade_count=signal.tradeCount
            )

            # Detect new game
            if signal.gameId != self.current_game_id:
                if self.current_game_id is not None:
                    # Previous game ended implicitly, finish it
                    self.recorder.finish({})
                    self.ring_buffer.complete_game({})

                # Start new game
                self.current_game_id = signal.gameId
                self.recorder.start(signal.gameId)
                self.ring_buffer.start_game(signal.gameId)

                # Emit GAME_START
                self.event_bus.publish(Events.GAME_START, {
                    'game_id': signal.gameId
                })

            # Record tick
            self.recorder.write_tick(tick)
            self.ring_buffer.ingest_tick(tick)

            # Push to ReplayEngine (thread-safe)
            if self.replay_engine:
                self.replay_engine.push_tick(tick)

        @self.websocket.on('gameComplete')
        def on_game_complete(payload):
            # Finalize recording
            metadata = {
                'game_number': payload.get('gameNumber'),
                # ... other metadata
            }
            self.recorder.finish(metadata)
            self.ring_buffer.complete_game(metadata)

            # Emit GAME_END
            self.event_bus.publish(Events.GAME_END, metadata)

            self.current_game_id = None

        # Connect
        self.websocket.connect()

    def stop(self):
        """Disconnect WebSocket"""
        if self.websocket:
            self.websocket.disconnect()

        # Stop keep-alive thread
        # ... cleanup

    def _start_keep_alive(self):
        """Start background keep-alive thread (4-minute ping)"""
        # Similar to continuous_game_recorder.py
        pass
```

**Tasks**:
1. Port WebSocketFeed from CV-BOILER-PLATE-FORK
2. Create LiveFeedSource implementing ReplaySource
3. Wire signal/gameComplete events
4. Integrate with RecorderSink and LiveRingBuffer
5. Implement keep-alive mechanism (4-minute ping)
6. Handle reconnection and errors gracefully
7. Write tests:
   - Mock WebSocket events, verify tick flow
   - Test game transition (old game ends, new game starts)
   - Test recording and buffering
   - Test keep-alive mechanism

**Deliverables**:
- `src/services/websocket_feed.py` - WebSocket client
- `src/core/live_feed_source.py` - Live source implementation
- Integration with recorder and buffer
- Error handling and reconnection logic
- Integration tests (mocked WebSocket)
- Documentation update

**Why This Matters for RL**:
- Bot can play in LIVE environment (not just replay)
- Validates bot behavior in real-time (immediate feedback)
- Live games recorded for later analysis (replay "interesting" games)
- Same code paths as replay (perfect fidelity guarantee)

**Git Commit Message**:
```
Phase 6: LiveFeedSource - Real-Time WebSocket Integration

Add WebSocketFeed Service:
- Ported from CV-BOILER-PLATE-FORK with minimal changes
- Handles connection, keep-alive (4-minute ping), event dispatching
- Robust error handling and reconnection logic

Implement LiveFeedSource:
- ReplaySource implementation for live WebSocket feed
- Converts WebSocket signals to GameTick objects
- Perfect fidelity: Live ticks indistinguishable from recorded
- Dual recording: Saves to JSONL + buffers for context

Integration:
- Wire signal/gameComplete events to RecorderSink and LiveRingBuffer
- Automatic game transition detection (new game_id)
- Emit GAME_START/GAME_END events (same as file source)
- Push ticks to ReplayEngine (thread-safe via push_tick)

Keep-Alive Mechanism:
- Background thread pings every 4 minutes
- Prevents WebSocket timeout during long sessions
- Logs connection status for monitoring

Testing:
- Mock WebSocket events to test tick flow
- Test game transitions (end old, start new)
- Verify recording and buffering
- Test reconnection on connection loss

Architecture:
- Same GameState, TradeManager, UI react to live ticks
- Only difference: Tick SOURCE (WebSocket vs file)
- Enables bot deployment in live environment
- All live games recorded for later replay/training

REPLAYER now supports dual-mode operation:
- Replay Mode: Load JSONL files
- Live Mode: Connect to WebSocket feed

Both modes use identical code paths (perfect fidelity).

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

---

#### Phase 7: UI Mode Toggle & Polish (1-2 days)

**Duration**: 1-2 days
**Prerequisites**: Phase 6 complete
**Status**: Planned

**Goal**: Add UI controls for live vs recorded mode switching

**Design Principle**: **Seamless Mode Switching**
- User can toggle between recorded and live mode
- Incompatible controls disabled in each mode
- Connection status visible
- Pause works differently (buffer vs stop playback)

**UI Changes**:

**1. Mode Toggle** (`src/ui/panels.py` - ControlsPanel):
```python
class ControlsPanel:
    def __init__(self, ...):
        # ... existing controls

        # Add mode toggle
        self.mode_var = tk.StringVar(value='recorded')
        mode_frame = tk.Frame(self.frame)
        tk.Radiobutton(
            mode_frame, text='Recorded',
            variable=self.mode_var, value='recorded',
            command=self._on_mode_change
        ).pack(side='left')
        tk.Radiobutton(
            mode_frame, text='Live',
            variable=self.mode_var, value='live',
            command=self._on_mode_change
        ).pack(side='left')
        mode_frame.pack()

        # Connection status (live mode only)
        self.status_label = tk.Label(self.frame, text='')
        self.status_label.pack()

    def _on_mode_change(self):
        mode = self.mode_var.get()
        if mode == 'live':
            self._switch_to_live()
        else:
            self._switch_to_recorded()

    def _switch_to_live(self):
        # Disable file selection, step controls
        self.file_button.config(state='disabled')
        self.step_button.config(state='disabled')
        self.slider.config(state='disabled')

        # Enable connection
        self.status_label.config(text='Connecting...')
        # ... attach LiveFeedSource

    def _switch_to_recorded(self):
        # Enable file selection, step controls
        self.file_button.config(state='normal')
        self.step_button.config(state='normal')
        self.slider.config(state='normal')

        # Disconnect live feed
        self.status_label.config(text='')
        # ... detach LiveFeedSource, attach FileDirectorySource
```

**2. Connection Status Indicator**:
- Connected: ✅ "Live - Connected (45 games recorded)"
- Connecting: ⏳ "Connecting to live feed..."
- Disconnected: ❌ "Disconnected - Reconnecting..."

**3. Control Updates for Live Mode**:
- **Play/Pause**: Works differently
  - Recorded: Start/stop playback
  - Live: Can't pause live feed (just buffer ticks)
- **Step**: Disabled in live mode (can't step through live feed)
- **Speed**: Disabled in live mode (real-time only)
- **Slider**: Disabled in live mode (can't seek)
- **File Selection**: Disabled in live mode

**4. Pause Buffering** (Live Mode):
- When paused, live ticks continue to arrive
- Buffer them in memory (up to N ticks)
- When resumed, fast-forward through buffered ticks
- Prevents dropping ticks during pause

**Tasks**:
1. Add mode toggle UI (Recorded / Live radio buttons)
2. Add connection status indicator
3. Disable incompatible controls in each mode
4. Update playback controls for live semantics
5. Implement pause buffering for live mode
6. Update user documentation (README.md)
7. Write tests:
   - Test mode switching
   - Test control state updates
   - Test pause buffering

**Deliverables**:
- Mode toggle UI
- Connection status indicator
- Control state management
- Pause buffering (live mode)
- User documentation
- Final testing and polish

**Git Commit Message**:
```
Phase 7: UI Mode Toggle - Seamless Dual-Mode Operation

Add Mode Toggle:
- Radio buttons: Recorded / Live
- Automatic source switching on mode change
- Connection status indicator (Connected, Connecting, Disconnected)

Control State Management:
- Recorded Mode: All controls enabled (file, step, speed, slider)
- Live Mode: Real-time only (disable step, speed, slider)
- Play/Pause works in both modes (different semantics)

Live Mode Enhancements:
- Pause buffering: Ticks buffered during pause, fast-forward on resume
- Connection status updates in real-time
- Automatic reconnection on disconnect

UI Polish:
- Clear visual indication of current mode
- Status messages for connection events
- Tooltips explaining mode differences

Documentation:
- Updated README.md with dual-mode usage
- User guide for live mode
- Troubleshooting section (connection issues)

Testing:
- Test mode switching (recorded ↔ live)
- Test control state updates
- Test pause buffering in live mode
- Test reconnection handling

REPLAYER now complete with dual-mode operation:
- Replay Mode: Full playback controls for recorded games
- Live Mode: Real-time display of WebSocket feed

Users can seamlessly switch between modes without restarting.
All live games recorded to JSONL for later analysis.

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Phase Timeline Summary

| Phase | Duration | Status | Deliverable |
|-------|----------|--------|-------------|
| **3A**: Commit Audit Fixes | 10 min | **IMMEDIATE** | Clean baseline, all fixes committed |
| **3B**: Documentation Cleanup | 30 min | **NEXT** | Consolidated CLAUDE.md, archived old docs |
| **4**: ReplaySource Abstraction | 1-2 days | Planned | Pluggable source architecture |
| **5**: RecorderSink & Buffer | 2-3 days | Planned | Recording + 10-game context |
| **6**: LiveFeedSource | 3-4 days | Planned | WebSocket integration |
| **7**: UI Mode Toggle | 1-2 days | Planned | Dual-mode UI with seamless switching |

**Total Timeline**: ~1-2 weeks for full live integration

---

## 6. Testing Philosophy for RL Infrastructure

### Current Testing (Already in Place)

✅ **Unit Tests**: 148 tests covering models, core, services, bot, ML
✅ **Integration Tests**: Multi-component interaction tests
✅ **Fixtures**: Reusable test components (mock state, event bus)
✅ **Coverage**: Critical paths covered (GameState, EventBus, etc.)

### Additional Testing for RL Readiness (Future)

**NOT implementing now, but infrastructure must support:**

#### 1. Determinism Tests
**Purpose**: Same replay → same results (required for RL training)

```python
def test_replay_determinism():
    """Same game file played twice produces identical state"""
    state1 = replay_game('game_12345.jsonl')
    state2 = replay_game('game_12345.jsonl')
    assert state1.metrics == state2.metrics
    assert state1.closed_positions == state2.closed_positions
```

#### 2. State Observability Tests
**Purpose**: Ensure all reward-relevant state is observable

```python
def test_state_snapshot_completeness():
    """Snapshot contains all reward-relevant information"""
    snapshot = game_state.get_snapshot()
    required_keys = [
        'balance', 'position', 'sidebet', 'current_price',
        'current_tick', 'rugged', 'rug_detected', 'metrics'
    ]
    for key in required_keys:
        assert key in snapshot
```

#### 3. Action Space Tests
**Purpose**: Validate action effects are observable

```python
def test_action_observability():
    """Every action changes observable state"""
    before = game_state.get_snapshot()
    trade_manager.execute_buy(amount=0.001)
    after = game_state.get_snapshot()

    assert before != after  # State changed
    assert after['position'] is not None  # Position created
```

#### 4. Reward Property Tests (Future - when implementing rewards)
**Purpose**: Mathematical properties of reward function

```python
@given(rug_prob=floats(0, 1))
def test_rug_penalty_monotonic(rug_prob):
    """Higher rug probability → higher penalty"""
    penalty1 = calculate_rug_penalty(rug_prob)
    penalty2 = calculate_rug_penalty(rug_prob + 0.1)
    assert penalty2 >= penalty1
```

### Tools to Add Later

**Phase 4-7 (Live Integration)**:
- ✅ pytest (already using)
- ✅ pytest-mock (already using)
- ⏳ pytest-benchmark (for regression testing)

**Future RL Training**:
- ⏳ hypothesis (property-based testing)
- ⏳ gymnasium (RL environment testing)
- ⏳ wandb or tensorboard (training monitoring)

---

## 7. Questions for Consensus

Before we proceed with Phase 3A/3B, we need to decide:

### Q1: Documentation Strategy

Which structure do you prefer?

- **Option A**: Single comprehensive `CLAUDE.md` + concise `AGENTS.md` (Recommended)
- **Option B**: `AGENTS.md` as primary + detailed `docs/DEVELOPMENT.md`
- **Option C**: Other structure?

### Q2: File Cleanup Actions

What should we do with these files?

- `debug_volatility.py` - **Archive or delete?**
- `test_multi_game.py` - **Keep for manual testing or archive?**
- `setup_playwright_mcp.sh` - **Still needed or archive?**
- `VOLATILITY_SPIKE_VALIDATION.md` - **Archive?** (analysis complete)
- `SPIKE_TIMING_ANALYSIS.md` - **Archive?** (analysis complete)
- `CLEANUP_COMPLETE.md` - **Archive?** (cleanup done)
- `docs/LIVE_INTEGRATION_PLAN.md` - **Same as Codex version? Delete duplicate?**

### Q3: Phase Plan Approval

Do you agree with the phase breakdown (3A-7)?

- Any phases to add/remove/reorder?
- Any concerns about timeline estimates?
- Any missing deliverables or requirements?

### Q4: Commit Strategy

Which approach for Phase 3A/3B?

- **Option A**: Commit Phase 3A immediately (audit fixes), then 3B separately (docs)
- **Option B**: Bundle Phase 3A + 3B (fixes + docs) in one commit
- **Option C**: Other strategy?

### Q5: RL Context Clarity

Is the RL testing methodology section clear as **meta context**?

- Confirms we understand the end goal (gymnasium environment)
- Confirms we're NOT implementing ML/training now
- Confirms infrastructure design must support future RL use
- Any clarifications needed?

---

## 8. Next Steps (After Consensus)

### Immediate (Today)

1. ✅ Review this planning document
2. ⏳ Answer Questions 1-5 above
3. ⏳ Agree on file cleanup actions
4. ⏳ Approve phase plan

### After Consensus

1. **Phase 3A**: Run tests, commit audit fixes, push to GitHub (10 min)
2. **Phase 3B**: Clean up documentation, update CLAUDE.md (30 min)
3. **Brief**: Review Phase 4 plan (ReplaySource abstraction)
4. **Begin Phase 4**: Start coding when ready (1-2 days)

---

## 9. Summary

### What's Clear ✅

- Current state is correct (all audit fixes applied, production-ready)
- Reference implementation clear (continuous_game_recorder.py)
- End goal understood (dual-mode + RL gymnasium environment)
- RL testing is meta context (design now, implement later)
- Phase plan detailed (3A-7, ~1-2 weeks)

### What Needs Decision ⏳

- Documentation structure (Q1)
- File cleanup actions (Q2)
- Phase plan approval (Q3)
- Commit strategy (Q4)
- RL context clarity (Q5)

### What Happens Next

**NO CODING until consensus on Questions 1-5**

Once consensus reached:
1. Execute Phase 3A (commit audit fixes)
2. Execute Phase 3B (documentation cleanup)
3. Review Phase 4 plan together
4. Begin live feed integration phases

---

**Date**: 2025-11-14
**Status**: Planning - Awaiting Consensus
**Next Action**: Review and answer Questions 1-5
