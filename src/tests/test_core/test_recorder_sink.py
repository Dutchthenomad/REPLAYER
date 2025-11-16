"""
Tests for RecorderSink class
"""

import pytest
import tempfile
import json
import time
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from core.recorder_sink import RecorderSink
from models import GameTick


class TestRecorderSinkInit:
    """Tests for RecorderSink initialization"""

    def test_init_creates_directory(self):
        """Test RecorderSink creates recordings directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "recordings"
            assert not test_dir.exists()

            recorder = RecorderSink(test_dir)

            assert test_dir.exists()
            assert recorder.recordings_dir == test_dir

    def test_init_with_existing_directory(self):
        """Test RecorderSink with pre-existing directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            recorder = RecorderSink(test_dir)

            assert recorder.recordings_dir == test_dir

    def test_init_with_custom_buffer_size(self):
        """Test RecorderSink with custom buffer size"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir, buffer_size=50)

            assert recorder.buffer_size == 50


class TestRecorderSinkFileNaming:
    """Tests for timestamp-based file naming"""

    def test_start_recording_creates_timestamped_file(self):
        """Test that start_recording creates file with timestamp"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir)

            before_time = datetime.now()
            filepath = recorder.start_recording(game_id="test-game-123")
            after_time = datetime.now()

            assert filepath.exists()
            assert filepath.suffix == ".jsonl"
            assert filepath.name.startswith("game_")

            # Extract timestamp from filename (game_YYYYMMDD_HHMMSS.jsonl)
            timestamp_str = filepath.stem.replace("game_", "")
            file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

            # Verify timestamp is within test execution window (allow 1 second tolerance)
            from datetime import timedelta
            time_tolerance = timedelta(seconds=1)
            assert (before_time - time_tolerance) <= file_time <= (after_time + time_tolerance)

    def test_multiple_recordings_have_unique_filenames(self):
        """Test that sequential recordings get unique timestamps"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir)

            filepath1 = recorder.start_recording("game1")
            time.sleep(1.1)  # Ensure different second in timestamp
            filepath2 = recorder.start_recording("game2")

            assert filepath1 != filepath2
            assert filepath1.exists()
            assert filepath2.exists()


class TestRecorderSinkTickRecording:
    """Tests for tick recording functionality"""

    @pytest.fixture
    def sample_tick(self):
        """Create a sample game tick"""
        return GameTick(
            game_id="test-game",
            tick=42,
            timestamp="2025-11-15T10:00:00",
            price=Decimal("1.5"),
            phase="ACTIVE",
            active=True,
            rugged=False,
            cooldown_timer=0,
            trade_count=10
        )

    def test_record_tick_writes_to_file(self, sample_tick):
        """Test that record_tick writes tick to file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir)
            recorder.start_recording(sample_tick.game_id)

            result = recorder.record_tick(sample_tick)

            assert result is True
            assert recorder.tick_count == 1

    def test_record_tick_auto_starts_recording(self, sample_tick):
        """Test that record_tick auto-starts recording if not started"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir)

            # Record without explicitly starting
            result = recorder.record_tick(sample_tick)

            assert result is True
            assert recorder.is_recording()
            assert recorder.current_file is not None

    def test_recorded_tick_format(self, sample_tick):
        """Test that recorded tick has correct JSON format"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir, buffer_size=1)  # Flush immediately
            recorder.start_recording(sample_tick.game_id)
            recorder.record_tick(sample_tick)

            # Save file path before stopping (stop_recording() sets current_file to None)
            filepath = recorder.current_file
            recorder.stop_recording()  # Ensure buffer is flushed

            # Read back the recorded file (skip metadata header and end metadata)
            with open(filepath, 'r') as f:
                lines = f.readlines()
                # Line 0: start metadata, Line 1: tick, Line 2: end metadata
                assert len(lines) >= 2
                tick_line = lines[1].strip()
                data = json.loads(tick_line)

            assert data['game_id'] == sample_tick.game_id
            assert data['tick'] == sample_tick.tick
            assert data['phase'] == sample_tick.phase

    def test_multiple_ticks_recorded(self, sample_tick):
        """Test recording multiple ticks"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir, buffer_size=10)
            recorder.start_recording(sample_tick.game_id)

            # Record 5 ticks
            for i in range(5):
                tick = GameTick(
                    game_id=sample_tick.game_id,
                    tick=i,
                    timestamp=f"2025-11-15T10:00:{i:02d}",
                    price=Decimal("1.0") + Decimal(str(i * 0.1)),
                    phase="ACTIVE",
                    active=True,
                    rugged=False,
                    cooldown_timer=0,
                    trade_count=i
                )
                recorder.record_tick(tick)

            assert recorder.tick_count == 5


class TestRecorderSinkBuffering:
    """Tests for buffered write behavior"""

    def test_buffer_not_flushed_until_full(self):
        """Test that buffer doesn't flush until reaching buffer_size"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir, buffer_size=3)
            recorder.start_recording("test-game")

            # Record 2 ticks (buffer not full)
            for i in range(2):
                tick = GameTick(
                    game_id="test-game",
                    tick=i,
                    timestamp=f"2025-11-15T10:00:{i:02d}",
                    price=Decimal("1.0"),
                    phase="ACTIVE",
                    active=True,
                    rugged=False,
                    cooldown_timer=0,
                    trade_count=0
                )
                recorder.record_tick(tick)

            # File should only have metadata header (ticks not flushed yet)
            with open(recorder.current_file, 'r') as f:
                lines = f.readlines()
            assert len(lines) == 1  # Only metadata header

    def test_buffer_flushed_when_full(self):
        """Test that buffer flushes when reaching buffer_size"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir, buffer_size=3)
            recorder.start_recording("test-game")

            # Record 3 ticks (buffer full)
            for i in range(3):
                tick = GameTick(
                    game_id="test-game",
                    tick=i,
                    timestamp=f"2025-11-15T10:00:{i:02d}",
                    price=Decimal("1.0"),
                    phase="ACTIVE",
                    active=True,
                    rugged=False,
                    cooldown_timer=0,
                    trade_count=0
                )
                recorder.record_tick(tick)

            # File should have 4 lines (metadata header + 3 ticks)
            with open(recorder.current_file, 'r') as f:
                lines = f.readlines()
            assert len(lines) == 4  # 1 metadata header + 3 ticks

    def test_buffer_flushed_on_stop(self):
        """Test that buffer flushes when stopping recording"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir, buffer_size=100)
            recorder.start_recording("test-game")

            # Record 2 ticks (buffer not full)
            for i in range(2):
                tick = GameTick(
                    game_id="test-game",
                    tick=i,
                    timestamp=f"2025-11-15T10:00:{i:02d}",
                    price=Decimal("1.0"),
                    phase="ACTIVE",
                    active=True,
                    rugged=False,
                    cooldown_timer=0,
                    trade_count=0
                )
                recorder.record_tick(tick)

            # Stop recording (should flush buffer)
            recorder.stop_recording()

            # File should have 4 lines (start metadata + 2 ticks + end metadata)
            filepath = Path(tmpdir) / [f for f in Path(tmpdir).glob("*.jsonl")][0].name
            with open(filepath, 'r') as f:
                lines = f.readlines()
            assert len(lines) == 4  # Start metadata + 2 ticks + end metadata


