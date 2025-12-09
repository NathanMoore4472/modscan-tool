"""
Telemetry Client

Collects and reports anonymous usage data for analytics.
Privacy-first approach: no personal info, anonymous UUID, opt-out available.
"""

import sys
import platform
import uuid
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class TelemetryClient:
    """Privacy-respecting telemetry client for app analytics"""

    def __init__(self, app_version: str, settings, backend=None):
        """
        Initialize telemetry client

        Args:
            app_version: Current app version
            settings: QSettings object for storing preferences
            backend: Analytics backend adapter (SupabaseBackend, HTTPBackend, etc.)
        """
        self.app_version = app_version
        self.settings = settings
        self.backend = backend

        # Load or generate anonymous user ID
        self.user_id = self._get_or_create_user_id()

        # Load preferences
        self.telemetry_enabled = settings.value("telemetry_enabled", True, type=bool)

        # Track install date and launch count
        self._update_usage_stats()

    def _get_or_create_user_id(self) -> str:
        """Get existing anonymous user ID or create a new one"""
        user_id = self.settings.value("telemetry_user_id", None)
        if not user_id:
            user_id = str(uuid.uuid4())
            self.settings.setValue("telemetry_user_id", user_id)
        return user_id

    def _update_usage_stats(self):
        """Update install date and launch count"""
        # Install date (first launch)
        if not self.settings.value("telemetry_install_date"):
            self.settings.setValue("telemetry_install_date", datetime.now().isoformat())

        # Launch count
        launch_count = self.settings.value("telemetry_launch_count", 0, type=int)
        self.settings.setValue("telemetry_launch_count", launch_count + 1)

    def _collect_data(self) -> Dict[str, Any]:
        """Collect telemetry data to send"""
        install_date = self.settings.value("telemetry_install_date")
        launch_count = self.settings.value("telemetry_launch_count", 0, type=int)

        return {
            "user_id": self.user_id,
            "app_version": self.app_version,
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "install_date": install_date,
            "launch_count": launch_count,
            "timestamp": datetime.now().isoformat(),
        }

    def send_telemetry(self, background=True):
        """
        Send telemetry data to backend

        Args:
            background: If True, send in background thread (non-blocking)
        """
        # Check if telemetry is enabled
        if not self.telemetry_enabled:
            print("Telemetry disabled by user")
            return

        # Check if backend is configured
        if not self.backend:
            print("Telemetry backend not configured")
            return

        # Collect data
        data = self._collect_data()

        # Send in background or blocking
        if background:
            thread = threading.Thread(target=self._send_data, args=(data,), daemon=True)
            thread.start()
        else:
            self._send_data(data)

    def _send_data(self, data: Dict[str, Any]):
        """Send data to backend (internal method)"""
        try:
            success = self.backend.send(data)
            if success:
                print(f"Telemetry sent successfully (user: {self.user_id[:8]}...)")
            else:
                print("Telemetry failed to send")
        except Exception as e:
            print(f"Telemetry error: {e}")
            # Silently fail - don't interrupt user experience

    def set_enabled(self, enabled: bool):
        """Enable or disable telemetry"""
        self.telemetry_enabled = enabled
        self.settings.setValue("telemetry_enabled", enabled)
        print(f"Telemetry {'enabled' if enabled else 'disabled'}")

    def get_user_info(self) -> Dict[str, Any]:
        """Get user info for display in settings (for transparency)"""
        return {
            "user_id": self.user_id,
            "install_date": self.settings.value("telemetry_install_date"),
            "launch_count": self.settings.value("telemetry_launch_count", 0, type=int),
            "enabled": self.telemetry_enabled,
        }


def get_backend():
    """
    Load and return configured backend from analytics_config.py

    Returns:
        Backend instance (SupabaseBackend or HTTPBackend) or None if not configured
    """
    try:
        import analytics_config as config
        from .backends.supabase import SupabaseBackend
        from .backends.http import HTTPBackend

        backend_type = getattr(config, 'BACKEND_TYPE', 'supabase')

        if backend_type == 'supabase':
            url = getattr(config, 'SUPABASE_URL', None)
            key = getattr(config, 'SUPABASE_KEY', None)
            return SupabaseBackend(url, key)
        elif backend_type == 'http':
            endpoint = getattr(config, 'HTTP_ENDPOINT_URL', None)
            api_key = getattr(config, 'HTTP_API_KEY', None)
            return HTTPBackend(endpoint, api_key)
        else:
            print(f"Unknown backend type: {backend_type}")
            return None

    except ImportError:
        print("analytics_config.py not found - telemetry disabled")
        return None
    except Exception as e:
        print(f"Error loading telemetry backend: {e}")
        return None
