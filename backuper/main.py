import argparse
import logging
import signal
import sys
import threading
import time
from threading import Thread
from types import FrameType
from typing import NoReturn

from backuper import config, notifications
from backuper.backup_targets.base_target import BaseBackupTarget
from backuper.providers import BaseBackupProvider, GoogleCloudStorage, LocalFiles

exit_event = threading.Event()
log = logging.getLogger(__name__)


def quit(sig: int, frame: FrameType | None) -> None:
    log.info("interrupted by %s, shutting down", sig)
    exit_event.set()


def backup_provider() -> BaseBackupProvider:
    if config.BACKUP_PROVIDER == config.BackupProviderEnum.LOCAL_FILES:
        return LocalFiles()
    elif config.BACKUP_PROVIDER == config.BackupProviderEnum.GOOGLE_CLOUD_STORAGE:
        return GoogleCloudStorage()
    else:  # pragma: no cover
        raise RuntimeError(f"Unknown provider: `{config.BACKUP_PROVIDER}`")


def backup_targets() -> list[BaseBackupTarget]:
    backup_targets_map: dict[config.BackupTargetEnum, type[BaseBackupTarget]] = {}
    for backup_target in BaseBackupTarget.__subclasses__():
        backup_targets_map[backup_target.NAME] = backup_target

    backup_targets: list[BaseBackupTarget] = []
    target_models = config.create_target_models()
    if not target_models:
        raise RuntimeError("Found 0 backup targets, at least 1 is required.")

    log.info("initializating %s backup targets", len(target_models))

    for target_model in target_models:
        if target_model.target_type in backup_targets_map:
            log.info(
                "initializing target: `%s`",
                target_model.env_name,
            )
            backup_target_cls = backup_targets_map[target_model.target_type]
            log.debug("initializing %s with %s", backup_target_cls, target_model)
            backup_targets.append(backup_target_cls(**target_model.model_dump()))
            log.info(
                "success initializing target: `%s`",
                target_model.env_name,
            )
        else:  # pragma: no cover
            raise RuntimeError(
                "panic!!! unsupported backup target",
                target_model.model_dump(),
            )
    return backup_targets


def shutdown() -> NoReturn:
    timeout_secs = config.BACKUPER_SIGTERM_TIMEOUT_SECS
    start = time.time()
    deadline = start + timeout_secs
    log.info(
        "start backuper shutdown, force exit after BACKUPER_SIGTERM_TIMEOUT_SECS=%ss, "
        "use this environment to control it.",
        timeout_secs,
    )
    for thread in threading.enumerate():
        if thread.name == "MainThread":
            continue
        timeout_left = deadline - time.time()
        if timeout_left < 0:
            break
        log.info(
            "there is still backup running, waiting %ss for thread `%s` to join...",
            round(timeout_left, 2),
            thread.name,
        )
        thread.join(timeout=timeout_left)
        if thread.is_alive():
            log.warning(
                "thread `%s` is still alive!",
                thread.name,
            )
        else:
            log.info(
                "thread `%s` exited gracefully",
                thread.name,
            )
    if threading.active_count() == 1:
        log.info("gracefully exiting backuper")
        sys.exit(0)
    else:
        log.warning(
            "noooo, exiting! i am now killing myself with %d daemon threads force killed. "
            "you can extend this time using environment BACKUPER_SIGTERM_TIMEOUT_SECS.",
            threading.active_count() - 1,
        )
        sys.exit(1)


def run_backup(target: BaseBackupTarget, provider: BaseBackupProvider) -> None:
    log.info("start making backup of target: `%s`", target.env_name)
    backup_file = target.make_backup()
    if not backup_file:
        notifications.send_fail_message(
            env_name=target.env_name,
            provider_name=provider.NAME,
            reason=notifications.FAIL_REASON.BACKUP_CREATE,
            backup_file=None,
        )
        return
    upload_path = provider.safe_post_save(backup_file=backup_file)
    if upload_path:
        provider.safe_clean(backup_file=backup_file)
        notifications.send_success_message(
            env_name=target.env_name,
            provider_name=provider.NAME,
            upload_path=upload_path,
        )
    else:
        notifications.send_fail_message(
            env_name=target.env_name,
            provider_name=provider.NAME,
            reason=notifications.FAIL_REASON.UPLOAD,
            backup_file=backup_file,
        )
    log.info(
        "next planned backup of target `%s` is: %s",
        target.env_name,
        target.next_backup_time,
    )


def setup_runtime_arguments() -> None:
    parser = argparse.ArgumentParser(description="Backuper program")
    parser.add_argument(
        "-s", "--single", action="store_true", help="Only single backup then exit"
    )
    args = parser.parse_args()
    config.RUNTIME_SINGLE = args.single


def main() -> NoReturn:
    signal.signal(signalnum=signal.SIGINT, handler=quit)
    signal.signal(signalnum=signal.SIGTERM, handler=quit)

    setup_runtime_arguments()

    provider = backup_provider()
    targets = backup_targets()

    i = 0
    while not exit_event.is_set():
        for target in targets:
            if target.next_backup() or config.RUNTIME_SINGLE:
                i += 1
                backup_thread = Thread(
                    target=run_backup,
                    args=(target, provider),
                    daemon=True,
                    name=f"{target.env_name}-{i}",
                )
                backup_thread.start()
                exit_event.wait(0.5)
        if config.RUNTIME_SINGLE:
            exit_event.set()
        exit_event.wait(5)

    shutdown()


if __name__ == "__main__":  # pragma: no cover
    main()
