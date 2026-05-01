"""
PostgreSQL Backend Adapter (via PostgREST)

Sends telemetry data to PostgreSQL database via PostgREST REST API.
Similar to Supabase backend but uses direct PostgreSQL + PostgREST.
"""

import json
import urllib.request
import urllib.error
import ssl
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# Use certifi for SSL verification in PyInstaller builds
try:
    import certifi

    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

# Cache for user roles (to avoid repeated lookups)
_USER_ROLES_CACHE: Optional[List[str]] = None


def _fetch_user_roles(user_id: str, postgres_url: str) -> List[str]:
    """
    Fetch user roles from PostgreSQL known_users table via PostgREST

    Args:
        user_id: User UUID to look up
        postgres_url: PostgREST base URL (e.g., http://192.168.1.72:3001)

    Returns:
        List of role strings (e.g., ['developer', 'admin', 'debug'])
    """
    global _USER_ROLES_CACHE

    # Return cached roles if available
    if _USER_ROLES_CACHE is not None:
        return _USER_ROLES_CACHE

    try:
        # Call the get_user_roles() function via PostgREST RPC
        endpoint = f"{postgres_url}/rpc/get_user_roles"

        headers = {
            "Content-Type": "application/json",
        }

        payload = json.dumps({"user_uuid": user_id}).encode("utf-8")

        req = urllib.request.Request(
            endpoint, data=payload, headers=headers, method="POST"
        )

        with urllib.request.urlopen(req, timeout=3, context=SSL_CONTEXT) as response:
            if response.status == 200:
                roles = json.loads(response.read().decode("utf-8"))
                # Cache the result
                _USER_ROLES_CACHE = roles if isinstance(roles, list) else []
                return _USER_ROLES_CACHE
            else:
                return []

    except Exception as e:
        # If role lookup fails, just return empty array (user is not known)
        # This is not an error - most users won't be in known_users table
        return []


def _has_role(role: str, postgres_url: str) -> bool:
    """
    Check if current user has a specific role

    Args:
        role: Role name to check (e.g., 'developer', 'admin', 'beta', 'debug')
        postgres_url: PostgREST base URL

    Returns:
        True if user has the role, False otherwise
    """
    try:
        import analytics_config as config
        from PyQt6.QtCore import QSettings

        # Get user UUID from settings
        settings = QSettings("ModScanTool", "ModbusScannerGUI")
        user_id = settings.value("telemetry_user_id", None)

        if not user_id:
            return False

        # Fetch roles and check
        roles = _fetch_user_roles(user_id, postgres_url)
        return role.lower() in [r.lower() for r in roles]

    except Exception:
        return False


def _is_developer_mode(postgres_url: str) -> bool:
    """
    Check if debug mode should be enabled

    Debug mode is enabled if:
    - TELEMETRY_DEBUG setting is True, OR
    - User has 'developer' role, OR
    - User has 'debug' role (for remote debugging)
    """
    try:
        import analytics_config as config

        # Check if explicitly enabled
        if getattr(config, "TELEMETRY_DEBUG", False):
            return True

        # Check if user has 'developer' or 'debug' role
        return _has_role("developer", postgres_url) or _has_role("debug", postgres_url)

    except ImportError:
        return False


def _debug_log(message: str):
    """Write debug message to telemetry log file (only if debug mode is enabled)"""
    try:
        # Can't check debug mode here without postgres_url, so check directly
        import analytics_config as config

        if not getattr(config, "TELEMETRY_DEBUG", False):
            return

        log_file = Path.home() / "Desktop" / "modscan_telemetry_debug.log"
        with open(log_file, "a") as f:
            timestamp = datetime.now().isoformat()
            f.write(f"[{timestamp}] [PostgreSQL] {message}\n")
    except Exception:
        pass


class PostgresBackend:
    """PostgreSQL backend for telemetry data (via PostgREST)"""

    def __init__(self, url: Optional[str] = None, table_name: str = "telemetry"):
        """
        Initialize PostgreSQL backend

        Args:
            url: PostgREST URL (e.g., http://192.168.1.72:3001)
            table_name: Database table name (default: "telemetry", use "telemetry_test" for CI tests)
        """
        self.url = url
        self.table_name = table_name

    def is_configured(self) -> bool:
        """Check if backend is properly configured"""
        return bool(self.url)

    def send(self, data: Dict[str, Any]) -> bool:
        """
        Send telemetry data to PostgreSQL via PostgREST

        Args:
            data: Telemetry data dictionary

        Returns:
            True if successful, False otherwise
        """
        _debug_log("send() called")
        if not self.is_configured():
            msg = "PostgreSQL backend not configured (URL missing)"
            _debug_log(msg)
            print(msg)
            return False

        try:
            # PostgREST REST API endpoint
            endpoint = f"{self.url}/{self.table_name}"
            _debug_log(f"Endpoint: {endpoint}")

            # Prepare request
            headers = {
                "Content-Type": "application/json",
                "Prefer": "return=minimal",  # Don't return inserted data
            }

            # Convert data to JSON
            payload = json.dumps(data).encode("utf-8")
            _debug_log(f"Payload size: {len(payload)} bytes")

            # Create request
            req = urllib.request.Request(
                endpoint, data=payload, headers=headers, method="POST"
            )

            _debug_log("Sending POST request to PostgREST...")
            # Send request with SSL context
            with urllib.request.urlopen(
                req, timeout=5, context=SSL_CONTEXT
            ) as response:
                _debug_log(f"Response status: {response.status}")
                if response.status in [200, 201]:
                    _debug_log("Success!")
                    return True
                else:
                    msg = f"PostgreSQL error: HTTP {response.status}"
                    _debug_log(msg)
                    print(msg)
                    return False

        except urllib.error.HTTPError as e:
            # Read error response body
            try:
                error_body = e.read().decode("utf-8")
                _debug_log(f"HTTP error body: {error_body}")
            except:
                pass
            msg = f"PostgreSQL HTTP error: {e.code} - {e.reason}"
            _debug_log(msg)
            print(msg)
            return False
        except urllib.error.URLError as e:
            msg = f"PostgreSQL connection error: {e.reason}"
            _debug_log(msg)
            print(msg)
            return False
        except Exception as e:
            msg = f"PostgreSQL unexpected error: {e}"
            _debug_log(msg)
            print(msg)
            return False

    @staticmethod
    def get_setup_instructions() -> str:
        """
        Get setup instructions for PostgreSQL RLS configuration

        Returns:
            Setup instructions and SQL script reference
        """
        return """
PostgreSQL RLS Setup Required:

1. Run setup_postgres.sql against your appdb database:
   psql -h 192.168.1.72 -U postgres -d appdb -f setup_postgres.sql

2. This creates:
   - RLS policies on telemetry, telemetry_test tables
   - get_user_roles(user_uuid) RPC function
   - Enables postgREST to safely expose REST API

3. PostgREST Configuration:
   - Ensure postgREST is configured with:
     - db_uri: "postgres://[user]:[pass]@192.168.1.72:5432/appdb"
     - db_anon_role: "anon"
     - Port: 3001

4. Security Model:
   - App (unauthenticated) can INSERT telemetry (anon role)
   - App cannot READ telemetry (RLS denies SELECT)
   - Dashboard/admin uses authenticated role to READ telemetry
        """
