#!/bin/bash
# Launch Rugs Replay Viewer

echo "🚀 Starting Rugs Replay Viewer"
echo "=============================="

# Use rugs-rl-bot venv for ML dependencies compatibility
VENV_PYTHON="/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3"

cd "$(dirname "$0")/src"

if [ -x "$VENV_PYTHON" ]; then
    echo "Using rugs-rl-bot venv Python"
    $VENV_PYTHON main.py
else
    echo "⚠️  rugs-rl-bot venv not found, using system python3"
    python3 main.py
fi
