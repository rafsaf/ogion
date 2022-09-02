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

ENV PG_DUMP_FOLDER_PATH='/var/lib/pg_dump/'
ENV PG_DUMP_BACKUP_FOLDER_PATH='/var/lib/pg_dump/data/backup/'
ENV PG_DUMP_PICKLE_PG_DUMP_QUEUE_NAME='/var/lib/pg_dump/data/pg_queue.pickle'
ENV PG_DUMP_LOG_FOLDER_PATH='/var/log/pg_dump/'
ENV PG_DUMP_PGPASS_FILE_PATH='/var/lib/pg_dump/.pgpass'
ENV PG_DUMP_GPG_PUBLIC_KEY_BASE64_PATH='/var/lib/pg_dump/gpg_public.key.pub'
ENV PG_DUMP_LOG_LEVEL='INFO'
ENV PG_DUMP_SERVICE_NAME='pg_dump'

RUN addgroup --gid 1001 --system $PG_DUMP_SERVICE_NAME && \
    adduser --gid 1001 --shell /bin/false --disabled-password --no-create-home --uid 1001 $PG_DUMP_SERVICE_NAME && \
    mkdir -p /var/log/$PG_DUMP_SERVICE_NAME

ENTRYPOINT [ "/bin/bash", "/docker-entrypoint.sh" ]
CMD [ "python", "/var/lib/pg_dump/pg_dump/main.py"] 
