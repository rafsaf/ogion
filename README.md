# pg_dump

Small yet solid image for postgresql 10-15 backups scheduling based on postgresql-client `pg_dump`.

# Example docker-compose.yml

```yml
version: "3.4"

services:
  pg_dump:
    image: rafsaf/pg_dump:0.4.0
    volumes:
      - pg_dump_data:/var/lib/pg_dump/data/

volumes:
  pg_dump_data:
```

Supported backup providers:

- Local files
- Google Cloud Storage

# Full docker image reference

`rafsaf/pg_dump:0.4.0`

## Dockerhub:

https://hub.docker.com/repository/docker/rafsaf/pg_dump

## Reference:

**POSTGRES_HOST** - Postgres database hostname, defaults to `localhost`.

**POSTGRES_USER** - Postgres database username, defaults to `postgres`.

**POSTGRES_PASSWORD** - Postgres database password, defaults to `postgres`.

**POSTGRES_PORT** - Postgres database port, defaults to `5432`.

**POSTGRES_DB** - Postgres database name of db, defaults to `postgres`.

**CRON_RULE** - Cron expression when should backups perform, defaults to `0 5 * * *` (5 am UTC every day), must be valid cron syntax, see https://crontab.guru/examples.html for examples.

**ZIP_ARCHIVE_PASSWORD** - Password to 7zip archive creating, defaults to empty string, required for every provider in `BACKUP_PROVIDER` except `local`.

**BACKUP_PROVIDER** - Backup provider, must be one of supported, defaults to `local`.

**SUBPROCESS_TIMEOUT_SECS** - Timeout for all shell subprocesses in seconds, defaults to `3600` (1 hour).

**BACKUP_COOLING_SECS** - Cooling period after pg_dump subprocess fail in seconds, defaults to `60` (1 min).

**BACKUP_COOLING_RETRIES** - Max number of retries for single scheduled backup, defaults to `1`.

**BACKUP_MAX_NUMBER** - Max number of backups that can be stored in data folder (for local files provider) or in cloud, defaults to 7.

**LOG_LEVEL** - Log level (DEBUG, INFO, WARNING, ERROR), by default in docker image it is `INFO`

**GOOGLE_BUCKET_NAME** - Name of google bucket, by default empty string, requried for `gcs` as a `BACKUP_PROVIDER`, refer to section about Google Cloud Storage.

**GOOGLE_SERVICE_ACCOUNT_BASE64** - Base64 gcloud json service account, by default empty string, requried for `gcs` as a `BACKUP_PROVIDER`, refer to section about Google Cloud Storage.

**GOOGLE_BUCKET_UPLOAD_PATH** - Name of google bucket, by default None, optional for `gcs` as a `BACKUP_PROVIDER`, refer to section about Google Cloud Storage.


`gpg --generate-key`
`gpg --armor --export rafsaf | base64 -w 0 > public.key`
