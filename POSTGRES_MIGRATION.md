# PostgreSQL/PostgREST Telemetry Migration Guide

This guide walks through migrating from Supabase to your self-hosted PostgreSQL with PostgREST.

## Overview

- **Database**: PostgreSQL at `192.168.1.72` (port 5432), database `appdb`
- **API Layer**: PostgREST running on port 3001
- **Security Model**: Row-level security (RLS) policies with unauthenticated INSERT access, authenticated SELECT access
- **No Configuration Needed**: App is fully distributable - no local config required

## Step 1: Run Database Setup Script

Before deploying, create the RLS policies and RPC function:

```bash
# Connect to your PostgreSQL database and run:
psql -h 192.168.1.72 -U postgres -d appdb -f setup_postgres.sql
```

This creates:
- **RLS policies** on `telemetry`, `telemetry_test` tables
- **`get_user_roles()` RPC function** for role-based debug logging
- **Enables PostgREST REST API** to safely expose the database

### What the SQL Script Does:

1. **Enables Row-Level Security (RLS)** on three tables:
   - `telemetry` (production telemetry data)
   - `telemetry_test` (CI/test data)
   - `known_users` (user roles and metadata)

2. **Creates RLS policies**:
   - **Anonymous users (anon role)**: Can INSERT telemetry, cannot READ
   - **Authenticated users**: Can READ telemetry (for analytics dashboard/admin)
   - **Prevents unauthenticated data access** while allowing distributed app to send data

3. **Creates `get_user_roles()` RPC function**:
   - Allows checking if a user has 'developer' or 'debug' roles
   - Used by the app to enable debug logging features
   - Called via PostgREST: `POST /rest/v1/rpc/get_user_roles`

## Step 2: Verify PostgREST Configuration

Ensure your PostgREST is running and configured correctly:

```bash
# Test PostgREST is accessible
curl http://192.168.1.72:3001/rest/v1/
# Should return PostgREST version info
```

**PostgREST config requirements:**
- `db_uri`: `"postgres://user:password@192.168.1.72:5432/appdb"`
- `db_anon_role`: `"anon"` (for unauthenticated requests)
- `server_port`: `3001`
- Ensure the PostgreSQL user has appropriate grants

## Step 3: Configure the App

The app is already configured for PostgreSQL in `analytics_config.py`:

```python
BACKEND_TYPE = "postgres"
POSTGRES_HOST = "192.168.1.72"
POSTGRES_PORT = 3001
POSTGRES_URL = "http://192.168.1.72:3001"
```

**No local configuration needed** - the app will work out of the box. To customize, copy `analytics_config.example.py` to `analytics_config.py` and modify.

## Step 4: Test the Integration

### Quick Test - Insert a telemetry record:

```bash
curl -X POST http://192.168.1.72:3001/rest/v1/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "00000000-0000-0000-0000-000000000000",
    "app_version": "1.0.0-test",
    "os": "Darwin",
    "os_version": "15.4",
    "python_version": "3.11.0",
    "timestamp": "2024-01-01T12:00:00"
  }'
```

### Run Integration Tests:

```bash
# Run telemetry tests (will use telemetry_test table)
pytest tests/integration/test_telemetry_integration.py -v
```

### Launch the App and Verify:

1. Launch the ModScan Tool app
2. Verify telemetry is sent in debug log:
   ```
   tail -f ~/Desktop/modscan_telemetry_debug.log
   ```
3. Query the database to confirm records were inserted:
   ```sql
   SELECT COUNT(*), app_version FROM telemetry GROUP BY app_version;
   ```

## Security Model

### INSERT Access (App - Unauthenticated)
- ✅ App can INSERT records without authentication
- ✅ Each app instance generates its own UUID
- ✅ User sends their UUID with telemetry data
- ⚠️ **Trade-off**: An attacker on the network could forge requests with another user's UUID, but this is acceptable for telemetry

### SELECT Access (Dashboard - Authenticated)
- ✅ Only authenticated users can READ telemetry data
- ✅ Used for analytics dashboard and admin reporting
- ✅ Requires database credentials (not exposed to distributed app)

### Role-Based Features
- Debug logging is enabled if user has 'developer' or 'debug' role
- Roles are stored in `known_users` table
- Retrieved via `get_user_roles()` RPC function

## Troubleshooting

### PostgREST returns 404 for tables

**Solution**: Verify RLS is enabled and policies exist:
```sql
SELECT tablename, rowsecurity FROM pg_tables 
WHERE tablename IN ('telemetry', 'telemetry_test', 'known_users');
```

### PostgREST returns 403 Forbidden

**Solution**: Check RLS policies are correct:
```sql
SELECT tablename, policyname, permissive, roles 
FROM pg_policies 
WHERE tablename IN ('telemetry', 'telemetry_test');
```

### App says "PostgreSQL backend not configured"

**Solution**: Ensure `analytics_config.py` has:
```python
BACKEND_TYPE = "postgres"
POSTGRES_URL = "http://192.168.1.72:3001"
```

### RPC call to `get_user_roles` returns 404

**Solution**: Verify function exists and has correct signature:
```sql
SELECT routine_name, routine_type 
FROM information_schema.routines 
WHERE routine_name = 'get_user_roles';
```

## File Changes Summary

### New Files
- `analytics/backends/postgres.py` - PostgreSQL/PostgREST backend adapter
- `setup_postgres.sql` - Database setup script with RLS policies
- `analytics_config.example.py` - Configuration template

### Modified Files
- `analytics_config.py` - Changed default backend to PostgreSQL
- `analytics/telemetry.py` - Added PostgreSQL backend support in `get_backend()`

### Git Tracking
- `analytics_config.py` is in `.gitignore` to prevent credential leakage
- All other changes are tracked in git

## Next Steps

1. ✅ Run `setup_postgres.sql` against your appdb database
2. ✅ Verify PostgREST is running on port 3001
3. ✅ Test with curl or your app
4. ✅ Monitor `~/Desktop/modscan_telemetry_debug.log` to verify data is being sent
5. Deploy the updated app with confidence - it's fully distributable!

## Migration from Supabase

If migrating from Supabase:
1. Consider backing up your Supabase telemetry data first
2. Update `BACKEND_TYPE = "postgres"` in analytics_config.py
3. Run `setup_postgres.sql` to create RLS policies
4. Test with both backends running during transition if desired
5. Switch all clients to PostgreSQL backend once verified
