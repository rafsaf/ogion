import logging
import smtplib
import ssl

from backuper import config
from backuper.notifications.base_notification_system import NotificationSystem

log = logging.getLogger(__name__)

context = ssl.create_default_context()


class SMTP(NotificationSystem):
    def _send(self, message: str) -> bool:
        if not config.options.SMTP_HOST:
            log.info("skip sending smtp notification, no setup")
            return False

        log.info("sending smtp notification")

        email_message = (
            f"FROM: {config.options.SMTP_FROM_ADDR}"
            + "\n"
            + f"SUBJECT: {config.options.INSTANCE_NAME}"
            + "\n\n"
            + message
        )

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

            smtp_server.sendmail(
                from_addr=config.options.SMTP_FROM_ADDR,
                to_addrs=config.options.smtp_addresses,
                msg=email_message,
            )
            return True
