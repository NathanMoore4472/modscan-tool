#!/bin/bash
# Script to run tests locally

echo "ModScan Tool Test Runner"
echo "========================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update test dependencies
echo "Installing test dependencies..."
pip install -q -r requirements-dev.txt

echo ""
echo "Running tests..."
echo ""

# Run pytest with coverage
pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✓ All tests passed!"
    echo ""
    echo "Coverage report: htmlcov/index.html"
else
    echo ""
    echo "✗ Some tests failed"
    exit 1
fi
