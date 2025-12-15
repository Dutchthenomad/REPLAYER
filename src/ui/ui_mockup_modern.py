import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

class ModernReplayerUI(ttk.Window):
    def __init__(self):
        super().__init__(themename="cyborg")
        self.title("REPLAYER - Modern UI Prototype")
        self.geometry("1200x800")
        
        # Define custom styles if needed (though bootstrap themes are usually sufficient)
        # We can override specific colors if the theme's "success" isn't "green enough"
        # But cyborg's success is quite green.
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main Layout: Top Bar, Middle (Chart + Side Panel), Bottom (Log/Status)
        
        # --- Top Status Bar ---
        self.create_status_bar()
        
        # --- Main Container ---
        main_container = ttk.Frame(self, padding=10)
        main_container.pack(fill=BOTH, expand=YES)
        
        # Left: Chart Area (Placeholder)
        self.create_chart_area(main_container)
        
        # Right: Control Panel
        self.create_control_panel(main_container)
        
    def create_status_bar(self):
        status_frame = ttk.Frame(self, padding=(10, 5), bootstyle="secondary")
        status_frame.pack(fill=X)
        
        # Metrics with distinct styling
        metrics = [
            ("TICK", "1337", "info"),
            ("PRICE", "2.4500 X", "light"),
            ("PHASE", "LIVE", "success"),
            ("BALANCE", "10.500 SOL", "warning"),
            ("P&L", "+0.25 SOL", "success")
        ]
        
        for label, value, color in metrics:
            container = ttk.Frame(status_frame)
            container.pack(side=LEFT, padx=20)
            
            ttk.Label(container, text=label, font=("Roboto", 8, "bold"), bootstyle="secondary").pack(anchor=W)
            ttk.Label(container, text=value, font=("Roboto", 12, "bold"), bootstyle=color).pack(anchor=W)
            
        # Connection Status
        ttk.Label(status_frame, text="● Connected", bootstyle="success").pack(side=RIGHT, padx=10)

    def create_chart_area(self, parent):
        chart_frame = ttk.Labelframe(parent, text=" Price Action ", padding=10)
        chart_frame.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 10))
        
        # Placeholder for chart
        canvas = tk.Canvas(chart_frame, bg="#111", highlightthickness=0)
        canvas.pack(fill=BOTH, expand=YES)
        
        # Draw some dummy chart data
        w, h = 800, 600
        points = [
            (50, 500), (100, 480), (150, 490), (200, 450), 
            (250, 400), (300, 420), (350, 350), (400, 300),
            (450, 280), (500, 200), (550, 150), (600, 100)
        ]
        
        # Grid lines
        for i in range(0, h, 50):
            canvas.create_line(0, i, w, i, fill="#222")
        for i in range(0, w, 50):
            canvas.create_line(i, 0, i, h, fill="#222")
            
        # Line
        for i in range(len(points) - 1):
            canvas.create_line(points[i], points[i+1], fill="#00ff00", width=2)
            
        # Current Price Indicator
        last_x, last_y = points[-1]
        canvas.create_oval(last_x-4, last_y-4, last_x+4, last_y+4, fill="#fff")
        canvas.create_line(0, last_y, w, last_y, fill="#ffffff", dash=(2, 4))

    def create_control_panel(self, parent):
        panel_width = 350
        panel = ttk.Frame(parent, width=panel_width)
        panel.pack(side=RIGHT, fill=Y)
        panel.pack_propagate(False) # Enforce width
        
        # --- Playback Controls ---
        playback_frame = ttk.Labelframe(panel, text=" Playback ", padding=10)
        playback_frame.pack(fill=X, pady=(0, 10))
        
        pb_btns = ttk.Frame(playback_frame)
        pb_btns.pack(fill=X)
        
        ttk.Button(pb_btns, text="⏮", bootstyle="secondary-outline", width=4).pack(side=LEFT, padx=2)
        ttk.Button(pb_btns, text="▶", bootstyle="primary", width=6).pack(side=LEFT, padx=2)
        ttk.Button(pb_btns, text="⏭", bootstyle="secondary-outline", width=4).pack(side=LEFT, padx=2)
        
        ttk.Label(pb_btns, text="1.0x", font=("bold"), bootstyle="light").pack(side=RIGHT, padx=5)
        
        # Slider
        ttk.Scale(playback_frame, from_=0, to=100, value=75).pack(fill=X, pady=5)
        
        # --- Trading Controls ---
        trade_frame = ttk.Labelframe(panel, text=" Trading ", padding=10)
        trade_frame.pack(fill=X, pady=10)
        
        # Bet Amount
        ttk.Label(trade_frame, text="Wager Amount (SOL)").pack(anchor=W)
        
        amt_row = ttk.Frame(trade_frame)
        amt_row.pack(fill=X, pady=5)
        
        entry = ttk.Entry(amt_row, font=("Roboto", 14))
        entry.insert(0, "0.5")
        entry.pack(side=LEFT, fill=X, expand=YES)
        
        # Quick Actions
        quick_row = ttk.Frame(trade_frame)
        quick_row.pack(fill=X, pady=5)
        for val in ["MIN", "1/2", "2X", "MAX"]:
            ttk.Button(quick_row, text=val, bootstyle="secondary-outline", width=5).pack(side=LEFT, padx=2, expand=YES)

        # Main Action Buttons
        # We use 'success' for Buy (Green) and 'danger' for Sell (Red)
        
        btn_grid = ttk.Frame(trade_frame, padding=(0, 10))
        btn_grid.pack(fill=X)
        
        # Buy Button
        self.create_big_button(btn_grid, "BUY", "UP", "success").pack(fill=X, pady=5)
        
        # Sell Button (Disabled look vs Enabled look)
        self.create_big_button(btn_grid, "SELL", "CLOSE", "danger").pack(fill=X, pady=5)
        
        # Sidebet
        ttk.Separator(trade_frame).pack(fill=X, pady=10)
        self.create_big_button(trade_frame, "SIDE BET", "5x WIN", "info").pack(fill=X, pady=5)

        # --- Bot Controls ---
        bot_frame = ttk.Labelframe(panel, text=" Auto-Pilot ", padding=10)
        bot_frame.pack(fill=X, pady=10, expand=YES, anchor=N)
        
        ttk.Label(bot_frame, text="Strategy").pack(anchor=W)
        ttk.Combobox(bot_frame, values=["Sniper v1", "Trend Follower", "Scalper"], state="readonly").pack(fill=X, pady=5)
        
        toggle_row = ttk.Frame(bot_frame, padding=(0, 10))
        toggle_row.pack(fill=X)
        
        ttk.Checkbutton(toggle_row, text="Enable Bot", bootstyle="round-toggle").pack(side=LEFT)
        ttk.Label(toggle_row, text="Idle", bootstyle="secondary").pack(side=RIGHT)

    def create_big_button(self, parent, text, subtext, style):
        # Custom composite button for a "big" click area
        btn = ttk.Button(parent, bootstyle=style, padding=15)
        # Note: ttk.Button doesn't easily support multi-line text with different fonts natively 
        # without compound images or custom layout.
        # For this mockup, we'll stick to simple text but styled boldly.
        btn.configure(text=f"{text}  |  {subtext}")
        return btn

if __name__ == "__main__":
    app = ModernReplayerUI()
    app.mainloop()
