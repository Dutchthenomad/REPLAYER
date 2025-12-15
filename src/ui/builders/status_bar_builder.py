"""
StatusBarBuilder - Builds the status bar UI row

Extracted from MainWindow._create_ui() (Phase 1)
Handles construction of status bar with tick, price, phase, and status labels.
"""

import tkinter as tk
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class StatusBarBuilder:
    """
    Builds the status bar row with tick, price, phase, and status labels.

    Usage:
        builder = StatusBarBuilder(root, toggle_recording=callback)
        widgets = builder.build()
        tick_label = widgets['tick_label']
    """

    def __init__(self, parent: tk.Tk, toggle_recording: Optional[Callable] = None):
        """
        Initialize StatusBarBuilder.

        Args:
            parent: Parent Tk root window
            toggle_recording: Callback for recording toggle button
        """
        self.parent = parent
        self.toggle_recording = toggle_recording

    def build(self) -> dict:
        """
        Build the status bar and return widget references.

        Returns:
            dict with keys:
                - status_bar: The status bar frame
                - tick_label: Label showing current tick
                - price_label: Label showing current price
                - phase_label: Label showing game phase
                - player_profile_label: Label showing authenticated player
                - browser_status_label: Label showing browser connection status
        """
        # Create status bar frame
        status_bar = tk.Frame(self.parent, bg='#000000', height=30)
        status_bar.pack(fill=tk.X)
        status_bar.pack_propagate(False)  # Fixed height

        # Tick (left)
        tick_label = tk.Label(
            status_bar,
            text="TICK: 0",
            font=('Arial', 11, 'bold'),
            bg='#000000',
            fg='white'
        )
        tick_label.pack(side=tk.LEFT, padx=10)

        # Price (center-left)
        price_label = tk.Label(
            status_bar,
            text="PRICE: 1.0000 X",
            font=('Arial', 11, 'bold'),
            bg='#000000',
            fg='white'
        )
        price_label.pack(side=tk.LEFT, padx=20)

        # Phase (right)
        phase_label = tk.Label(
            status_bar,
            text="PHASE: UNKNOWN",
            font=('Arial', 11, 'bold'),
            bg='#000000',
            fg='white'
        )
        phase_label.pack(side=tk.RIGHT, padx=10)

        # Player profile label (shows authenticated username)
        player_profile_label = tk.Label(
            status_bar,
            text="\U0001F464 Not Authenticated",  # 👤
            font=('Arial', 10, 'bold'),
            bg='#000000',
            fg='#666666'  # Gray when not authenticated
        )
        player_profile_label.pack(side=tk.RIGHT, padx=15)

        # Browser status (right)
        browser_status_label = tk.Label(
            status_bar,
            text="BROWSER: \u26AB Not Connected",  # ⚫
            font=('Arial', 9),
            bg='#000000',
            fg='#888888'  # Gray when disconnected
        )
        browser_status_label.pack(side=tk.RIGHT, padx=10)

        # Event source indicator (left, after price)
        source_label = tk.Label(
            status_bar,
            text="\U0001F534 No Source",  # 🔴
            font=('Helvetica', 9),
            bg='#000000',
            fg='#ff4444'  # Red when no source
        )
        source_label.pack(side=tk.LEFT, padx=10)

        # Recording toggle button (left, after source)
        recording_toggle = tk.Button(
            status_bar,
            text="\u23FA REC OFF",  # ⏺ REC OFF
            font=('Arial', 9, 'bold'),
            bg='#333333',
            fg='#888888',
            activebackground='#444444',
            activeforeground='white',
            relief=tk.FLAT,
            padx=8,
            pady=2,
            command=self.toggle_recording or (lambda: None)
        )
        recording_toggle.pack(side=tk.LEFT, padx=10)

        logger.debug("StatusBarBuilder: Status bar built")

        return {
            'status_bar': status_bar,
            'tick_label': tick_label,
            'price_label': price_label,
            'phase_label': phase_label,
            'player_profile_label': player_profile_label,
            'browser_status_label': browser_status_label,
            'source_label': source_label,
            'recording_toggle': recording_toggle,
        }
