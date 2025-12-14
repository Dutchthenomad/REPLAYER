# REPLAYER Modular Refactoring Plan

**Version**: 1.0
**Created**: 2025-12-12
**Status**: DESIGN PHASE
**Branch**: `claude/refactor-modular-system-MchkM`

---

## Executive Summary

This document outlines a comprehensive refactoring plan to reorganize the `/src` directory for better modularity, reduced coupling, and improved maintainability. The current codebase has **20,591 LOC across 107 files** with significant architectural issues.

**Key Issues Identified**:
1. Browser automation code fragmented between `bot/` and `browser_automation/`
2. Monolithic UI module with duplicate main windows (5,542 LOC)
3. 668 LOC of dead code in production
4. Missing abstraction layers
5. Inconsistent module organization

**Expected Outcomes**:
- **Remove ~2,100 LOC** of duplicate/dead code
- **Consolidate browser automation** into single module
- **Decompose monolithic UI** into manageable components
- **Improve testability** with better abstractions
- **Clarify module boundaries** for easier onboarding

---

## Current vs. Proposed Structure

### Current Structure (Problems Highlighted)
```
src/
├── bot/                      # 16 files, 5,267 LOC
│   ├── controller.py
│   ├── strategies/           # ✅ Good organization
│   ├── ui_controller.py      # ❌ UI code in bot module
│   ├── browser_executor.py   # ❌ Browser code in bot module
│   ├── browser_bridge.py     # ❌ Browser code in bot module
│   ├── browser_selectors.py  # ❌ Browser code in bot module
│   ├── browser_timing.py     # ❌ Browser code in bot module
│   ├── browser_actions.py    # ❌ DEAD CODE (421 LOC)
│   └── browser_state_reader.py # ❌ DEAD CODE (247 LOC)
│
├── browser_automation/       # 4 files, 1,293 LOC
│   ├── cdp_browser_manager.py
│   ├── rugs_browser.py
│   ├── automation.py
│   └── persistent_profile.py
│
├── ui/                       # 19 files, 5,542 LOC
│   ├── main_window.py        # ❌ 1,529 LOC (God object)
│   ├── modern_main_window.py # ❌ 1,433 LOC (DUPLICATE!)
│   ├── panels.py             # ❌ Should be 5+ files
│   ├── components/           # ❌ Duplicates widgets/
│   ├── widgets/              # ❌ Overlaps with components/
│   ├── controllers/          # ⚠️ 5 files, overlapping responsibilities
│   └── tk_dispatcher.py      # ❌ Should be in services/
│
├── sources/                  # 3 files, 1,636 LOC
│   ├── websocket_feed.py     # ❌ 1,161 LOC (Monolithic)
│   └── game_state_machine.py # ⚠️ Unclear module placement
│
├── core/                     # ✅ 10 files, well-organized
├── models/                   # ✅ 9 files, clean data structures
├── services/                 # ✅ 4 files, good utilities
├── ml/                       # ✅ 3 files, clean integration
├── utils/                    # ⚠️ 2 files, minimal usage
└── scripts/                  # ✅ Helper scripts
```

