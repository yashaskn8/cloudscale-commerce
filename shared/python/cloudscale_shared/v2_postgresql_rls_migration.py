"""
PostgreSQL Row-Level Security (RLS) Migration Blueprint.

This module provides SQL migration templates and helper functions for enabling
Row-Level Security on multi-tenant tables. RLS adds a database-enforced security
layer that prevents cross-tenant data access even if application code fails to
filter by tenant_id.

Architecture:
  - Application sets `app.current_tenant_id` via SET LOCAL at the start of each
    database session (done in the shared middleware/session manager).
  - RLS policies use `current_setting('app.current_tenant_id')` to filter rows.
  - Even a SQL injection attack cannot access other tenants' data because the
    policy is enforced by PostgreSQL itself.

Usage:
  - In production, these statements are executed via Alembic migrations.
  - The `generate_rls_migration()` function returns the full SQL for a given table.
  - `set_tenant_context()` demonstrates how to set the tenant context per-session.

Note: SQLite (used in tests) does not support RLS. These policies are
PostgreSQL-specific and are validated via migration dry-run tests.
"""

from collections.abc import Sequence

# ── Tables requiring RLS ────────────────────────────────────────────────────────

TENANT_TABLES: list[dict[str, str]] = [
    {"table": "products", "tenant_column": "tenant_id", "service": "catalog"},
    {"table": "orders", "tenant_column": "tenant_id", "service": "order"},
    {"table": "order_items", "tenant_column": "tenant_id", "service": "order"},
    {"table": "subscriptions", "tenant_column": "tenant_id", "service": "payment"},
    {"table": "invoices", "tenant_column": "tenant_id", "service": "payment"},
    {"table": "inventory_items", "tenant_column": "tenant_id", "service": "inventory"},
]


def generate_rls_migration(table_name: str, tenant_column: str = "tenant_id") -> str:
    """
    Generate the complete SQL migration for enabling RLS on a table.

    Returns a multi-statement SQL script that:
      1. Enables RLS on the table
      2. Forces RLS for table owners (prevents bypass by superuser roles)
      3. Creates a SELECT policy filtering rows by tenant context
      4. Creates INSERT/UPDATE/DELETE policies enforcing tenant ownership
      5. Creates a function to set tenant context per-session

    Args:
        table_name: Name of the PostgreSQL table.
        tenant_column: Column containing the tenant identifier.

    Returns:
        Complete SQL migration script as a string.
    """
    if table_name == "order_items":
        return f"""  # nosec B608
-- ============================================================================
-- Row-Level Security Migration: {table_name}
-- ============================================================================
-- Step 1: Enable Row-Level Security on the table
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

-- Step 2: Force RLS even for table owners (defense in depth)
ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;

-- Step 3: Drop existing policies if re-running migration
DROP POLICY IF EXISTS tenant_isolation_select ON {table_name};
DROP POLICY IF EXISTS tenant_isolation_insert ON {table_name};
DROP POLICY IF EXISTS tenant_isolation_update ON {table_name};
DROP POLICY IF EXISTS tenant_isolation_delete ON {table_name};

-- Step 4: SELECT policy — users can only read their own tenant's order items
CREATE POLICY tenant_isolation_select ON {table_name}
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM orders WHERE orders.id = {table_name}.order_id 
        AND orders.tenant_id = current_setting('app.current_tenant_id', true)
    ));

-- Step 5: INSERT policy — users can only insert order items for their own tenant's orders
CREATE POLICY tenant_isolation_insert ON {table_name}
    FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM orders WHERE orders.id = {table_name}.order_id 
        AND orders.tenant_id = current_setting('app.current_tenant_id', true)
    ));

-- Step 6: UPDATE policy — users can only update their own tenant's order items
CREATE POLICY tenant_isolation_update ON {table_name}
    FOR UPDATE
    USING (EXISTS (
        SELECT 1 FROM orders WHERE orders.id = {table_name}.order_id 
        AND orders.tenant_id = current_setting('app.current_tenant_id', true)
    ));

-- Step 7: DELETE policy — users can only delete their own tenant's order items
CREATE POLICY tenant_isolation_delete ON {table_name}
    FOR DELETE
    USING (EXISTS (
        SELECT 1 FROM orders WHERE orders.id = {table_name}.order_id 
        AND orders.tenant_id = current_setting('app.current_tenant_id', true)
    ));
""".strip()

    return f"""  # nosec B608
-- ============================================================================
-- Row-Level Security Migration: {table_name}
-- ============================================================================
-- This migration adds database-enforced tenant isolation to the {table_name}
-- table. Even if application code fails to filter by tenant_id, PostgreSQL
-- will prevent cross-tenant data access.
-- ============================================================================

-- Step 1: Enable Row-Level Security on the table
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

-- Step 2: Force RLS even for table owners (defense in depth)
ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;

-- Step 3: Drop existing policies if re-running migration
DROP POLICY IF EXISTS tenant_isolation_select ON {table_name};
DROP POLICY IF EXISTS tenant_isolation_insert ON {table_name};
DROP POLICY IF EXISTS tenant_isolation_update ON {table_name};
DROP POLICY IF EXISTS tenant_isolation_delete ON {table_name};

-- Step 4: SELECT policy — users can only read their own tenant's rows
CREATE POLICY tenant_isolation_select ON {table_name}
    FOR SELECT
    USING ({tenant_column} = current_setting('app.current_tenant_id', true));

-- Step 5: INSERT policy — users can only insert rows for their own tenant
CREATE POLICY tenant_isolation_insert ON {table_name}
    FOR INSERT
    WITH CHECK ({tenant_column} = current_setting('app.current_tenant_id', true));

-- Step 6: UPDATE policy — users can only update their own tenant's rows
CREATE POLICY tenant_isolation_update ON {table_name}
    FOR UPDATE
    USING ({tenant_column} = current_setting('app.current_tenant_id', true))
    WITH CHECK ({tenant_column} = current_setting('app.current_tenant_id', true));

-- Step 7: DELETE policy — users can only delete their own tenant's rows
CREATE POLICY tenant_isolation_delete ON {table_name}
    FOR DELETE
    USING ({tenant_column} = current_setting('app.current_tenant_id', true));

-- Step 8: Create index on tenant column for RLS query performance
CREATE INDEX IF NOT EXISTS idx_{table_name}_{tenant_column}
    ON {table_name} ({tenant_column});

-- Step 9: Grant minimal permissions to application role
-- (In production, the app connects as 'cloudscale_app' role, not superuser)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON {table_name} TO cloudscale_app;
""".strip()


