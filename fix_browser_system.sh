#!/bin/bash
# Complete Browser Connection System Fix
# Based on comprehensive audit findings

set -e  # Exit on error

echo "🔧 Fixing REPLAYER Browser Connection System..."
echo "================================================"

cd /home/nomad/Desktop/REPLAYER

# 1. Create required directories
echo ""
echo "📁 Step 1: Creating browser directories..."
mkdir -p browser_profiles/rugs_fun_phantom
mkdir -p browser_extensions/phantom
echo "✅ Created:"
echo "   - browser_profiles/rugs_fun_phantom"
echo "   - browser_extensions/phantom"

# 2. Update rugs_browser.py paths
echo ""
echo "🛠️  Step 2: Updating browser paths in rugs_browser.py..."
sed -i 's|Path.home() / "\.gamebot"|Path.home() / "Desktop/REPLAYER"|g' browser_automation/rugs_browser.py
echo "✅ Updated paths to use REPLAYER directory structure"

# 3. Install Playwright browsers
echo ""
echo "📦 Step 3: Installing Playwright browsers..."
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python -m playwright install chromium
echo "✅ Chromium browser installed"

# 4. Verify imports work
echo ""
echo "🔍 Step 4: Verifying imports..."
cd src
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python -c "
try:
    from browser_automation.rugs_browser import RugsBrowserManager
    print('✅ RugsBrowserManager import successful')
except Exception as e:
    print(f'❌ Import failed: {e}')
    exit(1)
"

# 5. Test directories exist
echo ""
echo "🔍 Step 5: Verifying directory structure..."
cd /home/nomad/Desktop/REPLAYER
if [ -d "browser_profiles/rugs_fun_phantom" ]; then
    echo "✅ browser_profiles/rugs_fun_phantom exists"
else
    echo "❌ browser_profiles/rugs_fun_phantom missing"
fi

if [ -d "browser_extensions" ]; then
    echo "✅ browser_extensions exists"
else
    echo "❌ browser_extensions missing"
fi

# 6. Summary
echo ""
echo "================================================"
echo "✅ Browser Connection System Fixed!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Run: cd ~/Desktop/REPLAYER && ./run.sh"
echo "2. Click: Browser → Connect Browser..."
echo "3. Click 'Connect Browser' button in dialog"
echo ""
echo "The browser should now launch successfully!"
