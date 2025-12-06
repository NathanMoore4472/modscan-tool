#!/usr/bin/env python3
"""
Modbus TCP Test Server
Simulates a Modbus device with test data matching the LVSG-E0-01-D1.opf configuration
"""

import sys
import os
import signal
import argparse
from pathlib import Path
from pymodbus.server import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext

# PID file location
PID_FILE = Path(os.path.expanduser("~")) / ".modbus_test_server.pid"


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


def write_pid_file():
    """Write current process PID to file"""
    try:
        PID_FILE.write_text(str(os.getpid()))
    except Exception as e:
        print(f"Warning: Could not write PID file: {e}")


def remove_pid_file():
    """Remove PID file"""
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception as e:
        print(f"Warning: Could not remove PID file: {e}")


def stop_server():
    """Stop running Modbus test server"""
    if not PID_FILE.exists():
        print("No running server found (PID file does not exist)")
        return False

    try:
        # Read PID from file
        pid = int(PID_FILE.read_text().strip())

        # Check if process is running
        try:
            os.kill(pid, 0)  # Signal 0 just checks if process exists
        except OSError:
            print(f"Server with PID {pid} is not running")
            remove_pid_file()
            return False

        # Kill the process
        print(f"Stopping Modbus test server (PID: {pid})...")
        os.kill(pid, signal.SIGTERM)

        # Wait a bit and check if it stopped
        import time
        time.sleep(0.5)

        try:
            os.kill(pid, 0)
            # Still running, force kill
            print("Server did not stop gracefully, forcing...")
            os.kill(pid, signal.SIGKILL)
        except OSError:
            # Process is gone
            pass

        remove_pid_file()
        print("✓ Server stopped successfully")
        return True

    except Exception as e:
        print(f"Error stopping server: {e}")
        remove_pid_file()
        return False


def run_server(host='0.0.0.0', port=5020):
    """Run the Modbus TCP server"""

    # Check if server is already running
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            try:
                os.kill(pid, 0)
                print(f"Error: Server is already running with PID {pid}")
                print(f"Stop it first with: python3 modbus_test_server.py --stop")
                sys.exit(1)
            except OSError:
                # PID file exists but process is dead, clean it up
                remove_pid_file()
        except:
            remove_pid_file()

    # Write PID file
    write_pid_file()

    print("=" * 60)
    print("Modbus TCP Test Server")
    print("=" * 60)
    print(f"\nServer Configuration:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Unit ID: 1")
    print(f"  PID: {os.getpid()}")
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
    print("To stop the server:")
    print("  python3 modbus_test_server.py --stop")
    print("  or press Ctrl+C")
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
        remove_pid_file()
    except Exception as e:
        print(f"\nError starting server: {e}")
        print("\nNote: If port is in use, try a different port:")
        print("  python3 modbus_test_server.py --port 5021")
        remove_pid_file()
        sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Modbus TCP Test Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Start server on default port:
    python3 modbus_test_server.py

  Start server on specific port:
    python3 modbus_test_server.py --port 5021

  Stop running server:
    python3 modbus_test_server.py --stop
        """
    )

    parser.add_argument(
        '--port', '-p',
        type=int,
        default=5020,
        help='Port to listen on (default: 5020)'
    )

    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )

    parser.add_argument(
        '--stop',
        action='store_true',
        help='Stop running Modbus test server'
    )

    # For backwards compatibility, also accept port as positional argument
    parser.add_argument(
        'legacy_port',
        nargs='?',
        type=int,
        help=argparse.SUPPRESS  # Hidden from help
    )

    args = parser.parse_args()

    # Handle --stop command
    if args.stop:
        sys.exit(0 if stop_server() else 1)

    # Use legacy port if provided (backwards compatibility)
    port = args.legacy_port if args.legacy_port else args.port

    # Note: Port 502 requires root/admin privileges
    if port == 502:
        print("WARNING: Port 502 requires root/administrator privileges")
        print("Consider using port 5020 instead (no special privileges needed)")
        print()

    run_server(host=args.host, port=port)


if __name__ == "__main__":
    main()
