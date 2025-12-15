# Technical Debt Audit - System Design

**Date:** 2025-12-14
**Status:** Approved
**Methodology:** Working Effectively with Legacy Code (Michael Feathers)

---

## Overview

Systematic approach to cleaning up technical debt in the REPLAYER codebase using industry-standard practices, GitHub workflow integration, and test-based verification.

### Problem Statement

The codebase has accumulated technical debt through rapid feature development:
- **State conflicts**: Recording shows "disabled" in logs but "enabled" in UI
- **Dead code**: Unused imports, stale services, broken symlinks
- **Service overlaps**: Multiple recording systems, duplicate noise filtering
- **Infrastructure debt**: venv located in external project (`rugs-rl-bot`)
- **Missing tests**: Code paths without coverage

### Approach: Parallel Track

```
main ─────●────●────●────●────●────●────●────●───▶ (features continue)
           \                        ↑
            \                       │ (cherry-pick urgent fixes)
             \                      │
repair/audit ─●────●────●────●────●─┴───●────●───▶ (cleanup work)
              │    │    │    │    │     │
              │    │    │    │    │     └─ Final merge when stable
              │    │    │    │    └─ Periodic rebase from main
              │    │    │    └─ Issue #N fix
              │    │    └─ Issue #2 fix
              │    └─ Issue #1 fix
              └─ Characterization tests + dependency map
```

---

## GitHub Taxonomy

### Labels

| Label | Color | Description |
|-------|-------|-------------|
| `tech-debt/dead-code` | `#FBCA04` | Unused files, imports, unreachable code |
| `tech-debt/state-conflict` | `#D93F0B` | Multiple sources of truth |
| `tech-debt/duplicate` | `#F9D0C4` | Overlapping services |
| `tech-debt/infrastructure` | `#0E8A16` | venv, symlinks, configs |
| `tech-debt/missing-tests` | `#1D76DB` | Coverage gaps |
| `P0-critical` | `#B60205` | Blocking current work |
| `P1-high` | `#D93F0B` | Affects reliability |
| `P2-medium` | `#FBCA04` | Cleanup, not urgent |
| `P3-low` | `#0E8A16` | Nice to have |
| `component/recording` | `#C5DEF5` | RecorderSink, ReplayEngine |
| `component/websocket` | `#C5DEF5` | WebSocketFeed, EventBus |
| `component/event-bus` | `#C5DEF5` | Event pub/sub system |
| `component/ui-state` | `#C5DEF5` | Controllers, main window |
| `component/infrastructure` | `#C5DEF5` | venv, build, CI |

### Milestones

1. **Tech Debt Audit - Phase 1: Mapping** - Characterization tests + dependency graph
2. **Tech Debt Audit - Phase 2: Foundation** - WebSocket + UI state fixes
3. **Tech Debt Audit - Phase 3: Recording** - Recording system fixes
4. **Tech Debt Audit - Phase 4: Infrastructure** - venv migration, cleanup

---

## Phase 1: Setup & Automated Mapping

**Duration:** 1-2 sessions

### Step 1.1: Create Branch and Infrastructure

```bash
# Create tracking branch
git checkout -b repair/technical-debt-audit

# Labels and milestones created via GitHub CLI (see scripts/setup_audit_infrastructure.sh)
```

### Step 1.2: Run Automated Analysis

```bash
# Install analysis tools
.venv/bin/pip install vulture pydeps radon

# Dead code detection
vulture src/ --min-confidence 80 > reports/dead_code.txt

# Dependency graph
pydeps src/ --max-bacon 3 -o reports/dependency_graph.svg

# Cyclomatic complexity
radon cc src/ -a -s > reports/complexity.txt
```

### Step 1.3: Generate Findings

Each finding becomes a GitHub issue with appropriate labels.

---

## Phase 2: Characterization Tests

**Duration:** 2-3 sessions
**Purpose:** Capture current behavior (even if buggy) as safety net

### Priority Order

1. **B: WebSocket/Event Flow** - Foundation for all features
2. **C: UI State Management** - User-facing behavior
3. **A: Recording System** - Current blocker

### Test Structure

```
tests/test_characterization/
├── __init__.py
├── test_event_flow.py        # WebSocket → EventBus → Controllers → UI
├── test_ui_state.py          # State management, widget sync
└── test_recording_system.py  # Recording state, auto-start behavior
```

### Event Flow Characterization

```python
class TestEventFlowCharacterization:
    """Captures CURRENT behavior - do not 'fix' these tests."""

    def test_websocket_event_reaches_event_bus(self):
        """Document: What events does WebSocketFeed publish?"""

    def test_event_bus_to_controller_flow(self):
        """Document: Which controllers respond to which events?"""

    def test_controller_to_ui_state_sync(self):
        """Document: How does controller state reach UI widgets?"""
```

### UI State Characterization

