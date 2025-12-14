"""
Game State Management Module
Centralized state management with observer pattern for reactive updates
"""

from typing import Dict, Any, List, Optional, Callable, Deque
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
import threading
from collections import defaultdict, deque
import logging
from enum import Enum

from config import config

logger = logging.getLogger(__name__)

# AUDIT FIX: Bounded history to prevent unbounded memory growth
MAX_HISTORY_SIZE = config.MEMORY.get('max_state_history', 1000)  # Configurable cap
MAX_TRANSACTION_LOG_SIZE = 1000  # Max transactions to keep
MAX_CLOSED_POSITIONS_SIZE = 500  # Max closed positions to keep


class StateEvents(Enum):
    """Events that can be emitted by state changes"""
    BALANCE_CHANGED = "balance_changed"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    POSITION_REDUCED = "position_reduced"  # Phase 8.1
    SIDEBET_PLACED = "sidebet_placed"
    SIDEBET_RESOLVED = "sidebet_resolved"
    TICK_UPDATED = "tick_updated"
    GAME_STARTED = "game_started"
    GAME_ENDED = "game_ended"
    RUG_EVENT = "rug_event"
    PHASE_CHANGED = "phase_changed"
    BOT_ACTION = "bot_action"
    SELL_PERCENTAGE_CHANGED = "sell_percentage_changed"  # Phase 8.1
    STATE_RECONCILED = "state_reconciled"  # Phase 11: Server state sync

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
    active: bool = False
    rugged: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

