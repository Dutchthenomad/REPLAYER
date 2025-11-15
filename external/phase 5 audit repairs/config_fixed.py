"""
Production-ready configuration module for Rugs Replay Viewer
Centralizes all constants, settings, and configuration with validation
"""

import os
import json
import logging
from pathlib import Path
from decimal import Decimal
from typing import Dict, Any, Optional, Union


class ConfigError(Exception):
    """Configuration validation error"""
    pass


class Config:
    """
    Production-ready configuration management with:
    - Input validation
    - Environment variable support
    - Safe defaults
    - Type checking
    """
    
    # ========== Financial Settings ==========
    FINANCIAL = {
        'initial_balance': Decimal('0.100'),
        'default_bet': Decimal('0.001'),
        'min_bet': Decimal('0.001'),
        'max_bet': Decimal('1.0'),
        'decimal_precision': 10,
        'commission_rate': Decimal('0.0025'),
    }
    
    # ========== Game Rules ==========
    GAME_RULES = {
        'sidebet_multiplier': Decimal('5.0'),
        'sidebet_window_ticks': 40,
        'sidebet_cooldown_ticks': 5,
        'rug_liquidation_price': Decimal('0.02'),
        'max_position_size': Decimal('10.0'),
        'stop_loss_threshold': Decimal('0.5'),
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
        'cleanup_interval': 60,
    }
    
    # ========== File Settings ==========
    @classmethod
    def get_files_config(cls) -> dict:
        """Get file configuration with lazy initialization to avoid import issues"""
        base_dir = Path(__file__).parent
        return {
            'recordings_dir': Path(os.getenv(
                'RUGS_RECORDINGS_DIR',
                str(base_dir / 'rugs_recordings')
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
    
    FILES = property(lambda self: self.get_files_config())

    # ========== Live Feed Settings (With Validation) ==========
    @classmethod
    def get_live_feed_config(cls) -> dict:
        """Get live feed configuration with validation"""
        ring_buffer_size = int(os.getenv('RUGS_RING_BUFFER_SIZE', '5000'))
        recording_buffer_size = int(os.getenv('RUGS_RECORDING_BUFFER_SIZE', '100'))
        auto_recording = os.getenv('RUGS_AUTO_RECORDING', 'true').lower() == 'true'
        
        # Validate and enforce minimum values
        ring_buffer_size = max(100, min(100000, ring_buffer_size))  # 100-100k range
        recording_buffer_size = max(10, min(1000, recording_buffer_size))  # 10-1k range
        
        return {
            'ring_buffer_size': ring_buffer_size,
            'auto_recording': auto_recording,
            'recording_buffer_size': recording_buffer_size,
        }
    
    LIVE_FEED = property(lambda self: self.get_live_feed_config())
    
    # ========== Logging Settings ==========
    LOGGING = {
        'level': os.getenv('LOG_LEVEL', 'INFO'),
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'date_format': '%Y-%m-%d %H:%M:%S',
        'max_bytes': 5 * 1024 * 1024,
        'backup_count': 3,
        'console_output': True,
    }
    
    # ========== Flat Config Attributes (for bot compatibility) ==========
    MIN_BET_SOL = Decimal('0.001')
    MAX_BET_SOL = Decimal('1.0')
    DEFAULT_BET_SOL = Decimal('0.001')
    SIDEBET_MULTIPLIER = Decimal('5.0')
    SIDEBET_WINDOW_TICKS = 40
    SIDEBET_COOLDOWN_TICKS = 5
    BLOCKED_PHASES_FOR_TRADING = ["COOLDOWN", "RUG_EVENT", "RUG_EVENT_1", "UNKNOWN"]
    INITIAL_BALANCE_SOL = Decimal('0.100')
    MAX_POSITION_HISTORY = 1000

    # ========== Bot Settings ==========
    BOT = {
        'decision_delay': 0.5,
        'max_consecutive_losses': 5,
        'risk_per_trade': Decimal('0.02'),
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
    
    def __init__(self, config_file: Optional[str] = None, validate: bool = True):
        """
        Initialize configuration with optional validation
        
        Args:
            config_file: Optional path to JSON config file
            validate: Whether to validate configuration on init
        """
        self.config_file = config_file
        self._custom_settings = {}
        self._logger = None  # Will be set after logger initialization
        
        # Create directories if they don't exist
        self._ensure_directories()
        
        # Load custom configuration if provided
        if config_file:
            self.load_from_file(config_file)
        
        # Validate configuration
        if validate:
            self.validate()
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        try:
            files_config = self.get_files_config()
            for key in ['recordings_dir', 'config_dir', 'log_dir']:
                path = files_config[key]
                path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            # Can't use logger yet, use print for bootstrap errors
            print(f"Warning: Could not create directories: {e}")
    
    def validate(self):
        """
        Validate all configuration values
        
        Raises:
            ConfigError: If configuration is invalid
        """
        errors = []
        
        # Validate financial settings
        if self.FINANCIAL['min_bet'] <= 0:
            errors.append("min_bet must be positive")
        if self.FINANCIAL['max_bet'] <= self.FINANCIAL['min_bet']:
            errors.append("max_bet must be greater than min_bet")
        if self.FINANCIAL['decimal_precision'] < 1 or self.FINANCIAL['decimal_precision'] > 20:
            errors.append("decimal_precision must be between 1 and 20")
        
        # Validate game rules
        if self.GAME_RULES['sidebet_window_ticks'] < 1:
            errors.append("sidebet_window_ticks must be positive")
        if self.GAME_RULES['sidebet_cooldown_ticks'] < 0:
            errors.append("sidebet_cooldown_ticks cannot be negative")
        
        # Validate playback settings
        if self.PLAYBACK['min_speed'] <= 0:
            errors.append("min_speed must be positive")
        if self.PLAYBACK['max_speed'] <= self.PLAYBACK['min_speed']:
            errors.append("max_speed must be greater than min_speed")
        
        # Validate UI settings
        if self.UI['window_width'] < 100 or self.UI['window_height'] < 100:
            errors.append("Window dimensions must be at least 100x100")
        
        # Validate memory settings
        if self.MEMORY['max_position_history'] < 10:
            errors.append("max_position_history must be at least 10")
        if self.MEMORY['max_chart_points'] < 10:
            errors.append("max_chart_points must be at least 10")
        
        # Validate live feed settings
        live_feed = self.get_live_feed_config()
        if live_feed['ring_buffer_size'] < 100:
            errors.append("ring_buffer_size must be at least 100")
        if live_feed['recording_buffer_size'] < 10:
            errors.append("recording_buffer_size must be at least 10")
        
        if errors:
            raise ConfigError("Configuration validation failed:\n" + "\n".join(errors))
    
    def load_from_file(self, filepath: Union[str, Path]):
        """
        Load configuration from JSON file with validation
        
        Args:
            filepath: Path to JSON configuration file
        """
        filepath = Path(filepath)
        
        try:
            if not filepath.exists():
                if self._logger:
                    self._logger.warning(f"Config file not found: {filepath}")
                return
            
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            # Convert string Decimals back to Decimal objects
            for section in ['financial', 'game_rules', 'bot']:
                if section in data:
                    for key, value in data[section].items():
                        if isinstance(value, str) and '.' in value:
                            try:
                                data[section][key] = Decimal(value)
                            except:
                                pass
            
            self._custom_settings = data
            
            if self._logger:
                self._logger.info(f"Loaded configuration from {filepath}")
                
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in config file: {e}"
            if self._logger:
                self._logger.error(error_msg)
            raise ConfigError(error_msg)
        except Exception as e:
            error_msg = f"Error loading config file: {e}"
            if self._logger:
                self._logger.error(error_msg)
            raise ConfigError(error_msg)
    
    def save_to_file(self, filepath: Union[str, Path]):
        """
        Save current configuration to JSON file
        
        Args:
            filepath: Path where to save the configuration
        """
        filepath = Path(filepath)
        
        # Build configuration dictionary
        config_dict = {
            'financial': self._serialize_dict(self.FINANCIAL),
            'game_rules': self._serialize_dict(self.GAME_RULES),
            'playback': self.PLAYBACK,
            'ui': self.UI,
            'memory': self.MEMORY,
            'bot': self._serialize_dict(self.BOT),
            'network': self.NETWORK,
            'logging': self.LOGGING,
            'live_feed': self.get_live_feed_config(),
        }
        
        # Merge with custom settings
        for section, values in self._custom_settings.items():
            if section in config_dict:
                config_dict[section].update(values)
            else:
                config_dict[section] = values
        
        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2, default=str)
            
        if self._logger:
            self._logger.info(f"Saved configuration to {filepath}")
    
    def _serialize_dict(self, d: dict) -> dict:
        """Convert Decimal values to strings for JSON serialization"""
        result = {}
        for key, value in d.items():
            if isinstance(value, Decimal):
                result[key] = str(value)
            else:
                result[key] = value
        return result
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get configuration value with support for custom settings
        
        Args:
            section: Configuration section name
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        # Check custom settings first
        section_lower = section.lower()
        if section_lower in self._custom_settings:
            if key in self._custom_settings[section_lower]:
                return self._custom_settings[section_lower][key]
        
        # Fall back to default settings
        section_attr = section.upper()
        if hasattr(self, section_attr):
            section_dict = getattr(self, section_attr)
            if callable(section_dict):
                section_dict = section_dict()
            if isinstance(section_dict, dict):
                return section_dict.get(key, default)
        
        return default
    
    def set(self, section: str, key: str, value: Any):
        """
        Set a configuration value
        
        Args:
            section: Configuration section name
            key: Configuration key
            value: Value to set
        """
        section_lower = section.lower()
        if section_lower not in self._custom_settings:
            self._custom_settings[section_lower] = {}
        self._custom_settings[section_lower][key] = value
    
    def set_logger(self, logger):
        """Set logger instance after logger initialization"""
        self._logger = logger
    
    @property
    def current_theme(self) -> Dict[str, str]:
        """Get current color theme"""
        theme_name = self.get('ui', 'theme', 'dark')
        return self.THEMES.get(theme_name, self.THEMES['dark'])
    
    def to_dict(self) -> dict:
        """Export entire configuration as dictionary"""
        return {
            'financial': self._serialize_dict(self.FINANCIAL),
            'game_rules': self._serialize_dict(self.GAME_RULES),
            'playback': self.PLAYBACK,
            'ui': self.UI,
            'memory': self.MEMORY,
            'files': {k: str(v) if isinstance(v, Path) else v 
                     for k, v in self.get_files_config().items()},
            'live_feed': self.get_live_feed_config(),
            'logging': self.LOGGING,
            'bot': self._serialize_dict(self.BOT),
            'network': self.NETWORK,
            'themes': self.THEMES,
            'custom': self._custom_settings,
        }


# Create global configuration instance
config = Config(validate=False)  # Skip validation on initial import

# Set up logging after config is created
logging.basicConfig(
    level=getattr(logging, config.LOGGING['level']),
    format=config.LOGGING['format'],
    datefmt=config.LOGGING['date_format']
)

# Now set the logger
logger = logging.getLogger(__name__)
config.set_logger(logger)

# Validate configuration after logger is set
try:
    config.validate()
except ConfigError as e:
    logger.error(f"Configuration validation failed: {e}")
    # Continue with defaults, but log the error
