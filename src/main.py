"""
Main Entry Point for Rugs Replay Viewer
Clean, modular implementation
"""

import sys
import logging
from pathlib import Path
import tkinter as tk
from typing import Optional

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from core.game_state import GameState
from services.event_bus import event_bus, Events
from services.logger import setup_logging
from ui.main_window import MainWindow


class Application:
    """
    Main application controller
    Coordinates all components and manages lifecycle
    """
    
    def __init__(self):
        # Initialize logging first
        self.logger = setup_logging()
        self.logger.info("="*60)
        self.logger.info("Rugs Replay Viewer - Starting Application")
        self.logger.info("="*60)
        
        # Initialize core components
        self.config = config
        self.state = GameState(config.FINANCIAL['initial_balance'])
        self.event_bus = event_bus
        
        # Start event bus
        self.event_bus.start()
        
        # Setup event handlers
        self._setup_event_handlers()
        
        # Create UI
        self.root = tk.Tk()
        self.main_window = None
        
        # Configure root window
        self._configure_root()
        
        self.logger.info("Application initialized successfully")
    
    def _configure_root(self):
        """Configure the root tkinter window"""
        self.root.title("Rugs.fun Replay Viewer - Professional Edition")
        self.root.geometry(f"{config.UI['window_width']}x{config.UI['window_height']}")
        
        # Set minimum size
        self.root.minsize(800, 600)
        
        # Configure grid weights for responsive design
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Set icon if available
        icon_path = Path(__file__).parent / 'assets' / 'icon.ico'
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception as e:
                self.logger.warning(f"Could not set icon: {e}")
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
    
    def _setup_event_handlers(self):
        """Setup global event handlers"""
        # Application lifecycle events
        self.event_bus.subscribe(Events.UI_ERROR, self._handle_ui_error)
        
        # Game events
        self.event_bus.subscribe(Events.GAME_START, self._handle_game_start)
        self.event_bus.subscribe(Events.GAME_END, self._handle_game_end)
        self.event_bus.subscribe(Events.GAME_RUG, self._handle_rug_event)
        
        # Trading events
        self.event_bus.subscribe(Events.TRADE_EXECUTED, self._handle_trade_executed)
        self.event_bus.subscribe(Events.TRADE_FAILED, self._handle_trade_failed)
        
        self.logger.debug("Event handlers configured")
    
    def _handle_ui_error(self, event):
        """Handle UI errors"""
        self.logger.error(f"UI Error: {event.data}")
    
    def _handle_game_start(self, event):
        """Handle game start event"""
        self.logger.info(f"Game started: {event.data}")
    
    def _handle_game_end(self, event):
        """Handle game end event"""
        metrics = self.state.calculate_metrics()
        self.logger.info(f"Game ended. Metrics: {metrics}")
    
    def _handle_rug_event(self, event):
        """Handle rug event"""
        data = event.get('data', {})
        tick = data.get('tick', 'unknown')
        self.logger.warning(f"RUG EVENT at tick {tick}")

    def _handle_trade_executed(self, event):
        """Handle successful trade"""
        data = event.get('data', {})
        self.logger.info(f"Trade executed: {data}")

    def _handle_trade_failed(self, event):
        """Handle failed trade"""
        data = event.get('data', {})
        self.logger.warning(f"Trade failed: {data}")
    
    def run(self):
        """Run the application"""
        try:
            # Create main window
            self.main_window = MainWindow(
                self.root, 
                self.state, 
                self.event_bus,
                self.config
            )
            
            # Auto-load games if directory exists
            self._auto_load_games()
            
            # Publish ready event
            self.event_bus.publish(Events.UI_READY)
            
            # Start main loop
            self.logger.info("Starting UI main loop")
            self.root.mainloop()
            
        except Exception as e:
            self.logger.critical(f"Critical error in main loop: {e}", exc_info=True)
            self.shutdown()
    
    def _auto_load_games(self):
        """Auto-load game files if available"""
        recordings_dir = self.config.FILES['recordings_dir']
        
        if recordings_dir.exists():
            game_files = sorted(recordings_dir.glob("game_*.jsonl"))
            if game_files:
                self.logger.info(f"Found {len(game_files)} game files to auto-load")
                # Notify main window about available games
                self.event_bus.publish(
                    Events.FILE_LOADED, 
                    {'files': game_files}
                )
    
    def shutdown(self):
        """Clean shutdown of application"""
        self.logger.info("Shutting down application...")
        
        try:
            # Save configuration
            config_file = self.config.FILES['config_dir'] / 'settings.json'
            self.config.save_to_file(str(config_file))
            
            # Save state metrics
            metrics = self.state.calculate_metrics()
            self.logger.info(f"Final session metrics: {metrics}")
            
            # Stop event bus
            self.event_bus.stop()
            
            # Destroy UI
            if self.main_window:
                self.main_window.shutdown()

            if self.root:
                self.root.quit()
                self.root.destroy()
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
        
        finally:
            self.logger.info("Application shutdown complete")
            sys.exit(0)


def main():
    """Main entry point"""
    # Create and run application
    app = Application()
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        app.shutdown()
    except Exception as e:
        logging.critical(f"Unhandled exception: {e}", exc_info=True)
        app.shutdown()


if __name__ == "__main__":
    main()
