import argparse
import logging
import signal
import threading

from pg_dump import config
from pg_dump.backup_targets import BaseBackupTarget, PostgreSQL
from pg_dump.storage_providers import BaseBackupProvider, GoogleCloudStorage, LocalFiles

exit_event = threading.Event()
log = logging.getLogger(__name__)


def quit(sig, frame):
    log.info("Interrupted by %s, shutting down" % sig)
    exit_event.set()


def backup_provider() -> BaseBackupProvider:
    map: dict[str, BaseBackupProvider] = {
        config.BackupProviderEnum.LOCAL_FILES: LocalFiles(),
        config.BackupProviderEnum.GOOGLE_CLOUD_STORAGE: GoogleCloudStorage(),
    }
    provider = map.get(config.BACKUP_PROVIDER, None)
    if provider is None:
        raise RuntimeError(f"Unknown provider: `{config.BACKUP_PROVIDER}`")
    return provider


def backup_targets() -> list[BaseBackupTarget]:
    targets = []
    for target in config.BACKUP_TARGETS:
        if target.type == config.BackupTargetEnum.POSTGRESQL:
            targets.append(PostgreSQL(**target.dict()))
    return targets


def main():
    parser = argparse.ArgumentParser(description="Pg dump backup program")
    parser.add_argument(
        "-s", "--single", action="store_true", help="Only single backup then exit"
    )
    parser.add_argument(
        "-n", "--now", action="store_true", help="Start first backup immediatly"
    )
    parser.parse_args()

    # if not croniter.is_valid(config.CRON_RULE):
    #     raise RuntimeError(
    #         f"Croniter: cron expression `{config.CRON_RULE}` is not valid"
    #     )
    provider = backup_provider()
    targets = backup_targets()

    while not exit_event.is_set():
        for target in targets:
            if target.next_backup():
                backup_file = target.make_backup()
                if not backup_file:
                    continue
                success = provider.safe_post_save(backup_file=backup_file)
                provider.safe_clean(success)
        # if args.single:
        #     exit_event.set()
        exit_event.wait(5)
    log.info("Gracefully exited")


if __name__ == "__main__":
    signal.signal(signalnum=signal.SIGINT, handler=quit)
    signal.signal(signalnum=signal.SIGTERM, handler=quit)
    main()
