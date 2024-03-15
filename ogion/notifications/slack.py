# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging

import requests
from requests.adapters import HTTPAdapter, Retry

from ogion import config
from ogion.notifications.base_notification_system import NotificationSystem

log = logging.getLogger(__name__)


STATUS_CODE_200 = 200


class Slack(NotificationSystem):
    def _send(self, message: str) -> bool:
        if not config.options.SLACK_WEBHOOK_URL:
            log.info("skip sending slack notification, no setup")
            return False

        log.info("sending slack notification")

        content = self.limit_message(
            message=message, limit=config.options.SLACK_MAX_MSG_LEN
        )

        with requests.session() as session:
            retry = Retry(
                total=4,
                backoff_factor=0.5,
                status_forcelist=[500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("", adapter=adapter)

            slack_resp = session.post(
                str(config.options.SLACK_WEBHOOK_URL),
                json={"text": content},
                headers={"Content-Type": "application/json"},
                timeout=3,
            )

            if slack_resp.status_code != STATUS_CODE_200:
                log.error(
                    "failed send slack `%s` to %s with status code %s and resp: %s",
                    message,
                    config.options.SLACK_WEBHOOK_URL,
                    slack_resp.status_code,
                    slack_resp.content,
                )
                return False
            return True
