# Phase 8 Completion Roadmap - UI-First Bot System

**Document Created**: 2025-11-17
**Last Updated**: 2025-11-18 (Session Complete)
**Current Status**: 90% Complete (Phases 8.1-8.6 done, 8.7 pending)
**Estimated Completion**: 2-3 hours (Phase 8.7 only)
**Priority**: MEDIUM - Infrastructure complete, only safety mechanisms remaining

---

## Executive Summary

Phase 8 infrastructure is **90% complete** with all critical bugs fixed and timing metrics implemented:

### ✅ Completed This Session (2025-11-18):
1. ✅ **12 bug fixes applied** (6 original + 5 critical audit + 1 runtime)
2. ✅ **Configuration defaults fixed** (bet amount 0, execution mode ui_layer, persistence)
3. ✅ **Phase 8.6 complete** (Timing metrics + draggable overlay widget)
4. ✅ **275/275 tests passing** (13 new regression tests added)
5. ✅ **Documentation updated** (README, CLAUDE.md, this roadmap)

### ⏳ Remaining Work:
- **Phase 8.7**: Production Readiness (2-3 hours) - Safety mechanisms, validation layer

---

## Current State Analysis

### ✅ Phases 8.1-8.5: IMPLEMENTED

#### **Phase 8.1: Partial Sell Infrastructure** ✅
- **Files**: `src/models/position.py`, `src/core/game_state.py`, `src/core/trade_manager.py`
- **Features**:
  - `Position.reduce_amount(percentage)` method
  - `GameState.partial_close_position()` method
  - `POSITION_REDUCED` event type
- **Tests**: 62 tests in `src/tests/test_core/test_partial_sell.py` (ALL PASSING)

#### **Phase 8.2: UI Partial Sell Buttons** ✅
- **File**: `src/ui/main_window.py` (lines 504-539)
- **Features**:
  - 4 percentage buttons: 10%, 25%, 50%, 100%
  - Radio-button style selector with highlighting
  - `set_sell_percentage()` method
  - Event handlers for UI synchronization

#### **Phase 8.3: BotUIController** ✅
- **File**: `src/bot/ui_controller.py` (347 lines)
- **Features**:
  - `set_bet_amount()`, `click_buy()`, `click_sell(%)`, `click_sidebet()`
  - `read_balance()`, `read_position()`, `read_current_price()`
  - Human delay simulation (10-50ms)
  - Thread-safe UI scheduling via `_schedule_ui_action()`
  - Composite actions: `execute_buy_with_amount()`, `execute_partial_sell()`

#### **Phase 8.4: Bot Configuration UI** ✅
- **File**: `src/ui/bot_config_panel.py` (312 lines)
- **Features**:
  - Modal configuration dialog
  - Settings: execution_mode, strategy, bot_enabled
  - JSON persistence to `bot_config.json`
  - Menu integration: "Bot → Configuration..."

#### **Phase 8.5: Browser Automation** ✅
- **File**: `src/bot/browser_executor.py` (517 lines)
- **Features**:
  - `BrowserExecutor` class with async browser control
  - Browser menu in menu bar
  - `BrowserConnectionDialog` for user-controlled connection
  - Thread-safe async operations
  - Integration with CV-BOILER-PLATE-FORK automation

---

## Critical Gaps Requiring Immediate Fix

### ❌ Gap 1: Bet Amount Defaults to 0.001 (HIGH PRIORITY)

**User Requirement**: "Position size should normally be 0 so the bot has to begin by entering the position size"

**Current Implementation**:
```python
# src/config.py line 31
'default_bet': Decimal('0.001'),

# src/ui/main_window.py line 431
self.bet_entry.insert(0, str(self.config.FINANCIAL['default_bet']))
```

**Impact**: Bot can accidentally execute trades with pre-filled amount instead of forcing explicit entry

**Fix**:
```python
# Option 1: Change config (RECOMMENDED)
# src/config.py line 31
'default_bet': Decimal('0'),

# Option 2: Hardcode zero in UI
# src/ui/main_window.py line 431
self.bet_entry.insert(0, "0")
```

**Verification**: Run app, check bet entry shows "0", try BUY without entering amount (should fail validation)

---

