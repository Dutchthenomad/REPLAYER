# Configuration Expansion Roadmap

**Purpose**: Document all configurable parameters for future advanced bot configuration UI
**Status**: Planning/Reference
**Date**: 2025-11-18

---

## Overview

This document catalogs **40+ configurable parameters** across all trading strategies, providing a roadmap for building an advanced configuration UI that allows users to fine-tune bot behavior without code changes.

---

## Current Configuration State

### ✅ Implemented (Phase A.7)

**Location**: Bot → Configuration... menu

**Current Settings**:
1. Execution mode (BACKEND / UI_LAYER)
2. Strategy selection (conservative / aggressive / sidebet / foundational)
3. Bot enable/disable
4. Button depression duration (10-500ms)
5. Inter-click pause (0-5000ms)

**Persistence**: `bot_config.json`

---

## Future Configuration Expansion

### Architecture Design

**Proposed Structure**:
```
bot_config.json
├── execution_mode: "ui_layer"
├── strategy: "foundational"
├── bot_enabled: false
├── timing:
│   ├── button_depress_duration_ms: 50
│   └── inter_click_pause_ms: 100
├── strategy_params:
│   ├── foundational:
│   │   ├── entry:
│   │   │   ├── price_min: 25.0
│   │   │   ├── price_max: 50.0
│   │   │   ├── safe_window_ticks: 69
│   │   │   └── position_size_sol: 0.005
│   │   ├── exit:
│   │   │   ├── profit_target_pct: 100
│   │   │   ├── stop_loss_pct: -30
│   │   │   ├── max_hold_ticks: 60
│   │   │   └── temporal_exit_tick: 138
│   │   └── sidebet:
│   │       ├── enabled: true
│   │       ├── danger_zone_min_tick: 104
│   │       ├── danger_zone_max_tick: 138
│   │       └── amount_sol: 0.002
│   ├── conservative: { ... }
│   ├── aggressive: { ... }
│   └── sidebet: { ... }
└── risk_management:
    ├── max_position_size_sol: 0.01
    ├── daily_loss_limit_sol: 0.05
    └── bankruptcy_protection_threshold: 0.001
```

---

## Configurable Parameters by Strategy

### 1. FoundationalStrategy (Evidence-Based)

**Total**: 13 parameters

#### Entry Parameters (4)

| Parameter | Current | Range | Description |
|-----------|---------|-------|-------------|
| `entry_price_min` | 25.0 | 1.0 - 100.0 | Sweet spot lower bound (x multiplier) |
| `entry_price_max` | 50.0 | 1.0 - 1000.0 | Sweet spot upper bound (x multiplier) |
| `safe_window_ticks` | 69 | 0 - 300 | Max tick for entry (rug risk threshold) |
| `buy_amount` | 0.005 | 0.001 - 1.0 | Position size (SOL) |

**UI Component**:
```
Entry Settings
  Price Range: [25.0] to [50.0] x
  Safe Window: [69] ticks max
  Position Size: [0.005] SOL
```

#### Exit Parameters (4)

| Parameter | Current | Range | Description |
|-----------|---------|-------|-------------|
| `profit_target` | 100 | 10 - 1000 | Profit target (% gain) |
| `stop_loss` | -30 | -90 to -5 | Stop loss (% loss) |
| `max_hold_ticks` | 60 | 10 - 500 | Max time to hold position (ticks) |
| `median_rug_tick` | 138 | 50 - 500 | Temporal exit threshold (ticks) |

**UI Component**:
```
Exit Settings
  Profit Target: [100] %
  Stop Loss: [-30] %
  Max Hold Time: [60] ticks
  Temporal Exit: [138] ticks
```

#### Sidebet Parameters (5)

| Parameter | Current | Range | Description |
|-----------|---------|-------|-------------|
| `sidebet_enabled` | true | boolean | Enable/disable sidebets |
| `sidebet_tick_min` | 104 | 0 - 300 | Danger zone start (ticks) |
| `sidebet_tick_max` | 138 | 0 - 500 | Danger zone end (ticks) |
| `sidebet_amount` | 0.002 | 0.001 - 0.1 | Sidebet size (SOL) |
| `use_ml_predictor` | false | boolean | Use SidebetPredictor ML model |

