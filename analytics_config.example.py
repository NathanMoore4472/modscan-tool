"""
Analytics Configuration Example

Copy this file to 'analytics_config.py' and fill in your credentials.
"""

# Backend selection: 'supabase' or 'http'
BACKEND_TYPE = 'supabase'

# Supabase configuration
SUPABASE_URL = 'https://xxxxx.supabase.co'
SUPABASE_KEY = 'your-anon-key-here'

# HTTP endpoint configuration (for custom server)
HTTP_ENDPOINT_URL = 'https://your-server.com/api/telemetry'
HTTP_API_KEY = 'your-api-key-here'

# Telemetry settings
TELEMETRY_ENABLED_BY_DEFAULT = True
TELEMETRY_DEBUG = False
