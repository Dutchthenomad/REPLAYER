# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Repository Overview

- **Project**: Rugs.fun Replay Viewer – dual-mode replay/live trading platform with bot automation, browser integration, and ML.
- **Primary entrypoints**:
  - `./run.sh` – preferred way to launch the Tkinter UI using the shared rugs-rl-bot virtualenv.
  - `src/main.py` – direct entrypoint when running from `src/`.
- **Key docs**:
  - `README.md` – high-level features, project structure, and test commands.
  - `CLAUDE.md` – in-depth architecture, workflows, and audit notes (most complete technical reference).
  - `AGENTS.md` and `src/AGENTS.md` – concise repo rules, coding standards, and commands.
  - `docs/PHASE_8_COMPLETION_ROADMAP.md` – status and roadmap for the UI-first bot system.

Use `CLAUDE.md` when you need deep architectural detail or historical context; use this file plus `AGENTS.md` for quick orientation.

## Core Commands

### Running the application

From the repository root:

```bash
./run.sh                     # Launch UI using rugs-rl-bot venv if available
# or
cd src && python3 main.py    # Run directly from source
```

### Demos and browser connection

```bash
# Incremental button-clicking demo (educational UI behavior)
cd src && python3 demo_incremental_clicking.py

# CDP browser connection test (see CLAUDE.md for workflow)
cd . && python3 scripts/test_cdp_connection.py
```

### Tests

Canonical workflow (from `AGENTS.md` / `CLAUDE.md`):

```bash
cd src

# Full suite
python3 -m pytest tests/ -v

# Run tests for a module or package
python3 -m pytest tests/test_core/ -v
python3 -m pytest tests/test_bot/ -v

# Run a single test file
python3 -m pytest tests/test_core/test_game_state.py -v

# Filter to a single test function (pattern match)
python3 -m pytest tests/test_core/test_game_state.py -k "test_balance_updates" -vv

# With coverage (directory-level)
python3 -m pytest tests/ --cov=. --cov-report=html

# With markers (from pytest.ini)
python3 -m pytest -m unit
python3 -m pytest -m integration
python3 -m pytest -m "not slow"
python3 -m pytest -m ui
```

### Linting, formatting, and type-checking

```bash
cd src

black .
flake8
mypy core/ bot/ services/

# Project-specific test/lint wrapper
./verify_tests.sh
```

From the repo root there is also an automated review helper:

```bash
./scripts/pre_commit_review.sh   # Runs aicode-review checks (see CLAUDE.md)
```

### Analysis scripts (RL / research)

Run from the repository root:

```bash
python3 analyze_trading_patterns.py
python3 analyze_position_duration.py
python3 analyze_game_durations.py
```

These generate JSON/analysis outputs, which should be kept under `files/` or other gitignored paths (per `AGENTS.md`).

## High-Level Architecture

### Top-level layout

- `src/` – runtime code and tests (primary focus for Warp agents).
- `browser_automation/` – Playwright/CDP-based browser control and wallet automation.
- `docs/` – design plans, debugging guides, browser connection plans, and phase roadmaps.
- Root-level `analyze_*.py` scripts – empirical analysis utilities feeding RL/bot design.

Within `src/`, the main subsystems (see also the structure diagrams in `README.md` and `CLAUDE.md`):

- `main.py` – wires configuration, `GameState`, `EventBus`, and UI; owns application lifecycle.
- `config.py` – central configuration object, including paths, UI sizes, and financial/game constants.
- `models/` – data structures: ticks, positions (including partial closes), sidebets, and enums.
- `core/` – core game/business logic: `GameState`, replay engine, trade management, validators, live ring buffer, and recorder sink.
- `bot/` – bot orchestration: controller, async executor, UI-layer controller, browser executor, execution mode enum, and pluggable strategies.
- `ml/` – ML integration (symlinks into the separate rugs-rl-bot project for predictors and feature extraction).
- `sources/` – tick sources (e.g., live WebSocket feed).
- `ui/` – Tkinter/ttkbootstrap UI (windows, panels, bot config dialog, timing overlay, reusable widgets).
- `services/` – infrastructure services: event bus and logging.
- `tests/` – pytest suite mirroring the `src/` layout.

### Architectural patterns

#### Event-driven, thread-safe core

- **EventBus** (`services/event_bus.py`) implements a pub/sub system with queue-based async processing.
- **GameState** (`core/game_state.py`) is the single source of truth for balances, positions, and tick state.
  - Uses `threading.RLock` for re-entrant locking.
  - Emits state-change events via the EventBus instead of letting callers mutate state directly.
- **UI updates must stay on the main thread**:
  - Background workers publish events and/or dispatch work via `ui/tk_dispatcher.py`.
  - Any direct Tk widget mutation from background threads is a bug—always go through the dispatcher.

When changing core behavior, preserve the contract that:
- `GameState` updates are atomic and emit corresponding Events.
- Event callbacks do not re-enter `GameState` mutation while holding locks (see notes in `CLAUDE.md`).

