"""
Configuration module for Rugs Replay Viewer
Centralizes all constants, settings, and configuration
"""

import os
from pathlib import Path
from decimal import Decimal
from typing import Dict, Any, Optional
import json

class Config:
    """Configuration management with support for environment variables and config files"""
    
    # ========== Financial Settings ==========
    FINANCIAL = {
        'initial_balance': Decimal('0.100'),
        'default_bet': Decimal('0.001'),
        'min_bet': Decimal('0.001'),
        'max_bet': Decimal('1.0'),
        'decimal_precision': 10,
        'commission_rate': Decimal('0.0025'),  # 0.25% trading fee
    }
    
    # ========== Game Rules ==========
    GAME_RULES = {
        'sidebet_multiplier': Decimal('5.0'),
        'sidebet_window_ticks': 40,
        'sidebet_cooldown_ticks': 5,
        'rug_liquidation_price': Decimal('0.02'),
        'max_position_size': Decimal('10.0'),
        'stop_loss_threshold': Decimal('0.5'),  # 50% loss triggers stop
    }
    
    # ========== Playback Settings ==========
    PLAYBACK = {
        'default_delay': 0.25,
        'min_speed': 0.1,
        'max_speed': 5.0,
        'default_speed': 1.0,
        'auto_play_next': True,
        'skip_cooldown_phases': False,
    }
    
    # ========== UI Settings ==========
    UI = {
        'window_width': 1200,
        'window_height': 800,
        'chart_height': 300,
        'controls_height': 150,
        'stats_panel_width': 700,
        'trading_panel_width': 400,
        'chart_update_interval': 0.1,
        'animation_duration': 200,
        'font_family': 'Arial',
        'font_size_base': 10,
    }
    
    # ========== Memory Management ==========
    MEMORY = {
        'max_position_history': 1000,
        'max_chart_points': 500,
        'max_toasts': 5,
        'max_log_entries': 10000,
        'cache_size': 100,
        'cleanup_interval': 60,  # seconds
    }
    
    # ========== File Settings ==========
    FILES = {
        'recordings_dir': Path(os.getenv(
            'RUGS_RECORDINGS_DIR',
            str(Path(__file__).parent / 'rugs_recordings')
        )),
        'config_dir': Path(os.getenv(
            'RUGS_CONFIG_DIR',
            str(Path.home() / '.rugs_viewer')
        )),
        'log_dir': Path(os.getenv(
            'RUGS_LOG_DIR',
            str(Path.home() / '.rugs_viewer' / 'logs')
        )),
        'max_file_size_mb': 100,
        'backup_count': 3,
    }

    # ========== Live Feed Settings ==========
    LIVE_FEED = {
        'ring_buffer_size': 5000,  # Max ticks to keep in memory (configurable)
        'auto_recording': True,     # Auto-record live games (explicit opt-out)
        'recording_buffer_size': 100,  # Ticks to buffer before disk flush
    }
    
    # ========== Logging Settings ==========
    LOGGING = {
        'level': os.getenv('LOG_LEVEL', 'INFO'),
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'date_format': '%Y-%m-%d %H:%M:%S',
        'max_bytes': 5 * 1024 * 1024,  # 5MB
        'backup_count': 3,
        'console_output': True,
    }
    
    # ========== Flat Config Attributes (for bot compatibility) ==========
    # Financial
    MIN_BET_SOL = Decimal('0.001')
    MAX_BET_SOL = Decimal('1.0')
    DEFAULT_BET_SOL = Decimal('0.001')

    # Sidebet
    SIDEBET_MULTIPLIER = Decimal('5.0')
    SIDEBET_WINDOW_TICKS = 40
    SIDEBET_COOLDOWN_TICKS = 5

    # Trading restrictions
    BLOCKED_PHASES_FOR_TRADING = ["COOLDOWN", "RUG_EVENT", "RUG_EVENT_1", "UNKNOWN"]

    # Initial balance
    INITIAL_BALANCE_SOL = Decimal('0.100')

    # Position history
    MAX_POSITION_HISTORY = 1000

    # ========== Bot Settings ==========
    BOT = {
        'decision_delay': 0.5,
        'max_consecutive_losses': 5,
        'risk_per_trade': Decimal('0.02'),  # 2% risk per trade
        'take_profit_multiplier': Decimal('2.0'),
        'stop_loss_multiplier': Decimal('0.5'),
        'confidence_threshold': 0.6,
    }
    
    # ========== Network Settings ==========
    NETWORK = {
        'timeout': 30,
        'max_retries': 3,
        'retry_delay': 1,
        'websocket_heartbeat': 30,
    }
    
    # ========== Color Themes ==========
    THEMES = {
        'dark': {
            'bg': '#1a1a1a',
            'panel': '#2a2a2a',
            'text': '#ffffff',
            'green': '#00ff88',
            'red': '#ff3366',
            'yellow': '#ffcc00',
            'blue': '#3366ff',
            'gray': '#666666',
            'chart_bg': '#0a0a0a',
            'chart_grid': '#333333',
        },
        'light': {
            'bg': '#ffffff',
            'panel': '#f0f0f0',
            'text': '#000000',
            'green': '#00cc66',
            'red': '#cc2244',
            'yellow': '#dd9900',
            'blue': '#2255dd',
            'gray': '#999999',
            'chart_bg': '#fafafa',
            'chart_grid': '#dddddd',
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration, optionally loading from file"""
        self.config_file = config_file
        self._custom_settings = {}
        
        # Create directories if they don't exist
        self._ensure_directories()
        
        # Load custom configuration if provided
        if config_file:
            self.load_from_file(config_file)
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        for path in [self.FILES['recordings_dir'], 
                    self.FILES['config_dir'], 
                    self.FILES['log_dir']]:
            path.mkdir(parents=True, exist_ok=True)
    
    def load_from_file(self, filepath: str):
        """Load configuration from JSON file"""
        try:
            with open(filepath, 'r') as f:
                self._custom_settings = json.load(f)
                logger.info(f"Loaded configuration from {filepath}")
        except FileNotFoundError:
            logger.warning(f"Config file not found: {filepath}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid config file: {e}")
    
    def save_to_file(self, filepath: str):
        """Save current configuration to JSON file"""
        config_dict = {
            'financial': {k: str(v) if isinstance(v, Decimal) else v 
                         for k, v in self.FINANCIAL.items()},
            'game_rules': {k: str(v) if isinstance(v, Decimal) else v 
                          for k, v in self.GAME_RULES.items()},
            'playback': self.PLAYBACK,
            'ui': self.UI,
            'memory': self.MEMORY,
            'bot': {k: str(v) if isinstance(v, Decimal) else v 
                   for k, v in self.BOT.items()},
        }
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
            logger.info(f"Saved configuration to {filepath}")
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration value with support for custom settings"""
        # Check custom settings first
        if section in self._custom_settings:
            if key in self._custom_settings[section]:
                return self._custom_settings[section][key]
        
        # Fall back to default settings
        section_dict = getattr(self, section.upper(), {})
        return section_dict.get(key, default)
    
    def set(self, section: str, key: str, value: Any):
        """Set a configuration value"""
        if section not in self._custom_settings:
            self._custom_settings[section] = {}
        self._custom_settings[section][key] = value
    
    @property
    def current_theme(self) -> Dict[str, str]:
        """Get current color theme"""
        theme_name = self.get('ui', 'theme', 'dark')
        return self.THEMES.get(theme_name, self.THEMES['dark'])

# Global configuration instance
config = Config()

# Logger setup should be imported from services.logger after config is initialized
import logging
logger = logging.getLogger(__name__)
