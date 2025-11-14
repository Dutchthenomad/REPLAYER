# Live Feed Integration Plan

This document outlines how to evolve REPLAYER from “JSONL playback” to “dual-mode live + recorded” operation while continuing to archive every Rugs.fun session via `continuous_game_recorder.py`.

## Goals
1. Ingest the Socket.IO feed (via `WebSocketFeed`) and render it through the existing UI/bot stack with no special cases.
2. Persist every live game under `config.FILES['recordings_dir']` while simultaneously maintaining an in-memory 10-game window for bot context.
3. Allow seamless switching between recorded playback and live mode using the same `ReplayEngine` APIs.
4. Keep multi-game playback continuous unless the user pauses, mirroring live conditions.

## Current Recorder (Context)
`CV-BOILER-PLATE-FORK/scripts/continuous_game_recorder.py` already:
- Connects to Rugs.fun via `WebSocketFeed`.
- Streams `signal` ticks and `gameComplete` events.
- Writes one JSONL per game with `game_start` / `tick` / `game_end` events.

We will reuse its event wiring but embed it directly in REPLAYER so the UI/bot consume ticks as they arrive.

## Target Architecture
```
WebSocketFeed --> LiveFeedSource --> ReplayEngine (new ingestion adapters)
                                    |
        +---------------------------+------------------------------+
        |                           |                              |
   GameState <--> EventBus   LiveRingBuffer (10 games)   RecorderSink (JSONL)
        |                           |                              |
      UI/Bot                   Bot Analyzer/ML              Disk persistence
```

### Key Components
1. **LiveFeedSource**  
   - Wraps `WebSocketFeed`. Normalizes events into `GameTick` objects, forwards them to `ReplayEngine.push_tick()`, and mirrors them to the recorder sink.
2. **RecorderSink**  
   - Shared module that replicates `ContinuousRecorder`’s `start_new_game_file`, `write_tick`, `_finish_game_file` functionality, but runs inside REPLAYER to avoid dual processes.
3. **LiveRingBuffer**  
   - Deque of the last N (`>=10`) completed games + partial current game for bot context. On startup, pre-populate from most recent JSONL files so context survives restarts.
4. **ReplaySource Abstraction**  
   - Introduce `ReplaySource` interface (`next_tick()`, `load_game()`, `is_live`). Implementations:
     - `FileDirectorySource` (existing JSONL playback).
     - `LiveFeedSource` (new).  
   - `ReplayEngine` gains `attach_source(source)` and a `push_tick` method for live pushes.
5. **UI Orchestration**  
   - Add a mode toggle (Recorded / Live). In Live mode, disable manual step controls but keep pause/resume; default to auto-play.

## Implementation Steps
1. **Stabilize Core (Blockers)**  
   - Fix thread safety, rug handling, state reset, event bus shutdown, metrics, `game_id`, and feature extractor issues documented in `codebase_audit.md`.
2. **Abstract Replay Sources**  
   - Extract file iteration logic from `ReplayEngine` into `FileDirectorySource`. Provide a simple iterator returning `GameTick` sequences.
3. **Add `push_tick` Path**  
   - Extend `ReplayEngine` with `push_tick(tick: GameTick, *, live: bool = False)` that bypasses the `ticks` list and directly updates state/UI. Use `root.after` to schedule UI updates safely.
4. **Embed RecorderSink**  
   - Port the minimal recording functionality from `continuous_game_recorder.py` into `src/services/recorder.py`. It should expose `start(game_id)`, `write_tick(tick: GameTick)`, `finish(metadata)`.
5. **Implement LiveRingBuffer**  
   - New module `src/services/live_ring_buffer.py` maintaining `deque[GameSummary]`. Provide methods: `ingest_tick(game_id, tick)`, `complete_game(game_id, metadata)`, `get_last_n(n)`.
   - On startup, load the latest JSONL files (bounded) to warm the buffer.
6. **Create LiveFeedSource**  
   - Wrap `WebSocketFeed` inside REPLAYER (respecting the same keep-alive). Emit events:
     ```python
     class LiveFeedSource(ReplaySource):
         def start(self):
             self.websocket.on('signal')(self._handle_tick)
             self.websocket.on('gameComplete')(self._handle_complete)
             self.websocket.connect()
     ```
   - `_handle_tick` should:
     - Detect new game IDs → call `recorder.start(game_id)` and `game_state.reset()`.
     - Convert payload to `GameTick`.
     - Forward to `ReplayEngine.push_tick(tick, live=True)`.
     - Persist via `recorder.write_tick`.
     - Update `LiveRingBuffer`.
