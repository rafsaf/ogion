# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
from typing import override

import requests
from requests.adapters import HTTPAdapter, Retry

from ogion import config
from ogion.notifications.base_notification_system import NotificationSystem

log = logging.getLogger(__name__)


STATUS_CODE_204 = 204


class Discord(NotificationSystem):
    @override
    def _send(self, message: str) -> bool:
        if not config.options.DISCORD_WEBHOOK_URL:
            log.info("skip sending discord notification, no setup")
            return False

        log.info("sending discord notification")

        content = self.limit_message(
            message=message, limit=config.options.DISCORD_MAX_MSG_LEN
        )

        with requests.session() as session:
            retry = Retry(
                total=4,
                backoff_factor=0.5,
                status_forcelist=[500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("", adapter=adapter)

            discord_resp = session.post(
                str(config.options.DISCORD_WEBHOOK_URL),
                json={"content": content},
                headers={"Content-Type": "application/json"},
                timeout=3,
            )

            if discord_resp.status_code != STATUS_CODE_204:
                log.error(
                    "failed send discord `%s` to %s with status code %s and resp: %s",
                    message,
                    config.options.DISCORD_WEBHOOK_URL,
                    discord_resp.status_code,
                    discord_resp.content,
                )
                return False
            return True