class TestRecorderSinkStopRecording:
    """Tests for stop_recording functionality"""

    def test_stop_recording_closes_file(self):
        """Test that stop_recording closes file handle"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir)
            recorder.start_recording("test-game")

            assert recorder.is_recording()
            recorder.stop_recording()

            assert not recorder.is_recording()
            assert recorder.file_handle is None
            assert recorder.current_file is None

    def test_stop_recording_returns_summary(self):
        """Test that stop_recording returns correct summary"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir, buffer_size=1)
            recorder.start_recording("test-game")

            # Record 3 ticks
            for i in range(3):
                tick = GameTick(
                    game_id="test-game",
                    tick=i,
                    timestamp=f"2025-11-15T10:00:{i:02d}",
                    price=Decimal("1.0"),
                    phase="ACTIVE",
                    active=True,
                    rugged=False,
                    cooldown_timer=0,
                    trade_count=0
                )
                recorder.record_tick(tick)

            summary = recorder.stop_recording()

            assert summary is not None
            assert 'filepath' in summary
            assert 'tick_count' in summary
            assert 'file_size' in summary
            assert summary['tick_count'] == 3
            assert summary['file_size'] > 0

    def test_stop_recording_without_start_returns_none(self):
        """Test stop_recording without active recording returns None"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir)

            summary = recorder.stop_recording()

            assert summary is None

    def test_start_recording_stops_previous_session(self):
        """Test that starting new recording stops previous one"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir, buffer_size=1)

            # Start first recording
            file1 = recorder.start_recording("game1")
            recorder.record_tick(GameTick(
                game_id="game1",
                tick=0,
                timestamp="2025-11-15T10:00:00",
                price=Decimal("1.0"),
                phase="ACTIVE",
                active=True,
                rugged=False,
                cooldown_timer=0,
                trade_count=0
            ))

            # Start second recording (should stop first)
            time.sleep(1.1)
            file2 = recorder.start_recording("game2")

            assert file1.exists()
            assert file2.exists()
            assert file1 != file2

            # First file should have 3 lines (start metadata + 1 tick + end metadata)
            with open(file1, 'r') as f:
                assert len(f.readlines()) == 3