### Proposed Structure (Clean Separation)
```
src/
├── bot/                      # 9 files, ~2,500 LOC
│   ├── __init__.py
│   ├── controller.py         # Strategy orchestration
│   ├── interface.py          # BotInterface abstraction
│   ├── execution_mode.py     # BACKEND vs UI_LAYER
│   ├── async_executor.py     # Async execution wrapper
│   ├── strategies/           # Trading strategies
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── conservative.py
│   │   ├── aggressive.py
│   │   ├── foundational.py
│   │   └── sidebet.py
│   └── config.py             # Bot configuration
│
├── browser/                  # 15 files, ~3,800 LOC (consolidated)
│   ├── __init__.py
│   ├── executor.py           # Main executor (from bot/)
│   ├── bridge.py             # UI→Browser bridge (from bot/)
│   ├── manager.py            # CDP browser manager
│   ├── profiles.py           # Profile management
│   ├── automation.py         # Wallet automation
│   ├── dom/                  # DOM interaction
│   │   ├── __init__.py
│   │   ├── selectors.py      # Element selectors (from bot/)
│   │   ├── timing.py         # Timing delays (from bot/)
│   │   └── state_reader.py   # Read browser state
│   ├── cdp/                  # Chrome DevTools Protocol
│   │   ├── __init__.py
│   │   ├── connection.py     # CDP connection logic
│   │   └── launcher.py       # Chrome launcher
│   └── exceptions.py         # Browser-specific errors
│
├── ui/                       # 20 files, ~3,400 LOC (decomposed)
│   ├── __init__.py
│   ├── main/
│   │   ├── __init__.py
│   │   └── window.py         # Consolidated main window (~2,000 LOC)
│   ├── dialogs/              # All dialogs in one place
│   │   ├── __init__.py
│   │   ├── browser_connection.py
│   │   ├── bot_config.py
│   │   └── balance_edit.py
│   ├── panels/               # Decomposed from panels.py
│   │   ├── __init__.py
│   │   ├── status.py         # Status panel
│   │   ├── chart.py          # Chart panel
│   │   ├── trading.py        # Trading panel
│   │   ├── bot.py            # Bot panel
│   │   └── controls.py       # Playback controls
│   ├── widgets/              # Merged components/ + widgets/
│   │   ├── __init__.py
│   │   ├── chart.py          # Chart widget
│   │   ├── toast.py          # Toast notifications
│   │   ├── game_button.py    # Game buttons
│   │   ├── timing_overlay.py # Timing metrics
│   │   └── ...
│   ├── controllers/          # UI controllers
│   │   ├── __init__.py
│   │   ├── replay.py         # Replay controller
│   │   ├── bot_executor.py   # Bot UI executor (from bot/)
│   │   ├── browser.py        # Browser controller
│   │   └── ...
│   └── themes/               # Theme management
│       ├── __init__.py
│       ├── theme_manager.py
│       └── dark_theme.py
│
├── sources/                  # 8 files, ~1,800 LOC (decomposed)
│   ├── __init__.py
│   ├── base.py               # Abstract GameSource interface
│   ├── websocket/            # WebSocket feed decomposed
│   │   ├── __init__.py
│   │   ├── client.py         # WebSocket client
│   │   ├── parser.py         # Message parsing
│   │   ├── reconnect.py      # Reconnection logic
│   │   └── buffer.py         # Message buffering
│   ├── replay/
│   │   ├── __init__.py
│   │   └── file_reader.py    # JSONL replay source
│   └── state_machine.py      # Game state machine
│
├── core/                     # 10 files (unchanged, well-organized)
│   ├── __init__.py
│   ├── game_state.py
│   ├── replay_engine.py
│   ├── trade_manager.py
│   ├── validators.py
│   ├── live_ring_buffer.py
│   └── recorder_sink.py
│
├── models/                   # 9 files (unchanged, clean)
│   ├── __init__.py
│   ├── game_tick.py
│   ├── position.py
│   ├── side_bet.py
│   └── enums.py
│
├── services/                 # 6 files, ~800 LOC (enhanced)
│   ├── __init__.py
│   ├── event_bus.py
│   ├── logger.py
│   ├── configuration.py      # Moved from root config.py
│   ├── ui_dispatcher.py      # Moved from ui/tk_dispatcher.py
│   └── error_handler.py      # NEW: Centralized error handling
│
├── ml/                       # 3 files (unchanged)
│   ├── __init__.py
│   ├── predictor.py
│   └── feature_extractor.py
│
└── abstractions/             # NEW: Shared interfaces
    ├── __init__.py
    ├── game_source.py        # GameSource ABC
    ├── browser_interface.py  # Browser ABC
    └── executor_interface.py # Executor ABC
```

---

## Refactoring Phases

### Phase 1: Quick Wins (1-2 hours)
**Goal**: Remove dead code, consolidate duplicates

**Tasks**:
1. ✅ Delete `bot/browser_actions.py` (421 LOC)
   - Convert to `docs/BROWSER_API_REFERENCE.md`
2. ✅ Delete `bot/browser_state_reader.py` (247 LOC)
   - Merge relevant parts into docs
