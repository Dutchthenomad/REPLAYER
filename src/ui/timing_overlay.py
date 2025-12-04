"""
Draggable Timing Overlay Widget - Phase 8.6

Floating widget that displays bot execution timing metrics.
- Draggable: Click and drag to reposition
- Collapsible: Click header to expand/collapse
- Persistent: Remembers position and state
- Mode-aware: Only visible in UI_LAYER mode
"""

import tkinter as tk
from typing import Optional, Dict, Any
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TimingOverlay:
    """
    Draggable overlay widget for timing metrics display

    Features:
    - Minimal collapsed state (2 lines: delay + success rate)
    - Expanded state shows full stats (P50, P95, execution count)
    - Click-and-drag repositioning
    - Persistent position across sessions
    """

    def __init__(self, parent: tk.Widget, config_file: str = "timing_overlay.json"):
        """
        Initialize timing overlay

        Args:
            parent: Parent widget (main window)
            config_file: Path to config file for persistent state
        """
        self.parent = parent
        self.config_file = Path(config_file)

        # Load persistent state
        self.config = self._load_config()

        # Create toplevel window (floating)
        self.window = tk.Toplevel(parent)
        self.window.title("")  # No title bar text
        self.window.overrideredirect(True)  # Remove window decorations
        self.window.attributes('-topmost', True)  # Always on top
        self.window.configure(bg='#1a1a1a')

        # State
        self.expanded = self.config.get('expanded', False)
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0

        # Build UI
        self._create_ui()

        # Position window (wait for parent to be ready)
        self.parent.update_idletasks()

        # Get default position if not in config
        x = self.config.get('x')
        y = self.config.get('y')

        # If no saved position, calculate default (bottom-right corner)
        if x is None or y is None:
            screen_width = self.parent.winfo_screenwidth()
            screen_height = self.parent.winfo_screenheight()
            x = screen_width - 200 if x is None else x
            y = screen_height - 300 if y is None else y

        x, y = self._sanitize_position(x, y)

        self.window.geometry(f"+{x}+{y}")

        # Start hidden (will show when mode is UI_LAYER)
        self.window.withdraw()

        logger.info("TimingOverlay initialized")

    def _load_config(self) -> Dict[str, Any]:
        """Load persistent configuration"""
        default_config = {
            'x': None,
            'y': None,
            'expanded': False
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    default_config.update(loaded)
                    logger.debug(f"Loaded timing overlay config: {loaded}")
            except Exception as e:
                logger.error(f"Failed to load timing overlay config: {e}")

        return default_config

    def _save_config(self) -> None:
        """Save persistent configuration"""
        try:
            # Get current position
            self.config['x'] = self.window.winfo_x()
            self.config['y'] = self.window.winfo_y()
            self.config['expanded'] = self.expanded

            # Ensure parent directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            # Write config
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)

            logger.debug(f"Saved timing overlay config: {self.config}")
        except Exception as e:
            logger.error(f"Failed to save timing overlay config: {e}")

    def _sanitize_position(self, x: int, y: int) -> tuple[int, int]:
        """Ensure overlay coordinates stay within screen bounds."""
        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()
        safe_x = max(0, min(int(x), screen_width - 50))
        safe_y = max(0, min(int(y), screen_height - 50))
        return safe_x, safe_y

    def _create_ui(self):
        """Create overlay UI"""
        # Main container
        self.container = tk.Frame(
            self.window,
            bg='#2a2a2a',
            relief=tk.RAISED,
            bd=2
        )
        self.container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Header (draggable, clickable)
        self.header = tk.Frame(self.container, bg='#3a3a3a', cursor='fleur')
        self.header.pack(fill=tk.X)

        # Unicode symbols with ASCII fallback
        try:
            # Test if font supports Unicode symbols
            test_label = tk.Label(self.header, text="⏱️")
            test_font = test_label.cget('font')
            # If this doesn't raise, Unicode is supported
            timer_symbol = "⏱️"
            expand_symbol = "▼"
            collapse_symbol = "▶"
            check_symbol = "✓"
            test_label.destroy()
        except Exception:
            # Fallback to ASCII
            timer_symbol = "[T]"
            expand_symbol = "v"
            collapse_symbol = ">"
            check_symbol = "OK"
            logger.warning("Unicode symbols not supported, using ASCII fallback")

        self.title_label = tk.Label(
            self.header,
            text=f"{timer_symbol} TIMING",
            font=('Arial', 9, 'bold'),
            bg='#3a3a3a',
            fg='#ffffff',
            cursor='fleur'
        )
        self.title_label.pack(side=tk.LEFT, padx=5, pady=3)

        # Collapse/expand indicator
        self.toggle_label = tk.Label(
            self.header,
            text=expand_symbol if self.expanded else collapse_symbol,
            font=('Arial', 8),
            bg='#3a3a3a',
            fg='#888888',
            cursor='hand2'
        )
        self.toggle_label.pack(side=tk.RIGHT, padx=5)

        # Store symbols for later use
        self.expand_symbol = expand_symbol
        self.collapse_symbol = collapse_symbol
        self.check_symbol = check_symbol

        # Bind drag events to header
        self.header.bind('<Button-1>', self._start_drag)
        self.header.bind('<B1-Motion>', self._on_drag)
        self.header.bind('<ButtonRelease-1>', self._stop_drag)
        self.title_label.bind('<Button-1>', self._start_drag)
        self.title_label.bind('<B1-Motion>', self._on_drag)
        self.title_label.bind('<ButtonRelease-1>', self._stop_drag)

        # Bind toggle event
        self.toggle_label.bind('<Button-1>', self._toggle_expand)

        # Stats container (collapsed state)
        self.compact_frame = tk.Frame(self.container, bg='#2a2a2a')
        self.compact_frame.pack(fill=tk.X, padx=5, pady=5)

        self.delay_label = tk.Label(
            self.compact_frame,
            text="0ms",
            font=('Arial', 11, 'bold'),
            bg='#2a2a2a',
            fg='#00ff88'
        )
        self.delay_label.pack(anchor=tk.W)

        self.success_label = tk.Label(
            self.compact_frame,
            text="0% ✓",
            font=('Arial', 10),
            bg='#2a2a2a',
            fg='#ffffff'
        )
        self.success_label.pack(anchor=tk.W)

        # Expanded stats (initially hidden)
        self.expanded_frame = tk.Frame(self.container, bg='#2a2a2a')

        self.exec_count_label = tk.Label(
            self.expanded_frame,
            text="Executions: 0",
            font=('Arial', 9),
            bg='#2a2a2a',
            fg='#cccccc'
        )
        self.exec_count_label.pack(anchor=tk.W, padx=5, pady=2)

        self.p50_label = tk.Label(
            self.expanded_frame,
            text="P50: 0ms",
            font=('Arial', 9),
            bg='#2a2a2a',
            fg='#cccccc'
        )
        self.p50_label.pack(anchor=tk.W, padx=5, pady=2)

        self.p95_label = tk.Label(
            self.expanded_frame,
            text="P95: 0ms",
            font=('Arial', 9),
            bg='#2a2a2a',
            fg='#cccccc'
        )
        self.p95_label.pack(anchor=tk.W, padx=5, pady=2)

        # Show/hide expanded frame based on state
        if self.expanded:
            self.expanded_frame.pack(fill=tk.X, pady=(0, 5))

    def _start_drag(self, event):
        """Start dragging overlay"""
        self.dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def _on_drag(self, event):
        """Handle drag motion"""
        if self.dragging:
            # Calculate new position
            x = self.window.winfo_x() + event.x - self.drag_start_x
            y = self.window.winfo_y() + event.y - self.drag_start_y

            # Move window
            self.window.geometry(f"+{x}+{y}")

    def _stop_drag(self, event):
        """Stop dragging and save position"""
        if self.dragging:
            self.dragging = False
            self._save_config()

    def _toggle_expand(self, event):
        """Toggle expanded/collapsed state"""
        self.expanded = not self.expanded

        # Update toggle indicator (use stored symbols for Unicode/ASCII compatibility)
        self.toggle_label.config(text=self.expand_symbol if self.expanded else self.collapse_symbol)

        # Show/hide expanded frame
        if self.expanded:
            self.expanded_frame.pack(fill=tk.X, pady=(0, 5))
        else:
            self.expanded_frame.pack_forget()

        # Save state
        self._save_config()

    def update_stats(self, stats: Dict[str, Any]):
        """
        Update displayed timing stats (THREAD-SAFE)

        Args:
            stats: Dictionary with timing metrics from BrowserExecutor

        Note: This method can be called from background threads, so all GUI
              updates are marshaled to the main thread via parent.after()
        """
        try:
            # Format compact stats (safe - no GUI access)
            delay_ms = int(stats.get('avg_total_delay_ms', 0))
            success_rate = int(stats.get('success_rate', 0) * 100)
            exec_count = stats.get('total_executions', 0)
            p50 = int(stats.get('p50_total_delay_ms', 0))
            p95 = int(stats.get('p95_total_delay_ms', 0))

            # Thread-safe GUI update wrapper
            def _update_gui():
                try:
                    # Update compact display
                    self.delay_label.config(text=f"{delay_ms}ms")
                    self.success_label.config(text=f"{success_rate}% {self.check_symbol}")

                    # Update expanded stats
                    self.exec_count_label.config(text=f"Executions: {exec_count}")
                    self.p50_label.config(text=f"P50: {p50}ms")
                    self.p95_label.config(text=f"P95: {p95}ms")
                except Exception as e:
                    logger.error(f"Failed to update timing overlay GUI: {e}", exc_info=True)

            # Marshal to main thread
            self.parent.after(0, _update_gui)

        except Exception as e:
            logger.error(f"Failed to update timing overlay: {e}", exc_info=True)

    def show(self):
        """Show overlay"""
        self.window.deiconify()
        logger.debug("Timing overlay shown")

    def hide(self):
        """Hide overlay"""
        self.window.withdraw()
        logger.debug("Timing overlay hidden")

    def destroy(self):
        """
        Destroy overlay and save state (SAFE - handles already-destroyed widgets)

        Note: Wrapped in try/except to handle cases where parent or window
              may already be destroyed (e.g., during shutdown)
        """
        try:
            # Check if window still exists before accessing
            if hasattr(self, 'window') and self.window.winfo_exists():
                self._save_config()
                self.window.destroy()
                logger.info("Timing overlay destroyed")
            else:
                logger.debug("Timing overlay already destroyed")
        except tk.TclError as e:
            # Window already destroyed - this is fine
            logger.debug(f"Timing overlay destruction skipped (already gone): {e}")
        except Exception as e:
            # Unexpected error - log but don't crash
            logger.error(f"Error destroying timing overlay: {e}", exc_info=True)
