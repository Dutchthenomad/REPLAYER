# UI Theming Version Control Plan

**Project**: REPLAYER - Rugs.fun Trading Platform
**Focus**: Safe UI theming with ttkbootstrap
**Date**: November 24, 2025

---

## Executive Summary

This document provides a comprehensive plan for safely implementing UI theming updates using proper version control practices. The goal is to modernize the REPLAYER UI with ttkbootstrap while maintaining code quality and reversibility.

---

## Current State Assessment

### What You Have

1. **REPLAYER Repository** (Main Project)
   - Location: `/home/nomad/Desktop/REPLAYER/`
   - Git Remote: `https://github.com/Dutchthenomad/REPLAYER.git`
   - Status: Production-ready, 237/237 tests passing
   - Current UI: Standard tkinter/ttk

2. **Theming Documentation Package**
   - Location: `/home/nomad/Desktop/REPLAYER/external/ttk-bootstrap=guipack/`
   - Contents: Documentation, examples, demo scripts
   - Purpose: Reference material for ttkbootstrap integration
   - NOT a git repository - just documentation

3. **ttkbootstrap Library** (External Dependency)
   - GitHub: `https://github.com/israel-dryer/ttkbootstrap`
   - Installation: `pip install ttkbootstrap`
   - License: MIT (permissive)
   - Status: Actively maintained

### What You Need

A safe, reversible way to:
1. Implement ttkbootstrap theming in REPLAYER
2. Test different themes (cyborg, darkly, superhero)
3. Iterate on UI improvements
4. Roll back if needed
5. Merge to production when ready

---

## Recommended Approach: Feature Branch Workflow

