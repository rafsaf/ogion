FROM python:3.12.4-slim-bookworm AS base
ARG PYTHONUNBUFFERED=1
ARG PIP_DISABLE_PIP_VERSION_CHECK=1
ARG PIP_NO_CACHE_DIR=1
ENV ROOT_MODE="false"
ENV SERVICE_NAME="ogion"
ENV FOLDER_PATH="/var/lib/ogion"
ENV LOG_FOLDER_PATH="/var/log/ogion"
WORKDIR ${FOLDER_PATH}

RUN apt-get -y update && apt-get -y install wget unzip gpg
COPY scripts scripts
RUN ./scripts/install_mariadb_client.sh
RUN ./scripts/install_postgresql_client.sh
RUN apt-get -y remove gpg
RUN addgroup --gid 1001 --system ${SERVICE_NAME} && \
    adduser --gid 1001 --shell /bin/false --disabled-password --uid 1001 ${SERVICE_NAME}

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
RUN remove_arch=$(arch | sed s/aarch64/amd64/ | sed s/x86_64/arm64/) \
    && rm -rf ogion/bin/7zip/${remove_arch}
# rm 7zip 7zz dynamic linked version binary
RUN target_arch=$(arch | sed s/aarch64/arm64/ | sed s/x86_64/amd64/) \
    && rm -f ogion/bin/7zip/${target_arch}/7zz

COPY scripts/docker_entrypoint.sh /docker_entrypoint.sh
RUN rm -rf scripts
COPY LICENSE LICENSE

ENTRYPOINT ["/bin/sh", "/docker_entrypoint.sh"]

FROM common AS tests
COPY --from=poetry /requirements-tests.txt .
RUN pip install -r requirements-tests.txt
COPY pyproject.toml .
COPY tests tests
CMD ["pytest"]

FROM common AS build
CMD ["python", "-m", "ogion.main"] 