3. ✅ Choose main window implementation
   - Keep `main_window.py` OR `modern_main_window.py`
   - Delete the other (saves 1,433 LOC)
4. ✅ Move `ui/tk_dispatcher.py` → `services/ui_dispatcher.py`
5. ✅ Merge `ui/components/` into `ui/widgets/`

**Outcome**: Remove ~2,100 LOC of dead/duplicate code

---

### Phase 2: Browser Consolidation (3-4 hours)
**Goal**: Unify all browser automation in `browser/` module

**Migration Steps**:

1. **Create new `browser/` directory structure**:
   ```bash
   mkdir -p src/browser/dom src/browser/cdp
   ```

2. **Move files from `bot/` → `browser/`**:
   ```bash
   git mv src/bot/browser_executor.py src/browser/executor.py
   git mv src/bot/browser_bridge.py src/browser/bridge.py
   git mv src/bot/browser_selectors.py src/browser/dom/selectors.py
   git mv src/bot/browser_timing.py src/browser/dom/timing.py
   ```

3. **Move files from `browser_automation/` → `browser/`**:
   ```bash
   git mv src/browser_automation/cdp_browser_manager.py src/browser/manager.py
   git mv src/browser_automation/rugs_browser.py src/browser/cdp/launcher.py
   git mv src/browser_automation/automation.py src/browser/automation.py
   git mv src/browser_automation/persistent_profile.py src/browser/profiles.py
   ```

4. **Update imports across codebase**:
   ```python
   # Old imports
   from bot.browser_executor import BrowserExecutor
   from browser_automation.cdp_browser_manager import CDPBrowserManager

   # New imports
   from browser.executor import BrowserExecutor
   from browser.manager import CDPBrowserManager
   ```

5. **Add `browser/__init__.py` with clean exports**:
   ```python
   from .executor import BrowserExecutor
   from .bridge import BrowserBridge
   from .manager import CDPBrowserManager

   __all__ = ['BrowserExecutor', 'BrowserBridge', 'CDPBrowserManager']
   ```

6. **Delete empty `browser_automation/` directory**

**Outcome**: Single unified browser module with clear structure

---

### Phase 3: UI Decomposition (4-6 hours)
**Goal**: Break monolithic UI into manageable components

**Migration Steps**:

1. **Create new UI subdirectories**:
   ```bash
   mkdir -p src/ui/main src/ui/dialogs src/ui/panels src/ui/controllers src/ui/themes
   ```

2. **Consolidate main windows**:
   - Choose implementation (likely `modern_main_window.py`)
   - Move to `src/ui/main/window.py`
   - Delete duplicate

3. **Decompose `ui/panels.py`** (491 LOC):
   - Extract `StatusPanel` → `ui/panels/status.py`
   - Extract `ChartPanel` → `ui/panels/chart.py`
   - Extract `TradingPanel` → `ui/panels/trading.py`
   - Extract `BotPanel` → `ui/panels/bot.py`
   - Extract `ControlsPanel` → `ui/panels/controls.py`

4. **Organize dialogs**:
   ```bash
   git mv src/ui/browser_connection_dialog.py src/ui/dialogs/browser_connection.py
   git mv src/ui/bot_config_panel.py src/ui/dialogs/bot_config.py
   git mv src/ui/balance_edit_dialog.py src/ui/dialogs/balance_edit.py
   ```

5. **Move bot UI controller**:
   ```bash
   git mv src/bot/ui_controller.py src/ui/controllers/bot_executor.py
   ```

6. **Update imports**:
   ```python
   # Old
   from ui.main_window import MainWindow
   from ui.panels import StatusPanel
   from bot.ui_controller import BotUIController

   # New
   from ui.main.window import MainWindow
   from ui.panels.status import StatusPanel
   from ui.controllers.bot_executor import BotUIController
   ```

**Outcome**: Organized UI with clear separation of concerns

---

### Phase 4: Sources Refactoring (2-3 hours)
**Goal**: Create abstract GameSource interface, decompose websocket_feed.py

**Migration Steps**:

1. **Create abstractions module**:
   ```bash
   mkdir -p src/abstractions
   ```

