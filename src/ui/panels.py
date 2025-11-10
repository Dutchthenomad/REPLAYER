"""
UI Panel Classes
Specialized panels for different UI sections
"""

import tkinter as tk
from tkinter import ttk
from decimal import Decimal
from typing import Optional, Dict, Callable
import logging

from ui.layout_manager import Panel, PanelConfig
from ui.widgets import ChartWidget

logger = logging.getLogger(__name__)


class StatusPanel(Panel):
    """
    Top status bar showing game state
    Displays: tick, price, phase, balance
    """

    def __init__(self, parent: tk.Widget, config: PanelConfig):
        super().__init__(parent, config)
        self._create_widgets()

    def _create_widgets(self):
        """Create status display widgets"""
        # Tick display
        self.tick_label = tk.Label(
            self.frame,
            text="Tick: 0",
            font=('Arial', 12),
            bg=self.config.background,
            fg='white'
        )
        self.tick_label.pack(side=tk.LEFT, padx=10)

        # Price display (prominent)
        self.price_label = tk.Label(
            self.frame,
            text="Price: 1.0000x",
            font=('Arial', 14, 'bold'),
            bg=self.config.background,
            fg='#00ff88'
        )
        self.price_label.pack(side=tk.LEFT, padx=10)

        # Phase display
        self.phase_label = tk.Label(
            self.frame,
            text="Phase: UNKNOWN",
            font=('Arial', 12),
            bg=self.config.background,
            fg='#ffcc00'
        )
        self.phase_label.pack(side=tk.LEFT, padx=10)

        # Separator
        tk.Frame(self.frame, width=2, bg='#444444').pack(side=tk.LEFT, fill=tk.Y, padx=20)

        # Balance display
        self.balance_label = tk.Label(
            self.frame,
            text="Balance: 0.1000 SOL",
            font=('Arial', 12, 'bold'),
            bg=self.config.background,
            fg='white'
        )
        self.balance_label.pack(side=tk.LEFT, padx=10)

        # P&L display
        self.pnl_label = tk.Label(
            self.frame,
            text="P&L: +0.0000 SOL",
            font=('Arial', 12),
            bg=self.config.background,
            fg='#00ff88'
        )
        self.pnl_label.pack(side=tk.LEFT, padx=10)

    def update(self, tick: int = 0, price: float = 1.0, phase: str = "UNKNOWN",
               balance: float = 0.1, pnl: float = 0.0):
        """Update status display"""
        self.tick_label.config(text=f"Tick: {tick}")
        self.price_label.config(text=f"Price: {price:.4f}x")
        self.phase_label.config(text=f"Phase: {phase}")
        self.balance_label.config(text=f"Balance: {balance:.4f} SOL")

        # Color-code P&L
        pnl_color = '#00ff88' if pnl >= 0 else '#ff3366'
        pnl_text = f"P&L: {'+' if pnl >= 0 else ''}{pnl:.4f} SOL"
        self.pnl_label.config(text=pnl_text, fg=pnl_color)


class ChartPanel(Panel):
    """
    Center panel for price chart display
    """

    def __init__(self, parent: tk.Widget, config: PanelConfig, width: int = 800, height: int = 300):
        super().__init__(parent, config)
        self.chart_width = width
        self.chart_height = height
        self._create_widgets()

    def _create_widgets(self):
        """Create chart and controls"""
        # Chart widget
        self.chart = ChartWidget(self.frame, width=self.chart_width, height=self.chart_height)
        self.chart.pack(pady=5)

        # Chart controls
        controls_frame = tk.Frame(self.frame, bg=self.config.background)
        controls_frame.pack(fill=tk.X, pady=5)

        # Zoom buttons
        tk.Button(
            controls_frame,
            text="🔍+ Zoom In",
            command=self.chart.zoom_in,
            bg='#444444',
            fg='white',
            font=('Arial', 9)
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            controls_frame,
            text="🔍- Zoom Out",
            command=self.chart.zoom_out,
            bg='#444444',
            fg='white',
            font=('Arial', 9)
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            controls_frame,
            text="↺ Reset Zoom",
            command=self.chart.reset_zoom,
            bg='#444444',
            fg='white',
            font=('Arial', 9)
        ).pack(side=tk.LEFT, padx=5)

    def update_chart(self, ticks, current_index=None):
        """Update chart with new data"""
        self.chart.update_data(ticks, current_index)

    def add_marker(self, tick_index, marker_type, color='#00ff88'):
        """Add a marker to the chart"""
        self.chart.add_marker(tick_index, marker_type, color)


