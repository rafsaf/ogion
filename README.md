# Backuper

A tool for performing scheduled database backups and transferring encrypted data to secure clouds, for home labs, hobby projects, etc., in environments such as k8s, docker, vms.

| WARNING                                                                                                                                                                                                                                                    |
| :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| While this project aims to be a reliable backup tool and can help protect your hobby 5GB Postgres database from evaporation, it is **NOT** suitable for enterprise production systems with huge databases and application workloads. You have been warned. |

## Documentation
[https://backuper.rafsaf.pl](https://backuper.rafsaf.pl)

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

- docker (docker compose) container
- kubernetes deployment

## Architectures

- linux/amd64
- linux/arm64

<br>
<br>