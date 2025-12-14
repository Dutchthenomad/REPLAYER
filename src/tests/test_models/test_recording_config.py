"""
Tests for RecordingConfig model - Phase 10.5A Config Model & Persistence

TDD: Tests written FIRST before implementation.

Tests cover:
- CaptureMode enum: game_state_only, game_and_player
- MonitorThresholdType enum: ticks, games
- RecordingConfig dataclass with defaults
- JSON serialization (to_dict)
- JSON deserialization (from_dict)
- File persistence (save/load)
- Default config factory
"""

import json
import os
import pytest
import tempfile
from datetime import datetime
from pathlib import Path

# These imports will FAIL until we create the module (TDD RED phase)
from models.recording_config import (
    CaptureMode,
    MonitorThresholdType,
    RecordingConfig,
)


class TestEnums:
    """Tests for recording config enums"""

    @pytest.mark.parametrize("enum_val,expected", [
        (CaptureMode.GAME_STATE_ONLY, "game_state_only"),
        (CaptureMode.GAME_AND_PLAYER, "game_and_player"),
        (MonitorThresholdType.TICKS, "ticks"),
        (MonitorThresholdType.GAMES, "games"),
    ])
    def test_enum_values(self, enum_val, expected):
        """Test all enum values are correct"""
        assert enum_val.value == expected

    @pytest.mark.parametrize("str_val,expected_enum", [
        ("game_state_only", CaptureMode.GAME_STATE_ONLY),
        ("game_and_player", CaptureMode.GAME_AND_PLAYER),
    ])
    def test_capture_mode_from_string(self, str_val, expected_enum):
        """Test creating CaptureMode from string value"""
        assert CaptureMode(str_val) == expected_enum


class TestRecordingConfigDefaults:
    """Tests for RecordingConfig default values"""

    @pytest.mark.parametrize("attr,expected", [
        ("capture_mode", CaptureMode.GAME_STATE_ONLY),
        ("game_count", None),
        ("time_limit_minutes", None),
        ("monitor_threshold_type", MonitorThresholdType.TICKS),
        ("monitor_threshold_value", 20),
        ("audio_cues", True),
        ("auto_start_on_launch", False),
        ("last_modified", None),
    ])
    def test_default_values(self, attr, expected):
        """Test all default values are correct"""
        config = RecordingConfig()
        assert getattr(config, attr) == expected


class TestRecordingConfigCreation:
    """Tests for RecordingConfig creation with custom values"""

    def test_creation_with_capture_mode(self):
        """Test creating config with game_and_player capture mode"""
        config = RecordingConfig(capture_mode=CaptureMode.GAME_AND_PLAYER)
        assert config.capture_mode == CaptureMode.GAME_AND_PLAYER

    def test_creation_with_game_count(self):
        """Test creating config with specific game count"""
        config = RecordingConfig(game_count=25)
        assert config.game_count == 25

    def test_creation_with_time_limit(self):
        """Test creating config with time limit"""
        config = RecordingConfig(time_limit_minutes=30)
        assert config.time_limit_minutes == 30

    def test_creation_with_monitor_by_games(self):
        """Test creating config with monitor threshold by games"""
        config = RecordingConfig(
            monitor_threshold_type=MonitorThresholdType.GAMES,
            monitor_threshold_value=3
        )
        assert config.monitor_threshold_type == MonitorThresholdType.GAMES
        assert config.monitor_threshold_value == 3

    def test_creation_with_audio_cues_off(self):
        """Test creating config with audio cues disabled"""
        config = RecordingConfig(audio_cues=False)
        assert config.audio_cues is False

    def test_creation_with_auto_start(self):
        """Test creating config with auto_start enabled"""
        config = RecordingConfig(auto_start_on_launch=True)
        assert config.auto_start_on_launch is True

    def test_creation_full(self):
        """Test creating config with all fields"""
        timestamp = datetime(2025, 12, 7, 14, 30, 0)
        config = RecordingConfig(
            capture_mode=CaptureMode.GAME_AND_PLAYER,
            game_count=50,
            time_limit_minutes=60,
            monitor_threshold_type=MonitorThresholdType.GAMES,
            monitor_threshold_value=5,
            audio_cues=False,
            auto_start_on_launch=True,
            last_modified=timestamp
        )
        assert config.capture_mode == CaptureMode.GAME_AND_PLAYER
        assert config.game_count == 50
        assert config.time_limit_minutes == 60
        assert config.monitor_threshold_type == MonitorThresholdType.GAMES
        assert config.monitor_threshold_value == 5
        assert config.audio_cues is False
        assert config.auto_start_on_launch is True
        assert config.last_modified == timestamp