**UI Component**:
```
Sidebet Settings
  Enable Sidebets: [✓]
  Danger Zone: [104] to [138] ticks
  Sidebet Amount: [0.002] SOL
  Use ML Predictor: [ ] (38.1% win rate, 754% ROI)
```

---

### 2. ConservativeStrategy

**Total**: 8 parameters

| Parameter | Current | Range | Description |
|-----------|---------|-------|-------------|
| `buy_threshold` | 1.5 | 1.0 - 10.0 | Max entry price (x multiplier) |
| `take_profit` | 20 | 5 - 500 | Profit target (% gain) |
| `stop_loss` | -15 | -90 to -5 | Stop loss (% loss) |
| `bubble_exit` | 10.0 | 5.0 - 100.0 | Emergency exit price (x) |
| `sidebet_tick` | 100 | 0 - 300 | Min tick for sidebet |
| `buy_amount` | 0.005 | 0.001 - 1.0 | Position size (SOL) |
| `sidebet_amount` | 0.002 | 0.001 - 0.1 | Sidebet size (SOL) |
| `sidebet_enabled` | true | boolean | Enable/disable sidebets |

**UI Component**:
```
Conservative Strategy Settings
  Entry Settings
    Max Entry Price: [1.5] x
    Position Size: [0.005] SOL
  Exit Settings
    Profit Target: [20] %
    Stop Loss: [-15] %
    Bubble Exit: [10.0] x
  Sidebet Settings
    Enable: [✓]
    Min Tick: [100]
    Amount: [0.002] SOL
```

---

### 3. AggressiveStrategy

**Total**: 9 parameters

| Parameter | Current | Range | Description |
|-----------|---------|-------|-------------|
| `entry_min` | 5.0 | 1.0 - 50.0 | Min entry price (x) |
| `entry_max` | 100.0 | 10.0 - 1000.0 | Max entry price (x) |
| `profit_target_low` | 50 | 10 - 200 | Profit @ low entry (%) |
| `profit_target_high` | 150 | 50 - 500 | Profit @ high entry (%) |
| `stop_loss` | -25 | -90 to -5 | Stop loss (% loss) |
| `bubble_exit` | 200.0 | 50.0 - 1000.0 | Emergency exit (x) |
| `buy_amount` | 0.008 | 0.001 - 1.0 | Position size (SOL) |
| `sidebet_amount` | 0.005 | 0.001 - 0.1 | Sidebet size (SOL) |
| `sidebet_enabled` | true | boolean | Enable/disable sidebets |

---

### 4. SidebetStrategy

**Total**: 6 parameters

| Parameter | Current | Range | Description |
|-----------|---------|-------|-------------|
| `sidebet_always` | true | boolean | Always place sidebets |
| `sidebet_amount` | 0.003 | 0.001 - 0.1 | Sidebet size (SOL) |
| `position_allowed` | false | boolean | Allow main positions |
| `buy_threshold` | 2.0 | 1.0 - 10.0 | Entry price if positions allowed |
| `buy_amount` | 0.001 | 0.001 - 1.0 | Position size (SOL) |
| `use_ml_predictor` | false | boolean | Use SidebetPredictor |

---

## Global Risk Management Parameters

**Total**: 7 parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `max_position_size_sol` | 0.01 | 0.001 - 1.0 | Max single position size |
| `max_total_exposure_sol` | 0.05 | 0.001 - 10.0 | Max combined positions |
| `daily_loss_limit_sol` | 0.05 | 0.001 - 10.0 | Stop trading after loss |
| `daily_profit_target_sol` | 0.10 | 0.001 - 100.0 | Stop trading after profit |
| `bankruptcy_threshold_sol` | 0.001 | 0.0001 - 0.1 | Min balance to continue |
| `position_size_mode` | "fixed" | "fixed" / "percent" | Fixed SOL or % of balance |
| `position_size_percent` | 5.0 | 1.0 - 50.0 | % of balance (if mode=percent) |

