import argparse
import logging
import signal
import threading

from backuper import config
from backuper.backup_targets import BaseBackupTarget, File, Folder, PostgreSQL
from backuper.storage_providers import (
    BaseBackupProvider,
    GoogleCloudStorage,
    LocalFiles,
)

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
            log.info(
                "start initializing connection with database: `%s`", target.env_name
            )
            targets.append(PostgreSQL(**target.dict()))
            log.info("connection with database `%s`: ok", target.env_name)
        elif target.type == config.BackupTargetEnum.FILE:
            log.info("start initializing file: `%s`", target.env_name)
            targets.append(File(**target.dict()))
            log.info("file `%s`: ok", target.env_name)
        elif target.type == config.BackupTargetEnum.FOLDER:
            log.info("start initializing folder: `%s`", target.env_name)
            targets.append(Folder(**target.dict()))
            log.info("folder `%s`: ok", target.env_name)
    return targets


def main():
    parser = argparse.ArgumentParser(description="Backuper program")
    parser.add_argument(
        "-s", "--single", action="store_true", help="Only single backup then exit"
    )
    args = parser.parse_args()

    provider = backup_provider()
    targets = backup_targets()

    while not exit_event.is_set():
        for target in targets:
            if target.next_backup() or args.single:
                backup_file = target.make_backup()
                if not backup_file:
                    continue
                success = provider.safe_post_save(backup_file=backup_file)
                if success:
                    provider.safe_clean(backup_file=backup_file)
        if args.single:
            exit_event.set()
        exit_event.wait(5)
    log.info("Gracefully exited")


if __name__ == "__main__":
    signal.signal(signalnum=signal.SIGINT, handler=quit)
    signal.signal(signalnum=signal.SIGTERM, handler=quit)
    main()
