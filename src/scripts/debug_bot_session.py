#!/usr/bin/env python3
"""
Debug Bot Session - Automated testing with screenshots and detailed logging

This script runs the bot in REPLAYER and captures:
- All bot decisions with reasoning
- Screenshots at key moments (entry, exit, errors)
- Timing metrics for button clicks
- Balance/position changes
- Any errors or unexpected behavior

Usage:
    cd /home/nomad/Desktop/REPLAYER/src
    /home/nomad/Desktop/rugs-rl-bot/.venv/bin/python3 debug_bot_session.py

Output:
    - debug_session_TIMESTAMP/ directory with:
      - bot_decisions.log (detailed event log)
      - screenshots/ (numbered screenshots)
      - metrics.json (performance data)
"""

import sys
import logging
import threading
import time
import json
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import tkinter as tk

# Add parent directory to Python path to allow imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core import GameState, ReplayEngine
from bot import BotInterface, BotController, ExecutionMode

# Setup debug logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
debug_dir = Path(f"debug_session_{timestamp}")
debug_dir.mkdir(exist_ok=True)
screenshot_dir = debug_dir / "screenshots"
screenshot_dir.mkdir(exist_ok=True)

# Configure logging
log_file = debug_dir / "bot_decisions.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Metrics tracking
metrics = {
    'session_start': timestamp,
    'decisions': [],
    'trades': [],
    'errors': [],
    'timing': [],
    'screenshots': []
}

screenshot_counter = 0


def take_screenshot(root, reason: str):
    """Take screenshot of current UI state"""
    global screenshot_counter
    try:
        screenshot_counter += 1
        filename = f"{screenshot_counter:03d}_{reason}.png"
        filepath = screenshot_dir / filename

        # Take screenshot using tkinter
        root.update_idletasks()
        x = root.winfo_rootx()
        y = root.winfo_rooty()
        width = root.winfo_width()
        height = root.winfo_height()

        # Use scrot or gnome-screenshot if available
        import subprocess
        try:
            subprocess.run([
                'gnome-screenshot',
                '-w',
                '-f', str(filepath)
            ], check=True, timeout=2)

            metrics['screenshots'].append({
                'number': screenshot_counter,
                'reason': reason,
                'filename': filename,
                'timestamp': datetime.now().isoformat()
            })
            logger.info(f"📸 Screenshot {screenshot_counter}: {reason}")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            logger.debug(f"Screenshot tool not available, skipping {reason}")
    except Exception as e:
        logger.error(f"Failed to take screenshot: {e}")


class DebugBotMonitor:
    """Monitor bot behavior and capture debug info"""

    def __init__(self, root, event_bus, game_state):
        self.root = root
        self.event_bus = event_bus
        self.game_state = game_state

        # Subscribe to all relevant events
        self.event_bus.subscribe(Events.BOT_DECISION, self._on_bot_decision)
        self.event_bus.subscribe(Events.TRADE_EXECUTED, self._on_trade)
        self.event_bus.subscribe(Events.TRADE_FAILED, self._on_trade_failed)
        self.event_bus.subscribe(Events.GAME_START, self._on_game_start)
        self.event_bus.subscribe(Events.GAME_END, self._on_game_end)

    def _on_bot_decision(self, data):
        """Log bot decision and take screenshot if important"""
        decision = data.get('decision')
        reasoning = data.get('reasoning', 'No reasoning provided')

        logger.info(f"🤖 BOT DECISION: {decision}")
        logger.info(f"   Reasoning: {reasoning}")

        # Record decision
        metrics['decisions'].append({
            'timestamp': datetime.now().isoformat(),
            'decision': decision,
            'reasoning': reasoning,
            'game_state': {
                'tick': self.game_state.get('current_tick'),
                'price': float(self.game_state.get('current_price', 0)),
                'balance': float(self.game_state.get('balance', 0)),
                'has_position': self.game_state.get('position') is not None
            }
        })

        # Take screenshot for BUY/SELL decisions
        if decision in ['BUY', 'SELL', 'SIDEBET']:
            take_screenshot(self.root, f"decision_{decision.lower()}")

    def _on_trade(self, data):
        """Log successful trade execution"""
        trade_type = data.get('type', 'UNKNOWN')
        amount = data.get('amount', 0)

        logger.info(f"✅ TRADE EXECUTED: {trade_type} {amount} SOL")

        metrics['trades'].append({
            'timestamp': datetime.now().isoformat(),
            'type': trade_type,
            'amount': float(amount),
            'success': True
        })

        take_screenshot(self.root, f"trade_{trade_type.lower()}")

    def _on_trade_failed(self, data):
        """Log failed trade and capture error"""
        trade_type = data.get('type', 'UNKNOWN')
        error = data.get('error', 'Unknown error')

        logger.error(f"❌ TRADE FAILED: {trade_type} - {error}")

        metrics['errors'].append({
            'timestamp': datetime.now().isoformat(),
            'type': 'TRADE_FAILED',
            'trade_type': trade_type,
            'error': str(error)
        })

        take_screenshot(self.root, f"error_trade_failed")

    def _on_game_start(self, data):
        """Log game start"""
        logger.info("🎮 GAME STARTED")
        take_screenshot(self.root, "game_start")

    def _on_game_end(self, data):
        """Log game end with final metrics"""
        result = data.get('result', {})
        logger.info(f"🏁 GAME ENDED - Result: {result}")
        take_screenshot(self.root, "game_end")


