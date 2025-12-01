#!/usr/bin/env python3
"""
ttkbootstrap Theme Preview
Quick visual demo of all available themes
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

class ThemePreview:
    def __init__(self):
        self.root = ttk.Window(themename='cyborg')
        self.root.title("ttkbootstrap Theme Preview")
        self.root.geometry("800x600")
        
        self.create_ui()
        
    def create_ui(self):
        # Theme selector at top
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill=X)
        
        ttk.Label(header, text="Select Theme:", font=('Arial', 12, 'bold')).pack(side=LEFT, padx=5)
        
        self.theme_var = ttk.StringVar(value='cyborg')
        theme_combo = ttk.Combobox(
            header,
            textvariable=self.theme_var,
            values=self.root.style.theme_names(),
            state='readonly',
            width=20
        )
        theme_combo.pack(side=LEFT, padx=5)
        theme_combo.bind('<<ComboboxSelected>>', self.change_theme)
        
        # Main content area
        content = ttk.Frame(self.root, padding=20)
        content.pack(fill=BOTH, expand=YES)
        
        # Sample widgets
        ttk.Label(content, text="Sample UI Components", font=('Arial', 16, 'bold')).pack(pady=10)
        
        # Buttons
        btn_frame = ttk.Frame(content)
        btn_frame.pack(fill=X, pady=10)
        
        ttk.Label(btn_frame, text="Buttons:", font=('Arial', 10, 'bold')).pack(anchor=W, pady=5)
        
        btn_row = ttk.Frame(btn_frame)
        btn_row.pack(fill=X)
        
        ttk.Button(btn_row, text="Primary", bootstyle=PRIMARY).pack(side=LEFT, padx=5)
        ttk.Button(btn_row, text="Success", bootstyle=SUCCESS).pack(side=LEFT, padx=5)
        ttk.Button(btn_row, text="Info", bootstyle=INFO).pack(side=LEFT, padx=5)
        ttk.Button(btn_row, text="Warning", bootstyle=WARNING).pack(side=LEFT, padx=5)
        ttk.Button(btn_row, text="Danger", bootstyle=DANGER).pack(side=LEFT, padx=5)
        
        # Entry and Labels
        input_frame = ttk.Frame(content)
        input_frame.pack(fill=X, pady=10)
        
        ttk.Label(input_frame, text="Input Fields:", font=('Arial', 10, 'bold')).pack(anchor=W, pady=5)
        
        ttk.Label(input_frame, text="Username:").pack(anchor=W, padx=20)
        ttk.Entry(input_frame).pack(fill=X, padx=20, pady=2)
        
        ttk.Label(input_frame, text="Password:").pack(anchor=W, padx=20, pady=(10, 0))
        ttk.Entry(input_frame, show="*").pack(fill=X, padx=20, pady=2)
        
        # Progress bar
        progress_frame = ttk.Frame(content)
        progress_frame.pack(fill=X, pady=10)
        
        ttk.Label(progress_frame, text="Progress:", font=('Arial', 10, 'bold')).pack(anchor=W, pady=5)
        
        pb = ttk.Progressbar(progress_frame, mode='determinate', value=65, bootstyle=SUCCESS)
        pb.pack(fill=X, padx=20)
        
        # Scale
        scale_frame = ttk.Frame(content)
        scale_frame.pack(fill=X, pady=10)
        
        ttk.Label(scale_frame, text="Scale:", font=('Arial', 10, 'bold')).pack(anchor=W, pady=5)
        ttk.Scale(scale_frame, from_=0, to=100, value=50, bootstyle=INFO).pack(fill=X, padx=20)
        
        # Info panel
        info_frame = ttk.LabelFrame(content, text="Game Stats", padding=15)
        info_frame.pack(fill=BOTH, expand=YES, pady=10)
        
        ttk.Label(info_frame, text="Tick: 100", font=('Arial', 11)).pack(anchor=W, pady=2)
        ttk.Label(info_frame, text="Price: 1.5x", font=('Arial', 11)).pack(anchor=W, pady=2)
        ttk.Label(info_frame, text="Balance: 1.234 SOL", font=('Arial', 11)).pack(anchor=W, pady=2)
        ttk.Label(info_frame, text="P&L: +0.123 SOL", font=('Arial', 11), bootstyle=SUCCESS).pack(anchor=W, pady=2)
        
    def change_theme(self, event=None):
        theme = self.theme_var.get()
        self.root.style.theme_use(theme)
        
    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    app = ThemePreview()
    app.run()
