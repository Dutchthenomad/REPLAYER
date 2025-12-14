# TDD Cycle Checklist

## Before Writing Any Code
- [ ] Requirement is clearly understood
- [ ] Test file location identified (tests/test_{module}/)
- [ ] Test name follows pattern: test_{function}_{scenario}_{expected}

## RED Phase
- [ ] Write ONE failing test
- [ ] Run: `cd src && python3 -m pytest tests/test_{file}.py -v`
- [ ] Confirm test FAILS (not errors)
- [ ] Failure is for RIGHT reason (missing feature, not syntax)

## GREEN Phase
- [ ] Write MINIMAL code to pass
- [ ] No feature creep
- [ ] Run: `cd src && python3 -m pytest tests/ -v`
- [ ] ALL tests pass (not just new one)

## REFACTOR Phase
- [ ] Remove duplication
- [ ] Improve naming
- [ ] Tests still pass

## COMMIT
- [ ] Small, focused commit
- [ ] Message format: `feat|fix|refactor: description`
