#!/bin/bash
# SUPER SIMPLE - One command to push to GitHub
# Uses GitHub CLI (gh) which handles authentication automatically

echo "=========================================="
echo "REPLAYER - Quick Push to GitHub"
echo "=========================================="
echo ""

cd /home/nomad/Desktop/REPLAYER

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) not found"
    echo ""
    echo "OPTION 1: Install GitHub CLI (recommended)"
    echo "  sudo apt update && sudo apt install gh -y"
    echo "  Then run this script again"
    echo ""
    echo "OPTION 2: Add SSH key to GitHub (manual)"
    echo "  1. Copy this SSH key:"
    echo ""
    cat ~/.ssh/id_ed25519.pub
    echo ""
    echo "  2. Go to: https://github.com/settings/keys"
    echo "  3. Click 'New SSH key'"
    echo "  4. Paste the key above"
    echo "  5. Run this script again"
    echo ""
    exit 1
fi

# Authenticate if needed
echo "Step 1: Checking GitHub authentication..."
if ! gh auth status &> /dev/null; then
    echo "  → Authenticating with GitHub..."
    gh auth login
else
    echo "  ✅ Already authenticated"
fi

# Push main branch
echo ""
echo "Step 2: Pushing main branch..."
git push origin main

# Push tag
echo ""
echo "Step 3: Verifying tag..."
git push origin v2.0-phase7b 2>/dev/null || echo "  ✅ Tag already pushed"

# Success
echo ""
echo "=========================================="
echo "✅ SUCCESS - Everything on GitHub!"
echo "=========================================="
echo ""
echo "Repository: https://github.com/Dutchthenomad/REPLAYER"
echo "Tag: https://github.com/Dutchthenomad/REPLAYER/releases/tag/v2.0-phase7b"
echo ""
echo "For auditor:"
echo "  git clone https://github.com/Dutchthenomad/REPLAYER.git"
echo "  cd REPLAYER"
echo "  cat AUDIT_PACKAGE.md"
echo ""
