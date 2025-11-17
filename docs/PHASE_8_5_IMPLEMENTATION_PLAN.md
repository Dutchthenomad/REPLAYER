# Phase 8.5: Browser Automation - Implementation Plan
## Menu-Based Approach - Production Ready

## Executive Summary

Transform browser automation from auto-start to user-controlled menu system with:
- **Browser menu** with connection wizard
- **Step-by-step progress** indicators
- **Status display** always visible
- **Error handling** with retry capability
- **Thread-safe** async browser operations

---

## Current State Analysis

### Problems with Current Implementation

1. **Auto-start on --live flag** (line 64, main_window.py)
   - Hard to debug (no visibility into connection steps)
   - Fails silently if import errors occur
   - No user control over when to connect
   - No retry mechanism

2. **Import path issues**
   - `browser_automation/` not in Python path for UI imports
   - BrowserExecutor import fails silently (try/except catches it)
   - User sees "No module named 'browser_automation'" warning

3. **No status visibility**
   - User doesn't know if browser connected
   - No indication of connection state
   - Hard to diagnose failures

### What Works

✅ **Standalone test script** (`test_browser_connection.py`) works perfectly
✅ **Browser automation code** is solid (rugs_browser.py, automation.py)
✅ **Profile configuration** is correct (rugs_fun_phantom with Phantom extension)
✅ **Playwright integration** tested and verified

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│  REPLAYER UI (main_window.py)                       │
│  ├── Menu Bar                                       │
│  │   ├── File / Playback / Recording               │
│  │   ├── Bot (existing - uses BotController)       │
│  │   ├── Live Feed (existing - WebSocket)          │
│  │   └── Browser (NEW - Playwright automation)     │
│  │                                                  │
│  ├── Status Bar (NEW indicator)                    │
│  │   └── "BROWSER: ● Connected (rugs.fun)"         │
│  │                                                  │
│  └── Connection Dialog (browser_connection_dialog.py) │
│      ├── Profile selector                          │
│      ├── Options (visible mode, auto-wallet, navigate) │
│      ├── Progress log (real-time step feedback)   │
│      └── Connect / Cancel buttons                  │
└─────────────────────────────────────────────────────┘
         │
         │ Uses
         ▼
┌─────────────────────────────────────────────────────┐
│  BrowserExecutor (bot/browser_executor.py)          │
│  ├── start_browser() - Initialize and start        │
│  ├── stop_browser() - Clean shutdown               │
│  ├── is_ready() - Check connection state           │
│  └── click_buy/sell/sidebet() - Execute trades     │
└─────────────────────────────────────────────────────┘
         │
         │ Uses
         ▼
┌─────────────────────────────────────────────────────┐
│  RugsBrowserManager (browser_automation/rugs_browser.py) │
│  ├── start_browser() - Launch Chromium             │
│  ├── navigate_to_game() - Go to rugs.fun           │
│  ├── connect_wallet() - Auto-connect Phantom       │
│  └── stop_browser() - Cleanup                      │
└─────────────────────────────────────────────────────┘
```

---

## Implementation Plan - 7 Steps

### Step 1: Initialize BrowserExecutor (Always Available)

**File**: `src/ui/main_window.py` (lines 53-73)

**Current** (auto-start on --live):
```python
if self.live_mode:
    self.browser_executor = BrowserExecutor(...)
    self.root.after(1000, self._start_browser_async)  # AUTO-START ❌
```

**New** (initialize but don't auto-start):
```python
# Phase 8.5: Initialize browser executor (always available, user controls connection)
self.browser_executor = None
self.browser_connected = False

try:
    from bot.browser_executor import BrowserExecutor
    self.browser_executor = BrowserExecutor(profile_name="rugs_fun_phantom")
    logger.info("BrowserExecutor available - user can connect via Browser menu")
except Exception as e:
    logger.warning(f"BrowserExecutor not available: {e}")
    # Graceful degradation - Browser menu will show "Not Available"
