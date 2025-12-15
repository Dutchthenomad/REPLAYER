---
title: "[Priority 8] Player Profile UI Integration"
labels: enhancement, ui, priority-medium, phase-12
assignees: ""
---

## Goal
Display player identity, balance, positions, and PnL from server state.

## Context
Phase 11 captures authenticated player updates. Need UI to display this data.

## Tasks
### Player Profile Widget
- [ ] Design player profile widget
- [ ] Display username + player ID
- [ ] Display current SOL balance
- [ ] Display active position (qty, avg cost, unrealized P&L)
- [ ] Display session statistics (games played, win rate)

### Wire to CDP WebSocket Events
- [ ] Wire `usernameStatus` → identity display
- [ ] Wire `playerUpdate` → balance/position updates
- [ ] Wire `gameStatePlayerUpdate` → leaderboard rank

### Balance History Chart
- [ ] Plot balance over time
- [ ] Highlight trade events
- [ ] Show deposits/withdrawals

### Balance Drift Alerts
- [ ] Compare local vs server balance
- [ ] Show warning icon if divergence > threshold
- [ ] Log drift events for debugging

## Success Criteria
- Player profile displays authenticated data
- Balance updates in real-time (<1s latency)
- Drift alerts trigger when local state is stale
- Profile persists across app restarts
- UI integrates cleanly with existing layout

## Dependencies
- Priority 2 complete (server state authority)

## Related Files
- `src/sources/cdp_websocket_interceptor.py` - CDP interception (205 lines)
- `src/services/event_source_manager.py` - Source management (86 lines)
- `src/ui/main_window.py` - Main UI

## Estimated Effort
6-8 hours
