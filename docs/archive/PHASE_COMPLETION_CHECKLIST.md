# Phase Completion Checklist

**Use this checklist at the end of each development phase before committing to git.**

---

## 🔍 Pre-Commit Review Process

### Quick Review (Staged Files Only)
```bash
cd /home/nomad/Desktop/REPLAYER
./scripts/pre_commit_review.sh
```

### Full Phase Review (Recommended)
```bash
cd /home/nomad/Desktop/REPLAYER
./scripts/pre_commit_review.sh --phase-complete
```

---

## ✅ Phase Completion Checklist

### 1. Code Quality Checks

- [ ] **Run automated review script**
  ```bash
  ./scripts/pre_commit_review.sh --phase-complete
  ```

- [ ] **All tests passing** (237/237)
  ```bash
  cd src && python3 -m pytest tests/ -v
  ```

- [ ] **No pylint critical issues**
  - Warnings acceptable if documented
  - Errors must be fixed

- [ ] **No mypy type errors**
  - Use `# type: ignore` only when absolutely necessary
  - Document why type checking is disabled

### 2. Design Pattern Compliance

- [ ] **Check architect.yaml patterns**
  - Thread safety rules followed?
  - UI updates use `ui_dispatcher.submit()`?
  - Lock released before callbacks?
  - Event handlers have error boundaries?

- [ ] **Check RULES.yaml compliance**
  - Using `Decimal` for money/prices?
  - Using `RLock` for state management?
  - Bounded collections (`deque(maxlen=N)`)?
  - Type hints on all functions?

### 3. Documentation Updates

- [ ] **Update CLAUDE.md if needed**
  - New features documented?
  - Architecture changes noted?
  - Known issues updated?

- [ ] **Update AGENTS.md if needed**
  - Quick reference accurate?
  - Commands still valid?

- [ ] **Add/update docstrings**
  - Public functions documented?
  - Complex logic explained?

### 4. Git Workflow

- [ ] **Review changes**
  ```bash
  git status
  git diff
  ```

- [ ] **Stage files**
  ```bash
  git add <files>
  ```

- [ ] **Run final review**
  ```bash
  ./scripts/pre_commit_review.sh
  ```

- [ ] **Commit with descriptive message**
  ```bash
  git commit -m "Phase X: [Feature/Fix] - Description

  - Detail 1
  - Detail 2

  🤖 Generated with Claude Code
  Co-Authored-By: Claude <noreply@anthropic.com>"
  ```

- [ ] **Push to remote**
  ```bash
  git push origin main
  ```

---

## 📊 Review Report

After running the review script, check the generated report:
```bash
# Report saved to: review_report_YYYYMMDD_HHMMSS.txt
cat review_report_*.txt | tail -50
```

### Interpreting Results

**✓ All checks passed!**
- Green light to commit and push
- All design patterns followed
- No critical issues

**⚠ Warnings found**
- Review warnings in report
- Decide if acceptable
- Document why if ignored

**✗ Errors found**
- Must fix before committing
- Run review again after fixes
- Iterate until clean

---

## 🚀 Phase-Specific Checklists

### Phase 8.1: Partial Sell Infrastructure

- [ ] `Position.reduce_amount()` method added
- [ ] `TradeManager.execute_partial_sell()` added
- [ ] `GameState.partial_close_position()` added
- [ ] `POSITION_REDUCED` event added to EventBus
- [ ] Unit tests passing for partial sells
- [ ] Integration tests passing
- [ ] Thread safety verified (locks held correctly)

### Phase 8.2: UI Partial Sell Buttons

- [ ] 4 sell buttons added (10%, 25%, 50%, 100%)
- [ ] Button handlers use `ui_dispatcher.submit()`
- [ ] Position label updates correctly
- [ ] Buttons enable/disable based on position state
- [ ] Toast notifications show partial P&L
- [ ] Manual testing completed

### Phase 8.3: BotUIController

- [ ] `BotUIController` class created
- [ ] Methods: `set_bet_amount()`, `click_buy()`, `click_sell()`, `click_sidebet()`
- [ ] Read methods: `read_balance()`, `read_position()`
- [ ] Human delay simulation (50-200ms)
- [ ] `ExecutionMode` enum added
- [ ] `BotController` updated for dual-mode
- [ ] Tests passing for both modes

### Phase 8.4: Bot Configuration UI

- [ ] `BotConfigPanel` class created
- [ ] Settings: execution mode, strategy, bet amount
- [ ] "Bot → Configuration..." menu item added
- [ ] Config persists to `bot_config.json`
- [ ] Config loads on startup
- [ ] UI validation working

### Phase 8.5: Playwright Integration

- [ ] `BrowserExecutor` class created
- [ ] `RugsBrowserManager` imported
- [ ] Async methods implemented
- [ ] `--live` flag added to CLI
- [ ] Execution validation working
- [ ] Retry logic tested (max 3 attempts)
- [ ] Error handling with screenshots

### Phase 8.6: State Synchronization

- [ ] Browser state polling implemented
- [ ] State reconciliation working
- [ ] Timing metrics tracked
- [ ] Timing dashboard UI added
- [ ] Timing data logged
- [ ] Visual validation completed

### Phase 8.7: Production Readiness

- [ ] Safety mechanisms added (loss limits, position size, emergency stop)
- [ ] Comprehensive logging added
- [ ] Confirmation dialog for `--live` mode
- [ ] README updated
- [ ] Troubleshooting guide added
- [ ] 1+ hour bot run successful (no crashes)

---

## 🛠 Common Issues & Fixes

### Tests Failing

```bash
# Run specific test
cd src
python3 -m pytest tests/test_core/test_game_state.py -v

# Run with more detail
python3 -m pytest tests/ -vv --tb=long
```

### Pylint Errors

```bash
# Check specific file
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/pylint src/core/game_state.py

# Disable specific warning (use sparingly)
# pylint: disable=too-many-arguments
```

### Mypy Type Errors

```bash
# Check specific file
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/mypy src/core/game_state.py --strict

# Add type ignore (document why)
result = some_function()  # type: ignore  # Third-party library has no types
```

### Review Script Errors

```bash
# Run with verbose output
./scripts/pre_commit_review.sh --file src/core/game_state.py

# Check script is executable
chmod +x ./scripts/pre_commit_review.sh
```

---

## 📈 Quality Metrics

Track these over time:

- **Test Coverage**: Aim for 90%+
- **Pylint Score**: Aim for 9.0+/10.0
- **Mypy Compliance**: 100% (strict mode)
- **Design Pattern Violations**: 0 (critical), <5 (warnings)

---

## 🎯 Success Criteria

A phase is complete when:

1. ✅ All tests passing (237+)
2. ✅ Review script passes with 0 errors
3. ✅ Documentation updated
4. ✅ Code committed with proper message
5. ✅ Pushed to remote successfully

---

**Last Updated**: 2025-11-16
**Next Review**: End of Phase 8.1