### ❌ Gap 2: Execution Mode Defaults to BACKEND (HIGH PRIORITY)

**User Requirement**: "Bot system uses the button interface just like a human player"

**Current Implementation**:
```python
# src/ui/bot_config_panel.py line 68
'execution_mode': 'backend',  # Default to BACKEND mode
```

**Impact**: Bot bypasses UI layer by default, defeating Phase 8 purpose

**Fix**:
```python
# src/ui/bot_config_panel.py line 68
'execution_mode': 'ui_layer',  # Default to UI_LAYER mode
```

**Documentation Update**: Clarify BACKEND mode is for training only (fast, no UI delays)

**Verification**: Open "Bot → Configuration...", check "UI Layer" is selected by default

---

### ❌ Gap 3: No Initial Bot Config File (MEDIUM PRIORITY)

**Issue**: `bot_config.json` does not exist until user opens config dialog

**Impact**: Bot always uses hardcoded defaults on first run

**Fix**:
```python
# Option 1: Generate on first run (RECOMMENDED)
# src/main.py - Add on startup:
if not os.path.exists('bot_config.json'):
    default_config = {
        'execution_mode': 'ui_layer',
        'strategy': 'conservative',
        'bot_enabled': False
    }
    with open('bot_config.json', 'w') as f:
        json.dump(default_config, f, indent=2)

# Option 2: User generates manually
# Run app → Bot → Configuration... → Click OK
```

**Verification**: Check `bot_config.json` exists with correct defaults

---

## Test Coverage Gaps

### ⚠️ Missing Test Files

**Current**: 237 tests (235 passing, 2 pre-existing failures)
**Target**: 274+ tests (all passing)

#### **Gap 1: UI Partial Sell Button Tests**
**File**: Create `src/tests/test_ui/test_partial_sell_ui.py`
**Tests Needed** (~15 tests):
- `test_percentage_button_click_10()`
- `test_percentage_button_click_25()`
- `test_percentage_button_click_50()`
- `test_percentage_button_click_100()`
- `test_percentage_button_highlight_sync()`
- `test_sell_percentage_changed_event()`
- `test_percentage_selection_persists()`
- `test_percentage_disabled_without_position()`
- `test_percentage_enabled_with_position()`

#### **Gap 2: Bot Config Panel Tests**
**File**: Create `src/tests/test_ui/test_bot_config_panel.py`
**Tests Needed** (~10 tests):
- `test_config_panel_creation()`
- `test_config_load_from_file()`
- `test_config_save_to_file()`
- `test_execution_mode_selection()`
- `test_strategy_selection()`
- `test_bot_enabled_toggle()`
- `test_dialog_ok_saves_config()`
- `test_dialog_cancel_discards_changes()`

#### **Gap 3: BotUIController Integration Tests**
**File**: Create `src/tests/test_bot/test_ui_controller_integration.py`
**Tests Needed** (~12 tests):
- `test_bot_sets_bet_amount_via_ui()`
- `test_bot_clicks_buy_button()`
- `test_bot_clicks_sell_button_with_percentage()`
- `test_bot_clicks_sidebet_button()`
- `test_composite_action_buy_with_amount()`
- `test_composite_action_partial_sell()`
- `test_human_delay_applied()`
- `test_thread_safe_ui_scheduling()`
- `test_ui_action_validation_failure()`

---

## Phase 8.6: State Synchronization & Timing Learning

**Status**: NOT STARTED
**Estimated Time**: 3-4 hours
**Priority**: HIGH (required before live trading)

### Task 1: Browser State Polling

**File**: `src/bot/browser_executor.py`

**Add Methods**:
```python
async def read_balance_from_dom(self) -> Optional[Decimal]:
    """Read actual SOL balance from browser DOM"""
    # Use Playwright to query balance element
    # Parse text to Decimal
    # Return balance or None if not found

async def read_position_from_dom(self) -> Optional[Dict]:
    """Read current position details from browser DOM"""
    # Query position panel elements
    # Extract: amount, entry_price, current_pnl
    # Return dict or None if no position

async def reconcile_state(self):
    """Sync REPLAYER state with browser state (browser = source of truth)"""
    # Read balance from DOM
    # Read position from DOM
    # Update GameState if discrepancies found
    # Log reconciliation events
```

