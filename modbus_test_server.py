#!/usr/bin/env python3
"""
Modbus TCP Test Server
Simulates a Modbus device with test data matching the LVSG-E0-01-D1.opf configuration
"""

import sys
import time
import random
from pymodbus.server import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext


def create_test_data():
    """Create test data for holding registers"""
    # Initialize 100 holding registers with test data
    # Registers 1-6 will have bit patterns matching the .opf tags

    # Register 1 (40001): Various status bits
    # Bits: 0=Open, 1=Closed, 2=Tripped, 3=Connected, 4=Test, 5=Disconnected, etc.
    reg_1 = 0b0000000000001010  # Bits 1 and 3 set (Closed, Connected)

    # Register 2 (40002): More status bits
    reg_2 = 0b0000000000000011  # Bits 0 and 1 set

    # Register 3-6: Some test values
    reg_3 = 12345
    reg_4 = 0xABCD
    reg_5 = 0x1234
    reg_6 = 54321

    # Create data block: [0] is not used, [1] = first register
    registers = [0] + [reg_1, reg_2, reg_3, reg_4, reg_5, reg_6] + [0] * 93

    return registers


def run_server(host='0.0.0.0', port=5020):
    """Run the Modbus TCP server"""

    print("=" * 60)
    print("Modbus TCP Test Server")
    print("=" * 60)
    print(f"\nServer Configuration:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Unit ID: 1")
    print()
    print("Register Configuration:")

    # Create test data
    test_data = create_test_data()

    # Show register values
    print("  Holding Registers:")
    for i in range(1, 7):
        binary = format(test_data[i], '016b')
        print(f"    Register {i} (40001+{i-1}): {test_data[i]:5d} (0x{test_data[i]:04X}) Binary: {binary}")

    # Create datastore with holding registers
    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [0]*100),  # Discrete Inputs
        co=ModbusSequentialDataBlock(0, [0]*100),  # Coils
        hr=ModbusSequentialDataBlock(0, test_data),  # Holding Registers
        ir=ModbusSequentialDataBlock(0, [0]*100)   # Input Registers
    )

    context = ModbusServerContext(slaves=store, single=True)

    # Server identification
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'ModScan Test Server'
    identity.ProductCode = 'MTS'
    identity.VendorUrl = 'https://github.com'
    identity.ProductName = 'Modbus Test Server'
    identity.ModelName = 'Test Device'
    identity.MajorMinorRevision = '1.0.0'

    print("\nServer starting...")
    print(f"\nTo connect with ModScan Tool:")
    print(f"  1. Import the .opf file")
    print(f"  2. Or manually set:")
    print(f"     IP Address: 127.0.0.1 (or {host})")
    print(f"     Port: {port}")
    print(f"     Unit ID: 1")
    print(f"     Start Register: 1")
    print(f"     Register Count: 6")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print()

    try:
        # Start server
        StartTcpServer(
            context=context,
            identity=identity,
            address=(host, port)
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\nError starting server: {e}")
        print("\nNote: If port 502 is in use, try a different port:")
        print("  python3 modbus_test_server.py 5020")


def main():
    """Main entry point"""
    # Default port
    port = 5020

    # Check if port is specified in command line
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}")
            print("Usage: python3 modbus_test_server.py [port]")
            print("Example: python3 modbus_test_server.py 5020")
            sys.exit(1)

    # Note: Port 502 requires root/admin privileges
    if port == 502:
        print("WARNING: Port 502 requires root/administrator privileges")
        print("Consider using port 5020 instead (no special privileges needed)")
        print()

    run_server(host='0.0.0.0', port=port)


if __name__ == "__main__":
    main()
