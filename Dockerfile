FROM python:3.11.3-slim-bullseye AS base
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME="backuper"
ENV FOLDER_PATH="/var/lib/backuper"
WORKDIR ${FOLDER_PATH}

RUN addgroup --gid 1001 --system $SERVICE_NAME && \
    adduser --gid 1001 --shell /bin/false --disabled-password --uid 1001 $SERVICE_NAME

RUN python -m venv venv
ENV PATH="$FOLDER_PATH/venv/bin:$PATH"

COPY scripts/docker_entrypoint.sh /docker_entrypoint.sh
COPY scripts scripts
COPY bin bin
RUN /bin/bash scripts/install_apt_libs_and_7zip.sh
RUN rm -rf scripts bin/7zip
RUN apt-get remove -y wget lsb-release gpg xz-utils && apt-get autoremove --purge -y        \
    && rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/*.list

ENTRYPOINT ["/bin/bash", "/docker_entrypoint.sh"]

FROM base AS tests
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY pyproject.toml .
COPY tests tests
COPY backuper backuper
CMD ["coverage", "run", "-m", "pytest", "-vv"]

FROM tests AS pyinstaller
COPY backuper_cli.py .
RUN apt-get -y update && apt-get -y install binutils
ENTRYPOINT []
CMD ["pyinstaller", "backuper_cli.py", "--add-binary", "bin/7zz:bin/7zz", "--name","backuper"]

FROM base AS build
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY backuper backuper
CMD ["python", "-m", "backuper.main"] 