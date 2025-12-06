"""
Pytest configuration and shared fixtures
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for GUI tests"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    # Don't quit - let pytest handle cleanup


@pytest.fixture
def mock_modbus_client():
    """Mock Modbus client for testing without real hardware"""
    client = MagicMock()
    client.connect.return_value = True
    client.is_socket_open.return_value = True
    client.read_holding_registers = MagicMock(return_value=Mock(registers=[0] * 10))
    client.read_input_registers = MagicMock(return_value=Mock(registers=[0] * 10))
    client.read_coils = MagicMock(return_value=Mock(bits=[False] * 10))
    client.read_discrete_inputs = MagicMock(return_value=Mock(bits=[False] * 10))
    client.write_single_register = MagicMock(return_value=Mock(function_code=6))
    client.write_single_coil = MagicMock(return_value=Mock(function_code=5))
    return client


@pytest.fixture
def sample_csv_data():
    """Sample CSV data for import testing"""
    return """Address,Name,Type,Value
0,Temperature,Int16,25
1,Pressure,UInt16,1013
2,Flow Rate,Float32,3.14
"""


@pytest.fixture
def sample_opf_data():
    """Sample OPF XML data for import testing"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<Project>
    <Tag>
        <Name>Temperature</Name>
        <Address>400001</Address>
        <DataType>Short</DataType>
    </Tag>
    <Tag>
        <Name>Pressure</Name>
        <Address>400002</Address>
        <DataType>Word</DataType>
    </Tag>
</Project>
"""


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing"""
    def _create_temp_file(content, filename="test_file.csv"):
        file_path = tmp_path / filename
        file_path.write_text(content)
        return str(file_path)
    return _create_temp_file
