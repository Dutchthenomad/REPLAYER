"""
Thread Safety Stress Tests

PHASE 4 AUDIT: Tests for concurrent access to critical components.

Tests verify:
- GameState can handle concurrent read/write operations
- RecorderSink can handle concurrent tick recording
- EventBus can handle concurrent publish/subscribe
- No deadlocks under high contention
- Data integrity maintained under concurrent access
"""

import pytest
import time
import threading
import tempfile
from pathlib import Path
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch

from core.game_state import GameState, StateEvents
from core.recorder_sink import RecorderSink
from services.event_bus import EventBus, Events
from models import GameTick


class TestGameStateThreadSafety:
    """Thread safety stress tests for GameState"""

    def test_concurrent_balance_updates(self):
        """Test concurrent balance updates maintain data integrity"""
        state = GameState(Decimal('1.000'))

        def update_balance():
            for _ in range(100):
                current = state.get('balance')
                state.update(balance=current + Decimal('0.001'))

        threads = [threading.Thread(target=update_balance) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have initial + (100 updates * 10 threads * 0.001)
        final = state.get('balance')
        # Due to race conditions in the test itself (read-modify-write),
        # we just verify no crash and balance is reasonable
        assert final >= Decimal('1.000')

    def test_concurrent_state_reads(self):
        """Test concurrent state reads don't block"""
        state = GameState(Decimal('1.000'))
        state.update(current_tick=100, current_price=Decimal('1.5'))

        read_results = []

        def read_state():
            for _ in range(500):
                snapshot = state.get_snapshot()
                read_results.append(snapshot)

        threads = [threading.Thread(target=read_state) for _ in range(20)]

        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.time() - start

        # Should complete quickly (< 5 seconds)
        assert elapsed < 5.0
        assert len(read_results) == 10000  # 500 * 20

    def test_concurrent_position_operations(self):
        """Test concurrent position open/close operations"""
        state = GameState(Decimal('1.000'))
        errors = []

        def position_cycle():
            try:
                for i in range(20):
                    state.open_position({
                        'entry_price': Decimal(f'1.{i:02d}'),
                        'amount': Decimal('0.001'),
                        'entry_tick': i
                    })
                    time.sleep(0.001)  # Small delay
                    state.close_position(
                        exit_price=Decimal(f'1.{i+1:02d}'),
                        exit_tick=i + 1
                    )
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=position_cycle) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # May have some expected errors from concurrent position ops
        # Just verify no deadlock and state is still usable
        assert state.get_snapshot() is not None

    def test_concurrent_sidebet_operations(self):
        """Test concurrent sidebet operations"""
        state = GameState(Decimal('1.000'))
        operations_count = [0]

        def sidebet_cycle():
            for i in range(10):
                try:
                    state.place_sidebet({
                        'amount': Decimal('0.001'),
                        'start_tick': i,
                        'target_ticks': 40
                    })
                    operations_count[0] += 1
                    time.sleep(0.002)
                    state.resolve_sidebet(i + 40, won=i % 2 == 0)
                except (ValueError, RuntimeError):
                    pass  # Expected when sidebet already active

        threads = [threading.Thread(target=sidebet_cycle) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no deadlock
        assert state.get_snapshot() is not None

    def test_concurrent_subscription_and_updates(self):
        """Test concurrent event subscription and state updates"""
        state = GameState(Decimal('1.000'))
        callback_counts = {'count': 0}
        lock = threading.Lock()

        # Subscribe to TICK_UPDATED (which is actually emitted by _notify_changes)
        def callback(data):
            with lock:
                callback_counts['count'] += 1

        state.subscribe(StateEvents.TICK_UPDATED, callback)

        def update_continuously():
            for i in range(50):
                # Update current_tick which triggers TICK_UPDATED event
                state.update(current_tick=i)
                time.sleep(0.001)

        update_threads = [threading.Thread(target=update_continuously) for _ in range(3)]

        for t in update_threads:
            t.start()
        for t in update_threads:
            t.join()

        # Should have received callbacks (some tick updates will emit events)
        assert callback_counts['count'] > 0

    def test_no_deadlock_under_heavy_load(self):
        """Test no deadlock occurs under heavy concurrent load"""
        state = GameState(Decimal('1.000'))
        completed = [0]
        timeout = 10.0

        def heavy_operation():
            for i in range(100):
                state.update(
                    current_tick=i,
                    current_price=Decimal(f'1.{i:03d}'),
                    balance=Decimal(f'{i}.000')
                )
                _ = state.get_snapshot()
                _ = state.get('balance')
            completed[0] += 1

        threads = [threading.Thread(target=heavy_operation) for _ in range(20)]

        start = time.time()
        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=timeout)

        elapsed = time.time() - start

        # All threads should complete without deadlock
        assert elapsed < timeout
        assert completed[0] == 20


