"""
Integration tests for telemetry system

Tests the analytics backend connection and data sending.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def is_telemetry_configured():
    """
    Check if telemetry backend is configured with credentials

    Returns:
        bool: True if credentials are configured, False if not

    Raises:
        ImportError: If analytics_config.py is missing (should fail the test)
    """
    import analytics_config as config

    backend_type = getattr(config, 'BACKEND_TYPE', None)

    if backend_type == 'supabase':
        url = getattr(config, 'SUPABASE_URL', None)
        key = getattr(config, 'SUPABASE_KEY', None)
        # Check if credentials are actually set (not None or empty)
        return bool(url and key and url != 'None' and key != 'None')
    elif backend_type == 'http':
        endpoint = getattr(config, 'HTTP_ENDPOINT_URL', None)
        return bool(endpoint and endpoint != 'None')

    return False


# Skip all tests in this module if credentials are not configured
# Note: If analytics_config.py is missing entirely, ImportError will fail the tests (not skip)
pytestmark = pytest.mark.skipif(
    not is_telemetry_configured(),
    reason="Telemetry credentials not configured (SUPABASE_URL/KEY or HTTP_ENDPOINT_URL not set)"
)


class TestTelemetryIntegration:
    """Integration tests for telemetry system"""

    def test_backend_configured(self):
        """Test that backend is properly configured"""
        from analytics.telemetry import get_backend

        backend = get_backend()
        assert backend is not None, "Backend should be configured"
        assert backend.is_configured(), "Backend should report as configured"

    def test_supabase_connection(self):
        """
        Test connection to Supabase backend

        Note: This test sends one record with real OS/version data per test run.
        Data is sent to 'telemetry_test' table (separate from production 'telemetry' table).
        """
        import analytics_config as config
        from analytics.backends.supabase import SupabaseBackend
        import platform
        from datetime import datetime

        # Get actual app version
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from launcher import VERSION
            app_version = f"test-{VERSION}"
        except ImportError:
            app_version = "test-unknown"

        # Only run if Supabase is configured
        if config.BACKEND_TYPE != 'supabase':
            pytest.skip("Supabase backend not selected")

        # Use separate table for test data
        backend = SupabaseBackend(config.SUPABASE_URL, config.SUPABASE_KEY, table_name="telemetry_test")

        # Verify backend is configured
        assert backend.is_configured(), "Supabase backend should be configured"

        # Test data with REAL OS/version info (one record per test run)
        test_data = {
            "user_id": "00000000-0000-0000-0000-000000000000",  # Test UUID for filtering
            "app_version": app_version,  # e.g., "test-1.4.1"
            "os": platform.system(),  # Real OS: Darwin, Linux, Windows
            "os_version": platform.version(),  # Real OS version
            "os_release": platform.release(),  # Real OS release
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "install_date": datetime.now().isoformat(),
            "launch_count": 1,
            "timestamp": datetime.now().isoformat()
        }

        # Try to send test data
        result = backend.send(test_data)

        # Should succeed (or at least not crash)
        assert isinstance(result, bool), "Backend should return boolean result"

        # If it fails, print useful debug info
        if not result:
            pytest.fail(
                f"Failed to send telemetry to Supabase. "
                f"Check that:\n"
                f"1. SUPABASE_URL is correct\n"
                f"2. SUPABASE_KEY is valid\n"
                f"3. Table 'telemetry' exists in database\n"
                f"4. RLS policies allow anonymous inserts"
            )

    def test_http_connection(self):
        """Test connection to HTTP backend"""
        import analytics_config as config
        from analytics.backends.http import HTTPBackend

        # Only run if HTTP is configured
        if config.BACKEND_TYPE != 'http':
            pytest.skip("HTTP backend not selected")

        backend = HTTPBackend(config.HTTP_ENDPOINT_URL, config.HTTP_API_KEY)

        # Verify backend is configured
        assert backend.is_configured(), "HTTP backend should be configured"

        # Test data to send
        test_data = {
            "user_id": "00000000-0000-0000-0000-000000000000",  # Test UUID
            "app_version": "test-1.0.0",
            "os": "test-os",
            "os_version": "test-version",
            "os_release": "test-release",
            "python_version": "3.9.0",
            "install_date": "2024-01-01T00:00:00",
            "launch_count": 1,
            "timestamp": "2024-01-01T00:00:00"
        }

        # Try to send test data
        result = backend.send(test_data)

        # Should succeed (or at least not crash)
        assert isinstance(result, bool), "Backend should return boolean result"

        # If it fails, print useful debug info
        if not result:
            pytest.fail(
                f"Failed to send telemetry to HTTP endpoint. "
                f"Check that:\n"
                f"1. HTTP_ENDPOINT_URL is correct and accessible\n"
                f"2. HTTP_API_KEY is valid (if required)\n"
                f"3. Endpoint accepts POST requests with JSON data"
            )

    def test_telemetry_client_send(self):
        """Test full telemetry client send flow without actually sending data"""
        from PyQt6.QtCore import QSettings
        from analytics.telemetry import TelemetryClient, get_backend

        # Create temporary settings
        settings = QSettings("ModScanTool-Test", "TelemetryTest")
        settings.clear()  # Clean slate

        # Initialize telemetry client
        backend = get_backend()
        client = TelemetryClient("test-1.0.0", settings, backend)

        # Verify client initialized properly
        assert client.telemetry_enabled is not None
        assert client.user_id is not None
        assert client.backend is not None

        # Verify data collection works (without sending)
        data = client._collect_data()
        assert data["user_id"] == client.user_id
        assert data["app_version"] == "test-1.0.0"
        assert "os" in data
        assert "timestamp" in data

        # Clean up
        settings.clear()
