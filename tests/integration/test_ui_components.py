"""
Integration tests for UI components
"""
import pytest
from PyQt6.QtWidgets import QPushButton, QLineEdit, QSpinBox, QComboBox
from PyQt6.QtCore import Qt
from unittest.mock import Mock, patch


@pytest.mark.ui
class TestMainWindow:
    """Test main window initialization and basic functionality"""

    @pytest.fixture
    def main_window(self, qapp, mock_modbus_client):
        """Create main window instance for testing"""
        with patch('modscan_tool.ModbusTcpClient', return_value=mock_modbus_client):
            from modscan_tool import ModbusScannerGUI
            window = ModbusScannerGUI(version="1.4.0")
            yield window
            window.close()

    def test_window_creation(self, main_window):
        """Test that main window is created successfully"""
        assert main_window is not None
        assert main_window.windowTitle() == "ModScan Tool"

    def test_window_has_required_widgets(self, main_window):
        """Test that main window has all required widgets"""
        # Should have connection controls
        assert hasattr(main_window, 'host_input')
        assert hasattr(main_window, 'port_input')
        assert hasattr(main_window, 'connect_btn')

        # Should have scan controls
        assert hasattr(main_window, 'start_addr_input')
        assert hasattr(main_window, 'end_addr_input')
        assert hasattr(main_window, 'scan_btn')

        # Should have results table
        assert hasattr(main_window, 'results_table')

    def test_initial_state(self, main_window):
        """Test initial state of controls"""
        # Connect button should be enabled
        assert main_window.connect_btn.isEnabled()

        # Scan button should be disabled (no connection)
        assert not main_window.scan_btn.isEnabled()


@pytest.mark.ui
class TestConnectionControls:
    """Test connection control functionality"""

    @pytest.fixture
    def main_window(self, qapp, mock_modbus_client):
        """Create main window instance for testing"""
        with patch('modscan_tool.ModbusTcpClient', return_value=mock_modbus_client):
            from modscan_tool import ModbusScannerGUI
            window = ModbusScannerGUI(version="1.4.0")
            yield window
            window.close()

    def test_host_input_default(self, main_window):
        """Test default host input value"""
        assert main_window.host_input.text() == "127.0.0.1"

    def test_port_input_default(self, main_window):
        """Test default port input value"""
        assert main_window.port_input.value() == 502

    def test_connect_button_click(self, main_window, qtbot):
        """Test connect button click"""
        # Click connect button
        qtbot.mouseClick(main_window.connect_btn, Qt.MouseButton.LeftButton)

        # Should enable scan button after connection
        assert main_window.scan_btn.isEnabled()


@pytest.mark.ui
class TestScanControls:
    """Test scan control functionality"""

    @pytest.fixture
    def main_window(self, qapp, mock_modbus_client):
        """Create connected main window instance"""
        with patch('modscan_tool.ModbusTcpClient', return_value=mock_modbus_client):
            from modscan_tool import ModbusScannerGUI
            window = ModbusScannerGUI(version="1.4.0")
            # Simulate connection
            window.client = mock_modbus_client
            window.scan_btn.setEnabled(True)
            yield window
            window.close()

    def test_address_range_inputs(self, main_window):
        """Test address range input controls"""
        # Set address range
        main_window.start_addr_input.setValue(0)
        main_window.end_addr_input.setValue(99)

        assert main_window.start_addr_input.value() == 0
        assert main_window.end_addr_input.value() == 99

    def test_register_type_selector(self, main_window):
        """Test register type selection"""
        if hasattr(main_window, 'register_type_combo'):
            # Should have options for different register types
            assert main_window.register_type_combo.count() > 0


@pytest.mark.ui
class TestResultsTable:
    """Test results table functionality"""

    @pytest.fixture
    def main_window(self, qapp, mock_modbus_client):
        """Create main window with results"""
        with patch('modscan_tool.ModbusTcpClient', return_value=mock_modbus_client):
            from modscan_tool import ModbusScannerGUI
            window = ModbusScannerGUI(version="1.4.0")
            window.client = mock_modbus_client
            yield window
            window.close()

    def test_table_columns(self, main_window):
        """Test that results table has correct columns"""
        table = main_window.results_table
        assert table.columnCount() >= 3  # At least Address, Name, Value

    def test_table_initially_empty(self, main_window):
        """Test that results table starts empty"""
        table = main_window.results_table
        assert table.rowCount() == 0


@pytest.mark.ui
class TestMenus:
    """Test menu functionality"""

    @pytest.fixture
    def main_window(self, qapp, mock_modbus_client):
        """Create main window instance"""
        with patch('modscan_tool.ModbusTcpClient', return_value=mock_modbus_client):
            from modscan_tool import ModbusScannerGUI
            window = ModbusScannerGUI(version="1.4.0")
            yield window
            window.close()

    def test_has_file_menu(self, main_window):
        """Test that File menu exists"""
        menubar = main_window.menuBar()
        actions = menubar.actions()
        menu_titles = [action.text() for action in actions]

        assert "File" in menu_titles or "&File" in menu_titles

    def test_has_help_menu(self, main_window):
        """Test that Help menu exists"""
        menubar = main_window.menuBar()
        actions = menubar.actions()
        menu_titles = [action.text() for action in actions]

        assert "Help" in menu_titles or "&Help" in menu_titles
