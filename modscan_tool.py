#!/usr/bin/env python3
"""
Modbus Register Reader - PyQt6 Version
A cross-platform GUI tool for reading Modbus TCP register values
"""

import sys
import threading
import ipaddress
import struct
import time
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTextEdit, QProgressBar, QCheckBox, QGroupBox,
                             QMessageBox, QFileDialog, QRadioButton, QButtonGroup,
                             QTableWidget, QTableWidgetItem, QHeaderView, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException


class WorkerSignals(QObject):
    """Signals for thread-safe communication"""
    log = pyqtSignal(str, str)  # message, tag
    status = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    update_table = pyqtSignal(list, int)  # registers, start_address


class ModbusScannerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modbus Register Reader")
        self.setGeometry(100, 100, 900, 700)

        self.scanning = False
        self.scan_thread = None
        self.signals = WorkerSignals()

        # Connect signals
        self.signals.log.connect(self.log_message)
        self.signals.status.connect(self.update_status)
        self.signals.progress.connect(self.update_progress)
        self.signals.finished.connect(self.scan_finished)
        self.signals.update_table.connect(self.populate_table)

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Settings Group
        settings_group = QGroupBox("Connection Settings")
        settings_layout = QVBoxLayout()

        # IP Address
        ip_layout = QHBoxLayout()
        ip_layout.addWidget(QLabel("IP Address:"))
        self.ip_entry = QLineEdit("192.168.1.1")
        self.ip_entry.setPlaceholderText("e.g., 192.168.1.100")
        self.ip_entry.setMaximumWidth(200)
        ip_layout.addWidget(self.ip_entry)
        ip_layout.addStretch()
        settings_layout.addLayout(ip_layout)

        # Port
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_entry = QLineEdit("502")
        self.port_entry.setMaximumWidth(100)
        port_layout.addWidget(self.port_entry)
        port_layout.addStretch()
        settings_layout.addLayout(port_layout)

        # Unit ID
        unit_layout = QHBoxLayout()
        unit_layout.addWidget(QLabel("Unit ID:"))
        self.unit_entry = QLineEdit("1")
        self.unit_entry.setMaximumWidth(100)
        unit_layout.addWidget(self.unit_entry)
        unit_layout.addStretch()
        settings_layout.addLayout(unit_layout)

        # Timeout
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (seconds):"))
        self.timeout_entry = QLineEdit("2")
        self.timeout_entry.setMaximumWidth(100)
        timeout_layout.addWidget(self.timeout_entry)
        timeout_layout.addStretch()
        settings_layout.addLayout(timeout_layout)

        # Start Register
        start_reg_layout = QHBoxLayout()
        start_reg_layout.addWidget(QLabel("Start Register:"))
        self.start_register_entry = QLineEdit("0")
        self.start_register_entry.setMaximumWidth(100)
        start_reg_layout.addWidget(self.start_register_entry)
        start_reg_layout.addStretch()
        settings_layout.addLayout(start_reg_layout)

        # Register Count
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("Register Count:"))
        self.register_count_entry = QLineEdit("10")
        self.register_count_entry.setMaximumWidth(100)
        count_layout.addWidget(self.register_count_entry)
        count_layout.addStretch()
        settings_layout.addLayout(count_layout)

        # Register type selection
        register_layout = QHBoxLayout()
        register_layout.addWidget(QLabel("Data Type:"))

        self.register_button_group = QButtonGroup()

        self.holding_radio = QRadioButton("Holding Registers (16-bit)")
        self.holding_radio.setChecked(True)
        self.register_button_group.addButton(self.holding_radio, 1)
        register_layout.addWidget(self.holding_radio)

        self.input_radio = QRadioButton("Input Registers (16-bit)")
        self.register_button_group.addButton(self.input_radio, 2)
        register_layout.addWidget(self.input_radio)

        self.coils_radio = QRadioButton("Coils (1-bit)")
        self.register_button_group.addButton(self.coils_radio, 3)
        register_layout.addWidget(self.coils_radio)

        self.discrete_radio = QRadioButton("Discrete Inputs (1-bit)")
        self.register_button_group.addButton(self.discrete_radio, 4)
        register_layout.addWidget(self.discrete_radio)

        register_layout.addStretch()
        settings_layout.addLayout(register_layout)

        # Data interpretation options
        options_layout = QHBoxLayout()
        options_layout.addWidget(QLabel("Options:"))

        self.reverse_byte_order_check = QCheckBox("Reverse Byte Order")
        options_layout.addWidget(self.reverse_byte_order_check)

        self.reverse_word_order_check = QCheckBox("Reverse Word Order")
        options_layout.addWidget(self.reverse_word_order_check)

        self.zero_based_check = QCheckBox("0-based Addressing")
        self.zero_based_check.setChecked(True)
        options_layout.addWidget(self.zero_based_check)

        options_layout.addStretch()
        settings_layout.addLayout(options_layout)

        # Continuous polling option
        polling_layout = QHBoxLayout()
        self.continuous_read_check = QCheckBox("Continuous Read")
        polling_layout.addWidget(self.continuous_read_check)

        polling_layout.addWidget(QLabel("Interval (seconds):"))
        self.polling_interval_entry = QLineEdit("1")
        self.polling_interval_entry.setMaximumWidth(60)
        polling_layout.addWidget(self.polling_interval_entry)

        self.read_individually_check = QCheckBox("Read Individually (slower, handles missing registers)")
        polling_layout.addWidget(self.read_individually_check)

        polling_layout.addStretch()
        settings_layout.addLayout(polling_layout)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Control Buttons
        button_layout = QHBoxLayout()

        self.scan_button = QPushButton("Read Registers")
        self.scan_button.clicked.connect(self.start_scan)
        self.scan_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        button_layout.addWidget(self.scan_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_scan)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
        button_layout.addWidget(self.stop_button)

        self.clear_button = QPushButton("Clear Results")
        self.clear_button.clicked.connect(self.clear_results)
        self.clear_button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        button_layout.addWidget(self.clear_button)

        self.export_button = QPushButton("Export Results")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 8px;")
        button_layout.addWidget(self.export_button)

        layout.addLayout(button_layout)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Status Label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("background-color: #90EE90; padding: 5px; font-weight: bold;")
        self.status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        layout.addWidget(self.status_label)

        # Results Table
        results_group = QGroupBox("Register Values")
        results_layout = QVBoxLayout()

        # Info label
        self.info_label = QLabel("Ready to read. Configure connection and register range above, then click 'Read Registers'.")
        self.info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        results_layout.addWidget(self.info_label)

        # Search/Filter section
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))

        self.filter_column_combo = QComboBox()
        self.filter_column_combo.addItems([
            "All Columns", "Address", "Hex", "Uint16", "Int16", "Uint32", "Int32", "Float32", "String"
        ])
        self.filter_column_combo.setMaximumWidth(120)
        filter_layout.addWidget(self.filter_column_combo)

        self.filter_entry = QLineEdit()
        self.filter_entry.setPlaceholderText("Type to filter table...")
        self.filter_entry.textChanged.connect(self.filter_table)
        self.filter_column_combo.currentIndexChanged.connect(self.filter_table)
        filter_layout.addWidget(self.filter_entry)

        clear_filter_btn = QPushButton("Clear Filter")
        clear_filter_btn.clicked.connect(self.clear_filter)
        clear_filter_btn.setMaximumWidth(100)
        filter_layout.addWidget(clear_filter_btn)

        results_layout.addLayout(filter_layout)

        # Create table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels([
            "Address", "Hex", "Uint16", "Int16", "Uint32", "Int32", "Float32", "String"
        ])

        # Make table fill available space and resize columns to content
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)

        results_layout.addWidget(self.results_table)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

    def log_message(self, message, tag):
        """Display a log message in the info label"""
        # Set color based on tag
        color = "black"
        if tag == "success":
            color = "green"
        elif tag == "error":
            color = "red"
        elif tag == "info":
            color = "blue"

        self.info_label.setText(message)
        self.info_label.setStyleSheet(f"color: {color};  padding: 5px;")

    def update_status(self, message):
        """Update the status label"""
        self.status_label.setText(message)

    def update_progress(self, value):
        """Update the progress bar"""
        self.progress_bar.setValue(value)

    def clear_results(self):
        """Clear the results table"""
        self.results_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.info_label.setText("Table cleared.")

    def filter_table(self):
        """Filter table rows based on search criteria"""
        filter_text = self.filter_entry.text().lower()
        column_index = self.filter_column_combo.currentIndex() - 1  # -1 because first item is "All Columns"

        if not filter_text:
            # Show all rows if filter is empty
            for row in range(self.results_table.rowCount()):
                self.results_table.setRowHidden(row, False)
            return

        # Filter rows
        for row in range(self.results_table.rowCount()):
            show_row = False

            if column_index == -1:
                # Search all columns
                for col in range(self.results_table.columnCount()):
                    item = self.results_table.item(row, col)
                    if item and filter_text in item.text().lower():
                        show_row = True
                        break
            else:
                # Search specific column
                item = self.results_table.item(row, column_index)
                if item and filter_text in item.text().lower():
                    show_row = True

            self.results_table.setRowHidden(row, not show_row)

    def clear_filter(self):
        """Clear the filter and show all rows"""
        self.filter_entry.clear()
        for row in range(self.results_table.rowCount()):
            self.results_table.setRowHidden(row, False)

    def validate_inputs(self):
        """Validate user inputs"""
        try:
            port = int(self.port_entry.text())
            if port < 1 or port > 65535:
                raise ValueError("Port must be between 1 and 65535")

            timeout = float(self.timeout_entry.text())
            if timeout <= 0:
                raise ValueError("Timeout must be positive")

            unit_id = int(self.unit_entry.text())
            if unit_id < 0 or unit_id > 255:
                raise ValueError("Unit ID must be between 0 and 255")

            start_reg = int(self.start_register_entry.text())
            zero_based = self.zero_based_check.isChecked()

            # Validate based on addressing mode
            if zero_based:
                if start_reg < 0 or start_reg > 65535:
                    raise ValueError("Start register must be between 0 and 65535 (0-based)")
            else:
                if start_reg < 1 or start_reg > 65536:
                    raise ValueError("Start register must be between 1 and 65536 (1-based)")

            reg_count = int(self.register_count_entry.text())

            # Check limits based on data type
            is_bit_type = self.coils_radio.isChecked() or self.discrete_radio.isChecked()
            if is_bit_type:
                if reg_count < 1 or reg_count > 2000:
                    raise ValueError("Bit count must be between 1 and 2000 for coils/discrete inputs")
            else:
                if reg_count < 1 or reg_count > 125:
                    raise ValueError("Register count must be between 1 and 125")

            # Check range limits based on addressing mode
            if zero_based:
                if start_reg + reg_count > 65536:
                    raise ValueError("Register range exceeds maximum address (65535)")
            else:
                if start_reg + reg_count > 65537:
                    raise ValueError("Register range exceeds maximum address (65536)")

            # Validate IP address
            ipaddress.ip_address(self.ip_entry.text().strip())

            return True
        except ValueError as e:
            QMessageBox.critical(self, "Input Error", str(e))
            return False

    def start_scan(self):
        """Start the scanning process"""
        if not self.validate_inputs():
            return

        self.scanning = True
        self.scan_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.clear_results()

        self.signals.log.emit("=" * 80, "header")
        self.signals.log.emit(f"Reading Registers - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "header")
        self.signals.log.emit("=" * 80, "header")
        self.signals.log.emit("", "")

        self.scan_thread = threading.Thread(target=self.scan_worker, daemon=True)
        self.scan_thread.start()

    def stop_scan(self):
        """Stop the scanning process"""
        self.scanning = False
        self.signals.status.emit("Stopping scan...")

    def scan_worker(self):
        """Worker thread for reading registers"""
        try:
            ip = self.ip_entry.text().strip()
            port = int(self.port_entry.text())
            timeout = float(self.timeout_entry.text())
            unit_id = int(self.unit_entry.text())
            start_reg = int(self.start_register_entry.text())
            reg_count = int(self.register_count_entry.text())
            zero_based = self.zero_based_check.isChecked()
            continuous = self.continuous_read_check.isChecked()
            read_individually = self.read_individually_check.isChecked()

            # Get polling interval
            try:
                interval = float(self.polling_interval_entry.text())
                if interval < 0.1:
                    interval = 0.1  # Minimum 0.1 second interval
            except:
                interval = 1.0

            # Store the user's input address for display
            display_start = start_reg

            # Adjust for 0-based vs 1-based addressing
            if not zero_based:
                # User entered 1-based address, convert to 0-based for protocol
                start_reg -= 1

            # Determine register type to read
            if self.holding_radio.isChecked():
                register_type = 'holding'
                reg_name = "Holding Registers"
            elif self.input_radio.isChecked():
                register_type = 'input'
                reg_name = "Input Registers"
            elif self.coils_radio.isChecked():
                register_type = 'coils'
                reg_name = "Coils"
            else:  # discrete inputs
                register_type = 'discrete'
                reg_name = "Discrete Inputs"

            self.signals.log.emit(f"Device: {ip}:{port}", "")
            self.signals.log.emit(f"Unit ID: {unit_id}", "")
            self.signals.log.emit(f"Register Type: {reg_name}", "")
            self.signals.log.emit(f"Register Range: {display_start} to {display_start + reg_count - 1} ({reg_count} registers)", "")
            if continuous:
                self.signals.log.emit(f"Continuous mode: reading every {interval} seconds", "info")
            self.signals.log.emit("", "")

            read_count = 0
            while self.scanning:
                read_count += 1

                if continuous:
                    self.signals.status.emit(f"Reading registers... (read #{read_count})")
                else:
                    self.signals.status.emit(f"Connecting to {ip}:{port}...")

                self.signals.progress.emit(25)

                # Connect and read registers
                if read_individually:
                    # Read each register individually
                    registers = self.read_registers_individually(ip, port, unit_id, timeout, register_type, start_reg, reg_count)

                    # Count successes and errors
                    success_count = sum(1 for r in registers if not isinstance(r, dict))
                    error_count = sum(1 for r in registers if isinstance(r, dict))

                    self.signals.progress.emit(75)

                    if continuous:
                        self.signals.log.emit(f"Read #{read_count} at {datetime.now().strftime('%H:%M:%S')}: {success_count} OK, {error_count} errors", "success" if error_count == 0 else "info")
                    else:
                        self.signals.log.emit(f"Read complete: {success_count} successful, {error_count} errors", "success" if error_count == 0 else "info")

                    # Always update table with mixed results
                    self.signals.update_table.emit(registers, start_reg)

                    if continuous:
                        self.signals.status.emit(f"Continuous read active (#{read_count})")
                    else:
                        self.signals.status.emit(f"Read {success_count}/{reg_count} registers")
                else:
                    # Read all registers in one request (original behavior)
                    result = self.read_registers(ip, port, unit_id, timeout, register_type, start_reg, reg_count)

                    self.signals.progress.emit(75)

                    if result['success']:
                        if continuous:
                            self.signals.log.emit(f"Read #{read_count} successful at {datetime.now().strftime('%H:%M:%S')}", "success")
                        else:
                            self.signals.log.emit(f"Successfully read {reg_count} registers", "success")
                        # Pass the protocol address (0-based) to populate_table
                        self.signals.update_table.emit(result['registers'], start_reg)
                        if continuous:
                            self.signals.status.emit(f"Continuous read active (#{read_count})")
                        else:
                            self.signals.status.emit(f"Successfully read {reg_count} registers")
                    else:
                        self.signals.log.emit(f"ERROR: {result['error']}", "error")
                        self.signals.status.emit("Failed to read registers")
                        if not continuous:
                            break

                self.signals.progress.emit(100)

                # If not continuous mode, exit after one read
                if not continuous:
                    break

                # Wait for the interval before next read
                if self.scanning and continuous:
                    time.sleep(interval)

        except Exception as e:
            self.signals.log.emit(f"Error: {str(e)}", "error")
            self.signals.status.emit("Operation failed")
        finally:
            self.signals.finished.emit()

    def populate_table(self, registers, start_address):
        """Populate the table with register values and interpretations"""
        self.results_table.setRowCount(len(registers))

        # Get options
        reverse_byte = self.reverse_byte_order_check.isChecked()
        reverse_word = self.reverse_word_order_check.isChecked()
        zero_based = self.zero_based_check.isChecked()

        # Check if we're dealing with bit values (coils/discrete inputs)
        is_bit_type = False
        if len(registers) > 0:
            first_valid = next((v for v in registers if not isinstance(v, dict)), None)
            if first_valid is not None and isinstance(first_valid, bool):
                is_bit_type = True

        for i, value in enumerate(registers):
            # Calculate display address
            addr = start_address + i
            if not zero_based:
                addr += 1  # Display as 1-based

            row = i

            # Check if this is an error entry (dict with 'error' key)
            if isinstance(value, dict) and 'error' in value:
                # Display error in table
                self.results_table.setItem(row, 0, QTableWidgetItem(str(addr)))
                error_msg = value['error']
                for col in range(1, 8):
                    item = QTableWidgetItem("ERROR")
                    item.setToolTip(error_msg)  # Show full error on hover
                    self.results_table.setItem(row, col, item)
                continue

            # Handle bit values (coils/discrete inputs)
            if is_bit_type:
                self.results_table.setItem(row, 0, QTableWidgetItem(str(addr)))
                bit_val = "1" if value else "0"
                self.results_table.setItem(row, 1, QTableWidgetItem(bit_val))
                # Mark other columns as N/A for bit values
                for col in range(2, 8):
                    self.results_table.setItem(row, col, QTableWidgetItem("-"))
                continue

            # Apply byte order reversal if needed
            if reverse_byte:
                # Swap the bytes within the 16-bit word
                value = ((value & 0xFF) << 8) | ((value >> 8) & 0xFF)

            # Address
            self.results_table.setItem(row, 0, QTableWidgetItem(str(addr)))

            # Hex value
            hex_val = f"0x{value:04X}"
            self.results_table.setItem(row, 1, QTableWidgetItem(hex_val))

            # Uint16
            uint16_val = value
            self.results_table.setItem(row, 2, QTableWidgetItem(str(uint16_val)))

            # Int16 (signed)
            int16_val = value if value < 32768 else value - 65536
            self.results_table.setItem(row, 3, QTableWidgetItem(str(int16_val)))

            # Uint32 (combine with next register if available)
            if i + 1 < len(registers):
                # Get next register value
                next_value = registers[i + 1]

                # Check if next value is an error
                if isinstance(next_value, dict) and 'error' in next_value:
                    # Can't calculate 32-bit values if next register is an error
                    self.results_table.setItem(row, 4, QTableWidgetItem("N/A"))
                    self.results_table.setItem(row, 5, QTableWidgetItem("N/A"))
                    self.results_table.setItem(row, 6, QTableWidgetItem("N/A"))
                else:
                    # Next value is valid, proceed with 32-bit calculations
                    if reverse_byte:
                        # Swap bytes in the second register too
                        next_value = ((next_value & 0xFF) << 8) | ((next_value >> 8) & 0xFF)

                    # Combine words (apply word order)
                    if reverse_word:
                        uint32_val = (next_value << 16) | value
                    else:
                        uint32_val = (value << 16) | next_value

                    self.results_table.setItem(row, 4, QTableWidgetItem(str(uint32_val)))

                    # Int32 (signed 32-bit)
                    int32_val = uint32_val if uint32_val < 2147483648 else uint32_val - 4294967296
                    self.results_table.setItem(row, 5, QTableWidgetItem(str(int32_val)))

                    # Float32
                    try:
                        # Pack as two 16-bit unsigned ints, then unpack as float
                        if reverse_word:
                            bytes_data = struct.pack('>HH', next_value, value)
                        else:
                            bytes_data = struct.pack('>HH', value, next_value)
                        float_val = struct.unpack('>f', bytes_data)[0]
                        self.results_table.setItem(row, 6, QTableWidgetItem(f"{float_val:.6f}"))
                    except:
                        self.results_table.setItem(row, 6, QTableWidgetItem("N/A"))
            else:
                self.results_table.setItem(row, 4, QTableWidgetItem("-"))
                self.results_table.setItem(row, 5, QTableWidgetItem("-"))
                self.results_table.setItem(row, 6, QTableWidgetItem("-"))

            # String (ASCII representation of the 2 bytes)
            try:
                high_byte = (value >> 8) & 0xFF
                low_byte = value & 0xFF
                # Only show printable ASCII characters
                chars = []
                if 32 <= high_byte <= 126:
                    chars.append(chr(high_byte))
                if 32 <= low_byte <= 126:
                    chars.append(chr(low_byte))
                string_val = ''.join(chars) if chars else '.'
                self.results_table.setItem(row, 7, QTableWidgetItem(string_val))
            except:
                self.results_table.setItem(row, 7, QTableWidgetItem('.'))

    def read_registers(self, ip, port, unit_id, timeout, register_type, start_reg, count):
        """Read registers from a Modbus device"""
        result = {
            'success': False,
            'registers': None,
            'error': None
        }

        try:
            client = ModbusTcpClient(ip, port=port, timeout=timeout)

            if not client.connect():
                result['error'] = "Failed to connect to device"
                return result

            try:
                # Try with 'slave' parameter first (pymodbus 3.x compatibility)
                try:
                    if register_type == 'holding':
                        response = client.read_holding_registers(start_reg, count=count, slave=unit_id)
                    elif register_type == 'input':
                        response = client.read_input_registers(start_reg, count=count, slave=unit_id)
                    elif register_type == 'coils':
                        response = client.read_coils(start_reg, count=count, slave=unit_id)
                    else:  # discrete inputs
                        response = client.read_discrete_inputs(start_reg, count=count, slave=unit_id)
                except TypeError:
                    # Fallback to 'unit' parameter if 'slave' doesn't work
                    if register_type == 'holding':
                        response = client.read_holding_registers(start_reg, count=count, unit=unit_id)
                    elif register_type == 'input':
                        response = client.read_input_registers(start_reg, count=count, unit=unit_id)
                    elif register_type == 'coils':
                        response = client.read_coils(start_reg, count=count, unit=unit_id)
                    else:  # discrete inputs
                        response = client.read_discrete_inputs(start_reg, count=count, unit=unit_id)

                if response.isError():
                    result['error'] = f"Modbus error: {response}"
                else:
                    result['success'] = True
                    # For coils and discrete inputs, use .bits instead of .registers
                    if register_type in ['coils', 'discrete']:
                        result['registers'] = response.bits[:count]  # Only take the requested count
                    else:
                        result['registers'] = response.registers

            except Exception as e:
                result['error'] = f"Failed to read registers: {str(e)}"
            finally:
                client.close()

        except Exception as e:
            result['error'] = f"Connection error: {str(e)}"

        return result

    def read_registers_individually(self, ip, port, unit_id, timeout, register_type, start_reg, count):
        """Read registers one at a time, continuing even if some fail"""
        results = []

        client = ModbusTcpClient(ip, port=port, timeout=timeout)

        if not client.connect():
            # If can't connect at all, return all errors
            for i in range(count):
                results.append({'error': 'Failed to connect to device'})
            return results

        try:
            for i in range(count):
                reg_addr = start_reg + i
                try:
                    # Try with 'slave' parameter first (pymodbus 3.x compatibility)
                    try:
                        if register_type == 'holding':
                            response = client.read_holding_registers(reg_addr, count=1, slave=unit_id)
                        elif register_type == 'input':
                            response = client.read_input_registers(reg_addr, count=1, slave=unit_id)
                        elif register_type == 'coils':
                            response = client.read_coils(reg_addr, count=1, slave=unit_id)
                        else:  # discrete inputs
                            response = client.read_discrete_inputs(reg_addr, count=1, slave=unit_id)
                    except TypeError:
                        # Fallback to 'unit' parameter if 'slave' doesn't work
                        if register_type == 'holding':
                            response = client.read_holding_registers(reg_addr, count=1, unit=unit_id)
                        elif register_type == 'input':
                            response = client.read_input_registers(reg_addr, count=1, unit=unit_id)
                        elif register_type == 'coils':
                            response = client.read_coils(reg_addr, count=1, unit=unit_id)
                        else:  # discrete inputs
                            response = client.read_discrete_inputs(reg_addr, count=1, unit=unit_id)

                    if response.isError():
                        results.append({'error': f"Modbus error: {response}"})
                    else:
                        # For coils and discrete inputs, use .bits[0] instead of .registers[0]
                        if register_type in ['coils', 'discrete']:
                            results.append(response.bits[0])
                        else:
                            results.append(response.registers[0])

                except Exception as e:
                    results.append({'error': f"{str(e)}"})

        finally:
            client.close()

        return results

    def scan_finished(self):
        """Called when scan is finished"""
        self.scan_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def export_results(self):
        """Export results to a CSV file"""
        if self.results_table.rowCount() == 0:
            QMessageBox.information(self, "Export", "No results to export")
            return

        filename = f"modbus_registers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        try:
            with open(filename, 'w') as f:
                # Write header
                headers = []
                for col in range(self.results_table.columnCount()):
                    headers.append(self.results_table.horizontalHeaderItem(col).text())
                f.write(','.join(headers) + '\n')

                # Write data
                for row in range(self.results_table.rowCount()):
                    row_data = []
                    for col in range(self.results_table.columnCount()):
                        item = self.results_table.item(row, col)
                        row_data.append(item.text() if item else '')
                    f.write(','.join(row_data) + '\n')

            QMessageBox.information(self, "Export", f"Results exported to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export results: {str(e)}")


def main():
    app = QApplication(sys.argv)
    window = ModbusScannerGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
