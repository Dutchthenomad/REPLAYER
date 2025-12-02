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
    """Dialog to set balance when re-locking.

    Allows user to enter their actual in-game balance so REPLAYER
    can accurately track P&L from that point forward.
    """

    def __init__(self, parent, manual_balance: Decimal, tracked_balance: Decimal, on_choice: Callable):
        """
        Initialize relock dialog.

        Args:
            parent: Parent window
            manual_balance: Current manually set balance
            tracked_balance: P&L-tracked balance (what it would be without manual override)
            on_choice: Callback with choice ('keep_manual', 'revert_to_pnl', or 'custom')
                       and optional new_balance parameter
        """
        self.parent = parent
        self.manual_balance = manual_balance
        self.tracked_balance = tracked_balance
        self.on_choice = on_choice
        self.result = 'keep_manual'  # Default

        # Create modal dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Set Balance")
        self.dialog.geometry("450x380")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.configure(bg='#1a1a2e')

        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        bg_color = '#1a1a2e'
        fg_color = '#ffffff'
        input_bg = '#2d2d44'
        accent_color = '#4fc3f7'

        # Title
        title_frame = tk.Frame(self.dialog, bg=bg_color, padx=20, pady=15)
        title_frame.pack(fill='x')

        title_label = tk.Label(
            title_frame,
            text="💰 Set Your Balance",
            font=('TkDefaultFont', 14, 'bold'),
            bg=bg_color,
            fg=fg_color
        )
        title_label.pack()

        # Instruction message
        msg_frame = tk.Frame(self.dialog, bg=bg_color, padx=20, pady=5)
        msg_frame.pack(fill='x')

        message = (
            "Enter your current in-game wallet balance.\n"
            "P&L tracking will resume from this value."
        )

        msg_label = tk.Label(
            msg_frame,
            text=message,
            justify='left',
            bg=bg_color,
            fg='#aaaaaa',
            wraplength=400
        )
        msg_label.pack(anchor='w')

        # Balance input section
        input_frame = tk.Frame(self.dialog, bg=bg_color, padx=20, pady=15)
        input_frame.pack(fill='x')

        input_label = tk.Label(
            input_frame,
            text="Balance (SOL):",
            bg=bg_color,
            fg=fg_color,
            font=('TkDefaultFont', 10)
        )
        input_label.pack(anchor='w')

        # Entry with current manual value as default
        self.balance_entry = tk.Entry(
            input_frame,
            font=('TkDefaultFont', 16),
            width=20,
            bg=input_bg,
            fg=fg_color,
            insertbackground=fg_color,
            relief='flat',
            highlightthickness=2,
            highlightcolor=accent_color,
            highlightbackground='#444466'
        )
        self.balance_entry.insert(0, f"{self.manual_balance:.4f}")
        self.balance_entry.select_range(0, tk.END)
        self.balance_entry.pack(anchor='w', pady=(5, 0))
        self.balance_entry.focus_set()

        # Reference values
        ref_frame = tk.Frame(self.dialog, bg=bg_color, padx=20, pady=10)
        ref_frame.pack(fill='x')

        ref_label = tk.Label(
            ref_frame,
            text="Reference values (click to use):",
            bg=bg_color,
            fg='#888888',
            font=('TkDefaultFont', 9)
        )
        ref_label.pack(anchor='w')

        # Clickable reference values
        refs_row = tk.Frame(ref_frame, bg=bg_color)
        refs_row.pack(anchor='w', pady=(5, 0))

        manual_ref = tk.Label(
            refs_row,
            text=f"Previous: {self.manual_balance:.4f}",
            bg=bg_color,
            fg=accent_color,
            font=('TkDefaultFont', 9, 'underline'),
            cursor='hand2'
        )
        manual_ref.pack(side='left', padx=(0, 15))
        manual_ref.bind('<Button-1>', lambda e: self._set_entry_value(self.manual_balance))

        tracked_ref = tk.Label(
            refs_row,
            text=f"P&L Tracked: {self.tracked_balance:.4f}",
            bg=bg_color,
            fg=accent_color,
            font=('TkDefaultFont', 9, 'underline'),
            cursor='hand2'
        )
        tracked_ref.pack(side='left')
        tracked_ref.bind('<Button-1>', lambda e: self._set_entry_value(self.tracked_balance))

        # Buttons
        button_frame = tk.Frame(self.dialog, bg=bg_color, padx=20, pady=20)
        button_frame.pack(fill='x', side='bottom')

        # Apply button (primary action)
        apply_btn = tk.Button(
            button_frame,
            text="Apply Balance",
            command=self._on_apply,
            bg=accent_color,
            fg='#000000',
            font=('TkDefaultFont', 11, 'bold'),
            relief='flat',
            padx=20,
            pady=8,
            cursor='hand2'
        )
        apply_btn.pack(fill='x', pady=(0, 10))

        # Cancel button
        cancel_btn = tk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            bg='#444466',
            fg=fg_color,
            font=('TkDefaultFont', 10),
            relief='flat',
            padx=15,
            pady=5,
            cursor='hand2'
        )
        cancel_btn.pack(fill='x')

        # Bind keys
        self.dialog.bind('<Escape>', lambda e: self._on_cancel())
        self.dialog.bind('<Return>', lambda e: self._on_apply())

    def _set_entry_value(self, value: Decimal):
        """Set entry field to a specific value."""
        self.balance_entry.delete(0, tk.END)
        self.balance_entry.insert(0, f"{value:.4f}")
        self.balance_entry.select_range(0, tk.END)
        self.balance_entry.focus_set()

    def _on_apply(self):
        """Apply the entered balance."""
        try:
            new_balance = Decimal(self.balance_entry.get().strip())
            if new_balance < 0:
                messagebox.showerror("Invalid Balance", "Balance cannot be negative")
                return

            logger.info(f"User set balance to: {new_balance:.4f} SOL")
            self.result = 'custom'
            self.dialog.destroy()
            # Pass the new balance to the callback
            self.on_choice('custom', new_balance)

        except InvalidOperation:
            messagebox.showerror("Invalid Balance", "Please enter a valid number (e.g., 0.5000)")

    def _on_cancel(self):
        """Cancel without changes."""
        logger.info("User canceled balance set")
        self.dialog.destroy()
        # Keep current manual value
        self.on_choice('keep_manual', self.manual_balance)


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
