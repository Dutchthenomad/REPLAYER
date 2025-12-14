"""
Real-Time WebSocket Feed for Rugs.fun

Python port of the Socket.IO real-time collector.
Provides noise-free, tick-by-tick game state updates.

Usage:
    feed = WebSocketFeed()
    feed.connect()

    # Get latest signal
    signal = feed.get_last_signal()
    print(f"Price: {signal['price']:.4f}x")

    # Or use callbacks
    @feed.on('signal')
    def handle_signal(signal):
        print(f"Tick {signal['tickCount']}: {signal['price']:.4f}x")
"""

import socketio
import time
import threading
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import logging
from decimal import Decimal
from collections import deque  # AUDIT FIX: For efficient latency tracking

# REPLAYER imports
from models import GameTick

# Phase 10.4A: Extracted modules
from sources.feed_monitors import (
    LatencySpikeDetector,
    ConnectionHealth,
    ConnectionHealthMonitor
)
from sources.feed_rate_limiter import (
    TokenBucketRateLimiter,
    PriorityRateLimiter
)
from sources.feed_degradation import (
    OperatingMode,
    GracefulDegradationManager
)

# Phase 3 refactoring: GameSignal and GameStateMachine extracted to own module
from sources.game_state_machine import GameSignal, GameStateMachine

logger = logging.getLogger(__name__)

# Hardcoded credentials for Dutch (workaround for unauthenticated WebSocket)
# The server only sends usernameStatus to authenticated clients, so we
# pre-configure the identity and extract state from gameStatePlayerUpdate events
HARDCODED_PLAYER_ID = "did:privy:cmaibr7rt0094jp0mc2mbpfu4"
HARDCODED_USERNAME = "Dutch"


