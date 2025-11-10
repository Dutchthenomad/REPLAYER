"""
Game State Management Module
Centralized state management with observer pattern for reactive updates
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
import threading
from collections import defaultdict
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class StateEvents(Enum):
    """Events that can be emitted by state changes"""
    BALANCE_CHANGED = "balance_changed"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    SIDEBET_PLACED = "sidebet_placed"
    SIDEBET_RESOLVED = "sidebet_resolved"
    TICK_UPDATED = "tick_updated"
    GAME_STARTED = "game_started"
    GAME_ENDED = "game_ended"
    RUG_EVENT = "rug_event"
    PHASE_CHANGED = "phase_changed"
    BOT_ACTION = "bot_action"

@dataclass
class StateSnapshot:
    """Immutable snapshot of game state at a point in time"""
    timestamp: datetime
    tick: int
    balance: Decimal
    position: Optional[Dict] = None
    sidebet: Optional[Dict] = None
    phase: str = "UNKNOWN"
    price: Decimal = Decimal('1.0')
    game_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class GameState:
    """
    Centralized game state management with thread-safe operations
    and observer pattern for reactive updates
    """
    
    def __init__(self, initial_balance: Decimal = Decimal('0.100')):
        # Core state
        self._state = {
            'balance': initial_balance,
            'initial_balance': initial_balance,
            'position': None,
            'sidebet': None,
            'current_tick': 0,
            'current_price': Decimal('1.0'),
            'current_phase': 'UNKNOWN',
            'game_id': None,
            'game_active': False,
            'rugged': False,
            'rug_detected': False,
            'bot_enabled': False,
            'bot_strategy': None,
        }

        # Statistics
        self._stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': Decimal('0'),
            'max_drawdown': Decimal('0'),
            'peak_balance': initial_balance,
            'sidebets_won': 0,
            'sidebets_lost': 0,
            'games_played': 0,
        }

        # History
        self._history: List[StateSnapshot] = []
        self._transaction_log: List[Dict] = []
        self._closed_positions: List[Dict] = []  # Track closed positions for compatibility
        
        # Observer pattern
        self._observers: Dict[StateEvents, List[Callable]] = defaultdict(list)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # State validation rules
        self._validators: List[Callable] = []
        
        logger.info(f"GameState initialized with balance: {initial_balance}")
    
    # ========== State Access Methods ==========
    
    def get(self, key: str, default: Any = None) -> Any:
        """Thread-safe state getter"""
        with self._lock:
            return self._state.get(key, default)
    
    def get_stats(self, key: Optional[str] = None) -> Any:
        """Get statistics"""
        with self._lock:
            if key:
                return self._stats.get(key)
            return self._stats.copy()
    
    def get_snapshot(self) -> StateSnapshot:
        """Get immutable snapshot of current state"""
        with self._lock:
            return StateSnapshot(
                timestamp=datetime.now(),
                tick=self._state['current_tick'],
                balance=self._state['balance'],
                position=dict(self._state['position']) if self._state['position'] else None,
                sidebet=dict(self._state['sidebet']) if self._state['sidebet'] else None,
                phase=self._state['current_phase'],
                price=self._state['current_price'],
                game_id=self._state['game_id'],
                metadata={
                    'bot_enabled': self._state['bot_enabled'],
                    'rugged': self._state['rugged']
                }
            )
    
    # ========== State Mutation Methods ==========
    
    def update(self, **kwargs) -> bool:
        """
        Update state with validation and notification
        Returns True if update was successful
        """
        with self._lock:
            old_state = self._state.copy()
            
            try:
                # Apply updates
                for key, value in kwargs.items():
                    if key in self._state:
                        self._state[key] = value
                    else:
                        logger.warning(f"Attempted to update unknown state key: {key}")
                
                # Validate new state
                if not self._validate_state():
                    # Rollback on validation failure
                    self._state = old_state
                    return False
                
                # Record history
                self._history.append(self.get_snapshot())
                
                # Notify observers of changes
                self._notify_changes(old_state, self._state)
                
                return True
                
            except Exception as e:
                logger.error(f"State update failed: {e}")
                self._state = old_state
                return False
    
    def update_balance(self, amount: Decimal, reason: str = "") -> bool:
        """Update balance with transaction logging"""
        with self._lock:
            old_balance = self._state['balance']
            new_balance = old_balance + amount
            
            if new_balance < 0:
                logger.warning(f"Balance would go negative: {new_balance}")
                return False
            
            self._state['balance'] = new_balance
            
            # Log transaction
            self._transaction_log.append({
                'timestamp': datetime.now(),
                'type': 'balance_change',
                'amount': amount,
                'old_balance': old_balance,
                'new_balance': new_balance,
                'reason': reason
            })
            
            # Update statistics
            if new_balance > self._stats['peak_balance']:
                self._stats['peak_balance'] = new_balance
            
            drawdown = (self._stats['peak_balance'] - new_balance) / self._stats['peak_balance']
            if drawdown > self._stats['max_drawdown']:
                self._stats['max_drawdown'] = drawdown
            
            # Notify observers
            self._emit(StateEvents.BALANCE_CHANGED, {
                'old': old_balance,
                'new': new_balance,
                'amount': amount
            })
            
            logger.info(f"Balance updated: {old_balance} -> {new_balance} ({reason})")
            return True
    
    def open_position(self, position_data) -> bool:
        """Open a new position or add to existing position (accepts Position object or dict)"""
        with self._lock:
            import time
            from models import Position

            # Convert Position object to dict if needed
            if isinstance(position_data, Position):
                new_entry_price = position_data.entry_price
                new_amount = position_data.amount
                new_entry_tick = position_data.entry_tick
            else:
                new_entry_price = position_data['entry_price']
                new_amount = position_data['amount']
                new_entry_tick = position_data.get('entry_tick', 0)

            # Check if we have enough balance for this purchase
            cost = new_amount * new_entry_price
            if cost > self._state['balance']:
                logger.warning(f"Insufficient balance for position: {cost} > {self._state['balance']}")
                return False

            # If we have an active position, add to it (average entry price)
            if self._state['position'] and self._state['position'].get('status') == 'active':
                existing = self._state['position']
                old_amount = existing['amount']
                old_entry_price = existing['entry_price']

                # Calculate weighted average entry price
                total_cost = (old_amount * old_entry_price) + (new_amount * new_entry_price)
                total_amount = old_amount + new_amount
                avg_entry_price = total_cost / total_amount

                # Update existing position
                existing['amount'] = total_amount
                existing['entry_price'] = avg_entry_price
                # Keep original entry time and tick from first position

                logger.info(f"Added to position: {new_amount} SOL at {new_entry_price}x (avg: {avg_entry_price:.4f}x)")
            else:
                # Create new position
                position_dict = {
                    'entry_price': new_entry_price,
                    'amount': new_amount,
                    'entry_time': time.time(),
                    'entry_tick': new_entry_tick,
                    'status': 'active'
                }
                self._state['position'] = position_dict
                self._stats['total_trades'] += 1
                logger.info(f"Opened position: {new_amount} SOL at {new_entry_price}x")

            # Deduct cost from balance
            self.update_balance(-cost, f"Bought {new_amount} SOL at {new_entry_price}x")

            self._emit(StateEvents.POSITION_OPENED, self._state['position'])
            return True
    
    def close_position(self, exit_price: Decimal, exit_time=None, exit_tick: int = 0) -> Optional[Dict]:
        """Close the active position (exit_time is optional for backwards compatibility)"""
        with self._lock:
            # exit_time is ignored in modular version (kept for test compatibility)
            position = self._state['position']
            if not position or position.get('status') != 'active':
                logger.warning("No active position to close")
                return None
            
            # Calculate P&L
            entry_value = position['amount'] * position['entry_price']
            exit_value = position['amount'] * exit_price
            pnl = exit_value - entry_value
            pnl_percent = ((exit_price / position['entry_price']) - 1) * 100
            
            # Update position
            position['status'] = 'closed'
            position['exit_price'] = exit_price
            position['exit_tick'] = exit_tick
            position['pnl_sol'] = pnl
            position['pnl_percent'] = pnl_percent
            
            # Update balance
            self.update_balance(exit_value, f"Position closed at {exit_price}")
            
            # Update statistics
            self._stats['total_pnl'] += pnl
            if pnl > 0:
                self._stats['winning_trades'] += 1
            else:
                self._stats['losing_trades'] += 1
            
            self._emit(StateEvents.POSITION_CLOSED, position)

            # Add to closed positions history
            self._closed_positions.append(position.copy())

            # Clear active position
            self._state['position'] = None

            return position
    
    def place_sidebet(self, amount_or_sidebet, tick=None, price=None) -> bool:
        """Place a side bet (accepts SideBet object or individual parameters)"""
        with self._lock:
            from models import SideBet

            if self._state['sidebet'] and self._state['sidebet'].get('status') == 'active':
                logger.warning("Cannot place sidebet: active sidebet exists")
                return False

            # Accept either SideBet object or individual parameters
            if isinstance(amount_or_sidebet, SideBet):
                amount = amount_or_sidebet.amount
                tick = amount_or_sidebet.placed_tick
                price = amount_or_sidebet.placed_price
            else:
                amount = amount_or_sidebet

            if amount > self._state['balance']:
                logger.warning(f"Insufficient balance for sidebet: {amount} > {self._state['balance']}")
                return False

            sidebet = {
                'amount': amount,
                'placed_tick': tick,
                'placed_price': price,
                'status': 'active'
            }

            self._state['sidebet'] = sidebet
            self.update_balance(-amount, "Sidebet placed")

            self._emit(StateEvents.SIDEBET_PLACED, sidebet)
            return True
    
    def resolve_sidebet(self, won: bool, tick: int) -> Optional[Dict]:
        """Resolve the active sidebet"""
        with self._lock:
            sidebet = self._state['sidebet']
            if not sidebet or sidebet.get('status') != 'active':
                return None

            sidebet['status'] = 'won' if won else 'lost'
            sidebet['resolved_tick'] = tick

            if won:
                winnings = sidebet['amount'] * Decimal('5.0')  # 5x multiplier
                self.update_balance(winnings, "Sidebet won")
                self._stats['sidebets_won'] += 1
            else:
                self._stats['sidebets_lost'] += 1

            # Track last resolved tick for cooldown
            self._state['last_sidebet_resolved_tick'] = tick

            self._emit(StateEvents.SIDEBET_RESOLVED, sidebet)
            self._state['sidebet'] = None

            return sidebet
    
    # ========== Observer Pattern ==========
    
    def subscribe(self, event: StateEvents, callback: Callable):
        """Subscribe to state change events"""
        with self._lock:
            self._observers[event].append(callback)
            logger.debug(f"Subscribed to {event.value}")
    
    def unsubscribe(self, event: StateEvents, callback: Callable):
        """Unsubscribe from state change events"""
        with self._lock:
            if callback in self._observers[event]:
                self._observers[event].remove(callback)
                logger.debug(f"Unsubscribed from {event.value}")
    
    def _emit(self, event: StateEvents, data: Any = None):
        """Emit an event to all subscribers"""
        for callback in self._observers[event]:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Observer callback error for {event.value}: {e}")
    
    def _notify_changes(self, old_state: Dict, new_state: Dict):
        """Detect and notify about state changes"""
        # Tick change
        if old_state['current_tick'] != new_state['current_tick']:
            self._emit(StateEvents.TICK_UPDATED, new_state['current_tick'])
        
        # Phase change
        if old_state['current_phase'] != new_state['current_phase']:
            self._emit(StateEvents.PHASE_CHANGED, new_state['current_phase'])
        
        # Rug event
        if not old_state['rugged'] and new_state['rugged']:
            self._emit(StateEvents.RUG_EVENT, new_state['current_tick'])
    
    # ========== Validation ==========
    
    def add_validator(self, validator: Callable[[Dict], bool]):
        """Add a state validator function"""
        self._validators.append(validator)
    
    def _validate_state(self) -> bool:
        """Validate current state against all validators"""
        for validator in self._validators:
            if not validator(self._state):
                return False
        
        # Built-in validations
        if self._state['balance'] < 0:
            logger.error("Invalid state: negative balance")
            return False
        
        if self._state['current_tick'] < 0:
            logger.error("Invalid state: negative tick")
            return False
        
        return True
    
    # ========== State Reset ==========
    
    def reset(self):
        """Reset state to initial values"""
        with self._lock:
            initial_balance = self._state['initial_balance']
            
            self._state = {
                'balance': initial_balance,
                'initial_balance': initial_balance,
                'position': None,
                'sidebet': None,
                'current_tick': 0,
                'current_price': Decimal('1.0'),
                'current_phase': 'UNKNOWN',
                'game_id': None,
                'game_active': False,
                'rugged': False,
                'bot_enabled': self._state.get('bot_enabled', False),
                'bot_strategy': self._state.get('bot_strategy'),
            }
            
            # Keep cumulative stats but reset per-game stats
            self._stats['games_played'] += 1

            self._history.clear()
            self._closed_positions.clear()

            self._emit(StateEvents.GAME_ENDED, None)
            logger.info("Game state reset")
    
    # ========== History and Analytics ==========
    
    def get_history(self, limit: Optional[int] = None) -> List[StateSnapshot]:
        """Get state history"""
        with self._lock:
            if limit:
                return self._history[-limit:]
            return self._history.copy()
    
    def get_transaction_log(self, limit: Optional[int] = None) -> List[Dict]:
        """Get transaction log"""
        with self._lock:
            if limit:
                return self._transaction_log[-limit:]
            return self._transaction_log.copy()
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics"""
        with self._lock:
            total_trades = self._stats['total_trades']
            if total_trades == 0:
                win_rate = Decimal('0')
                avg_win = Decimal('0')
                avg_loss = Decimal('0')
            else:
                win_rate = Decimal(self._stats['winning_trades']) / Decimal(total_trades)

                # Calculate average win/loss from transaction log
                wins = [t['amount'] for t in self._transaction_log
                       if t.get('reason', '').startswith('Position closed') and t['amount'] > 0]
                losses = [abs(t['amount']) for t in self._transaction_log
                         if t.get('reason', '').startswith('Position closed') and t['amount'] < 0]

                avg_win = sum(wins) / len(wins) if wins else Decimal('0')
                avg_loss = sum(losses) / len(losses) if losses else Decimal('0')

            return {
                'total_pnl': self._stats['total_pnl'],
                'win_rate': win_rate,
                'max_drawdown': self._stats['max_drawdown'],
                'total_trades': total_trades,
                'average_win': avg_win,
                'average_loss': avg_loss,
                'current_balance': self._state['balance'],
                'roi': (self._state['balance'] - self._state['initial_balance']) / self._state['initial_balance']
            }

    # ========== Bot Interface Compatibility Methods ==========

    def has_active_position(self) -> bool:
        """Check if has active position (bot interface compatibility)"""
        with self._lock:
            position = self._state.get('position')
            return position is not None and position.get('status') == 'active'

    def has_active_sidebet(self) -> bool:
        """Check if has active sidebet (bot interface compatibility)"""
        with self._lock:
            sidebet = self._state.get('sidebet')
            return sidebet is not None and sidebet.get('status') == 'active'

    @property
    def active_position(self):
        """Get active position as property (bot interface compatibility)"""
        with self._lock:
            position = self._state.get('position')
            if position and position.get('status') == 'active':
                # Convert to Position-like object for bot interface
                from models import Position
                import time
                return Position(
                    entry_price=position['entry_price'],
                    amount=position['amount'],
                    entry_time=position.get('entry_time', time.time()),
                    entry_tick=position['entry_tick']
                )
            return None

    @property
    def active_sidebet(self):
        """Get active sidebet as property (bot interface compatibility)"""
        with self._lock:
            sidebet = self._state.get('sidebet')
            if sidebet and sidebet.get('status') == 'active':
                # Convert to SideBet-like object for bot interface
                from models import SideBet
                return SideBet(
                    amount=sidebet['amount'],
                    placed_tick=sidebet['placed_tick'],
                    placed_price=sidebet['placed_price']
                )
            return None

    @property
    def current_tick(self):
        """Get current tick as property (bot interface compatibility)"""
        with self._lock:
            # Return stored tick object if available, otherwise create from state
            stored_tick = self._state.get('_current_tick_object')
            if stored_tick:
                return stored_tick

            # Fallback: create from state data
            from models import GameTick
            return GameTick(
                tick=self._state.get('current_tick', 0),
                price=self._state.get('current_price', Decimal('1.0')),
                phase=self._state.get('current_phase', 'UNKNOWN'),
                active=self._state.get('game_active', False),
                rugged=self._state.get('rugged', False),
                trade_count=0
            )

    @current_tick.setter
    def current_tick(self, tick):
        """Set current tick object (replay engine compatibility)"""
        with self._lock:
            # Store the GameTick object directly
            self._state['_current_tick_object'] = tick

    @property
    def balance(self) -> Decimal:
        """Get current balance as property (bot interface compatibility)"""
        with self._lock:
            return self._state.get('balance', Decimal('0'))

    @property
    def initial_balance(self) -> Decimal:
        """Get initial balance as property (bot interface compatibility)"""
        with self._lock:
            return self._state.get('initial_balance', Decimal('0.100'))

    @property
    def session_pnl(self) -> Decimal:
        """Get session P&L as property (bot interface compatibility)"""
        with self._lock:
            return self._stats.get('total_pnl', Decimal('0'))

    @property
    def current_game_id(self) -> Optional[str]:
        """Get current game ID as property (bot interface compatibility)"""
        with self._lock:
            return self._state.get('game_id')

    @property
    def _current_tick_index(self) -> int:
        """Get current tick index (bot interface compatibility)"""
        with self._lock:
            return self._state.get('current_tick', 0)

    @property
    def _current_game(self) -> List:
        """Get current game (bot interface compatibility)"""
        # Return empty list as replay engine manages this
        return []

    @property
    def _last_sidebet_resolved_tick(self) -> Optional[int]:
        """Get last sidebet resolved tick (bot interface compatibility)"""
        with self._lock:
            # Track this in state if needed
            return self._state.get('last_sidebet_resolved_tick')

    def get_position_history(self) -> List[Dict]:
        """Get history of closed positions (compatibility method)"""
        with self._lock:
            # Track closed positions separately for backwards compatibility
            if not hasattr(self, '_closed_positions'):
                self._closed_positions = []
            return self._closed_positions.copy()
