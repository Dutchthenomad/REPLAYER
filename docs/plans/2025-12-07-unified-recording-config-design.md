# Unified Recording Configuration System - Phase 10.5 Design

**Date**: December 7, 2025
**Status**: Design Complete - Ready for Implementation
**Phase**: 10.5

---

## 1. Overview

### Purpose
Replace the current fragmented recording systems with a unified configuration interface that allows users to control all recording behavior through a single pre-session config modal.

### Key Principles
- Recording is **OFF by default** - user explicitly starts sessions
- **No partial captures** - data integrity is paramount
- **Full game captures only** - start-to-end or nothing
- **Dual-layer architecture** - Game State (always) + Player State (optional)
- **Session-by-session configuration** with persistence option

---

## 2. File Organization

### Directory Structure
```
rugs_recordings/
├── games/                              # All game state recordings
│   ├── 20251207_143052_abc123.json
│   ├── 20251207_143215_def456.json
│   └── ...
│
└── demonstrations/                     # Player state recordings (when enabled)
    ├── 20251207_143052_abc123_player.json
    └── ...
```

### Game State File Schema
```json
{
  "meta": {
    "game_id": "abc123-def456-...",
    "start_time": "2025-12-07T14:30:52.123Z",
    "end_time": "2025-12-07T14:32:15.456Z",
    "duration_ticks": 138,
    "peak_multiplier": "2.45",
    "server_seed_hash": "...",
    "server_seed": "...",
    "has_player_input": true,
    "player_file": "demonstrations/20251207_143052_abc123_player.json"
  },
  "prices": ["1.0", "1.01", "1.03", ...]
}
```

### Player State File Schema
```json
{
  "meta": {
    "game_id": "abc123-def456-...",
    "player_id": "player-xyz",
    "username": "trader123",
    "session_start": "2025-12-07T14:30:52.123Z"
  },
  "actions": [
    {
      "tick": 45,
      "timestamp": "2025-12-07T14:31:15.789Z",
      "action": "BUY",
      "button": "BUY",
      "amount": "0.005",
      "price": "1.23",
      "balance_after": "0.995",
      "position_qty_after": "0.005",
      "latency_ms": 125
    }
  ]
}
```

### ML Pipeline Compatibility
- **Game State Only Training**: Ingest all files from `games/`
- **Imitation Learning**: Filter `games/` by `has_player_input: true`, join with `demonstrations/`
- **Index files**: Daily `index.json` in each directory for fast lookups

---

## 3. Configuration Options

### 3.1 Capture Mode
| Option | Description |
|--------|-------------|
| **Game State Only** | Record tick-by-tick prices, seeds, peak multiplier (DEFAULT) |
| **Game State + Player State** | Above + all human inputs, trades, timing, latency |

### 3.2 Session Limits
| Setting | Options | Default |
|---------|---------|---------|
| **Game Count** | 1, 5, 10, 25, 50, ∞ | ∞ |
| **Time Limit** | Off, 15m, 30m, 1hr, 2hr, Custom | Off |

**Behavior**: First limit reached stops recording (after current game completes).

### 3.3 Data Integrity
| Setting | Options | Default |
|---------|---------|---------|
| **Monitor Mode Threshold (Ticks)** | 5, 10, 15, 20, 30, 45, 60 | 20 |
| **Monitor Mode Threshold (Games)** | 1, 2, 3, 5, 10 | - |

**Note**: Ticks and Games thresholds are **mutually exclusive** - user selects one or the other.

### 3.4 Preferences
| Setting | Options | Default |
|---------|---------|---------|
| **Audio Cues** | On / Off | On |
| **Auto-start on Launch** | On / Off | Off |

### 3.5 Config Persistence
- Single saved configuration file (`recording_config.json`)
- `[Save Settings]` button persists current selections
- Settings loaded on application startup
- Auto-start respects saved config if enabled

---

## 4. Data Integrity Rules

### 4.1 Full Capture Requirement
**No partial games are ever saved.** A game recording must contain:
- Complete tick sequence from game start to rug/crash
- Valid game_id throughout
- Proper end event (rug detected)

### 4.2 Clean Start Behavior
When recording session begins:
1. Check if a game is currently in progress
2. If yes: **IGNORE** current game, enter MONITORING state
3. Wait for current game to end
4. Begin recording on **next fresh game start**

### 4.3 Clean Stop Behavior
When session limit is reached:
1. If mid-game: **CONTINUE** recording current game
2. Wait for game to complete (rug/crash)
3. Save completed game
4. **THEN** stop recording session

### 4.4 Monitor Mode
**Purpose**: Ensure data integrity by pausing recording during backend issues.

