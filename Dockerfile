FROM python:3.11-slim-bullseye

ENV PYTHONUNBUFFERED=1
ENV PD_SERVICE_NAME="pg_dump"
ENV PD_FOLDER_PATH="/var/lib/pg_dump"

COPY scripts/install_pg_client_and_7zip.sh /install_pg_client_and_7zip.sh
RUN /bin/bash /install_pg_client_and_7zip.sh && rm -f /install_pg_client_and_7zip.sh

COPY pg_dump ${PD_FOLDER_PATH}/pg_dump/
COPY requirements.txt ${PD_FOLDER_PATH}/requirements.txt
COPY scripts/docker_entrypoint.sh /docker_entrypoint.sh

RUN python -m venv ${PD_FOLDER_PATH}/venv
ENV PATH="/var/lib/pg_dump/venv/bin:$PATH"
RUN pip install -r ${PD_FOLDER_PATH}/requirements.txt
RUN addgroup --gid 1001 --system $PD_SERVICE_NAME && \
    adduser --gid 1001 --shell /bin/false --disabled-password --uid 1001 $PD_SERVICE_NAME

ENTRYPOINT ["/bin/bash", "/docker_entrypoint.sh"]
WORKDIR /var/lib/pg_dump/
CMD ["python", "-m", "pg_dump.main"] 
