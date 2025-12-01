# Phase 3: MainWindow Refactoring Plan

**Current State**: MainWindow is 2231 lines (God Object anti-pattern)
**Target State**: ~800 lines (with extracted controllers)
**Estimated Savings**: ~1400 lines extracted into 5 controller classes

---

## Sub-Phase Breakdown

### Phase 3.1: Extract BotManager (~300 lines saved)

**New File**: `src/ui/controllers/bot_manager.py`

**Methods to Extract**:
- `toggle_bot()` (line 1042)
- `_toggle_bot_from_menu()` (line 1596)
- `_on_strategy_changed()` (line 1089)
- `_check_bot_results()` (line 1316)
- `_show_bot_config()` (line 1627)
- `_show_timing_metrics()` (line 1658)
- `_update_timing_metrics_display()` (line 1764)
- `_update_timing_metrics_loop()` (line 1794)
- `_toggle_timing_overlay()` (line 1609)

**Responsibilities**:
- Bot lifecycle management (start/stop)
- Strategy selection and configuration
- Timing metrics tracking and display
- Bot results monitoring

**Dependencies**:
- bot.controller.BotController
- bot.ui_controller.BotUIController
- ui.bot_config_panel.BotConfigPanel
- ui.timing_overlay.TimingOverlay

---

### Phase 3.2: Extract ReplayController (~400 lines saved)

**New File**: `src/ui/controllers/replay_controller.py`

**Methods to Extract**:
- `toggle_playback()` (line 888)
- `step_forward()` (line 899)
- `step_backward()` (line 1501)
- `reset_game()` (line 905)
- `set_playback_speed()` (line 913)
- `toggle_play_pause()` (line 1544)
- `load_game()` (line 713)
- `load_game_file()` (line 726)
- `load_file_dialog()` (line 1540)
- `_load_next_game()` (line 1234)
- `_toggle_recording()` (line 1548)
- `_open_recordings_folder()` (line 1596)

**Responsibilities**:
- Game file loading (file dialog, auto-load)
- Playback control (play/pause, step, reset)
- Playback speed management
- Recording control

**Dependencies**:
- core.replay_engine.ReplayEngine
- core.recorder_sink.RecorderSink

---

### Phase 3.3: Extract BrowserBridgeController (~200 lines saved)

**New File**: `src/ui/controllers/browser_controller.py`

**Methods to Extract**:
- `_show_browser_connection_dialog()` (line 1809)
- `_on_browser_connected()` (line 1855)
- `_on_browser_connection_failed()` (line 1878)
- `_disconnect_browser()` (line 1884)
- `_on_browser_disconnected()` (line 1931)
- `_update_browser_status()` (line 1954)
- `_connect_browser_bridge()` (line 1991)
- `_disconnect_browser_bridge()` (line 2001)
- `_on_bridge_status_change()` (line 2008)

**Responsibilities**:
- Browser connection dialog
- Browser connection lifecycle
- Bridge status monitoring
- Status UI updates

**Dependencies**:
- bot.browser_bridge.BrowserBridge (get_browser_bridge)
- ui.browser_connection_dialog.BrowserConnectionDialog

---

### Phase 3.4: Extract TradingController (~200 lines saved)

**New File**: `src/ui/controllers/trading_controller.py`

**Methods to Extract**:
- `execute_buy()` (line 919)
- `execute_sell()` (line 938)
- `execute_sidebet()` (line 963)
- `set_sell_percentage()` (line 986)
- `highlight_percentage_button()` (line 1012)
- `set_bet_amount()` (line 1368)
- `increment_bet_amount()` (line 1374)
- `clear_bet_amount()` (line 1392)
- `half_bet_amount()` (line 1402)
- `double_bet_amount()` (line 1417)
- `max_bet_amount()` (line 1432)
- `get_bet_amount()` (line 1444)

**Responsibilities**:
- Trade execution (buy/sell/sidebet)
- Bet amount management
- Sell percentage management
- UI updates for trade state

**Dependencies**:
- core.trade_manager.TradeManager
- core.game_state.GameState

---

### Phase 3.5: Extract LiveFeedController (~200 lines saved)

**New File**: `src/ui/controllers/live_feed_controller.py`

**Methods to Extract**:
- `enable_live_feed()` (line 746)
- `disable_live_feed()` (line 861)
- `toggle_live_feed()` (line 879)
- `_toggle_live_feed_from_menu()` (line 2062)

**Responsibilities**:
- WebSocket feed connection/disconnection
- Live mode state management
- Feed source switching
- UI updates for live feed status

**Dependencies**:
- sources.websocket_feed.WebSocketFeedSource
- core.live_ring_buffer.LiveRingBuffer

---

## Implementation Strategy

### For Each Controller Extraction:

1. **Create Controller Class**:
   ```python
   class BotManager:
       """Manages bot lifecycle, configuration, and monitoring"""
       
       def __init__(self, parent_window, state, event_bus, config):
           self.window = parent_window
           self.state = state
           self.event_bus = event_bus
           self.config = config
           # ... initialize dependencies
       
       # ... extracted methods
   ```

2. **Update MainWindow**:
   - Create controller instance in `__init__`
   - Replace method calls with `self.bot_manager.method_name()`
   - Keep only UI construction in MainWindow

3. **Update Tests**:
   - Create new test file for each controller
   - Move relevant tests from test_ui/test_main_window.py
   - Update fixtures to mock controllers

4. **Verify**:
   - Run all tests (should stay at 310/310)
   - Visual test: Launch application, verify all features work
   - Check no regressions introduced

---

## Execution Order

**Priority**: Low risk → High risk

1. ✅ **Phase 3.1**: BotManager (lowest risk - self-contained feature)
2. ✅ **Phase 3.2**: ReplayController (medium risk - core feature but well-isolated)
3. ✅ **Phase 3.3**: TradingController (medium risk - business logic)
4. ✅ **Phase 3.4**: LiveFeedController (medium risk - newer feature)
5. ✅ **Phase 3.5**: BrowserBridgeController (highest risk - Phase 9 integration)

---

## Success Criteria

- ✅ MainWindow reduced from 2231 lines to ~800 lines
- ✅ All 310 tests still passing
- ✅ Application launches and all features work correctly
- ✅ No behavioral changes (refactoring only)
- ✅ Each controller has single, clear responsibility
- ✅ Controllers are testable in isolation

---

## Estimated Timeline

- Phase 3.1 (BotManager): 2-3 hours
- Phase 3.2 (ReplayController): 3-4 hours
- Phase 3.3 (TradingController): 2-3 hours
- Phase 3.4 (LiveFeedController): 2-3 hours
- Phase 3.5 (BrowserBridgeController): 2-3 hours

**Total**: 11-16 hours of work

---

## Next Steps

After approval:
1. Create `src/ui/controllers/` directory
2. Start with Phase 3.1 (BotManager - lowest risk)
3. Test after each extraction
4. Continue through phases in order
