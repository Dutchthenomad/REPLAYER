"""
Raw WebSocket Capture Recorder

Captures ALL raw Socket.IO events for protocol discovery and debugging.
Creates its own independent Socket.IO connection to avoid interfering with
the main WebSocketFeed.

Usage:
    recorder = RawCaptureRecorder()
    recorder.start_capture()
    # ... interact with rugs.fun ...
    recorder.stop_capture()
    # -> Creates JSONL file in raw_captures/
"""

import socketio
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger(__name__)


class RawCaptureRecorder:
    """
    Records ALL raw Socket.IO events without filtering.

    Creates a separate Socket.IO connection to capture the complete
    protocol exchange for documentation and debugging.
    """

    DEFAULT_CAPTURE_DIR = Path('/home/nomad/rugs_recordings/raw_captures')
    SERVER_URL = 'https://backend.rugs.fun?frontend-version=1.0'

    def __init__(self, capture_dir: Optional[Path] = None):
        """
        Initialize raw capture recorder.

        Args:
            capture_dir: Directory for capture files (default: raw_captures/)
        """
        self.capture_dir = capture_dir or self.DEFAULT_CAPTURE_DIR
        self.capture_dir.mkdir(parents=True, exist_ok=True)

        # Socket.IO client (created fresh for each capture)
        self.sio: Optional[socketio.Client] = None

        # Capture state
        self.is_capturing = False
        self.capture_file: Optional[Path] = None
        self.file_handle = None
        self.sequence_number = 0
        self.event_counts: Dict[str, int] = {}
        self.start_time: Optional[datetime] = None

        # Thread safety
        self._lock = threading.Lock()

        # Callbacks for UI updates
        self.on_event_captured: Optional[Callable[[str, int], None]] = None
        self.on_capture_started: Optional[Callable[[Path], None]] = None
        self.on_capture_stopped: Optional[Callable[[Path, Dict[str, int]], None]] = None
        self.on_connection_status: Optional[Callable[[bool, str], None]] = None

        logger.info(f"RawCaptureRecorder initialized: {self.capture_dir}")

    def start_capture(self) -> Optional[Path]:
        """
        Start capturing raw WebSocket events.

        Creates a new Socket.IO connection and captures ALL events.

        Returns:
            Path to capture file, or None if failed
        """
        with self._lock:
            if self.is_capturing:
                logger.warning("Capture already in progress")
                return self.capture_file

            # Generate capture filename
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            self.capture_file = self.capture_dir / f'{timestamp}_raw.jsonl'

            # Reset state
            self.sequence_number = 0
            self.event_counts = {}
            self.start_time = datetime.now()

            try:
                # Open file for writing
                self.file_handle = open(self.capture_file, 'w', encoding='utf-8')

                # Create fresh Socket.IO client
                self.sio = socketio.Client(
                    logger=False,
                    engineio_logger=False,
                    reconnection=False,  # Don't auto-reconnect for raw capture
                )

                # Setup catch-all handler BEFORE connecting
                self._setup_handlers()

                # Connect
                logger.info(f"Starting raw capture to: {self.capture_file}")
                self.is_capturing = True

                # Notify UI
                if self.on_capture_started:
                    self.on_capture_started(self.capture_file)

                # Connect in background thread to not block UI
                connect_thread = threading.Thread(
                    target=self._connect_async,
                    daemon=True
                )
                connect_thread.start()

                return self.capture_file

            except Exception as e:
                logger.error(f"Failed to start capture: {e}")
                self._cleanup()
                return None

    def _connect_async(self):
        """Connect to server (runs in background thread)"""
        try:
            if self.on_connection_status:
                self.on_connection_status(False, "Connecting...")

            self.sio.connect(
                self.SERVER_URL,
                transports=['websocket', 'polling'],
                wait_timeout=20
            )

            if self.on_connection_status:
                self.on_connection_status(True, "Connected")

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            if self.on_connection_status:
                self.on_connection_status(False, f"Failed: {e}")
            self.stop_capture()

    def _setup_handlers(self):
        """Setup Socket.IO event handlers for raw capture"""

        @self.sio.event
        def connect():
            self._record_event('connect', None)
            logger.info("Raw capture: Connected to server")

        @self.sio.event
        def disconnect(reason=None):
            self._record_event('disconnect', {'reason': reason})
            logger.info(f"Raw capture: Disconnected ({reason})")

        @self.sio.event
        def connect_error(data):
            self._record_event('connect_error', {'error': str(data)})
            logger.error(f"Raw capture: Connection error: {data}")

        # Catch-all handler for ALL other events
        @self.sio.on('*')
        def catch_all(event, *args):
            # Convert args to serializable format
            data = args[0] if len(args) == 1 else list(args) if args else None
            self._record_event(event, data)

    def _record_event(self, event_name: str, data: Any):
        """
        Record a single event to the capture file.

        Args:
            event_name: Socket.IO event name
            data: Event payload (any JSON-serializable data)
        """
        if not self.is_capturing or not self.file_handle:
            return

        with self._lock:
            self.sequence_number += 1

            # Track event counts
            self.event_counts[event_name] = self.event_counts.get(event_name, 0) + 1

            # Build record
            record = {
                'seq': self.sequence_number,
                'ts': datetime.now().isoformat(),
                'event': event_name,
                'data': data
            }

            try:
                # Write to file (one JSON object per line)
                json_line = json.dumps(record, default=str)
                self.file_handle.write(json_line + '\n')
                self.file_handle.flush()  # Ensure data is written immediately

                # Notify UI
                if self.on_event_captured:
                    self.on_event_captured(event_name, self.sequence_number)

            except Exception as e:
                logger.error(f"Failed to write event: {e}")

    def stop_capture(self) -> Optional[Dict[str, Any]]:
        """
        Stop capturing and close the connection.

        Returns:
            Dict with capture summary, or None if not capturing
        """
        with self._lock:
            if not self.is_capturing:
                return None

            logger.info("Stopping raw capture...")

            # Calculate duration
            duration = None
            if self.start_time:
                duration = (datetime.now() - self.start_time).total_seconds()

            # Build summary BEFORE cleanup
            summary = {
                'capture_file': str(self.capture_file),
                'total_events': self.sequence_number,
                'event_counts': dict(self.event_counts),
                'duration_seconds': duration,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': datetime.now().isoformat()
            }

            # Store references for async cleanup
            sio_ref = self.sio
            capture_file_ref = self.capture_file
            event_counts_ref = dict(self.event_counts)

            # Cleanup state immediately (don't wait for disconnect)
            self._cleanup()

            logger.info(f"Capture complete: {summary['total_events']} events in {duration:.1f}s" if duration else "Capture complete")

        # Disconnect Socket.IO in background thread to avoid UI freeze
        def disconnect_async():
            if sio_ref and sio_ref.connected:
                try:
                    sio_ref.disconnect()
                    logger.debug("Socket.IO disconnected")
                except Exception as e:
                    logger.warning(f"Error disconnecting: {e}")

            # Notify UI after disconnect
            if self.on_capture_stopped:
                self.on_capture_stopped(capture_file_ref, event_counts_ref)

        disconnect_thread = threading.Thread(target=disconnect_async, daemon=True)
        disconnect_thread.start()

        return summary

    def _cleanup(self):
        """Clean up resources"""
        self.is_capturing = False

        if self.file_handle:
            try:
                self.file_handle.close()
            except Exception:
                pass
            self.file_handle = None

        self.sio = None

    def get_status(self) -> Dict[str, Any]:
        """
        Get current capture status.

        Returns:
            Dict with is_capturing, file, event_count, event_types
        """
        with self._lock:
            return {
                'is_capturing': self.is_capturing,
                'capture_file': str(self.capture_file) if self.capture_file else None,
                'total_events': self.sequence_number,
                'event_counts': dict(self.event_counts),
                'connected': self.sio.connected if self.sio else False
            }

    def get_last_capture_file(self) -> Optional[Path]:
        """
        Get the most recent capture file.

        Returns:
            Path to most recent capture, or None if no captures exist
        """
        captures = sorted(self.capture_dir.glob('*_raw.jsonl'), reverse=True)
        return captures[0] if captures else None
