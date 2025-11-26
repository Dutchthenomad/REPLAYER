# Phase 9: Live Browser Integration - Implementation Guide

**Status**: In Progress
**Created**: 2025-11-20
**Estimated Completion**: 7-11 hours across 4 phases

---

## Progress Tracker

### Phase 1: Session-Persistent Balance System (2-3 hours)
- [x] **1.1** Create `session_state.py` with persistence logic ✅
- [x] **1.2** Update `bot_config.json` with `default_balance_sol` field ✅
- [x] **1.3** Create `balance_edit_dialog.py` with unlock/relock dialogs ✅
- [ ] **1.4** Integrate session state into `main.py` startup
- [ ] **1.5** Add balance lock/unlock toggle to `main_window.py`
- [ ] **1.6** Wire P&L updates to auto-save session state
- [ ] **1.7** Add default balance field to `bot_config_panel.py`
- [ ] **1.8** Test balance persistence across restarts

### Phase 2: Live Mode Toggle & Browser Connection (2-3 hours)
- [ ] **2.1** Add "Mode" menu to `main_window.py`
- [ ] **2.2** Create `live_mode_toast.py` for warning notification
- [ ] **2.3** Implement live mode activation flow
- [ ] **2.4** Implement live mode deactivation flow
- [ ] **2.5** Add safety interlocks
- [ ] **2.6** Add visual indicators (red checkbox, yellow balance)
- [ ] **2.7** Test activation/deactivation flow

### Phase 3: Button Click Forwarding (1-2 hours)
- [ ] **3.1** Modify button handlers in `main_window.py`
- [ ] **3.2** Create `_forward_*_to_browser()` methods
- [ ] **3.3** Add 🌐 icons to buttons when live mode active
- [ ] **3.4** Enhance console logging for live actions
- [ ] **3.5** Test button forwarding (BUY, SELL, increments)

### Phase 4: Selector Validation & Safety (2-3 hours)
- [ ] **4.1** Create `validate_selectors.py` script
- [ ] **4.2** Enhance `browser_executor.py` with fallback selectors
- [ ] **4.3** Add retry logic to browser actions
- [ ] **4.4** Add loss limit checking
- [ ] **4.5** Add emergency stop button
- [ ] **4.6** Add action validation (verify position opened)
- [ ] **4.7** Add deadlock detection
- [ ] **4.8** Test validation script and safety mechanisms

---

## Implementation Details

### Phase 1.4: Integrate Session State into main.py

**File**: `src/main.py`

**Current Code** (lines ~30-50):
```python
# Initialize state
state = GameState(event_bus)
```

**Add After**:
```python
# Initialize session state (Phase 9.1)
from core.session_state import SessionState

# Get default balance from bot config
bot_config_file = Path("bot_config.json")
default_balance = Decimal('0.01')
if bot_config_file.exists():
    with open(bot_config_file) as f:
        bot_config = json.load(f)
        default_balance = Decimal(str(bot_config.get('default_balance_sol', 0.01)))

session_state = SessionState(default_balance=default_balance)

# Set initial balance from session state
state.update(balance=session_state.get_balance())
logger.info(f"Loaded session balance: {session_state.get_balance():.4f} SOL")
```

**Pass to MainWindow**:
```python
# Current:
window = MainWindow(root, state, event_bus, config)

# Updated:
window = MainWindow(root, state, event_bus, config, session_state=session_state)
```

---

### Phase 1.5: Add Balance Lock/Unlock Toggle to main_window.py

**File**: `src/ui/main_window.py`

**Step 1: Add to __init__ (after line 51)**:
```python
self.session_state = session_state  # Phase 9.1
self.balance_locked = True  # Default: locked (P&L tracking)
self.balance_edit_widget = None  # Placeholder for edit entry
```

**Step 2: Modify balance label creation (replace lines 480-487)**:

**Before**:
```python
self.balance_label = tk.Label(
    bet_row,
    text=f"WALLET: {self.state.get('balance'):.3f}",
    font=('Arial', 11, 'bold'),
    bg='#1a1a1a',
    fg='#ffcc00'
)
self.balance_label.pack(side=tk.RIGHT, padx=10)
```

