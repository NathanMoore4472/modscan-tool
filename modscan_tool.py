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

from updater import UpdateChecker
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTextEdit, QProgressBar, QCheckBox, QGroupBox,
                             QMessageBox, QFileDialog, QRadioButton, QButtonGroup,
                             QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
                             QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator,
                             QAbstractItemView, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QSettings
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
import pymodbus
from opf_parser import parse_opf_file


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
        self.app_version = "1.2.0"
        self.setWindowTitle("ModScan Tool")
        self.setGeometry(100, 100, 1050, 750)

        self.scanning = False
        self.scan_thread = None
        self.signals = WorkerSignals()
        self.tag_mappings = {}  # Store tag mappings from imported .opf files
        self.tags_imported = False  # Track if tags have been imported
        self.auto_expand_bits = False  # Preference for auto-expanding bit rows

        # Settings for IP history
        self.settings = QSettings("ModScanTool", "ModbusScannerGUI")

        # Initialize update checker
        self.updater = UpdateChecker(self.app_version, self.settings, self)

        # Connect signals
        self.signals.log.connect(self.log_message)
        self.signals.status.connect(self.update_status)
        self.signals.progress.connect(self.update_progress)
        self.signals.finished.connect(self.scan_finished)
        self.signals.update_table.connect(self.populate_table)

        self.init_ui()
        self.create_menu_bar()
        self.load_settings()

        # Check for updates on startup if enabled
        if self.updater.check_updates_on_startup:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1000, lambda: self.updater.check_for_updates(silent=True))

    def init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        central_widget.setLayout(layout)

        # Connection Settings Group - Horizontal Layout
        connection_group = QGroupBox("Connection")
        connection_layout = QHBoxLayout()
        connection_layout.setSpacing(15)

        # IP Address with history dropdown
        connection_layout.addWidget(QLabel("IP Address:"))
        self.ip_combo = QComboBox()
        self.ip_combo.setEditable(True)
        self.ip_combo.setMinimumWidth(150)
        self.ip_combo.setMaximumWidth(200)
        self.ip_combo.addItem("192.168.1.1")
        self.ip_combo.addItem("127.0.0.1")
        self.ip_combo.setCurrentIndex(0)
        connection_layout.addWidget(self.ip_combo)

        # Port
        connection_layout.addWidget(QLabel("Port:"))
        self.port_entry = QLineEdit("502")
        self.port_entry.setMaximumWidth(80)
        connection_layout.addWidget(self.port_entry)

        # Unit ID
        connection_layout.addWidget(QLabel("Unit ID:"))
        self.unit_entry = QLineEdit("1")
        self.unit_entry.setMaximumWidth(80)
        connection_layout.addWidget(self.unit_entry)

        # Timeout
        connection_layout.addWidget(QLabel("Timeout:"))
        self.timeout_entry = QLineEdit("2")
        self.timeout_entry.setMaximumWidth(60)
        connection_layout.addWidget(self.timeout_entry)
        connection_layout.addWidget(QLabel("sec"))

        connection_layout.addStretch()
        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)

        # Register Settings Group - Horizontal Layout
        register_group = QGroupBox("Register Configuration")
        register_layout = QHBoxLayout()
        register_layout.setSpacing(15)

        # Data Type dropdown
        register_layout.addWidget(QLabel("Data Type:"))
        self.register_type_combo = QComboBox()
        self.register_type_combo.addItem("Holding Registers (16-bit)", "holding")
        self.register_type_combo.addItem("Input Registers (16-bit)", "input")
        self.register_type_combo.addItem("Coils (1-bit)", "coils")
        self.register_type_combo.addItem("Discrete Inputs (1-bit)", "discrete")
        self.register_type_combo.setMinimumWidth(200)
        register_layout.addWidget(self.register_type_combo)

        # Start Register
        register_layout.addWidget(QLabel("Start:"))
        self.start_register_entry = QLineEdit("0")
        self.start_register_entry.setMaximumWidth(80)
        register_layout.addWidget(self.start_register_entry)

        # Register Count
        register_layout.addWidget(QLabel("Count:"))
        self.register_count_entry = QLineEdit("10")
        self.register_count_entry.setMaximumWidth(80)
        register_layout.addWidget(self.register_count_entry)

        register_layout.addStretch()
        register_group.setLayout(register_layout)
        layout.addWidget(register_group)

        # Options Group - Horizontal Layout
        options_group = QGroupBox("Options")
        options_layout = QHBoxLayout()
        options_layout.setSpacing(15)

        self.reverse_byte_order_check = QCheckBox("Reverse Byte Order")
        options_layout.addWidget(self.reverse_byte_order_check)

        self.reverse_word_order_check = QCheckBox("Reverse Word Order")
        options_layout.addWidget(self.reverse_word_order_check)

        self.zero_based_check = QCheckBox("0-based Addressing")
        self.zero_based_check.setChecked(True)
        options_layout.addWidget(self.zero_based_check)

        self.continuous_read_check = QCheckBox("Continuous Read")
        options_layout.addWidget(self.continuous_read_check)

        options_layout.addWidget(QLabel("Interval:"))
        self.polling_interval_entry = QLineEdit("1")
        self.polling_interval_entry.setMaximumWidth(50)
        options_layout.addWidget(self.polling_interval_entry)
        options_layout.addWidget(QLabel("sec"))

        self.read_individually_check = QCheckBox("Read Individually")
        self.read_individually_check.setToolTip("Slower, but handles missing registers")
        options_layout.addWidget(self.read_individually_check)

        options_layout.addStretch()
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

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
            "All Columns", "Address", "Tag Name", "Hex", "Binary", "Uint16", "Int16", "Uint32", "Int32", "Float32", "String"
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

        # Create tree widget (replaces table for expandable bit rows)
        self.results_table = QTreeWidget()
        self.results_table.setColumnCount(10)
        self.results_table.setHeaderLabels([
            "Address", "Tag Name", "Hex", "Binary", "Uint16", "Int16", "Uint32", "Int32", "Float32", "String"
        ])

        # Configure tree widget
        header = self.results_table.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)

        # Enable editing for Tag Name column
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)

        # Show Tag Name column by default (user can add tags manually)
        # No longer hide it - it's always available

        results_layout.addWidget(self.results_table)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

    def load_settings(self):
        """Load saved settings from QSettings"""
        # Load IP history
        ip_history = self.settings.value("ip_history", [])
        if ip_history:
            self.ip_combo.clear()
            for ip in ip_history:
                self.ip_combo.addItem(ip)
            self.ip_combo.setCurrentIndex(0)

    def save_settings(self):
        """Save current settings to QSettings"""
        # Save IP history (keep last 10 unique IPs)
        ip_history = []
        current_ip = self.ip_combo.currentText()

        # Add current IP first
        if current_ip:
            ip_history.append(current_ip)

        # Add other IPs from combo
        for i in range(self.ip_combo.count()):
            ip = self.ip_combo.itemText(i)
            if ip and ip not in ip_history:
                ip_history.append(ip)

        # Keep only last 10
        ip_history = ip_history[:10]
        self.settings.setValue("ip_history", ip_history)

    def get_register_type(self):
        """Get the selected register type from combo box"""
        return self.register_type_combo.currentData()

    def set_register_type(self, reg_type):
        """Set the register type in combo box by data value"""
        for i in range(self.register_type_combo.count()):
            if self.register_type_combo.itemData(i) == reg_type:
                self.register_type_combo.setCurrentIndex(i)
                return

    def create_menu_bar(self):
        """Create the menu bar with File and Help menus"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        # Import action
        import_action = file_menu.addAction("Import from KEPServerEX...")
        import_action.triggered.connect(self.import_opf)
        import_action.setShortcut("Ctrl+I")

        file_menu.addSeparator()

        # Preferences action
        prefs_action = file_menu.addAction("Preferences...")
        prefs_action.triggered.connect(self.show_preferences_dialog)
        prefs_action.setShortcut("Ctrl+,")
        prefs_action.setMenuRole(prefs_action.MenuRole.NoRole)  # Keep in File menu on macOS

        # Help menu
        help_menu = menubar.addMenu("Help")

        # Check for Updates action
        update_action = help_menu.addAction("Check for Updates...")
        update_action.triggered.connect(lambda: self.updater.check_for_updates(silent=False))

        help_menu.addSeparator()

        # About action
        about_action = help_menu.addAction("About ModScan Tool")
        about_action.triggered.connect(self.show_about_dialog)
        about_action.setMenuRole(about_action.MenuRole.NoRole)  # Keep in Help menu on macOS

    def show_about_dialog(self):
        """Show the About dialog with version and info"""
        pymodbus_version = getattr(pymodbus, '__version__', 'unknown')

        try:
            from PyQt6 import QtCore
            pyqt_version = QtCore.PYQT_VERSION_STR
        except:
            pyqt_version = 'unknown'

        about_text = f"""
