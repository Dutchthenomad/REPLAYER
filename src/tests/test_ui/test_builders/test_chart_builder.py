"""Tests for ChartBuilder"""

import pytest
import tkinter as tk
from ui.builders.chart_builder import ChartBuilder


@pytest.fixture
def root():
    """Create a Tk root window for testing"""
    root = tk.Tk()
    root.withdraw()  # Hide the window
    yield root
    root.destroy()


class TestChartBuilder:
    """Tests for ChartBuilder"""

    def test_build_returns_dict(self, root):
        """build() should return a dictionary of widgets"""
        builder = ChartBuilder(root)
        result = builder.build()
        assert isinstance(result, dict)

    def test_build_creates_chart_container(self, root):
        """build() should create chart_container frame"""
        builder = ChartBuilder(root)
        widgets = builder.build()
        assert 'chart_container' in widgets
        assert isinstance(widgets['chart_container'], tk.Frame)

    def test_build_creates_chart_widget(self, root):
        """build() should create chart widget"""
        builder = ChartBuilder(root)
        widgets = builder.build()
        assert 'chart' in widgets
        # ChartWidget is a custom widget, not plain tk.Widget
        assert widgets['chart'] is not None

    def test_build_creates_zoom_overlay(self, root):
        """build() should create zoom overlay frame"""
        builder = ChartBuilder(root)
        widgets = builder.build()
        assert 'zoom_overlay' in widgets
        assert isinstance(widgets['zoom_overlay'], tk.Frame)

    def test_zoom_buttons_exist(self, root):
        """Zoom buttons should exist in the overlay"""
        builder = ChartBuilder(root)
        widgets = builder.build()
        # Check that zoom overlay has children (buttons)
        children = widgets['zoom_overlay'].winfo_children()
        assert len(children) >= 3  # Zoom In, Zoom Out, Reset