**Triggers** (any of these, after threshold exceeded):
- WebSocket connection loss/reconnect
- Data gaps (missing ticks in sequence)
- Abnormal game end (no proper rug/crash event)

**Threshold**: Configurable by ticks OR games (mutually exclusive)
- Ticks: 5, 10, 15, 20, 30, 45, 60 consecutive ticks of data loss
- Games: 1, 2, 3, 5, 10 dropped/corrupted games

**Recovery**:
1. Enter MONITORING state
2. Observe until ONE full clean game completes successfully
3. Resume recording on next game start

---

## 5. State Machine

```
                                    ┌─────────────────┐
                                    │                 │
                    ┌───────────────│      IDLE       │
                    │               │                 │
                    │               └────────┬────────┘
                    │                        │
                    │              User clicks "Start"
                    │                        │
                    │                        ▼
                    │               ┌─────────────────┐
                    │               │                 │
                    │               │   MONITORING    │◄────────────┐
                    │               │                 │             │
                    │               └────────┬────────┘             │
                    │                        │                      │
                    │           Full clean game observed            │
                    │                        │                      │
                    │                        ▼                      │
                    │               ┌─────────────────┐             │
                    │               │                 │             │
                    │               │   RECORDING     │─────────────┘
                    │               │                 │   Data integrity
                    │               └────────┬────────┘   issue detected
                    │                        │
                    │              Limit reached mid-game
                    │                        │
                    │                        ▼
                    │               ┌─────────────────┐
                    │               │                 │
                    │               │ FINISHING_GAME  │
                    │               │                 │
                    │               └────────┬────────┘
                    │                        │
                    │                  Game ends
                    │                        │
                    └────────────────────────┘
```

### State Descriptions

| State | Description |
|-------|-------------|
| **IDLE** | Not recording. Waiting for user to start session. |
| **MONITORING** | Watching feed, waiting for clean game to begin recording. |
| **RECORDING** | Actively capturing game data. |
| **FINISHING_GAME** | Limit reached, completing current game before stopping. |

---

## 6. Toast Notifications

| Event | Color | Message |
|-------|-------|---------|
| Recording started | Green | "Recording started" |
| Monitor mode entered | Yellow | "Recording paused - Monitor Mode active" |
| Recording resumed | Green | "Recording resumed" |
| Recording stopped | Blue | "Recording stopped - X games captured" |
| Session limit reached | Blue | "Session limit reached - finishing current game" |

---

## 7. UI Design

### 7.1 Entry Point
- Menu: `Recording → Start Recording Session...`
- Opens modal dialog (blocks main UI)

### 7.2 Modal Layout

