FROM python:3.11-slim-bullseye AS base
ENV PYTHONUNBUFFERED=1
ENV PD_SERVICE_NAME="pg_dump"
ENV PD_FOLDER_PATH="/var/lib/pg_dump"
WORKDIR ${PD_FOLDER_PATH}

RUN addgroup --gid 1001 --system $PD_SERVICE_NAME && \
    adduser --gid 1001 --shell /bin/false --disabled-password --uid 1001 $PD_SERVICE_NAME

RUN python -m venv venv
ENV PATH="$PD_FOLDER_PATH/venv/bin:$PATH"

COPY scripts/docker_entrypoint.sh /docker_entrypoint.sh
COPY scripts/install_pg_client_and_7zip.sh /install_pg_client_and_7zip.sh
RUN /bin/bash /install_pg_client_and_7zip.sh && rm -f /install_pg_client_and_7zip.sh

ENTRYPOINT ["/bin/bash", "/docker_entrypoint.sh"]

FROM base AS build
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY pg_dump .
CMD ["python", "-m", "pg_dump.main"] 

FROM base AS tests
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY pyproject.toml .
COPY tests .
COPY pg_dump .
CMD ["pytest"]