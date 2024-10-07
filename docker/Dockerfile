FROM python:3.12.7-slim-bookworm AS base
ARG TARGETARCH
ARG PYTHONUNBUFFERED=1
ARG PIP_DISABLE_PIP_VERSION_CHECK=1
ARG PIP_NO_CACHE_DIR=1
ENV SERVICE_NAME="ogion"
ENV FOLDER_PATH="/var/lib/ogion"
ENV LOG_FOLDER_PATH="/var/log/ogion"
ENV OGION_CPU_ARCHITECTURE=${TARGETARCH}
WORKDIR ${FOLDER_PATH}

RUN apt-get -y update && apt-get -y install wget unzip gpg rsync
COPY scripts scripts
RUN ./scripts/install_mariadb_client.sh
RUN ./scripts/install_postgresql_client.sh
RUN apt-get -y remove gpg

FROM base as poetry
RUN pip install poetry==1.8.2
RUN poetry self add poetry-plugin-export
COPY poetry.lock pyproject.toml ./
RUN poetry export -o /requirements.txt --without-hashes
RUN poetry export -o /requirements-tests.txt --without-hashes --with tests

FROM base as common
COPY --from=poetry /requirements.txt .
RUN pip install -r requirements.txt
RUN rm -f requirements.txt
# reduce size of botocore lib, see https://github.com/boto/botocore/issues/1543
RUN mkdir /tmp/data \
    && cp -r /usr/local/lib/python3.12/site-packages/botocore/data/s3 /tmp/data/ \ 
    && cp -f /usr/local/lib/python3.12/site-packages/botocore/data/*.json /tmp/data \
    && rm -rf /usr/local/lib/python3.12/site-packages/botocore/data \
    && cp -r /tmp/data /usr/local/lib/python3.12/site-packages/botocore/ \
    && rm -rf /tmp/data

COPY ogion ogion
# rm 7zip to save ~5M for aarch64 when on amd64 and reverse
RUN find ./ogion/bin/7zip/* ! -name "${OGION_CPU_ARCHITECTURE}" -type d -exec rm -r {} +
# rm 7zip 7zz dynamic linked version binary
RUN rm -f ogion/bin/7zip/${OGION_CPU_ARCHITECTURE}/7zz
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
RUN pip install -r requirements-tests.txt
COPY pyproject.toml .
COPY tests tests
CMD ["pytest"]

FROM common AS build
CMD ["python", "-m", "ogion.main"] 