```

**Benefits**:
- No auto-start (user control)
- Browser menu always visible (even if unavailable)
- Clear error messages in menu if unavailable

---

### Step 2: Add Browser Menu to Menu Bar

**File**: `src/ui/main_window.py` (in `_create_menu_bar` method)

**Location**: After "Live Feed" menu, before "Help" menu (line ~200)

**Code**:
```python
def _create_menu_bar(self):
    # ... existing menus (File, Playback, Recording, Bot, Live Feed) ...

    # ========== BROWSER MENU (Phase 8.5) ==========
    browser_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Browser", menu=browser_menu)

    # Check if browser executor available
    if self.browser_executor:
        # Connect command (enabled)
        browser_menu.add_command(
            label="Connect Browser...",
            command=lambda: self.root.after(0, self._show_browser_connection_dialog)
        )

        browser_menu.add_separator()

        # Status indicators (disabled, display only)
        browser_menu.add_command(
            label="⚫ Status: Not Connected",
            state=tk.DISABLED
        )

        browser_menu.add_command(
            label="Profile: rugs_fun_phantom",
            state=tk.DISABLED
        )

        browser_menu.add_separator()

        # Disconnect command (initially disabled)
        browser_menu.add_command(
            label="Disconnect Browser",
            command=self._disconnect_browser,
            state=tk.DISABLED
        )
    else:
        # Browser not available
        browser_menu.add_command(
            label="Browser automation not available",
            state=tk.DISABLED
        )
        browser_menu.add_command(
            label="(Check browser_automation/ directory)",
            state=tk.DISABLED
        )

    # Help menu
    # ... existing help menu ...
```

**Status Updates** (store menu item indices for later updates):
```python
def _create_menu_bar(self):
    # ... after creating browser_menu ...

    # Store menu item indices for status updates
    self.browser_menu = browser_menu
    self.browser_status_item_index = 2  # "⚫ Status: Not Connected"
    self.browser_disconnect_item_index = 5  # "Disconnect Browser"
```

---

### Step 3: Create Browser Connection Dialog

**File**: `src/ui/browser_connection_dialog.py` (NEW FILE - 450 lines)

**Key Features**:
- Profile dropdown (rugs_fun_phantom, rugs_observer)
- Options checkboxes (visible mode, auto-wallet, navigate)
- Progress log with real-time updates
- Async connection with thread safety
- Error handling with retry capability

**Complete implementation** (see design doc lines 152-335)

**Thread Safety**:
- All progress updates use `self.parent.after(0, ...)` to marshal to UI thread
- Async connection runs in background thread
- Dialog updates are thread-safe

---

### Step 4: Add Status Indicator to Status Bar

**File**: `src/ui/main_window.py` (in `_create_ui` method, line ~208)

**Current** (ROW 1: STATUS BAR):
```python
status_bar = tk.Frame(self.root, bg='#000000', height=30)
status_bar.pack(fill=tk.X)

# Tick (left)
self.tick_label = tk.Label(...)

# Price (center-left)
self.price_label = tk.Label(...)

# Phase (right)
self.phase_label = tk.Label(...)
```

**New** (add browser status):
```python
status_bar = tk.Frame(self.root, bg='#000000', height=30)
status_bar.pack(fill=tk.X)

# Tick (left)
self.tick_label = tk.Label(...)

# Price (center-left)
self.price_label = tk.Label(...)

# Phase (center-right)
self.phase_label = tk.Label(...)