class WebSocketFeed:
    """Real-time WebSocket feed for Rugs.fun game state"""

    def __init__(self, log_level: str = 'INFO', rate_limit: float = 20.0):
        """
        Initialize WebSocket feed

        Args:
            log_level: Logging level (DEBUG, INFO, WARN, ERROR)
            rate_limit: Max signals per second (PHASE 3.1 AUDIT FIX)
        """
        self.server_url = 'https://backend.rugs.fun?frontend-version=1.0'

        # AUDIT FIX: Configure Socket.IO with heartbeat and reconnection
        self.sio = socketio.Client(
            logger=False,
            engineio_logger=False,
            reconnection=True,              # Enable automatic reconnection
            reconnection_attempts=10,       # Max 10 reconnection attempts
            reconnection_delay=1,           # Start with 1s delay
            reconnection_delay_max=10,      # Max 10s delay (exponential backoff)
        )
        self.state_machine = GameStateMachine()

        # PHASE 3.1 AUDIT FIX: Rate limiter to prevent data floods (with critical bypass)
        self.rate_limiter = PriorityRateLimiter(rate=rate_limit)

        # PHASE 3.2 AUDIT FIX: Connection health monitor
        self.health_monitor = ConnectionHealthMonitor()

        # PHASE 3.5 AUDIT FIX: Latency spike detector
        self.spike_detector = LatencySpikeDetector()

        # PHASE 3.6 AUDIT FIX: Graceful degradation manager
        self.degradation_manager = GracefulDegradationManager()
        self.degradation_manager.on_mode_change = self._on_mode_change

        # Metrics
        self.metrics = {
            'start_time': time.time(),
            'total_signals': 0,
            'total_ticks': 0,
            'total_games': 0,
            'noise_filtered': 0,
            'latencies': deque(maxlen=1000),  # AUDIT FIX: O(1) operations, extended history
            'phase_transitions': 0,
            'anomalies': 0,
            'errors': 0,  # AUDIT FIX: Track callback errors
            'rate_limited': 0,  # PHASE 3.1: Track rate-limited signals
            'latency_spikes': 0  # PHASE 3.5: Track latency spikes
        }

        # State
        self.last_signal: Optional[GameSignal] = None
        self.last_tick_time = None
        self.is_connected = False
        self.event_handlers = {}

        # Phase 10.7: Player state tracking
        self.player_id: Optional[str] = None
        self.username: Optional[str] = None
        self.last_player_update: Optional[Dict[str, Any]] = None

        # Phase 10.8: Authentication state tracking
        self._identity_confirmed = False  # True once usernameStatus OR playerLeaderboardPosition received
        self._identity_source: Optional[str] = None  # 'usernameStatus' or 'leaderboard'
        self._last_known_balance: Optional[float] = None  # From playerUpdate
        self._last_server_state: Optional[Dict[str, Any]] = None  # Phase 11: Full server state for reconciliation
        self._profile_cache_path = self._get_profile_cache_path()

        # AUDIT FIX: Guard to prevent duplicate event listener registration
        self._listeners_setup = False

        # Setup logging (MUST be before _load_cached_profile)
        self.logger = logging.getLogger('WebSocketFeed')
        self.logger.setLevel(getattr(logging, log_level.upper()))
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Load cached profile as fallback (after logger setup)
        self._load_cached_profile()

        # Setup Socket.IO event handlers
        self._setup_event_listeners()

    def _on_mode_change(self, old_mode: str, new_mode: str):
        """
        PHASE 3.6: Handle operating mode changes.

        Args:
            old_mode: Previous operating mode
            new_mode: New operating mode
        """
        self.logger.warning(f'🔄 Operating mode changed: {old_mode} → {new_mode}')
        self._emit_event('mode_change', {
            'old_mode': old_mode,
            'new_mode': new_mode,
            'status': self.degradation_manager.get_status()
        })

    # ========================================================================
    # PHASE 10.8: Profile Cache Methods
    # ========================================================================

    def _get_profile_cache_path(self) -> str:
        """Get path to profile cache file"""
        import os
        from pathlib import Path
        config_dir = Path(os.getenv('RUGS_CONFIG_DIR', str(Path.home() / '.rugs_viewer')))
        config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir / 'profile_cache.json')

    def _load_cached_profile(self):
        """Load cached profile as fallback (doesn't confirm identity, just shows last known)"""
        import json
        try:
            with open(self._profile_cache_path, 'r') as f:
                data = json.load(f)
                # Store as "last known" but don't confirm identity
                self._cached_player_id = data.get('player_id')
                self._cached_username = data.get('username')
                self._cached_balance = data.get('last_balance')
                if self._cached_username:
                    self.logger.info(f"📋 Cached profile loaded: {self._cached_username}")
        except (FileNotFoundError, json.JSONDecodeError):
            self._cached_player_id = None
            self._cached_username = None
            self._cached_balance = None

    def _save_profile_cache(self):
        """Save current profile to cache for redundancy"""
        import json
        if not self.player_id or not self.username:
            return
        try:
            data = {
                'player_id': self.player_id,
                'username': self.username,
                'last_balance': self._last_known_balance,
                'updated_at': datetime.now().isoformat()
            }
            with open(self._profile_cache_path, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.debug(f"Profile cache saved: {self.username}")
        except Exception as e:
            self.logger.error(f"Failed to save profile cache: {e}")

    def _confirm_identity(self, player_id: str, username: str, source: str):
        """
        Confirm player identity and display prominent terminal output.

        Args:
            player_id: Player's Privy DID
            username: Display name
            source: Source of identity ('usernameStatus' or 'leaderboard')
        """
        # Skip if already confirmed with same identity
        if self._identity_confirmed and self.player_id == player_id:
            return

        self.player_id = player_id
        self.username = username
        self._identity_confirmed = True
        self._identity_source = source

        # Save to cache for redundancy
        self._save_profile_cache()

        # CLEAR TERMINAL OUTPUT - Identity Confirmation
        player_id_short = player_id[:30] + '...' if len(player_id) > 30 else player_id
        print("\n" + "=" * 60)
        print("✅ PLAYER IDENTITY CONFIRMED")
        print("=" * 60)
        print(f"   Username:  {username}")
        print(f"   Player ID: {player_id_short}")
        print(f"   Source:    {source}")
        if self._last_known_balance is not None:
            print(f"   Balance:   {self._last_known_balance:.4f} SOL")
        print("=" * 60 + "\n")

        # Also log at WARNING level for log files
        self.logger.warning(f"✅ IDENTITY CONFIRMED: {username} ({player_id_short}) via {source}")

        # Emit event
        self._emit_event('player_identity', {
            'player_id': player_id,
            'username': username,
            'source': source,
            'confirmed': True
        })

    def _update_balance(self, cash: float, source: str = 'playerUpdate'):
        """Update known balance and display if changed significantly"""
        old_balance = self._last_known_balance
        self._last_known_balance = cash

        # Save updated balance to cache
        self._save_profile_cache()

        # Only print if balance changed significantly (>0.0001 SOL)
        if old_balance is None or abs(cash - old_balance) > 0.0001:
            self.logger.warning(f"💰 Balance: {cash:.4f} SOL (via {source})")

    def get_authentication_status(self) -> Dict[str, Any]:
        """Get current authentication status for UI display"""
        return {
            'confirmed': self._identity_confirmed,
            'player_id': self.player_id,
            'username': self.username,
            'source': self._identity_source,
            'balance': self._last_known_balance,
            'cached_username': getattr(self, '_cached_username', None),
            'cached_balance': getattr(self, '_cached_balance', None)
        }

    def get_last_server_state(self) -> Optional['ServerState']:
        """
        Get the last known server state for reconciliation (Phase 11).

        Returns ServerState object if available, None if no playerUpdate received yet.
        """
        if self._last_server_state is None:
            return None

        from decimal import Decimal
        from models.recording_models import ServerState

        return ServerState(
            cash=Decimal(str(self._last_server_state.get('cash', 0))),
            position_qty=Decimal(str(self._last_server_state.get('positionQty', 0))),
            avg_cost=Decimal(str(self._last_server_state.get('avgCost', 0))),
            cumulative_pnl=Decimal(str(self._last_server_state.get('cumulativePnL', 0))),
            total_invested=Decimal(str(self._last_server_state.get('totalInvested', 0))),
        )

    def _setup_event_listeners(self):
        """
        Setup Socket.IO event listeners

        AUDIT FIX: Guard against duplicate event listener registration.
        If called multiple times (e.g., on reconnect), this prevents
        handler accumulation and memory leaks.
        """
        # AUDIT FIX: Prevent duplicate event listener registration
        if self._listeners_setup:
            self.logger.debug("Event listeners already set up, skipping duplicate registration")
            return

        self._listeners_setup = True

        @self.sio.event
        def connect():
            # AUDIT FIX: Error boundary for connection handler
            try:
                self.is_connected = True
                # PHASE 3.2: Update health monitor
                self.health_monitor.set_connected(True)
                self.logger.info('✅ Connected to Rugs.fun backend')
                self.logger.info(f'   Socket ID: {self.sio.sid}')

                # Auto-confirm identity using hardcoded credentials
                # (Server doesn't send usernameStatus to unauthenticated clients)
                self._confirm_identity(
                    HARDCODED_PLAYER_ID,
                    HARDCODED_USERNAME,
                    'hardcoded_credentials'
                )

                self._emit_event('connected', {'socketId': self.sio.sid})
            except Exception as e:
                self.logger.error(f"Error in connect handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        @self.sio.event
        def disconnect(reason=None):
            # AUDIT FIX: Error boundary for disconnect handler
            # FIX 2025-12-01: Accept optional reason argument (newer Socket.IO versions pass it)
            try:
                self.is_connected = False
                # PHASE 3.2: Update health monitor
                self.health_monitor.set_connected(False)
                # PHASE 3.4: Initiate state machine recovery
                recovery_info = self.state_machine.recover_from_disconnect()
                # PHASE 3.6: Notify degradation manager
                self.degradation_manager.record_disconnect()
                # FIX: Reset latency baseline to prevent spike spam on reconnect
                self.last_tick_time = None
                self.spike_detector.latencies.clear()
                self.spike_detector.total_samples = 0
                reason_str = f' (reason: {reason})' if reason else ''
                self.logger.warning(f'❌ Disconnected from backend{reason_str}')
                self._emit_event('disconnected', {'recovery_info': recovery_info, 'reason': reason})
                # AUDIT FIX: Clear handlers on disconnect to prevent memory leaks
                # Note: Don't clear Socket.IO internal handlers, only our custom handlers
                # self.clear_handlers()  # Commented out - handlers are intentionally persistent
            except Exception as e:
                self.logger.error(f"Error in disconnect handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        @self.sio.event
        def connect_error(data):
            # AUDIT FIX: Error boundary for connect_error handler
            try:
                self.logger.error(f'🚨 Connection error: {data}')
                self._emit_event('error', {'message': str(data), 'type': 'connect_error'})
            except Exception as e:
                self.logger.error(f"Error in connect_error handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        # AUDIT FIX: Add reconnection event handlers
        @self.sio.event
        def reconnect():
            """Handle successful reconnection"""
            try:
                self.is_connected = True
                # PHASE 3.2: Update health monitor
                self.health_monitor.set_connected(True)
                # PHASE 3.4: Log state machine recovery status
                state_summary = self.state_machine.get_state_summary()
                # PHASE 3.6: Notify degradation manager
                self.degradation_manager.record_reconnect()
                # FIX: Reset latency baseline to prevent spike spam after reconnect
                self.last_tick_time = None
                self.spike_detector.latencies.clear()
                self.spike_detector.total_samples = 0
                self.logger.info('🔄 Reconnected to Rugs.fun backend')
                self.logger.info(f'   State machine: phase={state_summary["phase"]}, game={state_summary["game_id"]}')
                self._emit_event('reconnected', {
                    'socketId': self.sio.sid,
                    'state_summary': state_summary
                })
            except Exception as e:
                self.logger.error(f"Error in reconnect handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        @self.sio.event
        def reconnect_attempt(attempt_number):
            """Handle reconnection attempt"""
            try:
                self.logger.warning(f'⏳ Reconnection attempt #{attempt_number}...')
                self._emit_event('reconnect_attempt', {'attempt': attempt_number})
            except Exception as e:
                self.logger.error(f"Error in reconnect_attempt handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        @self.sio.event
        def reconnect_failed():
            """Handle reconnection failure (all attempts exhausted)"""
            try:
                self.logger.error('❌ Reconnection failed - all attempts exhausted')
                self._emit_event('reconnect_failed', {})
            except Exception as e:
                self.logger.error(f"Error in reconnect_failed handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        @self.sio.on('gameStateUpdate')
        def on_game_state_update(data):
            # AUDIT FIX: Critical error boundary - prevents connection death
            try:
                self._handle_game_state_update(data)
            except Exception as e:
                self.logger.error(f"Error handling game state update: {e}", exc_info=True)
                self.metrics['errors'] += 1

        # Phase 10.7: Player identity event (once on connect)
        # This is the PRIMARY source of identity - usernameStatus fires once when authenticated
        @self.sio.on('usernameStatus')
        def on_username_status(*args):
            try:
                # Handle trace argument format: [{__trace:...}, {actual_data}]
                # The actual identity data is the LAST argument
                data = args[-1] if args else {}
                if isinstance(data, dict):
                    player_id = data.get('id')
                    username = data.get('username')
                    if player_id and username:
                        # Use centralized identity confirmation
                        self._confirm_identity(player_id, username, 'usernameStatus')
                else:
                    self.logger.warning(f'⚠️ usernameStatus received unexpected format: {type(data)}')
            except Exception as e:
                self.logger.error(f"Error in usernameStatus handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        # Phase 10.7: Player state update (after each server-side trade)
        # This provides ongoing validation and balance updates
        # Phase 11: Now also stores full state for reconciliation
        @self.sio.on('playerUpdate')
        def on_player_update(*args):
            try:
                # Handle potential trace argument format
                data = args[-1] if args else {}
                if isinstance(data, dict):
                    self.last_player_update = data
                    # Phase 11: Store full server state for reconciliation
                    self._last_server_state = data

                    cash = data.get('cash', 0)
                    pos_qty = data.get('positionQty', 0)

                    # Update balance tracking
                    self._update_balance(cash, 'playerUpdate')

                    # Log position info
                    self.logger.warning(f'💰 Player state: cash={cash:.4f}, pos={pos_qty:.4f}')

                    # Emit event for UI
                    self._emit_event('player_update', data)
            except Exception as e:
                self.logger.error(f"Error in playerUpdate handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        # Phase 10.8: Player leaderboard position (secondary auth confirmation)
        # This fires intermittently and can confirm identity if usernameStatus was missed
        @self.sio.on('playerLeaderboardPosition')
        def on_player_leaderboard_position(*args):
            try:
                # Handle potential trace argument format: [{__trace:...}, {actual_data}]
                data = args[-1] if args else {}
                if isinstance(data, dict):
                    player_entry = data.get('playerEntry', {})
                    rank = data.get('rank')
                    total = data.get('total')
                    player_id = player_entry.get('playerId')
                    username = player_entry.get('username')
                    pnl = player_entry.get('pnl', 0)

                    # Use as fallback identity if not yet confirmed
                    if player_id and username and not self._identity_confirmed:
                        self._confirm_identity(player_id, username, 'playerLeaderboardPosition')

                    # Log leaderboard position
                    if rank and total:
                        self.logger.warning(f'🏆 Leaderboard: #{rank}/{total} (PnL: {pnl:+.4f} SOL)')

                    # Emit event
                    self._emit_event('player_leaderboard', {
                        'rank': rank,
                        'total': total,
                        'player_entry': player_entry
                    })
            except Exception as e:
                self.logger.error(f"Error in playerLeaderboardPosition handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        # gameStatePlayerUpdate: Personal leaderboard entry with PnL, position, etc.
        # This is the PRIMARY source of player state when using hardcoded credentials
        # (since playerUpdate is not sent to unauthenticated clients)
        @self.sio.on('gameStatePlayerUpdate')
        def on_game_state_player_update(*args):
            try:
                # Handle potential trace argument format
                data = args[-1] if args else {}
                if not isinstance(data, dict):
                    return

                leaderboard_entry = data.get('leaderboardEntry', {})
                player_id = leaderboard_entry.get('id')

                # Only process if this is OUR player (match hardcoded ID)
                if player_id != HARDCODED_PLAYER_ID:
                    return

                # Extract player state
                pnl = leaderboard_entry.get('pnl', 0)
                pnl_percent = leaderboard_entry.get('pnlPercent', 0)
                position_qty = leaderboard_entry.get('positionQty', 0)
                avg_cost = leaderboard_entry.get('avgCost', 0)
                total_invested = leaderboard_entry.get('totalInvested', 0)
                has_active_trades = leaderboard_entry.get('hasActiveTrades', False)
                sidebet = leaderboard_entry.get('sideBet')
                sidebet_pnl = leaderboard_entry.get('sidebetPnl', 0)

                # Build server state for reconciliation (Phase 11 compatible)
                # Note: gameStatePlayerUpdate doesn't include 'cash', so we leave it as None
                self._last_server_state = {
                    'positionQty': position_qty,
                    'avgCost': avg_cost,
                    'cumulativePnL': pnl,
                    'totalInvested': total_invested,
                    'pnlPercent': pnl_percent,
                    'hasActiveTrades': has_active_trades,
                    'sideBet': sidebet,
                    'sidebetPnl': sidebet_pnl,
                }

                # Log significant state changes
                if has_active_trades or position_qty > 0:
                    self.logger.warning(
                        f'💰 Player state: pos={position_qty:.6f}, '
                        f'pnl={pnl:+.6f} ({pnl_percent:+.2f}%), '
                        f'invested={total_invested:.6f}'
                    )

                # Emit event for UI/recording
                self._emit_event('player_state_update', {
                    'game_id': data.get('gameId'),
                    'player_id': player_id,
                    'pnl': pnl,
                    'pnl_percent': pnl_percent,
                    'position_qty': position_qty,
                    'avg_cost': avg_cost,
                    'total_invested': total_invested,
                    'has_active_trades': has_active_trades,
                    'sidebet': sidebet,
                    'sidebet_pnl': sidebet_pnl,
                })

            except Exception as e:
                self.logger.error(f"Error in gameStatePlayerUpdate handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        # Catch-all for noise tracking
        @self.sio.on('*')
        def catch_all(event, *args):
            # AUDIT FIX: Error boundary for catch-all handler
            try:
                # Phase 10.8: Don't count player events as noise
                tracked_events = {
                    'gameStateUpdate', 'usernameStatus', 'playerUpdate',
                    'playerLeaderboardPosition', 'gameStatePlayerUpdate'
                }
                if event not in tracked_events:
                    self.metrics['noise_filtered'] += 1
                    self.logger.debug(f'❌ NOISE filtered: {event}')
            except Exception as e:
                self.logger.error(f"Error in catch_all handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

    def _handle_game_state_update(self, raw_data: Dict[str, Any]):
        """Handle gameStateUpdate event - PRIMARY SIGNAL SOURCE"""
        receive_time = time.time() * 1000  # milliseconds

        # Calculate tick interval
        if self.last_tick_time:
            tick_interval = receive_time - self.last_tick_time

            # FIX: Reset baseline if gap exceeds threshold (5 seconds)
            # This prevents cumulative latency spam after processing pauses
            # (e.g., when browser connection blocks the handler thread)
            MAX_REASONABLE_GAP_MS = 5000.0  # 5 seconds
            if tick_interval > MAX_REASONABLE_GAP_MS:
                self.logger.info(
                    f"⏭️ Large gap detected ({tick_interval:.0f}ms), resetting latency baseline"
                )
                # Reset spike detector's baseline by clearing its history
                self.spike_detector.latencies.clear()
                self.spike_detector.total_samples = 0
                # Don't record this anomalous interval
                self.last_tick_time = receive_time
                # Continue processing the signal but skip latency recording
            else:
                # Normal case: record the tick interval
                # AUDIT FIX: deque auto-evicts oldest when maxlen exceeded (O(1) operation)
                self.metrics['latencies'].append(tick_interval)

                # PHASE 3.5: Check for latency spike
                spike_info = self.spike_detector.record(tick_interval)
                if spike_info:
                    self.metrics['latency_spikes'] += 1
                    self.logger.warning(f"⚠️ Latency spike detected: {spike_info['reason']}")
                    # PHASE 3.6: Notify degradation manager
                    self.degradation_manager.record_spike()
                    self._emit_event('latency_spike', spike_info)
        self.last_tick_time = receive_time

        # PHASE 3.2: Record signal reception for health monitoring
        self.health_monitor.record_signal()

        # PHASE 3.6: Check for recovery from degraded state
        self.degradation_manager.check_recovery()

        # Extract signal (9 fields only)
        signal_dict = self._extract_signal(raw_data)

        # Validate with state machine
        validation = self.state_machine.process(raw_data)

        # Add metadata
        signal_dict['phase'] = validation['phase']
        signal_dict['isValid'] = validation['isValid']
        signal_dict['timestamp'] = int(receive_time)
        signal_dict['latency'] = time.time() * 1000 - receive_time

        # Create signal object
        signal = GameSignal(**signal_dict)

        # PHASE 3.1 AUDIT FIX: Apply rate limiting with critical bypass
        if not self.rate_limiter.should_process(signal):
            self.metrics['rate_limited'] += 1
            if self.metrics['rate_limited'] % 100 == 1:
                stats = self.rate_limiter.get_stats()
                drop_rate = stats.get('drop_rate', 0.0)
                self.logger.warning(
                    f"Rate limiting active: {self.metrics['rate_limited']} signals dropped "
                    f"(drop rate: {drop_rate:.1f}%)"
                )
            return  # Drop this signal

        # Update metrics
        self.metrics['total_signals'] += 1
        self.metrics['total_ticks'] += 1

        if validation['phase'] != validation['previousPhase']:
            self.metrics['phase_transitions'] += 1
            self.logger.info(f"🔄 {validation['previousPhase']} → {validation['phase']}")

        if not validation['isValid']:
            self.metrics['anomalies'] += 1

        # Store last signal
        self.last_signal = signal

        # Broadcast signal
        self._broadcast_signal(signal, validation)

    def _extract_signal(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract ONLY the 9 signal fields from raw gameStateUpdate"""
        # AUDIT FIX: Convert price to Decimal for financial precision
        raw_price = raw_data.get('price', 1.0)
        price = Decimal(str(raw_price)) if raw_price is not None else Decimal('1.0')

        return {
            'gameId': raw_data.get('gameId', ''),
            'active': raw_data.get('active', False),
            'rugged': raw_data.get('rugged', False),
            'tickCount': raw_data.get('tickCount', 0),
            'price': price,  # AUDIT FIX: Now Decimal, not float
            'cooldownTimer': raw_data.get('cooldownTimer', 0),
            'allowPreRoundBuys': raw_data.get('allowPreRoundBuys', False),
            'tradeCount': raw_data.get('tradeCount', 0),
            'gameHistory': raw_data.get('gameHistory')
        }

    def _broadcast_signal(self, signal: GameSignal, validation: Dict[str, Any]):
        """Broadcast clean signal to consumers"""
        # Emit 'signal' event
        self._emit_event('signal', signal)

        # Emit phase-specific events
        self._emit_event(f'phase:{signal.phase}', signal)

        # Emit tick event during active gameplay
        if signal.phase == 'ACTIVE_GAMEPLAY':
            self._emit_event('tick', {
                'gameId': signal.gameId,
                'tickCount': signal.tickCount,
                'price': signal.price,
                'timestamp': signal.timestamp
            })

        # Detect game completion (AUDIT FIX: only emit on RUG_EVENT_1 to prevent duplicates)
        if signal.phase == 'RUG_EVENT_1':
            self._handle_game_complete(signal)

    def _handle_game_complete(self, signal: GameSignal):
        """Handle game completion"""
        self.metrics['total_games'] += 1

        # Extract seed data if available
        seed_data = None
        if signal.gameHistory and len(signal.gameHistory) > 0:
            completed_game = signal.gameHistory[0]
            provably_fair = completed_game.get('provablyFair', {})
            seed_data = {
                'gameId': completed_game.get('id'),
                'serverSeed': provably_fair.get('serverSeed'),
                'serverSeedHash': provably_fair.get('serverSeedHash'),
                'peakMultiplier': completed_game.get('peakMultiplier'),
                'finalTick': len(completed_game.get('prices', [])) or signal.tickCount
            }

        self.logger.info('💥 GAME COMPLETE')
        if seed_data:
            self.logger.info(f"   Game ID: {seed_data['gameId']}")
            self.logger.info(f"   Peak: {seed_data['peakMultiplier']:.2f}x")

        self._emit_event('gameComplete', {
            'signal': signal,
            'seedData': seed_data,
            'gameNumber': self.metrics['total_games']
        })

    def _emit_event(self, event_name: str, data: Any):
        """Emit event to registered handlers"""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    handler(data)
                except Exception as e:
                    self.logger.error(f"Error in event handler for '{event_name}': {e}")

    def on(self, event_name: str, handler: Callable = None):
        """
        Register event handler (decorator or function)

        Usage:
            @feed.on('signal')
            def handle_signal(signal):
                print(signal.price)

            # OR

            def handler(signal):
                print(signal.price)
            feed.on('signal', handler)
        """
        def decorator(func):
            if event_name not in self.event_handlers:
                self.event_handlers[event_name] = []
            self.event_handlers[event_name].append(func)
            return func

        if handler is None:
            return decorator
        else:
            return decorator(handler)

    def remove_handler(self, event_name: str, handler: Callable):
        """
        Remove a specific event handler (AUDIT FIX: Prevent memory leaks)

        Args:
            event_name: Event to remove handler from
            handler: Handler function to remove
        """
        if event_name in self.event_handlers:
            try:
                self.event_handlers[event_name].remove(handler)
                # Remove empty lists to free memory
                if not self.event_handlers[event_name]:
                    del self.event_handlers[event_name]
            except ValueError:
                # Handler not found, silently ignore
                pass

    def clear_handlers(self, event_name: str = None):
        """
        Clear event handlers (AUDIT FIX: Prevent memory leaks on reconnect)

        Args:
            event_name: Specific event to clear, or None to clear all
        """
        if event_name:
            if event_name in self.event_handlers:
                self.event_handlers[event_name] = []
                del self.event_handlers[event_name]
        else:
            # Clear all handlers
            self.event_handlers.clear()
            self.logger.debug("Cleared all event handlers")

    def connect(self):
        """Connect to Rugs.fun backend"""
        self.logger.info('🔌 Connecting to Rugs.fun backend...')
        self.logger.info(f'   Server: {self.server_url}')
        self.logger.info('   Mode: READ-ONLY (0% noise, 9 signal fields only)')

        try:
            self.sio.connect(
                self.server_url,
                transports=['websocket', 'polling'],
                wait_timeout=20
            )
        except Exception as e:
            self.logger.error(f'🚨 Connection failed: {e}')
            raise

    def disconnect(self):
        """Disconnect from backend"""
        self.logger.info('🔌 Disconnecting...')
        self.sio.disconnect()
        self.print_metrics()

    def get_last_signal(self) -> Optional[GameSignal]:
        """Get the last received signal"""
        return self.last_signal

    def get_player_info(self) -> Dict[str, Any]:
        """
        Get current player identity and state.

        Phase 10.7: Returns player ID, username, and last server update.

        Returns:
            Dict with player_id, username, and last_update
        """
        return {
            'player_id': self.player_id,
            'username': self.username,
            'last_update': self.last_player_update
        }

    def signal_to_game_tick(self, signal: GameSignal) -> GameTick:
        """
        Convert GameSignal to REPLAYER GameTick model

        Args:
            signal: GameSignal from WebSocket feed

        Returns:
            GameTick compatible with REPLAYER models
        """
        return GameTick(
            game_id=signal.gameId,
            tick=signal.tickCount,
            timestamp=datetime.fromtimestamp(signal.timestamp / 1000).isoformat(),
            price=signal.price,  # AUDIT FIX: Already Decimal, no conversion needed
            phase=signal.phase,
            active=signal.active,
            rugged=signal.rugged,
            cooldown_timer=signal.cooldownTimer,
            trade_count=signal.tradeCount
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics summary"""
        uptime = time.time() - self.metrics['start_time']

        avg_latency = (
            sum(self.metrics['latencies']) / len(self.metrics['latencies'])
            if self.metrics['latencies'] else 0
        )

        # PHASE 3.1: Include rate limiter stats
        rate_stats = self.rate_limiter.get_stats()

        return {
            'uptime': f'{uptime:.1f}s',
            'totalSignals': self.metrics['total_signals'],
            'totalTicks': self.metrics['total_ticks'],
            'totalGames': self.metrics['total_games'],
            'noiseFiltered': self.metrics['noise_filtered'],
            'phaseTransitions': self.metrics['phase_transitions'],
            'anomalies': self.metrics['anomalies'],
            'avgLatency': f'{avg_latency:.2f}ms',
            'signalsPerSecond': f'{self.metrics["total_signals"] / uptime:.2f}' if uptime > 0 else '0',
            'currentPhase': self.state_machine.current_phase,
            'currentGameId': self.state_machine.current_game_id or 'N/A',
            'lastPrice': f'{self.last_signal.price:.4f}x' if self.last_signal else 'N/A',
            # PHASE 3.1: Rate limiting stats
            'rateLimited': self.metrics['rate_limited'],
            'rateLimitDropRate': f'{rate_stats["drop_rate"]:.1f}%',
            'errors': self.metrics['errors']
        }

    def get_health(self) -> Dict[str, Any]:
        """
        Get connection health status.

        PHASE 3.2 AUDIT FIX: Provides health check for monitoring.

        Returns:
            Dict with status, issues, and health metrics
        """
        # Calculate metrics for health check
        avg_latency = (
            sum(self.metrics['latencies']) / len(self.metrics['latencies'])
            if self.metrics['latencies'] else 0
        )

        total_signals = self.metrics['total_signals']
        error_rate = (
            (self.metrics['errors'] / total_signals * 100)
            if total_signals > 0 else 0.0
        )

        rate_stats = self.rate_limiter.get_stats()
        drop_rate = rate_stats['drop_rate']

        return self.health_monitor.check_health(
            avg_latency_ms=avg_latency,
            error_rate=error_rate,
            drop_rate=drop_rate
        )

    def is_healthy(self) -> bool:
        """
        Quick health check.

        PHASE 3.2 AUDIT FIX: Simple boolean for health checks.

        Returns:
            True if connection is healthy
        """
        health = self.get_health()
        return health['status'] == ConnectionHealth.HEALTHY

    def get_operating_mode(self) -> str:
        """
        Get current operating mode.

        PHASE 3.6 AUDIT FIX: Returns current degradation state.

        Returns:
            Operating mode string (NORMAL, DEGRADED, MINIMAL, OFFLINE)
        """
        return self.degradation_manager.current_mode

    def get_degradation_status(self) -> Dict[str, Any]:
        """
        Get full degradation status.

        PHASE 3.6 AUDIT FIX: Provides detailed degradation info.

        Returns:
            Dict with mode, error counts, and history
        """
        return self.degradation_manager.get_status()

    def print_metrics(self):
        """Print metrics summary"""
        metrics = self.get_metrics()

        print('')
        print('━' * 50)
        print('📊 WEBSOCKET FEED METRICS')
        print('━' * 50)
        print(f'   Uptime: {metrics["uptime"]}')
        print(f'   Total Signals: {metrics["totalSignals"]}')
        print(f'   Total Ticks: {metrics["totalTicks"]}')
        print(f'   Total Games: {metrics["totalGames"]}')
        print(f'   Noise Filtered: {metrics["noiseFiltered"]}')
        print('')
        print('   Performance:')
        print(f'     Avg Latency: {metrics["avgLatency"]}')
        print(f'     Signals/sec: {metrics["signalsPerSecond"]}')
        print('')
        print('   Validation:')
        print(f'     Phase Transitions: {metrics["phaseTransitions"]}')
        print(f'     Anomalies: {metrics["anomalies"]}')
        print('')
        print('   Current State:')
        print(f'     Phase: {metrics["currentPhase"]}')
        print(f'     Game: {metrics["currentGameId"]}')
        print(f'     Price: {metrics["lastPrice"]}')
        print('━' * 50)

    def wait(self):
        """Wait for Socket.IO events (blocking)"""
        try:
            self.sio.wait()
        except KeyboardInterrupt:
            self.logger.info('')
            self.logger.info('🛑 Shutting down gracefully...')
            self.disconnect()
