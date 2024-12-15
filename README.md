[![License](https://img.shields.io/github/license/rafsaf/ogion)](https://github.com/rafsaf/ogion/blob/main/LICENSE)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue)](https://docs.python.org/3/whatsnew/3.13.html)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Tests](https://github.com/rafsaf/ogion/actions/workflows/tests.yml/badge.svg)](https://github.com/rafsaf/ogion/actions/workflows/tests.yml)
[![Type check](https://github.com/rafsaf/ogion/actions/workflows/type_check.yml/badge.svg)](https://github.com/rafsaf/ogion/actions/workflows/type_check.yml)
[![Dev build](https://github.com/rafsaf/ogion/actions/workflows/dev_build.yml/badge.svg)](https://github.com/rafsaf/ogion/actions/workflows/dev_build.yml)
[![Release build](https://github.com/rafsaf/ogion/actions/workflows/release_build.yml/badge.svg)](https://github.com/rafsaf/ogion/actions/workflows/release_build.yml)
[![Update of db versions](https://github.com/rafsaf/ogion/actions/workflows/update_compose_dbs.yml/badge.svg)](https://github.com/rafsaf/ogion/actions/workflows/update_compose_dbs.yml)

# Ogion

A tool for performing scheduled database backups and transferring encrypted data to secure public clouds, for home labs, hobby projects, etc., in environments such as k8s, docker, vms.

Backups are in `age` format using [age](https://github.com/FiloSottile/age), with strong encryption under the hood. Why age? it's modern replacement for GnuPG, available for most architectures and systems.

This project is more or less well tested cron-like runtime with predefined supported providers and backup targets (see below) with sensible defaults for backup commands. It has rich integration tests using providers container replacements: fake gcs, azurite, minio. Goal was to make 100% sure it will work in the wild.

There is **no compression before age encryption** step whatsoever. This is intentional, prepare for large backups size (compared to ogion 6.0 where 7zip was used, some backups that were 300MB now are 2.2GB). There are known exploits when mixing compression with encryption, and for small systems compression this just seems unnecessary. See:

- [CRIME](https://en.wikipedia.org/wiki/CRIME)
- [BREACH](https://en.wikipedia.org/wiki/BREACH)
- [Known plaintext attack](https://en.wikipedia.org/wiki/Known-plaintext_attack)
- [A Known Plaintext Attack on the PKZIP](https://link.springer.com/content/pdf/10.1007/3-540-60590-8_12.pdf)
- [TLSv1.3 removes compression](https://blog.cloudflare.com/tls-1-3-overview-and-q-and-a/)

## Documentation

- [https://ogion.rafsaf.pl](https://ogion.rafsaf.pl)

## Alternatives

There are better tools for big corporate databases and systems:

- [pgBackRest - Reliable PostgreSQL Backup & Restore](https://pgbackrest.org/)
- [postgres operator for k8s based on pgBackRest from crunchydata](https://access.crunchydata.com/documentation/postgres-operator/latest)

## Supported backup targets

- PostgreSQL ([all currently supported versions](https://endoflife.date/postgresql))
- MariaDB ([all currently supported versions](https://endoflife.date/mariadb))
- MySQL ([all currently supported versions](https://endoflife.date/mysql))
- Single file
- Directory

## Supported upload providers

- Google Cloud Storage bucket
- S3 storage compatibile bucket (AWS, Minio)
- Azure Blob Storage
- Debug (local)

## Notifications

- Discord
- Email (SMTP)
- Slack

## Deployment strategies

Using docker image: `rafsaf/ogion:latest`, see all tags on [dockerhub](https://hub.docker.com/r/rafsaf/ogion/tags)

- docker (docker compose) container
- kubernetes deployment

## Architectures

- linux/amd64
- linux/arm64

## Example

Everyday 5am backup of PostgreSQL database defined in the same file and running in docker container.

```yml
# docker-compose.yml

services:
  db:
    image: postgres:17
    environment:
      - POSTGRES_PASSWORD=pwd
  ogion:
    image: rafsaf/ogion:latest
    environment:
      - POSTGRESQL_DB_README=host=db password=pwd cron_rule=0 0 5 * * port=5432
      - AGE_RECIPIENTS=age1q5g88krfjgty48thtctz22h5ja85grufdm0jly3wll6pr9f30qsszmxzm2
      - BACKUP_PROVIDER=name=debug
```

(NOTE this will use provider [debug](https://ogion.rafsaf.pl/latest/providers/debug/) that store backups locally in the container).

## Real world usage

The author actively uses ogion (with GCS) for one production project [plemiona-planer.pl](https://plemiona-planer.pl) postgres database (both PRD and STG) and for bunch of homelab projects including self hosted Firefly III mariadb, Grafana postgres, KeyCloak postgres, Nextcloud postgres and configuration file, Minecraft server files, and two other postgres dbs for some demo projects.

See how it looks for ~2GB size database:

![ogion_gcp_example_twp-min.jpg](https://raw.githubusercontent.com/rafsaf/ogion/main/docs/images/ogion_gcp_example_twp-min.jpg)

<br>
<br>
