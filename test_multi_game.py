#!/usr/bin/env python3
"""
Test Multi-Game Mode Programmatically
Enables multi-game mode via code (no UI toggle needed)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from main import Application

def main():
    """Test multi-game mode with programmatic control"""
    print("=" * 80)
    print("MULTI-GAME MODE TEST")
    print("=" * 80)
    print()
    print("This script enables multi-game mode programmatically.")
    print("Games will auto-advance instantly after each game ends.")
    print()
    print("Instructions:")
    print("1. Enable the bot")
    print("2. Click Play")
    print("3. Watch the bot play through multiple games automatically")
    print()
    print("=" * 80)
    print()

    # Create application
    app = Application()

    # Enable multi-game mode programmatically (NO UI TOGGLE)
    app.main_window.multi_game_mode = True
    print("✅ Multi-game mode ENABLED")

    # Optionally limit queue for testing
    # app.main_window.game_queue.games = app.main_window.game_queue.games[:10]
    # print("✅ Queue limited to 10 games for testing")

    # Auto-load first game
    if app.main_window.game_queue.has_next():
        first_game = app.main_window.game_queue.next_game()
        app.main_window.load_game_file(first_game)
        print(f"✅ Loaded first game: {first_game.name}")
        print(f"   Queue: {app.main_window.game_queue.current_index}/{len(app.main_window.game_queue)} games")
    else:
        print("❌ No games found in queue")
        return

    print()
    print("🤖 You can now enable the bot and click Play to start multi-game session")
    print()

    # Run application
    app.run()


if __name__ == "__main__":
    main()
