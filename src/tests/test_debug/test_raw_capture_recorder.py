"""
Tests for RawCaptureRecorder

Tests the raw WebSocket capture functionality for protocol debugging.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from debug.raw_capture_recorder import RawCaptureRecorder


class TestRawCaptureRecorderInit:
    """Test RawCaptureRecorder initialization"""

    def test_default_capture_dir(self):
        """Test default capture directory is set"""
        recorder = RawCaptureRecorder()
        assert recorder.capture_dir == Path('/home/nomad/rugs_recordings/raw_captures')

    def test_custom_capture_dir(self):
        """Test custom capture directory"""
        custom_dir = Path('/tmp/test_captures')
        recorder = RawCaptureRecorder(capture_dir=custom_dir)
        assert recorder.capture_dir == custom_dir

    def test_initial_state(self):
        """Test initial state is not capturing"""
        recorder = RawCaptureRecorder()
        assert recorder.is_capturing is False
        assert recorder.capture_file is None
        assert recorder.sequence_number == 0
        assert recorder.event_counts == {}


class TestRawCaptureRecorderCapture:
    """Test capture start/stop functionality"""

    def test_start_capture_creates_file(self):
        """Test starting capture creates JSONL file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RawCaptureRecorder(capture_dir=Path(tmpdir))

            # Mock Socket.IO to avoid actual connection
            with patch.object(recorder, '_connect_async'):
                capture_file = recorder.start_capture()

            assert capture_file is not None
            assert capture_file.suffix == '.jsonl'
            assert '_raw' in capture_file.name
            assert recorder.is_capturing is True

            # Cleanup
            recorder.stop_capture()

    def test_start_capture_while_capturing_returns_existing(self):
        """Test starting capture while already capturing returns existing file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RawCaptureRecorder(capture_dir=Path(tmpdir))

            with patch.object(recorder, '_connect_async'):
                file1 = recorder.start_capture()
                file2 = recorder.start_capture()

            assert file1 == file2

            recorder.stop_capture()

    def test_stop_capture_returns_summary(self):
        """Test stopping capture returns summary dict"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RawCaptureRecorder(capture_dir=Path(tmpdir))

            with patch.object(recorder, '_connect_async'):
                recorder.start_capture()

            # Simulate some events
            recorder._record_event('test_event', {'key': 'value'})
            recorder._record_event('test_event', {'key': 'value2'})
            recorder._record_event('other_event', None)

            summary = recorder.stop_capture()

            assert summary is not None
            assert summary['total_events'] == 3
            assert summary['event_counts']['test_event'] == 2
            assert summary['event_counts']['other_event'] == 1
            assert 'duration_seconds' in summary

    def test_stop_capture_when_not_capturing_returns_none(self):
        """Test stopping when not capturing returns None"""
        recorder = RawCaptureRecorder()
        result = recorder.stop_capture()
        assert result is None


