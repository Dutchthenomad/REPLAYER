# Code Review Checklist

## Before Requesting Review
- [ ] All tests pass: `cd src && python3 -m pytest tests/ -v`
- [ ] No new warnings
- [ ] Changes follow architect.yaml patterns
- [ ] Changes follow RULES.yaml standards

## Critical (Must Fix)
- [ ] Thread safety: UI updates use TkDispatcher
- [ ] Thread safety: GameState accessed with proper locking
- [ ] Data precision: Money uses Decimal, not float
- [ ] Error handling: All EventBus handlers have try/except
- [ ] Memory: Bounded collections, proper cleanup
- [ ] Tests: Every new function has tests

## Important (Should Fix)
- [ ] Type hints on all public functions
- [ ] No bare `except:` clauses
- [ ] Docstrings on public functions
- [ ] Event types documented

## Minor (Nice to Have)
- [ ] Naming follows conventions
- [ ] No commented-out code
- [ ] Imports organized

## Review Output
```
## Critical Issues
[List or "None found"]

## Important Issues
[List or "None found"]

## Verdict
[ ] APPROVED
[ ] CHANGES REQUESTED
```
