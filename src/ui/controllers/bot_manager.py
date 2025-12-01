"""
BotManager Controller

Extracted from MainWindow (Phase 3.1)
Handles bot lifecycle, configuration, timing metrics, and monitoring.

Responsibilities:
- Bot enable/disable lifecycle
- Strategy selection and updates
- Bot configuration dialog
- Timing metrics display and updates  
- Bot results monitoring
"""

import logging
import tkinter as tk
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class BotManager:
    """
    Manages bot lifecycle, configuration, and monitoring.
    
    Extracted from MainWindow to follow Single Responsibility Principle.
    """
    
    def __init__(
        self,
        root: tk.Tk,
        state,
        bot_executor,
        bot_controller,
        bot_config_panel,
        timing_overlay,
        browser_executor,
        # UI widgets
        bot_toggle_button: tk.Button,
        bot_status_label: tk.Label,
        buy_button: tk.Button,
        sell_button: tk.Button,
        sidebet_button: tk.Button,
        strategy_var: tk.StringVar,
        bot_var: tk.BooleanVar,
        timing_overlay_var: tk.BooleanVar,
        # Callbacks
        log_callback: Callable[[str], None],
        # Notifications
        toast: Optional[object] = None
    ):
        """Initialize BotManager with dependencies"""
        self.root = root
        self.state = state
        self.bot_executor = bot_executor
        self.bot_controller = bot_controller
        self.bot_config_panel = bot_config_panel
        self.timing_overlay = timing_overlay
        self.browser_executor = browser_executor
        
        # UI widgets
        self.bot_toggle_button = bot_toggle_button
        self.bot_status_label = bot_status_label
        self.buy_button = buy_button
        self.sell_button = sell_button
        self.sidebet_button = sidebet_button
        self.strategy_var = strategy_var
        self.bot_var = bot_var
        self.timing_overlay_var = timing_overlay_var
        
        # Callbacks
        self.log = log_callback
        self.toast = toast
        
        # State
        self.bot_enabled = False
        
        # Start monitoring loops
        self._start_monitoring()
    
    def _start_monitoring(self):
        """Start periodic monitoring loops"""
        self.root.after(100, self._check_bot_results)
        self.root.after(1000, self._update_timing_metrics_loop)
    
    # ========================================================================
    # BOT LIFECYCLE
    # ========================================================================
    
    def toggle_bot(self):
        """Toggle bot enable/disable"""
        self.bot_enabled = not self.bot_enabled

        if self.bot_enabled:
            # Start async bot executor
            self.bot_executor.start()

            self.bot_toggle_button.config(
                text="🤖 Disable Bot",
                bg='#ff3366'
            )
            self.bot_status_label.config(
                text=f"Bot: ACTIVE ({self.strategy_var.get()})",
                fg='#00ff88'
            )
            # Disable manual trading when bot is active
            self.buy_button.config(state=tk.DISABLED)
            self.sell_button.config(state=tk.DISABLED)
            self.sidebet_button.config(state=tk.DISABLED)
            self.log(f"🤖 Bot enabled with {self.strategy_var.get()} strategy (async mode)")
        else:
            # Stop async bot executor
            self.bot_executor.stop()

            self.bot_toggle_button.config(
                text="🤖 Enable Bot",
                bg='#666666'
            )
            self.bot_status_label.config(
                text="Bot: Disabled",
                fg='#666666'
            )

            # Bug 5 Fix: Re-enable manual trading buttons when bot is disabled
            # (but only if game is active)
            current_tick = self.state.get('current_tick')
            if current_tick and current_tick.active:
                self.buy_button.config(state=tk.NORMAL)
                self.sell_button.config(state=tk.NORMAL)
                self.sidebet_button.config(state=tk.NORMAL)

            self.log("🤖 Bot disabled")

        # Bug 4 Fix: Sync menu checkbox with bot state
        self.bot_var.set(self.bot_enabled)
    
    def toggle_bot_from_menu(self):
        """
        Toggle bot enable/disable from menu (syncs with button)
        AUDIT FIX: Ensure all UI updates happen in main thread
        """
        def do_toggle():
            self.toggle_bot()
            # Sync menu checkbutton state with actual bot state
            self.bot_var.set(self.bot_enabled)

        # AUDIT FIX: Defensive - ensure always runs in main thread
        self.root.after(0, do_toggle)
    
    def on_strategy_changed(self, event=None):
        """Handle strategy selection change"""
        from bot import get_strategy

        strategy_name = self.strategy_var.get()
        try:
            # Update bot controller with new strategy
            strategy = get_strategy(strategy_name)
            self.bot_controller.strategy = strategy
            self.log(f"Strategy changed to: {strategy_name}")

            # Update status if bot is active
            if self.bot_enabled:
                self.bot_status_label.config(
                    text=f"Bot: ACTIVE ({strategy_name})"
                )
        except Exception as e:
            self.log(f"Failed to change strategy: {e}")
    
    # ========================================================================
    # BOT CONFIGURATION
    # ========================================================================
    
    def show_bot_config(self):
        """
        Show bot configuration dialog (Phase 8.4)
        Thread-safe via root.after()
        """
        try:
            # Show configuration dialog (modal)
            updated_config = self.bot_config_panel.show()

            # If user clicked OK (not cancelled)
            if updated_config:
                self.log("Bot configuration updated - restart required for changes to take effect")

                # Inform user that restart is needed
                if self.toast:
                    self.toast.show(
                        "Configuration updated. Restart required.",
                        duration=5000,
                        bootstyle="warning"
                    )

                # Note: We don't update bot at runtime to avoid complexity
                # User needs to restart application for changes to take effect

        except Exception as e:
            logger.error(f"Failed to show bot config: {e}", exc_info=True)
            self.log(f"Error showing configuration: {e}")
    
    # ========================================================================
    # TIMING METRICS
    # ========================================================================
    
    def toggle_timing_overlay(self):
        """
        Toggle timing overlay widget visibility (Phase A)
        Shows/hides the draggable timing metrics overlay
        """
        def do_toggle():
            if self.timing_overlay_var.get():
                # Show overlay
                self.timing_overlay.show()
                self.log("Timing overlay shown")
            else:
                # Hide overlay
                self.timing_overlay.hide()
                self.log("Timing overlay hidden")

        # Ensure always runs in main thread
        self.root.after(0, do_toggle)
    
    def show_timing_metrics(self):
        """
        Show detailed timing metrics window (Phase 8.6 - Option C)
        Modal popup with full statistics
        """
        if not self.browser_executor:
            from tkinter import messagebox
            messagebox.showinfo(
                "Timing Metrics",
                "Timing metrics are only available when browser executor is active.\n\n"
                "Enable browser connection first."
            )
            return

        # Get timing stats
        stats = self.browser_executor.get_timing_stats()

        # Create modal dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Bot Timing Metrics")
        dialog.geometry("400x350")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Main container
        main_frame = tk.Frame(dialog, bg='#1a1a1a', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = tk.Label(
            main_frame,
            text="Execution Timing Statistics",
            font=('Arial', 14, 'bold'),
            bg='#1a1a1a',
            fg='#ffffff'
        )
        title_label.pack(pady=(0, 15))

        # Stats frame
        stats_frame = tk.Frame(main_frame, bg='#2a2a2a', relief=tk.RIDGE, bd=2)
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Format stats as labels
        stats_text = [
            ("Total Executions:", f"{stats['total_executions']}"),
            ("Successful:", f"{stats['successful_executions']}"),
            ("Success Rate:", f"{stats['success_rate']:.1%}"),
            ("", ""),
            ("Average Total Delay:", f"{stats['avg_total_delay_ms']:.1f}ms"),
            ("Average Click Delay:", f"{stats['avg_click_delay_ms']:.1f}ms"),
            ("Average Confirmation:", f"{stats['avg_confirmation_delay_ms']:.1f}ms"),
            ("", ""),
            ("P50 Delay:", f"{stats['p50_total_delay_ms']:.1f}ms"),
            ("P95 Delay:", f"{stats['p95_total_delay_ms']:.1f}ms"),
        ]

        for i, (label_text, value_text) in enumerate(stats_text):
            if not label_text:  # Separator
                separator = tk.Frame(stats_frame, height=10, bg='#2a2a2a')
                separator.pack(fill=tk.X)
                continue

            row_frame = tk.Frame(stats_frame, bg='#2a2a2a')
            row_frame.pack(fill=tk.X, padx=15, pady=5)

            label = tk.Label(
                row_frame,
                text=label_text,
                font=('Arial', 10),
                bg='#2a2a2a',
                fg='#cccccc',
                anchor=tk.W
            )
            label.pack(side=tk.LEFT)

            value = tk.Label(
                row_frame,
                text=value_text,
                font=('Arial', 10, 'bold'),
                bg='#2a2a2a',
                fg='#00ff00' if 'Success' in label_text else '#ffffff',
                anchor=tk.E
            )
            value.pack(side=tk.RIGHT)

        # Close button
        close_button = tk.Button(
            main_frame,
            text="Close",
            command=dialog.destroy,
            bg='#3a3a3a',
            fg='#ffffff',
            font=('Arial', 10),
            relief=tk.FLAT,
            padx=20,
            pady=5
        )
        close_button.pack()

        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
    
    def _update_timing_metrics_display(self):
        """
        Update draggable timing overlay (Phase 8.6)
        Called every second when bot is active in UI_LAYER mode
        """
        if not self.browser_executor:
            # Hide overlay if no executor
            self.timing_overlay.hide()
            return

        # Get current execution mode
        execution_mode = self.bot_config_panel.get_execution_mode()
        from bot.execution_mode import ExecutionMode

        # Only show timing overlay if BOTH conditions met:
        # 1. UI_LAYER mode
        # 2. User has toggled it on via menu
        if execution_mode == ExecutionMode.UI_LAYER and self.timing_overlay_var.get():
            # Show overlay
            self.timing_overlay.show()

            # Get timing stats
            stats = self.browser_executor.get_timing_stats()

            # Update overlay with stats
            self.timing_overlay.update_stats(stats)
        else:
            # Hide overlay if not in UI_LAYER mode OR user toggled it off
            self.timing_overlay.hide()
    
    def _update_timing_metrics_loop(self):
        """
        Periodic timing metrics update loop (Phase 8.6)
        Runs every 1 second to update inline timing display
        """
        try:
            self._update_timing_metrics_display()
        except Exception as e:
            logger.error(f"Error updating timing metrics: {e}", exc_info=True)

        # Schedule next update (every 1000ms = 1 second)
        self.root.after(1000, self._update_timing_metrics_loop)
    
    # ========================================================================
    # BOT MONITORING
    # ========================================================================
    
    def _check_bot_results(self):
        """
        Periodically check for bot execution results from async executor
        This runs in the UI thread and processes results non-blocking
        """
        if self.bot_enabled:
            # Process all pending results
            while True:
                result = self.bot_executor.get_latest_result()
                if not result:
                    break

                # Handle errors
                if 'error' in result:
                    self.bot_status_label.config(
                        text=f"Bot: ERROR",
                        fg='#ff3366'
                    )
                    self.log(f"🤖 Bot error at tick {result['tick']}: {result['error']}")
                    continue

                # Process successful execution
                bot_result = result.get('result', {})
                action = bot_result.get('action', 'WAIT')
                reasoning = bot_result.get('reasoning', '')
                success = bot_result.get('success', False)

                # Update UI for non-WAIT actions
                if action != 'WAIT':
                    status_text = f"Bot: {action}"
                    if reasoning:
                        status_text += f" ({reasoning[:30]}...)" if len(reasoning) > 30 else f" ({reasoning})"

                    self.bot_status_label.config(
                        text=status_text,
                        fg='#00ff88' if success else '#ff3366'
                    )

                    # Log bot action
                    if success:
                        self.log(f"🤖 Bot: {action} - {reasoning}")
                    else:
                        reason = bot_result.get('reason', 'Unknown')
                        self.log(f"🤖 Bot: {action} FAILED - {reason}")

        # Schedule next check (every 100ms)
        self.root.after(100, self._check_bot_results)
