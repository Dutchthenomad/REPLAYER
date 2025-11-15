"""
RecorderSink - Production-ready recorder for live game ticks
Writes incoming ticks to JSONL files with proper error handling and resource management
"""

import json
import logging
import threading
import atexit
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal
from contextlib import contextmanager

from models import GameTick

logger = logging.getLogger(__name__)


class RecordingError(Exception):
    """Custom exception for recording-related errors"""
    pass


class RecorderSink:
    """
    Production-ready recorder for game ticks with:
    - Robust error handling for disk operations
    - Proper resource cleanup
    - Thread-safe operations
    - Automatic recovery from failures
    """

    # Class-level lock for managing multiple instances
    _instances_lock = threading.Lock()
    _active_instances = []

    def __init__(self, recordings_dir: Path, buffer_size: int = 100):
        """
        Initialize recorder with production safeguards
        
        Args:
            recordings_dir: Directory to save recordings
            buffer_size: Number of ticks to buffer before flush
            
        Raises:
            RecordingError: If directory cannot be created or accessed
        """
        self.recordings_dir = Path(recordings_dir)
        self.buffer_size = max(1, buffer_size)  # Ensure positive buffer size
        
        # Validate and create directory
        try:
            self.recordings_dir.mkdir(parents=True, exist_ok=True)
            # Test write permissions
            test_file = self.recordings_dir / '.write_test'
            test_file.touch()
            test_file.unlink()
        except (OSError, PermissionError) as e:
            raise RecordingError(f"Cannot access recordings directory: {e}")

        # Recording state
        self.current_file: Optional[Path] = None
        self.file_handle = None
        self.buffer = []
        self.tick_count = 0
        self.error_count = 0
        self.max_errors = 5  # Stop recording after this many errors
        
        # Performance metrics
        self.total_bytes_written = 0
        self.last_flush_time = datetime.now()

        # Thread safety
        self._lock = threading.RLock()
        self._closed = False
        
        # Register instance for cleanup
        self._register_instance()
        
        logger.info(f"RecorderSink initialized: {self.recordings_dir} (buffer_size={buffer_size})")

    def _register_instance(self):
        """Register this instance for cleanup on exit"""
        with self._instances_lock:
            self._active_instances.append(self)
            if len(self._active_instances) == 1:
                atexit.register(self._cleanup_all_instances)

    @classmethod
    def _cleanup_all_instances(cls):
        """Clean up all active recorder instances on exit"""
        with cls._instances_lock:
            for instance in cls._active_instances:
                try:
                    instance.close()
                except Exception as e:
                    logger.error(f"Error cleaning up recorder: {e}")
            cls._active_instances.clear()

    @contextmanager
    def _safe_file_operation(self):
        """Context manager for safe file operations with error handling"""
        try:
            yield
        except IOError as e:
            self.error_count += 1
            logger.error(f"IO error during file operation: {e}")
            if self.error_count >= self.max_errors:
                logger.error(f"Max errors ({self.max_errors}) reached, stopping recording")
                self.stop_recording()
                raise RecordingError(f"Recording stopped due to repeated errors: {e}")
        except Exception as e:
            self.error_count += 1
            logger.error(f"Unexpected error during file operation: {e}")
            raise

    def _check_disk_space(self, min_free_mb: int = 100) -> bool:
        """
        Check if sufficient disk space is available
        
        Args:
            min_free_mb: Minimum free space required in MB
            
        Returns:
            True if sufficient space available
        """
        try:
            stat = os.statvfs(self.recordings_dir)
            free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
            if free_mb < min_free_mb:
                logger.warning(f"Low disk space: {free_mb:.1f} MB free")
                return False
            return True
        except (OSError, AttributeError):
            # AttributeError for Windows (statvfs not available)
            # Fallback: try to write a test file
            try:
                test_data = b'x' * (min_free_mb * 1024)  # Test with smaller amount
                test_file = self.recordings_dir / '.space_test'
                test_file.write_bytes(test_data)
                test_file.unlink()
                return True
            except:
                return False

    def start_recording(self, game_id: Optional[str] = None) -> Path:
        """
        Start recording a new game with production safeguards
        
        Args:
            game_id: Optional game identifier
            
        Returns:
            Path to recording file
            
        Raises:
            RecordingError: If recording cannot be started
        """
        with self._lock:
            if self._closed:
                raise RecordingError("RecorderSink is closed")
                
            # Check disk space
            if not self._check_disk_space():
                raise RecordingError("Insufficient disk space")
                
            # Close previous recording if open
            if self.file_handle:
                self.stop_recording()

            # Generate timestamp-based filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Add microseconds if needed to ensure uniqueness
            filename = f"game_{timestamp}.jsonl"
            self.current_file = self.recordings_dir / filename
            
            # Handle potential filename collision
            counter = 0
            while self.current_file.exists() and counter < 100:
                counter += 1
                filename = f"game_{timestamp}_{counter}.jsonl"
                self.current_file = self.recordings_dir / filename
                
            if self.current_file.exists():
                raise RecordingError("Cannot create unique filename")

            # Open file for writing with proper encoding
            try:
                self.file_handle = open(self.current_file, 'w', encoding='utf-8', buffering=8192)
                self.buffer = []
                self.tick_count = 0
                self.error_count = 0
                self.total_bytes_written = 0
                
                # Write metadata header
                metadata = {
                    '_metadata': {
                        'game_id': game_id,
                        'start_time': datetime.now().isoformat(),
                        'version': '1.0'
                    }
                }
                self.file_handle.write(json.dumps(metadata) + '\n')
                self.file_handle.flush()
                
            except Exception as e:
                if self.file_handle:
                    self.file_handle.close()
                    self.file_handle = None
                raise RecordingError(f"Failed to start recording: {e}")

            logger.info(f"Started recording: {filename}")
            return self.current_file

    def record_tick(self, tick: GameTick) -> bool:
        """
        Record a single tick with proper error handling
        
        Args:
            tick: GameTick to record
            
        Returns:
            True if recorded successfully
        """
        with self._lock:
            if self._closed:
                return False
                
            if not self.file_handle:
                logger.warning("No recording in progress, auto-starting")
                try:
                    self.start_recording(getattr(tick, 'game_id', None))
                except RecordingError as e:
                    logger.error(f"Failed to auto-start recording: {e}")
                    return False

            try:
                # Convert tick to JSON with Decimal handling
                tick_dict = self._serialize_tick(tick)
                tick_json = json.dumps(tick_dict)
                
                # Validate JSON is not too large (prevent memory issues)
                if len(tick_json) > 1024 * 1024:  # 1MB per tick limit
                    logger.error(f"Tick JSON too large: {len(tick_json)} bytes")
                    return False
                
                # Add to buffer
                self.buffer.append(tick_json)
                self.tick_count += 1

                # Flush buffer if full or if it's been too long
                if len(self.buffer) >= self.buffer_size or self._should_force_flush():
                    with self._safe_file_operation():
                        self._flush()

                return True
                
            except Exception as e:
                logger.error(f"Failed to record tick: {e}")
                self.error_count += 1
                if self.error_count >= self.max_errors:
                    self.stop_recording()
                return False

    def _serialize_tick(self, tick: GameTick) -> Dict[str, Any]:
        """
        Serialize tick to JSON-compatible dict with Decimal handling
        
        Args:
            tick: GameTick to serialize
            
        Returns:
            JSON-compatible dictionary
        """
        tick_dict = tick.to_dict() if hasattr(tick, 'to_dict') else tick.__dict__.copy()
        
        # Convert Decimal to string for JSON compatibility
        for key, value in tick_dict.items():
            if isinstance(value, Decimal):
                tick_dict[key] = str(value)
        
        return tick_dict

    def _should_force_flush(self) -> bool:
        """Check if buffer should be flushed based on time"""
        # Force flush every 10 seconds to prevent data loss
        return (datetime.now() - self.last_flush_time).total_seconds() > 10

    def _flush(self):
        """
        Flush buffer to disk with error recovery
        Note: Called with lock held
        """
        if not self.buffer or not self.file_handle:
            return

        try:
            # Check disk space before writing
            if not self._check_disk_space(min_free_mb=10):
                raise RecordingError("Insufficient disk space during flush")
            
            # Write all buffered ticks
            for tick_json in self.buffer:
                bytes_written = self.file_handle.write(tick_json + '\n')
                self.total_bytes_written += bytes_written

            self.file_handle.flush()
            os.fsync(self.file_handle.fileno())  # Force OS flush
            
            self.buffer = []
            self.last_flush_time = datetime.now()
            self.error_count = 0  # Reset error count on successful flush
            
        except Exception as e:
            logger.error(f"Flush failed: {e}")
            # Don't clear buffer on error - will retry on next flush
            raise

    def stop_recording(self) -> Optional[dict]:
        """
        Stop recording and close file with proper cleanup
        
        Returns:
            Summary dict with recording statistics
        """
        with self._lock:
            if not self.file_handle:
                return None

            summary = None
            
            try:
                # Flush remaining buffer
                if self.buffer:
                    with self._safe_file_operation():
                        self._flush()
                
                # Write end metadata
                end_metadata = {
                    '_metadata': {
                        'end_time': datetime.now().isoformat(),
                        'tick_count': self.tick_count,
                        'total_bytes': self.total_bytes_written
                    }
                }
                self.file_handle.write(json.dumps(end_metadata) + '\n')
                
                # Get file size before closing
                self.file_handle.flush()
                file_size = self.current_file.stat().st_size if self.current_file.exists() else 0
                
                summary = {
                    'filepath': str(self.current_file),
                    'tick_count': self.tick_count,
                    'file_size': file_size,
                    'total_bytes_written': self.total_bytes_written,
                    'error_count': self.error_count
                }
                
                logger.info(
                    f"Stopped recording: {self.current_file.name} "
                    f"({self.tick_count} ticks, {file_size} bytes)"
                )
                
            except Exception as e:
                logger.error(f"Error stopping recording: {e}")
                
            finally:
                # Always close file handle
                try:
                    if self.file_handle:
                        self.file_handle.close()
                except:
                    pass
                    
                # Reset state
                self.file_handle = None
                self.current_file = None
                self.buffer = []
                self.tick_count = 0
                self.error_count = 0
                self.total_bytes_written = 0

            return summary

    def is_recording(self) -> bool:
        """Check if currently recording"""
        with self._lock:
            return self.file_handle is not None and not self._closed

    def get_current_file(self) -> Optional[Path]:
        """Get path to current recording file"""
        with self._lock:
            return self.current_file

    def get_tick_count(self) -> int:
        """Get number of ticks recorded in current session"""
        with self._lock:
            return self.tick_count

    def get_status(self) -> dict:
        """Get detailed recorder status"""
        with self._lock:
            return {
                'recording': self.is_recording(),
                'current_file': str(self.current_file) if self.current_file else None,
                'tick_count': self.tick_count,
                'buffer_size': len(self.buffer),
                'error_count': self.error_count,
                'total_bytes_written': self.total_bytes_written,
                'closed': self._closed
            }

    def close(self):
        """Close recorder and clean up resources"""
        with self._lock:
            if self._closed:
                return
                
            # Stop any active recording
            if self.file_handle:
                self.stop_recording()
            
            self._closed = True
            
            # Remove from active instances
            with self._instances_lock:
                if self in self._active_instances:
                    self._active_instances.remove(self)
            
            logger.info("RecorderSink closed")

    def __enter__(self):
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.close()

    def __del__(self):
        """Destructor for cleanup (fallback only)"""
        try:
            if not self._closed:
                self.close()
        except:
            pass
