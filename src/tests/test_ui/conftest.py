"""UI test configuration.

Some UI tests require a real Tk display. In headless environments (CI/sandboxes),
Tk initialization can fail with `TclError: couldn't connect to display`.

Skip UI tests in that case rather than erroring during fixture setup.
"""

from __future__ import annotations

import tkinter as tk

import pytest


@pytest.fixture(autouse=True)
def _require_tk_display():
    try:
        root = tk.Tk()
        root.withdraw()
        root.destroy()
    except tk.TclError:
        pytest.skip("Tk display not available (headless environment)")