**Integration**: Call `reconcile_state()` periodically (every 5 ticks)

**Tests**: Mock browser DOM, verify state synchronization

---

### Task 2: Timing Metrics Tracking

**File**: Create `src/bot/timing_tracker.py` (~150 lines)

**Class**: `TimingTracker`

**Features**:
```python
class TimingTracker:
    def __init__(self):
        self.metrics = {
            'decision_to_click': [],  # Time from decision to click
            'click_to_confirm': [],   # Time from click to state change
            'total_delay': [],        # Total action delay
        }

    def start_action(self, action_type: str):
        """Mark start of action (decision time)"""

    def mark_click(self, action_type: str):
        """Mark UI button clicked"""

    def mark_confirmation(self, action_type: str):
        """Mark state change confirmed"""

    def get_statistics(self) -> Dict:
        """Return avg, median, std dev for all metrics"""

    def save_to_file(self, filepath: str):
        """Save metrics to JSON"""
```

**Integration**:
- `BotController` calls `start_action()` before decision
- `BotUIController` calls `mark_click()` after clicking
- `GameState` event handlers call `mark_confirmation()`

**Output**: `timing_metrics.json` with statistics

---

### Task 3: Timing Dashboard UI

**File**: `src/ui/main_window.py`

**Add Panel**: Below action buttons (ROW 6)

**Layout**:
```
┌─────────────────────────────────────────────────────┐
│ Timing Metrics (UI Layer Mode)                     │
│ ├─ Avg Decision→Click: 35ms                        │
│ ├─ Avg Click→Confirm: 120ms                        │
│ ├─ Total Avg Delay: 155ms                          │
│ └─ Success Rate: 98.5% (197/200 actions)           │
└─────────────────────────────────────────────────────┘
```

**Updates**: Real-time via `TIMING_METRIC_UPDATED` event

**Hide/Show**: Only visible when execution_mode == UI_LAYER

---

## Phase 8.7: Production Readiness

**Status**: NOT STARTED
**Estimated Time**: 2-3 hours
**Priority**: HIGH (safety mechanisms critical)

### Task 1: Safety Mechanisms

**File**: Create `src/bot/risk_manager.py` (~200 lines)

**Class**: `RiskManager`

**Features**:
```python
class RiskManager:
    def __init__(self, config: Dict):
        self.daily_loss_limit = config.get('daily_loss_limit', Decimal('1.0'))  # 1 SOL max loss/day
        self.max_position_size = config.get('max_position_size', Decimal('0.1'))  # 0.1 SOL max
        self.max_consecutive_losses = config.get('max_consecutive_losses', 5)
        self.emergency_stop_triggered = False

    def check_trade_allowed(self, amount: Decimal) -> Tuple[bool, str]:
        """Check if trade is allowed (returns (allowed, reason))"""
        # Check daily loss limit
        # Check max position size
        # Check consecutive losses
        # Return (False, reason) if blocked

    def record_trade_result(self, pnl: Decimal):
        """Record trade result for risk tracking"""

    def emergency_stop(self):
        """Trigger emergency stop (blocks all trades)"""

    def reset_daily_limits(self):
        """Reset daily counters (call at midnight)"""
```

**UI Integration**:
- Add "Emergency Stop" button (red, always visible)
- Show risk status in status bar
- Toast notification on risk limit hit

**Configuration**: Add to `bot_config.json`:
```json
{
  "risk_management": {
    "daily_loss_limit": 1.0,
    "max_position_size": 0.1,
    "max_consecutive_losses": 5,
    "enabled": true
  }
}
```

---

### Task 2: Comprehensive Logging

**File**: Update `src/services/logger.py`

**Add Structured Logging**:
```python
# JSON format for bot actions
bot_action_logger = logging.getLogger('bot_actions')
bot_action_logger.addHandler(
    logging.FileHandler('logs/bot_actions.log')
)

# Separate error log
error_logger = logging.getLogger('errors')
error_logger.addHandler(
    logging.FileHandler('logs/errors.log')
)

# Log format (JSON)
{
  "timestamp": "2025-11-17T15:30:45.123",
  "action": "BUY",
  "amount": 0.01,
  "price": 1.5,
  "execution_mode": "ui_layer",
  "result": "success",
  "delay_ms": 155
}
```

