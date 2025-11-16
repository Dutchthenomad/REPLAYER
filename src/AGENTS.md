# Repository Guidelines

## Project Structure & Module Organization
Runtime code lives in `src/`, with `main.py` orchestrating modules under `core/`, `bot/`, `services/`, `ui/`, `models/`, and optional `ml/`. Strategies belong in `bot/strategies`, widgets in `ui/widgets`, and reusable helpers under `utils/`. Mirror code in `tests/` (for example, `core/game_state.py` → `tests/test_core/test_game_state.py`). Stand-alone analytics live beside the repo root (e.g., `analyze_trading_patterns.py`) and should drop outputs in `files/` or another gitignored path. Long-form docs sit in `docs/` (see `docs/CLAUDE.md`), while `config.py` consolidates tunables pulled from env vars like `RUGS_RECORDINGS_DIR`.

## Build, Test, and Development Commands
- `./run.sh` – launch the Tkinter replay UI, preferring the rugs-rl-bot virtualenv.
- `cd src && python3 main.py` – run the app directly for debugging or breakpointing.
- `python3 analyze_trading_patterns.py` (or other `analyze_*.py`) – regenerate RL datasets alongside each script.
- `cd src && python3 -m pytest tests/ -v` – canonical test sweep (~140 tests).
- `cd src && pytest tests/ --cov=rugs_replay_viewer --cov-report=html` – enforce coverage parity.
- `cd src && black . && flake8 && mypy core/ bot/ services/` – formatting, linting, and type checks expected pre-commit.

## Coding Style & Naming Conventions
Code is formatted with Black (88 cols, double quotes). Use snake_case for modules/functions, PascalCase for classes, and SCREAMING_SNAKE_CASE for constants. Keep tunables centralized in `config.py`, inject dependencies instead of importing globals, and annotate public interfaces so mypy remains quiet. Favor descriptive filenames (e.g., `debug_volatility.py`) and keep runtime assets outside `src/` unless required by the Tkinter UI.

## Testing Guidelines
Pytest powers the suite; tests reside under `src/tests/` mirroring their source paths. Name tests `test_<behavior>` and tag longer flows using markers defined in `pytest.ini` (`integration`, `slow`, `ui`). For analytics scripts, back tests with fixture JSON stored under `tests/test_analysis/` and assert on structured dicts rather than printouts. Run coverage periodically with the HTML report to catch regressions before review.

## Commit & Pull Request Guidelines
Commits use short, imperative subjects (e.g., `Add volatility analyzer`) under 72 chars, with optional bodies explaining context. Group work by feature (UI tweaks separate from analytics). Pull requests should describe intent, link the Rugs.fun issue or task, list verification commands (tests, linters, analytics), and include fresh UI screenshots when layouts shift. Keep generated outputs out of version control and document new configuration knobs in `config.py`.

## Security & Configuration Tips
Runtime paths and credentials flow through `config.py` plus env vars such as `RUGS_CONFIG_DIR` and `LOG_LEVEL`. Never commit recordings, ML checkpoints, or API tokens—store them under `files/` or external storage and update `.gitignore` when adding new artifacts. Modules under `src/ml/` rely on symlinks into `~/Desktop/rugs-rl-bot/`; detect missing models gracefully and log degradations instead of crashing.
