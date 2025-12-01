# REPLAYER Refactoring Plan

**Created**: 2025-11-28
**Branch**: `feat/modern-ui-overhaul`
**Status**: Planning Complete, Implementation Pending

---

## Executive Summary

This plan addresses the remaining refactoring work identified during the src folder audit:

| Phase | Target | Lines | Effort | Priority |
|-------|--------|-------|--------|----------|
| 1 | browser_executor.py | 1,001 → ~400 | 2-3 hrs | HIGH |
| 2 | replay_engine.py | 803 → ~550 | 1-2 hrs | MEDIUM |
| 3 | websocket_feed.py | 643 → ~500 | 1 hr | LOW |
| 4 | Modern UI stubs | 392 lines | 2-3 hrs | OPTIONAL |
| 5 | ML module migration | N/A | 2-3 hrs | HIGH |
| 6 | Test fixes | 2 files | 30 min | MEDIUM |

**Total Estimated Effort**: 9-13 hours

---

## Phase 1: browser_executor.py Refactoring (HIGH PRIORITY)

**Current State**: 1,001 lines, 3 classes, mixed responsibilities
**Goal**: Split into focused modules following Single Responsibility Principle

### 1.1 Extract Timing Classes (30 min)

**Create**: `src/bot/browser_timing.py`

```python
# Move from browser_executor.py:
# - ExecutionTiming dataclass (lines 50-77)
# - TimingMetrics dataclass (lines 79-137)
```

**Files changed**:
- NEW: `src/bot/browser_timing.py` (~90 lines)
- UPDATE: `src/bot/browser_executor.py` (remove timing classes, add import)

### 1.2 Extract Browser Actions (1 hr)

**Create**: `src/bot/browser_actions.py`

```python
# Move from browser_executor.py:
# - click_buy() (lines 473-524)
# - click_sell() (lines 525-574)
# - click_sidebet() (lines 575-630)
# - _set_bet_amount_in_browser() (lines 631-667)
# - _set_sell_percentage_in_browser() (lines 668-723)
# - _click_increment_button_in_browser() (lines 724-799)
# - _build_amount_incrementally_in_browser() (lines 800-871)
```

**Pattern**: Create `BrowserActions` mixin or standalone class that receives `page` object

**Files changed**:
- NEW: `src/bot/browser_actions.py` (~400 lines)
- UPDATE: `src/bot/browser_executor.py` (delegate to BrowserActions)

### 1.3 Extract State Reader (45 min)

**Create**: `src/bot/browser_state_reader.py`

```python
# Move from browser_executor.py:
# - read_balance_from_browser() (lines 872-921)
# - read_position_from_browser() (lines 922-981)
```

**Files changed**:
- NEW: `src/bot/browser_state_reader.py` (~120 lines)
- UPDATE: `src/bot/browser_executor.py` (delegate to StateReader)

### 1.4 Final Structure

```
src/bot/
├── browser_executor.py      # Core lifecycle (~300 lines)
│   ├── __init__, start_browser, stop_browser
│   ├── is_ready, page property
│   └── Delegates to actions/reader
├── browser_timing.py        # Timing metrics (~90 lines)
│   ├── ExecutionTiming
│   └── TimingMetrics
├── browser_actions.py       # Action execution (~400 lines)
│   ├── BrowserActions class
│   ├── click_buy, click_sell, click_sidebet
│   └── Incremental clicking logic
└── browser_state_reader.py  # State reading (~120 lines)
    ├── read_balance_from_browser
    └── read_position_from_browser
```

### 1.5 Testing

```bash
# Run browser executor tests
python3 -m pytest tests/test_bot/ -v -k "browser"

# Run full bot test suite
python3 -m pytest tests/test_bot/ -v
```

---

## Phase 2: replay_engine.py Refactoring (MEDIUM PRIORITY)

**Current State**: 803 lines, 1 class, multiple concerns
**Goal**: Extract recording logic, improve cohesion

### 2.1 Extract Recording Mixin (1 hr)

**Create**: `src/core/replay_recording.py`

```python
# Move from replay_engine.py:
# - enable_recording() (lines 725-746)
# - disable_recording() (lines 747-767)
# - is_recording() (lines 768-771)
# - get_recording_info() (lines 772-783)
# - Recording-related state and callbacks
```

**Pattern**: Create `RecordingMixin` that ReplayEngine inherits from

### 2.2 Final Structure

```
src/core/
├── replay_engine.py         # Core playback (~550 lines)
│   ├── Tick management
│   ├── Playback control
│   └── Inherits RecordingMixin
├── replay_recording.py      # Recording concern (~120 lines)
│   └── RecordingMixin class
├── recorder_sink.py         # Existing - file writing
└── live_ring_buffer.py      # Existing - memory buffer
```

### 2.3 Testing

```bash
python3 -m pytest tests/test_core/test_replay_engine.py -v
python3 -m pytest tests/test_core/test_recorder_sink.py -v
```

---

## Phase 3: websocket_feed.py Refactoring (LOW PRIORITY)

**Current State**: 643 lines, 3 classes
**Goal**: Extract GameStateMachine to separate file

### 3.1 Extract GameStateMachine (30 min)

**Create**: `src/sources/game_state_machine.py`

```python
# Move from websocket_feed.py:
# - GameStateMachine class (lines 65-194)
```

### 3.2 Keep GameSignal in websocket_feed.py

GameSignal is a simple dataclass tightly coupled to WebSocketFeed, keep it.

