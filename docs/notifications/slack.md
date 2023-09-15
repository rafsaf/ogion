---
hide:
  - toc
---

# Slack

It is possible to send messages to your Slack channels in events of failed backups.

Integration is via **Slack webhooks** and environment variables.

Follow their documentation [https://api.slack.com/messaging/webhooks#create_a_webhook](https://api.slack.com/messaging/webhooks#create_a_webhook).

You should be able to generate webhooks like `"https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"`.

## Environemt variables

| Name              | Type     | Description                                                                                     | Default |
| :---------------- | :------- | :---------------------------------------------------------------------------------------------- | :------ |
| SLACK_WEBHOOK_URL | http url | Webhook URL for fail messages.                                                                  | -       |
| SLACK_MAX_MSG_LEN | int      | Maximum length of messages send to slack API. Sensible default used. Min `150` and max `10000`. | 1500    |

## Examples:

```bash
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
```

<br>
<br>