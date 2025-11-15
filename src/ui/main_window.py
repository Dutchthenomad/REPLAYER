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
from bot import BotInterface, BotController, list_strategies
from bot.async_executor import AsyncBotExecutor
from sources import WebSocketFeed

logger = logging.getLogger(__name__)

class MainWindow:
    """
    Main application window with integrated ReplayEngine
    """

    def __init__(self, root: tk.Tk, state, event_bus, config):
        self.root = root
        self.state = state
        self.event_bus = event_bus
        self.config = config

        # Initialize replay engine and trade manager
        self.replay_engine = ReplayEngine(state)
        self.trade_manager = TradeManager(state)

        # Initialize game queue for multi-game sessions
        recordings_dir = config.FILES['recordings_dir']
        self.game_queue = GameQueue(recordings_dir)
        self.multi_game_mode = False  # Programmatically controlled, not via UI

        # Initialize bot
        self.bot_interface = BotInterface(state, self.trade_manager)
        self.bot_controller = BotController(self.bot_interface, "conservative")
        self.bot_enabled = False

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

        # Start periodic bot result checker
        self._check_bot_results()

        logger.info("MainWindow initialized with ReplayEngine and async bot executor")
    
    def _create_ui(self):
        """Create UI matching the user's mockup design"""
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

        self.strategy_var = tk.StringVar(value="conservative")
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
                    self.live_feed_connected = True
                    self.log(f"✅ Live feed connected (Socket ID: {info.get('socketId', 'N/A')})")
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

            # Connect to feed
            self.live_feed.connect()

        except Exception as e:
            logger.error(f"Failed to enable live feed: {e}", exc_info=True)
            self.log(f"Failed to connect to live feed: {e}")
            self.toast.show(f"Live feed error: {e}", "error")
            self.live_feed = None
            self.live_feed_connected = False

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
        """Execute sell action using TradeManager"""
        result = self.trade_manager.execute_sell()

        if result['success']:
            pnl = result.get('pnl_sol', 0)
            pnl_pct = result.get('pnl_percent', 0)
            msg_type = "success" if pnl >= 0 else "error"
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
            self.log("🤖 Bot disabled")

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

    def shutdown(self):
        """Cleanup dispatcher resources during application shutdown."""
        if self.bot_enabled:
            self.bot_executor.stop()
            self.bot_enabled = False
        self.ui_dispatcher.stop()
