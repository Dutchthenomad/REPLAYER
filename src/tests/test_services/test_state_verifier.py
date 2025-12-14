"""
Tests for state_verifier.py - Phase 10.4E

TDD: Tests written FIRST before implementation.

Tests cover:
- StateVerifier: drift detection between local and server state
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock

# This import will FAIL until we create the module (TDD RED phase)
from services.state_verifier import StateVerifier, BALANCE_TOLERANCE, POSITION_TOLERANCE


class MockPosition:
    """Mock position for testing"""
    def __init__(self, amount: Decimal, entry_price: Decimal):
        self.amount = amount
        self.entry_price = entry_price


class MockGameState:
    """Mock GameState for testing"""
    def __init__(self, balance: Decimal, position=None):
        self.balance = balance
        self.position = position


class TestStateVerifier:
    """Tests for StateVerifier"""

    def test_initialization(self):
        """Test default initialization"""
        game_state = MockGameState(Decimal("1.0"))
        verifier = StateVerifier(game_state)

        assert verifier.game_state == game_state
        assert verifier.drift_count == 0
        assert verifier.total_verifications == 0
        assert verifier.last_verification is None

    def test_verify_matching_state(self):
        """Test verification passes when states match"""
        game_state = MockGameState(
            balance=Decimal("1.5"),
            position=MockPosition(Decimal("0.001"), Decimal("1.234"))
        )
        verifier = StateVerifier(game_state)

        result = verifier.verify({
            'cash': Decimal("1.5"),
            'position_qty': Decimal("0.001"),
            'avg_cost': Decimal("1.234")
        })

        assert result['verified'] is True
        assert result['balance']['ok'] is True
        assert result['position']['ok'] is True
        assert result['entry_price']['ok'] is True
        assert verifier.drift_count == 0

    def test_verify_balance_drift(self):
        """Test verification detects balance drift"""
        game_state = MockGameState(balance=Decimal("1.5"))
        verifier = StateVerifier(game_state)

        result = verifier.verify({
            'cash': Decimal("1.6"),  # Different from local
            'position_qty': Decimal("0"),
            'avg_cost': Decimal("0")
        })

        assert result['verified'] is False
        assert result['balance']['ok'] is False
        assert result['balance']['local'] == Decimal("1.5")
        assert result['balance']['server'] == Decimal("1.6")
        assert verifier.drift_count == 1

    def test_verify_position_drift(self):
        """Test verification detects position quantity drift"""
        game_state = MockGameState(
            balance=Decimal("1.0"),
            position=MockPosition(Decimal("0.001"), Decimal("1.0"))
        )
        verifier = StateVerifier(game_state)

        result = verifier.verify({
            'cash': Decimal("1.0"),
            'position_qty': Decimal("0.002"),  # Different
            'avg_cost': Decimal("1.0")
        })

        assert result['verified'] is False
        assert result['position']['ok'] is False
        assert verifier.drift_count == 1

    def test_verify_entry_price_drift(self):
        """Test verification detects entry price drift"""
        game_state = MockGameState(
            balance=Decimal("1.0"),
            position=MockPosition(Decimal("0.001"), Decimal("1.0"))
        )
        verifier = StateVerifier(game_state)

        result = verifier.verify({
            'cash': Decimal("1.0"),
            'position_qty': Decimal("0.001"),
            'avg_cost': Decimal("1.5")  # Different
        })

        assert result['verified'] is False
        assert result['entry_price']['ok'] is False

    def test_verify_no_position(self):
        """Test verification when no position"""
        game_state = MockGameState(balance=Decimal("1.0"))
        verifier = StateVerifier(game_state)

        result = verifier.verify({
            'cash': Decimal("1.0"),
            'position_qty': Decimal("0"),
            'avg_cost': Decimal("0")
        })

        assert result['verified'] is True
        assert result['position']['local'] == Decimal("0")
        assert result['position']['server'] == Decimal("0")

    def test_verify_within_tolerance(self):
        """Test small differences within tolerance pass"""
        game_state = MockGameState(balance=Decimal("1.0"))
        verifier = StateVerifier(game_state)

        # Difference smaller than tolerance
        result = verifier.verify({
            'cash': Decimal("1.0000001"),  # Within tolerance
            'position_qty': Decimal("0"),
            'avg_cost': Decimal("0")
        })

        assert result['verified'] is True
        assert result['balance']['ok'] is True

    def test_tracks_verification_count(self):
        """Test verification count tracking"""
        game_state = MockGameState(balance=Decimal("1.0"))
        verifier = StateVerifier(game_state)

        verifier.verify({'cash': Decimal("1.0"), 'position_qty': Decimal("0"), 'avg_cost': Decimal("0")})
        verifier.verify({'cash': Decimal("1.0"), 'position_qty': Decimal("0"), 'avg_cost': Decimal("0")})
        verifier.verify({'cash': Decimal("2.0"), 'position_qty': Decimal("0"), 'avg_cost': Decimal("0")})

        assert verifier.total_verifications == 3
        assert verifier.drift_count == 1

    def test_last_verification_stored(self):
        """Test last verification is stored"""
        game_state = MockGameState(balance=Decimal("1.0"))
        verifier = StateVerifier(game_state)

        result = verifier.verify({
            'cash': Decimal("1.0"),
            'position_qty': Decimal("0"),
            'avg_cost': Decimal("0")
        })

        assert verifier.last_verification == result

    def test_result_includes_counts(self):
        """Test result includes drift and verification counts"""
        game_state = MockGameState(balance=Decimal("1.0"))
        verifier = StateVerifier(game_state)

        verifier.verify({'cash': Decimal("2.0"), 'position_qty': Decimal("0"), 'avg_cost': Decimal("0")})
        result = verifier.verify({'cash': Decimal("1.0"), 'position_qty': Decimal("0"), 'avg_cost': Decimal("0")})

        assert result['drift_count'] == 1
        assert result['total_verifications'] == 2


class TestTolerances:
    """Tests for tolerance constants"""

    def test_balance_tolerance(self):
        """Test balance tolerance value"""
        assert BALANCE_TOLERANCE == Decimal('0.000001')

    def test_position_tolerance(self):
        """Test position tolerance value"""
        assert POSITION_TOLERANCE == Decimal('0.000001')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