class TestRecordingConfigSerialization:
    """Tests for RecordingConfig JSON serialization"""

    def test_to_dict_defaults(self):
        """Test serialization with default values"""
        config = RecordingConfig()
        result = config.to_dict()

        assert result["capture_mode"] == "game_state_only"
        assert result["game_count"] is None  # infinite
        assert result["time_limit_minutes"] is None
        assert result["monitor_threshold_type"] == "ticks"
        assert result["monitor_threshold_value"] == 20
        assert result["audio_cues"] is True
        assert result["auto_start_on_launch"] is False
        assert result["last_modified"] is None

    def test_to_dict_full(self):
        """Test serialization with all values set"""
        timestamp = datetime(2025, 12, 7, 14, 30, 0)
        config = RecordingConfig(
            capture_mode=CaptureMode.GAME_AND_PLAYER,
            game_count=25,
            time_limit_minutes=45,
            monitor_threshold_type=MonitorThresholdType.GAMES,
            monitor_threshold_value=3,
            audio_cues=False,
            auto_start_on_launch=True,
            last_modified=timestamp
        )
        result = config.to_dict()

        assert result["capture_mode"] == "game_and_player"
        assert result["game_count"] == 25
        assert result["time_limit_minutes"] == 45
        assert result["monitor_threshold_type"] == "games"
        assert result["monitor_threshold_value"] == 3
        assert result["audio_cues"] is False
        assert result["auto_start_on_launch"] is True
        assert result["last_modified"] == "2025-12-07T14:30:00"

    def test_from_dict_defaults(self):
        """Test deserialization creating config with defaults"""
        data = {
            "capture_mode": "game_state_only",
            "game_count": None,
            "time_limit_minutes": None,
            "monitor_threshold_type": "ticks",
            "monitor_threshold_value": 20,
            "audio_cues": True,
            "auto_start_on_launch": False,
            "last_modified": None
        }
        config = RecordingConfig.from_dict(data)

        assert config.capture_mode == CaptureMode.GAME_STATE_ONLY
        assert config.game_count is None
        assert config.time_limit_minutes is None
        assert config.monitor_threshold_type == MonitorThresholdType.TICKS
        assert config.monitor_threshold_value == 20
        assert config.audio_cues is True
        assert config.auto_start_on_launch is False
        assert config.last_modified is None

    def test_from_dict_full(self):
        """Test deserialization with all values"""
        data = {
            "capture_mode": "game_and_player",
            "game_count": 10,
            "time_limit_minutes": 120,
            "monitor_threshold_type": "games",
            "monitor_threshold_value": 5,
            "audio_cues": False,
            "auto_start_on_launch": True,
            "last_modified": "2025-12-07T14:30:00"
        }
        config = RecordingConfig.from_dict(data)

        assert config.capture_mode == CaptureMode.GAME_AND_PLAYER
        assert config.game_count == 10
        assert config.time_limit_minutes == 120
        assert config.monitor_threshold_type == MonitorThresholdType.GAMES
        assert config.monitor_threshold_value == 5
        assert config.audio_cues is False
        assert config.auto_start_on_launch is True
        assert config.last_modified == datetime(2025, 12, 7, 14, 30, 0)

    def test_roundtrip(self):
        """Test serialization->deserialization roundtrip"""
        original = RecordingConfig(
            capture_mode=CaptureMode.GAME_AND_PLAYER,
            game_count=50,
            time_limit_minutes=60,
            monitor_threshold_type=MonitorThresholdType.GAMES,
            monitor_threshold_value=3,
            audio_cues=False,
            auto_start_on_launch=True,
            last_modified=datetime(2025, 12, 7, 14, 30, 0)
        )

        serialized = original.to_dict()
        restored = RecordingConfig.from_dict(serialized)

        assert restored.capture_mode == original.capture_mode
        assert restored.game_count == original.game_count
        assert restored.time_limit_minutes == original.time_limit_minutes
        assert restored.monitor_threshold_type == original.monitor_threshold_type
        assert restored.monitor_threshold_value == original.monitor_threshold_value
        assert restored.audio_cues == original.audio_cues
        assert restored.auto_start_on_launch == original.auto_start_on_launch
        assert restored.last_modified == original.last_modified


