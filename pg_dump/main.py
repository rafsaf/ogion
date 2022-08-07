import logging
import sys
import threading
import time
import traceback
from datetime import datetime

import croniter
from config import BASE_DIR, settings

log = logging.getLogger(__name__)
sys.path.insert(0, str(BASE_DIR))


def get_next_backup_time(cron_expression: str) -> datetime:
    now = datetime.utcnow()
    cron = croniter.croniter(
        cron_expression,
        start_time=now,
    )
    return cron.get_next(ret_type=datetime)


def main():
    from pg_dump import core

    log.info("Initialize pg_dump...")
    core.recreate_pgpass_file()
    log.info("Recreated pgpass file")
    try:
        settings.POSTGRESQL_VERSION = core.get_postgres_version()
    except core.PgDumpSubprocessError:
        error_message = traceback.format_exc()
        log.critical(error_message)
        log.critical("Unable to connect to database, aborted")
        exit(1)
    log.info("config POSTGRESQL_VERSION set to: %s", settings.POSTGRESQL_VERSION)
    log.info("Initialization finished.")

    next_backup_time = get_next_backup_time(
        settings.PGDUMP_BACKUP_POLICY_CRON_EXPRESSION
    )
    log.info("Next backup time %s.", next_backup_time)
    log.info("Waiting...")
    while True:
        now = datetime.utcnow()
        if now > next_backup_time:
            file_name = core.get_new_backup_filename(now=now)
            log.info("Calculated file name is %s", file_name)

            pg_dump_thread = threading.Thread(
                target=core.run_pg_dump, args=(file_name,)
            )
            pg_dump_thread.start()
            log.info("Start pg_dump thread...")
            # hard limit on pg_dump timeout declared in settings, no worries about infinite hang
            pg_dump_thread.join()

            if not core.get_full_backup_folder_path(file_name).stat().st_size:
                log.error("Error inside pg_dump thread, backup file empty")
                core.get_full_backup_folder_path(file_name).unlink()
                log.error("Removed empty backup file %s", file_name)
                log.error(
                    "Start cooling period %ss...",
                    settings.PGDUMP_COOLING_PERIOD_AFTER_TIMEOUT,
                )
                time.sleep(settings.PGDUMP_COOLING_PERIOD_AFTER_TIMEOUT)
            else:
                next_backup_time = get_next_backup_time(
                    settings.PGDUMP_BACKUP_POLICY_CRON_EXPRESSION
                )
                log.info("Next backup time %s.", next_backup_time)
                log.info("Waiting...")
        time.sleep(5)


if __name__ == "__main__":
    main()
