"""
Chart Widget - Logarithmic price chart display
Handles smooth progression from 1x to 100x+ using log scale
"""

import tkinter as tk
from tkinter import Canvas
from collections import deque
from decimal import Decimal
import math
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


class ChartWidget(Canvas):
    """
    Logarithmic price chart widget

    Features:
    - Logarithmic Y-axis for smooth progression (1x → 100x+)
    - Candlestick-style price display
    - Auto-scaling based on visible range
    - Grid lines at log intervals
    - Price labels
    - Scrollable history (last 500 ticks)
    """

    def __init__(self, parent, width=800, height=400, **kwargs):
        # Initialize canvas with dark theme
        super().__init__(
            parent,
            width=width,
            height=height,
            bg='#0a0a0a',
            highlightthickness=0,
            **kwargs
        )

        # Chart dimensions
        self.width = width
        self.height = height
        self.padding_left = 60  # Space for price labels
        self.padding_right = 20
        self.padding_top = 20
        self.padding_bottom = 40  # Space for tick labels

        # Drawable area
        self.chart_width = width - self.padding_left - self.padding_right
        self.chart_height = height - self.padding_top - self.padding_bottom

        # Price history (stores tuples of (tick, price))
        self.price_history = deque(maxlen=500)  # Last 500 ticks

        # Current visible range
        self.visible_ticks = 100  # Show last 100 ticks by default
        self.scroll_offset = 0

        # Price range for auto-scaling
        self.min_price = Decimal('1.0')
        self.max_price = Decimal('2.0')

        # Colors (Phase 5: Theme-aware)
        self.colors = self._get_theme_colors()

        # Log scale parameters
        self.log_base = 10

        # Bind resize event to handle dynamic sizing
        self.bind('<Configure>', self._on_resize)

        logger.info(f"ChartWidget initialized ({width}x{height}, log scale)")

    def _get_theme_colors(self):
        """
        Get chart colors based on current theme
        Phase 5: Theme-aware chart colors
        """
        try:
            import ttkbootstrap as ttk

            # Get current theme name
            style = ttk.Style()
            theme = style.theme_use()

            # Theme-specific color palettes
            theme_colors = {
                'cyborg': {
                    'grid': '#1a1a1a',
                    'grid_major': '#2a2a2a',
                    'text': '#77B7D7',
                    'text_bright': '#ffffff',
                    'price_up': '#2A9FD6',
                    'price_down': '#ff3366',
                    'price_neutral': '#ffcc00',
                    'background': '#060606'
                },
                'darkly': {
                    'grid': '#2a2a2a',
                    'grid_major': '#3a3a3a',
                    'text': '#AAAAAA',
                    'text_bright': '#ffffff',
                    'price_up': '#375A7F',
                    'price_down': '#ff3366',
                    'price_neutral': '#ffcc00',
                    'background': '#222222'
                },
                'superhero': {
                    'grid': '#2a2a2a',
                    'grid_major': '#3a3a3a',
                    'text': '#AAAAAA',
                    'text_bright': '#ffffff',
                    'price_up': '#4F9FE0',
                    'price_down': '#DF6919',
                    'price_neutral': '#ECA400',
                    'background': '#2B3E50'
                },
                # Default colors for other themes
                'default': {
                    'grid': '#1a1a1a',
                    'grid_major': '#2a2a2a',
                    'text': '#666666',
                    'text_bright': '#ffffff',
                    'price_up': '#00ff88',
                    'price_down': '#ff3366',
                    'price_neutral': '#ffcc00',
                    'background': '#0a0a0a'
                }
            }

            # Get colors for current theme or use default
            colors = theme_colors.get(theme, theme_colors['default'])
            logger.debug(f"Using chart colors for theme: {theme}")
            return colors

        except Exception as e:
            logger.warning(f"Could not get theme colors: {e}, using defaults")
            # Fallback to default colors
            return {
                'grid': '#1a1a1a',
                'grid_major': '#2a2a2a',
                'text': '#666666',
                'text_bright': '#ffffff',
                'price_up': '#00ff88',
                'price_down': '#ff3366',
                'price_neutral': '#ffcc00',
                'background': '#0a0a0a'
            }

    def update_theme_colors(self):
        """
        Update chart colors to match current theme
        Call this after theme changes
        Phase 5: Theme coordination
        """
        self.colors = self._get_theme_colors()
        self.config(bg=self.colors['background'])
        self.draw()  # Redraw with new colors

    def _on_resize(self, event):
        """
        Handle canvas resize events to make chart responsive
        """
        # Only process if size actually changed
        if event.width != self.width or event.height != self.height:
            self.width = event.width
            self.height = event.height

            # Recalculate drawable area
            self.chart_width = self.width - self.padding_left - self.padding_right
            self.chart_height = self.height - self.padding_top - self.padding_bottom

            # Redraw chart with new dimensions
            self.draw()
            logger.debug(f"ChartWidget resized to {self.width}x{self.height}")

    # ========================================================================
    # DATA MANAGEMENT
    # ========================================================================

    def add_tick(self, tick_number: int, price: Decimal):
        """
        Add a new price tick to the chart

        Args:
            tick_number: Tick/frame number
            price: Current price multiplier (e.g., 1.5 = 1.5x)
        """
        self.price_history.append((tick_number, price))

        # Auto-scale if needed
        self._update_price_range()

        # Redraw chart
        self.draw()

    def clear_history(self):
        """Clear all price history"""
        self.price_history.clear()
        self.min_price = Decimal('1.0')
        self.max_price = Decimal('2.0')
        self.draw()

    def _update_price_range(self):
        """Update min/max price range based on visible ticks"""
        if not self.price_history:
            return

        # Get visible prices
        visible = list(self.price_history)[-self.visible_ticks:]
        if not visible:
            return

        prices = [price for _, price in visible]
        self.min_price = min(prices)
        self.max_price = max(prices)

        # Add 10% padding on log scale
        log_range = math.log10(float(self.max_price)) - math.log10(float(self.min_price))
        padding = log_range * 0.1

        self.min_price = Decimal(str(10 ** (math.log10(float(self.min_price)) - padding)))
        self.max_price = Decimal(str(10 ** (math.log10(float(self.max_price)) + padding)))

        # Ensure minimum range
        if self.max_price / self.min_price < Decimal('1.2'):
            center = (self.min_price + self.max_price) / 2
            self.min_price = center * Decimal('0.9')
            self.max_price = center * Decimal('1.1')

    # ========================================================================
    # COORDINATE CONVERSION (LOG SCALE)
    # ========================================================================

    def price_to_y(self, price: Decimal) -> float:
        """
        Convert price to Y coordinate using logarithmic scale

        Args:
            price: Price multiplier

        Returns:
            Y coordinate on canvas
        """
        if price <= 0:
            price = Decimal('0.01')

        # Logarithmic transformation
        log_price = math.log10(float(price))
        log_min = math.log10(float(self.min_price))
        log_max = math.log10(float(self.max_price))

        # Avoid division by zero
        if log_max == log_min:
            normalized = 0.5
        else:
            normalized = (log_price - log_min) / (log_max - log_min)

        # Invert Y (canvas Y=0 is top)
        y = self.padding_top + (1 - normalized) * self.chart_height

        return y

    def tick_to_x(self, tick_index: int) -> float:
        """
        Convert tick index to X coordinate

        Args:
            tick_index: Index in visible price history

        Returns:
            X coordinate on canvas
        """
        if self.visible_ticks <= 1:
            return self.padding_left

        normalized = tick_index / (self.visible_ticks - 1)
        x = self.padding_left + normalized * self.chart_width

        return x

    # ========================================================================
    # DRAWING
    # ========================================================================

    def draw(self):
        """Redraw the entire chart"""
        # Clear canvas
        self.delete('all')

        if not self.price_history:
            self._draw_empty_state()
            return

        # Draw components in order
        self._draw_background()
        self._draw_grid()
        self._draw_price_labels()
        self._draw_price_line()
        self._draw_tick_labels()
        self._draw_border()

    def _draw_empty_state(self):
        """Draw empty state message"""
        self.create_text(
            self.width / 2,
            self.height / 2,
            text="No price data",
            fill=self.colors['text'],
            font=('Arial', 14)
        )

    def _draw_background(self):
        """Draw chart background"""
        self.create_rectangle(
            self.padding_left,
            self.padding_top,
            self.width - self.padding_right,
            self.height - self.padding_bottom,
            fill=self.colors['background'],
            outline=''
        )

    def _draw_grid(self):
        """Draw logarithmic grid lines"""
        # Price grid lines at log intervals
        # Common multipliers: 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000

        log_min = math.log10(float(self.min_price))
        log_max = math.log10(float(self.max_price))

        # Generate grid line values
        grid_values = []

        # Start from 10^floor(log_min)
        base = 10 ** math.floor(log_min)

        # Add multiples: 1x, 2x, 5x, 10x, 20x, 50x, etc.
        multipliers = [1, 2, 5]

        while base < float(self.max_price) * 10:
            for mult in multipliers:
                value = base * mult
                if self.min_price <= Decimal(str(value)) <= self.max_price:
                    grid_values.append(Decimal(str(value)))
            base *= 10

        # Draw grid lines
        for price in grid_values:
            y = self.price_to_y(price)

            # Major grid lines at 10^n
            is_major = (float(price) == 10 ** round(math.log10(float(price))))
            color = self.colors['grid_major'] if is_major else self.colors['grid']

            self.create_line(
                self.padding_left,
                y,
                self.width - self.padding_right,
                y,
                fill=color,
                dash=(2, 4) if not is_major else None
            )

    def _draw_price_labels(self):
        """Draw price labels on Y-axis"""
        log_min = math.log10(float(self.min_price))
        log_max = math.log10(float(self.max_price))

        # Generate label values (same as grid)
        label_values = []

        base = 10 ** math.floor(log_min)
        multipliers = [1, 2, 5]

        while base < float(self.max_price) * 10:
            for mult in multipliers:
                value = base * mult
                if self.min_price <= Decimal(str(value)) <= self.max_price:
                    label_values.append(Decimal(str(value)))
            base *= 10

        # Draw labels
        for price in label_values:
            y = self.price_to_y(price)

            # Format price label
            if price >= 100:
                label = f"{float(price):.0f}x"
            elif price >= 10:
                label = f"{float(price):.1f}x"
            else:
                label = f"{float(price):.2f}x"

            self.create_text(
                self.padding_left - 10,
                y,
                text=label,
                fill=self.colors['text_bright'],
                anchor='e',
                font=('Arial', 9)
            )

    def _draw_price_line(self):
        """Draw price line with candlestick-style coloring"""
        if len(self.price_history) < 2:
            return

        # Get visible ticks
        visible = list(self.price_history)[-self.visible_ticks:]

        if len(visible) < 2:
            return

        # Draw line segments with color based on trend
        for i in range(len(visible) - 1):
            tick1, price1 = visible[i]
            tick2, price2 = visible[i + 1]

            x1 = self.tick_to_x(i)
            y1 = self.price_to_y(price1)
            x2 = self.tick_to_x(i + 1)
            y2 = self.price_to_y(price2)

            # Color based on price movement
            if price2 > price1:
                color = self.colors['price_up']
            elif price2 < price1:
                color = self.colors['price_down']
            else:
                color = self.colors['price_neutral']

            # Draw line segment
            self.create_line(
                x1, y1, x2, y2,
                fill=color,
                width=2,
                capstyle=tk.ROUND
            )

            # Draw dot at each point
            self.create_oval(
                x1 - 2, y1 - 2,
                x1 + 2, y1 + 2,
                fill=color,
                outline=''
            )

        # Draw final point
        last_i = len(visible) - 1
        _, last_price = visible[last_i]
        x = self.tick_to_x(last_i)
        y = self.price_to_y(last_price)

        self.create_oval(
            x - 3, y - 3,
            x + 3, y + 3,
            fill=self.colors['price_neutral'],
            outline=self.colors['text_bright'],
            width=1
        )

    def _draw_tick_labels(self):
        """Draw tick number labels on X-axis"""
        if not self.price_history:
            return

        visible = list(self.price_history)[-self.visible_ticks:]

        if not visible:
            return

        # Draw tick labels at intervals
        label_count = min(5, len(visible))

        for i in range(label_count):
            index = int(i * (len(visible) - 1) / max(1, label_count - 1))
            tick_number, _ = visible[index]

            x = self.tick_to_x(index)
            y = self.height - self.padding_bottom + 20

            self.create_text(
                x, y,
                text=f"#{tick_number}",
                fill=self.colors['text'],
                font=('Arial', 9)
            )

    def _draw_border(self):
        """Draw chart border"""
        self.create_rectangle(
            self.padding_left,
            self.padding_top,
            self.width - self.padding_right,
            self.height - self.padding_bottom,
            outline=self.colors['grid_major'],
            width=1
        )

    # ========================================================================
    # CONTROLS
    # ========================================================================

    def zoom_in(self):
        """Zoom in (show fewer ticks)"""
        self.visible_ticks = max(20, int(self.visible_ticks * 0.7))
        self._update_price_range()
        self.draw()
        logger.debug(f"Zoomed in: {self.visible_ticks} visible ticks")

    def zoom_out(self):
        """Zoom out (show more ticks)"""
        self.visible_ticks = min(500, int(self.visible_ticks * 1.4))
        self._update_price_range()
        self.draw()
        logger.debug(f"Zoomed out: {self.visible_ticks} visible ticks")

    def reset_zoom(self):
        """Reset to default zoom"""
        self.visible_ticks = 100
        self._update_price_range()
        self.draw()
        logger.debug("Zoom reset")

    # ========================================================================
    # INFO
    # ========================================================================

    def get_info(self) -> dict:
        """Get chart info"""
        return {
            'tick_count': len(self.price_history),
            'visible_ticks': self.visible_ticks,
            'min_price': float(self.min_price),
            'max_price': float(self.max_price),
            'price_range_ratio': float(self.max_price / self.min_price) if self.min_price > 0 else 0
        }
