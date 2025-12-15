"""
MenuBarBuilder - Builds the application menu bar

Extracted from MainWindow._create_menu_bar() (Phase 1)
Handles construction of all menus: File, Playback, Recording, Bot, Live Feed, Browser, View, Developer Tools, Help.
"""

import tkinter as tk
from typing import Callable, Dict
import logging

logger = logging.getLogger(__name__)


class MenuBarBuilder:
    """
    Builds the complete menu bar with all application menus.

    Usage:
        callbacks = {
            'load_file': lambda: controller.load_file(),
            'toggle_playback': lambda: controller.toggle_playback(),
            # ... etc
        }
        variables = {
            'recording_var': tk.BooleanVar(),
            'bot_var': tk.BooleanVar(),
            'live_feed_var': tk.BooleanVar(),
            'timing_overlay_var': tk.BooleanVar(),
        }
        builder = MenuBarBuilder(root, callbacks, variables)
        menubar, menu_refs = builder.build()
    """

    def __init__(self, root: tk.Tk, callbacks: Dict[str, Callable], variables: Dict[str, tk.BooleanVar]):
        """
        Initialize MenuBarBuilder.

        Args:
            root: The Tk root window
            callbacks: Dictionary of callback functions keyed by action name
            variables: Dictionary of Tk variables for checkbutton menus
        """
        self.root = root
        self.callbacks = callbacks
        self.variables = variables

    def _get_callback(self, name: str) -> Callable:
        """Get callback by name or return no-op"""
        return self.callbacks.get(name, lambda: None)

    def build(self) -> tuple:
        """
        Build the menu bar and return (menubar, menu_refs).

        Returns:
            tuple: (menubar, dict of menu references for dynamic updates)
        """
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Build all menus
        self._build_file_menu(menubar)
        self._build_playback_menu(menubar)
        self._build_recording_menu(menubar)
        self._build_bot_menu(menubar)
        self._build_live_feed_menu(menubar)
        browser_menu, browser_indices = self._build_browser_menu(menubar)
        self._build_view_menu(menubar)
        dev_menu, dev_indices = self._build_developer_menu(menubar)
        self._build_help_menu(menubar)

        logger.debug("MenuBarBuilder: Menu bar built")

        return menubar, {
            'browser_menu': browser_menu,
            'dev_menu': dev_menu,
            'browser_status_item_index': browser_indices['status'],
            'browser_disconnect_item_index': browser_indices['disconnect'],
            'browser_connect_item_index': browser_indices['connect'],
            'dev_capture_item_index': dev_indices['capture'],
        }

    def _build_file_menu(self, menubar: tk.Menu):
        """Build File menu"""
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Recording...", command=self._get_callback('load_file'))
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._get_callback('exit_app'))

    def _build_playback_menu(self, menubar: tk.Menu):
        """Build Playback menu"""
        playback_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Playback", menu=playback_menu)
        playback_menu.add_command(label="Play/Pause", command=self._get_callback('toggle_playback'))
        playback_menu.add_command(label="Stop", command=self._get_callback('reset_game'))

    def _build_recording_menu(self, menubar: tk.Menu):
        """Build Recording menu"""
        recording_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Recording", menu=recording_menu)

        # Unified Recording Session
        recording_menu.add_command(
            label="Configure & Start Recording...",
            command=self._get_callback('show_recording_config')
        )
        recording_menu.add_command(
            label="Stop Recording",
            command=self._get_callback('stop_recording')
        )
        recording_menu.add_separator()
        recording_menu.add_command(
            label="Open Recordings Folder",
            command=self._get_callback('open_recordings_folder')
        )
        recording_menu.add_command(
            label="Show Recording Status",
            command=self._get_callback('show_recording_status')
        )

    def _build_bot_menu(self, menubar: tk.Menu):
        """Build Bot menu"""
        bot_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Bot", menu=bot_menu)

        bot_menu.add_checkbutton(
            label="Enable Bot",
            variable=self.variables.get('bot_var'),
            command=self._get_callback('toggle_bot')
        )
        bot_menu.add_separator()
        bot_menu.add_command(
            label="Configuration...",
            command=self._get_callback('show_bot_config')
        )
        bot_menu.add_command(
            label="Timing Metrics...",
            command=self._get_callback('show_timing_metrics')
        )
        bot_menu.add_separator()
        bot_menu.add_checkbutton(
            label="Show Timing Overlay",
            variable=self.variables.get('timing_overlay_var'),
            command=self._get_callback('toggle_timing_overlay')
        )

    def _build_live_feed_menu(self, menubar: tk.Menu):
        """Build Live Feed menu"""
        live_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Live Feed", menu=live_menu)

        live_menu.add_checkbutton(
            label="Connect to Live Feed",
            variable=self.variables.get('live_feed_var'),
            command=self._get_callback('toggle_live_feed')
        )

    def _build_browser_menu(self, menubar: tk.Menu) -> tuple:
        """Build Browser menu and return (menu, indices)"""
        browser_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Browser", menu=browser_menu)

        browser_menu.add_command(
            label="Connect to Browser",
            command=self._get_callback('connect_browser')
        )
        browser_menu.add_separator()

        # Status indicators (disabled, display only)
        browser_menu.add_command(
            label="\u26AB Status: Disconnected",  # ⚫
            state=tk.DISABLED
        )
        browser_menu.add_command(
            label="Profile: rugs_bot",
            state=tk.DISABLED
        )
        browser_menu.add_separator()

        # Disconnect command (initially disabled)
        browser_menu.add_command(
            label="Disconnect Browser",
            command=self._get_callback('disconnect_browser'),
            state=tk.DISABLED
        )

        indices = {
            'connect': 0,
            'status': 2,
            'disconnect': 5,
        }

        return browser_menu, indices

    def _build_view_menu(self, menubar: tk.Menu):
        """Build View menu with theme options"""
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)

        # Theme submenu
        theme_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Theme", menu=theme_menu)

        # Dark themes submenu
        dark_theme_menu = tk.Menu(theme_menu, tearoff=0)
        theme_menu.add_cascade(label="Dark Themes", menu=dark_theme_menu)

        change_theme = self._get_callback('change_theme')
        dark_themes = [
            ('cyborg', 'Cyborg - Neon gaming style'),
            ('darkly', 'Darkly - Professional dark'),
            ('superhero', 'Superhero - Bold & vibrant'),
            ('solar', 'Solar - Warm dark theme'),
            ('vapor', 'Vapor - Vaporwave aesthetic'),
        ]
        for theme_id, theme_label in dark_themes:
            dark_theme_menu.add_command(
                label=theme_label,
                command=lambda t=theme_id: change_theme(t)
            )

        # Light themes submenu
        light_theme_menu = tk.Menu(theme_menu, tearoff=0)
        theme_menu.add_cascade(label="Light Themes", menu=light_theme_menu)

        light_themes = [
            ('cosmo', 'Cosmo - Professional blue'),
            ('flatly', 'Flatly - Modern flat design'),
            ('litera', 'Litera - Clean serif style'),
            ('minty', 'Minty - Fresh green accent'),
            ('lumen', 'Lumen - Bright & clean'),
            ('sandstone', 'Sandstone - Warm earth tones'),
            ('yeti', 'Yeti - Cool blue minimal'),
            ('pulse', 'Pulse - Vibrant purple'),
            ('united', 'United - Ubuntu-inspired'),
            ('morph', 'Morph - Soft neumorphic'),
            ('journal', 'Journal - Serif elegant'),
            ('simplex', 'Simplex - Minimalist clean'),
            ('cerculean', 'Cerculean - Sky blue fresh'),
        ]
        for theme_id, theme_label in light_themes:
            light_theme_menu.add_command(
                label=theme_label,
                command=lambda t=theme_id: change_theme(t)
            )

        # UI Style submenu
        view_menu.add_separator()
        ui_style_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="UI Style", menu=ui_style_menu)
        ui_style_menu.add_command(label="Standard \u2713", state=tk.DISABLED)
        ui_style_menu.add_command(
            label="Modern (Game-Like)",
            command=lambda: self._get_callback('set_ui_style')('modern')
        )

    def _build_developer_menu(self, menubar: tk.Menu) -> tuple:
        """Build Developer Tools menu and return (menu, indices)"""
        dev_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Developer Tools", menu=dev_menu)

        # Raw capture toggle
        dev_menu.add_command(
            label="Start Raw Capture",
            command=self._get_callback('toggle_raw_capture')
        )
        dev_menu.add_separator()
        dev_menu.add_command(
            label="Analyze Last Capture",
            command=self._get_callback('analyze_capture')
        )
        dev_menu.add_command(
            label="Open Captures Folder",
            command=self._get_callback('open_captures_folder')
        )
        dev_menu.add_separator()
        dev_menu.add_command(
            label="Show Capture Status",
            command=self._get_callback('show_capture_status')
        )
        dev_menu.add_separator()
        dev_menu.add_command(
            label="Open Debug Terminal",
            command=self._get_callback('open_debug_terminal')
        )

        indices = {
            'capture': 0,  # Index of "Start/Stop Raw Capture"
        }

        return dev_menu, indices

    def _build_help_menu(self, menubar: tk.Menu):
        """Build Help menu"""
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._get_callback('show_about'))
