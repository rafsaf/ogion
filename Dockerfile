FROM python:3.11.4-slim-bookworm AS base
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV SERVICE_NAME="backuper"
ENV FOLDER_PATH="/var/lib/backuper"
ENV LOG_FOLDER_PATH="/var/log/backuper"
WORKDIR ${FOLDER_PATH}

RUN apt-get update -y && apt-get install -y curl wget unzip gpg xz-utils
RUN addgroup --gid 1001 --system $SERVICE_NAME && \
    adduser --gid 1001 --shell /bin/false --disabled-password --uid 1001 $SERVICE_NAME

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY scripts/docker_entrypoint.sh /docker_entrypoint.sh
COPY scripts scripts
COPY bin bin
RUN /bin/bash scripts/install_postgresql_client.sh
RUN /bin/bash scripts/install_mariadb_mysql_client.sh
RUN rm -rf scripts


ENTRYPOINT ["/bin/bash", "/docker_entrypoint.sh"]

FROM base as poetry
RUN pip install poetry==1.5.1
COPY poetry.lock pyproject.toml ./
RUN poetry export -o /requirements.txt --without-hashes
RUN poetry export -o /requirements-dev.txt --without-hashes --with dev

FROM base AS tests
RUN apt-get update -y && apt-get install -y make
COPY --from=poetry /requirements-dev.txt .
RUN pip install -r requirements-dev.txt
RUN rm -f requirements-dev.txt
COPY pyproject.toml .
COPY tests tests
COPY backuper backuper
COPY Makefile .
CMD ["make", "coverage"]

FROM tests AS pyinstaller
COPY backuper_cli.py .
RUN apt-get -y update && apt-get -y install binutils
ENTRYPOINT []
CMD ["pyinstaller", "backuper_cli.py", "--add-binary", "bin/7zz:bin/7zz", "--name","backuper"]

FROM base AS build
COPY --from=poetry /requirements.txt .
RUN pip install -r requirements.txt
RUN rm -f requirements.txt
COPY backuper backuper
CMD ["python", "-m", "backuper.main"] 