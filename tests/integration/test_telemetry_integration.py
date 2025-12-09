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
    """Check if telemetry backend is configured with credentials"""
    try:
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
    except ImportError:
        return False


# Skip all tests in this module if telemetry is not configured
pytestmark = pytest.mark.skipif(
    not is_telemetry_configured(),
    reason="Telemetry backend not configured (analytics_config.py missing or credentials not set)"
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
        """Test connection to Supabase backend"""
        import analytics_config as config
        from analytics.backends.supabase import SupabaseBackend

        # Only run if Supabase is configured
        if config.BACKEND_TYPE != 'supabase':
            pytest.skip("Supabase backend not selected")

        backend = SupabaseBackend(config.SUPABASE_URL, config.SUPABASE_KEY)

        # Verify backend is configured
        assert backend.is_configured(), "Supabase backend should be configured"

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
        """Test full telemetry client send flow"""
        from PyQt6.QtCore import QSettings
        from analytics.telemetry import TelemetryClient, get_backend

        # Create temporary settings
        settings = QSettings("ModScanTool-Test", "TelemetryTest")
        settings.clear()  # Clean slate

        # Initialize telemetry client
        backend = get_backend()
        client = TelemetryClient("test-1.0.0", settings, backend)

        # Enable telemetry explicitly for test
        client.telemetry_enabled = True

        # Send telemetry (blocking, not background)
        # This should not raise any exceptions
        try:
            client.send_telemetry(background=False)
        except Exception as e:
            pytest.fail(f"Telemetry send raised exception: {e}")

        # Clean up
        settings.clear()
