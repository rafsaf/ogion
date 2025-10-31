FROM python:3.14-slim-trixie AS base
ARG TARGETARCH
ARG PYTHONUNBUFFERED=1
ARG PIP_DISABLE_PIP_VERSION_CHECK=1
ARG PIP_NO_CACHE_DIR=1
ENV SERVICE_NAME="ogion"
ENV FOLDER_PATH="/var/lib/ogion"
ENV LOG_FOLDER_PATH="/var/log/ogion"
ENV OGION_CPU_ARCHITECTURE=${TARGETARCH}
WORKDIR ${FOLDER_PATH}

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get -y update && apt-get -y install age curl wget tar gpg plzip lzip bash-completion

COPY scripts scripts
RUN ./scripts/install_mariadb_client.sh
RUN ./scripts/install_postgresql_client.sh
RUN apt-get -y remove gpg curl wget

FROM base AS uv
COPY --from=ghcr.io/astral-sh/uv:0.9.2 /uv /uvx /bin/
COPY uv.lock pyproject.toml ./
RUN uv export --no-dev --no-group tests --no-hashes -o /requirements.txt --no-install-workspace --frozen
RUN uv export --only-group tests --no-hashes -o /requirements-tests.txt --no-install-workspace --frozen

FROM base AS common
COPY --from=uv /requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
RUN rm -f requirements.txt
RUN activate-global-python-argcomplete -y

COPY ogion ogion

RUN ln -s ${FOLDER_PATH}/ogion/bin/ogion /usr/bin/ogion
RUN python -m compileall -b ${FOLDER_PATH}/ogion

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
COPY --from=uv /requirements-tests.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements-tests.txt
COPY pyproject.toml .
COPY tests tests
CMD ["pytest", "-vv"]

FROM common AS build
CMD ["ogion"] 