# Quick Start Guide - Foundational Bot with Incremental Clicking

**Last Updated**: 2025-11-18
**Features**: Phase A (Incremental Clicking) + Phase B (Foundational Strategy)

---

## 🚀 Quick Start (5 Minutes)

### 1. Run the Demo

See the bot click buttons like a human:

```bash
cd /home/nomad/Desktop/REPLAYER/src
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3 demo_incremental_clicking.py
```

**What you'll see**:
- Buttons glowing **light green** when clicked
- 500ms pauses between clicks (slow for visibility)
- Smart button sequences (uses 1/2 and X2 optimizations)
- Bet amounts building incrementally

**Expected output**:
```
✓ UI initialized
✓ Demo timing configured (500ms pauses for visibility)

Demo 1: Build 0.003 SOL
  Bot clicks: X → +0.001 → X2 [3 clicks vs 4 clicks!]
  ✓ Amount built successfully: 0.003 SOL

Demo 2: Build 0.005 SOL
  Bot clicks: X → +0.01 → 1/2 [3 clicks vs 5 clicks!]
  ✓ Amount built successfully: 0.005 SOL

[... continues for 7 demos ...]

DEMO COMPLETE!
```

---

### 2. Configure Bot Timing

Adjust how the bot clicks buttons:

```bash
cd /home/nomad/Desktop/REPLAYER && ./run.sh
```

**In REPLAYER**:
1. Open: **Bot → Configuration...**
2. Scroll to **"UI Button Timing"** section
3. Adjust settings:
   - **Button depression duration**: `50` ms (visual feedback)
   - **Pause between clicks**: `100` ms (realistic human timing)
4. Click **OK** to save

**Settings persist** to `bot_config.json` and reload on next startup.

---

### 3. Enable Foundational Bot

Run the evidence-based trading strategy:

**In REPLAYER**:
1. Open: **Bot → Configuration...**
2. Select **Strategy**: `foundational` (Evidence-Based)
3. Click **OK**
4. Enable bot: **Bot → Enable Bot** (or press **B**)

**What the bot does**:
- ✅ Enters at **sweet spot** (25-50x) during **safe window** (tick < 69)
- ✅ Exits at **100% profit** or **-30% stop loss**
- ✅ Places **sidebets** during **danger zone** (ticks 104-138)
- ✅ Provides **clear reasoning** for every decision

**Watch console for decisions**:
```
🎯 Enter sweet spot at 35.2x (tick 45, safe window: < 69)
⏳ Holding (Price: 42.3x, P&L: +45.2%, Held: 38 ticks)
✅ Take profit at +120.5% (target: 100%)
```

---

## 📋 Feature Guides

### Incremental Button Clicking

**What it does**: Bot clicks UI buttons like a human (not direct text entry)

**How to watch**:
1. Enable bot
2. Watch bet entry field
3. See buttons glow **light green** when clicked
4. Amounts build incrementally (0.001 → 0.002 → 0.003)

**Visual indicators**:
- **SUNKEN relief**: Button looks pressed down
- **Light green color**: Background changes to #90EE90
- **Duration**: Configurable (default 50ms)

**Timing**:
- **Demo mode**: 500ms pauses (clearly visible)
- **Production mode**: 100ms pauses (realistic human)
- **Fast mode**: 0ms pauses (instant, for training)

**Configuration**: Bot → Configuration... → UI Button Timing

---

### Foundational Strategy

**What it does**: Evidence-based trading using empirical analysis findings

**Strategy parameters**:
- **Entry**: 25-50x (sweet spot with 75% success rate)
- **Safe window**: < 69 ticks (< 30% rug risk)
- **Profit target**: 100% (median return)
- **Stop loss**: -30% (conservative)
- **Max hold**: 60 ticks (optimal)
- **Temporal exit**: Tick 138 (median rug time)

**Decision priorities**:
1. **Exit** existing positions (profit/loss/temporal)
2. **Enter** sweet spot during safe window
3. **Sidebet** during danger zone (ticks 104-138)
4. **Wait** for opportunity

**Reasoning output** (emoji-annotated):
- 🎯 Entry decisions
- ✅ Profit takes
- 🛑 Stop losses
- ⏰ Temporal exits
- ⌛ Hold time limits
- 💰 Sidebet placements
- ⏳ Waiting states

---

## 🎮 Common Use Cases

### Use Case 1: Watch Bot Play (Demo Mode)

**Goal**: See bot behavior visually

**Steps**:
1. Run demo script: `python3 demo_incremental_clicking.py`
2. Watch button clicks (500ms slow mode)
3. Observe smart optimizations (1/2, X2 buttons)

**Time**: 1 minute

---

### Use Case 2: Test Strategy (REPLAYER)

**Goal**: Validate foundational bot performance

**Steps**:
1. Launch REPLAYER: `./run.sh`
2. Configure bot:
   - Strategy: `foundational`
   - Execution mode: `ui_layer`
3. Load game from recordings
4. Enable bot (press **B**)
5. Watch console for decisions
6. Observe button clicks (100ms realistic timing)

**Time**: 5-10 minutes per game

---

### Use Case 3: Customize Timing

