"""
Balance Edit Dialog

Provides unlock confirmation and manual balance editing functionality.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal, InvalidOperation
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class BalanceUnlockDialog:
    """Dialog to confirm unlocking balance for manual editing."""

    def __init__(self, parent, current_balance: Decimal, on_confirm: Callable):
        """
        Initialize unlock confirmation dialog.

        Args:
            parent: Parent window
            current_balance: Current P&L-tracked balance
            on_confirm: Callback when user confirms unlock
        """
        self.parent = parent
        self.current_balance = current_balance
        self.on_confirm = on_confirm
        self.result = False

        # Create modal dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Unlock Balance for Manual Editing")
        self.dialog.geometry("450x250")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        # Warning icon + message
        warning_frame = ttk.Frame(self.dialog, padding=20)
        warning_frame.pack(fill='x')

        warning_label = ttk.Label(
            warning_frame,
            text="⚠️ Unlock Balance for Manual Editing?",
            font=('TkDefaultFont', 12, 'bold')
        )
        warning_label.pack()

        # Explanation
        msg_frame = ttk.Frame(self.dialog, padding=(20, 10))
        msg_frame.pack(fill='both', expand=True)

        message = (
            "This will allow you to manually override the balance.\n"
            "The programmatic P&L tracking will be temporarily paused.\n\n"
            f"Current Balance (P&L Tracked): {self.current_balance:.4f} SOL"
        )

        msg_label = ttk.Label(
            msg_frame,
            text=message,
            justify='left',
            wraplength=400
        )
        msg_label.pack()

        # Buttons
        button_frame = ttk.Frame(self.dialog, padding=(20, 10))
        button_frame.pack(fill='x', side='bottom')

        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=12
        )
        cancel_btn.pack(side='right', padx=5)

        unlock_btn = ttk.Button(
            button_frame,
            text="Unlock",
            command=self._on_unlock,
            width=12
        )
        unlock_btn.pack(side='right', padx=5)

        # Focus unlock button
        unlock_btn.focus_set()

        # Bind escape key to cancel
        self.dialog.bind('<Escape>', lambda e: self._on_cancel())
        self.dialog.bind('<Return>', lambda e: self._on_unlock())

    def _on_unlock(self):
        """Handle unlock confirmation."""
        logger.info("User confirmed balance unlock")
        self.result = True
        self.dialog.destroy()
        self.on_confirm()

    def _on_cancel(self):
        """Handle cancel."""
        logger.info("User canceled balance unlock")
        self.result = False
        self.dialog.destroy()


class BalanceRelockDialog:
    """Dialog to choose between keeping manual value or reverting to P&L tracked value."""

    def __init__(self, parent, manual_balance: Decimal, tracked_balance: Decimal, on_choice: Callable):
        """
        Initialize relock dialog.

        Args:
            parent: Parent window
            manual_balance: Current manually set balance
            tracked_balance: P&L-tracked balance (what it would be without manual override)
            on_choice: Callback with choice ('keep_manual' or 'revert_to_pnl')
        """
        self.parent = parent
        self.manual_balance = manual_balance
        self.tracked_balance = tracked_balance
        self.on_choice = on_choice
        self.result = 'keep_manual'  # Default

        # Create modal dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Re-lock Balance")
        self.dialog.geometry("450x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        # Title
        title_frame = ttk.Frame(self.dialog, padding=20)
        title_frame.pack(fill='x')

        title_label = ttk.Label(
            title_frame,
            text="🔒 Re-lock Balance",
            font=('TkDefaultFont', 12, 'bold')
        )
        title_label.pack()

        # Message
        msg_frame = ttk.Frame(self.dialog, padding=(20, 10))
        msg_frame.pack(fill='both', expand=True)

        message = (
            "Choose which balance to use when re-locking:\n\n"
            f"Manual Value: {self.manual_balance:.4f} SOL\n"
            f"P&L Tracked Value: {self.tracked_balance:.4f} SOL\n\n"
            "If you keep the manual value, P&L tracking will resume from the new baseline."
        )

        msg_label = ttk.Label(
            msg_frame,
            text=message,
            justify='left',
            wraplength=400
        )
        msg_label.pack()

        # Buttons
        button_frame = ttk.Frame(self.dialog, padding=(20, 10))
        button_frame.pack(fill='x', side='bottom')

        revert_btn = ttk.Button(
            button_frame,
            text=f"Revert to P&L ({self.tracked_balance:.4f})",
            command=self._on_revert,
            width=25
        )
        revert_btn.pack(side='bottom', pady=5)

        keep_btn = ttk.Button(
            button_frame,
            text=f"Keep Manual ({self.manual_balance:.4f})",
            command=self._on_keep,
            width=25
        )
        keep_btn.pack(side='bottom', pady=5)

        # Focus keep button (default choice)
        keep_btn.focus_set()

        # Bind escape key to keep manual (safe default)
        self.dialog.bind('<Escape>', lambda e: self._on_keep())

    def _on_keep(self):
        """Keep manual value."""
        logger.info(f"User chose to keep manual balance: {self.manual_balance:.4f} SOL")
        self.result = 'keep_manual'
        self.dialog.destroy()
        self.on_choice('keep_manual')

    def _on_revert(self):
        """Revert to P&L tracked value."""
        logger.info(f"User chose to revert to P&L balance: {self.tracked_balance:.4f} SOL")
        self.result = 'revert_to_pnl'
        self.dialog.destroy()
        self.on_choice('revert_to_pnl')


class BalanceEditEntry:
    """Inline balance editing widget (replaces label temporarily)."""

    def __init__(self, parent, current_balance: Decimal, on_save: Callable, on_cancel: Callable):
        """
        Initialize balance edit entry.

        Args:
            parent: Parent frame (where label normally lives)
            current_balance: Current balance to edit
            on_save: Callback with new balance (Decimal)
            on_cancel: Callback when user cancels
        """
        self.parent = parent
        self.current_balance = current_balance
        self.on_save = on_save
        self.on_cancel = on_cancel

        # Create entry widget
        self.entry = ttk.Entry(parent, width=15, font=('TkDefaultFont', 10))
        self.entry.insert(0, f"{current_balance:.4f}")
        self.entry.select_range(0, tk.END)  # Select all text
        self.entry.focus_set()

        # Bind events
        self.entry.bind('<Return>', self._on_enter)
        self.entry.bind('<Escape>', self._on_escape)
        self.entry.bind('<FocusOut>', self._on_focus_out)

    def pack(self, **kwargs):
        """Pack the entry widget."""
        self.entry.pack(**kwargs)

    def grid(self, **kwargs):
        """Grid the entry widget."""
        self.entry.grid(**kwargs)

    def destroy(self):
        """Destroy the entry widget."""
        self.entry.destroy()

    def _on_enter(self, event=None):
        """Handle Enter key (save)."""
        try:
            new_balance = Decimal(self.entry.get())
            if new_balance < 0:
                messagebox.showerror("Invalid Balance", "Balance cannot be negative")
                return
            logger.info(f"User saved new balance: {new_balance:.4f} SOL")
            self.on_save(new_balance)
        except InvalidOperation:
            messagebox.showerror("Invalid Balance", "Please enter a valid number")

    def _on_escape(self, event=None):
        """Handle Escape key (cancel)."""
        logger.info("User canceled balance edit")
        self.on_cancel()

    def _on_focus_out(self, event=None):
        """Handle focus loss (treat as save)."""
        self._on_enter()
