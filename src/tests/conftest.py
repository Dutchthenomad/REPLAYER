"""
Shared test fixtures for pytest
"""

import pytest
from decimal import Decimal
from models import GameTick, Position, SideBet
from core import GameState, TradeManager, ReplayEngine
from bot import BotInterface, BotController
from services import event_bus, setup_logging


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Setup logging for all tests"""
    setup_logging()


@pytest.fixture
def game_state():
    """Create a fresh GameState with default balance"""
    return GameState(Decimal('0.100'))


@pytest.fixture
def trade_manager(game_state):
    """Create TradeManager with GameState"""
    return TradeManager(game_state)


@pytest.fixture
def replay_engine(game_state):
    """Create ReplayEngine with GameState"""
    return ReplayEngine(game_state)


@pytest.fixture
def bot_interface(game_state, trade_manager):
    """Create BotInterface with dependencies"""
    return BotInterface(game_state, trade_manager)


@pytest.fixture
def bot_controller(bot_interface):
    """Create BotController with conservative strategy"""
    return BotController(bot_interface, "conservative")


@pytest.fixture
def sample_tick():
    """Create a sample GameTick for testing"""
    return GameTick.from_dict({
        'game_id': 'test-game',
        'tick': 0,
        'timestamp': '2025-11-04T00:00:00',
        'price': 1.0,
        'phase': 'ACTIVE',
        'active': True,
        'rugged': False,
        'cooldown_timer': 0,
        'trade_count': 0
    })


@pytest.fixture
def sample_position():
    """Create a sample Position for testing"""
    return Position(
        entry_price=Decimal('1.0'),
        amount=Decimal('0.01'),
        entry_time=1234567890.0,
        entry_tick=0
    )


@pytest.fixture
def sample_sidebet():
    """Create a sample SideBet for testing"""
    return SideBet(
        amount=Decimal('0.002'),
        placed_tick=10,
        placed_price=Decimal('1.2')
    )


@pytest.fixture
def loaded_game_state(game_state, sample_tick):
    """GameState with a loaded game"""
    # Set up game state as if a game is loaded
    game_state.update(
        game_id='test-game',
        game_active=True,
        current_tick=0,
        current_price=sample_tick.price,
        current_phase=sample_tick.phase
    )
    return game_state


@pytest.fixture
def price_series():
    """Create a series of price ticks for testing (10 ticks, rise then fall)"""
    prices = [1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 2.5, 2.0, 1.5, 1.0]
    ticks = []
    for i, price in enumerate(prices):
        tick = GameTick.from_dict({
            'game_id': 'test-game',
            'tick': i,
            'timestamp': f'2025-11-04T00:00:{i:02d}',
            'price': price,
            'phase': 'ACTIVE',
            'active': True,
            'rugged': False,
            'cooldown_timer': 0,
            'trade_count': i
        })
        ticks.append(tick)
    return ticks


@pytest.fixture(autouse=True)
def cleanup_event_bus():
    """Clean up event bus after each test"""
    # Start event bus for tests
    if not event_bus._processing:
        event_bus.start()

    yield

    # Clear all subscribers after test
    event_bus._subscribers.clear()