class GameState:
    """
    Centralized game state management with thread-safe operations
    and observer pattern for reactive updates
    """
    
    def __init__(self, initial_balance: Decimal = Decimal('0.100')):
        # Core state
        self._state = self._build_initial_state(initial_balance)

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

        # History - AUDIT FIX: Use deque with maxlen for O(1) bounded memory
        self._history: Deque[StateSnapshot] = deque(maxlen=MAX_HISTORY_SIZE)
        self._transaction_log: Deque[Dict] = deque(maxlen=MAX_TRANSACTION_LOG_SIZE)
        self._closed_positions: Deque[Dict] = deque(maxlen=MAX_CLOSED_POSITIONS_SIZE)
        
        # Observer pattern
        self._observers: Dict[StateEvents, List[Callable]] = defaultdict(list)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # State validation rules
        self._validators: List[Callable] = []
        
        logger.info(f"GameState initialized with balance: {initial_balance}")

    def _build_initial_state(
        self,
        initial_balance: Decimal,
        bot_enabled: Optional[bool] = None,
        bot_strategy: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a fresh state dictionary with optional bot flags preserved."""
        return {
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
            'bot_enabled': False if bot_enabled is None else bot_enabled,
            'bot_strategy': bot_strategy,
            'last_sidebet_resolved_tick': None,
            'sell_percentage': Decimal('1.0')  # Phase 8.1: Default 100%
        }
    
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
                active=self._state.get('game_active', False),
                rugged=self._state.get('rugged', False),
                metadata={
                    'bot_enabled': self._state['bot_enabled']
                }
            )

    def get_current_tick(self):
        """
        Get current tick as a GameTick object (for TradeManager compatibility)
        Constructs a GameTick from current state data
        """
        from models import GameTick
        with self._lock:
            return GameTick.from_dict({
                'game_id': self._state.get('game_id', 'unknown'),
                'tick': self._state.get('current_tick', 0),
                'timestamp': '',  # Not tracked in state (used for JSONL only)
                'price': float(self._state.get('current_price', Decimal('1.0'))),
                'phase': self._state.get('current_phase', 'UNKNOWN'),
                'active': self._state.get('game_active', False),
                'rugged': self._state.get('rug_detected', False),  # Fixed field name
                'cooldown_timer': 0,  # Not tracked in state
                'trade_count': 0,  # Not tracked in state
            })

    def capture_demo_snapshot(self, bet_amount: Decimal) -> 'DemoStateSnapshot':
        """
        Capture state snapshot for demo recording (Phase 10).

        Returns models.demo_action.StateSnapshot with all state context
        needed for imitation learning.

        Args:
            bet_amount: Current bet amount from UI (not tracked in GameState)

        Returns:
            StateSnapshot from models.demo_action (not core.game_state.StateSnapshot)
        """
        from models.demo_action import StateSnapshot as DemoStateSnapshot

        with self._lock:
            # Convert position to dict with string Decimals for JSON
            position_dict = None
            if self._state['position']:
                pos = self._state['position']
                position_dict = {
                    'entry_price': str(pos.get('entry_price', Decimal('0'))),
                    'amount': str(pos.get('amount', Decimal('0'))),
                    'entry_tick': pos.get('entry_tick', 0),
                    'entry_time': pos.get('entry_time'),
                }

            # Convert sidebet to dict with string Decimals for JSON
            sidebet_dict = None
            if self._state['sidebet']:
                sb = self._state['sidebet']
                sidebet_dict = {
                    'amount': str(sb.get('amount', Decimal('0'))),
                    'placed_tick': sb.get('placed_tick', 0),
                    'placed_time': sb.get('placed_time'),
                }

            return DemoStateSnapshot(
                balance=self._state['balance'],
                position=position_dict,
                sidebet=sidebet_dict,
                bet_amount=bet_amount,
                sell_percentage=self._state.get('sell_percentage', Decimal('1.0')),
                current_tick=self._state.get('current_tick', 0),
                current_price=self._state.get('current_price', Decimal('1.0')),
                phase=self._state.get('current_phase', 'UNKNOWN'),
            )

    def capture_local_snapshot(self, bet_amount: Decimal) -> 'LocalStateSnapshot':
        """
        Capture state snapshot for Phase 10.6 validation-aware recording.

        Returns LocalStateSnapshot with all state context needed for
        zero-tolerance validation against server state.

        Args:
            bet_amount: Current bet amount from UI (not tracked in GameState)

        Returns:
            LocalStateSnapshot from models.recording_models
        """
        from models.recording_models import LocalStateSnapshot

        with self._lock:
            # Get position details
            position_qty = Decimal('0')
            position_entry_price = None
            position_pnl = None

            if self._state['position']:
                pos = self._state['position']
                position_qty = pos.get('amount', Decimal('0'))
                position_entry_price = pos.get('entry_price')
                # Calculate PnL if we have entry price and current price
                if position_entry_price and self._state.get('current_price'):
                    current_price = self._state['current_price']
                    position_pnl = (current_price - position_entry_price) * position_qty

            # Get sidebet details
            sidebet_active = False
            sidebet_amount = None

            if self._state['sidebet']:
                sb = self._state['sidebet']
                sidebet_active = True
                sidebet_amount = sb.get('amount', Decimal('0'))

            return LocalStateSnapshot(
                balance=self._state['balance'],
                position_qty=position_qty,
                position_entry_price=position_entry_price,
                position_pnl=position_pnl,
                sidebet_active=sidebet_active,
                sidebet_amount=sidebet_amount,
                bet_amount=bet_amount,
                sell_percentage=self._state.get('sell_percentage', Decimal('1.0')),
                current_tick=self._state.get('current_tick', 0),
                current_price=self._state.get('current_price', Decimal('1.0')),
                phase=self._state.get('current_phase', 'UNKNOWN'),
            )

    # ========== Phase 11: Server State Reconciliation ==========

    def reconcile_with_server(self, server_state: 'ServerState') -> Dict[str, Any]:
        """
        Reconcile local state with server truth (Phase 11).

        The server (playerUpdate WebSocket event) is the source of truth.
        This method updates local state to match server and returns any drift detected.

        Args:
            server_state: ServerState object from WebSocket playerUpdate

        Returns:
            Dict of any drift detected: {'field': {'local': x, 'server': y}}
        """
        from models.recording_models import ServerState

        drifts = {}
        with self._lock:
            # Balance reconciliation
            server_cash = server_state.cash
            local_balance = self._state['balance']
            if local_balance != server_cash:
                drifts['balance'] = {
                    'local': local_balance,
                    'server': server_cash,
                    'diff': abs(local_balance - server_cash)
                }
                self._state['balance'] = server_cash
                logger.info(f"Balance reconciled: {local_balance} -> {server_cash}")

            # Position reconciliation
            server_position_qty = server_state.position_qty
            server_avg_cost = server_state.avg_cost

            if server_position_qty == Decimal('0'):
                # Server says no position
                if self._state['position'] and self._state['position'].get('status') == 'active':
                    drifts['position'] = {
                        'local': 'active',
                        'server': 'none',
                        'local_qty': self._state['position'].get('amount', Decimal('0'))
                    }
                    self._state['position'] = None
                    logger.info("Position reconciled: closed (server has no position)")
            else:
                # Server says we have a position
                if not self._state['position'] or self._state['position'].get('status') != 'active':
                    # Local has no position but server does - create one
                    self._state['position'] = {
                        'entry_price': server_avg_cost,
                        'amount': server_position_qty,
                        'entry_tick': self._state.get('current_tick', 0),
                        'status': 'active'
                    }
                    drifts['position'] = {
                        'local': 'none',
                        'server': 'active',
                        'server_qty': server_position_qty
                    }
                    logger.info(f"Position reconciled: opened from server (qty={server_position_qty})")
                else:
                    # Both have position - check for qty/price drift
                    local_qty = self._state['position'].get('amount', Decimal('0'))
                    local_entry = self._state['position'].get('entry_price', Decimal('0'))

                    if local_qty != server_position_qty:
                        drifts['position_qty'] = {
                            'local': local_qty,
                            'server': server_position_qty,
                            'diff': abs(local_qty - server_position_qty)
                        }
                        self._state['position']['amount'] = server_position_qty
                        logger.info(f"Position qty reconciled: {local_qty} -> {server_position_qty}")

                    if local_entry != server_avg_cost and server_avg_cost > 0:
                        drifts['entry_price'] = {
                            'local': local_entry,
                            'server': server_avg_cost,
                            'diff': abs(local_entry - server_avg_cost)
                        }
                        self._state['position']['entry_price'] = server_avg_cost
                        logger.info(f"Entry price reconciled: {local_entry} -> {server_avg_cost}")

        # Emit event outside lock to prevent deadlocks
        if drifts:
            self._emit(StateEvents.STATE_RECONCILED, drifts)
            logger.warning(f"State drift detected and reconciled: {list(drifts.keys())}")

        return drifts

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
                
                # Record history (AUDIT FIX: deque auto-evicts when maxlen reached)
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

            # Log transaction (AUDIT FIX: bounded)
            # AUDIT FIX: deque auto-evicts when maxlen reached
            self._transaction_log.append({
                'timestamp': datetime.now(),
                'type': 'balance_change',
                'amount': amount,
                'old_balance': old_balance,
                'new_balance': new_balance,
                'reason': reason
            })

            # Update statistics
            # Track session P&L (cumulative balance changes)
            self._stats['total_pnl'] += amount

            if new_balance > self._stats['peak_balance']:
                self._stats['peak_balance'] = new_balance

            if self._stats['peak_balance'] > 0:
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

    def set_baseline_balance(self, new_baseline: Decimal, reason: str = "Manual baseline set"):
        """
        Set a new baseline balance for P&L tracking.

        This updates the initial_balance which is used for:
        - ROI calculations
        - Reset operations (bankruptcy recovery)
        - Session P&L tracking baseline

        Args:
            new_baseline: The new baseline balance
            reason: Reason for the change (for logging)
        """
        with self._lock:
            old_initial = self._state['initial_balance']

            # Update initial balance (the baseline for P&L)
            self._state['initial_balance'] = new_baseline

            # Reset P&L stats since we're starting fresh from this baseline
            self._stats['total_pnl'] = Decimal('0')
            self._stats['peak_balance'] = new_baseline
            self._stats['max_drawdown'] = Decimal('0')

            # Log the transaction
            self._transaction_log.append({
                'timestamp': datetime.now(),
                'type': 'baseline_reset',
                'old_baseline': old_initial,
                'new_baseline': new_baseline,
                'reason': reason
            })

            logger.info(
                f"Baseline balance set: {old_initial} -> {new_baseline} ({reason}). "
                f"P&L tracking reset to 0."
            )

            # Emit event for any listeners
            self._emit(StateEvents.BALANCE_CHANGED, {
                'old': old_initial,
                'new': new_baseline,
                'baseline_reset': True
            })

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
                new_entry_time = position_data.entry_time  # Preserve from Position object
            else:
                new_entry_price = position_data['entry_price']
                new_amount = position_data['amount']
                new_entry_tick = position_data.get('entry_tick', 0)
                new_entry_time = position_data.get('entry_time', time.time())

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
                    'entry_time': new_entry_time,
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
    
    def close_position(self, exit_price: Decimal, exit_time=None, exit_tick: Optional[int] = None) -> Optional[Dict]:
        """Close the active position (exit_time maintained for backwards compatibility)"""
        with self._lock:
            # exit_time is ignored in modular version (kept for test compatibility)
            position = self._state['position']
            if not position or position.get('status') != 'active':
                logger.warning("No active position to close")
                return None
            
            if exit_tick is None:
                exit_tick = self._state.get('current_tick', 0)
            
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
            
            # Update balance (P&L automatically tracked via update_balance)
            self.update_balance(exit_value, f"Position closed at {exit_price}")

            # Update statistics (AUDIT FIX: removed duplicate total_pnl update - already tracked in update_balance)
            if pnl > 0:
                self._stats['winning_trades'] += 1
            else:
                self._stats['losing_trades'] += 1
            
            self._emit(StateEvents.POSITION_CLOSED, position)

            # Add to closed positions history (AUDIT FIX: deque auto-evicts when maxlen reached)
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
    
    def resolve_sidebet(self, won: bool, tick: Optional[int] = None) -> Optional[Dict]:
        """Resolve the active sidebet"""
        with self._lock:
            sidebet = self._state['sidebet']
            if not sidebet or sidebet.get('status') != 'active':
                return None

            if tick is None:
                tick = self._state.get('current_tick', 0)

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

    # ========== Sell Percentage Management (Phase 8.1) ==========

    def set_sell_percentage(self, percentage: Decimal) -> bool:
        """
        Set the sell percentage (for partial position closing)

        Args:
            percentage: Percentage to sell (0.1, 0.25, 0.5, or 1.0)

        Returns:
            True if successful, False if invalid percentage
        """
        with self._lock:
            # Validate percentage (only allow 10%, 25%, 50%, 100%)
            valid_percentages = [Decimal('0.1'), Decimal('0.25'), Decimal('0.5'), Decimal('1.0')]
            if percentage not in valid_percentages:
                logger.error(f"Invalid sell percentage: {percentage}. Must be one of {valid_percentages}")
                return False

            old_percentage = self._state['sell_percentage']
            self._state['sell_percentage'] = percentage

            # Emit event
            self._emit(StateEvents.SELL_PERCENTAGE_CHANGED, {
                'old': old_percentage,
                'new': percentage
            })

            logger.info(f"Sell percentage changed: {old_percentage*100:.0f}% -> {percentage*100:.0f}%")
            return True

    def get_sell_percentage(self) -> Decimal:
        """
        Get the current sell percentage

        Returns:
            Current sell percentage (0.1 to 1.0)
        """
        with self._lock:
            return self._state.get('sell_percentage', Decimal('1.0'))

    def partial_close_position(
        self,
        percentage: Decimal,
        exit_price: Decimal,
        exit_time=None,
        exit_tick: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Partially close the active position (Phase 8.1)

        Args:
            percentage: Percentage of position to close (0.1 to 1.0)
            exit_price: Exit price multiplier
            exit_time: Exit timestamp (maintained for backwards compatibility)
            exit_tick: Exit tick number

        Returns:
            Dictionary with partial close details, or None if no active position
        """
        with self._lock:
            position = self._state['position']
            if not position or position.get('status') != 'active':
                logger.warning("No active position to partially close")
                return None

            if exit_tick is None:
                exit_tick = self._state.get('current_tick', 0)

            # Validate percentage
            valid_percentages = [Decimal('0.1'), Decimal('0.25'), Decimal('0.5'), Decimal('1.0')]
            if percentage not in valid_percentages:
                logger.error(f"Invalid percentage: {percentage}. Must be one of {valid_percentages}")
                return None

            # If 100%, use normal close_position
            if percentage == Decimal('1.0'):
                return self.close_position(exit_price, exit_time, exit_tick)

            # Calculate partial amounts
            original_amount = position['amount']
            amount_to_sell = original_amount * percentage
            remaining_amount = original_amount - amount_to_sell

            # Calculate P&L for the portion being sold
            entry_value = amount_to_sell * position['entry_price']
            exit_value = amount_to_sell * exit_price
            pnl = exit_value - entry_value
            pnl_percent = ((exit_price / position['entry_price']) - 1) * 100

            # Update position with reduced amount
            position['amount'] = remaining_amount

            # Update balance (add proceeds from partial sell)
            self.update_balance(exit_value, f"Partial sell ({percentage*100:.0f}%) at {exit_price}")

            # Update statistics (partial sell counts as a trade)
            if pnl > 0:
                self._stats['winning_trades'] += 1
            else:
                self._stats['losing_trades'] += 1

            # Create partial close record
            partial_close = {
                'type': 'partial_close',
                'percentage': percentage,
                'amount_sold': amount_to_sell,
                'remaining_amount': remaining_amount,
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'exit_tick': exit_tick,
                'pnl_sol': pnl,
                'pnl_percent': pnl_percent
            }

            # Emit event
            self._emit(StateEvents.POSITION_REDUCED, partial_close)

            logger.info(
                f"Partial close ({percentage*100:.0f}%): "
                f"Sold {amount_to_sell} SOL at {exit_price}, "
                f"Remaining {remaining_amount} SOL, "
                f"P&L: {pnl} SOL ({pnl_percent:.1f}%)"
            )

            return partial_close

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
        """Emit an event to all subscribers (releases lock before calling callbacks)"""
        # Get callbacks while holding lock, then release before calling
        with self._lock:
            callbacks = list(self._observers[event])  # Copy to avoid mutation during iteration

        # Call callbacks WITHOUT holding lock to prevent deadlocks
        for callback in callbacks:
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
            bot_enabled = self._state.get('bot_enabled', False)
            bot_strategy = self._state.get('bot_strategy')
            game_was_active = self._state.get('game_id') is not None
            
            self._state = self._build_initial_state(
                initial_balance,
                bot_enabled=bot_enabled,
                bot_strategy=bot_strategy
            )
            
            if game_was_active:
                self._stats['games_played'] += 1

            self._history.clear()
            self._closed_positions.clear()

            logger.info("Game state reset")
    
    # ========== History and Analytics ==========
    
    def get_history(self, limit: Optional[int] = None) -> List[StateSnapshot]:
        """Get state history (AUDIT FIX: works with deque)"""
        with self._lock:
            history_list = list(self._history)
            if limit:
                return history_list[-limit:]
            return history_list

    def get_transaction_log(self, limit: Optional[int] = None) -> List[Dict]:
        """Get transaction log (AUDIT FIX: works with deque)"""
        with self._lock:
            log_list = list(self._transaction_log)
            if limit:
                return log_list[-limit:]
            return log_list
    
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
                
                wins = [
                    pos['pnl_sol'] for pos in self._closed_positions
                    if pos.get('pnl_sol') is not None and pos['pnl_sol'] > 0
                ]
                losses = [
                    abs(pos['pnl_sol']) for pos in self._closed_positions
                    if pos.get('pnl_sol') is not None and pos['pnl_sol'] < 0
                ]

                avg_win = (sum(wins) / len(wins)) if wins else Decimal('0')
                avg_loss = (sum(losses) / len(losses)) if losses else Decimal('0')

            initial_balance = self._state['initial_balance']
            roi = Decimal('0')
            if initial_balance:
                roi = (self._state['balance'] - initial_balance) / initial_balance

            return {
                'total_pnl': self._stats['total_pnl'],
                'win_rate': win_rate,
                'max_drawdown': self._stats['max_drawdown'],
                'total_trades': total_trades,
                'average_win': avg_win,
                'average_loss': avg_loss,
                'current_balance': self._state['balance'],
                'roi': roi
            }

    # ========== Test Helpers ==========

    def get_position_history(self) -> List:
        """Get history of closed positions (returns Position objects) - Used by Tests"""
        with self._lock:
            from models import Position
            # Track closed positions separately for backwards compatibility
            if not hasattr(self, '_closed_positions'):
                self._closed_positions = []
            # Convert dicts to Position objects
            return [
                Position(
                    entry_price=p['entry_price'],
                    amount=p['amount'],
                    entry_time=p['entry_time'],
                    entry_tick=p['entry_tick'],
                    status=p.get('status', 'active'),
                    exit_price=p.get('exit_price'),
                    exit_time=p.get('exit_time'),
                    exit_tick=p.get('exit_tick'),
                    pnl_sol=p.get('pnl_sol'),
                    pnl_percent=p.get('pnl_percent')
                )
                for p in self._closed_positions
            ]
