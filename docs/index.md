# Backuper

A tool for performing scheduled database backups and transferring encrypted data to secure clouds, for home labs, hobby projects, etc., in environments such as k8s, docker, vms.

| WARNING                                                                                                                                                                                                                                                    |
| :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| While this project aims to be a reliable backup tool and can help protect your hobby 5GB Postgres database from evaporation, it is **NOT** suitable for enterprise production systems with huge databases and application workloads. You have been warned. |

## Documentation
- [https://backuper.rafsaf.pl](https://backuper.rafsaf.pl)

## Supported backup targets

- PostgreSQL (tested on 15, 14, 13, 12, 11)
- MySQL (tested on 8.0, 5.7)
- MariaDB (tested on 10.11, 10.6, 10.5, 10.4)
- Single file
- Directory

## Supported upload providers

- Google Cloud Storage bucket

## Notifications

- Discord

## Deployment strategies

Dockerhub: [https://hub.docker.com/r/rafsaf/backuper](https://hub.docker.com/r/rafsaf/backuper)

- docker (docker compose) container
- kubernetes deployment

## Architectures

- linux/amd64
- linux/arm64

## Example

Everyday 5am backup to Google Cloud Storage of PostgreSQL database defined in the same file and running in docker container.

```yml
# docker-compose.yml

services:
  postgresql_15:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=secret
  backuper:
    image: rafsaf/backuper:latest
    env_file:
      - .env.demo

```

And `.env.demo` file would look like (NOTE for this to work, **GOOGLE_SERVICE_ACCOUNT_BASE64** would need to be valid google service account, as described in [this section](/providers/google_cloud_storage/#google_service_account_base64)).

```bash
# .env.demo

POSTGRESQL_MY_PG_DB15='{"host": "postgresql_15","port": 5432, "password": "secret", "cron_rule": "0 0 5 * *"}'
ZIP_ARCHIVE_PASSWORD='change_me'
BACKUP_PROVIDER='gcs'
GOOGLE_BUCKET_NAME='my_bucket_name'
GOOGLE_BUCKET_UPLOAD_PATH='my_backuper_demo_instance'
GOOGLE_SERVICE_ACCOUNT_BASE64='Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo='
```

<br>
<br>