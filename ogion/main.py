# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import argparse
import logging
import signal
import sys
import threading
import time
from dataclasses import dataclass
from types import FrameType
from typing import NoReturn

from ogion import config, core
from ogion.backup_targets import (
    base_target,
    targets_mapping,
)
from ogion.notifications.notifications_context import (
    PROGRAM_STEP,
    NotificationsContext,
)
from ogion.upload_providers import (
    base_provider,
    providers_mapping,
)

exit_event = threading.Event()
log = logging.getLogger(__name__)


def quit(sig: int, frame: FrameType | None) -> None:
    log.info("interrupted by %s, shutting down", sig)
    exit_event.set()


@NotificationsContext(step_name=PROGRAM_STEP.SETUP_PROVIDER)
def backup_provider() -> base_provider.BaseUploadProvider:
    provider_cls_map = providers_mapping.get_provider_cls_map()

    provider_model = core.create_provider_model()
    log.info(
        "initializing provider: `%s`",
        provider_model.name,
    )

    provider_target_cls = provider_cls_map[provider_model.name]
    log.debug("initializing %s with %s", provider_target_cls, provider_model)
    res_backup_provider = provider_target_cls(target_provider=provider_model)
    log.info(
        "success initializing provider: `%s`",
        provider_model.name,
    )
    return res_backup_provider


@NotificationsContext(step_name=PROGRAM_STEP.SETUP_TARGETS)
def backup_targets() -> list[base_target.BaseBackupTarget]:
    backup_target_cls_map = targets_mapping.get_target_cls_map()

    backup_targets: list[base_target.BaseBackupTarget] = []
    target_models = core.create_target_models()
    if not target_models:
        raise RuntimeError("Found 0 backup targets, at least 1 is required.")

    log.info("initializating %s backup targets", len(target_models))

    for target_model in target_models:
        log.info(
            "initializing target: `%s`",
            target_model.env_name,
        )
        backup_target_cls = backup_target_cls_map[target_model.name]
        log.debug("initializing %s with %s", backup_target_cls, target_model)
        backup_targets.append(backup_target_cls(target_model=target_model))
        log.info(
            "success initializing target: `%s`",
            target_model.env_name,
        )

    return backup_targets


def shutdown() -> NoReturn:  # pragma: no cover
    timeout_secs = config.options.SIGTERM_TIMEOUT_SECS
    start = time.time()
    deadline = start + timeout_secs
    log.info(
        "start ogion shutdown, force exit after SIGTERM_TIMEOUT_SECS=%ss, "
        "use this environment to control it, see https://ogion.rafsaf.pl/latest/configuration/.",
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
        log.info("gracefully exiting ogion")
        sys.exit(0)
    else:
        log.warning(
            "noooo, exiting! i am now killing myself with %d daemon threads "
            "force killed. you can extend this time using environment "
            "SIGTERM_TIMEOUT_SECS.",
            threading.active_count() - 1,
        )
        sys.exit(1)


def run_backup(target: base_target.BaseBackupTarget) -> None:
    log.info("start making backup of target: `%s`", target.env_name)

    # init provider every time in each new thread
    # eg. s3 session are not thread safe
    # this should add only minimal overhead
    provider = backup_provider()

    with NotificationsContext(
        step_name=PROGRAM_STEP.BACKUP_CREATE, env_name=target.env_name
    ):
        backup_file = target.backup()
    log.info(
        "backup file created: %s, starting post save upload to provider %s",
        backup_file,
        provider.__class__.__name__,
    )
    with NotificationsContext(
        step_name=PROGRAM_STEP.UPLOAD,
        env_name=target.env_name,
    ):
        provider.post_save(backup_file=backup_file)

    with NotificationsContext(
        step_name=PROGRAM_STEP.CLEANUP,
        env_name=target.env_name,
    ):
        provider.clean(
            backup_file=backup_file,
            max_backups=target.max_backups,
            min_retention_days=target.min_retention_days,
        )

    log.info(
        "backup and upload finished, next backup of target `%s` is: %s",
        target.env_name,
        target.next_backup_time,
    )


@dataclass
class RuntimeArgs:
    single: bool
    debug_notifications: bool
    debug_download: str | None
    list: bool
    restore_latest: bool
    target: str | None
    restore: str


def setup_runtime_arguments() -> RuntimeArgs:
    parser = argparse.ArgumentParser(description="Ogion program")
    parser.add_argument(
        "-s", "--single", action="store_true", help="Only single backup then exit"
    )
    parser.add_argument(
        "-n",
        "--debug-notifications",
        action="store_true",
        help="Check if notifications setup is working",
    )
    parser.add_argument(
        "--debug-download",
        type=str,
        default=None,
        required=False,
        help="Download given backup file locally and print path",
    )
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        required=False,
        help="Backup target",
    )
    parser.add_argument(
        "--restore-latest",
        action="store_true",
        help="Restore given target to latest database",
    )
    parser.add_argument(
        "-r",
        "--restore",
        type=str,
        default=None,
        required=False,
        help="Restore given target to backup file",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List all backups for given target",
    )
    return RuntimeArgs(**vars(parser.parse_args()))


