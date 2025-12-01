# Next Session Plan - Bot Debugging & Validation

**Session Goal**: Test foundational bot in REPLAYER, identify issues, and fix them
**Prepared**: 2025-11-18
**Status**: Ready to begin

---

## Session Overview

**What We'll Do**:
1. **Manual Testing** - You run REPLAYER and describe what you see
2. **Automated Testing** - I run debug scripts to capture detailed logs/screenshots
3. **Issue Diagnosis** - Analyze logs and screenshots to find root causes
4. **Apply Fixes** - Fix identified issues
5. **Validation** - Re-test to confirm fixes work

**Dual Approach**:
- **You watch UI**: Describe visual issues, button behavior, timing
- **I watch terminal**: Analyze logs, errors, decision reasoning, timing metrics

---

## Quick Start Commands

### For You (Manual Testing)
```bash
cd /home/nomad/Desktop/REPLAYER
./run.sh
```

**Then in REPLAYER**:
1. File → Open Recent (select a game)
2. Bot → Configuration...
   - Strategy: `foundational`
   - Execution mode: `ui_layer`
   - Check timing: 50ms depression, 100ms pause
3. Bot → Enable Bot (or press `B`)
4. **Watch and describe what you see**

### For Me (Automated Testing)
```bash
# Debug session with screenshots (30 seconds)
cd /home/nomad/Desktop/REPLAYER/src
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3 debug_bot_session.py --duration 30

# Automated validation test
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3 automated_bot_test.py --games 5

# Check output
ls -la debug_session_*/
cat debug_session_*/bot_decisions.log
```

---

## What to Observe

### ✅ Expected Behavior
1. **Visual Feedback**:
   - Buttons glow **light green** when bot clicks them
   - Button appears SUNKEN (pressed down)
   - Button returns to normal after 50ms

2. **Incremental Clicking**:
   - Bet amount builds incrementally (not instant)
   - See multiple button clicks for larger amounts
   - 100ms pause between clicks (visible but fast)

3. **Smart Algorithm**:
   - Uses X2 button for efficiency (0.001 → 0.002)
   - Uses 1/2 button for efficiency (0.01 → 0.005)
   - Minimal total clicks

4. **Trading Logic**:
   - Bot waits for sweet spot (25-50x)
   - Only enters during safe window (tick < 69)
   - Clear reasoning in console (emoji-annotated)
   - Exits at +100% profit or -30% stop loss

5. **State Updates**:
   - Balance updates after trades
   - Position shows current P&L
   - Tick counter advances
   - Price multiplier updates

### ❌ Problem Signs

**Visual Issues**:
- [ ] Buttons don't change color
- [ ] No SUNKEN relief visible
- [ ] Bet amount appears instantly (not incremental)
- [ ] Button clicks too fast to see

**Logic Issues**:
- [ ] Bot never enters positions
- [ ] Bot enters at wrong prices
- [ ] Bot enters after tick 69
- [ ] No reasoning in console

**State Issues**:
- [ ] Balance doesn't update
- [ ] Position P&L stuck
- [ ] Tick counter frozen
- [ ] Price not updating

**Performance Issues**:
- [ ] UI freezes when bot enabled
- [ ] Delays/lag between actions
- [ ] Console flooded with errors

---

## Debugging Tools Available

### 1. Debug Bot Session Script
**Purpose**: Capture detailed logs + screenshots
**Command**: `python3 debug_bot_session.py --duration 30`
**Output**:
```
debug_session_TIMESTAMP/
├── bot_decisions.log       # All decisions with reasoning
├── metrics.json            # Performance metrics
└── screenshots/
    ├── 001_initial_state.png
    ├── 002_decision_buy.png
    ├── 003_trade_buy.png
    └── ...
```

**When to Use**: After reproducing an issue manually

### 2. Playwright Debug Helper
**Purpose**: Visual validation for browser automation
**Command**: `python3 playwright_debug_helper.py`
**Output**: Screenshots before/after browser actions

**When to Use**: Testing browser integration (Phase 8.5+)

### 3. Automated Bot Test
**Purpose**: Automated validation checks
**Command**: `python3 automated_bot_test.py --games 5`
**Output**: `test_report.json` with pass/fail results

**When to Use**: After applying fixes, to validate they work

---

## Session Workflow

### Phase 1: Manual Observation (5-10 minutes)
**Your Actions**:
1. Run REPLAYER
2. Enable bot (foundational strategy, ui_layer mode)
3. Watch behavior for 1-2 games
4. Describe what you see (good and bad)

