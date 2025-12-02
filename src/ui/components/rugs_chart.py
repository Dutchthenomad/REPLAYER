import tkinter as tk
import math

# Chart Colors
COLOR_BG_DARK = "#1e2832"       # Chart BG
COLOR_GRID_LINE = "#2d3b48"     # Grid
COLOR_TEXT_PRICE = "#ffd700"    # Gold
COLOR_CANDLE_UP = "#00e676"     # Green
COLOR_CANDLE_DOWN = "#ff3d00"   # Red
COLOR_PRESALE = "#ffcc00"       # Yellow/Gold for presale/waiting phases

class RugsChartLog(tk.Canvas):
    """
    Logarithmic Chart for visualizing game data.
    Handles massive price ranges (1x to 50,000x+) using log10 scale.
    """
    def __init__(self, parent, width=800, height=400):
        super().__init__(parent, width=width, height=height, bg=COLOR_BG_DARK, highlightthickness=0)
        self.width = width
        self.height = height
        
        self.prices = []        # List of dicts: {'o', 'c', 'h', 'l', 'phase'}
        self.current_price = 1.0
        self.current_phase = 'TRADING'  # Track current phase for yellow line
        self.history_size = 200 # Number of candles to show (increased for better density)
        self.visible_candles = 100  # How many candles to display (for zoom)
        self.max_candle_width = 8  # Cap candle width for visual consistency

        self.bind("<Configure>", self._on_resize)
        
    def _on_resize(self, event):
        self.width = event.width
        self.height = event.height
        self.draw_chart()
        
    def update_tick(self, price, is_new_candle=False, phase='TRADING'):
        """
        Update the chart with a new price tick.

        Args:
            price: Current price multiplier
            is_new_candle: Whether to start a new candle
            phase: Current game phase ('TRADING', 'WAITING', 'COOLDOWN', 'COUNTDOWN')
        """
        # Convert Decimal to float for chart operations
        price = float(price)
        self.current_phase = phase

        # Determine if this is a presale/waiting phase (yellow line)
        is_presale = phase in ('WAITING', 'COOLDOWN', 'COUNTDOWN', 'PRE_ROUND')

        if not self.prices:
            self.prices.append({'o': price, 'c': price, 'h': price, 'l': price, 'phase': phase})

        self.current_price = price

        if is_new_candle:
            self.prices.append({'o': price, 'c': price, 'h': price, 'l': price, 'phase': phase})
            if len(self.prices) > self.history_size:
                self.prices.pop(0)
        else:
            c = self.prices[-1]
            c['c'] = price
            c['h'] = max(c['h'], price)
            c['l'] = min(c['l'], price)
            c['phase'] = phase  # Update phase for current candle

        self.draw_chart()
        
    def reset(self):
        self.prices = []
        self.current_price = 1.0
        self.current_phase = 'TRADING'
        self.visible_candles = 100  # Reset zoom level
        self.draw_chart()

    # ========================================================================
    # ZOOM CONTROLS
    # ========================================================================

    def zoom_in(self):
        """Zoom in (show fewer candles, larger size)"""
        self.visible_candles = max(20, int(self.visible_candles * 0.7))
        self.draw_chart()

    def zoom_out(self):
        """Zoom out (show more candles, smaller size)"""
        self.visible_candles = min(self.history_size, int(self.visible_candles * 1.4))
        self.draw_chart()

    def reset_zoom(self):
        """Reset to default zoom level"""
        self.visible_candles = 100
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

        # Get visible candles (respects zoom level)
        visible_prices = self.prices[-self.visible_candles:]

        # 1. Determine Range (based on visible candles only)
        vals = [p['h'] for p in visible_prices] + [p['l'] for p in visible_prices]
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
        num_candles = len(visible_prices)
        if num_candles == 0: return

        # Calculate candle width with cap for visual consistency
        raw_candle_w = (w - 60) / num_candles
        candle_w = min(raw_candle_w, self.max_candle_width)

        # Center candles in available space if we're using capped width
        total_candles_width = candle_w * num_candles
        chart_area = w - 60
        x_offset = 50 + (chart_area - total_candles_width) / 2 if total_candles_width < chart_area else 50

        for i, p in enumerate(visible_prices):
            x = x_offset + i * candle_w

            y_open = self.get_y_log(p['o'], min_log, range_log, draw_h)
            y_close = self.get_y_log(p['c'], min_log, range_log, draw_h)
            y_high = self.get_y_log(p['h'], min_log, range_log, draw_h)
            y_low = self.get_y_log(p['l'], min_log, range_log, draw_h)

            # Determine candle color based on phase and price movement
            phase = p.get('phase', 'TRADING')
            is_presale = phase in ('WAITING', 'COOLDOWN', 'COUNTDOWN', 'PRE_ROUND')

            if is_presale:
                # Yellow for presale/waiting phases (connects games visually)
                color = COLOR_PRESALE
            elif p['c'] >= p['o']:
                color = COLOR_CANDLE_UP
            else:
                color = COLOR_CANDLE_DOWN

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
