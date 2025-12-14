"""Tests for StatusBarBuilder"""

import pytest
import tkinter as tk
from ui.builders.status_bar_builder import StatusBarBuilder


@pytest.fixture
def root():
    """Create a Tk root window for testing"""
    root = tk.Tk()
    root.withdraw()  # Hide the window
    yield root
    root.destroy()


class TestStatusBarBuilder:
    """Tests for StatusBarBuilder"""

    def test_build_returns_dict(self, root):
        """build() should return a dictionary of widgets"""
        builder = StatusBarBuilder(root)
        result = builder.build()
        assert isinstance(result, dict)

    def test_build_creates_tick_label(self, root):
        """build() should create tick_label"""
        builder = StatusBarBuilder(root)
        widgets = builder.build()
        assert 'tick_label' in widgets
        assert isinstance(widgets['tick_label'], tk.Label)

    def test_build_creates_price_label(self, root):
        """build() should create price_label"""
        builder = StatusBarBuilder(root)
        widgets = builder.build()
        assert 'price_label' in widgets
        assert isinstance(widgets['price_label'], tk.Label)

    def test_build_creates_phase_label(self, root):
        """build() should create phase_label"""
        builder = StatusBarBuilder(root)
        widgets = builder.build()
        assert 'phase_label' in widgets
        assert isinstance(widgets['phase_label'], tk.Label)

    def test_build_creates_player_profile_label(self, root):
        """build() should create player_profile_label"""
        builder = StatusBarBuilder(root)
        widgets = builder.build()
        assert 'player_profile_label' in widgets
        assert isinstance(widgets['player_profile_label'], tk.Label)

    def test_build_creates_browser_status_label(self, root):
        """build() should create browser_status_label"""
        builder = StatusBarBuilder(root)
        widgets = builder.build()
        assert 'browser_status_label' in widgets
        assert isinstance(widgets['browser_status_label'], tk.Label)

    def test_build_creates_status_bar_frame(self, root):
        """build() should create the status bar frame"""
        builder = StatusBarBuilder(root)
        widgets = builder.build()
        assert 'status_bar' in widgets
        assert isinstance(widgets['status_bar'], tk.Frame)

    def test_tick_label_initial_text(self, root):
        """tick_label should have initial text 'TICK: 0'"""
        builder = StatusBarBuilder(root)
        widgets = builder.build()
        assert widgets['tick_label'].cget('text') == 'TICK: 0'

    def test_price_label_initial_text(self, root):
        """price_label should have initial text 'PRICE: 1.0000 X'"""
        builder = StatusBarBuilder(root)
        widgets = builder.build()
        assert widgets['price_label'].cget('text') == 'PRICE: 1.0000 X'
