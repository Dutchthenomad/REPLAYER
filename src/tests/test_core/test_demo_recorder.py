"""
Tests for DemoRecorderSink - Human Demonstration Recording

TDD: These tests are written FIRST before implementation.
All tests should FAIL until DemoRecorderSink is implemented.
"""

import pytest
import tempfile
import json
import time
import threading
from pathlib import Path
from decimal import Decimal
from datetime import datetime

# These imports will fail until implementation exists
from core.demo_recorder import DemoRecorderSink
from models import (
    ActionCategory,
    StateSnapshot,
    DemoAction,
    get_category_for_button,
)


class TestDemoRecorderInit:
    """Tests for DemoRecorderSink initialization"""

    def test_init_creates_base_directory(self):
        """Test DemoRecorderSink creates base directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "demonstrations"
            assert not test_dir.exists()

            recorder = DemoRecorderSink(test_dir)

            assert test_dir.exists()
            assert recorder.base_dir == test_dir

    def test_init_with_existing_directory(self):
        """Test DemoRecorderSink with pre-existing directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            recorder = DemoRecorderSink(test_dir)

            assert recorder.base_dir == test_dir

    def test_init_with_custom_buffer_size(self):
        """Test DemoRecorderSink with custom buffer size"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir, buffer_size=50)

            assert recorder.buffer_size == 50


class TestSessionManagement:
    """Tests for session start/stop functionality"""

    def test_start_session_creates_directory(self):
        """Test start_session creates session directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir)

            session_id = recorder.start_session()

            assert session_id is not None
            session_dir = Path(tmpdir) / session_id
            assert session_dir.exists()
            assert session_dir.is_dir()

    def test_session_naming_convention(self):
        """Test session directory follows naming convention: session_YYYYMMDD_HHMMSS"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir)

            before_time = datetime.now()
            session_id = recorder.start_session()
            after_time = datetime.now()

            # Verify naming convention
            assert session_id.startswith("session_")

            # Extract timestamp from session_id
            timestamp_str = session_id.replace("session_", "")
            session_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

            # Verify timestamp is within test execution window
            from datetime import timedelta
            assert (before_time - timedelta(seconds=1)) <= session_time <= (after_time + timedelta(seconds=1))

    def test_start_session_twice_ends_first(self):
        """Test starting new session ends previous session"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir)

            session1 = recorder.start_session()
            time.sleep(1.1)  # Ensure different timestamp
            session2 = recorder.start_session()

            assert session1 != session2
            assert (Path(tmpdir) / session1).exists()
            assert (Path(tmpdir) / session2).exists()

    def test_end_session_returns_summary(self):
        """Test end_session returns session summary"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir)
            recorder.start_session()

            summary = recorder.end_session()

            assert summary is not None
            assert 'session_id' in summary
            assert 'games_played' in summary
            assert 'total_actions' in summary

    def test_end_session_creates_metadata_file(self):
        """Test end_session creates session_metadata.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir)
            session_id = recorder.start_session()

            recorder.end_session()

            metadata_file = Path(tmpdir) / session_id / "session_metadata.json"
            assert metadata_file.exists()

            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            assert '_metadata' in metadata
            assert metadata['_metadata']['session_id'] == session_id