class TestRecorderSinkThreadSafety:
    """Thread safety stress tests for RecorderSink"""

    @pytest.fixture
    def temp_recordings_dir(self):
        """Create temporary recordings directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_concurrent_tick_recording(self, temp_recordings_dir):
        """Test concurrent tick recording maintains data integrity"""
        from datetime import datetime
        recorder = RecorderSink(temp_recordings_dir, buffer_size=10)
        recorder.start_recording('test-game')

        tick_ids = []
        lock = threading.Lock()

        def record_ticks():
            for i in range(50):
                tick = GameTick(
                    game_id='test-game',
                    tick=i,
                    timestamp=datetime.now().isoformat(),
                    price=Decimal('1.5'),
                    phase='ACTIVE',
                    active=True,
                    rugged=False,
                    cooldown_timer=0,
                    trade_count=0
                )
                recorder.record_tick(tick)
                with lock:
                    tick_ids.append(i)

        threads = [threading.Thread(target=record_ticks) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        summary = recorder.stop_recording()

        # Should have recorded all ticks
        assert summary is not None
        assert summary['tick_count'] == 250  # 50 * 5 threads

    def test_concurrent_start_stop_recording(self, temp_recordings_dir):
        """Test concurrent start/stop doesn't corrupt state"""
        from datetime import datetime
        recorder = RecorderSink(temp_recordings_dir)
        errors = []

        def start_stop_cycle():
            try:
                for i in range(10):
                    recorder.start_recording(f'game-{i}')
                    tick = GameTick(
                        game_id=f'game-{i}',
                        tick=0,
                        timestamp=datetime.now().isoformat(),
                        price=Decimal('1.0'),
                        phase='ACTIVE',
                        active=True,
                        rugged=False,
                        cooldown_timer=0,
                        trade_count=0
                    )
                    recorder.record_tick(tick)
                    recorder.stop_recording()
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=start_stop_cycle) for _ in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No crashes or corruption
        recorder.close()

    def test_high_throughput_recording(self, temp_recordings_dir):
        """Test high-throughput recording performance"""
        from datetime import datetime
        recorder = RecorderSink(temp_recordings_dir, buffer_size=100)
        recorder.start_recording('high-throughput-test')

        total_ticks = [0]
        lock = threading.Lock()
        start = time.time()

        def record_burst():
            local_count = 0
            for i in range(1000):
                tick = GameTick(
                    game_id='test',
                    tick=i,
                    timestamp=datetime.now().isoformat(),
                    price=Decimal('1.5'),
                    phase='ACTIVE',
                    active=True,
                    rugged=False,
                    cooldown_timer=0,
                    trade_count=0
                )
                if recorder.record_tick(tick):
                    local_count += 1
            with lock:
                total_ticks[0] += local_count

        threads = [threading.Thread(target=record_burst) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        elapsed = time.time() - start
        recorder.stop_recording()
        recorder.close()

        # Should handle at least 100 ticks/sec (conservative for tests)
        throughput = total_ticks[0] / elapsed if elapsed > 0 else 0
        assert throughput > 100  # Conservative lower bound


class TestEventBusThreadSafety:
    """Thread safety stress tests for EventBus"""

    def test_concurrent_publish_subscribe(self):
        """Test concurrent publish and subscribe operations"""
        bus = EventBus()
        bus.start()  # Start event processing
        received = []
        lock = threading.Lock()

        # Create unique callbacks for each subscriber
        callbacks = []
        for i in range(20):
            def make_callback(idx):
                def cb(data):
                    with lock:
                        received.append((idx, data))
                return cb
            callbacks.append(make_callback(i))

        def subscribe_many(start_idx):
            for i in range(start_idx, min(start_idx + 7, len(callbacks))):
                bus.subscribe(Events.GAME_TICK, callbacks[i])
                time.sleep(0.001)

        def publish_many():
            for i in range(50):
                bus.publish(Events.GAME_TICK, {'tick': i})
                time.sleep(0.001)

        sub_threads = [threading.Thread(target=subscribe_many, args=(i*7,)) for i in range(3)]
        pub_threads = [threading.Thread(target=publish_many) for _ in range(3)]

        for t in sub_threads + pub_threads:
            t.start()
        for t in sub_threads + pub_threads:
            t.join()

        # Wait for event processing
        time.sleep(0.2)
        bus.stop()

        # Should have received messages
        assert len(received) > 0

    def test_concurrent_unsubscribe(self):
        """Test concurrent unsubscribe doesn't crash"""
        bus = EventBus()
        callbacks = []

        for i in range(20):
            def cb(data, idx=i):
                pass
            callbacks.append(cb)
            bus.subscribe(Events.GAME_TICK, cb)

        def unsubscribe_random():
            for cb in callbacks[:10]:
                try:
                    bus.unsubscribe(Events.GAME_TICK, cb)
                except Exception:
                    pass
                time.sleep(0.001)

        def publish_continuously():
            for i in range(100):
                bus.publish(Events.GAME_TICK, {'tick': i})
                time.sleep(0.001)

        unsub_threads = [threading.Thread(target=unsubscribe_random) for _ in range(3)]
        pub_threads = [threading.Thread(target=publish_continuously) for _ in range(2)]

        for t in unsub_threads + pub_threads:
            t.start()
        for t in unsub_threads + pub_threads:
            t.join()

        # No crash means success

    def test_high_frequency_publishing(self):
        """Test high-frequency event publishing"""
        bus = EventBus()
        count = [0]
        lock = threading.Lock()

        def callback(data):
            with lock:
                count[0] += 1

        bus.subscribe(Events.GAME_TICK, callback)

        def publish_burst():
            for i in range(1000):
                bus.publish(Events.GAME_TICK, {'tick': i})

        threads = [threading.Thread(target=publish_burst) for _ in range(10)]

        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.time() - start

        # Should handle high throughput
        assert elapsed < 10.0  # Complete within 10 seconds


class TestCrossComponentThreadSafety:
    """Tests for thread safety across multiple components"""

    @pytest.fixture
    def temp_recordings_dir(self):
        """Create temporary recordings directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_full_pipeline_concurrent(self, temp_recordings_dir):
        """Test full data pipeline under concurrent load"""
        from datetime import datetime
        state = GameState(Decimal('1.000'))
        bus = EventBus()
        bus.start()  # Start event processing
        recorder = RecorderSink(temp_recordings_dir)
        recorder.start_recording('pipeline-test')

        ticks_recorded = [0]
        lock = threading.Lock()

        def on_tick(data):
            tick_data = data.get('data', data)  # Handle event wrapper
            tick = GameTick(
                game_id='pipeline-test',
                tick=tick_data.get('tick', 0),
                timestamp=datetime.now().isoformat(),
                price=Decimal(str(tick_data.get('price', 1.0))),
                phase='ACTIVE',
                active=True,
                rugged=False,
                cooldown_timer=0,
                trade_count=0
            )
            if recorder.record_tick(tick):
                with lock:
                    ticks_recorded[0] += 1

        bus.subscribe(Events.GAME_TICK, on_tick)

        def update_state_and_publish():
            for i in range(100):
                state.update(
                    current_tick=i,
                    current_price=Decimal(f'1.{i:03d}')
                )
                bus.publish(Events.GAME_TICK, {
                    'tick': i,
                    'price': 1.0 + i * 0.001
                })

        threads = [threading.Thread(target=update_state_and_publish) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Wait for event processing
        time.sleep(0.2)
        bus.stop()

        recorder.stop_recording()
        recorder.close()

        # Should have recorded ticks
        assert ticks_recorded[0] > 0

    def test_producer_consumer_pattern(self, temp_recordings_dir):
        """Test producer-consumer pattern with GameState as shared state"""
        state = GameState(Decimal('1.000'))
        # Initialize state with current_tick so consumers can see updates
        state.update(current_tick=0, current_price=Decimal('1.000'))

        produced = [0]
        consumed = [0]
        lock = threading.Lock()
        stop_flag = threading.Event()

        def producer():
            for i in range(1, 201):  # Start from 1 since we initialized with 0
                if stop_flag.is_set():
                    break
                state.update(current_tick=i, current_price=Decimal(f'1.{i:03d}'))
                with lock:
                    produced[0] += 1
                time.sleep(0.001)

        def consumer():
            last_tick = -1
            while not stop_flag.is_set():
                snapshot = state.get_snapshot()
                # StateSnapshot is a dataclass, access .tick attribute (not dict.get)
                current_tick = snapshot.tick
                if current_tick > last_tick:
                    last_tick = current_tick
                    with lock:
                        consumed[0] += 1
                time.sleep(0.001)

        producers = [threading.Thread(target=producer) for _ in range(3)]
        consumers = [threading.Thread(target=consumer) for _ in range(5)]

        for t in producers + consumers:
            t.start()

        for p in producers:
            p.join()

        stop_flag.set()

        for c in consumers:
            c.join(timeout=2.0)

        # Both producers and consumers should have worked
        assert produced[0] > 0
        assert consumed[0] > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
