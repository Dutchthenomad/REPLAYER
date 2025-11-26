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
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
import logging
from decimal import Decimal
from collections import deque  # AUDIT FIX: For efficient latency tracking

# REPLAYER imports
from models import GameTick


@dataclass
class GameSignal:
    """Clean game state signal (9 fields + metadata)"""
    # Core identifiers
    gameId: str

    # State flags
    active: bool
    rugged: bool

    # Game progress
    tickCount: int
    price: Decimal  # AUDIT FIX: Use Decimal for financial precision

    # Timing
    cooldownTimer: int

    # Trading
    allowPreRoundBuys: bool
    tradeCount: int

    # Post-game data
    gameHistory: Optional[List[Dict[str, Any]]]

    # Metadata (added by collector)
    phase: str = "UNKNOWN"
    isValid: bool = True
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    latency: float = 0.0


class GameStateMachine:
    """Validates game state transitions and detects phases"""

    def __init__(self):
        self.current_phase = "UNKNOWN"
        self.current_game_id = None
        self.last_tick_count = -1
        self.transition_history = []
        self.anomaly_count = 0

    def detect_phase(self, data: Dict[str, Any]) -> str:
        """Detect game phase from raw data"""
        # RUG EVENT - gameHistory ONLY appears during rug events
        if data.get('gameHistory'):
            if data.get('active') and data.get('rugged'):
                return 'RUG_EVENT_1'  # Seed reveal
            if not data.get('active') and data.get('rugged'):
                return 'RUG_EVENT_2'  # New game setup

        # PRESALE - 10-second window before game starts
        cooldown = data.get('cooldownTimer', 0)
        if (0 < cooldown <= 10000 and
            data.get('allowPreRoundBuys', False)):
            return 'PRESALE'

        # COOLDOWN - 5-second settlement buffer
        if (cooldown > 10000 and
            data.get('rugged', False) and
            not data.get('active', True)):
            return 'COOLDOWN'

        # ACTIVE GAMEPLAY - Main game phase
        if (data.get('active', False) and
            data.get('tickCount', 0) > 0 and
            not data.get('rugged', False)):
            return 'ACTIVE_GAMEPLAY'

        # GAME ACTIVATION - Instant transition from presale
        if (data.get('active', False) and
            data.get('tickCount', 0) == 0 and
            not data.get('rugged', False)):
            return 'GAME_ACTIVATION'

        # Log unknown states for debugging
        logging.debug(f"UNKNOWN state detected - active:{data.get('active')} rugged:{data.get('rugged')} tick:{data.get('tickCount')} cooldown:{cooldown}")

        # If we can't determine state but game is active, stay in current phase
        # This handles brief moments where data might be in transition
        if self.current_phase in ['ACTIVE_GAMEPLAY', 'GAME_ACTIVATION'] and data.get('active', False):
            return self.current_phase

        return 'UNKNOWN'

    def validate_transition(self, new_phase: str, data: Dict[str, Any]) -> bool:
        """Validate state transition is legal"""
        # First state is always valid
        if self.current_phase == 'UNKNOWN':
            return True

        # Transitioning TO unknown is allowed (data ambiguity, not an error)
        # But log it for monitoring
        if new_phase == 'UNKNOWN':
            logging.debug(f"Transitioning from {self.current_phase} to UNKNOWN (data ambiguity)")
            return True

        # Legal transition map
        legal_transitions = {
            'GAME_ACTIVATION': ['ACTIVE_GAMEPLAY', 'RUG_EVENT_1'],
            'ACTIVE_GAMEPLAY': ['ACTIVE_GAMEPLAY', 'RUG_EVENT_1'],
            'RUG_EVENT_1': ['RUG_EVENT_2'],
            'RUG_EVENT_2': ['COOLDOWN'],
            'COOLDOWN': ['PRESALE'],
            'PRESALE': ['PRESALE', 'GAME_ACTIVATION', 'ACTIVE_GAMEPLAY'],  # FIX: Allow direct PRESALE → ACTIVE_GAMEPLAY
            'UNKNOWN': ['GAME_ACTIVATION', 'ACTIVE_GAMEPLAY', 'PRESALE', 'COOLDOWN']
        }

        allowed_next = legal_transitions.get(self.current_phase, [])
        is_legal = new_phase in allowed_next or new_phase == self.current_phase

        if not is_legal:
            logging.warning(f"Illegal transition: {self.current_phase} → {new_phase} (allowed: {allowed_next})")
            return False

        # Validate tick progression in active gameplay
        if new_phase == 'ACTIVE_GAMEPLAY' and self.current_phase == 'ACTIVE_GAMEPLAY':
            game_id = data.get('gameId')
            tick_count = data.get('tickCount', 0)

            if game_id == self.current_game_id:
                if tick_count <= self.last_tick_count:
                    logging.warning(f"Tick regression detected: {self.last_tick_count} → {tick_count}")
                    return False

        return True

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process game state update and return validation result"""
        phase = self.detect_phase(data)
        is_valid = self.validate_transition(phase, data)

        if not is_valid:
            self.anomaly_count += 1
            logging.warning(f"Invalid state transition detected (anomaly #{self.anomaly_count})")

        # Track transition
        previous_phase = self.current_phase
        if phase != self.current_phase:
            self.transition_history.append({
                'from': self.current_phase,
                'to': phase,
                'gameId': data.get('gameId'),
                'tick': data.get('tickCount', 0),
                'timestamp': int(time.time() * 1000)
            })

            # Keep only last 20 transitions
            if len(self.transition_history) > 20:
                self.transition_history.pop(0)

        # Update state
        self.current_phase = phase
        self.current_game_id = data.get('gameId')
        self.last_tick_count = data.get('tickCount', 0)

        return {
            'phase': phase,
            'isValid': is_valid,
            'previousPhase': previous_phase
        }


class WebSocketFeed:
    """Real-time WebSocket feed for Rugs.fun game state"""

    def __init__(self, log_level: str = 'INFO'):
        """
        Initialize WebSocket feed

        Args:
            log_level: Logging level (DEBUG, INFO, WARN, ERROR)
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

        # Metrics
        self.metrics = {
            'start_time': time.time(),
            'total_signals': 0,
            'total_ticks': 0,
            'total_games': 0,
            'noise_filtered': 0,
            'latencies': deque(maxlen=100),  # AUDIT FIX: O(1) operations, auto-evicts oldest
            'phase_transitions': 0,
            'anomalies': 0,
            'errors': 0  # AUDIT FIX: Track callback errors
        }

        # State
        self.last_signal: Optional[GameSignal] = None
        self.last_tick_time = None
        self.is_connected = False
        self.event_handlers = {}

        # AUDIT FIX: Guard to prevent duplicate event listener registration
        self._listeners_setup = False

        # Setup logging
        self.logger = logging.getLogger('WebSocketFeed')
        self.logger.setLevel(getattr(logging, log_level.upper()))
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Setup Socket.IO event handlers
        self._setup_event_listeners()

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
                self.logger.info('✅ Connected to Rugs.fun backend')
                self.logger.info(f'   Socket ID: {self.sio.sid}')
                self._emit_event('connected', {'socketId': self.sio.sid})
            except Exception as e:
                self.logger.error(f"Error in connect handler: {e}", exc_info=True)
                self.metrics['errors'] += 1

        @self.sio.event
        def disconnect():
            # AUDIT FIX: Error boundary for disconnect handler
            try:
                self.is_connected = False
                self.logger.warning('❌ Disconnected from backend')
                self._emit_event('disconnected', {})
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
                self.logger.info('🔄 Reconnected to Rugs.fun backend')
                self._emit_event('reconnected', {'socketId': self.sio.sid})
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

        # Catch-all for noise tracking
        @self.sio.on('*')
        def catch_all(event, *args):
            # AUDIT FIX: Error boundary for catch-all handler
            try:
                if event != 'gameStateUpdate':
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
            # AUDIT FIX: deque auto-evicts oldest when maxlen exceeded (O(1) operation)
            self.metrics['latencies'].append(tick_interval)
        self.last_tick_time = receive_time

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
            'lastPrice': f'{self.last_signal.price:.4f}x' if self.last_signal else 'N/A'
        }

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
