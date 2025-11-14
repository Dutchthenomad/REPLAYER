# REPLAYER Codebase Audit

## Scope & Method
- Reviewed all Python packages under `src/` plus supporting scripts (notably `continuous_game_recorder.py`) focusing on replay, UI, bot, ML, and services layers.
- Verified threading, Tkinter usage, event bus semantics, state management, analytics, and file I/O for live-feed readiness.
- Findings ranked by potential impact on correctness, stability, and readiness for live Socket.IO ingestion.

## High-Level Summary
- The modular architecture is solid, but several core mechanics (rug handling, state resets, event emissions) are incomplete, preventing faithful replays or live bridging.
- Tkinter is being mutated from worker threads, which jeopardizes UI stability during real-time playback.
- Metrics/analytics surfaces (P&L, exit tick tracking) currently return inaccurate data because of parameter ordering/logging mistakes.
- Event-bus shutdown and multi-game life cycle handling need hardening before they can sustain a continuous socket feed.

## Findings Overview

| Severity | Issue | Location |
| --- | --- | --- |
| Critical | Tkinter UI mutated from playback thread; causes crashes & undefined behavior. | `src/core/replay_engine.py:150-208` calling `MainWindow._on_tick_update` (`src/ui/main_window.py:578-655`) |
| High | Rug events never liquidate positions or resolve sidebets; helper unused and emits non-existent event. | `src/core/trade_manager.py:205-260`, `src/services/event_bus.py:18-46` |
| High | Loading/reseting games does not clear state or emit `GAME_START`, so balances/flags bleed across sessions. | `src/core/replay_engine.py:61-126`, `src/main.py:82-108` |
| High | `GameState.reset` omits `rug_detected`, spamming `GAME_RUG` on every tick after first game. | `src/core/game_state.py:427-454` |
| Medium | Sell path mixes up `exit_tick` vs `exit_time`, so every closed position reports tick `0`. | `src/core/trade_manager.py:117-145`, `src/core/game_state.py:264-304` |
| Medium | EventBus shutdown can deadlock when queue is full because sentinel is enqueued after `_processing=False`. | `src/services/event_bus.py:94-101` |
| Medium | Metrics use gross balance deltas instead of realized P&L, making average win/loss meaningless. | `src/core/game_state.py:483-501` |
| Low | State never records `game_id` when ticks load, so bot/UI always see `Unknown`. | `src/core/replay_engine.py:292-320` |
| Low | Feature extractor divides by `(q3-q1)` without epsilon, crashing on constant-length sample batches. | `src/ml/feature_extractor.py:115-123` |

> **Note:** These are blockers for “accurately replay real games” because they distort session boundaries, rugs, and analytics—the same paths would be exercised by the live feed.

## Detailed Notes

### 1. UI Thread Safety (Critical)
- `ReplayEngine.play()` spawns a daemon thread that directly calls `display_tick()`, which calls the Tk-bound callback chain. Tkinter requires all widget operations on the root thread; you must marshal updates via `root.after` or an event queue.
- Failure mode: random `TclError`, frozen window, or outright crash—unacceptable for continuous live view.

### 2. Rug & Sidebet Lifecycle (High)
- `TradeManager.check_and_handle_rug` and `check_sidebet_expiry` are never invoked. As a result:
  - Active positions remain “open” at original entry price after a rug.
  - Sidebets never resolve, so balances stay debited permanently.
- Even if wired, the functions publish `Events.RUG_DETECTED`, a constant not defined in the EventBus enum—calling it would raise `AttributeError`.
- Fix by invoking these hooks from `ReplayEngine.display_tick`, closing positions, resolving bets, and emitting a defined event (`Events.GAME_RUG` already exists).

### 3. Session Reset Hygiene (High)
- `load_file()` displays the first tick without resetting state, zeroing metrics, or emitting `Events.GAME_START`.
- `GameState.reset()` recreates `_state` but drops keys (`rug_detected`, `game_id`, `last_sidebet_resolved_tick`), so pending detectors misfire and info panes show stale data.
- Multi-game auto-advance relies on `self.state.reset()` but because internal fields are missing, the next session starts corrupted.

### 4. Analytics Accuracy (Medium)
- `TradeManager.execute_sell()` passes `(exit_price, exit_tick)` to `GameState.close_position(exit_price, exit_time=None, exit_tick=0)` incorrectly, storing the tick in the `exit_time` slot and leaving `exit_tick=0`.
- `GameState.calculate_metrics()` infers win/loss from transaction log entries that represent *cash movements*, not P&L. Every sell logs the positive exit value; the “losses” list is always empty, so `avg_loss` reads 0%.
- Without fixing these, training data, UI stats, and live dashboards will misrepresent performance.

### 5. Event Bus Shutdown (Medium)
- `EventBus.stop()` sets `_processing=False` before enqueuing a sentinel. If the queue is at capacity, `put` blocks forever while the background thread has already exited, deadlocking shutdown (particularly if the live feed floods events).
- Move the sentinel enqueue before flipping the flag, or drain the queue in a loop until success.

### 6. Missing Metadata (Low)
- `display_tick` never writes `game_id` into `GameState`. Bots and UI labels accessing `state.current_game_id` always see `None`/`Unknown`. Include `game_id=tick.game_id` and carry it into snapshots.

### 7. Feature Extractor Divide-by-Zero (Low)
- `calculate_iqr_position` divides by `(stats['q3'] - stats['q1'])` without guarding; `RollingStats` can easily produce equal quartiles when fed short or uniform samples. Add `max(1, q3-q1)` or `max(eps, ...)`.

## Readiness for Live Feed
- Current architecture already separates ingestion (`ReplayEngine`), state (`GameState`), and presentation (`MainWindow`). However, the seven issues above must be resolved before the Socket.IO feed can be trusted:
  1. Thread-safe UI updates.
  2. Accurate rug handling and state resets.
  3. Correct metrics for bot evaluation.
  4. Reliable shutdown (important for auto-reconnect loops).
  5. Metadata propagation for multi-game analytics.

## Recommendations
- Fix high-severity issues before wiring in the live feed to avoid compounding bugs.
- Add regression tests for rug resolution, sidebet expiry, multi-game resets, and Tkinter-safe update wrappers (mock root).
- Instrument `EventBus` stats more aggressively during live sessions to detect drops/backlogs early.

Once these items are cleared, the project will be ready to accept ticks from `continuous_game_recorder.py` (or a live Socket.IO client) while simultaneously persisting recordings and feeding the bot’s rolling context.
