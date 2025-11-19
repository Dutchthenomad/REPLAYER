#!/usr/bin/env python3
"""
Interactive Demo: Bot Incremental Button Clicking

Phase A.5: Visual demonstration that the bot clicks UI buttons like a human player.

This script launches the REPLAYER UI and demonstrates the bot clicking
increment buttons to build bet amounts, exactly as a human would.

Usage:
    cd /home/nomad/Desktop/REPLAYER/src
    /home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3 demo_incremental_clicking.py
"""

import tkinter as tk
import time
import logging
from decimal import Decimal
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_demo():
    """
    Run interactive demo of incremental button clicking

    Demonstrates:
    1. Building 0.003 SOL by clicking +0.001 button 3 times
    2. Building 0.015 SOL by clicking +0.01 once and +0.001 five times
    3. Building 1.234 SOL by clicking +1, +0.1, +0.01, +0.001 buttons
    4. Clearing with X button
    5. Using 1/2 and X2 buttons
    """

    print("\n" + "="*70)
    print("  INCREMENTAL BUTTON CLICKING DEMO - Phase A.5")
    print("="*70)
    print("\nThis demo shows the bot clicking UI buttons like a human player.")
    print("The bot will build bet amounts by clicking increment buttons,")
    print("NOT by directly typing into the text field.")
    print("\n" + "="*70 + "\n")

    # Import after setup
    from bot.ui_controller import BotUIController
    from ui.main_window import MainWindow
    from core.game_state import GameState
    from config import config

    # Create minimal UI for demo
    root = tk.Tk()
    root.title("Incremental Clicking Demo - Phase A.5")
    root.geometry("800x600")

    print("✓ Creating UI window...")

    # Create event bus
    from services.event_bus import EventBus
    event_bus = EventBus()

    # Create game state (no config argument needed)
    game_state = GameState()

    # Create main window
    main_window = MainWindow(root, state=game_state, event_bus=event_bus, config=config)

    print("✓ UI initialized")
    print("✓ BotUIController ready")

    # Get bot UI controller from main window
    bot_ui = main_window.bot_ui_controller

    # Phase A.7: Override timing for slow demo mode (visibility)
    bot_ui.button_depress_duration_ms = 50   # Keep visual feedback at 50ms
    bot_ui.inter_click_pause_ms = 500        # Slow 500ms pauses for visibility

    print("✓ Demo timing configured (500ms pauses for visibility)")
    print("\nStarting demo sequence in 2 seconds...\n")

    # Demo sequence - showcasing smart algorithm
    demo_steps = [
        {
            'description': "Demo 1: Build 0.003 SOL (standard)",
            'detail': "Bot clicks: X → +0.001 (3x) [4 clicks total]",
            'amount': Decimal('0.003'),
            'delay': 3.0
        },
        {
            'description': "Demo 2: Build 0.005 SOL (optimized with 1/2)",
            'detail': "Bot clicks: X → +0.01 → 1/2 [3 clicks vs 5 clicks!]",
            'amount': Decimal('0.005'),
            'delay': 3.0
        },
        {
            'description': "Demo 3: Build 0.012 SOL (optimized with X2)",
            'detail': "Bot clicks: X → +0.01 → 1/2 → +0.001 → X2 [5 clicks vs 12 clicks!]",
            'amount': Decimal('0.012'),
            'delay': 4.0
        },
        {
            'description': "Demo 4: Build 0.050 SOL (optimized with 1/2)",
            'detail': "Bot clicks: X → +0.1 → 1/2 [3 clicks vs 5 clicks!]",
            'amount': Decimal('0.050'),
            'delay': 3.0
        },
        {
            'description': "Demo 5: Build 0.015 SOL (standard)",
            'detail': "Bot clicks: X → +0.01 → +0.001 (5x) [7 clicks - no optimization]",
            'amount': Decimal('0.015'),
            'delay': 5.0
        },
        {
            'description': "Demo 6: Build 1.234 SOL (standard)",
            'detail': "Bot clicks: X → +1 → +0.1 (2x) → +0.01 (3x) → +0.001 (4x)",
            'amount': Decimal('1.234'),
            'delay': 6.0
        },
        {
            'description': "Demo 7: Clear to 0.0",
            'detail': "Bot clicks: X",
            'amount': Decimal('0.0'),
            'delay': 2.0
        },
    ]

    def run_demo_step(step_index):
        """Run a single demo step"""
        if step_index >= len(demo_steps):
            print("\n" + "="*70)
            print("  DEMO COMPLETE!")
            print("="*70)
            print("\nAll button clicking sequences demonstrated successfully.")
            print("The bot clicks buttons exactly like a human player would.")
            print("\nYou can now close this window or continue testing manually.")
            return

        step = demo_steps[step_index]

        print(f"\n{'='*70}")
        print(f"  {step['description']}")
        print(f"{'='*70}")
        print(f"  {step['detail']}")
        print(f"{'='*70}\n")

        # Execute demo action
        if 'action' in step:
            # Custom action
            step['action']()
        else:
            # Standard incremental build
            success = bot_ui.build_amount_incrementally(step['amount'])
            if success:
                # Read back the bet entry value
                current_value = main_window.bet_entry.get()
                print(f"✓ Amount built successfully: {current_value} SOL")
            else:
                print(f"✗ Failed to build amount: {step['amount']}")

        # Schedule next step
        delay_ms = int(step['delay'] * 1000)
        root.after(delay_ms, lambda: run_demo_step(step_index + 1))

    def demo_half_button(bot_ui):
        """Demo using 1/2 button"""
        # First build 0.1
        bot_ui.build_amount_incrementally(Decimal('0.1'))
        time.sleep(0.5)
        print("✓ Built 0.1 SOL")

        # Then click 1/2 button
        time.sleep(0.3)
        bot_ui.click_increment_button('1/2')
        print("✓ Clicked 1/2 button → Now 0.05 SOL")

    def demo_double_button(bot_ui):
        """Demo using X2 button"""
        # Current value should be 0.05 from previous step
        bot_ui.click_increment_button('X2')
        print("✓ Clicked X2 button → Now 0.1 SOL")

    # Start demo sequence after UI is ready
    root.after(2000, lambda: run_demo_step(0))

    # Run UI loop
    print("\nUI window should appear now...")
    print("Watch the bet amount entry field to see button clicks!")
    root.mainloop()

    print("\n✓ Demo finished")


if __name__ == "__main__":
    try:
        run_demo()
    except KeyboardInterrupt:
        print("\n\n✗ Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"\n✗ Demo failed: {e}")
        raise
