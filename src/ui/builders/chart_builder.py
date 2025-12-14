"""
ChartBuilder - Builds the chart area with zoom controls

Extracted from MainWindow._create_ui() (Phase 1)
Handles construction of chart container, ChartWidget, and zoom overlay.
"""

import tkinter as tk
import logging

from ui.widgets import ChartWidget

logger = logging.getLogger(__name__)


class ChartBuilder:
    """
    Builds the chart area with zoom controls.

    Usage:
        builder = ChartBuilder(parent)
        widgets = builder.build()
        chart = widgets['chart']
    """

    def __init__(self, parent: tk.Tk):
        """
        Initialize ChartBuilder.

        Args:
            parent: Parent Tk widget
        """
        self.parent = parent

    def build(self) -> dict:
        """
        Build the chart area and return widget references.

        Returns:
            dict with keys:
                - chart_container: The chart container frame
                - chart: The ChartWidget instance
                - zoom_overlay: The zoom controls frame
        """
        # Chart container
        chart_container = tk.Frame(self.parent, bg='#0a0a0a')
        chart_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Chart widget (MAXIMIZED - no fixed dimensions)
        chart = ChartWidget(chart_container)
        chart.pack(fill=tk.BOTH, expand=True)

        # Zoom controls (overlaid at bottom-left of chart)
        zoom_overlay = tk.Frame(chart_container, bg='#2a2a2a')
        zoom_overlay.place(x=10, y=10, anchor='nw')

        tk.Button(
            zoom_overlay,
            text="+ ZOOM IN",
            command=chart.zoom_in,
            bg='#333333',
            fg='white',
            font=('Arial', 9),
            bd=1,
            relief=tk.RAISED
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            zoom_overlay,
            text="+ ZOOM OUT",
            command=chart.zoom_out,
            bg='#333333',
            fg='white',
            font=('Arial', 9),
            bd=1,
            relief=tk.RAISED
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            zoom_overlay,
            text="RESET ZOOM",
            command=chart.reset_zoom,
            bg='#333333',
            fg='white',
            font=('Arial', 9),
            bd=1,
            relief=tk.RAISED
        ).pack(side=tk.LEFT, padx=2)

        logger.debug("ChartBuilder: Chart area built")

        return {
            'chart_container': chart_container,
            'chart': chart,
            'zoom_overlay': zoom_overlay,
        }
