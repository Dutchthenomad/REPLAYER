"""
Modern UI Main Window
Replaces the standard MainWindow with a game-like interface.
Uses custom components: RugsChartLog and GameButton3D.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import decimal
from decimal import Decimal
import logging
import threading

# Local imports
from core import ReplayEngine, TradeManager
from core.game_queue import GameQueue
from models import GameTick
from ui.widgets import ToastNotification
from ui.tk_dispatcher import TkDispatcher
from ui.bot_config_panel import BotConfigPanel
from bot import BotInterface, BotController, list_strategies
from bot.async_executor import AsyncBotExecutor
from bot.execution_mode import ExecutionMode
from bot.ui_controller import BotUIController
from bot.browser_bridge import get_browser_bridge
from sources import WebSocketFeed

# New UI Components
from ui.components.game_button import GameButton3D
from ui.components.rugs_chart import RugsChartLog

logger = logging.getLogger(__name__)

# Palette constants
COLOR_BG_PANEL = "#1e2832"
COLOR_INPUT_BG = "#1e2832"
BTN_CTRL_BG = "#5fa8d3"
BTN_CTRL_FG = "white"

# Button Colors
BTN_BUY_FACE = "#00e676"
BTN_BUY_DEPTH = "#00b359"
BTN_SELL_FACE = "#ff3d00"
BTN_SELL_DEPTH = "#cc2900"
BTN_SIDE_FACE = "#2979ff"
BTN_SIDE_DEPTH = "#1565c0"


class ModernMainWindow:
    """
    Modern, game-like application window.
    Replaces standard Tkinter widgets with custom drawn components.
    """

    def __init__(self, root: tk.Tk, state, event_bus, config, live_mode: bool = False):
        self.root = root
        self.state = state
        self.event_bus = event_bus
        self.config = config
        self.live_mode = live_mode

        # Configure root for dark theme
        self.root.configure(bg=COLOR_BG_PANEL)

        # Browser Automation (same as standard UI)
        self.browser_executor = None
        self.browser_connected = False
        try:
            from bot.browser_executor import BrowserExecutor
            self.browser_executor = BrowserExecutor(profile_name="rugs_fun_phantom")
        except Exception as e:
            logger.warning(f"BrowserExecutor not available: {e}")

        self.browser_bridge = get_browser_bridge()
        self.browser_bridge.on_status_change = self._on_bridge_status_change

        # Core Engines
        self.replay_engine = ReplayEngine(state)
        self.trade_manager = TradeManager(state)
        self.game_queue = GameQueue(config.FILES['recordings_dir'])
        self.multi_game_mode = False

        # Chart candlestick settings - AUDIT FIX: Track tick for proper candlestick rendering
        self.candle_period = 10  # Create new candle every N ticks
        self.last_candle_tick = -1  # Track which tick started the last candle

        # Bot Setup
        self.bot_config_panel = BotConfigPanel(root, config_file="bot_config.json")
        self.bot_interface = BotInterface(state, self.trade_manager)
        self.bot_enabled = self.bot_config_panel.is_bot_enabled()
        
        # Bot Placeholders
        self.bot_ui_controller = None
        self.bot_controller = None
        self.bot_executor = None

        # Live Feed
        self.live_feed = None
        self.live_feed_connected = False

        # UI State
        self.ui_dispatcher = TkDispatcher(self.root)
        self.user_paused = True

        # Replay Callbacks
        self.replay_engine.on_tick_callback = self._on_tick_update
        self.replay_engine.on_game_end_callback = self._on_game_end

        # Create UI Layout
        self.toast = None
        self._create_ui()
        self._setup_event_handlers()
        self._setup_keyboard_shortcuts()

        # Initialize Bot components (Post-UI creation)
        self._init_bot_components()

        # Auto-start bot if enabled
        if self.bot_enabled:
            self.bot_executor.start()
            logger.info("Bot executor auto-started")

        # Start periodic checks
        self._check_bot_results()

    def _create_ui(self):
        """Build the Modern UI layout"""
        # 1. Menu Bar (Standard functionality)
        self._create_menu_bar()

        # 2. Main Content Frame
        main_frame = tk.Frame(self.root, bg=COLOR_BG_PANEL)
        main_frame.pack(fill="both", expand=True)

        # --- STATUS BAR (Phase 3.1) ---
        self._create_status_bar(main_frame)

        # --- CHART AREA ---
        chart_container = tk.Frame(main_frame, bg=COLOR_BG_PANEL)
        chart_container.pack(fill="both", expand=True, padx=10, pady=5)

        self.chart = RugsChartLog(chart_container)
        self.chart.pack(fill="both", expand=True)

        # --- PLAYBACK CONTROLS (Phase 3.2) ---
        self._create_playback_bar(main_frame)

        # --- CONTROL BAR ---
        self._create_control_bar(main_frame)

        # --- ACTION AREA ---
        self._create_action_area(main_frame)

        # --- INFO PANEL (Phase 3.3) ---
        self._create_info_panel(main_frame)

        # Initialize Toast
        self.toast = ToastNotification(self.root)

    def _create_control_bar(self, parent):
        """Bet amount inputs and quick buttons"""
        bar_frame = tk.Frame(parent, bg=COLOR_BG_PANEL)
        bar_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Left: Bet Input
        input_group = tk.Frame(bar_frame, bg=COLOR_BG_PANEL)
        input_group.pack(side="left", fill="y", padx=(0, 10))
        
        # Amount Entry (Custom styled)
        self.bet_var = tk.StringVar(value=str(self.config.FINANCIAL['default_bet']))
        self.bet_entry = tk.Entry(input_group, textvariable=self.bet_var, 
                                font=("Comic Sans MS", 14, "bold"), 
                                bg=COLOR_INPUT_BG, fg="white", 
                                width=8, bd=0, justify="center")
        self.bet_entry.pack(side="left", padx=5, pady=10)
        
        # Divider
        tk.Frame(input_group, bg="#444", width=1).pack(side="left", fill="y", pady=5)
        
        # Quick Buttons
        vals = [
            ("+0.001", lambda: self.increment_bet_amount(Decimal('0.001'))),
            ("+0.01", lambda: self.increment_bet_amount(Decimal('0.01'))),
            ("+0.1", lambda: self.increment_bet_amount(Decimal('0.1'))),
            ("+1", lambda: self.increment_bet_amount(Decimal('1'))),
            ("1/2", self.half_bet_amount),
            ("X2", self.double_bet_amount),
            ("MAX", self.max_bet_amount)
        ]
        
        for txt, cmd in vals:
            btn = tk.Button(input_group, text=txt, font=("Arial", 9, "bold"), 
                          bg=BTN_CTRL_BG, fg=BTN_CTRL_FG, 
                          activebackground="#4a90e2", activeforeground="white", 
                          bd=0, padx=8, pady=4, cursor="hand2",
                          command=cmd)
            btn.pack(side="left", padx=2)

        # Right: Bot/Strategy
        right_group = tk.Frame(bar_frame, bg=COLOR_BG_PANEL)
        right_group.pack(side="right")
        
        # Bot Status Icon
        self.bot_status_indicator = tk.Button(right_group, text="🤖", font=("Arial", 12), 
                                            bg="#444", fg="white", bd=0, width=4,
                                            command=self.toggle_bot)
        self.bot_status_indicator.pack(side="left", padx=2)
        
        # Percentages
        self.pct_buttons = {}
        pcts = [("10%", 0.1), ("25%", 0.25), ("50%", 0.5), ("100%", 1.0)]
        for txt, val in pcts:
            btn = tk.Button(right_group, text=txt, font=("Arial", 9, "bold"), 
                          bg=BTN_CTRL_BG, fg=BTN_CTRL_FG, 
                          bd=0, padx=8, pady=4,
                          command=lambda v=val: self.set_sell_percentage(v))
            btn.pack(side="left", padx=2)
            self.pct_buttons[val] = btn

    def _create_action_area(self, parent):
        """Big 3D Action Buttons"""
        action_frame = tk.Frame(parent, bg=COLOR_BG_PANEL)
        action_frame.pack(fill="x", padx=10, pady=(0, 20))
        
        center_container = tk.Frame(action_frame, bg=COLOR_BG_PANEL)
        center_container.pack(anchor="center")
        
        # BUY
        self.buy_button = GameButton3D(center_container, text="BUY", subtext="+0.001 SOL", 
                                     face_color=BTN_BUY_FACE, depth_color=BTN_BUY_DEPTH,
                                     width=220, height=75,
                                     command=self.execute_buy)
        self.buy_button.pack(side="left", padx=15)
        
        # SELL
        self.sell_button = GameButton3D(center_container, text="SELL", subtext=None,
                                      face_color=BTN_SELL_FACE, depth_color=BTN_SELL_DEPTH,
                                      width=220, height=75,
                                      command=self.execute_sell)
        self.sell_button.pack(side="left", padx=15)
        
        # SIDEBET
        self.sidebet_button = GameButton3D(center_container, text="SIDE BET", subtext="5x WIN",
                                         face_color=BTN_SIDE_FACE, depth_color=BTN_SIDE_DEPTH,
                                         width=220, height=75,
                                         command=self.execute_sidebet)
        self.sidebet_button.pack(side="left", padx=15)

    def _create_status_bar(self, parent):
        """Create top status bar with game info (Phase 3.1)"""
        status_bar = tk.Frame(parent, bg='#0a0f14', height=35)
        status_bar.pack(fill="x")
        status_bar.pack_propagate(False)

        # Left section - tick and price
        left_section = tk.Frame(status_bar, bg='#0a0f14')
        left_section.pack(side="left", fill="y", padx=10)

        self.tick_label = tk.Label(
            left_section,
            text="TICK: 0",
            font=("Roboto Mono", 11, "bold"),
            bg='#0a0f14',
            fg='#00e5ff'
        )
        self.tick_label.pack(side="left", padx=(0, 20))

        self.price_label = tk.Label(
            left_section,
            text="PRICE: 1.0000 X",
            font=("Roboto Mono", 11, "bold"),
            bg='#0a0f14',
            fg='#ffea00'
        )
        self.price_label.pack(side="left", padx=(0, 20))

        # Center section - game phase
        center_section = tk.Frame(status_bar, bg='#0a0f14')
        center_section.pack(side="left", fill="y", expand=True)

        self.phase_label = tk.Label(
            center_section,
            text="PHASE: WAITING",
            font=("Roboto Mono", 11, "bold"),
            bg='#0a0f14',
            fg='#b0bec5'
        )
        self.phase_label.pack(pady=6)

        # Right section - connection indicators
        right_section = tk.Frame(status_bar, bg='#0a0f14')
        right_section.pack(side="right", fill="y", padx=10)

        self.browser_indicator = tk.Label(
            right_section,
            text="⚫ BROWSER",
            font=("Arial", 9),
            bg='#0a0f14',
            fg='#666666'
        )
        self.browser_indicator.pack(side="right", padx=5)

        self.live_indicator = tk.Label(
            right_section,
            text="⚫ LIVE",
            font=("Arial", 9),
            bg='#0a0f14',
            fg='#666666'
        )
        self.live_indicator.pack(side="right", padx=5)

        self.bot_indicator = tk.Label(
            right_section,
            text="⚫ BOT",
            font=("Arial", 9),
            bg='#0a0f14',
            fg='#666666'
        )
        self.bot_indicator.pack(side="right", padx=5)

    def _create_playback_bar(self, parent):
        """Create playback control bar (Phase 3.2)"""
        playback_bar = tk.Frame(parent, bg='#141e28', height=45)
        playback_bar.pack(fill="x", padx=10, pady=5)
        playback_bar.pack_propagate(False)

        # Left - playback buttons
        left_frame = tk.Frame(playback_bar, bg='#141e28')
        left_frame.pack(side="left", fill="y", padx=5)

        btn_style = {
            'font': ('Arial', 10, 'bold'),
            'bd': 0,
            'padx': 15,
            'pady': 5,
            'cursor': 'hand2'
        }

        self.load_button = tk.Button(
            left_frame,
            text="📂 LOAD",
            bg='#37474f',
            fg='white',
            activebackground='#455a64',
            command=self._load_file_dialog,
            **btn_style
        )
        self.load_button.pack(side="left", padx=3, pady=6)

        self.play_button = tk.Button(
            left_frame,
            text="▶️ PLAY",
            bg='#00c853',
            fg='white',
            activebackground='#00e676',
            command=self._toggle_playback,
            **btn_style
        )
        self.play_button.pack(side="left", padx=3, pady=6)

        self.step_back_button = tk.Button(
            left_frame,
            text="⏮",
            bg='#546e7a',
            fg='white',
            activebackground='#78909c',
            command=self._step_backward,
            width=3,
            **btn_style
        )
        self.step_back_button.pack(side="left", padx=2, pady=6)

        self.step_fwd_button = tk.Button(
            left_frame,
            text="⏭",
            bg='#546e7a',
            fg='white',
            activebackground='#78909c',
            command=self._step_forward,
            width=3,
            **btn_style
        )
        self.step_fwd_button.pack(side="left", padx=2, pady=6)

        self.reset_button = tk.Button(
            left_frame,
            text="↺ RESET",
            bg='#d32f2f',
            fg='white',
            activebackground='#f44336',
            command=self._reset_game,
            **btn_style
        )
        self.reset_button.pack(side="left", padx=3, pady=6)

        # Right - speed controls
        right_frame = tk.Frame(playback_bar, bg='#141e28')
        right_frame.pack(side="right", fill="y", padx=10)

        self.speed_label = tk.Label(
            right_frame,
            text="SPEED: 1.0x",
            font=("Roboto Mono", 10, "bold"),
            bg='#141e28',
            fg='#90a4ae'
        )
        self.speed_label.pack(side="right", padx=5, pady=10)

        # Speed buttons
        speed_btn_style = {'font': ('Arial', 8, 'bold'), 'bd': 0, 'width': 4, 'cursor': 'hand2'}
        speeds = [0.25, 0.5, 1.0, 2.0, 5.0]

        for speed in reversed(speeds):
            btn = tk.Button(
                right_frame,
                text=f"{speed}x",
                bg='#263238' if speed != 1.0 else '#37474f',
                fg='white',
                activebackground='#455a64',
                command=lambda s=speed: self._on_speed_button_click(s),
                **speed_btn_style
            )
            btn.pack(side="right", padx=1, pady=10)

    def _create_info_panel(self, parent):
        """Create bottom info panel with trading stats (Phase 3.3)"""
        info_bar = tk.Frame(parent, bg='#0a0f14', height=40)
        info_bar.pack(fill="x", side="bottom")
        info_bar.pack_propagate(False)

        # Left - balance
        left_section = tk.Frame(info_bar, bg='#0a0f14')
        left_section.pack(side="left", fill="y", padx=15)

        self.balance_label = tk.Label(
            left_section,
            text=f"💰 BALANCE: {self.state.get('balance'):.4f} SOL",
            font=("Roboto Mono", 11, "bold"),
            bg='#0a0f14',
            fg='#ffc107'
        )
        self.balance_label.pack(pady=8)

        # Center - position info
        center_section = tk.Frame(info_bar, bg='#0a0f14')
        center_section.pack(side="left", fill="both", expand=True)

        self.position_label = tk.Label(
            center_section,
            text="📊 POSITION: NONE",
            font=("Roboto Mono", 10),
            bg='#0a0f14',
            fg='#78909c'
        )
        self.position_label.pack(side="left", padx=20, pady=10)

        self.sidebet_label = tk.Label(
            center_section,
            text="🎲 SIDEBET: NONE",
            font=("Roboto Mono", 10),
            bg='#0a0f14',
            fg='#78909c'
        )
        self.sidebet_label.pack(side="left", padx=20, pady=10)

        # Right - game info
        right_section = tk.Frame(info_bar, bg='#0a0f14')
        right_section.pack(side="right", fill="y", padx=15)

        self.game_label = tk.Label(
            right_section,
            text="📄 GAME: --",
            font=("Roboto Mono", 10),
            bg='#0a0f14',
            fg='#607d8b'
        )
        self.game_label.pack(pady=10)

    def _on_speed_button_click(self, speed: float):
        """Handle speed button click and update label"""
        self._set_playback_speed(speed)
        self.speed_label.config(text=f"SPEED: {speed}x")

    def _init_bot_components(self):
        """Initialize bot controller and executor"""
        bot_config = self.bot_config_panel.get_config()
        
        self.bot_ui_controller = BotUIController(
            self,
            button_depress_duration_ms=bot_config.get('button_depress_duration_ms', 50),
            inter_click_pause_ms=bot_config.get('inter_click_pause_ms', 100)
        )

        execution_mode = self.bot_config_panel.get_execution_mode()
        strategy = self.bot_config_panel.get_strategy()

        self.bot_controller = BotController(
            self.bot_interface,
            strategy_name=strategy,
            execution_mode=execution_mode,
            ui_controller=self.bot_ui_controller if execution_mode == ExecutionMode.UI_LAYER else None
        )
        
        self.bot_executor = AsyncBotExecutor(self.bot_controller)

    # ... (Methods below are ported from main_window.py with minimal changes for logic) ...
    
    def _on_tick_update(self, tick: GameTick, index: int, total: int):
        self.ui_dispatcher.submit(self._process_tick_ui, tick, index, total)

    def _process_tick_ui(self, tick: GameTick, index: int, total: int):
        """Execute tick updates on the Tk main thread"""
        # Update status bar labels
        self.tick_label.config(text=f"TICK: {tick.tick}")
        self.price_label.config(text=f"PRICE: {tick.price:.4f}X")

        # Show "RUGGED" if game was rugged (even during cooldown phase)
        display_phase = "RUGGED" if tick.rugged else tick.phase
        self.phase_label.config(text=f"PHASE: {display_phase}")

        # Update phase color
        phase_colors = {
            'WAITING': '#b0bec5',
            'COUNTDOWN': '#ffea00',
            'TRADING': '#00e676',
            'RUGGED': '#ff1744',
            'COOLDOWN': '#ff9100'
        }
        self.phase_label.config(fg=phase_colors.get(display_phase, '#b0bec5'))

        # Update Chart - AUDIT FIX: Create new candles every N ticks for proper candlestick display
        current_candle_group = tick.tick // self.candle_period
        last_candle_group = self.last_candle_tick // self.candle_period if self.last_candle_tick >= 0 else -1
        is_new_candle = current_candle_group > last_candle_group
        self.last_candle_tick = tick.tick
        self.chart.update_tick(tick.price, is_new_candle=is_new_candle)

        # Bot logic
        self.trade_manager.check_and_handle_rug(tick)
        self.trade_manager.check_sidebet_expiry(tick)

        if self.bot_enabled:
            self.bot_executor.queue_execution(tick)

        # Update position display
        position = self.state.get('position')
        if position and position.get('status') == 'active':
            entry_price = position['entry_price']
            amount = position['amount']
            pnl_pct = ((tick.price / entry_price) - 1) * 100
            pnl_sol = amount * (tick.price - entry_price)

            pnl_color = '#00e676' if pnl_sol >= 0 else '#ff5252'
            self.position_label.config(
                text=f"📊 POS: {pnl_sol:+.4f} SOL ({pnl_pct:+.1f}%)",
                fg=pnl_color
            )
        else:
            self.position_label.config(text="📊 POSITION: NONE", fg='#78909c')

        # Update sidebet countdown
        sidebet = self.state.get('sidebet')
        if sidebet and sidebet.get('status') == 'active':
            placed_tick = sidebet.get('placed_tick', 0)
            resolution_window = self.config.GAME_RULES.get('sidebet_window_ticks', 40)
            ticks_remaining = (placed_tick + resolution_window) - tick.tick

            if ticks_remaining > 0:
                self.sidebet_label.config(
                    text=f"🎲 SIDEBET: {ticks_remaining} ticks",
                    fg='#ffea00'
                )
            else:
                self.sidebet_label.config(text="🎲 SIDEBET: RESOLVING", fg='#ff9100')
        else:
            self.sidebet_label.config(text="🎲 SIDEBET: NONE", fg='#78909c')

        # Button States (only when bot is disabled)
        if not self.bot_enabled:
            if tick.is_tradeable():
                self.buy_button.config(state="normal")
                if not self.state.get('sidebet'):
                    self.sidebet_button.config(state="normal")
            else:
                self.buy_button.config(state="disabled")
                self.sidebet_button.config(state="disabled")

            # Sell Button
            if position and position.get('status') == 'active':
                self.sell_button.config(state="normal")
            else:
                self.sell_button.config(state="disabled")

    def execute_buy(self):
        self.browser_bridge.on_buy_clicked()
        amount = self.get_bet_amount()
        if amount is None: return
        
        result = self.trade_manager.execute_buy(amount)
        if result['success']:
            self.log(f"BUY: {result['price']:.4f}x")
            self.toast.show("BUY SUCCESS", "success")
        else:
            self.toast.show(f"BUY FAILED: {result['reason']}", "error")

    def execute_sell(self):
        self.browser_bridge.on_sell_clicked()
        result = self.trade_manager.execute_sell()
        if result['success']:
            pnl = result.get('pnl_sol', 0)
            self.toast.show(f"SOLD: {pnl:+.4f} SOL", "success" if pnl >= 0 else "error")
        else:
            self.toast.show(f"SELL FAILED: {result['reason']}", "error")

    def execute_sidebet(self):
        self.browser_bridge.on_sidebet_clicked()
        amount = self.get_bet_amount()
        if amount:
            self.trade_manager.execute_sidebet(amount)
            self.toast.show("SIDEBET PLACED", "warning")

    def get_bet_amount(self):
        try:
            return Decimal(self.bet_var.get())
        except (decimal.InvalidOperation, ValueError):
            # AUDIT FIX: Catch specific Decimal conversion exceptions
            return None

    def increment_bet_amount(self, val):
        try:
            curr = Decimal(self.bet_var.get())
        except (decimal.InvalidOperation, ValueError):
            # AUDIT FIX: Catch specific Decimal conversion exceptions
            curr = Decimal('0')
        self.bet_var.set(str(curr + val))
        self.browser_bridge.on_increment_clicked(f"+{val}")

    def half_bet_amount(self):
        try:
            curr = Decimal(self.bet_var.get())
            self.bet_var.set(str(curr / 2))
            self.browser_bridge.on_increment_clicked("1/2")
        except (decimal.InvalidOperation, ValueError, ZeroDivisionError):
            # AUDIT FIX: Catch specific exceptions
            pass

    def double_bet_amount(self):
        try:
            curr = Decimal(self.bet_var.get())
            self.bet_var.set(str(curr * 2))
            self.browser_bridge.on_increment_clicked("X2")
        except (decimal.InvalidOperation, ValueError):
            # AUDIT FIX: Catch specific exceptions
            pass

    def max_bet_amount(self):
        bal = self.state.get('balance')
        self.bet_var.set(str(bal))
        self.browser_bridge.on_increment_clicked("MAX")

    def set_sell_percentage(self, val):
        self.browser_bridge.on_percentage_clicked(val)
        self.state.set_sell_percentage(Decimal(str(val)))
        # Update button styles (simple bg change)
        for v, btn in self.pct_buttons.items():
            if v == val:
                btn.config(bg="#00cc66")
            else:
                btn.config(bg=BTN_CTRL_BG)

    def toggle_bot(self):
        """Toggle bot enabled state"""
        self.bot_enabled = not self.bot_enabled
        if self.bot_enabled:
            self.bot_executor.start()
            self.bot_status_indicator.config(bg="#00cc66")  # Green
            self.bot_indicator.config(text="🟢 BOT", fg='#00e676')
            self.bot_var.set(True)
            self.log("Bot enabled")
        else:
            self.bot_executor.stop()
            self.bot_status_indicator.config(bg="#444")  # Gray
            self.bot_indicator.config(text="⚫ BOT", fg='#666666')
            self.bot_var.set(False)
            self.log("Bot disabled")

    # ... (Menu and other boilerplate omitted for brevity, can be copied from main_window) ...
    
    def log(self, msg):
        logger.info(msg)

    # ========================================================================
    # MENU BAR (Phase 1.1)
    # ========================================================================

    def _create_menu_bar(self):
        """Create menu bar with full functionality"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Recording...", command=self._load_file_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Playback Menu
        playback_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Playback", menu=playback_menu)
        playback_menu.add_command(label="Play/Pause", command=self._toggle_playback)
        playback_menu.add_command(label="Step Forward", command=self._step_forward)
        playback_menu.add_command(label="Step Back", command=self._step_backward)
        playback_menu.add_separator()
        playback_menu.add_command(label="Reset", command=self._reset_game)

        # Speed submenu
        speed_menu = tk.Menu(playback_menu, tearoff=0)
        playback_menu.add_cascade(label="Speed", menu=speed_menu)
        for speed in [0.25, 0.5, 1.0, 2.0, 5.0]:
            speed_menu.add_command(
                label=f"{speed}x",
                command=lambda s=speed: self._set_playback_speed(s)
            )

        # Bot Menu
        bot_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Bot", menu=bot_menu)

        self.bot_var = tk.BooleanVar(value=self.bot_enabled)
        bot_menu.add_checkbutton(
            label="Enable Bot",
            variable=self.bot_var,
            command=self.toggle_bot
        )
        bot_menu.add_separator()
        bot_menu.add_command(label="Configuration...", command=self._show_bot_config)

        # Strategy submenu
        strategy_menu = tk.Menu(bot_menu, tearoff=0)
        bot_menu.add_cascade(label="Strategy", menu=strategy_menu)
        for strategy in list_strategies():
            strategy_menu.add_command(
                label=strategy.title(),
                command=lambda s=strategy: self._set_strategy(s)
            )

        # Live Feed Menu
        live_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Live Feed", menu=live_menu)

        self.live_feed_var = tk.BooleanVar(value=self.live_feed_connected)
        live_menu.add_checkbutton(
            label="Connect to Live Feed",
            variable=self.live_feed_var,
            command=self._toggle_live_feed
        )

        # Browser Menu
        browser_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Browser", menu=browser_menu)
        browser_menu.add_command(label="Connect to Browser", command=self._connect_browser)
        browser_menu.add_separator()
        browser_menu.add_command(label="⚫ Status: Disconnected", state=tk.DISABLED)
        browser_menu.add_separator()
        browser_menu.add_command(label="Disconnect Browser", command=self._disconnect_browser, state=tk.DISABLED)

        self.browser_menu = browser_menu
        self.browser_status_item_index = 2
        self.browser_disconnect_item_index = 4

        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)

        # Theme submenu
        theme_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Theme", menu=theme_menu)

        # Dark themes
        dark_theme_menu = tk.Menu(theme_menu, tearoff=0)
        theme_menu.add_cascade(label="Dark Themes", menu=dark_theme_menu)
        dark_themes = [
            ('cyborg', 'Cyborg - Neon gaming'),
            ('darkly', 'Darkly - Professional'),
            ('superhero', 'Superhero - Bold'),
            ('solar', 'Solar - Warm'),
            ('vapor', 'Vapor - Vaporwave'),
        ]
        for theme_id, theme_label in dark_themes:
            dark_theme_menu.add_command(
                label=theme_label,
                command=lambda t=theme_id: self._change_theme(t)
            )

        # Light themes
        light_theme_menu = tk.Menu(theme_menu, tearoff=0)
        theme_menu.add_cascade(label="Light Themes", menu=light_theme_menu)
        light_themes = [
            ('cosmo', 'Cosmo - Professional'),
            ('flatly', 'Flatly - Modern'),
            ('minty', 'Minty - Fresh'),
            ('lumen', 'Lumen - Bright'),
        ]
        for theme_id, theme_label in light_themes:
            light_theme_menu.add_command(
                label=theme_label,
                command=lambda t=theme_id: self._change_theme(t)
            )

        # UI Style submenu (Phase 6)
        view_menu.add_separator()
        ui_style_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="UI Style", menu=ui_style_menu)
        ui_style_menu.add_command(label="Standard", command=lambda: self._set_ui_style('standard'))
        ui_style_menu.add_command(label="Modern (Game-Like) ✓", state=tk.DISABLED)

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_keyboard_help)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)

    # ========================================================================
    # KEYBOARD SHORTCUTS (Phase 1.2)
    # ========================================================================

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for common actions"""
        self.root.bind('<space>', lambda e: self._toggle_playback())
        self.root.bind('b', lambda e: self.execute_buy())
        self.root.bind('B', lambda e: self.execute_buy())
        self.root.bind('s', lambda e: self.execute_sell())
        self.root.bind('S', lambda e: self.execute_sell())
        self.root.bind('d', lambda e: self.execute_sidebet())
        self.root.bind('D', lambda e: self.execute_sidebet())
        self.root.bind('r', lambda e: self._reset_game())
        self.root.bind('R', lambda e: self._reset_game())
        self.root.bind('<Left>', lambda e: self._step_backward())
        self.root.bind('<Right>', lambda e: self._step_forward())
        self.root.bind('h', lambda e: self._show_keyboard_help())
        self.root.bind('H', lambda e: self._show_keyboard_help())
        self.root.bind('l', lambda e: self._toggle_live_feed())
        self.root.bind('L', lambda e: self._toggle_live_feed())
        self.root.bind('<Control-o>', lambda e: self._load_file_dialog())

        logger.info("Keyboard shortcuts configured")

    # ========================================================================
    # EVENT HANDLERS (Phase 1.3)
    # ========================================================================

    def _setup_event_handlers(self):
        """Setup event bus subscriptions"""
        from services.event_bus import Events
        from core.game_state import StateEvents

        # Subscribe to game events
        self.event_bus.subscribe(Events.GAME_TICK, self._handle_game_tick)
        self.event_bus.subscribe(Events.TRADE_EXECUTED, self._handle_trade_executed)
        self.event_bus.subscribe(Events.TRADE_FAILED, self._handle_trade_failed)
        self.event_bus.subscribe(Events.FILE_LOADED, self._handle_file_loaded)

        # Subscribe to state events
        self.state.subscribe(StateEvents.BALANCE_CHANGED, self._handle_balance_changed)
        self.state.subscribe(StateEvents.POSITION_OPENED, self._handle_position_opened)
        self.state.subscribe(StateEvents.POSITION_CLOSED, self._handle_position_closed)
        self.state.subscribe(StateEvents.SELL_PERCENTAGE_CHANGED, self._handle_sell_percentage_changed)
        self.state.subscribe(StateEvents.POSITION_REDUCED, self._handle_position_reduced)

        logger.info("Event handlers configured")

    # ========================================================================
    # BOT RESULT POLLING (Phase 2.1)
    # ========================================================================

    def _check_bot_results(self):
        """Periodic polling for async bot execution results"""
        if self.bot_executor:
            result = self.bot_executor.get_latest_result()
            if result:
                self._handle_bot_result(result)
        self.root.after(100, self._check_bot_results)

    def _handle_bot_result(self, result):
        """Handle bot execution result"""
        if result.get('error'):
            logger.debug(f"Bot error: {result.get('error')}")
        elif result.get('result'):
            bot_result = result.get('result', {})
            action = bot_result.get('action', 'WAIT')
            if action != 'WAIT':
                self.log(f"Bot: {action}")

    # ========================================================================
    # GAME END CALLBACK (Phase 2.2)
    # ========================================================================

    def _on_game_end(self, metrics):
        """Callback for game end - AUDIT FIX Phase 2.6: Thread-safe UI updates"""
        self.log(f"Game ended. Final balance: {metrics.get('current_balance', 0):.4f} SOL")

        def _update_ui():
            """Execute UI updates on main thread"""
            if self.toast:
                final_balance = metrics.get('current_balance', 0)
                initial_balance = metrics.get('initial_balance', 1)
                pnl = final_balance - initial_balance
                msg = f"Game Over - P&L: {pnl:+.4f} SOL"
                self.toast.show(msg, "success" if pnl >= 0 else "error")

            # Check bankruptcy
            if self.state.get('balance') < Decimal('0.001'):
                logger.warning("BANKRUPT - Resetting balance")
                self.state.update(balance=self.state.get('initial_balance'))
                if self.toast:
                    self.toast.show("⚠️ Bankrupt! Balance reset.", "warning")

            # Multi-game auto-advance
            if self.multi_game_mode and self.game_queue.has_next():
                next_file = self.game_queue.next_game()
                logger.info(f"Auto-loading next game: {next_file.name}")
                self._load_game_file(next_file)
                if not self.user_paused:
                    self.replay_engine.play()

        # AUDIT FIX Phase 2.6: Marshal to UI thread
        self.ui_dispatcher.submit(_update_ui)

    # ========================================================================
    # BROWSER BRIDGE STATUS (Phase 2.3)
    # ========================================================================

    def _on_bridge_status_change(self, status):
        """Update browser connection indicator - AUDIT FIX Phase 2.6: Thread-safe"""
        def _update_ui():
            """Execute UI updates on main thread"""
            if status == "connected":
                self.browser_connected = True
                # Update menu status
                if hasattr(self, 'browser_menu'):
                    self.browser_menu.entryconfig(self.browser_status_item_index, label="🟢 Status: Connected")
                    self.browser_menu.entryconfig(self.browser_disconnect_item_index, state=tk.NORMAL)
                # Update status bar indicator
                if hasattr(self, 'browser_indicator'):
                    self.browser_indicator.config(text="🟢 BROWSER", fg='#00e676')
                if self.toast:
                    self.toast.show("Browser connected", "success")
            else:
                self.browser_connected = False
                if hasattr(self, 'browser_menu'):
                    self.browser_menu.entryconfig(self.browser_status_item_index, label="⚫ Status: Disconnected")
                    self.browser_menu.entryconfig(self.browser_disconnect_item_index, state=tk.DISABLED)
                # Update status bar indicator
                if hasattr(self, 'browser_indicator'):
                    self.browser_indicator.config(text="⚫ BROWSER", fg='#666666')

        # AUDIT FIX Phase 2.6: Marshal to UI thread
        self.ui_dispatcher.submit(_update_ui)

    # ========================================================================
    # EVENT HANDLER IMPLEMENTATIONS
    # ========================================================================

    def _handle_game_tick(self, event):
        """Handle game tick event from event bus"""
        pass  # Handled by ReplayEngine callback

    def _handle_trade_executed(self, event):
        """Handle successful trade"""
        self.log(f"Trade executed: {event.get('data')}")

    def _handle_trade_failed(self, event):
        """Handle failed trade"""
        self.log(f"Trade failed: {event.get('data')}")

    def _handle_file_loaded(self, event):
        """Handle file loaded event - AUDIT FIX: Do NOT auto-load files on boot"""
        files = event.get('data', {}).get('files', [])
        if files:
            self.log(f"Found {len(files)} game files available (use File menu to load)")
            # AUDIT FIX: Removed auto-load of first file - user should manually select

    def _handle_balance_changed(self, data):
        """Handle balance change"""
        new_balance = data.get('new')
        if new_balance is not None:
            self.ui_dispatcher.submit(
                lambda: self._update_balance_display(new_balance)
            )

    def _handle_position_opened(self, data):
        """Handle position opened"""
        entry_price = data.get('entry_price', 0)
        self.ui_dispatcher.submit(lambda: self.log(f"Position opened at {entry_price:.4f}"))

    def _handle_position_closed(self, data):
        """Handle position closed"""
        pnl = data.get('pnl_sol', 0)
        self.ui_dispatcher.submit(lambda: self.log(f"Position closed - P&L: {pnl:+.4f} SOL"))

    def _handle_sell_percentage_changed(self, data):
        """Handle sell percentage changed"""
        new_percentage = data.get('new', 1.0)
        self.ui_dispatcher.submit(lambda: self.set_sell_percentage(float(new_percentage)))

    def _handle_position_reduced(self, data):
        """Handle partial position close"""
        percentage = data.get('percentage', 0)
        pnl = data.get('pnl_sol', 0)
        self.ui_dispatcher.submit(
            lambda: self.log(f"Position reduced ({percentage*100:.0f}%) - P&L: {pnl:+.4f} SOL")
        )

    # ========================================================================
    # PLAYBACK METHODS
    # ========================================================================

    def _load_file_dialog(self):
        """Open file dialog to load a recording"""
        filepath = filedialog.askopenfilename(
            title="Open Recording",
            initialdir=self.config.FILES['recordings_dir'],
            filetypes=[("JSONL files", "*.jsonl"), ("All files", "*.*")]
        )
        if filepath:
            self._load_game_file(Path(filepath))

    def _load_game_file(self, filepath: Path):
        """Load a game file and update UI"""
        try:
            self.replay_engine.load_file(filepath)
            self.chart.reset()
            self.state.reset()
            self.last_candle_tick = -1  # AUDIT FIX: Reset candle tracking for new game
            # Update game label
            if hasattr(self, 'game_label'):
                self.game_label.config(text=f"📄 GAME: {filepath.stem}")
            # Update balance
            self._update_balance_display(self.state.get('balance'))
            self.log(f"Loaded: {filepath.name}")
            if self.toast:
                self.toast.show(f"Loaded {filepath.name}", "success")
        except Exception as e:
            logger.error(f"Failed to load file: {e}")
            if self.toast:
                self.toast.show(f"Load failed: {e}", "error")

    def _toggle_playback(self):
        """Toggle play/pause state"""
        if self.replay_engine.is_playing:
            self.replay_engine.pause()
            self.user_paused = True
            if hasattr(self, 'play_button'):
                self.play_button.config(text="▶️ PLAY", bg='#00c853')
            self.log("Paused")
        else:
            self.replay_engine.play()
            self.user_paused = False
            if hasattr(self, 'play_button'):
                self.play_button.config(text="⏸ PAUSE", bg='#ff9800')
            self.log("Playing")

    def _step_forward(self):
        """Step forward one tick"""
        self.replay_engine.step_forward()

    def _step_backward(self):
        """Step backward one tick"""
        if hasattr(self.replay_engine, 'step_backward'):
            self.replay_engine.step_backward()

    def _reset_game(self):
        """Reset the current game"""
        self.replay_engine.reset()
        self.state.reset()
        self.chart.reset()
        self.user_paused = True
        self.log("Game reset")

    def _set_playback_speed(self, speed: float):
        """Set playback speed"""
        self.replay_engine.set_speed(speed)
        self.log(f"Speed: {speed}x")

    # ========================================================================
    # BOT CONFIGURATION METHODS
    # ========================================================================

    def _show_bot_config(self):
        """Show bot configuration dialog"""
        self.bot_config_panel.show()

    def _set_strategy(self, strategy_name: str):
        """Set bot strategy"""
        self.bot_controller.set_strategy(strategy_name)
        self.log(f"Strategy: {strategy_name}")

    # ========================================================================
    # LIVE FEED METHODS
    # ========================================================================

    def _toggle_live_feed(self):
        """Toggle live feed connection"""
        if self.live_feed_connected:
            self._disconnect_live_feed()
        else:
            self._connect_live_feed()

    def _connect_live_feed(self):
        """Connect to live WebSocket feed"""
        try:
            if not self.live_feed:
                # AUDIT FIX: WebSocketFeed uses hardcoded server_url, no url parameter
                self.live_feed = WebSocketFeed()
            self.live_feed.on_tick = self._on_live_tick
            self.live_feed.connect()
            self.live_feed_connected = True
            self.live_feed_var.set(True)
            # Update indicator
            if hasattr(self, 'live_indicator'):
                self.live_indicator.config(text="🟢 LIVE", fg='#00e676')
            self.log("Live feed connected")
            if self.toast:
                self.toast.show("Live feed connected", "success")
        except Exception as e:
            logger.error(f"Failed to connect live feed: {e}")
            if self.toast:
                self.toast.show(f"Connection failed: {e}", "error")

    def _disconnect_live_feed(self):
        """Disconnect from live feed"""
        if self.live_feed:
            self.live_feed.disconnect()
        self.live_feed_connected = False
        self.live_feed_var.set(False)
        # Update indicator
        if hasattr(self, 'live_indicator'):
            self.live_indicator.config(text="⚫ LIVE", fg='#666666')
        self.log("Live feed disconnected")

    def _on_live_tick(self, tick_data):
        """Handle incoming live tick"""
        try:
            tick = GameTick.from_dict(tick_data)
            self.ui_dispatcher.submit(self._process_tick_ui, tick, 0, 0)
        except Exception as e:
            logger.debug(f"Error processing live tick: {e}")

    # ========================================================================
    # BROWSER METHODS
    # ========================================================================

    def _connect_browser(self):
        """Connect to browser for automation"""
        if self.browser_executor:
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                # AUDIT FIX: Check return value from start_browser()
                success = loop.run_until_complete(self.browser_executor.start_browser())
                if success:
                    self._on_bridge_status_change("connected")
                else:
                    logger.error("Browser connection failed (start_browser returned False)")
                    if self.toast:
                        self.toast.show("Browser connection failed", "error")
            except Exception as e:
                logger.error(f"Browser connection failed: {e}")
                if self.toast:
                    self.toast.show(f"Browser error: {e}", "error")
            finally:
                loop.close()
        else:
            if self.toast:
                self.toast.show("Browser executor not available", "warning")

    def _disconnect_browser(self):
        """Disconnect from browser"""
        if self.browser_executor:
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.browser_executor.stop_browser())
                self._on_bridge_status_change("disconnected")
            except Exception as e:
                logger.error(f"Browser disconnect failed: {e}")
            finally:
                loop.close()

    # ========================================================================
    # THEME & UI STYLE METHODS
    # ========================================================================

    def _change_theme(self, theme_name: str):
        """Change UI theme"""
        try:
            import ttkbootstrap as ttk
            if hasattr(self.root, 'style'):
                self.root.style.theme_use(theme_name)
            else:
                style = ttk.Style()
                style.theme_use(theme_name)

            # Save preference
            self._save_ui_preference('theme', theme_name)

            if self.toast:
                self.toast.show(f"Theme: {theme_name}", "success")
        except Exception as e:
            logger.error(f"Theme change failed: {e}")

    def _set_ui_style(self, style: str):
        """Set UI style and auto-restart the application"""
        self._save_ui_preference('ui_style', style)

        # Ask user to confirm restart
        result = messagebox.askyesno(
            "Restart Application",
            f"UI style changed to '{style}'.\n\nRestart now to apply changes?"
        )

        if result:
            self._restart_application()

    def _restart_application(self):
        """Restart the application"""
        import sys
        import os

        logger.info("Restarting application...")

        # Get the Python executable and script path
        python = sys.executable
        script = os.path.abspath(sys.argv[0])
        script_dir = os.path.dirname(script)

        # Build the command line arguments (preserve any existing args)
        args = [python, script] + sys.argv[1:]

        # Remove --modern flag if present (let it load from preference)
        args = [a for a in args if a != '--modern']

        logger.info(f"Restart command: {' '.join(args)}")
        logger.info(f"Working directory: {script_dir}")

        # Schedule the restart after a short delay to allow cleanup
        self.root.after(100, lambda: self._do_restart(python, args, script_dir))

    def _do_restart(self, python, args, working_dir):
        """Execute the restart"""
        import os

        try:
            # Destroy the current window
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

        # Change to the script's directory before restarting
        os.chdir(working_dir)

        # Replace current process with new instance
        os.execv(python, args)

    def _save_ui_preference(self, key: str, value: str):
        """Save UI preference to config file"""
        import json
        config_dir = Path.home() / '.config' / 'replayer'
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / 'ui_config.json'

        config_data = {}
        if config_file.exists():
            with open(config_file, 'r') as f:
                config_data = json.load(f)

        config_data[key] = value

        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)

    # ========================================================================
    # HELP METHODS
    # ========================================================================

    def _show_keyboard_help(self):
        """Show keyboard shortcuts help"""
        help_text = """
