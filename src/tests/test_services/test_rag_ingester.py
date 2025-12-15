"""Tests for RAG event ingestion."""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from services.rag_ingester import RAGIngester


class TestRAGIngester:
    """Test RAG event cataloging."""

    def test_init_creates_capture_dir(self, tmp_path):
        """Ingester creates capture directory if missing."""
        capture_dir = tmp_path / "captures"
        ingester = RAGIngester(capture_dir=capture_dir)

        assert capture_dir.exists()

    def test_start_session_creates_file(self, tmp_path):
        """Starting session creates JSONL file."""
        ingester = RAGIngester(capture_dir=tmp_path)

        filepath = ingester.start_session()

        assert filepath is not None
        assert filepath.exists()
        assert filepath.suffix == '.jsonl'

    def test_catalog_writes_event(self, tmp_path):
        """Cataloging event writes to file."""
        ingester = RAGIngester(capture_dir=tmp_path)
        ingester.start_session()

        event = {
            'event': 'gameStateUpdate',
            'data': {'price': 1.5},
            'timestamp': '2025-12-14T12:00:00',
            'direction': 'received'
        }
        ingester.catalog(event)

        # Read back
        with open(ingester.current_session) as f:
            line = f.readline()
            record = json.loads(line)

        assert record['event'] == 'gameStateUpdate'
        assert record['data']['price'] == 1.5
        assert record['source'] == 'cdp_intercept'

    def test_catalog_tracks_event_counts(self, tmp_path):
        """Cataloging tracks event type counts."""
        ingester = RAGIngester(capture_dir=tmp_path)
        ingester.start_session()

        ingester.catalog({'event': 'gameStateUpdate', 'data': {}})
        ingester.catalog({'event': 'gameStateUpdate', 'data': {}})
        ingester.catalog({'event': 'usernameStatus', 'data': {}})

        assert ingester.event_counts['gameStateUpdate'] == 2
        assert ingester.event_counts['usernameStatus'] == 1

    def test_catalog_detects_novel_events(self, tmp_path):
        """Cataloging detects undocumented events."""
        ingester = RAGIngester(capture_dir=tmp_path)
        ingester.start_session()

        ingester.catalog({'event': 'unknownNewEvent', 'data': {}})

        assert 'unknownNewEvent' in ingester.novel_events

    def test_catalog_known_event_not_novel(self, tmp_path):
        """Known events not flagged as novel."""
        ingester = RAGIngester(capture_dir=tmp_path)
        ingester.start_session()

        ingester.catalog({'event': 'gameStateUpdate', 'data': {}})

        assert 'gameStateUpdate' not in ingester.novel_events

    def test_stop_session_returns_summary(self, tmp_path):
        """Stopping session returns summary."""
        ingester = RAGIngester(capture_dir=tmp_path)
        ingester.start_session()
        ingester.catalog({'event': 'gameStateUpdate', 'data': {}})

        summary = ingester.stop_session()

        assert summary['total_events'] == 1
        assert 'gameStateUpdate' in summary['event_counts']
        assert summary['capture_file'] is not None

    def test_stop_session_closes_file(self, tmp_path):
        """Stopping session closes file handle."""
        ingester = RAGIngester(capture_dir=tmp_path)
        ingester.start_session()

        ingester.stop_session()

        assert ingester.current_session is None
        assert ingester._file_handle is None