class TestRecorderSinkStatus:
    """Tests for status query methods"""

    def test_is_recording_false_initially(self):
        """Test is_recording returns False initially"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir)

            assert not recorder.is_recording()

    def test_is_recording_true_after_start(self):
        """Test is_recording returns True after starting"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir)
            recorder.start_recording("test-game")

            assert recorder.is_recording()

    def test_get_current_file_returns_path(self):
        """Test get_current_file returns correct path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir)
            filepath = recorder.start_recording("test-game")

            assert recorder.get_current_file() == filepath

    def test_get_tick_count_increments(self):
        """Test get_tick_count increments correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir)
            recorder.start_recording("test-game")

            assert recorder.get_tick_count() == 0

            for i in range(5):
                recorder.record_tick(GameTick(
                    game_id="test-game",
                    tick=i,
                    timestamp=f"2025-11-15T10:00:{i:02d}",
                    price=Decimal("1.0"),
                    phase="ACTIVE",
                    active=True,
                    rugged=False,
                    cooldown_timer=0,
                    trade_count=0
                ))

            assert recorder.get_tick_count() == 5


class TestRecorderSinkThreadSafety:
    """Tests for thread-safe operations"""

    def test_concurrent_record_tick(self):
        """Test concurrent tick recording from multiple threads"""
        import threading

        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = RecorderSink(tmpdir, buffer_size=1)
            recorder.start_recording("test-game")

            def record_ticks(start_tick, count):
                for i in range(count):
                    tick = GameTick(
                        game_id="test-game",
                        tick=start_tick + i,
                        timestamp=f"2025-11-15T10:00:{i:02d}",
                        price=Decimal("1.0"),
                        phase="ACTIVE",
                        active=True,
                        rugged=False,
                        cooldown_timer=0,
                        trade_count=0
                    )
                    recorder.record_tick(tick)

            # Launch 3 threads recording 10 ticks each
            threads = []
            for i in range(3):
                t = threading.Thread(target=record_ticks, args=(i * 10, 10))
                threads.append(t)
                t.start()

            # Wait for all threads to complete
            for t in threads:
                t.join()

            # Should have recorded 30 ticks total
            assert recorder.get_tick_count() == 30
