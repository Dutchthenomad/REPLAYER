# Bot Timing Configuration Guide

**Phase A.7** - Configure button clicking timing via UI

---

## Overview

The bot now supports **configurable timing** for button clicking behavior. This allows you to adjust how the bot interacts with UI buttons without changing code.

---

## Accessing Configuration

1. Launch REPLAYER: `cd /home/nomad/Desktop/REPLAYER && ./run.sh`
2. Open menu: **Bot → Configuration...**
3. Scroll to **"UI Button Timing (UI Layer Mode)"** section

---

## Configuration Options

### 1. Button Depression Duration (ms)

**What it controls**: How long buttons appear "pressed down" (SUNKEN relief)

**Range**: 10 - 500 milliseconds

**Default**: 50ms

**Visual Effect**:
- 10ms: Very quick flash (barely visible)
- 50ms: Clearly visible depression (recommended)
- 100ms: Noticeable press-and-release
- 500ms: Exaggerated slow press (demo mode)

**When to adjust**:
- **Faster (10-30ms)**: When you want minimal visual feedback
- **Standard (50ms)**: Default, good balance of visibility and speed
- **Slower (100-500ms)**: When demonstrating bot behavior to others

---

### 2. Pause Between Button Clicks (ms)

**What it controls**: Delay between EVERY button press

**Range**: 0 - 5000 milliseconds

**Default**: 100ms

**Timing Examples**:
- **0ms**: Instant clicking (no pause, fastest)
- **60-100ms**: Realistic human timing (recommended for production)
- **200-300ms**: Slightly slower, easier to follow visually
- **500ms**: Slow demo mode (clearly visible, like demo script)
- **1000ms+**: Very slow, for presentation/debugging

**When to adjust**:
- **Fast (0-60ms)**: Training mode, maximize speed
- **Realistic (60-100ms)**: Production play, mimics human
- **Demo (500ms)**: Visibility mode, watch each click
- **Debug (1000ms+)**: Step-by-step observation

---

## Configuration Examples

### Example 1: Production (Realistic Human Play)
```
Button depression: 50ms
Inter-click pause: 100ms
```
**Effect**: Bot clicks buttons at human speed, realistic timing for RL training

---

### Example 2: Fast Training Mode
```
Button depression: 50ms
Inter-click pause: 0ms
```
**Effect**: Bot clicks buttons instantly, maximum training speed (no delays)

---

### Example 3: Slow Demo Mode
```
Button depression: 50ms
Inter-click pause: 500ms
```
**Effect**: Bot clicks buttons slowly, each click clearly visible (like demo script)

---

### Example 4: Presentation Mode
```
Button depression: 100ms
Inter-click pause: 1000ms
```
**Effect**: Bot clicks buttons very slowly, perfect for showing others

---

## How to Save Configuration

1. Adjust spinbox values to desired timing
2. Click **OK** button
3. Configuration saves to `bot_config.json`
4. Restart REPLAYER to load new timing

**Configuration File** (`bot_config.json`):
```json
{
  "execution_mode": "ui_layer",
  "strategy": "conservative",
  "bot_enabled": false,
  "button_depress_duration_ms": 50,
  "inter_click_pause_ms": 100
}
```

---

## Visual Feedback

### Button Depression Cycle

1. **Normal State** (RAISED relief, original color)
   - Button appears normal, ready to click

