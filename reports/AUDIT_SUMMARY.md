# Technical Debt Audit - Phase 1 Summary

**Date:** 2025-12-14
**Branch:** repair/technical-debt-audit

## Automated Analysis Results

### Dead Code (Vulture)
- **41 findings** total
- **Production code issues:** 6
- **Test code issues:** 35 (mostly mock variables)

#### Production Code Issues (Actionable)
| File | Line | Issue | Priority |
|------|------|-------|----------|
| `ui/audio_cue_player.py` | 217 | Unreachable code after 'return' | P2-medium |
| `models/enums.py` | 5 | Unused import 'auto' | P3-low |
| `ui/ui_mockup_modern.py` | 4 | Unused import 'PhotoImage' | P3-low |
| `ui/widgets/chart.py` | 82 | Unused import 'tkttk' | P3-low |
| `scripts/debug_bot_session.py` | 32 | Unused import 'ImageGrab' | P3-low |

#### Convention Variables (No Action Needed)
- `exc_tb` in exception handlers (4 instances) - Python convention
- `signum` in signal handler - Python convention

### Complexity (Radon)
- **High complexity functions (C/D rating):**
  - `Config.validate` - D (25) - Too complex
  - `FoundationalStrategy.decide` - C (20)
  - `MainWindow._create_ui` - C (20)
  - `GameStateMachine.detect_phase` - C (19)
  - `MainWindow._process_tick_ui` - C (19)

### State Management Issues

**Key Finding: Two Independent Recording Systems**

1. **Legacy System (ReplayEngine)**
   - `auto_recording` (bool) - Whether recording is enabled
   - `recorder_sink.is_recording()` - Whether actively recording
   - `get_recording_info()` - Returns both states

2. **Phase 10.5 System (RecordingController)**
   - `RecordingStateMachine` - 4 states (IDLE, MONITORING, RECORDING, FINISHING_GAME)
   - `UnifiedRecorder` - Actual recording logic
   - `is_recording` / `is_active` properties

**Root Cause of Issue #18:** These two systems are independent. UI may show Phase 10.5 state while logs show legacy state.

## Characterization Tests Added

**Location:** `src/tests/test_characterization/`

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_recording_system.py` | 9 | Recording state sources, mismatch scenarios, log triggers |

## Issues Created

| Issue | Title | Priority | Labels |
|-------|-------|----------|--------|
| #17 | Master Tracking Issue | - | tech-debt/infrastructure |
| #18 | Recording state mismatch | P0-critical | tech-debt/state-conflict |
| #19 | Venv migration | P1-high | tech-debt/infrastructure |

## Recommended Next Issues

1. **P2-medium:** Unreachable code in audio_cue_player.py:217
2. **P2-medium:** Unused imports cleanup
3. **P2-medium:** High complexity functions refactor (Config.validate)

## Phase 1 Success Criteria

- [x] Repair branch created
- [x] All labels and milestones exist
- [x] Automated analysis reports generated
- [x] Initial issues created from findings
- [x] Characterization tests for recording system

## Next Steps (Phase 2)

1. Fix Issue #18 (Recording state mismatch) - P0-critical
2. Fix Issue #19 (Venv migration) - P1-high
3. Add characterization tests for event flow
4. Add characterization tests for UI state