def run_debug_notifications_and_exit() -> NoReturn:
    log.info("start run_debug_notifications_and_exit")
    try:
        with NotificationsContext(step_name=PROGRAM_STEP.DEBUG_NOTIFICATIONS):
            raise ValueError("hi! this is notifications debug exception")
    finally:
        sys.exit(0)


def run_single_all_backups() -> NoReturn:
    log.info("start run_single_all_backups")

    backup_provider()
    targets = backup_targets()

    for target in targets:
        threading.Thread(
            target=run_backup,
            args=(target,),
            daemon=True,
            name=target.pretty_thread_name,
        ).start()

    shutdown()


def run_download_backup_file(path: str) -> NoReturn:
    provider = backup_provider()

    out = provider.download_backup(path)
    print(out)
    sys.exit(0)


def run_list_backup_files(target_name: str) -> NoReturn:
    provider = backup_provider()
    targets = backup_targets()

    for target in targets:
        if target.env_name.lower() != target_name.lower():
            continue
        backups = provider.all_target_backups(target.env_name.lower())
        for i in backups:
            print(i)
        sys.exit(0)
    log.warning("target '%s' does not exist")
    sys.exit(1)


def run_restore_latest(target_name: str) -> NoReturn:
    provider = backup_provider()
    targets = backup_targets()

    for target in targets:
        if target.env_name.lower() != target_name.lower():
            continue
        backups = provider.all_target_backups(target.env_name.lower())
        if not backups:
            log.warning("no backups at all for '%s'", target_name)
            sys.exit(2)
        latest_backup = backups[0]
        path_age = provider.download_backup(latest_backup)
        path = core.run_decrypt_age_archive(path_age)
        target.restore(str(path))
        sys.exit(0)
    log.warning("target '%s' does not exist")
    sys.exit(1)


def run_restore(backup_name: str, target_name: str) -> NoReturn:
    provider = backup_provider()
    targets = backup_targets()

    for target in targets:
        if target.env_name.lower() != target_name.lower():
            continue
        backups = provider.all_target_backups(target.env_name.lower())
        if not backups:
            log.warning("no backups at all for '%s'", target_name)
            sys.exit(2)
        if backup_name not in backups:
            log.warning(
                "backup '%s' not exist at all for '%s'", backup_name, target_name
            )
            sys.exit(2)
        path_age = provider.download_backup(backup_name)
        path = core.run_decrypt_age_archive(path_age)
        target.restore(str(path))
        sys.exit(0)
    log.warning("target '%s' does not exist")
    sys.exit(1)


def run_main_loop() -> NoReturn:  # pragma: no cover
    log.info("start run_main_loop")

    backup_provider()
    targets = backup_targets()

    while not exit_event.is_set():
        for target in targets:
            if not target.next_backup():
                continue

            threading.Thread(
                target=run_backup,
                args=(target,),
                daemon=True,
                name=target.pretty_thread_name,
            ).start()
            exit_event.wait(0.5)

        exit_event.wait(5)

    shutdown()


def main() -> NoReturn:
    log.info("parsing runtime arguments...")

    runtime_args = setup_runtime_arguments()

    log.debug("runtime args: %s", runtime_args)

    log.info("starting ogion...")

    if runtime_args.debug_notifications:
        run_debug_notifications_and_exit()
    elif runtime_args.single:
        run_single_all_backups()
    elif runtime_args.debug_download is not None:
        run_download_backup_file(runtime_args.debug_download)
    elif runtime_args.list:
        if runtime_args.target is None:
            log.warning("--target must be defined to use --list")
            sys.exit(3)
        run_list_backup_files(runtime_args.target)
    elif runtime_args.restore_latest:
        if runtime_args.target is None:
            log.warning("--target must be defined to use --restore-latest")
            sys.exit(3)
        run_restore_latest(runtime_args.target)
    elif runtime_args.restore is not None:
        if runtime_args.target is None:
            log.warning("--target must be defined to use --restore-latest")
            sys.exit(3)
        run_restore(runtime_args.restore, runtime_args.target)
    else:  # pragma: no cover
        run_main_loop()


if __name__ == "__main__":  # pragma: no cover
    signal.signal(signalnum=signal.SIGINT, handler=quit)
    signal.signal(signalnum=signal.SIGTERM, handler=quit)

    main()
