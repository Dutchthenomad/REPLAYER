# Implementation Plan: Refactor main_window.py (Issue #4)

## Goal
Extract controllers and builders from `main_window.py` to reduce it from 2,036 lines to under 800 lines while maintaining identical behavior.

## GitHub Issue
#4: Refactor main_window.py: Extract Controllers to Stay Under 800-Line Limit

## Current State Analysis

| Component | Lines | Location |
|-----------|-------|----------|
| main_window.py | 2,036 | Over limit by 1,236 lines |
| Existing controllers | 2,185 | Already extracted (6 controllers) |

### Line Breakdown in main_window.py

| Section | Lines | Extractable? |
|---------|-------|--------------|
| Imports + __init__ | ~155 | Keep |
| `_create_menu_bar` | ~225 | Yes → MenuBarBuilder |
| `_create_ui` | ~562 | Partially → UI Builders |
| Controller init in _create_ui | ~138 | Keep (dependency wiring) |
| `_setup_event_handlers` | ~36 | Keep |
| Tick processing | ~144 | Keep (core functionality) |
| Event handlers | ~290 | Yes → EventHandlerController |
| Balance lock/unlock | ~99 | Yes → BalanceController |
| Keyboard shortcuts | ~53 | Keep |
| Theme management | ~174 | Yes → ThemeController |
| Demo recording handlers | ~74 | Keep (small, menu callbacks) |
| Recording handlers | ~51 | Keep (delegates to controller) |
| Raw capture handlers | ~128 | Keep (menu callbacks) |
| Shutdown | ~46 | Keep |

**Estimated extractable**: ~788 lines → Target ~1,248 lines remaining (still over 800)

### Revised Strategy

To get under 800 lines, we need more aggressive extraction:

1. **Phase 1: UI Builders** (-400 lines) - Status bar, chart, playback, betting, action buttons
2. **Phase 2: Event Handler Controller** (-200 lines) - All `_handle_*` methods
3. **Phase 3: Balance Controller** (-100 lines) - Balance lock/unlock/edit
4. **Phase 4: Theme Controller** (-150 lines) - Theme + UI style management
5. **Phase 5: Menu Actions Controller** (-200 lines) - Demo recording + raw capture handlers

**Total extraction target**: ~1,050 lines → ~986 lines remaining (under 1,000)

## Architecture Impact

| Component | Change |
|-----------|--------|
| `src/ui/builders/` | NEW - UI construction modules |
| `src/ui/controllers/event_handler_controller.py` | NEW - Event handler consolidation |
| `src/ui/controllers/balance_controller.py` | NEW - Balance lock/unlock |
| `src/ui/controllers/theme_controller.py` | NEW - Theme management |
| `src/ui/controllers/menu_actions_controller.py` | NEW - Menu action handlers |
| `src/ui/main_window.py` | MODIFY - Reduce to orchestration only |

## Files to Create

| File | Lines Est. | Description |
|------|------------|-------------|
| `src/ui/builders/__init__.py` | 20 | Package exports |
| `src/ui/builders/menu_bar_builder.py` | 200 | Menu bar construction |
| `src/ui/builders/status_bar_builder.py` | 50 | Status bar row |
| `src/ui/builders/chart_builder.py` | 60 | Chart + zoom controls |
| `src/ui/builders/playback_builder.py` | 80 | Playback control row |
| `src/ui/builders/betting_builder.py` | 80 | Bet amount controls |
| `src/ui/builders/action_builder.py` | 120 | Action buttons + percentages |
| `src/ui/controllers/event_handler_controller.py` | 200 | Event handlers |
| `src/ui/controllers/balance_controller.py` | 100 | Balance management |
| `src/ui/controllers/theme_controller.py` | 150 | Theme + restart |
| `src/ui/controllers/menu_actions_controller.py` | 200 | Demo/capture handlers |

## Implementation Tasks (TDD Order)

---

### Phase 1: UI Builders (~400 lines extraction)

#### Task 1.1: Create builders package structure

**Test First:**
```python
# tests/test_ui/test_builders/__init__.py
# tests/test_ui/test_builders/test_menu_bar_builder.py
def test_menu_bar_builder_creates_menu():
    """MenuBarBuilder should create a tk.Menu with expected structure"""
    pass
```

**Implementation:**
```python
# src/ui/builders/__init__.py
from .menu_bar_builder import MenuBarBuilder
from .status_bar_builder import StatusBarBuilder
# ... etc
```

**Verify:**
```bash
cd src && python3 -c "from ui.builders import MenuBarBuilder; print('OK')"
```

#### Task 1.2: Extract MenuBarBuilder

**Pattern:**
```python
# src/ui/builders/menu_bar_builder.py
class MenuBarBuilder:
    def __init__(self, root: tk.Tk, callbacks: dict):
        self.root = root
        self.callbacks = callbacks

    def build(self) -> tuple[tk.Menu, dict]:
        """Build menu bar and return (menubar, menu_refs)"""
        menubar = tk.Menu(self.root)
        # ... construction
        return menubar, {
            'browser_menu': browser_menu,
            'dev_menu': dev_menu,
            # ... other refs needed by MainWindow
        }
```

#### Task 1.3: Extract StatusBarBuilder

**Pattern:**
```python
# src/ui/builders/status_bar_builder.py
class StatusBarBuilder:
    def __init__(self, parent: tk.Frame):
        self.parent = parent

    def build(self) -> dict:
        """Build status bar and return widget references"""
        # ... construction
        return {
            'tick_label': tick_label,
            'price_label': price_label,
            'phase_label': phase_label,
            'player_profile_label': player_profile_label,
            'browser_status_label': browser_status_label,
        }
```

