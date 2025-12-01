#!/usr/bin/env python3
"""
Basic Integration Example
Shows minimal code changes needed to add ttkbootstrap theming
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

class BasicIntegrationExample:
    """
    Minimal example showing how to integrate ttkbootstrap
    into an existing tkinter application
    """
    
    def __init__(self):
        # CHANGE 1: Use ttk.Window instead of tk.Tk()
        # OLD: self.root = tk.Tk()
        # NEW:
        self.root = ttk.Window(themename='cyborg')
        
        self.root.title("Basic Integration Example")
        self.root.geometry("600x400")
        
        self.create_ui()
    
    def create_ui(self):
        """Create UI with themed widgets"""
        
        # Main container
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)
        
        # Title
        ttk.Label(
            main_frame,
            text="ttkbootstrap Integration Example",
            font=('Arial', 16, 'bold')
        ).pack(pady=10)
        
        # Status panel (simulating game stats)
        status_frame = ttk.LabelFrame(main_frame, text="Game Status", padding=15)
        status_frame.pack(fill=X, pady=10)
        
        # CHANGE 2: Use ttk.Label instead of tk.Label
        # OLD: tk.Label(status_frame, text="Tick: 0", bg='#1a1a1a', fg='white')
        # NEW: Just use ttk.Label - theme handles colors
        ttk.Label(status_frame, text="Tick: 100", font=('Arial', 11)).pack(anchor=W, pady=2)
        ttk.Label(status_frame, text="Price: 1.5x", font=('Arial', 11)).pack(anchor=W, pady=2)
        ttk.Label(status_frame, text="Balance: 1.234 SOL", font=('Arial', 11)).pack(anchor=W, pady=2)
        
        # CHANGE 3: Use bootstyle parameter for semantic colors
        # OLD: tk.Label(..., fg='#00ff88')
        # NEW: ttk.Label(..., bootstyle='success')
        ttk.Label(
            status_frame,
            text="P&L: +0.123 SOL",
            font=('Arial', 11),
            bootstyle=SUCCESS  # Green for positive
        ).pack(anchor=W, pady=2)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=X, pady=10)
        
        # CHANGE 4: Use ttk.Button with bootstyle
        # OLD: tk.Button(..., bg='#444444', fg='white')
        # NEW: ttk.Button(..., bootstyle='primary')
        ttk.Button(
            button_frame,
            text="Buy",
            bootstyle=SUCCESS,
            command=lambda: print("Buy clicked")
        ).pack(side=LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Sell",
            bootstyle=DANGER,
            command=lambda: print("Sell clicked")
        ).pack(side=LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Bot Toggle",
            bootstyle=INFO,
            command=lambda: print("Bot toggled")
        ).pack(side=LEFT, padx=5)
        
        # Info text
        info_text = """
        Key Changes Made:
        
        1. Changed tk.Tk() → ttk.Window(themename='cyborg')
        2. Changed tk.Label → ttk.Label (removed bg/fg params)
        3. Changed tk.Button → ttk.Button (use bootstyle)
        4. Theme handles all colors automatically
        
        That's it! Your app now has professional theming.
        """
        
        ttk.Label(
            main_frame,
            text=info_text,
            justify=LEFT,
            wraplength=500
        ).pack(pady=20)
    
    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = BasicIntegrationExample()
    app.run()
