#!/usr/bin/env python3
"""
Basic test for check_repo_status.py
"""

import sys
import subprocess
from pathlib import Path


def test_script_runs():
    """Test that the script runs without errors."""
    script_path = Path(__file__).parent.parent / "scripts" / "check_repo_status.py"
    
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Check output contains expected sections
    assert "Multi-Repository Status Checker" in result.stdout
    assert "Repository: REPLAYER" in result.stdout
    assert "Summary" in result.stdout
    
    print("✓ Script runs successfully")
    print("✓ Output contains expected sections")
    return True


def test_script_detects_repo():
    """Test that the script detects the REPLAYER repository."""
    script_path = Path(__file__).parent.parent / "scripts" / "check_repo_status.py"
    
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should detect REPLAYER repo
    assert "Repository: REPLAYER" in result.stdout
    assert "Path: " in result.stdout
    assert "Branch: " in result.stdout
    
    print("✓ Script detects REPLAYER repository")
    print("✓ Shows branch information")
    return True


if __name__ == "__main__":
    print("\nTesting check_repo_status.py...")
    print("=" * 60)
    
    try:
        test_script_runs()
        print()
        test_script_detects_repo()
        print()
        print("=" * 60)
        print("✓ All tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error running tests: {e}")
        sys.exit(1)
