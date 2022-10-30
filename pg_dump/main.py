import logging
import signal
import threading
from datetime import datetime

import croniter

from pg_dump import config, core
from pg_dump.providers import Local

exit_event = threading.Event()
log = logging.getLogger(__name__)


def sleep_till_next_backup():
    now = datetime.utcnow()
    cron = croniter.croniter(
        config.CRON_RULE,
        start_time=now,
    )
    next_backup: datetime = cron.get_next(ret_type=datetime)
    wait_time = next_backup - now
    exit_event.wait(wait_time.seconds + 1)


def quit(sig, frame):
    log.info("Interrupted by %s, shutting down" % sig)
    exit_event.set()


def main():
    core.init_pgpass_file()
    db_version = core.postgres_connection()
    provider = Local()
    sleep_till_next_backup()

    while not exit_event.is_set():
        backup = core.run_pg_dump(db_version=db_version)
        provider.post_save(backup_file=backup)
        provider.clean()
        sleep_till_next_backup()
    log.info("Gracefully exited")


if __name__ == "__main__":
    signal.signal(signalnum=signal.SIGINT, handler=quit)
    signal.signal(signalnum=signal.SIGTERM, handler=quit)
    main()
