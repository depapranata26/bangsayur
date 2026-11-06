#!/bin/sh
# Runs once, on first init of an empty pgdata volume (postgres entrypoint).
# Creates the Mattermost role + database. $MM_PASSWORD is passed to the
# postgres service from .env via docker-compose.yml.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mmuser') THEN
    CREATE ROLE mmuser LOGIN PASSWORD '${MM_PASSWORD}';
  ELSE
    ALTER ROLE mmuser LOGIN PASSWORD '${MM_PASSWORD}';
  END IF;
END
\$\$;
SELECT 'CREATE DATABASE mattermost OWNER mmuser'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mattermost')\gexec
EOSQL
