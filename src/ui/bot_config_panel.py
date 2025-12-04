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
        self.button_depress_duration_var = None  # Phase A.7: Button depression duration
        self.inter_click_pause_var = None        # Phase A.7: Inter-click pause

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
            '_schema_version': 1,
            'execution_mode': 'ui_layer',  # Default to UI_LAYER mode
            'strategy': 'conservative',    # Default strategy
            'bot_enabled': False,          # Bot disabled by default
            'button_depress_duration_ms': 50,  # Visual feedback duration (ms)
            'inter_click_pause_ms': 100   # Pause between button clicks (ms)
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

        # Validate schema
        allowed_modes = {'backend', 'ui_layer'}
        if default_config.get('execution_mode') not in allowed_modes:
            logger.warning(f"Invalid execution_mode '{default_config.get('execution_mode')}', resetting to ui_layer")
            default_config['execution_mode'] = 'ui_layer'

        allowed_strategies = set(list_strategies())
        if default_config.get('strategy') not in allowed_strategies:
            logger.warning(f"Invalid strategy '{default_config.get('strategy')}', resetting to conservative")
            default_config['strategy'] = 'conservative'

        # Sanitize balance precision (9 decimal places to avoid float noise)
        if 'default_balance_sol' in default_config:
            try:
                default_config['default_balance_sol'] = round(
                    float(default_config['default_balance_sol']), 9
                )
            except (TypeError, ValueError):
                logger.warning("Invalid default_balance_sol; resetting to 0.0")
                default_config['default_balance_sol'] = 0.0

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
        self.dialog.geometry("450x450")  # Phase A.7: Increased height for timing controls
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
        # BALANCE CONFIGURATION (Phase 9.1)
        # ========================================================================

        balance_frame = ttk.LabelFrame(main_frame, text="Balance Configuration", padding="10")
        balance_frame.pack(fill=tk.X, pady=(0, 10))

        # Default balance label and entry
        default_balance_label = ttk.Label(balance_frame, text="Default balance (SOL):")
        default_balance_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)

        self.default_balance_var = tk.StringVar(value=str(self.config.get('default_balance_sol', 0.01)))

        default_balance_entry = ttk.Entry(
            balance_frame,
            textvariable=self.default_balance_var,
            width=12
        )
        default_balance_entry.grid(row=0, column=1, sticky=tk.W, pady=5)

        # Help text
        help_text = ttk.Label(
            balance_frame,
            text="Initial balance for new sessions (can be overridden with balance lock toggle)",
            font=('TkDefaultFont', 8),
            foreground='gray'
        )
        help_text.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

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
        # TIMING CONFIGURATION (Phase A.7)
        # ========================================================================

        timing_frame = ttk.LabelFrame(main_frame, text="UI Button Timing (UI Layer Mode)", padding="10")
        timing_frame.pack(fill=tk.X, pady=(0, 10))

        # Button depress duration
        depress_label = ttk.Label(timing_frame, text="Button depression duration (ms):")
        depress_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        self.button_depress_duration_var = tk.IntVar(value=self.config.get('button_depress_duration_ms', 50))

        depress_spinbox = ttk.Spinbox(
            timing_frame,
            from_=10,
            to=500,
            textvariable=self.button_depress_duration_var,
            width=10
        )
        depress_spinbox.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        depress_info = ttk.Label(
            timing_frame,
            text="(Visual feedback: SUNKEN relief duration)",
            font=('Arial', 8),
            foreground='gray'
        )
        depress_info.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        # Inter-click pause
        pause_label = ttk.Label(timing_frame, text="Pause between button clicks (ms):")
        pause_label.grid(row=2, column=0, sticky=tk.W, pady=5)

        self.inter_click_pause_var = tk.IntVar(value=self.config.get('inter_click_pause_ms', 100))

        pause_spinbox = ttk.Spinbox(
            timing_frame,
            from_=0,
            to=5000,
            textvariable=self.inter_click_pause_var,
            width=10
        )
        pause_spinbox.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        pause_info = ttk.Label(
            timing_frame,
            text="(Human timing: 60-100ms typical, 500ms for slow demo)",
            font=('Arial', 8),
            foreground='gray'
        )
        pause_info.grid(row=3, column=0, columnspan=2, sticky=tk.W)

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
        self.config['button_depress_duration_ms'] = self.button_depress_duration_var.get()  # Phase A.7
        self.config['inter_click_pause_ms'] = self.inter_click_pause_var.get()  # Phase A.7

        # Phase 9.1: Save default balance
        try:
            default_balance = float(self.default_balance_var.get())
            if default_balance < 0:
                messagebox.showerror("Invalid Value", "Default balance must be >= 0")
                return
            self.config['default_balance_sol'] = default_balance
        except ValueError:
            messagebox.showerror("Invalid Value", "Default balance must be a number")
            return

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
