# Repository Guidelines

**Last Updated**: 2025-11-17
**Project Status**: Phase 8 (UI-First Bot System) - 85% Complete
**Active Branch**: `main`
**Tests**: 275/276 passing (99.6%)

## Current Sprint

**Objective**: Complete Phase 8 - UI-First Bot System
**Progress**: Phases 8.1-8.5 ✅ complete, 8.6-8.7 pending (11-17 hours)
**See**: `docs/PHASE_8_COMPLETION_ROADMAP.md` for detailed plan

**Critical Issues** (Fix in next session):
1. Bet amount defaults to 0.001 (should be 0)
2. Execution mode defaults to BACKEND (should be UI_LAYER)
3. Missing bot_config.json file

**Recent Completions**:
- ✅ Browser connection working (Chromium + Phantom extension)
- ✅ Partial sell infrastructure (10%, 25%, 50%, 100% buttons)
- ✅ BotUIController (UI-layer execution with human delays)
- ✅ Repository cleanup (54 files archived)

---

## Project Structure & Module Organization
Runtime code sits in `src/`, with `main.py` wiring `core/`, `bot/`, `services/`, `ui/`, `models/`, and optional `ml/` bridges into rugs-rl-bot. Keep strategies in `src/bot/strategies`, widgets in `src/ui/widgets`, and tests mirroring code under `src/tests/`. Docs live in `docs/` (deep dive: `CLAUDE.md`), while replay analytics utilities (`analyze_*.py`, `debug_volatility.py`) remain at the repo root; stash their JSON outputs under `files/` or other gitignored paths to keep commits clean.

## Build, Test & Development Commands
- `./run.sh` – launches the Tkinter replay UI, preferring the rugs-rl-bot venv when available.
- `cd src && python3 main.py` – run the app directly for debugging or breakpointing.
- `python3 analyze_trading_patterns.py` / `python3 analyze_position_duration.py` – regenerate RL datasets beside the script.
- `cd src && python3 -m pytest tests/ -v` – canonical test sweep (≈140 cases).
- `cd src && pytest tests/ --cov=rugs_replay_viewer --cov-report=html` – coverage gate; keep changed modules near their current ratios.
- `cd src && black . && flake8 && mypy core/ bot/ services/` – formatting, linting, and type enforcement expected pre-commit.

## Coding Style & Naming Conventions
Black governs formatting (88 cols, double quotes). Use snake_case for modules/functions, PascalCase for classes, SCREAMING_SNAKE_CASE for constants. Centralize tunables in `config.py`, inject dependencies instead of importing globals, and annotate public interfaces so mypy stays quiet.

## Testing Guidelines
Mirror code structure under `src/tests/` (`core/game_state.py` → `tests/test_core/test_game_state.py`). Write deterministic pytest functions named `test_<behavior>` and tag longer flows with markers from `pytest.ini` (`integration`, `slow`, `ui`). For analytics scripts, add fixture-driven tests (JSON snippets under `tests/test_analysis/`) and assert on structured dicts. Use `src/verify_tests.sh` as a quick readiness checklist before requesting review.

## Commit & Pull Request Guidelines
Git history favors concise, imperative subjects (`Add`, `Update`, `Phase 2:`). Keep summaries ≤72 chars, expand rationale in the body if context is non-obvious, and group changes by feature (UI work separate from analytics). Pull requests should describe intent, link the Rugs.fun issue or task, list the commands you ran, and include fresh UI screenshots whenever layout or styling changes.

## Configuration & Security Notes
Runtime paths and credentials flow through `config.py` plus env vars like `RUGS_RECORDINGS_DIR`, `RUGS_CONFIG_DIR`, and `LOG_LEVEL`; document new knobs there. Never commit raw recordings, ML checkpoints, or API tokens—stash them in `files/` or external storage and update `.gitignore` if needed. Modules under `src/ml/` assume symlinks into `~/Desktop/rugs-rl-bot/`; detect missing models gracefully and log degrads instead of crashing.

