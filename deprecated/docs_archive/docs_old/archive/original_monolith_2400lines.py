#!/usr/bin/env python3
"""
Game-Accurate Replay Viewer for Rugs.fun
Mimics the actual game UI for realistic practice

FULLY REFACTORED VERSION - All bugs fixed, features implemented
"""

import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
from datetime import datetime
from pathlib import Path
import threading
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import logging
import os
from collections import deque

# ============================================================================
# CONSTANTS - All magic numbers extracted
# ============================================================================

# Financial Constants
INITIAL_BALANCE_SOL = Decimal('0.100')
DEFAULT_BET_SOL = Decimal('0.001')
MIN_BET_SOL = Decimal('0.001')
MAX_BET_SOL = Decimal('1.0')

# Game Rules
SIDEBET_MULTIPLIER = Decimal('5.0')
SIDEBET_WINDOW_TICKS = 40
SIDEBET_COOLDOWN_TICKS = 5
RUG_LIQUIDATION_PRICE = Decimal('0.02')

# Playback Settings
DEFAULT_PLAYBACK_DELAY = 0.25  # seconds
MIN_SPEED = 0.1
MAX_SPEED = 5.0
DEFAULT_SPEED = 1.0

# UI Settings
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
CHART_HEIGHT = 300
CONTROLS_HEIGHT = 150
STATS_PANEL_WIDTH = 700
TRADING_PANEL_WIDTH = 400

# Memory Management
MAX_POSITION_HISTORY = 1000
MAX_CHART_POINTS = 500

# File Settings
DEFAULT_RECORDINGS_DIR = os.getenv(
    'RUGS_RECORDINGS_DIR',
    str(Path.home() / 'rugs_recordings')
)

# Logging
LOG_FILE = 'game_replay_viewer.log'
LOG_LEVEL = logging.INFO

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

def setup_logging():
    """Configure logging system"""
    logging.basicConfig(
        level=LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================

class GamePhase(Enum):
    """Game phase enumeration"""
    UNKNOWN = "UNKNOWN"
    COOLDOWN = "COOLDOWN"
    PRESALE = "PRESALE"
    GAME_ACTIVATION = "GAME_ACTIVATION"
    ACTIVE_GAMEPLAY = "ACTIVE_GAMEPLAY"
    RUG_EVENT = "RUG_EVENT"
    RUG_EVENT_1 = "RUG_EVENT_1"

@dataclass
class Position:
    """Represents a trading position"""
    entry_price: Decimal
    amount: Decimal
    entry_time: float
    entry_tick: int
    status: str = "active"  # active, closed
    exit_price: Optional[Decimal] = None
    exit_time: Optional[float] = None
    exit_tick: Optional[int] = None
    pnl_sol: Decimal = Decimal('0.0')
    pnl_percent: Decimal = Decimal('0.0')

@dataclass
class SideBet:
    """Represents a side bet"""
    amount: Decimal
    placed_tick: int
    placed_price: Decimal
    multiplier: Decimal = SIDEBET_MULTIPLIER
    status: str = "active"  # active, won, lost
    resolved_tick: Optional[int] = None

@dataclass
class GameTick:
    """Represents a single game tick"""
    timestamp: str
    game_id: str
    tick: int
    price: Decimal
    phase: str
    active: bool
    rugged: bool
    cooldown_timer: int
    trade_count: int

    @classmethod
    def from_dict(cls, data: dict) -> 'GameTick':
        """Create GameTick from dictionary with validation"""
        try:
            return cls(
                timestamp=str(data.get('timestamp', '')),
                game_id=str(data.get('game_id', '')),
                tick=int(data.get('tick', 0)),
                price=Decimal(str(data.get('price', 1.0))),
                phase=str(data.get('phase', 'UNKNOWN')),
                active=bool(data.get('active', False)),
                rugged=bool(data.get('rugged', False)),
                cooldown_timer=int(data.get('cooldown_timer', 0)),
                trade_count=int(data.get('trade_count', 0))
            )
        except (ValueError, InvalidOperation) as e:
            logger.error(f"Failed to parse GameTick: {e}, data: {data}")
            raise ValueError(f"Invalid game tick data: {e}")

@dataclass
class ChartPoint:
    """Represents a point on the price chart"""
    tick: int
    price: Decimal
    action: Optional[str] = None  # BUY, SELL, SIDE, None
    color: Optional[str] = None

# ============================================================================
# TOAST NOTIFICATION WIDGET
# ============================================================================

class ToastNotification:
    """Toast notification system for temporary messages"""

    def __init__(self, parent):
        self.parent = parent
        self.active_toasts = []

    def show(self, message: str, msg_type: str = "info", duration: int = 3000):
        """
        Show a toast notification

        Args:
            message: Message to display
            msg_type: Type of message (info, warning, error, success)
            duration: Duration in milliseconds
        """
        # Create toast window
        toast = tk.Toplevel(self.parent)
        toast.withdraw()
        toast.overrideredirect(True)

        # Color scheme based on type
        colors = {
            'info': ('#3366ff', '#ffffff'),
            'warning': ('#ffcc00', '#000000'),
            'error': ('#ff3366', '#ffffff'),
            'success': ('#00ff88', '#000000')
        }
        bg_color, fg_color = colors.get(msg_type, colors['info'])

        # Create label
        label = tk.Label(
            toast,
            text=message,
            bg=bg_color,
            fg=fg_color,
            font=('Arial', 10, 'bold'),
            padx=20,
            pady=10
        )
        label.pack()

        # Position toast
        toast.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - toast.winfo_width()) // 2
        y = self.parent.winfo_y() + 50 + len(self.active_toasts) * 60
        toast.geometry(f"+{x}+{y}")
        toast.deiconify()

        self.active_toasts.append(toast)

        # Auto-dismiss
        def dismiss():
            if toast in self.active_toasts:
                self.active_toasts.remove(toast)
            toast.destroy()

        toast.after(duration, dismiss)

        # Log the message
        log_methods = {
            'info': logger.info,
            'warning': logger.warning,
            'error': logger.error,
            'success': logger.info
        }
        log_methods.get(msg_type, logger.info)(f"Toast: {message}")

# ============================================================================
# BOT INTERFACE - Programmatic Control API
# ============================================================================

