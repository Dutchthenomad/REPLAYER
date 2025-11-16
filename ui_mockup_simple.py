#!/usr/bin/env python3
"""
REPLAYER UI Mockup - Menu Bar Only
===================================

Simple mockup that ONLY adds a menu bar to the existing REPLAYER UI.
No other changes - just testing the menu structure.

Usage: python3 ui_mockup_simple.py
"""

import tkinter as tk
from tkinter import messagebox


class SimpleMenuMockup:
    """Mockup showing ONLY menu bar addition to current REPLAYER UI"""

    def __init__(self, root):
        self.root = root
        self.root.title("REPLAYER - Menu Bar Mockup")
        self.root.geometry("1200x800")

        # State variables (same as proposed)
        self.recording_enabled = tk.BooleanVar(value=True)  # Default: ON
        self.live_feed_connected = tk.BooleanVar(value=False)
        self.bot_enabled = tk.BooleanVar(value=False)

        # ===== ADD MENU BAR (ONLY NEW THING) =====
        self._create_menu_bar()

        # ===== EXISTING REPLAYER UI (unchanged) =====
        self._create_existing_ui()

    def _create_menu_bar(self):
        """Create menu bar - THIS IS THE ONLY NEW ADDITION"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Recording...", command=self.placeholder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Playback Menu
        playback_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Playback", menu=playback_menu)
        playback_menu.add_command(label="Play/Pause", command=self.placeholder)
        playback_menu.add_command(label="Stop", command=self.placeholder)

        # Recording Menu
        recording_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Recording", menu=recording_menu)
        recording_menu.add_checkbutton(
            label="Enable Recording",
            variable=self.recording_enabled,
            command=self.toggle_recording
        )
        recording_menu.add_separator()
        recording_menu.add_command(label="Open Recordings Folder", command=self.placeholder)

        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Show/Hide Panels...", command=self.placeholder)

        # Bot Menu
        bot_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Bot", menu=bot_menu)
        bot_menu.add_checkbutton(label="Enable Bot", variable=self.bot_enabled, command=self.toggle_bot)

        # Live Feed Menu
        live_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Live Feed", menu=live_menu)
        live_menu.add_checkbutton(
            label="Connect to Live Feed",
            variable=self.live_feed_connected,
            command=self.toggle_live_feed
        )

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def _create_existing_ui(self):
        """Recreate EXISTING REPLAYER UI - NO CHANGES"""
        # This mimics the current REPLAYER layout exactly

        # ========== ROW 1: STATUS BAR ==========
        status_bar = tk.Frame(self.root, bg='#000000', height=30)
        status_bar.pack(fill=tk.X)
        status_bar.pack_propagate(False)

        tk.Label(status_bar, text="TICK: 0", font=('Arial', 11, 'bold'), bg='#000000', fg='white').pack(side=tk.LEFT, padx=10)
        tk.Label(status_bar, text="PRICE: 1.0000 X", font=('Arial', 11, 'bold'), bg='#000000', fg='#00ff00').pack(side=tk.LEFT, padx=10)
        tk.Label(status_bar, text="PHASE: ACTIVE", font=('Arial', 11, 'bold'), bg='#000000', fg='#00ff00').pack(side=tk.LEFT, padx=10)
        tk.Label(status_bar, text="BALANCE: 1.000 SOL", font=('Arial', 11, 'bold'), bg='#000000', fg='white').pack(side=tk.LEFT, padx=10)

        # ========== ROW 2: MAIN CONTENT ==========
        main_container = tk.Frame(self.root, bg='#1a1a1a')
        main_container.pack(fill=tk.BOTH, expand=True)

        # LEFT PANEL: Trading Controls
        left_panel = tk.Frame(main_container, bg='#2d2d30', width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        left_panel.pack_propagate(False)

        tk.Label(left_panel, text="TRADING PANEL", bg='#2d2d30', fg='white', font=('Arial', 12, 'bold')).pack(pady=10)
        tk.Label(left_panel, text="Position: None", bg='#2d2d30', fg='gray').pack(pady=5)
        tk.Label(left_panel, text="P&L: 0.000 SOL", bg='#2d2d30', fg='gray').pack(pady=5)

        # CENTER PANEL: Chart
        chart_frame = tk.Frame(main_container, bg='#1a1a1a')
        chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(chart_frame, text="PRICE CHART", bg='#1a1a1a', fg='white', font=('Arial', 14, 'bold')).pack(pady=20)

        # Simulate chart area
        chart_canvas = tk.Canvas(chart_frame, bg='#0d0d0d', highlightthickness=1, highlightbackground='#444')
        chart_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Recording indicator (if enabled)
        if self.recording_enabled.get():
            chart_canvas.create_oval(15, 15, 25, 25, fill="red", outline="red")
            chart_canvas.create_text(45, 20, text="REC", fill="red", font=("Arial", 10, "bold"))

        # RIGHT PANEL: Bot Controls
        right_panel = tk.Frame(main_container, bg='#2d2d30', width=250)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        right_panel.pack_propagate(False)

        tk.Label(right_panel, text="BOT PANEL", bg='#2d2d30', fg='white', font=('Arial', 12, 'bold')).pack(pady=10)
        tk.Label(right_panel, text="Bot: Disabled", bg='#2d2d30', fg='gray').pack(pady=5)

        # ========== ROW 3: PLAYBACK CONTROLS ==========
        controls_frame = tk.Frame(self.root, bg='#1a1a1a', height=60)
        controls_frame.pack(fill=tk.X)
        controls_frame.pack_propagate(False)

        tk.Button(controls_frame, text="◀◀", width=5, command=self.placeholder).pack(side=tk.LEFT, padx=5, pady=10)
        tk.Button(controls_frame, text="▶", width=10, command=self.placeholder).pack(side=tk.LEFT, padx=5, pady=10)
        tk.Button(controls_frame, text="▶▶", width=5, command=self.placeholder).pack(side=tk.LEFT, padx=5, pady=10)
        tk.Label(controls_frame, text="Speed: 1.0x", bg='#1a1a1a', fg='white').pack(side=tk.LEFT, padx=20)

    # ===== Menu Callbacks =====

    def toggle_recording(self):
        """Toggle recording"""
        status = "ENABLED" if self.recording_enabled.get() else "DISABLED"
        messagebox.showinfo("Recording", f"Recording {status}")

    def toggle_bot(self):
        """Toggle bot"""
        status = "ENABLED" if self.bot_enabled.get() else "DISABLED"
        messagebox.showinfo("Bot", f"Bot {status}")

    def toggle_live_feed(self):
        """Toggle live feed"""
        status = "CONNECTED" if self.live_feed_connected.get() else "DISCONNECTED"
        messagebox.showinfo("Live Feed", f"Live Feed {status}")

    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About", "REPLAYER Menu Bar Mockup\n\nThis shows ONLY the menu bar addition\nto the existing UI.")

    def placeholder(self):
        """Placeholder for menu items"""
        messagebox.showinfo("Menu", "This menu item is not yet implemented in mockup")


def main():
    """Run mockup"""
    root = tk.Tk()
    app = SimpleMenuMockup(root)
    root.mainloop()


if __name__ == "__main__":
    main()
