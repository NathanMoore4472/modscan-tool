# ModScan Tool Test Suite

Automated tests for ModScan Tool using pytest.

## Test Structure

```
tests/
├── unit/                       # Unit tests (fast, isolated)
│   ├── test_data_conversion.py  # Data type conversions
│   └── test_file_operations.py  # CSV/OPF import/export
├── integration/                # Integration tests (slower)
│   ├── test_modbus_communication.py  # Modbus protocol tests
│   └── test_ui_components.py         # Qt GUI tests
├── fixtures/                   # Shared test fixtures
│   ├── modbus_server.py         # Test Modbus server
│   └── __init__.py
└── conftest.py                 # Pytest configuration
```

## Running Tests

### Install test dependencies
```bash
pip install -r requirements-dev.txt
```

### Run all tests
```bash
pytest
```

### Run specific test categories
```bash
# Unit tests only (fast)
pytest tests/unit

# Integration tests only
pytest tests/integration

# Modbus tests only
pytest -m modbus

# UI tests only
pytest -m ui

# Skip slow tests
pytest -m "not slow"
```

### Run with coverage
```bash
pytest --cov=. --cov-report=html
# Open htmlcov/index.html to view coverage report
```

### Run specific test file
```bash
pytest tests/unit/test_data_conversion.py -v
```

### Run specific test
```bash
pytest tests/unit/test_data_conversion.py::TestDataConversion::test_int16_conversion -v
```

## Test Markers

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.ui` - UI/GUI tests
- `@pytest.mark.modbus` - Modbus communication tests
- `@pytest.mark.slow` - Slow-running tests

## Writing Tests

### Unit Test Example
```python
import pytest

class TestDataConversion:
    def test_int16_conversion(self):
        """Test Int16 conversion"""
        value = 1000
        assert value == 1000
```

### Integration Test Example
```python
import pytest

@pytest.mark.integration
@pytest.mark.modbus
class TestModbusReading:
    def test_read_holding_registers(self, modbus_test_server):
        """Test reading holding registers"""
        # Test implementation
        pass
```

### UI Test Example
```python
import pytest

@pytest.mark.ui
class TestMainWindow:
    def test_window_creation(self, main_window, qtbot):
        """Test window creation"""
        assert main_window is not None
```

## Continuous Integration

Tests run automatically on GitHub Actions for:
- Every push to main/master branch
- Every pull request
- Multiple Python versions (3.9, 3.10, 3.11)
- Multiple platforms (Ubuntu, Windows, macOS)

See `.github/workflows/test.yml` for CI configuration.