class BotInterface:
    """
    Programmatic interface for bot control of the replay viewer.

    Provides methods for bots to:
    - Execute actions (BUY, SELL, SIDE, WAIT)
    - Observe game state
    - Get auxiliary information
    - Receive detailed feedback on action results

    All actions respect game rules and return detailed result dictionaries.
    """

    def __init__(self, viewer: 'GameUIReplayViewer'):
        """
        Initialize bot interface

        Args:
            viewer: The GameUIReplayViewer instance to control
        """
        self.viewer = viewer
        logger.info("BotInterface initialized")

    def bot_execute_action(self, action_type: str, amount: Optional[Decimal] = None) -> Dict:
        """
        Execute an action on behalf of the bot

        Args:
            action_type: One of "BUY", "SELL", "SIDE", "WAIT"
            amount: Bet amount in SOL (required for BUY and SIDE, ignored for SELL and WAIT)

        Returns:
            {
                'success': bool,           # Whether action succeeded
                'action': str,             # Action type executed
                'amount': Decimal,         # Amount used (None for WAIT/SELL)
                'price': Decimal,          # Current price
                'tick': int,               # Current tick
                'phase': str,              # Current phase
                'new_balance': Decimal,    # Wallet balance after action
                'reason': str,             # Success message or error reason
                'reward': Decimal,         # Immediate reward from this action
                'position': Optional[Dict],# Active position info (if any)
                'sidebet': Optional[Dict]  # Active sidebet info (if any)
            }
        """
        with self.viewer.state_lock:
            # Validate game state
            if not self.viewer.current_game or self.viewer.current_tick_index >= len(self.viewer.current_game):
                return self._error_result("No game loaded or game ended", action_type)

            tick = self.viewer.current_game[self.viewer.current_tick_index]
            prev_balance = self.viewer.wallet_balance

            # Execute action based on type
            if action_type == "WAIT":
                return self._execute_wait(tick, prev_balance)
            elif action_type == "BUY":
                return self._execute_buy(tick, amount, prev_balance)
            elif action_type == "SELL":
                return self._execute_sell(tick, prev_balance)
            elif action_type == "SIDE":
                return self._execute_sidebet(tick, amount, prev_balance)
            else:
                return self._error_result(f"Invalid action type: {action_type}", action_type)

    def _execute_wait(self, tick: GameTick, prev_balance: Decimal) -> Dict:
        """Execute WAIT action (do nothing)"""
        return {
            'success': True,
            'action': 'WAIT',
            'amount': None,
            'price': tick.price,
            'tick': tick.tick,
            'phase': tick.phase,
            'new_balance': self.viewer.wallet_balance,
            'reason': 'Waited (no action taken)',
            'reward': Decimal('0.0'),
            'position': self._get_position_info(),
            'sidebet': self._get_sidebet_info()
        }

    def _execute_buy(self, tick: GameTick, amount: Optional[Decimal], prev_balance: Decimal) -> Dict:
        """Execute BUY action"""
        # Validate amount provided
        if amount is None:
            return self._error_result("BUY requires amount parameter", "BUY")

        # Validate amount value
        try:
            amount = Decimal(str(amount))
        except (ValueError, InvalidOperation):
            return self._error_result(f"Invalid amount: {amount}", "BUY")

        if amount < MIN_BET_SOL:
            return self._error_result(f"Amount {amount} below minimum {MIN_BET_SOL} SOL", "BUY")

        if amount > MAX_BET_SOL:
            return self._error_result(f"Amount {amount} exceeds maximum {MAX_BET_SOL} SOL", "BUY")

        if amount > self.viewer.wallet_balance:
            return self._error_result(
                f"Insufficient balance: have {self.viewer.wallet_balance:.4f}, need {amount} SOL",
                "BUY"
            )

        # Validate game is active
        if not tick.active:
            return self._error_result("Game not active yet", "BUY")

        # Validate phase
        if tick.phase in ["COOLDOWN", "RUG_EVENT", "RUG_EVENT_1", "UNKNOWN"]:
            return self._error_result(f"Cannot buy in {tick.phase} phase", "BUY")

        # Execute buy via viewer (temporarily set bet amount)
        old_bet = self.viewer.bet_entry.get()
        self.viewer.bet_entry.delete(0, tk.END)
        self.viewer.bet_entry.insert(0, str(amount))

        # Call existing buy logic
        self.viewer.execute_buy()

        # Restore old bet
        self.viewer.bet_entry.delete(0, tk.END)
        self.viewer.bet_entry.insert(0, old_bet)

        # Calculate reward (balance change)
        balance_change = self.viewer.wallet_balance - prev_balance

        return {
            'success': True,
            'action': 'BUY',
            'amount': amount,
            'price': tick.price,
            'tick': tick.tick,
            'phase': tick.phase,
            'new_balance': self.viewer.wallet_balance,
            'reason': f'Bought {amount} SOL at {tick.price:.4f}x',
            'reward': balance_change,  # Should be -amount (spent SOL)
            'position': self._get_position_info(),
            'sidebet': self._get_sidebet_info()
        }

    def _execute_sell(self, tick: GameTick, prev_balance: Decimal) -> Dict:
        """Execute SELL action"""
        # Validate position exists
        if not self.viewer.active_position or self.viewer.active_position.status != "active":
            return self._error_result("No active position to sell", "SELL")

        # Store position info before selling
        entry_price = self.viewer.active_position.entry_price
        position_amount = self.viewer.active_position.amount

        # Execute sell
        self.viewer.execute_sell()

        # Calculate reward (P&L from this trade)
        balance_change = self.viewer.wallet_balance - prev_balance

        return {
            'success': True,
            'action': 'SELL',
            'amount': position_amount,
            'price': tick.price,
            'tick': tick.tick,
            'phase': tick.phase,
            'new_balance': self.viewer.wallet_balance,
            'reason': f'Sold {position_amount} SOL at {tick.price:.4f}x (entry: {entry_price:.4f}x)',
            'reward': balance_change,  # P&L
            'position': None,  # Position closed
            'sidebet': self._get_sidebet_info()
        }

    def _execute_sidebet(self, tick: GameTick, amount: Optional[Decimal], prev_balance: Decimal) -> Dict:
        """Execute SIDE BET action"""
        # Validate amount provided
        if amount is None:
            return self._error_result("SIDE requires amount parameter", "SIDE")

        # Validate amount value
        try:
            amount = Decimal(str(amount))
        except (ValueError, InvalidOperation):
            return self._error_result(f"Invalid amount: {amount}", "SIDE")

        if amount < MIN_BET_SOL:
            return self._error_result(f"Amount {amount} below minimum {MIN_BET_SOL} SOL", "SIDE")

        if amount > MAX_BET_SOL:
            return self._error_result(f"Amount {amount} exceeds maximum {MAX_BET_SOL} SOL", "SIDE")

        if amount > self.viewer.wallet_balance:
            return self._error_result(
                f"Insufficient balance: have {self.viewer.wallet_balance:.4f}, need {amount} SOL",
                "SIDE"
            )

        # Validate game is active
        if not tick.active:
            return self._error_result("Game not active yet", "SIDE")

        # Validate phase
        if tick.phase in ["COOLDOWN", "RUG_EVENT", "RUG_EVENT_1", "UNKNOWN"]:
            return self._error_result(f"Cannot place sidebet in {tick.phase} phase", "SIDE")

        # Check if sidebet already active
        if self.viewer.active_sidebet and self.viewer.active_sidebet.status == "active":
            return self._error_result("Sidebet already active", "SIDE")

        # Check cooldown
        if self.viewer.last_sidebet_resolved_tick is not None:
            ticks_since_resolution = tick.tick - self.viewer.last_sidebet_resolved_tick
            if ticks_since_resolution <= SIDEBET_COOLDOWN_TICKS:
                return self._error_result(
                    f"Sidebet cooldown: {SIDEBET_COOLDOWN_TICKS - ticks_since_resolution} ticks remaining",
                    "SIDE"
                )

        # Execute sidebet via viewer
        old_bet = self.viewer.bet_entry.get()
        self.viewer.bet_entry.delete(0, tk.END)
        self.viewer.bet_entry.insert(0, str(amount))

        self.viewer.execute_sidebet()

        # Restore old bet
        self.viewer.bet_entry.delete(0, tk.END)
        self.viewer.bet_entry.insert(0, old_bet)

        # Calculate reward (balance change - should be negative)
        balance_change = self.viewer.wallet_balance - prev_balance

        return {
            'success': True,
            'action': 'SIDE',
            'amount': amount,
            'price': tick.price,
            'tick': tick.tick,
            'phase': tick.phase,
            'new_balance': self.viewer.wallet_balance,
            'reason': f'Placed sidebet: {amount} SOL (potential win: {amount * SIDEBET_MULTIPLIER} SOL)',
            'reward': balance_change,  # Should be -amount
            'position': self._get_position_info(),
            'sidebet': self._get_sidebet_info()
        }

    def _error_result(self, reason: str, action_type: str) -> Dict:
        """Create error result dictionary"""
        tick = None
        if self.viewer.current_game and self.viewer.current_tick_index < len(self.viewer.current_game):
            tick = self.viewer.current_game[self.viewer.current_tick_index]

        return {
            'success': False,
            'action': action_type,
            'amount': None,
            'price': tick.price if tick else Decimal('0.0'),
            'tick': tick.tick if tick else 0,
            'phase': tick.phase if tick else 'UNKNOWN',
            'new_balance': self.viewer.wallet_balance,
            'reason': reason,
            'reward': Decimal('-0.05'),  # Small penalty for invalid action
            'position': self._get_position_info(),
            'sidebet': self._get_sidebet_info()
        }

    def _get_position_info(self) -> Optional[Dict]:
        """Get active position information"""
        if not self.viewer.active_position or self.viewer.active_position.status != "active":
            return None

        pos = self.viewer.active_position

        # Calculate current P&L
        if self.viewer.current_game and self.viewer.current_tick_index < len(self.viewer.current_game):
            tick = self.viewer.current_game[self.viewer.current_tick_index]
            price_change = tick.price / pos.entry_price - 1
            current_pnl = pos.amount * price_change
            current_pnl_percent = price_change * 100
        else:
            current_pnl = Decimal('0.0')
            current_pnl_percent = Decimal('0.0')

        return {
            'entry_price': float(pos.entry_price),
            'amount': float(pos.amount),
            'entry_tick': pos.entry_tick,
            'current_pnl_sol': float(current_pnl),
            'current_pnl_percent': float(current_pnl_percent)
        }

    def _get_sidebet_info(self) -> Optional[Dict]:
        """Get active sidebet information"""
        if not self.viewer.active_sidebet or self.viewer.active_sidebet.status != "active":
            return None

        sb = self.viewer.active_sidebet

        # Calculate ticks remaining
        if self.viewer.current_game and self.viewer.current_tick_index < len(self.viewer.current_game):
            tick = self.viewer.current_game[self.viewer.current_tick_index]
            expiry_tick = sb.placed_tick + SIDEBET_WINDOW_TICKS
            ticks_remaining = expiry_tick - tick.tick
        else:
            ticks_remaining = 0

        return {
            'amount': float(sb.amount),
            'placed_tick': sb.placed_tick,
            'placed_price': float(sb.placed_price),
            'ticks_remaining': ticks_remaining,
            'potential_payout': float(sb.amount * SIDEBET_MULTIPLIER)
        }

    def bot_get_observation(self) -> Optional[Dict]:
        """
        Get current game state as observation for bot

        Returns:
            {
                'current_state': {
                    'price': float,
                    'tick': int,
                    'phase': str,
                    'active': bool,
                    'rugged': bool,
                    'cooldown_timer': int,
                    'trade_count': int
                },
                'wallet': {
                    'balance': float,
                    'starting_balance': float,
                    'session_pnl': float
                },
                'position': Optional[Dict],  # From _get_position_info()
                'sidebet': Optional[Dict],   # From _get_sidebet_info()
                'game_info': {
                    'game_id': str,
                    'total_ticks': int,
                    'progress': float  # 0.0 to 1.0
                }
            }

            Returns None if no game loaded
        """
        if not self.viewer.current_game or self.viewer.current_tick_index >= len(self.viewer.current_game):
            return None

        tick = self.viewer.current_game[self.viewer.current_tick_index]

        return {
            'current_state': {
                'price': float(tick.price),
                'tick': tick.tick,
                'phase': tick.phase,
                'active': tick.active,
                'rugged': tick.rugged,
                'cooldown_timer': tick.cooldown_timer,
                'trade_count': tick.trade_count
            },
            'wallet': {
                'balance': float(self.viewer.wallet_balance),
                'starting_balance': float(self.viewer.initial_balance),
                'session_pnl': float(self.viewer.session_pnl)
            },
            'position': self._get_position_info(),
            'sidebet': self._get_sidebet_info(),
            'game_info': {
                'game_id': self.viewer.current_game_id or 'Unknown',
                'total_ticks': len(self.viewer.current_game),
                'progress': self.viewer.current_tick_index / len(self.viewer.current_game)
            }
        }

    def bot_get_info(self) -> Dict:
        """
        Get auxiliary information about game state and bot capabilities

        Returns:
            {
                'valid_actions': List[str],  # Actions that can be taken now
                'game_loaded': bool,
                'game_ended': bool,
                'can_buy': bool,
                'can_sell': bool,
                'can_sidebet': bool,
                'constraints': {
                    'min_bet': float,
                    'max_bet': float,
                    'sidebet_multiplier': float,
                    'sidebet_window_ticks': int,
                    'sidebet_cooldown_ticks': int
                }
            }
        """
        # Check if game is valid
        game_loaded = self.viewer.current_game is not None
        game_ended = False
        if game_loaded:
            game_ended = self.viewer.current_tick_index >= len(self.viewer.current_game)

        # Determine valid actions
        valid_actions = ['WAIT']  # WAIT is always valid
        can_buy = False
        can_sell = False
        can_sidebet = False

        if game_loaded and not game_ended:
            tick = self.viewer.current_game[self.viewer.current_tick_index]

            # Can buy if game is active, in valid phase, and have balance
            if tick.active and tick.phase not in ["COOLDOWN", "RUG_EVENT", "RUG_EVENT_1", "UNKNOWN"]:
                if self.viewer.wallet_balance >= MIN_BET_SOL:
                    can_buy = True
                    valid_actions.append('BUY')

            # Can sell if have active position
            if self.viewer.active_position and self.viewer.active_position.status == "active":
                can_sell = True
                valid_actions.append('SELL')

            # Can sidebet if game active, no active sidebet, not in cooldown, valid phase
            if tick.active and tick.phase not in ["COOLDOWN", "RUG_EVENT", "RUG_EVENT_1", "UNKNOWN"]:
                if not (self.viewer.active_sidebet and self.viewer.active_sidebet.status == "active"):
                    # Check cooldown
                    in_cooldown = False
                    if self.viewer.last_sidebet_resolved_tick is not None:
                        ticks_since_resolution = tick.tick - self.viewer.last_sidebet_resolved_tick
                        in_cooldown = ticks_since_resolution <= SIDEBET_COOLDOWN_TICKS

                    if not in_cooldown and self.viewer.wallet_balance >= MIN_BET_SOL:
                        can_sidebet = True
                        valid_actions.append('SIDE')

        return {
            'valid_actions': valid_actions,
            'game_loaded': game_loaded,
            'game_ended': game_ended,
            'can_buy': can_buy,
            'can_sell': can_sell,
            'can_sidebet': can_sidebet,
            'constraints': {
                'min_bet': float(MIN_BET_SOL),
                'max_bet': float(MAX_BET_SOL),
                'sidebet_multiplier': float(SIDEBET_MULTIPLIER),
                'sidebet_window_ticks': SIDEBET_WINDOW_TICKS,
                'sidebet_cooldown_ticks': SIDEBET_COOLDOWN_TICKS
            }
        }

