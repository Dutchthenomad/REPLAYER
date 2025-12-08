# Phase 8.5: Browser Automation UI Design
## Menu-Based Approach for Better Debugging

### Problem Statement
Auto-starting browser on --live flag is difficult to debug. Need discrete, user-controlled steps.

### Solution: Menu-Based Browser Control

## Browser Menu Structure

```
Menu Bar:
├── File
├── Playback
├── Recording
├── Bot
├── Live Feed
├── Browser (NEW) ◄── Add this menu
│   ├── Connect Browser... (launches connection wizard)
│   ├── ─────────────
│   ├──  Status: Not Connected (disabled, shows status)
│   ├──  Profile: rugs_fun_phantom (disabled, shows current profile)
│   ├── ─────────────
│   ├── Disconnect Browser (disabled when not connected)
│   └── Browser Settings...
└── Help
```

## Connection Wizard Flow

When user clicks "Browser → Connect Browser...":

### Dialog Window: "Connect to Live Browser"

```
┌─────────────────────────────────────────┐
│ Connect to Rugs.fun Browser             │
├─────────────────────────────────────────┤
│                                         │
│  Profile:  [rugs_fun_phantom   ▼]      │
│                                         │
│  [✓] Open browser in visible mode      │
│  [✓] Auto-connect Phantom wallet       │
│  [✓] Navigate to rugs.fun              │
│                                         │
│  Status: Ready to connect               │
│                                         │
│  [ Connect Browser ]  [ Cancel ]       │
│                                         │
└─────────────────────────────────────────┘
```

### Connection Steps (with progress indicators)

```
Step 1: Starting browser...
  ├── Initializing RugsBrowserManager
  ├── Loading profile: rugs_fun_phantom
  ├── Loading Phantom extension
  └── ✓ Browser started

Step 2: Navigating to rugs.fun...
  ├── Opening https://rugs.fun
  ├── Waiting for page load
  └── ✓ Page loaded

Step 3: Connecting wallet...
  ├── Checking existing connection
  ├── Clicking Connect button
  ├── Selecting Phantom
  ├── Waiting for approval
  └── ✓ Wallet connected (or ⚠ Manual action needed)

Status: ✓ Connected and Ready
```

## Status Indicators

### Status Bar Addition
```
┌────────────────────────────────────────────────────────┐
│ TICK: 0  |  PRICE: 1.0000 X  |  PHASE: UNKNOWN        │
│ BROWSER: ● Connected (rugs.fun) ◄── Add this          │
└────────────────────────────────────────────────────────┘
```

**Status Colors:**
- ⚫ Gray: Not connected
- 🟡 Yellow: Connecting...
- 🔴 Red: Connection failed
- 🟢 Green: Connected

## Implementation Plan

### Files to Modify

1. **`src/ui/main_window.py`** - Add Browser menu
2. **`src/ui/browser_connection_dialog.py`** (NEW) - Connection wizard
3. **`src/bot/browser_executor.py`** - Expose status methods
4. **`src/config.py`** - Add browser profiles configuration

### Menu Implementation (`main_window.py`)

```python
def _create_menu_bar(self):
    # ... existing menus ...

    # Browser Menu (Phase 8.5)
    browser_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Browser", menu=browser_menu)

    # Connect command
    browser_menu.add_command(
        label="Connect Browser...",
        command=self._show_browser_connection_dialog
    )

    browser_menu.add_separator()

    # Status indicators (disabled, just for display)
    self.browser_status_label = tk.StringVar(value="● Not Connected")
    browser_menu.add_command(
        label="Status: Not Connected",
        state=tk.DISABLED
    )

    self.browser_profile_label = tk.StringVar(value="Profile: None")
    browser_menu.add_command(
        label="Profile: None",
        state=tk.DISABLED
    )

    browser_menu.add_separator()

    # Disconnect command
    self.disconnect_browser_item = browser_menu.add_command(
        label="Disconnect Browser",
        command=self._disconnect_browser,
        state=tk.DISABLED
    )

    browser_menu.add_separator()
    browser_menu.add_command(
        label="Browser Settings...",
        command=self._show_browser_settings
    )
```

### Connection Dialog (`browser_connection_dialog.py`)

