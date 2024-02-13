"""
https://discord.com/developers/docs/resources/webhook#execute-webhook
"""

import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from contextlib import ContextDecorator
from datetime import datetime, timezone
from enum import StrEnum
from types import TracebackType

from backuper import config
from backuper.notifications.discord import Discord
from backuper.notifications.slack import Slack
from backuper.notifications.smtp import SMTP

log = logging.getLogger(__name__)


class PROGRAM_STEP(StrEnum):
    SETUP_PROVIDER = "upload provider setup"
    SETUP_TARGETS = "backup targets setup"
    BACKUP_CREATE = "backup create"
    UPLOAD = "upload to provider"
    CLEANUP = "cleanup old backups"
    DEBUG_NOTIFICATIONS = "debug check notifications are fired"


class NotificationsContext(ContextDecorator):
    def __init__(
        self,
        step_name: PROGRAM_STEP,
        env_name: str | None = None,
    ) -> None:
        self.step_name: PROGRAM_STEP = step_name
        self.env_name = env_name

    def create_fail_message(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_traceback: TracebackType,
    ) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S,%f %Z")
        msg = f"[FAIL] {now}\nStep: {self.step_name}\n"
        msg += f"Backuper Host: {config.options.INSTANCE_NAME}\n"
        if self.env_name:
            msg += f"Target: {self.env_name}\n"
        msg += f"Exception Type: {exc_type}\n"
        msg += f"Exception Value: {exc_val}\n"

        tb = "".join(traceback.format_exception(exc_type, exc_val, exc_traceback))
        msg += f"\n{tb}\n"
        return msg

    def send_all(self, message: str) -> None:
        with ThreadPoolExecutor() as executor:
            executor.submit(Discord().send, message)
            executor.submit(SMTP().send, message)
            executor.submit(Slack().send, message)

    def __enter__(self) -> None:
        log.debug("start notifications context: %s, %s", self.step_name, self.env_name)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        if exc_type and exc_val and exc_traceback:
            log.error("step %s failed, sending notifications", self.step_name)

            fail_message = self.create_fail_message(
                exc_type=exc_type, exc_val=exc_val, exc_traceback=exc_traceback
            )

            log.debug("fail message: %s", fail_message)

            self.send_all(message=fail_message)
