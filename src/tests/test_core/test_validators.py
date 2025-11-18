"""
Tests for validation functions
"""

import pytest
from decimal import Decimal
from models import GameTick
from core import validate_bet_amount, validate_trading_allowed, validate_sidebet


class TestValidateBetAmount:
    """Tests for validate_bet_amount function"""

    def test_valid_bet_amount(self):
        """Test validation passes for valid bet amount"""
        is_valid, error = validate_bet_amount(Decimal('0.005'), Decimal('0.1'))

        assert is_valid == True
        assert error is None

    def test_bet_below_minimum(self):
        """Test validation fails for bet below minimum"""
        is_valid, error = validate_bet_amount(Decimal('0.0001'), Decimal('0.1'))

        assert is_valid == False
        assert "below minimum" in error

    def test_bet_above_maximum(self):
        """Test validation fails for bet above maximum"""
        is_valid, error = validate_bet_amount(Decimal('2.0'), Decimal('0.1'))

        assert is_valid == False
        assert "exceeds maximum" in error

    def test_insufficient_balance(self):
        """Test validation fails for insufficient balance"""
        is_valid, error = validate_bet_amount(Decimal('0.5'), Decimal('0.1'))

        assert is_valid == False
        assert "Insufficient balance" in error

    def test_exact_minimum_bet(self):
        """Test validation passes for exact minimum bet"""
        from config import config
        min_bet = config.FINANCIAL['min_bet']

        is_valid, error = validate_bet_amount(min_bet, Decimal('0.1'))

        assert is_valid == True
        assert error is None

    def test_exact_maximum_bet(self):
        """Test validation passes for exact maximum bet (if balance allows)"""
        from config import config
        max_bet = config.FINANCIAL['max_bet']

        # Only valid if balance is sufficient
        is_valid, error = validate_bet_amount(max_bet, max_bet)

        assert is_valid == True
        assert error is None

    def test_exact_balance(self):
        """Test validation passes for bet equal to balance"""
        balance = Decimal('0.05')
        is_valid, error = validate_bet_amount(balance, balance)

        assert is_valid == True
        assert error is None

    def test_zero_bet(self):
        """Test validation fails for zero bet"""
        is_valid, error = validate_bet_amount(Decimal('0'), Decimal('0.1'))

        assert is_valid == False
        assert "below minimum" in error

    def test_negative_bet(self):
        """Test validation fails for negative bet"""
        is_valid, error = validate_bet_amount(Decimal('-0.01'), Decimal('0.1'))

        assert is_valid == False


class TestValidateTradingAllowed:
    """Tests for validate_trading_allowed function"""

    def test_trading_allowed_when_active(self, sample_tick):
        """Test trading allowed when game is active"""
        is_valid, error = validate_trading_allowed(sample_tick)

        assert is_valid == True
        assert error is None

    def test_trading_blocked_when_inactive(self, sample_tick):
        """Test trading blocked when game is not active"""
        sample_tick.active = False
        is_valid, error = validate_trading_allowed(sample_tick)

        assert is_valid == False
        assert "not active" in error

    def test_trading_blocked_when_rugged(self, sample_tick):
        """Test trading blocked when game is rugged"""
        sample_tick.rugged = True
        is_valid, error = validate_trading_allowed(sample_tick)

        assert is_valid == False
        assert "rugged" in error or "not active" in error

    def test_trading_in_presale_phase(self):
        """Test trading allowed in PRESALE phase"""
        tick = GameTick.from_dict({
            'game_id': 'test', 'tick': 0, 'timestamp': '', 'price': 1.0,
            'phase': 'PRESALE', 'active': True, 'rugged': False,
            'cooldown_timer': 0, 'trade_count': 0
        })

        is_valid, error = validate_trading_allowed(tick)

        assert is_valid == True

    def test_trading_in_active_phase(self):
        """Test trading allowed in ACTIVE phase"""
        tick = GameTick.from_dict({
            'game_id': 'test', 'tick': 0, 'timestamp': '', 'price': 1.0,
            'phase': 'ACTIVE', 'active': True, 'rugged': False,
            'cooldown_timer': 0, 'trade_count': 0
        })

        is_valid, error = validate_trading_allowed(tick)

        assert is_valid == True

    def test_trading_in_cooldown_phase(self):
        """Test trading blocked in COOLDOWN phase"""
        tick = GameTick.from_dict({
            'game_id': 'test', 'tick': 0, 'timestamp': '', 'price': 1.0,
            'phase': 'COOLDOWN', 'active': False, 'rugged': False,
            'cooldown_timer': 5, 'trade_count': 0
        })

        is_valid, error = validate_trading_allowed(tick)

        assert is_valid == False
        assert "not active" in error


