"""
Integration tests for Modbus communication
Note: These tests require a Modbus server running on localhost:5502
Run modbus_test_server.py manually if you want to execute these tests
"""
import pytest
from pymodbus.client import ModbusTcpClient

# Skip all tests in this module if no server is available
pytestmark = pytest.mark.skip(reason="Requires Modbus test server running on localhost:5502")


@pytest.mark.integration
@pytest.mark.modbus
class TestModbusConnection:
    """Test Modbus TCP connection handling"""

    def test_connect_to_server(self, modbus_test_server):
        """Test connecting to Modbus server"""
        client = ModbusTcpClient("127.0.0.1", port=5502)
        result = client.connect()
        assert result is True
        assert client.is_socket_open() is True
        client.close()

    def test_connect_invalid_host(self):
        """Test connection failure to invalid host"""
        client = ModbusTcpClient("invalid_host", port=5502, timeout=1)
        result = client.connect()
        assert result is False

    def test_connect_invalid_port(self):
        """Test connection failure to invalid port"""
        client = ModbusTcpClient("127.0.0.1", port=9999, timeout=1)
        result = client.connect()
        # May connect but should fail quickly
        client.close()


@pytest.mark.integration
@pytest.mark.modbus
class TestModbusReading:
    """Test reading from Modbus server"""

    def test_read_holding_registers(self, modbus_test_server):
        """Test reading holding registers"""
        client = ModbusTcpClient("127.0.0.1", port=5502)
        client.connect()

        result = client.read_holding_registers(0, 10)
        assert not result.isError()
        assert len(result.registers) == 10

        client.close()

    def test_read_input_registers(self, modbus_test_server):
        """Test reading input registers"""
        client = ModbusTcpClient("127.0.0.1", port=5502)
        client.connect()

        result = client.read_input_registers(0, 10)
        assert not result.isError()
        assert len(result.registers) == 10

        client.close()

    def test_read_coils(self, modbus_test_server):
        """Test reading coils"""
        client = ModbusTcpClient("127.0.0.1", port=5502)
        client.connect()

        result = client.read_coils(0, 10)
        assert not result.isError()
        assert len(result.bits) >= 10

        client.close()

    def test_read_discrete_inputs(self, modbus_test_server):
        """Test reading discrete inputs"""
        client = ModbusTcpClient("127.0.0.1", port=5502)
        client.connect()

        result = client.read_discrete_inputs(0, 10)
        assert not result.isError()
        assert len(result.bits) >= 10

        client.close()

    def test_read_invalid_address(self, modbus_test_server):
        """Test reading from invalid address"""
        client = ModbusTcpClient("127.0.0.1", port=5502)
        client.connect()

        # Try to read beyond valid range
        result = client.read_holding_registers(10000, 10)
        # Should return error or exception
        assert result.isError() or hasattr(result, 'exception_code')

        client.close()


@pytest.mark.integration
@pytest.mark.modbus
class TestModbusWriting:
    """Test writing to Modbus server"""

    def test_write_single_register(self, modbus_test_server):
        """Test writing a single holding register"""
        client = ModbusTcpClient("127.0.0.1", port=5502)
        client.connect()

        # Write value
        write_result = client.write_register(0, 1234)
        assert not write_result.isError()

        # Read back to verify
        read_result = client.read_holding_registers(0, 1)
        assert read_result.registers[0] == 1234

        client.close()

    def test_write_multiple_registers(self, modbus_test_server):
        """Test writing multiple holding registers"""
        client = ModbusTcpClient("127.0.0.1", port=5502)
        client.connect()

        values = [100, 200, 300]
        write_result = client.write_registers(0, values)
        assert not write_result.isError()

        # Read back to verify
        read_result = client.read_holding_registers(0, 3)
        assert read_result.registers == values

        client.close()

    def test_write_single_coil(self, modbus_test_server):
        """Test writing a single coil"""
        client = ModbusTcpClient("127.0.0.1", port=5502)
        client.connect()

        # Write True
        write_result = client.write_coil(0, True)
        assert not write_result.isError()

        # Read back
        read_result = client.read_coils(0, 1)
        assert read_result.bits[0] is True

        client.close()


@pytest.mark.integration
@pytest.mark.modbus
@pytest.mark.slow
class TestModbusBulkOperations:
    """Test bulk Modbus operations"""

    def test_read_large_register_block(self, modbus_test_server):
        """Test reading a large block of registers"""
        client = ModbusTcpClient("127.0.0.1", port=5502)
        client.connect()

        # Read maximum allowed (125 registers)
        result = client.read_holding_registers(0, 100)
        assert not result.isError()
        assert len(result.registers) == 100

        client.close()

    def test_sequential_reads(self, modbus_test_server):
        """Test multiple sequential read operations"""
        client = ModbusTcpClient("127.0.0.1", port=5502)
        client.connect()

        # Perform 10 sequential reads
        for i in range(10):
            result = client.read_holding_registers(i, 1)
            assert not result.isError()

        client.close()
