import argparse
import logging
import signal
import threading
from datetime import datetime

from croniter import croniter

from pg_dump import config, core
from pg_dump.storage_providers import GoogleCloudStorage, LocalFiles

exit_event = threading.Event()
log = logging.getLogger(__name__)


def sleep_till_next_backup():
    now = datetime.utcnow()
    cron = croniter(
        config.CRON_RULE,
        start_time=now,
    )
    next_backup: datetime = cron.get_next(ret_type=datetime)
    wait_time = next_backup - now
    log.info("Next backup at: %s", next_backup)
    exit_event.wait(wait_time.seconds + 1)


def quit(sig, frame):
    log.info("Interrupted by %s, shutting down" % sig)
    exit_event.set()


def main():
    parser = argparse.ArgumentParser(description="Pg dump backup program")
    parser.add_argument(
        "-s", "--single", action="store_true", help="Only single backup then exit"
    )
    parser.add_argument(
        "-n", "--now", action="store_true", help="Start first backup immediatly"
    )
    args = parser.parse_args()

    if not croniter.is_valid(config.CRON_RULE):
        raise RuntimeError(
            f"Croniter: cron expression `{config.CRON_RULE}` is not valid"
        )
    core.init_pgpass_file()
    db_version = core.postgres_connection()
    if config.BACKUP_PROVIDER == config.Provider.LOCAL_FILES:
        provider = LocalFiles()
    elif config.BACKUP_PROVIDER == config.Provider.GOOGLE_CLOUD_STORAGE:
        provider = GoogleCloudStorage()
    else:
        raise RuntimeError(f"Unknown provider: `{config.BACKUP_PROVIDER}`")
    if not args.single and not args.now:
        sleep_till_next_backup()
    while not exit_event.is_set():
        backup = core.run_pg_dump(db_version=db_version)
        success = provider.safe_post_save(backup_file=backup)
        provider.safe_clean(success)
        if args.single:
            exit_event.set()
        sleep_till_next_backup()
    log.info("Gracefully exited")


if __name__ == "__main__":
    signal.signal(signalnum=signal.SIGINT, handler=quit)
    signal.signal(signalnum=signal.SIGTERM, handler=quit)
    main()
