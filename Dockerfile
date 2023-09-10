FROM python:3.11.5-alpine AS base
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV ROOT_MODE="false"
ENV SERVICE_NAME="backuper"
ENV FOLDER_PATH="/var/lib/backuper"
ENV LOG_FOLDER_PATH="/var/log/backuper"
WORKDIR ${FOLDER_PATH}

RUN apk update && apk add wget unzip postgresql-client mariadb-client mariadb-connector-c runuser
RUN addgroup --gid 1001 --system $SERVICE_NAME && \
    adduser -D -G $SERVICE_NAME --shell /bin/false --uid 1001 $SERVICE_NAME

COPY bin bin
COPY scripts/docker_entrypoint.sh /docker_entrypoint.sh

ENTRYPOINT ["/bin/sh", "/docker_entrypoint.sh"]

FROM base as poetry
RUN apk add build-base
RUN pip install poetry==1.5.1
COPY poetry.lock pyproject.toml ./
RUN poetry export -o /requirements.txt --without-hashes
RUN poetry export -o /requirements-dev.txt --without-hashes --with dev

FROM base AS tests
RUN apk add make
COPY --from=poetry /requirements-dev.txt .
RUN pip install -r requirements-dev.txt
RUN rm -f requirements-dev.txt
COPY pyproject.toml .
COPY tests tests
COPY backuper backuper
CMD ["pytest"]

FROM base AS build
COPY --from=poetry /requirements.txt .
RUN pip install -r requirements.txt
RUN rm -f requirements.txt
COPY backuper backuper
CMD ["python", "-m", "backuper.main"] 