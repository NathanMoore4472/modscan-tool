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
    """Check if telemetry backend is configured"""
    import analytics_config as config

    backend_type = getattr(config, 'BACKEND_TYPE', None)

    if backend_type == 'postgres':
        url = getattr(config, 'POSTGRES_URL', None)
        return bool(url and url != 'None')
    elif backend_type == 'http':
        endpoint = getattr(config, 'HTTP_ENDPOINT_URL', None)
        return bool(endpoint and endpoint != 'None')
    elif backend_type == 'supabase':
        url = getattr(config, 'SUPABASE_URL', None)
        key = getattr(config, 'SUPABASE_KEY', None)
        return bool(url and key and url != 'None' and key != 'None')

    return False


# Skip all tests in this module if backend is not configured
pytestmark = pytest.mark.skipif(
    not is_telemetry_configured(),
    reason="Telemetry backend not configured (POSTGRES_URL or HTTP_ENDPOINT_URL not set)"
)


class TestTelemetryIntegration:
    """Integration tests for telemetry system"""

    def test_backend_configured(self):
        """Test that backend is properly configured"""
        from analytics.telemetry import get_backend

        backend = get_backend()
        assert backend is not None, "Backend should be configured"
        assert backend.is_configured(), "Backend should report as configured"

    def test_postgres_connection(self):
        """
        Test connection to PostgreSQL backend via PostgREST

        Sends one record to 'telemetry_test' table (separate from production).
        """
        import analytics_config as config
        from analytics.backends.postgres import PostgresBackend
        import platform
        from datetime import datetime

        if config.BACKEND_TYPE != 'postgres':
            pytest.skip("PostgreSQL backend not selected")

        try:
            from launcher import VERSION
            app_version = f"test-{VERSION}"
        except ImportError:
            app_version = "test-unknown"

        backend = PostgresBackend(config.POSTGRES_URL, table_name="telemetry_test")

        assert backend.is_configured(), "PostgreSQL backend should be configured"

        test_data = {
            "user_id": "00000000-0000-0000-0000-000000000000",
            "app_version": app_version,
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "install_date": datetime.now().isoformat(),
            "launch_count": 1,
            "timestamp": datetime.now().isoformat()
        }

        result = backend.send(test_data)

        assert isinstance(result, bool), "Backend should return boolean result"

        if not result:
            pytest.fail(
                f"Failed to send telemetry to PostgreSQL. "
                f"Check that:\n"
                f"1. POSTGRES_URL ({config.POSTGRES_URL}) is correct and accessible\n"
                f"2. PostgREST is running and reachable\n"
                f"3. RLS policy allows anon INSERT on telemetry_test table\n"
                f"4. setup_postgres.sql has been run against the database"
            )

    def test_http_connection(self):
        """Test connection to HTTP backend"""
        import analytics_config as config
        from analytics.backends.http import HTTPBackend

        if config.BACKEND_TYPE != 'http':
            pytest.skip("HTTP backend not selected")

        backend = HTTPBackend(config.HTTP_ENDPOINT_URL, config.HTTP_API_KEY)

        assert backend.is_configured(), "HTTP backend should be configured"

        test_data = {
            "user_id": "00000000-0000-0000-0000-000000000000",
            "app_version": "test-1.0.0",
            "os": "test-os",
            "os_version": "test-version",
            "os_release": "test-release",
            "python_version": "3.9.0",
            "install_date": "2024-01-01T00:00:00",
            "launch_count": 1,
            "timestamp": "2024-01-01T00:00:00"
        }

        result = backend.send(test_data)

        assert isinstance(result, bool), "Backend should return boolean result"

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

        settings = QSettings("ModScanTool-Test", "TelemetryTest")
        settings.clear()

        backend = get_backend()
        client = TelemetryClient("test-1.0.0", settings, backend)

        assert client.telemetry_enabled is not None
        assert client.user_id is not None
        assert client.backend is not None

        data = client._collect_data()
        assert data["user_id"] == client.user_id
        assert data["app_version"] == "test-1.0.0"
        assert "os" in data
        assert "timestamp" in data

        settings.clear()