2. **Create `abstractions/game_source.py`**:
   ```python
   from abc import ABC, abstractmethod

   class GameSource(ABC):
       @abstractmethod
       async def connect(self):
           pass

       @abstractmethod
       async def get_next_tick(self):
           pass

       @abstractmethod
       async def disconnect(self):
           pass
   ```

3. **Decompose `sources/websocket_feed.py`** (1,161 LOC):
   - `WebSocketClient` → `sources/websocket/client.py`
   - `MessageParser` → `sources/websocket/parser.py`
   - `ReconnectLogic` → `sources/websocket/reconnect.py`
   - `MessageBuffer` → `sources/websocket/buffer.py`

4. **Implement GameSource interface**:
   ```python
   # sources/websocket/client.py
   from abstractions.game_source import GameSource

   class WebSocketGameSource(GameSource):
       # Implementation...
   ```

**Outcome**: Clean abstraction for swapping data sources

---

### Phase 5: Configuration & Services (1-2 hours)
**Goal**: Move configuration to services, add error handling

**Migration Steps**:

1. **Move config**:
   ```bash
   git mv src/config.py src/services/configuration.py
   ```

2. **Create centralized error handler**:
   ```python
   # src/services/error_handler.py
   class ErrorHandler:
       """Centralized error handling with logging and user notification"""

       def handle_browser_error(self, error):
           # Log, notify user, attempt recovery
           pass

       def handle_network_error(self, error):
           # Log, retry logic
           pass
   ```

3. **Update imports**:
   ```python
   # Old
   from config import Config

   # New
   from services.configuration import Config
   ```

**Outcome**: Cleaner services module with error handling

---

## Migration Checklist

### Pre-Migration
- [ ] Create backup branch: `git checkout -b refactor-backup`
- [ ] Run full test suite: `pytest src/tests/ -v`
- [ ] Document current test coverage: `pytest --cov`
- [ ] Commit clean state

### Phase 1 Checklist
- [ ] Delete `bot/browser_actions.py`
- [ ] Delete `bot/browser_state_reader.py`
- [ ] Choose main window (main_window.py or modern_main_window.py)
- [ ] Delete duplicate main window
- [ ] Move `ui/tk_dispatcher.py` → `services/ui_dispatcher.py`
- [ ] Merge `ui/components/` → `ui/widgets/`
- [ ] Update all imports
- [ ] Run tests: `pytest src/tests/ -v`
- [ ] Commit: `git commit -m "Phase 1: Remove dead code and duplicates"`

### Phase 2 Checklist
- [ ] Create `src/browser/` directory structure
- [ ] Move browser files from `bot/`
- [ ] Move browser files from `browser_automation/`
- [ ] Update imports in all affected files
- [ ] Add `browser/__init__.py` with exports
- [ ] Delete `browser_automation/` directory
- [ ] Run tests: `pytest src/tests/test_bot/ -v`
- [ ] Fix any broken tests
- [ ] Commit: `git commit -m "Phase 2: Consolidate browser automation"`

### Phase 3 Checklist
- [ ] Create `ui/main/`, `ui/dialogs/`, `ui/panels/`, `ui/controllers/`
- [ ] Move main window to `ui/main/window.py`
- [ ] Decompose `ui/panels.py` into 5 files
- [ ] Move dialogs to `ui/dialogs/`
- [ ] Move `bot/ui_controller.py` to `ui/controllers/bot_executor.py`
- [ ] Update imports
- [ ] Run tests: `pytest src/tests/test_ui/ -v`
- [ ] Fix any broken tests
- [ ] Commit: `git commit -m "Phase 3: Decompose UI module"`

### Phase 4 Checklist
- [ ] Create `src/abstractions/` directory
- [ ] Create `GameSource` ABC
- [ ] Create `sources/websocket/` subdirectory
- [ ] Decompose `websocket_feed.py` into 4 files
- [ ] Implement `GameSource` interface
- [ ] Update imports
- [ ] Run tests: `pytest src/tests/test_sources/ -v`
- [ ] Commit: `git commit -m "Phase 4: Refactor sources with abstractions"`

