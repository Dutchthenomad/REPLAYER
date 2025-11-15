#!/usr/bin/env python3
"""
Automated test for Phase 6 live feed integration
Tests: Connect -> Receive signals -> Disconnect -> Shutdown
"""

import time
import logging
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sources.websocket_feed import WebSocketFeed, GameSignal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_live_feed_connection():
    """Test live feed connection, signal reception, and clean disconnection"""

    print("="*70)
    print("Phase 6: Live Feed Automated Test")
    print("="*70)

    feed = None
    signals_received = []

    try:
        # Step 1: Create WebSocketFeed
        print("\n[1/5] Creating WebSocketFeed...")
        feed = WebSocketFeed(log_level='INFO')

        # Step 2: Register signal handler
        print("[2/5] Registering signal handler...")

        @feed.on('signal')
        def on_signal(signal):
            signals_received.append(signal)
            print(f"  📊 Signal #{len(signals_received)}: "
                  f"tick={signal.tickCount}, "
                  f"price={signal.price:.2f}x, "
                  f"phase={signal.phase}")

        # Step 3: Connect to live feed
        print("[3/5] Connecting to live feed...")
        feed.connect()
        print(f"  ✅ Connected! Socket ID: {feed.sio.sid}")

        # Step 4: Receive signals for 15 seconds
        print(f"[4/5] Receiving signals for 15 seconds...")
        start_time = time.time()

        while time.time() - start_time < 15:
            time.sleep(1)
            elapsed = int(time.time() - start_time)
            print(f"  ⏱  {elapsed}/15 seconds - {len(signals_received)} signals received", end='\r')

        print(f"\n  ✅ Received {len(signals_received)} signals in 15 seconds")

        # Step 5: Disconnect cleanly
        print("[5/5] Disconnecting...")
        feed.disconnect()
        print("  ✅ Disconnected cleanly")

        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"✅ Connection: SUCCESS")
        print(f"✅ Signals received: {len(signals_received)}")
        print(f"✅ Disconnection: SUCCESS")

        metrics = feed.get_metrics()
        print(f"\nMetrics:")
        print(f"  - Total signals: {metrics['totalSignals']}")
        print(f"  - Total ticks: {metrics['totalTicks']}")
        print(f"  - Total games: {metrics['totalGames']}")
        print(f"  - Noise filtered: {metrics['noiseFiltered']}")
        print(f"  - Avg latency: {metrics['avgLatency']}")
        print(f"  - Uptime: {metrics['uptime']}")

        if len(signals_received) > 0:
            print("\n✅ PHASE 6 TEST: PASSED")
            return True
        else:
            print("\n⚠️  PHASE 6 TEST: WARNING - No signals received")
            return False

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        return False

    except Exception as e:
        print(f"\n\n❌ TEST FAILED: {e}")
        logger.error(f"Test failed: {e}", exc_info=True)
        return False

    finally:
        # Cleanup
        if feed and feed.is_connected:
            print("\nCleaning up...")
            feed.disconnect()
            print("  ✅ Cleanup complete")


if __name__ == '__main__':
    success = test_live_feed_connection()
    sys.exit(0 if success else 1)
