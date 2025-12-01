# Modern UI Completion Plan

## Goal
Complete `modern_main_window.py` and add it as a switchable UI option accessible via View > UI Style menu.

## User Decisions
- **UI Switching**: Require app restart (simpler, more reliable)
- **Scope**: Full feature parity with standard UI (12-18 hours)

---

## Phase 1: Core Stub Methods (2-3 hours)

### 1.1 `_create_menu_bar()`
Port from `main_window.py` lines 243-294. Create full menu structure:
- **File**: Open Game, Load Multiple, Exit
- **Playback**: Play/Pause, Step Forward/Back, Reset, Speed controls
- **Bot**: Enable/Disable, Configure, Strategies submenu
- **Live Feed**: Connect/Disconnect, Status
- **Browser**: Connect, Disconnect, Status
- **View**: Theme (Dark/Light submenus), UI Style (Standard/Modern), Timing Overlay
- **Help**: About, Keyboard Shortcuts

### 1.2 `_setup_keyboard_shortcuts()`
Port from `main_window.py`. Bind:
- Space: Play/Pause
- B: Buy, S: Sell, D: Sidebet
- Right/Left arrows: Step forward/back
- R: Reset, H: Help
- Ctrl+O: Open file

### 1.3 `_setup_event_handlers()`
Subscribe to EventBus and GameState events:
- `Events.GAME_TICK`, `Events.GAME_STARTED`, `Events.GAME_ENDED`
- `Events.POSITION_OPENED`, `Events.POSITION_CLOSED`
- `Events.BALANCE_CHANGED`, `Events.SIDEBET_PLACED`
- `StateEvents.PHASE_CHANGED`

---

## Phase 2: Bot & Bridge Callbacks (1-2 hours)

### 2.1 `_check_bot_results()`
Periodic polling (100ms) for async bot execution results:
```python
def _check_bot_results(self):
    if self.bot_executor:
        result = self.bot_executor.get_result()
        if result:
            self._handle_bot_result(result)
    self.root.after(100, self._check_bot_results)
```

### 2.2 `_on_game_end(metrics)`
Handle game completion:
- Show toast with game summary
- Reset state if bankrupted
- Auto-advance to next game if multi-game mode
- Update statistics display

### 2.3 `_on_bridge_status_change(status)`
Update browser connection indicator:
```python
def _on_bridge_status_change(self, status):
    color = "#00cc66" if status == "connected" else "#ff3333"
    self.browser_status_label.config(bg=color)
```

---

## Phase 3: Missing UI Elements (2-3 hours)

### 3.1 Status Bar
Add bottom status bar with:
- Tick count label
- Current price label
- Game phase label
- Browser status indicator
- Bot status indicator

### 3.2 Playback Controls
Add control bar above action buttons:
- LOAD button (file dialog)
- PLAY/PAUSE toggle
- STEP FORWARD/BACK buttons
- RESET button
- Speed slider (0.5x, 1x, 2x, 4x)

### 3.3 Info Display Panel
Add side panel or overlay showing:
- Current balance
- Position details (entry price, P&L)
- Sidebet status
- Game ID

---

## Phase 4: Controller Integration (1-2 hours)

Reuse existing controllers instead of duplicating logic:
```python
from ui.controllers import (
    BotManager, ReplayController, TradingController,
    LiveFeedController, BrowserBridgeController
)
```

Wire controllers to modern UI callbacks and update displays.

---

## Phase 5: Theme Support for Components (1-2 hours)

### 5.1 RugsChartLog
Add theme-aware colors:
```python
def update_theme_colors(self, theme_name):
    colors = THEME_PALETTES.get(theme_name, DEFAULT_PALETTE)
    self.configure(bg=colors['background'])
    # Update candle colors, grid, etc.
```

### 5.2 GameButton3D
Add theme presets or dynamic color calculation based on theme.

---

## Phase 6: UI Style Switcher (1-2 hours)

### 6.1 Add to View Menu
```python
# In both main_window.py and modern_main_window.py
ui_menu = tk.Menu(view_menu, tearoff=0)
view_menu.add_cascade(label="UI Style", menu=ui_menu)
ui_menu.add_radiobutton(label="Standard", command=lambda: self._set_ui_style('standard'))
ui_menu.add_radiobutton(label="Modern (Game-Like)", command=lambda: self._set_ui_style('modern'))
```

### 6.2 Persistence
Save to `~/.config/replayer/ui_config.json`:
```json
{
  "theme": "cyborg",
  "ui_style": "modern"
}
```

### 6.3 Application Entry Point
Modify `main.py` to read UI style preference and instantiate correct window class:
```python
ui_style = load_ui_style_preference()  # 'standard' or 'modern'
if ui_style == 'modern':
    from ui.modern_main_window import ModernMainWindow
    window = ModernMainWindow(root, state, event_bus, config)
else:
    from ui.main_window import MainWindow
    window = MainWindow(root, state, event_bus, config)
```

---

## Phase 7: Testing & Polish (1-2 hours)

### Manual Testing Checklist
- [ ] File open works
- [ ] Playback controls work
- [ ] Bot enable/disable works
- [ ] Buy/Sell/Sidebet work
- [ ] Theme switching works
- [ ] UI style switching works (requires app restart)
- [ ] Keyboard shortcuts work
- [ ] Live feed connection works
- [ ] Browser connection works

---

## Critical Files

| File | Purpose | Lines to Reference |
|------|---------|-------------------|
| `src/ui/main_window.py` | Port menu, shortcuts, event handlers | 243-294, 306-469, 814-1081 |
| `src/ui/modern_main_window.py` | Target file (6 stubs to complete) | All |
| `src/main.py` | Add UI style selection logic | 35-75, 151-173 |
| `src/ui/controllers/` | Reuse existing controllers | All |
| `src/ui/components/rugs_chart.py` | Add theme support | All |

---

## Estimated Total Effort
**12-18 hours** across 7 phases

## Recommended Order
1. Phase 1 (Core Stubs) - Foundation
2. Phase 3 (Missing UI) - Visual completeness
3. Phase 2 (Callbacks) - Functionality
4. Phase 4 (Controllers) - Clean architecture
5. Phase 6 (Switcher) - User-facing feature
6. Phase 5 (Theme Support) - Polish
7. Phase 7 (Testing) - Quality assurance

---

## Current State of modern_main_window.py

**Working (393 lines)**:
- Chart (RugsChartLog)
- 3D Buttons (GameButton3D) for BUY/SELL/SIDEBET
- Bet amount controls (+0.001, +0.01, etc.)
- Bot integration framework
- Toast notifications

**6 Stub Methods to Complete**:
1. `_create_menu_bar()` - Empty pass (line 381-383)
2. `_setup_keyboard_shortcuts()` - Empty pass (line 384)
3. `_setup_event_handlers()` - Empty pass (line 385)
4. `_check_bot_results()` - Empty pass (line 386)
5. `_on_game_end(metrics)` - Empty pass (line 387)
6. `_on_bridge_status_change(status)` - Empty pass (line 388)

**Missing Functionality**:
- File > Open Game menu
- File > Load Multiple Games (queue)
- Live Feed connection menu
- Playback controls (play/pause/stop/speed)
- Game info display (tick count, phase, price)
- Position/balance display
- Status bar
- Browser connection menu
