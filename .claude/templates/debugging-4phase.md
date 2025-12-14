# 4-Phase Debugging Protocol

**Iron Law**: NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST

## Phase 1: Root Cause Investigation

1. Read error messages and stack traces CAREFULLY
2. Reproduce consistently:
   ```bash
   cd src && python3 -m pytest tests/test_{file}.py::test_{name} -v
   ```
3. Check recent changes:
   ```bash
   git diff HEAD~5
   git log --oneline -10
   ```
4. Add diagnostic logging at component boundaries
5. Trace data flow through EventBus -> GameState -> UI

**Output**: "The failure occurs at [file:line] because [specific reason]"

## Phase 2: Pattern Analysis

1. Find WORKING examples in codebase
2. Check architect.yaml for pattern reference
3. Compare working vs broken code
4. Map dependencies through event_bus subscriptions

**Output**: "Working code does X, broken code does Y, the difference is Z"

## Phase 3: Hypothesis Testing

1. Form SPECIFIC hypothesis: "I think X causes Y because Z"
2. Test with MINIMAL changes (one thing at a time)
3. If fix fails, REVERT before trying another:
   ```bash
   git checkout -- src/{file}
   ```

**Critical**: After 3 failed attempts, STOP.
- Question if architecture is fundamentally flawed
- Review architect.yaml patterns
- Consider asking for help

## Phase 4: Implementation

1. Write FAILING test that reproduces the bug
2. Implement SINGLE fix addressing root cause
3. Verify test now passes
4. Verify ALL other tests still pass
5. Commit with message: `fix: [description] - root cause: [what was wrong]`

## REPLAYER-Specific Debugging

### Thread Safety Issues
- Check TkDispatcher usage for UI updates
- Check RLock acquisition in GameState
- Review EventBus handler thread safety

### Event Flow Issues
- Add logging to EventBus publish/subscribe
- Check event handler registration order
- Verify event types match expected

### State Issues
- Check GameState lock release before callbacks
- Verify Position immutability
- Check Decimal precision handling
