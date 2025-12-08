# Live Game Display Integration Plan

**Date**: 2025-11-10
**Status**: Planning Phase
**Goal**: Integrate live WebSocket game feed into REPLAYER for real-time game visualization

---

## Executive Summary

Transform REPLAYER from a pure replay viewer into a dual-mode system that can:
1. **Replay Mode** (existing): View recorded games from JSONL files
2. **Live Mode** (new): Real-time display of active games from WebSocket feed

This will enable visual validation of RL bot behavior in production and provide a unified interface for both historical analysis and live monitoring.

---

## Architecture Analysis

### Current State: Recorder System

**WebSocketFeed** (`CV-BOILER-PLATE-FORK/core/rugs/websocket_feed.py`):
- 496 lines, Socket.IO client
- Event-driven architecture with callbacks
- Robust connection management (keep-alive every 4 minutes)
- GameStateMachine for phase detection
- Clean signal extraction (9 core fields)

```python
# Key components:
class WebSocketFeed:
    - connect() / disconnect()
    - on(event, handler) - decorator pattern
    - get_last_signal()
    - get_metrics()

# Events emitted:
- 'connected', 'disconnected', 'error'
- 'signal' - every tick
- 'gameComplete' - end of game
- 'tick' - during active gameplay
- 'phase:ACTIVE_GAMEPLAY', etc.
```

**ContinuousRecorder** (`CV-BOILER-PLATE-FORK/scripts/continuous_game_recorder.py`):
- 325 lines
- Uses WebSocketFeed as backend
- Keep-alive thread (pings every 4 minutes)
- Records to separate JSONL files per game
- Graceful shutdown with statistics

**Connection Stability Features**:
- ✅ Automatic keep-alive pinging (240s interval)
- ✅ Activity tracking (last_activity timestamp)
- ✅ Connection status monitoring
- ✅ Graceful reconnection handling
- ✅ Metrics tracking (uptime, latency, games, ticks)

### Current State: REPLAYER

**Architecture** (Event-driven modular design):
- ~13,365 lines across 141 tests
- Tkinter UI with professional layout
- Centralized GameState management
- EventBus pub/sub system
- Bot automation with pluggable strategies

**Key Components**:
```
main.py - Application entry point
├── GameState - Centralized state (observer pattern)
├── EventBus - Pub/sub event system
├── MainWindow - Tkinter UI
│   ├── StatusPanel
│   ├── ChartWidget
│   ├── TradingPanel
│   ├── BotPanel
│   └── ControlsPanel
├── ReplayEngine - Playback control
└── BotController - Strategy execution
```

**Current Data Flow**:
```
JSONL File → ReplayEngine → GameState → EventBus → UI Panels
```

---

## Integration Design

### Target Architecture

**Dual-Mode System**:
```
┌──────────────────────────────────────────────────────┐
│                   REPLAYER UI                        │
├──────────────────────────────────────────────────────┤
│  [Mode: LIVE ▼] [Connect] [Record] [Bot: OFF]       │
├──────────────────────────────────────────────────────┤
│                                                      │
│   ┌─────────────────────────────────┐               │
│   │     Price Chart (Real-time)     │               │
│   │                                 │               │
│   └─────────────────────────────────┘               │
│                                                      │
│   Game: 7a3b2f1c | Tick: 142 | Price: 2.34x        │
│   Phase: ACTIVE_GAMEPLAY | Balance: 0.105 SOL      │
│                                                      │
└──────────────────────────────────────────────────────┘
         ↑                           ↑
         │                           │
    WebSocketFeed              RecordingManager
    (live data)                (optional save)
```

**New Data Flow (Live Mode)**:
```
WebSocket Backend → WebSocketFeed → LiveGameAdapter → GameState → EventBus → UI
                                         ↓
                                  RecordingManager (optional)
                                         ↓
                                    JSONL File
```

### Core Components to Add

**1. LiveGameAdapter** (NEW - `src/core/live_game_adapter.py`):
- Bridge between WebSocketFeed and GameState
- Translates WebSocket signals to GameState updates
- Manages connection lifecycle
- Handles reconnection logic

```python
class LiveGameAdapter:
    """Adapts WebSocketFeed to GameState interface"""

    def __init__(self, state: GameState, event_bus: EventBus):
        self.state = state
        self.event_bus = event_bus
        self.websocket = None
        self.is_live = False

    def connect(self) -> bool:
        """Connect to live feed"""

    def disconnect(self):
        """Disconnect from feed"""

    def _handle_signal(self, signal: GameSignal):
        """Translate signal to state updates"""

    def _handle_game_complete(self, data):
        """Handle game completion"""

    def get_connection_status(self) -> Dict:
        """Get connection metrics"""
```

