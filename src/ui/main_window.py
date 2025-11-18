"""
Main Window UI Module - Minimal Implementation
This gets your app running with basic UI
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from decimal import Decimal
import json
import logging
from typing import Optional, List, Dict
import threading

from core import ReplayEngine, TradeManager
from core.game_queue import GameQueue
from models import GameTick
from ui.widgets import ChartWidget, ToastNotification
from ui.tk_dispatcher import TkDispatcher
from ui.bot_config_panel import BotConfigPanel  # Phase 8.4
from bot import BotInterface, BotController, list_strategies
from bot.async_executor import AsyncBotExecutor
from bot.execution_mode import ExecutionMode  # Phase 8.4
from bot.ui_controller import BotUIController  # Phase 8.4
from bot.browser_executor import BrowserExecutor  # Phase 8.5
from sources import WebSocketFeed

logger = logging.getLogger(__name__)

class MainWindow:
    """
    Main application window with integrated ReplayEngine
    Phase 8.5: Added browser automation support
    """

    def __init__(self, root: tk.Tk, state, event_bus, config, live_mode: bool = False):
        """
        Initialize main window

        Args:
            root: Tkinter root window
            state: GameState instance
            event_bus: EventBus instance
            config: Configuration object
            live_mode: If True, enable live browser automation (Phase 8.5)
        """
        self.root = root
        self.state = state
        self.event_bus = event_bus
        self.config = config
        self.live_mode = live_mode  # Phase 8.5

        # Phase 8.5: Initialize browser executor (user controls connection via menu)
        self.browser_executor = None
        self.browser_connected = False

        try:
            from bot.browser_executor import BrowserExecutor
            self.browser_executor = BrowserExecutor(profile_name="rugs_fun_phantom")
            logger.info("BrowserExecutor available - user can connect via Browser menu")
        except Exception as e:
            logger.warning(f"BrowserExecutor not available: {e}")
            # Graceful degradation - Browser menu will show "Not Available"

        # Initialize replay engine and trade manager
        self.replay_engine = ReplayEngine(state)
        self.trade_manager = TradeManager(state)

        # Initialize game queue for multi-game sessions
        recordings_dir = config.FILES['recordings_dir']
        self.game_queue = GameQueue(recordings_dir)
        self.multi_game_mode = False  # Programmatically controlled, not via UI

        # Phase 8.4: Initialize bot configuration panel
        self.bot_config_panel = BotConfigPanel(root, config_file="bot_config.json")
        bot_config = self.bot_config_panel.get_config()

        # Phase 8.4: Initialize bot with config settings
        self.bot_interface = BotInterface(state, self.trade_manager)

        # Phase 8.4: Initialize BotUIController for UI_LAYER mode
        self.bot_ui_controller = BotUIController(self)  # 'self' = MainWindow instance

        # Phase 8.4: Create BotController with execution mode from config
        execution_mode = self.bot_config_panel.get_execution_mode()
        strategy = self.bot_config_panel.get_strategy()

        self.bot_controller = BotController(
            self.bot_interface,
            strategy_name=strategy,  # Fixed: parameter name is strategy_name
            execution_mode=execution_mode,
            ui_controller=self.bot_ui_controller if execution_mode == ExecutionMode.UI_LAYER else None
        )

        # Phase 8.4: Set bot enabled state from config
        self.bot_enabled = self.bot_config_panel.is_bot_enabled()

        # Initialize async bot executor (prevents deadlock)
        self.bot_executor = AsyncBotExecutor(self.bot_controller)

        # Initialize live feed (Phase 6)
        self.live_feed = None
        self.live_feed_connected = False

        # Ensure UI updates happen on Tk main thread
        self.ui_dispatcher = TkDispatcher(self.root)
        self.user_paused = True

        # Set replay callbacks
        self.replay_engine.on_tick_callback = self._on_tick_update
        self.replay_engine.on_game_end_callback = self._on_game_end

        # Initialize toast notifications
        self.toast = None  # Will be initialized after root window is ready

        # Initialize UI
        self._create_ui()
        self._setup_event_handlers()
        self._setup_keyboard_shortcuts()

        # Bug 3 Fix: Start executor if bot was enabled in config
        if self.bot_enabled:
            self.bot_executor.start()
            self.bot_toggle_button.config(state=tk.NORMAL)
            logger.info("Bot executor auto-started from config")

        # Start periodic bot result checker
        self._check_bot_results()

        # Phase 8.6: Start periodic timing metrics updater
        self._update_timing_metrics_loop()

        logger.info("MainWindow initialized with ReplayEngine and async bot executor")

    def _create_menu_bar(self):
        """Create menu bar for additional functionality"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Recording...", command=self.load_file_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Playback Menu
        playback_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Playback", menu=playback_menu)
        playback_menu.add_command(label="Play/Pause", command=self.toggle_play_pause)
        playback_menu.add_command(label="Stop", command=self.reset_game)

        # Recording Menu
        recording_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Recording", menu=recording_menu)

        # Recording toggle - tracks replay_engine.auto_recording state
        self.recording_var = tk.BooleanVar(value=self.replay_engine.auto_recording)
        recording_menu.add_checkbutton(
            label="Enable Recording",
            variable=self.recording_var,
            command=self._toggle_recording
        )
        recording_menu.add_separator()
        recording_menu.add_command(label="Open Recordings Folder", command=self._open_recordings_folder)

        # Bot Menu
        bot_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Bot", menu=bot_menu)

        self.bot_var = tk.BooleanVar(value=self.bot_enabled)
        bot_menu.add_checkbutton(
            label="Enable Bot",
            variable=self.bot_var,
            command=self._toggle_bot_from_menu
        )

        # Phase 8.4: Add configuration menu item
        bot_menu.add_separator()
        bot_menu.add_command(
            label="Configuration...",
            command=lambda: self.root.after(0, self._show_bot_config)
        )

        # Phase 8.6: Add timing metrics menu item
        bot_menu.add_command(
            label="Timing Metrics...",
            command=lambda: self.root.after(0, self._show_timing_metrics)
        )

        # Live Feed Menu
        live_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Live Feed", menu=live_menu)

        self.live_feed_var = tk.BooleanVar(value=self.live_feed_connected)
        live_menu.add_checkbutton(
            label="Connect to Live Feed",
            variable=self.live_feed_var,
            command=self._toggle_live_feed_from_menu
        )

        # ========== BROWSER MENU (Phase 8.5) ==========
        browser_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Browser", menu=browser_menu)

        # Check if browser executor available
        if self.browser_executor:
            # Connect command (enabled)
            browser_menu.add_command(
                label="Connect Browser...",
                command=lambda: self.root.after(0, self._show_browser_connection_dialog)
            )

            browser_menu.add_separator()

            # Status indicators (disabled, display only)
            browser_menu.add_command(
                label="⚫ Status: Not Connected",
                state=tk.DISABLED
            )

            browser_menu.add_command(
                label="Profile: rugs_fun_phantom",
                state=tk.DISABLED
            )

            browser_menu.add_separator()

            # Disconnect command (initially disabled)
            browser_menu.add_command(
                label="Disconnect Browser",
                command=self._disconnect_browser,
                state=tk.DISABLED
            )

            # Store menu references for status updates
            self.browser_menu = browser_menu
            self.browser_status_item_index = 2  # "⚫ Status: Not Connected"
            self.browser_disconnect_item_index = 5  # "Disconnect Browser"
        else:
            # Browser not available
            browser_menu.add_command(
                label="Browser automation not available",
                state=tk.DISABLED
            )
            browser_menu.add_command(
                label="(Check browser_automation/ directory)",
                state=tk.DISABLED
            )

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _create_ui(self):
        """Create UI matching the user's mockup design"""
        # Create menu bar first
        self._create_menu_bar()

        # ========== ROW 1: STATUS BAR (minimal height) ==========
        status_bar = tk.Frame(self.root, bg='#000000', height=30)
        status_bar.pack(fill=tk.X)
        status_bar.pack_propagate(False)  # Fixed height

        # Tick (left)
        self.tick_label = tk.Label(
            status_bar,
            text="TICK: 0",
            font=('Arial', 11, 'bold'),
            bg='#000000',
            fg='white'
        )
        self.tick_label.pack(side=tk.LEFT, padx=10)

        # Price (center-left)
        self.price_label = tk.Label(
            status_bar,
            text="PRICE: 1.0000 X",
            font=('Arial', 11, 'bold'),
            bg='#000000',
            fg='white'
        )
        self.price_label.pack(side=tk.LEFT, padx=20)

        # Phase (right)
        self.phase_label = tk.Label(
            status_bar,
            text="PHASE: UNKNOWN",
            font=('Arial', 11, 'bold'),
            bg='#000000',
            fg='white'
        )
        self.phase_label.pack(side=tk.RIGHT, padx=10)

        # Browser status (right) - Phase 8.5
        self.browser_status_label = tk.Label(
            status_bar,
            text="BROWSER: ⚫ Not Connected",
            font=('Arial', 9),
            bg='#000000',
            fg='#888888'  # Gray when disconnected
        )
        self.browser_status_label.pack(side=tk.RIGHT, padx=10)

        # ========== ROW 2: CHART AREA (expands to fill) ==========
        chart_container = tk.Frame(self.root, bg='#0a0a0a')
        chart_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Chart widget (MAXIMIZED - no fixed dimensions)
        self.chart = ChartWidget(chart_container)
        self.chart.pack(fill=tk.BOTH, expand=True)

        # Zoom controls (overlaid at bottom-left of chart)
        zoom_overlay = tk.Frame(chart_container, bg='#2a2a2a')
        zoom_overlay.place(x=10, y=10, anchor='nw')

        tk.Button(
            zoom_overlay,
            text="+ ZOOM IN",
            command=self.chart.zoom_in,
            bg='#333333',
            fg='white',
            font=('Arial', 9),
            bd=1,
            relief=tk.RAISED
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            zoom_overlay,
            text="+ ZOOM OUT",
            command=self.chart.zoom_out,
            bg='#333333',
            fg='white',
            font=('Arial', 9),
            bd=1,
            relief=tk.RAISED
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            zoom_overlay,
            text="RESET ZOOM",
            command=self.chart.reset_zoom,
            bg='#333333',
            fg='white',
            font=('Arial', 9),
            bd=1,
            relief=tk.RAISED
        ).pack(side=tk.LEFT, padx=2)

        # ========== ROW 3: PLAYBACK CONTROLS ==========
        playback_row = tk.Frame(self.root, bg='#1a1a1a', height=40)
        playback_row.pack(fill=tk.X)
        playback_row.pack_propagate(False)

        # Left side - playback buttons
        playback_left = tk.Frame(playback_row, bg='#1a1a1a')
        playback_left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_style = {'font': ('Arial', 10), 'width': 12, 'bd': 1, 'relief': tk.RAISED}

        self.load_button = tk.Button(
            playback_left,
            text="LOAD GAME",
            command=self.load_game,
            bg='#444444',
            fg='white',
            **btn_style
        )
        self.load_button.pack(side=tk.LEFT, padx=5)

        self.play_button = tk.Button(
            playback_left,
            text="PLAY",
            command=self.toggle_playback,
            bg='#444444',
            fg='white',
            state=tk.DISABLED,
            **btn_style
        )
        self.play_button.pack(side=tk.LEFT, padx=5)

        self.step_button = tk.Button(
            playback_left,
            text="STEP",
            command=self.step_forward,
            bg='#444444',
            fg='white',
            state=tk.DISABLED,
            **btn_style
        )
        self.step_button.pack(side=tk.LEFT, padx=5)

        self.reset_button = tk.Button(
            playback_left,
            text="RESET",
            command=self.reset_game,
            bg='#444444',
            fg='white',
            state=tk.DISABLED,
            **btn_style
        )
        self.reset_button.pack(side=tk.LEFT, padx=5)

        # Right side - playback speed controls
        speed_frame = tk.Frame(playback_row, bg='#1a1a1a')
        speed_frame.pack(side=tk.RIGHT, padx=10)

        self.speed_label = tk.Label(
            speed_frame,
            text="SPEED: 1.0X",
            font=('Arial', 10, 'bold'),
            bg='#1a1a1a',
            fg='white'
        )
        self.speed_label.pack(side=tk.LEFT, padx=5)

        # Speed buttons
        speed_btn_style = {'font': ('Arial', 8), 'width': 5, 'bd': 1, 'relief': tk.RAISED}
        tk.Button(speed_frame, text="0.25x", command=lambda: self.set_playback_speed(0.25), bg='#333333', fg='white', **speed_btn_style).pack(side=tk.LEFT, padx=1)
        tk.Button(speed_frame, text="0.5x", command=lambda: self.set_playback_speed(0.5), bg='#333333', fg='white', **speed_btn_style).pack(side=tk.LEFT, padx=1)
        tk.Button(speed_frame, text="1x", command=lambda: self.set_playback_speed(1.0), bg='#444444', fg='white', **speed_btn_style).pack(side=tk.LEFT, padx=1)
        tk.Button(speed_frame, text="2x", command=lambda: self.set_playback_speed(2.0), bg='#333333', fg='white', **speed_btn_style).pack(side=tk.LEFT, padx=1)
        tk.Button(speed_frame, text="5x", command=lambda: self.set_playback_speed(5.0), bg='#333333', fg='white', **speed_btn_style).pack(side=tk.LEFT, padx=1)

        # ========== ROW 4: BET AMOUNT CONTROLS ==========
        bet_row = tk.Frame(self.root, bg='#1a1a1a', height=40)
        bet_row.pack(fill=tk.X)
        bet_row.pack_propagate(False)

        # Left - bet amount display
        bet_left = tk.Frame(bet_row, bg='#1a1a1a')
        bet_left.pack(side=tk.LEFT, padx=10)

        self.bet_entry = tk.Entry(
            bet_left,
            bg='#000000',
            fg='white',
            font=('Arial', 14, 'bold'),
            width=8,
            bd=1,
            relief=tk.SOLID,
            justify=tk.RIGHT
        )
        self.bet_entry.pack(side=tk.LEFT)
        self.bet_entry.insert(0, str(self.config.FINANCIAL['default_bet']))

        tk.Label(bet_left, text="SOL", bg='#1a1a1a', fg='white', font=('Arial', 10)).pack(side=tk.LEFT, padx=5)

        # Center - bet adjustment buttons
        bet_center = tk.Frame(bet_row, bg='#1a1a1a')
        bet_center.pack(side=tk.LEFT, padx=10)

        bet_btn_style = {'font': ('Arial', 9), 'width': 6, 'bd': 1, 'relief': tk.RAISED}

        tk.Button(bet_center, text="X", command=self.clear_bet_amount, bg='#333333', fg='white', **bet_btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(bet_center, text="+0.001", command=lambda: self.increment_bet_amount(Decimal('0.001')), bg='#333333', fg='white', **bet_btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(bet_center, text="+0.01", command=lambda: self.increment_bet_amount(Decimal('0.01')), bg='#333333', fg='white', **bet_btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(bet_center, text="+0.1", command=lambda: self.increment_bet_amount(Decimal('0.1')), bg='#333333', fg='white', **bet_btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(bet_center, text="+1", command=lambda: self.increment_bet_amount(Decimal('1')), bg='#333333', fg='white', **bet_btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(bet_center, text="1/2", command=lambda: self.set_bet_amount(Decimal(self.bet_entry.get())/2), bg='#333333', fg='white', **bet_btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(bet_center, text="X2", command=lambda: self.set_bet_amount(Decimal(self.bet_entry.get())*2), bg='#333333', fg='white', **bet_btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(bet_center, text="MAX", command=lambda: self.set_bet_amount(self.state.get('balance')), bg='#333333', fg='white', **bet_btn_style).pack(side=tk.LEFT, padx=2)

        # Right - wallet balance
        self.balance_label = tk.Label(
            bet_row,
            text=f"WALLET: {self.state.get('balance'):.3f}",
            font=('Arial', 11, 'bold'),
            bg='#1a1a1a',
            fg='#ffcc00'
        )
        self.balance_label.pack(side=tk.RIGHT, padx=10)

        # ========== ROW 5: ACTION BUTTONS ==========
        action_row = tk.Frame(self.root, bg='#1a1a1a', height=80)
        action_row.pack(fill=tk.X)
        action_row.pack_propagate(False)

        # Left - large action buttons
        action_left = tk.Frame(action_row, bg='#1a1a1a')
        action_left.pack(side=tk.LEFT, padx=10, pady=10)

        large_btn_style = {'font': ('Arial', 14, 'bold'), 'width': 10, 'height': 2, 'bd': 2, 'relief': tk.RAISED}

        self.sidebet_button = tk.Button(
            action_left,
            text="SIDEBET",
            command=self.execute_sidebet,
            bg='#3399ff',
            fg='white',
            state=tk.DISABLED,
            **large_btn_style
        )
        self.sidebet_button.pack(side=tk.LEFT, padx=5)

        self.buy_button = tk.Button(
            action_left,
            text="BUY",
            command=self.execute_buy,
            bg='#00ff66',
            fg='black',
            state=tk.DISABLED,
            **large_btn_style
        )
        self.buy_button.pack(side=tk.LEFT, padx=5)

        self.sell_button = tk.Button(
            action_left,
            text="SELL",
            command=self.execute_sell,
            bg='#ff3399',
            fg='white',
            state=tk.DISABLED,
            **large_btn_style
        )
        self.sell_button.pack(side=tk.LEFT, padx=5)

        # Phase 8.2: Percentage selector buttons (radio-button style)
        # Separator between action buttons and percentage selectors
        separator = tk.Frame(action_left, bg='#444444', width=2)
        separator.pack(side=tk.LEFT, padx=10, fill=tk.Y, pady=15)

        # Percentage buttons (smaller, radio-style)
        pct_btn_style = {'font': ('Arial', 10, 'bold'), 'width': 6, 'height': 1, 'bd': 2, 'relief': tk.RAISED}

        self.percentage_buttons = {}
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
                command=lambda v=value: self.set_sell_percentage(v),
                bg=default_color,
                fg='white',
                **pct_btn_style
            )
            btn.pack(side=tk.LEFT, padx=3)
            self.percentage_buttons[value] = {
                'button': btn,
                'default_color': default_color,
                'selected_color': '#00cc66',  # Green when selected
                'value': value
            }

        # Set initial selection to 100%
        self.current_sell_percentage = 1.0
        self.highlight_percentage_button(1.0)

        # Right - bot and info
        action_right = tk.Frame(action_row, bg='#1a1a1a')
        action_right.pack(side=tk.RIGHT, padx=10, pady=10)

        # Bot controls (top right)
        bot_top = tk.Frame(action_right, bg='#1a1a1a')
        bot_top.pack(anchor='e')

        self.bot_toggle_button = tk.Button(
            bot_top,
            text="ENABLE BOT",
            command=self.toggle_bot,
            bg='#444444',
            fg='white',
            font=('Arial', 10),
            width=12,
            state=tk.DISABLED
        )
        self.bot_toggle_button.pack(side=tk.LEFT, padx=5)

        tk.Label(bot_top, text="STRATEGY:", bg='#1a1a1a', fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=5)

        # Bug 3 Fix: Initialize strategy_var with loaded strategy from config (not hardcoded)
        loaded_strategy = self.bot_config_panel.get_strategy()
        self.strategy_var = tk.StringVar(value=loaded_strategy)
        self.strategy_dropdown = ttk.Combobox(
            bot_top,
            textvariable=self.strategy_var,
            values=list_strategies(),
            state='readonly',
            width=12,
            font=('Arial', 9)
        )
        self.strategy_dropdown.pack(side=tk.LEFT)
        self.strategy_dropdown.bind('<<ComboboxSelected>>', self._on_strategy_changed)

        # Info labels (bottom right)
        bot_bottom = tk.Frame(action_right, bg='#1a1a1a')
        bot_bottom.pack(anchor='e', pady=(5, 0))

        # Bot status label
        self.bot_status_label = tk.Label(
            bot_bottom,
            text="BOT: DISABLED",
            font=('Arial', 10),
            bg='#1a1a1a',
            fg='#666666'
        )
        self.bot_status_label.pack(side=tk.LEFT, padx=10)

        self.position_label = tk.Label(
            bot_bottom,
            text="POSITION: NONE",
            font=('Arial', 10),
            bg='#1a1a1a',
            fg='#666666'
        )
        self.position_label.pack(side=tk.LEFT, padx=10)

        self.sidebet_status_label = tk.Label(
            bot_bottom,
            text="SIDEBET: NONE",
            font=('Arial', 10),
            bg='#1a1a1a',
            fg='#666666'
        )
        self.sidebet_status_label.pack(side=tk.LEFT, padx=10)

        # Phase 8.6: Draggable timing overlay (replaces inline labels)
        # Create overlay widget (hidden initially, shown in UI_LAYER mode)
        from ui.timing_overlay import TimingOverlay
        self.timing_overlay = TimingOverlay(self.root, config_file="timing_overlay.json")

        # Initialize toast notifications
        self.toast = ToastNotification(self.root)
    
    def _setup_event_handlers(self):
        """Setup event bus subscriptions"""
        from services.event_bus import Events
        
        # Subscribe to game events
        self.event_bus.subscribe(Events.GAME_TICK, self._handle_game_tick)
        self.event_bus.subscribe(Events.TRADE_EXECUTED, self._handle_trade_executed)
        self.event_bus.subscribe(Events.TRADE_FAILED, self._handle_trade_failed)
        self.event_bus.subscribe(Events.FILE_LOADED, self._handle_file_loaded)
        
        # Subscribe to state events
        from core.game_state import StateEvents
        self.state.subscribe(StateEvents.BALANCE_CHANGED, self._handle_balance_changed)
        self.state.subscribe(StateEvents.POSITION_OPENED, self._handle_position_opened)
        self.state.subscribe(StateEvents.POSITION_CLOSED, self._handle_position_closed)
        # Phase 8.2: Partial sell events
        self.state.subscribe(StateEvents.SELL_PERCENTAGE_CHANGED, self._handle_sell_percentage_changed)
        self.state.subscribe(StateEvents.POSITION_REDUCED, self._handle_position_reduced)
    
    def log(self, message: str):
        """Log message (using logger instead of text widget)"""
        logger.info(message)
    
    def load_game(self):
        """Load a game file"""
        filepath = filedialog.askopenfilename(
            title="Select Game Recording",
            filetypes=[("JSONL files", "*.jsonl"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                self.load_game_file(Path(filepath))
            except Exception as e:
                messagebox.showerror("Load Error", f"Failed to load game: {e}")
    
    def load_game_file(self, filepath: Path):
        """Load game data from file using ReplayEngine"""
        # Sync multi-game mode to replay engine
        self.replay_engine.multi_game_mode = self.multi_game_mode

        success = self.replay_engine.load_file(filepath)

        if success:
            info = self.replay_engine.get_info()
            self.log(f"Loaded game with {info['total_ticks']} ticks")

            # Enable controls
            self.play_button.config(state=tk.NORMAL)
            self.step_button.config(state=tk.NORMAL)
            self.reset_button.config(state=tk.NORMAL)
            self.bot_toggle_button.config(state=tk.NORMAL)
        else:
            self.log("Failed to load game file")
            messagebox.showerror("Load Error", "Failed to load game file")

    def enable_live_feed(self):
        """Enable WebSocket live feed (Phase 6)"""
        if self.live_feed_connected:
            self.log("Live feed already connected")
            return

        try:
            self.log("Connecting to live feed...")
            # Show connecting toast for user feedback
            if self.toast:
                self.toast.show("Connecting to live feed...", "info")

            # Create WebSocketFeed
            self.live_feed = WebSocketFeed(log_level='WARN')

            # Register event handlers (THREAD-SAFE with root.after)
            @self.live_feed.on('signal')
            def on_signal(signal):
                # Marshal to Tkinter main thread
                def process_signal():
                    try:
                        # Convert GameSignal to GameTick
                        tick = self.live_feed.signal_to_game_tick(signal)

                        # Push to replay engine (auto-records if enabled)
                        self.replay_engine.push_tick(tick)

                        # Publish to event bus for UI updates
                        from services.event_bus import Events
                        self.event_bus.publish(Events.GAME_TICK, {'tick': tick})
                    except Exception as e:
                        logger.error(f"Error processing live signal: {e}", exc_info=True)

                self.root.after(0, process_signal)

            @self.live_feed.on('connected')
            def on_connected(info):
                # Marshal to Tkinter main thread
                def handle_connected():
                    socket_id = info.get('socketId')

                    # Skip first connection event (Socket ID not yet assigned)
                    # Socket.IO fires 'connect' twice during handshake - ignore the first one
                    if socket_id is None:
                        self.log("🔌 Connection negotiating...")
                        return

                    # Only process when Socket ID is available (actual connection established)
                    self.live_feed_connected = True
                    # Sync menu checkbox state (connection succeeded)
                    self.live_feed_var.set(True)
                    self.log(f"✅ Live feed connected (Socket ID: {socket_id})")
                    if self.toast:
                        self.toast.show("Live feed connected", "success")
                    # Update status label if it exists
                    if hasattr(self, 'phase_label'):
                        self.phase_label.config(text="PHASE: LIVE FEED", fg='#00ff88')

                self.root.after(0, handle_connected)

            @self.live_feed.on('disconnected')
            def on_disconnected(info):
                # Marshal to Tkinter main thread
                def handle_disconnected():
                    self.live_feed_connected = False
                    # Sync menu checkbox state (disconnected)
                    self.live_feed_var.set(False)
                    self.log("❌ Live feed disconnected")
                    if self.toast:
                        self.toast.show("Live feed disconnected", "error")
                    if hasattr(self, 'phase_label'):
                        self.phase_label.config(text="PHASE: DISCONNECTED", fg='#ff3366')

                self.root.after(0, handle_disconnected)

            @self.live_feed.on('gameComplete')
            def on_game_complete(data):
                # Marshal to Tkinter main thread
                def handle_game_complete():
                    game_num = data.get('gameNumber', 0)
                    self.log(f"💥 Game {game_num} complete")

                self.root.after(0, handle_game_complete)

            # Bug 6 Fix: Connect to feed in background thread (non-blocking)
            # This prevents UI freeze during Socket.IO handshake (up to 20s timeout)
            def connect_in_background():
                try:
                    self.live_feed.connect()
                except Exception as e:
                    logger.error(f"Background connection failed: {e}", exc_info=True)
                    # Marshal error handling to main thread
                    def handle_error():
                        self.log(f"Failed to connect to live feed: {e}")
                        if self.toast:
                            self.toast.show(f"Live feed error: {e}", "error")
                        self.live_feed = None
                        self.live_feed_connected = False
                        self.live_feed_var.set(False)
                    self.root.after(0, handle_error)

            import threading
            connection_thread = threading.Thread(target=connect_in_background, daemon=True)
            connection_thread.start()

        except Exception as e:
            logger.error(f"Failed to enable live feed: {e}", exc_info=True)
            self.log(f"Failed to connect to live feed: {e}")
            if self.toast:
                self.toast.show(f"Live feed error: {e}", "error")
            self.live_feed = None
            self.live_feed_connected = False
            # Sync menu checkbox state (connection failed)
            self.live_feed_var.set(False)

    def disable_live_feed(self):
        """Disable WebSocket live feed"""
        if not self.live_feed:
            self.log("Live feed not active")
            return

        try:
            self.log("Disconnecting from live feed...")
            self.live_feed.disconnect()
            self.live_feed = None
            self.live_feed_connected = False
            self.toast.show("Live feed disconnected", "info")
            if hasattr(self, 'phase_label'):
                self.phase_label.config(text="PHASE: DISCONNECTED", fg='white')
        except Exception as e:
            logger.error(f"Error disconnecting live feed: {e}", exc_info=True)
            self.log(f"Error disconnecting: {e}")

    def toggle_live_feed(self):
        """Toggle live feed on/off"""
        if self.live_feed_connected:
            self.disable_live_feed()
        else:
            self.enable_live_feed()

# display_tick() removed - now handled by ReplayEngine callbacks

    def toggle_playback(self):
        """Toggle play/pause using ReplayEngine"""
        if self.replay_engine.is_playing:
            self.replay_engine.pause()
            self.user_paused = True
            self.play_button.config(text="▶️ Play")
        else:
            self.replay_engine.play()
            self.user_paused = False
            self.play_button.config(text="⏸️ Pause")
    
    def step_forward(self):
        """Step forward one tick using ReplayEngine"""
        if not self.replay_engine.step_forward():
            self.log("Reached end of game")
            self.play_button.config(text="▶️ Play")
    
    def reset_game(self):
        """Reset to beginning using ReplayEngine"""
        self.replay_engine.reset()
        self.chart.clear_history()
        self.play_button.config(text="▶️ Play")
        self.user_paused = True
        self.log("Game reset")

    def set_playback_speed(self, speed: float):
        """Set playback speed"""
        self.replay_engine.set_speed(speed)
        self.speed_label.config(text=f"SPEED: {speed}X")
        self.log(f"Playback speed set to {speed}x")
    
    def execute_buy(self):
        """Execute buy action using TradeManager"""
        amount = self.get_bet_amount()
        if amount is None:
            return  # Validation failed (toast already shown)

        result = self.trade_manager.execute_buy(amount)

        if result['success']:
            self.log(f"BUY executed at {result['price']:.4f}x")
            self.toast.show(f"Bought {amount} SOL at {result['price']:.4f}x", "success")
        else:
            self.log(f"BUY failed: {result['reason']}")
            self.toast.show(f"Buy failed: {result['reason']}", "error")
    
    def execute_sell(self):
        """Execute sell action using TradeManager (Phase 8.2: supports partial sells)"""
        result = self.trade_manager.execute_sell()

        if result['success']:
            pnl = result.get('pnl_sol', 0)
            pnl_pct = result.get('pnl_percent', 0)
            msg_type = "success" if pnl >= 0 else "error"

            # Phase 8.2: Show partial sell information
            if result.get('partial', False):
                percentage = result.get('percentage', 1.0)
                remaining = result.get('remaining_amount', 0)
                self.log(f"PARTIAL SELL ({percentage*100:.0f}%) - P&L: {pnl:+.4f} SOL, Remaining: {remaining:.4f} SOL")
                self.toast.show(f"Sold {percentage*100:.0f}%! P&L: {pnl:+.4f} SOL ({pnl_pct:+.1f}%)", msg_type)
            else:
                self.log(f"SELL executed - P&L: {pnl:+.4f} SOL")
                self.toast.show(f"Sold! P&L: {pnl:+.4f} SOL ({pnl_pct:+.1f}%)", msg_type)
        else:
            self.log(f"SELL failed: {result['reason']}")
            self.toast.show(f"Sell failed: {result['reason']}", "error")
    
    def execute_sidebet(self):
        """Execute sidebet using TradeManager"""
        amount = self.get_bet_amount()
        if amount is None:
            return  # Validation failed (toast already shown)

        result = self.trade_manager.execute_sidebet(amount)

        if result['success']:
            potential_win = result.get('potential_win', 0)
            self.log(f"SIDEBET placed ({amount} SOL)")
            self.toast.show(f"Side bet placed! {amount} SOL (potential: {potential_win:.4f} SOL)", "warning")
        else:
            self.log(f"SIDEBET failed: {result['reason']}")
            self.toast.show(f"Side bet failed: {result['reason']}", "error")

    # ========================================================================
    # PERCENTAGE SELECTOR (Phase 8.2)
    # ========================================================================

    def set_sell_percentage(self, percentage: float):
        """
        Set the sell percentage (user clicked a percentage button)

        Phase 8.2: Radio-button style selector for partial sells

        Args:
            percentage: 0.1 (10%), 0.25 (25%), 0.5 (50%), or 1.0 (100%)
        """
        from decimal import Decimal

        # Update GameState with new percentage
        success = self.state.set_sell_percentage(Decimal(str(percentage)))

        if success:
            self.current_sell_percentage = percentage
            # Highlight the selected button
            self.ui_dispatcher.submit(lambda: self.highlight_percentage_button(percentage))
            self.log(f"Sell percentage set to {percentage*100:.0f}%")
        else:
            self.toast.show(f"Invalid percentage: {percentage*100:.0f}%", "error")

    def highlight_percentage_button(self, selected_percentage: float):
        """
        Highlight the selected percentage button (radio-button style)

        Phase 8.2: Only one button is highlighted at a time

        Args:
            selected_percentage: The percentage value that should be highlighted
        """
        for pct, btn_info in self.percentage_buttons.items():
            button = btn_info['button']
            if pct == selected_percentage:
                # Highlight selected button
                button.config(
                    bg=btn_info['selected_color'],
                    relief=tk.SUNKEN,
                    bd=3
                )
            else:
                # Reset unselected buttons
                button.config(
                    bg=btn_info['default_color'],
                    relief=tk.RAISED,
                    bd=2
                )

    # ========================================================================
    # BOT CONTROLS
    # ========================================================================

    def toggle_bot(self):
        """Toggle bot enable/disable"""
        self.bot_enabled = not self.bot_enabled

        if self.bot_enabled:
            # Start async bot executor
            self.bot_executor.start()

            self.bot_toggle_button.config(
                text="🤖 Disable Bot",
                bg='#ff3366'
            )
            self.bot_status_label.config(
                text=f"Bot: ACTIVE ({self.strategy_var.get()})",
                fg='#00ff88'
            )
            # Disable manual trading when bot is active
            self.buy_button.config(state=tk.DISABLED)
            self.sell_button.config(state=tk.DISABLED)
            self.sidebet_button.config(state=tk.DISABLED)
            self.log(f"🤖 Bot enabled with {self.strategy_var.get()} strategy (async mode)")
        else:
            # Stop async bot executor
            self.bot_executor.stop()

            self.bot_toggle_button.config(
                text="🤖 Enable Bot",
                bg='#666666'
            )
            self.bot_status_label.config(
                text="Bot: Disabled",
                fg='#666666'
            )

            # Bug 5 Fix: Re-enable manual trading buttons when bot is disabled
            # (but only if game is active)
            current_tick = self.state.current_tick
            if current_tick and current_tick.active:
                self.buy_button.config(state=tk.NORMAL)
                self.sell_button.config(state=tk.NORMAL)
                self.sidebet_button.config(state=tk.NORMAL)

            self.log("🤖 Bot disabled")

        # Bug 4 Fix: Sync menu checkbox with bot state
        self.bot_var.set(self.bot_enabled)

    def _on_strategy_changed(self, event):
        """Handle strategy selection change"""
        from bot import get_strategy

        strategy_name = self.strategy_var.get()
        try:
            # Update bot controller with new strategy
            strategy = get_strategy(strategy_name)
            self.bot_controller.strategy = strategy
            self.log(f"Strategy changed to: {strategy_name}")

            # Update status if bot is active
            if self.bot_enabled:
                self.bot_status_label.config(
                    text=f"Bot: ACTIVE ({strategy_name})"
                )
        except Exception as e:
            self.log(f"Failed to change strategy: {e}")

    # ========================================================================
    # REPLAY ENGINE CALLBACKS
    # ========================================================================

    def _on_tick_update(self, tick: GameTick, index: int, total: int):
        """Background callback for ReplayEngine tick updates"""
        self.ui_dispatcher.submit(self._process_tick_ui, tick, index, total)

    def _process_tick_ui(self, tick: GameTick, index: int, total: int):
        """Execute tick updates on the Tk main thread"""
        # Update UI labels
        self.tick_label.config(text=f"TICK: {tick.tick}")
        self.price_label.config(text=f"PRICE: {tick.price:.4f}X")

        # Show "RUGGED" if game was rugged (even during cooldown phase)
        display_phase = "RUGGED" if tick.rugged else tick.phase
        self.phase_label.config(text=f"PHASE: {display_phase}")

        # Update chart
        self.chart.add_tick(tick.tick, tick.price)

        # Maintain trading state lifecycles
        self.trade_manager.check_and_handle_rug(tick)
        self.trade_manager.check_sidebet_expiry(tick)

        # ========== BOT EXECUTION (ASYNC) ==========
        # Queue bot execution (non-blocking) - prevents deadlock
        if self.bot_enabled:
            self.bot_executor.queue_execution(tick)

        # Update button states based on phase (only when bot disabled)
        if not self.bot_enabled:
            if tick.is_tradeable():
                self.buy_button.config(state=tk.NORMAL)
                if not self.state.get('sidebet'):
                    self.sidebet_button.config(state=tk.NORMAL)
            else:
                self.buy_button.config(state=tk.DISABLED)
                self.sidebet_button.config(state=tk.DISABLED)

            # Check position status and display P&L
            position = self.state.get('position')
            if position and position.get('status') == 'active':
                self.sell_button.config(state=tk.NORMAL)

                # Calculate P&L in both percentage and SOL
                entry_price = position['entry_price']
                amount = position['amount']
                pnl_pct = ((tick.price / entry_price) - 1) * 100
                pnl_sol = amount * (tick.price - entry_price)

                self.position_label.config(
                    text=f"POS: {pnl_sol:+.4f} SOL ({pnl_pct:+.1f}%)",
                    fg='#00ff88' if pnl_sol > 0 else '#ff3366'
                )
            else:
                self.sell_button.config(state=tk.DISABLED)
                self.position_label.config(text="POSITION: NONE", fg='#666666')
        else:
            # Keep position display updated even when bot is active
            position = self.state.get('position')
            if position and position.get('status') == 'active':
                entry_price = position['entry_price']
                amount = position['amount']
                pnl_pct = ((tick.price / entry_price) - 1) * 100
                pnl_sol = amount * (tick.price - entry_price)

                self.position_label.config(
                    text=f"POS: {pnl_sol:+.4f} SOL ({pnl_pct:+.1f}%)",
                    fg='#00ff88' if pnl_sol > 0 else '#ff3366'
                )
            else:
                self.position_label.config(text="POSITION: NONE", fg='#666666')

        # Update sidebet countdown
        sidebet = self.state.get('sidebet')
        if sidebet and sidebet.get('status') == 'active':
            placed_tick = sidebet.get('placed_tick', 0)
            resolution_window = self.config.GAME_RULES.get('sidebet_window_ticks', 40)
            ticks_remaining = (placed_tick + resolution_window) - tick.tick

            if ticks_remaining > 0:
                self.sidebet_status_label.config(
                    text=f"SIDEBET: {ticks_remaining} ticks",
                    fg='#ffcc00'
                )
            else:
                self.sidebet_status_label.config(text="SIDEBET: RESOLVING", fg='#ff9900')
        else:
            self.sidebet_status_label.config(text="SIDEBET: NONE", fg='#666666')

    def _on_game_end(self, metrics: dict):
        """Callback for game end"""
        self.log(f"Game ended. Final balance: {metrics.get('current_balance', 0):.4f} SOL")

        # Check bankruptcy and reset for continuous testing
        if self.state.get('balance') < Decimal('0.001'):
            logger.warning("BANKRUPT - Resetting balance to initial")
            self.state.update(balance=self.state.get('initial_balance'))
            self.log("⚠️ Balance reset to initial (bankruptcy)")

        # Multi-game auto-advance (if enabled programmatically)
        if self.multi_game_mode and self.game_queue.has_next():
            next_file = self.game_queue.next_game()
            logger.info(f"Auto-loading next game: {next_file.name}")
            self.log(f"Auto-loading game {self.game_queue.current_index}/{len(self.game_queue)}")
            # Instant advance - NO DELAY
            self._load_next_game(next_file)
            if not self.user_paused:
                self.replay_engine.play()
                self.play_button.config(text="⏸️ Pause")
            else:
                self.play_button.config(text="▶️ Play")
        else:
            # Stop bot (original behavior when NOT in multi-game mode)
            if self.bot_enabled:
                self.bot_executor.stop()
                self.bot_enabled = False
                self.bot_toggle_button.config(text="🤖 Enable Bot", bg='#666666')
                self.bot_status_label.config(text="Bot: Disabled", fg='#666666')

                # Bug 4 Fix: Sync menu checkbox when auto-shutdown occurs
                self.bot_var.set(False)

            self.play_button.config(text="▶️ Play")

    def _load_next_game(self, filepath: Path):
        """Load next game in multi-game session (instant, no delay)"""
        try:
            self.load_game_file(filepath)
            # Keep bot running if it was enabled
            if self.bot_enabled:
                # Bot stays enabled across games
                logger.info("Bot remains enabled for next game")
        except Exception as e:
            logger.error(f"Failed to load next game: {e}")
            self.log(f"❌ Failed to load next game: {e}")
            # Stop multi-game mode on error
            self.multi_game_mode = False

    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================

    def _handle_game_tick(self, event):
        """Handle game tick event"""
        # Now handled by ReplayEngine callbacks
        pass
    
    def _handle_trade_executed(self, event):
        """Handle successful trade"""
        self.log(f"Trade executed: {event.get('data')}")
    
    def _handle_trade_failed(self, event):
        """Handle failed trade"""
        self.log(f"Trade failed: {event.get('data')}")
    
    def _handle_file_loaded(self, event):
        """Handle file loaded event"""
        files = event.get('data', {}).get('files', [])
        if files:
            self.log(f"Found {len(files)} game files")
            # Auto-load first file
            self.load_game_file(files[0])
    
    def _handle_balance_changed(self, data):
        """Handle balance change (thread-safe via TkDispatcher)"""
        new_balance = data.get('new')
        if new_balance is not None:
            # Marshal to UI thread via TkDispatcher
            self.ui_dispatcher.submit(
                lambda: self.balance_label.config(text=f"Balance: {new_balance:.4f} SOL")
            )
    
    def _handle_position_opened(self, data):
        """Handle position opened (thread-safe via TkDispatcher)"""
        entry_price = data.get('entry_price', 0)
        # Marshal to UI thread via TkDispatcher
        self.ui_dispatcher.submit(
            lambda: self.log(f"Position opened at {entry_price:.4f}")
        )
    
    def _handle_position_closed(self, data):
        """Handle position closed (thread-safe via TkDispatcher)"""
        pnl = data.get('pnl_sol', 0)
        # Marshal to UI thread via TkDispatcher
        self.ui_dispatcher.submit(
            lambda: self.log(f"Position closed - P&L: {pnl:+.4f} SOL")
        )

    def _handle_sell_percentage_changed(self, data):
        """Handle sell percentage changed (Phase 8.2, thread-safe via TkDispatcher)"""
        new_percentage = data.get('new', 1.0)
        # Marshal to UI thread - update button highlighting
        self.ui_dispatcher.submit(
            lambda: self.highlight_percentage_button(float(new_percentage))
        )

    def _handle_position_reduced(self, data):
        """Handle partial position close (Phase 8.2, thread-safe via TkDispatcher)"""
        percentage = data.get('percentage', 0)
        pnl = data.get('pnl_sol', 0)
        remaining = data.get('remaining_amount', 0)
        # Marshal to UI thread
        self.ui_dispatcher.submit(
            lambda: self.log(f"Position reduced ({percentage*100:.0f}%) - P&L: {pnl:+.4f} SOL, Remaining: {remaining:.4f} SOL")
        )

    def _check_bot_results(self):
        """
        Periodically check for bot execution results from async executor
        This runs in the UI thread and processes results non-blocking
        """
        if self.bot_enabled:
            # Process all pending results
            while True:
                result = self.bot_executor.get_latest_result()
                if not result:
                    break

                # Handle errors
                if 'error' in result:
                    self.bot_status_label.config(
                        text=f"Bot: ERROR",
                        fg='#ff3366'
                    )
                    self.log(f"🤖 Bot error at tick {result['tick']}: {result['error']}")
                    continue

                # Process successful execution
                bot_result = result.get('result', {})
                action = bot_result.get('action', 'WAIT')
                reasoning = bot_result.get('reasoning', '')
                success = bot_result.get('success', False)

                # Update UI for non-WAIT actions
                if action != 'WAIT':
                    status_text = f"Bot: {action}"
                    if reasoning:
                        status_text += f" ({reasoning[:30]}...)" if len(reasoning) > 30 else f" ({reasoning})"

                    self.bot_status_label.config(
                        text=status_text,
                        fg='#00ff88' if success else '#ff3366'
                    )

                    # Log bot action
                    if success:
                        self.log(f"🤖 Bot: {action} - {reasoning}")
                    else:
                        reason = bot_result.get('reason', 'Unknown')
                        self.log(f"🤖 Bot: {action} FAILED - {reason}")

        # Schedule next check (every 100ms)
        self.root.after(100, self._check_bot_results)

    # ========================================================================
    # BET AMOUNT METHODS
    # ========================================================================

    def set_bet_amount(self, amount: Decimal):
        """Set bet amount from quick buttons or manual input"""
        self.bet_entry.delete(0, tk.END)
        self.bet_entry.insert(0, str(amount))
        logger.debug(f"Bet amount set to {amount}")

    def increment_bet_amount(self, amount: Decimal):
        """Increment bet amount by specified amount"""
        try:
            current_amount = Decimal(self.bet_entry.get())
        except Exception:
            current_amount = Decimal('0')

        new_amount = current_amount + amount
        self.bet_entry.delete(0, tk.END)
        self.bet_entry.insert(0, str(new_amount))
        logger.debug(f"Bet amount incremented by {amount} to {new_amount}")

    def clear_bet_amount(self):
        """Clear bet amount to zero"""
        self.bet_entry.delete(0, tk.END)
        self.bet_entry.insert(0, "0")
        logger.debug("Bet amount cleared to 0")

    def get_bet_amount(self) -> Optional[Decimal]:
        """
        Get and validate bet amount from entry

        Returns:
            Decimal amount if valid, None otherwise
        """
        try:
            bet_amount = Decimal(self.bet_entry.get())

            min_bet = self.config.FINANCIAL['min_bet']
            max_bet = self.config.FINANCIAL['max_bet']

            if bet_amount < min_bet:
                self.toast.show(f"Bet must be at least {min_bet} SOL", "error")
                return None

            if bet_amount > max_bet:
                self.toast.show(f"Bet cannot exceed {max_bet} SOL", "error")
                return None

            balance = self.state.get('balance')
            if bet_amount > balance:
                self.toast.show(f"Insufficient balance! Have {balance:.4f} SOL", "error")
                return None

            return bet_amount

        except Exception as e:
            self.toast.show("Invalid bet amount", "error")
            logger.error(f"Invalid bet amount: {e}")
            return None

    # ========================================================================
    # KEYBOARD SHORTCUTS
    # ========================================================================

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for common actions"""
        self.root.bind('<space>', lambda e: self.toggle_playback())
        self.root.bind('b', lambda e: self.execute_buy() if self.buy_button['state'] != tk.DISABLED else None)
        self.root.bind('B', lambda e: self.execute_buy() if self.buy_button['state'] != tk.DISABLED else None)
        self.root.bind('s', lambda e: self.execute_sell() if self.sell_button['state'] != tk.DISABLED else None)
        self.root.bind('S', lambda e: self.execute_sell() if self.sell_button['state'] != tk.DISABLED else None)
        self.root.bind('d', lambda e: self.execute_sidebet() if self.sidebet_button['state'] != tk.DISABLED else None)
        self.root.bind('D', lambda e: self.execute_sidebet() if self.sidebet_button['state'] != tk.DISABLED else None)
        self.root.bind('r', lambda e: self.reset_game())
        self.root.bind('R', lambda e: self.reset_game())
        self.root.bind('<Left>', lambda e: self.step_backward())
        self.root.bind('<Right>', lambda e: self.step_forward())
        self.root.bind('<h>', lambda e: self.show_help())
        self.root.bind('<H>', lambda e: self.show_help())
        self.root.bind('l', lambda e: self.toggle_live_feed())
        self.root.bind('L', lambda e: self.toggle_live_feed())

        logger.info("Keyboard shortcuts configured (added 'L' for live feed)")

    def step_backward(self):
        """Step backward one tick"""
        if self.replay_engine.step_backward():
            self.log("Stepped backward")

    def show_help(self):
        """Show help dialog with keyboard shortcuts"""
        help_text = """
KEYBOARD SHORTCUTS:

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

Other:
  H - Show this help

GAME RULES:
• Side bets win if rug occurs within 40 ticks
• Side bet pays 5x your wager
• After side bet resolves, 5 tick cooldown before next bet
• All positions are lost when rug occurs
"""
        messagebox.showinfo("Help - Keyboard Shortcuts", help_text)

    # ========================================================================
    # MENU BAR CALLBACKS
    # ========================================================================

    def load_file_dialog(self):
        """Alias for load_game() - used by menu bar"""
        self.load_game()

    def toggle_play_pause(self):
        """Alias for toggle_playback() - used by menu bar"""
        self.toggle_playback()

    def _toggle_recording(self):
        """
        Toggle recording on/off from menu
        AUDIT FIX: Ensure all UI updates happen in main thread
        """
        def do_toggle():
            if self.replay_engine.auto_recording:
                self.replay_engine.disable_recording()
                self.recording_var.set(False)
                self.log("Recording disabled")
                if self.toast:
                    self.toast.show("Recording disabled", "info")
            else:
                self.replay_engine.enable_recording()
                self.recording_var.set(True)
                self.log("Recording enabled")
                if self.toast:
                    self.toast.show("Recording enabled", "success")

        # AUDIT FIX: Defensive - ensure always runs in main thread
        self.root.after(0, do_toggle)

    def _open_recordings_folder(self):
        """Open recordings folder in system file manager"""
        import subprocess
        import platform

        recordings_dir = self.config.FILES['recordings_dir']

        try:
            system = platform.system()
            if system == 'Linux':
                # Try xdg-open first (most Linux distros)
                subprocess.run(['xdg-open', str(recordings_dir)], check=True)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', str(recordings_dir)], check=True)
            elif system == 'Windows':
                subprocess.run(['explorer', str(recordings_dir)], check=True)
            else:
                raise OSError(f"Unsupported platform: {system}")

            self.log(f"Opened recordings folder: {recordings_dir}")
        except Exception as e:
            logger.error(f"Failed to open recordings folder: {e}", exc_info=True)
            self.log(f"Failed to open recordings folder: {e}")
            if self.toast:
                self.toast.show(f"Error opening folder: {e}", "error")

    def _toggle_bot_from_menu(self):
        """
        Toggle bot enable/disable from menu (syncs with button)
        AUDIT FIX: Ensure all UI updates happen in main thread
        """
        def do_toggle():
            self.toggle_bot()
            # Sync menu checkbutton state with actual bot state
            self.bot_var.set(self.bot_enabled)

        # AUDIT FIX: Defensive - ensure always runs in main thread
        self.root.after(0, do_toggle)

    def _show_bot_config(self):
        """
        Show bot configuration dialog (Phase 8.4)
        Thread-safe via root.after()
        """
        try:
            # Show configuration dialog (modal)
            updated_config = self.bot_config_panel.show()

            # If user clicked OK (not cancelled)
            if updated_config:
                self.log("Bot configuration updated - restart required for changes to take effect")

                # Inform user that restart is needed
                if self.toast:
                    self.toast.show(
                        "Configuration saved. Restart application to apply changes.",
                        "info"
                    )

                # Note: We don't update bot at runtime to avoid complexity
                # User needs to restart application for changes to take effect

        except Exception as e:
            logger.error(f"Failed to show bot config: {e}", exc_info=True)
            self.log(f"Error showing configuration: {e}")
            if self.toast:
                self.toast.show(f"Configuration error: {e}", "error")

    # ========== TIMING METRICS (Phase 8.6) ==========

    def _show_timing_metrics(self):
        """
        Show detailed timing metrics window (Phase 8.6 - Option C)
        Modal popup with full statistics
        """
        if not self.browser_executor:
            from tkinter import messagebox
            messagebox.showinfo(
                "Timing Metrics",
                "Timing metrics are only available when browser executor is active.\n\n"
                "Enable browser connection first."
            )
            return

        # Get timing stats
        stats = self.browser_executor.get_timing_stats()

        # Create modal dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Bot Timing Metrics")
        dialog.geometry("400x350")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Main container
        main_frame = tk.Frame(dialog, bg='#1a1a1a', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = tk.Label(
            main_frame,
            text="Execution Timing Statistics",
            font=('Arial', 14, 'bold'),
            bg='#1a1a1a',
            fg='#ffffff'
        )
        title_label.pack(pady=(0, 15))

        # Stats frame
        stats_frame = tk.Frame(main_frame, bg='#2a2a2a', relief=tk.RIDGE, bd=2)
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Format stats as labels
        stats_text = [
            ("Total Executions:", f"{stats['total_executions']}"),
            ("Successful:", f"{stats['successful_executions']}"),
            ("Success Rate:", f"{stats['success_rate']:.1%}"),
            ("", ""),
            ("Average Total Delay:", f"{stats['avg_total_delay_ms']:.1f}ms"),
            ("Average Click Delay:", f"{stats['avg_click_delay_ms']:.1f}ms"),
            ("Average Confirmation:", f"{stats['avg_confirmation_delay_ms']:.1f}ms"),
            ("", ""),
            ("P50 Delay:", f"{stats['p50_total_delay_ms']:.1f}ms"),
            ("P95 Delay:", f"{stats['p95_total_delay_ms']:.1f}ms"),
        ]

        for i, (label_text, value_text) in enumerate(stats_text):
            if not label_text:  # Separator
                separator = tk.Frame(stats_frame, height=10, bg='#2a2a2a')
                separator.pack(fill=tk.X)
                continue

            row_frame = tk.Frame(stats_frame, bg='#2a2a2a')
            row_frame.pack(fill=tk.X, padx=15, pady=5)

            label = tk.Label(
                row_frame,
                text=label_text,
                font=('Arial', 10),
                bg='#2a2a2a',
                fg='#cccccc',
                anchor=tk.W
            )
            label.pack(side=tk.LEFT)

            value = tk.Label(
                row_frame,
                text=value_text,
                font=('Arial', 10, 'bold'),
                bg='#2a2a2a',
                fg='#00ff00' if 'Success' in label_text else '#ffffff',
                anchor=tk.E
            )
            value.pack(side=tk.RIGHT)

        # Close button
        close_button = tk.Button(
            main_frame,
            text="Close",
            command=dialog.destroy,
            bg='#3a3a3a',
            fg='#ffffff',
            font=('Arial', 10),
            relief=tk.FLAT,
            padx=20,
            pady=5
        )
        close_button.pack()

        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def _update_timing_metrics_display(self):
        """
        Update draggable timing overlay (Phase 8.6)
        Called every second when bot is active in UI_LAYER mode
        """
        if not self.browser_executor:
            # Hide overlay if no executor
            self.timing_overlay.hide()
            return

        # Get current execution mode
        execution_mode = self.bot_config_panel.get_execution_mode()
        from bot.execution_mode import ExecutionMode

        # Only show timing overlay in UI_LAYER mode
        if execution_mode == ExecutionMode.UI_LAYER:
            # Show overlay
            self.timing_overlay.show()

            # Get timing stats
            stats = self.browser_executor.get_timing_stats()

            # Update overlay with stats
            self.timing_overlay.update_stats(stats)
        else:
            # Hide overlay in BACKEND mode
            self.timing_overlay.hide()

    def _update_timing_metrics_loop(self):
        """
        Periodic timing metrics update loop (Phase 8.6)
        Runs every 1 second to update inline timing display
        """
        try:
            self._update_timing_metrics_display()
        except Exception as e:
            logger.error(f"Error updating timing metrics: {e}", exc_info=True)

        # Schedule next update (every 1000ms = 1 second)
        self.root.after(1000, self._update_timing_metrics_loop)

    # ========== BROWSER AUTOMATION CALLBACKS (Phase 8.5) ==========

    def _show_browser_connection_dialog(self):
        """Show browser connection wizard (Phase 8.5)"""
        from tkinter import messagebox

        if not self.browser_executor:
            messagebox.showerror(
                "Browser Not Available",
                "Browser automation is not available.\n\n"
                "Check that browser_automation/ directory exists."
            )
            return

        if self.browser_connected:
            messagebox.showinfo(
                "Already Connected",
                "Browser is already connected.\n\n"
                "Disconnect first before reconnecting."
            )
            return

        # AUDIT FIX: Wrap dialog creation in try/except to catch and log errors
        try:
            # Import dialog
            from ui.browser_connection_dialog import BrowserConnectionDialog

            logger.debug("Creating BrowserConnectionDialog...")

            # Show dialog
            dialog = BrowserConnectionDialog(
                parent=self.root,
                browser_executor=self.browser_executor,
                on_connected=self._on_browser_connected,
                on_failed=self._on_browser_connection_failed
            )

            logger.debug("Calling dialog.show()...")
            dialog.show()
            logger.debug("Dialog displayed successfully")

        except Exception as e:
            logger.error(f"Failed to show browser connection dialog: {e}", exc_info=True)
            messagebox.showerror(
                "Dialog Error",
                f"Failed to show browser connection dialog:\n\n{e}\n\nCheck logs for details."
            )

    def _on_browser_connected(self):
        """Called when browser connects successfully"""
        self.browser_connected = True

        # Update status bar (if browser_status_label exists)
        if hasattr(self, 'browser_status_label'):
            self._update_browser_status('connected')

        # Update menu (change status, enable disconnect)
        if hasattr(self, 'browser_menu'):
            self.browser_menu.entryconfig(
                self.browser_status_item_index,
                label="🟢 Status: Connected"
            )
            self.browser_menu.entryconfig(
                self.browser_disconnect_item_index,
                state=tk.NORMAL
            )

        logger.info("Browser connected successfully")
        if self.toast:
            self.toast.show("Browser connected to rugs.fun", "success")

    def _on_browser_connection_failed(self, error=None):
        """Called when browser connection fails"""
        logger.error(f"Browser connection failed: {error}")
        if self.toast:
            self.toast.show(f"Browser connection failed: {error}", "error")

    def _disconnect_browser(self):
        """Disconnect browser (Phase 8.5)"""
        from tkinter import messagebox
        import asyncio
        import threading

        if not self.browser_connected:
            return

        # Confirm with user
        result = messagebox.askyesno(
            "Disconnect Browser",
            "Disconnect from live browser?\n\n"
            "This will close the browser window."
        )

        if not result:
            return

        # Update status immediately
        if hasattr(self, 'browser_status_label'):
            self._update_browser_status('disconnecting')

        # Stop browser in background thread
        def stop_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.browser_executor.stop_browser())
                logger.info("Browser stopped successfully")

                # Update UI on main thread
                self.root.after(0, self._on_browser_disconnected)
            except Exception as e:
                logger.error(f"Error stopping browser: {e}")
                self.root.after(
                    0,
                    lambda: messagebox.showerror("Disconnect Failed", str(e))
                )
            finally:
                # AUDIT FIX: Always close event loop to prevent resource leak
                loop.close()
                asyncio.set_event_loop(None)

        thread = threading.Thread(target=stop_async, daemon=True)
        thread.start()

    def _on_browser_disconnected(self):
        """Called when browser disconnects"""
        self.browser_connected = False

        # Update status bar
        if hasattr(self, 'browser_status_label'):
            self._update_browser_status('disconnected')

        # Update menu (change status, disable disconnect)
        if hasattr(self, 'browser_menu'):
            self.browser_menu.entryconfig(
                self.browser_status_item_index,
                label="⚫ Status: Not Connected"
            )
            self.browser_menu.entryconfig(
                self.browser_disconnect_item_index,
                state=tk.DISABLED
            )

        logger.info("Browser disconnected")
        if self.toast:
            self.toast.show("Browser disconnected", "info")

    def _update_browser_status(self, status):
        """
        Update browser status indicator

        Args:
            status: "disconnected", "connecting", "connected", "disconnecting", "error"
        """
        status_icons = {
            'disconnected': '⚫',      # Gray
            'connecting': '🟡',        # Yellow
            'connected': '🟢',         # Green
            'disconnecting': '🟡',     # Yellow
            'error': '🔴'              # Red
        }

        colors = {
            'disconnected': '#888888',
            'connecting': '#ffcc00',
            'connected': '#00ff88',
            'disconnecting': '#ffcc00',
            'error': '#ff3366'
        }

        icon = status_icons.get(status, '⚫')
        fg_color = colors.get(status, '#888888')
        text = f"BROWSER: {icon} {status.title()}"

        # Update status label (thread-safe)
        if hasattr(self, 'browser_status_label'):
            self.ui_dispatcher.submit(
                lambda: self.browser_status_label.config(text=text, fg=fg_color)
            )

    def _toggle_live_feed_from_menu(self):
        """
        Toggle live feed connection from menu (syncs with actual state)
        AUDIT FIX: Ensure all UI updates happen in main thread
        """
        def do_toggle():
            self.toggle_live_feed()
            # Checkbox will be synced in event handlers (connected/disconnected)
            # Don't sync here - connection is async and takes 100-2000ms!

        # AUDIT FIX: Defensive - ensure always runs in main thread
        self.root.after(0, do_toggle)

    def _show_about(self):
        """Show about dialog with application information"""
        about_text = """
REPLAYER - Rugs.fun Game Replay & Analysis System
Version: 2.0 (Phase 7B - Menu Bar)

A professional replay viewer and empirical analysis engine for
Rugs.fun trading game recordings.

Features:
• Interactive replay with speed control
• Trading bot automation (Conservative, Aggressive, Sidebet)
• Real-time WebSocket live feed integration
• Multi-game session support
• Position & P&L tracking
• Empirical analysis for RL training

Architecture:
• Event-driven modular design
• Thread-safe state management
• 141 test suite coverage
• Symlinked ML predictor integration

Part of the Rugs.fun quantitative trading ecosystem:
• CV-BOILER-PLATE-FORK: YOLOv8 live detection
• rugs-rl-bot: Reinforcement learning trading bot
• REPLAYER: Replay viewer & analysis engine

Keyboard Shortcuts: Press 'H' for help

© 2025 REPLAYER Project
"""
        messagebox.showinfo("About REPLAYER", about_text)

    def shutdown(self):
        """Cleanup dispatcher resources during application shutdown."""
        # Phase 8.5: Stop browser if connected
        if self.browser_connected and self.browser_executor:
            loop = None
            try:
                logger.info("Shutting down browser...")
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.browser_executor.stop_browser())
                logger.info("Browser stopped")
            except Exception as e:
                logger.error(f"Error stopping browser during shutdown: {e}", exc_info=True)
            finally:
                # AUDIT FIX: Always close event loop to prevent resource leak
                if loop:
                    loop.close()
                    asyncio.set_event_loop(None)

        # Disconnect live feed first (Phase 6 cleanup)
        if self.live_feed_connected and self.live_feed:
            try:
                logger.info("Shutting down live feed...")
                self.live_feed.disconnect()
                self.live_feed = None
                self.live_feed_connected = False
            except Exception as e:
                logger.error(f"Error disconnecting live feed during shutdown: {e}", exc_info=True)

        # Stop bot executor
        if self.bot_enabled:
            self.bot_executor.stop()
            self.bot_enabled = False

        # Stop UI dispatcher
        self.ui_dispatcher.stop()
