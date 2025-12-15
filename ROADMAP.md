# REPLAYER Development Roadmap
**Version**: 0.11.0 | **Date**: December 15, 2025

This roadmap tracks the development priorities for REPLAYER, the rugs.fun trading bot and RL training platform.

---

## Current Status

- **Phase 11**: CDP WebSocket Interception ✅ COMPLETE
- **796 tests passing**
- **CDP browser integration working**
- **Human demo recording system operational**

---

## High-Priority Tasks (Immediate Focus)

### 🎯 Priority 2: Server State Authority Migration
**Goal**: Replace local state calculations with authoritative server state from WebSocket events.

**Context**: Phase 11 completed CDP WebSocket interception. The server now sends `playerUpdate` events with authoritative balance, position, and PnL data.

**Tasks**:
- Use `ServerState.cash` as source of truth for player balance
- Use `ServerState.position_qty` and `ServerState.avg_cost` for position tracking
- Deprecate local position/balance calculations (or make them secondary/validation-only)
- Add drift detection logging when local state diverges from server state
- Update UI to display server-authoritative data with drift warnings

**Success Criteria**:
- All balance displays show server truth
- Position calculations use server data
- Drift warnings appear when local != server (with threshold tolerance)
- Zero manual balance tracking in TradingController

**Related**:
- Builds on Priority 1 (✅ Complete): Server state wiring
- `docs/SESSION_HANDOFF.md` - Original priority stack
- `src/sources/websocket_feed.py` - Server state events

---

### 🎯 Priority 3: Live Game Recording Session (20-30 Games)
**Goal**: Record 20-30 live games with authenticated CDP WebSocket data for RL training.

**Context**: All recording infrastructure is complete (Phase 10). Need real gameplay data with server-authenticated events.

**Prerequisites**:
- Priority 2 complete (server state authority)
- Chrome connected via CDP
- Phantom wallet authenticated to rugs.fun

**Tasks**:
- Manual gameplay session: Play 20-30 games while recording
- Verify recordings capture:
  - Complete price histories (500+ ticks/game)
  - Server-authenticated player updates
  - Game lifecycle events (START/END)
  - All trade actions with server confirmations
- Export recordings to `/home/nomad/rugs_recordings/`
- Generate recording quality report (coverage, completeness, anomalies)

**Success Criteria**:
- 20-30 complete game recordings
- All recordings include authenticated server state
- No missing price data or lifecycle gaps
- Recordings validated for RL training compatibility

**Related**:
- Phase 10 (✅ Complete): Demo recording system
- `src/core/recorder_sink.py` - Recording engine
- `src/services/rag_ingester.py` - Event cataloging

---

### 🎯 Priority 4: RAG Knowledge Base for rugs-expert Agent
**Goal**: Build a queryable knowledge base of game events and patterns for LLM-powered game analysis.

**Context**: Phase 11 implemented RAG event cataloging to `/home/nomad/rugs_recordings/rag_events/`. Need to structure this data for semantic search and agent queries.

**Tasks**:
- Design RAG schema for event types:
  - Game state updates (price, tick, phase)
  - Player actions (trades, sidebets)
  - Market patterns (volatility, rug signals)
  - Leaderboard dynamics
- Implement vector embedding for event similarity search
- Create query interface for rugs-expert agent
- Index existing recordings (929 games)
- Build retrieval prompts for common patterns:
  - "Show games where player bought at 10x and sold at 40x"
  - "Find games with similar volatility to game X"
  - "Identify early rug signals from historical data"

**Success Criteria**:
- RAG database indexed with 929+ games
- Query API returns relevant events within 500ms
- rugs-expert agent can answer complex pattern questions
- Documentation for query syntax and capabilities

**Related**:
- `src/services/rag_ingester.py` - Event cataloging
- `docs/plans/2025-12-14-cdp-websocket-interception-design.md` - RAG architecture
- `/home/nomad/rugs_recordings/rag_events/` - Event storage

---

## Phase 12: Live Trading & RL Integration

### 🎯 Priority 5: RL Model Integration Framework
**Goal**: Integrate trained RL models from rugs-rl-bot for live trading decisions.

**Context**: RL models exist in `/home/nomad/Desktop/rugs-rl-bot/` but are not yet wired into REPLAYER for live inference.

**Tasks**:
- Design model inference pipeline:
  - Load trained RL models (PPO/DQN)
  - Feature extraction from live game state
  - Action selection (buy/sell/hold/sidebet)
  - Confidence scoring
- Create `RLStrategyAdapter` class:
  - Implements `TradingStrategy` ABC
  - Wraps RL model inference
  - Handles feature preprocessing
  - Applies risk limits (max position, stop loss)
- Add model selection UI:
  - Dropdown for trained models
  - Model performance metrics display
  - Live inference confidence visualization
- Integration tests with backtesting

**Success Criteria**:
- RL models load successfully at startup
- Model can generate trade decisions in <100ms
- Bot executes RL-recommended actions in BACKEND mode
- Performance metrics tracked (win rate, avg PnL, Sharpe ratio)

**Related**:
- `/home/nomad/Desktop/rugs-rl-bot/` - RL training project
- `src/bot/strategies/` - Existing strategy framework
- `src/ml/` - ML symlinks

---

### 🎯 Priority 6: Browser Automation for Live Trading
**Goal**: Execute RL bot decisions as real trades through authenticated browser.

**Context**: BrowserExecutor exists (Phase 9) but needs integration with RL decision pipeline for live trading.

**Tasks**:
- Wire `RLStrategyAdapter` → `BrowserExecutor`:
  - Action decisions → browser button clicks
  - Real-time position sync
  - Trade confirmation handling
