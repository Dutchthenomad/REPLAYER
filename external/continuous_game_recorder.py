#!/usr/bin/env python3
"""
Continuous Game Recorder - Background Data Collection

Records games continuously without browser or manual input.
Perfect for accumulating training data while developing other systems.

Features:
- Automatic keep-alive pinging every 4 minutes to prevent timeout
- Records each game to a separate timestamped JSONL file
- Graceful shutdown on Ctrl+C with summary statistics

Usage:
    # Record 20 games
    python scripts/continuous_game_recorder.py --games 20

    # Run indefinitely (Ctrl+C to stop)
    python scripts/continuous_game_recorder.py --continuous

    # Custom output directory
    python scripts/continuous_game_recorder.py --continuous --output-dir ~/rugs_recordings

Output:
    ~/rugs_recordings/game_YYYYMMDD_HHMMSS.jsonl (one file per game)
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import argparse
import signal
import threading
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.rugs.websocket_feed import WebSocketFeed


class ContinuousRecorder:
    """Records games continuously in background"""

    def __init__(self, output_dir: Path, max_games: int = None):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.max_games = max_games
        self.continuous = max_games is None

        # Recording state
        self.recording = True
        self.games_completed = 0
        self.current_game_id = None
        self.current_game_ticks = []
        self.current_file = None
        self.current_file_path = None

        # WebSocket feed
        self.websocket = None

        # Keep-alive mechanism (ping every 4 minutes)
        self.keep_alive_thread = None
        self.keep_alive_interval = 240  # 4 minutes in seconds
        self.last_activity = time.time()

        print()
        print('╔═══════════════════════════════════════════╗')
        print('║   Continuous Game Recorder                ║')
        print('╚═══════════════════════════════════════════╝')
        print()
        if self.continuous:
            print('Mode: CONTINUOUS (press Ctrl+C to stop)')
        else:
            print(f'Mode: Recording {max_games} games')
        print(f'Output: {self.output_dir}')
        print(f'Keep-alive: Pinging every {self.keep_alive_interval // 60} minutes')
        print()

    def start_new_game_file(self, game_id: str):
        """Start recording new game to separate file"""
        # Close previous file if exists
        if self.current_file:
            self._finish_game_file()

        # Create new file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_file_path = self.output_dir / f"game_{timestamp}.jsonl"
        self.current_file = open(self.current_file_path, 'w')
        self.current_game_ticks = []
        self.current_game_id = game_id

        # Write game metadata
        event = {
            "type": "game_start",
            "timestamp": datetime.now().isoformat(),
            "game_id": game_id
        }
        self.current_file.write(json.dumps(event) + '\n')
        self.current_file.flush()

    def write_tick(self, tick_data: dict):
        """Write tick to current game file"""
        if self.current_file:
            event = {
                "type": "tick",
                "timestamp": datetime.now().isoformat(),
                **tick_data
            }
            self.current_file.write(json.dumps(event) + '\n')
            self.current_file.flush()
            self.current_game_ticks.append(tick_data)

            # Update last activity timestamp
            self.last_activity = time.time()

    def _finish_game_file(self):
        """Finish current game file with metadata"""
        if self.current_file and self.current_game_ticks:
            # Calculate game statistics
            prices = [t['price'] for t in self.current_game_ticks]
            ticks = [t['tick'] for t in self.current_game_ticks]

            metadata = {
                "type": "game_end",
                "timestamp": datetime.now().isoformat(),
                "game_id": self.current_game_id,
                "total_ticks": len(self.current_game_ticks),
                "tick_range": [min(ticks), max(ticks)] if ticks else [0, 0],
                "price_range": [min(prices), max(prices)] if prices else [0, 0],
                "peak_price": max(prices) if prices else 0,
                "final_price": prices[-1] if prices else 0
            }

            self.current_file.write(json.dumps(metadata) + '\n')
            self.current_file.close()

            # Print summary
            file_size = self.current_file_path.stat().st_size / 1024
            print(f'   ✓ Game {self.games_completed}: '
                  f'{len(self.current_game_ticks)} ticks, '
                  f'peak {max(prices):.2f}x, '
                  f'{file_size:.1f}KB')

            self.current_file = None
            self.current_file_path = None

    def _keep_alive_worker(self):
        """Background worker that pings every 4 minutes to prevent timeout"""
        while self.recording and self.websocket and self.websocket.is_connected:
            time.sleep(self.keep_alive_interval)

            if not self.recording or not self.websocket or not self.websocket.is_connected:
                break

            # Log keep-alive ping
            elapsed = time.time() - self.last_activity
            print(f'💓 Keep-alive ping (last activity: {elapsed:.0f}s ago)')

            # Update last activity timestamp
            self.last_activity = time.time()

            # Get current metrics to keep connection active
            if self.websocket:
                try:
                    metrics = self.websocket.get_metrics()
                    print(f'   Connection status: {metrics["totalGames"]} games, {metrics["totalTicks"]} ticks')
                except Exception as e:
                    print(f'   Warning: Keep-alive check failed: {e}')

    def _start_keep_alive(self):
        """Start the keep-alive background thread"""
        if self.keep_alive_thread is None or not self.keep_alive_thread.is_alive():
            self.keep_alive_thread = threading.Thread(
                target=self._keep_alive_worker,
                daemon=True,
                name='KeepAliveThread'
            )
            self.keep_alive_thread.start()
            print('💓 Keep-alive thread started (4-minute interval)')

    def setup_websocket(self):
        """Setup WebSocket feed with event handlers"""
        self.websocket = WebSocketFeed(log_level='WARN')

        @self.websocket.on('connected')
        def on_connected(info):
            print('✅ WebSocket connected - Recording started!')
            print()
            print('🎮 Waiting for games...')
            print()
            # Start keep-alive thread
            self._start_keep_alive()

        @self.websocket.on('signal')
        def on_signal(signal):
            """Record every tick"""
            # Check if new game
            if signal.gameId != self.current_game_id:
                # If we have a current game, we'll finish it on game_complete event
                # For now, just track the new game ID
                if self.current_game_id is None:
                    # First game, start recording
                    self.start_new_game_file(signal.gameId)
                    print(f'📊 Recording Game {self.games_completed + 1}: {signal.gameId[-8:]}')

            # Write tick data
            tick_data = {
                'game_id': signal.gameId,
                'tick': signal.tickCount,
                'price': signal.price,
                'phase': signal.phase,
                'active': signal.active,
                'rugged': signal.rugged,
                'cooldown_timer': signal.cooldownTimer,
                'trade_count': signal.tradeCount
            }
            self.write_tick(tick_data)

        @self.websocket.on('gameComplete')
        def on_game_complete(data):
            signal = data['signal']
            game_number = data['gameNumber']

            # Finish current game file
            self._finish_game_file()

            self.games_completed += 1

            # Check if we should stop
            if not self.continuous and self.games_completed >= self.max_games:
                print()
                print('━' * 70)
                print(f'✅ Recording complete! Recorded {self.max_games} games')
                print(f'   Output directory: {self.output_dir}')
                print('━' * 70)
                print()
                self.recording = False
                self.websocket.disconnect()
            else:
                # Prepare for next game (will start on next signal)
                self.current_game_id = None

        # Connect
        self.websocket.connect()

    def run(self):
        """Run continuous recording"""
        try:
            # Setup and start WebSocket
            self.setup_websocket()

            # Wait for recording to complete or Ctrl+C
            while self.recording and self.websocket.is_connected:
                import time
                time.sleep(0.1)

        except KeyboardInterrupt:
            print()
            print('🛑 Stopping recording...')
        finally:
            # Finish current game if recording
            if self.current_file:
                self._finish_game_file()

            # Disconnect WebSocket
            if self.websocket:
                self.websocket.disconnect()

            print()
            print('━' * 70)
            print('📊 RECORDING SUMMARY')
            print('━' * 70)
            print(f'   Games recorded: {self.games_completed}')
            print(f'   Output directory: {self.output_dir}')

            # Count files
            game_files = list(self.output_dir.glob('game_*.jsonl'))
            total_size = sum(f.stat().st_size for f in game_files) / 1024

            print(f'   Total files: {len(game_files)}')
            print(f'   Total size: {total_size:.1f} KB')
            print('━' * 70)
            print()


def main():
    parser = argparse.ArgumentParser(description='Continuous game recorder')
    parser.add_argument('--games', type=int, default=None,
                        help='Number of games to record (default: continuous)')
    parser.add_argument('--continuous', action='store_true',
                        help='Record continuously until Ctrl+C')
    parser.add_argument('--output-dir', type=Path, default=Path.home() / 'rugs_recordings',
                        help='Output directory for recordings')

    args = parser.parse_args()

    # Determine max games
    if args.continuous:
        max_games = None
    elif args.games:
        max_games = args.games
    else:
        max_games = 10  # Default to 10 games

    recorder = ContinuousRecorder(
        output_dir=args.output_dir,
        max_games=max_games
    )

    # Setup signal handler for clean shutdown
    def signal_handler(sig, frame):
        print()
        print('🛑 Received interrupt signal')
        recorder.recording = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    recorder.run()


if __name__ == '__main__':
    main()
