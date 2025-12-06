"""
Test Modbus server for integration testing
"""
import threading
import time
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSequentialDataBlock


class TestModbusServer:
    """Test Modbus TCP server for integration testing"""

    def __init__(self, host="127.0.0.1", port=5502):
        self.host = host
        self.port = port
        self.server_thread = None
        self.running = False

    def start(self):
        """Start the test server in a background thread"""
        if self.running:
            return

        # Create data blocks for each Modbus function
        store = ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [0] * 100),  # Discrete Inputs
            co=ModbusSequentialDataBlock(0, [0] * 100),  # Coils
            hr=ModbusSequentialDataBlock(0, [0] * 100),  # Holding Registers
            ir=ModbusSequentialDataBlock(0, [0] * 100),  # Input Registers
        )
        context = ModbusServerContext(slaves=store, single=True)

        # Start server in background thread
        self.server_thread = threading.Thread(
            target=lambda: StartTcpServer(
                context=context,
                address=(self.host, self.port),
            ),
            daemon=True,
        )
        self.server_thread.start()
        self.running = True

        # Give server time to start
        time.sleep(0.5)

    def stop(self):
        """Stop the test server"""
        self.running = False
        # Server will stop when thread is terminated


# Pytest fixture
import pytest

@pytest.fixture(scope="session")
def modbus_test_server():
    """Fixture providing a test Modbus server"""
    server = TestModbusServer()
    server.start()
    yield server
    server.stop()