**2. RecordingManager** (NEW - `src/core/recording_manager.py`):
- Optional recording of live games
- Same format as continuous_game_recorder
- User can toggle recording on/off

```python
class RecordingManager:
    """Records live games to JSONL files"""

    def __init__(self, output_dir: Path):
        self.recording = False
        self.current_file = None

    def start_recording(self, game_id: str):
        """Start recording new game"""

    def write_tick(self, tick_data: dict):
        """Write tick to file"""

    def stop_recording(self):
        """Finish current game file"""
```

**3. ModeManager** (NEW - `src/core/mode_manager.py`):
- Manages switching between LIVE and REPLAY modes
- Ensures clean state transitions
- Handles resource cleanup

```python
class ModeManager:
    """Manages LIVE vs REPLAY mode switching"""

    LIVE = "live"
    REPLAY = "replay"

    def __init__(self, state: GameState, event_bus: EventBus):
        self.current_mode = self.REPLAY
        self.live_adapter = None
        self.replay_engine = None

    def switch_to_live(self):
        """Switch to live mode"""

    def switch_to_replay(self):
        """Switch to replay mode"""

    def get_current_mode(self) -> str:
        """Get active mode"""
```

**4. UI Updates**:

**New LiveControlsPanel** (`src/ui/panels.py`):
- Mode selector dropdown (LIVE/REPLAY)
- Connect/Disconnect button
- Connection status indicator
- Recording toggle
- Latency display

**Modified MainWindow**:
- Add LiveControlsPanel
- Update layout to accommodate mode switching
- Add connection status bar

---

## Implementation Phases

### Phase 1: Core Integration (Week 1)
**Goal**: Basic live mode working without recording

**Tasks**:
1. ✅ Analyze WebSocketFeed architecture
2. ✅ Analyze REPLAYER architecture
3. Create LiveGameAdapter class
4. Add WebSocketFeed as dependency (symlink or copy)
5. Implement basic signal → GameState translation
6. Add connection status tracking
7. Test basic connection stability

**Deliverables**:
- `src/core/live_game_adapter.py` (300-400 lines)
- Connection to backend.rugs.fun working
- GameState updates from live feed
- EventBus events firing correctly

**Testing**:
- Connect to live feed, observe ticks in console
- Verify GameState updates match live data
- Test disconnect/reconnect behavior
- Monitor keep-alive mechanism (4-minute pings)

**Git Commits**:
- Phase 1A: Add LiveGameAdapter skeleton
- Phase 1B: Implement WebSocket connection
- Phase 1C: Add signal translation logic
- Phase 1D: Test connection stability

---

### Phase 2: UI Integration (Week 2)
**Goal**: Live mode visible in UI with mode switching

**Tasks**:
1. Create ModeManager class
2. Add LiveControlsPanel to UI
3. Implement mode switching logic
4. Update chart to handle real-time updates
5. Add connection status indicators
6. Handle UI state during mode switches

**Deliverables**:
- `src/core/mode_manager.py` (200-300 lines)
- `src/ui/panels.py` updated with LiveControlsPanel
- Mode dropdown in UI
- Connect/Disconnect buttons
- Real-time chart updates

**Testing**:
- Switch between LIVE and REPLAY modes
- Verify UI updates correctly
- Test chart performance with real-time data
- Ensure no memory leaks during extended sessions

**Git Commits**:
- Phase 2A: Add ModeManager skeleton
- Phase 2B: Implement mode switching logic
- Phase 2C: Add LiveControlsPanel to UI
- Phase 2D: Test UI integration

---

### Phase 3: Recording Integration (Week 3)
**Goal**: Optional recording of live games

**Tasks**:
1. Create RecordingManager class
2. Add recording toggle to UI
3. Implement JSONL file writing
4. Ensure recorded files match existing format
5. Test replay of recorded live games

**Deliverables**:
- `src/core/recording_manager.py` (200-300 lines)
- Recording toggle in LiveControlsPanel
- JSONL files compatible with replay mode
- Statistics display (games recorded, file size)

**Testing**:
- Record 10+ live games
- Verify JSONL format matches existing recordings
- Test replay of recorded games
- Ensure file naming doesn't conflict

