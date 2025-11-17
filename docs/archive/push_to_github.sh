#!/bin/bash
# One-command script to push REPLAYER to GitHub for auditor review
# No sudo required

set -e  # Exit on error

echo "=========================================="
echo "REPLAYER - Push to GitHub for Audit"
echo "=========================================="
echo ""

cd /home/nomad/Desktop/REPLAYER

# Step 1: Add GitHub to known_hosts (if not already added)
echo "Step 1: Verifying GitHub SSH host key..."
if ! grep -q "github.com" ~/.ssh/known_hosts 2>/dev/null; then
    echo "  → Adding GitHub to known_hosts..."
    ssh-keyscan -H github.com >> ~/.ssh/known_hosts 2>/dev/null
    echo "  ✅ GitHub host key added"
else
    echo "  ✅ GitHub already in known_hosts"
fi

# Step 2: Verify we're on main branch
echo ""
echo "Step 2: Verifying branch..."
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "  → Switching to main branch..."
    git checkout main
fi
echo "  ✅ On main branch"

# Step 3: Verify remote is SSH
echo ""
echo "Step 3: Verifying remote URL..."
REMOTE_URL=$(git remote get-url origin)
if [[ "$REMOTE_URL" != git@github.com:* ]]; then
    echo "  → Setting remote to SSH..."
    git remote set-url origin git@github.com:Dutchthenomad/REPLAYER.git
fi
echo "  ✅ Remote: $REMOTE_URL"

# Step 4: Push main branch
echo ""
echo "Step 4: Pushing main branch to GitHub..."
git push origin main

# Step 5: Verify tag is pushed
echo ""
echo "Step 5: Verifying release tag..."
if git ls-remote --tags origin | grep -q "v2.0-phase7b"; then
    echo "  ✅ Tag v2.0-phase7b is on GitHub"
else
    echo "  → Pushing tag..."
    git push origin v2.0-phase7b
fi

# Step 6: Show summary
echo ""
echo "=========================================="
echo "✅ SUCCESS - All Changes Pushed to GitHub"
echo "=========================================="
echo ""
echo "GitHub Repository:"
echo "  https://github.com/Dutchthenomad/REPLAYER"
echo ""
echo "Release Tag (for auditor):"
echo "  https://github.com/Dutchthenomad/REPLAYER/releases/tag/v2.0-phase7b"
echo ""
echo "Key Files for Auditor:"
echo "  → AUDIT_PACKAGE.md (start here)"
echo "     https://github.com/Dutchthenomad/REPLAYER/blob/main/AUDIT_PACKAGE.md"
echo ""
echo "  → AUDIT_FILE_LIST.txt"
echo "     https://github.com/Dutchthenomad/REPLAYER/blob/main/AUDIT_FILE_LIST.txt"
echo ""
echo "  → DEVELOPMENT_ROADMAP.md"
echo "     https://github.com/Dutchthenomad/REPLAYER/blob/main/DEVELOPMENT_ROADMAP.md"
echo ""
echo "Commit Details:"
LATEST_COMMIT=$(git log -1 --oneline)
echo "  $LATEST_COMMIT"
echo ""
echo "Files Changed:"
git diff --stat origin/main~6 origin/main | tail -1
echo ""
echo "=========================================="
echo "✅ Ready for Audit"
echo "=========================================="
echo ""
echo "Tell your auditor to clone:"
echo "  git clone https://github.com/Dutchthenomad/REPLAYER.git"
echo "  cd REPLAYER"
echo "  git checkout v2.0-phase7b"
echo "  cat AUDIT_PACKAGE.md"
echo ""