**UI Component**:
```
Risk Management
  Position Sizing
    Mode: ○ Fixed SOL  ● % of Balance
    Size: [5.0] % (or [0.005] SOL)
  Limits
    Max Position: [0.01] SOL
    Max Exposure: [0.05] SOL
    Daily Loss Limit: [0.05] SOL
    Daily Profit Target: [0.10] SOL
    Bankruptcy Threshold: [0.001] SOL
```

---

## Advanced Features (Future)

### Preset Profiles

**Purpose**: Quick strategy templates for different risk levels

**Presets**:

1. **Conservative** (Default)
   - Sweet spot: 25-50x
   - Profit target: 100%
   - Stop loss: -30%
   - Position size: 0.005 SOL

2. **Aggressive**
   - Sweet spot: 5-100x
   - Profit target: 150%
   - Stop loss: -40%
   - Position size: 0.010 SOL

3. **Ultra-Conservative**
   - Sweet spot: 25-35x
   - Profit target: 50%
   - Stop loss: -20%
   - Position size: 0.003 SOL

4. **Custom**
   - User-defined parameters
   - Save/load custom profiles

**UI Component**:
```
Strategy Presets
  ○ Conservative (default)
  ○ Aggressive
  ○ Ultra-Conservative
  ● Custom

  [Load Preset] [Save Custom]
```

---

### Dynamic Parameter Adjustment

**Real-Time Tuning**: Adjust parameters while bot is running

**Example Use Cases**:
- Tighten stop loss during volatile period
- Increase position size after winning streak
- Change sweet spot based on market conditions

**UI Component**:
```
Live Tuning (Experimental)
  [✓] Allow real-time adjustments

  Current Settings (editable):
    Entry Price Range: [25] - [50] x
    Profit Target: [100] %
    Stop Loss: [-30] %

  [Apply Changes] [Revert]
```

**Warning**: Changes apply to next trade, not current positions

---

## Implementation Plan

### Phase 1: Enhanced Config Structure (1 week)

**Tasks**:
1. Extend `bot_config.json` schema with strategy_params
2. Update `BotConfigPanel` to load/save nested config
3. Backward compatibility with existing config

**Deliverables**:
- Extended JSON schema
- Config migration script
- Updated BotConfigPanel class

---

### Phase 2: Advanced Configuration UI (1-2 weeks)

**Tasks**:
1. Create `AdvancedConfigPanel` with tabbed interface
2. Add parameter validation (ranges, types)
3. Add preset profile system
4. Real-time preview of changes

**UI Design**:
```
Bot → Advanced Configuration...

  Tabs:
  ├── Strategy [Foundational ▾]
  ├── Entry Settings
  ├── Exit Settings
  ├── Sidebet Settings
  ├── Risk Management
  └── Presets

  [Load Preset ▾] [Save Custom] [Reset to Defaults]

  [Apply] [Cancel]
```

---

### Phase 3: Strategy Introspection (1 week)

**Tasks**:
1. Add `get_configurable_params()` method to TradingStrategy
2. Auto-generate UI from strategy parameters
3. Dynamic form generation

**Benefits**:
- No manual UI updates when adding new strategies
- Consistent configuration experience
- Easy to add new parameters

**Example**:
```python
class FoundationalStrategy(TradingStrategy):
    def get_configurable_params(self):
        return {
            'entry': {
                'price_min': {
                    'type': 'float',
                    'default': 25.0,
                    'range': (1.0, 100.0),
                    'description': 'Sweet spot lower bound (x multiplier)',
                    'unit': 'x'
                },
                # ... more params
            }
        }
```

---

### Phase 4: Performance Tracking (1 week)

**Tasks**:
1. Add performance metrics to strategy
2. Track win rate, P&L, rug avoidance per config
3. Display historical performance

**UI Component**:
```
Configuration History

  Config A (2025-11-15 to 2025-11-17)
    Win Rate: 65%
    Avg P&L: +72%
    Games: 150
    [View Details] [Revert to This]

  Config B (2025-11-18 to present)
    Win Rate: 68%
    Avg P&L: +85%
    Games: 45
    [View Details] [Current]
```

---

## User Experience Flow

### Beginner Flow (Simple)