**My Actions**:
- Listen to your observations
- Take notes on issues
- Categorize problems (visual, logic, state, performance)

### Phase 2: Automated Capture (5 minutes)
**My Actions**:
1. Run debug_bot_session.py to capture logs
2. Analyze screenshots for visual issues
3. Check bot_decisions.log for reasoning errors
4. Review metrics.json for timing issues

**Your Actions**:
- Continue observing (if desired)
- Provide additional context on issues

### Phase 3: Diagnosis (10-15 minutes)
**Together**:
1. Review screenshots side-by-side
2. Analyze console logs
3. Identify root causes
4. Prioritize fixes (critical → minor)

### Phase 4: Apply Fixes (20-30 minutes)
**My Actions**:
1. Fix critical issues first
2. Run tests after each fix
3. Commit fixes incrementally

**Your Actions**:
- Manual re-testing after fixes
- Confirm visual improvements
- Report any remaining issues

### Phase 5: Validation (10 minutes)
**Together**:
1. Run automated_bot_test.py
2. Verify all checks pass
3. Manual confirmation of fixes
4. Final commit + push

---

## Common Issues & Quick Fixes

### Issue: Buttons Don't Glow Green
**Quick Check**: Timing config too short?
**Quick Fix**: Increase `button_depress_duration_ms` to 100-200ms

### Issue: Bot Never Enters
**Quick Check**: Price outside sweet spot?
**Quick Fix**: Load different game, or adjust entry parameters

### Issue: UI Freezes
**Quick Check**: Bot running in main thread?
**Quick Fix**: Ensure AsyncBotExecutor is used

### Issue: Balance Not Updating
**Quick Check**: Trade execution calling state.update()?
**Quick Fix**: Add balance update to TradeManager

### Issue: Clicking Too Fast
**Quick Check**: inter_click_pause_ms too low?
**Quick Fix**: Increase to 200-500ms for visibility

---

## Success Criteria

**Session Complete When**:
- [ ] ✅ Bot enters positions correctly (sweet spot + safe window)
- [ ] ✅ Buttons glow green visibly
- [ ] ✅ Incremental clicking works (observable)
- [ ] ✅ Balance updates correctly
- [ ] ✅ Reasoning appears in console
- [ ] ✅ No errors during 5-game test
- [ ] ✅ All automated tests pass
- [ ] ✅ UI remains responsive

---

## Files to Reference

**Bot Logic**:
- `src/bot/controller.py` - Main controller
- `src/bot/ui_controller.py` - UI-layer execution (lines 170-224: visual feedback)
- `src/bot/strategies/foundational.py` - Trading strategy

**UI Components**:
- `src/ui/main_window.py` - Main window (lines 649-654: bot init)
- `src/ui/bot_config_panel.py` - Config UI (lines 250-301: timing)

**Configuration**:
- `src/bot_config.json` - Bot settings

**Tests**:
- `src/tests/test_bot/test_ui_controller_incremental.py` - 22 tests

**Debug Guides**:
- `DEBUGGING_GUIDE.md` - Comprehensive debugging reference
- `QUICK_START_GUIDE.md` - User-facing quick start

---

## Notes for Claude

**Context Loading**:
- Session starts with CLAUDE.md context
- Review DEBUGGING_GUIDE.md for reference
- Check QUICK_START_GUIDE.md for user expectations

**Key Focus Areas**:
1. **Visual Feedback** - Green buttons, SUNKEN relief
2. **Incremental Clicking** - Observable sequential clicks
3. **Timing** - 50ms depression, 100ms pauses
4. **Trading Logic** - Sweet spot (25-50x), safe window (tick < 69)
5. **State Sync** - Balance/position updates

**Testing Approach**:
1. Reproduce issue manually first
2. Capture with debug script
3. Analyze logs/screenshots
4. Apply targeted fix
5. Re-test immediately

**Documentation**:
- Update completion docs after fixes
- Commit incrementally with clear messages
- Update QUICK_START_GUIDE if behavior changes

---

## Expected Timeline

**Optimistic** (1-2 hours):
- Few minor issues
- Quick fixes
- All tests pass

**Realistic** (2-3 hours):
- Several issues to fix
- Some testing iterations
- All tests pass eventually

**Conservative** (3-4 hours):
- Complex issues
- Multiple rounds of fixes
- Edge cases to handle

---

**Status**: Ready to begin debugging session ✅
**Tools**: All scripts created and tested
**Documentation**: Complete and comprehensive
**Repository**: All changes committed and pushed

🚀 Ready for next session! 🚀
