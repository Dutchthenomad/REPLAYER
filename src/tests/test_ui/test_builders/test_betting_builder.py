"""Tests for BettingBuilder"""

import pytest
import tkinter as tk
from decimal import Decimal
from ui.builders.betting_builder import BettingBuilder


@pytest.fixture
def root():
    """Create a Tk root window for testing"""
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def callbacks():
    """Create mock callbacks"""
    return {
        'clear_bet': lambda: None,
        'increment_bet': lambda amount: None,
        'half_bet': lambda: None,
        'double_bet': lambda: None,
        'max_bet': lambda: None,
        'toggle_balance_lock': lambda: None,
    }


class TestBettingBuilder:
    """Tests for BettingBuilder"""

    def test_build_returns_dict(self, root, callbacks):
        """build() should return a dictionary of widgets"""
        builder = BettingBuilder(root, callbacks, Decimal('0.001'), Decimal('1.0'))
        result = builder.build()
        assert isinstance(result, dict)

    def test_build_creates_bet_row(self, root, callbacks):
        """build() should create bet_row frame"""
        builder = BettingBuilder(root, callbacks, Decimal('0.001'), Decimal('1.0'))
        widgets = builder.build()
        assert 'bet_row' in widgets
        assert isinstance(widgets['bet_row'], tk.Frame)

    def test_build_creates_bet_entry(self, root, callbacks):
        """build() should create bet_entry"""
        builder = BettingBuilder(root, callbacks, Decimal('0.001'), Decimal('1.0'))
        widgets = builder.build()
        assert 'bet_entry' in widgets
        assert isinstance(widgets['bet_entry'], tk.Entry)

    def test_build_creates_balance_label(self, root, callbacks):
        """build() should create balance_label"""
        builder = BettingBuilder(root, callbacks, Decimal('0.001'), Decimal('1.0'))
        widgets = builder.build()
        assert 'balance_label' in widgets
        assert isinstance(widgets['balance_label'], tk.Label)

    def test_build_creates_increment_buttons(self, root, callbacks):
        """build() should create all increment buttons"""
        builder = BettingBuilder(root, callbacks, Decimal('0.001'), Decimal('1.0'))
        widgets = builder.build()
        assert 'increment_001_button' in widgets
        assert 'increment_01_button' in widgets
        assert 'increment_10_button' in widgets
        assert 'increment_1_button' in widgets

    def test_bet_entry_has_default_value(self, root, callbacks):
        """bet_entry should have the default bet value"""
        builder = BettingBuilder(root, callbacks, Decimal('0.001'), Decimal('1.0'))
        widgets = builder.build()
        assert widgets['bet_entry'].get() == '0.001'

    def test_balance_label_shows_initial_balance(self, root, callbacks):
        """balance_label should show the initial balance"""
        builder = BettingBuilder(root, callbacks, Decimal('0.001'), Decimal('1.5'))
        widgets = builder.build()
        assert '1.5' in widgets['balance_label'].cget('text')
