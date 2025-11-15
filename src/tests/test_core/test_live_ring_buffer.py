"""
Tests for LiveRingBuffer class
"""

import pytest
import threading
from decimal import Decimal
from core.live_ring_buffer import LiveRingBuffer
from models import GameTick


class TestLiveRingBufferInit:
    """Tests for LiveRingBuffer initialization"""

    def test_init_with_default_size(self):
        """Test LiveRingBuffer initializes with default size"""
        buffer = LiveRingBuffer()

        assert buffer.get_max_size() == 5000
        assert buffer.get_size() == 0
        assert not buffer.is_full()

    def test_init_with_custom_size(self):
        """Test LiveRingBuffer with custom size"""
        buffer = LiveRingBuffer(max_size=100)

        assert buffer.get_max_size() == 100
        assert buffer.get_size() == 0

    def test_init_with_invalid_size(self):
        """Test LiveRingBuffer with invalid size raises error"""
        with pytest.raises(ValueError, match="must be positive"):
            LiveRingBuffer(max_size=0)

        with pytest.raises(ValueError, match="must be positive"):
            LiveRingBuffer(max_size=-10)


class TestLiveRingBufferAppend:
    """Tests for append functionality"""

    @pytest.fixture
    def sample_tick(self):
        """Create a sample game tick"""
        return GameTick(
            game_id="test-game",
            tick=0,
            timestamp="2025-11-15T10:00:00",
            price=Decimal("1.0"),
            phase="ACTIVE",
            active=True,
            rugged=False,
            cooldown_timer=0,
            trade_count=0
        )

    def test_append_adds_tick(self, sample_tick):
        """Test append adds tick to buffer"""
        buffer = LiveRingBuffer(max_size=10)

        result = buffer.append(sample_tick)

        assert result is True
        assert buffer.get_size() == 1

    def test_append_multiple_ticks(self):
        """Test appending multiple ticks"""
        buffer = LiveRingBuffer(max_size=10)

        for i in range(5):
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
            buffer.append(tick)

        assert buffer.get_size() == 5

    def test_append_evicts_oldest_when_full(self):
        """Test that append evicts oldest tick when buffer is full"""
        buffer = LiveRingBuffer(max_size=3)

        # Add 3 ticks (buffer full)
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
            buffer.append(tick)

        assert buffer.is_full()
        assert buffer.get_oldest_tick().tick == 0

        # Add 4th tick (should evict tick 0)
        tick4 = GameTick(
            game_id="test-game",
            tick=3,
            timestamp="2025-11-15T10:00:03",
            price=Decimal("1.0"),
            phase="ACTIVE",
            active=True,
            rugged=False,
            cooldown_timer=0,
            trade_count=0
        )
        buffer.append(tick4)

        assert buffer.get_size() == 3  # Still size 3 (max)
        assert buffer.get_oldest_tick().tick == 1  # Tick 0 evicted
        assert buffer.get_newest_tick().tick == 3


