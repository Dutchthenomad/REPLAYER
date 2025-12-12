#!/usr/bin/env python3
"""
Raw Capture Analysis Tool

Analyzes JSONL files created by RawCaptureRecorder to document
WebSocket protocol events.

Usage:
    # List event types with counts
    python analyze_raw_capture.py session.jsonl --summary

    # Extract specific event type
    python analyze_raw_capture.py session.jsonl --extract usernameStatus

    # Show events in sequence range
    python analyze_raw_capture.py session.jsonl --range 1-50

    # Generate full report
    python analyze_raw_capture.py session.jsonl --report
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict


def load_capture(filepath: Path) -> List[Dict[str, Any]]:
    """Load all events from a JSONL capture file."""
    events = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Warning: Skipping malformed line: {e}", file=sys.stderr)
    return events


def summary(events: List[Dict[str, Any]]) -> None:
    """Print summary of event types with counts."""
    counts: Dict[str, int] = defaultdict(int)
    first_ts = None
    last_ts = None

    for event in events:
        event_name = event.get('event', 'unknown')
        counts[event_name] += 1

        ts = event.get('ts')
        if ts:
            if first_ts is None:
                first_ts = ts
            last_ts = ts

    print("=" * 60)
    print("RAW CAPTURE SUMMARY")
    print("=" * 60)
    print(f"Total events: {len(events)}")
    print(f"Unique event types: {len(counts)}")
    if first_ts and last_ts:
        print(f"Time range: {first_ts} to {last_ts}")
    print()
    print("Event Counts:")
    print("-" * 40)

    # Sort by count descending
    for event_name, count in sorted(counts.items(), key=lambda x: -x[1]):
        pct = (count / len(events)) * 100 if events else 0
        print(f"  {event_name:30s} {count:6d} ({pct:5.1f}%)")

    print("=" * 60)


def extract(events: List[Dict[str, Any]], event_type: str, pretty: bool = True) -> None:
    """Extract and print all events of a specific type."""
    matching = [e for e in events if e.get('event') == event_type]

    print(f"Found {len(matching)} '{event_type}' events:")
    print("-" * 60)

    for event in matching:
        if pretty:
            print(f"\n[seq={event.get('seq')}] {event.get('ts')}")
            print(json.dumps(event.get('data'), indent=2, default=str))
        else:
            print(json.dumps(event, default=str))

    print("-" * 60)


def show_range(events: List[Dict[str, Any]], start: int, end: int, pretty: bool = True) -> None:
    """Show events within a sequence range."""
    matching = [e for e in events if start <= e.get('seq', 0) <= end]

    print(f"Events {start}-{end} ({len(matching)} found):")
    print("-" * 60)

    for event in matching:
        seq = event.get('seq')
        ts = event.get('ts')
        event_name = event.get('event')
        data = event.get('data')

        print(f"\n[{seq}] {ts} - {event_name}")
        if data and pretty:
            print(json.dumps(data, indent=2, default=str))

    print("-" * 60)


def _collect_event_stats(
    events: List[Dict[str, Any]]
) -> Tuple[Dict[str, int], Dict[str, Any], Optional[str], Optional[str]]:
    """Collect event counts, samples, and time range from events."""
    counts: Dict[str, int] = defaultdict(int)
    samples: Dict[str, Any] = {}
    first_ts, last_ts = None, None

    for event in events:
        event_name = event.get('event', 'unknown')
        counts[event_name] += 1
        if event_name not in samples:
            samples[event_name] = event.get('data')
        if ts := event.get('ts'):
            first_ts = first_ts or ts
            last_ts = ts

    return counts, samples, first_ts, last_ts


def generate_report(events: List[Dict[str, Any]], output_base: Path) -> None:  # pylint: disable=too-many-locals
    """Generate summary.md and events.json reports."""
    counts, samples, first_ts, last_ts = _collect_event_stats(events)
    base_stem = output_base.stem.replace('_raw', '')

    # Generate summary.md
    summary_file = output_base.parent / f'{base_stem}_summary.md'
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("# Raw Capture Summary\n\n")
        f.write(f"**Generated**: {datetime.now().isoformat()}\n")
        f.write(f"**Source**: {output_base.name}\n\n")
        f.write("## Statistics\n\n")
        f.write(f"- Total events: {len(events)}\n")
        f.write(f"- Unique event types: {len(counts)}\n")
        f.write(f"- Time range: {first_ts} to {last_ts}\n\n")
        f.write("## Event Counts\n\n")
        f.write("| Event Type | Count | Percentage |\n")
        f.write("|------------|-------|------------|\n")
        for name, count in sorted(counts.items(), key=lambda x: -x[1]):
            pct = (count / len(events)) * 100 if events else 0
            f.write(f"| {name} | {count} | {pct:.1f}% |\n")
        f.write("\n## Event Timeline\n\n")
        f.write("First 20 events:\n\n```\n")
        for event in events[:20]:
            ts_str = event.get('ts', '').split('T')[1][:12] if event.get('ts') else ''
            f.write(f"[{event.get('seq'):3d}] {ts_str} {event.get('event')}\n")
        f.write("```\n")
    print(f"Generated: {summary_file}")

    # Generate events.json
    events_file = output_base.parent / f'{base_stem}_events.json'
    event_types = {
        name: {
            'count': counts[name],
            'percentage': round((counts[name] / len(events)) * 100, 1),
            'sample_payload': samples.get(name)
        }
        for name in sorted(counts.keys())
    }
    inventory: Dict[str, Any] = {
        'generated': datetime.now().isoformat(),
        'source': str(output_base),
        'total_events': len(events),
        'event_types': event_types
    }
    with open(events_file, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=2, default=str)
    print(f"Generated: {events_file}")


def main() -> None:
    """Parse arguments and run the requested analysis."""
    parser = argparse.ArgumentParser(
        description='Analyze raw WebSocket capture files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s capture.jsonl --summary
    %(prog)s capture.jsonl --extract gameStateUpdate
    %(prog)s capture.jsonl --range 1-50
    %(prog)s capture.jsonl --report
        """
    )

    parser.add_argument(
        'capture_file',
        type=Path,
        help='Path to JSONL capture file'
    )

    parser.add_argument(
        '--summary', '-s',
        action='store_true',
        help='Show event type summary with counts'
    )

    parser.add_argument(
        '--extract', '-e',
        type=str,
        metavar='EVENT',
        help='Extract all events of a specific type'
    )

    parser.add_argument(
        '--range', '-r',
        type=str,
        metavar='N-M',
        help='Show events in sequence range (e.g., 1-50)'
    )

    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate summary.md and events.json reports'
    )

    parser.add_argument(
        '--compact',
        action='store_true',
        help='Output compact JSON (no pretty-printing)'
    )

    args = parser.parse_args()

    # Validate file exists
    if not args.capture_file.exists():
        print(f"Error: File not found: {args.capture_file}", file=sys.stderr)
        sys.exit(1)

    # Load events
    print(f"Loading {args.capture_file}...")
    events = load_capture(args.capture_file)
    print(f"Loaded {len(events)} events\n")

    # Execute requested action(s)
    if args.summary:
        summary(events)

    if args.extract:
        extract(events, args.extract, pretty=not args.compact)

    if args.range:
        try:
            start, end = map(int, args.range.split('-'))
            show_range(events, start, end, pretty=not args.compact)
        except ValueError:
            print(f"Error: Invalid range '{args.range}'. Use N-M (e.g., 1-50)", file=sys.stderr)
            sys.exit(1)

    if args.report:
        generate_report(events, args.capture_file)

    # Default to summary if no action specified
    if not any([args.summary, args.extract, args.range, args.report]):
        summary(events)


if __name__ == '__main__':
    main()