# ============================================================================
# BOT CONTROLLER - Decision Making Logic
# ============================================================================

class BotController:
    """
    Controls bot decision-making during replay playback.

    Wraps BotInterface and implements decision logic.
    Generates human-readable reasoning for each action.
    """

    def __init__(self, bot_interface: BotInterface, strategy: str = "conservative"):
        """
        Initialize bot controller

        Args:
            bot_interface: BotInterface instance for executing actions
            strategy: Strategy name ("conservative", "aggressive", "sidebet")
        """
        self.bot = bot_interface
        self.strategy = strategy
        self.last_action = None
        self.last_reasoning = ""

        logger.info(f"BotController initialized with {strategy} strategy")

    def decide_action(self) -> tuple:
        """
        Decide next action based on strategy

        Returns:
            (action_type, amount, reasoning)
        """
        obs = self.bot.bot_get_observation()
        info = self.bot.bot_get_info()

        if not obs:
            return ("WAIT", None, "No game state available")

        current_state = obs['current_state']
        position = obs['position']
        sidebet = obs['sidebet']
        wallet = obs['wallet']

        # Conservative strategy
        if self.strategy == "conservative":
            return self._conservative_strategy(current_state, position, sidebet, wallet, info)
        elif self.strategy == "aggressive":
            return self._aggressive_strategy(current_state, position, sidebet, wallet, info)
        elif self.strategy == "sidebet":
            return self._sidebet_strategy(current_state, position, sidebet, wallet, info)
        else:
            return ("WAIT", None, "Unknown strategy")

    def _conservative_strategy(self, state, position, sidebet, wallet, info) -> tuple:
        """
        Conservative strategy: Buy low, sell on modest profit, avoid risk
        """
        price = state['price']
        tick = state['tick']
        phase = state['phase']
        balance = wallet['balance']

        # No position - look to buy at good price
        if position is None and info['can_buy']:
            if price < 1.5 and balance >= Decimal('0.005'):
                return ("BUY", Decimal('0.005'),
                       f"Entry at {price:.2f}x (low price, good entry point)")

        # Have position - manage it
        if position is not None and info['can_sell']:
            pnl_pct = position['current_pnl_percent']

            # Take profit at 20%
            if pnl_pct > 20:
                return ("SELL", None,
                       f"Take profit at +{pnl_pct:.1f}% (target: 20%)")

            # Cut losses at -15%
            if pnl_pct < -15:
                return ("SELL", None,
                       f"Stop loss at {pnl_pct:.1f}% (limit: -15%)")

            # Emergency exit if price too high (bubble risk)
            if price > 10:
                return ("SELL", None,
                       f"Exit at {price:.2f}x (bubble risk, take gains)")

        # Place sidebet conservatively
        if sidebet is None and info['can_sidebet']:
            # Only bet if we think rug is coming (late game)
            if tick > 100 and balance >= Decimal('0.002'):
                return ("SIDE", Decimal('0.002'),
                       f"Sidebet at tick {tick} (late game rug risk)")

        return ("WAIT", None, f"Holding position (Price: {price:.2f}x, P&L: {position['current_pnl_percent']:.1f}%)" if position else f"Waiting for entry (Price: {price:.2f}x too high)")

    def _aggressive_strategy(self, state, position, sidebet, wallet, info) -> tuple:
        """
        Aggressive strategy: Buy often, hold for bigger gains, take risks
        """
        price = state['price']
        balance = wallet['balance']

        # Buy aggressively if no position
        if position is None and info['can_buy']:
            if price < 3.0 and balance >= Decimal('0.010'):
                return ("BUY", Decimal('0.010'),
                       f"Aggressive entry at {price:.2f}x")

        # Hold for bigger gains
        if position is not None and info['can_sell']:
            pnl_pct = position['current_pnl_percent']

            # Only sell at 50% profit
            if pnl_pct > 50:
                return ("SELL", None,
                       f"Big profit exit at +{pnl_pct:.1f}%")

            # Wider stop loss
            if pnl_pct < -30:
                return ("SELL", None,
                       f"Stop loss at {pnl_pct:.1f}%")

        return ("WAIT", None, f"Holding for bigger gains (P&L: {position['current_pnl_percent']:.1f}%)" if position else f"Waiting")

    def _sidebet_strategy(self, state, position, sidebet, wallet, info) -> tuple:
        """
        Sidebet-focused strategy: Prioritize sidebet testing
        """
        tick = state['tick']
        price = state['price']
        balance = wallet['balance']

        # Place sidebets frequently for testing
        if sidebet is None and info['can_sidebet']:
            if balance >= Decimal('0.003'):
                return ("SIDE", Decimal('0.003'),
                       f"Testing sidebet at tick {tick}")

        # Also trade normally
        if position is None and info['can_buy']:
            if price < 2.0 and balance >= Decimal('0.005'):
                return ("BUY", Decimal('0.005'),
                       f"Entry at {price:.2f}x")

        if position is not None and info['can_sell']:
            if position['current_pnl_percent'] > 30:
                return ("SELL", None, "Quick profit")

        return ("WAIT", None, f"Waiting for sidebet opportunity")

    def execute_step(self) -> Dict:
        """
        Execute one decision cycle

        Returns:
            Result dictionary from bot_execute_action
        """
        action_type, amount, reasoning = self.decide_action()

        self.last_action = action_type
        self.last_reasoning = reasoning

        result = self.bot.bot_execute_action(action_type, amount)

        logger.info(f"Bot action: {action_type} - {reasoning} - Success: {result['success']}")

        return result

# ============================================================================
# MAIN APPLICATION CLASS
# ============================================================================

