"""
Integration tests to prevent import-time dependency explosions and noisy side effects.

These tests run imports in a fresh Python subprocess to avoid interference from
already-imported modules within the pytest process.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_python_import(code: str) -> subprocess.CompletedProcess[str]:
    src_dir = Path(__file__).resolve().parents[2]
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(src_dir),
        capture_output=True,
        text=True,
        check=False,
    )


def test_import_config_is_quiet():
    """
    Importing config should not validate, configure logging, or print to stdout/stderr.

    This prevents test pollution and avoids hard-to-debug import-order issues.
    """
    proc = _run_python_import("import config")

    assert proc.returncode == 0, proc.stderr
    combined = (proc.stdout or "") + (proc.stderr or "")
    assert "Configuration validated successfully" not in combined
    assert "FATAL: Configuration validation failed" not in combined


def test_import_services_and_sources_does_not_require_socketio():
    """
    Importing the packages should not force optional runtime deps (like python-socketio).

    Socket.IO should only be required when actually connecting to the live feed.
    """
    proc = _run_python_import("import services; import sources")

    assert proc.returncode == 0, proc.stderr
    combined = (proc.stdout or "") + (proc.stderr or "")
    assert "No module named 'socketio'" not in combined

