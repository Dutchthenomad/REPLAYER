# Claude Code Superpowers Workflow - Quick Reference

## Session Bootstrap Prompts

### Fresh Session - Full Context Load
Copy and paste this to bring a new Claude session to peak state:

```
Read ~/.claude/WORKFLOW_QUICKREF.md and ~/CLAUDE.md to understand my development workflow.

I follow the Superpowers methodology:
1. TDD Iron Law: NO code without failing test first
2. Verification: Evidence before claims
3. Systematic Debugging: 4-phase root cause analysis
4. Zero-Context Plans: Plans executable by anyone
5. Git Worktrees: Isolated feature development

Acknowledge you understand these principles before we proceed.
```

### Quick Session - Minimal Context
```
I use TDD (test first), systematic debugging (4-phase), and verification before completion. Use /tdd, /debug, /verify commands. Read CLAUDE.md for project context.
```

### New Project Setup
```
Initialize this project for Superpowers workflow:
1. Create CLAUDE.md with project context
2. Create .claude/settings.local.json with permissions
3. Set up .gitignore for .worktrees/
4. Verify test framework is configured
5. Run baseline tests to confirm clean state
```

---

## Slash Commands Reference

| Command | When to Use | Key Rule |
|---------|-------------|----------|
| `/tdd` | ALL new code, bug fixes, refactoring | Test fails BEFORE implementation |
| `/plan` | Before starting any feature | Plans must work with ZERO context |
| `/debug` | ANY technical failure | Root cause BEFORE fix attempts |
| `/verify` | Before claiming task complete | Fresh test run, not "should pass" |
| `/worktree` | Starting isolated feature work | Always check .gitignore first |
| `/review` | After completing task | Check before proceeding |
| `/run-tests` | Anytime | Auto-detects project test framework |

---

## Thinking Budget Keywords

Use these keywords to control Claude's reasoning depth:

| Keyword | Tokens | Use For |
|---------|--------|---------|
| `think` | ~4k | Simple tasks, quick fixes |
| `think hard` | ~10k | Debugging, optimization, code review |
| `think harder` | ~20k | Complex debugging, multi-file changes |
| `ultrathink` | ~32k | Architecture, complex refactors, new features |

### Examples
```
think about why this test is failing

think hard about the performance of this function

ultrathink about how to architect this new feature
```

---

## Git Worktree Quick Commands

```bash
# Create worktree for feature
git worktree add .worktrees/feature-name -b feature/feature-name
cd .worktrees/feature-name

# List all worktrees
git worktree list

# Remove worktree (after merge)
git worktree remove .worktrees/feature-name

# Prune stale worktrees
git worktree prune
```

---

## TDD Cycle Checklist

```
□ RED: Write ONE failing test
□ Verify: Test FAILS (not errors)
□ Verify: Failure is for RIGHT reason
□ GREEN: Write MINIMAL passing code
□ Verify: Test PASSES
□ Verify: ALL tests still pass
□ REFACTOR: Clean up (tests still pass)
□ COMMIT: Small, focused commit
```

---

## Debugging 4-Phase Protocol

```
□ Phase 1: ROOT CAUSE INVESTIGATION
  - Read error messages carefully
  - Reproduce consistently
  - Check git diff/log for recent changes
  - Add diagnostic logging

□ Phase 2: PATTERN ANALYSIS
  - Find working examples in codebase
  - Compare working vs broken code
  - Map dependencies

□ Phase 3: HYPOTHESIS TESTING
  - Form specific hypothesis: "X causes Y because Z"
  - Test ONE change at a time
  - REVERT failed attempts before trying next
  - STOP after 3 failures → architecture review

□ Phase 4: IMPLEMENTATION
  - Write failing test reproducing bug
  - Implement SINGLE fix
  - Verify all tests pass
```

---

## Verification Checklist

Before claiming ANY task complete:

```
□ Identified proof command (pytest, npm test, etc.)
□ Executed FRESH (not "it passed before")
□ Read COMPLETE output
□ Exit code is 0
□ 0 failures, 0 errors
□ Original symptom is fixed (not just tests pass)
```

---

## Red Flags - STOP Immediately

- [ ] Writing code before tests
- [ ] Tests pass immediately when written
- [ ] Making multiple simultaneous changes
- [ ] "Just this once" rationalization
- [ ] Using words: "should," "probably," "seems to"
- [ ] Third fix attempt failed
- [ ] Proposing fix before understanding issue

---

## Project Test Commands

| Project | Test Command |
|---------|--------------|
| CV-BOILER-PLATE-FORK | `.venv/bin/python -m pytest tests/ -v` |
| rugs-rl-bot | `.venv/bin/python -m pytest tests/ -v` |
| REPLAYER | `cd src && python -m pytest tests/ -v` |
| hyperliquid-data-system | `npm test` |

---

## Hook Examples (Optional)

Add to `.claude/settings.local.json` for automatic enforcement:

```json
{
  "hooks": {
    "pre-commit": {
      "command": "pytest tests/ -v --tb=short",
      "description": "Run tests before commit"
    },
    "post-edit": {
      "command": "echo 'Remember: /verify before claiming complete'",
      "description": "Verification reminder"
    }
  }
}
```

---

## Common Prompts Library

### Start New Feature
```
I want to add [FEATURE].

1. First /plan the implementation with zero-context detail
2. Then /worktree to isolate the work
3. We'll use /tdd for each component
```

