"""
Layout Manager Module
Professional layout management system for organizing UI panels
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PanelPosition(Enum):
    """Panel positioning options"""
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"


class ResizeMode(Enum):
    """Panel resize behavior"""
    FIXED = "fixed"          # Fixed size
    FLEXIBLE = "flexible"    # Can grow/shrink
    PROPORTIONAL = "proportional"  # Maintains proportions


@dataclass
class PanelConfig:
    """Configuration for a UI panel"""
    name: str
    position: PanelPosition
    min_width: Optional[int] = None
    min_height: Optional[int] = None
    max_width: Optional[int] = None
    max_height: Optional[int] = None
    resize_mode: ResizeMode = ResizeMode.FLEXIBLE
    weight: int = 1  # Grid weight for resizing
    padding: int = 5
    background: str = '#1a1a1a'
    visible: bool = True


class Panel:
    """
    Base panel class for UI sections
    Manages a self-contained UI panel with its own layout
    """

    def __init__(self, parent: tk.Widget, config: PanelConfig):
        self.config = config
        self.parent = parent

        # Create panel frame
        self.frame = tk.Frame(
            parent,
            bg=config.background,
            relief=tk.FLAT,
            borderwidth=0
        )

        # Store widgets for management
        self.widgets: Dict[str, tk.Widget] = {}
        self._visible = config.visible

        logger.debug(f"Panel '{config.name}' initialized at {config.position.value}")

    def show(self):
        """Show the panel"""
        if not self._visible:
            self.frame.pack(
                side=self._get_pack_side(),
                fill=self._get_pack_fill(),
                expand=self._get_pack_expand(),
                padx=self.config.padding,
                pady=self.config.padding
            )
            self._visible = True
            logger.debug(f"Panel '{self.config.name}' shown")

    def hide(self):
        """Hide the panel"""
        if self._visible:
            self.frame.pack_forget()
            self._visible = False
            logger.debug(f"Panel '{self.config.name}' hidden")

    def _get_pack_side(self) -> str:
        """Get pack() side parameter based on position"""
        position_to_side = {
            PanelPosition.TOP: tk.TOP,
            PanelPosition.BOTTOM: tk.BOTTOM,
            PanelPosition.LEFT: tk.LEFT,
            PanelPosition.RIGHT: tk.RIGHT,
            PanelPosition.CENTER: tk.TOP  # Center uses top with expand
        }
        return position_to_side.get(self.config.position, tk.TOP)

    def _get_pack_fill(self) -> str:
        """Get pack() fill parameter based on position"""
        if self.config.position in [PanelPosition.LEFT, PanelPosition.RIGHT]:
            return tk.Y
        elif self.config.position in [PanelPosition.TOP, PanelPosition.BOTTOM]:
            return tk.X
        else:  # CENTER
            return tk.BOTH

    def _get_pack_expand(self) -> bool:
        """Get pack() expand parameter based on resize mode"""
        return self.config.resize_mode != ResizeMode.FIXED

    def add_widget(self, name: str, widget: tk.Widget):
        """Add a widget to the panel's widget registry"""
        self.widgets[name] = widget

    def get_widget(self, name: str) -> Optional[tk.Widget]:
        """Get a widget by name"""
        return self.widgets.get(name)

    def clear(self):
        """Clear all widgets from the panel"""
        for widget in self.frame.winfo_children():
            widget.destroy()
        self.widgets.clear()


class LayoutManager:
    """
    Main layout manager for organizing UI panels
    Handles panel creation, positioning, and responsive behavior
    """

    def __init__(self, root: tk.Widget, theme: Optional[Dict] = None):
        self.root = root
        self.theme = theme or self._default_theme()
        self.panels: Dict[str, Panel] = {}

        # Create main container
        self.main_container = tk.Frame(root, bg=self.theme['bg'])
        self.main_container.pack(fill=tk.BOTH, expand=True)

        logger.info("LayoutManager initialized")

    @staticmethod
    def _default_theme() -> Dict:
        """Default dark theme"""
        return {
            'bg': '#1a1a1a',
            'panel': '#2a2a2a',
            'text': '#ffffff',
            'accent': '#00ff88',
            'error': '#ff3366',
            'warning': '#ffcc00',
            'info': '#3366ff',
            'button_bg': '#444444',
            'button_fg': '#ffffff',
            'input_bg': '#333333',
            'input_fg': '#ffffff',
        }

    def create_panel(self, config: PanelConfig) -> Panel:
        """
        Create and register a new panel

        Args:
            config: Panel configuration

        Returns:
            Created Panel instance
        """
        if config.name in self.panels:
            logger.warning(f"Panel '{config.name}' already exists, returning existing")
            return self.panels[config.name]

        panel = Panel(self.main_container, config)
        self.panels[config.name] = panel

        # Show panel if visible by default
        if config.visible:
            panel.show()

        logger.info(f"Panel '{config.name}' created at {config.position.value}")
        return panel

    def get_panel(self, name: str) -> Optional[Panel]:
        """Get a panel by name"""
        return self.panels.get(name)

    def show_panel(self, name: str):
        """Show a panel by name"""
        panel = self.panels.get(name)
        if panel:
            panel.show()

    def hide_panel(self, name: str):
        """Hide a panel by name"""
        panel = self.panels.get(name)
        if panel:
            panel.hide()

    def toggle_panel(self, name: str):
        """Toggle panel visibility"""
        panel = self.panels.get(name)
        if panel:
            if panel._visible:
                panel.hide()
            else:
                panel.show()

    def resize_panel(self, name: str, width: Optional[int] = None, height: Optional[int] = None):
        """Resize a panel"""
        panel = self.panels.get(name)
        if panel:
            if width:
                panel.frame.config(width=width)
            if height:
                panel.frame.config(height=height)

    def create_grid_layout(self, rows: int, cols: int):
        """
        Create a grid-based layout (alternative to pack-based)
        Useful for complex layouts

        Args:
            rows: Number of rows
            cols: Number of columns
        """
        # Configure grid weights for responsive design
        for i in range(rows):
            self.main_container.grid_rowconfigure(i, weight=1)
        for j in range(cols):
            self.main_container.grid_columnconfigure(j, weight=1)

        logger.info(f"Grid layout created: {rows}x{cols}")

    def apply_theme(self, theme: Dict):
        """Apply a color theme to all panels"""
        self.theme = theme
        self.main_container.config(bg=theme['bg'])

        for panel in self.panels.values():
            panel.frame.config(bg=theme.get('panel', theme['bg']))

        logger.info("Theme applied to layout")

    def get_layout_info(self) -> Dict:
        """Get information about current layout"""
        return {
            'panels': list(self.panels.keys()),
            'visible_panels': [name for name, panel in self.panels.items() if panel._visible],
            'theme': self.theme
        }
