import tkinter as tk
import math

# Chart Colors
COLOR_BG_DARK = "#1e2832"       # Chart BG
COLOR_GRID_LINE = "#2d3b48"     # Grid
COLOR_TEXT_PRICE = "#ffd700"    # Gold
COLOR_CANDLE_UP = "#00e676"     # Green
COLOR_CANDLE_DOWN = "#ff3d00"   # Red

class RugsChartLog(tk.Canvas):
    """
    Logarithmic Chart for visualizing game data.
    Handles massive price ranges (1x to 50,000x+) using log10 scale.
    """
    def __init__(self, parent, width=800, height=400):
        super().__init__(parent, width=width, height=height, bg=COLOR_BG_DARK, highlightthickness=0)
        self.width = width
        self.height = height
        
        self.prices = []        # List of dicts: {'o', 'c', 'h', 'l'}
        self.current_price = 1.0
        self.history_size = 100 # Number of candles to show
        
        self.bind("<Configure>", self._on_resize)
        
    def _on_resize(self, event):
        self.width = event.width
        self.height = event.height
        self.draw_chart()
        
    def update_tick(self, price, is_new_candle=False):
        """
        Update the chart with a new price tick.
        """
        # Convert Decimal to float for chart operations
        price = float(price)

        if not self.prices:
             self.prices.append({'o': price, 'c': price, 'h': price, 'l': price})

        self.current_price = price

        if is_new_candle:
             self.prices.append({'o': price, 'c': price, 'h': price, 'l': price})
             if len(self.prices) > self.history_size:
                 self.prices.pop(0)
        else:
             c = self.prices[-1]
             c['c'] = price
             c['h'] = max(c['h'], price)
             c['l'] = min(c['l'], price)

        self.draw_chart()
        
    def reset(self):
        self.prices = []
        self.current_price = 1.0
        self.draw_chart()

    def get_y_log(self, price, min_log, range_log, draw_h):
        """Map price to Y pixel using Log10 scale"""
        # Safety floor for log10
        p = max(price, 0.001) 
        log_p = math.log10(p)
        
        # Normalized 0..1
        if range_log == 0: ratio = 0.5
        else: ratio = (log_p - min_log) / range_log
        
        # Invert Y (0 is top)
        return self.height - 50 - (ratio * draw_h)

    def draw_chart(self):
        self.delete("all")
        
        if not self.prices:
            return
            
        w, h = self.width, self.height
        draw_h = h - 100 # Padding for text/grid
        
        # 1. Determine Range
        vals = [p['h'] for p in self.prices] + [p['l'] for p in self.prices]
        if not vals: return
        
        max_val = max(vals)
        min_val = min(vals)
        
        # Ensure minimum visual range (at least 1 decade if flat)
        if max_val / max(min_val, 0.0001) < 2:
            min_val = max_val / 2
            
        # Padding
        min_base = min_val * 0.9
        max_base = max_val * 1.1
        
        # Log range
        min_log = math.log10(max(min_base, 0.001))
        max_log = math.log10(max(max_base, 0.001))
        range_log = max_log - min_log
        
        # 2. Grid Lines (Decades)
        # Generate powers of 10 dynamically based on range
        powers = [0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000, 100000]
        
        for p in powers:
            if p >= min_base and p <= max_base:
                y = self.get_y_log(p, min_log, range_log, draw_h)
                self.create_line(0, y, w, y, fill=COLOR_GRID_LINE, dash=(2, 4))
                self.create_text(20, y - 10, text=f"{p}x", fill="#5fa8d3", font=("Arial", 10), anchor="w")

        # 3. Draw Candles
        num_candles = len(self.prices)
        if num_candles == 0: return
        
        candle_w = (w - 60) / num_candles
        
        for i, p in enumerate(self.prices):
            x = 50 + i * candle_w
            
            y_open = self.get_y_log(p['o'], min_log, range_log, draw_h)
            y_close = self.get_y_log(p['c'], min_log, range_log, draw_h)
            y_high = self.get_y_log(p['h'], min_log, range_log, draw_h)
            y_low = self.get_y_log(p['l'], min_log, range_log, draw_h)
            
            color = COLOR_CANDLE_UP if p['c'] >= p['o'] else COLOR_CANDLE_DOWN
            
            # Wick
            self.create_line(x + candle_w/2, y_high, x + candle_w/2, y_low, fill=color)
            
            # Body
            pad = 1 if candle_w > 3 else 0
            if abs(y_open - y_close) < 1: 
                y_close = y_open + 1 # Min height
                
            self.create_rectangle(x + pad, y_open, x + candle_w - pad, y_close, fill=color, outline=color)

        # 4. Price Overlay
        price_txt = f"{self.current_price:,.4f}x"
        
        # Shadow (Black)
        self.create_text(w - 48, h - 88, text=price_txt, fill="black", font=("Comic Sans MS", 48, "bold"), anchor="e")
        # Main (Gold)
        self.create_text(w - 50, h - 90, text=price_txt, fill=COLOR_TEXT_PRICE, font=("Comic Sans MS", 48, "bold"), anchor="e")
