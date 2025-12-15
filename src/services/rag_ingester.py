"""
RAG Ingester - Event Cataloging for rugs-expert Agent

Catalogs WebSocket events to JSONL format for RAG pipeline indexing.
Compatible with claude-flow/rag-pipeline/ingestion/event_chunker.py
"""
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)

# Known event types (documented in EVENTS_INDEX.md)
KNOWN_EVENTS = {
    'gameStateUpdate',
    'standard/newTrade',
    'newChatMessage',
    'goldenHourUpdate',
    'goldenHourDrawing',
    'battleEventUpdate',
    'usernameStatus',
    'playerUpdate',
    'connect',
    'disconnect',
}


class RAGIngester:
    """
    Catalogs WebSocket events for RAG pipeline.

    Writes events to JSONL format compatible with claude-flow's
    event_chunker.py for automatic indexing by rugs-expert agent.
    """

    DEFAULT_CAPTURE_DIR = Path('/home/nomad/rugs_recordings/raw_captures')

    def __init__(self, capture_dir: Optional[Path] = None):
        """
        Initialize RAG ingester.

        Args:
            capture_dir: Directory for capture files
        """
        self.capture_dir = capture_dir or self.DEFAULT_CAPTURE_DIR
        self.capture_dir.mkdir(parents=True, exist_ok=True)

        # Session state
        self.current_session: Optional[Path] = None
        self._file_handle = None
        self._lock = threading.Lock()

        # Statistics
        self.sequence_number: int = 0
        self.event_counts: Dict[str, int] = {}
        self.novel_events: Set[str] = set()
        self.start_time: Optional[datetime] = None

        logger.info(f"RAGIngester initialized: {self.capture_dir}")

    def start_session(self) -> Optional[Path]:
        """
        Start a new capture session.

        Returns:
            Path to capture file
        """
        with self._lock:
            if self._file_handle:
                logger.warning("Session already active")
                return self.current_session

            # Generate filename
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            self.current_session = self.capture_dir / f'{timestamp}_cdp.jsonl'

            # Reset state
            self.sequence_number = 0
            self.event_counts = {}
            self.novel_events = set()
            self.start_time = datetime.now()

            # Open file
            self._file_handle = open(self.current_session, 'w', encoding='utf-8')

            logger.info(f"RAG capture session started: {self.current_session}")
            return self.current_session

    def catalog(self, event: Dict[str, Any]):
        """
        Catalog an event for RAG indexing.

        Args:
            event: Event dict with 'event', 'data', 'timestamp', 'direction'
        """
        if not self._file_handle:
            return

        with self._lock:
            self.sequence_number += 1
            event_type = event.get('event', 'unknown')

            # Track counts
            self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1

            # Check for novel events
            if event_type not in KNOWN_EVENTS:
                if event_type not in self.novel_events:
                    self.novel_events.add(event_type)
                    logger.info(f"🆕 Novel event type discovered: {event_type}")

            # Build record (compatible with event_chunker.py)
            record = {
                'seq': self.sequence_number,
                'ts': event.get('timestamp', datetime.now().isoformat()),
                'event': event_type,
                'data': event.get('data'),
                'source': 'cdp_intercept',
                'direction': event.get('direction', 'received')
            }

            try:
                json_line = json.dumps(record, default=str)
                self._file_handle.write(json_line + '\n')
                self._file_handle.flush()
            except Exception as e:
                logger.error(f"Failed to write event: {e}")

    def stop_session(self) -> Optional[Dict[str, Any]]:
        """
        Stop the capture session.

        Returns:
            Summary dict with statistics
        """
        with self._lock:
            if not self._file_handle:
                return None

            # Calculate duration
            duration = None
            if self.start_time:
                duration = (datetime.now() - self.start_time).total_seconds()

            # Build summary
            summary = {
                'capture_file': str(self.current_session),
                'total_events': self.sequence_number,
                'event_counts': dict(self.event_counts),
                'novel_events': list(self.novel_events),
                'duration_seconds': duration
            }

            # Close file
            try:
                self._file_handle.close()
            except Exception:
                pass

            self._file_handle = None
            self.current_session = None

            logger.info(f"RAG capture complete: {summary['total_events']} events")
            if self.novel_events:
                logger.info(f"Novel events discovered: {self.novel_events}")

            return summary

    def get_status(self) -> Dict[str, Any]:
        """Get current session status."""
        with self._lock:
            return {
                'is_active': self._file_handle is not None,
                'capture_file': str(self.current_session) if self.current_session else None,
                'event_count': self.sequence_number,
                'event_types': len(self.event_counts),
                'novel_events': list(self.novel_events)
            }