class TradingPanel(Panel):
    """
    Trading controls panel
    Buy/Sell/Sidebet buttons and amount input
    """

    def __init__(self, parent: tk.Widget, config: PanelConfig, on_buy: Callable,
                 on_sell: Callable, on_sidebet: Callable):
        self.on_buy = on_buy
        self.on_sell = on_sell
        self.on_sidebet = on_sidebet
        super().__init__(parent, config)
        self._create_widgets()

    def _create_widgets(self):
        """Create trading controls"""
        # Title
        title = tk.Label(
            self.frame,
            text="TRADING CONTROLS",
            font=('Arial', 11, 'bold'),
            bg=self.config.background,
            fg='#00ff88'
        )
        title.pack(pady=(0, 5))

        # Amount input
        input_frame = tk.Frame(self.frame, bg=self.config.background)
        input_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            input_frame,
            text="Amount (SOL):",
            font=('Arial', 10),
            bg=self.config.background,
            fg='white'
        ).pack(side=tk.LEFT, padx=5)

        self.amount_entry = tk.Entry(
            input_frame,
            font=('Arial', 10),
            bg='#333333',
            fg='white',
            insertbackground='white',
            width=10
        )
        self.amount_entry.pack(side=tk.LEFT, padx=5)
        self.amount_entry.insert(0, "0.001")

        # Quick amount buttons
        quick_frame = tk.Frame(self.frame, bg=self.config.background)
        quick_frame.pack(fill=tk.X, pady=5)

        for amount in ["0.001", "0.005", "0.010", "0.050"]:
            tk.Button(
                quick_frame,
                text=amount,
                command=lambda a=amount: self.set_amount(a),
                bg='#444444',
                fg='white',
                font=('Arial', 8),
                width=6
            ).pack(side=tk.LEFT, padx=2)

        # Action buttons
        buttons_frame = tk.Frame(self.frame, bg=self.config.background)
        buttons_frame.pack(fill=tk.X, pady=5)

        self.buy_button = tk.Button(
            buttons_frame,
            text="🟢 BUY (B)",
            command=self.on_buy,
            bg='#00aa44',
            fg='white',
            font=('Arial', 11, 'bold'),
            width=12,
            height=2
        )
        self.buy_button.pack(side=tk.LEFT, padx=5)

        self.sell_button = tk.Button(
            buttons_frame,
            text="🔴 SELL (S)",
            command=self.on_sell,
            bg='#cc2244',
            fg='white',
            font=('Arial', 11, 'bold'),
            width=12,
            height=2,
            state=tk.DISABLED
        )
        self.sell_button.pack(side=tk.LEFT, padx=5)

        self.sidebet_button = tk.Button(
            buttons_frame,
            text="💎 SIDEBET (D)",
            command=self.on_sidebet,
            bg='#3366ff',
            fg='white',
            font=('Arial', 11, 'bold'),
            width=12,
            height=2
        )
        self.sidebet_button.pack(side=tk.LEFT, padx=5)

    def get_amount(self) -> Optional[Decimal]:
        """Get current amount from entry"""
        try:
            return Decimal(self.amount_entry.get())
        except:
            return None

    def set_amount(self, amount: str):
        """Set amount in entry"""
        self.amount_entry.delete(0, tk.END)
        self.amount_entry.insert(0, amount)

    def enable_buy(self):
        """Enable buy button"""
        self.buy_button.config(state=tk.NORMAL)

    def disable_buy(self):
        """Disable buy button"""
        self.buy_button.config(state=tk.DISABLED)

    def enable_sell(self):
        """Enable sell button"""
        self.sell_button.config(state=tk.NORMAL)

    def disable_sell(self):
        """Disable sell button"""
        self.sell_button.config(state=tk.DISABLED)

    def enable_sidebet(self):
        """Enable sidebet button"""
        self.sidebet_button.config(state=tk.NORMAL)

    def disable_sidebet(self):
        """Disable sidebet button"""
        self.sidebet_button.config(state=tk.DISABLED)