**Git Commits**:
- Phase 3A: Add RecordingManager skeleton
- Phase 3B: Implement file writing
- Phase 3C: Add recording toggle to UI
- Phase 3D: Test recording functionality

---

### Phase 4: Bot Integration (Week 4)
**Goal**: Bot can trade on live games

**Tasks**:
1. Enable bot in LIVE mode
2. Add safety checks (paper trading flag)
3. Implement trade execution validation
4. Add live performance metrics
5. Create bot monitoring dashboard

**Deliverables**:
- Bot works in LIVE mode
- Paper trading toggle (no real trades)
- Live performance tracking
- Visual bot decision indicators

**Testing**:
- Run bot on 20+ live games
- Verify paper trading (no actual execution)
- Monitor bot decision quality
- Validate performance metrics

**Git Commits**:
- Phase 4A: Enable bot in LIVE mode
- Phase 4B: Add paper trading safety
- Phase 4C: Implement live metrics
- Phase 4D: Test bot integration

---

### Phase 5: Polish & Testing (Week 5)
**Goal**: Production-ready live mode

**Tasks**:
1. Add comprehensive error handling
2. Implement reconnection logic
3. Add connection quality metrics
4. Create user documentation
5. Performance optimization
6. Extended stability testing (24+ hours)

**Deliverables**:
- Robust error handling
- Automatic reconnection
- Connection quality dashboard
- User guide for live mode
- 24-hour stability test passed

**Testing**:
- 24-hour continuous connection test
- Simulate network failures
- Test reconnection scenarios
- Monitor memory usage
- Validate all edge cases

**Git Commits**:
- Phase 5A: Add error handling
- Phase 5B: Implement reconnection
- Phase 5C: Add connection metrics
- Phase 5D: Polish and optimize
- Phase 5E: Update documentation

---

## Technical Specifications

### WebSocket Integration

**Dependencies**:
```python
# Add to requirements.txt
python-socketio>=5.0.0
websocket-client>=1.0.0
```

**Connection Parameters**:
```python
SERVER_URL = 'https://backend.rugs.fun?frontend-version=1.0'
KEEP_ALIVE_INTERVAL = 240  # 4 minutes
CONNECTION_TIMEOUT = 20     # seconds
RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 5         # seconds
```

### Data Format Mapping

**WebSocket Signal → GameState**:
```python
signal = {
    'gameId': str,
    'tickCount': int,
    'price': float,
    'phase': str,  # 'ACTIVE_GAMEPLAY', 'PRESALE', etc.
    'active': bool,
    'rugged': bool,
    'cooldownTimer': int,
    'allowPreRoundBuys': bool,
    'tradeCount': int
}

# Maps to:
state.update(
    game_id=signal.gameId,
    current_tick=signal.tickCount,
    current_price=Decimal(str(signal.price)),
    current_phase=signal.phase,
    game_active=signal.active,
    rugged=signal.rugged
)
```

### Event Mapping

**WebSocketFeed Events → REPLAYER Events**:
```python
WebSocket Event          →  REPLAYER Event
─────────────────────────────────────────────
'connected'              →  Events.GAME_START (on first signal)
'signal'                 →  Events.GAME_TICK
'gameComplete'           →  Events.GAME_END
'phase:ACTIVE_GAMEPLAY'  →  (phase-specific logic)
'phase:RUG_EVENT_1'      →  Events.GAME_RUG
'disconnected'           →  (show connection error)
'error'                  →  Events.UI_ERROR
```

---

## Risk Analysis & Mitigation

### Critical Risks

**1. Connection Instability**
- **Risk**: WebSocket drops during critical moments
- **Mitigation**:
  - Keep-alive mechanism (every 4 minutes)
  - Automatic reconnection with exponential backoff
  - Connection quality metrics
  - Graceful degradation (show last known state)

**2. Data Synchronization Issues**
- **Risk**: GameState gets out of sync with live feed
- **Mitigation**:
  - Validate every state transition
  - Detect tick regressions
  - Reset state on game_id change
  - Log all anomalies

**3. Performance Degradation**
- **Risk**: UI becomes unresponsive with real-time updates
- **Mitigation**:
  - Event throttling (max 10 updates/sec)
  - Bounded collections (deque with maxlen)
  - Async processing of non-critical updates
  - Memory profiling during testing

**4. Bot Execution Safety**
- **Risk**: Accidental real trades in production
- **Mitigation**:
  - Paper trading flag (always on by default)
  - Explicit confirmation for real trading
  - Trade execution validation
  - Emergency stop button

### Medium Risks

