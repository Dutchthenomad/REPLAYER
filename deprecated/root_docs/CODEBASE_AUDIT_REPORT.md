# Codebase Audit Report

## Executive Summary
The `/src` codebase demonstrates a mature and modular architecture, particularly in its use of event-driven design and thread-safe state management. The transition to CDP-based browser automation (`src/browser_automation/cdp_browser_manager.py`) is a significant architectural strength, solving critical issues with wallet persistence. However, the codebase shows signs of rapid iteration, including clutter in the UI directory, ad-hoc test scripts in the source root, and some minor technical debt in error handling and configuration management.

## 1. Architecture & Design
**Strengths:**
*   **Modular Structure:** Clear separation between Core, Bot, UI, and Services.
*   **Event-Driven:** The `EventBus` (`src/services/event_bus.py`) effectively decouples components, with recent fixes for weak references and deadlock prevention.
*   **State Management:** `GameState` (`src/core/game_state.py`) implements a robust observer pattern with thread safety and bounded history, preventing memory leaks.
*   **Browser Automation:** The `CDPBrowserManager` is well-designed to handle the specific challenges of Web3 automation (wallet extensions, persistence).

**Weaknesses:**
*   **Configuration Hardcoding:** `CDPBrowserManager` contains hardcoded paths for Chrome binaries and user profiles, reducing portability.
*   **Script Pollution:** Top-level ad-hoc scripts (`automated_bot_test.py`, `debug_bot_session.py`) clutter the source root and should be moved to `tests/` or `scripts/`.

## 2. Technical Debt
### UI Directory Clutter
The `src/ui/` directory contains several backup files that should be removed to avoid confusion and maintain a clean repository.
*   `src/ui/main_window.py.backup`
*   `src/ui/main_window.py.old_ui`
*   `src/ui/main_window.py.pre_optimization_backup`

### TODOs and Incomplete Features
*   **Bot Manager:** `src/ui/controllers/bot_manager.py` contains a TODO regarding the lack of a toast notification system for configuration updates.
    ```python
    # TODO: Consider adding toast callback or notification system
    ```
*   **Hardcoded Strategies:** `src/automated_bot_test.py` has a TODO to integrate with the actual REPLAYER.

## 3. Bugs & Potential Issues
### Replay Engine Destructor
In `src/core/replay_engine.py`, the `__del__` method swallows all exceptions during cleanup. While this prevents crashes during shutdown, it may hide underlying resource leakage issues.
```python
def __del__(self):
    try:
        self.cleanup()
    except Exception:
        pass  # AUDIT FIX: Should log this instead of silent pass
```

### Chrome Binary Detection
In `src/browser_automation/cdp_browser_manager.py`, the list of Chrome binaries is hardcoded for Linux. This will fail on macOS or Windows, or non-standard Linux setups.
```python
CHROME_BINARIES = [
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    ...
]
```

## 4. Recommendations

### High Priority
1.  **Clean up UI Directory:** Remove all `*.backup`, `*.old_ui` files from `src/ui/`.
2.  **Move Scripts:** Move `src/automated_bot_test.py`, `src/debug_bot_session.py`, and `src/playwright_debug_helper.py` to `src/scripts/` or `src/tests/` to clean up the package root.

### Medium Priority
1.  **Fix ReplayEngine Cleanup:** Update `src/core/replay_engine.py` to log errors in `__del__` using the safe logging mechanism already present in the class (`_safe_log`).
2.  **Configurable Browser Paths:** Refactor `CDPBrowserManager` to load Chrome binary paths and profile directories from `config.py` or environment variables, improving portability.
3.  **Implement Notifications:** Address the TODO in `src/ui/controllers/bot_manager.py` by passing the `toast` object from `MainWindow` to `BotManager` (similar to how it's passed to `TradingController`).

### Low Priority
1.  **Standardize Testing:** Consolidate ad-hoc test scripts into the `src/tests/` directory and ensure they run with the standard `pytest` runner.

## 5. Action Plan
To immediately improve the codebase health, I recommend executing the "High Priority" cleanup tasks first, followed by the "Medium Priority" fixes for `ReplayEngine` and `BotManager`.