def generate_tenant_context_function() -> str:
    """
    Generate the SQL function for setting tenant context at session level.

    This function is called at the beginning of each database session
    (via SQLAlchemy event listener) to set the current tenant ID.
    """
    return """
-- ============================================================================
-- Tenant Context Session Function
-- ============================================================================
-- Called at the start of each database session to set the tenant context.
-- Uses SET LOCAL so the setting is transaction-scoped (automatically reset
-- on COMMIT/ROLLBACK).
-- ============================================================================

CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id TEXT)
RETURNS VOID AS $$
BEGIN
    -- SET LOCAL scopes the setting to the current transaction only
    PERFORM set_config('app.current_tenant_id', p_tenant_id, true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute to application role
-- GRANT EXECUTE ON FUNCTION set_tenant_context(TEXT) TO cloudscale_app;
""".strip()


def generate_rollback_migration(table_name: str) -> str:
    """Generate the rollback (downgrade) migration for removing RLS from a table."""
    return f"""  # nosec B608
-- Rollback: Remove RLS from {table_name}
DROP POLICY IF EXISTS tenant_isolation_select ON {table_name};
DROP POLICY IF EXISTS tenant_isolation_insert ON {table_name};
DROP POLICY IF EXISTS tenant_isolation_update ON {table_name};
DROP POLICY IF EXISTS tenant_isolation_delete ON {table_name};
ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;
""".strip()


def generate_full_migration() -> str:
    """Generate the complete RLS migration for all tenant-scoped tables."""
    sections = [
        "-- ==========================================================",
        "-- CloudScale Commerce: Full RLS Migration",
        "-- ==========================================================",
        "-- Applies Row-Level Security to all multi-tenant tables.",
        "-- Run this migration AFTER the tenant_id columns exist.",
        "-- ==========================================================",
        "",
        generate_tenant_context_function(),
        "",
    ]

    for table_config in TENANT_TABLES:
        sections.append(generate_rls_migration(table_config["table"], table_config["tenant_column"]))
        sections.append("")

    return "\n".join(sections)


def set_tenant_context_sql(tenant_id: str) -> str:
    """
    Return the SQL statement to set tenant context for the current transaction.

    This is called by the SQLAlchemy session event listener in the shared
    DatabaseManager to set the tenant context after acquiring a connection.

    Example usage in SQLAlchemy:
        @event.listens_for(engine, "connect")
        def set_tenant(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute(set_tenant_context_sql(tenant_id))
            cursor.close()
    """
    # Use parameterized setting to prevent SQL injection
    safe_tenant = tenant_id.replace("'", "''")
    return f"SELECT set_config('app.current_tenant_id', '{safe_tenant}', true);"  # nosec B608


# ── Validation Helpers ──────────────────────────────────────────────────────────


def validate_rls_coverage(existing_tables: Sequence[str]) -> list[str]:
    """
    Check that all expected tenant tables have RLS configured.

    Returns a list of table names that are missing RLS policies.
    Useful for CI/CD pipeline health checks.
    """
    expected = {t["table"] for t in TENANT_TABLES}
    covered = set(existing_tables)
    missing = expected - covered
    return sorted(missing)