# Browser status (right) - NEW
self.browser_status_label = tk.Label(
    status_bar,
    text="BROWSER: ⚫ Not Connected",
    font=('Arial', 9),
    bg='#000000',
    fg='#888888'  # Gray when disconnected
)
self.browser_status_label.pack(side=tk.RIGHT, padx=10)
```

**Status Updates**:
```python
def _update_browser_status(self, status, color):
    """Update browser status indicator"""
    status_icons = {
        'disconnected': '⚫',  # Gray
        'connecting': '🟡',   # Yellow
        'connected': '🟢',    # Green
        'error': '🔴'         # Red
    }

    colors = {
        'disconnected': '#888888',
        'connecting': '#ffcc00',
        'connected': '#00ff88',
        'error': '#ff3366'
    }

    icon = status_icons.get(status, '⚫')
    fg_color = colors.get(status, '#888888')
    text = f"BROWSER: {icon} {status.title()}"

    self.ui_dispatcher.submit(
        lambda: self.browser_status_label.config(text=text, fg=fg_color)
    )
```

---

### Step 5: Implement Connection/Disconnection Logic

**File**: `src/ui/main_window.py`

**Connection Method**:
```python
def _show_browser_connection_dialog(self):
    """Show browser connection wizard (Phase 8.5)"""
    if not self.browser_executor:
        messagebox.showerror(
            "Browser Not Available",
            "Browser automation is not available.\n\n"
            "Check that browser_automation/ directory exists."
        )
        return

    if self.browser_connected:
        messagebox.showinfo(
            "Already Connected",
            "Browser is already connected.\n\n"
            "Disconnect first before reconnecting."
        )
        return

    # Import dialog
    from ui.browser_connection_dialog import BrowserConnectionDialog

    # Show dialog
    dialog = BrowserConnectionDialog(
        parent=self.root,
        browser_executor=self.browser_executor,
        on_connected=self._on_browser_connected,
        on_failed=self._on_browser_connection_failed
    )
    dialog.show()
```

**Connection Success Callback**:
```python
def _on_browser_connected(self):
    """Called when browser connects successfully"""
    self.browser_connected = True

    # Update status bar
    self._update_browser_status('connected', '#00ff88')

    # Update menu (change status, enable disconnect)
    if self.browser_menu:
        self.browser_menu.entryconfig(
            self.browser_status_item_index,
            label="🟢 Status: Connected"
        )
        self.browser_menu.entryconfig(
            self.browser_disconnect_item_index,
            state=tk.NORMAL
        )

    logger.info("Browser connected successfully")
    if self.toast:
        self.toast.show("Browser connected to rugs.fun", "success")
```

**Disconnection Method**:
```python
def _disconnect_browser(self):
    """Disconnect browser (Phase 8.5)"""
    if not self.browser_connected:
        return

    # Confirm with user
    result = messagebox.askyesno(
        "Disconnect Browser",
        "Disconnect from live browser?\n\n"
        "This will close the browser window."
    )

    if not result:
        return

    # Stop browser in background thread
    import asyncio
    import threading

    def stop_async():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.browser_executor.stop_browser())
            logger.info("Browser stopped successfully")

            # Update UI on main thread
            self.root.after(0, self._on_browser_disconnected)
        except Exception as e:
            logger.error(f"Error stopping browser: {e}")
            self.root.after(
                0,
                lambda: messagebox.showerror("Disconnect Failed", str(e))
            )

    thread = threading.Thread(target=stop_async, daemon=True)
    thread.start()
```

**Disconnection Callback**:
```python
def _on_browser_disconnected(self):
    """Called when browser disconnects"""
    self.browser_connected = False

    # Update status bar
    self._update_browser_status('disconnected', '#888888')

    # Update menu (change status, disable disconnect)
    if self.browser_menu:
        self.browser_menu.entryconfig(
            self.browser_status_item_index,
            label="⚫ Status: Not Connected"
        )
        self.browser_menu.entryconfig(
            self.browser_disconnect_item_index,
            state=tk.DISABLED
        )

    logger.info("Browser disconnected")
    if self.toast:
        self.toast.show("Browser disconnected", "info")
