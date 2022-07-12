import logging
import pathlib
import re
import subprocess

from pg_dump import config

log = logging.getLogger(__name__)


class SubprocessError(Exception):
    pass


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
    p = subprocess.Popen(
        shell_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    log.info("run_subprocess() %s Running: '%s'", p.pid, " ".join(shell_args))
    output, err = p.communicate()

    if p.returncode != 0:
        log.error("run_subprocess() %s: Fail with status %s", p.pid, p.returncode)
        log.error("run_subprocess() stdout: %s", output)
        log.error("run_subprocess() stderr: %s", err)
        raise SubprocessError(
            f"'{' '.join(shell_args)}' \n"
            f"Subprocess {p.pid} failed with code: {p.returncode} and shell args: {shell_args}"
        )
    else:
        log.info("run_subprocess() %s: Finished with status %s", p.pid, p.returncode)
        log.debug("run_subprocess() stdout: %s", output)
        log.debug("run_subprocess() stderr: %s", err)
    return output


def run_pg_dump(output_file_path: str):
    log.info("Start pg_dump")
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
            output_file_path,
        ],
    )
    log.info("Finished pg_dump, output file: %s", output_file_path)


def get_postgres_version():
    log.info("Start postgres connection to get pg version")
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
    version = "Unknown"
    try:
        matches: list[str] = pg_version_regex.findall(result)

        for match in matches:
            version = match.strip()
            break
    except KeyError:
        log.error("Error get_postgres_version, got KeyError: %s", result)

    log.info("Calculated PostgreSQL version: %s", version)
    return version