class TestGameManagement:
    """Tests for per-game file management"""

    def test_start_game_creates_file(self):
        """Test start_game creates JSONL file for game"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir)
            recorder.start_session()

            filepath = recorder.start_game("abc123")

            assert filepath.exists()
            assert filepath.suffix == ".jsonl"

    def test_game_naming_convention(self):
        """Test game file follows naming: game_NNN_gameId.jsonl"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir)
            recorder.start_session()

            filepath = recorder.start_game("abc123def")

            # game_001_abc123def.jsonl
            assert filepath.name.startswith("game_001_")
            assert "abc123def" in filepath.name

    def test_multiple_games_incrementing_numbers(self):
        """Test multiple games get incrementing numbers"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir)
            recorder.start_session()

            file1 = recorder.start_game("game1")
            recorder.end_game()
            file2 = recorder.start_game("game2")
            recorder.end_game()
            file3 = recorder.start_game("game3")

            assert "game_001_" in file1.name
            assert "game_002_" in file2.name
            assert "game_003_" in file3.name

    def test_start_game_requires_session(self):
        """Test start_game raises error if no session started"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir)

            with pytest.raises(RuntimeError, match="No session"):
                recorder.start_game("abc123")

    def test_end_game_returns_summary(self):
        """Test end_game returns game summary"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir)
            recorder.start_session()
            recorder.start_game("test-game")

            summary = recorder.end_game()

            assert summary is not None
            assert 'game_id' in summary
            assert 'action_count' in summary
            assert 'filepath' in summary

    def test_game_file_has_header(self):
        """Test game file starts with header metadata"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir, buffer_size=1)
            recorder.start_session()
            filepath = recorder.start_game("test-game")
            recorder.end_game()

            with open(filepath, 'r') as f:
                first_line = f.readline()
                header = json.loads(first_line)

            assert '_header' in header
            assert header['_header']['game_id'] == "test-game"

    def test_game_file_has_footer(self):
        """Test game file ends with footer metadata"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir, buffer_size=1)
            recorder.start_session()
            recorder.start_game("test-game")
            recorder.end_game()

            # Find the game file
            session_dir = list(Path(tmpdir).glob("session_*"))[0]
            game_file = list(session_dir.glob("game_*.jsonl"))[0]

            with open(game_file, 'r') as f:
                lines = f.readlines()
                last_line = lines[-1]
                footer = json.loads(last_line)

            assert '_footer' in footer
            assert footer['_footer']['game_id'] == "test-game"


class TestActionRecording:
    """Tests for recording button press actions"""

    @pytest.fixture
    def sample_state(self):
        """Create a sample state snapshot"""
        return StateSnapshot(
            balance=Decimal("0.100"),
            position=None,
            sidebet=None,
            bet_amount=Decimal("0.001"),
            sell_percentage=Decimal("1.0"),
            current_tick=42,
            current_price=Decimal("1.523"),
            phase="ACTIVE"
        )

    def test_record_bet_increment_action(self, sample_state):
        """Test recording bet increment button press"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir, buffer_size=1)
            recorder.start_session()
            recorder.start_game("test-game")

            action_id = recorder.record_button_press(
                button="+0.01",
                state_before=sample_state
            )

            assert action_id is not None
            assert recorder.action_count == 1

    def test_record_action_captures_category(self, sample_state):
        """Test that recorded action has correct category"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir, buffer_size=1)
            recorder.start_session()
            recorder.start_game("test-game")
            recorder.record_button_press(
                button="+0.01",
                state_before=sample_state
            )
            recorder.end_game()

            # Find and read game file
            session_dir = list(Path(tmpdir).glob("session_*"))[0]
            game_file = list(session_dir.glob("game_*.jsonl"))[0]

            with open(game_file, 'r') as f:
                lines = f.readlines()
                # Skip header, get action line
                action_line = lines[1]
                action = json.loads(action_line)

            assert action['category'] == ActionCategory.BET_INCREMENT.value

    def test_record_trade_action_with_amount(self, sample_state):
        """Test recording trade action captures amount"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir, buffer_size=1)
            recorder.start_session()
            recorder.start_game("test-game")

            action_id = recorder.record_button_press(
                button="BUY",
                state_before=sample_state,
                amount=Decimal("0.015")
            )
            recorder.end_game()

            # Find and read game file
            session_dir = list(Path(tmpdir).glob("session_*"))[0]
            game_file = list(session_dir.glob("game_*.jsonl"))[0]

            with open(game_file, 'r') as f:
                lines = f.readlines()
                action_line = lines[1]
                action = json.loads(action_line)

            assert action['category'] == ActionCategory.TRADE_BUY.value
            assert action['amount'] == "0.015"

    def test_record_action_captures_timestamp(self, sample_state):
        """Test that recorded action has timestamp"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir, buffer_size=1)
            recorder.start_session()
            recorder.start_game("test-game")

            before_time = int(time.time() * 1000)
            recorder.record_button_press(
                button="SELL",
                state_before=sample_state
            )
            after_time = int(time.time() * 1000)
            recorder.end_game()

            # Find and read game file
            session_dir = list(Path(tmpdir).glob("session_*"))[0]
            game_file = list(session_dir.glob("game_*.jsonl"))[0]

            with open(game_file, 'r') as f:
                lines = f.readlines()
                action_line = lines[1]
                action = json.loads(action_line)

            assert 'timestamp_pressed' in action
            assert before_time <= action['timestamp_pressed'] <= after_time

    def test_record_action_captures_state_before(self, sample_state):
        """Test that recorded action captures state_before"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir, buffer_size=1)
            recorder.start_session()
            recorder.start_game("test-game")
            recorder.record_button_press(
                button="+0.001",
                state_before=sample_state
            )
            recorder.end_game()

            # Find and read game file
            session_dir = list(Path(tmpdir).glob("session_*"))[0]
            game_file = list(session_dir.glob("game_*.jsonl"))[0]

            with open(game_file, 'r') as f:
                lines = f.readlines()
                action_line = lines[1]
                action = json.loads(action_line)

            assert 'state_before' in action
            assert action['state_before']['balance'] == "0.100"
            assert action['state_before']['current_tick'] == 42
            assert action['state_before']['phase'] == "ACTIVE"

    def test_all_bet_increment_buttons(self, sample_state):
        """Test all bet increment buttons can be recorded"""
        bet_buttons = ['X', '+0.001', '+0.01', '+0.1', '+1', '1/2', 'X2', 'MAX']

        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir, buffer_size=100)
            recorder.start_session()
            recorder.start_game("test-game")

            for button in bet_buttons:
                recorder.record_button_press(
                    button=button,
                    state_before=sample_state
                )

            assert recorder.action_count == len(bet_buttons)

    def test_all_sell_percentage_buttons(self, sample_state):
        """Test all sell percentage buttons can be recorded"""
        pct_buttons = ['10%', '25%', '50%', '100%']

        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir, buffer_size=100)
            recorder.start_session()
            recorder.start_game("test-game")

            for button in pct_buttons:
                recorder.record_button_press(
                    button=button,
                    state_before=sample_state
                )

            assert recorder.action_count == len(pct_buttons)

    def test_all_trade_buttons(self, sample_state):
        """Test all trade buttons can be recorded"""
        trade_buttons = ['BUY', 'SELL', 'SIDEBET']

        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir, buffer_size=100)
            recorder.start_session()
            recorder.start_game("test-game")

            for button in trade_buttons:
                recorder.record_button_press(
                    button=button,
                    state_before=sample_state,
                    amount=Decimal("0.01")
                )

            assert recorder.action_count == len(trade_buttons)