#### Task 1.4-1.7: Extract remaining builders

Same pattern for:
- ChartBuilder
- PlaybackBuilder
- BettingBuilder
- ActionBuilder

---

### Phase 2: Event Handler Controller (~200 lines extraction)

#### Task 2.1: Create EventHandlerController

**Test First:**
```python
# tests/test_ui/test_controllers/test_event_handler_controller.py
def test_event_handler_controller_handles_game_tick():
    """EventHandlerController should process game tick events"""
    pass
```

**Implementation:**
```python
# src/ui/controllers/event_handler_controller.py
class EventHandlerController:
    def __init__(self, state, event_bus, ui_dispatcher, controllers: dict, widgets: dict):
        self.state = state
        # ... store dependencies

    def _handle_game_tick(self, event):
        """Forward to recording controller if active"""
        pass

    def _handle_trade_executed(self, event):
        pass

    # ... all _handle_* methods
```

---

### Phase 3: Balance Controller (~100 lines extraction)

#### Task 3.1: Create BalanceController

**Test First:**
```python
# tests/test_ui/test_controllers/test_balance_controller.py
def test_balance_controller_toggle_lock():
    """BalanceController should toggle between locked and unlocked states"""
    pass
```

**Implementation:**
```python
# src/ui/controllers/balance_controller.py
class BalanceController:
    def __init__(self, state, ui_dispatcher, widgets: dict):
        self.state = state
        self.ui_dispatcher = ui_dispatcher
        self.balance_locked = True
        self.manual_balance = None
        self.tracked_balance = state.get('balance')
        # ... store widget refs

    def toggle_balance_lock(self):
        """Handle lock/unlock button press"""
        pass

    def unlock_balance(self):
        pass

    def relock_balance(self, choice: str, new_balance=None):
        pass
```

---

### Phase 4: Theme Controller (~150 lines extraction)

#### Task 4.1: Create ThemeController

**Test First:**
```python
# tests/test_ui/test_controllers/test_theme_controller.py
def test_theme_controller_change_theme():
    """ThemeController should apply theme and save preference"""
    pass
```

**Implementation:**
```python
# src/ui/controllers/theme_controller.py
class ThemeController:
    def __init__(self, root, chart, toast=None):
        self.root = root
        self.chart = chart
        self.toast = toast

    def change_theme(self, theme_name: str):
        pass

    def save_theme_preference(self, theme_name: str):
        pass

    @staticmethod
    def load_theme_preference() -> str:
        pass

    @staticmethod
    def load_ui_style_preference() -> str:
        pass

    def set_ui_style(self, style: str):
        pass

    def restart_application(self):
        pass
```

---

### Phase 5: Menu Actions Controller (~200 lines extraction)

#### Task 5.1: Create MenuActionsController

**Test First:**
```python
# tests/test_ui/test_controllers/test_menu_actions_controller.py
def test_menu_actions_controller_demo_recording():
    """MenuActionsController should manage demo recording lifecycle"""
    pass
```

**Implementation:**
```python
# src/ui/controllers/menu_actions_controller.py
class MenuActionsController:
    def __init__(self, demo_recorder, raw_capture_recorder,
                 recording_controller, ui_dispatcher, toast, log_callback):
        pass

    # Demo recording
    def start_demo_session(self):
        pass

    def end_demo_session(self):
        pass

    # ... all demo methods

    # Raw capture
    def toggle_raw_capture(self):
        pass

    # ... all capture methods
```

---

### Phase 6: Integration & Cleanup

#### Task 6.1: Update MainWindow to use new modules

```python
# main_window.py - Final structure
class MainWindow:
    def __init__(self, ...):
        # Initialize builders
        # Build UI
        # Initialize controllers
        # Wire event handlers

    def _create_ui(self):
        # Use builders
        status_widgets = StatusBarBuilder(self.root).build()
        self.tick_label = status_widgets['tick_label']
        # ...

    def _create_menu_bar(self):
        menubar, refs = MenuBarBuilder(self.root, self._get_menu_callbacks()).build()
        self.browser_menu = refs['browser_menu']
        # ...
```

#### Task 6.2: Update controllers/__init__.py

Add new controllers to exports.

#### Task 6.3: Verify all tests pass

```bash
cd src && python3 -m pytest tests/ -v --tb=short
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular imports | Builders don't import MainWindow; use callbacks dict |
| Breaking keyboard shortcuts | Test shortcuts after each phase |
| Widget reference timing | Controllers init AFTER UI built |
| Callback threading | Maintain TkDispatcher usage in all handlers |

## Definition of Done

- [ ] `main_window.py` under 800 lines
- [ ] All tests pass (737 baseline)
- [ ] No new dependencies added
- [ ] No behavioral changes
- [ ] Each new file under 400 lines
- [ ] No circular imports
- [ ] PR created with `Closes #4`

## Estimated Effort

| Phase | Tasks | Est. Time |
|-------|-------|-----------|
| Phase 1: UI Builders | 7 tasks | 2-3 hours |
| Phase 2: Event Handlers | 2 tasks | 1 hour |
| Phase 3: Balance | 2 tasks | 30 min |
| Phase 4: Theme | 2 tasks | 30 min |
| Phase 5: Menu Actions | 2 tasks | 1 hour |
| Phase 6: Integration | 3 tasks | 1 hour |
| **Total** | **18 tasks** | **6-7 hours** |

## Execution Order

1. Create branch: `git checkout -b refactor/issue-4-main-window`
2. Execute phases 1-5 sequentially
3. Run full test suite between phases
4. Final integration in phase 6
5. Create PR with `Closes #4`

---

*Plan created: 2025-12-13*
*Status: PENDING APPROVAL*
