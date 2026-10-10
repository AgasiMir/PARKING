#!/bin/bash
set -e

# роль для потока WAL
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    -- идемпотентно: не падаем, если роль уже существует (volume не пересоздавался)
    DO \$do\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${REPLICATION_USER}') THEN
            CREATE ROLE ${REPLICATION_USER} WITH REPLICATION LOGIN PASSWORD '${REPLICATION_PASSWORD}';
        END IF;
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${POSTGRES_REPLICA_USER}') THEN
            CREATE ROLE ${POSTGRES_REPLICA_USER} LOGIN PASSWORD '${POSTGRES_REPLICA_PASSWORD}';
        END IF;
    END
    \$do\$;

    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_REPLICA_USER};
    GRANT USAGE ON SCHEMA public TO ${POSTGRES_REPLICA_USER};
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO ${POSTGRES_REPLICA_USER};
    -- default privileges: покрывают таблицы, которые alembic создаст ПОСЛЕ этого скрипта
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO ${POSTGRES_REPLICA_USER};
EOSQL

# разрешаем репликацию по сети
echo "host replication ${REPLICATION_USER} all scram-sha-256" >> "$PGDATA/pg_hba.conf"