#### Dual-mode bot execution (BACKEND vs UI_LAYER)

The bot can execute in two modes (central to Phase 8+):

- **BACKEND** (`bot.execution_mode.ExecutionMode.BACKEND`)
  - Direct calls into `GameState`/`TradeManager` for fast replay/ML training.
  - No artificial delays; best for offline analysis and backtests.

- **UI_LAYER** (`ExecutionMode.UI_LAYER`)
  - Routes actions through `BotUIController` (`bot/ui_controller.py`), which clicks widgets in the Tk UI.
  - Uses an incremental-clicking algorithm to build bet amounts via buttons (`X`, `+0.001`, `+0.01`, `+0.1`, `+1`, `1/2`, `X2`, `MAX`).
  - Simulates human timing with configurable small delays between clicks.

Bot strategies live under `bot/strategies/` and implement a common ABC (see `bot/strategies/base.py`).
`bot/controller.py` selects a strategy, pulls observations from `GameState`, and routes chosen actions through either the backend or UI-layer path.

#### Browser automation & CDP integration

- `browser_automation/` contains the infrastructure for controlling a real Chrome instance:
  - Legacy `rugs_browser.py` (Playwright-based helper).
  - CDP-based manager (`cdp_browser_manager.py` referenced in `CLAUDE.md`) for attaching to system Chrome.
- `bot/browser_executor.py` is the bridge between bot actions and the live browser DOM:
  - Mirrors `BotUIController`’s incremental button-clicking logic using Playwright selectors.
  - Provides methods to click trading/sidebet buttons and (eventually) reconcile browser state back into `GameState`.
- `ui/browser_connection_dialog.py` (described in `CLAUDE.md`) drives the user-facing connection flow.

Warp agents modifying browser behavior should:
- Prefer reusing/updating selectors from `docs/XPATHS.txt`.
- Keep UI-layer and browser-layer button semantics aligned (same incremental-clicking algorithm).

#### UI composition

- `ui/main_window.py` is the classic main UI shell, responsible for:
  - Laying out charts, controls, position tables, and bot controls.
  - Wiring menu actions (Bot, Live Feed, Browser, Recording, etc.).
  - Subscribing to `Events` and marshalling updates via `TkDispatcher`.
- `ui/panels.py`, `ui/bot_config_panel.py`, and `ui/widgets/` provide reusable panes and widgets.
- `ui/timing_overlay.py` implements a draggable timing overlay that displays execution delay statistics; it is tightly coupled to the timing metrics emitted from bot/browser paths.

There is also a newer `ui/modern_main_window.py` used when the `Application` is instantiated with `modern_ui=True`.

#### Tests and quality gates

- Tests mirror the `src/` layout under `src/tests/` (e.g., `core/game_state.py` → `tests/test_core/test_game_state.py`).
- Markers (`unit`, `integration`, `slow`, `ui`) are defined in `pytest.ini` and are used heavily in CLAUDE examples.
- `verify_tests.sh` encapsulates the expected pre-commit checks (pytest, formatting, lint, mypy).
- Additional code review/quality tooling is wired via `scripts/pre_commit_review.sh` and the `architect.yaml` / `RULES.yaml` configuration.

## Configuration, Environment, and External Dependencies

- `config.py` centralizes configuration including:
  - UI sizing and theme settings.
  - Financial defaults (e.g., `default_bet` now defaults to `0.0`, not `0.001`, as part of Phase 8 fixes).
  - File paths for recordings and config directories.
  - Accessors for environment variables like `RUGS_RECORDINGS_DIR`, `RUGS_CONFIG_DIR`, and `LOG_LEVEL`.
- Bot runtime configuration is persisted in `bot_config.json` (created and managed by `ui/bot_config_panel.py`):
  - Keys include `execution_mode`, `strategy`, `bot_enabled`, and UI timing parameters.
  - Defaults have been tuned so that execution mode is `ui_layer` and bet amount is `0`.
- `src/rugs_recordings/` is a symlink to an external recordings directory (typically `/home/nomad/rugs_recordings/` as described in `CLAUDE.md`).
- `src/ml/` contains symlinks into the separate `rugs-rl-bot` project; ML features should degrade gracefully when those links are missing.

When adding new configuration options, follow the existing patterns in `config.py`, persist user-facing knobs via the bot config panel where appropriate, and update relevant docs (especially `CLAUDE.md` and `README.md`).

## How Warp Agents Should Use Existing Docs

- For **quick commands, file layout, and basic rules**, consult:
  - `AGENTS.md` (root and `src/AGENTS.md`).
- For **deep architecture details, gotchas, and current phase priorities**, use:
  - `CLAUDE.md` (primary, up-to-date technical playbook).
  - `docs/PHASE_8_COMPLETION_ROADMAP.md` and related phase documents under `docs/`.
- For **user-facing behavior and demos**, use:
  - `README.md` and `QUICK_START_GUIDE.md`.

This WARP.md is meant to keep Warp agents aligned with those sources while giving a concise, big-picture map of how the system fits together.