**Goal**: Adjust button clicking speed

**Steps**:
1. Open: Bot → Configuration...
2. Timing section:
   - **Visible mode**: 200ms depression, 500ms pause
   - **Realistic mode**: 50ms depression, 100ms pause
   - **Fast mode**: 50ms depression, 0ms pause
3. Click OK
4. Enable bot and observe

**Time**: 30 seconds

---

### Use Case 4: Compare Strategies

**Goal**: Test different strategies

**Steps**:
1. Configure strategy: `conservative`
2. Run 10 games, note performance
3. Configure strategy: `foundational`
4. Run 10 games, note performance
5. Compare win rate, P&L, rug avoidance

**Time**: 1-2 hours

---

## 🔧 Configuration Reference

### Bot Configuration File

**Location**: `bot_config.json`

**Current settings**:
```json
{
  "execution_mode": "ui_layer",
  "strategy": "foundational",
  "bot_enabled": false,
  "button_depress_duration_ms": 50,
  "inter_click_pause_ms": 100
}
```

**Available strategies**:
- `conservative` - Low-risk, modest profits
- `aggressive` - High-risk, high rewards
- `sidebet` - Sidebet-focused (5x payout)
- `foundational` - Evidence-based (sweet spot) ⭐ **NEW**

**Execution modes**:
- `backend` - Direct calls (fast, for training)
- `ui_layer` - Button clicks (realistic, for live prep) ⭐ **RECOMMENDED**

---

### Timing Presets

**Demo Mode** (Highly Visible):
```json
{
  "button_depress_duration_ms": 50,
  "inter_click_pause_ms": 500
}
```

**Production Mode** (Realistic Human):
```json
{
  "button_depress_duration_ms": 50,
  "inter_click_pause_ms": 100
}
```

**Fast Training Mode** (Maximum Speed):
```json
{
  "button_depress_duration_ms": 50,
  "inter_click_pause_ms": 0
}
```

---

## 🐛 Troubleshooting

### Issue: Buttons don't glow green

**Cause**: Button depression duration too short

**Solution**:
1. Open Bot → Configuration...
2. Increase button depression: 100ms
3. Restart REPLAYER

---

### Issue: Bot clicks too fast to see

**Cause**: Inter-click pause too short

**Solution**:
1. Open Bot → Configuration...
2. Increase inter-click pause: 500ms
3. Click OK

---

### Issue: Demo doesn't run

**Cause**: Wrong Python environment

**Solution**:
```bash
# Use rugs-rl-bot venv (has all dependencies)
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3 demo_incremental_clicking.py
```

---

### Issue: Strategy not in dropdown

**Cause**: REPLAYER needs restart

**Solution**:
1. Close REPLAYER
2. Reopen: `./run.sh`
3. Check Bot → Configuration... → Strategy dropdown

---

### Issue: Bot doesn't enter positions

**Possible causes**:
1. **Price outside sweet spot**: Wait for 25-50x
2. **Past safe window**: Tick >= 69
3. **Insufficient balance**: Need 0.005 SOL

**Check reasoning**:
```
⏳ Price too low (18.5x, need: 25.0x+)
⏳ Past safe window (tick 85, limit: 69)
```

---

## 📚 Additional Resources

### Documentation

- **Phase A Completion**: `docs/PHASE_A_COMPLETION.md`
- **Phase B Completion**: `docs/PHASE_B_COMPLETION.md`
- **Timing Guide**: `docs/TIMING_CONFIGURATION_GUIDE.md`
- **Visual Feedback**: `docs/BUTTON_VISUAL_FEEDBACK.md`
- **Demo Guide**: `DEMO_INCREMENTAL_CLICKING.md`
- **Future Roadmap**: `docs/CONFIGURATION_EXPANSION_ROADMAP.md`

### Session Summary

- **Session Summary**: `SESSION_SUMMARY_2025-11-18.md`
- **Development Time**: 4 hours
- **Features Delivered**: Phase A (7 sub-phases) + Phase B (3 sub-phases)

---

## 🎯 Next Steps

### Immediate
1. ✅ Run demo (`demo_incremental_clicking.py`)
2. ✅ Configure timing (Bot → Configuration...)
3. ✅ Test foundational strategy (enable bot in REPLAYER)

### Short-Term
1. ⏭️ Run 100-game backtest
2. ⏭️ Tune strategy parameters
3. ⏭️ Build advanced configuration UI

### Long-Term
1. ⏭️ ML integration (SidebetPredictor)
2. ⏭️ Multi-strategy ensemble
3. ⏭️ RL training using foundational as baseline

---

## ✅ Success Checklist

After reading this guide, you should be able to:

- [ ] Run the incremental clicking demo
- [ ] See buttons glow green when clicked
- [ ] Configure button timing via UI
- [ ] Enable foundational bot strategy
- [ ] Understand bot decision reasoning
- [ ] Troubleshoot common issues

---

**Status**: ✅ Production Ready (pending exhaustive testing)
**Last Updated**: 2025-11-18
**Questions?**: Check documentation or console logs for reasoning output

🚀 **Ready to watch the bot play!** 🚀
