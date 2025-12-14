"""
RecorderSink - Production-ready recorder for live game ticks

PRODUCTION FIX (2025-11-30):
- Proper buffer management to prevent memory leaks
- Emergency buffer trimming on persistent flush failures
- Configurable backpressure with graceful degradation
- Async-safe flush operations
- Comprehensive metrics for monitoring

Writes incoming ticks to JSONL files with proper error handling and resource management.
"""

import json
import logging
import threading
import atexit
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal
from contextlib import contextmanager
from collections import deque
from dataclasses import dataclass, field

from models import GameTick

logger = logging.getLogger(__name__)


class RecordingError(Exception):
    """Custom exception for recording-related errors"""
    pass


@dataclass
class RecordingMetrics:
    """Metrics for monitoring recording health"""
    ticks_recorded: int = 0
    ticks_dropped: int = 0
    bytes_written: int = 0
    flush_count: int = 0
    flush_errors: int = 0
    emergency_trims: int = 0
    last_flush_time: Optional[datetime] = None
    last_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'ticks_recorded': self.ticks_recorded,
            'ticks_dropped': self.ticks_dropped,
            'bytes_written': self.bytes_written,
            'flush_count': self.flush_count,
            'flush_errors': self.flush_errors,
            'emergency_trims': self.emergency_trims,
            'drop_rate': self.ticks_dropped / max(1, self.ticks_recorded + self.ticks_dropped),
            'last_flush_time': self.last_flush_time.isoformat() if self.last_flush_time else None,
            'last_error': self.last_error,
        }


