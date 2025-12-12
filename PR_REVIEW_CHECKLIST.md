# PR Review Checklist - Modular Refactoring

**Branch**: `claude/refactor-modular-system-MchkM`
**Target**: `main`

---

## 🚨 CRITICAL: This PR Cannot Be Merged Without Completing This Checklist

This refactoring involves:
- **5 file deletions** (including 1,433 LOC duplicate main window)
- **1 file rename** (critical import path change)
- **4 file modifications** (import updates)
- **1 directory removal** (unused widgets)

**Total Impact**: -2,504 LOC across 10 files

---

## Pre-Review: Automated Checks

### Run Verification Script

Before reviewing, run this automated verification:

```bash
cd /home/user/REPLAYER
./scripts/verify_refactoring.sh
```

**If script doesn't exist**, run these commands manually:

```bash
cd /home/user/REPLAYER

echo "=== Checking for broken imports ==="
python3 << 'EOF'
import sys
sys.path.insert(0, 'src')
try:
    import main
    import ui.main_window
    from services.ui_dispatcher import TkDispatcher
    import bot.browser_executor
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)
EOF

echo ""
echo "=== Searching for deleted file references ==="
deleted_files=(
    "modern_main_window"
    "ModernMainWindow"
    "browser_actions.py"
    "browser_state_reader.py"
    "ui.components"
    "ui/components"
    "ui.tk_dispatcher"
)

for pattern in "${deleted_files[@]}"; do
    echo "Checking: $pattern"
    if grep -r "$pattern" src/ --include="*.py" 2>/dev/null | grep -v "REFACTORING_CHANGELOG\|PR_REVIEW"; then
        echo "❌ FOUND REFERENCE TO DELETED CODE: $pattern"
    else
        echo "✅ No references to $pattern"
    fi
done

echo ""
echo "=== Test suite verification ==="
cd src
if command -v pytest &> /dev/null; then
    python3 -m pytest tests/ -v --tb=short -x 2>&1 | tail -20
    if [ $? -eq 0 ]; then
        echo "✅ Tests passed"
    else
        echo "❌ Tests failed"
    fi
else
    echo "⚠️ pytest not installed, skipping test verification"
fi
```

---

## Manual Review Checklist

### 1. Code Review

- [ ] **Review REFACTORING_CHANGELOG.md**
  - Understand all file changes
  - Verify impact assessment is accurate

- [ ] **Verify Deleted Files Were Actually Dead Code**
  - [ ] `browser_actions.py` - Confirm not imported anywhere
  - [ ] `browser_state_reader.py` - Confirm not imported anywhere
  - [ ] `modern_main_window.py` - Confirm was outdated duplicate
  - [ ] `ui/components/` directory - Confirm not used

- [ ] **Review File Rename**
  - [ ] `ui/tk_dispatcher.py` → `services/ui_dispatcher.py`
  - [ ] Verify all imports updated correctly
  - [ ] Check `main_window.py` uses new path
  - [ ] Check `test_dispatcher.py` uses new path

- [ ] **Review Modified Files**
  - [ ] `main.py` - Simplified window logic looks correct
  - [ ] `ui/main_window.py` - Import change only
  - [ ] `bot/browser_executor.py` - Docstring update only
  - [ ] `tests/test_ui/test_dispatcher.py` - Import change only

### 2. Functional Testing

- [ ] **Application Launch**
  ```bash
  ./run.sh
  # Expected: Application opens without errors
  ```

- [ ] **Load Recording**
  - Open application
  - File → Load Game
  - Select a `.jsonl` recording
  - Verify playback works

- [ ] **Bot Controls**
  - Toggle bot on/off
  - Open bot configuration panel
  - Verify settings persist

- [ ] **Browser Menu**
  - Browser → Connect to Browser
  - Verify dialog opens (even if connection fails)

- [ ] **Theme Switching**
  - Try different ttkbootstrap themes
  - Verify theme persists across restarts

### 3. Import Path Verification

Run this search to find any missed import updates:

```bash
cd /home/user/REPLAYER

# Should return NO results (or only from changelog/docs)
grep -r "from ui\.tk_dispatcher" src/ --include="*.py" | grep -v "CHANGELOG\|PR_REVIEW"
grep -r "from ui import tk_dispatcher" src/ --include="*.py" | grep -v "CHANGELOG\|PR_REVIEW"
grep -r "import ui\.tk_dispatcher" src/ --include="*.py" | grep -v "CHANGELOG\|PR_REVIEW"
```

**Expected**: No results (all imports updated to `services.ui_dispatcher`)

- [ ] Verified no old import paths found

### 4. Documentation Review

- [ ] **CLAUDE.md Updates Needed?**
  ```bash
  grep -n "modern_main_window\|--modern\|--standard\|ui/components" CLAUDE.md
  ```
  - [ ] Update file organization section if references found
  - [ ] Update command examples if flags mentioned