```

---

### Step 6: Update Shutdown Logic

**File**: `src/ui/main_window.py` (in `shutdown` method, line ~1509)

**Current**:
```python
def shutdown(self):
    # Phase 8.5: Stop browser if in live mode
    if self.browser_executor:
        try:
            logger.info("Shutting down browser...")
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.browser_executor.stop_browser())
            logger.info("Browser stopped")
        except Exception as e:
            logger.error(f"Error stopping browser: {e}", exc_info=True)

    # ... rest of shutdown ...
```

**New** (only stop if connected):
```python
def shutdown(self):
    # Phase 8.5: Stop browser if connected
    if self.browser_connected and self.browser_executor:
        try:
            logger.info("Shutting down browser...")
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.browser_executor.stop_browser())
            logger.info("Browser stopped")
        except Exception as e:
            logger.error(f"Error stopping browser: {e}", exc_info=True)

    # ... rest of shutdown ...
```

---

### Step 7: Remove Auto-Start Logic

**File**: `src/ui/main_window.py` (lines 53-73)

**Remove**:
```python
# DELETE THIS ENTIRE BLOCK:
if self.live_mode:
    logger.info("Live mode enabled - initializing BrowserExecutor")
    try:
        self.browser_executor = BrowserExecutor(profile_name="rugs_fun_phantom")
        logger.info("BrowserExecutor initialized successfully")

        # Auto-start browser on initialization
        logger.info("Auto-starting browser for live mode...")
        self.root.after(1000, self._start_browser_async)  # ❌ DELETE

    except Exception as e:
        logger.error(f"Failed to initialize BrowserExecutor: {e}")
        # ... error dialog ...
```

**Replace with** (from Step 1):
```python
# Phase 8.5: Initialize browser executor (user controls connection via menu)
self.browser_executor = None
self.browser_connected = False

try:
    from bot.browser_executor import BrowserExecutor
    self.browser_executor = BrowserExecutor(profile_name="rugs_fun_phantom")
    logger.info("BrowserExecutor available - user can connect via Browser menu")
except Exception as e:
    logger.warning(f"BrowserExecutor not available: {e}")
```

---

## File Structure After Implementation

```
src/
├── ui/
│   ├── main_window.py (MODIFIED - add Browser menu, status bar, callbacks)
│   └── browser_connection_dialog.py (NEW - connection wizard)
│
├── bot/
│   └── browser_executor.py (NO CHANGES - already has needed methods)
│
└── config.py (NO CHANGES - profiles already configured)

