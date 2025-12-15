---
title: "[Priority 7] Portfolio Management Dashboard"
labels: enhancement, ui, priority-medium, phase-12
assignees: ""
---

## Goal
Real-time portfolio tracking and risk metrics visualization.

## Tasks
### Portfolio Panel Layout
- [ ] Design portfolio panel layout
- [ ] Live P&L (session, daily, all-time)
- [ ] Position history table
- [ ] Win/loss distribution chart
- [ ] Risk metrics (Sharpe, max drawdown, win rate)

### Live Portfolio Tracking
- [ ] Subscribe to trade execution events
- [ ] Calculate rolling statistics
- [ ] Detect anomalies (unusual losses, high volatility)

### Historical Performance View
- [ ] Daily P&L chart
- [ ] Trade timeline
- [ ] Strategy comparison (if multiple models)

### Export
- [ ] Export portfolio reports (CSV, JSON)

## Success Criteria
- Real-time P&L updates during live trading
- Portfolio metrics accurate vs server state
- Historical data persisted across sessions
- Export formats compatible with tax/accounting tools
- UI responsive with <100ms update latency

## Dependencies
- Priority 6 complete (live trading operational)

## Related Files
- `src/ui/main_window.py` - Main UI (1730 lines)
- `src/core/game_state.py` - State management
- `src/services/event_bus.py` - Event pub/sub

## Estimated Effort
8-10 hours
