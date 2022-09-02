# pg_dump

Small yet solid image for postgresql 10-14 backups scheduling based on postgresql-client `pg_dump`.

# Example docker-compose.yml

```yml
version: "3.4"

services:
  pg_dump:
    image: rafsaf/pg_dump:0.3
    volumes:
      - pg_dump_data:/var/lib/pg_dump/data/
      - pg_dump_logs:/var/log/pg_dump/

volumes:
  pg_dump_data:
  pg_dump_logs:
```

# Docker image reference

`rafsaf/pg_dump:0.3`

## Dockerhub:

https://hub.docker.com/repository/docker/rafsaf/pg_dump

## Reference:

**PGDUMP_DATABASE_HOSTNAME** - Postgres database hostname, defaults to `localhost`

**PGDUMP_DATABASE_USER** - Postgres database username, defaults to `postgres`

**PGDUMP_DATABASE_PASSWORD** - Postgres database password, defaults to `postgres`

**PGDUMP_DATABASE_PORT** - Postgres database port, defaults to `5432`

**PGDUMP_DATABASE_DB** - Postgres database name of db, defaults to `postgres`

**PGDUMP_BACKUP_POLICY_CRON_EXPRESSION** - Cron expression when should backups perform, defaults to `0 5 * * *` (5am every day), must be valid cron syntax, see https://crontab.guru/examples.html

**PGDUMP_NUMBER_PGDUMP_THREADS** - Number of worker threads, defaults to `2`

**PGDUMP_POSTGRES_TIMEOUT_AFTER_SECS** - Timeout for pgdump subprocess in seconds, defaults to `3600` (1 hour)

**PGDUMP_COOLING_PERIOD_SECS** - Cooling period after pgdump subprocess fail in seconds, defaults to `300` (5min)

**PGDUMP_COOLING_PERIOD_RETRIES** - Max number of retries for single scheduled backup, defaults to `5`

**PGDUMP_BACKUP_FOLDER_PATH** - Path to backup folder where pgdump subprocesses output folders are stored, by default in docker image it is `/var/lib/pg_dump/data/backup`

**PGDUMP_LOG_FOLDER_PATH** - Path to folder with logs, by default in docker image it is `/var/log/pg_dump/`

**PGDUMP_PGPASS_FILE_PATH** - Path to pgpass file, by default in docker image it is `/var/lib/pg_dump/.pgpass`

**PGDUMP_PICKLE_PGDUMP_QUEUE_NAME** - Path to pickled queue, background queue is dumped on app exit, to avoid data losses, by default in docker image it is `/var/lib/pg_dump/data/PGDUMP_QUEUE.pickle`

**PGDUMP_LOG_LEVEL** - Log level (DEBUG, INFO, WARNING, ERROR), by default in docker image it is `INFO`