### 3.3 Final Structure

```
src/sources/
├── websocket_feed.py        # WebSocket + GameSignal (~500 lines)
├── game_state_machine.py    # State detection (~130 lines)
└── __init__.py              # Export both
```

### 3.4 Testing

```bash
python3 -m pytest tests/test_sources/test_websocket_feed.py -v
```

---

## Phase 4: Modern UI Completion (OPTIONAL)

**Current State**: `modern_main_window.py` has stub methods
**Goal**: Complete implementation or document as experimental

### 4.1 Option A: Complete Implementation (2-3 hrs)

Fill in stub methods in `modern_main_window.py`:

```python
# Stubs to implement:
def _create_menu_bar(self): pass      # Port from main_window.py
def _setup_keyboard_shortcuts(self): pass
def _setup_event_handlers(self): pass
def _check_bot_results(self): pass
def _on_game_end(self, metrics): pass
def _on_bridge_status_change(self, status): pass
```

### 4.2 Option B: Document as Experimental

Update `MODERN_UI_HANDOFF.md` to clearly mark as WIP/experimental.

### 4.3 Testing

```bash
# Test Modern UI launches
python3 src/main.py --modern
```

---

## Phase 5: ML Module Migration (HIGH PRIORITY)

**Current State**: Symlinks to rugs-rl-bot/archive/
**Goal**: Independent REPLAYER with own ML modules

### 5.1 Copy ML Files (30 min)

```bash
# Remove symlinks
rm src/ml/predictor.py
rm src/ml/feature_extractor.py
rm src/ml/__init__.py

# Copy actual files
cp /home/nomad/Desktop/rugs-rl-bot/archive/rugs_bot/sidebet/predictor.py src/ml/
cp /home/nomad/Desktop/rugs-rl-bot/archive/rugs_bot/sidebet/feature_extractor.py src/ml/
cp /home/nomad/Desktop/rugs-rl-bot/archive/rugs_bot/sidebet/__init__.py src/ml/
```

### 5.2 Create REPLAYER Virtual Environment (1 hr)

```bash
cd /home/nomad/Desktop/REPLAYER
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 5.3 Update run.sh (15 min)

```bash
#!/bin/bash
# Use REPLAYER's own venv
VENV_PATH="$(dirname "$0")/.venv"
if [ -d "$VENV_PATH" ]; then
    "$VENV_PATH/bin/python3" src/main.py "$@"
else
    echo "Virtual environment not found. Run: python3 -m venv .venv && pip install -r requirements.txt"
    exit 1
fi
```

### 5.4 Testing

```bash
# Activate new venv and run tests
source .venv/bin/activate
cd src && python3 -m pytest tests/ -v
```

---

## Phase 6: Test Fixes (MEDIUM PRIORITY)

**Current Issues**: 2 import errors during test collection

### 6.1 Fix test_websocket_feed.py Import

Error: `ModuleNotFoundError: No module named 'socketio'`

**Fix**: Add `python-socketio[client]` to requirements.txt (may already be there)

### 6.2 Fix test_dispatcher.py Import

Error: Cascading import from websocket_feed.py

**Fix**: Same as above - ensure socketio is installed

### 6.3 Validation

```bash
# Full test suite should pass
cd src && python3 -m pytest tests/ -v --tb=short
```

---

## Implementation Order

### Recommended Sequence

```
Day 1 (4-5 hrs):
├── Phase 1.1: Extract browser_timing.py (30 min)
├── Phase 1.2: Extract browser_actions.py (1 hr)
├── Phase 1.3: Extract browser_state_reader.py (45 min)
├── Phase 1.4: Test and validate (30 min)
└── Phase 5: ML module migration (2 hrs)

Day 2 (3-4 hrs):
├── Phase 2: replay_engine.py refactoring (1.5 hrs)
├── Phase 3: websocket_feed.py refactoring (30 min)
├── Phase 6: Test fixes (30 min)
└── Final validation and documentation (1 hr)

Day 3 (Optional, 2-3 hrs):
└── Phase 4: Modern UI completion (if desired)
```

---

## Success Criteria

### Code Quality
- [ ] No file exceeds 600 lines (except game_state.py - core state)
- [ ] Each class has single responsibility
- [ ] All imports are explicit (no circular dependencies)

### Testing
- [ ] 288+ tests passing (current baseline)
- [ ] No import errors during collection
- [ ] Coverage maintained or improved

### Independence
- [ ] REPLAYER runs with own .venv
- [ ] No symlinks in src/ml/
- [ ] run.sh uses local venv

### Documentation
- [ ] CLAUDE.md updated with new file structure
- [ ] TECHNICAL_DEBT.md updated (ML migration complete)
- [ ] All new files have docstrings

---

## Rollback Plan

If refactoring introduces issues:

1. Each phase should be committed separately
2. Use `git revert` for specific phase commits
3. Keep backup branch before starting: `git checkout -b backup/pre-refactor`

---

## Commands Reference

```bash
# Create backup branch
git checkout -b backup/pre-refactor
git checkout feat/modern-ui-overhaul

# Run tests after each phase
cd /home/nomad/Desktop/REPLAYER/src
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python -m pytest tests/ -v --tb=short

# Check file sizes
find src -name "*.py" -exec wc -l {} \; | sort -rn | head -20

# Commit pattern
git add .
git commit -m "Phase X.Y: [Description]"
```

---

**Plan Created By**: Claude Code
**Date**: 2025-11-28
**Status**: Ready for Implementation