class TestValidateSidebet:
    """Tests for validate_sidebet function - Bug 1 Regression Tests"""

    def test_sidebet_allowed_after_exactly_5_ticks(self, sample_tick):
        """
        Regression test for Bug 1: Sidebet cooldown off-by-one error

        The bug was that cooldown used <= instead of <, blocking bets at exactly tick 5.
        This test verifies that a sidebet is allowed at exactly tick N+5 after resolution.
        """
        from config import config

        # Last sidebet resolved at tick 100
        last_resolved_tick = 100
        # Current tick is 105 (exactly 5 ticks later)
        sample_tick.tick = 105

        # Should be ALLOWED (5 >= SIDEBET_COOLDOWN_TICKS of 5)
        is_valid, error = validate_sidebet(
            amount=Decimal('0.001'),
            balance=Decimal('1.0'),
            tick=sample_tick,
            has_active_sidebet=False,
            last_sidebet_resolved_tick=last_resolved_tick
        )

        assert is_valid == True, f"Expected sidebet to be allowed at exactly {config.SIDEBET_COOLDOWN_TICKS} ticks, but got: {error}"
        assert error is None

    def test_sidebet_blocked_at_4_ticks(self, sample_tick):
        """Test sidebet blocked at 4 ticks (1 tick before cooldown expires)"""
        from config import config

        last_resolved_tick = 100
        sample_tick.tick = 104  # 4 ticks later

        is_valid, error = validate_sidebet(
            amount=Decimal('0.001'),
            balance=Decimal('1.0'),
            tick=sample_tick,
            has_active_sidebet=False,
            last_sidebet_resolved_tick=last_resolved_tick
        )

        assert is_valid == False
        assert "cooldown: 1 ticks remaining" in error

    def test_sidebet_blocked_at_1_tick(self, sample_tick):
        """Test sidebet blocked at 1 tick after resolution"""
        last_resolved_tick = 100
        sample_tick.tick = 101  # 1 tick later

        is_valid, error = validate_sidebet(
            amount=Decimal('0.001'),
            balance=Decimal('1.0'),
            tick=sample_tick,
            has_active_sidebet=False,
            last_sidebet_resolved_tick=last_resolved_tick
        )

        assert is_valid == False
        assert "cooldown: 4 ticks remaining" in error

    def test_sidebet_allowed_at_6_ticks(self, sample_tick):
        """Test sidebet allowed at 6 ticks (well past cooldown)"""
        last_resolved_tick = 100
        sample_tick.tick = 106  # 6 ticks later

        is_valid, error = validate_sidebet(
            amount=Decimal('0.001'),
            balance=Decimal('1.0'),
            tick=sample_tick,
            has_active_sidebet=False,
            last_sidebet_resolved_tick=last_resolved_tick
        )

        assert is_valid == True
        assert error is None

    def test_sidebet_allowed_when_no_previous_bet(self, sample_tick):
        """Test sidebet allowed when no previous bet exists"""
        is_valid, error = validate_sidebet(
            amount=Decimal('0.001'),
            balance=Decimal('1.0'),
            tick=sample_tick,
            has_active_sidebet=False,
            last_sidebet_resolved_tick=None  # No previous bet
        )

        assert is_valid == True
        assert error is None

    def test_sidebet_blocked_when_active(self, sample_tick):
        """Test sidebet blocked when another is already active"""
        is_valid, error = validate_sidebet(
            amount=Decimal('0.001'),
            balance=Decimal('1.0'),
            tick=sample_tick,
            has_active_sidebet=True,  # Already has active sidebet
            last_sidebet_resolved_tick=None
        )

        assert is_valid == False
        assert "already active" in error

    def test_sidebet_insufficient_balance(self, sample_tick):
        """Test sidebet blocked with insufficient balance"""
        is_valid, error = validate_sidebet(
            amount=Decimal('1.0'),
            balance=Decimal('0.001'),  # Not enough balance
            tick=sample_tick,
            has_active_sidebet=False,
            last_sidebet_resolved_tick=None
        )

        assert is_valid == False
        assert "Insufficient balance" in error or "balance" in error.lower()
