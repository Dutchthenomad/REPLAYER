"""
Tests for ReplaySource interface and FileDirectorySource
"""

import pytest
import tempfile
import json
from pathlib import Path
from decimal import Decimal
from core.replay_source import ReplaySource, FileDirectorySource
from models import GameTick


class TestReplaySourceInterface:
    """Tests for ReplaySource abstract interface"""

    def test_cannot_instantiate_abstract_class(self):
        """Test ReplaySource cannot be instantiated directly"""
        with pytest.raises(TypeError):
            ReplaySource()


class TestFileDirectorySource:
    """Tests for FileDirectorySource implementation"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_game_file(self, temp_dir):
        """Create a sample game JSONL file"""
        filepath = temp_dir / "game_test.jsonl"

        ticks = [
            {
                'game_id': 'test-game',
                'tick': 0,
                'timestamp': '2025-11-15T00:00:00',
                'price': 1.0,
                'phase': 'ACTIVE',
                'active': True,
                'rugged': False,
                'cooldown_timer': 0,
                'trade_count': 0
            },
            {
                'game_id': 'test-game',
                'tick': 1,
                'timestamp': '2025-11-15T00:00:01',
                'price': 1.2,
                'phase': 'ACTIVE',
                'active': True,
                'rugged': False,
                'cooldown_timer': 0,
                'trade_count': 1
            },
            {
                'game_id': 'test-game',
                'tick': 2,
                'timestamp': '2025-11-15T00:00:02',
                'price': 1.5,
                'phase': 'ACTIVE',
                'active': True,
                'rugged': False,
                'cooldown_timer': 0,
                'trade_count': 2
            }
        ]

        with open(filepath, 'w') as f:
            for tick in ticks:
                f.write(json.dumps(tick) + '\n')

        return filepath

    def test_init_with_valid_directory(self, temp_dir):
        """Test initializing with valid directory"""
        source = FileDirectorySource(temp_dir)
        assert source.directory == temp_dir

    def test_init_with_invalid_directory(self):
        """Test initializing with non-existent directory fails"""
        with pytest.raises(FileNotFoundError):
            FileDirectorySource("/nonexistent/directory")

    def test_load_game_from_file(self, temp_dir, sample_game_file):
        """Test loading game from JSONL file"""
        source = FileDirectorySource(temp_dir)
        ticks, game_id = source.load(sample_game_file.name)

        assert len(ticks) == 3
        assert game_id == 'test-game'
        assert all(isinstance(tick, GameTick) for tick in ticks)
        assert ticks[0].tick == 0
        assert ticks[1].tick == 1
        assert ticks[2].tick == 2

    def test_load_with_absolute_path(self, sample_game_file):
        """Test loading with absolute file path"""
        source = FileDirectorySource(sample_game_file.parent)
        ticks, game_id = source.load(str(sample_game_file))

        assert len(ticks) == 3
        assert game_id == 'test-game'

    def test_load_nonexistent_file(self, temp_dir):
        """Test loading non-existent file raises error"""
        source = FileDirectorySource(temp_dir)

        with pytest.raises(FileNotFoundError):
            source.load("nonexistent.jsonl")

    def test_load_empty_file(self, temp_dir):
        """Test loading empty file raises error"""
        empty_file = temp_dir / "empty.jsonl"
        empty_file.touch()

        source = FileDirectorySource(temp_dir)

        with pytest.raises(ValueError, match="No valid ticks"):
            source.load(empty_file.name)

    def test_load_invalid_json(self, temp_dir):
        """Test loading file with invalid JSON raises error"""
        bad_file = temp_dir / "bad.jsonl"
        with open(bad_file, 'w') as f:
            f.write("not valid json\n")

        source = FileDirectorySource(temp_dir)

        with pytest.raises(ValueError, match="Invalid tick data"):
            source.load(bad_file.name)

    def test_is_available_existing_file(self, temp_dir, sample_game_file):
        """Test is_available returns True for existing file"""
        source = FileDirectorySource(temp_dir)
        assert source.is_available(sample_game_file.name) == True

    def test_is_available_nonexistent_file(self, temp_dir):
        """Test is_available returns False for missing file"""
        source = FileDirectorySource(temp_dir)
        assert source.is_available("nonexistent.jsonl") == False

    def test_list_available_files(self, temp_dir, sample_game_file):
        """Test listing available JSONL files"""
        # Create additional files
        (temp_dir / "game2.jsonl").touch()
        (temp_dir / "game3.jsonl").touch()
        (temp_dir / "notajsonl.txt").touch()

        source = FileDirectorySource(temp_dir)
        available = source.list_available()

        assert len(available) == 3
        assert "game_test.jsonl" in available
        assert "game2.jsonl" in available
        assert "game3.jsonl" in available
        assert "notajsonl.txt" not in available

    def test_get_metadata(self, temp_dir, sample_game_file):
        """Test getting file metadata"""
        source = FileDirectorySource(temp_dir)
        metadata = source.get_metadata(sample_game_file.name)

        assert 'filepath' in metadata
        assert 'tick_count' in metadata
        assert 'file_size' in metadata
        assert 'modified' in metadata
        assert metadata['tick_count'] == 3

    def test_get_metadata_nonexistent_file(self, temp_dir):
        """Test getting metadata for non-existent file returns empty dict"""
        source = FileDirectorySource(temp_dir)
        metadata = source.get_metadata("nonexistent.jsonl")

        assert metadata == {}
