"""
ReplayController - Manages game file loading and playback control

Extracted from MainWindow to follow Single Responsibility Principle.
Handles:
- Game file loading (file dialog, auto-load)
- Playback control (play/pause, step, reset)
- Playback speed management
- Recording control
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Callable
import subprocess
import platform
import logging

logger = logging.getLogger(__name__)


class ReplayController:
    """
    Manages game file loading and playback control.

    Extracted from MainWindow (Phase 3.2) to reduce God Object anti-pattern.
    """

    def __init__(
        self,
        root: tk.Tk,
        parent_window,  # Reference to MainWindow for state access
        replay_engine,
        chart,
        config,
        # UI widgets
        play_button: tk.Button,
        step_button: tk.Button,
        reset_button: tk.Button,
        bot_toggle_button: tk.Button,
        speed_label: tk.Label,
        # UI variables
        recording_var: tk.BooleanVar,
        # Other dependencies
        toast,
        # Callbacks
        log_callback: Callable[[str], None],
        # Issue #18 fix: Use RecordingController for state consistency
        recording_controller=None
    ):
        """
        Initialize ReplayController with dependencies.

        Args:
            root: Tkinter root window
            parent_window: MainWindow instance (for state access)
            replay_engine: ReplayEngine instance
            chart: Chart widget instance
            config: Config object
            play_button: Play/pause button
            step_button: Step forward button
            reset_button: Reset button
            bot_toggle_button: Bot toggle button
            speed_label: Speed display label
            recording_var: Recording checkbox variable
            toast: Toast notification widget
            log_callback: Logging function
            recording_controller: RecordingController for state management (Issue #18)
        """
        self.root = root
        self.parent = parent_window  # Access to MainWindow state
        self.replay_engine = replay_engine
        self.chart = chart
        self.config = config

        # UI widgets
        self.play_button = play_button
        self.step_button = step_button
        self.reset_button = reset_button
        self.bot_toggle_button = bot_toggle_button
        self.speed_label = speed_label

        # UI variables
        self.recording_var = recording_var

        # Other dependencies
        self.toast = toast

        # Issue #18: RecordingController is now the source of truth
        self.recording_controller = recording_controller

        # Callbacks
        self.log = log_callback

        logger.info("ReplayController initialized")

    # ========================================================================
    # GAME FILE LOADING
    # ========================================================================

    def load_game(self):
        """Load a game file via file dialog"""
        filepath = filedialog.askopenfilename(
            title="Select Game Recording",
            filetypes=[("JSONL files", "*.jsonl"), ("All files", "*.*")]
        )

        if filepath:
            try:
                self.load_game_file(Path(filepath))
            except Exception as e:
                messagebox.showerror("Load Error", f"Failed to load game: {e}")

    def load_game_file(self, filepath: Path):
        """Load game data from file using ReplayEngine"""
        # Sync multi-game mode to replay engine
        self.replay_engine.multi_game_mode = self.parent.multi_game_mode

        success = self.replay_engine.load_file(filepath)

        if success:
            info = self.replay_engine.get_info()
            self.log(f"Loaded game with {info['total_ticks']} ticks")

            # Enable controls
            self.play_button.config(state=tk.NORMAL)
            self.step_button.config(state=tk.NORMAL)
            self.reset_button.config(state=tk.NORMAL)
            self.bot_toggle_button.config(state=tk.NORMAL)
        else:
            self.log("Failed to load game file")
            messagebox.showerror("Load Error", "Failed to load game file")

    def load_file_dialog(self):
        """Alias for load_game() - used by menu bar"""
        self.load_game()

    def load_next_game(self, filepath: Path):
        """Load next game in multi-game session (instant, no delay)"""
        try:
            self.load_game_file(filepath)
            # Keep bot running if it was enabled
            if self.parent.bot_enabled:
                # Bot stays enabled across games
                logger.info("Bot remains enabled for next game")
        except Exception as e:
            logger.error(f"Failed to load next game: {e}")
            self.log(f"❌ Failed to load next game: {e}")
            # Stop multi-game mode on error
            self.parent.multi_game_mode = False

    # ========================================================================
    # PLAYBACK CONTROL
    # ========================================================================

    def toggle_playback(self):
        """Toggle play/pause using ReplayEngine"""
        if self.replay_engine.is_playing:
            self.replay_engine.pause()
            self.parent.user_paused = True
            self.play_button.config(text="▶️ Play")
        else:
            self.replay_engine.play()
            self.parent.user_paused = False
            self.play_button.config(text="⏸️ Pause")

    def toggle_play_pause(self):
        """Alias for toggle_playback() - used by menu bar"""
        self.toggle_playback()

    def step_forward(self):
        """Step forward one tick using ReplayEngine"""
        if not self.replay_engine.step_forward():
            self.log("Reached end of game")
            self.play_button.config(text="▶️ Play")

    def step_backward(self):
        """Step backward one tick"""
        if self.replay_engine.step_backward():
            self.log("Stepped backward")

    def reset_game(self):
        """Reset to beginning using ReplayEngine"""
        self.replay_engine.reset()
        self.chart.clear_history()
        self.play_button.config(text="▶️ Play")
        self.parent.user_paused = True
        self.log("Game reset")

    # ========================================================================
    # PLAYBACK SPEED
    # ========================================================================

    def set_playback_speed(self, speed: float):
        """Set playback speed"""
        self.replay_engine.set_speed(speed)
        self.speed_label.config(text=f"SPEED: {speed}X")
        self.log(f"Playback speed set to {speed}x")

    # ========================================================================
    # RECORDING CONTROL
    # ========================================================================

    def toggle_recording(self):
        """
        Toggle recording on/off from menu.

        Issue #18 Fix: Uses RecordingController instead of ReplayEngine
        for consistent state management.
        """
        def do_toggle():
            # Issue #18: Use RecordingController as source of truth
            if self.recording_controller:
                if self.recording_controller.is_active:
                    self.recording_controller.stop_session()
                    self.recording_var.set(False)
                    self.log("Recording stopped")
                else:
                    # Show config dialog for new recording session
                    if self.recording_controller.show_config_dialog():
                        self.recording_var.set(True)
                        self.log("Recording started")
            else:
                # Fallback for backwards compatibility (no recording_controller)
                logger.warning("No recording_controller - falling back to legacy")
                if self.replay_engine.auto_recording:
                    self.replay_engine.disable_recording()
                    self.recording_var.set(False)
                    self.log("Recording disabled")
                    if self.toast:
                        self.toast.show("Recording disabled", "info")
                else:
                    self.replay_engine.enable_recording()
                    self.recording_var.set(True)
                    self.log("Recording enabled")
                    if self.toast:
                        self.toast.show("Recording enabled", "success")

        # Ensure always runs in main thread
        self.root.after(0, do_toggle)

    def open_recordings_folder(self):
        """Open recordings folder in system file manager"""
        recordings_dir = self.config.FILES['recordings_dir']

        try:
            system = platform.system()
            if system == 'Linux':
                # Try xdg-open first (most Linux distros)
                subprocess.run(['xdg-open', str(recordings_dir)], check=True)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', str(recordings_dir)], check=True)
            elif system == 'Windows':
                subprocess.run(['explorer', str(recordings_dir)], check=True)
            else:
                raise OSError(f"Unsupported platform: {system}")

            self.log(f"Opened recordings folder: {recordings_dir}")
        except Exception as e:
            logger.error(f"Failed to open recordings folder: {e}", exc_info=True)
            self.log(f"Failed to open recordings folder: {e}")
            if self.toast:
                self.toast.show(f"Error opening folder: {e}", "error")
