"""Tests for MenuBarBuilder"""

import pytest
import tkinter as tk
from ui.builders.menu_bar_builder import MenuBarBuilder


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
        'load_file': lambda: None,
        'exit_app': lambda: None,
        'toggle_playback': lambda: None,
        'reset_game': lambda: None,
        'show_recording_config': lambda: None,
        'stop_recording': lambda: None,
        'toggle_recording': lambda: None,
        'open_recordings_folder': lambda: None,
        'show_recording_status': lambda: None,
        'start_demo_session': lambda: None,
        'end_demo_session': lambda: None,
        'start_demo_game': lambda: None,
        'end_demo_game': lambda: None,
        'show_demo_status': lambda: None,
        'toggle_bot': lambda: None,
        'show_bot_config': lambda: None,
        'show_timing_metrics': lambda: None,
        'toggle_timing_overlay': lambda: None,
        'toggle_live_feed': lambda: None,
        'connect_browser': lambda: None,
        'disconnect_browser': lambda: None,
        'change_theme': lambda t: None,
        'set_ui_style': lambda s: None,
        'toggle_raw_capture': lambda: None,
        'analyze_capture': lambda: None,
        'open_captures_folder': lambda: None,
        'show_capture_status': lambda: None,
        'show_about': lambda: None,
    }


@pytest.fixture
def variables(root):
    """Create UI variables"""
    return {
        'recording_var': tk.BooleanVar(value=False),
        'bot_var': tk.BooleanVar(value=False),
        'live_feed_var': tk.BooleanVar(value=False),
        'timing_overlay_var': tk.BooleanVar(value=False),
    }


class TestMenuBarBuilder:
    """Tests for MenuBarBuilder"""

    def test_build_returns_tuple(self, root, callbacks, variables):
        """build() should return a tuple of (menubar, refs)"""
        builder = MenuBarBuilder(root, callbacks, variables)
        result = builder.build()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_build_creates_menu(self, root, callbacks, variables):
        """build() should create a tk.Menu"""
        builder = MenuBarBuilder(root, callbacks, variables)
        menubar, refs = builder.build()
        assert isinstance(menubar, tk.Menu)

    def test_build_returns_refs_dict(self, root, callbacks, variables):
        """build() should return a refs dictionary"""
        builder = MenuBarBuilder(root, callbacks, variables)
        menubar, refs = builder.build()
        assert isinstance(refs, dict)

    def test_refs_contains_browser_menu(self, root, callbacks, variables):
        """refs should contain browser_menu for dynamic updates"""
        builder = MenuBarBuilder(root, callbacks, variables)
        menubar, refs = builder.build()
        assert 'browser_menu' in refs

    def test_refs_contains_dev_menu(self, root, callbacks, variables):
        """refs should contain dev_menu for dynamic updates"""
        builder = MenuBarBuilder(root, callbacks, variables)
        menubar, refs = builder.build()
        assert 'dev_menu' in refs

    def test_refs_contains_menu_indices(self, root, callbacks, variables):
        """refs should contain menu item indices for updates"""
        builder = MenuBarBuilder(root, callbacks, variables)
        menubar, refs = builder.build()
        assert 'browser_status_item_index' in refs
        assert 'browser_disconnect_item_index' in refs
        assert 'dev_capture_item_index' in refs
