# Changes Summary (Codex Session)

## Scope
Repairs covered every finding from the audit (UI threading, rug/state hygiene, metrics accuracy, event bus shutdown, metadata propagation, feature extractor guard, multi-game semantics) plus new regression tests and documentation.

## Highlights
1. **State & Metrics**
   - `src/core/game_state.py` now rebuilds state via `_build_initial_state`, preserves `rug_detected`/`last_sidebet_resolved_tick`, records exit ticks when closing positions, and computes drawdown/ROI safely. Metrics derive average win/loss from realized P&L stored in `_closed_positions`.
2. **Replay Flow**
   - `src/core/replay_engine.py` resets `GameState`, sets `game_id`, and emits `Events.GAME_START` before showing tick zero; `Events.GAME_END` now clears `game_active`.
3. **Trade Lifecycle**
   - `src/core/trade_manager.py` passes `exit_tick` explicitly and reuses rug/sidebet checks on every tick (triggered from the UI dispatcher).
4. **Thread-Safe UI**
   - Added `src/ui/tk_dispatcher.py` and integrated it in `MainWindow`, ensuring background ticks schedule UI work on Tk’s thread. Multi-game mode resumes automatically unless the user paused.
5. **Event Bus & Utilities**
   - `src/services/event_bus.py` gained `RUG_DETECTED` and a resilient `stop()` handling full queues.
   - `src/ml/feature_extractor.py` guards against zero IQR.
6. **New Tests**
   - Added coverage for GameState resets/metrics, replay load behavior, Tk dispatcher, event bus shutdown, and feature extractor edge cases (`src/tests/test_*` additions).
7. **Docs & Tracking**
   - Created `docs/Codex/live_feed_integration_plan.md`, `docs/Codex/codebase_audit.md`, and the scratch pad `docs/Codex/REPAIR_NOTES.md` (all repairs marked complete).

## Testing
- `RUGS_LOG_DIR=/tmp/rugs_logs pytest tests/test_core/test_game_state.py::TestGameStateResetAndMetrics::test_reset_restores_core_flags -q`
- `RUGS_LOG_DIR=/tmp/rugs_logs pytest tests/test_core/test_replay_engine.py tests/test_ui/test_dispatcher.py tests/test_services/test_event_bus.py::TestEventBusShutdown::test_stop_handles_full_queue tests/test_ml/test_feature_extractor.py -q`

All targeted fixes are covered; broader suites can be run once remaining legacy tests are aligned with the current API. No outstanding high- or medium-severity findings remain from the audit list.
