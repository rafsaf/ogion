import logging
import sys
import threading
import time
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
    settings.POSTGRESQL_VERSION = core.get_postgres_version()
    log.info("config POSTGRESQL_VERSION set to: %s", settings.POSTGRESQL_VERSION)
    core.recreate_pgpass_file()
    log.info("Initialization finished.")

    next_backup_time = get_next_backup_time(
        settings.PGDUMP_BACKUP_POLICY_CRON_EXPRESSION
    )
    log.info("Next backup time %s.", next_backup_time)
    log.info("Waiting...")
    while True:
        now = datetime.utcnow()
        if now > next_backup_time:
            file_name = "backup__pg_dump__{}__{}__{}.sql".format(
                now.strftime("%Y-%m-%d-%H:%M"),
                settings.POSTGRESQL_VERSION,
                settings.PGDUMP_DATABASE_DB,
            )
            log.info("Calculated file name is %s", file_name)
            pg_dump_thread = threading.Thread(
                target=core.run_pg_dump, args=(file_name,)
            )
            pg_dump_thread.start()
            log.info("Start pg_dump thread...")
            pg_dump_thread.join()
            # hard limit on pg_dump timeout declared in settings, no worries about infinite lock
            if not core.get_full_backup_folder_path(file_name).stat().st_size:
                log.warning("Error inside pg_dump thread, backup file empty")
                core.get_full_backup_folder_path(file_name).unlink()
                log.warning("Removed empty backup file %s", file_name)
                log.warning(
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
    # Start pg_dump process
    main()