```
┌──────────────────────────────────────────────────────┐
│            Recording Configuration                    │
├──────────────────────────────────────────────────────┤
│                                                      │
│  CAPTURE MODE                                        │
│  ┌────────────────────────────────────────────────┐  │
│  │  ○ Game State Only                             │  │
│  │  ● Game State + Player State                   │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
├──────────────────────────────────────────────────────┤
│                                                      │
│  SESSION LIMITS                                      │
│                                                      │
│  Game Count:                                         │
│    ○ 1   ○ 5   ○ 10   ○ 25   ○ 50   ● ∞            │
│                                                      │
│  Time Limit:                                         │
│    ● Off   ○ 15m   ○ 30m   ○ 1hr   ○ 2hr           │
│    ○ Custom: [____] min                             │
│                                                      │
├──────────────────────────────────────────────────────┤
│                                                      │
│  DATA INTEGRITY                                      │
│                                                      │
│  Monitor Mode Threshold:                             │
│                                                      │
│    By Ticks:                                         │
│    ○ 5  ○ 10  ○ 15  ● 20  ○ 30  ○ 45  ○ 60        │
│                                                      │
│    By Games:                                         │
│    ○ 1   ○ 2   ○ 3   ○ 5   ○ 10                    │
│                                                      │
├──────────────────────────────────────────────────────┤
│                                                      │
│  PREFERENCES                                         │
│  ┌────────────────────────────────────────────────┐  │
│  │  ☑ Audio Cues                                  │  │
│  │  ☐ Auto-start on Launch                        │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
├──────────────────────────────────────────────────────┤
│                                                      │
│    [Save Settings]         [Cancel]      [Start]    │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 7.3 Button Behavior

| Button | Action |
|--------|--------|
| **Save Settings** | Persist current selections to `recording_config.json`. Stay in dialog. |
| **Cancel** | Close dialog without starting. No changes saved. |
| **Start** | Begin recording session with current settings. Close dialog. Does NOT auto-save. |

### 7.4 Control Types

| Setting | Control Type |
|---------|--------------|
| Capture Mode | Radio buttons (vertical) |
| Game Count | Radio buttons (horizontal row) |
| Time Limit | Radio buttons (horizontal) + Custom input |
| Threshold (Ticks) | Radio buttons (horizontal row) |
| Threshold (Games) | Radio buttons (horizontal row) |
| Audio Cues | Checkbox |
| Auto-start on Launch | Checkbox |

---

## 8. Config File Format

### Location
`~/.replayer/recording_config.json` or `src/recording_config.json`

### Schema
```json
{
  "capture_mode": "game_state_only",
  "game_count": "infinite",
  "time_limit_minutes": null,
  "monitor_threshold_type": "ticks",
  "monitor_threshold_value": 20,
  "audio_cues": true,
  "auto_start_on_launch": false,
  "last_modified": "2025-12-07T14:30:00Z"
}
```

### Field Values
| Field | Valid Values |
|-------|--------------|
| `capture_mode` | `"game_state_only"`, `"game_and_player"` |
| `game_count` | `1`, `5`, `10`, `25`, `50`, `"infinite"` |
| `time_limit_minutes` | `null`, `15`, `30`, `60`, `120`, or custom integer |
| `monitor_threshold_type` | `"ticks"`, `"games"` |
| `monitor_threshold_value` | Depends on type (see section 3.3) |
| `audio_cues` | `true`, `false` |
| `auto_start_on_launch` | `true`, `false` |

---

## 9. Audio Cues

| Event | Sound |
|-------|-------|
| Recording started | Short ascending chime |
| Recording paused (monitor mode) | Warning tone |
| Recording resumed | Short ascending chime |
| Recording stopped | Completion tone |

**Implementation**: Use system sounds or bundled WAV files.

---

## 10. Implementation Phases

### Phase 10.5A: Config Model & Persistence
- Create `RecordingConfig` dataclass
- Implement load/save to JSON
- Unit tests for serialization

### Phase 10.5B: Recording State Machine
- Create `RecordingStateMachine` class
- Implement state transitions (IDLE → MONITORING → RECORDING → FINISHING_GAME)
- Wire to WebSocket events for game start/end detection
- Unit tests for all state transitions

### Phase 10.5C: Data Integrity Monitor
- Create `DataIntegrityMonitor` class
- Track consecutive data loss (ticks and games)
- Emit events when threshold exceeded
- Unit tests for threshold detection

### Phase 10.5D: Unified Recorder
- Create `UnifiedRecorder` class
- Orchestrates GameStateRecorder + PlayerSessionRecorder
- Respects capture mode setting
- Handles clean start/stop behavior
- Unit tests for dual-layer recording

### Phase 10.5E: Config Modal UI
- Create `RecordingConfigDialog` (Tkinter Toplevel)
- Implement all controls per design
- Wire Save/Cancel/Start buttons
- Integration test for UI flow

### Phase 10.5F: Toast Notifications
- Create `ToastNotification` widget
- Implement show/auto-dismiss behavior
- Wire to recording state changes

### Phase 10.5G: Audio Cues
- Bundle or reference sound files
- Create `AudioCuePlayer` utility
- Wire to recording events

### Phase 10.5H: Integration & Testing
- Wire all components together
- End-to-end testing
- Update MainWindow menu integration

---

## 11. Success Criteria

- [ ] Config modal appears on "Start Recording" menu selection
- [ ] All settings persist correctly across sessions
- [ ] Auto-start on launch works when enabled
- [ ] No partial games ever saved
- [ ] Clean start ignores in-progress games
- [ ] Clean stop finishes current game before stopping
- [ ] Monitor mode triggers correctly on data integrity issues
- [ ] Monitor mode recovers after observing clean game
- [ ] Toast notifications display for all recording events
- [ ] Audio cues play when enabled
- [ ] Dual-layer recording works (game + player state)
- [ ] Files organized correctly in games/ and demonstrations/
- [ ] `has_player_input` flag correctly set in game files
- [ ] All existing tests continue to pass
- [ ] New tests cover all Phase 10.5 components

---

## 12. Dependencies

### Existing Components (Phase 10.4)
- `GameStateRecorder` - records game state to JSON
- `PlayerSessionRecorder` - records player actions to JSON
- `PriceHistoryHandler` - tracks tick-by-tick prices
- `PlayerStateHandler` - handles player WebSocket events
- `StateVerifier` - detects drift between local and server state

### New Components (Phase 10.5)
- `RecordingConfig` - config dataclass + persistence
- `RecordingStateMachine` - state management
- `DataIntegrityMonitor` - data loss detection
- `UnifiedRecorder` - orchestration layer
- `RecordingConfigDialog` - config UI modal
- `ToastNotification` - notification widget
- `AudioCuePlayer` - sound playback utility

---

*Design Complete - Ready for Implementation*
