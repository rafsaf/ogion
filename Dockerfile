FROM python:3.11.5-alpine AS base
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV ROOT_MODE="false"
ENV SERVICE_NAME="backuper"
ENV FOLDER_PATH="/var/lib/backuper"
ENV LOG_FOLDER_PATH="/var/log/backuper"
WORKDIR ${FOLDER_PATH}

RUN apk update && apk add wget unzip postgresql-client mariadb-client mariadb-connector-c runuser build-base libffi-dev
RUN addgroup --gid 1001 --system $SERVICE_NAME && \
    adduser -D -G $SERVICE_NAME --shell /bin/false --uid 1001 $SERVICE_NAME

FROM base as poetry
RUN pip install poetry==1.5.1
COPY poetry.lock pyproject.toml ./
RUN poetry export -o /requirements.txt --without-hashes
RUN poetry export -o /requirements-dev.txt --without-hashes --with dev

FROM base AS tests
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
# reduce size of botocore lib, see https://github.com/boto/botocore/issues/1543
RUN mkdir /tmp/data \
    && cp -r /usr/local/lib/python3.11/site-packages/botocore/data/s3 /tmp/data/ \ 
    && cp -f /usr/local/lib/python3.11/site-packages/botocore/data/*.json /tmp/data \
    && rm -rf /usr/local/lib/python3.11/site-packages/botocore/data \
    && cp -r /tmp/data /usr/local/lib/python3.11/site-packages/botocore/ \
    && rm -rf /tmp/data

COPY backuper backuper
# rm 7zip to save ~5M for aarch64 when on amd64 and reverse
RUN remove_arch=$(arch | sed s/aarch64/amd64/ | sed s/x86_64/arm64/) \
    && rm -rf backuper/bin/7zip/${remove_arch}
# rm 7zip 7zz dynamic linked version binary
RUN target_arch=$(arch | sed s/aarch64/arm64/ | sed s/x86_64/amd64/) \
    && rm -f backuper/bin/7zip/${target_arch}/7zz
RUN apk del build-base libffi-dev
COPY scripts/docker_entrypoint.sh /docker_entrypoint.sh

ENTRYPOINT ["/bin/sh", "/docker_entrypoint.sh"]
CMD ["python", "-m", "backuper.main"] 