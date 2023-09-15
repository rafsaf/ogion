---
hide:
  - toc
---

# Discord

It is possible to send messages to your Discord channels in events of failed backups.

Integration is via **Discord webhooks** and environment variables.

Follow their documentation [https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks).

You should be able to generate webhooks like `"https://discord.com/api/webhooks/1111111111/some-long-token"`.

## Environemt variables

| Name                | Type     | Description                                                                                       | Default |
| :------------------ | :------- | :------------------------------------------------------------------------------------------------ | :------ |
| DISCORD_WEBHOOK_URL | http url | Webhook URL for fail messages.                                                                    | -       |
| DISCORD_MAX_MSG_LEN | int      | Maximum length of messages send to discord API. Sensible default used. Min `150` and max `10000`. | 1500    |

## Examples:

```bash
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/1111111111/long-token"
```

<br>
<br>