class TestLiveRingBufferRetrieve:
    """Tests for tick retrieval methods"""

    @pytest.fixture
    def populated_buffer(self):
        """Create a buffer with 5 ticks"""
        buffer = LiveRingBuffer(max_size=10)
        for i in range(5):
            tick = GameTick(
                game_id="test-game",
                tick=i,
                timestamp=f"2025-11-15T10:00:{i:02d}",
                price=Decimal("1.0") + Decimal(str(i * 0.1)),
                phase="ACTIVE",
                active=True,
                rugged=False,
                cooldown_timer=0,
                trade_count=i
            )
            buffer.append(tick)
        return buffer

    def test_get_all_returns_all_ticks(self, populated_buffer):
        """Test get_all returns all ticks"""
        ticks = populated_buffer.get_all()

        assert len(ticks) == 5
        assert ticks[0].tick == 0
        assert ticks[-1].tick == 4

    def test_get_latest_with_n(self, populated_buffer):
        """Test get_latest returns last N ticks"""
        latest = populated_buffer.get_latest(3)

        assert len(latest) == 3
        assert latest[0].tick == 2
        assert latest[-1].tick == 4

    def test_get_latest_all_when_n_none(self, populated_buffer):
        """Test get_latest returns all when n=None"""
        latest = populated_buffer.get_latest(None)

        assert len(latest) == 5
        assert latest[0].tick == 0
        assert latest[-1].tick == 4

    def test_get_latest_more_than_size(self, populated_buffer):
        """Test get_latest with n > buffer size returns all"""
        latest = populated_buffer.get_latest(100)

        assert len(latest) == 5  # Only 5 ticks available

    def test_get_latest_zero_returns_empty(self, populated_buffer):
        """Test get_latest(0) returns empty list"""
        latest = populated_buffer.get_latest(0)

        assert len(latest) == 0

    def test_get_latest_negative_returns_empty(self, populated_buffer):
        """Test get_latest with negative n returns empty list"""
        latest = populated_buffer.get_latest(-5)

        assert len(latest) == 0

    def test_get_oldest_tick(self, populated_buffer):
        """Test get_oldest_tick returns first tick"""
        oldest = populated_buffer.get_oldest_tick()

        assert oldest is not None
        assert oldest.tick == 0

    def test_get_newest_tick(self, populated_buffer):
        """Test get_newest_tick returns last tick"""
        newest = populated_buffer.get_newest_tick()

        assert newest is not None
        assert newest.tick == 4

    def test_get_oldest_tick_empty_buffer(self):
        """Test get_oldest_tick on empty buffer returns None"""
        buffer = LiveRingBuffer(max_size=10)

        oldest = buffer.get_oldest_tick()

        assert oldest is None

    def test_get_newest_tick_empty_buffer(self):
        """Test get_newest_tick on empty buffer returns None"""
        buffer = LiveRingBuffer(max_size=10)

        newest = buffer.get_newest_tick()

        assert newest is None


class TestLiveRingBufferTickRange:
    """Tests for get_tick_range method"""

    @pytest.fixture
    def populated_buffer(self):
        """Create a buffer with ticks 10-19"""
        buffer = LiveRingBuffer(max_size=20)
        for i in range(10, 20):
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
            buffer.append(tick)
        return buffer

    def test_get_tick_range_returns_matching_ticks(self, populated_buffer):
        """Test get_tick_range returns ticks within range"""
        ticks = populated_buffer.get_tick_range(12, 15)

        assert len(ticks) == 4  # Ticks 12, 13, 14, 15
        assert ticks[0].tick == 12
        assert ticks[-1].tick == 15

    def test_get_tick_range_inclusive(self, populated_buffer):
        """Test get_tick_range is inclusive on both ends"""
        ticks = populated_buffer.get_tick_range(10, 10)

        assert len(ticks) == 1
        assert ticks[0].tick == 10

    def test_get_tick_range_outside_buffer(self, populated_buffer):
        """Test get_tick_range with range outside buffer"""
        ticks = populated_buffer.get_tick_range(0, 5)

        assert len(ticks) == 0

    def test_get_tick_range_partial_overlap(self, populated_buffer):
        """Test get_tick_range with partial overlap"""
        ticks = populated_buffer.get_tick_range(5, 15)

        assert len(ticks) == 6  # Ticks 10-15
        assert ticks[0].tick == 10
        assert ticks[-1].tick == 15


class TestLiveRingBufferClear:
    """Tests for clear operation"""

    def test_clear_empties_buffer(self):
        """Test clear removes all ticks"""
        buffer = LiveRingBuffer(max_size=10)

        # Add ticks
        for i in range(5):
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
            buffer.append(tick)

        assert buffer.get_size() == 5

        # Clear buffer
        buffer.clear()

        assert buffer.get_size() == 0
        assert len(buffer.get_all()) == 0
        assert buffer.get_oldest_tick() is None
        assert buffer.get_newest_tick() is None

    def test_clear_on_empty_buffer(self):
        """Test clear on empty buffer doesn't error"""
        buffer = LiveRingBuffer(max_size=10)

        buffer.clear()  # Should not raise error

        assert buffer.get_size() == 0


class TestLiveRingBufferStatus:
    """Tests for status query methods"""

    def test_is_full_false_initially(self):
        """Test is_full returns False for empty buffer"""
        buffer = LiveRingBuffer(max_size=10)

        assert not buffer.is_full()

    def test_is_full_true_when_full(self):
        """Test is_full returns True when buffer is full"""
        buffer = LiveRingBuffer(max_size=3)

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
            buffer.append(tick)

        assert buffer.is_full()

    def test_get_size_increments(self):
        """Test get_size increments correctly"""
        buffer = LiveRingBuffer(max_size=10)

        assert buffer.get_size() == 0

        for i in range(5):
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
            buffer.append(tick)
            assert buffer.get_size() == i + 1

    def test_get_size_capped_at_max(self):
        """Test get_size doesn't exceed max_size"""
        buffer = LiveRingBuffer(max_size=3)

        for i in range(10):
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
            buffer.append(tick)

        assert buffer.get_size() == 3


