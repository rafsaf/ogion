# Deployment

In general, use docker image `rafsaf/backuper` (here [available tags on dockerhub](https://hub.docker.com/r/rafsaf/backuper/tags)), it supports both `amd64` and `arm64` architectures. Standard way would be to run it with docker compose or as a kubernetes deployment.

## Docker Compose

```yml
services:
  # other stuff...

  backuper:
    image: rafsaf/backuper:latest
    env_file:
      - .env
```

## Kubernetes


