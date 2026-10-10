#!/bin/bash
set -e

if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "Doing initial basebackup from primary..."
  # пароль передаём в connection string:
  # 1) pg_basebackup не будет спрашивать Password: в неинтерактивном контейнере
  # 2) --write-recovery-conf пропишет его в primary_conninfo (postgresql.auto.conf),
  #    и standby после старта сам подключится к primary без запроса пароля
  until pg_basebackup \
      --dbname="host=postgres port=5432 user=${REPLICATION_USER} password=${REPLICATION_PASSWORD}" \
      --pgdata="$PGDATA" \
      --wal-method=stream --write-recovery-conf --progress; do
    echo "Waiting for primary to become available..."
    sleep 3
  done
  chown -R postgres:postgres "$PGDATA"
  # точка монтирования volume создаётся с 0755 от root;
  # pg_basebackup пишет в готовый каталог, не меняя режим, а chown
  # меняет только владельца — поэтому явно выставляем права,
  # иначе postgres откажется стартовать (Permissions should be 0700/0750)
  chmod 700 "$PGDATA"
fi

# стартуем от имени пользователя postgres
# (вариант без лага: recovery_min_apply_delay не задаём — WAL применяется сразу)
exec gosu postgres postgres -D "$PGDATA"
