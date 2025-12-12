"""
BrowserBridgeController - Manages browser automation and CDP bridge connection

Extracted from MainWindow to follow Single Responsibility Principle.
Handles:
- Browser connection dialog workflow
- CDP bridge connection/disconnection
- Browser status updates and indicators
- Connection lifecycle management
"""

import tkinter as tk
import asyncio
import logging
from typing import Callable, Optional
from browser.executor import BrowserExecutor
from browser.bridge import BridgeStatus
from ui.browser_connection_dialog import BrowserConnectionDialog

logger = logging.getLogger(__name__)


class BrowserBridgeController:
    """
    Manages browser automation and CDP bridge connection.

    Extracted from MainWindow (Phase 3.5) to reduce God Object anti-pattern.
    """

    def __init__(
        self,
        root: tk.Tk,
        parent_window,  # Reference to MainWindow for state access
        # UI components
        browser_menu: tk.Menu,
        browser_status_item_index: int,
        browser_disconnect_item_index: int,
        # Notifications
        toast,
        # Callbacks
        log_callback: Callable[[str], None]
    ):
        """
        Initialize BrowserBridgeController with dependencies.

        Args:
            root: Tkinter root window (for thread-safe marshaling)
            parent_window: MainWindow instance (for state access)
            browser_menu: Browser menu widget
            browser_status_item_index: Index of status menu item
            browser_disconnect_item_index: Index of disconnect menu item
            toast: Toast notification widget
            log_callback: Logging function
        """
        self.root = root
        self.parent = parent_window
        self.browser_menu = browser_menu
        self.browser_status_item_index = browser_status_item_index
        self.browser_disconnect_item_index = browser_disconnect_item_index
        self.toast = toast
        self.log = log_callback

        logger.info("BrowserBridgeController initialized")

    # ========================================================================
    # BROWSER CONNECTION DIALOG (Legacy - Phase 8.5)
    # ========================================================================

    def show_browser_connection_dialog(self):
        """Show browser connection wizard (Phase 8.5)"""
        try:
            # Create dialog with callbacks
            dialog = BrowserConnectionDialog(
                parent=self.root,
                on_connected=self.on_browser_connected,
                on_failed=self.on_browser_connection_failed
            )
            dialog.show()

        except Exception as e:
            logger.error(f"Error showing browser connection dialog: {e}", exc_info=True)
            self.log(f"Failed to show browser dialog: {e}")
            if self.toast:
                self.toast.show(f"Browser dialog error: {e}", "error")

    def on_browser_connected(self):
        """Called when browser connects successfully"""
        try:
            self.log("Browser connected successfully")
            if self.toast:
                self.toast.show("Browser connected", "success")

            # Update browser menu
            if hasattr(self, 'browser_menu'):
                # Enable disconnect button
                self.browser_menu.entryconfig(
                    self.browser_disconnect_item_index,
                    state=tk.NORMAL
                )
                # Update status indicator
                self.browser_menu.entryconfig(
                    self.browser_status_item_index,
                    label="🟢 Status: Connected"
                )

        except Exception as e:
            logger.error(f"Error handling browser connected: {e}", exc_info=True)

    def on_browser_connection_failed(self, error=None):
        """Called when browser connection fails"""
        error_msg = f"Browser connection failed: {error}" if error else "Browser connection failed"
        self.log(error_msg)
        if self.toast:
            self.toast.show(error_msg, "error")

    def disconnect_browser(self):
        """Disconnect browser (Phase 8.5)"""
        if not self.parent.browser_executor:
            self.log("No browser connection to disconnect")
            return

        # Confirm disconnection
        from tkinter import messagebox
        if not messagebox.askyesno(
            "Disconnect Browser",
            "Are you sure you want to disconnect the browser?\n\n"
            "The browser window will remain open but automation will stop."
        ):
            return

        try:
            self.log("Disconnecting browser...")

            # Run async disconnect in background thread
            def run_disconnect():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.parent.browser_executor.disconnect())
                    loop.close()

                    # Update UI in main thread
                    self.root.after(0, self.on_browser_disconnected)
                except Exception as e:
                    logger.error(f"Background disconnect failed: {e}", exc_info=True)
                    self.root.after(0, lambda: self.log(f"Disconnect error: {e}"))

            import threading
            disconnect_thread = threading.Thread(target=run_disconnect, daemon=True)
            disconnect_thread.start()

        except Exception as e:
            logger.error(f"Error disconnecting browser: {e}", exc_info=True)
            self.log(f"Error disconnecting browser: {e}")

    def on_browser_disconnected(self):
        """Called when browser disconnects"""
        try:
            self.parent.browser_executor = None
            self.log("Browser disconnected")
            if self.toast:
                self.toast.show("Browser disconnected", "info")

            # Update browser menu
            if hasattr(self, 'browser_menu'):
                # Disable disconnect button
                self.browser_menu.entryconfig(
                    self.browser_disconnect_item_index,
                    state=tk.DISABLED
                )
                # Update status indicator
                self.browser_menu.entryconfig(
                    self.browser_status_item_index,
                    label="⚫ Status: Disconnected"
                )

        except Exception as e:
            logger.error(f"Error handling browser disconnected: {e}", exc_info=True)

    # ========================================================================
    # BROWSER STATUS UPDATES
    # ========================================================================

    def update_browser_status(self, status):
        """Update browser status indicator"""
        # Map status to icon and color
        status_map = {
            'disconnected': ('⚫', 'Disconnected'),
            'connecting': ('🟡', 'Connecting...'),
            'connected': ('🟢', 'Connected'),
            'error': ('🔴', 'Error'),
            'reconnecting': ('🟡', 'Reconnecting...'),
        }

        icon, label = status_map.get(status, ('⚫', 'Unknown'))

        # Update menu item
        if hasattr(self, 'browser_menu'):
            self.browser_menu.entryconfig(
                self.browser_status_item_index,
                label=f"{icon} Status: {label}"
            )

            # Enable/disable disconnect button based on status
            if status == 'connected':
                self.browser_menu.entryconfig(
                    self.browser_disconnect_item_index,
                    state=tk.NORMAL
                )
            else:
                self.browser_menu.entryconfig(
                    self.browser_disconnect_item_index,
                    state=tk.DISABLED
                )

    # ========================================================================
    # CDP BRIDGE CONNECTION (Phase 9.3)
    # ========================================================================

    def connect_browser_bridge(self):
        """Connect to browser via CDP bridge (Phase 9.3)"""
        if not self.parent.browser_bridge:
            self.log("Browser bridge not initialized")
            return

        # Run async connect in background (non-blocking)
        self.parent.browser_bridge.connect_async()

    def disconnect_browser_bridge(self):
        """Disconnect from browser via CDP bridge (Phase 9.3)"""
        if not self.parent.browser_bridge:
            self.log("Browser bridge not initialized")
            return

        self.parent.browser_bridge.disconnect()

    def on_bridge_status_change(self, status: BridgeStatus):
        """
        Callback when browser bridge status changes (Phase 9.3)

        THREAD-SAFE: Marshals UI updates to main thread
        """
        # Extract data in worker thread
        status_value = status.value if hasattr(status, 'value') else str(status)

        # Marshal to main thread
        def update_ui():
            try:
                # Map BridgeStatus to menu display
                status_display_map = {
                    BridgeStatus.DISCONNECTED: ('⚫', 'Disconnected', tk.DISABLED),
                    BridgeStatus.CONNECTING: ('🟡', 'Connecting...', tk.DISABLED),
                    BridgeStatus.CONNECTED: ('🟢', 'Connected', tk.NORMAL),
                    BridgeStatus.ERROR: ('🔴', 'Error', tk.DISABLED),
                    BridgeStatus.RECONNECTING: ('🟡', 'Reconnecting...', tk.DISABLED),
                }

                icon, label, disconnect_state = status_display_map.get(
                    status,
                    ('⚫', 'Unknown', tk.DISABLED)
                )

                # Update status indicator
                self.browser_menu.entryconfig(
                    self.browser_status_item_index,
                    label=f"{icon} Status: {label}"
                )

                # Update disconnect button state
                self.browser_menu.entryconfig(
                    self.browser_disconnect_item_index,
                    state=disconnect_state
                )

                # Log status change
                self.log(f"Browser bridge: {label}")

                # Show toast for important status changes
                if status == BridgeStatus.CONNECTED:
                    if self.toast:
                        self.toast.show("Browser bridge connected", "success")
                elif status == BridgeStatus.ERROR:
                    if self.toast:
                        self.toast.show("Browser bridge error", "error")
                elif status == BridgeStatus.DISCONNECTED:
                    if self.toast:
                        self.toast.show("Browser bridge disconnected", "info")

            except Exception as e:
                logger.error(f"Error updating browser status UI: {e}", exc_info=True)

        self.root.after(0, update_ui)
