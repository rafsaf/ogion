# Deployment

In general, use docker image `rafsaf/ogion` (here [available tags on dockerhub](https://hub.docker.com/r/rafsaf/ogion/tags)), it supports both `amd64` and `arm64` architectures. Standard way would be to run it with docker compose or as a kubernetes deployment. If not sure, use `latest`.

## Docker Compose

### Docker compose file

```yml
# docker-compose.yml

services:
  ogion:
    container_name: ogion
    image: rafsaf/ogion:latest
    environment:
      - POSTGRESQL_DB1=...
      - MYSQL_DB2=...
      - MARIADB_DB3=...

      - ZIP_ARCHIVE_PASSWORD=change_me
      - BACKUP_PROVIDER=name=gcs bucket_name=my_bucket_name bucket_upload_path=my_ogion_instance_1 service_account_base64=Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo=
```

### Notes

- For hard debug you can set `LOG_LEVEL=DEBUG` and use (container name is ogion):
  ```bash
  docker logs ogion
  ```
- There is runtime flag `--single` that **ignores cron, make all databases backups and exits**. To use it when having already running container, use:
  ```bash
  docker compose run --rm ogion python -m ogion.main --single
  ```
  BE CAREFUL, if your setup if fine, this will upload backup files to cloud provider, so costs may apply.
- There is runtime flag `--debug-notifications` that **setup notifications, raise dummy exception and exits**. This can help ensure notifications are working:
  ```bash
  docker compose run --rm ogion python -m ogion.main --debug-notifications
  ```

## Kubernetes

```yml
# ogion-deployment.yml

kind: Namespace
apiVersion: v1
metadata:
  name: ogion
---
apiVersion: v1
kind: Secret
metadata:
  name: ogion-secrets
  namespace: ogion
type: Opaque
stringData:
  POSTGRESQL_DB1: ...
  MYSQL_DB2: ...
  MARIADB_DB3: ...
  ZIP_ARCHIVE_PASSWORD: change_me
  BACKUP_PROVIDER: "name=gcs bucket_name=my_bucket_name bucket_upload_path=my_ogion_instance_1 service_account_base64=Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo="
---
apiVersion: apps/v1
kind: Deployment
metadata:
  namespace: ogion
  name: ogion
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ogion
  template:
    metadata:
      labels:
        app: ogion
    spec:
      containers:
        - image: rafsaf/ogion:latest
          name: ogion
          envFrom:
            - secretRef:
                name: ogion-secrets
```

### Notes

- For hard debug you can set `LOG_LEVEL: DEBUG` and use (for brevity random pod name used):
  ```bash
  kubectl logs ogion-9c8b8b77d-z5xsc -n ogion
  ```
- There is runtime flag `--single` that **ignores cron, make all databases backups and exits**. To use it when having already running container, use:
  ```bash
  kubectl exec --stdin --tty ogion-9c8b8b77d-z5xsc -n ogion -- runuser -u ogion -- python -m ogion.main --single
  ```
  BE CAREFUL, if your setup if fine, this will upload backup files to cloud provider, so costs may apply.
- There is runtime flag `--debug-notifications` that **setup notifications, raise dummy exception and exits**. This can help ensure notifications are working:
  ```bash
  kubectl exec --stdin --tty ogion-9c8b8b77d-z5xsc -n ogion -- runuser -u ogion -- python -m ogion.main --debug-notifications
  ```
  <br>
  <br>
