"""Tests for ActionBuilder"""

import pytest
import tkinter as tk
from tkinter import ttk
from ui.builders.action_builder import ActionBuilder


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
        'execute_sidebet': lambda: None,
        'execute_buy': lambda: None,
        'execute_sell': lambda: None,
        'set_sell_percentage': lambda p: None,
        'toggle_bot': lambda: None,
        'on_strategy_changed': lambda e: None,
    }


class TestActionBuilder:
    """Tests for ActionBuilder"""

    def test_build_returns_dict(self, root, callbacks):
        """build() should return a dictionary of widgets"""
        builder = ActionBuilder(root, callbacks, ['conservative', 'aggressive'], 'conservative')
        result = builder.build()
        assert isinstance(result, dict)

    def test_build_creates_action_row(self, root, callbacks):
        """build() should create action_row frame"""
        builder = ActionBuilder(root, callbacks, ['conservative'], 'conservative')
        widgets = builder.build()
        assert 'action_row' in widgets
        assert isinstance(widgets['action_row'], tk.Frame)

    def test_build_creates_sidebet_button(self, root, callbacks):
        """build() should create sidebet_button"""
        builder = ActionBuilder(root, callbacks, ['conservative'], 'conservative')
        widgets = builder.build()
        assert 'sidebet_button' in widgets
        assert isinstance(widgets['sidebet_button'], tk.Button)

    def test_build_creates_buy_button(self, root, callbacks):
        """build() should create buy_button"""
        builder = ActionBuilder(root, callbacks, ['conservative'], 'conservative')
        widgets = builder.build()
        assert 'buy_button' in widgets
        assert isinstance(widgets['buy_button'], tk.Button)

    def test_build_creates_sell_button(self, root, callbacks):
        """build() should create sell_button"""
        builder = ActionBuilder(root, callbacks, ['conservative'], 'conservative')
        widgets = builder.build()
        assert 'sell_button' in widgets
        assert isinstance(widgets['sell_button'], tk.Button)

    def test_build_creates_percentage_buttons(self, root, callbacks):
        """build() should create percentage selector buttons"""
        builder = ActionBuilder(root, callbacks, ['conservative'], 'conservative')
        widgets = builder.build()
        assert 'percentage_buttons' in widgets
        assert isinstance(widgets['percentage_buttons'], dict)
        # Should have 4 percentage options: 10%, 25%, 50%, 100%
        assert len(widgets['percentage_buttons']) == 4

    def test_build_creates_bot_toggle_button(self, root, callbacks):
        """build() should create bot_toggle_button"""
        builder = ActionBuilder(root, callbacks, ['conservative'], 'conservative')
        widgets = builder.build()
        assert 'bot_toggle_button' in widgets
        assert isinstance(widgets['bot_toggle_button'], tk.Button)

    def test_build_creates_strategy_dropdown(self, root, callbacks):
        """build() should create strategy_dropdown"""
        builder = ActionBuilder(root, callbacks, ['conservative', 'aggressive'], 'conservative')
        widgets = builder.build()
        assert 'strategy_dropdown' in widgets
        assert isinstance(widgets['strategy_dropdown'], ttk.Combobox)

    def test_build_creates_status_labels(self, root, callbacks):
        """build() should create status labels"""
        builder = ActionBuilder(root, callbacks, ['conservative'], 'conservative')
        widgets = builder.build()
        assert 'bot_status_label' in widgets
        assert 'position_label' in widgets
        assert 'sidebet_status_label' in widgets

    def test_bot_toggle_initially_disabled(self, root, callbacks):
        """bot_toggle_button should be initially disabled"""
        builder = ActionBuilder(root, callbacks, ['conservative'], 'conservative')
        widgets = builder.build()
        assert widgets['bot_toggle_button'].cget('state') == tk.DISABLED
