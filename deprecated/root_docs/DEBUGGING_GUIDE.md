# REPLAYER Bot Debugging Guide

**Purpose**: Quick reference for debugging bot issues in next session
**Created**: 2025-11-18
**Status**: Ready for use

---

## Quick Start - Manual Testing

### 1. Run REPLAYER with Bot
```bash
cd /home/nomad/Desktop/REPLAYER
./run.sh
```

**In REPLAYER**:
1. Load a game: File → Open Recent (or select from recordings)
2. Configure bot: Bot → Configuration...
   - Strategy: `foundational`
   - Execution mode: `ui_layer`
   - Button timing: 50ms depression, 100ms pause
3. Enable bot: Bot → Enable Bot (or press `B`)
4. Watch and observe behavior

### 2. What to Watch For

**✅ Expected Behavior**:
- Buttons glow **light green** when clicked
- Bot waits for sweet spot (25-50x)
- Enters during safe window (tick < 69)
- Clear reasoning in console (emoji-annotated)
- Balance updates after trades
- Position shows P&L

**❌ Problem Signs**:
- Buttons don't change color
- No button clicks happening
- Bot not entering positions
- Balance not updating
- Errors in console
- UI freezing

---

## Automated Testing Scripts

### Script 1: Debug Bot Session (with screenshots)
```bash
cd /home/nomad/Desktop/REPLAYER/src
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3 debug_bot_session.py --duration 60
```

**What it does**:
- Runs bot for 60 seconds
- Takes screenshots at key moments (entry, exit, errors)
- Logs all bot decisions with reasoning
- Captures timing metrics
- Saves everything to `debug_session_TIMESTAMP/`

**Output**:
```
debug_session_20251118_210000/
├── bot_decisions.log          # All decisions + reasoning
├── metrics.json               # Performance data
└── screenshots/
    ├── 001_initial_state.png
    ├── 002_decision_buy.png
    ├── 003_trade_buy.png
    └── ...
```

### Script 2: Playwright Debug Helper (browser automation)
```bash
cd /home/nomad/Desktop/REPLAYER/src
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3 playwright_debug_helper.py
```

**What it does**:
- Opens browser with visual debugging
- Takes screenshots before/after each action
- Captures console logs from browser
- Validates UI state changes
- Monitors for errors

**Use when**: Testing browser automation (Phase 8.5 integration)

### Script 3: Automated Bot Test (validation)
```bash
cd /home/nomad/Desktop/REPLAYER/src
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3 automated_bot_test.py --games 5
```

**What it does**:
- Runs bot through 5 games
- Automatically checks:
  - ✅ Bot made decisions
  - ✅ Buttons were clicked
  - ✅ No trade failures
  - ✅ No errors
  - ✅ Decisions have reasoning
  - ✅ Timing is reasonable
- Generates pass/fail report

**Output**: `automated_test_TIMESTAMP/test_report.json`

---

## Common Issues & Fixes

### Issue 1: Buttons Don't Glow Green

**Symptoms**: Bot seems to click but no visual feedback

**Possible Causes**:
1. Button depression duration too short
2. Color restoration happening too fast
3. Wrong button reference

**Debug Steps**:
```python
# Check timing config
cat src/bot_config.json | grep button

# Expected:
{
  "button_depress_duration_ms": 50,
  "inter_click_pause_ms": 100
}
```

**Fix**: Increase `button_depress_duration_ms` to 100-200ms for testing

### Issue 2: Bot Not Entering Positions

**Symptoms**: Bot runs but never buys

**Possible Causes**:
1. Price outside sweet spot (not 25-50x)
2. Past safe window (tick >= 69)
3. Insufficient balance

**Debug Steps**:
1. Check console for reasoning: `⏳ Price too low (18.5x, need: 25.0x+)`
2. Watch current tick counter
3. Check balance display

**Fix**: Load a different game or adjust strategy parameters

### Issue 3: UI Freezing

**Symptoms**: UI stops responding when bot enabled

**Possible Causes**:
1. Bot running in main thread (should be async)
2. Lock contention in GameState
3. Event bus queue overflow

**Debug Steps**:
```bash
# Check if AsyncBotExecutor is being used
grep -n "AsyncBotExecutor" src/bot/controller.py

# Check thread safety
grep -n "ui_dispatcher" src/ui/main_window.py
```

**Fix**: Ensure bot uses `AsyncBotExecutor`, not direct execution

### Issue 4: Balance Not Updating

**Symptoms**: Trades execute but balance stays same

**Possible Causes**:
1. GameState not updating balance
2. UI not subscribing to BALANCE_CHANGED event
3. Trade execution not calling state.update()

**Debug Steps**:
```python
# Add debug print in trade execution
# src/core/trade_manager.py
logger.debug(f"Balance before: {self.state.get('balance')}")
# ... execute trade ...
logger.debug(f"Balance after: {self.state.get('balance')}")
```

### Issue 5: Incremental Clicking Not Working

**Symptoms**: Bet amount appears instantly (not incremental)

**Possible Causes**:
1. Using BACKEND mode (direct calls, not UI clicks)
2. BotUIController not being used
3. build_amount_incrementally() not called

**Debug Steps**:
```bash
# Check execution mode
cat src/bot_config.json | grep execution_mode

# Should be:
"execution_mode": "ui_layer"
```

**Fix**: Change to `ui_layer` mode in Bot → Configuration...

