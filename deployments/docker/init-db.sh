#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE auth_db;
    CREATE DATABASE catalog_db;
    CREATE DATABASE inventory_db;
    CREATE DATABASE order_db;
    CREATE DATABASE payment_db;
    CREATE DATABASE notification_db;

    -- Create a non-superuser application role for RLS enforcement.
    -- Superuser roles bypass RLS unconditionally, so services MUST connect
    -- as this role for row-level security policies to take effect.
    CREATE ROLE cloudscale_app WITH LOGIN PASSWORD 'cloudscale_app_pass';
EOSQL

# Grant permissions on each microservice database to the app role
for db in auth_db catalog_db inventory_db order_db payment_db notification_db; do
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" <<-EOSQL
        GRANT CONNECT ON DATABASE ${db} TO cloudscale_app;
        GRANT USAGE ON SCHEMA public TO cloudscale_app;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cloudscale_app;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            GRANT USAGE, SELECT ON SEQUENCES TO cloudscale_app;
EOSQL
done

echo "Microservice databases and cloudscale_app role successfully created."
