"""
HTTP Backend Adapter

Sends telemetry data to a custom HTTP endpoint (Flask/FastAPI server).
This is a simple alternative to Supabase for self-hosted solutions.
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


class HTTPBackend:
    """HTTP backend for telemetry data (custom Flask/FastAPI endpoint)"""

    def __init__(self, endpoint_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize HTTP backend

        Args:
            endpoint_url: Full URL to telemetry endpoint (e.g., https://your-server.com/api/telemetry)
            api_key: Optional API key for authentication
        """
        self.endpoint_url = endpoint_url
        self.api_key = api_key

    def is_configured(self) -> bool:
        """Check if backend is properly configured"""
        return bool(self.endpoint_url)

    def send(self, data: Dict[str, Any]) -> bool:
        """
        Send telemetry data to HTTP endpoint

        Args:
            data: Telemetry data dictionary

        Returns:
            True if successful, False otherwise
        """
        if not self.is_configured():
            print("HTTP backend not configured (endpoint URL missing)")
            return False

        try:
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "ModScan-Tool-Telemetry/1.0",
            }

            # Add API key if provided
            if self.api_key:
                headers["X-API-Key"] = self.api_key

            # Convert data to JSON
            payload = json.dumps(data).encode('utf-8')

            # Create request
            req = urllib.request.Request(
                self.endpoint_url,
                data=payload,
                headers=headers,
                method='POST'
            )

            # Send request
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status in [200, 201, 202]:
                    return True
                else:
                    print(f"HTTP backend error: HTTP {response.status}")
                    return False

        except urllib.error.HTTPError as e:
            print(f"HTTP backend HTTP error: {e.code} - {e.reason}")
            return False
        except urllib.error.URLError as e:
            print(f"HTTP backend connection error: {e.reason}")
            return False
        except Exception as e:
            print(f"HTTP backend unexpected error: {e}")
            return False

    @staticmethod
    def get_flask_example() -> str:
        """
        Get example Flask endpoint code for receiving telemetry

        Returns:
            Flask example code
        """
        return '''
# Example Flask endpoint for receiving telemetry
from flask import Flask, request, jsonify
from datetime import datetime
import sqlite3  # or your preferred database

app = Flask(__name__)

@app.route('/api/telemetry', methods=['POST'])
def receive_telemetry():
    """Receive and store telemetry data"""
    try:
        data = request.get_json()

        # Optional: Validate API key
        api_key = request.headers.get('X-API-Key')
        if api_key != 'your-secret-key':
            return jsonify({"error": "Unauthorized"}), 401

        # Store in database
        conn = sqlite3.connect('telemetry.db')
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO telemetry (
                user_id, app_version, os, os_version,
                install_date, launch_count, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('user_id'),
            data.get('app_version'),
            data.get('os'),
            data.get('os_version'),
            data.get('install_date'),
            data.get('launch_count'),
            data.get('timestamp')
        ))

        conn.commit()
        conn.close()

        return jsonify({"status": "success"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
        '''

    @staticmethod
    def get_fastapi_example() -> str:
        """
        Get example FastAPI endpoint code for receiving telemetry

        Returns:
            FastAPI example code
        """
        return '''
# Example FastAPI endpoint for receiving telemetry
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import sqlite3  # or your preferred database

app = FastAPI()

class TelemetryData(BaseModel):
    user_id: str
    app_version: str
    os: str
    os_version: Optional[str]
    os_release: Optional[str]
    python_version: Optional[str]
    install_date: Optional[str]
    launch_count: int
    timestamp: str

@app.post("/api/telemetry")
async def receive_telemetry(
    data: TelemetryData,
    x_api_key: Optional[str] = Header(None)
):
    """Receive and store telemetry data"""
    # Optional: Validate API key
    if x_api_key != "your-secret-key":
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Store in database
    conn = sqlite3.connect('telemetry.db')
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO telemetry (
            user_id, app_version, os, os_version,
            install_date, launch_count, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.user_id,
        data.app_version,
        data.os,
        data.os_version,
        data.install_date,
        data.launch_count,
        data.timestamp
    ))

    conn.commit()
    conn.close()

    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
        '''
