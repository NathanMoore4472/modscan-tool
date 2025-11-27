# Modbus TCP Scanner Tool

A cross-platform GUI tool for scanning and discovering Modbus TCP devices on your network.

## Features

- Scan single IP addresses or entire network ranges
- Configurable port, timeout, and Unit ID ranges
- Optional register reading to verify device responsiveness
- Real-time scan progress and results
- Export results to text file
- Multi-threaded scanning for better performance
- Clean, intuitive GUI built with tkinter

## Requirements

- Python 3.7 or higher
- pymodbus library

## Installation

1. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Option 1: Using the run script (macOS/Linux)
```bash
./run.sh
```

### Option 2: Manual run
```bash
source venv/bin/activate  # Activate virtual environment
python modscan_tool.py
```

2. Configure scan settings:
   - **IP Address/Range**: Enter a single IP (e.g., `192.168.1.10`) or CIDR notation (e.g., `192.168.1.0/24`)
   - **Port**: Modbus TCP port (default: 502)
   - **Timeout**: Connection timeout in seconds (default: 2)
   - **Unit ID Range**: Range of Modbus Unit IDs to scan (default: 1-10)
   - **Read Registers**: Check to attempt reading holding registers 0-10

3. Click "Start Scan" to begin scanning

4. View results in the results panel:
   - Green text indicates found devices
   - Register values are displayed if read successfully

5. Export results to a timestamped text file using "Export Results" button

## Examples

### Scan a single device
- IP: `192.168.1.100`
- Port: `502`
- Unit ID: `1` to `1`

### Scan a subnet
- IP: `192.168.1.0/24`
- Port: `502`
- Unit ID: `1` to `247`

### Quick scan with shorter timeout
- IP: `10.0.0.0/24`
- Port: `502`
- Timeout: `1`
- Unit ID: `1` to `10`

## Platform Compatibility

This tool uses tkinter for the GUI, which is included with Python on most platforms:
- macOS: Works natively
- Windows: Works natively
- Linux: May require `python3-tk` package installation

## Security Note

This tool is intended for authorized network scanning only. Ensure you have permission to scan the target network before use.

## License

MIT License
