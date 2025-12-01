#!/usr/bin/env python3
"""
Chart Colors Example
Shows how to coordinate custom Chart widget colors with ttkbootstrap themes
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from decimal import Decimal
import math


# Theme-coordinated color palettes
THEME_CHART_COLORS = {
    'cyborg': {
        'background': '#060606',
        'grid': '#1a1a1a',
        'grid_major': '#2a2a2a',
        'text': '#888888',
        'text_bright': '#FFFFFF',
        'price_up': '#63C971',      # Neon green
        'price_down': '#CC0000',     # Red
        'price_neutral': '#2A9FD6',  # Cyan
    },
    'darkly': {
        'background': '#222222',
        'grid': '#2a2a2a',
        'grid_major': '#3a3a3a',
        'text': '#888888',
        'text_bright': '#FFFFFF',
        'price_up': '#00BC8C',       # Teal green
        'price_down': '#E74C3C',     # Red
        'price_neutral': '#375A7F',  # Blue
    },
    'superhero': {
        'background': '#2B3E50',
        'grid': '#3a4d60',
        'grid_major': '#4a5d70',
        'text': '#999999',
        'text_bright': '#FFFFFF',
        'price_up': '#5CB85C',       # Green
        'price_down': '#D9534F',     # Red
        'price_neutral': '#4C9BE8',  # Blue
    },
    'solar': {
        'background': '#002B36',
        'grid': '#073642',
        'grid_major': '#0a4652',
        'text': '#586e75',
        'text_bright': '#93A1A1',
        'price_up': '#859900',       # Olive
        'price_down': '#DC322F',     # Red
        'price_neutral': '#268BD2',  # Blue
    },
    # Default fallback
    'default': {
        'background': '#0a0a0a',
        'grid': '#1a1a1a',
        'grid_major': '#2a2a2a',
        'text': '#666666',
        'text_bright': '#ffffff',
        'price_up': '#00ff88',
        'price_down': '#ff3366',
        'price_neutral': '#ffcc00',
    }
}


class SimpleChartWidget(tk.Canvas):
    """
    Simplified chart widget demonstrating theme coordination
    Based on your existing ChartWidget
    """
    
    def __init__(self, parent, width=600, height=300, **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            highlightthickness=0,
            **kwargs
        )
        
        self.width = width
        self.height = height
        
        # Default to cyborg colors
        self.colors = THEME_CHART_COLORS['cyborg'].copy()
        self.config(bg=self.colors['background'])
        
        # Sample price data (simulating 1x to 2x progression)
        self.price_data = [1.0 + (x * 0.01) for x in range(100)]
        
        self.draw()
    
    def update_theme(self, theme_name: str):
        """
        Update chart colors to match theme
        
        This method should be called whenever the app theme changes
        """
        # Get colors for this theme, fallback to default
        self.colors = THEME_CHART_COLORS.get(theme_name, THEME_CHART_COLORS['default']).copy()
        
        # Update canvas background
        self.config(bg=self.colors['background'])
        
        # Redraw with new colors
        self.draw()
        
        print(f"Chart theme updated to: {theme_name}")
    
    def draw(self):
        """Draw simple price chart"""
        self.delete('all')
        
        padding = 50
        chart_width = self.width - 2 * padding
        chart_height = self.height - 2 * padding
        
        # Draw background
        self.create_rectangle(
            padding, padding,
            self.width - padding, self.height - padding,
            fill=self.colors['background'],
            outline=''
        )
        
        # Draw grid
        for i in range(5):
            y = padding + (i * chart_height / 4)
            self.create_line(
                padding, y,
                self.width - padding, y,
                fill=self.colors['grid'],
                width=1
            )
        
        # Draw price line
        if len(self.price_data) > 1:
            points = []
            for i, price in enumerate(self.price_data):
                x = padding + (i * chart_width / (len(self.price_data) - 1))
                # Simple linear scale for demo
                y_norm = (price - 1.0) / 1.0  # Normalize to 0-1
                y = (self.height - padding) - (y_norm * chart_height)
                points.extend([x, y])
            
            # Draw line with color based on trend
            for i in range(0, len(points) - 2, 2):
                x1, y1 = points[i], points[i+1]
                x2, y2 = points[i+2], points[i+3]
                
                # Determine color based on movement
                if y2 < y1:  # Price going up (y inverted)
                    color = self.colors['price_up']
                elif y2 > y1:  # Price going down
                    color = self.colors['price_down']
                else:
                    color = self.colors['price_neutral']
                
                self.create_line(
                    x1, y1, x2, y2,
                    fill=color,
                    width=2
                )
        
        # Draw price labels
        for price in [1.0, 1.25, 1.5, 1.75, 2.0]:
            y_norm = (price - 1.0) / 1.0
            y = (self.height - padding) - (y_norm * chart_height)
            
            self.create_text(
                padding - 10, y,
                text=f"{price:.2f}x",
                fill=self.colors['text_bright'],
                anchor='e',
                font=('Arial', 9)
            )
        
        # Draw title
        self.create_text(
            self.width / 2, 20,
            text="Price Chart (Theme-Coordinated Colors)",
            fill=self.colors['text_bright'],
            font=('Arial', 12, 'bold')
        )


class ChartColorsExample:
    """
    Demo showing how to keep chart colors synchronized with app theme
    """
    
    def __init__(self):
        self.root = ttk.Window(themename='cyborg')
        self.root.title("Chart Colors Example")
        self.root.geometry("800x600")
        
        self.create_ui()
    
    def create_ui(self):
        """Create UI with themed chart"""
        
        # Header with theme selector
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill=X)
        
        ttk.Label(
            header,
            text="Theme:",
            font=('Arial', 12, 'bold')
        ).pack(side=LEFT, padx=5)
        
        self.theme_var = ttk.StringVar(value='cyborg')
        
        dark_themes = ['cyborg', 'darkly', 'superhero', 'solar']
        
        theme_combo = ttk.Combobox(
            header,
            textvariable=self.theme_var,
            values=dark_themes,
            state='readonly',
            width=15
        )
        theme_combo.pack(side=LEFT, padx=5)
        theme_combo.bind('<<ComboboxSelected>>', self.on_theme_change)
        
        # Main content
        content = ttk.Frame(self.root, padding=20)
        content.pack(fill=BOTH, expand=YES)
        
        # Chart widget
        self.chart = SimpleChartWidget(content, width=700, height=400)
        self.chart.pack(pady=10)
        
        # Color info panel
        self.color_info = ttk.LabelFrame(content, text="Current Theme Colors", padding=10)
        self.color_info.pack(fill=X, pady=10)
        
        self.color_labels = {}
        for color_name in ['background', 'price_up', 'price_down', 'price_neutral']:
            frame = ttk.Frame(self.color_info)
            frame.pack(fill=X, pady=2)
            
            ttk.Label(frame, text=f"{color_name}:", width=15).pack(side=LEFT)
            
            label = ttk.Label(frame, text="", font=('Courier', 10))
            label.pack(side=LEFT, padx=10)
            
            self.color_labels[color_name] = label
        
        self.update_color_display()
        
        # Instructions
        info_text = """
        This example shows how to coordinate your custom ChartWidget colors
        with the active ttkbootstrap theme.
        
        Key Implementation:
        1. Define THEME_CHART_COLORS mapping (see source code)
        2. Add update_theme(theme_name) method to ChartWidget
        3. Call chart.update_theme() when app theme changes
        
        Try switching themes above - notice how chart colors change instantly
        to match the overall app aesthetic!
        """
        
        ttk.Label(
            content,
            text=info_text,
            justify=LEFT,
            wraplength=700
        ).pack(pady=10)
    
    def on_theme_change(self, event=None):
        """Handle theme change"""
        new_theme = self.theme_var.get()
        
        # Update app theme
        self.root.style.theme_use(new_theme)
        
        # Update chart colors - THIS IS THE KEY STEP
        self.chart.update_theme(new_theme)
        
        # Update color display
        self.update_color_display()
    
    def update_color_display(self):
        """Update color value labels"""
        for color_name, label in self.color_labels.items():
            color_value = self.chart.colors.get(color_name, '#000000')
            label.config(text=color_value)
    
    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = ChartColorsExample()
    app.run()
