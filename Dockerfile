FROM python:3.10-slim-buster

ENV PD_SERVICE_NAME="pg_dump"
ENV PD_FOLDER_PATH="/var/lib/pg_dump"
ENV PD_LOG_FOLDER_PATH="/var/log/pg_dump"
ENV PD_LOG_LEVEL="INFO"

# https://www.postgresql.org/download/linux/debian/
RUN apt-get -y update && apt-get install -y wget gnupg2 gpg
RUN sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt buster-pgdg main" > \
    /etc/apt/sources.list.d/pgdg.list'
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    | apt-key add -
RUN apt-get -y update && apt-get -y install postgresql-client-14

COPY pg_dump ${PD_FOLDER_PATH}/pg_dump/
COPY requirements.txt ${PD_FOLDER_PATH}/requirements.txt
COPY scripts/docker_entrypoint.sh /docker_entrypoint.sh

RUN python -m venv ${PD_FOLDER_PATH}/venv
ENV PATH="/var/lib/pg_dump/venv/bin:$PATH"
RUN pip install -r ${PD_FOLDER_PATH}/requirements.txt
RUN addgroup --gid 1001 --system $PD_SERVICE_NAME && \
    adduser --gid 1001 --shell /bin/false --disabled-password --uid 1001 $PD_SERVICE_NAME && \
    mkdir -p /var/log/$PD_SERVICE_NAME

ENTRYPOINT ["/bin/bash", "/docker_entrypoint.sh"]
CMD ["python", "/var/lib/pg_dump/pg_dump/main.py"] 
