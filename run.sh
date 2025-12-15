#!/bin/bash
# Launch Rugs Replay Viewer

echo "🚀 Starting Rugs Replay Viewer"
echo "=============================="

# Get script directory (robust method)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use local REPLAYER venv
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"

cd "$SCRIPT_DIR/src"

if [ -x "$VENV_PYTHON" ]; then
    echo "Using REPLAYER venv Python"
    $VENV_PYTHON main.py
else
    echo "⚠️  .venv not found at: $SCRIPT_DIR/.venv"
    echo "Run: cd $SCRIPT_DIR && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi
