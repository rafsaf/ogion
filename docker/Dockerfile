FROM python:3.13.1-slim-bookworm AS base
ARG TARGETARCH
ARG PYTHONUNBUFFERED=1
ARG PIP_DISABLE_PIP_VERSION_CHECK=1
ARG PIP_NO_CACHE_DIR=1
ENV SERVICE_NAME="ogion"
ENV FOLDER_PATH="/var/lib/ogion"
ENV LOG_FOLDER_PATH="/var/log/ogion"
ENV OGION_CPU_ARCHITECTURE=${TARGETARCH}
WORKDIR ${FOLDER_PATH}

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get -y update && apt-get -y install age curl wget tar gpg

COPY scripts scripts
RUN ./scripts/install_mariadb_client.sh
RUN ./scripts/install_postgresql_client.sh
RUN apt-get -y remove gpg

FROM base AS poetry
RUN --mount=type=cache,target=/root/.cache/pip pip install poetry==2.0.1
RUN --mount=type=cache,target=/root/.cache/pip poetry self add poetry-plugin-export
COPY poetry.lock pyproject.toml ./
RUN poetry export -o /requirements.txt --without-hashes
RUN poetry export -o /requirements-tests.txt --without-hashes --with tests

FROM base AS common
COPY --from=poetry /requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
RUN rm -f requirements.txt

COPY ogion ogion

# rm to save ~65M
RUN rm -f \
    /usr/bin/mariadb-binlog \
    /usr/bin/mariadb-slap \
    /usr/bin/mariadb-admin \
    /usr/bin/mariadb-check \
    /usr/bin/mariadb-show \
    /usr/bin/mariadb-import \
    /usr/bin/perror \
    /usr/bin/mariadb-conv \
    /usr/bin/mariadb-plugin \
    /usr/bin/mariadb-tzinfo-to-sql \
    /usr/bin/resolve_stack_dump \
    /usr/bin/my_print_defaults \
    /usr/bin/mariadb-waitpid \
    /usr/bin/replace

COPY LICENSE LICENSE

FROM common AS tests
COPY --from=poetry /requirements-tests.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements-tests.txt
COPY pyproject.toml .
COPY tests tests
CMD ["pytest"]

FROM common AS build
CMD ["python", "-m", "ogion.main"] 