---

## Debugging Workflow

### Step 1: Reproduce Issue
1. Run REPLAYER manually
2. Enable bot with known configuration
3. Observe and note exact symptoms
4. Check console output for errors

### Step 2: Capture Debug Info
```bash
# Run debug session script
cd /home/nomad/Desktop/REPLAYER/src
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3 debug_bot_session.py --duration 30

# Check output
ls -la debug_session_*/
cat debug_session_*/bot_decisions.log
```

### Step 3: Analyze Screenshots
- Look for visual feedback (green buttons)
- Check if UI elements are updating
- Verify game state matches expectations

### Step 4: Check Logs
```bash
# Filter for errors
grep "ERROR" debug_session_*/bot_decisions.log

# Filter for bot decisions
grep "BOT DECISION" debug_session_*/bot_decisions.log

# Filter for trades
grep "TRADE" debug_session_*/bot_decisions.log
```

### Step 5: Test Fix
1. Make code change
2. Run automated test to verify fix
3. Run manual session to confirm visually

---

## Key Files to Check

### Bot Logic
- `src/bot/controller.py` - Main bot controller
- `src/bot/ui_controller.py` - UI-layer execution (347 lines)
- `src/bot/strategies/foundational.py` - Trading strategy (285 lines)

### UI Components
- `src/ui/main_window.py` - Main window (lines 649-654: BotUIController init)
- `src/ui/bot_config_panel.py` - Configuration UI (lines 250-301: timing controls)

### Configuration
- `src/bot_config.json` - Bot settings (check `execution_mode`, timing)

### Tests
- `src/tests/test_bot/test_ui_controller_incremental.py` - 22 tests for button clicking

---

## Terminal Output Examples

### ✅ Good Output (Working)
```
🎯 Enter sweet spot at 35.2x (tick 45, safe window: < 69)
🤖 BOT DECISION: BUY
   Reasoning: 🎯 Enter sweet spot at 35.2x (tick 45, safe window: < 69)
✅ TRADE EXECUTED: BUY 0.005 SOL
📸 Screenshot 3: trade_buy
⏳ Holding (Price: 42.3x, P&L: +45.2%, Held: 38 ticks)
✅ Take profit at +120.5% (target: 100%)
🤖 BOT DECISION: SELL
```

### ❌ Bad Output (Problems)
```
⏳ Price too low (18.5x, need: 25.0x+)
⏳ Price too low (19.2x, need: 25.0x+)
⏳ Past safe window (tick 85, limit: 69)
ERROR - Failed to execute trade: Button not found
ERROR - UI thread blocked
```

---

## Playwright Automation (Phase 8.5)

**Note**: This is for browser automation testing, not REPLAYER UI testing.

### Setup
```bash
# Check browser automation is available
ls -la /home/nomad/Desktop/REPLAYER/src/browser_automation/

# Expected files:
# rugs_browser.py
# automation.py
# persistent_profile.py
```

### Test Browser Connection
```python
# Quick test
cd /home/nomad/Desktop/REPLAYER/src
python3 -c "
from browser_automation.rugs_browser import RugsBrowserManager
import asyncio

async def test():
    mgr = RugsBrowserManager(headless=False)
    await mgr.start()
    print('✅ Browser started')
    await asyncio.sleep(5)
    await mgr.cleanup()

asyncio.run(test())
"
```

---

## Next Session Checklist

**Before Starting**:
- [ ] REPLAYER runs without errors: `./run.sh`
- [ ] Bot config file exists: `cat src/bot_config.json`
- [ ] Recordings directory available: `ls ~/rugs_recordings/ | wc -l`
- [ ] Tests passing: `cd src && python3 -m pytest tests/test_bot/ -v`

**During Session**:
- [ ] Run manual test first (observe behavior)
- [ ] Capture screenshots of issues
- [ ] Run debug script for detailed logs
- [ ] Note specific error messages
- [ ] Test fixes with automated script

**After Fixes**:
- [ ] All 275 tests passing
- [ ] Bot enters positions correctly
- [ ] Visual feedback working (green buttons)
- [ ] Balance updates correctly
- [ ] No errors in console

---

## Quick Commands Reference

```bash
# Run REPLAYER
cd /home/nomad/Desktop/REPLAYER && ./run.sh

# Run all tests
cd /home/nomad/Desktop/REPLAYER/src && python3 -m pytest tests/ -v

# Run bot-specific tests
cd /home/nomad/Desktop/REPLAYER/src && python3 -m pytest tests/test_bot/ -v

# Check bot config
cat /home/nomad/Desktop/REPLAYER/src/bot_config.json

# Debug session (30 seconds)
cd /home/nomad/Desktop/REPLAYER/src && \
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3 debug_bot_session.py --duration 30

# Automated test (5 games)
cd /home/nomad/Desktop/REPLAYER/src && \
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3 automated_bot_test.py --games 5

# Check recent debug sessions
ls -lt debug_session_*/

# View latest debug log
cat $(ls -t debug_session_*/bot_decisions.log | head -1)

# View latest test report
cat $(ls -t automated_test_*/test_report.json | head -1) | jq .
```

---

**Status**: Debugging infrastructure ready ✅
**Next Session**: Run bot, observe issues, apply fixes
**Tools Available**: Manual testing, automated scripts, screenshot capture, detailed logging

🔧 Ready for debugging! 🔧
