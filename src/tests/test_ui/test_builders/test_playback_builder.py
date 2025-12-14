"""Tests for PlaybackBuilder"""

import pytest
import tkinter as tk
from ui.builders.playback_builder import PlaybackBuilder


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
        'load_game': lambda: None,
        'toggle_playback': lambda: None,
        'step_forward': lambda: None,
        'reset_game': lambda: None,
        'set_speed': lambda s: None,
    }


class TestPlaybackBuilder:
    """Tests for PlaybackBuilder"""

    def test_build_returns_dict(self, root, callbacks):
        """build() should return a dictionary of widgets"""
        builder = PlaybackBuilder(root, callbacks)
        result = builder.build()
        assert isinstance(result, dict)

    def test_build_creates_playback_row(self, root, callbacks):
        """build() should create playback_row frame"""
        builder = PlaybackBuilder(root, callbacks)
        widgets = builder.build()
        assert 'playback_row' in widgets
        assert isinstance(widgets['playback_row'], tk.Frame)

    def test_build_creates_load_button(self, root, callbacks):
        """build() should create load_button"""
        builder = PlaybackBuilder(root, callbacks)
        widgets = builder.build()
        assert 'load_button' in widgets
        assert isinstance(widgets['load_button'], tk.Button)

    def test_build_creates_play_button(self, root, callbacks):
        """build() should create play_button"""
        builder = PlaybackBuilder(root, callbacks)
        widgets = builder.build()
        assert 'play_button' in widgets
        assert isinstance(widgets['play_button'], tk.Button)

    def test_build_creates_step_button(self, root, callbacks):
        """build() should create step_button"""
        builder = PlaybackBuilder(root, callbacks)
        widgets = builder.build()
        assert 'step_button' in widgets
        assert isinstance(widgets['step_button'], tk.Button)

    def test_build_creates_reset_button(self, root, callbacks):
        """build() should create reset_button"""
        builder = PlaybackBuilder(root, callbacks)
        widgets = builder.build()
        assert 'reset_button' in widgets
        assert isinstance(widgets['reset_button'], tk.Button)

    def test_build_creates_speed_label(self, root, callbacks):
        """build() should create speed_label"""
        builder = PlaybackBuilder(root, callbacks)
        widgets = builder.build()
        assert 'speed_label' in widgets
        assert isinstance(widgets['speed_label'], tk.Label)

    def test_play_button_initially_disabled(self, root, callbacks):
        """play_button should be initially disabled"""
        builder = PlaybackBuilder(root, callbacks)
        widgets = builder.build()
        assert widgets['play_button'].cget('state') == tk.DISABLED

    def test_speed_buttons_exist(self, root, callbacks):
        """Speed control buttons should exist"""
        builder = PlaybackBuilder(root, callbacks)
        widgets = builder.build()
        assert 'speed_buttons' in widgets
        assert len(widgets['speed_buttons']) == 5  # 0.25x, 0.5x, 1x, 2x, 5x
