"""
https://discord.com/developers/docs/resources/webhook#execute-webhook
"""
import logging
import traceback
from contextlib import ContextDecorator
from datetime import datetime
from enum import StrEnum
from types import TracebackType

import requests

from backuper import config

log = logging.getLogger(__name__)


class PROGRAM_STEP(StrEnum):
    SETUP_PROVIDER = "upload provider setup"
    SETUP_TARGETS = "backup targets setup"
    BACKUP_CREATE = "backup create"
    UPLOAD = "upload to provider"


def _formated_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S,%f UTC")


class NotificationsContext(ContextDecorator):
    def __init__(
        self,
        step_name: PROGRAM_STEP,
        env_name: str | None = None,
        send_on_success: bool = False,
    ) -> None:
        self.step_name: PROGRAM_STEP = step_name
        self.env_name = env_name
        self.send_on_success = send_on_success

    def _success_message(self) -> str:
        now = _formated_now()
        message_to_send = (
            f"[SUCCESS] {now} target `{self.env_name}` uploaded new backup file "
        )
        return message_to_send

    def _fail_message(self, traceback: str) -> str:
        now = _formated_now()
        msg = f"[FAIL] {now}\nSTEP: {self.step_name}\n"
        if self.env_name:
            msg += f"TARGET: {self.env_name}\n"

        traceback_length = len(traceback)
        limit = config.FAIL_NOTIFICATION_MAX_MSG_LEN
        if traceback_length < limit:
            reason = traceback
        else:
            reason = f"{traceback[:limit]}...({traceback_length - limit} more chars)"
        msg += f"REASON:\n```\n{reason}\n```"
        return msg

    def _send_discord(self, message: str, webhook_url: str) -> None:
        if not webhook_url:
            log.debug("skip sending discord notification, no webhook url")
            return None
        try:
            discord_resp = requests.post(
                webhook_url,
                json={"content": message},
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
            if discord_resp.status_code != 204:
                log.error("failed send_discord `%s` to %s", message, webhook_url)
        except Exception as err:
            log.error("fatal error send_discord %s: %s", message, err)

    def __enter__(self) -> None:
        log.debug("start Notifications context: %s, %s", self.step_name, self.env_name)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        if exc_type and exc_val:
            tb = "".join(traceback.format_exception(None, exc_val, exc_traceback))
            log.error("step %s failed, sending notifications", self.step_name)
            fail_message = self._fail_message(traceback=tb)
            log.debug("fail message: %s", fail_message)
            self._send_discord(
                message=fail_message, webhook_url=config.DISCORD_FAIL_WEBHOOK_URL
            )
        elif self.send_on_success:
            sucess_message = self._success_message()
            self._send_discord(
                message=sucess_message,
                webhook_url=config.DISCORD_SUCCESS_WEBHOOK_URL,
            )
