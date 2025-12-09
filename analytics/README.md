## Analytics / Telemetry System

Privacy-respecting analytics for tracking app usage, versions, and OS distribution.

### Features

- ✓ **Anonymous tracking** - Random UUID, no personal info
- ✓ **User opt-out** - Easy to disable in settings
- ✓ **Non-blocking** - Runs in background, doesn't slow down app
- ✓ **Backend agnostic** - Easy to switch between Supabase and custom endpoint

### Data Collected

- Anonymous user ID (UUID)
- App version
- Operating system and version
- Python version
- Install date (first launch)
- Launch count
- Timestamp

**NOT collected:**
- No IP addresses
- No usernames
- No email addresses
- No file paths
- No Modbus data or PLC information

### Setup Instructions

#### Option 1: Supabase (Current)

1. Create a Supabase account at https://supabase.com
2. Create a new project
3. Run this SQL in the SQL Editor:

```sql
-- Get the SQL from SupabaseBackend.get_table_schema()
-- Or run in Python:
from analytics.backends import SupabaseBackend
print(SupabaseBackend.get_table_schema())
```

4. Get your credentials:
   - Go to Settings > API
   - Copy Project URL and anon/public key

5. Update `analytics_config.py`:
```python
SUPABASE_URL = 'https://xxxxx.supabase.co'
SUPABASE_KEY = 'your-anon-key-here'
```

#### Option 2: Custom HTTP Endpoint (Future)

1. Create a Flask or FastAPI endpoint:

```python
# Get example code:
from analytics.backends import HTTPBackend
print(HTTPBackend.get_flask_example())
# or
print(HTTPBackend.get_fastapi_example())
```

2. Deploy your endpoint (Railway, Render, AWS, etc.)

3. Update `analytics_config.py`:
```python
BACKEND_TYPE = 'http'
HTTP_ENDPOINT_URL = 'https://your-server.com/api/telemetry'
HTTP_API_KEY = 'optional-api-key'
```

### Usage

The telemetry system is automatically initialized when the app starts and sends data on each launch (if enabled).

**User Control:**
- Users can disable telemetry in: Help → Preferences → Privacy
- Setting is persistent across app launches

### Querying Data

#### Supabase Queries

```sql
-- Total unique users
SELECT COUNT(DISTINCT user_id) FROM telemetry;

-- Active users (launched in last 30 days)
SELECT COUNT(DISTINCT user_id) FROM telemetry
WHERE timestamp > NOW() - INTERVAL '30 days';

-- Version distribution
SELECT app_version, COUNT(DISTINCT user_id) as users
FROM telemetry
GROUP BY app_version
ORDER BY users DESC;

-- OS distribution
SELECT os, os_release, COUNT(DISTINCT user_id) as users
FROM telemetry
GROUP BY os, os_release
ORDER BY users DESC;

-- Daily active users
SELECT DATE(timestamp) as date, COUNT(DISTINCT user_id) as users
FROM telemetry
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

### Privacy

This implementation follows privacy best practices:
- Fully anonymous (UUID only)
- User can opt-out anytime
- No tracking of user behavior or data
- Only basic usage statistics
- Transparent about what's collected