- [ ] **README.md Updates Needed?**
  ```bash
  grep -n "modern_main_window\|--modern\|--standard" README.md
  ```
  - [ ] Update usage examples if found

- [ ] **docs/ Updates Needed?**
  ```bash
  grep -r "browser_actions\.py\|browser_state_reader\.py\|modern_main_window" docs/
  ```
  - [ ] Update any references found

### 5. Test Suite

- [ ] **Run Full Test Suite**
  ```bash
  cd src
  python3 -m pytest tests/ -v
  ```
  - [ ] All tests pass
  - [ ] No import errors
  - [ ] No deprecation warnings related to refactoring

- [ ] **Run Specific Test Files**
  ```bash
  # Test dispatcher specifically
  python3 -m pytest tests/test_ui/test_dispatcher.py -v

  # Test bot system
  python3 -m pytest tests/test_bot/ -v

  # Test core system
  python3 -m pytest tests/test_core/ -v
  ```

### 6. Git Hygiene

- [ ] **Commit Message Quality**
  - Descriptive commit message
  - Lists all changes
  - References issue/task if applicable

- [ ] **No Unintended Changes**
  ```bash
  git diff main...claude/refactor-modular-system-MchkM
  ```
  - [ ] Only expected files changed
  - [ ] No debug code left in
  - [ ] No commented-out code

- [ ] **Branch is Up to Date**
  ```bash
  git fetch origin main
  git merge-base --is-ancestor origin/main HEAD
  ```
  - [ ] Branch includes latest main changes

---

## Risk Assessment

### High Risk Changes (Review Carefully)

1. **Deleted `modern_main_window.py`** (1,433 LOC)
   - Risk: If any code still references this, application will crash
   - Mitigation: Verified removed from `main.py`, search confirms no imports

2. **Renamed `ui/tk_dispatcher.py`**
   - Risk: Missed import updates will cause ImportError
   - Mitigation: Only 2 files import it, both updated

3. **Removed command-line flags** (`--modern`, `--standard`)
   - Risk: Scripts or CI/CD using these flags will fail
   - Mitigation: Check shell scripts and CI configs

### Medium Risk Changes

4. **Deleted reference docs** (`browser_actions.py`, `browser_state_reader.py`)
   - Risk: Developers may have referenced these for API examples
   - Mitigation: Functionality still exists in `browser_executor.py`, just not as separate files

### Low Risk Changes

5. **Removed `ui/components/` directory**
   - Risk: Very low - not imported anywhere
   - Mitigation: Confirmed no imports found

---

## Approval Criteria

### Must Have (Blocking)

- [x] REFACTORING_CHANGELOG.md reviewed and accurate
- [ ] All automated checks pass (imports, tests)
- [ ] Application launches without errors
- [ ] No broken references to deleted files
- [ ] All import paths updated correctly

### Should Have (Strongly Recommended)

- [ ] Documentation updated (CLAUDE.md, README.md)
- [ ] Manual functional testing completed
- [ ] Test suite passes (if pytest available)

### Nice to Have

- [ ] Performance comparison (app launch time, memory usage)
- [ ] Code review by second developer

---

## Reviewer Sign-Off

**Reviewer Name**: _____________________

**Date**: _____________________

### Verification Completed

- [ ] Automated checks passed
- [ ] Manual testing completed
- [ ] Documentation reviewed
- [ ] Risk assessment reviewed
- [ ] Approval criteria met

### Approval Decision

- [ ] ✅ **APPROVED** - Safe to merge
- [ ] 🟡 **APPROVED WITH COMMENTS** - Merge after addressing comments below
- [ ] ❌ **CHANGES REQUESTED** - Do not merge, see comments below

**Comments**:
```
[Add any review comments here]
```

---

## Post-Merge Actions

After merging to `main`:

- [ ] Delete refactoring branch
  ```bash
  git branch -d claude/refactor-modular-system-MchkM
  git push origin --delete claude/refactor-modular-system-MchkM
  ```

- [ ] Tag release (optional)
  ```bash
  git tag -a v0.9.5-refactor-phase1 -m "Phase 1: Removed 2,504 LOC of dead code"
  git push origin v0.9.5-refactor-phase1
  ```

- [ ] Update CLAUDE.md with new file structure

- [ ] Archive this changelog
  ```bash
  mv REFACTORING_CHANGELOG.md docs/archive/REFACTORING_CHANGELOG_PHASE1.md
  mv PR_REVIEW_CHECKLIST.md docs/archive/PR_REVIEW_CHECKLIST_PHASE1.md
  ```

---

**Last Updated**: 2025-12-12
**Status**: 🔴 **PENDING REVIEW**