**After**:
```python
# Balance display with lock/unlock toggle (Phase 9.1)
balance_frame = tk.Frame(bet_row, bg='#1a1a1a')
balance_frame.pack(side=tk.RIGHT, padx=10)

self.balance_label = tk.Label(
    balance_frame,
    text=f"WALLET: {self.state.get('balance'):.3f}",
    font=('Arial', 11, 'bold'),
    bg='#1a1a1a',
    fg='#ffcc00'
)
self.balance_label.pack(side=tk.LEFT)

# Lock/unlock toggle button (Phase 9.1)
self.balance_lock_button = tk.Button(
    balance_frame,
    text="🔒",
    command=self._toggle_balance_lock,
    bg='#333333',
    fg='white',
    font=('Arial', 14),
    width=2,
    relief=tk.FLAT,
    cursor='hand2'
)
self.balance_lock_button.pack(side=tk.LEFT, padx=5)
```

**Step 3: Add lock/unlock methods (add after balance label code, around line 650)**:

```python
def _toggle_balance_lock(self):
    """Toggle balance lock/unlock (Phase 9.1)."""
    if self.balance_locked:
        # Unlock balance for manual editing
        self._unlock_balance()
    else:
        # Re-lock balance
        self._relock_balance()

def _unlock_balance(self):
    """Unlock balance for manual editing (Phase 9.1)."""
    from ui.balance_edit_dialog import BalanceUnlockDialog

    current_balance = self.state.get('balance')

    def on_confirm():
        """User confirmed unlock."""
        # Hide label, show entry
        self.balance_label.pack_forget()

        # Create inline edit entry
        from ui.balance_edit_dialog import BalanceEditEntry
        self.balance_edit_widget = BalanceEditEntry(
            parent=self.balance_label.master,  # Use same parent frame
            current_balance=current_balance,
            on_save=self._on_balance_save,
            on_cancel=self._on_balance_cancel
        )
        self.balance_edit_widget.pack(side=tk.LEFT)

        # Update lock button
        self.balance_lock_button.config(text="🔓")
        self.balance_locked = False

        logger.info("Balance unlocked for manual editing")

    # Show unlock confirmation dialog
    BalanceUnlockDialog(self.root, current_balance, on_confirm)

def _on_balance_save(self, new_balance: Decimal):
    """Save manually edited balance (Phase 9.1)."""
    # Update session state (manual override)
    self.session_state.set_balance_manual(new_balance)

    # Update game state
    self.state.update(balance=new_balance)

    # Destroy edit widget, show label
    if self.balance_edit_widget:
        self.balance_edit_widget.destroy()
        self.balance_edit_widget = None

    self.balance_label.config(text=f"WALLET: {new_balance:.3f}")
    self.balance_label.pack(side=tk.LEFT)

    logger.info(f"Balance manually set to {new_balance:.4f} SOL")

def _on_balance_cancel(self):
    """Cancel balance edit (Phase 9.1)."""
    # Destroy edit widget, show label
    if self.balance_edit_widget:
        self.balance_edit_widget.destroy()
        self.balance_edit_widget = None

    self.balance_label.pack(side=tk.LEFT)

    logger.info("Balance edit canceled")

def _relock_balance(self):
    """Re-lock balance to P&L tracking (Phase 9.1)."""
    from ui.balance_edit_dialog import BalanceRelockDialog

    manual_balance = self.state.get('balance')
    tracked_balance = manual_balance  # In this case, they're the same (user already saved)

    def on_choice(choice: str):
        """Handle user's choice."""
        if choice == 'keep_manual':
            # Keep manual value, resume P&L tracking from new baseline
            self.session_state.set_balance_manual(manual_balance)
        elif choice == 'revert_to_pnl':
            # Revert to tracked balance (in this case, same as manual)
            # Future: Could track "what balance WOULD be without manual override"
            pass

        # Update lock button
        self.balance_lock_button.config(text="🔒")
        self.balance_locked = True

        logger.info(f"Balance re-locked (choice: {choice})")

    # Show relock dialog
    BalanceRelockDialog(self.root, manual_balance, tracked_balance, on_choice)
```

---

### Phase 1.6: Wire P&L Updates to Auto-Save Session State

**File**: `src/ui/main_window.py`

**Find the balance update callback** (around line 1245):
```python
lambda: self.balance_label.config(text=f"Balance: {new_balance:.4f} SOL")
```