**Log All Actions**:
- Bot decisions (action chosen, reasoning)
- UI interactions (button clicks, amount entries)
- Trade results (P&L, exit reason)
- Errors (full stack traces)

**Log Rotation**: 7 days retention, 10MB max file size

---

### Task 3: Live Mode Confirmation Dialog

**File**: `src/main.py`

**Add Check on Startup**:
```python
# Check for --live flag
if '--live' in sys.argv:
    # Show confirmation dialog
    response = messagebox.askyesno(
        "⚠️ LIVE MODE WARNING",
        "You are about to run the bot in LIVE MODE.\n\n"
        "Real trades will be executed with real money.\n\n"
        "Are you sure you want to continue?"
    )
    if not response:
        sys.exit(0)
```

**Additional Safeguards**:
- Require `--live` flag for browser executor
- Log warning to console
- Show "LIVE MODE" indicator in UI (red banner)

---

### Task 4: Documentation Updates

**Files to Update**:

1. **`README.md`** - Add Phase 8 section:
   ```markdown
   ## Phase 8: UI-First Bot System

   The bot can now execute trades through the UI layer, simulating
   human interaction before live deployment.

   **Execution Modes**:
   - **Backend Mode**: Fast execution for training (no UI delays)
   - **UI Layer Mode**: Realistic execution via button clicks

   **Features**:
   - Partial sell (10%, 25%, 50%, 100%)
   - Human delay simulation (10-50ms)
   - Timing metrics learning
   - Safety mechanisms (loss limits, emergency stop)
   ```

2. **Create `docs/LIVE_MODE_GUIDE.md`** - Comprehensive guide:
   - Setup checklist
   - Safety configuration
   - Troubleshooting
   - Emergency procedures

3. **Update `CLAUDE.md`** - Phase 8 completion status

---

### Task 5: Validation Run

**Objective**: Run bot for 1+ hour without issues

**Test Configuration**:
- Mode: UI_LAYER (not BACKEND)
- Strategy: Conservative
- Execution: Replay mode (not live browser)
- Games: 20+ games
- Duration: 60+ minutes

**Monitoring**:
- CPU usage: < 25% sustained
- Memory usage: < 500MB, no leaks
- UI responsiveness: No freezes or lag
- Action execution: 100% success rate
- Errors: Zero crashes, zero deadlocks

**Log Review**:
- Check `bot_actions.log` for anomalies
- Check `errors.log` for any errors
- Check `timing_metrics.json` for realistic delays

**Success Criteria**:
✅ Zero crashes
✅ Zero UI freezes
✅ All actions execute correctly
✅ Timing delays realistic (10-50ms + 100-200ms confirm)
✅ Memory stable (no leaks)

---

## Dual Plugin Test System Setup

### System 1: Pre-Commit Hooks

**File**: Create `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        args: ['--line-length=120']

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: ['--max-line-length=120', '--ignore=E501,W503']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: ['--ignore-missing-imports']
```

**Installation**:
```bash
pip install pre-commit
pre-commit install
```

**Usage**: Hooks run automatically on `git commit`

---

### System 2: MCP Code Review Plugins

**Available Plugins**:
1. **`aicode-develop`** - Development-phase reviews
2. **`aicode-review`** - Final reviews before deployment
3. **`aicode-admin`** - Architecture pattern enforcement

**Usage Examples**:

```python
# Review a file during development
mcp__plugin_aicode-develop_aicode-patterns__review-code-change(
    file_path="src/bot/ui_controller.py"
)

# Final review before deployment
mcp__plugin_aicode-review_aicode-review__review-code-change(
    file_path="src/bot/browser_executor.py"
)

# Check design patterns
mcp__plugin_aicode-review_aicode-review__get-file-design-pattern(
    file_path="src/bot/timing_tracker.py"
)
```

**Documentation**: Create `docs/CODE_QUALITY.md` with full guide

---

## Implementation Timeline

### Week 1: Critical Fixes & Testing (6-8 hours)

**Day 1** (2-3 hours):
- [ ] Fix bet amount default to 0
- [ ] Fix execution mode default to ui_layer
- [ ] Generate bot_config.json with correct defaults
- [ ] Verify fixes with manual testing