class TestRecordingConfigFilePersistence:
    """Tests for RecordingConfig file persistence"""

    def test_save_to_file(self):
        """Test saving config to JSON file"""
        config = RecordingConfig(
            capture_mode=CaptureMode.GAME_AND_PLAYER,
            game_count=25,
            audio_cues=False
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            config.save(filepath)

            # Verify file exists and contains valid JSON
            assert os.path.exists(filepath)
            with open(filepath, 'r') as f:
                data = json.load(f)
            assert data["capture_mode"] == "game_and_player"
            assert data["game_count"] == 25
            assert data["audio_cues"] is False
        finally:
            os.unlink(filepath)

    def test_load_from_file(self):
        """Test loading config from JSON file"""
        data = {
            "capture_mode": "game_and_player",
            "game_count": 10,
            "time_limit_minutes": 30,
            "monitor_threshold_type": "ticks",
            "monitor_threshold_value": 15,
            "audio_cues": True,
            "auto_start_on_launch": True,
            "last_modified": "2025-12-07T14:30:00"
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            filepath = f.name

        try:
            config = RecordingConfig.load(filepath)

            assert config.capture_mode == CaptureMode.GAME_AND_PLAYER
            assert config.game_count == 10
            assert config.time_limit_minutes == 30
            assert config.monitor_threshold_value == 15
            assert config.auto_start_on_launch is True
        finally:
            os.unlink(filepath)

    def test_load_returns_default_if_file_missing(self):
        """Test load returns default config if file doesn't exist"""
        config = RecordingConfig.load("/nonexistent/path/config.json")

        # Should return default config
        assert config.capture_mode == CaptureMode.GAME_STATE_ONLY
        assert config.game_count is None
        assert config.monitor_threshold_value == 20

    def test_load_returns_default_if_file_invalid(self):
        """Test load returns default config if file contains invalid JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("not valid json {{{")
            filepath = f.name

        try:
            config = RecordingConfig.load(filepath)

            # Should return default config
            assert config.capture_mode == CaptureMode.GAME_STATE_ONLY
            assert config.game_count is None
        finally:
            os.unlink(filepath)

    def test_save_creates_directory(self):
        """Test save creates parent directories if they don't exist"""
        config = RecordingConfig()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "subdir", "nested", "config.json")
            config.save(filepath)

            assert os.path.exists(filepath)
            with open(filepath, 'r') as f:
                data = json.load(f)
            assert data["capture_mode"] == "game_state_only"

    def test_save_and_load_roundtrip(self):
        """Test full save->load roundtrip"""
        original = RecordingConfig(
            capture_mode=CaptureMode.GAME_AND_PLAYER,
            game_count=50,
            time_limit_minutes=90,
            monitor_threshold_type=MonitorThresholdType.GAMES,
            monitor_threshold_value=2,
            audio_cues=False,
            auto_start_on_launch=True,
            last_modified=datetime(2025, 12, 7, 15, 45, 30)
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            original.save(filepath)
            loaded = RecordingConfig.load(filepath)

            assert loaded.capture_mode == original.capture_mode
            assert loaded.game_count == original.game_count
            assert loaded.time_limit_minutes == original.time_limit_minutes
            assert loaded.monitor_threshold_type == original.monitor_threshold_type
            assert loaded.monitor_threshold_value == original.monitor_threshold_value
            assert loaded.audio_cues == original.audio_cues
            assert loaded.auto_start_on_launch == original.auto_start_on_launch
            assert loaded.last_modified == original.last_modified
        finally:
            os.unlink(filepath)


class TestRecordingConfigHelpers:
    """Tests for RecordingConfig helper methods"""

    def test_is_game_count_infinite_when_none(self):
        """Test game count is infinite when None"""
        config = RecordingConfig(game_count=None)
        assert config.is_game_count_infinite() is True

    def test_is_game_count_infinite_when_set(self):
        """Test game count is not infinite when set"""
        config = RecordingConfig(game_count=25)
        assert config.is_game_count_infinite() is False

    def test_is_time_limit_off_when_none(self):
        """Test time limit is off when None"""
        config = RecordingConfig(time_limit_minutes=None)
        assert config.is_time_limit_off() is True

    def test_is_time_limit_off_when_set(self):
        """Test time limit is not off when set"""
        config = RecordingConfig(time_limit_minutes=30)
        assert config.is_time_limit_off() is False

    def test_get_default_config_path(self):
        """Test default config path is returned correctly"""
        path = RecordingConfig.get_default_config_path()
        # Should be a Path object ending with recording_config.json
        assert isinstance(path, Path)
        assert path.name == "recording_config.json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