class TestLiveRingBufferMagicMethods:
    """Tests for magic methods (__len__, __bool__, __repr__)"""

    def test_len_returns_size(self):
        """Test len(buffer) returns size"""
        buffer = LiveRingBuffer(max_size=10)

        for i in range(5):
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
            buffer.append(tick)

        assert len(buffer) == 5

    def test_bool_false_when_empty(self):
        """Test bool(buffer) is False when empty"""
        buffer = LiveRingBuffer(max_size=10)

        assert not buffer

    def test_bool_true_when_not_empty(self):
        """Test bool(buffer) is True when not empty"""
        buffer = LiveRingBuffer(max_size=10)

        tick = GameTick(
            game_id="test-game",
            tick=0,
            timestamp="2025-11-15T10:00:00",
            price=Decimal("1.0"),
            phase="ACTIVE",
            active=True,
            rugged=False,
            cooldown_timer=0,
            trade_count=0
        )
        buffer.append(tick)

        assert buffer

    def test_repr_shows_buffer_info(self):
        """Test __repr__ shows useful debug info"""
        buffer = LiveRingBuffer(max_size=10)

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
            buffer.append(tick)

        repr_str = repr(buffer)

        assert "LiveRingBuffer" in repr_str
        assert "3/10" in repr_str
        assert "oldest_tick=0" in repr_str
        assert "newest_tick=2" in repr_str


class TestLiveRingBufferThreadSafety:
    """Tests for thread-safe operations"""

    def test_concurrent_append(self):
        """Test concurrent append from multiple threads"""
        buffer = LiveRingBuffer(max_size=1000)

        def append_ticks(start_tick, count):
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
                buffer.append(tick)

        # Launch 5 threads appending 100 ticks each
        threads = []
        for i in range(5):
            t = threading.Thread(target=append_ticks, args=(i * 100, 100))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Should have 500 ticks total
        assert buffer.get_size() == 500

    def test_concurrent_read_write(self):
        """Test concurrent reads and writes"""
        buffer = LiveRingBuffer(max_size=100)
        results = {'reads': 0, 'writes': 0}

        def write_ticks():
            for i in range(50):
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
                buffer.append(tick)
                results['writes'] += 1

        def read_ticks():
            for _ in range(50):
                buffer.get_all()
                results['reads'] += 1

        # Launch writers and readers
        writer = threading.Thread(target=write_ticks)
        reader = threading.Thread(target=read_ticks)

        writer.start()
        reader.start()

        writer.join()
        reader.join()

        # Verify both completed
        assert results['writes'] == 50
        assert results['reads'] == 50


class TestLiveRingBufferEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_single_element_buffer(self):
        """Test buffer with max_size=1"""
        buffer = LiveRingBuffer(max_size=1)

        tick1 = GameTick(
            game_id="test-game",
            tick=0,
            timestamp="2025-11-15T10:00:00",
            price=Decimal("1.0"),
            phase="ACTIVE",
            active=True,
            rugged=False,
            cooldown_timer=0,
            trade_count=0
        )
        buffer.append(tick1)

        assert buffer.is_full()
        assert buffer.get_oldest_tick() == buffer.get_newest_tick()

        # Add second tick (should evict first)
        tick2 = GameTick(
            game_id="test-game",
            tick=1,
            timestamp="2025-11-15T10:00:01",
            price=Decimal("1.0"),
            phase="ACTIVE",
            active=True,
            rugged=False,
            cooldown_timer=0,
            trade_count=0
        )
        buffer.append(tick2)

        assert buffer.get_size() == 1
        assert buffer.get_oldest_tick().tick == 1

    def test_exact_max_size_fill(self):
        """Test filling buffer to exactly max_size"""
        buffer = LiveRingBuffer(max_size=5)

        for i in range(5):
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
            buffer.append(tick)

        assert buffer.is_full()
        assert buffer.get_size() == 5
        assert buffer.get_oldest_tick().tick == 0
        assert buffer.get_newest_tick().tick == 4