**Strategy**: Use git feature branches in your REPLAYER repository. DO NOT fork ttkbootstrap (you're using it as a library, not modifying it).

### Why This Approach?

✅ **Pros:**
- Simple and lightweight
- Standard git workflow
- Easy to review changes
- Simple rollback (just switch branches)
- Works with your existing repository

❌ **Why NOT fork ttkbootstrap:**
- You're using it as a dependency (via pip)
- No need to modify the library itself
- MIT license allows commercial use as-is
- Forking adds unnecessary complexity

---

## Implementation Plan

### Phase 1: Setup (10 minutes)

#### 1.1 Create Feature Branch

```bash
cd /home/nomad/Desktop/REPLAYER

# Ensure you're on main and up to date
git checkout main
git pull origin main

# Create feature branch for theming work
git checkout -b feature/ttkbootstrap-theming

# Verify you're on the new branch
git branch --show-current
```

#### 1.2 Install ttkbootstrap

```bash
# Install in the rugs-rl-bot venv (REPLAYER uses this)
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/pip install ttkbootstrap

# OR if using system Python
pip install ttkbootstrap

# Verify installation
python3 -c "import ttkbootstrap; print(ttkbootstrap.__version__)"
```

#### 1.3 Document Installation

```bash
# Update requirements (if you have one)
echo "ttkbootstrap>=1.10.1" >> requirements.txt

# Or document in CLAUDE.md
```

#### 1.4 Create Checkpoint Commit

```bash
git add requirements.txt
git commit -m "Phase 1: Setup ttkbootstrap dependency

- Install ttkbootstrap library
- Update requirements
- Ready for UI integration

Files changed: 1 file (1 insertion)
Tests: 237/237 passing

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push feature branch to remote
git push -u origin feature/ttkbootstrap-theming
```

### Phase 2: Proof of Concept (15 minutes)

#### 2.1 Minimal Integration

Edit `src/main.py` to use ttkbootstrap:

```python
# OLD (Line ~30):
import tkinter as tk
self.root = tk.Tk()

# NEW:
import ttkbootstrap as ttk
self.root = ttk.Window(themename='cyborg')
```

#### 2.2 Test Each Theme

```bash
# Test with cyborg theme (gaming style)
./run.sh

# Edit main.py to test other themes:
# themename='darkly'  # Professional dark
# themename='superhero'  # Bold colorful

# Run tests to verify nothing broke
cd src && python3 -m pytest tests/ -v
```

#### 2.3 Commit POC

```bash
git add src/main.py
git commit -m "Phase 2: Proof of concept - ttkbootstrap integration

- Replace tk.Tk() with ttk.Window(themename='cyborg')
- Test successful with cyborg theme
- All 237 tests still passing
- No functional changes, only visual

Files changed: 1 file (2 insertions, 1 deletion)
Tests: 237/237 passing

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin feature/ttkbootstrap-theming
```

### Phase 3: Theme Switcher (30 minutes)

#### 3.1 Add Theme Menu

Update `src/ui/main_window.py`:

```python
def _create_menu_bar(self):
    # ... existing menu code ...

    # Add View menu with theme switcher
    view_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="View", menu=view_menu)

    theme_menu = tk.Menu(view_menu, tearoff=0)
    view_menu.add_cascade(label="Theme", menu=theme_menu)

    themes = ['cyborg', 'darkly', 'superhero', 'cosmo', 'flatly']
    for theme in themes:
        theme_menu.add_command(
            label=theme.title(),
            command=lambda t=theme: self._change_theme(t)
        )

def _change_theme(self, theme_name):
    """Switch UI theme"""
    try:
        self.root.style.theme_use(theme_name)
        self._save_theme_preference(theme_name)
    except Exception as e:
        print(f"Failed to switch theme: {e}")
```

#### 3.2 Add Theme Persistence

```python
# src/config.py
def save_theme_preference(theme_name):
    """Save theme to config file"""
    config_path = os.path.expanduser('~/.config/replayer/ui_config.json')
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)

    config['theme'] = theme_name

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

def load_theme_preference():
    """Load saved theme"""
    config_path = os.path.expanduser('~/.config/replayer/ui_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config.get('theme', 'cyborg')
    return 'cyborg'
```

#### 3.3 Commit Theme Switcher

```bash
git add src/ui/main_window.py src/config.py
git commit -m "Phase 3: Add theme switcher with persistence

- Add View → Theme menu with 5 themes
- Add theme_use() switching functionality
- Add JSON config persistence (~/.config/replayer/ui_config.json)
- Theme preference survives app restarts

Files changed: 2 files (45 insertions)
Tests: 237/237 passing

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin feature/ttkbootstrap-theming
```

### Phase 4: Progressive Widget Upgrades (1-2 hours)

#### 4.1 Upgrade One Panel at a Time

**Strategy**: Upgrade widgets incrementally, test after each change.

```bash
# Example: Start with StatusPanel
# src/ui/panels.py

# OLD:
import tkinter as tk
label = tk.Label(parent, text="Status")

# NEW:
import tkinter.ttk as ttk
label = ttk.Label(parent, text="Status")

# Test this panel specifically
./run.sh  # Visual inspection
pytest tests/test_ui/test_panels.py -v
```

#### 4.2 Commit After Each Panel

```bash
git add src/ui/panels.py
git commit -m "Phase 4.1: Upgrade StatusPanel to ttk widgets

- Replace tk.Label with ttk.Label
- Replace tk.Button with ttk.Button
- Visual appearance now matches theme
- No functional changes

Files changed: 1 file (8 insertions, 8 deletions)
Tests: 237/237 passing

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin feature/ttkbootstrap-theming
```

Repeat for:
- TradingPanel
- BotPanel
- Other panels

### Phase 5: Chart Color Coordination (30 minutes)

#### 5.1 Theme-Aware Chart Colors

```python
# src/ui/widgets/chart.py

def _get_theme_colors(self):
    """Get colors from current theme"""
    style = ttk.Style()
    theme_colors = {
        'cyborg': {
            'bg': '#060606',
            'line': '#2A9FD6',
            'grid': '#1E1E1E',
            'text': '#77B7D7'
        },
        'darkly': {
            'bg': '#222222',
            'line': '#375A7F',
            'grid': '#333333',
            'text': '#AAAAAA'
        },
        # ... other themes
    }

    current_theme = style.theme_use()
    return theme_colors.get(current_theme, theme_colors['cyborg'])
```

#### 5.2 Commit Chart Updates

```bash
git add src/ui/widgets/chart.py
git commit -m "Phase 5: Add theme-aware chart colors

- Chart colors now match selected theme
- Maintains high contrast for readability
- Tested with cyborg, darkly, superhero themes

Files changed: 1 file (25 insertions, 5 deletions)
Tests: 237/237 passing

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin feature/ttkbootstrap-theming
```

### Phase 6: Testing & Validation (1 hour)

#### 6.1 Comprehensive Testing

```bash
# Run full test suite
cd src && python3 -m pytest tests/ -v

# Visual testing with each theme
./run.sh  # Switch themes via menu

# Performance testing
# - Load a recorded game
# - Play at 50Hz
# - Monitor CPU usage
# - Verify no frame drops
```

#### 6.2 Create Testing Checklist

Create `docs/UI_TESTING_CHECKLIST.md`:

```markdown
## UI Testing Checklist

### Functional Tests
- [ ] All 237 tests passing
- [ ] Theme switcher works
- [ ] Theme persists across restarts
- [ ] All panels render correctly
- [ ] Chart colors match theme
- [ ] Button clicks work
- [ ] Keyboard shortcuts work

### Visual Tests (Each Theme)
For cyborg, darkly, superhero:
- [ ] Text readable on all backgrounds
- [ ] Contrast ratios acceptable (WCAG AA)
- [ ] Charts visible and clear
- [ ] No visual glitches
- [ ] Colors cohesive throughout

### Performance Tests
- [ ] 50Hz replay smooth (no frame drops)
- [ ] Live WebSocket feed responsive
- [ ] Theme switching instant (<100ms)
- [ ] Bot execution unaffected
- [ ] Memory usage stable
```

#### 6.3 Commit Testing Documentation

```bash
git add docs/UI_TESTING_CHECKLIST.md
git commit -m "Phase 6: Add UI testing checklist

- Document functional tests
- Document visual tests per theme
- Document performance requirements
- Ready for final validation

Files changed: 1 file (40 insertions)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin feature/ttkbootstrap-theming
```

### Phase 7: Pull Request & Merge (30 minutes)

#### 7.1 Final Review

```bash
# Review all changes on feature branch
git log --oneline feature/ttkbootstrap-theming ^main

# Check diff from main
git diff main...feature/ttkbootstrap-theming

# Verify branch is up to date with main
git fetch origin
git merge origin/main  # Resolve conflicts if any
```

#### 7.2 Create Pull Request

```bash
# On GitHub: Create Pull Request
# Title: "Phase 1-6: ttkbootstrap UI Theming Implementation"
# Description:
```

**Pull Request Template:**

```markdown
## Summary
Complete implementation of ttkbootstrap theming for professional UI upgrade.

## Changes
- ✅ Phase 1: Setup ttkbootstrap dependency
- ✅ Phase 2: Proof of concept integration
- ✅ Phase 3: Theme switcher with persistence
- ✅ Phase 4: Progressive widget upgrades
- ✅ Phase 5: Chart color coordination
- ✅ Phase 6: Testing & validation

## Testing
- All 237 tests passing
- Visual testing complete (cyborg, darkly, superhero)
- Performance validated (50Hz smooth)
- User acceptance testing complete

## Files Changed
- `src/main.py` - Root window initialization
- `src/ui/main_window.py` - Theme menu and switcher
- `src/ui/panels.py` - Widget upgrades
- `src/ui/widgets/chart.py` - Theme-aware colors
- `src/config.py` - Theme persistence
- `requirements.txt` - Add ttkbootstrap dependency
- `docs/UI_TESTING_CHECKLIST.md` - Testing documentation

## Screenshots
[Add before/after screenshots]

## Rollback Plan
If issues arise post-merge:
```bash
git revert <merge-commit-sha>
```

## Recommended Theme
**cyborg** - Best for HUD-style gaming UI
```

#### 7.3 Merge to Main

```bash
# After PR approval:
git checkout main
git merge --no-ff feature/ttkbootstrap-theming
git push origin main

# Tag the release
git tag -a v2.0.0-theming -m "UI Theming Update - ttkbootstrap integration"
git push origin v2.0.0-theming
```

#### 7.4 Cleanup

```bash
# Delete feature branch (optional)
git branch -d feature/ttkbootstrap-theming
git push origin --delete feature/ttkbootstrap-theming
```

---

## Alternative: Experimental Branch for Testing

If you want to test more aggressively without affecting main:

```bash
# Create experimental branch
git checkout -b experimental/ui-themes

# Try radical changes
# Break things
# Experiment freely

# If successful, create clean feature branch:
git checkout main
git checkout -b feature/ttkbootstrap-theming
# Cherry-pick good commits from experimental branch
git cherry-pick <commit-sha>
```

---

## Rollback Strategies

### Strategy 1: Branch Switching (Pre-Merge)

```bash
# If theming branch has issues, just switch back
git checkout main
./run.sh  # Back to original UI
```

### Strategy 2: Revert Commits (Post-Merge)

```bash
# Revert specific commit
git revert <commit-sha>

# Revert entire feature
git revert -m 1 <merge-commit-sha>
```

### Strategy 3: Emergency Rollback

```bash
# Nuclear option - reset to previous state
git reset --hard <pre-theming-commit-sha>
# WARNING: Only use if no other work has been committed
```

---

## If You Need to Fork ttkbootstrap (Advanced)

**Only do this if you need to modify the ttkbootstrap library itself** (unlikely).

### When to Fork

- Custom theme creation beyond 26 built-ins
- Library bug fixes
- Performance optimizations
- Custom widget implementations

### How to Fork

```bash
# 1. Fork on GitHub
# Go to https://github.com/israel-dryer/ttkbootstrap
# Click "Fork" button
# Creates: https://github.com/Dutchthenomad/ttkbootstrap

# 2. Clone your fork
cd ~/Desktop
git clone https://github.com/Dutchthenomad/ttkbootstrap.git
cd ttkbootstrap

# 3. Add upstream remote
git remote add upstream https://github.com/israel-dryer/ttkbootstrap.git

# 4. Create feature branch
git checkout -b feature/custom-rugs-theme

# 5. Make changes, test, commit
# ... edit code ...
git add .
git commit -m "Add custom Rugs.fun theme"

# 6. Install from your fork
cd /home/nomad/Desktop/REPLAYER
pip uninstall ttkbootstrap
pip install -e ~/Desktop/ttkbootstrap  # Editable install

# 7. Keep fork updated
cd ~/Desktop/ttkbootstrap
git fetch upstream
git merge upstream/master
```

---

## Best Practices

### Commit Messages

Use descriptive commit messages following this pattern:

```
Phase X: Brief description (50 chars)

- Bullet point change 1
- Bullet point change 2
- Bullet point change 3

Files changed: X files (Y insertions, Z deletions)
Tests: 237/237 passing

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Testing Before Commits

```bash
# Always test before committing
cd src
python3 -m pytest tests/ -v  # All tests
./run.sh  # Visual inspection

# Then commit
git add .
git commit -m "..."
```

### Small, Atomic Commits

- One logical change per commit
- Easy to review
- Easy to revert if needed
- Clear history

### Branch Naming Convention

- `feature/` - New features
- `bugfix/` - Bug fixes
- `experimental/` - Radical experiments
- `hotfix/` - Emergency production fixes

---

## Timeline Estimate

| Phase | Task | Time | Commits |
|-------|------|------|---------|
| 1 | Setup | 10 min | 1 |
| 2 | Proof of Concept | 15 min | 1 |
| 3 | Theme Switcher | 30 min | 1 |
| 4 | Widget Upgrades | 1-2 hours | 3-5 |
| 5 | Chart Colors | 30 min | 1 |
| 6 | Testing | 1 hour | 1 |
| 7 | PR & Merge | 30 min | 1 |
| **TOTAL** | **~4 hours** | **9-12 commits** |

---

## Success Criteria

### Must Have
- ✅ All 237 tests passing
- ✅ Theme switcher functional
- ✅ Theme persists across sessions
- ✅ Performance maintained (50Hz)
- ✅ Rollback plan documented

### Should Have
- ✅ 3+ themes available
- ✅ Chart colors match theme
- ✅ Visual consistency across panels
- ✅ User documentation updated

### Nice to Have
- Custom Rugs.fun branded theme
- Theme preview in menu
- Keyboard shortcut for theme switching
- Accessibility audit (contrast ratios)

---

## Resources

### Documentation
- ttkbootstrap docs: https://ttkbootstrap.readthedocs.io
- Git branching guide: https://git-scm.com/book/en/v2/Git-Branching-Branching-Workflows

### Examples in Package
- `/home/nomad/Desktop/REPLAYER/external/ttk-bootstrap-work/GUI_THEMING_PACKAGE/examples/`
- `basic_integration.py` - Minimal example
- `theme_switcher.py` - Theme switching
- `chart_colors.py` - Chart coordination

### Testing Scripts
- `scripts/theme_preview.py` - Live theme demo
- Run: `python3 scripts/theme_preview.py`

---

## Next Steps

1. **Review this plan** - Understand the workflow
2. **Create feature branch** - `git checkout -b feature/ttkbootstrap-theming`
3. **Start with Phase 1** - Setup and POC
4. **Commit frequently** - Small, atomic commits
5. **Test continuously** - Run tests before each commit
6. **Document changes** - Update CLAUDE.md as you go
7. **Create PR when ready** - Get review before merge

---

**Questions?** Review the GUI_THEMING_PACKAGE documentation at:
`/home/nomad/Desktop/REPLAYER/external/ttk-bootstrap-work/GUI_THEMING_PACKAGE/`

**Ready to start?** Begin with Phase 1: Setup!

---

**Document Version:** 1.0
**Created:** November 24, 2025
**Last Updated:** November 24, 2025
**Author:** Claude (Anthropic)
