import logging
import pathlib
import re
import subprocess

import psycopg2

from pg_dump import config

log = logging.getLogger(__name__)


class SubprocessError(Exception):
    pass


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


def run_subprocess(shell_args: list[str]) -> str:
    log.info("Running in subprocess: '%s'", " ".join(shell_args))
    p = subprocess.Popen(
        shell_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    output, err = p.communicate()

    if p.returncode != 0:
        log.error("Finished with status %s", p.returncode)
        log.error(output)
        log.error(err)
        raise SubprocessError(
            f"'{' '.join(shell_args)}' \n"
            f"Process failed with code: {p.returncode} and shell args: {shell_args}"
        )
    else:
        log.info("Finished successfully")
        log.info(output)
        log.info(err)
    return output


def run_pg_dump():
    run_subprocess(
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
    )


def get_postgres_version():
    pg_version_regex = re.compile(r"PostgreSQL \d*\.\d* ")
    result = run_subprocess(
        [
            "psql",
            "-U",
            config.settings.PGDUMP_DATABASE_USER,
            "-p",
            config.settings.PGDUMP_DATABASE_PORT,
            "-h",
            config.settings.PGDUMP_DATABASE_HOSTNAME,
            config.settings.PGDUMP_DATABASE_DB,
            "-c",
            "SELECT version();",
        ],
    )
    try:
        matches: list[str] = pg_version_regex.findall(result)
        for match in matches:
            return match.strip()
        return "Unknown"
    except KeyError:
        return "Unknown"
