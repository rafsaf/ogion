# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import override

from ogion import config
from ogion.notifications.base_notification_system import NotificationSystem

log = logging.getLogger(__name__)

context = ssl.create_default_context()


class SMTP(NotificationSystem):
    @override
    def _send(self, message: str) -> bool:
        if not config.options.SMTP_HOST:
            log.info("skip sending smtp notification, no setup")
            return False

        log.info("sending smtp notification")

        email_message = EmailMessage()
        email_message["From"] = config.options.SMTP_FROM_ADDR
        email_message["To"] = ", ".join(config.options.smtp_addresses)
        email_message["Subject"] = config.options.INSTANCE_NAME
        email_message.set_content(message)

        log.debug(
            "smtp sendmail: from: %s, to: %s, msg: %s",
            config.options.SMTP_FROM_ADDR,
            config.options.smtp_addresses,
            email_message,
        )

        with smtplib.SMTP(
            host=config.options.SMTP_HOST, port=config.options.SMTP_PORT
        ) as smtp_server:
            smtp_server.starttls(context=context)

            smtp_server.login(
                user=config.options.SMTP_FROM_ADDR,
                password=config.options.SMTP_PASSWORD.get_secret_value(),
            )

            smtp_server.send_message(email_message)
            return True
