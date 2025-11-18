"""
Bot Configuration Panel - Phase 8.4

Minimal configuration UI for bot settings:
- Execution mode (BACKEND vs UI_LAYER)
- Strategy selection
- Enable/disable bot
- Configuration persistence
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from bot.execution_mode import ExecutionMode
from bot.strategies import list_strategies

logger = logging.getLogger(__name__)


class BotConfigPanel:
    """
    Bot configuration dialog

    Phase 8.4: Minimal configuration UI for essential bot settings
    - Execution mode (BACKEND for training, UI_LAYER for live prep)
    - Strategy selection (conservative, aggressive, sidebet)
    - Enable/disable toggle
    - Configuration persistence to JSON file
    """

    def __init__(self, parent: tk.Tk, config_file: str = "bot_config.json"):
        """
        Initialize bot configuration panel

        Args:
            parent: Parent window (for modal dialog)
            config_file: Path to configuration file (relative to project root)
        """
        self.parent = parent
        self.config_file = Path(config_file)

        # Current configuration values
        self.config = self._load_config()

        # Dialog window (will be created when show() is called)
        self.dialog = None

        # UI variables
        self.execution_mode_var = None
        self.strategy_var = None
        self.bot_enabled_var = None

        logger.info(f"BotConfigPanel initialized (config: {self.config_file})")

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from JSON file

        Returns:
            Configuration dictionary with defaults
        """
        # Default configuration
        # Phase 8 Fix: Default to UI_LAYER mode (for live trading preparation)
        # BACKEND mode is for fast training, UI_LAYER learns realistic timing
        default_config = {
            'execution_mode': 'ui_layer',  # Default to UI_LAYER mode
            'strategy': 'conservative',    # Default strategy
            'bot_enabled': False           # Bot disabled by default
        }

        # Try to load existing config
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults (in case new keys added)
                    default_config.update(loaded_config)
                    logger.info(f"Loaded bot config from {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to load bot config: {e}")
        else:
            # Phase 8 Fix: Create default config file on first run
            logger.info("No bot config found, creating default configuration")
            self._save_default_config(default_config)

        return default_config

    def _save_default_config(self, config: Dict[str, Any]) -> None:
        """
        Save default configuration to file (called on first run)

        Args:
            config: Configuration dictionary to save
        """
        try:
            # Ensure parent directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            # Write config to file
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Created default bot config at {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to create default config: {e}")

    def _save_config(self) -> bool:
        """
        Save configuration to JSON file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            # Write config to file
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)

            logger.info(f"Saved bot config to {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save bot config: {e}")
            messagebox.showerror("Save Error", f"Failed to save configuration:\n{e}")
            return False

    def show(self) -> Optional[Dict[str, Any]]:
        """
        Show configuration dialog (modal)

        Returns:
            Updated configuration if user clicked OK, None if cancelled
        """
        # Create modal dialog
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Bot Configuration")
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)

        # Make dialog modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Create UI
        self._create_ui()

        # Center dialog on parent
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Wait for dialog to close
        self.dialog.wait_window()

        # Return config if user clicked OK
        return getattr(self, '_result', None)

    def _create_ui(self):
        """Create dialog UI elements"""
        # Main container with padding
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ========================================================================
        # EXECUTION MODE
        # ========================================================================

        mode_frame = ttk.LabelFrame(main_frame, text="Execution Mode", padding="10")
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        self.execution_mode_var = tk.StringVar(value=self.config['execution_mode'])

        # BACKEND mode radio button
        backend_radio = ttk.Radiobutton(
            mode_frame,
            text="Backend (Fast - for training)",
            variable=self.execution_mode_var,
            value='backend'
        )
        backend_radio.pack(anchor=tk.W, pady=2)

        # UI_LAYER mode radio button
        ui_layer_radio = ttk.Radiobutton(
            mode_frame,
            text="UI Layer (Realistic - for live prep)",
            variable=self.execution_mode_var,
            value='ui_layer'
        )
        ui_layer_radio.pack(anchor=tk.W, pady=2)

        # Info label
        info_label = ttk.Label(
            mode_frame,
            text="Backend: Direct calls (0ms)\nUI Layer: Simulated clicks (10-50ms delays)",
            font=('Arial', 8),
            foreground='gray'
        )
        info_label.pack(anchor=tk.W, pady=(5, 0))

        # ========================================================================
        # STRATEGY SELECTION
        # ========================================================================

        strategy_frame = ttk.LabelFrame(main_frame, text="Trading Strategy", padding="10")
        strategy_frame.pack(fill=tk.X, pady=(0, 10))

        self.strategy_var = tk.StringVar(value=self.config['strategy'])

        # Strategy dropdown
        strategy_label = ttk.Label(strategy_frame, text="Strategy:")
        strategy_label.pack(side=tk.LEFT, padx=(0, 10))

        strategies = list_strategies()
        strategy_combo = ttk.Combobox(
            strategy_frame,
            textvariable=self.strategy_var,
            values=strategies,
            state='readonly',
            width=20
        )
        strategy_combo.pack(side=tk.LEFT)

        # ========================================================================
        # BOT ENABLE/DISABLE
        # ========================================================================

        enable_frame = ttk.LabelFrame(main_frame, text="Bot Control", padding="10")
        enable_frame.pack(fill=tk.X, pady=(0, 10))

        self.bot_enabled_var = tk.BooleanVar(value=self.config['bot_enabled'])

        enable_checkbox = ttk.Checkbutton(
            enable_frame,
            text="Enable bot on startup",
            variable=self.bot_enabled_var
        )
        enable_checkbox.pack(anchor=tk.W)

        # ========================================================================
        # BUTTONS
        # ========================================================================

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        # OK button
        ok_button = ttk.Button(
            button_frame,
            text="OK",
            command=self._on_ok,
            width=10
        )
        ok_button.pack(side=tk.RIGHT, padx=(5, 0))

        # Cancel button
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=10
        )
        cancel_button.pack(side=tk.RIGHT)

        # Make OK button default (Enter key)
        self.dialog.bind('<Return>', lambda e: self._on_ok())
        self.dialog.bind('<Escape>', lambda e: self._on_cancel())

    def _on_ok(self):
        """Handle OK button click"""
        # Update config with current values
        self.config['execution_mode'] = self.execution_mode_var.get()
        self.config['strategy'] = self.strategy_var.get()
        self.config['bot_enabled'] = self.bot_enabled_var.get()

        # Save config to file
        if self._save_config():
            # Set result and close dialog
            self._result = self.config.copy()
            self.dialog.destroy()

    def _on_cancel(self):
        """Handle Cancel button click"""
        # No result (user cancelled)
        self._result = None
        self.dialog.destroy()

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration (without showing dialog)

        Returns:
            Current configuration dictionary
        """
        return self.config.copy()

    def get_execution_mode(self) -> ExecutionMode:
        """
        Get execution mode as enum

        Returns:
            ExecutionMode enum value
        """
        mode_str = self.config['execution_mode']
        return ExecutionMode.BACKEND if mode_str == 'backend' else ExecutionMode.UI_LAYER

    def get_strategy(self) -> str:
        """
        Get strategy name

        Returns:
            Strategy name string
        """
        return self.config['strategy']

    def is_bot_enabled(self) -> bool:
        """
        Check if bot should be enabled on startup

        Returns:
            True if bot should be enabled, False otherwise
        """
        return self.config['bot_enabled']
