"""
Logger Service Module
Centralized logging configuration with rotation, formatting, and multiple handlers
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
from typing import Optional, Dict, Any
import json
import os

# Try to import colorlog for colored console output (optional)
try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False


class LoggerService:
    """
    Centralized logging service with support for:
    - Multiple log levels
    - File rotation
    - Colored console output
    - JSON structured logging
    - Performance logging
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.loggers = {}
        self.handlers = {}
        
        # Create log directory
        self.log_dir = Path(self.config.get("log_dir", "./logs"))
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            if not os.access(self.log_dir, os.W_OK):
                raise PermissionError(f"Log directory not writable: {self.log_dir}")
        except Exception:
            # Fall back to a local writable directory to avoid crashing tests/app
            self.log_dir = Path("./logs")
            self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup root logger
        self._setup_root_logger()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default logging configuration"""
        return {
            'log_dir': './logs',
            'log_level': 'INFO',
            'console_level': 'INFO',
            'file_level': 'DEBUG',
            'max_bytes': 5 * 1024 * 1024,  # 5MB
            'backup_count': 3,
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'date_format': '%Y-%m-%d %H:%M:%S',
            'colored_output': True,
            'json_logs': False,
            'performance_logs': True
        }
    
    def _setup_root_logger(self):
        """Configure the root logger"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # Capture all, filter at handler level
        
        # Remove existing handlers
        root_logger.handlers = []
        
        # Add console handler
        console_handler = self._create_console_handler()
        root_logger.addHandler(console_handler)
        
        # Add file handlers
        file_handler = self._create_file_handler('app.log')
        root_logger.addHandler(file_handler)
        
        # Add error file handler
        error_handler = self._create_file_handler('errors.log', level=logging.ERROR)
        root_logger.addHandler(error_handler)
        
        # Add performance log handler if enabled
        if self.config.get('performance_logs'):
            perf_handler = self._create_performance_handler()
            root_logger.addHandler(perf_handler)
    
    def _create_console_handler(self) -> logging.Handler:
        """Create console handler with optional colored output"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(
            getattr(logging, self.config.get('console_level', 'INFO'))
        )
        
        if COLORLOG_AVAILABLE and self.config.get('colored_output'):
            formatter = colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt=self.config.get('date_format'),
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        else:
            formatter = logging.Formatter(
                self.config.get('format'),
                datefmt=self.config.get('date_format')
            )
        
        console_handler.setFormatter(formatter)
        return console_handler
    
    def _create_file_handler(self, filename: str, 
                            level: Optional[int] = None) -> logging.Handler:
        """Create rotating file handler"""
        file_path = self.log_dir / filename

        try:
            handler: logging.Handler = RotatingFileHandler(
                file_path,
                maxBytes=self.config.get("max_bytes"),
                backupCount=self.config.get("backup_count"),
            )
        except OSError:
            # Don't fail hard if filesystem isn't writable (common in CI/sandboxes).
            handler = logging.StreamHandler(sys.stderr)
        
        handler.setLevel(
            level or getattr(logging, self.config.get('file_level', 'DEBUG'))
        )
        
        if self.config.get('json_logs'):
            handler.setFormatter(JsonFormatter())
        else:
            formatter = logging.Formatter(
                self.config.get('format'),
                datefmt=self.config.get('date_format')
            )
            handler.setFormatter(formatter)
        
        return handler
    
    def _create_performance_handler(self) -> logging.Handler:
        """Create handler for performance metrics"""
        perf_path = self.log_dir / 'performance.log'

        try:
            handler: logging.Handler = TimedRotatingFileHandler(
                perf_path,
                when="midnight",
                interval=1,
                backupCount=7,
            )
        except OSError:
            handler = logging.StreamHandler(sys.stderr)
        
        handler.setLevel(logging.INFO)
        handler.setFormatter(JsonFormatter())
        
        return handler
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a named logger"""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
        
        return self.loggers[name]
    
    def log_performance(self, operation: str, duration: float, 
                       metadata: Optional[Dict] = None):
        """Log performance metrics"""
        perf_logger = self.get_logger('performance')
        
        perf_data = {
            'operation': operation,
            'duration_ms': duration * 1000,
            'timestamp': datetime.now().isoformat(),
        }
        
        if metadata:
            perf_data.update(metadata)
        
        perf_logger.info(json.dumps(perf_data))
    
    def set_level(self, level: str, logger_name: Optional[str] = None):
        """Set logging level for a specific logger or all loggers"""
        level_value = getattr(logging, level.upper())
        
        if logger_name:
            logger = logging.getLogger(logger_name)
            logger.setLevel(level_value)
        else:
            logging.getLogger().setLevel(level_value)
    
    def add_file_handler(self, logger_name: str, filename: str):
        """Add a file handler to a specific logger"""
        logger = self.get_logger(logger_name)
        handler = self._create_file_handler(filename)
        logger.addHandler(handler)
        
        # Track handler for cleanup
        if logger_name not in self.handlers:
            self.handlers[logger_name] = []
        self.handlers[logger_name].append(handler)
    
    def cleanup(self):
        """Clean up handlers and close files"""
        # Close all handlers
        for logger_handlers in self.handlers.values():
            for handler in logger_handlers:
                handler.close()
        
        # Clear handler references
        self.handlers.clear()
        
        # Reset loggers
        for logger in self.loggers.values():
            logger.handlers = []
        
        self.loggers.clear()


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 
                          'funcName', 'levelname', 'levelno', 'lineno', 
                          'module', 'msecs', 'message', 'pathname', 'process',
                          'processName', 'relativeCreated', 'thread', 
                          'threadName', 'exc_info', 'exc_text', 'stack_info']:
                log_data[key] = value
        
        return json.dumps(log_data)


