# REPLAYER Development Setup

## Prerequisites

- **Python**: 3.10+ (3.11 recommended)
- **Git**: 2.30+
- **Chrome**: Latest stable version (for live trading features)
- **Phantom Wallet**: Chrome extension (optional, for live trading)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/Dutchthenomad/REPLAYER.git
cd REPLAYER
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
# Core dependencies
pip install -e .

# Development dependencies (testing, linting)
pip install -e ".[dev]"

# ML features (optional)
pip install -e ".[ml]"
```

### 4. Install Playwright Browsers

```bash
playwright install chromium
```

### 5. Verify Installation

```bash
cd src && python3 -m pytest tests/ -v --tb=short
```

All 737+ tests should pass.

---

## Running the Application

### GUI Mode (Default)

```bash
./run.sh
# or: cd src && python3 main.py
```

### Test Mode

```bash
cd src && python3 -m pytest tests/ -v
```

### With Coverage

```bash
cd src && python3 -m pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html  # View coverage report
```

---

## Project Structure

```
REPLAYER/
├── run.sh              # Launch script
├── src/
│   ├── main.py         # Entry point
│   ├── core/           # Game state, replay, trade management
│   ├── bot/            # Strategies, browser automation
│   ├── ui/             # Tkinter interface
│   ├── models/         # Data models
│   ├── services/       # EventBus, logging
│   ├── sources/        # WebSocket feed
│   ├── ml/             # ML integration (symlinks)
│   └── tests/          # Test suite (737+ tests)
├── browser_automation/ # Chrome CDP integration
├── docs/               # Design documents
└── deprecated/         # Archived code
```

---

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `RUGS_RECORDINGS_DIR` | `~/rugs_recordings` | Recording storage |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `CHROME_DEBUG_PORT` | `9222` | CDP debugging port |

### Recording Symlink

The application expects recordings at `src/rugs_recordings/`. Set up symlink:

```bash
ln -s /path/to/your/recordings src/rugs_recordings
```

Or use the default path:
```bash
mkdir -p ~/rugs_recordings
ln -s ~/rugs_recordings src/rugs_recordings
```

---

## Browser Connection (Live Trading)

### First-Time Setup

1. **Start Chrome with Debugging**:
   ```bash
   google-chrome --remote-debugging-port=9222 --user-data-dir=~/.config/chrome-debug
   ```

2. **Install Phantom Wallet**:
   Navigate to Chrome Web Store and install Phantom.

3. **Connect Wallet**:
   Visit rugs.fun and connect your wallet.

4. **Test Connection**:
   ```bash
   python3 scripts/test_cdp_connection.py
   ```

### Subsequent Sessions

Chrome remembers your wallet connection. Just:
1. Start Chrome with debugging (step 1 above)
2. Launch REPLAYER
3. Use "Connect to Browser" in the UI

---

## ML Features Setup

The `src/ml/` directory uses symlinks to the rugs-rl-bot project for ML predictions.

### If ML symlinks are broken:

```bash
# Check for broken symlinks
find src/ml -xtype l

# Re-create symlinks (adjust path as needed)
ln -sf /path/to/rugs-rl-bot/rugs_bot/sidebet/predictor.py src/ml/predictor.py
ln -sf /path/to/rugs-rl-bot/rugs_bot/sidebet/feature_extractor.py src/ml/feature_extractor.py
```

ML features gracefully degrade if symlinks are broken - the app still works.

---

## Troubleshooting

### Tests Fail with "No module named 'tkinter'"

```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter

# macOS (Homebrew)
brew install python-tk
```

### Playwright Browser Missing

```bash
playwright install chromium
```

### Permission Denied on run.sh

```bash
chmod +x run.sh
```

### ML Features Not Working

```bash
# Install ML dependencies
pip install -e ".[ml]"

# Verify symlinks exist
ls -la src/ml/
```

### Socket.IO Connection Issues

```bash
# Verify python-socketio is installed
pip install python-socketio[client]
```

### Tests Timeout or Hang

```bash
# Run with verbose output
cd src && python3 -m pytest tests/ -v -s --timeout=30

# Run specific test file
python3 -m pytest tests/test_core/test_game_state.py -v
```

---

## Development Tools

### Code Formatting

```bash
# Format code
black src/

# Check without changing
black --check src/
```

### Linting

```bash
flake8 src/ --max-line-length=88 --extend-ignore=E203
```

### Type Checking

```bash
mypy src/core/ src/bot/ src/services/ --ignore-missing-imports
```

### Pre-commit Review (if configured)

```bash
./scripts/pre_commit_review.sh
```

---

## IDE Setup

### VS Code

Recommended extensions:
- Python
- Pylance
- Black Formatter
- GitLens

Settings (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.formatting.provider": "black",
  "editor.formatOnSave": true
}
```

### PyCharm

1. File → Settings → Project → Python Interpreter
2. Select `.venv/bin/python`
3. Enable "Black" as formatter in Tools → External Tools

---

## Getting Help

- **Issues**: https://github.com/Dutchthenomad/REPLAYER/issues
- **Documentation**: See `docs/` folder
- **Architecture**: See `CLAUDE.md`
- **Guidelines**: See `CONTRIBUTING.md`