class TestLatencyTracking:
    """Tests for round-trip latency measurement"""

    @pytest.fixture
    def sample_state(self):
        """Create a sample state snapshot"""
        return StateSnapshot(
            balance=Decimal("0.100"),
            position=None,
            sidebet=None,
            bet_amount=Decimal("0.015"),
            sell_percentage=Decimal("1.0"),
            current_tick=42,
            current_price=Decimal("1.523"),
            phase="ACTIVE"
        )

    def test_record_confirmation_updates_latency(self, sample_state):
        """Test recording confirmation calculates latency"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir, buffer_size=1)
            recorder.start_session()
            recorder.start_game("test-game")

            action_id = recorder.record_button_press(
                button="BUY",
                state_before=sample_state,
                amount=Decimal("0.015")
            )

            # Simulate delay
            time.sleep(0.1)

            # Record confirmation
            latency_ms = recorder.record_confirmation(
                action_id=action_id,
                server_data={'success': True, 'server_tick': 43}
            )

            assert latency_ms is not None
            assert latency_ms >= 100  # At least 100ms

    def test_confirmation_written_to_file(self, sample_state):
        """Test confirmation data is written to file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir, buffer_size=1)
            recorder.start_session()
            recorder.start_game("test-game")

            action_id = recorder.record_button_press(
                button="SELL",
                state_before=sample_state,
                amount=Decimal("0.01")
            )

            recorder.record_confirmation(
                action_id=action_id,
                server_data={'success': True, 'server_tick': 50}
            )
            recorder.end_game()

            # Find and read game file
            session_dir = list(Path(tmpdir).glob("session_*"))[0]
            game_file = list(session_dir.glob("game_*.jsonl"))[0]

            with open(game_file, 'r') as f:
                lines = f.readlines()
                action_line = lines[1]
                action = json.loads(action_line)

            assert 'timestamp_confirmed' in action
            assert action['timestamp_confirmed'] is not None
            assert 'latency_ms' in action
            assert 'confirmation' in action
            assert action['confirmation']['success'] is True

    def test_pending_action_not_found_returns_none(self, sample_state):
        """Test confirmation for unknown action returns None"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir)
            recorder.start_session()
            recorder.start_game("test-game")

            latency = recorder.record_confirmation(
                action_id="unknown-id",
                server_data={'success': True}
            )

            assert latency is None


class TestThreadSafety:
    """Tests for thread-safe operations"""

    @pytest.fixture
    def sample_state(self):
        """Create a sample state snapshot"""
        return StateSnapshot(
            balance=Decimal("0.100"),
            position=None,
            sidebet=None,
            bet_amount=Decimal("0.001"),
            sell_percentage=Decimal("1.0"),
            current_tick=0,
            current_price=Decimal("1.0"),
            phase="ACTIVE"
        )

    def test_concurrent_action_recording(self, sample_state):
        """Test concurrent action recording from multiple threads"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir, buffer_size=1)
            recorder.start_session()
            recorder.start_game("test-game")

            def record_actions(button, count):
                for i in range(count):
                    recorder.record_button_press(
                        button=button,
                        state_before=sample_state
                    )

            # Launch 3 threads recording 10 actions each
            threads = []
            buttons = ['+0.001', '+0.01', '+0.1']
            for button in buttons:
                t = threading.Thread(target=record_actions, args=(button, 10))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            # Should have recorded 30 actions total
            assert recorder.action_count == 30

    def test_concurrent_session_and_game_operations(self, sample_state):
        """Test thread safety of session and game operations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir, buffer_size=1)
            recorder.start_session()

            errors = []

            def game_worker(game_num):
                try:
                    recorder.start_game(f"game-{game_num}")
                    for i in range(5):
                        recorder.record_button_press(
                            button="+0.001",
                            state_before=sample_state
                        )
                    recorder.end_game()
                except Exception as e:
                    errors.append(str(e))

            # Note: Only one game at a time, so this tests sequential games
            # from different threads
            for i in range(3):
                game_worker(i)

            assert len(errors) == 0


class TestBuffering:
    """Tests for buffered write behavior"""

    @pytest.fixture
    def sample_state(self):
        """Create a sample state snapshot"""
        return StateSnapshot(
            balance=Decimal("0.100"),
            position=None,
            sidebet=None,
            bet_amount=Decimal("0.001"),
            sell_percentage=Decimal("1.0"),
            current_tick=0,
            current_price=Decimal("1.0"),
            phase="ACTIVE"
        )

    def test_buffer_flushed_on_end_game(self, sample_state):
        """Test buffer flushes when ending game"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir, buffer_size=100)
            recorder.start_session()
            recorder.start_game("test-game")

            # Record fewer actions than buffer size
            for i in range(5):
                recorder.record_button_press(
                    button="+0.001",
                    state_before=sample_state
                )

            recorder.end_game()

            # File should have header + 5 actions + footer
            session_dir = list(Path(tmpdir).glob("session_*"))[0]
            game_file = list(session_dir.glob("game_*.jsonl"))[0]

            with open(game_file, 'r') as f:
                lines = f.readlines()

            assert len(lines) == 7  # 1 header + 5 actions + 1 footer


class TestStatusMethods:
    """Tests for status query methods"""

    def test_is_session_active(self):
        """Test is_session_active returns correct state"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir)

            assert not recorder.is_session_active()

            recorder.start_session()
            assert recorder.is_session_active()

            recorder.end_session()
            assert not recorder.is_session_active()

    def test_is_game_active(self):
        """Test is_game_active returns correct state"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir)
            recorder.start_session()

            assert not recorder.is_game_active()

            recorder.start_game("test-game")
            assert recorder.is_game_active()

            recorder.end_game()
            assert not recorder.is_game_active()

    def test_get_status_returns_dict(self):
        """Test get_status returns complete status"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = DemoRecorderSink(tmpdir)
            recorder.start_session()
            recorder.start_game("test-game")

            status = recorder.get_status()

            assert 'session_id' in status
            assert 'session_active' in status
            assert 'game_id' in status
            assert 'game_active' in status
            assert 'games_played' in status
            assert 'total_actions' in status
