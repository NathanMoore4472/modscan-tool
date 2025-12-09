"""
Supabase Backend Adapter

Sends telemetry data to Supabase (PostgreSQL) database.
"""

import json
import urllib.request
import urllib.error
import ssl
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Use certifi for SSL verification in PyInstaller builds
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None


def _debug_log(message: str):
    """Write debug message to telemetry log file (only if TELEMETRY_DEBUG is enabled)"""
    try:
        # Only log if debug mode is enabled
        try:
            import analytics_config as config
            if not getattr(config, 'TELEMETRY_DEBUG', False):
                return
        except ImportError:
            return

        log_file = Path.home() / "Desktop" / "modscan_telemetry_debug.log"
        with open(log_file, 'a') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"[{timestamp}] [Supabase] {message}\n")
    except Exception:
        pass


class SupabaseBackend:
    """Supabase backend for telemetry data"""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None, table_name: str = "telemetry"):
        """
        Initialize Supabase backend

        Args:
            url: Supabase project URL (e.g., https://xxxxx.supabase.co)
            key: Supabase anon/public key
            table_name: Database table name (default: "telemetry", use "telemetry_test" for CI tests)
        """
        self.url = url
        self.key = key
        self.table_name = table_name

    def is_configured(self) -> bool:
        """Check if backend is properly configured"""
        return bool(self.url and self.key)

    def send(self, data: Dict[str, Any]) -> bool:
        """
        Send telemetry data to Supabase

        Args:
            data: Telemetry data dictionary

        Returns:
            True if successful, False otherwise
        """
        _debug_log("send() called")
        if not self.is_configured():
            msg = "Supabase backend not configured (URL or key missing)"
            _debug_log(msg)
            print(msg)
            return False

        try:
            # Supabase REST API endpoint
            endpoint = f"{self.url}/rest/v1/{self.table_name}"
            _debug_log(f"Endpoint: {endpoint}")

            # Prepare request
            headers = {
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",  # Don't return inserted data
            }

            # Convert data to JSON
            payload = json.dumps(data).encode('utf-8')
            _debug_log(f"Payload size: {len(payload)} bytes")

            # Create request
            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers=headers,
                method='POST'
            )

            _debug_log("Sending POST request to Supabase...")
            # Send request with SSL context
            with urllib.request.urlopen(req, timeout=5, context=SSL_CONTEXT) as response:
                _debug_log(f"Response status: {response.status}")
                if response.status in [200, 201]:
                    _debug_log("Success!")
                    return True
                else:
                    msg = f"Supabase error: HTTP {response.status}"
                    _debug_log(msg)
                    print(msg)
                    return False

        except urllib.error.HTTPError as e:
            # Read error response body
            try:
                error_body = e.read().decode('utf-8')
                _debug_log(f"HTTP error body: {error_body}")
            except:
                pass
            msg = f"Supabase HTTP error: {e.code} - {e.reason}"
            _debug_log(msg)
            print(msg)
            return False
        except urllib.error.URLError as e:
            msg = f"Supabase connection error: {e.reason}"
            _debug_log(msg)
            print(msg)
            return False
        except Exception as e:
            msg = f"Supabase unexpected error: {e}"
            _debug_log(msg)
            print(msg)
            return False

    @staticmethod
    def get_table_schema(table_name: str = "telemetry") -> str:
        """
        Get SQL schema for creating a telemetry table in Supabase

        Args:
            table_name: Name of the table to create (default: "telemetry")

        Returns:
            SQL CREATE TABLE statement
        """
        return f"""
-- Create {table_name} table in Supabase
CREATE TABLE {table_name} (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    app_version TEXT NOT NULL,
    os TEXT NOT NULL,
    os_version TEXT,
    os_release TEXT,
    python_version TEXT,
    install_date TIMESTAMP,
    launch_count INTEGER,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index on user_id for faster queries
CREATE INDEX idx_{table_name}_user_id ON {table_name}(user_id);

-- Create index on app_version for version tracking
CREATE INDEX idx_{table_name}_app_version ON {table_name}(app_version);

-- Create index on timestamp for time-based queries
CREATE INDEX idx_{table_name}_timestamp ON {table_name}(timestamp);

-- Enable Row Level Security (RLS)
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

-- Create policy to allow anonymous inserts (for telemetry)
CREATE POLICY "Allow anonymous {table_name} inserts"
ON {table_name}
FOR INSERT
TO anon
WITH CHECK (true);

-- Create policy to allow authenticated reads (for analytics dashboard)
CREATE POLICY "Allow authenticated {table_name} reads"
ON {table_name}
FOR SELECT
TO authenticated
USING (true);
        """