**Enhance to save session state**:
```python
def _on_balance_changed(self, data):
    """Handle balance change event (Phase 9.1 enhanced)."""
    new_balance = data.get('balance')

    # Update UI
    self.ui_dispatcher.submit(
        lambda: self.balance_label.config(text=f"WALLET: {new_balance:.3f}")
    )

    # Auto-save to session state (if locked/tracking P&L)
    if self.balance_locked and hasattr(self, 'session_state'):
        # Calculate P&L delta
        # Note: session_state tracks cumulative changes
        # Game state update already happened, just persist it
        self.session_state.balance_sol = new_balance
        self.session_state.save()
        logger.debug(f"Session state auto-saved: balance={new_balance:.4f} SOL")
```

**Subscribe to balance change event** (in __init__, around line 140):
```python
# Subscribe to state change events
self.state.subscribe('balance_changed', self._on_balance_changed)
```

---

### Phase 1.7: Add Default Balance Field to bot_config_panel.py

**File**: `src/ui/bot_config_panel.py`

**Find the strategy dropdown** (around line 150):
```python
ttk.Label(form_frame, text="Strategy:").grid(row=0, column=0, sticky='w', pady=5)
self.strategy_var = tk.StringVar(value=self.config.get('strategy', 'conservative'))
```

**Add after** (new row):
```python
# Default Balance (Phase 9.1)
ttk.Label(form_frame, text="Default Balance (SOL):").grid(row=3, column=0, sticky='w', pady=5)
self.default_balance_var = tk.StringVar(value=str(self.config.get('default_balance_sol', 0.01)))
default_balance_entry = ttk.Entry(form_frame, textvariable=self.default_balance_var, width=10)
default_balance_entry.grid(row=3, column=1, sticky='w', pady=5)

# Help text
help_label = ttk.Label(
    form_frame,
    text="Initial balance for new sessions (can be overridden with balance lock toggle)",
    font=('TkDefaultFont', 8),
    foreground='gray'
)
help_label.grid(row=4, column=0, columnspan=2, sticky='w', pady=(0, 10))
```

**Update save method** (around line 250):
```python
def save(self):
    """Save configuration to JSON file."""
    try:
        self.config['default_balance_sol'] = float(self.default_balance_var.get())
    except ValueError:
        messagebox.showerror("Invalid Value", "Default balance must be a number")
        return False

    # ... rest of save logic
```

---

## Testing Checklist

### Phase 1 Tests

**Test 1: Session Persistence**
- [  ] Start app → Balance is 0.01 SOL (default)
- [ ] Execute trade with +0.05 SOL profit → Balance becomes 0.06 SOL
- [ ] Close app
- [ ] Restart app → Balance still 0.06 SOL ✅

**Test 2: Manual Override**
- [ ] Click 🔒 lock icon → Unlock dialog appears
- [ ] Confirm unlock → Balance becomes editable entry
- [ ] Type "1.5" + Enter → Balance updates to 1.5 SOL
- [ ] Click 🔓 unlock icon → Re-lock dialog appears
- [ ] Choose "Keep Manual" → Balance stays 1.5 SOL
- [ ] Execute trade with -0.2 SOL loss → Balance becomes 1.3 SOL ✅

**Test 3: Config Default**
- [ ] Open Bot → Configuration
- [ ] Set "Default Balance" to 0.1 SOL
- [ ] Save config
- [ ] Delete `~/.config/replayer/session_state.json`
- [ ] Restart app → Balance is 0.1 SOL ✅

---

## Files Created (Phase 1)

- [x] `src/core/session_state.py` (230 lines)
- [x] `src/ui/balance_edit_dialog.py` (290 lines)
- [x] `docs/PHASE_9_IMPLEMENTATION_GUIDE.md` (this file)

## Files Modified (Phase 1)

- [x] `src/bot_config.json` - Added `default_balance_sol` field
- [ ] `src/main.py` - Load session state on startup
- [ ] `src/ui/main_window.py` - Balance lock/unlock toggle + auto-save
- [ ] `src/ui/bot_config_panel.py` - Default balance field

---

## Next Steps

1. Complete Phase 1.4-1.8 (integrate into main files)
2. Test Phase 1 thoroughly
3. Proceed to Phase 2 (Live Mode Toggle)
4. Continue through Phases 3-4

**Current Status**: Phase 1 infrastructure complete (session_state.py, dialog files). Ready to integrate into main application files.
