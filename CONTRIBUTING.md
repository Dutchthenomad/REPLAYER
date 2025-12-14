# Contributing to REPLAYER

## Development Workflow

### 1. Issue-First Development

All work starts with a GitHub Issue:
```bash
gh issue view <number>           # Read requirements
gh issue create                  # Create new issue
```

**Every task** must have an issue before starting work.

### 2. Branch Naming Convention

```
<type>/issue-<number>-<description>
```

**Types**:
| Type | Usage |
|------|-------|
| `feat/` | New features |
| `fix/` | Bug fixes |
| `refactor/` | Code restructuring |
| `docs/` | Documentation only |
| `test/` | Test additions/fixes |

**Examples**:
- `feat/issue-4-extract-controllers`
- `fix/issue-7-websocket-reconnect`
- `refactor/issue-5-module-cleanup`

### 3. Worktree Strategy

**When to use worktrees**:
- Parallel development on different issues
- Long-running features that shouldn't block other work
- Investigating bugs while preserving main workspace

```bash
# Create worktree for issue #4
git worktree add .worktrees/issue-4 -b feat/issue-4-extract-controllers

# Work in isolation
cd .worktrees/issue-4
# ... make changes ...

# Create PR from worktree
gh pr create --title "feat: Extract controllers" --body "Closes #4"

# After PR merges, cleanup
cd ../..
git worktree remove .worktrees/issue-4
```

### 4. Worktree Lifecycle

```
1. CLAIM ISSUE    → gh issue edit 4 --add-assignee @me
2. CREATE WORKTREE → git worktree add .worktrees/issue-4 -b feat/issue-4
3. DEVELOP        → Write tests, implement, verify
4. SYNC MAIN      → git fetch origin main && git rebase origin/main
5. CREATE PR      → gh pr create --body "Closes #4"
6. CLEANUP        → git worktree remove .worktrees/issue-4
```

### 5. Commit Messages

```
<type>: <description>

[optional body]

[optional footer: Closes #<issue>]
```

**Types**: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

**Example**:
```
feat: Add partial sell buttons to trading panel

- Add 10%, 25%, 50%, 100% percentage buttons
- Integrate with TradeManager.execute_partial_sell()
- Update position display after partial close

Closes #4
```

### 6. Pull Request Process

1. Push branch: `git push -u origin <branch>`
2. Create PR: `gh pr create --title "..." --body "Closes #<issue>"`
3. Wait for CI (tests must pass)
4. Request review if needed
5. Merge: `gh pr merge --squash --delete-branch`

---

## Code Quality Standards

### Before Committing

```bash
cd src && python3 -m pytest tests/ -v --tb=short  # All tests pass
black .                                            # Format code
flake8                                            # Lint check
mypy core/ bot/ services/                         # Type check
```

### Hot Files (Coordinate Before Editing)

These files are frequently modified and prone to conflicts:

| File | Lines | Risk |
|------|-------|------|
| `src/ui/main_window.py` | 2000+ | CRITICAL |
| `src/core/game_state.py` | 950+ | HIGH |
| `src/bot/browser_executor.py` | 950+ | HIGH |
| `src/sources/websocket_feed.py` | 900+ | HIGH |

**Rule**: Open an issue BEFORE modifying hot files. Coordinate in issue comments.

---

## Parallel Development Guidelines

### For Multiple Sessions (Claude or Human)

1. **Each session gets ONE issue** - No overlapping work
2. **Use worktrees** - Each session works in isolated worktree
3. **Check issue assignment** - `gh issue view <n>` shows assignee
4. **Communicate via issues** - Leave comments for coordination

### File Ownership by Issue

| Issue | Safe to Modify |
|-------|---------------|
| #4 (Extract Controllers) | `src/ui/controllers/*`, `src/ui/builders/*` |
| #5 (Module Cleanup) | `src/` structure, `__init__.py` files |
| #3 (Mixin Contracts) | `src/bot/mixins/*`, interface files |
| #2 (WebSocket) | `src/sources/websocket_*.py` |

### Conflict Prevention

1. **Vertical slicing** - Each issue owns specific files
2. **Interface contracts** - Define interfaces before implementation
3. **Small PRs** - Merge frequently to reduce drift
4. **Rebase before PR** - `git pull --rebase origin main`

### Multi-Session Coordination

**Session A starts:**
```bash
gh issue edit 4 --add-assignee @me
git worktree add .worktrees/issue-4 -b feat/issue-4
cd .worktrees/issue-4
```

**Session B starts (different issue):**
```bash
gh issue edit 5 --add-assignee @me
git worktree add .worktrees/issue-5 -b refactor/issue-5
cd .worktrees/issue-5
```

**Both work in parallel, merge independently.**

---

## Testing Requirements

### Test Command
```bash
cd src && python3 -m pytest tests/ -v --tb=short
```

### Coverage Expectations
- New code: 80%+ coverage
- Bug fixes: Include regression test
- Refactors: No coverage decrease

### Test File Naming

Mirror source structure:
```
src/core/game_state.py    → tests/test_core/test_game_state.py
src/bot/controller.py     → tests/test_bot/test_controller.py
```

---

## Documentation

### When to Update Docs
- New features: Update README.md
- Architecture changes: Update CLAUDE.md
- API changes: Update relevant docstrings
- New configuration: Update config.py comments

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | User-facing overview |
| `CLAUDE.md` | AI assistant context |
| `AGENTS.md` | Repository guidelines |
| `SETUP.md` | Developer onboarding |
| `docs/` | Design documents |

---

## Getting Help

- **Issues**: https://github.com/Dutchthenomad/REPLAYER/issues
- **Documentation**: See `docs/` folder
- **Test examples**: See `src/tests/` for patterns
