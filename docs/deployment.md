# Deployment

Use docker image `rafsaf/ogion` ([available tags on dockerhub](https://hub.docker.com/r/rafsaf/ogion/tags)). Supports both `amd64` and `arm64` architectures. Standard deployment methods are docker compose or kubernetes. Using `latest` tag is not recommended.

For runtime flags and CLI commands, see [CLI Reference](cli.md). For environment variables and configuration, see [Configuration](configuration.md).

## Docker Compose

```yml
# docker-compose.yml

services:
  ogion:
    container_name: ogion
    image: rafsaf/ogion:8.2
    network_mode: host
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    volumes:
      - ogion_data:/var/lib/ogion/data
    env_file:
      - .env

volumes:
  ogion_data:
```

## Kubernetes

```yml
# ogion-deployment.yml

apiVersion: apps/v1
kind: Deployment
metadata:
  namespace: ogion
  name: ogion
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: ogion
  template:
    metadata:
      labels:
        app: ogion
    spec:
      securityContext:
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        runAsNonRoot: true
      containers:
        - name: ogion
          image: rafsaf/ogion:8.2
          imagePullPolicy: Always
          securityContext:
            readOnlyRootFilesystem: true
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
            seccompProfile:
              type: RuntimeDefault
          envFrom:
            - secretRef:
                name: ogion-secrets
          env:
            - name: LZIP_THREADS
              valueFrom:
                resourceFieldRef:
                  resource: limits.cpu
          resources:
            requests:
              cpu: "20m"
              memory: "512Mi"
            limits:
              cpu: "2"
              memory: "512Mi"
          volumeMounts:
            - name: data
              mountPath: /var/lib/ogion/data
      volumes:
        - name: data
          emptyDir: {}
```

<br>
<br>
