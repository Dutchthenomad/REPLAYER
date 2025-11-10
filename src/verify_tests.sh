#!/bin/bash
# Verification script for Phase 5 test suite

echo "========================================"
echo "Phase 5 Test Suite Verification"
echo "========================================"
echo ""

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Not in rugs_replay_viewer directory"
    echo "Please run: cd /home/nomad/Desktop/REPLAYER/MODULAR/rugs_replay_viewer"
    exit 1
fi

echo "✅ In correct directory"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null && ! python3 -m pytest --version &> /dev/null; then
    echo "❌ pytest is not installed"
    echo ""
    echo "Install with one of these methods:"
    echo "  1. sudo apt install python3-pytest"
    echo "  2. pip3 install --user pytest"
    echo "  3. python3 -m venv venv && source venv/bin/activate && pip install pytest"
    echo ""
    exit 1
fi

echo "✅ pytest is installed"
python3 -m pytest --version
echo ""

# Check test files exist
echo "Checking test files..."
test_count=$(find tests/ -name "test_*.py" | wc -l)
echo "✅ Found $test_count test files"
echo ""

# List test files
echo "Test files:"
find tests/ -name "test_*.py" -exec echo "  - {}" \;
echo ""

# Check conftest.py exists
if [ ! -f "tests/conftest.py" ]; then
    echo "❌ tests/conftest.py not found"
    exit 1
fi
echo "✅ conftest.py exists"
echo ""

# Check pytest.ini exists
if [ ! -f "pytest.ini" ]; then
    echo "❌ pytest.ini not found"
    exit 1
fi
echo "✅ pytest.ini exists"
echo ""

# Run pytest with collection only (no execution)
echo "Collecting tests..."
python3 -m pytest tests/ --collect-only -q 2>&1 | head -20
echo ""

# Count total tests
total_tests=$(python3 -m pytest tests/ --collect-only -q 2>&1 | grep "test session starts" -A 100 | grep " selected" | awk '{print $1}')
if [ -z "$total_tests" ]; then
    total_tests=$(python3 -m pytest tests/ --collect-only -q 2>&1 | tail -1 | awk '{print $1}')
fi

echo "📊 Total tests collected: $total_tests"
echo ""

# Ask user if they want to run tests
echo "========================================"
echo "Ready to run tests!"
echo "========================================"
echo ""
echo "Run all tests with:"
echo "  python3 -m pytest tests/ -v"
echo ""
echo "Run with coverage:"
echo "  python3 -m pytest tests/ --cov=. --cov-report=html"
echo ""
echo "Run specific test file:"
echo "  python3 -m pytest tests/test_core/test_game_state.py -v"
echo ""

# Optionally run tests
read -p "Run all tests now? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Running all tests..."
    python3 -m pytest tests/ -v
    exit_code=$?
    echo ""
    if [ $exit_code -eq 0 ]; then
        echo "✅ All tests passed!"
    else
        echo "❌ Some tests failed (exit code: $exit_code)"
    fi
    exit $exit_code
else
    echo "Verification complete. Tests are ready to run!"
fi