```python
class BrowserConnectionDialog:
    """
    Connection wizard for browser automation

    Shows step-by-step progress with visual feedback
    """

    def __init__(self, parent, browser_executor):
        self.parent = parent
        self.browser_executor = browser_executor
        self.dialog = None
        self.progress_text = None
        self.connect_button = None

    def show(self):
        """Show connection dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Connect to Live Browser")
        self.dialog.geometry("500x400")

        # Profile selection
        profile_frame = ttk.Frame(self.dialog, padding=10)
        profile_frame.pack(fill=tk.X)

        ttk.Label(profile_frame, text="Profile:").pack(side=tk.LEFT)
        self.profile_var = tk.StringVar(value="rugs_fun_phantom")
        profile_dropdown = ttk.Combobox(
            profile_frame,
            textvariable=self.profile_var,
            values=["rugs_fun_phantom", "rugs_observer"],
            state='readonly'
        )
        profile_dropdown.pack(side=tk.LEFT, padx=10)

        # Options
        options_frame = ttk.Frame(self.dialog, padding=10)
        options_frame.pack(fill=tk.X)

        self.visible_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Open browser in visible mode",
            variable=self.visible_var
        ).pack(anchor=tk.W)

        self.auto_wallet_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Auto-connect Phantom wallet",
            variable=self.auto_wallet_var
        ).pack(anchor=tk.W)

        self.navigate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Navigate to rugs.fun",
            variable=self.navigate_var
        ).pack(anchor=tk.W)

        # Progress display
        progress_frame = ttk.Frame(self.dialog, padding=10)
        progress_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(progress_frame, text="Status:").pack(anchor=tk.W)

        self.progress_text = tk.Text(
            progress_frame,
            height=15,
            width=60,
            state='disabled',
            bg='#f0f0f0',
            font=('Courier', 9)
        )
        self.progress_text.pack(fill=tk.BOTH, expand=True)

        # Buttons
        button_frame = ttk.Frame(self.dialog, padding=10)
        button_frame.pack(fill=tk.X)

        self.connect_button = ttk.Button(
            button_frame,
            text="Connect Browser",
            command=self._start_connection
        )
        self.connect_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy
        ).pack(side=tk.LEFT)

        # Center dialog
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

    def _log_progress(self, message, status="info"):
        """Add message to progress display"""
        self.progress_text.config(state='normal')

        # Color codes
        colors = {
            'info': '',
            'success': '✓ ',
            'error': '✗ ',
            'warning': '⚠ '
        }

        prefix = colors.get(status, '')
        self.progress_text.insert(tk.END, f"{prefix}{message}\n")
        self.progress_text.see(tk.END)
        self.progress_text.config(state='disabled')
        self.dialog.update()

    async def _connect_async(self):
        """Async connection process"""
        try:
            # Step 1: Start browser
            self._log_progress("Step 1: Starting browser...")
            self._log_progress("  Initializing RugsBrowserManager")

            profile = self.profile_var.get()
            self._log_progress(f"  Loading profile: {profile}")
            self._log_progress("  Loading Phantom extension")

            success = await self.browser_executor.start_browser()
            if not success:
                self._log_progress("Browser failed to start", "error")
                return False

            self._log_progress("Browser started successfully!", "success")

            # Step 2: Navigate
            if self.navigate_var.get():
                self._log_progress("\nStep 2: Navigating to rugs.fun...")
                self._log_progress("  Opening https://rugs.fun")

                nav_success = await self.browser_executor.browser_manager.navigate_to_game()
                if nav_success:
                    self._log_progress("Page loaded successfully!", "success")
                else:
                    self._log_progress("Navigation unclear - check browser", "warning")

            # Step 3: Connect wallet
            if self.auto_wallet_var.get():
                self._log_progress("\nStep 3: Connecting wallet...")
                self._log_progress("  Checking existing connection")
                self._log_progress("  Looking for Connect button")

                wallet_success = await self.browser_executor.browser_manager.connect_wallet()
                if wallet_success:
                    self._log_progress("Wallet connected successfully!", "success")
                else:
                    self._log_progress("Wallet connection unclear - may need manual approval", "warning")

            self._log_progress("\n" + "="*50, "success")
            self._log_progress("✓ Connection Complete!", "success")
            self._log_progress("Browser is ready for trading", "success")

            return True

        except Exception as e:
            self._log_progress(f"\nConnection failed: {e}", "error")
            return False

    def _start_connection(self):
        """Start connection in background thread"""
        import asyncio
        import threading

        self.connect_button.config(state='disabled')
        self._log_progress("Starting connection process...\n")

        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._connect_async())

            # Re-enable button
            self.parent.after(0, lambda: self.connect_button.config(state='normal'))

        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
```

## Benefits of This Approach

1. **Better Debugging**: See each step execute
2. **User Control**: Connect only when ready
3. **Status Visibility**: Always know connection state
4. **Error Handling**: Clear feedback when things fail
5. **No Auto-Start**: User decides when to connect
6. **Progress Tracking**: See what's happening in real-time

## Migration from --live Flag

**Old Approach**:
```bash
./run.sh --live  # Auto-connects (hard to debug)
```

**New Approach**:
```bash
./run.sh         # Normal mode
# Then: Browser → Connect Browser... (user control)
```

**Keep --live flag for backwards compatibility**, but it just enables the Browser menu (doesn't auto-connect).

## Next Steps

1. Remove auto-start logic from main_window.py
2. Create browser_connection_dialog.py
3. Add Browser menu to menu bar
4. Add status indicators
5. Test step-by-step connection
6. Document user workflow