KEYBOARD SHORTCUTS

Trading:
  B - Buy (open position)
  S - Sell (close position)
  D - Place side bet

Playback:
  Space - Play/Pause
  R - Reset game
  ← - Step backward
  → - Step forward

Data Sources:
  L - Toggle live WebSocket feed

File:
  Ctrl+O - Open recording

Other:
  H - Show this help

GAME RULES:
• Side bets win if rug occurs within 40 ticks
• Side bet pays 5x your wager
• 5 tick cooldown after sidebet resolves
• All positions are lost when rug occurs
"""
        messagebox.showinfo("Keyboard Shortcuts", help_text)

    def _show_about(self):
        """Show about dialog"""
        about_text = """
REPLAYER - Modern UI Edition

A professional replay viewer and analysis engine
for Rugs.fun trading game recordings.

Version: 2.1 (Modern UI)

Features:
• Interactive replay with speed control
• Trading bot automation
• Real-time WebSocket live feed
• Custom game-like visual components
• Theme customization

© 2025 REPLAYER Project
"""
        messagebox.showinfo("About REPLAYER", about_text)

    # ========================================================================
    # UI UPDATE METHODS
    # ========================================================================

    def _update_balance_display(self, balance):
        """Update balance display (called from UI thread)"""
        if hasattr(self, 'balance_label'):
            self.balance_label.config(text=f"💰 BALANCE: {balance:.4f} SOL")

    # ========================================================================
    # SHUTDOWN
    # ========================================================================

    def shutdown(self):
        """Clean shutdown"""
        # Stop live feed
        if self.live_feed_connected and self.live_feed:
            self.live_feed.disconnect()

        # Stop bot
        if self.bot_executor:
            self.bot_executor.stop()

        # Disconnect browser
        if self.browser_connected and self.browser_executor:
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.browser_executor.stop_browser())
            except Exception:
                pass
            finally:
                loop.close()

        # Stop UI dispatcher
        if hasattr(self, 'ui_dispatcher'):
            self.ui_dispatcher.stop()
