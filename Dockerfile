FROM python:3.10-slim-buster

# https://www.postgresql.org/download/linux/debian/
RUN apt-get -y update && apt-get install -y wget gnupg2

RUN sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt buster-pgdg main" > \
    /etc/apt/sources.list.d/pgdg.list'

RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    | apt-key add -

RUN apt-get -y update && apt-get -y install postgresql-client-14

COPY pg_dump /var/lib/pg_dump/pg_dump/
COPY requirements.txt /var/lib/pg_dump/requirements.txt
COPY docker-entrypoint.sh /docker-entrypoint.sh

RUN python -m venv /var/lib/pg_dump/venv
ENV PATH="/var/lib/pg_dump/venv/bin:$PATH"

RUN pip install -r /var/lib/pg_dump/requirements.txt

ENV PGDUMP_FOLDER_PATH='/var/lib/pg_dump/'
ENV PGDUMP_BACKUP_FOLDER_PATH='/var/lib/pg_dump/data/backup/'
ENV PGDUMP_PICKLE_PGDUMP_QUEUE_NAME='/var/lib/pg_dump/data/PGDUMP_QUEUE.pickle'
ENV PGDUMP_LOG_FOLDER_PATH='/var/log/pg_dump/'
ENV PGDUMP_PGPASS_FILE_PATH='/var/lib/pg_dump/.pgpass'
ENV PGDUMP_LOG_LEVEL='INFO'
ENV SERVICE_NAME='pg_dump'

RUN addgroup --gid 1001 --system $SERVICE_NAME && \
    adduser --gid 1001 --shell /bin/false --disabled-password --no-create-home --uid 1001 $SERVICE_NAME && \
    mkdir -p /var/log/$SERVICE_NAME

ENTRYPOINT [ "/bin/bash", "/docker-entrypoint.sh" ]
CMD [ "python", "/var/lib/pg_dump/pg_dump/main.py"] 
