# REPLAYER Cleanup & Verification Plan

**Date**: 2025-11-17
**Status**: Pre-commit cleanup before Phase 8

---

## ✅ Step 1: Verify CV-BOILER-PLATE Integration

### Files Copied from CV-BOILER-PLATE-FORK:
1. `browser_automation/automation.py` (8,008 bytes)
2. `browser_automation/persistent_profile.py` (5,033 bytes)
3. `browser_automation/rugs_browser.py` (8,416 bytes)
4. `browser_automation/__init__.py` (0 bytes)

### Integration Status:
- ✅ All imports use `from browser_automation.` prefix (correct)
- ✅ `src/main.py` adds REPLAYER root to `sys.path` (line 16)
- ✅ `rugs_browser.py` uses `.gamebot` profile (shared with CV-BOILER-PLATE)
- ✅ `persistent_profile.py` uses hardcoded `/home/nomad/.cache/` path
- ✅ No broken imports or missing dependencies

### External Dependencies:
- Uses `/home/nomad/.gamebot/chromium_profiles/rugs_fun_phantom/` (40 dirs, pre-configured)
- Uses `/home/nomad/.gamebot/chromium_extensions/phantom/` (45MB Phantom extension)
- Uses `/home/nomad/.cache/ms-playwright/chromium-1187/` (Playwright browser)

**Verdict**: ✅ Integration complete and verified

---

## 🗑️ Step 2: Clean Up Development Artifacts

### Test Scripts to Archive (move to docs/archive/):
1. `test_browser_connection.py` - Browser connection test (4,065 bytes)
2. `test_browser_launch.py` - Browser launch test (2,179 bytes)

### Development Docs to Archive (move to docs/archive/):
1. `BROWSER_CONNECTION_DEBUG_REPORT.md` - Browser debugging session
2. `PHASE_0_TEST_FIXES.md` - Phase 0 test fixes
3. `PHASE_7B_SUMMARY.md` - Phase 7B summary
4. `PHASE_COMPLETION_CHECKLIST.md` - Old checklist
5. `CODE_REVIEW_SETUP.md` - MCP setup docs
6. `MCP_CODE_CHECKER_SETUP.md` - MCP checker docs

### Analysis Scripts (KEEP - production tools):
- `analyze_game_durations.py`
- `analyze_position_duration.py`
- `analyze_spike_timing.py`
- `analyze_trading_patterns.py`
- `analyze_volatility_spikes.py`

### Empty/Unused Directories to Remove:
- `browser_profiles/` - Empty except for NEW profile (should use .gamebot)
- `browser_extensions/` - Now contains Phantom copy (redundant with .gamebot)

**Note**: Keep browser_automation/, it's production code

---

## 📝 Step 3: Update Documentation

### Files to Update:

**1. CLAUDE.md** ✅ Already up-to-date
- Last updated: 2025-11-16
- Includes Phase 8 plan
- Needs: Browser connection completion (Phase 8.5 prerequisite)

**2. AGENTS.md** (needs update)
- Add browser_automation/ to project structure
- Update Phase status (Phase 7B complete, browser connection working)

**3. README.md** (needs update)
- Add browser connection section
- Update installation instructions
- Add .gamebot dependency note

**4. Create: BROWSER_CONNECTION_COMPLETE.md** (new)
- Summary of browser connection fixes
- Integration with .gamebot profiles
- Path resolution fix details

---

## 🧪 Step 4: Run Plugin-Based Testing Suite

### Tests to Run:

**1. MCP Code Checker** (if installed):
```bash
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/mcp-code-checker \
  --project-dir /home/nomad/Desktop/REPLAYER \
  --venv-path /home/nomad/Desktop/rugs-rl-bot/.venv \
  --test-folder src/tests \
  --console-only
```

**2. Full Test Suite**:
```bash
cd /home/nomad/Desktop/REPLAYER/src
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python -m pytest tests/ -v
```

**3. Import Validation**:
```python
# Test browser_automation imports
from browser_automation.rugs_browser import RugsBrowserManager
from browser_automation.automation import connect_phantom_wallet
from browser_automation.persistent_profile import PersistentProfileConfig
```

**4. Browser Connection Test**:
```bash
cd /home/nomad/Desktop/REPLAYER
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python test_browser_launch.py
```

### Expected Results:
- 237/237 tests passing (or 236/237 with 1 known legacy failure)
- No import errors
- Browser launches successfully
- Phantom extension loads without errors

---

## 🔀 Step 5: Git Commit & Push

### Commit Message:
```
Browser Connection System Complete (Phase 8.5 Prerequisite)

✅ Browser connection working with pre-configured .gamebot profile
✅ Phantom extension loaded (no toast errors)
✅ Path resolution fixed (PLAYWRIGHT_BROWSERS_PATH hardcoded)
✅ All browser_automation imports verified
✅ Integration with CV-BOILER-PLATE-FORK complete

Fixes:
- Fixed Playwright browser path (/root/.cache → /home/nomad/.cache)
- Updated rugs_browser.py to use .gamebot profile
- Added manifest.json validation for extension loading
- Added comprehensive error handling to dialog creation
- Cleared Python bytecode cache

Files Modified:
- browser_automation/persistent_profile.py (line 120)
- browser_automation/rugs_browser.py (lines 66-67, 77-93)
- src/ui/main_window.py (lines 1481-1505)

Documentation:
- Cleaned up dev artifacts (archived test scripts and old docs)
- Updated AGENTS.md and README.md
- Created BROWSER_CONNECTION_COMPLETE.md

Status: Ready for Phase 8 - UI-First Bot System

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Git Commands:
```bash
cd /home/nomad/Desktop/REPLAYER
git add .
git status
git commit -m "[commit message above]"
git push origin main
```

---

## 📋 Checklist

**Step 1: Verify Integration**
- [ ] Check all browser_automation imports
- [ ] Verify .gamebot profile usage
- [ ] Confirm no broken dependencies

**Step 2: Clean Up**
- [ ] Archive test scripts to docs/archive/
- [ ] Archive dev docs to docs/archive/
- [ ] Remove empty/redundant directories
- [ ] Clear Python bytecode cache

**Step 3: Update Docs**
- [ ] Update AGENTS.md
- [ ] Update README.md
- [ ] Create BROWSER_CONNECTION_COMPLETE.md
- [ ] Verify CLAUDE.md is current

**Step 4: Run Tests**
- [ ] Run full test suite (237 tests)
- [ ] Run MCP code checker
- [ ] Validate all imports
- [ ] Test browser connection end-to-end

**Step 5: Commit & Push**
- [ ] Review git status
- [ ] Commit with detailed message
- [ ] Push to main branch
- [ ] Verify GitHub updated

**Step 6: Ready for Phase 8**
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Repo clean and organized
- [ ] Phase 8 plan ready to execute

---

## Next Steps After Cleanup

Once cleanup is complete and committed:
1. Run end-to-end test (Option 3 from earlier discussion)
2. Begin Phase 8.1 - Partial Sell Infrastructure
3. OR jump to Phase 8.5 - Playwright Integration (browser connection now working)

---

**Status**: Plan ready - awaiting execution
