"""
Toast Notification Widget - Phase 10.5F

Non-intrusive notifications that appear briefly and auto-dismiss.
Used for recording status updates.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ToastType:
    """Toast notification types with associated colors."""
    SUCCESS = "success"  # Green
    WARNING = "warning"  # Yellow/Orange
    INFO = "info"        # Blue
    ERROR = "error"      # Red


class ToastNotification:
    """
    Toast notification that appears in the corner of the window.

    Features:
    - Auto-dismiss after configurable duration
    - Color-coded by type (success, warning, info, error)
    - Non-modal (doesn't block interaction)
    - Stacks if multiple toasts shown

    Usage:
        toast = ToastNotification(root)
        toast.show("Recording started", ToastType.SUCCESS)
        toast.show("Monitor mode active", ToastType.WARNING, duration=5000)
    """

    # Color schemes for each type
    COLORS = {
        ToastType.SUCCESS: {"bg": "#4CAF50", "fg": "white"},  # Green
        ToastType.WARNING: {"bg": "#FF9800", "fg": "white"},  # Orange
        ToastType.INFO: {"bg": "#2196F3", "fg": "white"},     # Blue
        ToastType.ERROR: {"bg": "#f44336", "fg": "white"},    # Red
    }

    # Track active toasts for stacking
    _active_toasts = []

    def __init__(
        self,
        parent: tk.Tk,
        position: str = "bottom-right",
        default_duration: int = 3000
    ):
        """
        Initialize toast notification manager.

        Args:
            parent: Parent tkinter window
            position: Where to show toasts ("top-right", "bottom-right", etc.)
            default_duration: Default auto-dismiss time in milliseconds
        """
        self.parent = parent
        self.position = position
        self.default_duration = default_duration
        self._toast_frame: Optional[tk.Frame] = None
        self._after_id: Optional[str] = None

    def show(
        self,
        message: str,
        toast_type: str = ToastType.INFO,
        duration: Optional[int] = None
    ) -> None:
        """
        Show a toast notification.

        Args:
            message: Message to display
            toast_type: Type of toast (success, warning, info, error)
            duration: Auto-dismiss duration in ms (None = use default)
        """
        # Close existing toast if any
        self.dismiss()

        duration = duration or self.default_duration
        colors = self.COLORS.get(toast_type, self.COLORS[ToastType.INFO])

        # Create toast frame
        self._toast_frame = tk.Frame(
            self.parent,
            bg=colors["bg"],
            padx=15,
            pady=10
        )

        # Add message label
        label = tk.Label(
            self._toast_frame,
            text=message,
            bg=colors["bg"],
            fg=colors["fg"],
            font=("Segoe UI", 10),
            wraplength=300
        )
        label.pack()

        # Add close button
        close_btn = tk.Label(
            self._toast_frame,
            text="×",
            bg=colors["bg"],
            fg=colors["fg"],
            font=("Segoe UI", 12, "bold"),
            cursor="hand2"
        )
        close_btn.place(relx=1.0, rely=0, anchor="ne", x=-5, y=2)
        close_btn.bind("<Button-1>", lambda e: self.dismiss())

        # Position the toast
        self._position_toast()

        # Schedule auto-dismiss
        if duration > 0:
            self._after_id = self.parent.after(duration, self.dismiss)

        logger.debug(f"Toast shown: {message} ({toast_type})")

    def _position_toast(self) -> None:
        """Position the toast based on configured position."""
        if not self._toast_frame:
            return

        # Update to get actual size
        self._toast_frame.update_idletasks()

        # Get parent size
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        # Get toast size
        toast_width = self._toast_frame.winfo_reqwidth()
        toast_height = self._toast_frame.winfo_reqheight()

        # Calculate position
        padding = 20

        if "right" in self.position:
            x = parent_width - toast_width - padding
        else:
            x = padding

        if "bottom" in self.position:
            y = parent_height - toast_height - padding - 30  # Account for status bar
        else:
            y = padding + 30  # Account for menu bar

        # Stack offset if other toasts active
        stack_offset = len(ToastNotification._active_toasts) * (toast_height + 10)
        if "bottom" in self.position:
            y -= stack_offset
        else:
            y += stack_offset

        self._toast_frame.place(x=x, y=y)

        # Track this toast
        ToastNotification._active_toasts.append(self)

    def dismiss(self) -> None:
        """Dismiss the current toast."""
        if self._after_id:
            self.parent.after_cancel(self._after_id)
            self._after_id = None

        if self._toast_frame:
            self._toast_frame.destroy()
            self._toast_frame = None

        # Remove from active toasts
        if self in ToastNotification._active_toasts:
            ToastNotification._active_toasts.remove(self)

    def is_visible(self) -> bool:
        """Check if toast is currently visible."""
        return self._toast_frame is not None


class RecordingToastManager:
    """
    Convenience class for recording-specific toast notifications.

    Provides pre-configured methods for common recording events.
    """

    def __init__(self, parent: tk.Tk):
        """
        Initialize the recording toast manager.

        Args:
            parent: Parent tkinter window
        """
        self.toast = ToastNotification(parent, position="bottom-right")

    def recording_started(self) -> None:
        """Show 'Recording started' toast."""
        self.toast.show("Recording started", ToastType.SUCCESS)

    def recording_paused(self, reason: str = "Monitor Mode active") -> None:
        """Show recording paused toast."""
        self.toast.show(f"Recording paused - {reason}", ToastType.WARNING, duration=5000)

    def recording_resumed(self) -> None:
        """Show 'Recording resumed' toast."""
        self.toast.show("Recording resumed", ToastType.SUCCESS)

    def recording_stopped(self, games_captured: int) -> None:
        """Show recording stopped toast with count."""
        self.toast.show(
            f"Recording stopped - {games_captured} games captured",
            ToastType.INFO,
            duration=5000
        )

    def session_limit_reached(self) -> None:
        """Show session limit reached toast."""
        self.toast.show(
            "Session limit reached - finishing current game",
            ToastType.INFO,
            duration=4000
        )

    def data_integrity_issue(self, issue: str) -> None:
        """Show data integrity issue toast."""
        self.toast.show(
            f"Data integrity issue: {issue}",
            ToastType.WARNING,
            duration=5000
        )

    def dismiss(self) -> None:
        """Dismiss current toast."""
        self.toast.dismiss()
