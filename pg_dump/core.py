import logging
import pathlib
import subprocess

import psycopg2

from pg_dump import config

log = logging.getLogger(__name__)


def get_connection():
    log.info(
        "Connecting to postgres on host '%s' and port '%s'",
        config.settings.PGDUMP_DATABASE_HOSTNAME,
        config.settings.PGDUMP_DATABASE_PORT,
    )
    conn = psycopg2.connect(
        user=config.settings.PGDUMP_DATABASE_USER,
        password=config.settings.PGDUMP_DATABASE_PASSWORD,
        host=config.settings.PGDUMP_DATABASE_HOSTNAME,
        port=config.settings.PGDUMP_DATABASE_PORT,
        database=config.settings.PGDUMP_DATABASE_DB,
    )
    return conn


def get_postgres_major_version() -> int:
    log.info("Start getting postgres version")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT version();")
    result = cur.fetchone()
    if result is None:
        raise Exception("Could not fetch version from postgres database")
    full_version: str = result[0]

    log.info(full_version)

    full_version_split = full_version.split(" ")
    major_version = int(float(full_version_split[1]))

    cur.close()
    conn.close()
    log.info(f"Postgres major version: {major_version}")
    return major_version


def recreate_pgpass_file():
    log.info("Start creating .pgpass file")
    text = config.settings.PGDUMP_DATABASE_HOSTNAME
    text += f":{config.settings.PGDUMP_DATABASE_PORT}"
    text += f":{config.settings.PGDUMP_DATABASE_USER}"
    text += f":{config.settings.PGDUMP_DATABASE_DB}"
    text += f":{config.settings.PGDUMP_DATABASE_PASSWORD}"
    pgpass = pathlib.Path().home() / ".pgpass"
    log.info("Removing old .pgpass file")
    pgpass.unlink(missing_ok=True)
    pgpass.touch(0o600)

    with open(pgpass, "w") as file:
        file.write(text)
    log.info("File .pgpass created")


def run_pg_dump():
    p = subprocess.Popen(
        [
            "pg_dump",
            "-v",
            "-O",
            "-Fc",
            "-U",
            config.settings.PGDUMP_DATABASE_USER,
            "-p",
            config.settings.PGDUMP_DATABASE_PORT,
            "-h",
            config.settings.PGDUMP_DATABASE_HOSTNAME,
            config.settings.PGDUMP_DATABASE_DB,
            "-f",
            "outputasdlllll.sql",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output, err = p.communicate()
    if p.returncode != 0:
        log.error(output.decode())
        log.error(err.decode())
        log.error(f"Finished pg_dump with status code {p.returncode}")
    else:
        log.info(output.decode())
        log.info(err.decode())
        log.info(f"Finished pg_dump with status code {p.returncode}")
