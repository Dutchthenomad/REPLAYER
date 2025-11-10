#!/usr/bin/env python3
"""Debug volatility analysis to find the issue"""

import json
from pathlib import Path

# Test one game file
game_file = Path("/home/nomad/rugs_recordings_normalized/games/game_20251030_131703_bca24d88.jsonl")

ticks = []
with open(game_file, 'r') as f:
    for line in f:
        if line.strip():
            try:
                data = json.loads(line)
                if data.get('type') == 'tick':
                    ticks.append(data)
            except:
                pass

print(f"Game: {game_file.name}")
print(f"Total ticks: {len(ticks)}")
print()

# Check first few ticks
print("First 5 ticks:")
for i, tick in enumerate(ticks[:5]):
    print(f"  Tick {i}: price={tick.get('price')}, rugged={tick.get('rugged')}, active={tick.get('active')}")

print()
print("Last 5 ticks:")
for i, tick in enumerate(ticks[-5:], len(ticks)-5):
    print(f"  Tick {i}: price={tick.get('price')}, rugged={tick.get('rugged')}, active={tick.get('active')}")

# Extract prices
prices = [tick.get('price', 1.0) for tick in ticks]
print()
print(f"Price range: {min(prices):.2f} to {max(prices):.2f}")
print(f"First 10 prices: {prices[:10]}")
print(f"Last 10 prices: {prices[-10:]}")

# Check baseline volatility
baseline_prices = prices[:40]
print()
print(f"Baseline window (first 40 ticks): {len(baseline_prices)} prices")
print(f"Baseline price range: {min(baseline_prices):.4f} to {max(baseline_prices):.4f}")

# Calculate changes
changes = []
for i in range(1, len(baseline_prices)):
    if baseline_prices[i-1] > 0:
        change = abs(baseline_prices[i] - baseline_prices[i-1]) / baseline_prices[i-1]
        changes.append(change)

import numpy as np
baseline_vol = np.mean(changes) if changes else 0.0
print(f"Baseline volatility: {baseline_vol:.6f}")
print(f"Number of changes: {len(changes)}")

# Current volatility
current_prices = prices[-10:]
print()
print(f"Current window (last 10 ticks): {len(current_prices)} prices")
print(f"Current price range: {min(current_prices):.4f} to {max(current_prices):.4f}")

changes_current = []
for i in range(1, len(current_prices)):
    if current_prices[i-1] > 0:
        change = abs(current_prices[i] - current_prices[i-1]) / current_prices[i-1]
        changes_current.append(change)

current_vol = np.mean(changes_current) if changes_current else 0.0
print(f"Current volatility: {current_vol:.6f}")
print(f"Number of changes: {len(changes_current)}")

if baseline_vol > 0:
    ratio = current_vol / baseline_vol
    print()
    print(f"Volatility ratio: {ratio:.2f}x")
else:
    print()
    print("Baseline volatility is 0 - cannot calculate ratio!")
