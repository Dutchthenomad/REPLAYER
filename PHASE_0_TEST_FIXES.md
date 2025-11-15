# Phase 0: Test Suite Remediation

**Goal**: Achieve 100% test pass rate before Phase 4

**Current Status**: 119/148 passing (80%)
**Target**: 148/148 passing (100%)
**Failures**: 29 tests

---

## Failure Categories

### Category 1: EventBus Weak References (6 tests)
**Issue**: Tests check `handler in list`, but EventBus now uses weak references

**Affected Tests**:
- `test_subscribe_to_event` - Expects `handler in _subscribers[event]`
- `test_multiple_handlers_same_event` - Expects count of handlers
- `test_publish_event` - Expects handler in list
- `test_publish_multiple_events` - Expects handler called
- `test_publish_different_events` - Expects selective calling
- `test_handler_exception_doesnt_break_other_handlers` - Exception handling

**Fix Strategy**: Update tests to check functional behavior (handler called) instead of internal implementation (weak reference existence)

---

### Category 2: GameState API Changes (10 tests)
**Issue**: Tests reference old API methods/attributes

**Sub-category 2A: session_pnl attribute (3 tests)**
- `test_update_balance_decrease` - Expects `session_pnl` to track P&L
- `test_update_balance_increase` - Same
- `test_update_balance_multiple_changes` - Same

**Fix**: Either add `session_pnl` attribute or update tests to use metrics

**Sub-category 2B: load_game() method (4 tests)**
- `test_playthrough_simple_game` - Calls `game_state.load_game()`
- `test_playthrough_tracks_balance` - Same
- `test_playthrough_final_stats` - Same
- `test_playthrough_with_different_strategies` - Same

**Fix**: Update tests - `load_game()` is on ReplayEngine, not GameState

**Sub-category 2C: Position/Sidebet management (3 tests)**
- `test_open_position` - API mismatch
- `test_position_history` - API mismatch
- `test_multiple_positions_sequential` - API mismatch
- `test_resolve_sidebet` - API mismatch (only 1)

**Fix**: Update to match current GameState API

---

### Category 3: Other API Mismatches (13 tests)

**TradeManager** (4 tests):
- `test_buy_with_active_position` - Position check logic changed
- `test_sell_pnl_calculation` - P&L calculation API changed
- `test_trading_not_allowed_when_inactive` - Validation logic changed
- `test_trading_not_allowed_when_rugged` - Validation logic changed
- `test_multiple_trades_in_game` - API mismatch

**BotInterface** (3 tests):
- `test_observation_position_after_buy` - Observation format changed
- `test_info_cannot_buy_with_position` - Logic changed
- `test_execute_side_action` - Sidebet execution changed
- `test_cannot_buy_twice` - Position validation changed

**Strategies** (1 test):
- `test_get_invalid_strategy` - Error handling changed

**Validators** (1 test):
- `test_zero_bet` - Validation logic changed

**BotController** (1 test):
- `test_execute_step_maintains_state_consistency` - State handling changed

---

## Fix Implementation Plan

### Phase 0A: EventBus Tests (6 fixes)
Update tests to verify functional behavior instead of internal implementation

### Phase 0B: GameState API Tests (10 fixes)
1. Add `session_pnl` tracking or update tests
2. Move `load_game()` calls to ReplayEngine
3. Update position/sidebet API calls

### Phase 0C: Other API Tests (13 fixes)
Update each test to match current implementation

---

## Progress Tracking

- [ ] Phase 0A: EventBus tests (6/6)
- [ ] Phase 0B: GameState tests (10/10)
- [ ] Phase 0C: Other API tests (13/13)
- [ ] Final verification: 148/148 passing
- [ ] Commit Phase 0

---

**Status**: In Progress
**Last Updated**: 2025-11-15 08:45 UTC
