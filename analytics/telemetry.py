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
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


def _is_developer_mode() -> bool:
    """Check if debug mode should be enabled (TELEMETRY_DEBUG or developer user_id)"""
    try:
        import analytics_config as config

        # Check if explicitly enabled
        if getattr(config, 'TELEMETRY_DEBUG', False):
            return True

        # Check if user is a developer
        developer_ids = getattr(config, 'DEVELOPER_USER_IDS', [])
        if developer_ids:
            try:
                from PyQt6.QtCore import QSettings
                settings = QSettings("ModScanTool", "ModbusScannerGUI")
                user_id = settings.value("telemetry_user_id", None)
                if user_id and user_id in developer_ids:
                    return True
            except Exception:
                pass

        return False
    except ImportError:
        return False


def _debug_log(message: str):
    """Write debug message to telemetry log file (only if debug mode is enabled)"""
    try:
        if not _is_developer_mode():
            return

        # Write to Desktop for easy access
        log_file = Path.home() / "Desktop" / "modscan_telemetry_debug.log"
        with open(log_file, 'a') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # Silently fail if can't write log


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
        _debug_log(f"TelemetryClient.__init__ called with app_version={app_version}")
        _debug_log(f"Backend type: {type(backend).__name__ if backend else 'None'}")

        self.app_version = app_version
        self.settings = settings
        self.backend = backend

        # Load or generate anonymous user ID
        self.user_id = self._get_or_create_user_id()
        _debug_log(f"User ID: {self.user_id[:8]}...")

        # Load preferences
        self.telemetry_enabled = settings.value("telemetry_enabled", True, type=bool)
        _debug_log(f"Telemetry enabled: {self.telemetry_enabled}")

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

        # Get user-friendly OS information
        os_name = platform.system()
        if os_name == "Darwin":
            # macOS - get user-friendly version
            mac_ver = platform.mac_ver()[0]  # e.g., "15.4"
            os_name = "macOS"
            os_version = mac_ver if mac_ver else platform.release()
            os_release = platform.release()  # Kernel version like "24.4.0"
        else:
            # Windows, Linux, etc.
            os_version = platform.version()
            os_release = platform.release()

        return {
            "user_id": self.user_id,
            "app_version": self.app_version,
            "os": os_name,
            "os_version": os_version,
            "os_release": os_release,
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
        _debug_log(f"send_telemetry called (background={background})")

        # Check if telemetry is enabled
        if not self.telemetry_enabled:
            _debug_log("Telemetry disabled by user")
            print("Telemetry disabled by user")
            return

        # Check if backend is configured
        if not self.backend:
            _debug_log("Telemetry backend not configured")
            print("Telemetry backend not configured")
            return

        # Collect data
        data = self._collect_data()
        _debug_log(f"Collected data: app_version={data.get('app_version')}, os={data.get('os')}")

        # Send in background or blocking
        if background:
            _debug_log("Starting background thread for telemetry send")
            thread = threading.Thread(target=self._send_data, args=(data,), daemon=True)
            thread.start()
        else:
            _debug_log("Sending telemetry in blocking mode")
            self._send_data(data)

    def _send_data(self, data: Dict[str, Any]):
        """Send data to backend (internal method)"""
        _debug_log("_send_data called")
        try:
            _debug_log(f"Calling backend.send() - backend type: {type(self.backend).__name__}")
            success = self.backend.send(data)
            _debug_log(f"backend.send() returned: {success}")
            if success:
                msg = f"Telemetry sent successfully (user: {self.user_id[:8]}...)"
                _debug_log(msg)
                print(msg)
            else:
                msg = "Telemetry failed to send"
                _debug_log(msg)
                print(msg)
        except Exception as e:
            msg = f"Telemetry error: {e}"
            _debug_log(msg)
            print(msg)
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
    _debug_log("get_backend() called")
    try:
        _debug_log("Attempting to import analytics_config")
        import analytics_config as config
        _debug_log(f"analytics_config imported successfully from: {config.__file__}")

        from .backends.supabase import SupabaseBackend
        from .backends.http import HTTPBackend

        backend_type = getattr(config, 'BACKEND_TYPE', 'supabase')
        _debug_log(f"Backend type: {backend_type}")

        if backend_type == 'supabase':
            url = getattr(config, 'SUPABASE_URL', None)
            key = getattr(config, 'SUPABASE_KEY', None)
            _debug_log(f"Supabase URL configured: {bool(url)}, Key configured: {bool(key)}")
            backend = SupabaseBackend(url, key)
            _debug_log(f"SupabaseBackend created, is_configured: {backend.is_configured()}")
            return backend
        elif backend_type == 'http':
            endpoint = getattr(config, 'HTTP_ENDPOINT_URL', None)
            api_key = getattr(config, 'HTTP_API_KEY', None)
            _debug_log(f"HTTP endpoint: {endpoint}")
            return HTTPBackend(endpoint, api_key)
        else:
            msg = f"Unknown backend type: {backend_type}"
            _debug_log(msg)
            print(msg)
            return None

    except ImportError as e:
        msg = f"analytics_config.py not found - telemetry disabled: {e}"
        _debug_log(msg)
        print(msg)
        return None
    except Exception as e:
        msg = f"Error loading telemetry backend: {e}"
        _debug_log(msg)
        print(msg)
        return None
