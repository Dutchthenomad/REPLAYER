"""
ActionBuilder - Builds the action buttons row

Extracted from MainWindow._create_ui() (Phase 1)
Handles construction of SIDEBET, BUY, SELL buttons, percentage selectors, and bot controls.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List
import logging

logger = logging.getLogger(__name__)


class ActionBuilder:
    """
    Builds the action buttons row with trading controls and bot interface.

    Usage:
        callbacks = {
            'execute_sidebet': lambda: controller.execute_sidebet(),
            'execute_buy': lambda: controller.execute_buy(),
            'execute_sell': lambda: controller.execute_sell(),
            'set_sell_percentage': lambda p: controller.set_percentage(p),
            'toggle_bot': lambda: bot_manager.toggle_bot(),
            'on_strategy_changed': lambda e: bot_manager.on_strategy_changed(e),
        }
        builder = ActionBuilder(parent, callbacks, strategies, initial_strategy)
        widgets = builder.build()
    """

    def __init__(
        self,
        parent: tk.Tk,
        callbacks: Dict[str, Callable],
        strategies: List[str],
        initial_strategy: str,
        bot_enabled: bool = False
    ):
        """
        Initialize ActionBuilder.

        Args:
            parent: Parent Tk widget
            callbacks: Dictionary of callback functions
            strategies: List of available strategy names
            initial_strategy: Initially selected strategy
            bot_enabled: Initial bot enabled state
        """
        self.parent = parent
        self.callbacks = callbacks
        self.strategies = strategies
        self.initial_strategy = initial_strategy
        self.bot_enabled = bot_enabled

    def build(self) -> dict:
        """
        Build the action buttons row and return widget references.

        Returns:
            dict with keys: action_row, sidebet_button, buy_button, sell_button,
            percentage_buttons, bot_toggle_button, strategy_var, strategy_dropdown,
            bot_status_label, position_label, sidebet_status_label
        """
        # Action row frame
        action_row = tk.Frame(self.parent, bg='#1a1a1a', height=80)
        action_row.pack(fill=tk.X)
        action_row.pack_propagate(False)

        # Left - large action buttons
        action_left = tk.Frame(action_row, bg='#1a1a1a')
        action_left.pack(side=tk.LEFT, padx=10, pady=10)

        large_btn_style = {'font': ('Arial', 14, 'bold'), 'width': 10, 'height': 2, 'bd': 2, 'relief': tk.RAISED}

        sidebet_button = tk.Button(
            action_left,
            text="SIDEBET",
            command=self.callbacks.get('execute_sidebet', lambda: None),
            bg='#3399ff',
            fg='white',
            state=tk.NORMAL,
            **large_btn_style
        )
        sidebet_button.pack(side=tk.LEFT, padx=5)

        buy_button = tk.Button(
            action_left,
            text="BUY",
            command=self.callbacks.get('execute_buy', lambda: None),
            bg='#00ff66',
            fg='black',
            state=tk.NORMAL,
            **large_btn_style
        )
        buy_button.pack(side=tk.LEFT, padx=5)

        sell_button = tk.Button(
            action_left,
            text="SELL",
            command=self.callbacks.get('execute_sell', lambda: None),
            bg='#ff3399',
            fg='white',
            state=tk.NORMAL,
            **large_btn_style
        )
        sell_button.pack(side=tk.LEFT, padx=5)

        # Separator between action buttons and percentage selectors
        separator = tk.Frame(action_left, bg='#444444', width=2)
        separator.pack(side=tk.LEFT, padx=10, fill=tk.Y, pady=15)

        # Percentage buttons (smaller, radio-style)
        pct_btn_style = {'font': ('Arial', 10, 'bold'), 'width': 6, 'height': 1, 'bd': 2, 'relief': tk.RAISED}
        set_percentage = self.callbacks.get('set_sell_percentage', lambda p: None)

        percentage_buttons = {}
        percentages = [
            ('10%', 0.1, '#666666'),
            ('25%', 0.25, '#666666'),
            ('50%', 0.5, '#666666'),
            ('100%', 1.0, '#888888')  # Default selected (darker)
        ]

        for text, value, default_color in percentages:
            btn = tk.Button(
                action_left,
                text=text,
                command=lambda v=value: set_percentage(v),
                bg=default_color,
                fg='white',
                **pct_btn_style
            )
            btn.pack(side=tk.LEFT, padx=3)
            percentage_buttons[value] = {
                'button': btn,
                'default_color': default_color,
                'selected_color': '#00cc66',  # Green when selected
                'value': value
            }

        # Right - bot and info
        action_right = tk.Frame(action_row, bg='#1a1a1a')
        action_right.pack(side=tk.RIGHT, padx=10, pady=10)

        # Bot controls (top right)
        bot_top = tk.Frame(action_right, bg='#1a1a1a')
        bot_top.pack(anchor='e')

        bot_toggle_button = tk.Button(
            bot_top,
            text="ENABLE BOT",
            command=self.callbacks.get('toggle_bot', lambda: None),
            bg='#444444',
            fg='white',
            font=('Arial', 10),
            width=12,
            state=tk.DISABLED
        )
        bot_toggle_button.pack(side=tk.LEFT, padx=5)

        tk.Label(bot_top, text="STRATEGY:", bg='#1a1a1a', fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=5)

        strategy_var = tk.StringVar(value=self.initial_strategy)
        strategy_dropdown = ttk.Combobox(
            bot_top,
            textvariable=strategy_var,
            values=self.strategies,
            state='readonly',
            width=12,
            font=('Arial', 9)
        )
        strategy_dropdown.pack(side=tk.LEFT)
        strategy_dropdown.bind('<<ComboboxSelected>>', self.callbacks.get('on_strategy_changed', lambda e: None))

        # Info labels (bottom right)
        bot_bottom = tk.Frame(action_right, bg='#1a1a1a')
        bot_bottom.pack(anchor='e', pady=(5, 0))

        bot_status_label = tk.Label(
            bot_bottom,
            text="BOT: DISABLED",
            font=('Arial', 10),
            bg='#1a1a1a',
            fg='#666666'
        )
        bot_status_label.pack(side=tk.LEFT, padx=10)

        position_label = tk.Label(
            bot_bottom,
            text="POSITION: NONE",
            font=('Arial', 10),
            bg='#1a1a1a',
            fg='#666666'
        )
        position_label.pack(side=tk.LEFT, padx=10)

        sidebet_status_label = tk.Label(
            bot_bottom,
            text="SIDEBET: NONE",
            font=('Arial', 10),
            bg='#1a1a1a',
            fg='#666666'
        )
        sidebet_status_label.pack(side=tk.LEFT, padx=10)

        logger.debug("ActionBuilder: Action buttons built")

        return {
            'action_row': action_row,
            'sidebet_button': sidebet_button,
            'buy_button': buy_button,
            'sell_button': sell_button,
            'percentage_buttons': percentage_buttons,
            'bot_toggle_button': bot_toggle_button,
            'strategy_var': strategy_var,
            'strategy_dropdown': strategy_dropdown,
            'bot_status_label': bot_status_label,
            'position_label': position_label,
            'sidebet_status_label': sidebet_status_label,
        }
