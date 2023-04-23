import argparse
import logging
import signal
import threading

from backuper import config
from backuper.backup_targets import BaseBackupTarget, File, Folder, MySQL, PostgreSQL
from backuper.storage_providers import (
    BaseBackupProvider,
    GoogleCloudStorage,
    LocalFiles,
)

exit_event = threading.Event()
log = logging.getLogger(__name__)


def quit(sig, frame):
    log.info("interrupted by %s, shutting down" % sig)
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
                "initializing postgres target, trying to connect to database: `%s`",
                target.env_name,
            )
            pg_target = PostgreSQL(**target.dict())
            targets.append(pg_target)
            log.info(
                "success initializing postgres target, obtained db version is %s: `%s`",
                pg_target.db_version,
                target.env_name,
            )
        elif target.type == config.BackupTargetEnum.FILE:
            log.info("initializing file target: `%s`", target.env_name)
            targets.append(File(**target.dict()))
            log.info("success initializing file target: `%s`", target.env_name)
        elif target.type == config.BackupTargetEnum.FOLDER:
            log.info("initializing folder target: `%s`", target.env_name)
            targets.append(Folder(**target.dict()))
            log.info("success initializing folder target: `%s`", target.env_name)
        elif target.type == config.BackupTargetEnum.MYSQL:
            log.info("initializing folder target: `%s`", target.env_name)
            targets.append(MySQL(**target.dict()))
            log.info("success initializing folder target: `%s`", target.env_name)
        else:
            raise RuntimeError(
                "panic!!! unsupported backup target",
                target.dict(),
            )
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
                log.info("start making backup of target: `%s`", target.env_name)
                backup_file = target.make_backup()
                if not backup_file:
                    continue
                success = provider.safe_post_save(backup_file=backup_file)
                if success:
                    provider.safe_clean(backup_file=backup_file)
                log.info(
                    "next planned backup of target `%s` is: %s",
                    target.env_name,
                    target.next_backup_time,
                )
        if args.single:
            exit_event.set()
        exit_event.wait(5)
    log.info("gracefully exited backuper")


if __name__ == "__main__":
    signal.signal(signalnum=signal.SIGINT, handler=quit)
    signal.signal(signalnum=signal.SIGTERM, handler=quit)
    main()
