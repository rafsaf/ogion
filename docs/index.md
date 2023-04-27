# Backuper

Tool for making scheduled backups of databases and uploading encrypted to safe clouds, for homelabs, hobby projects and so on, in environments like k8s, docker, vms.

| WARNING                                                                                                                                                                                                                                                |
| :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Although this project aims to be reliable backup tool and can help protect your 5GB Postgres data from evaporation, it's **NOT** a fit for your enterprise production systems with enormous databases size and application load. You have been warned. |

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
- kubernetes container
- systemd application

<br>
<br>