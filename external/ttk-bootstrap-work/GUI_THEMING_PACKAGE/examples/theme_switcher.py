#!/usr/bin/env python3
"""
Theme Switcher Example
Shows how to implement runtime theme switching with persistence
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import json
from pathlib import Path


class ThemeSwitcherExample:
    """
    Example showing theme switching implementation
    with JSON-based persistence
    """
    
    def __init__(self):
        # Load saved theme preference
        saved_theme = self.load_theme_preference()
        
        # Create window with saved theme
        self.root = ttk.Window(themename=saved_theme)
        self.root.title("Theme Switcher Example")
        self.root.geometry("700x500")
        
        # Handle window close to save theme
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.create_ui()
    
    def create_ui(self):
        """Create UI with theme switcher"""
        
        # Header with theme selector
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill=X)
        
        ttk.Label(
            header,
            text="Select Theme:",
            font=('Arial', 12, 'bold')
        ).pack(side=LEFT, padx=5)
        
        # Theme combobox
        self.theme_var = ttk.StringVar(value=self.root.style.theme_use())
        
        # Filter to just dark themes for HUD aesthetic
        dark_themes = ['cyborg', 'darkly', 'superhero', 'solar', 'vapor']
        available_dark = [t for t in dark_themes if t in self.root.style.theme_names()]
        
        self.theme_combo = ttk.Combobox(
            header,
            textvariable=self.theme_var,
            values=available_dark,
            state='readonly',
            width=15
        )
        self.theme_combo.pack(side=LEFT, padx=5)
        self.theme_combo.bind('<<ComboboxSelected>>', self.on_theme_change)
        
        # Main content
        content = ttk.Frame(self.root, padding=20)
        content.pack(fill=BOTH, expand=YES)
        
        # Sample content that changes with theme
        ttk.Label(
            content,
            text="Theme Switching Demo",
            font=('Arial', 16, 'bold')
        ).pack(pady=10)
        
        # Status panel
        status_frame = ttk.LabelFrame(content, text="Game Status", padding=15)
        status_frame.pack(fill=X, pady=10)
        
        self.tick_label = ttk.Label(status_frame, text="Tick: 100", font=('Arial', 11))
        self.tick_label.pack(anchor=W, pady=2)
        
        self.price_label = ttk.Label(status_frame, text="Price: 1.5x", font=('Arial', 11))
        self.price_label.pack(anchor=W, pady=2)
        
        self.balance_label = ttk.Label(status_frame, text="Balance: 1.234 SOL", font=('Arial', 11))
        self.balance_label.pack(anchor=W, pady=2)
        
        self.pnl_label = ttk.Label(
            status_frame,
            text="P&L: +0.123 SOL",
            font=('Arial', 11),
            bootstyle=SUCCESS
        )
        self.pnl_label.pack(anchor=W, pady=2)
        
        # Buttons
        button_frame = ttk.Frame(content)
        button_frame.pack(fill=X, pady=10)
        
        ttk.Button(button_frame, text="Primary", bootstyle=PRIMARY).pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="Success", bootstyle=SUCCESS).pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="Info", bootstyle=INFO).pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="Warning", bootstyle=WARNING).pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="Danger", bootstyle=DANGER).pack(side=LEFT, padx=5)
        
        # Current theme info
        self.theme_info_label = ttk.Label(
            content,
            text=self.get_theme_info(),
            justify=LEFT,
            wraplength=600
        )
        self.theme_info_label.pack(pady=20)
    
    def on_theme_change(self, event=None):
        """Handle theme change event"""
        new_theme = self.theme_var.get()
        
        # Apply new theme
        self.root.style.theme_use(new_theme)
        
        # Update info label
        self.theme_info_label.config(text=self.get_theme_info())
        
        # Save preference
        self.save_theme_preference(new_theme)
        
        print(f"Theme changed to: {new_theme}")
    
    def get_theme_info(self):
        """Get information about current theme"""
        current_theme = self.root.style.theme_use()
        colors = self.root.style.colors
        
        return f"""
Current Theme: {current_theme.upper()}

Colors:
• Primary:     {colors.primary}
• Success:     {colors.success}
• Danger:      {colors.danger}
• Background:  {colors.bg}
• Foreground:  {colors.fg}

Try switching themes above to see instant changes!
Theme preference will be saved and restored next time.
        """.strip()
    
    def load_theme_preference(self):
        """Load saved theme preference from JSON config"""
        config_file = Path.home() / '.theme_switcher_demo' / 'config.json'
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    theme = config.get('theme', 'cyborg')
                    print(f"Loaded saved theme: {theme}")
                    return theme
            except Exception as e:
                print(f"Error loading theme preference: {e}")
        
        # Default to cyborg
        return 'cyborg'
    
    def save_theme_preference(self, theme_name: str):
        """Save theme preference to JSON config"""
        config_file = Path.home() / '.theme_switcher_demo' / 'config.json'
        config_file.parent.mkdir(exist_ok=True)
        
        try:
            with open(config_file, 'w') as f:
                json.dump({'theme': theme_name}, f, indent=2)
            print(f"Saved theme preference: {theme_name}")
        except Exception as e:
            print(f"Error saving theme preference: {e}")
    
    def on_closing(self):
        """Handle window close event"""
        # Save current theme before closing
        current_theme = self.root.style.theme_use()
        self.save_theme_preference(current_theme)
        
        # Close window
        self.root.destroy()
    
    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = ThemeSwitcherExample()
    app.run()
