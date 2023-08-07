# Deployment

In general, use docker image `rafsaf/backuper` (here [available tags on dockerhub](https://hub.docker.com/r/rafsaf/backuper/tags)), it supports both `amd64` and `arm64` architectures. Standard way would be to run it with docker compose or as a kubernetes deployment. If not sure, use `latest`.

## Docker Compose

### Docker compose file

```yml
# docker-compose.yml

services:
  backuper:
    container_name: backuper
    image: rafsaf/backuper:latest
    environment:
      - POSTGRESQL_DB1=...
      - MYSQL_DB2=...
      - MARIADB_DB3=...

      - ZIP_ARCHIVE_PASSWORD=change_me
      - BACKUP_PROVIDER=name=gcs bucket_name=my_bucket_name bucket_upload_path=my_backuper_instance_1 service_account_base64=Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo=
```

### Notes

- For hard debug you can set `LOG_LEVEL=DEBUG` and use (container name is backuper):
  ```bash
  docker logs backuper
  ```
- There is dedicated flag --single that **ignores cron, make all databases backups and exits**. To use it when having already running container, use:
  ```bash
  docker compose run --rm backuper python -m backuper.main --single
  ```
  BE CAREFUL, if your setup if fine, this will upload backup files to cloud provider, so costs may apply.

## Kubernetes

```yml
# backuper-deployment.yml

kind: Namespace
apiVersion: v1
metadata:
  name: backuper
---
apiVersion: v1
kind: Secret
metadata:
  name: backuper-secrets
  namespace: backuper
type: Opaque
stringData:
  POSTGRESQL_DB1: ...
  MYSQL_DB2: ...
  MARIADB_DB3: ...
  ZIP_ARCHIVE_PASSWORD: change_me
  BACKUP_PROVIDER: "name=gcs bucket_name=my_bucket_name bucket_upload_path=my_backuper_instance_1 service_account_base64=Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo="
---
apiVersion: apps/v1
kind: Deployment
metadata:
  namespace: backuper
  name: backuper
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backuper
  template:
    metadata:
      labels:
        app: backuper
    spec:
      containers:
        - image: rafsaf/backuper:latest
          name: backuper
          envFrom:
            - secretRef:
                name: backuper-secrets
```

### Notes

- For hard debug you can set `LOG_LEVEL: DEBUG` and use (for brevity random pod name used):
  ```bash
  kubectl logs backuper-9c8b8b77d-z5xsc -n backuper
  ```
- There is dedicated flag --single that **ignores cron, make all databases backups and exits**. To use it when having already running container, use:
  ```bash
  kubectl exec --stdin --tty backuper-9c8b8b77d-z5xsc -n backuper -- runuser -u backuper -- python -m backuper.main --single
  ``` 
  BE CAREFUL, if your setup if fine, this will upload backup files to cloud provider, so costs may apply.

<br>
<br>