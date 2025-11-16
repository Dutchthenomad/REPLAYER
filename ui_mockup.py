#!/usr/bin/env python3
"""
REPLAYER UI Mockup - Menu System Design
========================================

Standalone mockup to design and test the menu structure before
integrating into main REPLAYER codebase.

Usage: python3 ui_mockup.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import time


class REPLAYERMockup:
    """Mockup of REPLAYER UI with proposed menu system"""

    def __init__(self, root):
        self.root = root
        self.root.title("REPLAYER - UI Mockup")
        self.root.geometry("1200x800")

        # State variables for menu toggles
        self.recording_enabled = tk.BooleanVar(value=True)  # Default: ON
        self.auto_start_recording = tk.BooleanVar(value=True)
        self.include_metadata = tk.BooleanVar(value=True)
        self.compress_files = tk.BooleanVar(value=False)
        self.buffer_size = tk.StringVar(value="medium")

        self.live_feed_connected = tk.BooleanVar(value=False)
        self.auto_record_live = tk.BooleanVar(value=False)

        self.bot_enabled = tk.BooleanVar(value=False)
        self.bot_strategy = tk.StringVar(value="aggressive")

        self.show_status = tk.BooleanVar(value=True)
        self.show_chart = tk.BooleanVar(value=True)
        self.show_trading = tk.BooleanVar(value=True)
        self.show_bot = tk.BooleanVar(value=True)
        self.show_grid = tk.BooleanVar(value=True)
        self.show_phase_markers = tk.BooleanVar(value=True)
        self.theme = tk.StringVar(value="dark")

        self.playback_speed = tk.StringVar(value="1.0")

        # Recording stats
        self.session_games = 0
        self.total_size_mb = 0.0

        self._create_menu_bar()
        self._create_ui()
        self._create_status_bar()
        self._bind_keyboard_shortcuts()

        # Start status update loop
        self._update_status()

    def _create_menu_bar(self):
        """Create application menu bar with proposed structure"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # ===== FILE MENU =====
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Recording...", command=self.open_recording, accelerator="Ctrl+O")

        # Recent files submenu
        recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Open Recent", menu=recent_menu)
        recent_menu.add_command(label="game_20251115_193803.jsonl", command=lambda: self.log("Open: game_20251115_193803.jsonl"))
        recent_menu.add_command(label="game_20251115_193002.jsonl", command=lambda: self.log("Open: game_20251115_193002.jsonl"))
        recent_menu.add_separator()
        recent_menu.add_command(label="Clear Recent", command=lambda: self.log("Clear recent files"))

        file_menu.add_separator()
        file_menu.add_command(label="Export Game Data...", command=lambda: self.log("Export game data"))
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")

        # ===== PLAYBACK MENU =====
        playback_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Playback", menu=playback_menu)
        playback_menu.add_command(label="Play/Pause", command=self.toggle_playback, accelerator="Space")
        playback_menu.add_command(label="Stop", command=lambda: self.log("Stop playback"), accelerator="Ctrl+S")
        playback_menu.add_command(label="Next Game", command=lambda: self.log("Next game"), accelerator="→")
        playback_menu.add_command(label="Previous Game", command=lambda: self.log("Previous game"), accelerator="←")
        playback_menu.add_separator()

        # Speed submenu
        speed_menu = tk.Menu(playback_menu, tearoff=0)
        playback_menu.add_cascade(label="Speed", menu=speed_menu)
        speed_menu.add_radiobutton(label="0.5x", variable=self.playback_speed, value="0.5", command=self.update_speed)
        speed_menu.add_radiobutton(label="1.0x (Normal)", variable=self.playback_speed, value="1.0", command=self.update_speed)
        speed_menu.add_radiobutton(label="2.0x", variable=self.playback_speed, value="2.0", command=self.update_speed)
        speed_menu.add_radiobutton(label="4.0x", variable=self.playback_speed, value="4.0", command=self.update_speed)

        playback_menu.add_separator()
        playback_menu.add_command(label="Jump to Tick...", command=lambda: self.log("Jump to tick"), accelerator="Ctrl+J")

        # ===== RECORDING MENU ===== (Main focus)
        recording_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Recording", menu=recording_menu)
        recording_menu.add_checkbutton(
            label="Enable Recording",
            variable=self.recording_enabled,
            command=self.toggle_recording,
            accelerator="Ctrl+R"
        )
        recording_menu.add_separator()

        # Recording options submenu
        recording_options = tk.Menu(recording_menu, tearoff=0)
        recording_menu.add_cascade(label="Recording Options", menu=recording_options)
        recording_options.add_checkbutton(
            label="Auto-start on playback",
            variable=self.auto_start_recording,
            command=lambda: self.log(f"Auto-start: {self.auto_start_recording.get()}")
        )
        recording_options.add_checkbutton(
            label="Include metadata",
            variable=self.include_metadata,
            command=lambda: self.log(f"Metadata: {self.include_metadata.get()}")
        )
        recording_options.add_checkbutton(
            label="Compress recordings",
            variable=self.compress_files,
            command=lambda: self.log(f"Compress: {self.compress_files.get()}")
        )

        # Buffer size submenu
        buffer_menu = tk.Menu(recording_options, tearoff=0)
        recording_options.add_cascade(label="Buffer Size", menu=buffer_menu)
        buffer_menu.add_radiobutton(
            label="Small (10 ticks)",
            variable=self.buffer_size,
            value="small",
            command=lambda: self.log("Buffer: small")
        )
        buffer_menu.add_radiobutton(
            label="Medium (100 ticks)",
            variable=self.buffer_size,
            value="medium",
            command=lambda: self.log("Buffer: medium")
        )
        buffer_menu.add_radiobutton(
            label="Large (1000 ticks)",
            variable=self.buffer_size,
            value="large",
            command=lambda: self.log("Buffer: large")
        )

        recording_menu.add_separator()
        recording_menu.add_command(label="Recording Location...", command=lambda: self.log("Change recording location"))
        recording_menu.add_command(label="Open Recordings Folder", command=self.open_recordings_folder)
        recording_menu.add_separator()

        # Recording stats submenu
        stats_menu = tk.Menu(recording_menu, tearoff=0)
        recording_menu.add_cascade(label="Recording Stats", menu=stats_menu)
        stats_menu.add_command(label=f"Current Session: {self.session_games} games", state=tk.DISABLED)
        stats_menu.add_command(label=f"Total Size: {self.total_size_mb:.1f} MB", state=tk.DISABLED)
        stats_menu.add_command(label="Disk Space: 120 GB free", state=tk.DISABLED)
        stats_menu.add_separator()
        stats_menu.add_command(label="Clear Statistics", command=self.clear_stats)

        # ===== VIEW MENU =====
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_checkbutton(label="Show Status Panel", variable=self.show_status, command=self.update_panels, accelerator="F1")
        view_menu.add_checkbutton(label="Show Chart", variable=self.show_chart, command=self.update_panels, accelerator="F2")
        view_menu.add_checkbutton(label="Show Trading Panel", variable=self.show_trading, command=self.update_panels, accelerator="F3")
        view_menu.add_checkbutton(label="Show Bot Panel", variable=self.show_bot, command=self.update_panels, accelerator="F4")
        view_menu.add_separator()
        view_menu.add_checkbutton(label="Show Grid Lines", variable=self.show_grid, command=lambda: self.log(f"Grid: {self.show_grid.get()}"))
        view_menu.add_checkbutton(label="Show Phase Markers", variable=self.show_phase_markers, command=lambda: self.log(f"Phase markers: {self.show_phase_markers.get()}"))
        view_menu.add_separator()

        # Theme submenu
        theme_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Theme", menu=theme_menu)
        theme_menu.add_radiobutton(label="Dark", variable=self.theme, value="dark", command=self.update_theme)
        theme_menu.add_radiobutton(label="Light", variable=self.theme, value="light", command=self.update_theme)

        # ===== BOT MENU =====
        bot_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Bot", menu=bot_menu)
        bot_menu.add_checkbutton(label="Enable Bot", variable=self.bot_enabled, command=self.toggle_bot, accelerator="B")
        bot_menu.add_separator()

        # Strategy submenu
        strategy_menu = tk.Menu(bot_menu, tearoff=0)
        bot_menu.add_cascade(label="Strategy", menu=strategy_menu)
        strategy_menu.add_radiobutton(label="Conservative", variable=self.bot_strategy, value="conservative", command=self.update_strategy)
        strategy_menu.add_radiobutton(label="Aggressive", variable=self.bot_strategy, value="aggressive", command=self.update_strategy)
        strategy_menu.add_radiobutton(label="Sidebet-Focused", variable=self.bot_strategy, value="sidebet", command=self.update_strategy)

        bot_menu.add_separator()
        bot_menu.add_command(label="Bot Settings...", command=lambda: self.log("Open bot settings"))
        bot_menu.add_command(label="View Bot Logs", command=lambda: self.log("View bot logs"))

        # ===== LIVE FEED MENU =====
        live_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Live Feed", menu=live_menu)
        live_menu.add_checkbutton(
            label="Connect to Live Feed",
            variable=self.live_feed_connected,
            command=self.toggle_live_feed,
            accelerator="L"
        )
        live_menu.add_separator()

        # Connection status submenu
        status_submenu = tk.Menu(live_menu, tearoff=0)
        live_menu.add_cascade(label="Connection Status", menu=status_submenu)
        status_submenu.add_command(label="Status: Disconnected", state=tk.DISABLED)
        status_submenu.add_command(label="Uptime: --", state=tk.DISABLED)
        status_submenu.add_command(label="Signals: --", state=tk.DISABLED)

        live_menu.add_separator()
        live_menu.add_checkbutton(
            label="Auto-record live games",
            variable=self.auto_record_live,
            command=self.toggle_auto_record_live
        )
        live_menu.add_command(label="Live Feed Settings...", command=lambda: self.log("Live feed settings"))

        # ===== HELP MENU =====
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts, accelerator="F1")
        help_menu.add_command(label="Documentation", command=lambda: self.log("Open documentation"))
        help_menu.add_separator()
        help_menu.add_command(label="Check for Updates", command=lambda: self.log("Check for updates"))
        help_menu.add_command(label="About REPLAYER", command=self.show_about)

    def _create_ui(self):
        """Create simplified mockup of main UI panels"""
        # Main container
        main_container = tk.Frame(self.root, bg="#1e1e1e")
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left side: Status + Trading panels
        left_panel = tk.Frame(main_container, bg="#1e1e1e")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=5)

        # Status Panel
        self.status_panel = tk.LabelFrame(left_panel, text="Status", bg="#2d2d2d", fg="white", width=250)
        self.status_panel.pack(fill=tk.BOTH, pady=5)
        self.status_panel.pack_propagate(False)

        tk.Label(self.status_panel, text="PHASE: ACTIVE", bg="#2d2d2d", fg="#00ff00", font=("Courier", 12, "bold")).pack(pady=5)
        tk.Label(self.status_panel, text="Tick: 100", bg="#2d2d2d", fg="white").pack()
        tk.Label(self.status_panel, text="Price: 1.5x", bg="#2d2d2d", fg="white").pack()
        tk.Label(self.status_panel, text="Balance: 1.000 SOL", bg="#2d2d2d", fg="white").pack()

        # Trading Panel
        self.trading_panel = tk.LabelFrame(left_panel, text="Trading", bg="#2d2d2d", fg="white", width=250, height=200)
        self.trading_panel.pack(fill=tk.BOTH, pady=5)
        self.trading_panel.pack_propagate(False)

        tk.Label(self.trading_panel, text="No position", bg="#2d2d2d", fg="gray").pack(pady=10)

        # Bot Panel
        self.bot_panel = tk.LabelFrame(left_panel, text="Bot", bg="#2d2d2d", fg="white", width=250, height=150)
        self.bot_panel.pack(fill=tk.BOTH, pady=5)
        self.bot_panel.pack_propagate(False)

        tk.Label(self.bot_panel, text="Bot: DISABLED", bg="#2d2d2d", fg="gray").pack(pady=10)

        # Center: Chart panel
        self.chart_panel = tk.LabelFrame(main_container, text="Price Chart", bg="#2d2d2d", fg="white")
        self.chart_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # Chart canvas
        self.chart_canvas = tk.Canvas(self.chart_panel, bg="#1a1a1a", highlightthickness=0)
        self.chart_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Recording indicator on chart
        self.recording_indicator = None
        self._draw_recording_indicator()

        # Event log
        self.log_frame = tk.LabelFrame(main_container, text="Event Log", bg="#2d2d2d", fg="white", width=300)
        self.log_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5)

        self.log_text = tk.Text(self.log_frame, bg="#1a1a1a", fg="white", height=10, width=40, font=("Courier", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.log("REPLAYER UI Mockup loaded")
        self.log("Recording: ENABLED (default)")

    def _create_status_bar(self):
        """Create bottom status bar"""
        self.status_bar = tk.Label(
            self.root,
            text="Recording: ON | Live: OFF | Bot: OFF | Speed: 1.0x",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg="#2d2d2d",
            fg="white",
            font=("Arial", 9)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _bind_keyboard_shortcuts(self):
        """Bind keyboard shortcuts"""
        self.root.bind("<Control-r>", lambda e: self.toggle_recording())
        self.root.bind("<Control-o>", lambda e: self.open_recording())
        self.root.bind("<Control-q>", lambda e: self.root.quit())
        self.root.bind("<Control-s>", lambda e: self.log("Stop playback"))
        self.root.bind("<Control-j>", lambda e: self.log("Jump to tick"))
        self.root.bind("<space>", lambda e: self.toggle_playback())
        self.root.bind("<b>", lambda e: self.toggle_bot())
        self.root.bind("<l>", lambda e: self.toggle_live_feed())
        self.root.bind("<F1>", lambda e: self.show_shortcuts())
        self.root.bind("<F2>", lambda e: self.show_status.set(not self.show_status.get()) or self.update_panels())
        self.root.bind("<F3>", lambda e: self.show_chart.set(not self.show_chart.get()) or self.update_panels())
        self.root.bind("<F4>", lambda e: self.show_trading.set(not self.show_trading.get()) or self.update_panels())

    def _draw_recording_indicator(self):
        """Draw recording indicator on chart"""
        if self.recording_indicator:
            self.chart_canvas.delete(self.recording_indicator)

        if self.recording_enabled.get():
            # Red circle + "REC" text
            self.chart_canvas.create_oval(15, 15, 25, 25, fill="red", outline="red", tags="rec_indicator")
            self.chart_canvas.create_text(45, 20, text="REC", fill="red", font=("Arial", 10, "bold"), tags="rec_indicator")
            self.recording_indicator = "rec_indicator"
        else:
            self.recording_indicator = None

    def _update_status(self):
        """Update status bar with current state"""
        recording = "ON" if self.recording_enabled.get() else "OFF"
        live = "ON" if self.live_feed_connected.get() else "OFF"
        bot = "ON" if self.bot_enabled.get() else "OFF"
        speed = f"{self.playback_speed.get()}x"

        self.status_bar.config(text=f"Recording: {recording} | Live: {live} | Bot: {bot} | Speed: {speed}")

        # Schedule next update
        self.root.after(500, self._update_status)

    # ===== Menu Callbacks =====

    def toggle_recording(self):
        """Toggle recording on/off"""
        if self.recording_enabled.get():
            self.log("✅ Recording ENABLED")
        else:
            self.log("❌ Recording DISABLED")
        self._draw_recording_indicator()

    def toggle_live_feed(self):
        """Toggle live feed connection"""
        if self.live_feed_connected.get():
            self.log("🔗 Live feed CONNECTED")
        else:
            self.log("🔌 Live feed DISCONNECTED")

    def toggle_auto_record_live(self):
        """Toggle auto-recording for live games"""
        if self.auto_record_live.get():
            self.log("📹 Auto-record live games ENABLED")
        else:
            self.log("⏸️  Auto-record live games DISABLED")

    def toggle_bot(self):
        """Toggle bot on/off"""
        if self.bot_enabled.get():
            self.log(f"🤖 Bot ENABLED (strategy: {self.bot_strategy.get()})")
            for widget in self.bot_panel.winfo_children():
                widget.destroy()
            tk.Label(self.bot_panel, text=f"Bot: ENABLED", bg="#2d2d2d", fg="#00ff00", font=("Arial", 10, "bold")).pack(pady=5)
            tk.Label(self.bot_panel, text=f"Strategy: {self.bot_strategy.get()}", bg="#2d2d2d", fg="white").pack()
        else:
            self.log("⏹️  Bot DISABLED")
            for widget in self.bot_panel.winfo_children():
                widget.destroy()
            tk.Label(self.bot_panel, text="Bot: DISABLED", bg="#2d2d2d", fg="gray").pack(pady=10)

    def update_strategy(self):
        """Update bot strategy"""
        self.log(f"🎯 Bot strategy: {self.bot_strategy.get()}")
        if self.bot_enabled.get():
            self.toggle_bot()  # Refresh bot panel

    def toggle_playback(self):
        """Toggle playback play/pause"""
        self.log("⏯️  Play/Pause")

    def update_speed(self):
        """Update playback speed"""
        self.log(f"⏩ Speed: {self.playback_speed.get()}x")

    def update_panels(self):
        """Update panel visibility"""
        self.status_panel.pack_forget() if not self.show_status.get() else self.status_panel.pack(fill=tk.BOTH, pady=5)
        self.trading_panel.pack_forget() if not self.show_trading.get() else self.trading_panel.pack(fill=tk.BOTH, pady=5)
        self.bot_panel.pack_forget() if not self.show_bot.get() else self.bot_panel.pack(fill=tk.BOTH, pady=5)
        self.chart_panel.pack_forget() if not self.show_chart.get() else self.chart_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.log(f"👁️  Panels updated")

    def update_theme(self):
        """Update UI theme"""
        self.log(f"🎨 Theme: {self.theme.get()}")
        messagebox.showinfo("Theme", f"Theme changed to: {self.theme.get()}\n(mockup only)")

    def open_recording(self):
        """Open recording file dialog"""
        self.log("📂 Open recording dialog")
        messagebox.showinfo("Open Recording", "File dialog would open here")

    def open_recordings_folder(self):
        """Open recordings folder"""
        self.log("📁 Open recordings folder: /home/nomad/rugs_recordings/")
        messagebox.showinfo("Recordings Folder", "/home/nomad/rugs_recordings/")

    def clear_stats(self):
        """Clear recording statistics"""
        self.session_games = 0
        self.total_size_mb = 0.0
        self.log("🗑️  Recording statistics cleared")

    def show_shortcuts(self):
        """Show keyboard shortcuts dialog"""
        shortcuts = """
Keyboard Shortcuts
==================

Playback:
  Space       Play/Pause
  Ctrl+S      Stop
  →           Next game
  ←           Previous game
  Ctrl+J      Jump to tick

Recording:
  Ctrl+R      Toggle recording

Live Feed:
  L           Toggle live feed

Bot:
  B           Toggle bot

View:
  F1          Toggle status panel
  F2          Toggle chart
  F3          Toggle trading panel
  F4          Toggle bot panel

General:
  Ctrl+O      Open recording
  Ctrl+Q      Exit
        """
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)

    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About REPLAYER", "REPLAYER - UI Mockup\nVersion 1.0\n\nMenu system design prototype")

    def log(self, message):
        """Add message to event log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)


def main():
    """Run mockup"""
    root = tk.Tk()
    app = REPLAYERMockup(root)
    root.mainloop()


if __name__ == "__main__":
    main()