class RecorderSink:
    """
    Production-ready recorder for game ticks with:
    - Robust error handling for disk operations
    - Memory-bounded buffer with emergency trimming
    - Proper resource cleanup
    - Thread-safe operations
    - Automatic recovery from failures
    - Comprehensive metrics
    """

    # Class-level lock for managing multiple instances
    _instances_lock = threading.Lock()
    _active_instances: List['RecorderSink'] = []

    # Default configuration
    DEFAULT_BUFFER_SIZE = 100
    DEFAULT_MAX_BUFFER_SIZE = 1000
    DEFAULT_MIN_DISK_SPACE_MB = 100
    DEFAULT_MAX_ERRORS = 5
    DEFAULT_EMERGENCY_TRIM_RATIO = 0.5  # Trim 50% of buffer on emergency

    def __init__(
        self,
        recordings_dir: Path,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
        max_buffer_size: int = DEFAULT_MAX_BUFFER_SIZE,
        min_disk_space_mb: int = DEFAULT_MIN_DISK_SPACE_MB,
        max_errors: int = DEFAULT_MAX_ERRORS
    ):
        """
        Initialize recorder with production safeguards.

        Args:
            recordings_dir: Directory to save recordings
            buffer_size: Number of ticks to buffer before flush (normal operation)
            max_buffer_size: Maximum buffer size before forcing emergency action
            min_disk_space_mb: Minimum free disk space required (MB)
            max_errors: Stop recording after this many consecutive errors

        Raises:
            RecordingError: If directory cannot be created or accessed
        """
        self.recordings_dir = Path(recordings_dir)
        self.buffer_size = max(1, buffer_size)
        self.max_buffer_size = max(buffer_size * 2, max_buffer_size)
        self.min_disk_space_mb = min_disk_space_mb
        self.max_errors = max_errors
        
        # Validate and create directory
        self._ensure_directory_accessible()

        # Recording state
        self.current_file: Optional[Path] = None
        self.file_handle = None
        
        # PRODUCTION FIX: Use deque for efficient trimming
        self._buffer: deque = deque(maxlen=self.max_buffer_size * 2)  # Allow overflow detection
        self._consecutive_errors = 0
        
        # Metrics
        self.metrics = RecordingMetrics()

        # Thread safety
        self._lock = threading.RLock()
        self._closed = False
        
        # Register instance for cleanup
        self._register_instance()
        
        logger.info(
            f"RecorderSink initialized: {self.recordings_dir} "
            f"(buffer={buffer_size}, max={max_buffer_size})"
        )

    def _ensure_directory_accessible(self):
        """Validate directory is accessible and writable"""
        try:
            self.recordings_dir.mkdir(parents=True, exist_ok=True)
            # Test write permissions
            test_file = self.recordings_dir / '.write_test'
            test_file.touch()
            test_file.unlink()
        except (OSError, PermissionError) as e:
            raise RecordingError(f"Cannot access recordings directory: {e}")

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
                    # Can't use logger during atexit
                    pass
            cls._active_instances.clear()

    @contextmanager
    def _safe_file_operation(self):
        """Context manager for safe file operations with error handling"""
        try:
            yield
            self._consecutive_errors = 0  # Reset on success
        except IOError as e:
            self._consecutive_errors += 1
            self.metrics.flush_errors += 1
            self.metrics.last_error = str(e)
            logger.error(f"IO error during file operation: {e}")
            
            if self._consecutive_errors >= self.max_errors:
                logger.error(f"Max consecutive errors ({self.max_errors}) reached, stopping recording")
                self.stop_recording()
                raise RecordingError(f"Recording stopped due to repeated errors: {e}")
            raise
        except Exception as e:
            self._consecutive_errors += 1
            self.metrics.flush_errors += 1
            self.metrics.last_error = str(e)
            logger.error(f"Unexpected error during file operation: {e}")
            raise

    def _check_disk_space(self) -> bool:
        """
        Check if sufficient disk space is available.
        
        Returns:
            True if sufficient space available
        """
        try:
            if os.name == 'nt':
                # Windows
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(str(self.recordings_dir)),
                    None, None, ctypes.pointer(free_bytes)
                )
                free_mb = free_bytes.value / (1024 * 1024)
            else:
                # Unix/Linux
                stat = os.statvfs(self.recordings_dir)
                free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
            
            if free_mb < self.min_disk_space_mb:
                logger.warning(f"Low disk space: {free_mb:.1f} MB free (min: {self.min_disk_space_mb})")
                return False
            return True
            
        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")
            return True  # Assume OK if check fails

    def _emergency_trim_buffer(self) -> int:
        """
        PRODUCTION FIX: Emergency buffer trimming when normal flush fails.
        
        Removes oldest entries to prevent unbounded memory growth.
        
        Returns:
            Number of ticks dropped
        """
        trim_count = int(len(self._buffer) * self.DEFAULT_EMERGENCY_TRIM_RATIO)
        
        if trim_count <= 0:
            return 0
        
        # Remove oldest entries
        for _ in range(trim_count):
            if self._buffer:
                self._buffer.popleft()
        
        self.metrics.ticks_dropped += trim_count
        self.metrics.emergency_trims += 1
        
        logger.warning(
            f"Emergency buffer trim: dropped {trim_count} oldest ticks "
            f"(total dropped: {self.metrics.ticks_dropped})"
        )
        
        return trim_count

    @property
    def tick_count(self) -> int:
        """Get number of ticks recorded in current session"""
        return self.metrics.ticks_recorded

    def get_tick_count(self) -> int:
        """Get number of ticks recorded (for compatibility)"""
        return self.tick_count

    def get_current_file(self) -> Optional[Path]:
        """Get current recording file path"""
        with self._lock:
            return self.current_file

    def is_recording(self) -> bool:
        """Check if currently recording"""
        with self._lock:
            return self.file_handle is not None and not self._closed

    def start_recording(self, game_id: Optional[str] = None) -> Path:
        """
        Start recording to a new file.
        
        Args:
            game_id: Optional game identifier for filename
            
        Returns:
            Path to the new recording file
            
        Raises:
            RecordingError: If recording cannot be started
        """
        with self._lock:
            if self._closed:
                raise RecordingError("Recorder has been closed")
            
            # Stop any existing recording
            if self.file_handle:
                self.stop_recording()
            
            # Check disk space
            if not self._check_disk_space():
                raise RecordingError(f"Insufficient disk space (need {self.min_disk_space_mb}MB)")
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            game_suffix = f"_{game_id}" if game_id else ""
            filename = f"game_{timestamp}{game_suffix}.jsonl"
            self.current_file = self.recordings_dir / filename
            
            temp_handle = None
            try:
                # Open file for writing
                temp_handle = open(self.current_file, 'w', encoding='utf-8', buffering=1)
                
                # Write start metadata
                metadata = {
                    '_metadata': {
                        'start_time': datetime.now().isoformat(),
                        'game_id': game_id,
                        'version': '2.0'  # PRODUCTION version
                    }
                }
                temp_handle.write(json.dumps(metadata) + '\n')
                temp_handle.flush()
                
                # PRODUCTION FIX: Only assign after success
                self.file_handle = temp_handle
                temp_handle = None
                
                # Reset state
                self._buffer.clear()
                self._consecutive_errors = 0
                self.metrics = RecordingMetrics()  # Fresh metrics
                
            except Exception as e:
                if temp_handle:
                    try:
                        temp_handle.close()
                    except:
                        pass
                raise RecordingError(f"Failed to start recording: {e}")
            
            logger.info(f"Started recording: {filename}")
            return self.current_file

    def record_tick(self, tick: GameTick) -> bool:
        """
        Record a single tick with proper error handling and backpressure.
        
        PRODUCTION FIX: Implements emergency buffer trimming to prevent
        memory exhaustion when flush operations fail.

        Args:
            tick: GameTick to record

        Returns:
            True if recorded successfully (or dropped gracefully)
        """
        with self._lock:
            if self._closed:
                return False

            # Auto-start recording if needed
            if not self.file_handle:
                logger.warning("No recording in progress, auto-starting")
                try:
                    self.start_recording(getattr(tick, 'game_id', None))
                except RecordingError as e:
                    logger.error(f"Failed to auto-start recording: {e}")
                    return False

            # PRODUCTION FIX: Check buffer overflow BEFORE adding
            buffer_len = len(self._buffer)
            
            if buffer_len >= self.max_buffer_size:
                logger.warning(
                    f"Buffer at max capacity ({buffer_len}/{self.max_buffer_size}), "
                    "attempting emergency flush"
                )
                
                # Try emergency flush
                try:
                    with self._safe_file_operation():
                        self._flush()
                except Exception as e:
                    logger.error(f"Emergency flush failed: {e}")
                    # PRODUCTION FIX: Trim buffer instead of stopping
                    # This prevents memory exhaustion while losing some data
                    self._emergency_trim_buffer()
            
            # Convert tick to JSON
            try:
                tick_dict = self._serialize_tick(tick)
                
                # Add to buffer
                self._buffer.append(tick_dict)
                self.metrics.ticks_recorded += 1
                
                # Normal flush when buffer is full
                if len(self._buffer) >= self.buffer_size:
                    try:
                        with self._safe_file_operation():
                            self._flush()
                    except Exception as e:
                        # Non-fatal - data is buffered, will retry
                        logger.warning(f"Flush failed, data buffered: {e}")
                
                return True
                
            except Exception as e:
                logger.error(f"Error recording tick: {e}")
                self.metrics.last_error = str(e)
                return False

    def _serialize_tick(self, tick: GameTick) -> dict:
        """
        Serialize tick to JSON-compatible dict.
        
        Handles Decimal conversion for JSON serialization.
        """
        tick_dict = {}
        
        for key, value in vars(tick).items():
            if key.startswith('_'):
                continue
            if isinstance(value, Decimal):
                tick_dict[key] = str(value)  # Preserve precision
            elif isinstance(value, datetime):
                tick_dict[key] = value.isoformat()
            else:
                tick_dict[key] = value
        
        # Add recording timestamp
        tick_dict['_recorded_at'] = datetime.now().isoformat()
        
        return tick_dict

    def _flush(self) -> int:
        """
        Write buffered ticks to file.
        
        Returns:
            Number of bytes written
        """
        if not self._buffer or not self.file_handle:
            return 0
        
        bytes_written = 0
        
        try:
            # Write all buffered ticks
            for tick_dict in self._buffer:
                line = json.dumps(tick_dict, default=str) + '\n'
                self.file_handle.write(line)
                bytes_written += len(line.encode('utf-8'))
            
            # Force OS flush
            self.file_handle.flush()
            os.fsync(self.file_handle.fileno())
            
            self.metrics.bytes_written += bytes_written
            self.metrics.flush_count += 1
            self.metrics.last_flush_time = datetime.now()
            
            # Clear buffer after successful write
            self._buffer.clear()
            
        except Exception as e:
            logger.error(f"Flush failed: {e}")
            raise
        
        return bytes_written

    def stop_recording(self) -> Optional[dict]:
        """
        Stop recording and close file with proper cleanup.
        
        Returns:
            Summary dict with recording statistics
        """
        with self._lock:
            if not self.file_handle:
                return None

            summary = None
            filepath = self.current_file  # Save before cleanup
            
            try:
                # Flush remaining buffer
                if self._buffer:
                    try:
                        with self._safe_file_operation():
                            self._flush()
                    except Exception as e:
                        logger.warning(f"Final flush failed, {len(self._buffer)} ticks lost: {e}")
                        self.metrics.ticks_dropped += len(self._buffer)
                
                # Write end metadata
                end_metadata = {
                    '_metadata': {
                        'end_time': datetime.now().isoformat(),
                        'tick_count': self.metrics.ticks_recorded,
                        'ticks_dropped': self.metrics.ticks_dropped,
                        'total_bytes': self.metrics.bytes_written,
                        'flush_errors': self.metrics.flush_errors
                    }
                }
                self.file_handle.write(json.dumps(end_metadata) + '\n')
                self.file_handle.flush()
                
                # Get file size before closing
                file_size = filepath.stat().st_size if filepath and filepath.exists() else 0
                
                summary = {
                    'filepath': str(filepath),
                    'tick_count': self.metrics.ticks_recorded,
                    'ticks_dropped': self.metrics.ticks_dropped,
                    'file_size': file_size,
                    'total_bytes_written': self.metrics.bytes_written,
                    'flush_errors': self.metrics.flush_errors,
                    'emergency_trims': self.metrics.emergency_trims
                }
                
                logger.info(
                    f"Stopped recording: {filepath.name if filepath else 'unknown'} "
                    f"({self.metrics.ticks_recorded} ticks, {self.metrics.ticks_dropped} dropped, "
                    f"{file_size} bytes)"
                )
                
            except Exception as e:
                logger.error(f"Error stopping recording: {e}")
                
            finally:
                # Always close file handle
                try:
                    if self.file_handle:
                        self.file_handle.close()
                except Exception as e:
                    logger.error(f"Error closing file: {e}")
                
                self.file_handle = None
                self.current_file = None
                self._buffer.clear()
            
            return summary

    def close(self):
        """Close recorder and release all resources"""
        with self._lock:
            if self._closed:
                return
            
            self._closed = True
            self.stop_recording()
            
            # Unregister from cleanup list
            with self._instances_lock:
                if self in self._active_instances:
                    self._active_instances.remove(self)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current recording metrics"""
        with self._lock:
            metrics = self.metrics.to_dict()
            metrics['buffer_size'] = len(self._buffer)
            metrics['max_buffer_size'] = self.max_buffer_size
            metrics['is_recording'] = self.is_recording()
            return metrics

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.close()
        return False

    def __repr__(self):
        return (
            f"RecorderSink(dir={self.recordings_dir}, "
            f"recording={self.is_recording()}, "
            f"ticks={self.metrics.ticks_recorded}, "
            f"buffer={len(self._buffer)}/{self.max_buffer_size})"
        )
