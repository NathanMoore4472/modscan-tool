"""
Supabase Backend Adapter

Sends telemetry data to Supabase (PostgreSQL) database.
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


class SupabaseBackend:
    """Supabase backend for telemetry data"""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """
        Initialize Supabase backend

        Args:
            url: Supabase project URL (e.g., https://xxxxx.supabase.co)
            key: Supabase anon/public key
        """
        self.url = url
        self.key = key
        self.table_name = "telemetry"  # Table name in Supabase

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
        if not self.is_configured():
            print("Supabase backend not configured (URL or key missing)")
            return False

        try:
            # Supabase REST API endpoint
            endpoint = f"{self.url}/rest/v1/{self.table_name}"

            # Prepare request
            headers = {
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",  # Don't return inserted data
            }

            # Convert data to JSON
            payload = json.dumps(data).encode('utf-8')

            # Create request
            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers=headers,
                method='POST'
            )

            # Send request
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status in [200, 201]:
                    return True
                else:
                    print(f"Supabase error: HTTP {response.status}")
                    return False

        except urllib.error.HTTPError as e:
            print(f"Supabase HTTP error: {e.code} - {e.reason}")
            return False
        except urllib.error.URLError as e:
            print(f"Supabase connection error: {e.reason}")
            return False
        except Exception as e:
            print(f"Supabase unexpected error: {e}")
            return False

    @staticmethod
    def get_table_schema() -> str:
        """
        Get SQL schema for creating the telemetry table in Supabase

        Returns:
            SQL CREATE TABLE statement
        """
        return """
-- Create telemetry table in Supabase
CREATE TABLE telemetry (
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
CREATE INDEX idx_telemetry_user_id ON telemetry(user_id);

-- Create index on app_version for version tracking
CREATE INDEX idx_telemetry_app_version ON telemetry(app_version);

-- Create index on timestamp for time-based queries
CREATE INDEX idx_telemetry_timestamp ON telemetry(timestamp);

-- Enable Row Level Security (RLS)
ALTER TABLE telemetry ENABLE ROW LEVEL SECURITY;

-- Create policy to allow anonymous inserts (for telemetry)
CREATE POLICY "Allow anonymous telemetry inserts"
ON telemetry
FOR INSERT
TO anon
WITH CHECK (true);

-- Create policy to allow authenticated reads (for analytics dashboard)
CREATE POLICY "Allow authenticated reads"
ON telemetry
FOR SELECT
TO authenticated
USING (true);
        """