### Phase 5 Checklist
- [ ] Move `config.py` → `services/configuration.py`
- [ ] Create `services/error_handler.py`
- [ ] Update imports
- [ ] Run full test suite: `pytest src/tests/ -v`
- [ ] Verify test coverage: `pytest --cov`
- [ ] Commit: `git commit -m "Phase 5: Finalize services module"`

### Post-Migration
- [ ] Update `CLAUDE.md` with new structure
- [ ] Update `AGENTS.md`
- [ ] Run full test suite: `pytest src/tests/ -v`
- [ ] Verify all features work in UI
- [ ] Update documentation
- [ ] Push to remote: `git push origin claude/refactor-modular-system-MchkM`

---

## Testing Strategy

### Unit Tests
- Update import paths in all test files
- Verify tests still pass after each phase
- Add new tests for abstraction layers

### Integration Tests
- Test bot execution after browser consolidation
- Test UI functionality after decomposition
- Test WebSocket connection after sources refactoring

### Manual Testing Checklist
- [ ] Launch application: `./run.sh`
- [ ] Load a recording
- [ ] Play/pause/step through recording
- [ ] Open bot configuration
- [ ] Toggle bot on/off
- [ ] Connect to browser
- [ ] Execute browser actions
- [ ] Check all UI panels render
- [ ] Verify toast notifications work

---

## Risk Mitigation

### High-Risk Changes
1. **Browser consolidation**: Many imports to update
   - Mitigation: Use find/replace, run tests after each move

2. **UI decomposition**: Main window is 1,529 LOC
   - Mitigation: Start with panels.py (smaller), test incrementally

3. **Import path updates**: Affects entire codebase
   - Mitigation: Use automated refactoring tools, git grep to verify

### Rollback Plan
- Each phase committed separately
- Can revert individual phases with `git revert`
- Backup branch (`refactor-backup`) for full rollback

---

## Success Metrics

### Code Quality Metrics
- **Before**: 20,591 LOC, 107 files
- **After Target**: ~18,500 LOC, 115 files (smaller files, better organized)
- **Dead Code Removed**: 2,100 LOC
- **Average File Size**: Reduce from 192 LOC → 160 LOC

### Architectural Improvements
- ✅ Single browser module (not 2)
- ✅ No duplicate main windows
- ✅ Abstract interfaces for testing
- ✅ Clear module boundaries
- ✅ Improved navigability

### Developer Experience
- Easier onboarding (clear module structure)
- Faster test execution (better isolation)
- Reduced merge conflicts (smaller files)
- Improved IDE navigation

---

## Timeline Estimate

| Phase | Duration | Complexity |
|-------|----------|------------|
| Phase 1: Quick Wins | 1-2 hours | Low |
| Phase 2: Browser | 3-4 hours | Medium |
| Phase 3: UI | 4-6 hours | High |
| Phase 4: Sources | 2-3 hours | Medium |
| Phase 5: Services | 1-2 hours | Low |
| **Total** | **11-17 hours** | **Mixed** |

**Recommended Approach**: Execute one phase per session, commit and test thoroughly between phases.

---

## Notes & Considerations

### Why Not Refactor Tests?
- Test structure already mirrors code structure
- Will automatically update after code refactoring
- Update imports, don't restructure test files

### Why Keep `models/` Separate from `core/`?
- Pure data structures (no business logic)
- Can be reused across projects
- Clear dependency direction (core → models, not models → core)

### Why Create `abstractions/` Module?
- Shared interfaces reduce coupling
- Easier to swap implementations
- Improves testability (mock interfaces)
- Follows SOLID principles

### Future Considerations
- **Phase 6**: Add dependency injection framework
- **Phase 7**: Implement async/await consistently
- **Phase 8**: Add API layer for external integrations

---

## Approval & Sign-off

**Created By**: Claude Code
**Reviewed By**: _Pending_
**Approved By**: _Pending_

**Status**: 🔴 **AWAITING APPROVAL**

Once approved, proceed with Phase 1 implementation.

---

**Last Updated**: 2025-12-12
**Document Version**: 1.0
**Branch**: `claude/refactor-modular-system-MchkM`