**5. File Format Incompatibility**
- **Risk**: Recorded live games don't replay correctly
- **Mitigation**:
  - Use exact same format as continuous_game_recorder
  - Validate recorded files before saving
  - Automated tests comparing formats

**6. Mode Switching Bugs**
- **Risk**: State corruption during LIVE ↔ REPLAY switching
- **Mitigation**:
  - Clean state reset on mode change
  - Disable switching during active game
  - Comprehensive state validation

---

## Testing Strategy

### Unit Tests (New: ~50 tests)

**LiveGameAdapter Tests** (20 tests):
- Signal translation accuracy
- Connection state management
- Error handling
- Keep-alive mechanism
- Reconnection logic

**RecordingManager Tests** (15 tests):
- File creation and writing
- Format compatibility
- File rotation
- Error handling
- Statistics accuracy

**ModeManager Tests** (15 tests):
- Mode switching logic
- State cleanup
- Resource management
- Edge case handling

### Integration Tests (New: ~20 tests)

**Live Mode Integration** (10 tests):
- Full connection flow
- Signal → GameState → UI pipeline
- Bot execution in live mode
- Recording during live session
- Mode switching scenarios

**Stability Tests** (10 tests):
- Extended connection (1+ hour)
- Reconnection after disconnect
- Memory leak detection
- Performance benchmarks

### Manual Testing Checklist

**Before Each Commit**:
- [ ] Run all unit tests (191 total: 141 existing + 50 new)
- [ ] Run integration tests (20 new)
- [ ] Test basic connection/disconnection
- [ ] Verify UI updates correctly

**Phase Completion**:
- [ ] Extended stability test (1+ hour)
- [ ] Memory profiling
- [ ] Performance benchmarks
- [ ] Code review
- [ ] Documentation updated

**Production Release**:
- [ ] 24-hour stability test
- [ ] Load testing (multiple games)
- [ ] Security audit
- [ ] User acceptance testing
- [ ] Deployment guide complete

---

## Version Control Strategy

### Branch Structure
```
main
├── dev/live-integration      (active development)
├── feature/live-adapter      (Phase 1)
├── feature/ui-integration    (Phase 2)
├── feature/recording         (Phase 3)
└── feature/bot-integration   (Phase 4)
```

### Commit Frequency
- **Minimum**: After each working feature
- **Target**: Every 100-150 lines of code
- **Maximum**: End of each day

### Commit Message Format
```
Phase X: [Component] - Brief description

- Detailed change 1
- Detailed change 2
- Tests: X passing, Y added

[Optional: Related issue #]
```

**Examples**:
```
Phase 1A: [LiveGameAdapter] Add connection management

- Implement connect() and disconnect() methods
- Add keep-alive thread mechanism
- Handle WebSocketFeed initialization
- Tests: 5 passing, 5 added

Phase 2C: [UI] Add LiveControlsPanel

- Create mode selector dropdown
- Add connect/disconnect buttons
- Implement connection status indicator
- Update MainWindow layout
- Tests: 3 passing, 3 added
```

### Pre-Commit Checklist
- [ ] All tests passing
- [ ] Code linted (flake8)
- [ ] Type hints added
- [ ] Docstrings updated
- [ ] No debug print statements
- [ ] CLAUDE.md updated (if architecture changed)

### Major Milestones
- [ ] Phase 1 Complete → Tag `v0.1.0-live-alpha`
- [ ] Phase 2 Complete → Tag `v0.2.0-live-beta`
- [ ] Phase 3 Complete → Tag `v0.3.0-live-rc1`
- [ ] Phase 5 Complete → Tag `v1.0.0-live-production`

---

## File Structure Changes

### New Files
```
src/
├── core/
│   ├── live_game_adapter.py      (NEW - 300-400 lines)
│   ├── recording_manager.py      (NEW - 200-300 lines)
│   ├── mode_manager.py           (NEW - 200-300 lines)
│   └── websocket_feed.py         (NEW - symlink or copy from CV-BOILER-PLATE-FORK)
│
├── tests/
│   ├── test_core/
│   │   ├── test_live_game_adapter.py    (NEW - ~400 lines, 20 tests)
│   │   ├── test_recording_manager.py    (NEW - ~300 lines, 15 tests)
│   │   └── test_mode_manager.py         (NEW - ~300 lines, 15 tests)
│   └── test_integration/
│       └── test_live_mode.py            (NEW - ~600 lines, 20 tests)
│
└── docs/
    ├── LIVE_INTEGRATION_PLAN.md         (THIS FILE)
    ├── LIVE_MODE_USER_GUIDE.md          (NEW - Phase 5)
    └── CONNECTION_TROUBLESHOOTING.md    (NEW - Phase 5)
```