<h2>ModScan Tool</h2>
<p><b>Version:</b> {self.app_version}</p>

<h3>About</h3>
<p>A modern, cross-platform GUI application for reading and monitoring Modbus TCP devices.</p>
<p><i>Features automatic update checking to keep you up to date!</i></p>

<h3>Dependencies</h3>
<ul>
<li><b>pymodbus:</b> {pymodbus_version}</li>
<li><b>PyQt6:</b> {pyqt_version}</li>
<li><b>Python:</b> {sys.version.split()[0]}</li>
</ul>

<h3>Links</h3>
<p>🔗 <a href="https://github.com/NathanMoore4472/modscan-tool">GitHub Repository</a></p>
<p>🐛 <a href="https://github.com/NathanMoore4472/modscan-tool/issues">Report Issues</a></p>

<h3>License</h3>
<p>GNU General Public License v3.0</p>

<h3>Author</h3>
<p>Nathan Moore</p>

<p style="margin-top: 20px; font-size: small; color: gray;">
Built with Python, PyQt6, and pymodbus
</p>
        """

        msg = QMessageBox(self)
        msg.setWindowTitle("About ModScan Tool")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(about_text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def show_preferences_dialog(self):
        """Show the Preferences dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Preferences")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Update Settings group
        update_group = QGroupBox("Update Settings")
        update_layout = QVBoxLayout()

        # Checkbox for auto-update checking
        check_startup_cb = QCheckBox("Check for updates on startup")
        check_startup_cb.setChecked(self.updater.check_updates_on_startup)
        check_startup_cb.setToolTip("Automatically check for new versions when the application starts")
        update_layout.addWidget(check_startup_cb)

        # Checkbox for debug logging
        debug_logging_cb = QCheckBox("Enable update debug logging")
        debug_logging_cb.setChecked(self.updater.update_debug_logging)
        debug_logging_cb.setToolTip("Save detailed logs to Desktop when updating (for troubleshooting)")
        update_layout.addWidget(debug_logging_cb)

        update_group.setLayout(update_layout)
        layout.addWidget(update_group)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)

        # If accepted, save the preferences
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.updater.check_updates_on_startup = check_startup_cb.isChecked()
            self.updater.update_debug_logging = debug_logging_cb.isChecked()

            # Save to QSettings
            self.settings.setValue("check_updates_on_startup", self.updater.check_updates_on_startup)
            self.settings.setValue("update_debug_logging", self.updater.update_debug_logging)

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
        self.results_table.clear()
        self.progress_bar.setValue(0)
        self.info_label.setText("Table cleared.")

    def filter_table(self):
        """Filter tree items based on search criteria"""
        filter_text = self.filter_entry.text().lower()
        column_index = self.filter_column_combo.currentIndex() - 1  # -1 because first item is "All Columns"

        if not filter_text:
            # Show all items if filter is empty
            iterator = QTreeWidgetItemIterator(self.results_table)
            while iterator.value():
                iterator.value().setHidden(False)
                iterator += 1
            return

        # Filter items
        iterator = QTreeWidgetItemIterator(self.results_table)
        while iterator.value():
            item = iterator.value()
            show_item = False

            if column_index == -1:
                # Search all columns
                for col in range(self.results_table.columnCount()):
                    if filter_text in item.text(col).lower():
                        show_item = True
                        break
            else:
                # Search specific column
                if filter_text in item.text(column_index).lower():
                    show_item = True

            item.setHidden(not show_item)

            # If this is a child item (bit row) that matches, also show its parent
            if show_item and item.parent():
                item.parent().setHidden(False)

            iterator += 1

    def clear_filter(self):
        """Clear the filter and show all items"""
        self.filter_entry.clear()
        iterator = QTreeWidgetItemIterator(self.results_table)
        while iterator.value():
            iterator.value().setHidden(False)
            iterator += 1

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
            reg_type = self.get_register_type()
            is_bit_type = reg_type in ['coils', 'discrete']
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
            ipaddress.ip_address(self.ip_combo.currentText().strip())

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
            ip = self.ip_combo.currentText().strip()
            port = int(self.port_entry.text())
            timeout = float(self.timeout_entry.text())
            unit_id = int(self.unit_entry.text())
            start_reg = int(self.start_register_entry.text())
            reg_count = int(self.register_count_entry.text())
            zero_based = self.zero_based_check.isChecked()
            continuous = self.continuous_read_check.isChecked()
            read_individually = self.read_individually_check.isChecked()

            # Save settings (including IP history)
            self.save_settings()

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
            register_type = self.get_register_type()
            reg_name_map = {
                'holding': "Holding Registers",
                'input': "Input Registers",
                'coils': "Coils",
                'discrete': "Discrete Inputs"
            }
            reg_name = reg_name_map.get(register_type, "Unknown")

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
        """Populate the tree widget with register values (with expandable bit rows)"""

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

        # Check if this is first population or structure changed
        needs_rebuild = False
        if self.results_table.topLevelItemCount() != len(registers):
            needs_rebuild = True

        # If structure hasn't changed, update in place
        if not needs_rebuild and self.results_table.topLevelItemCount() > 0:
            self._update_table_values(registers, start_address, reverse_byte, reverse_word, zero_based, is_bit_type)
            return

        # Otherwise rebuild the table
        self.results_table.clear()
        self.results_table.setHeaderLabels([
            "Address", "Tag Name", "Hex", "Binary", "Uint16", "Int16", "Uint32", "Int32", "Float32", "String"
        ])

        for i, value in enumerate(registers):
            # Calculate display address
            addr = start_address + i
            if not zero_based:
                addr += 1  # Display as 1-based

            # Check if this is an error entry
            if isinstance(value, dict) and 'error' in value:
                item = QTreeWidgetItem([str(addr), "ERROR", "ERROR", "ERROR", "ERROR", "ERROR", "ERROR", "ERROR", "ERROR", "ERROR"])
                item.setToolTip(0, value['error'])
                self.results_table.addTopLevelItem(item)
                continue

            # Handle bit values (coils/discrete inputs)
            if is_bit_type:
                tag_name = self.tag_mappings.get((addr, None), "")
                bit_val = "1" if value else "0"
                item = QTreeWidgetItem([str(addr), tag_name, bit_val, "-", "-", "-", "-", "-", "-", "-"])
                self.results_table.addTopLevelItem(item)
                continue

            # Apply byte order reversal if needed
            if reverse_byte:
                value = ((value & 0xFF) << 8) | ((value >> 8) & 0xFF)

            # Create parent item for the register
            hex_val = f"0x{value:04X}"
            binary_val = format(value, '016b')

            # Get tag for whole register
            whole_reg_tag = self.tag_mappings.get((addr, None), "")

            # Uint16, Int16
            uint16_val = str(value)
            int16_val = value if value < 32768 else value - 65536

            # Uint32, Int32, Float32
            uint32_str = "-"
            int32_str = "-"
            float32_str = "-"

            if i + 1 < len(registers):
                next_value = registers[i + 1]
                if not (isinstance(next_value, dict) and 'error' in next_value):
                    if reverse_byte:
                        next_value = ((next_value & 0xFF) << 8) | ((next_value >> 8) & 0xFF)

                    if reverse_word:
                        uint32_val = (next_value << 16) | value
                    else:
                        uint32_val = (value << 16) | next_value

                    uint32_str = str(uint32_val)
                    int32_val = uint32_val if uint32_val < 2147483648 else uint32_val - 4294967296
                    int32_str = str(int32_val)

                    try:
                        if reverse_word:
                            bytes_data = struct.pack('>HH', next_value, value)
                        else:
                            bytes_data = struct.pack('>HH', value, next_value)
                        float_val = struct.unpack('>f', bytes_data)[0]
                        float32_str = f"{float_val:.6f}"
                    except:
                        float32_str = "N/A"

            # String
            try:
                high_byte = (value >> 8) & 0xFF
                low_byte = value & 0xFF
                chars = []
                if 32 <= high_byte <= 126:
                    chars.append(chr(high_byte))
                if 32 <= low_byte <= 126:
                    chars.append(chr(low_byte))
                string_val = ''.join(chars) if chars else '.'
            except:
                string_val = '.'

            # Create parent item
            parent_item = QTreeWidgetItem([
                str(addr),
                whole_reg_tag,
                hex_val,
                binary_val,
                uint16_val,
                str(int16_val),
                uint32_str,
                int32_str,
                float32_str,
                string_val
            ])

            # Make Tag Name column editable
            parent_item.setFlags(parent_item.flags() | Qt.ItemFlag.ItemIsEditable)

            self.results_table.addTopLevelItem(parent_item)

            # Always add child items for all 16 bits
            for bit in range(16):
                bit_value = (value >> bit) & 1
                # Get tag for this bit if it exists
                bit_tag = self.tag_mappings.get((addr, bit), "")

                # Display bit number based on addressing mode
                bit_display = bit + 1 if not zero_based else bit

                bit_item = QTreeWidgetItem([
                    f"{addr}.{bit_display}",
                    bit_tag,
                    str(bit_value),
                    binary_val,  # Show full register binary for context
                    hex_val,     # Show full register hex for context
                    "-",
                    "-",
                    "-",
                    "-",
                    "-"
                ])
                # Make Tag Name editable for bit rows too
                bit_item.setFlags(bit_item.flags() | Qt.ItemFlag.ItemIsEditable)
                parent_item.addChild(bit_item)

            # Use auto_expand_bits preference for new items
            if self.auto_expand_bits:
                parent_item.setExpanded(True)
            else:
                parent_item.setExpanded(False)

    def _update_table_values(self, registers, start_address, reverse_byte, reverse_word, zero_based, is_bit_type):
        """Update existing table items in place (preserves tag names, expansion state, scroll position)"""

        for i, value in enumerate(registers):
            # Calculate display address
            addr = start_address + i
            if not zero_based:
                addr += 1  # Display as 1-based

            # Get the existing parent item
            parent_item = self.results_table.topLevelItem(i)
            if not parent_item:
                continue

            # Check if this is an error entry
            if isinstance(value, dict) and 'error' in value:
                parent_item.setText(0, str(addr))
                parent_item.setText(2, "ERROR")
                parent_item.setText(3, "ERROR")
                parent_item.setText(4, "ERROR")
                parent_item.setText(5, "ERROR")
                parent_item.setText(6, "ERROR")
                parent_item.setText(7, "ERROR")
                parent_item.setText(8, "ERROR")
                parent_item.setText(9, "ERROR")
                parent_item.setToolTip(0, value['error'])
                continue

            # Handle bit values (coils/discrete inputs)
            if is_bit_type:
                bit_val = "1" if value else "0"
                parent_item.setText(0, str(addr))
                parent_item.setText(2, bit_val)
                parent_item.setText(3, "-")
                parent_item.setText(4, "-")
                parent_item.setText(5, "-")
                parent_item.setText(6, "-")
                parent_item.setText(7, "-")
                parent_item.setText(8, "-")
                parent_item.setText(9, "-")
                continue

            # Apply byte order reversal if needed
            if reverse_byte:
                value = ((value & 0xFF) << 8) | ((value >> 8) & 0xFF)

            # Update parent item values
            hex_val = f"0x{value:04X}"
            binary_val = format(value, '016b')
            uint16_val = str(value)
            int16_val = value if value < 32768 else value - 65536

            # Uint32, Int32, Float32
            uint32_str = "-"
            int32_str = "-"
            float32_str = "-"

            if i + 1 < len(registers):
                next_value = registers[i + 1]
                if not (isinstance(next_value, dict) and 'error' in next_value):
                    if reverse_byte:
                        next_value = ((next_value & 0xFF) << 8) | ((next_value >> 8) & 0xFF)

                    if reverse_word:
                        uint32_val = (next_value << 16) | value
                    else:
                        uint32_val = (value << 16) | next_value

                    uint32_str = str(uint32_val)
                    int32_val = uint32_val if uint32_val < 2147483648 else uint32_val - 4294967296
                    int32_str = str(int32_val)

                    try:
                        if reverse_word:
                            bytes_data = struct.pack('>HH', next_value, value)
                        else:
                            bytes_data = struct.pack('>HH', value, next_value)
                        float_val = struct.unpack('>f', bytes_data)[0]
                        float32_str = f"{float_val:.6f}"
                    except:
                        float32_str = "N/A"

            # String
            try:
                high_byte = (value >> 8) & 0xFF
                low_byte = value & 0xFF
                chars = []
                if 32 <= high_byte <= 126:
                    chars.append(chr(high_byte))
                if 32 <= low_byte <= 126:
                    chars.append(chr(low_byte))
                string_val = ''.join(chars) if chars else '.'
            except:
                string_val = '.'

            # Update parent item (preserve column 1 - Tag Name)
            parent_item.setText(0, str(addr))
            # Column 1 (Tag Name) is NOT updated - preserves user edits
            parent_item.setText(2, hex_val)
            parent_item.setText(3, binary_val)
            parent_item.setText(4, uint16_val)
            parent_item.setText(5, str(int16_val))
            parent_item.setText(6, uint32_str)
            parent_item.setText(7, int32_str)
            parent_item.setText(8, float32_str)
            parent_item.setText(9, string_val)

            # Update child bit items
            for bit in range(16):
                if bit < parent_item.childCount():
                    bit_item = parent_item.child(bit)
                    bit_value = (value >> bit) & 1

                    # Display bit number based on addressing mode
                    bit_display = bit + 1 if not zero_based else bit

                    # Update bit item (preserve column 1 - Tag Name)
                    bit_item.setText(0, f"{addr}.{bit_display}")
                    # Column 1 (Tag Name) is NOT updated - preserves user edits
                    bit_item.setText(2, str(bit_value))
                    bit_item.setText(3, binary_val)
                    bit_item.setText(4, hex_val)

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
                # Try different parameter names for different pymodbus versions
                response = None
                for param_style in [('slave', unit_id), ('unit', unit_id), (None, None)]:
                    try:
                        param_name, param_value = param_style
                        if param_name:
                            kwargs = {'count': count, param_name: param_value}
                        else:
                            kwargs = {'count': count}

                        if register_type == 'holding':
                            response = client.read_holding_registers(start_reg, **kwargs)
                        elif register_type == 'input':
                            response = client.read_input_registers(start_reg, **kwargs)
                        elif register_type == 'coils':
                            response = client.read_coils(start_reg, **kwargs)
                        else:  # discrete inputs
                            response = client.read_discrete_inputs(start_reg, **kwargs)
                        break  # If successful, exit the loop
                    except TypeError:
                        continue  # Try next parameter style

                if response is None:
                    raise Exception("Could not call read function with any known parameter style")

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
                    # Try different parameter names for different pymodbus versions
                    response = None
                    for param_style in [('slave', unit_id), ('unit', unit_id), (None, None)]:
                        try:
                            param_name, param_value = param_style
                            if param_name:
                                kwargs = {'count': 1, param_name: param_value}
                            else:
                                kwargs = {'count': 1}

                            if register_type == 'holding':
                                response = client.read_holding_registers(reg_addr, **kwargs)
                            elif register_type == 'input':
                                response = client.read_input_registers(reg_addr, **kwargs)
                            elif register_type == 'coils':
                                response = client.read_coils(reg_addr, **kwargs)
                            else:  # discrete inputs
                                response = client.read_discrete_inputs(reg_addr, **kwargs)
                            break  # If successful, exit the loop
                        except TypeError:
                            continue  # Try next parameter style

                    if response is None:
                        results.append({'error': 'Could not call read function with any known parameter style'})
                        continue

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
        if self.results_table.topLevelItemCount() == 0:
            QMessageBox.information(self, "Export", "No results to export")
            return

        filename = f"modbus_registers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        try:
            with open(filename, 'w') as f:
                # Write header
                headers = []
                for col in range(self.results_table.columnCount()):
                    headers.append(self.results_table.headerItem().text(col))
                f.write(','.join(headers) + '\n')

                # Write data (iterate through tree items)
                iterator = QTreeWidgetItemIterator(self.results_table)
                while iterator.value():
                    item = iterator.value()
                    row_data = []
                    for col in range(self.results_table.columnCount()):
                        row_data.append(item.text(col))
                    f.write(','.join(row_data) + '\n')
                    iterator += 1

            QMessageBox.information(self, "Export", f"Results exported to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export results: {str(e)}")

    def import_opf(self):
        """Import device configuration from KEPServerEX .opf file"""
        # Open file dialog to select .opf file
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select KEPServerEX Project File",
            "",
            "KEPServerEX Files (*.opf);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Parse the .opf file
            self.signals.status.emit("Parsing KEPServerEX file...")
            config = parse_opf_file(file_path)

            # Populate connection settings
            if config['ip']:
                self.ip_combo.setCurrentText(config['ip'])
                # Add to combo if not already there
                if self.ip_combo.findText(config['ip']) == -1:
                    self.ip_combo.addItem(config['ip'])
                    self.ip_combo.setCurrentText(config['ip'])

            self.port_entry.setText(str(config['port']))
            self.unit_entry.setText(str(config['unit_id']))

            # Populate register settings
            if config['register_count'] > 0:
                self.start_register_entry.setText(str(config['min_address']))
                self.register_count_entry.setText(str(config['scan_count']))

            # Set to holding registers by default
            self.set_register_type('holding')

            # Store tag mappings for display
            # Create a lookup dict: (address, bit) -> tag_name
            self.tag_mappings = {}
            for tag in config.get('tags', []):
                key = (tag['address'], tag.get('bit'))
                self.tag_mappings[key] = tag['tag_name']

            # Update tags imported flag
            if self.tag_mappings:
                self.tags_imported = True

            # Create custom dialog with auto-expand checkbox
            dialog = QDialog(self)
            dialog.setWindowTitle("Import Successful")
            dialog.setMinimumWidth(500)

            layout = QVBoxLayout()

            # Summary text
            summary = f"""Successfully imported KEPServerEX configuration:

Connection:
  IP Address: {config['ip']}
  Port: {config['port']}
  Unit ID: {config['unit_id']}

Registers:
  Total unique registers: {config['register_count']}
  Register range: {config['min_address']} to {config['max_address']}
  Scan count: {config['scan_count']}

Tags:
  Total tags imported: {config.get('tag_count', 0)}

The connection settings have been auto-populated.
Click 'Read Registers' to start scanning."""

            label = QLabel(summary)
            layout.addWidget(label)

            # Auto-expand checkbox
            auto_expand_check = QCheckBox("Automatically expand bit rows when scanning")
            auto_expand_check.setChecked(self.auto_expand_bits)  # Use current preference
            layout.addWidget(auto_expand_check)

            # OK button
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
            button_box.accepted.connect(dialog.accept)
            layout.addWidget(button_box)

            dialog.setLayout(layout)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Save the auto-expand preference
                self.auto_expand_bits = auto_expand_check.isChecked()

            self.signals.status.emit("KEPServerEX configuration imported successfully")

        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import KEPServerEX file:\n{str(e)}")
            self.signals.status.emit("Failed to import configuration")


def main():
    app = QApplication(sys.argv)
    window = ModbusScannerGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