**Day 2** (2-3 hours):
- [ ] Add UI partial sell button tests (15 tests)
- [ ] Add bot config panel tests (10 tests)
- [ ] Run full test suite, verify 260+ tests passing

**Day 3** (2 hours):
- [ ] Add BotUIController integration tests (12 tests)
- [ ] Setup pre-commit hooks
- [ ] Document MCP plugin usage

---

### Week 2: Phase 8.6-8.7 (8-10 hours)

**Day 4** (3-4 hours):
- [ ] Implement browser state polling
- [ ] Create TimingTracker class
- [ ] Add timing dashboard UI
- [ ] Test timing metrics tracking

**Day 5** (2-3 hours):
- [ ] Create RiskManager class
- [ ] Add emergency stop button
- [ ] Implement comprehensive logging
- [ ] Add live mode confirmation dialog

**Day 6** (2-3 hours):
- [ ] Update README.md
- [ ] Create LIVE_MODE_GUIDE.md
- [ ] Update CLAUDE.md
- [ ] Run 1+ hour validation test

---

## Final Verification Checklist

Before marking Phase 8 complete:

### Configuration ✅
- [ ] Bet amount defaults to "0"
- [ ] Execution mode defaults to "ui_layer"
- [ ] `bot_config.json` exists with correct defaults

### Testing ✅
- [ ] 274+ tests passing (current 237 + 37 new)
- [ ] Pre-commit hooks run successfully
- [ ] All files reviewed with MCP plugins

### Features ✅
- [ ] Partial sell buttons working (10%, 25%, 50%, 100%)
- [ ] Bot interacts via UI layer (not backend)
- [ ] Timing metrics tracked and displayed
- [ ] Browser state synchronization working

### Safety ✅
- [ ] Risk manager active (loss limits enforced)
- [ ] Emergency stop button functional
- [ ] Live mode confirmation required
- [ ] Comprehensive logging enabled

### Documentation ✅
- [ ] README updated with Phase 8 features
- [ ] LIVE_MODE_GUIDE.md created
- [ ] CODE_QUALITY.md created
- [ ] CLAUDE.md updated

### Validation ✅
- [ ] 1+ hour bot run completed (zero crashes)
- [ ] UI remains responsive throughout
- [ ] All actions execute correctly
- [ ] Timing delays realistic
- [ ] Memory usage stable

---

## Success Metrics

**Before Phase 8 Completion**:
- Status: 85% complete
- Critical Issues: 3 config defaults wrong
- Test Coverage: 237 tests
- Safety: No risk management
- Documentation: Incomplete

**After Phase 8 Completion**:
- Status: 100% complete ✅
- Critical Issues: All fixed ✅
- Test Coverage: 274+ tests ✅
- Safety: Full risk management ✅
- Documentation: Comprehensive ✅

**Deployment Ready**: Bot can simulate human interaction, learn timing, enforce safety limits, and is fully tested for production use.

---

## Risk Assessment

### Risks Mitigated ✅
1. ✅ **Accidental Trades** - Bet amount must be entered explicitly
2. ✅ **Unrealistic Timing** - Bot learns delays from UI interaction
3. ✅ **Catastrophic Losses** - Risk manager enforces limits
4. ✅ **System Instability** - Comprehensive testing + validation run

### Remaining Risks ⚠️
1. ⚠️ **Browser Automation Failures** - Playwright may fail (add retry logic)
2. ⚠️ **Network Latency Spikes** - Real game may have variable delays
3. ⚠️ **UI Changes** - Game UI updates may break selectors

**Mitigation**: Continuous monitoring, extensive logging, manual oversight during initial live runs

---

## Conclusion

**Phase 8 Status**: 85% → 100% complete (estimated 11-17 hours work)

**Next Session Priorities**:
1. Apply 3 critical configuration fixes (1-2 hours)
2. Add missing test coverage (2-3 hours)
3. Implement Phase 8.6: Timing & state sync (3-4 hours)
4. Implement Phase 8.7: Production readiness (2-3 hours)
5. Final validation run (1+ hour)

**Outcome**: Production-ready bot that simulates human UI interaction with realistic timing, comprehensive safety mechanisms, and full test coverage.

---

**Document End** - Ready for next session
