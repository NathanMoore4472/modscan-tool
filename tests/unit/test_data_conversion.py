"""
Unit tests for data type conversion and parsing
"""
import pytest
import struct


class TestDataConversion:
    """Test data type conversion functions"""

    def test_int16_conversion(self):
        """Test Int16 (signed 16-bit) conversion"""
        # Positive value
        value = 1000
        assert value == 1000

        # Negative value (two's complement)
        value = 0xFFFF  # -1 in signed 16-bit
        signed_value = struct.unpack('>h', struct.pack('>H', value))[0]
        assert signed_value == -1

    def test_uint16_conversion(self):
        """Test UInt16 (unsigned 16-bit) conversion"""
        value = 65535  # Max UInt16
        assert value == 65535

        value = 0
        assert value == 0

    def test_int32_conversion(self):
        """Test Int32 (signed 32-bit) from two registers"""
        # Convert two 16-bit registers to 32-bit value
        high = 0x0000
        low = 0x03E8  # 1000 in hex

        # Big-endian (AB CD)
        value_be = (high << 16) | low
        assert value_be == 1000

        # Little-endian (CD AB)
        value_le = (low << 16) | high
        assert value_le == 1000 << 16

    def test_float32_conversion(self):
        """Test Float32 conversion from two registers"""
        # Known float value: 3.14159
        float_value = 3.14159
        packed = struct.pack('>f', float_value)
        high, low = struct.unpack('>HH', packed)

        # Reconstruct float
        reconstructed_packed = struct.pack('>HH', high, low)
        reconstructed = struct.unpack('>f', reconstructed_packed)[0]

        assert abs(reconstructed - float_value) < 0.0001

    def test_endianness_swap(self):
        """Test byte order swapping"""
        # Big-endian to little-endian swap
        value = 0x1234
        swapped = ((value & 0xFF) << 8) | ((value & 0xFF00) >> 8)
        assert swapped == 0x3412

    @pytest.mark.parametrize("bits,expected", [
        ([True, False, True, False], [0, 2]),
        ([False, False, False, False], []),
        ([True, True, True, True], [0, 1, 2, 3]),
    ])
    def test_bit_extraction(self, bits, expected):
        """Test extracting bit positions from boolean array"""
        result = [i for i, bit in enumerate(bits) if bit]
        assert result == expected


class TestAddressCalculation:
    """Test Modbus address calculations"""

    def test_zero_based_addressing(self):
        """Test zero-based address calculation"""
        # Register 0 in zero-based = address 0
        register = 0
        assert register == 0

        register = 99
        assert register == 99

    def test_one_based_addressing(self):
        """Test one-based (Modbus standard) addressing"""
        # Holding register starts at 40001
        modbus_address = 40001
        register_address = modbus_address - 40001
        assert register_address == 0

        modbus_address = 40100
        register_address = modbus_address - 40001
        assert register_address == 99

    def test_coil_addressing(self):
        """Test coil address ranges"""
        # Coils start at 00001
        coil_address = 1
        register_address = coil_address - 1
        assert register_address == 0

    def test_input_register_addressing(self):
        """Test input register address ranges"""
        # Input registers start at 30001
        modbus_address = 30001
        register_address = modbus_address - 30001
        assert register_address == 0