class PerformanceLogger:
    """Context manager for performance logging"""
    
    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        """Start timing"""
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log performance"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type:
            self.logger.error(
                f"Operation '{self.operation}' failed after {duration:.3f}s: {exc_val}"
            )
        else:
            self.logger.info(
                f"Operation '{self.operation}' completed in {duration:.3f}s"
            )


# Global logger service instance
_logger_service = None
_logging_configured = False


def setup_logging(config: Optional[Dict] = None) -> logging.Logger:
    """
    Setup logging configuration and return root logger
    
    Args:
        config: Optional configuration dictionary
    
    Returns:
        Configured root logger
    """
    global _logger_service, _logging_configured

    if _logging_configured and _logger_service is not None:
        return logging.getLogger()
    
    if _logger_service is None:
        # Import config if available
        try:
            from config import config as app_config
            log_config = {
                'log_dir': str(app_config.FILES.get('log_dir', './logs')),
                'log_level': app_config.LOGGING.get('level', 'INFO'),
                'max_bytes': app_config.LOGGING.get('max_bytes', 5*1024*1024),
                'backup_count': app_config.LOGGING.get('backup_count', 3),
                'format': app_config.LOGGING.get('format'),
                'date_format': app_config.LOGGING.get('date_format'),
            }
            if config:
                log_config.update(config)
        except ImportError:
            log_config = config or {}
        
        _logger_service = LoggerService(log_config)
        _logging_configured = True
    
    return logging.getLogger()


def get_logger(name: str) -> logging.Logger:
    """Get a named logger"""
    if _logger_service is None:
        setup_logging()
    
    return _logger_service.get_logger(name)


def log_performance(operation: str, duration: float, metadata: Optional[Dict] = None):
    """Log performance metrics"""
    if _logger_service:
        _logger_service.log_performance(operation, duration, metadata)


def cleanup_logging():
    """Clean up logging resources"""
    global _logger_service, _logging_configured
    
    if _logger_service:
        _logger_service.cleanup()
        _logger_service = None
        _logging_configured = False


# Convenience function for module-level logger
def get_module_logger() -> logging.Logger:
    """Get logger for the calling module"""
    import inspect
    
    frame = inspect.currentframe()
    if frame and frame.f_back:
        module_name = frame.f_back.f_globals.get('__name__', 'unknown')
        return get_logger(module_name)
    
    return get_logger('unknown')
