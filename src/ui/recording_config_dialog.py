"""
Recording Configuration Dialog - Phase 10.5E

Modal dialog for configuring recording sessions.
Provides controls for capture mode, session limits, data integrity, and preferences.
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Callable, Optional

from models.recording_config import RecordingConfig, CaptureMode, MonitorThresholdType

logger = logging.getLogger(__name__)


class RecordingConfigDialog:
    """
    Configuration dialog for recording sessions.

    Displays a modal dialog with all recording settings:
    - Capture Mode (Game State Only / Game State + Player State)
    - Session Limits (Game Count, Time Limit)
    - Data Integrity (Monitor Mode Threshold)
    - Preferences (Audio Cues, Auto-start)

    Buttons:
    - Save Settings: Persist to file
    - Cancel: Close without action
    - Start: Begin recording with current settings
    """

    # Preset values for radio buttons
    GAME_COUNT_OPTIONS = [1, 5, 10, 25, 50, None]  # None = infinite
    TIME_LIMIT_OPTIONS = [None, 15, 30, 60, 120]  # None = off
    TICK_THRESHOLD_OPTIONS = [5, 10, 15, 20, 30, 45, 60]
    GAME_THRESHOLD_OPTIONS = [1, 2, 3, 5, 10]

    def __init__(
        self,
        parent: tk.Tk,
        config: Optional[RecordingConfig] = None,
        on_start: Optional[Callable[[RecordingConfig], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None
    ):
        """
        Initialize the config dialog.

        Args:
            parent: Parent tkinter window
            config: Initial configuration (defaults loaded if None)
            on_start: Callback when Start is clicked, receives config
            on_cancel: Callback when Cancel is clicked
        """
        self.parent = parent
        self.config = config or RecordingConfig.load()
        self.on_start = on_start
        self.on_cancel = on_cancel

        self.dialog: Optional[tk.Toplevel] = None
        self.result: Optional[RecordingConfig] = None

        # Tkinter variables
        self._capture_mode_var: Optional[tk.StringVar] = None
        self._game_count_var: Optional[tk.StringVar] = None
        self._time_limit_var: Optional[tk.StringVar] = None
        self._custom_time_var: Optional[tk.StringVar] = None
        self._threshold_type_var: Optional[tk.StringVar] = None
        self._tick_threshold_var: Optional[tk.StringVar] = None
        self._game_threshold_var: Optional[tk.StringVar] = None
        self._audio_cues_var: Optional[tk.BooleanVar] = None
        self._auto_start_var: Optional[tk.BooleanVar] = None

    def show(self) -> Optional[RecordingConfig]:
        """
        Show the dialog and wait for user interaction.

        Returns:
            RecordingConfig if Start was clicked, None if cancelled
        """
        self._create_dialog()
        self._populate_from_config()

        # Make modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.parent.wait_window(self.dialog)

        return self.result

    def _create_dialog(self) -> None:
        """Create the dialog window and all widgets."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Recording Configuration")

        # Get screen dimensions and set appropriate height
        screen_height = self.dialog.winfo_screenheight()
        dialog_height = min(580, screen_height - 100)  # Leave room for taskbar
        self.dialog.geometry(f"520x{dialog_height}")
        self.dialog.resizable(True, True)
        self.dialog.minsize(480, 400)

        # Center on parent
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - 260
        y = max(50, self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (dialog_height // 2))
        self.dialog.geometry(f"+{x}+{y}")

        # Create scrollable container
        container = ttk.Frame(self.dialog)
        container.pack(fill=tk.BOTH, expand=True)

        # Canvas and scrollbar
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

        # Scrollable frame inside canvas
        scrollable_frame = ttk.Frame(canvas, padding=15)

        # Configure canvas scrolling
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_frame = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # Make the frame expand to fill canvas width
        def configure_canvas(event):
            canvas.itemconfig(canvas_frame, width=event.width)
        canvas.bind("<Configure>", configure_canvas)

        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack scrollbar and canvas
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Enable mouse wheel scrolling - bind to canvas and frame only (not all widgets)
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_mousewheel_linux(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        # Bind scroll to canvas only
        canvas.bind("<MouseWheel>", on_mousewheel)  # Windows/Mac
        canvas.bind("<Button-4>", on_mousewheel_linux)  # Linux scroll up
        canvas.bind("<Button-5>", on_mousewheel_linux)  # Linux scroll down

        # Also bind to the scrollable frame for when mouse is over content
        scrollable_frame.bind("<MouseWheel>", on_mousewheel)
        scrollable_frame.bind("<Button-4>", on_mousewheel_linux)
        scrollable_frame.bind("<Button-5>", on_mousewheel_linux)

        # Create sections in scrollable frame
        self._create_capture_mode_section(scrollable_frame)
        self._create_separator(scrollable_frame)
        self._create_session_limits_section(scrollable_frame)
        self._create_separator(scrollable_frame)
        self._create_data_integrity_section(scrollable_frame)
        self._create_separator(scrollable_frame)
        self._create_preferences_section(scrollable_frame)
        self._create_separator(scrollable_frame)
        self._create_buttons(scrollable_frame)

        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _create_separator(self, parent: ttk.Frame) -> None:
        """Add a horizontal separator."""
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

    def _create_capture_mode_section(self, parent: ttk.Frame) -> None:
        """Create capture mode radio buttons."""
        frame = ttk.LabelFrame(parent, text="Capture Mode", padding=10)
        frame.pack(fill=tk.X)

        self._capture_mode_var = tk.StringVar()

        ttk.Radiobutton(
            frame,
            text="Game State Only (prices, seeds, peak)",
            variable=self._capture_mode_var,
            value=CaptureMode.GAME_STATE_ONLY.value
        ).pack(anchor=tk.W, pady=2)

        ttk.Radiobutton(
            frame,
            text="Game State + Player State (includes trades, timing, latency)",
            variable=self._capture_mode_var,
            value=CaptureMode.GAME_AND_PLAYER.value
        ).pack(anchor=tk.W, pady=2)

    def _create_session_limits_section(self, parent: ttk.Frame) -> None:
        """Create session limits controls."""
        frame = ttk.LabelFrame(parent, text="Session Limits", padding=10)
        frame.pack(fill=tk.X)

        # Game Count
        game_frame = ttk.Frame(frame)
        game_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(game_frame, text="Game Count:").pack(anchor=tk.W)

        game_row = ttk.Frame(game_frame)
        game_row.pack(fill=tk.X, pady=5)

        self._game_count_var = tk.StringVar()

        for value in self.GAME_COUNT_OPTIONS:
            text = "∞" if value is None else str(value)
            ttk.Radiobutton(
                game_row,
                text=text,
                variable=self._game_count_var,
                value=str(value) if value is not None else "infinite"
            ).pack(side=tk.LEFT, padx=5)

        # Time Limit
        time_frame = ttk.Frame(frame)
        time_frame.pack(fill=tk.X)

        ttk.Label(time_frame, text="Time Limit:").pack(anchor=tk.W)

        time_row = ttk.Frame(time_frame)
        time_row.pack(fill=tk.X, pady=5)

        self._time_limit_var = tk.StringVar()
        self._custom_time_var = tk.StringVar()

        for value in self.TIME_LIMIT_OPTIONS:
            if value is None:
                text = "Off"
            elif value == 60:
                text = "1hr"
            elif value == 120:
                text = "2hr"
            else:
                text = f"{value}m"

            ttk.Radiobutton(
                time_row,
                text=text,
                variable=self._time_limit_var,
                value=str(value) if value is not None else "off"
            ).pack(side=tk.LEFT, padx=5)

        # Custom time option
        custom_frame = ttk.Frame(time_frame)
        custom_frame.pack(fill=tk.X, pady=5)

        ttk.Radiobutton(
            custom_frame,
            text="Custom:",
            variable=self._time_limit_var,
            value="custom"
        ).pack(side=tk.LEFT)

        self._custom_time_entry = ttk.Entry(
            custom_frame,
            textvariable=self._custom_time_var,
            width=6
        )
        self._custom_time_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(custom_frame, text="min").pack(side=tk.LEFT)

    def _create_data_integrity_section(self, parent: ttk.Frame) -> None:
        """Create data integrity controls."""
        frame = ttk.LabelFrame(parent, text="Data Integrity", padding=10)
        frame.pack(fill=tk.X)

        ttk.Label(
            frame,
            text="Monitor Mode Threshold (mutually exclusive):",
            foreground="gray"
        ).pack(anchor=tk.W)

        self._threshold_type_var = tk.StringVar()
        self._tick_threshold_var = tk.StringVar()
        self._game_threshold_var = tk.StringVar()

        # By Ticks
        tick_frame = ttk.Frame(frame)
        tick_frame.pack(fill=tk.X, pady=(10, 5))

        ttk.Radiobutton(
            tick_frame,
            text="By Ticks:",
            variable=self._threshold_type_var,
            value=MonitorThresholdType.TICKS.value
        ).pack(side=tk.LEFT)

        tick_values_frame = ttk.Frame(tick_frame)
        tick_values_frame.pack(side=tk.LEFT, padx=10)

        for value in self.TICK_THRESHOLD_OPTIONS:
            ttk.Radiobutton(
                tick_values_frame,
                text=str(value),
                variable=self._tick_threshold_var,
                value=str(value)
            ).pack(side=tk.LEFT, padx=3)

        # By Games
        game_frame = ttk.Frame(frame)
        game_frame.pack(fill=tk.X, pady=5)

        ttk.Radiobutton(
            game_frame,
            text="By Games:",
            variable=self._threshold_type_var,
            value=MonitorThresholdType.GAMES.value
        ).pack(side=tk.LEFT)

        game_values_frame = ttk.Frame(game_frame)
        game_values_frame.pack(side=tk.LEFT, padx=10)

        for value in self.GAME_THRESHOLD_OPTIONS:
            ttk.Radiobutton(
                game_values_frame,
                text=str(value),
                variable=self._game_threshold_var,
                value=str(value)
            ).pack(side=tk.LEFT, padx=3)

    def _create_preferences_section(self, parent: ttk.Frame) -> None:
        """Create preferences checkboxes."""
        frame = ttk.LabelFrame(parent, text="Preferences", padding=10)
        frame.pack(fill=tk.X)

        self._audio_cues_var = tk.BooleanVar()
        self._auto_start_var = tk.BooleanVar()

        ttk.Checkbutton(
            frame,
            text="Audio Cues (play sounds on recording events)",
            variable=self._audio_cues_var
        ).pack(anchor=tk.W, pady=2)

        ttk.Checkbutton(
            frame,
            text="Auto-start on Launch",
            variable=self._auto_start_var
        ).pack(anchor=tk.W, pady=2)

    def _create_buttons(self, parent: ttk.Frame) -> None:
        """Create action buttons."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            frame,
            text="Save Settings",
            command=self._on_save
        ).pack(side=tk.LEFT)

        ttk.Button(
            frame,
            text="Start",
            command=self._on_start,
            style="Accent.TButton"
        ).pack(side=tk.RIGHT)

        ttk.Button(
            frame,
            text="Cancel",
            command=self._on_cancel
        ).pack(side=tk.RIGHT, padx=10)

    def _populate_from_config(self) -> None:
        """Populate widgets from current config."""
        # Capture mode
        self._capture_mode_var.set(self.config.capture_mode.value)

        # Game count
        if self.config.game_count is None:
            self._game_count_var.set("infinite")
        else:
            self._game_count_var.set(str(self.config.game_count))

        # Time limit
        if self.config.time_limit_minutes is None:
            self._time_limit_var.set("off")
        elif self.config.time_limit_minutes in [15, 30, 60, 120]:
            self._time_limit_var.set(str(self.config.time_limit_minutes))
        else:
            self._time_limit_var.set("custom")
            self._custom_time_var.set(str(self.config.time_limit_minutes))

        # Threshold type and value
        self._threshold_type_var.set(self.config.monitor_threshold_type.value)
        if self.config.monitor_threshold_type == MonitorThresholdType.TICKS:
            self._tick_threshold_var.set(str(self.config.monitor_threshold_value))
            self._game_threshold_var.set("3")  # default
        else:
            self._game_threshold_var.set(str(self.config.monitor_threshold_value))
            self._tick_threshold_var.set("20")  # default

        # Preferences
        self._audio_cues_var.set(self.config.audio_cues)
        self._auto_start_var.set(self.config.auto_start_on_launch)

    def _build_config_from_widgets(self) -> RecordingConfig:
        """Build a RecordingConfig from current widget values."""
        # Capture mode
        capture_mode = CaptureMode(self._capture_mode_var.get())

        # Game count
        game_count_str = self._game_count_var.get()
        game_count = None if game_count_str == "infinite" else int(game_count_str)

        # Time limit
        time_limit_str = self._time_limit_var.get()
        if time_limit_str == "off":
            time_limit = None
        elif time_limit_str == "custom":
            try:
                time_limit = int(self._custom_time_var.get())
            except ValueError:
                time_limit = None
        else:
            time_limit = int(time_limit_str)

        # Threshold
        threshold_type = MonitorThresholdType(self._threshold_type_var.get())
        if threshold_type == MonitorThresholdType.TICKS:
            threshold_value = int(self._tick_threshold_var.get())
        else:
            threshold_value = int(self._game_threshold_var.get())

        return RecordingConfig(
            capture_mode=capture_mode,
            game_count=game_count,
            time_limit_minutes=time_limit,
            monitor_threshold_type=threshold_type,
            monitor_threshold_value=threshold_value,
            audio_cues=self._audio_cues_var.get(),
            auto_start_on_launch=self._auto_start_var.get()
        )

    def _on_save(self) -> None:
        """Handle Save Settings button."""
        try:
            config = self._build_config_from_widgets()
            config.save()
            logger.info("Recording settings saved")
        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)

    def _on_start(self) -> None:
        """Handle Start button."""
        try:
            logger.debug("Start button clicked")
            self.result = self._build_config_from_widgets()
            logger.debug(f"Config built: {self.result.capture_mode.value}")
            if self.on_start:
                logger.debug("Calling on_start callback")
                self.on_start(self.result)
                logger.debug("on_start callback completed")
            self.dialog.destroy()
            logger.debug("Dialog destroyed")
        except Exception as e:
            logger.error(f"Error in Start button handler: {e}", exc_info=True)

    def _on_cancel(self) -> None:
        """Handle Cancel button or window close."""
        try:
            self.result = None
            if self.on_cancel:
                self.on_cancel()
            self.dialog.destroy()
        except Exception as e:
            logger.error(f"Error in Cancel button handler: {e}", exc_info=True)
