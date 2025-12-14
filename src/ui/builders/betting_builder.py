"""
BettingBuilder - Builds the bet amount controls row

Extracted from MainWindow._create_ui() (Phase 1)
Handles construction of bet entry, increment buttons, and balance display.
"""

import tkinter as tk
from typing import Callable, Dict
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class BettingBuilder:
    """
    Builds the bet amount controls row.

    Usage:
        callbacks = {
            'clear_bet': lambda: controller.clear_bet(),
            'increment_bet': lambda amount: controller.increment_bet(amount),
            'half_bet': lambda: controller.half_bet(),
            'double_bet': lambda: controller.double_bet(),
            'max_bet': lambda: controller.max_bet(),
            'toggle_balance_lock': lambda: controller.toggle_balance_lock(),
        }
        builder = BettingBuilder(parent, callbacks, default_bet, initial_balance)
        widgets = builder.build()
    """

    def __init__(
        self,
        parent: tk.Tk,
        callbacks: Dict[str, Callable],
        default_bet: Decimal,
        initial_balance: Decimal
    ):
        """
        Initialize BettingBuilder.

        Args:
            parent: Parent Tk widget
            callbacks: Dictionary of callback functions
            default_bet: Default bet amount
            initial_balance: Initial wallet balance
        """
        self.parent = parent
        self.callbacks = callbacks
        self.default_bet = default_bet
        self.initial_balance = initial_balance

    def build(self) -> dict:
        """
        Build the bet controls row and return widget references.

        Returns:
            dict with keys:
                - bet_row: The bet row frame
                - bet_entry: Bet amount entry field
                - clear_button: Clear (X) button
                - increment_*_button: Increment buttons
                - half_button: 1/2 button
                - double_button: X2 button
                - max_button: MAX button
                - balance_label: Wallet balance label
                - balance_lock_button: Lock/unlock button
        """
        # Bet row frame
        bet_row = tk.Frame(self.parent, bg='#1a1a1a', height=40)
        bet_row.pack(fill=tk.X)
        bet_row.pack_propagate(False)

        # Left - bet amount display
        bet_left = tk.Frame(bet_row, bg='#1a1a1a')
        bet_left.pack(side=tk.LEFT, padx=10)

        bet_entry = tk.Entry(
            bet_left,
            bg='#000000',
            fg='white',
            font=('Arial', 14, 'bold'),
            width=8,
            bd=1,
            relief=tk.SOLID,
            justify=tk.RIGHT
        )
        bet_entry.pack(side=tk.LEFT)
        bet_entry.insert(0, str(self.default_bet))

        tk.Label(bet_left, text="SOL", bg='#1a1a1a', fg='white', font=('Arial', 10)).pack(side=tk.LEFT, padx=5)

        # Center - bet adjustment buttons
        bet_center = tk.Frame(bet_row, bg='#1a1a1a')
        bet_center.pack(side=tk.LEFT, padx=10)

        bet_btn_style = {'font': ('Arial', 9), 'width': 6, 'bd': 1, 'relief': tk.RAISED}
        increment_bet = self.callbacks.get('increment_bet', lambda a: None)

        clear_button = tk.Button(
            bet_center,
            text="X",
            command=self.callbacks.get('clear_bet', lambda: None),
            bg='#333333',
            fg='white',
            **bet_btn_style
        )
        clear_button.pack(side=tk.LEFT, padx=2)

        increment_001_button = tk.Button(
            bet_center,
            text="+0.001",
            command=lambda: increment_bet(Decimal('0.001')),
            bg='#333333',
            fg='white',
            **bet_btn_style
        )
        increment_001_button.pack(side=tk.LEFT, padx=2)

        increment_01_button = tk.Button(
            bet_center,
            text="+0.01",
            command=lambda: increment_bet(Decimal('0.01')),
            bg='#333333',
            fg='white',
            **bet_btn_style
        )
        increment_01_button.pack(side=tk.LEFT, padx=2)

        increment_10_button = tk.Button(
            bet_center,
            text="+0.1",
            command=lambda: increment_bet(Decimal('0.1')),
            bg='#333333',
            fg='white',
            **bet_btn_style
        )
        increment_10_button.pack(side=tk.LEFT, padx=2)

        increment_1_button = tk.Button(
            bet_center,
            text="+1",
            command=lambda: increment_bet(Decimal('1')),
            bg='#333333',
            fg='white',
            **bet_btn_style
        )
        increment_1_button.pack(side=tk.LEFT, padx=2)

        half_button = tk.Button(
            bet_center,
            text="1/2",
            command=self.callbacks.get('half_bet', lambda: None),
            bg='#333333',
            fg='white',
            **bet_btn_style
        )
        half_button.pack(side=tk.LEFT, padx=2)

        double_button = tk.Button(
            bet_center,
            text="X2",
            command=self.callbacks.get('double_bet', lambda: None),
            bg='#333333',
            fg='white',
            **bet_btn_style
        )
        double_button.pack(side=tk.LEFT, padx=2)

        max_button = tk.Button(
            bet_center,
            text="MAX",
            command=self.callbacks.get('max_bet', lambda: None),
            bg='#333333',
            fg='white',
            **bet_btn_style
        )
        max_button.pack(side=tk.LEFT, padx=2)

        # Right - wallet balance + lock control
        balance_container = tk.Frame(bet_row, bg='#1a1a1a')
        balance_container.pack(side=tk.RIGHT, padx=5)

        balance_lock_button = tk.Button(
            balance_container,
            text="\U0001F512",  # 🔒
            command=self.callbacks.get('toggle_balance_lock', lambda: None),
            bg='#333333',
            fg='white',
            font=('Arial', 10, 'bold'),
            bd=1,
            relief=tk.RAISED,
            width=3
        )
        balance_lock_button.pack(side=tk.RIGHT, padx=4)

        balance_label = tk.Label(
            balance_container,
            text=f"WALLET: {self.initial_balance:.3f}",
            font=('Arial', 11, 'bold'),
            bg='#1a1a1a',
            fg='#ffcc00'
        )
        balance_label.pack(side=tk.RIGHT, padx=4)

        logger.debug("BettingBuilder: Bet controls built")

        return {
            'bet_row': bet_row,
            'bet_entry': bet_entry,
            'clear_button': clear_button,
            'increment_001_button': increment_001_button,
            'increment_01_button': increment_01_button,
            'increment_10_button': increment_10_button,
            'increment_1_button': increment_1_button,
            'half_button': half_button,
            'double_button': double_button,
            'max_button': max_button,
            'balance_label': balance_label,
            'balance_lock_button': balance_lock_button,
        }