2. **Pressed State** (SUNKEN relief, light green background)
   - Button appears pressed down with visual indicators:
     - Relief changes to SUNKEN (button looks indented)
     - Background changes to **light green (#90EE90)** for high visibility
   - Lasts for `button_depress_duration_ms` milliseconds

3. **Release State** (RAISED relief, original color restored)
   - Button returns to normal appearance
   - Relief restored to original state
   - Background color restored to original
   - Pause for `inter_click_pause_ms` milliseconds

4. **Next Click**
   - Cycle repeats for next button

---

## Testing Your Configuration

### Quick Test (Demo Script):

1. Set desired timing in Bot Configuration
2. Run demo script:
   ```bash
   cd /home/nomad/Desktop/REPLAYER/src
   /home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3 demo_incremental_clicking.py
   ```
3. Watch button clicks to verify timing
4. Adjust if needed

**Note**: Demo script overrides `inter_click_pause_ms` to 500ms for visibility. Edit line 80 to use your configured value instead.

---

## Timing Recommendations by Use Case

### RL Training (Fast)
- **Button depression**: 50ms
- **Inter-click pause**: 0-20ms
- **Rationale**: Maximize training speed while maintaining button state updates

---

### Production Play (Realistic)
- **Button depression**: 50ms
- **Inter-click pause**: 60-100ms
- **Rationale**: Human-like timing, realistic for live gameplay

---

### Demo / Presentation (Visible)
- **Button depression**: 50ms
- **Inter-click pause**: 500-1000ms
- **Rationale**: Clearly see each button click, easy to follow

---

### Debugging (Step-by-Step)
- **Button depression**: 100ms
- **Inter-click pause**: 2000ms (2 seconds)
- **Rationale**: Observe each action individually, diagnose issues

---

## Advanced: Programmatic Override

You can also set timing values programmatically:

```python
# In demo_incremental_clicking.py or custom script:
bot_ui = main_window.bot_ui_controller

# Override timing
bot_ui.button_depress_duration_ms = 50   # 50ms visual feedback
bot_ui.inter_click_pause_ms = 500        # 500ms pause between clicks

# Use the bot with new timing
bot_ui.build_amount_incrementally(Decimal('0.003'))
```

This is useful for:
- Custom demo scenarios
- Automated testing with specific timing
- A/B testing different timing profiles

---

## Troubleshooting

### Issue: Button clicks too fast to see
**Solution**: Increase `inter_click_pause_ms` to 500ms or higher

---

### Issue: Bot feels sluggish in training
**Solution**: Decrease `inter_click_pause_ms` to 0-20ms

---

### Issue: Button depression not visible
**Solution**: Increase `button_depress_duration_ms` to 100-200ms

---

### Issue: Configuration not saving
**Check**:
1. `bot_config.json` file is writable
2. Clicked "OK" button (not "Cancel")
3. Check console logs for save errors

---

### Issue: Configuration not loading
**Check**:
1. Restart REPLAYER after saving
2. Check `bot_config.json` has correct JSON format
3. Check console logs for load errors

---

## Technical Details

### Button Click Sequence

```python
# For each button in sequence:
for button_type in ['X', '+0.01', '+0.001']:
    # 1. Press button (SUNKEN relief)
    btn.config(relief=tk.SUNKEN)
    btn.update_idletasks()

    # 2. Hold pressed state (button_depress_duration_ms)
    root.after(button_depress_duration_ms, release_button)

    # 3. Execute button command
    btn.invoke()

    # 4. Pause before next click (inter_click_pause_ms)
    time.sleep(inter_click_pause_ms / 1000.0)
```

### Timing Math

**Example**: Build 0.015 SOL (7 button clicks: X + 0.01 + 0.001×5)

**Production (100ms pauses)**:
- Total time: 7 clicks × (50ms depression + 100ms pause) = **1.05 seconds**

**Demo (500ms pauses)**:
- Total time: 7 clicks × (50ms depression + 500ms pause) = **3.85 seconds**

**Fast Training (0ms pauses)**:
- Total time: 7 clicks × (50ms depression + 0ms pause) = **0.35 seconds**

---

## Integration with Phase 8

When the bot moves to live browser automation (Phase 8.5), these timing values will be used identically:

**REPLAYER (UI Layer)**:
```python
bot_ui.build_amount_incrementally(Decimal('0.003'))
# Uses configured timing: 50ms depression, 100ms pauses
```

**Live Browser (Playwright)**:
```python
browser_executor.build_amount_incrementally(Decimal('0.003'))
# Uses SAME configured timing: 50ms depression, 100ms pauses
```

**Result**: Bot behavior is **identical** in training and production environments.

---

## Summary

✅ **Configurable via UI**: No code changes needed
✅ **Persists across sessions**: Saved to bot_config.json
✅ **Flexible timing**: 0ms to 5000ms range
✅ **Multiple use cases**: Training, production, demo, debug
✅ **Visual feedback**: See button depression in action
✅ **Phase 8 ready**: Works in both REPLAYER and browser

**Recommended Settings**:
- **Production**: 50ms depression, 100ms pause
- **Demo**: 50ms depression, 500ms pause
- **Training**: 50ms depression, 0ms pause

---

**Status**: Phase A.7 Complete ✅
**Date**: 2025-11-18