7. **Continuous Playback & Pause Semantics**  
   - In multi-game (recorded) mode, call `play()` automatically after `GAME_END` unless the user paused. In live mode, `pause` should buffer ticks but not drop them (maintain queue).
8. **Configuration & CLI**  
   - Expose a CLI flag or config toggle (e.g., `--live` or `config.PLAYBACK['live_mode']`).  
   - Document environment requirements (Socket.IO credentials, output directory).

## Script Examples

### LiveFeedSource Skeleton
```python
# src/services/live_feed_source.py
class LiveFeedSource(ReplaySource):
    def __init__(self, event_bus, recorder, ring_buffer, config):
        self.websocket = WebSocketFeed(log_level='WARN')
        self.current_game_id = None
        self.recorder = recorder
        self.ring_buffer = ring_buffer
        self.config = config

    def start(self):
        @self.websocket.on('connected')
        def _on_connected(_info):
            event_bus.publish(Events.UI_UPDATE, {'message': 'Live feed connected'})

        @self.websocket.on('signal')
        def _on_signal(signal):
            if signal.gameId != self.current_game_id:
                self._start_new_game(signal.gameId)

            tick = GameTick(
                game_id=signal.gameId,
                tick=signal.tickCount,
                timestamp=datetime.utcnow().isoformat(),
                price=Decimal(str(signal.price)),
                phase=signal.phase,
                active=signal.active,
                rugged=signal.rugged,
                cooldown_timer=signal.cooldownTimer,
                trade_count=signal.tradeCount
            )

            self.recorder.write_tick(tick)
            self.ring_buffer.ingest_tick(tick)
            replay_engine.push_tick(tick, live=True)

        @self.websocket.on('gameComplete')
        def _on_complete(payload):
            self.recorder.finish(payload)
            self.ring_buffer.complete_game(payload)
            self.current_game_id = None

        self.websocket.connect()
```

### ReplayEngine Push Path
```python
class ReplayEngine:
    def push_tick(self, tick: GameTick, live: bool = False):
        def apply_tick():
            self.state.update(
                current_tick=tick.tick,
                current_price=tick.price,
                current_phase=tick.phase,
                rugged=tick.rugged,
                game_active=tick.active,
                game_id=tick.game_id
            )
            self.state.current_tick = tick
            self._maybe_handle_rug(tick)
            event_bus.publish(Events.GAME_TICK, {...})
            if self.on_tick_callback:
                self.on_tick_callback(tick, self.current_index, self.total_ticks)
        self.ui_loop.after(0, apply_tick)  # Tk-safe
```

### LiveRingBuffer Outline
```python
class LiveRingBuffer:
    def __init__(self, capacity=10):
        self.capacity = capacity
        self.completed = deque(maxlen=capacity)
        self.current = None

    def start_game(self, game_id):
        self.current = {'game_id': game_id, 'ticks': [], 'metadata': {}}

    def ingest_tick(self, tick: GameTick):
        if not self.current or self.current['game_id'] != tick.game_id:
            self.start_game(tick.game_id)
        self.current['ticks'].append(tick)

    def complete_game(self, metadata):
        if self.current:
            self.current['metadata'] = metadata
            self.completed.append(self.current)
            self.current = None

    def get_last_games(self, count=10):
        return list(self.completed)[-count:]
```

### RecorderSink Usage
```python
recorder = RecorderSink(config.FILES['recordings_dir'])
recorder.start(game_id)
recorder.write_tick(tick)  # writes JSON line + flush
recorder.finish({
    'total_ticks': len(game_ticks),
    'peak_price': max_price,
    ...
})
```

## Verification Checklist
1. Unit tests for:
   - Rug handling & sidebet resolution.
   - `ReplayEngine.push_tick` threading behavior (mock `Tk` root).
   - LiveRingBuffer persistence/restore.
2. Integration test that streams sample ticks through `LiveFeedSource` and confirms:
   - State resets between games.
   - Recorder writes files identical to legacy script.
   - Bot receives 10-game history.
3. Manual test plan:
   - Start live mode → verify UI updates in real time.
   - Toggle pause/resume.
   - Switch back to recorded playback without restarting the app.

## Next Steps
1. Land fixes from the audit.
2. Implement ReplaySource abstraction + push path.
3. Port recorder + buffer modules.
4. Embed WebSocket client and guard behind a config flag.
5. Harden automated tests & logging around the new pipeline.

Once complete, REPLAYER can continually record, replay, and display live Rugs.fun sessions with unified tooling, making it trivial to hook into reinforcement-learning agents or other downstream consumers.