def run_debug_session(game_file: str = None, duration_seconds: int = 60):
    """
    Run a debug session with the bot

    Args:
        game_file: Path to specific game recording (or None for first available)
        duration_seconds: How long to run (default 60s)
    """
    logger.info("=" * 80)
    logger.info("DEBUG BOT SESSION STARTING")
    logger.info(f"Output directory: {debug_dir}")
    logger.info("=" * 80)

    try:
        # Import UI components (needs to be after logging setup)
        import tkinter as tk
        from ui.main_window import MainWindow

        # Create tkinter root
        root = tk.Tk()
        root.title("REPLAYER - Debug Session")

        # Create main window
        logger.info("Creating REPLAYER UI...")
        main_window = MainWindow(root)

        # Get components
        event_bus = main_window.event_bus
        game_state = main_window.state

        # Setup debug monitor
        logger.info("Setting up debug monitor...")
        monitor = DebugBotMonitor(root, event_bus, game_state)

        # Load a game
        logger.info("Loading game recording...")
        recordings_dir = Path("/home/nomad/rugs_recordings")
        if game_file:
            game_path = Path(game_file)
        else:
            # Load first available game
            games = sorted(recordings_dir.glob("game_*.jsonl"))
            if not games:
                logger.error("No game recordings found!")
                return
            game_path = games[0]

        logger.info(f"Loading: {game_path.name}")
        # TODO: Load game via MainWindow API

        # Enable bot with foundational strategy
        logger.info("Enabling bot with foundational strategy...")
        main_window.bot_config_panel.config['strategy'] = 'foundational'
        main_window.bot_config_panel.config['execution_mode'] = 'ui_layer'
        main_window.bot_config_panel.config['bot_enabled'] = True

        # Take initial screenshot
        root.update()
        time.sleep(0.5)  # Let UI settle
        take_screenshot(root, "initial_state")

        # Start bot
        logger.info("Starting bot...")
        main_window._toggle_bot()  # Enable bot

        # Run for specified duration
        logger.info(f"Running for {duration_seconds} seconds...")
        start_time = time.time()

        def check_timeout():
            """Check if session should end"""
            elapsed = time.time() - start_time
            if elapsed >= duration_seconds:
                logger.info("⏱️ Duration reached, stopping session...")
                root.quit()
            else:
                root.after(1000, check_timeout)  # Check every second

        root.after(1000, check_timeout)

        # Run UI loop
        logger.info("UI loop starting...")
        root.mainloop()

    except Exception as e:
        logger.error(f"Debug session error: {e}", exc_info=True)
        metrics['errors'].append({
            'timestamp': datetime.now().isoformat(),
            'type': 'SESSION_ERROR',
            'error': str(e)
        })
    finally:
        # Save metrics
        logger.info("Saving metrics...")
        metrics_file = debug_dir / "metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)

        logger.info("=" * 80)
        logger.info("DEBUG SESSION COMPLETE")
        logger.info(f"Decisions logged: {len(metrics['decisions'])}")
        logger.info(f"Trades executed: {len(metrics['trades'])}")
        logger.info(f"Errors: {len(metrics['errors'])}")
        logger.info(f"Screenshots: {len(metrics['screenshots'])}")
        logger.info(f"Output directory: {debug_dir}")
        logger.info("=" * 80)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Debug bot session with screenshots')
    parser.add_argument('--game', type=str, help='Specific game file to load')
    parser.add_argument('--duration', type=int, default=60, help='Duration in seconds')

    args = parser.parse_args()

    run_debug_session(game_file=args.game, duration_seconds=args.duration)