1. Open Bot → Configuration...
2. Select strategy from dropdown
3. Use preset: Conservative / Aggressive
4. Click OK
5. Enable bot and trade

**Time**: 10 seconds

---

### Advanced Flow (Custom Tuning)

1. Open Bot → Advanced Configuration...
2. Select strategy: Foundational
3. Adjust entry settings:
   - Price range: 30-45x (tighter sweet spot)
   - Safe window: 50 ticks (more conservative)
4. Adjust exit settings:
   - Profit target: 80% (take profits earlier)
   - Stop loss: -25% (tighter risk management)
5. Enable risk management:
   - Position size: 3% of balance
   - Daily loss limit: 0.03 SOL
6. Save as custom preset: "My Strategy"
7. Click Apply
8. Enable bot and trade

**Time**: 2-3 minutes

---

### Expert Flow (A/B Testing)

1. Create Config A (Conservative: 25-50x, 100% profit)
2. Run 100 games, track performance
3. Create Config B (Aggressive: 30-60x, 150% profit)
4. Run 100 games, track performance
5. Compare metrics
6. Select winning config
7. Deploy to production

**Time**: Several days of testing

---

## Benefits of Configuration System

### For Users

✅ **Customization**: Tailor strategy to risk tolerance
✅ **No Coding**: Adjust parameters via UI
✅ **Experimentation**: A/B test different configs
✅ **Quick Changes**: Adapt to market conditions
✅ **Learning**: Understand strategy parameters

### For Developers

✅ **Extensibility**: Easy to add new parameters
✅ **Testing**: Quickly test parameter variations
✅ **Debugging**: Isolate parameter effects
✅ **Maintenance**: Centralized config management
✅ **Reusability**: Preset profiles for common scenarios

---

## Technical Considerations

### Validation

**Parameter Validation**:
- Type checking (float, int, bool, enum)
- Range validation (min/max bounds)
- Dependency checking (e.g., price_min < price_max)
- Unit conversion (SOL, %, ticks, x)

**Example**:
```python
def validate_config(config):
    # Type check
    assert isinstance(config['entry']['price_min'], (int, float))

    # Range check
    assert 1.0 <= config['entry']['price_min'] <= 100.0

    # Dependency check
    assert config['entry']['price_min'] < config['entry']['price_max']

    # Return validated config or raise ValueError
    return config
```

### Persistence

**Config Storage**:
- JSON format (human-readable)
- Atomic writes (prevent corruption)
- Backup old configs before overwrite
- Version number (for migrations)

**Example**:
```json
{
  "_version": "2.0",
  "_created": "2025-11-18T22:30:00Z",
  "_modified": "2025-11-18T23:15:00Z",
  "execution_mode": "ui_layer",
  "strategy": "foundational",
  "strategy_params": { ... }
}
```

### Performance

**Config Loading**:
- Load once on startup
- Cache in memory
- Hot-reload on file change (optional)
- Merge with strategy defaults

**Real-Time Updates**:
- Apply to next trade (not current)
- Validate before applying
- Rollback on error

---

## Prioritization

### High Priority (Implement First)

1. **Entry/Exit Parameters** - Core trading logic
2. **Position Sizing** - Risk management
3. **Preset Profiles** - Easy onboarding

### Medium Priority

4. **Sidebet Configuration** - Optional feature
5. **Risk Management Limits** - Advanced users
6. **Performance Tracking** - Validation

### Low Priority

7. **Real-Time Tuning** - Expert feature
8. **A/B Testing Framework** - Research tool
9. **Multi-Strategy Ensemble** - Advanced composition

---

## Summary

**Total Configurable Parameters**: 40+
**Implementation Effort**: 3-4 weeks (all phases)
**User Impact**: High (customization without coding)
**Developer Impact**: High (easier testing and tuning)

**Next Steps**:
1. ⏭️ Complete Phase B testing with current hard-coded params
2. ⏭️ Gather user feedback on desired configurability
3. ⏭️ Implement Phase 1 (enhanced config structure)
4. ⏭️ Build Phase 2 (advanced UI)

---

**Status**: Planning/Reference Document
**Date**: 2025-11-18
**Purpose**: Guide future configuration expansion development
