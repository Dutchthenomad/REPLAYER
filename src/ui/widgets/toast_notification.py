"""
Toast Notification Widget
Displays temporary pop-up messages
"""

import tkinter as tk
import logging

logger = logging.getLogger(__name__)


class ToastNotification:
    """Toast notification system for temporary messages"""

    def __init__(self, parent):
        self.parent = parent
        self.active_toasts = []

    def show(self, message: str, msg_type: str = "info", duration: int = 3000):
        """
        Show a toast notification

        Args:
            message: Message to display
            msg_type: Type of message (info, warning, error, success)
            duration: Duration in milliseconds
        """
        # Create toast window
        toast = tk.Toplevel(self.parent)
        toast.withdraw()
        toast.overrideredirect(True)

        # Color scheme based on type
        colors = {
            'info': ('#3366ff', '#ffffff'),
            'warning': ('#ffcc00', '#000000'),
            'error': ('#ff3366', '#ffffff'),
            'success': ('#00ff88', '#000000')
        }
        bg_color, fg_color = colors.get(msg_type, colors['info'])

        # Create label
        label = tk.Label(
            toast,
            text=message,
            bg=bg_color,
            fg=fg_color,
            font=('Arial', 10, 'bold'),
            padx=20,
            pady=10
        )
        label.pack()

        # Position toast
        toast.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - toast.winfo_width()) // 2
        y = self.parent.winfo_y() + 50 + len(self.active_toasts) * 60
        toast.geometry(f"+{x}+{y}")
        toast.deiconify()

        self.active_toasts.append(toast)

        # Auto-dismiss
        def dismiss():
            if toast in self.active_toasts:
                self.active_toasts.remove(toast)
            toast.destroy()

        toast.after(duration, dismiss)

        # Log the message
        log_methods = {
            'info': logger.info,
            'warning': logger.warning,
            'error': logger.error,
            'success': logger.info
        }
        log_methods.get(msg_type, logger.info)(f"Toast: {message}")
