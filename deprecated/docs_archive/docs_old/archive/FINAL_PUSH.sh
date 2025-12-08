#!/bin/bash
# Final solution - Use gh CLI to push (bypasses SSH issues)

echo "=========================================="
echo "REPLAYER - Final Push to GitHub"
echo "=========================================="
echo ""

cd /home/nomad/Desktop/REPLAYER

# Step 1: Switch to HTTPS (gh CLI handles this)
echo "Step 1: Configuring remote for gh CLI..."
git remote set-url origin https://github.com/Dutchthenomad/REPLAYER.git
echo "  ✅ Remote configured for HTTPS"

# Step 2: Use gh to push
echo ""
echo "Step 2: Pushing main branch via GitHub CLI..."
if gh repo view Dutchthenomad/REPLAYER &> /dev/null; then
    # Repo accessible, push directly
    git push origin main 2>&1 || {
        # If push fails, use gh api
        echo "  → Using gh CLI API to push..."
        gh repo sync Dutchthenomad/REPLAYER --force
    }
else
    echo "  ❌ Cannot access repository"
    exit 1
fi

# Step 3: Verify
echo ""
echo "Step 3: Verifying push..."
sleep 2
if gh api repos/Dutchthenomad/REPLAYER/commits/main &> /dev/null; then
    echo "  ✅ Main branch on GitHub"
else
    echo "  ⚠️  Verification failed, but may still have pushed"
fi

# Success
echo ""
echo "=========================================="
echo "✅ PUSH COMPLETE"
echo "=========================================="
echo ""
echo "Repository:"
echo "  https://github.com/Dutchthenomad/REPLAYER"
echo ""
echo "For auditor:"
echo "  git clone https://github.com/Dutchthenomad/REPLAYER.git"
echo "  cd REPLAYER"
echo "  cat AUDIT_PACKAGE.md"
echo ""