class BotPanel(Panel):
    """
    Bot controls panel
    Enable/disable bot, select strategy, view bot status
    """

    def __init__(self, parent: tk.Widget, config: PanelConfig, strategies: list,
                 on_toggle: Callable, on_strategy_change: Callable):
        self.strategies = strategies
        self.on_toggle = on_toggle
        self.on_strategy_change = on_strategy_change
        self.bot_enabled = False
        super().__init__(parent, config)
        self._create_widgets()

    def _create_widgets(self):
        """Create bot controls"""
        # Title
        title = tk.Label(
            self.frame,
            text="BOT CONTROLS",
            font=('Arial', 11, 'bold'),
            bg=self.config.background,
            fg='#3366ff'
        )
        title.pack(pady=(0, 5))

        # Toggle button
        self.toggle_button = tk.Button(
            self.frame,
            text="🤖 ENABLE BOT (SPACE)",
            command=self._on_toggle_click,
            bg='#444444',
            fg='white',
            font=('Arial', 10, 'bold'),
            width=20,
            height=2
        )
        self.toggle_button.pack(pady=5)

        # Strategy selector
        strategy_frame = tk.Frame(self.frame, bg=self.config.background)
        strategy_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            strategy_frame,
            text="Strategy:",
            font=('Arial', 10),
            bg=self.config.background,
            fg='white'
        ).pack(side=tk.LEFT, padx=5)

        self.strategy_var = tk.StringVar(value=self.strategies[0] if self.strategies else "")
        self.strategy_dropdown = ttk.Combobox(
            strategy_frame,
            textvariable=self.strategy_var,
            values=self.strategies,
            state='readonly',
            width=15
        )
        self.strategy_dropdown.pack(side=tk.LEFT, padx=5)
        self.strategy_dropdown.bind('<<ComboboxSelected>>', lambda e: self.on_strategy_change(self.strategy_var.get()))

        # Bot status
        self.status_label = tk.Label(
            self.frame,
            text="Status: Disabled",
            font=('Arial', 9),
            bg=self.config.background,
            fg='#666666'
        )
        self.status_label.pack(pady=5)

    def _on_toggle_click(self):
        """Handle toggle button click"""
        self.bot_enabled = not self.bot_enabled
        self.on_toggle(self.bot_enabled)
        self._update_ui()

    def _update_ui(self):
        """Update UI based on bot state"""
        if self.bot_enabled:
            self.toggle_button.config(
                text="🤖 DISABLE BOT (SPACE)",
                bg='#00aa44'
            )
            self.status_label.config(
                text=f"Status: Active ({self.strategy_var.get()})",
                fg='#00ff88'
            )
        else:
            self.toggle_button.config(
                text="🤖 ENABLE BOT (SPACE)",
                bg='#444444'
            )
            self.status_label.config(
                text="Status: Disabled",
                fg='#666666'
            )

    def set_enabled(self, enabled: bool):
        """Set bot enabled state programmatically"""
        self.bot_enabled = enabled
        self._update_ui()


class ControlsPanel(Panel):
    """
    Replay controls panel
    Play/pause, speed, file loading
    """

    def __init__(self, parent: tk.Widget, config: PanelConfig,
                 on_play_pause: Callable, on_load_file: Callable):
        self.on_play_pause = on_play_pause
        self.on_load_file = on_load_file
        self.is_playing = False
        super().__init__(parent, config)
        self._create_widgets()

    def _create_widgets(self):
        """Create replay controls"""
        # Title
        title = tk.Label(
            self.frame,
            text="REPLAY CONTROLS",
            font=('Arial', 11, 'bold'),
            bg=self.config.background,
            fg='#ffcc00'
        )
        title.pack(pady=(0, 5))

        # Control buttons
        buttons_frame = tk.Frame(self.frame, bg=self.config.background)
        buttons_frame.pack(fill=tk.X, pady=5)

        self.play_pause_button = tk.Button(
            buttons_frame,
            text="▶ PLAY (P)",
            command=self._on_play_pause_click,
            bg='#444444',
            fg='white',
            font=('Arial', 10, 'bold'),
            width=15
        )
        self.play_pause_button.pack(side=tk.LEFT, padx=5)

        self.load_button = tk.Button(
            buttons_frame,
            text="📂 LOAD FILE (L)",
            command=self.on_load_file,
            bg='#444444',
            fg='white',
            font=('Arial', 10, 'bold'),
            width=15
        )
        self.load_button.pack(side=tk.LEFT, padx=5)

        # Speed control
        speed_frame = tk.Frame(self.frame, bg=self.config.background)
        speed_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            speed_frame,
            text="Speed:",
            font=('Arial', 10),
            bg=self.config.background,
            fg='white'
        ).pack(side=tk.LEFT, padx=5)

        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_scale = tk.Scale(
            speed_frame,
            from_=0.1,
            to=5.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=self.speed_var,
            bg=self.config.background,
            fg='white',
            highlightthickness=0,
            length=200
        )
        self.speed_scale.pack(side=tk.LEFT, padx=5)

        self.speed_label = tk.Label(
            speed_frame,
            text="1.0x",
            font=('Arial', 10),
            bg=self.config.background,
            fg='white',
            width=5
        )
        self.speed_label.pack(side=tk.LEFT, padx=5)

        # Update speed label when scale changes
        self.speed_var.trace('w', self._update_speed_label)

    def _on_play_pause_click(self):
        """Handle play/pause button click"""
        self.is_playing = not self.is_playing
        self.on_play_pause(self.is_playing)
        self._update_ui()

    def _update_ui(self):
        """Update UI based on play state"""
        if self.is_playing:
            self.play_pause_button.config(
                text="⏸ PAUSE (P)",
                bg='#cc2244'
            )
        else:
            self.play_pause_button.config(
                text="▶ PLAY (P)",
                bg='#00aa44'
            )

    def _update_speed_label(self, *args):
        """Update speed label text"""
        self.speed_label.config(text=f"{self.speed_var.get():.1f}x")

    def get_speed(self) -> float:
        """Get current playback speed"""
        return self.speed_var.get()

    def set_playing(self, playing: bool):
        """Set playing state programmatically"""
        self.is_playing = playing
        self._update_ui()