### Modified Files
```
src/
├── main.py                              (Add mode manager initialization)
├── config.py                            (Add live mode settings)
├── ui/
│   ├── main_window.py                   (Add LiveControlsPanel)
│   └── panels.py                        (Add LiveControlsPanel class)
└── requirements.txt                     (Add socketio dependencies)
```

**Total New Code**: ~3,000 lines
**Total New Tests**: ~1,600 lines (50 unit + 20 integration)
**Modified Code**: ~500 lines

---

## Success Criteria

### Phase 1 Complete
- [x] WebSocket connection established
- [x] Signals received and logged
- [x] GameState updates from live feed
- [x] Connection stable for 1+ hour
- [x] Keep-alive mechanism working

### Phase 2 Complete
- [ ] Mode selector in UI
- [ ] Live mode displays real-time data
- [ ] Chart updates smoothly
- [ ] Mode switching works correctly
- [ ] No memory leaks after 2+ hours

### Phase 3 Complete
- [ ] Recording toggle functional
- [ ] Recorded files match format
- [ ] Recorded games replay correctly
- [ ] 10+ games recorded successfully

### Phase 4 Complete
- [ ] Bot trades on live games (paper)
- [ ] Paper trading safety verified
- [ ] Performance metrics accurate
- [ ] Bot ran 20+ live games successfully

### Phase 5 Complete
- [ ] 24-hour stability test passed
- [ ] All error cases handled
- [ ] Documentation complete
- [ ] User guide written
- [ ] Production deployment ready

---

## Next Steps (Immediate)

1. **Review this plan** with team/stakeholders
2. **Create feature branch**: `git checkout -b dev/live-integration`
3. **Start Phase 1A**: Create LiveGameAdapter skeleton
4. **Add WebSocketFeed dependency** (symlink or copy)
5. **Write first tests** for LiveGameAdapter
6. **First commit**: "Phase 1A: Add LiveGameAdapter skeleton"

---

## Questions to Resolve

1. **Dependency Management**: Should we symlink WebSocketFeed or copy it?
   - **Option A**: Symlink to CV-BOILER-PLATE-FORK (tight coupling)
   - **Option B**: Copy file (independence, but duplication)
   - **Recommendation**: Symlink initially, consider extracting to shared lib later

2. **Recording Location**: Same directory as continuous_game_recorder?
   - **Recommendation**: Yes, use `~/rugs_recordings/` for consistency

3. **Bot Safety**: How to prevent accidental real trading?
   - **Recommendation**: Paper trading always on, require config file change + CLI flag for real trading

4. **Performance**: Max acceptable latency for UI updates?
   - **Target**: <100ms from signal received to UI update
   - **Throttle**: Max 10 UI updates per second

---

## Resources & References

**Code References**:
- WebSocketFeed: `/home/nomad/Desktop/CV-BOILER-PLATE-FORK/core/rugs/websocket_feed.py`
- ContinuousRecorder: `/home/nomad/Desktop/CV-BOILER-PLATE-FORK/scripts/continuous_game_recorder.py`
- REPLAYER Main: `/home/nomad/Desktop/REPLAYER/src/main.py`
- GameState: `/home/nomad/Desktop/REPLAYER/src/core/game_state.py`
- EventBus: `/home/nomad/Desktop/REPLAYER/src/services/event_bus.py`

**Documentation**:
- REPLAYER CLAUDE.md: `/home/nomad/Desktop/REPLAYER/CLAUDE.md`
- CV-BOILER-PLATE CLAUDE.md: `/home/nomad/Desktop/CV-BOILER-PLATE-FORK/CLAUDE.md`
- Game Mechanics: `/home/nomad/Desktop/REPLAYER/docs/game_mechanics/GAME_MECHANICS.md`

**External Docs**:
- Socket.IO Python Client: https://python-socketio.readthedocs.io/
- Tkinter Real-time Updates: https://tkdocs.com/tutorial/concepts.html

---

## Contact & Support

**Primary Developer**: Claude Code
**Project Owner**: nomad
**Repository**: `/home/nomad/Desktop/REPLAYER`
**Related Projects**: `CV-BOILER-PLATE-FORK`, `rugs-rl-bot`

---

**Last Updated**: 2025-11-10
**Next Review**: After Phase 1 completion
