"""
Browser Connection Dialog - Phase 8.5
Connection wizard for browser automation with step-by-step progress
"""

import tkinter as tk
from tkinter import ttk
import asyncio
import threading
import logging

logger = logging.getLogger(__name__)


class BrowserConnectionDialog:
    """
    Connection wizard for browser automation

    Shows step-by-step progress with visual feedback:
    - Profile selection dropdown
    - Option checkboxes (visible mode, auto-wallet, navigate)
    - Real-time progress log
    - Thread-safe async connection
    """

    def __init__(self, parent, browser_executor, on_connected=None, on_failed=None):
        """
        Initialize connection dialog

        Args:
            parent: Parent tkinter window
            browser_executor: BrowserExecutor instance
            on_connected: Callback when connection succeeds
            on_failed: Callback when connection fails
        """
        self.parent = parent
        self.browser_executor = browser_executor
        self.on_connected = on_connected
        self.on_failed = on_failed

        self.dialog = None
        self.progress_text = None
        self.connect_button = None
        self.cancel_button = None

    def show(self):
        """Show connection dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Connect to Live Browser")
        self.dialog.geometry("600x500")

        # Profile selection
        profile_frame = ttk.Frame(self.dialog, padding=10)
        profile_frame.pack(fill=tk.X)

        ttk.Label(profile_frame, text="Profile:").pack(side=tk.LEFT)
        self.profile_var = tk.StringVar(value="rugs_fun_phantom")
        profile_dropdown = ttk.Combobox(
            profile_frame,
            textvariable=self.profile_var,
            values=["rugs_fun_phantom", "rugs_observer"],
            state='readonly',
            width=20
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

        ttk.Label(progress_frame, text="Connection Progress:").pack(anchor=tk.W)

        # Scrollable text widget
        text_scroll_frame = ttk.Frame(progress_frame)
        text_scroll_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_scroll_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.progress_text = tk.Text(
            text_scroll_frame,
            height=18,
            width=70,
            state='disabled',
            bg='#f0f0f0',
            font=('Courier', 9),
            yscrollcommand=scrollbar.set
        )
        self.progress_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.progress_text.yview)

        # Initial message
        self._log_progress("Ready to connect to Rugs.fun browser.", "info")
        self._log_progress("Click 'Connect Browser' to begin.", "info")

        # Buttons
        button_frame = ttk.Frame(self.dialog, padding=10)
        button_frame.pack(fill=tk.X)

        self.connect_button = ttk.Button(
            button_frame,
            text="Connect Browser",
            command=self._start_connection
        )
        self.connect_button.pack(side=tk.LEFT, padx=5)

        self.cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy
        )
        self.cancel_button.pack(side=tk.LEFT)

        # Center dialog
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

    def _log_progress(self, message, status="info"):
        """
        Add message to progress display

        Args:
            message: Message to log
            status: "info", "success", "error", "warning"
        """
        self.progress_text.config(state='normal')

        # Color prefixes
        prefixes = {
            'info': '  ',
            'success': '✓ ',
            'error': '✗ ',
            'warning': '⚠ '
        }

        prefix = prefixes.get(status, '  ')
        self.progress_text.insert(tk.END, f"{prefix}{message}\n")
        self.progress_text.see(tk.END)
        self.progress_text.config(state='disabled')
        self.dialog.update()

    async def _connect_async(self):
        """
        Async connection process

        Returns:
            bool: True if connection succeeded, False otherwise
        """
        try:
            # Step 1: Start browser
            self._log_progress("\nStep 1: Starting browser...", "info")
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
                self._log_progress("\nStep 2: Navigating to rugs.fun...", "info")
                self._log_progress("  Opening https://rugs.fun")

                nav_success = await self.browser_executor.browser_manager.navigate_to_game()
                if nav_success:
                    self._log_progress("Page loaded successfully!", "success")
                else:
                    self._log_progress("Navigation unclear - check browser", "warning")

            # Step 3: Connect wallet
            if self.auto_wallet_var.get():
                self._log_progress("\nStep 3: Connecting wallet...", "info")
                self._log_progress("  Checking existing connection")
                self._log_progress("  Looking for Connect button")

                wallet_success = await self.browser_executor.browser_manager.connect_wallet()
                if wallet_success:
                    self._log_progress("Wallet connected successfully!", "success")
                else:
                    self._log_progress("Wallet connection unclear - may need manual approval", "warning")

            self._log_progress("\n" + "="*60, "info")
            self._log_progress("✓ Connection Complete!", "success")
            self._log_progress("Browser is ready for trading", "success")
            self._log_progress("="*60, "info")

            return True

        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            self._log_progress(f"\nConnection failed: {e}", "error")
            self._log_progress("See logs for details", "error")
            return False

    def _start_connection(self):
        """Start connection in background thread"""
        # Disable buttons during connection
        self.connect_button.config(state='disabled')
        self.cancel_button.config(state='disabled')

        self._log_progress("\n" + "="*60, "info")
        self._log_progress("Starting connection process...", "info")
        self._log_progress("="*60, "info")

        def run_async():
            """Run async connection in background thread"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                result = loop.run_until_complete(self._connect_async())

                # Update UI on main thread
                self.parent.after(0, lambda: self._connection_finished(result))
            except Exception as e:
                logger.error(f"Async connection error: {e}", exc_info=True)
                self.parent.after(
                    0,
                    lambda: self._connection_finished(False, str(e))
                )
            finally:
                loop.close()

        # Start in background thread
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()

    def _connection_finished(self, success, error=None):
        """
        Called when connection finishes (on main thread)

        Args:
            success: Whether connection succeeded
            error: Error message if failed
        """
        # Re-enable cancel button (connect button stays disabled after success)
        self.cancel_button.config(state='normal')

        if success:
            # Call success callback
            if self.on_connected:
                self.on_connected()

            # Close dialog after brief delay
            self.parent.after(1500, self.dialog.destroy)
        else:
            # Re-enable connect button to allow retry
            self.connect_button.config(state='normal')

            # Call failure callback
            if self.on_failed:
                self.on_failed(error)

            # AUDIT FIX: Auto-close dialog after 30 seconds to prevent memory leak
            self.parent.after(30000, self._check_and_destroy)

    def _check_and_destroy(self):
        """Check if dialog still exists and destroy it to prevent memory leak"""
        if self.dialog and self.dialog.winfo_exists():
            logger.info("Auto-closing browser connection dialog after timeout")
            self.dialog.destroy()
