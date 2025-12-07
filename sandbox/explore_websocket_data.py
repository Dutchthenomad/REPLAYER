#!/usr/bin/env python3
"""
WebSocket Data Explorer - Phase 10.4 Sandbox

Purpose: Discover ALL data fields being broadcast by rugs.fun Socket.IO
         to identify high-value data points we're currently ignoring.

Usage:
    python3 sandbox/explore_websocket_data.py

Output:
    - sandbox/websocket_raw_samples.jsonl (raw data samples)
    - sandbox/field_analysis.json (field frequency/types)
    - Console output with field discovery
"""

import socketio
import json
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, Set

# Output directory
OUTPUT_DIR = Path(__file__).parent
OUTPUT_DIR.mkdir(exist_ok=True)

# Files
RAW_SAMPLES_FILE = OUTPUT_DIR / "websocket_raw_samples.jsonl"
FIELD_ANALYSIS_FILE = OUTPUT_DIR / "field_analysis.json"

# Currently captured fields (from websocket_feed.py _extract_signal)
CURRENTLY_CAPTURED = {
    'gameId', 'active', 'rugged', 'tickCount', 'price',
    'cooldownTimer', 'allowPreRoundBuys', 'tradeCount', 'gameHistory'
}


class WebSocketExplorer:
    """Explores raw WebSocket data to find ignored fields"""

    def __init__(self, max_samples: int = 100, duration_sec: int = 60):
        self.max_samples = max_samples
        self.duration_sec = duration_sec

        self.sio = socketio.Client(logger=False, engineio_logger=False)
        self.server_url = 'https://backend.rugs.fun?frontend-version=1.0'

        # Data collection
        self.samples = []
        self.all_fields: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'count': 0,
            'types': set(),
            'sample_values': [],
            'nested_fields': set()
        })
        self.event_types: Dict[str, int] = defaultdict(int)

        # State
        self.start_time = None
        self.running = True

        self._setup_handlers()

    def _setup_handlers(self):
        """Setup Socket.IO handlers to capture ALL data"""

        @self.sio.event
        def connect():
            print(f"✅ Connected to {self.server_url}")
            print(f"   Collecting {self.max_samples} samples over {self.duration_sec}s...")
            print()

        @self.sio.event
        def disconnect():
            print("❌ Disconnected")
            self.running = False

        @self.sio.on('gameStateUpdate')
        def on_game_state_update(data):
            self._record_sample('gameStateUpdate', data)

        # Catch ALL events to see what else is being broadcast
        @self.sio.on('*')
        def catch_all(event, *args):
            if event != 'gameStateUpdate':
                self.event_types[event] += 1
                if args:
                    self._record_sample(event, args[0] if len(args) == 1 else args)

    def _record_sample(self, event_type: str, data: Any):
        """Record a raw data sample and analyze its structure"""
        if len(self.samples) >= self.max_samples:
            return

        timestamp = datetime.now().isoformat()
        sample = {
            'timestamp': timestamp,
            'event_type': event_type,
            'data': data
        }
        self.samples.append(sample)

        # Analyze fields
        if isinstance(data, dict):
            self._analyze_dict(data, prefix='')

        # Progress indicator
        if len(self.samples) % 10 == 0:
            print(f"   Collected {len(self.samples)}/{self.max_samples} samples...")

    def _analyze_dict(self, d: Dict, prefix: str = ''):
        """Recursively analyze dict structure"""
        for key, value in d.items():
            full_key = f"{prefix}.{key}" if prefix else key
            field_info = self.all_fields[full_key]

            field_info['count'] += 1
            field_info['types'].add(type(value).__name__)

            # Store sample values (up to 5)
            if len(field_info['sample_values']) < 5:
                # Truncate large values
                if isinstance(value, (list, dict)):
                    sample_val = f"<{type(value).__name__} len={len(value)}>"
                elif isinstance(value, str) and len(value) > 100:
                    sample_val = value[:100] + "..."
                else:
                    sample_val = value
                field_info['sample_values'].append(sample_val)

            # Recurse into nested dicts
            if isinstance(value, dict):
                self._analyze_dict(value, prefix=full_key)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # Analyze first item of list of dicts
                self._analyze_dict(value[0], prefix=f"{full_key}[0]")

    def run(self):
        """Run the exploration"""
        print("=" * 60)
        print("🔍 WebSocket Data Explorer - Phase 10.4 Sandbox")
        print("=" * 60)
        print()

        self.start_time = time.time()

        try:
            self.sio.connect(
                self.server_url,
                transports=['websocket', 'polling'],
                wait_timeout=20
            )

            # Run until we have enough samples or timeout
            while self.running:
                elapsed = time.time() - self.start_time
                if elapsed >= self.duration_sec:
                    print(f"\n⏱️ Duration limit reached ({self.duration_sec}s)")
                    break
                if len(self.samples) >= self.max_samples:
                    print(f"\n📊 Sample limit reached ({self.max_samples})")
                    break
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        finally:
            self.sio.disconnect()

        self._save_results()
        self._print_analysis()

    def _save_results(self):
        """Save raw samples and analysis"""
        # Save raw samples
        with open(RAW_SAMPLES_FILE, 'w') as f:
            for sample in self.samples:
                f.write(json.dumps(sample, default=str) + '\n')
        print(f"\n💾 Saved {len(self.samples)} raw samples to {RAW_SAMPLES_FILE}")

        # Save field analysis
        analysis = {
            'collection_time': datetime.now().isoformat(),
            'samples_collected': len(self.samples),
            'duration_sec': time.time() - self.start_time,
            'event_types': dict(self.event_types),
            'fields': {}
        }

        for field, info in self.all_fields.items():
            analysis['fields'][field] = {
                'count': info['count'],
                'types': list(info['types']),
                'sample_values': info['sample_values'][:3],
                'is_captured': field.split('.')[0] in CURRENTLY_CAPTURED
            }

        with open(FIELD_ANALYSIS_FILE, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"💾 Saved field analysis to {FIELD_ANALYSIS_FILE}")

    def _print_analysis(self):
        """Print analysis summary"""
        print()
        print("=" * 60)
        print("📊 FIELD ANALYSIS")
        print("=" * 60)

        # Categorize fields
        captured = []
        ignored = []

        for field, info in sorted(self.all_fields.items()):
            root_field = field.split('.')[0].split('[')[0]
            is_captured = root_field in CURRENTLY_CAPTURED

            entry = {
                'field': field,
                'count': info['count'],
                'types': list(info['types']),
                'sample': info['sample_values'][0] if info['sample_values'] else None
            }

            if is_captured:
                captured.append(entry)
            else:
                ignored.append(entry)

        print()
        print(f"✅ CURRENTLY CAPTURED ({len(captured)} fields):")
        print("-" * 40)
        for entry in captured[:20]:  # Limit output
            sample_str = str(entry['sample'])[:30] if entry['sample'] else ''
            print(f"   {entry['field']}: {entry['types']} ({entry['count']}x) → {sample_str}")

        print()
        print(f"❌ CURRENTLY IGNORED ({len(ignored)} fields):")
        print("-" * 40)
        for entry in ignored:
            sample_str = str(entry['sample'])[:40] if entry['sample'] else ''
            print(f"   {entry['field']}: {entry['types']} ({entry['count']}x) → {sample_str}")

        print()
        print("=" * 60)
        print("🎯 HIGH-VALUE CANDIDATES FOR INTEGRATION:")
        print("=" * 60)

        # Identify high-value fields we're missing
        high_value_keywords = [
            'pnl', 'profit', 'loss', 'balance', 'position',
            'entry', 'exit', 'trade', 'order', 'bet', 'side',
            'latency', 'timestamp', 'server', 'client',
            'wallet', 'address', 'user', 'player',
            'volume', 'liquidity', 'pool', 'token'
        ]

        high_value = []
        for entry in ignored:
            field_lower = entry['field'].lower()
            for keyword in high_value_keywords:
                if keyword in field_lower:
                    high_value.append(entry)
                    break

        if high_value:
            for entry in high_value:
                print(f"   ⭐ {entry['field']}: {entry['types']}")
                print(f"      Sample: {entry['sample']}")
                print()
        else:
            print("   (No obvious high-value fields found in ignored data)")
            print("   Review sandbox/field_analysis.json for full details")

        print()
        print(f"📋 Other events received: {dict(self.event_types)}")


if __name__ == '__main__':
    explorer = WebSocketExplorer(max_samples=200, duration_sec=120)
    explorer.run()