### Fix a Bug
```
There's a bug: [DESCRIPTION]

Use /debug to systematically investigate:
1. Phase 1: Find root cause
2. Phase 2: Analyze patterns
3. Phase 3: Test hypothesis (max 3 attempts)
4. Phase 4: TDD fix
```

### Code Review Request
```
I've completed [TASK]. Please /review the changes:
- Files changed: [LIST]
- What it does: [DESCRIPTION]
- Tests added: [YES/NO]

Check for critical issues before I merge.
```

### Refactoring
```
I want to refactor [COMPONENT].

Requirements:
1. All existing tests must continue to pass
2. Use /tdd for any new functionality
3. /verify after each change
4. Small, focused commits
```

---

## File Locations

| File | Purpose |
|------|---------|
| `~/CLAUDE.md` | Master project context |
| `~/.claude/commands/*.md` | Slash command definitions |
| `~/.claude/agents/*.md` | Agent profile definitions |
| `~/.claude/WORKFLOW_QUICKREF.md` | This file |
| `~/.claude/plans/` | Persistent planning notes |
| `[project]/CLAUDE.md` | Project-specific context |
| `[project]/.claude/settings.local.json` | Project permissions |

---

## Emergency Recovery

If things go wrong:

```bash
# Discard all uncommitted changes
git checkout -- .

# Reset to last commit
git reset --hard HEAD

# Check worktree status
git worktree list

# Clean up stale worktrees
git worktree prune

# Re-run all tests
pytest tests/ -v  # or npm test
```

---

## SDLC Workflow (Strict Enforcement)

### The 5 Phases

```
GitHub Issue → /plan → /scratchpad → /tdd (@QA) → implement (@Dev) → /review → gh pr create
```

### Phase 1: Inception
- **Source of Truth**: GitHub Issue
- **Action**: `/plan #123` (read issue, create strategy)
- **Think Level**: ULTRATHINK
- **Constraint**: NO code until plan approved

### Phase 2: Context & Memory
- **Action**: `/scratchpad` (read previous context)
- **Update**: Save state before `/clear`

### Phase 3: Test-Driven Development
- **Agent**: @QA mindset
- **Action**: `/tdd "requirement"`
- **Constraint**: Write failing test, confirm failure, STOP

### Phase 4: Implementation
- **Agent**: @Dev mindset
- **Action**: Implement minimal code to pass tests
- **Environment**: Must be in activated venv

### Phase 5: Review & Commit
- **Action**: `/review src/changed_file.py`
- **Think Level**: THINK HARD
- **Commit**: `gh pr create --title "..." --body "Closes #123"`

---

## GitHub-First Development (MANDATORY)

**All development work MUST be tracked in GitHub.**

### Automatic Behaviors
1. **Every task** starts with a GitHub Issue (create if none exists)
2. **Every branch** is named `<type>/issue-<number>-<description>`
3. **Every commit** references the issue number
4. **Every completion** creates a PR with `Closes #<issue>`

### Issue-Driven Development
```bash
# View issue details
gh issue view 123

# Start work on issue
/plan #123                    # ULTRATHINK planning
git checkout -b feat/issue-123-description
/tdd "implement feature X"    # Write failing test
# implement
/review src/new_file.py       # Review changes
gh pr create --title "feat: Add feature X" --body "Closes #123"
```

### PR Workflow
```bash
# Create PR linked to issue
gh pr create --title "feat: Add feature X" --body "Closes #123"

# Request review
gh pr ready

# Merge after approval
gh pr merge --squash --delete-branch
```

### NEVER Do
- Push directly to main/master
- Create branches without issues
- Merge without PR review
- Use raw `git push` to remote (use `gh` instead)

---

## Context Management

| Command | Purpose |
|---------|---------|
| `/clear` | Start fresh (use at task boundaries) |
| `/compact` | Compress history when context fills |
| `/scratchpad` | Save/restore state across clears |

### Before Every /clear
```
/scratchpad  # Save current state
/clear       # Fresh start
/scratchpad  # Restore context
```

---

## Quick Commands Reference (Complete)

| Command | Phase | Think Level | Purpose |
|---------|-------|-------------|---------|
| `/plan #123` | Inception | ULTRATHINK | Plan from GitHub Issue |
| `/scratchpad` | Context | STANDARD | Memory persistence |
| `/tdd` | TDD | STANDARD | Write failing test |
| `/autotest` | TDD/Impl | STANDARD | Quick test runner |
| `/review` | Review | THINK HARD | Code audit |
| `/verify` | Review | STANDARD | Verification gate |
| `/debug` | Any | THINK HARD | 4-phase debugging |
| `/worktree` | Any | STANDARD | Parallel work |

---

## Agent Profiles

| Agent | Role | When to Use |
|-------|------|-------------|
| `@QA` | Write tests only | Phase 3: TDD |
| `@Dev` | Implementation only | Phase 4: Implementation |
| `@GitHub` | Repo master | All git operations |
| `@Sysadmin` | System operations | Linux/system setup |
| `@ML-Engineer` | ML/RL work | Training, models |

---

*Generated from [obra/superpowers](https://github.com/obra/superpowers) methodology*
*Enhanced with GitHub Issue-Driven SDLC*
*Adapted for Claude Code by nomad*
