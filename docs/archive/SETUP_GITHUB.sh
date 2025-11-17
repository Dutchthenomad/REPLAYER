#!/bin/bash
# One-command setup for GitHub push (requires sudo for gh install)

echo "=========================================="
echo "GitHub Setup & Push - One Command"
echo "=========================================="
echo ""

# Install GitHub CLI if not present
if ! command -v gh &> /dev/null; then
    echo "Installing GitHub CLI..."
    sudo apt update
    sudo apt install gh -y
    echo "✅ GitHub CLI installed"
else
    echo "✅ GitHub CLI already installed"
fi

# Run the quick push
echo ""
cd /home/nomad/Desktop/REPLAYER
./QUICK_PUSH.sh
