# Backuper

A tool for performing scheduled database backups and transferring encrypted data to secure clouds, for home labs, hobby projects, etc., in environments such as k8s, docker, vms.

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
- AWS S3 bucket
- Azure Blob Storage
- Debug (local)

## Notifications

- Discord

## Deployment strategies

Using docker image: `rafsaf/backuper:latest`, see all tags on [dockerhub](https://hub.docker.com/r/rafsaf/backuper/tags)

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
  db:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=pwd
  backuper:
    image: rafsaf/backuper:latest
    environment:
      - POSTGRESQL_PG15=host=db password=pwd cron_rule=0 0 5 * * port=5432
      - ZIP_ARCHIVE_PASSWORD=change_me
      - BACKUP_PROVIDER=name=debug

```

(NOTE this will use provider [debug](https://backuper.rafsaf.pl/providers/debug/) that store backups locally in the container).

## Real world usage

The author actively uses backuper (with GCS) for one production project [plemiona-planer.pl](https://plemiona-planer.pl) postgres database (both PRD and STG) and for bunch of homelab projects including self hosted Firefly III mariadb, Grafana postgres, KeyCloak postgres, Nextcloud postgres and configuration file, Minecraft server files, and two other postgres dbs for some demo projects.

See how it looks for PRD ~2GB size database:


![](docs/images/backuper_gcp_example_twp-min.jpg)

<br>
<br>