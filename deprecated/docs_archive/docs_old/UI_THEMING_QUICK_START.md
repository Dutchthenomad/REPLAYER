# UI Theming Quick Start Guide

**TL;DR**: Use git feature branches to safely implement ttkbootstrap theming. DO NOT fork ttkbootstrap itself.

---

## 5-Minute Quick Start

### 1. Create Feature Branch

```bash
cd /home/nomad/Desktop/REPLAYER
git checkout -b feature/ttkbootstrap-theming
git push -u origin feature/ttkbootstrap-theming
```

### 2. Install ttkbootstrap

```bash
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/pip install ttkbootstrap
```

### 3. Minimal Integration

Edit `src/main.py`:

```python
# Replace this:
import tkinter as tk
self.root = tk.Tk()

# With this:
import ttkbootstrap as ttk
self.root = ttk.Window(themename='cyborg')
```

### 4. Test

```bash
./run.sh
cd src && python3 -m pytest tests/ -v
```

### 5. Commit

```bash
git add .
git commit -m "Add ttkbootstrap theming (cyborg theme)"
git push origin feature/ttkbootstrap-theming
```

---

## Key Commands

### Branch Management

```bash
# Switch to feature branch
git checkout feature/ttkbootstrap-theming

# See your changes
git diff main

# Switch back to main
git checkout main

# Merge when ready
git checkout main
git merge --no-ff feature/ttkbootstrap-theming
```

### Testing Before Commits

```bash
# Always test first
cd src
python3 -m pytest tests/ -v
./run.sh  # Visual check

# Then commit
git add .
git commit -m "Description"
```

### Rollback If Needed

```bash
# Before merge: just switch branches
git checkout main

# After merge: revert
git revert <commit-sha>
```

---

## DO NOT Fork ttkbootstrap

You're using ttkbootstrap as a **library dependency** (via pip), not modifying it.

**Only fork if:**
- You need to fix bugs in the library itself
- You need custom themes beyond the 26 built-ins
- You need to modify library internals

**For 99% of use cases:** Just use `pip install ttkbootstrap` and import it.

---

## Workflow Summary

```
main branch (production)
    │
    └──> feature/ttkbootstrap-theming (your work)
              │
              ├─ commit 1: Setup
              ├─ commit 2: POC
              ├─ commit 3: Theme switcher
              ├─ commit 4-6: Widget upgrades
              ├─ commit 7: Chart colors
              ├─ commit 8: Testing
              │
              └──> [Create PR] ──> [Review] ──> [Merge to main]
```

---

## Resources

- **Full Plan**: `docs/UI_THEMING_VERSION_CONTROL_PLAN.md`
- **Theming Docs**: `external/ttk-bootstrap-work/GUI_THEMING_PACKAGE/`
- **ttkbootstrap GitHub**: https://github.com/israel-dryer/ttkbootstrap
- **ttkbootstrap Docs**: https://ttkbootstrap.readthedocs.io

---

## Estimated Timeline

- Setup: 10 minutes
- Proof of Concept: 15 minutes
- Theme Switcher: 30 minutes
- Widget Upgrades: 1-2 hours
- Chart Colors: 30 minutes
- Testing: 1 hour
- **Total: ~4 hours**

---

**Ready?** Create your feature branch and start with Phase 1!

```bash
git checkout -b feature/ttkbootstrap-theming
```
