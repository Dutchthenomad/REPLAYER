"""
Tests for data models (GameTick, Position, SideBet)
"""

import pytest
from decimal import Decimal
from models import GameTick, Position, SideBet


class TestGameTick:
    """Tests for GameTick model"""

    def test_gametick_creation_from_dict(self, sample_tick):
        """Test creating GameTick from dictionary"""
        assert sample_tick.game_id == 'test-game'
        assert sample_tick.tick == 0
        assert sample_tick.price == 1.0
        assert sample_tick.phase == 'ACTIVE'
        assert sample_tick.active == True
        assert sample_tick.rugged == False

    def test_gametick_is_tradeable(self, sample_tick):
        """Test GameTick.is_tradeable() returns True when active"""
        assert sample_tick.is_tradeable() == True

    def test_gametick_not_tradeable_when_inactive(self, sample_tick):
        """Test GameTick.is_tradeable() returns False when inactive"""
        sample_tick.active = False
        assert sample_tick.is_tradeable() == False

    def test_gametick_not_tradeable_when_rugged(self, sample_tick):
        """Test GameTick.is_tradeable() returns False when rugged"""
        sample_tick.rugged = True
        assert sample_tick.is_tradeable() == False

    def test_gametick_attributes(self):
        """Test all GameTick attributes are present"""
        tick_data = {
            'game_id': 'test-123',
            'tick': 42,
            'timestamp': '2025-11-04T12:00:00',
            'price': 2.5,
            'phase': 'COOLDOWN',
            'active': False,
            'rugged': True,
            'cooldown_timer': 5,
            'trade_count': 10
        }
        tick = GameTick.from_dict(tick_data)

        assert tick.game_id == 'test-123'
        assert tick.tick == 42
        assert tick.timestamp == '2025-11-04T12:00:00'
        assert tick.price == 2.5
        assert tick.phase == 'COOLDOWN'
        assert tick.active == False
        assert tick.rugged == True
        assert tick.cooldown_timer == 5
        assert tick.trade_count == 10


class TestPosition:
    """Tests for Position model"""

    def test_position_creation(self, sample_position):
        """Test creating Position"""
        assert sample_position.entry_price == Decimal('1.0')
        assert sample_position.amount == Decimal('0.01')
        assert sample_position.entry_time == 1234567890.0
        assert sample_position.entry_tick == 0

    def test_position_unrealized_pnl_profit(self, sample_position):
        """Test calculating unrealized P&L with profit"""
        pnl_sol, pnl_pct = sample_position.calculate_unrealized_pnl(Decimal('1.5'))

        assert pnl_sol == Decimal('0.005')
        assert pnl_pct == Decimal('50.0')

    def test_position_unrealized_pnl_loss(self, sample_position):
        """Test calculating unrealized P&L with loss"""
        pnl_sol, pnl_pct = sample_position.calculate_unrealized_pnl(Decimal('0.8'))

        assert pnl_sol == Decimal('-0.002')
        assert pnl_pct == Decimal('-20.0')

    def test_position_unrealized_pnl_breakeven(self, sample_position):
        """Test calculating unrealized P&L at entry price"""
        pnl_sol, pnl_pct = sample_position.calculate_unrealized_pnl(Decimal('1.0'))

        assert pnl_sol == Decimal('0.0')
        assert pnl_pct == Decimal('0.0')

    def test_position_custom_values(self):
        """Test Position with custom values"""
        position = Position(
            entry_price=Decimal('2.5'),
            amount=Decimal('0.05'),
            entry_time=9876543210.0,
            entry_tick=42
        )

        assert position.entry_price == Decimal('2.5')
        assert position.amount == Decimal('0.05')
        assert position.entry_time == 9876543210.0
        assert position.entry_tick == 42

        # Test P&L calculation with these values
        pnl_sol, pnl_pct = position.calculate_unrealized_pnl(Decimal('3.0'))
        # Exit value: 0.05 / 3.0 = 0.01667
        # Entry value: 0.05 / 2.5 = 0.02
        # P&L: 0.01667 - 0.02 = -0.00333 (wait, this seems wrong)

        # Actually with multiplier:
        # Entry value = amount = 0.05 SOL
        # Exit value = amount * (exit_price / entry_price) = 0.05 * (3.0 / 2.5) = 0.06
        # P&L = 0.06 - 0.05 = 0.01
        expected_pnl = Decimal('0.01')
        expected_pct = Decimal('20.0')

        assert pnl_sol == expected_pnl
        assert pnl_pct == expected_pct


class TestSideBet:
    """Tests for SideBet model"""

    def test_sidebet_creation(self, sample_sidebet):
        """Test creating SideBet"""
        assert sample_sidebet.amount == Decimal('0.002')
        assert sample_sidebet.placed_tick == 10
        assert sample_sidebet.placed_price == Decimal('1.2')
        assert sample_sidebet.status == "active"

    def test_sidebet_default_status(self):
        """Test SideBet default status is 'active'"""
        sidebet = SideBet(
            amount=Decimal('0.005'),
            placed_tick=0,
            placed_price=Decimal('1.0')
        )
        assert sidebet.status == "active"

    def test_sidebet_custom_values(self):
        """Test SideBet with custom values"""
        sidebet = SideBet(
            amount=Decimal('0.01'),
            placed_tick=100,
            placed_price=Decimal('5.5')
        )

        assert sidebet.amount == Decimal('0.01')
        assert sidebet.placed_tick == 100
        assert sidebet.placed_price == Decimal('5.5')

    def test_sidebet_payout_ratio(self):
        """Test SideBet has correct payout ratio (5:1)"""
        sidebet = SideBet(
            amount=Decimal('0.01'),
            placed_tick=0,
            placed_price=Decimal('1.0')
        )

        # Note: Payout ratio is defined in config, not in the model
        # This test documents the expected payout behavior
        from config import config
        expected_payout = sidebet.amount * config.GAME_RULES['sidebet_multiplier']
        assert expected_payout == Decimal('0.05')  # 5x payout
