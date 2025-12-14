"""
PlaybackBuilder - Builds the playback controls row

Extracted from MainWindow._create_ui() (Phase 1)
Handles construction of playback buttons and speed controls.
"""

import tkinter as tk
from typing import Callable, Dict
import logging

logger = logging.getLogger(__name__)


class PlaybackBuilder:
    """
    Builds the playback controls row with buttons and speed controls.

    Usage:
        callbacks = {
            'load_game': lambda: controller.load_game(),
            'toggle_playback': lambda: controller.toggle_playback(),
            'step_forward': lambda: controller.step_forward(),
            'reset_game': lambda: controller.reset_game(),
            'set_speed': lambda s: controller.set_playback_speed(s),
        }
        builder = PlaybackBuilder(parent, callbacks)
        widgets = builder.build()
    """

    def __init__(self, parent: tk.Tk, callbacks: Dict[str, Callable]):
        """
        Initialize PlaybackBuilder.

        Args:
            parent: Parent Tk widget
            callbacks: Dictionary of callback functions
        """
        self.parent = parent
        self.callbacks = callbacks

    def build(self) -> dict:
        """
        Build the playback controls row and return widget references.

        Returns:
            dict with keys:
                - playback_row: The playback row frame
                - load_button: Load game button
                - play_button: Play/pause button
                - step_button: Step forward button
                - reset_button: Reset button
                - speed_label: Speed display label
                - speed_buttons: List of speed control buttons
        """
        # Playback row frame
        playback_row = tk.Frame(self.parent, bg='#1a1a1a', height=40)
        playback_row.pack(fill=tk.X)
        playback_row.pack_propagate(False)

        # Left side - playback buttons
        playback_left = tk.Frame(playback_row, bg='#1a1a1a')
        playback_left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_style = {'font': ('Arial', 10), 'width': 12, 'bd': 1, 'relief': tk.RAISED}

        load_button = tk.Button(
            playback_left,
            text="LOAD GAME",
            command=self.callbacks.get('load_game', lambda: None),
            bg='#444444',
            fg='white',
            **btn_style
        )
        load_button.pack(side=tk.LEFT, padx=5)

        play_button = tk.Button(
            playback_left,
            text="PLAY",
            command=self.callbacks.get('toggle_playback', lambda: None),
            bg='#444444',
            fg='white',
            state=tk.DISABLED,
            **btn_style
        )
        play_button.pack(side=tk.LEFT, padx=5)

        step_button = tk.Button(
            playback_left,
            text="STEP",
            command=self.callbacks.get('step_forward', lambda: None),
            bg='#444444',
            fg='white',
            state=tk.DISABLED,
            **btn_style
        )
        step_button.pack(side=tk.LEFT, padx=5)

        reset_button = tk.Button(
            playback_left,
            text="RESET",
            command=self.callbacks.get('reset_game', lambda: None),
            bg='#444444',
            fg='white',
            state=tk.DISABLED,
            **btn_style
        )
        reset_button.pack(side=tk.LEFT, padx=5)

        # Right side - playback speed controls
        speed_frame = tk.Frame(playback_row, bg='#1a1a1a')
        speed_frame.pack(side=tk.RIGHT, padx=10)

        speed_label = tk.Label(
            speed_frame,
            text="SPEED: 1.0X",
            font=('Arial', 10, 'bold'),
            bg='#1a1a1a',
            fg='white'
        )
        speed_label.pack(side=tk.LEFT, padx=5)

        # Speed buttons
        speed_btn_style = {'font': ('Arial', 8), 'width': 5, 'bd': 1, 'relief': tk.RAISED}
        set_speed = self.callbacks.get('set_speed', lambda s: None)

        speed_buttons = []
        for speed, bg in [(0.25, '#333333'), (0.5, '#333333'), (1.0, '#444444'), (2.0, '#333333'), (5.0, '#333333')]:
            btn = tk.Button(
                speed_frame,
                text=f"{speed}x",
                command=lambda s=speed: set_speed(s),
                bg=bg,
                fg='white',
                **speed_btn_style
            )
            btn.pack(side=tk.LEFT, padx=1)
            speed_buttons.append(btn)

        logger.debug("PlaybackBuilder: Playback controls built")

        return {
            'playback_row': playback_row,
            'load_button': load_button,
            'play_button': play_button,
            'step_button': step_button,
            'reset_button': reset_button,
            'speed_label': speed_label,
            'speed_buttons': speed_buttons,
        }
