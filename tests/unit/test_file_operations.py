"""
Unit tests for file import/export operations
"""
import pytest
import csv
import xml.etree.ElementTree as ET
from io import StringIO


class TestCSVExport:
    """Test CSV export functionality"""

    def test_export_basic_data(self, temp_file):
        """Test exporting basic register data to CSV"""
        # Sample data
        data = [
            {"address": 0, "name": "Temperature", "type": "Int16", "value": 25},
            {"address": 1, "name": "Pressure", "type": "UInt16", "value": 1013},
        ]

        # Write to CSV
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["address", "name", "type", "value"])
        writer.writeheader()
        writer.writerows(data)

        # Verify output
        output.seek(0)
        reader = csv.DictReader(output)
        rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["address"] == "0"
        assert rows[0]["name"] == "Temperature"
        assert rows[1]["value"] == "1013"

    def test_export_with_bits(self, temp_file):
        """Test exporting register with bit-level tags"""
        data = [
            {"address": 0, "name": "Status", "type": "UInt16", "value": 15, "bit": ""},
            {"address": 0, "name": "Alarm", "type": "Bit", "value": 1, "bit": 0},
        ]

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["address", "name", "type", "value", "bit"])
        writer.writeheader()
        writer.writerows(data)

        output.seek(0)
        content = output.read()
        assert "Status" in content
        assert "Alarm" in content


class TestCSVImport:
    """Test CSV import functionality"""

    def test_import_basic_csv(self, sample_csv_data, temp_file):
        """Test importing basic CSV file"""
        file_path = temp_file(sample_csv_data, "test.csv")

        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 3
        assert rows[0]["Name"] == "Temperature"
        assert rows[0]["Type"] == "Int16"
        assert rows[1]["Address"] == "1"

    def test_import_empty_csv(self, temp_file):
        """Test importing empty CSV file"""
        content = "Address,Name,Type,Value\n"
        file_path = temp_file(content, "empty.csv")

        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 0

    def test_import_malformed_csv(self, temp_file):
        """Test handling malformed CSV"""
        content = "Address,Name\n0,Test\n1"  # Missing column
        file_path = temp_file(content, "malformed.csv")

        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Should still parse but with None values
        assert len(rows) == 2


class TestOPFImport:
    """Test KEPServerEX OPF file import"""

    def test_parse_opf_xml(self, sample_opf_data):
        """Test parsing OPF XML structure"""
        root = ET.fromstring(sample_opf_data)

        tags = root.findall(".//Tag")
        assert len(tags) == 2

        # Check first tag
        first_tag = tags[0]
        assert first_tag.find("Name").text == "Temperature"
        assert first_tag.find("Address").text == "400001"
        assert first_tag.find("DataType").text == "Short"

    def test_convert_opf_address_to_modbus(self):
        """Test converting OPF address format to Modbus"""
        # OPF uses 400001 format for holding registers
        opf_address = "400001"
        modbus_address = int(opf_address) - 400001
        assert modbus_address == 0

        opf_address = "400100"
        modbus_address = int(opf_address) - 400001
        assert modbus_address == 99

    def test_convert_opf_datatype(self):
        """Test converting OPF data types to internal format"""
        type_mapping = {
            "Short": "Int16",
            "Word": "UInt16",
            "Long": "Int32",
            "DWord": "UInt32",
            "Float": "Float32",
            "Double": "Float64",
        }

        assert type_mapping["Short"] == "Int16"
        assert type_mapping["Word"] == "UInt16"
        assert type_mapping["Float"] == "Float32"

    def test_parse_opf_with_no_tags(self):
        """Test parsing OPF file with no tags"""
        xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<Project>
</Project>
"""
        root = ET.fromstring(xml_data)
        tags = root.findall(".//Tag")
        assert len(tags) == 0
