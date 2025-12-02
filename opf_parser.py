#!/usr/bin/env python3
"""
KEPServerEX .opf File Parser
Extracts device connection info and register mappings from KEPServerEX project files
"""

import re
import struct


class OPFParser:
    """Parser for KEPServerEX .opf binary files"""

    def __init__(self, file_path):
        self.file_path = file_path
        self.data = None
        self.strings = []

    def load(self):
        """Load the .opf file into memory"""
        with open(self.file_path, 'rb') as f:
            self.data = f.read()

    def extract_strings(self, min_length=4):
        """Extract printable ASCII strings from binary data"""
        if not self.data:
            self.load()

        # Pattern to find printable ASCII strings
        pattern = b'[\x20-\x7E]{' + str(min_length).encode() + b',}'
        self.strings = [s.decode('ascii') for s in re.findall(pattern, self.data)]
        return self.strings

    def find_ip_addresses(self):
        """Find IP addresses in the file"""
        if not self.strings:
            self.extract_strings()

        ip_pattern = r'<(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})>'
        ips = []

        for s in self.strings:
            matches = re.findall(ip_pattern, s)
            for match in matches:
                # Validate IP
                parts = match.split('.')
                if all(0 <= int(p) <= 255 for p in parts):
                    ips.append(match)

        return ips

    def find_unit_ids(self):
        """Find unit IDs associated with IP addresses"""
        if not self.strings:
            self.extract_strings()

        # Pattern: <IP>.unitID
        pattern = r'<\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}>\.(\d+)'
        unit_ids = []

        for s in self.strings:
            matches = re.findall(pattern, s)
            unit_ids.extend([int(m) for m in matches])

        return unit_ids

    def find_register_addresses(self):
        """Find Modbus register addresses (format: 40001, 40001.0, etc.)"""
        if not self.strings:
            self.extract_strings()

        register_pattern = r'4(\d{4})(?:\.(\d+))?'
        registers = []

        for s in self.strings:
            matches = re.findall(register_pattern, s)
            for match in matches:
                reg_num = int(match[0])
                bit_num = int(match[1]) if match[1] else None

                # Store register info
                reg_info = {
                    'address': reg_num,  # 0-based internal address
                    'display_address': reg_num,  # 1-based display address
                    'bit': bit_num,
                    'type': 'holding'  # 40001-49999 are holding registers
                }
                registers.append(reg_info)

        return registers

    def find_tag_mappings(self):
        """Find tag names with their associated register addresses and bit positions"""
        if not self.strings:
            self.extract_strings()

        tag_mappings = []
        register_pattern = r'^4(\d{4})(?:\.(\d+))?$'
        skip_patterns = [
            r'^Rack \d+ - Slot \d+ - \d+$',  # Skip description-like strings
            r'^\*\.txt$',  # Skip file patterns
            r'^V\d+\.\d+',  # Skip version strings
        ]

        # Look for pattern: TagName, Description, RegisterAddress
        i = 0
        while i < len(self.strings):
            s = self.strings[i]

            # Skip strings that match skip patterns
            if any(re.match(pattern, s) for pattern in skip_patterns):
                i += 1
                continue

            # Check if this string looks like a tag name (contains letters, numbers, spaces, hyphens, underscores)
            if len(s) > 3 and re.match(r'^[\d_\-a-zA-Z][\w\s\-]*$', s):
                # Look ahead for register address within next 3 strings
                for j in range(1, min(4, len(self.strings) - i)):
                    next_str = self.strings[i + j]
                    match = re.match(register_pattern, next_str)

                    if match:
                        reg_num = int(match.group(1))
                        bit_num = int(match.group(2)) if match.group(2) else None

                        # Get description if available (usually between tag name and address)
                        description = None
                        if j == 2 and i + 1 < len(self.strings):
                            desc_candidate = self.strings[i + 1]
                            if not re.match(register_pattern, desc_candidate):
                                description = desc_candidate

                        tag_mappings.append({
                            'tag_name': s,
                            'description': description,
                            'address': reg_num,
                            'bit': bit_num,
                            'type': 'holding'
                        })
                        break

            i += 1

        return tag_mappings

    def parse(self):
        """Parse the .opf file and extract all relevant information"""
        self.extract_strings()

        ips = self.find_ip_addresses()
        unit_ids = self.find_unit_ids()
        registers = self.find_register_addresses()
        tag_mappings = self.find_tag_mappings()

        # Get unique register addresses (ignore bit positions for now)
        unique_regs = {}
        for reg in registers:
            addr = reg['address']
            if addr not in unique_regs:
                unique_regs[addr] = reg

        # Sort by address
        sorted_regs = sorted(unique_regs.values(), key=lambda x: x['address'])

        # Calculate register range
        if sorted_regs:
            min_addr = sorted_regs[0]['address']
            max_addr = sorted_regs[-1]['address']
            count = max_addr - min_addr + 1
        else:
            min_addr = 0
            max_addr = 0
            count = 0

        result = {
            'ip_addresses': ips,
            'unit_ids': unit_ids,
            'ip': ips[0] if ips else None,
            'unit_id': unit_ids[0] if unit_ids else 1,
            'port': 502,  # Default Modbus TCP port
            'registers': sorted_regs,
            'register_count': len(sorted_regs),
            'min_address': min_addr,
            'max_address': max_addr,
            'scan_count': count,
            'tags': tag_mappings,
            'tag_count': len(tag_mappings),
            'strings': self.strings[:50]  # First 50 strings for debugging
        }

        return result


def parse_opf_file(file_path):
    """Convenience function to parse an .opf file"""
    parser = OPFParser(file_path)
    return parser.parse()


if __name__ == "__main__":
    # Test with the sample file
    import sys

    if len(sys.argv) > 1:
        opf_file = sys.argv[1]
    else:
        opf_file = "LVSG-E0-01-D1.opf"

    print(f"Parsing {opf_file}...")
    result = parse_opf_file(opf_file)

    print("\n=== Connection Info ===")
    print(f"IP Address: {result['ip']}")
    print(f"Port: {result['port']}")
    print(f"Unit ID: {result['unit_id']}")

    print("\n=== Register Info ===")
    print(f"Total unique registers: {result['register_count']}")
    print(f"Register range: {result['min_address']} to {result['max_address']}")
    print(f"Scan count: {result['scan_count']}")

    print("\n=== Tag Mappings ===")
    print(f"Total tags: {result['tag_count']}")
    print("\nFirst 10 tags:")
    for tag in result['tags'][:10]:
        bit_str = f".{tag['bit']}" if tag['bit'] is not None else ""
        print(f"  [{tag['address']}{bit_str}] {tag['tag_name']}")
        if tag['description']:
            print(f"      Description: {tag['description']}")

    print("\n=== Sample Strings ===")
    for s in result['strings'][:20]:
        print(f"  {s}")
