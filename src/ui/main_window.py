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
from ui.balance_edit_dialog import BalanceUnlockDialog, BalanceRelockDialog, BalanceEditEntry
from bot import BotInterface, BotController, list_strategies
from bot.async_executor import AsyncBotExecutor
from bot.execution_mode import ExecutionMode  # Phase 8.4
from bot.ui_controller import BotUIController  # Phase 8.4
from bot.browser_executor import BrowserExecutor  # Phase 8.5
from bot.browser_bridge import get_browser_bridge, BridgeStatus  # Phase 9.3
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

        # Balance editing state (lock/unlock sync to rugs.fun)
        self.balance_locked = True
        self.manual_balance: Optional[Decimal] = None
        self.tracked_balance: Decimal = self.state.get('balance')

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

        # Phase 9.3: Initialize browser bridge for UI button -> browser sync
        self.browser_bridge = get_browser_bridge()
        # Phase 3.5: Callback registration moved to after BrowserBridgeController initialization
        logger.info("BrowserBridge initialized for UI-to-browser button sync")

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

        # Phase A.2: Bot components will be initialized AFTER UI is built (line ~640)
        # to avoid AttributeError when accessing button references
        self.bot_ui_controller = None  # Placeholder, will be set later
        self.bot_controller = None     # Placeholder, will be set later
        self.bot_executor = None       # Placeholder, will be set later

        # Phase 8.4: Set bot enabled state from config
        self.bot_enabled = self.bot_config_panel.is_bot_enabled()

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

        # Phase 3.1: Monitoring loops now handled by BotManager
        # (removed _check_bot_results() and _update_timing_metrics_loop() calls)

        logger.info("MainWindow initialized with ReplayEngine and async bot executor")

    def _create_menu_bar(self):
        """Create menu bar for additional functionality"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Recording...", command=lambda: self.replay_controller.load_file_dialog() if hasattr(self, 'replay_controller') else None)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Playback Menu
        playback_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Playback", menu=playback_menu)
        playback_menu.add_command(label="Play/Pause", command=lambda: self.replay_controller.toggle_play_pause() if hasattr(self, 'replay_controller') else None)
        playback_menu.add_command(label="Stop", command=lambda: self.replay_controller.reset_game() if hasattr(self, 'replay_controller') else None)

        # Recording Menu
        recording_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Recording", menu=recording_menu)

        # Recording toggle - tracks replay_engine.auto_recording state (variable created in _create_ui())
        recording_menu.add_checkbutton(
            label="Enable Recording",
            variable=self.recording_var,
            command=lambda: self.replay_controller.toggle_recording() if hasattr(self, 'replay_controller') else None
        )
        recording_menu.add_separator()
        recording_menu.add_command(label="Open Recordings Folder", command=lambda: self.replay_controller.open_recordings_folder() if hasattr(self, 'replay_controller') else None)

        # Bot Menu
        bot_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Bot", menu=bot_menu)

        # bot_var created in _create_ui()
        bot_menu.add_checkbutton(
            label="Enable Bot",
            variable=self.bot_var,
            command=self.bot_manager.toggle_bot_from_menu
        )

        # Phase 8.4: Add configuration menu item
        bot_menu.add_separator()
        bot_menu.add_command(
            label="Configuration...",
            command=lambda: self.root.after(0, self.bot_manager.show_bot_config)
        )

        # Phase 8.6: Add timing metrics menu item
        bot_menu.add_command(
            label="Timing Metrics...",
            command=lambda: self.root.after(0, self.bot_manager.show_timing_metrics)
        )

        # Phase A: Add timing overlay toggle (variable created in _create_ui())
        bot_menu.add_separator()
        bot_menu.add_checkbutton(
            label="Show Timing Overlay",
            variable=self.timing_overlay_var,
            command=self.bot_manager.toggle_timing_overlay
        )

        # Live Feed Menu
        live_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Live Feed", menu=live_menu)

        # live_feed_var created in _create_ui()
        live_menu.add_checkbutton(
            label="Connect to Live Feed",
            variable=self.live_feed_var,
            command=lambda: self.live_feed_controller.toggle_live_feed_from_menu()
        )

        # ========== BROWSER MENU (Phase 9.3: CDP Bridge) ==========
        browser_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Browser", menu=browser_menu)

        # Phase 9.3: Browser Bridge menu (uses CDP connection)
        browser_menu.add_command(
            label="Connect to Browser",
            command=lambda: self.root.after(0, self.browser_bridge_controller.connect_browser_bridge)
        )

        browser_menu.add_separator()

        # Status indicators (disabled, display only)
        browser_menu.add_command(
            label="⚫ Status: Disconnected",
            state=tk.DISABLED
        )

        browser_menu.add_command(
            label="Profile: rugs_bot",
            state=tk.DISABLED
        )

        browser_menu.add_separator()

        # Disconnect command (initially disabled)
        browser_menu.add_command(
            label="Disconnect Browser",
            command=lambda: self.root.after(0, self.browser_bridge_controller.disconnect_browser_bridge),
            state=tk.DISABLED
        )

        # Store menu references for status updates
        self.browser_menu = browser_menu
        self.browser_status_item_index = 2  # "⚫ Status: Disconnected"
        self.browser_disconnect_item_index = 5  # "Disconnect Browser"
        self.browser_connect_item_index = 0  # "Connect to Browser"

        # View Menu (Phase 3: UI Theming)
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)

        # Theme submenu with submenus for dark/light categories
        theme_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Theme", menu=theme_menu)

        # Dark themes submenu
        dark_theme_menu = tk.Menu(theme_menu, tearoff=0)
        theme_menu.add_cascade(label="Dark Themes", menu=dark_theme_menu)

        dark_themes = [
            ('cyborg', 'Cyborg - Neon gaming style'),
            ('darkly', 'Darkly - Professional dark'),
            ('superhero', 'Superhero - Bold & vibrant'),
            ('solar', 'Solar - Warm dark theme'),
            ('vapor', 'Vapor - Vaporwave aesthetic'),
        ]

        for theme_id, theme_label in dark_themes:
            dark_theme_menu.add_command(
                label=theme_label,
                command=lambda t=theme_id: self._change_theme(t)
            )

        # Light themes submenu
        light_theme_menu = tk.Menu(theme_menu, tearoff=0)
        theme_menu.add_cascade(label="Light Themes", menu=light_theme_menu)

        light_themes = [
            ('cosmo', 'Cosmo - Professional blue'),
            ('flatly', 'Flatly - Modern flat design'),
            ('litera', 'Litera - Clean serif style'),
            ('minty', 'Minty - Fresh green accent'),
            ('lumen', 'Lumen - Bright & clean'),
            ('sandstone', 'Sandstone - Warm earth tones'),
            ('yeti', 'Yeti - Cool blue minimal'),
            ('pulse', 'Pulse - Vibrant purple'),
            ('united', 'United - Ubuntu-inspired'),
            ('morph', 'Morph - Soft neumorphic'),
            ('journal', 'Journal - Serif elegant'),
            ('simplex', 'Simplex - Minimalist clean'),
            ('cerculean', 'Cerculean - Sky blue fresh'),
        ]

        for theme_id, theme_label in light_themes:
            light_theme_menu.add_command(
                label=theme_label,
                command=lambda t=theme_id: self._change_theme(t)
            )

        # UI Style submenu (Phase: Modern UI)
        view_menu.add_separator()
        ui_style_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="UI Style", menu=ui_style_menu)
        ui_style_menu.add_command(label="Standard ✓", state=tk.DISABLED)
        ui_style_menu.add_command(label="Modern (Game-Like)", command=lambda: self._set_ui_style('modern'))

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _create_ui(self):
        """Create UI matching the user's mockup design"""
        # Menu bar will be created after controllers are initialized (moved to __init__)

        # Create UI variables early (needed by controllers)
        self.bot_var = tk.BooleanVar(value=self.bot_enabled)
        self.recording_var = tk.BooleanVar(value=self.replay_engine.auto_recording)
        self.live_feed_var = tk.BooleanVar(value=self.live_feed_connected)
        self.timing_overlay_var = tk.BooleanVar(value=False)  # Hidden by default

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
            command=lambda: self.replay_controller.load_game() if hasattr(self, 'replay_controller') else None,
            bg='#444444',
            fg='white',
            **btn_style
        )
        self.load_button.pack(side=tk.LEFT, padx=5)

        self.play_button = tk.Button(
            playback_left,
            text="PLAY",
            command=lambda: self.replay_controller.toggle_playback() if hasattr(self, 'replay_controller') else None,
            bg='#444444',
            fg='white',
            state=tk.DISABLED,
            **btn_style
        )
        self.play_button.pack(side=tk.LEFT, padx=5)

        self.step_button = tk.Button(
            playback_left,
            text="STEP",
            command=lambda: self.replay_controller.step_forward() if hasattr(self, 'replay_controller') else None,
            bg='#444444',
            fg='white',
            state=tk.DISABLED,
            **btn_style
        )
        self.step_button.pack(side=tk.LEFT, padx=5)

        self.reset_button = tk.Button(
            playback_left,
            text="RESET",
            command=lambda: self.replay_controller.reset_game() if hasattr(self, 'replay_controller') else None,
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
        tk.Button(speed_frame, text="0.25x", command=lambda: self.replay_controller.set_playback_speed(0.25) if hasattr(self, 'replay_controller') else None, bg='#333333', fg='white', **speed_btn_style).pack(side=tk.LEFT, padx=1)
        tk.Button(speed_frame, text="0.5x", command=lambda: self.replay_controller.set_playback_speed(0.5) if hasattr(self, 'replay_controller') else None, bg='#333333', fg='white', **speed_btn_style).pack(side=tk.LEFT, padx=1)
        tk.Button(speed_frame, text="1x", command=lambda: self.replay_controller.set_playback_speed(1.0) if hasattr(self, 'replay_controller') else None, bg='#444444', fg='white', **speed_btn_style).pack(side=tk.LEFT, padx=1)
        tk.Button(speed_frame, text="2x", command=lambda: self.replay_controller.set_playback_speed(2.0) if hasattr(self, 'replay_controller') else None, bg='#333333', fg='white', **speed_btn_style).pack(side=tk.LEFT, padx=1)
        tk.Button(speed_frame, text="5x", command=lambda: self.replay_controller.set_playback_speed(5.0) if hasattr(self, 'replay_controller') else None, bg='#333333', fg='white', **speed_btn_style).pack(side=tk.LEFT, padx=1)

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

        # Store button references for BotUIController access (Phase A.2)
        self.clear_button = tk.Button(bet_center, text="X", command=lambda: self.trading_controller.clear_bet_amount() if hasattr(self, 'trading_controller') else None, bg='#333333', fg='white', **bet_btn_style)
        self.clear_button.pack(side=tk.LEFT, padx=2)

        self.increment_001_button = tk.Button(bet_center, text="+0.001", command=lambda: self.trading_controller.increment_bet_amount(Decimal('0.001')) if hasattr(self, 'trading_controller') else None, bg='#333333', fg='white', **bet_btn_style)
        self.increment_001_button.pack(side=tk.LEFT, padx=2)

        self.increment_01_button = tk.Button(bet_center, text="+0.01", command=lambda: self.trading_controller.increment_bet_amount(Decimal('0.01')) if hasattr(self, 'trading_controller') else None, bg='#333333', fg='white', **bet_btn_style)
        self.increment_01_button.pack(side=tk.LEFT, padx=2)

        self.increment_10_button = tk.Button(bet_center, text="+0.1", command=lambda: self.trading_controller.increment_bet_amount(Decimal('0.1')) if hasattr(self, 'trading_controller') else None, bg='#333333', fg='white', **bet_btn_style)
        self.increment_10_button.pack(side=tk.LEFT, padx=2)

        self.increment_1_button = tk.Button(bet_center, text="+1", command=lambda: self.trading_controller.increment_bet_amount(Decimal('1')) if hasattr(self, 'trading_controller') else None, bg='#333333', fg='white', **bet_btn_style)
        self.increment_1_button.pack(side=tk.LEFT, padx=2)

        self.half_button = tk.Button(bet_center, text="1/2", command=lambda: self.trading_controller.half_bet_amount() if hasattr(self, 'trading_controller') else None, bg='#333333', fg='white', **bet_btn_style)
        self.half_button.pack(side=tk.LEFT, padx=2)

        self.double_button = tk.Button(bet_center, text="X2", command=lambda: self.trading_controller.double_bet_amount() if hasattr(self, 'trading_controller') else None, bg='#333333', fg='white', **bet_btn_style)
        self.double_button.pack(side=tk.LEFT, padx=2)

        self.max_button = tk.Button(bet_center, text="MAX", command=lambda: self.trading_controller.max_bet_amount() if hasattr(self, 'trading_controller') else None, bg='#333333', fg='white', **bet_btn_style)
        self.max_button.pack(side=tk.LEFT, padx=2)

        # Right - wallet balance + lock control
        balance_container = tk.Frame(bet_row, bg='#1a1a1a')
        balance_container.pack(side=tk.RIGHT, padx=5)

        self.balance_lock_button = tk.Button(
            balance_container,
            text="🔒",
            command=self._toggle_balance_lock,
            bg='#333333',
            fg='white',
            font=('Arial', 10, 'bold'),
            bd=1,
            relief=tk.RAISED,
            width=3
        )
        self.balance_lock_button.pack(side=tk.RIGHT, padx=4)

        self.balance_label = tk.Label(
            balance_container,
            text=f"WALLET: {self.state.get('balance'):.3f}",
            font=('Arial', 11, 'bold'),
            bg='#1a1a1a',
            fg='#ffcc00'
        )
        self.balance_label.pack(side=tk.RIGHT, padx=4)

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
            command=lambda: self.trading_controller.execute_sidebet() if hasattr(self, 'trading_controller') else None,
            bg='#3399ff',
            fg='white',
            state=tk.NORMAL,  # Always enabled for testing browser forwarding
            **large_btn_style
        )
        self.sidebet_button.pack(side=tk.LEFT, padx=5)

        self.buy_button = tk.Button(
            action_left,
            text="BUY",
            command=lambda: self.trading_controller.execute_buy() if hasattr(self, 'trading_controller') else None,
            bg='#00ff66',
            fg='black',
            state=tk.NORMAL,  # Always enabled for testing browser forwarding
            **large_btn_style
        )
        self.buy_button.pack(side=tk.LEFT, padx=5)

        self.sell_button = tk.Button(
            action_left,
            text="SELL",
            command=lambda: self.trading_controller.execute_sell() if hasattr(self, 'trading_controller') else None,
            bg='#ff3399',
            fg='white',
            state=tk.NORMAL,  # Always enabled for testing browser forwarding
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
                command=lambda v=value: self.trading_controller.set_sell_percentage(v) if hasattr(self, 'trading_controller') else None,
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
        if hasattr(self, 'trading_controller'):
            self.trading_controller.highlight_percentage_button(1.0)

        # Right - bot and info
        action_right = tk.Frame(action_row, bg='#1a1a1a')
        action_right.pack(side=tk.RIGHT, padx=10, pady=10)

        # Bot controls (top right)
        bot_top = tk.Frame(action_right, bg='#1a1a1a')
        bot_top.pack(anchor='e')

        self.bot_toggle_button = tk.Button(
            bot_top,
            text="ENABLE BOT",
            command=lambda: self.bot_manager.toggle_bot() if hasattr(self, 'bot_manager') else None,
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
        self.strategy_dropdown.bind('<<ComboboxSelected>>', lambda e: self.bot_manager.on_strategy_changed(e) if hasattr(self, 'bot_manager') else None)

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

        # Phase A.2: Initialize BotUIController AFTER all UI widgets are created
        # (moved from line 82 to avoid AttributeError accessing button references)
        # Phase A.7: Pass timing configuration from bot_config.json
        bot_config = self.bot_config_panel.get_config()
        self.bot_ui_controller = BotUIController(
            self,
            button_depress_duration_ms=bot_config.get('button_depress_duration_ms', 50),
            inter_click_pause_ms=bot_config.get('inter_click_pause_ms', 100)
        )

        # Phase A.2: Create BotController now that ui_controller is ready
        execution_mode = self.bot_config_panel.get_execution_mode()
        strategy = self.bot_config_panel.get_strategy()

        self.bot_controller = BotController(
            self.bot_interface,
            strategy_name=strategy,
            execution_mode=execution_mode,
            ui_controller=self.bot_ui_controller if execution_mode == ExecutionMode.UI_LAYER else None
        )

        # Phase A.2: Initialize async bot executor (prevents deadlock)
        self.bot_executor = AsyncBotExecutor(self.bot_controller)

        # Phase 3.1: Initialize BotManager controller
        from ui.controllers import BotManager, ReplayController, TradingController, LiveFeedController, BrowserBridgeController
        self.bot_manager = BotManager(
            root=self.root,
            state=self.state,
            bot_executor=self.bot_executor,
            bot_controller=self.bot_controller,
            bot_config_panel=self.bot_config_panel,
            timing_overlay=self.timing_overlay,
            browser_executor=self.browser_executor,
            # UI widgets
            bot_toggle_button=self.bot_toggle_button,
            bot_status_label=self.bot_status_label,
            buy_button=self.buy_button,
            sell_button=self.sell_button,
            sidebet_button=self.sidebet_button,
            strategy_var=self.strategy_var,
            bot_var=self.bot_var,
            timing_overlay_var=self.timing_overlay_var,
            # Notifications
            toast=self.toast,
            # Callbacks
            log_callback=self.log
        )

        # Phase 3.2: Initialize ReplayController
        self.replay_controller = ReplayController(
            root=self.root,
            parent_window=self,
            replay_engine=self.replay_engine,
            chart=self.chart,
            config=self.config,
            # UI widgets
            play_button=self.play_button,
            step_button=self.step_button,
            reset_button=self.reset_button,
            bot_toggle_button=self.bot_toggle_button,
            speed_label=self.speed_label,
            # UI variables
            recording_var=self.recording_var,
            # Other dependencies
            toast=self.toast,
            # Callbacks
            log_callback=self.log
        )

        # Phase 3.3: Initialize TradingController
        self.trading_controller = TradingController(
            parent_window=self,
            trade_manager=self.trade_manager,
            state=self.state,
            config=self.config,
            browser_bridge=self.browser_bridge,
            # UI widgets
            bet_entry=self.bet_entry,
            percentage_buttons=self.percentage_buttons,
            # UI dispatcher
            ui_dispatcher=self.ui_dispatcher,
            # Notifications
            toast=self.toast,
            # Callbacks
            log_callback=self.log
        )

        # Phase 3.4: Initialize LiveFeedController
        self.live_feed_controller = LiveFeedController(
            root=self.root,
            parent_window=self,
            replay_engine=self.replay_engine,
            event_bus=self.event_bus,
            # UI variables
            live_feed_var=self.live_feed_var,
            # Notifications
            toast=self.toast,
            # Callbacks
            log_callback=self.log
        )

        # Create menu bar now (after controllers are initialized, before BrowserBridgeController needs it)
        self._create_menu_bar()

        # Phase 3.5: Initialize BrowserBridgeController
        self.browser_bridge_controller = BrowserBridgeController(
            root=self.root,
            parent_window=self,
            # UI components
            browser_menu=self.browser_menu,
            browser_status_item_index=self.browser_status_item_index,
            browser_disconnect_item_index=self.browser_disconnect_item_index,
            # Notifications
            toast=self.toast,
            # Callbacks
            log_callback=self.log
        )

        # Phase 3.5: Register browser bridge status change callback
        self.browser_bridge.on_status_change = self.browser_bridge_controller.on_bridge_status_change

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
    
    # Phase 3.2: load_game, load_game_file moved to ReplayController

    # Phase 3.4: enable_live_feed, disable_live_feed, toggle_live_feed moved to LiveFeedController

# display_tick() removed - now handled by ReplayEngine callbacks

    # Phase 3.2: toggle_playback, step_forward, reset_game, set_playback_speed moved to ReplayController

    # Phase 3.3: execute_buy, execute_sell, execute_sidebet, set_sell_percentage, highlight_percentage_button moved to TradingController

    # ========================================================================
    # BOT CONTROLS
    # ========================================================================

    # Phase 3.1: toggle_bot and _on_strategy_changed moved to BotManager

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

        # Live-mode safety: never block BUY/SELL/SIDEBET if live bridge or live_mode is on
        live_override = self.live_mode or (self.browser_bridge and self.browser_bridge.is_connected())

        # Update button states based on phase (only when bot disabled and not overridden)
        if not self.bot_enabled and not live_override:
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
            # Keep position display updated even when bot is active or live override is enabled
            position = self.state.get('position')
            if position and position.get('status') == 'active':
                entry_price = position['entry_price']
                amount = position['amount']
                pnl_pct = ((tick.price / entry_price) - 1) * 100
                pnl_sol = amount * (tick.price - entry_price)

                # Keep manual overrides enabled in live/bridge scenarios
                self.buy_button.config(state=tk.NORMAL)
                self.sidebet_button.config(state=tk.NORMAL)
                self.sell_button.config(state=tk.NORMAL)

                self.position_label.config(
                    text=f"POS: {pnl_sol:+.4f} SOL ({pnl_pct:+.1f}%)",
                    fg='#00ff88' if pnl_sol > 0 else '#ff3366'
                )
            else:
                # In live override, enable ALL buttons for manual control
                # FIX: Was only enabling SELL, now enable BUY/SIDEBET too
                if live_override:
                    self.buy_button.config(state=tk.NORMAL)
                    self.sidebet_button.config(state=tk.NORMAL)
                    self.sell_button.config(state=tk.NORMAL)
                else:
                    self.sell_button.config(state=tk.DISABLED)
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
        """Callback for game end - AUDIT FIX Phase 2.6: Thread-safe UI updates"""
        self.log(f"Game ended. Final balance: {metrics.get('current_balance', 0):.4f} SOL")

        def _update_ui():
            """Execute UI updates on main thread"""
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
                if hasattr(self, 'replay_controller'):
                    self.replay_controller.load_next_game(next_file)
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

        # AUDIT FIX Phase 2.6: Marshal to UI thread
        self.ui_dispatcher.submit(_update_ui)

    # Phase 3.2: _load_next_game moved to ReplayController

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
            if hasattr(self, 'replay_controller'):
                self.replay_controller.load_game_file(files[0])
    
    def _handle_balance_changed(self, data):
        """Handle balance change (thread-safe via TkDispatcher)"""
        new_balance = data.get('new')
        if new_balance is not None:
            # Track P&L balance for later re-lock decision
            self.tracked_balance = new_balance

            # Marshal to UI thread via TkDispatcher (only update label when locked)
            if self.balance_locked:
                self.ui_dispatcher.submit(
                    lambda: self.balance_label.config(text=f"WALLET: {new_balance:.4f} SOL")
                )

    # ========================================================================
    # BALANCE LOCK / UNLOCK
    # ========================================================================

    def _toggle_balance_lock(self):
        """Handle lock/unlock button press."""
        if self.balance_locked:
            # Prompt unlock
            BalanceUnlockDialog(
                parent=self.root,
                current_balance=self.state.get('balance'),
                on_confirm=self._unlock_balance
            )
        else:
            # Prompt relock choice (manual vs tracked)
            BalanceRelockDialog(
                parent=self.root,
                manual_balance=self.state.get('balance'),
                tracked_balance=self.tracked_balance,
                on_choice=self._relock_balance
            )

    def _unlock_balance(self):
        """Allow manual balance editing."""
        self.balance_locked = False
        self.balance_lock_button.config(text="🔓")
        self._start_balance_edit()

    def _relock_balance(self, choice: str, new_balance: Optional[Decimal] = None):
        """Re-lock balance, applying user's chosen balance.

        When user sets a custom balance, this becomes the NEW BASELINE for P&L tracking.
        All future P&L calculations will be relative to this value.

        Args:
            choice: 'custom' (user entered value) or 'keep_manual' (canceled)
            new_balance: The balance value to set (required for 'custom')
        """
        if choice == 'custom' and new_balance is not None:
            # User entered a specific balance - apply it
            current = self.state.get('balance')
            delta = new_balance - current
            if delta != Decimal('0'):
                self.state.update_balance(delta, f"Manual balance set to {new_balance:.4f} SOL")

            # CRITICAL: Update the baseline for P&L tracking
            # This resets initial_balance, total_pnl, and peak_balance
            self.state.set_baseline_balance(
                new_balance,
                reason=f"User set balance to {new_balance:.4f} SOL"
            )

            # Update tracked balance to match the new baseline
            self.tracked_balance = new_balance
            logger.info(f"Balance baseline set to {new_balance:.4f} SOL (P&L tracking reset)")

        elif choice == 'revert_to_pnl':
            # Legacy: Bring balance back to tracked P&L
            delta = self.tracked_balance - self.state.get('balance')
            if delta != Decimal('0'):
                self.state.update_balance(delta, "Relock to P&L balance")

        # If keep_manual, current state balance remains and P&L resumes from there

        self.balance_locked = True
        self.manual_balance = None
        self.balance_lock_button.config(text="🔒")
        # Refresh label to the new balance value
        self.balance_label.config(text=f"WALLET: {self.state.get('balance'):.4f} SOL")

    def _start_balance_edit(self):
        """Replace balance label with inline editor."""
        # Remove current label widget
        self.balance_label.pack_forget()
        # Create inline editor
        self.balance_edit_entry = BalanceEditEntry(
            parent=self.balance_label.master,
            current_balance=self.state.get('balance'),
            on_save=self._apply_manual_balance,
            on_cancel=self._cancel_balance_edit
        )
        self.balance_edit_entry.pack(side=tk.RIGHT, padx=4)

    def _apply_manual_balance(self, new_balance: Decimal):
        """Apply user-entered manual balance and keep unlocked."""
        current = self.state.get('balance')
        delta = new_balance - current
        if delta != 0:
            self.state.update_balance(delta, "Manual balance override")
        self.manual_balance = new_balance
        # Restore label view
        self.balance_edit_entry.destroy()
        self.balance_label.config(text=f"WALLET: {new_balance:.4f} SOL")
        self.balance_label.pack(side=tk.RIGHT, padx=4)

    def _cancel_balance_edit(self):
        """Cancel manual edit and restore label."""
        if hasattr(self, 'balance_edit_entry'):
            self.balance_edit_entry.destroy()
        self.balance_label.pack(side=tk.RIGHT, padx=4)
    
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
            lambda: self.trading_controller.highlight_percentage_button(float(new_percentage)) if hasattr(self, 'trading_controller') else None
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

    # Phase 3.1: _check_bot_results moved to BotManager

    # ========================================================================
    # BET AMOUNT METHODS
    # ========================================================================

    # Phase 3.3: set_bet_amount, increment_bet_amount, clear_bet_amount, half_bet_amount, double_bet_amount, max_bet_amount, get_bet_amount moved to TradingController

    # ========================================================================
    # KEYBOARD SHORTCUTS
    # ========================================================================

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for common actions"""
        self.root.bind('<space>', lambda e: self.replay_controller.toggle_playback() if hasattr(self, 'replay_controller') else None)
        self.root.bind('b', lambda e: self.trading_controller.execute_buy() if self.buy_button['state'] != tk.DISABLED else None)
        self.root.bind('B', lambda e: self.trading_controller.execute_buy() if self.buy_button['state'] != tk.DISABLED else None)
        self.root.bind('s', lambda e: self.trading_controller.execute_sell() if self.sell_button['state'] != tk.DISABLED else None)
        self.root.bind('S', lambda e: self.trading_controller.execute_sell() if self.sell_button['state'] != tk.DISABLED else None)
        self.root.bind('d', lambda e: self.trading_controller.execute_sidebet() if self.sidebet_button['state'] != tk.DISABLED else None)
        self.root.bind('D', lambda e: self.trading_controller.execute_sidebet() if self.sidebet_button['state'] != tk.DISABLED else None)
        self.root.bind('r', lambda e: self.replay_controller.reset_game() if hasattr(self, 'replay_controller') else None)
        self.root.bind('R', lambda e: self.replay_controller.reset_game() if hasattr(self, 'replay_controller') else None)
        self.root.bind('<Left>', lambda e: self.replay_controller.step_backward() if hasattr(self, 'replay_controller') else None)
        self.root.bind('<Right>', lambda e: self.replay_controller.step_forward() if hasattr(self, 'replay_controller') else None)
        self.root.bind('<h>', lambda e: self.show_help())
        self.root.bind('<H>', lambda e: self.show_help())
        self.root.bind('l', lambda e: self.live_feed_controller.toggle_live_feed())
        self.root.bind('L', lambda e: self.live_feed_controller.toggle_live_feed())

        logger.info("Keyboard shortcuts configured (added 'L' for live feed)")

    # Phase 3.2: step_backward moved to ReplayController

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

    # Phase 3.2: load_file_dialog, toggle_play_pause, _toggle_recording, _open_recordings_folder moved to ReplayController
    # Phase 3.1: _toggle_bot_from_menu, _toggle_timing_overlay, _show_bot_config moved to BotManager

    # ========== TIMING METRICS (Phase 8.6) ==========

    # Phase 3.1: _show_timing_metrics moved to BotManager


    # Phase 3.1: _update_timing_metrics_display moved to BotManager

    # Phase 3.1: _update_timing_metrics_loop moved to BotManager

    # Phase 3.4: _toggle_live_feed_from_menu moved to LiveFeedController

    # ========== THEME MANAGEMENT (Phase 3: UI Theming) ==========

    def _change_theme(self, theme_name: str):
        """
        Switch UI theme and save preference
        Phase 3: UI Theming + Phase 5: Chart color coordination
        """
        try:
            import ttkbootstrap as ttk

            # Get the style from the root window
            # Since root is now ttk.Window, we can use its style
            if hasattr(self.root, 'style'):
                style = self.root.style
            else:
                # Fallback: create style object
                style = ttk.Style()

            # Apply the theme
            style.theme_use(theme_name)

            # Phase 5: Update chart colors to match new theme
            if hasattr(self, 'chart'):
                self.chart.update_theme_colors()

            # Save preference
            self._save_theme_preference(theme_name)

            logger.info(f"Theme changed to: {theme_name}")

            # Show toast notification
            if hasattr(self, 'toast_notification'):
                self.toast_notification.show(
                    f"Theme changed to: {theme_name.title()}",
                    duration=2000
                )
        except Exception as e:
            logger.error(f"Failed to change theme to {theme_name}: {e}")
            messagebox.showerror(
                "Theme Error",
                f"Failed to change theme:\n{str(e)}"
            )

    def _save_theme_preference(self, theme_name: str):
        """Save theme preference to config file"""
        try:
            config_dir = Path.home() / '.config' / 'replayer'
            config_dir.mkdir(parents=True, exist_ok=True)

            config_file = config_dir / 'ui_config.json'

            # Load existing config or create new
            config_data = {}
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config_data = json.load(f)

            # Update theme
            config_data['theme'] = theme_name

            # Save config
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)

            logger.debug(f"Saved theme preference: {theme_name}")
        except Exception as e:
            logger.error(f"Failed to save theme preference: {e}")

    @staticmethod
    def load_theme_preference() -> str:
        """Load saved theme preference, default to 'cyborg'"""
        try:
            config_file = Path.home() / '.config' / 'replayer' / 'ui_config.json'

            if config_file.exists():
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    theme = config_data.get('theme', 'cyborg')
                    logger.debug(f"Loaded theme preference: {theme}")
                    return theme
        except Exception as e:
            logger.debug(f"Could not load theme preference: {e}")

        # Default theme
        return 'cyborg'

    @staticmethod
    def load_ui_style_preference() -> str:
        """Load saved UI style preference, default to 'standard'"""
        try:
            config_file = Path.home() / '.config' / 'replayer' / 'ui_config.json'

            if config_file.exists():
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    style = config_data.get('ui_style', 'standard')
                    logger.debug(f"Loaded UI style preference: {style}")
                    return style
        except Exception as e:
            logger.debug(f"Could not load UI style preference: {e}")

        return 'standard'

    def _set_ui_style(self, style: str):
        """Set UI style and auto-restart the application"""
        try:
            config_dir = Path.home() / '.config' / 'replayer'
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / 'ui_config.json'

            config_data = {}
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config_data = json.load(f)

            config_data['ui_style'] = style

            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)

            logger.info(f"Saved UI style preference: {style}")

            # Ask user to confirm restart
            result = messagebox.askyesno(
                "Restart Application",
                f"UI style changed to '{style}'.\n\nRestart now to apply changes?"
            )

            if result:
                self._restart_application()

        except Exception as e:
            logger.error(f"Failed to save UI style preference: {e}")
            messagebox.showerror("Error", f"Failed to save UI style: {e}")

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

        # Phase 3.4: Delegate live feed cleanup to LiveFeedController
        self.live_feed_controller.cleanup()

        # Stop bot executor
        if self.bot_enabled:
            self.bot_executor.stop()
            self.bot_enabled = False

        # Stop UI dispatcher
        self.ui_dispatcher.stop()
