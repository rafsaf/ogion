---
hide:
  - toc
---

# Email (SMTP)

It is possible to send messages via email using SMTP protocol. Implementation uses STARTTLS so be sure you mail server support it. For technical details refer to [https://docs.python.org/3/library/smtplib.html](https://docs.python.org/3/library/smtplib.html).

Note, when any of params `SMTP_HOST`, `SMTP_FROM_ADDR`, `SMTP_PASSWORD`, `SMTP_TO_ADDRS`  is set, all are required. If not provided, execption will be raised.

## Environemt variables

| Name           | Type                 | Description                                                                                                  | Default |
| :------------- | :------------------- | :----------------------------------------------------------------------------------------------------------- | :------ |
| SMTP_HOST      | string[**required**] | SMTP server host.                                                                                            | -       |
| SMTP_FROM_ADDR | string[**required**] | Email address that will send emails.                                                                         | -       |
| SMTP_PASSWORD  | string[**required**] | Password for `SMTP_FROM_ADDR`.                                                                               | -       |
| SMTP_TO_ADDRS  | string[**required**] | Comma separated list of email addresses to send emails. For example `email1@example.com,email2@example.com`. | -       |
| SMTP_PORT      | int                  | SMTP server port.                                                                                            | 587     |

## Examples:

```bash
SMTP_HOST="pro2.mail.ovh.net"
SMTP_FROM_ADDR="test@example.com"
SMTP_PASSWORD="changeme"
SMTP_TO_ADDRS="me@example.com,other@example.com"
SMTP_PORT=587
```

<br>
<br>