browser_automation/ (NO CHANGES - already works)
├── rugs_browser.py
├── automation.py
└── persistent_profile.py
```

---

## Testing Plan

### Unit Tests

1. **Menu Creation**: Verify Browser menu appears
2. **Dialog Creation**: Verify connection dialog opens
3. **Status Updates**: Verify status indicators change correctly
4. **Connection Flow**: Mock connection and verify callbacks
5. **Disconnection**: Verify cleanup happens correctly

### Integration Tests

1. **Full Connection**: Open dialog, connect, verify status
2. **Error Handling**: Simulate connection failure, verify error display
3. **Retry**: Fail connection, retry, verify second attempt
4. **Disconnect**: Connect, then disconnect, verify cleanup
5. **Shutdown**: Connect, close app, verify browser closes

### Manual Testing

1. **Happy Path**: Connect → See browser open → Wallet connects → Status green
2. **Profile Missing**: Delete profile → Try connect → See error
3. **Wallet Manual**: Uncheck auto-wallet → Connect → Manually approve → Success
4. **Connection Retry**: Fail first time → Retry → Success
5. **Multiple Connections**: Try connect while already connected → See warning

---

## Edge Cases & Error Handling

### Edge Case 1: Browser Already Open
**Scenario**: User runs test_browser_connection.py, then opens REPLAYER
**Handling**: Check for existing browser process, show error dialog

### Edge Case 2: Profile Locked
**Scenario**: Another Chromium instance using same profile
**Handling**: Detect "Failed to create ProcessSingleton" error, show clear message

### Edge Case 3: Phantom Not Installed
**Scenario**: Extension directory missing
**Handling**: Show error in connection log, suggest checking extension path

### Edge Case 4: rugs.fun Down
**Scenario**: Website unreachable
**Handling**: Show navigation error, allow retry

### Edge Case 5: Connection Timeout
**Scenario**: Browser starts but hangs during connection
**Handling**: Add timeout (30s), show error, allow retry

---

## Migration Strategy

### Phase 1: Remove Auto-Start (Immediate)
- Remove `self.root.after(1000, self._start_browser_async)`
- User must manually connect via menu

### Phase 2: Add Browser Menu (Day 1)
- Add Browser menu to menu bar
- Add placeholder "Coming soon" dialog

### Phase 3: Implement Connection Dialog (Day 2)
- Create browser_connection_dialog.py
- Wire up to Browser menu

### Phase 4: Add Status Indicators (Day 3)
- Add browser status to status bar
- Update menu status on connect/disconnect

### Phase 5: Testing & Polish (Day 4)
- Comprehensive testing
- Error message improvements
- Documentation

---

## Success Criteria

✅ **User Control**: User decides when to connect (not auto-start)
✅ **Visual Feedback**: Progress visible for each connection step
✅ **Error Handling**: Clear messages when connection fails
✅ **Status Visibility**: Always know if browser is connected
✅ **Retry Capability**: Can retry failed connections
✅ **Clean Shutdown**: Browser closes cleanly on app exit
✅ **Thread Safe**: No UI freezes during async operations

---

## Documentation Updates

### User Documentation

**File**: `README.md`

Add section: "Connecting to Live Browser"

```markdown
## Connecting to Live Browser

REPLAYER can connect to a live Chromium browser for real-time trading.

### Setup

1. Ensure browser profile exists: `~/.gamebot/chromium_profiles/rugs_fun_phantom`
2. Ensure Phantom extension installed: `~/.gamebot/chromium_extensions/phantom`

### Connect

1. Launch REPLAYER: `./run.sh`
2. Click **Browser** → **Connect Browser...**
3. Select profile: `rugs_fun_phantom`
4. Click **Connect Browser**
5. Wait for connection steps to complete
6. Browser window will open and navigate to rugs.fun

### Status

Browser status is always visible:
- **Status Bar**: `BROWSER: 🟢 Connected`
- **Browser Menu**: `Status: Connected`

### Disconnect

1. Click **Browser** → **Disconnect Browser**
2. Confirm disconnect
3. Browser window will close
```

### Developer Documentation

**File**: `docs/PHASE_8_5_BROWSER_INTEGRATION.md`

Document internal architecture, threading model, error handling.

---

## Timeline

| Day | Task | Estimated Hours |
|-----|------|----------------|
| 1 | Remove auto-start, add Browser menu | 2h |
| 2 | Create connection dialog, wire up | 4h |
| 3 | Add status indicators, callbacks | 3h |
| 4 | Testing, bug fixes, polish | 3h |
| **Total** | **4 days** | **12 hours** |

---

## Risks & Mitigation

### Risk 1: Import Path Issues
**Mitigation**: Verified `sys.path` includes repo root in main.py (line 16)

### Risk 2: Thread Safety
**Mitigation**: All UI updates use `root.after(0, ...)` or `ui_dispatcher.submit()`

### Risk 3: Browser Crashes
**Mitigation**: Try/except around all browser operations, show errors in UI

### Risk 4: Profile Corruption
**Mitigation**: User can select different profile in dropdown

---

## Conclusion

This implementation provides:
- ✅ **Better debugging**: See each connection step
- ✅ **User control**: Connect when ready
- ✅ **Clear feedback**: Status always visible
- ✅ **Error recovery**: Retry failed connections
- ✅ **Production ready**: Thread-safe, robust error handling

Ready to proceed with implementation.
