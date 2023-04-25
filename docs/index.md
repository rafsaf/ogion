# backuper

Tool for making scheduled backups of databases and uploading encrypted to safe clouds, for homelabs, hobby projects and so on, in environments like k8s, docker, vms.

!!! warning
    Although this project aims to be reliable backup tool and can help protect your 5GB Postgres data from evaporation, it's **NOT** a fit for your enterprise production systems with enormous databases size and application load. You have been warned.

## Supported backup targets

- PostgreSQL (11, 12, 13, 14, 15)
- MySQL (5.7, 8.0)
- Files
- Directories

## Supported upload providers

- Google Cloud Storage bucket
- Local directory
- ... more in the future

## Notifications

- Discord

## Deployment strategies

- docker (docker compose) container
- kubernetes container
- systemd application

<br>
<br>