class GameUIReplayViewer:
    """
    Main replay viewer application

    Provides a practice environment for Rugs.fun trading using historical
    game recordings. Features realistic UI, trading mechanics, and statistics.
    """

    def __init__(self, root):
        """Initialize the replay viewer"""
        self.root = root
        self.root.title("Rugs.fun - Practice Mode (ENHANCED)")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg='#0a0a0a')

        # Thread safety
        self.state_lock = threading.Lock()

        # Game state (protected by state_lock)
        self.current_game: Optional[List[GameTick]] = None
        self.current_game_id: Optional[str] = None
        self.current_tick_index = 0
        self.is_playing = False
        self.playback_speed = DEFAULT_SPEED

        # Player state (uses Decimal for precision)
        self.wallet_balance = INITIAL_BALANCE_SOL
        self.initial_balance = INITIAL_BALANCE_SOL
        self.bet_amount = DEFAULT_BET_SOL
        self.active_position: Optional[Position] = None
        self.active_sidebet: Optional[SideBet] = None
        self.last_sidebet_resolved_tick: Optional[int] = None

        # History with memory management
        self.position_history: deque = deque(maxlen=MAX_POSITION_HISTORY)

        # Performance tracking
        self.session_pnl = Decimal('0.0')
        self.games_played = 0
        self.trades_won = 0
        self.trades_lost = 0
        self.best_trade = Decimal('0.0')
        self.worst_trade = Decimal('0.0')
        self.current_streak = 0

        # Chart data with memory management
        self.chart_points: deque = deque(maxlen=MAX_CHART_POINTS)

        # Toast notification system
        self.toast = ToastNotification(self.root)

        # Bot Mode (NEW for Checkpoint 1B)
        self.bot_mode_enabled = False
        self.bot_interface = BotInterface(self)
        self.bot_controller: Optional[BotController] = None
        self.bot_strategy = "conservative"
        self.bot_action_complete = threading.Event()  # Synchronize bot actions
        self.bot_action_complete.set()  # Initially ready

        # Setup UI
        self.setup_game_ui()

        # Keyboard shortcuts
        self.setup_keyboard_shortcuts()

        # Threading for playback
        self.playback_thread = None
        self.stop_event = threading.Event()

        # Game queue
        self.pending_games = []

        logger.info("GameUIReplayViewer initialized")

    def setup_game_ui(self):
        """Setup UI to mimic the actual game interface"""

        # Define game-like colors
        self.colors = {
            'bg': '#0a0a0a',
            'panel': '#1a1a1a',
            'text': '#ffffff',
            'green': '#00ff88',
            'red': '#ff3366',
            'yellow': '#ffcc00',
            'blue': '#3366ff',
            'gray': '#666666'
        }

        # Main container
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Top section - Game display and controls
        top_section = tk.Frame(main_container, bg=self.colors['bg'])
        top_section.pack(fill=tk.BOTH, expand=True)

        # Left panel - Main game display
        left_panel = tk.Frame(top_section, bg=self.colors['panel'], relief=tk.FLAT, bd=2)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self._setup_game_display(left_panel)

        # Right panel - Trading interface
        right_panel = tk.Frame(top_section, bg=self.colors['panel'], relief=tk.FLAT, bd=2, width=TRADING_PANEL_WIDTH)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_panel.pack_propagate(False)

        self._setup_trading_interface(right_panel)

        # Bottom section - Controls and stats
        bottom_section = tk.Frame(main_container, bg=self.colors['bg'], height=CONTROLS_HEIGHT)
        bottom_section.pack(fill=tk.X, pady=(10, 0))
        bottom_section.pack_propagate(False)

        self._setup_controls_and_stats(bottom_section)

    def _setup_game_display(self, parent):
        """Setup the main game display area"""

        # Game header
        header_frame = tk.Frame(parent, bg=self.colors['panel'], height=80)
        header_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
        header_frame.pack_propagate(False)

        # Price display
        price_container = tk.Frame(header_frame, bg=self.colors['panel'])
        price_container.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(price_container, text="PRICE",
                fg=self.colors['gray'], bg=self.colors['panel'],
                font=('Arial', 10)).pack(anchor=tk.W)

        self.price_label = tk.Label(price_container, text="1.0000x",
                                   fg=self.colors['green'], bg=self.colors['panel'],
                                   font=('Arial', 36, 'bold'))
        self.price_label.pack(anchor=tk.W)

        # Phase and status
        status_container = tk.Frame(header_frame, bg=self.colors['panel'])
        status_container.pack(side=tk.RIGHT, fill=tk.Y, padx=20)

        self.phase_label = tk.Label(status_container, text="WAITING FOR GAME",
                                    fg=self.colors['yellow'], bg=self.colors['panel'],
                                    font=('Arial', 12, 'bold'))
        self.phase_label.pack(anchor=tk.E, pady=(5, 0))

        self.cooldown_label = tk.Label(status_container, text="",
                                       fg=self.colors['blue'], bg=self.colors['panel'],
                                       font=('Arial', 10))
        self.cooldown_label.pack(anchor=tk.E)

        # Chart area
        chart_frame = tk.Frame(parent, bg='#0f0f0f', relief=tk.SUNKEN, bd=2, height=CHART_HEIGHT)
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        chart_frame.pack_propagate(False)

        # Price chart canvas
        self.chart_canvas = tk.Canvas(chart_frame, bg='#0f0f0f', highlightthickness=0)
        self.chart_canvas.pack(fill=tk.BOTH, expand=True)

        # Game info panel
        info_frame = tk.Frame(parent, bg=self.colors['panel'], height=100)
        info_frame.pack(fill=tk.X, padx=20, pady=(10, 20))

        info_container = tk.Frame(info_frame, bg=self.colors['panel'])
        info_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tick_info_label = tk.Label(info_container,
                                        text="Tick: 0 | Trades: 0",
                                        fg=self.colors['gray'], bg=self.colors['panel'],
                                        font=('Arial', 10))
        self.tick_info_label.pack(side=tk.LEFT)

        self.game_id_label = tk.Label(info_container,
                                      text="Game: Loading...",
                                      fg=self.colors['gray'], bg=self.colors['panel'],
                                      font=('Arial', 10))
        self.game_id_label.pack(side=tk.RIGHT)

    def _setup_trading_interface(self, parent):
        """Setup the trading interface"""

        container = tk.Frame(parent, bg=self.colors['panel'])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        tk.Label(container, text="TRADING PANEL",
                fg=self.colors['text'], bg=self.colors['panel'],
                font=('Arial', 14, 'bold')).pack(pady=(0, 20))

        # Wallet display
        self._create_wallet_display(container)

        # Bet amount input
        self._create_bet_input(container)

        # Trading buttons
        self._create_trading_buttons(container)

        # Position display
        self._create_position_display(container)

    def _create_wallet_display(self, parent):
        """Create wallet balance display"""
        wallet_frame = tk.Frame(parent, bg='#2a2a2a', relief=tk.RAISED, bd=1)
        wallet_frame.pack(fill=tk.X, pady=(0, 20))

        wallet_container = tk.Frame(wallet_frame, bg='#2a2a2a')
        wallet_container.pack(fill=tk.X, padx=15, pady=10)

        tk.Label(wallet_container, text="WALLET BALANCE",
                fg=self.colors['gray'], bg='#2a2a2a',
                font=('Arial', 9)).pack(anchor=tk.W)

        self.wallet_label = tk.Label(wallet_container,
                                    text=f"{self.wallet_balance:.4f} SOL",
                                    fg=self.colors['green'], bg='#2a2a2a',
                                    font=('Arial', 18, 'bold'))
        self.wallet_label.pack(anchor=tk.W)

    def _create_bet_input(self, parent):
        """Create bet amount input controls"""
        bet_frame = tk.Frame(parent, bg=self.colors['panel'])
        bet_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(bet_frame, text="BET AMOUNT",
                fg=self.colors['gray'], bg=self.colors['panel'],
                font=('Arial', 9)).pack(anchor=tk.W, pady=(0, 5))

        input_container = tk.Frame(bet_frame, bg='#2a2a2a', relief=tk.RAISED, bd=1)
        input_container.pack(fill=tk.X)

        self.bet_entry = tk.Entry(input_container,
                                 bg='#1a1a1a', fg=self.colors['text'],
                                 font=('Arial', 14, 'bold'),
                                 bd=0, insertbackground=self.colors['text'],
                                 justify=tk.RIGHT)
        self.bet_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=8)
        self.bet_entry.insert(0, str(DEFAULT_BET_SOL))

        tk.Label(input_container, text="SOL",
                fg=self.colors['gray'], bg='#2a2a2a',
                font=('Arial', 12)).pack(side=tk.RIGHT, padx=10)

        # Quick bet buttons (increment mode)
        quick_bet_frame = tk.Frame(parent, bg=self.colors['panel'])
        quick_bet_frame.pack(fill=tk.X, pady=(0, 20))

        # Clear button (X)
        clear_btn = tk.Button(quick_bet_frame, text="X",
                            bg='#ff3366', fg='#ffffff',
                            font=('Arial', 9, 'bold'), bd=1, relief=tk.RAISED,
                            command=self.clear_bet_amount)
        clear_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        # Increment buttons
        for amount in [Decimal('0.001'), Decimal('0.005'), Decimal('0.010'), Decimal('0.025')]:
            btn = tk.Button(quick_bet_frame, text=f"+{amount}",
                          bg='#2a2a2a', fg=self.colors['green'],
                          font=('Arial', 9), bd=1, relief=tk.RAISED,
                          command=lambda a=amount: self.increment_bet_amount(a))
            btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

    def _create_trading_buttons(self, parent):
        """Create trading action buttons"""
        buttons_frame = tk.Frame(parent, bg=self.colors['panel'])
        buttons_frame.pack(fill=tk.X, pady=(0, 15))

        # BUY button
        self.buy_button = tk.Button(buttons_frame, text="BUY [B]",
                                   bg=self.colors['green'], fg='#000000',
                                   font=('Arial', 14, 'bold'),
                                   bd=0, relief=tk.FLAT,
                                   activebackground='#00cc66',
                                   height=2,
                                   command=self.execute_buy)
        self.buy_button.pack(fill=tk.X, pady=(0, 5))

        # SELL button
        self.sell_button = tk.Button(buttons_frame, text="SELL [S]",
                                    bg=self.colors['red'], fg='#ffffff',
                                    font=('Arial', 14, 'bold'),
                                    bd=0, relief=tk.FLAT,
                                    activebackground='#cc0044',
                                    height=2,
                                    state=tk.DISABLED,
                                    command=self.execute_sell)
        self.sell_button.pack(fill=tk.X, pady=(0, 5))

        # SIDE BET button
        self.sidebet_button = tk.Button(buttons_frame, text="SIDE BET [D]",
                                       bg=self.colors['yellow'], fg='#000000',
                                       font=('Arial', 14, 'bold'),
                                       bd=0, relief=tk.FLAT,
                                       activebackground='#cc9900',
                                       height=2,
                                       command=self.execute_sidebet)
        self.sidebet_button.pack(fill=tk.X)

        # Bot Mode Section (Visible in Trading Panel)
        bot_section = tk.Frame(parent, bg=self.colors['panel'])
        bot_section.pack(fill=tk.X, pady=(20, 0))

        tk.Label(bot_section, text="BOT MODE",
                fg=self.colors['text'], bg=self.colors['panel'],
                font=('Arial', 12, 'bold')).pack(pady=(0, 10))

        # Bot toggle button
        self.bot_mode_button = tk.Button(bot_section, text="🤖 ENABLE BOT",
                                        bg='#2a2a2a', fg=self.colors['blue'],
                                        font=('Arial', 12, 'bold'),
                                        bd=0, relief=tk.FLAT,
                                        height=2,
                                        command=self.toggle_bot_mode)
        self.bot_mode_button.pack(fill=tk.X, pady=(0, 10))

        # Strategy selector
        strategy_frame = tk.Frame(bot_section, bg=self.colors['panel'])
        strategy_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(strategy_frame, text="Strategy:",
                fg=self.colors['gray'], bg=self.colors['panel'],
                font=('Arial', 9)).pack(anchor=tk.W, pady=(0, 3))

        self.strategy_var = tk.StringVar(value="conservative")
        strategy_dropdown = ttk.Combobox(strategy_frame,
                                        textvariable=self.strategy_var,
                                        values=["conservative", "aggressive", "sidebet"],
                                        state="readonly",
                                        width=15,
                                        font=('Arial', 10))
        strategy_dropdown.pack(fill=tk.X)
        strategy_dropdown.bind('<<ComboboxSelected>>', self.on_strategy_change)

        # Bot decision display (compact)
        bot_decision_frame = tk.Frame(bot_section, bg='#0f0f0f', relief=tk.SUNKEN, bd=2)
        bot_decision_frame.pack(fill=tk.X, pady=(10, 0))

        bot_decision_container = tk.Frame(bot_decision_frame, bg='#0f0f0f')
        bot_decision_container.pack(fill=tk.X, padx=10, pady=8)

        tk.Label(bot_decision_container, text="BOT DECISION",
                fg=self.colors['yellow'], bg='#0f0f0f',
                font=('Arial', 9, 'bold')).pack(anchor=tk.W)

        self.bot_action_label = tk.Label(bot_decision_container,
                                         text="Bot Inactive",
                                         fg=self.colors['gray'], bg='#0f0f0f',
                                         font=('Arial', 9),
                                         wraplength=350,
                                         justify=tk.LEFT)
        self.bot_action_label.pack(anchor=tk.W, pady=(5, 0))

        self.bot_reasoning_label = tk.Label(bot_decision_container,
                                           text="",
                                           fg=self.colors['text'], bg='#0f0f0f',
                                           font=('Arial', 8),
                                           wraplength=350,
                                           justify=tk.LEFT)
        self.bot_reasoning_label.pack(anchor=tk.W, pady=(2, 0))

    def _create_position_display(self, parent):
        """Create position information display"""
        position_frame = tk.Frame(parent, bg='#2a2a2a', relief=tk.RAISED, bd=1)
        position_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))

        position_container = tk.Frame(position_frame, bg='#2a2a2a')
        position_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        tk.Label(position_container, text="POSITION",
                fg=self.colors['gray'], bg='#2a2a2a',
                font=('Arial', 9)).pack(anchor=tk.W, pady=(0, 10))

        # Trade position
        self.position_info_label = tk.Label(position_container,
                                           text="No Active Position",
                                           fg=self.colors['text'], bg='#2a2a2a',
                                           font=('Arial', 10),
                                           justify=tk.LEFT)
        self.position_info_label.pack(anchor=tk.W, pady=(2, 0))

        self.pnl_label = tk.Label(position_container,
                                 text="",
                                 fg=self.colors['green'], bg='#2a2a2a',
                                 font=('Arial', 11, 'bold'),
                                 justify=tk.LEFT)
        self.pnl_label.pack(anchor=tk.W, pady=(0, 15))

        # Side bet
        self.sidebet_position_label = tk.Label(position_container,
                                              text="",
                                              fg=self.colors['yellow'], bg='#2a2a2a',
                                              font=('Arial', 10, 'bold'),
                                              justify=tk.LEFT,
                                              wraplength=360)
        self.sidebet_position_label.pack(anchor=tk.W)

    def _setup_controls_and_stats(self, parent):
        """Setup replay controls and statistics"""

        # Controls panel
        controls_frame = tk.Frame(parent, bg='#1a1a1a', relief=tk.RAISED, bd=1)
        controls_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        controls_container = tk.Frame(controls_frame, bg='#1a1a1a')
        controls_container.pack(padx=20, pady=15)

        tk.Label(controls_container, text="REPLAY CONTROLS",
                fg=self.colors['text'], bg='#1a1a1a',
                font=('Arial', 11, 'bold')).pack(pady=(0, 10))

        # File controls
        file_frame = tk.Frame(controls_container, bg='#1a1a1a')
        file_frame.pack(pady=(0, 10))

        tk.Button(file_frame, text="Load Game",
                 bg='#2a2a2a', fg=self.colors['text'],
                 font=('Arial', 10), bd=1,
                 command=self.load_game).pack(side=tk.LEFT, padx=2)

        tk.Button(file_frame, text="Load Directory",
                 bg='#2a2a2a', fg=self.colors['text'],
                 font=('Arial', 10), bd=1,
                 command=self.load_directory).pack(side=tk.LEFT, padx=2)

        # Playback controls
        playback_frame = tk.Frame(controls_container, bg='#1a1a1a')
        playback_frame.pack(pady=(0, 10))

        self.play_button = tk.Button(playback_frame, text="▶ PLAY [Space]",
                                    bg=self.colors['green'], fg='#000000',
                                    font=('Arial', 10, 'bold'), bd=1,
                                    command=self.toggle_play)
        self.play_button.pack(side=tk.LEFT, padx=2)

        tk.Button(playback_frame, text="⏮ RESET [R]",
                 bg='#2a2a2a', fg=self.colors['text'],
                 font=('Arial', 10), bd=1,
                 command=self.reset_game).pack(side=tk.LEFT, padx=2)

        tk.Button(playback_frame, text="⏭ SKIP",
                 bg='#2a2a2a', fg=self.colors['text'],
                 font=('Arial', 10), bd=1,
                 command=self.skip_to_rug).pack(side=tk.LEFT, padx=2)

        # Step controls (NEW)
        step_frame = tk.Frame(controls_container, bg='#1a1a1a')
        step_frame.pack(pady=(0, 10))

        tk.Button(step_frame, text="◀ Step [←]",
                 bg='#2a2a2a', fg=self.colors['text'],
                 font=('Arial', 9), bd=1,
                 command=self.step_backward).pack(side=tk.LEFT, padx=2)

        tk.Button(step_frame, text="Step ▶ [→]",
                 bg='#2a2a2a', fg=self.colors['text'],
                 font=('Arial', 9), bd=1,
                 command=self.step_forward).pack(side=tk.LEFT, padx=2)

        # Speed control
        speed_frame = tk.Frame(controls_container, bg='#1a1a1a')
        speed_frame.pack(fill=tk.X)

        tk.Label(speed_frame, text="Speed:",
                fg=self.colors['gray'], bg='#1a1a1a',
                font=('Arial', 9)).pack(side=tk.LEFT, padx=(0, 5))

        self.speed_var = tk.DoubleVar(value=DEFAULT_SPEED)
        speed_scale = tk.Scale(speed_frame, from_=MIN_SPEED, to_=MAX_SPEED,
                             variable=self.speed_var, orient=tk.HORIZONTAL,
                             bg='#1a1a1a', fg=self.colors['text'],
                             highlightthickness=0, resolution=0.1,
                             length=150, showvalue=True)
        speed_scale.pack(side=tk.LEFT)

        # Speed presets (NEW)
        preset_frame = tk.Frame(controls_container, bg='#1a1a1a')
        preset_frame.pack(fill=tk.X, pady=(5, 0))

        for speed in [0.5, 1.0, 2.0, 5.0]:
            btn = tk.Button(preset_frame, text=f"{speed}x",
                          bg='#2a2a2a', fg=self.colors['gray'],
                          font=('Arial', 8), bd=1,
                          command=lambda s=speed: self.speed_var.set(s))
            btn.pack(side=tk.LEFT, padx=1, fill=tk.X, expand=True)

        # Bot controls moved to Trading Panel (right side) for better visibility

        # Stats panel
        stats_frame = tk.Frame(parent, bg='#1a1a1a', relief=tk.RAISED, bd=1, width=STATS_PANEL_WIDTH)
        stats_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
        stats_frame.pack_propagate(False)

        stats_container = tk.Frame(stats_frame, bg='#1a1a1a')
        stats_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        tk.Label(stats_container, text="SESSION STATISTICS",
                fg=self.colors['text'], bg='#1a1a1a',
                font=('Arial', 11, 'bold')).pack(pady=(0, 10))

        # Stats grid
        stats_grid = tk.Frame(stats_container, bg='#1a1a1a')
        stats_grid.pack(fill=tk.BOTH, expand=True)

        self.stat_labels = {}
        stats_data = [
            # Session Stats (Row 0)
            ("Session P&L", "session_pnl", "+0.0000 SOL"),
            ("Win Rate", "win_rate", "0.0%"),
            ("Total Trades", "total_trades", "0"),
            ("Games Played", "games_played", "0"),
            # Session Stats (Row 1)
            ("Current Streak", "streak", "0"),
            ("Best Trade", "best_trade", "+0.0000"),
            ("Worst Trade", "worst_trade", "-0.0000"),
            ("Avg Win", "avg_win", "+0.0000"),
            # Current Game Stats (Row 2)
            ("Game ID", "game_id", "---"),
            ("Total Ticks", "game_ticks", "0"),
            ("Peak Price", "peak_price", "1.0000x"),
            ("Game Trades", "game_trades", "0"),
        ]

        for i, (label, key, default) in enumerate(stats_data):
            row = i // 4
            col = i % 4

            frame = tk.Frame(stats_grid, bg='#1a1a1a')
            frame.grid(row=row*2, column=col, padx=10, pady=2, sticky=tk.W)

            tk.Label(frame, text=label,
                    fg=self.colors['gray'], bg='#1a1a1a',
                    font=('Arial', 8)).pack(anchor=tk.W)

            self.stat_labels[key] = tk.Label(frame, text=default,
                                            fg=self.colors['text'], bg='#1a1a1a',
                                            font=('Arial', 10, 'bold'))
            self.stat_labels[key].pack(anchor=tk.W)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(stats_container,
                                           variable=self.progress_var,
                                           maximum=100,
                                           style="game.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(10, 0))

        # Style the progress bar
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("game.Horizontal.TProgressbar",
                       background=self.colors['green'],
                       troughcolor='#2a2a2a',
                       bordercolor='#1a1a1a',
                       lightcolor=self.colors['green'],
                       darkcolor=self.colors['green'])

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for common actions"""
        self.root.bind('<space>', lambda e: self.toggle_play())
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

        logger.info("Keyboard shortcuts configured")

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

Other:
  H - Show this help

GAME RULES:
• Side bets win if rug occurs within 40 ticks
• Side bet pays 5x your wager
• After side bet resolves, 5 tick cooldown before next bet
• All positions are lost when rug occurs
"""
        messagebox.showinfo("Help - Keyboard Shortcuts", help_text)

    def set_bet_amount(self, amount: Decimal):
        """Set bet amount from quick buttons or manual input"""
        self.bet_entry.delete(0, tk.END)
        self.bet_entry.insert(0, str(amount))
        logger.debug(f"Bet amount set to {amount}")

    def increment_bet_amount(self, amount: Decimal):
        """Increment bet amount by specified amount"""
        try:
            current_amount = Decimal(self.bet_entry.get())
        except (ValueError, InvalidOperation):
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

            if bet_amount < MIN_BET_SOL:
                self.toast.show(f"Bet must be at least {MIN_BET_SOL} SOL", "error")
                return None

            if bet_amount > MAX_BET_SOL:
                self.toast.show(f"Bet cannot exceed {MAX_BET_SOL} SOL", "error")
                return None

            if bet_amount > self.wallet_balance:
                self.toast.show(f"Insufficient balance! Have {self.wallet_balance:.4f} SOL", "error")
                return None

            return bet_amount

        except (ValueError, InvalidOperation) as e:
            self.toast.show("Invalid bet amount", "error")
            logger.warning(f"Invalid bet amount: {self.bet_entry.get()}, error: {e}")
            return None

    def execute_buy(self):
        """Execute buy order at current price (can add to existing position)"""
        with self.state_lock:
            if not self.current_game or self.current_tick_index >= len(self.current_game):
                return

            bet_amount = self.get_bet_amount()
            if bet_amount is None:
                return

            tick = self.current_game[self.current_tick_index]

            # Check if game is active and phase is valid
            if not tick.active:
                self.toast.show("Game not active yet!", "warning")
                return

            if tick.phase in ["COOLDOWN", "RUG_EVENT", "RUG_EVENT_1", "UNKNOWN"]:
                self.toast.show("Cannot buy in this phase!", "warning")
                return

            # If position exists, add to it (calculate weighted average entry price)
            if self.active_position:
                old_amount = self.active_position.amount
                old_price = self.active_position.entry_price
                new_amount = bet_amount
                new_price = tick.price

                # Calculate weighted average entry price
                total_amount = old_amount + new_amount
                weighted_avg_price = (old_amount * old_price + new_amount * new_price) / total_amount

                # Update position
                self.active_position.amount = total_amount
                self.active_position.entry_price = weighted_avg_price

                self.toast.show(f"Added {bet_amount} SOL at {tick.price:.4f}x (Avg: {weighted_avg_price:.4f}x)", "success")
                logger.info(f"ADD TO POSITION: +{bet_amount} SOL at {tick.price}, new avg: {weighted_avg_price}, total: {total_amount}")
            else:
                # Create new position
                self.active_position = Position(
                    entry_price=tick.price,
                    amount=bet_amount,
                    entry_time=time.time(),
                    entry_tick=tick.tick
                )

                # Enable sell button for new positions
                self.sell_button.config(state=tk.NORMAL)

                self.toast.show(f"Bought {bet_amount} SOL at {tick.price:.4f}x", "success")
                logger.info(f"NEW POSITION: {bet_amount} SOL at {tick.price} (tick {tick.tick})")

            # Update wallet
            self.wallet_balance -= bet_amount
            self.update_wallet_display()

            # Flash button
            self.flash_button(self.buy_button, self.colors['green'])

            # Update displays
            self.update_position_display()

            # Add to chart
            self.add_chart_marker(tick.tick, tick.price, "BUY", self.colors['green'])

    def execute_sell(self):
        """Execute sell order at current price"""
        with self.state_lock:
            if not self.active_position:
                return

            if not self.current_game or self.current_tick_index >= len(self.current_game):
                return

            tick = self.current_game[self.current_tick_index]

            # Close position
            self.active_position.status = "closed"
            self.active_position.exit_price = tick.price
            self.active_position.exit_time = time.time()
            self.active_position.exit_tick = tick.tick

            # Calculate P&L with Decimal precision
            price_change = tick.price / self.active_position.entry_price - 1
            self.active_position.pnl_sol = self.active_position.amount * price_change
            self.active_position.pnl_percent = price_change * 100

            # Update wallet
            self.wallet_balance += self.active_position.amount + self.active_position.pnl_sol
            self.update_wallet_display()

            # Update stats
            self.update_session_stats(self.active_position)

            # Flash button
            self.flash_button(self.sell_button, self.colors['red'])

            # Add to chart
            self.add_chart_marker(tick.tick, tick.price, "SELL", self.colors['red'])

            # Store in history
            self.position_history.append(self.active_position)

            # Show result
            pnl_sign = "+" if self.active_position.pnl_sol >= 0 else ""
            self.toast.show(
                f"Sold at {tick.price:.4f}x: {pnl_sign}{self.active_position.pnl_sol:.4f} SOL",
                "success" if self.active_position.pnl_sol >= 0 else "error"
            )
            logger.info(f"SELL: {self.active_position.amount} SOL at {tick.price}, P&L: {self.active_position.pnl_sol}")

            # Clear active position
            self.active_position = None

            # Update UI
            self.buy_button.config(state=tk.NORMAL)
            self.sell_button.config(state=tk.DISABLED)
            self.update_position_display()

    def execute_sidebet(self):
        """Execute side bet at current price"""
        with self.state_lock:
            if not self.current_game or self.current_tick_index >= len(self.current_game):
                return

            bet_amount = self.get_bet_amount()
            if bet_amount is None:
                return

            tick = self.current_game[self.current_tick_index]

            # Check if game is active and phase is valid
            if not tick.active:
                self.toast.show("Game not active yet!", "warning")
                return

            if tick.phase in ["COOLDOWN", "RUG_EVENT", "RUG_EVENT_1", "UNKNOWN"]:
                self.toast.show("Cannot place side bet in this phase!", "warning")
                return

            # Create side bet
            self.active_sidebet = SideBet(
                amount=bet_amount,
                placed_tick=tick.tick,
                placed_price=tick.price
            )

            # Update wallet
            self.wallet_balance -= bet_amount
            self.update_wallet_display()

            # Flash button
            self.flash_button(self.sidebet_button, self.colors['yellow'])

            # Update displays
            self.update_position_display()

            # Add to chart
            self.add_chart_marker(tick.tick, tick.price, "SIDE", self.colors['yellow'])

            potential_win = bet_amount * SIDEBET_MULTIPLIER
            self.toast.show(f"Side bet: {bet_amount} SOL (Win: {potential_win} SOL)", "info")
            logger.info(f"SIDE BET: {bet_amount} SOL at tick {tick.tick}")

    def update_wallet_display(self):
        """Update wallet balance display with color coding"""
        self.wallet_label.config(text=f"{self.wallet_balance:.4f} SOL")

        # Color based on P&L
        if self.wallet_balance > self.initial_balance:
            self.wallet_label.config(fg=self.colors['green'])
        elif self.wallet_balance < self.initial_balance:
            self.wallet_label.config(fg=self.colors['red'])
        else:
            self.wallet_label.config(fg=self.colors['text'])

    def update_position_display(self):
        """Update position information display"""

        # Show active trading position
        if self.active_position and self.active_position.status == "active":
            if self.current_game and self.current_tick_index < len(self.current_game):
                tick = self.current_game[self.current_tick_index]

                # Calculate current P&L
                price_change = tick.price / self.active_position.entry_price - 1
                pnl_sol = self.active_position.amount * price_change
                pnl_percent = price_change * 100

                # Trade position info with current price
                position_text = f"TRADE: {self.active_position.entry_price:.4f}x @ {self.active_position.amount:.3f} SOL\nCurrent: {tick.price:.4f}x"
                self.position_info_label.config(text=position_text)

                # Live P&L display with color
                if pnl_sol >= 0:
                    pnl_text = f"P&L: +{pnl_sol:.4f} SOL (+{pnl_percent:.1f}%)"
                    pnl_color = self.colors['green']
                else:
                    pnl_text = f"P&L: {pnl_sol:.4f} SOL ({pnl_percent:.1f}%)"
                    pnl_color = self.colors['red']

                self.pnl_label.config(text=pnl_text, fg=pnl_color)
        else:
            self.position_info_label.config(text="No Active Position")
            self.pnl_label.config(text="")

        # Side bet display
        if self.active_sidebet and self.active_sidebet.status == "active":
            if self.current_game and self.current_tick_index < len(self.current_game):
                tick = self.current_game[self.current_tick_index]
                expiry_tick = self.active_sidebet.placed_tick + SIDEBET_WINDOW_TICKS
                ticks_remaining = expiry_tick - tick.tick
                potential_win = self.active_sidebet.amount * SIDEBET_MULTIPLIER

                sidebet_text = f"SIDE BET: {self.active_sidebet.amount:.3f} SOL (5x) → {potential_win:.3f} SOL\n{ticks_remaining} ticks remaining"
                self.sidebet_position_label.config(text=sidebet_text, fg=self.colors['yellow'])
            else:
                self.sidebet_position_label.config(text="")
        else:
            self.sidebet_position_label.config(text="")

    def update_session_stats(self, position: Position):
        """Update session statistics after a trade"""
        # Update counters
        if position.pnl_sol > 0:
            self.trades_won += 1
            self.current_streak = max(0, self.current_streak) + 1
        else:
            self.trades_lost += 1
            self.current_streak = min(0, self.current_streak) - 1

        total_trades = self.trades_won + self.trades_lost

        # Update session P&L
        self.session_pnl = self.wallet_balance - self.initial_balance

        # Update displays
        self.stat_labels['session_pnl'].config(
            text=f"{self.session_pnl:+.4f} SOL",
            fg=self.colors['green'] if self.session_pnl >= 0 else self.colors['red']
        )

        win_rate = (self.trades_won / total_trades * 100) if total_trades > 0 else Decimal('0')
        self.stat_labels['win_rate'].config(text=f"{win_rate:.1f}%")
        self.stat_labels['total_trades'].config(text=str(total_trades))
        self.stat_labels['games_played'].config(text=str(self.games_played))
        self.stat_labels['streak'].config(text=str(self.current_streak))

        # Track best/worst
        if position.pnl_sol > self.best_trade:
            self.best_trade = position.pnl_sol
            self.stat_labels['best_trade'].config(text=f"{self.best_trade:+.4f}")

        if position.pnl_sol < self.worst_trade:
            self.worst_trade = position.pnl_sol
            self.stat_labels['worst_trade'].config(text=f"{self.worst_trade:+.4f}")

        # Calculate average win
        winning_positions = [p for p in self.position_history if p.pnl_sol > 0]
        if winning_positions:
            avg_win = sum(p.pnl_sol for p in winning_positions) / len(winning_positions)
            self.stat_labels['avg_win'].config(text=f"{avg_win:+.4f}")

    def update_game_stats(self):
        """Update current game statistics display"""
        if not self.current_game:
            return

        # Game ID
        if self.current_game_id:
            short_id = self.current_game_id[-8:] if len(self.current_game_id) > 8 else self.current_game_id
            self.stat_labels['game_id'].config(text=short_id)
        else:
            self.stat_labels['game_id'].config(text="Unknown")

        # Total Ticks
        total_ticks = len(self.current_game)
        self.stat_labels['game_ticks'].config(text=str(total_ticks))

        # Peak Price
        peak_price = max(tick.price for tick in self.current_game)
        self.stat_labels['peak_price'].config(text=f"{peak_price:.4f}x")

        # Total Trades in Game (from last tick's trade_count)
        if self.current_game:
            # Find the maximum trade_count across all ticks
            max_trades = max(tick.trade_count for tick in self.current_game)
            self.stat_labels['game_trades'].config(text=str(max_trades))
        else:
            self.stat_labels['game_trades'].config(text="0")

        logger.info(f"Game stats updated: {total_ticks} ticks, peak {peak_price}x, {max_trades} trades")

    def handle_rug_event(self, tick: GameTick):
        """
        Handle rug event - Game Over

        Args:
            tick: Current game tick when rug occurred
        """
        logger.warning(f"RUG EVENT at tick {tick.tick}, price {tick.price}")

        # Show rug message
        self.price_label.config(text="RUG PULLED!", fg=self.colors['red'])

        # Close active position at total loss
        if self.active_position and self.active_position.status == "active":
            self.active_position.status = "closed"
            self.active_position.exit_price = RUG_LIQUIDATION_PRICE
            self.active_position.exit_tick = tick.tick
            self.active_position.pnl_sol = -self.active_position.amount
            self.active_position.pnl_percent = Decimal('-100.0')

            # Update stats
            self.update_session_stats(self.active_position)
            self.position_history.append(self.active_position)

            self.toast.show(f"Position liquidated: -{self.active_position.amount:.4f} SOL", "error")

            self.active_position = None

        # Check side bet
        if self.active_sidebet and self.active_sidebet.status == "active":
            expiry_tick = self.active_sidebet.placed_tick + SIDEBET_WINDOW_TICKS

            if tick.tick <= expiry_tick:
                # SIDE BET WON
                payout = self.active_sidebet.amount * SIDEBET_MULTIPLIER
                self.wallet_balance += payout
                self.update_wallet_display()

                ticks_called = tick.tick - self.active_sidebet.placed_tick
                self.toast.show(f"SIDE BET WON! +{payout:.4f} SOL (called at {ticks_called} ticks)", "success")
                logger.info(f"SIDE BET WON: +{payout} SOL")

                self.active_sidebet.status = "won"
                self.active_sidebet.resolved_tick = tick.tick
                self.last_sidebet_resolved_tick = tick.tick
            else:
                # Side bet expired
                self.toast.show(f"Side bet expired: -{self.active_sidebet.amount:.4f} SOL", "error")
                self.active_sidebet.status = "lost"
                self.active_sidebet.resolved_tick = tick.tick
                self.last_sidebet_resolved_tick = tick.tick

            self.active_sidebet = None

        # Update UI
        self.buy_button.config(state=tk.DISABLED)
        self.sell_button.config(state=tk.DISABLED)
        self.sidebet_button.config(state=tk.DISABLED)

    def flash_button(self, button, color):
        """Flash button to show action"""
        original_bg = button.cget('bg')
        button.config(bg='#ffffff')
        self.root.after(100, lambda: button.config(bg=original_bg))

    def add_chart_marker(self, tick: int, price: Decimal, action: str, color: str):
        """
        Add marker to chart and redraw

        Args:
            tick: Tick number
            price: Price at this tick
            action: Action type (BUY, SELL, SIDE)
            color: Color for the marker
        """
        self.chart_points.append(ChartPoint(tick, price, action, color))
        self.draw_chart()

    def draw_chart(self):
        """Draw the price chart with markers"""
        if not self.current_game or not self.chart_points:
            return

        # Clear canvas
        self.chart_canvas.delete("all")

        # Get canvas dimensions
        width = self.chart_canvas.winfo_width()
        height = self.chart_canvas.winfo_height()

        if width <= 1 or height <= 1:
            return

        # Get price range
        prices = [float(point.price) for point in self.chart_points]
        if not prices:
            return

        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price if max_price > min_price else 1

        # Get tick range
        ticks = [point.tick for point in self.chart_points]
        min_tick = min(ticks)
        max_tick = max(ticks)
        tick_range = max_tick - min_tick if max_tick > min_tick else 1

        # Margins
        margin_x = 40
        margin_y = 30
        chart_width = width - 2 * margin_x
        chart_height = height - 2 * margin_y

        # Draw grid lines
        for i in range(5):
            y = margin_y + (chart_height * i / 4)
            self.chart_canvas.create_line(
                margin_x, y, width - margin_x, y,
                fill='#2a2a2a', width=1
            )
            price_at_line = max_price - (price_range * i / 4)
            self.chart_canvas.create_text(
                margin_x - 5, y,
                text=f"{price_at_line:.2f}x",
                fill='#666666',
                anchor=tk.E,
                font=('Arial', 8)
            )

        # Draw price line
        points = []
        for point in self.chart_points:
            x = margin_x + ((point.tick - min_tick) / tick_range) * chart_width
            y = height - margin_y - ((float(point.price) - min_price) / price_range) * chart_height
            points.extend([x, y])

        if len(points) >= 4:
            self.chart_canvas.create_line(
                *points,
                fill=self.colors['green'],
                width=2,
                smooth=True
            )

        # Draw action markers
        for point in self.chart_points:
            if point.action:
                x = margin_x + ((point.tick - min_tick) / tick_range) * chart_width
                y = height - margin_y - ((float(point.price) - min_price) / price_range) * chart_height

                # Marker shape based on action
                if point.action == "BUY":
                    # Triangle up
                    self.chart_canvas.create_polygon(
                        x, y - 10, x - 6, y, x + 6, y,
                        fill=point.color, outline='#ffffff', width=1
                    )
                elif point.action == "SELL":
                    # Triangle down
                    self.chart_canvas.create_polygon(
                        x, y + 10, x - 6, y, x + 6, y,
                        fill=point.color, outline='#ffffff', width=1
                    )
                elif point.action == "SIDE":
                    # Diamond
                    self.chart_canvas.create_polygon(
                        x, y - 8, x + 6, y, x, y + 8, x - 6, y,
                        fill=point.color, outline='#ffffff', width=1
                    )

    def load_game(self):
        """Load a single game file"""
        filename = filedialog.askopenfilename(
            title="Select Game Recording",
            initialdir=DEFAULT_RECORDINGS_DIR,
            filetypes=[("JSONL files", "*.jsonl"), ("All files", "*.*")]
        )

        if filename:
            self.load_game_file(filename)

    def load_directory(self):
        """Load directory of games"""
        directory = filedialog.askdirectory(
            title="Select Game Recordings Directory",
            initialdir=DEFAULT_RECORDINGS_DIR
        )

        if directory:
            game_files = sorted(Path(directory).glob("game_*.jsonl"))
            if game_files:
                self.pending_games = list(game_files)
                self.load_next_game()
                self.toast.show(f"Loaded {len(game_files)} games", "success")
            else:
                messagebox.showwarning("No Games", "No game files found in directory")

    def load_next_game(self):
        """Load next game from queue"""
        if self.pending_games:
            next_file = self.pending_games.pop(0)
            self.load_game_file(next_file)

    def load_game_file(self, filename):
        """
        Load game data from JSONL file

        Args:
            filename: Path to JSONL file
        """
        try:
            game_ticks = []
            game_id = None

            with open(filename, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line.strip())

                        if data.get('type') == 'game_start':
                            game_id = data.get('game_id', 'Unknown')
                        elif data.get('type') == 'tick':
                            tick = GameTick.from_dict(data)
                            game_ticks.append(tick)
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.error(f"Error parsing line {line_num} in {filename}: {e}")
                        continue

            if game_ticks:
                self.current_game = game_ticks
                self.current_game_id = game_id
                # Reset cooldown tracking for new game
                self.last_sidebet_resolved_tick = None
                self.reset_game()

                # Update game info
                if game_id:
                    short_id = game_id[-8:] if len(game_id) > 8 else game_id
                    self.game_id_label.config(text=f"Game: {short_id}")

                # Update game statistics
                self.update_game_stats()

                self.toast.show(f"Loaded game with {len(game_ticks)} ticks", "success")
                logger.info(f"Loaded game {game_id} with {len(game_ticks)} ticks from {filename}")
            else:
                raise ValueError("No valid game ticks found in file")

        except FileNotFoundError:
            messagebox.showerror("Load Error", f"File not found: {filename}")
            logger.error(f"File not found: {filename}")
        except json.JSONDecodeError as e:
            messagebox.showerror("Load Error", f"Invalid JSON format: {str(e)}")
            logger.error(f"JSON decode error in {filename}: {e}")
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load game: {str(e)}")
            logger.error(f"Unexpected error loading {filename}: {e}", exc_info=True)

    def reset_game(self, reset_session: bool = False):
        """
        Reset game to beginning

        Args:
            reset_session: If True, also reset session statistics
        """
        self.stop_playback()

        self.current_tick_index = 0
        self.is_playing = False

        # Clear active positions
        self.active_position = None
        self.active_sidebet = None

        # Clear chart
        self.chart_points.clear()
        self.chart_canvas.delete("all")

        if reset_session:
            self.position_history.clear()
            self.session_pnl = Decimal('0.0')
            self.games_played = 0
            self.trades_won = 0
            self.trades_lost = 0
            self.best_trade = Decimal('0.0')
            self.worst_trade = Decimal('0.0')
            self.current_streak = 0
            # Update all stat labels
            self.stat_labels['session_pnl'].config(text="+0.0000 SOL")
            self.stat_labels['win_rate'].config(text="0.0%")
            self.stat_labels['total_trades'].config(text="0")
            self.stat_labels['games_played'].config(text="0")
            self.stat_labels['streak'].config(text="0")
            self.stat_labels['best_trade'].config(text="+0.0000")
            self.stat_labels['worst_trade'].config(text="-0.0000")
            self.stat_labels['avg_win'].config(text="+0.0000")

        # Reset UI
        self.buy_button.config(state=tk.NORMAL)
        self.sell_button.config(state=tk.DISABLED)
        self.sidebet_button.config(state=tk.NORMAL)
        self.play_button.config(text="▶ PLAY [Space]")

        # Clear displays
        self.position_info_label.config(text="No Active Position")
        self.pnl_label.config(text="")
        self.sidebet_position_label.config(text="")

        # Update display with first tick
        if self.current_game:
            self.update_display()

        logger.info(f"Game reset (session_reset={reset_session})")

    def toggle_play(self):
        """Toggle play/pause"""
        if self.is_playing:
            self.stop_playback()
        else:
            self.start_playback()

    def start_playback(self):
        """Start game playback"""
        if not self.current_game:
            messagebox.showwarning("No Game", "Please load a game first")
            return

        if self.current_tick_index >= len(self.current_game) - 1:
            # If at end, restart
            self.current_tick_index = 0

        self.is_playing = True
        self.play_button.config(text="⏸ PAUSE [Space]")
        self.stop_event.clear()

        # Start playback thread
        self.playback_thread = threading.Thread(target=self.playback_loop, daemon=True)
        self.playback_thread.start()

        logger.info("Playback started")

    def stop_playback(self):
        """Stop game playback"""
        self.is_playing = False
        self.play_button.config(text="▶ PLAY [Space]")
        self.stop_event.set()

        logger.info("Playback stopped")

    def playback_loop(self):
        """Main playback loop (runs in separate thread)"""
        if not self.current_game:
            return

        logger.debug(f"Playback loop started: {len(self.current_game)} ticks")

        while self.is_playing and self.current_tick_index < len(self.current_game):
            if self.stop_event.is_set():
                break

            logger.debug(f"Processing tick {self.current_tick_index}")

            # Update display (must be done on main thread)
            self.root.after(0, self.update_display)

            # Bot mode: Execute bot action and wait for completion
            if self.bot_mode_enabled and self.bot_controller:
                logger.debug(f"Scheduling bot action for tick {self.current_tick_index}")
                self.bot_action_complete.clear()  # Mark as not complete
                self.root.after(0, self.execute_bot_action)
                # Wait for bot action to complete (timeout after 1 second)
                if not self.bot_action_complete.wait(timeout=1.0):
                    logger.warning(f"Bot action timed out at tick {self.current_tick_index}")
                    self.bot_action_complete.set()  # Reset for next tick

            # Calculate delay to next tick
            if self.current_tick_index < len(self.current_game) - 1:
                current_tick = self.current_game[self.current_tick_index]
                next_tick = self.current_game[self.current_tick_index + 1]

                # Parse timestamps
                try:
                    current_ts = current_tick.timestamp.replace('Z', '+00:00') if current_tick.timestamp.endswith('Z') else current_tick.timestamp
                    next_ts = next_tick.timestamp.replace('Z', '+00:00') if next_tick.timestamp.endswith('Z') else next_tick.timestamp
                    current_time = datetime.fromisoformat(current_ts)
                    next_time = datetime.fromisoformat(next_ts)
                    delay = (next_time - current_time).total_seconds()
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Timestamp parsing failed: {e}, using default delay")
                    delay = DEFAULT_PLAYBACK_DELAY

                # Adjust for speed
                delay = delay / self.speed_var.get()
            else:
                delay = 0.1

            time.sleep(max(0.01, delay))
            self.current_tick_index += 1

        # Game ended
        self.root.after(0, self.game_ended)

    def step_forward(self):
        """Step forward one tick"""
        if self.current_game and self.current_tick_index < len(self.current_game) - 1:
            self.current_tick_index += 1
            self.update_display()
            logger.debug(f"Stepped forward to tick {self.current_tick_index}")

    def step_backward(self):
        """Step backward one tick"""
        if self.current_game and self.current_tick_index > 0:
            self.current_tick_index -= 1
            self.update_display()
            logger.debug(f"Stepped backward to tick {self.current_tick_index}")

    def update_display(self):
        """Update all displays with current tick"""
        if not self.current_game or self.current_tick_index >= len(self.current_game):
            return

        tick = self.current_game[self.current_tick_index]

        # Update price
        self.price_label.config(text=f"{tick.price:.4f}x")
        if tick.price > Decimal('1.5'):
            self.price_label.config(fg=self.colors['green'])
        elif tick.price < Decimal('1.0'):
            self.price_label.config(fg=self.colors['red'])
        else:
            self.price_label.config(fg=self.colors['text'])

        # Update phase
        phase_display = tick.phase.replace('_', ' ')
        self.phase_label.config(text=phase_display)

        # Update cooldown
        if tick.cooldown_timer > 0:
            seconds = tick.cooldown_timer / 1000
            self.cooldown_label.config(text=f"Next game in: {seconds:.1f}s")
        else:
            self.cooldown_label.config(text="")

        # Update tick info
        self.tick_info_label.config(text=f"Tick: {tick.tick} | Trades: {tick.trade_count}")

        # Update progress bar
        progress = (self.current_tick_index / len(self.current_game)) * 100
        self.progress_var.set(progress)

        # Check for rug (first occurrence)
        if tick.rugged and self.current_tick_index > 0:
            prev_tick = self.current_game[self.current_tick_index - 1]
            if not prev_tick.rugged:
                self.handle_rug_event(tick)

        # Check side bet expiry
        if self.active_sidebet and self.active_sidebet.status == "active":
            expiry_tick = self.active_sidebet.placed_tick + SIDEBET_WINDOW_TICKS
            if tick.tick > expiry_tick:
                self.toast.show(f"Side bet expired: -{self.active_sidebet.amount:.4f} SOL", "error")
                self.active_sidebet.status = "lost"
                self.active_sidebet.resolved_tick = tick.tick
                self.last_sidebet_resolved_tick = tick.tick
                self.active_sidebet = None

        # Update position display
        self.update_position_display()

        # Update button states
        self._update_button_states(tick)

        # Add point to chart
        self.chart_points.append(ChartPoint(tick.tick, tick.price))
        if len(self.chart_points) % 10 == 0:  # Redraw every 10 points to reduce overhead
            self.draw_chart()

    def _update_button_states(self, tick: GameTick):
        """Update button enabled/disabled states based on game state"""

        # BUY button - Always enabled in playable phases (can add to position)
        if tick.phase in ["COOLDOWN", "RUG_EVENT", "RUG_EVENT_1", "UNKNOWN"]:
            self.buy_button.config(state=tk.DISABLED)
        else:
            self.buy_button.config(state=tk.NORMAL)

        # SELL button
        if self.active_position and self.active_position.status == "active":
            self.sell_button.config(state=tk.NORMAL)
        else:
            self.sell_button.config(state=tk.DISABLED)

        # SIDE BET button
        in_cooldown = False
        if self.last_sidebet_resolved_tick is not None:
            ticks_since_resolution = tick.tick - self.last_sidebet_resolved_tick
            in_cooldown = ticks_since_resolution <= SIDEBET_COOLDOWN_TICKS

        if (self.active_sidebet and self.active_sidebet.status == "active") or in_cooldown or tick.phase in ["COOLDOWN", "RUG_EVENT", "RUG_EVENT_1", "UNKNOWN"]:
            self.sidebet_button.config(state=tk.DISABLED)
        else:
            self.sidebet_button.config(state=tk.NORMAL)

    def skip_to_rug(self):
        """Skip to rug event"""
        if not self.current_game:
            return

        for i, tick in enumerate(self.current_game):
            if tick.rugged:
                self.current_tick_index = max(0, i - 10)
                break

        self.update_display()
        logger.info(f"Skipped to rug event at tick {self.current_tick_index}")

    def game_ended(self):
        """Handle game end"""
        self.stop_playback()
        self.games_played += 1

        # Update final stats
        self.stat_labels['games_played'].config(text=str(self.games_played))

        # Show game over
        self.phase_label.config(text="GAME COMPLETE", fg=self.colors['yellow'])

        logger.info(f"Game {self.games_played} completed")

        # Auto-load next if available
        if self.pending_games:
            self.root.after(2000, self.load_next_game)

    # ========================================================================
    # BOT MODE METHODS (Checkpoint 1B)
    # ========================================================================

    def toggle_bot_mode(self):
        """Toggle bot mode on/off"""
        self.bot_mode_enabled = not self.bot_mode_enabled

        if self.bot_mode_enabled:
            # Enable bot mode
            self.bot_strategy = self.strategy_var.get()
            self.bot_controller = BotController(self.bot_interface, self.bot_strategy)

            self.bot_mode_button.config(
                text="🤖 DISABLE BOT",
                bg=self.colors['green'],
                fg='#000000'
            )
            self.bot_action_label.config(
                text=f"Bot Active ({self.bot_strategy})",
                fg=self.colors['green']
            )
            self.toast.show(f"Bot mode enabled - {self.bot_strategy} strategy", "success")
            logger.info(f"Bot mode enabled with {self.bot_strategy} strategy")
        else:
            # Disable bot mode
            self.bot_controller = None
            self.bot_action_complete.set()  # Clear any waiting

            self.bot_mode_button.config(
                text="🤖 ENABLE BOT",
                bg='#2a2a2a',
                fg=self.colors['blue']
            )
            self.bot_action_label.config(
                text="Bot Inactive",
                fg=self.colors['gray']
            )
            self.bot_reasoning_label.config(text="")
            self.toast.show("Bot mode disabled", "info")
            logger.info("Bot mode disabled")

    def on_strategy_change(self, event=None):
        """Handle strategy change"""
        new_strategy = self.strategy_var.get()

        # If bot is active, recreate controller with new strategy
        if self.bot_mode_enabled:
            self.bot_strategy = new_strategy
            self.bot_controller = BotController(self.bot_interface, new_strategy)
            self.bot_action_label.config(text=f"Bot Active ({new_strategy})")
            self.toast.show(f"Strategy changed to {new_strategy}", "info")
            logger.info(f"Bot strategy changed to {new_strategy}")

    def update_bot_decision_panel(self, action: str, reasoning: str, success: bool):
        """Update bot decision panel with latest action"""
        # Update action label
        action_colors = {
            'BUY': self.colors['green'],
            'SELL': self.colors['red'],
            'SIDE': self.colors['yellow'],
            'WAIT': self.colors['gray']
        }

        action_color = action_colors.get(action, self.colors['text'])

        if success:
            action_text = f"Action: {action}"
        else:
            action_text = f"Action: {action} (FAILED)"
            action_color = self.colors['red']

        self.bot_action_label.config(text=action_text, fg=action_color)
        self.bot_reasoning_label.config(text=reasoning)

    def execute_bot_action(self):
        """Execute bot decision at current tick"""
        if not self.bot_controller:
            self.bot_action_complete.set()
            return

        try:
            # Bot decides and executes action
            result = self.bot_controller.execute_step()

            # Update decision panel
            self.update_bot_decision_panel(
                result['action'],
                self.bot_controller.last_reasoning,
                result['success']
            )

            # If action failed, show why
            if not result['success']:
                logger.warning(f"Bot action failed: {result['reason']}")

        except Exception as e:
            logger.error(f"Bot execution error: {e}", exc_info=True)
            self.toast.show(f"Bot error: {e}", "error")
        finally:
            # Signal that bot action is complete
            self.bot_action_complete.set()


def main():
    """Main entry point"""
    root = tk.Tk()
    app = GameUIReplayViewer(root)

    # Try to auto-load test games if they exist
    test_dir = Path(DEFAULT_RECORDINGS_DIR)
    if test_dir.exists():
        game_files = sorted(test_dir.glob("game_*.jsonl"))
        if game_files:
            app.pending_games = list(game_files)
            app.load_next_game()
            logger.info(f"Auto-loaded {len(game_files)} games from {test_dir}")

    logger.info("Application started")
    root.mainloop()
    logger.info("Application closed")


if __name__ == "__main__":
    main()
