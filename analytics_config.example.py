"""
Analytics Configuration Template

Copy this file to analytics_config.py and update with your actual configuration.
NOTE: analytics_config.py is gitignored to keep credentials private.
"""

# ============================================================================
# BACKEND SELECTION
# ============================================================================
# Choose which backend to use: 'postgres', 'supabase', or 'http'
BACKEND_TYPE = "postgres"  # Change to 'supabase' or 'http' for other backends

# ============================================================================
# POSTGRESQL CONFIGURATION (PostgREST)
# ============================================================================
# Configure your PostgreSQL database with PostgREST API
# Run setup_postgres.sql against your database first

POSTGRES_URL = "http://api.modscan-tool.mooresedge.co.uk"

# ============================================================================
# SUPABASE CONFIGURATION (Legacy)
# ============================================================================
# Kept for backwards compatibility - not used if BACKEND_TYPE = "postgres"

SUPABASE_URL = None  # e.g., 'https://xxxxx.supabase.co'
SUPABASE_KEY = None  # Your Supabase anon/public key

# ============================================================================
# HTTP ENDPOINT CONFIGURATION (for future Flask/FastAPI server)
# ============================================================================
HTTP_ENDPOINT_URL = None  # e.g., 'https://your-server.com/api/telemetry'
HTTP_API_KEY = None  # Optional API key for authentication

# ============================================================================
# TELEMETRY SETTINGS
# ============================================================================
# Enable telemetry by default (users can still opt-out in settings)
TELEMETRY_ENABLED_BY_DEFAULT = True

# Print telemetry events to console for debugging
TELEMETRY_DEBUG = False

# Developer user IDs - automatically enable debug features for these users
DEVELOPER_USER_IDS = [
    # Add UUIDs here to enable debug mode for specific users
    # e.g., "ac745f73-b603-423c-b2ab-4943aa997a17",
]
