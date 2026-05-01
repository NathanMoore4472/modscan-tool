-- PostgreSQL RLS Setup for ModScan Tool Telemetry
-- Run this script against the appdb database to set up Row-Level Security policies
-- and required functions for postgREST-based telemetry collection

-- ============================================================================
-- ENSURE ID COLUMNS HAVE AUTO-INCREMENT
-- ============================================================================
-- Add GENERATED ALWAYS AS IDENTITY if not already set (safe to run multiple times)

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'telemetry' AND column_name = 'id'
        AND column_default IS NOT NULL
    ) THEN
        ALTER TABLE telemetry ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'telemetry_test' AND column_name = 'id'
        AND column_default IS NOT NULL
    ) THEN
        ALTER TABLE telemetry_test ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY;
    END IF;
END $$;

-- ============================================================================
-- ENSURE RLS IS ENABLED ON EXISTING TABLES
-- ============================================================================

ALTER TABLE telemetry ENABLE ROW LEVEL SECURITY;
ALTER TABLE telemetry_test ENABLE ROW LEVEL SECURITY;
ALTER TABLE known_users ENABLE ROW LEVEL SECURITY;


-- ============================================================================
-- DROP EXISTING POLICIES (if re-running this script)
-- ============================================================================

DROP POLICY IF EXISTS "anon_can_insert_telemetry" ON telemetry;
DROP POLICY IF EXISTS "anon_cannot_read_telemetry" ON telemetry;
DROP POLICY IF EXISTS "authenticated_can_read_telemetry" ON telemetry;

DROP POLICY IF EXISTS "anon_can_insert_telemetry_test" ON telemetry_test;
DROP POLICY IF EXISTS "anon_cannot_read_telemetry_test" ON telemetry_test;
DROP POLICY IF EXISTS "authenticated_can_read_telemetry_test" ON telemetry_test;

DROP POLICY IF EXISTS "anon_cannot_read_known_users" ON known_users;
DROP POLICY IF EXISTS "authenticated_can_read_known_users" ON known_users;


-- ============================================================================
-- TELEMETRY TABLE POLICIES (production)
-- ============================================================================
-- Allow anon role (from postgREST) to INSERT telemetry records
CREATE POLICY "anon_can_insert_telemetry"
ON telemetry
FOR INSERT
TO anon
WITH CHECK (true);

-- Deny anon role from reading telemetry (INSERT-only for app telemetry collection)
CREATE POLICY "anon_cannot_read_telemetry"
ON telemetry
FOR SELECT
TO anon
USING (false);

-- Allow authenticated role to read all telemetry (for analytics dashboard/admin)
CREATE POLICY "authenticated_can_read_telemetry"
ON telemetry
FOR SELECT
TO authenticated
USING (true);


-- ============================================================================
-- TELEMETRY_TEST TABLE POLICIES (CI/testing)
-- ============================================================================
-- Allow anon role to INSERT test records
CREATE POLICY "anon_can_insert_telemetry_test"
ON telemetry_test
FOR INSERT
TO anon
WITH CHECK (true);

-- Deny anon role from reading test data
CREATE POLICY "anon_cannot_read_telemetry_test"
ON telemetry_test
FOR SELECT
TO anon
USING (false);

-- Allow authenticated role to read test data (for test verification)
CREATE POLICY "authenticated_can_read_telemetry_test"
ON telemetry_test
FOR SELECT
TO authenticated
USING (true);


-- ============================================================================
-- KNOWN_USERS TABLE POLICIES
-- ============================================================================
-- Deny anon role from reading known_users
CREATE POLICY "anon_cannot_read_known_users"
ON known_users
FOR SELECT
TO anon
USING (false);

-- Allow authenticated role to read known_users (for role lookups in RPC)
CREATE POLICY "authenticated_can_read_known_users"
ON known_users
FOR SELECT
TO authenticated
USING (true);


-- ============================================================================
-- CREATE GET_USER_ROLES RPC FUNCTION
-- ============================================================================
-- This function replaces the Supabase RPC and is called by the app
-- to check if a user has developer/debug roles for logging features

DROP FUNCTION IF EXISTS get_user_roles(UUID) CASCADE;

CREATE OR REPLACE FUNCTION get_user_roles(user_uuid UUID)
RETURNS TEXT[]
AS $$
DECLARE
    result TEXT[];
BEGIN
    -- Query known_users table for roles associated with this user
    SELECT ARRAY(
        SELECT TRIM(BOTH ' ' FROM UNNEST(STRING_TO_ARRAY(ku.roles, ',')))
    )
    INTO result
    FROM known_users ku
    WHERE ku.uuid = user_uuid
    LIMIT 1;

    -- Return empty array if user not found
    RETURN COALESCE(result, ARRAY[]::TEXT[]);
END;
$$ LANGUAGE plpgsql STABLE;

-- Grant execute permission to postgREST roles
GRANT EXECUTE ON FUNCTION get_user_roles(UUID) TO anon, authenticated;


-- ============================================================================
-- ENABLE postgREST RPC ACCESS
-- ============================================================================
-- Ensure the get_user_roles function is accessible via postgREST
-- (postgreSQL RPC calls are automatically exposed by postgREST)

-- Verify function is executable
SELECT has_function_privilege('anon', 'get_user_roles(UUID)', 'EXECUTE') as "anon can execute";
SELECT has_function_privilege('authenticated', 'get_user_roles(UUID)', 'EXECUTE') as "authenticated can execute";


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these to verify setup is correct:

-- Check RLS is enabled:
-- SELECT schemaname, tablename, rowsecurity FROM pg_tables WHERE tablename IN ('telemetry', 'telemetry_test', 'known_users');

-- Check policies exist:
-- SELECT tablename, policyname, permissive, roles FROM pg_policies WHERE tablename IN ('telemetry', 'telemetry_test', 'known_users');

-- Test RPC function exists:
-- SELECT get_user_roles('00000000-0000-0000-0000-000000000000'::UUID);