- Implement safety rails:
  - Max daily loss limit
  - Max trade frequency (rate limiting)
  - Emergency stop button (UI + hotkey)
  - Position size limits
  - Slippage protection
- Add execution monitoring:
  - Trade latency tracking
  - Success/failure rate
  - Slippage analysis
  - Server confirmation validation
- Create "Paper Trading" mode:
  - Simulates trades without execution
  - Validates RL decisions
  - Tracks hypothetical P&L

**Success Criteria**:
- RL bot can execute live trades via browser
- Safety rails prevent catastrophic losses
- Paper trading mode validates bot logic
- Execution latency < 200ms (median)
- All trades receive server confirmation

**Related**:
- `src/bot/browser_executor.py` - Browser automation (517 lines)
- `browser_automation/cdp_browser_manager.py` - CDP control
- Phase 9 (✅ Complete): Browser integration

---

### 🎯 Priority 7: Portfolio Management Dashboard
**Goal**: Real-time portfolio tracking and risk metrics visualization.

**Tasks**:
- Design portfolio panel layout:
  - Live P&L (session, daily, all-time)
  - Position history table
  - Win/loss distribution chart
  - Risk metrics (Sharpe, max drawdown, win rate)
- Implement live portfolio tracking:
  - Subscribe to trade execution events
  - Calculate rolling statistics
  - Detect anomalies (unusual losses, high volatility)
- Add historical performance view:
  - Daily P&L chart
  - Trade timeline
  - Strategy comparison (if multiple models)
- Export portfolio reports (CSV, JSON)

**Success Criteria**:
- Real-time P&L updates during live trading
- Portfolio metrics accurate vs server state
- Historical data persisted across sessions
- Export formats compatible with tax/accounting tools

**Related**:
- `src/ui/main_window.py` - Main UI (1730 lines)
- `src/core/game_state.py` - State management
- Phase 8 (✅ Complete): UI enhancements

---

### 🎯 Priority 8: Player Profile UI Integration
**Goal**: Display player identity, balance, positions, and PnL from server state.

**Context**: Phase 11 captures authenticated player updates. Need UI to display this data.

**Tasks**:
- Design player profile widget:
  - Username + player ID
  - Current SOL balance
  - Active position (qty, avg cost, unrealized P&L)
  - Session statistics (games played, win rate)
- Wire to CDP WebSocket events:
  - `usernameStatus` → identity display
  - `playerUpdate` → balance/position updates
  - `gameStatePlayerUpdate` → leaderboard rank
- Add balance history chart:
  - Plot balance over time
  - Highlight trade events
  - Show deposits/withdrawals
- Implement balance drift alerts:
  - Compare local vs server balance
  - Show warning icon if divergence > threshold

**Success Criteria**:
- Player profile displays authenticated data
- Balance updates in real-time (<1s latency)
- Drift alerts trigger when local state is stale
- Profile persists across app restarts

**Related**:
- `src/sources/cdp_websocket_interceptor.py` - CDP interception (205 lines)
- `src/services/event_source_manager.py` - Source management (86 lines)
- Phase 11 (✅ Complete): CDP WebSocket interception

---

## Technical Debt & Infrastructure

### 🔧 Main Window Refactoring (Issue #4)
**Goal**: Break up monolithic `main_window.py` (1730 lines) into modular components.

**Status**: Design complete, implementation pending.

**Tasks**:
- Extract position panel → `ui/panels/position_panel.py`
- Extract control panel → `ui/panels/control_panel.py`
- Extract chart → `ui/panels/chart_panel.py`
- Extract status bar → `ui/widgets/status_bar.py`
- Refactor menu bar → `ui/menus/main_menu_bar.py`

**Success Criteria**:
- `main_window.py` < 500 lines
- All tests pass (796 → 796+)
- Zero UI regressions

**Related**:
- `docs/plans/2025-12-13-issue-4-main-window-refactoring.md`
- Issue #4 (existing)

---

### 🔧 Import Decoupling & Timestamp Fixes
**Goal**: Remove circular dependencies and standardize timestamp handling.

**Status**: Design complete, implementation pending.

**Tasks**:
- Decouple `sources/` from `ui/` imports
- Standardize timestamp format (ISO 8601)
- Remove unused imports (found by static analysis)

**Success Criteria**:
- Zero circular import warnings
- All timestamps use `datetime.isoformat()`
- Import graph is acyclic

**Related**:
- `docs/plans/2025-12-15-import-decoupling-and-timestamp-fixes-plan.md`

---

## Long-Term Goals (Phase 13+)

### 🚀 Multi-Strategy Tournament Mode
- Run multiple RL models in parallel
- A/B test strategies on same games
- Leaderboard for model performance

### 🚀 Advanced Risk Management
- Dynamic position sizing (Kelly Criterion)
- Portfolio-level stop losses
- Correlation-based hedging

### 🚀 Market Analysis Tools
- Volatility forecasting
- Rug prediction model
- Optimal exit timing analysis

### 🚀 Social Features
- Share recordings with community
- Compare strategies with other players
- Collaborative strategy development

---

## Priority Summary

| Priority | Task | Status | Dependencies |
|----------|------|--------|--------------|
| 1 | Wire Server State | ✅ Complete | None |
| 2 | Server State Authority | Pending | Priority 1 |
| 3 | Record 20-30 Games | Pending | Priority 2 |
| 4 | RAG Knowledge Base | Pending | Priority 3 |
| 5 | RL Model Integration | Pending | Priority 3 |
| 6 | Browser Live Trading | Pending | Priority 5 |
| 7 | Portfolio Dashboard | Pending | Priority 6 |
| 8 | Player Profile UI | Pending | Priority 2 |

---

## Contributing

See `CONTRIBUTING.md` for development workflow and PR guidelines.

---

*Last Updated: December 15, 2025*