class TestRawCaptureRecorderRecording:
    """Test event recording functionality"""

    def test_record_event_writes_jsonl(self):
        """Test events are written as JSONL"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RawCaptureRecorder(capture_dir=Path(tmpdir))

            with patch.object(recorder, '_connect_async'):
                capture_file = recorder.start_capture()

            # Record some events
            recorder._record_event('connect', None)
            recorder._record_event('gameStateUpdate', {'price': 1.5, 'tickCount': 10})
            recorder._record_event('usernameStatus', {'id': 'test', 'username': 'TestUser'})

            recorder.stop_capture()

            # Read and verify file
            with open(capture_file, 'r') as f:
                lines = f.readlines()

            assert len(lines) == 3

            # Verify first event
            event1 = json.loads(lines[0])
            assert event1['seq'] == 1
            assert event1['event'] == 'connect'
            assert event1['data'] is None
            assert 'ts' in event1

            # Verify second event
            event2 = json.loads(lines[1])
            assert event2['seq'] == 2
            assert event2['event'] == 'gameStateUpdate'
            assert event2['data']['price'] == 1.5

    def test_record_event_increments_sequence(self):
        """Test sequence numbers increment correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RawCaptureRecorder(capture_dir=Path(tmpdir))

            with patch.object(recorder, '_connect_async'):
                recorder.start_capture()

            recorder._record_event('event1', None)
            recorder._record_event('event2', None)
            recorder._record_event('event3', None)

            assert recorder.sequence_number == 3

            recorder.stop_capture()

    def test_record_event_updates_counts(self):
        """Test event counts are tracked correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RawCaptureRecorder(capture_dir=Path(tmpdir))

            with patch.object(recorder, '_connect_async'):
                recorder.start_capture()

            recorder._record_event('gameStateUpdate', {})
            recorder._record_event('gameStateUpdate', {})
            recorder._record_event('playerUpdate', {})

            assert recorder.event_counts['gameStateUpdate'] == 2
            assert recorder.event_counts['playerUpdate'] == 1

            recorder.stop_capture()

    def test_record_event_when_not_capturing_is_noop(self):
        """Test recording when not capturing does nothing"""
        recorder = RawCaptureRecorder()
        recorder._record_event('test', {'data': 'value'})
        assert recorder.sequence_number == 0


class TestRawCaptureRecorderCallbacks:
    """Test callback functionality"""

    def test_on_capture_started_callback(self):
        """Test capture started callback is invoked"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RawCaptureRecorder(capture_dir=Path(tmpdir))

            callback = Mock()
            recorder.on_capture_started = callback

            with patch.object(recorder, '_connect_async'):
                capture_file = recorder.start_capture()

            callback.assert_called_once_with(capture_file)
            recorder.stop_capture()

    def test_on_capture_stopped_callback(self):
        """Test capture stopped callback is invoked"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RawCaptureRecorder(capture_dir=Path(tmpdir))

            callback = Mock()
            recorder.on_capture_stopped = callback

            with patch.object(recorder, '_connect_async'):
                capture_file = recorder.start_capture()

            recorder._record_event('test', {})
            recorder.stop_capture()

            callback.assert_called_once()
            args = callback.call_args[0]
            assert args[0] == capture_file
            assert args[1] == {'test': 1}

    def test_on_event_captured_callback(self):
        """Test event captured callback is invoked"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RawCaptureRecorder(capture_dir=Path(tmpdir))

            callback = Mock()
            recorder.on_event_captured = callback

            with patch.object(recorder, '_connect_async'):
                recorder.start_capture()

            recorder._record_event('test_event', {'key': 'value'})

            callback.assert_called_once_with('test_event', 1)
            recorder.stop_capture()


class TestRawCaptureRecorderStatus:
    """Test status reporting"""

    def test_get_status_when_not_capturing(self):
        """Test status when not capturing"""
        recorder = RawCaptureRecorder()
        status = recorder.get_status()

        assert status['is_capturing'] is False
        assert status['capture_file'] is None
        assert status['total_events'] == 0
        assert status['connected'] is False

    def test_get_status_when_capturing(self):
        """Test status while capturing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RawCaptureRecorder(capture_dir=Path(tmpdir))

            with patch.object(recorder, '_connect_async'):
                recorder.start_capture()

            recorder._record_event('event1', {})
            recorder._record_event('event2', {})

            status = recorder.get_status()

            assert status['is_capturing'] is True
            assert status['capture_file'] is not None
            assert status['total_events'] == 2
            assert status['event_counts'] == {'event1': 1, 'event2': 1}

            recorder.stop_capture()

    def test_get_last_capture_file_returns_most_recent(self):
        """Test getting most recent capture file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            recorder = RawCaptureRecorder(capture_dir=tmppath)

            # Create some test files (older first)
            (tmppath / '2025-01-01_00-00-00_raw.jsonl').touch()
            (tmppath / '2025-01-02_00-00-00_raw.jsonl').touch()
            (tmppath / '2025-01-03_00-00-00_raw.jsonl').touch()

            last = recorder.get_last_capture_file()
            assert last.name == '2025-01-03_00-00-00_raw.jsonl'

    def test_get_last_capture_file_when_none_exist(self):
        """Test getting last capture when none exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RawCaptureRecorder(capture_dir=Path(tmpdir))
            assert recorder.get_last_capture_file() is None


class TestRawCaptureRecorderServerUrl:
    """Test server URL configuration"""

    def test_server_url_is_correct(self):
        """Test server URL matches expected value"""
        recorder = RawCaptureRecorder()
        assert recorder.SERVER_URL == 'https://backend.rugs.fun?frontend-version=1.0'
