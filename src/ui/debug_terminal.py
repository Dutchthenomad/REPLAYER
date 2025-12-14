"""
Debug Terminal - Real-time WebSocket Event Viewer

Displays ALL WebSocket events in a separate, non-blocking window.
Supports filtering and color-coded event types.
"""
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)

# Auth-required events
AUTH_EVENTS = {'usernameStatus', 'playerUpdate', 'buyOrderResponse', 'sellOrderResponse'}

# Known events (non-novel)
KNOWN_EVENTS = {
    'gameStateUpdate', 'standard/newTrade', 'newChatMessage',
    'goldenHourUpdate', 'goldenHourDrawing', 'battleEventUpdate',
    'usernameStatus', 'playerUpdate', 'connect', 'disconnect'
}

# Event colors
EVENT_COLORS = {
    'gameStateUpdate': '#888888',      # Gray - high frequency
    'usernameStatus': '#00ff88',       # Green - auth identity
    'playerUpdate': '#00ffff',         # Cyan - auth balance
    'standard/newTrade': '#ffff00',    # Yellow - trades
    'newChatMessage': '#ffffff',       # White - chat
    'goldenHourUpdate': '#ff8800',     # Orange - lottery
    'goldenHourDrawing': '#ff8800',    # Orange - lottery
    'battleEventUpdate': '#ff00ff',    # Magenta - battle
    'connect': '#00ff00',              # Bright green
    'disconnect': '#ff0000',           # Red
}

DEFAULT_COLOR = '#ff4444'  # Red for novel/unknown events


class DebugTerminal:
    """
    Real-time WebSocket event viewer in separate window.

    Features:
    - Independent Toplevel window (non-blocking)
    - Event filtering by type
    - Color-coded display
    - Live statistics
    """

    def __init__(self, parent):
        """
        Initialize debug terminal.

        Args:
            parent: Parent tkinter widget
        """
        self.parent = parent
        self.current_filter: str = 'ALL'
        self.event_count: int = 0
        self.novel_events: Set[str] = set()

        # Create separate window
        self.window = tk.Toplevel(parent)
        self.window.title("WebSocket Debug Terminal")
        self.window.geometry("1000x600")

        # Don't tie to parent visibility
        # (NOT calling transient - window is independent)

        self._setup_ui()

        logger.info("DebugTerminal window created")

    def _setup_ui(self):
        """Setup UI components."""
        # Top frame - controls
        control_frame = ttk.Frame(self.window)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Filter dropdown
        ttk.Label(control_frame, text="Filter:").pack(side=tk.LEFT)
        self._filter_var = tk.StringVar(value='ALL')
        self._filter_combo = ttk.Combobox(
            control_frame,
            textvariable=self._filter_var,
            values=[
                'ALL',
                'AUTH_ONLY',
                'NOVEL_ONLY',
                '---',
                'gameStateUpdate',
                'usernameStatus',
                'playerUpdate',
                'standard/newTrade',
                'newChatMessage',
            ],
            width=20
        )
        self._filter_combo.pack(side=tk.LEFT, padx=5)
        self._filter_combo.bind('<<ComboboxSelected>>', self._on_filter_changed)

        # Clear button
        ttk.Button(control_frame, text="Clear", command=self._clear_log).pack(side=tk.LEFT, padx=5)

        # Stats label
        self._stats_label = ttk.Label(control_frame, text="Events: 0")
        self._stats_label.pack(side=tk.RIGHT, padx=5)

        # Log display
        self._log_text = ScrolledText(
            self.window,
            font=("JetBrains Mono", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#ffffff",
            wrap=tk.NONE
        )
        self._log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configure tags for colors
        for event_type, color in EVENT_COLORS.items():
            self._log_text.tag_configure(event_type, foreground=color)
        self._log_text.tag_configure('novel', foreground=DEFAULT_COLOR)
        self._log_text.tag_configure('timestamp', foreground='#666666')

    def _on_filter_changed(self, event=None):
        """Handle filter selection change."""
        self.current_filter = self._filter_var.get()
        logger.debug(f"Filter changed to: {self.current_filter}")

    def set_filter(self, filter_type: str):
        """Set event filter programmatically."""
        self.current_filter = filter_type
        self._filter_var.set(filter_type)

    def _is_filtered(self, event: Dict[str, Any]) -> bool:
        """Check if event should be filtered out."""
        event_type = event.get('event', '')

        if self.current_filter == 'ALL':
            return False

        if self.current_filter == 'AUTH_ONLY':
            return event_type not in AUTH_EVENTS

        if self.current_filter == 'NOVEL_ONLY':
            return event_type in KNOWN_EVENTS

        # Specific event type filter
        return event_type != self.current_filter

    def _get_event_color(self, event_type: str) -> str:
        """Get color for event type."""
        if event_type in EVENT_COLORS:
            return EVENT_COLORS[event_type]
        return DEFAULT_COLOR

    def log_event(self, event: Dict[str, Any]):
        """
        Log an event to the display.

        Args:
            event: Event dict with 'event', 'data', 'timestamp'
        """
        if self._is_filtered(event):
            return

        self.event_count += 1
        event_type = event.get('event', 'unknown')

        # Track novel events
        if event_type not in KNOWN_EVENTS:
            self.novel_events.add(event_type)

        # Format line
        timestamp = event.get('timestamp', datetime.now().isoformat())
        if 'T' in timestamp:
            timestamp = timestamp.split('T')[1][:12]  # HH:MM:SS.mmm

        data = event.get('data', {})
        data_preview = self._format_data_preview(event_type, data)

        direction = event.get('direction', 'received')
        direction_symbol = '◀' if direction == 'received' else '▶'

        line = f"[{timestamp}] {direction_symbol} {event_type:<20} {data_preview}\n"

        # Insert with color tag
        tag = event_type if event_type in EVENT_COLORS else 'novel'
        self._log_text.insert(tk.END, line, tag)
        self._log_text.see(tk.END)

        # Update stats
        self._stats_label.config(text=f"Events: {self.event_count}")

    def _format_data_preview(self, event_type: str, data: Any) -> str:
        """Format data preview based on event type."""
        if not isinstance(data, dict):
            return str(data)[:50]

        if event_type == 'gameStateUpdate':
            price = data.get('price', '?')
            tick = data.get('tickCount', '?')
            game_id = data.get('gameId', '?')[:8]
            return f"game={game_id} tick={tick} price={price}"

        if event_type == 'usernameStatus':
            username = data.get('username', '?')
            return f"username={username}"

        if event_type == 'playerUpdate':
            cash = data.get('cash', '?')
            pos = data.get('positionQty', '?')
            return f"cash={cash} pos={pos}"

        if event_type == 'standard/newTrade':
            trade_type = data.get('type', '?')
            username = data.get('username', '?')
            amount = data.get('amount', '?')
            return f"{trade_type} by {username} amt={amount}"

        # Generic preview
        keys = list(data.keys())[:3]
        return ', '.join(f"{k}={data[k]}" for k in keys)[:60]

    def _clear_log(self):
        """Clear the log display."""
        self._log_text.delete(1.0, tk.END)
        self.event_count = 0
        self._stats_label.config(text="Events: 0")

    def show(self):
        """Show the window."""
        self.window.deiconify()
        self.window.lift()

    def hide(self):
        """Hide the window."""
        self.window.withdraw()

    def destroy(self):
        """Destroy the window."""
        self.window.destroy()