```python
class TestUIStateCharacterization:
    """Captures current UI state management behavior."""

    def test_recording_var_initialization(self):
        """Document: What is recording_var's initial state?"""

    def test_recording_var_vs_replay_engine_sync(self):
        """Document: Are these two always in sync?"""

    def test_multiple_state_sources(self):
        """Document: List all sources of 'recording enabled' truth."""
```

### Recording System Characterization

```python
class TestRecordingCharacterization:
    """Captures current recording behavior."""

    def test_recording_state_after_launch(self):
        """Document: What is recording state after app launch?"""

    def test_recording_state_after_websocket_connect(self):
        """Document: Does recording auto-start on WS connect?"""

    def test_recording_log_message_conditions(self):
        """Document: When does 'recording disabled' log appear?"""
```

---

## Phase 3: Systematic Repair Workflow

### Single Issue Fix Workflow

```
1. CLAIM ISSUE
   gh issue edit <num> --add-assignee @me

2. CREATE FIX BRANCH (from repair/technical-debt-audit)
   git checkout -b fix/issue-<num>-<short-desc>

3. WRITE FAILING TEST FIRST
   - Test asserts CORRECT behavior
   - Confirm it fails (proves bug exists)

4. IMPLEMENT MINIMAL FIX
   - Only fix what issue describes
   - No drive-by refactoring

5. VERIFY
   - New test passes
   - Characterization tests still pass
   - No regressions

6. PR WITH TEMPLATE
   gh pr create --base repair/technical-debt-audit

7. REVIEW + MERGE
   - Squash merge for clean history
   - Auto-close linked issue
```

### PR Template

```markdown
## Issue
Closes #<number>

## Root Cause
<!-- What was actually wrong? -->

## Fix
<!-- What did you change and why? -->

## Test Coverage
- [ ] New test proves fix works
- [ ] Characterization tests still pass
- [ ] No unrelated changes

## Checklist
- [ ] Single responsibility (one fix only)
- [ ] No drive-by refactoring
- [ ] Documentation updated if needed
```

### Cherry-pick Urgent Fixes

For P0-critical fixes needed in `main` before full audit merges:

```bash
git checkout main
git cherry-pick <commit-sha>
git push origin main
```

---

## Phase 4: Gates & Prevention

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: no-unused-imports
        name: Check unused imports
        entry: .venv/bin/python -m autoflake --check --remove-all-unused-imports
        language: system
        types: [python]

      - id: type-check
        name: Type checking
        entry: .venv/bin/python -m mypy src/ --ignore-missing-imports
        language: system
        types: [python]
        pass_filenames: false

      - id: test-touched-files
        name: Run tests for changed files
        entry: .venv/bin/python scripts/test_touched.py
        language: system
        types: [python]
```

### CI Checks (GitHub Actions)

```yaml
# .github/workflows/quality-gate.yml
name: Quality Gate

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m venv .venv
          .venv/bin/pip install -r requirements.txt
          .venv/bin/pip install -r requirements-dev.txt

      - name: Run tests
        run: .venv/bin/python -m pytest tests/ -v --tb=short

      - name: Dead code check
        run: .venv/bin/vulture src/ --min-confidence 90

      - name: Complexity check
        run: .venv/bin/radon cc src/ -a -nb
```

### Branch Protection Rules

- Require status checks to pass
- Require pull request reviews
- Enforce for administrators

### Documentation Standards

- Tests required (no merge without)
- Type hints on public functions
- Docstrings on classes and public methods
- No new circular imports

---

## Infrastructure Fixes

### Venv Migration

```bash
# Create proper REPLAYER venv
cd /home/nomad/Desktop/REPLAYER
python -m venv .venv

# Export current dependencies
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/pip freeze > requirements-migration.txt

# Install in new location
.venv/bin/pip install -r requirements-migration.txt

# Update run.sh
sed -i 's|/home/nomad/Desktop/rugs-rl-bot/.venv|.venv|g' run.sh

# Verify
.venv/bin/python -m pytest tests/ -v
```

---

## Success Criteria

### Phase 1 Complete When:
- [ ] Repair branch created
- [ ] All labels and milestones exist
- [ ] Automated analysis reports generated
- [ ] Initial issues created from findings

### Phase 2 Complete When:
- [ ] Characterization tests cover event flow
- [ ] Characterization tests cover UI state
- [ ] Characterization tests cover recording
- [ ] All tests document CURRENT behavior

### Phase 3 Complete When:
- [ ] All P0-critical issues resolved
- [ ] All P1-high issues resolved
- [ ] PR workflow established and followed

### Phase 4 Complete When:
- [ ] Pre-commit hooks installed
- [ ] CI workflow active
- [ ] Branch protection enabled
- [ ] Venv migrated to REPLAYER
- [ ] No external project dependencies

---

## References

- Michael Feathers, "Working Effectively with Legacy Code"
- Martin Fowler, "Technical Debt Quadrant"
- GitHub Flow documentation
